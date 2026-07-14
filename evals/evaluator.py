from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage

from evals.scenarios import EvaluationScenario


@dataclass(frozen=True)
class EvaluationResult:
    """
    Structured result produced after evaluating one scenario.

    The result stores the scenario identity, pass/fail status, observed tool
    sequence, final assistant response, and human-readable failure reasons.
    """

    scenario_name: str

    passed: bool

    observed_tools: tuple[str, ...] = ()

    final_response: str = ""

    failures: tuple[str, ...] = ()


def create_evaluation_result(
    scenario: EvaluationScenario,
    *,
    observed_tools: tuple[str, ...] = (),
    final_response: str = "",
    failures: tuple[str, ...] = (),
) -> EvaluationResult:
    """
    Create an immutable evaluation result from observed evaluation data.

    A scenario passes only when no failure reasons were recorded.
    """
    return EvaluationResult(
        scenario_name=scenario.name,
        passed=not failures,
        observed_tools=observed_tools,
        final_response=final_response,
        failures=failures,
    )


# =============================================================================
# Isolated Evaluation Workspace
# =============================================================================


def create_isolated_workspace(
    base_directory,
):
    """
    Create and return an empty isolated workspace directory.

    The caller controls the lifetime of the base directory. This function
    creates only the workspace root used by one evaluation scenario.
    """
    workspace = base_directory / "workspace"

    workspace.mkdir()

    return workspace


# =============================================================================
# Scenario Filesystem Seeding
# =============================================================================


def seed_scenario_workspace(
    scenario: EvaluationScenario,
    workspace,
) -> None:
    """
    Populate an isolated workspace with a scenario's initial filesystem state.

    Directories are created before files so scenarios may declare files inside
    explicitly configured directory structures.

    Parent directories required by initial files are also created to keep
    scenario definitions concise.
    """
    for directory in scenario.initial_directories:
        directory_path = workspace / directory

        directory_path.mkdir(
            parents=True,
            exist_ok=True,
        )

    for relative_path, content in scenario.initial_files.items():
        file_path = workspace / relative_path

        file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_path.write_text(
            content,
            encoding="utf-8",
        )


# =============================================================================
# Evaluation Workspace Binding
# =============================================================================


from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import core.paths


@contextmanager
def bind_workspace(
    workspace: Path,
) -> Iterator[None]:
    """
    Temporarily bind production filesystem path resolution to an evaluation
    workspace.

    All production filesystem tools resolve paths through
    core.paths.WORKSPACE_ROOT. Replacing that module-level reference causes
    the real tools to operate against the isolated evaluation workspace.

    The original workspace root is always restored, including when execution
    inside the context raises an exception.
    """
    original_workspace_root = core.paths.WORKSPACE_ROOT

    core.paths.WORKSPACE_ROOT = workspace.resolve()

    try:
        yield

    finally:
        core.paths.WORKSPACE_ROOT = original_workspace_root


# =============================================================================
# Deterministic Scenario Assertions
# =============================================================================


def collect_scenario_failures(
    scenario: EvaluationScenario,
    *,
    workspace: Path,
    observed_tools: tuple[str, ...] = (),
    final_response: str = "",
) -> tuple[str, ...]:
    """
    Evaluate deterministic scenario expectations and return failure reasons.

    Expected tools use membership semantics: every expected tool must appear
    at least once in observed_tools. Tool order and exact call counts are not
    enforced by this function.
    """
    failures: list[str] = []

    observed_tool_set = set(observed_tools)

    for tool_name in scenario.expected_tools:
        if tool_name not in observed_tool_set:
            failures.append(
                f"Expected tool was not called: {tool_name}"
            )

    for tool_name in scenario.forbidden_tools:
        if tool_name in observed_tool_set:
            failures.append(
                f"Forbidden tool was called: {tool_name}"
            )

    for relative_path, expected_content in scenario.expected_files.items():
        file_path = workspace / relative_path

        if not file_path.exists():
            failures.append(
                f"Expected file does not exist: {relative_path}"
            )

            continue

        if not file_path.is_file():
            failures.append(
                f"Expected file path is not a regular file: {relative_path}"
            )

            continue

        try:
            actual_content = file_path.read_text(
                encoding="utf-8",
            )

        except UnicodeDecodeError:
            failures.append(
                f"Expected file is not valid UTF-8 text: {relative_path}"
            )

            continue

        except OSError:
            failures.append(
                f"Expected file could not be read: {relative_path}"
            )

            continue

        if actual_content != expected_content:
            failures.append(
                f"Expected file content mismatch: {relative_path}"
            )

    for relative_path in scenario.expected_absent_paths:
        path = workspace / relative_path

        if path.exists():
            failures.append(
                f"Expected path to be absent: {relative_path}"
            )

    normalized_response = final_response.casefold()

    for substring in scenario.required_response_substrings:
        if substring.casefold() not in normalized_response:
            failures.append(
                f"Required response substring missing: {substring}"
            )

    for substring in scenario.forbidden_response_substrings:
        if substring.casefold() in normalized_response:
            failures.append(
                f"Forbidden response substring present: {substring}"
            )

    return tuple(failures)


def evaluate_scenario_outcome(
    scenario: EvaluationScenario,
    *,
    workspace: Path,
    observed_tools: tuple[str, ...] = (),
    final_response: str = "",
) -> EvaluationResult:
    """
    Evaluate deterministic scenario expectations and create the final result.
    """
    failures = collect_scenario_failures(
        scenario,
        workspace=workspace,
        observed_tools=observed_tools,
        final_response=final_response,
    )

    return create_evaluation_result(
        scenario,
        observed_tools=observed_tools,
        final_response=final_response,
        failures=failures,
    )


# =============================================================================
# Graph Execution Observation
# =============================================================================


from collections.abc import Mapping, Sequence
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage


def extract_observed_tools(
    messages: Sequence[BaseMessage],
) -> tuple[str, ...]:
    """
    Extract tool names from AI tool calls in chronological message order.

    Tool calls are observed from AIMessage.tool_calls because those messages
    represent the agent's actual tool-selection decisions.

    Malformed tool calls without a non-empty string name are ignored.
    """
    observed_tools: list[str] = []

    for message in messages:
        if not isinstance(message, AIMessage):
            continue

        for tool_call in message.tool_calls:
            if not isinstance(tool_call, Mapping):
                continue

            tool_name = tool_call.get("name")

            if not isinstance(tool_name, str):
                continue

            if not tool_name:
                continue

            observed_tools.append(tool_name)

    return tuple(observed_tools)


def extract_final_response(
    messages: Sequence[BaseMessage],
) -> str:
    """
    Return the content of the latest AI message without tool calls.

    The final assistant response is the most recent AIMessage that represents
    a user-facing answer rather than an intermediate tool-selection message.

    Raises:
        ValueError:
            If no final AI response exists.
    """
    for message in reversed(messages):
        if not isinstance(message, AIMessage):
            continue

        if message.tool_calls:
            continue

        if isinstance(message.content, str):
            return message.content

        return str(message.content)

    raise ValueError(
        "Completed graph state does not contain a final AI response."
    )


def extract_execution_observation(
    graph_state: Mapping[str, Any],
) -> tuple[tuple[str, ...], str]:
    """
    Extract the observed tool sequence and final response from graph state.

    Raises:
        ValueError:
            If graph state does not contain a valid message sequence.
    """
    messages = graph_state.get("messages")

    if (
        not isinstance(messages, Sequence)
        or isinstance(
            messages,
            (
                str,
                bytes,
                bytearray,
            ),
        )
    ):
        raise ValueError(
            "Completed graph state does not contain a valid message sequence."
        )

    observed_tools = extract_observed_tools(
        messages,
    )

    final_response = extract_final_response(
        messages,
    )

    return observed_tools, final_response


# =============================================================================
# Single Scenario Execution
# =============================================================================


def run_scenario(
    scenario: EvaluationScenario,
    graph: Any,
    *,
    base_directory: Path,
) -> EvaluationResult:
    """
    Execute one evaluation scenario against a graph.

    The scenario runs inside an isolated temporary workspace. Initial
    filesystem state is seeded before graph invocation, production filesystem
    tools are temporarily redirected to the isolated workspace, and observed
    graph behavior is evaluated deterministically after execution.

    Exceptions raised by graph execution are allowed to propagate while
    workspace binding is still restored by the context manager.
    """
    workspace = create_isolated_workspace(
        base_directory,
    )

    seed_scenario_workspace(
        scenario,
        workspace,
    )

    config = {
        "configurable": {
            "thread_id": f"eval-{scenario.name}",
        },
    }

    with bind_workspace(workspace):
        completed_state = graph.invoke(
            {
                "messages": [
                    HumanMessage(
                        content=scenario.user_request,
                    ),
                ],
            },
            config=config,
        )

        (
            observed_tools,
            final_response,
        ) = extract_execution_observation(
            completed_state,
        )

        return evaluate_scenario_outcome(
            scenario,
            workspace=workspace,
            observed_tools=observed_tools,
            final_response=final_response,
        )
