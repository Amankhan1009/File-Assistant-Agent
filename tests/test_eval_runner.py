import core.paths

from langchain_core.messages import HumanMessage

import pytest

from dataclasses import FrozenInstanceError

from evals.evaluator import (
    EvaluationResult,
    create_evaluation_result,
)
from evals.scenarios import (
    EvaluationScenario,
    SCENARIOS,
)



# =============================================================================
# Single Scenario Runner Tests
# =============================================================================


class FakeEvaluationGraph:
    """
    Deterministic graph test double used to verify scenario orchestration.

    The fake records invocation inputs and returns a predefined completed
    graph state without calling a language model.
    """

    def __init__(self, completed_state):
        self.completed_state = completed_state
        self.invocations = []

    def invoke(self, input_state, config=None):
        self.invocations.append(
            {
                "input_state": input_state,
                "config": config,
            }
        )

        return self.completed_state


def test_run_scenario_invokes_graph_with_human_message_and_thread_config(
    tmp_path: Path,
):
    from langchain_core.messages import AIMessage

    from evals.evaluator import run_scenario

    scenario = EvaluationScenario(
        name="runner-invocation",
        user_request="List the workspace files.",
    )

    graph = FakeEvaluationGraph(
        {
            "messages": [
                AIMessage(
                    content="The workspace is empty.",
                ),
            ],
        }
    )

    result = run_scenario(
        scenario,
        graph,
        base_directory=tmp_path,
    )

    assert len(graph.invocations) == 1

    invocation = graph.invocations[0]

    input_messages = invocation[
        "input_state"
    ]["messages"]

    assert len(input_messages) == 1
    assert isinstance(
        input_messages[0],
        HumanMessage,
    )

    assert (
        input_messages[0].content
        == scenario.user_request
    )

    assert invocation["config"] == {
        "configurable": {
            "thread_id": "eval-runner-invocation",
        },
    }

    assert result.passed is True


def test_run_scenario_seeds_workspace_before_graph_invocation(
    tmp_path: Path,
):
    from langchain_core.messages import AIMessage

    from evals.evaluator import run_scenario

    scenario = EvaluationScenario(
        name="runner-seeding",
        user_request="Inspect seeded files.",
        initial_directories=(
            "docs",
        ),
        initial_files={
            "docs/source.txt": "seeded content",
        },
    )

    class WorkspaceInspectingGraph:
        def invoke(self, input_state, config=None):
            assert (
                core.paths.WORKSPACE_ROOT
                / "docs"
            ).is_dir()

            assert (
                core.paths.WORKSPACE_ROOT
                / "docs"
                / "source.txt"
            ).read_text(
                encoding="utf-8",
            ) == "seeded content"

            return {
                "messages": [
                    AIMessage(
                        content="Seeded state inspected.",
                    ),
                ],
            }

    result = run_scenario(
        scenario,
        WorkspaceInspectingGraph(),
        base_directory=tmp_path,
    )

    assert result.passed is True


def test_run_scenario_evaluates_observed_tool_calls_and_filesystem_state(
    tmp_path: Path,
):
    from langchain_core.messages import AIMessage

    from evals.evaluator import run_scenario
    from tools.write_tools import create_file

    scenario = EvaluationScenario(
        name="runner-evaluation",
        user_request="Create result.txt",
        expected_tools=(
            "create_file",
        ),
        forbidden_tools=(
            "delete_file",
        ),
        expected_files={
            "result.txt": "created by fake graph",
        },
        required_response_substrings=(
            "created",
        ),
    )

    class ToolExecutingFakeGraph:
        def invoke(self, input_state, config=None):
            tool_result = create_file.invoke(
                {
                    "path": "result.txt",
                    "content": "created by fake graph",
                }
            )

            assert tool_result["ok"] is True

            return {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "create_file",
                                "args": {
                                    "path": "result.txt",
                                    "content": "created by fake graph",
                                },
                                "id": "runner-tool-call",
                                "type": "tool_call",
                            }
                        ],
                    ),
                    AIMessage(
                        content="The file was created.",
                    ),
                ],
            }

    result = run_scenario(
        scenario,
        ToolExecutingFakeGraph(),
        base_directory=tmp_path,
    )

    assert result.passed is True

    assert result.observed_tools == (
        "create_file",
    )

    assert result.final_response == (
        "The file was created."
    )

    assert result.failures == ()


def test_run_scenario_returns_failures_from_deterministic_evaluation(
    tmp_path: Path,
):
    from langchain_core.messages import AIMessage

    from evals.evaluator import run_scenario

    scenario = EvaluationScenario(
        name="runner-failure",
        user_request="Create missing.txt",
        expected_tools=(
            "create_file",
        ),
        expected_files={
            "missing.txt": "expected content",
        },
        required_response_substrings=(
            "created",
        ),
    )

    graph = FakeEvaluationGraph(
        {
            "messages": [
                AIMessage(
                    content="I did nothing.",
                ),
            ],
        }
    )

    result = run_scenario(
        scenario,
        graph,
        base_directory=tmp_path,
    )

    assert result.passed is False

    assert result.observed_tools == ()

    assert result.final_response == (
        "I did nothing."
    )

    assert result.failures == (
        "Expected tool was not called: create_file",
        "Expected file does not exist: missing.txt",
        "Required response substring missing: created",
    )


def test_run_scenario_restores_real_workspace_after_graph_failure(
    tmp_path: Path,
):
    from evals.evaluator import run_scenario

    original_workspace = core.paths.WORKSPACE_ROOT

    scenario = EvaluationScenario(
        name="runner-graph-failure",
        user_request="Trigger graph failure.",
    )

    class FailingGraph:
        def invoke(self, input_state, config=None):
            raise RuntimeError(
                "simulated graph failure"
            )

    with pytest.raises(
        RuntimeError,
        match="simulated graph failure",
    ):
        run_scenario(
            scenario,
            FailingGraph(),
            base_directory=tmp_path,
        )

    assert (
        core.paths.WORKSPACE_ROOT
        == original_workspace
    )


def test_run_scenario_does_not_modify_real_workspace(
    tmp_path: Path,
):
    from langchain_core.messages import AIMessage

    from evals.evaluator import run_scenario
    from tools.write_tools import create_file

    real_workspace = core.paths.WORKSPACE_ROOT

    before = sorted(
        path.relative_to(
            real_workspace,
        ).as_posix()
        for path in real_workspace.rglob("*")
    )

    scenario = EvaluationScenario(
        name="runner-real-workspace-safety",
        user_request="Create isolated.txt",
        expected_tools=(
            "create_file",
        ),
        expected_files={
            "isolated.txt": "isolated content",
        },
    )

    class IsolatedWritingGraph:
        def invoke(self, input_state, config=None):
            result = create_file.invoke(
                {
                    "path": "isolated.txt",
                    "content": "isolated content",
                }
            )

            assert result["ok"] is True

            return {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "create_file",
                                "args": {
                                    "path": "isolated.txt",
                                    "content": "isolated content",
                                },
                                "id": "isolated-tool-call",
                                "type": "tool_call",
                            }
                        ],
                    ),
                    AIMessage(
                        content="Completed.",
                    ),
                ],
            }

    result = run_scenario(
        scenario,
        IsolatedWritingGraph(),
        base_directory=tmp_path,
    )

    after = sorted(
        path.relative_to(
            real_workspace,
        ).as_posix()
        for path in real_workspace.rglob("*")
    )

    assert result.passed is True
    assert before == after

    assert not (
        real_workspace
        / "isolated.txt"
    ).exists()


# =============================================================================
# Real Evaluation Scenario Registry Tests
# =============================================================================


def test_scenarios_registry_contains_first_real_scenario():
    assert SCENARIOS[0].name == "create-file-with-content"


def test_create_file_with_content_scenario_contract():
    scenario = SCENARIOS[0]

    assert scenario == EvaluationScenario(
        name="create-file-with-content",
        user_request=(
            "Create a new file called evaluation.txt containing exactly: "
            "LangGraph agents can safely execute filesystem tools."
        ),
        expected_tools=(
            "create_file",
        ),
        forbidden_tools=(
            "delete_file",
            "delete_directory",
        ),
        expected_files={
            "evaluation.txt": (
                "LangGraph agents can safely execute filesystem tools."
            ),
        },
        required_response_substrings=(
            "created",
        ),
        forbidden_response_substrings=(
            "failed",
        ),
    )


def test_scenarios_registry_contains_second_real_scenario():
    assert SCENARIOS[1].name == "read-and-append-file"


def test_read_and_append_file_scenario_contract():
    scenario = SCENARIOS[1]

    assert scenario == EvaluationScenario(
        name="read-and-append-file",
        user_request=(
            "Read notes.txt and append a new line containing exactly: "
            "The agent loop continues until no more tools are required."
        ),
        expected_tools=(
            "read_file",
            "append_file",
        ),
        forbidden_tools=(
            "create_file",
            "delete_file",
            "delete_directory",
        ),
        initial_files={
            "notes.txt": (
                "LangGraph agents can call tools.\n"
            ),
        },
        expected_files={
            "notes.txt": (
                "LangGraph agents can call tools.\n"
                "The agent loop continues until no more tools are required.\n"
            ),
        },
        required_response_substrings=(
            "appended",
        ),
        forbidden_response_substrings=(
            "failed",
        ),
    )

def test_scenarios_registry_contains_third_real_scenario():
    assert SCENARIOS[2].name == "search-files-by-name"


def test_search_files_by_name_scenario_contract():
    scenario = SCENARIOS[2]

    assert scenario == EvaluationScenario(
        name="search-files-by-name",
        user_request=(
            "Find all files whose names contain summary."
        ),
        expected_tools=(
            "search_files",
        ),
        forbidden_tools=(
            "read_file",
            "create_file",
            "append_file",
            "delete_file",
            "delete_directory",
            "move_path",
        ),
        initial_files={
            "reports/summary.txt": "Current summary.",
            "archive/summary_old.txt": "Archived summary.",
            "notes.txt": "General notes.",
        },
        expected_files={
            "reports/summary.txt": "Current summary.",
            "archive/summary_old.txt": "Archived summary.",
            "notes.txt": "General notes.",
        },
        required_response_substrings=(
            "reports/summary.txt",
            "archive/summary_old.txt",
        ),
        forbidden_response_substrings=(
            "failed",
        ),
    )
