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
# Graph Execution Observation Tests
# =============================================================================


def test_extract_observed_tools_returns_empty_tuple_without_tool_calls():
    from langchain_core.messages import (
        AIMessage,
        HumanMessage,
    )

    from evals.evaluator import extract_observed_tools

    messages = [
        HumanMessage(content="Hello"),
        AIMessage(content="Hello!"),
    ]

    assert extract_observed_tools(messages) == ()


def test_extract_observed_tools_preserves_chronological_tool_order():
    from langchain_core.messages import (
        AIMessage,
        HumanMessage,
        ToolMessage,
    )

    from evals.evaluator import extract_observed_tools

    messages = [
        HumanMessage(content="Create and read notes.txt"),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "create_file",
                    "args": {
                        "path": "notes.txt",
                        "content": "hello",
                    },
                    "id": "call-1",
                    "type": "tool_call",
                }
            ],
        ),
        ToolMessage(
            content='{"ok": true}',
            tool_call_id="call-1",
        ),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "read_file",
                    "args": {
                        "path": "notes.txt",
                    },
                    "id": "call-2",
                    "type": "tool_call",
                }
            ],
        ),
        ToolMessage(
            content='{"ok": true}',
            tool_call_id="call-2",
        ),
        AIMessage(content="Done."),
    ]

    assert extract_observed_tools(messages) == (
        "create_file",
        "read_file",
    )


def test_extract_observed_tools_preserves_multiple_calls_from_same_ai_message():
    from langchain_core.messages import AIMessage

    from evals.evaluator import extract_observed_tools

    messages = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "read_file",
                    "args": {
                        "path": "a.txt",
                    },
                    "id": "call-1",
                    "type": "tool_call",
                },
                {
                    "name": "read_file",
                    "args": {
                        "path": "b.txt",
                    },
                    "id": "call-2",
                    "type": "tool_call",
                },
            ],
        ),
        AIMessage(content="Done."),
    ]

    assert extract_observed_tools(messages) == (
        "read_file",
        "read_file",
    )


def test_extract_final_response_returns_latest_non_tool_call_ai_message():
    from langchain_core.messages import (
        AIMessage,
        HumanMessage,
        ToolMessage,
    )

    from evals.evaluator import extract_final_response

    messages = [
        HumanMessage(content="Read notes.txt"),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "read_file",
                    "args": {
                        "path": "notes.txt",
                    },
                    "id": "call-1",
                    "type": "tool_call",
                }
            ],
        ),
        ToolMessage(
            content='{"ok": true}',
            tool_call_id="call-1",
        ),
        AIMessage(content="The file contains hello."),
    ]

    assert extract_final_response(
        messages,
    ) == "The file contains hello."


def test_extract_final_response_uses_latest_final_ai_message():
    from langchain_core.messages import AIMessage

    from evals.evaluator import extract_final_response

    messages = [
        AIMessage(content="Earlier response."),
        AIMessage(content="Latest response."),
    ]

    assert extract_final_response(
        messages,
    ) == "Latest response."


def test_extract_final_response_raises_without_final_ai_response():
    from langchain_core.messages import (
        AIMessage,
        HumanMessage,
    )

    from evals.evaluator import extract_final_response

    messages = [
        HumanMessage(content="Create file"),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "create_file",
                    "args": {
                        "path": "notes.txt",
                        "content": "hello",
                    },
                    "id": "call-1",
                    "type": "tool_call",
                }
            ],
        ),
    ]

    with pytest.raises(
        ValueError,
        match="does not contain a final AI response",
    ):
        extract_final_response(messages)


def test_extract_execution_observation_returns_tools_and_response():
    from langchain_core.messages import (
        AIMessage,
        HumanMessage,
        ToolMessage,
    )

    from evals.evaluator import extract_execution_observation

    graph_state = {
        "messages": [
            HumanMessage(content="Create notes.txt"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "create_file",
                        "args": {
                            "path": "notes.txt",
                            "content": "hello",
                        },
                        "id": "call-1",
                        "type": "tool_call",
                    }
                ],
            ),
            ToolMessage(
                content='{"ok": true}',
                tool_call_id="call-1",
            ),
            AIMessage(content="The file was created."),
        ]
    }

    observed_tools, final_response = extract_execution_observation(
        graph_state,
    )

    assert observed_tools == (
        "create_file",
    )

    assert final_response == "The file was created."


def test_extract_execution_observation_rejects_missing_messages():
    from evals.evaluator import extract_execution_observation

    with pytest.raises(
        ValueError,
        match="does not contain a valid message sequence",
    ):
        extract_execution_observation({})


def test_extract_execution_observation_rejects_non_sequence_messages():
    from evals.evaluator import extract_execution_observation

    with pytest.raises(
        ValueError,
        match="does not contain a valid message sequence",
    ):
        extract_execution_observation(
            {
                "messages": 123,
            }
        )


def test_extract_execution_observation_rejects_string_messages():
    from evals.evaluator import extract_execution_observation

    with pytest.raises(
        ValueError,
        match="does not contain a valid message sequence",
    ):
        extract_execution_observation(
            {
                "messages": "not-a-message-sequence",
            }
        )


