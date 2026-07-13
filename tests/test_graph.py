import pytest

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    ToolMessage,
)

from graph.nodes import get_recent_context
from graph.routing import route_after_agent


# =============================================================================
# get_recent_context Tests
# =============================================================================


def test_get_recent_context_returns_copy_when_history_is_within_limit():
    messages = [
        HumanMessage(content="User turn 1"),
        AIMessage(content="Assistant turn 1"),
        HumanMessage(content="User turn 2"),
        AIMessage(content="Assistant turn 2"),
    ]

    result = get_recent_context(
        messages,
        max_turns=2,
    )

    assert result == messages
    assert result is not messages


def test_get_recent_context_returns_empty_list_for_zero_turn_limit():
    messages = [
        HumanMessage(content="User turn 1"),
        AIMessage(content="Assistant turn 1"),
    ]

    result = get_recent_context(
        messages,
        max_turns=0,
    )

    assert result == []


def test_get_recent_context_returns_empty_list_for_negative_turn_limit():
    messages = [
        HumanMessage(content="User turn 1"),
        AIMessage(content="Assistant turn 1"),
    ]

    result = get_recent_context(
        messages,
        max_turns=-1,
    )

    assert result == []


def test_get_recent_context_keeps_only_most_recent_complete_turns():
    messages = [
        HumanMessage(content="User turn 1"),
        AIMessage(content="Assistant turn 1"),
        HumanMessage(content="User turn 2"),
        AIMessage(content="Assistant turn 2"),
        HumanMessage(content="User turn 3"),
        AIMessage(content="Assistant turn 3"),
    ]

    result = get_recent_context(
        messages,
        max_turns=2,
    )

    assert result == [
        messages[2],
        messages[3],
        messages[4],
        messages[5],
    ]


def test_get_recent_context_preserves_tool_messages_inside_retained_turn():
    messages = [
        HumanMessage(content="Old request"),
        AIMessage(content="Old response"),
        HumanMessage(content="Read notes.txt"),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "read_file",
                    "args": {
                        "path": "notes.txt",
                    },
                    "id": "tool-call-1",
                    "type": "tool_call",
                }
            ],
        ),
        ToolMessage(
            content='{"ok": true}',
            tool_call_id="tool-call-1",
        ),
        AIMessage(content="File read successfully."),
    ]

    result = get_recent_context(
        messages,
        max_turns=1,
    )

    assert result == messages[2:]

    assert isinstance(
        result[2],
        ToolMessage,
    )


def test_get_recent_context_does_not_modify_original_message_list():
    messages = [
        HumanMessage(content="User turn 1"),
        AIMessage(content="Assistant turn 1"),
        HumanMessage(content="User turn 2"),
        AIMessage(content="Assistant turn 2"),
    ]

    original_messages = messages.copy()

    get_recent_context(
        messages,
        max_turns=1,
    )

    assert messages == original_messages


def test_get_recent_context_returns_copy_when_no_human_messages_exist():
    messages = [
        AIMessage(content="Assistant message"),
        ToolMessage(
            content='{"ok": true}',
            tool_call_id="tool-call-1",
        ),
    ]

    result = get_recent_context(
        messages,
        max_turns=1,
    )

    assert result == messages
    assert result is not messages


# =============================================================================
# route_after_agent Tests
# =============================================================================


def test_route_after_agent_routes_to_tools_when_latest_ai_message_has_tool_calls():
    state = {
        "messages": [
            HumanMessage(content="Read notes.txt"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "read_file",
                        "args": {
                            "path": "notes.txt",
                        },
                        "id": "tool-call-1",
                        "type": "tool_call",
                    }
                ],
            ),
        ]
    }

    result = route_after_agent(state)

    assert result == "tools"


def test_route_after_agent_routes_to_end_when_latest_ai_message_has_no_tool_calls():
    state = {
        "messages": [
            HumanMessage(content="Hello"),
            AIMessage(content="Hello!"),
        ]
    }

    result = route_after_agent(state)

    assert result == "__end__"


def test_route_after_agent_rejects_empty_message_history():
    state = {
        "messages": [],
    }

    with pytest.raises(
        ValueError,
        match="Cannot route an empty message history",
    ):
        route_after_agent(state)


def test_route_after_agent_rejects_non_ai_latest_message():
    state = {
        "messages": [
            HumanMessage(content="Hello"),
        ]
    }

    with pytest.raises(
        TypeError,
        match="Expected the latest message to be an AIMessage",
    ):
        route_after_agent(state)


# =============================================================================
# agent_node Tests
# =============================================================================


class FakeAgentModel:
    """
    Deterministic fake model used to test agent_node without calling Groq.
    """

    def __init__(
        self,
        response=None,
        error=None,
    ):
        self.response = response
        self.error = error
        self.received_messages = None
        self.invoke_count = 0

    def invoke(self, messages):
        self.invoke_count += 1
        self.received_messages = messages

        if self.error is not None:
            raise self.error

        return self.response


def test_agent_node_injects_system_prompt_and_invokes_model_once(
    monkeypatch: pytest.MonkeyPatch,
):
    import graph.nodes

    fake_response = AIMessage(
        content="Fake response",
    )

    fake_model = FakeAgentModel(
        response=fake_response,
    )

    monkeypatch.setattr(
        graph.nodes,
        "get_agent_model",
        lambda: fake_model,
    )

    state = {
        "messages": [
            HumanMessage(content="Hello"),
        ]
    }

    result = graph.nodes.agent_node(state)

    assert fake_model.invoke_count == 1

    assert isinstance(
        fake_model.received_messages[0],
        graph.nodes.SystemMessage,
    )

    assert (
        fake_model.received_messages[0].content
        == graph.nodes.SYSTEM_PROMPT
    )

    assert fake_model.received_messages[1:] == state["messages"]

    assert result == {
        "messages": [
            fake_response,
        ]
    }


def test_agent_node_passes_only_bounded_recent_context_to_model(
    monkeypatch: pytest.MonkeyPatch,
):
    import graph.nodes

    fake_response = AIMessage(
        content="Bounded response",
    )

    fake_model = FakeAgentModel(
        response=fake_response,
    )

    monkeypatch.setattr(
        graph.nodes,
        "get_agent_model",
        lambda: fake_model,
    )

    messages = []

    for turn_number in range(
        1,
        graph.nodes.MAX_CONTEXT_TURNS + 6,
    ):
        messages.extend(
            [
                HumanMessage(
                    content=f"User turn {turn_number}",
                ),
                AIMessage(
                    content=f"Assistant turn {turn_number}",
                ),
            ]
        )

    original_messages = messages.copy()

    state = {
        "messages": messages,
    }

    result = graph.nodes.agent_node(state)

    received_context = (
        fake_model.received_messages[1:]
    )

    expected_context = graph.nodes.get_recent_context(
        messages,
    )

    assert received_context == expected_context

    assert received_context[0].content == "User turn 6"

    assert received_context[-1].content == "Assistant turn 15"

    assert state["messages"] == original_messages

    assert result == {
        "messages": [
            fake_response,
        ]
    }


def test_agent_node_preserves_tool_sequence_in_bounded_context(
    monkeypatch: pytest.MonkeyPatch,
):
    import graph.nodes

    fake_response = AIMessage(
        content="Final response",
    )

    fake_model = FakeAgentModel(
        response=fake_response,
    )

    monkeypatch.setattr(
        graph.nodes,
        "get_agent_model",
        lambda: fake_model,
    )

    messages = [
        HumanMessage(content="Old request"),
        AIMessage(content="Old response"),
    ]

    for turn_number in range(
        1,
        graph.nodes.MAX_CONTEXT_TURNS,
    ):
        messages.extend(
            [
                HumanMessage(
                    content=f"User turn {turn_number}",
                ),
                AIMessage(
                    content=f"Assistant turn {turn_number}",
                ),
            ]
        )

    messages.extend(
        [
            HumanMessage(content="Read notes.txt"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "read_file",
                        "args": {
                            "path": "notes.txt",
                        },
                        "id": "tool-call-agent-test",
                        "type": "tool_call",
                    }
                ],
            ),
            ToolMessage(
                content='{"ok": true}',
                tool_call_id="tool-call-agent-test",
            ),
            AIMessage(content="File read successfully."),
        ]
    )

    state = {
        "messages": messages,
    }

    graph.nodes.agent_node(state)

    received_context = (
        fake_model.received_messages[1:]
    )

    assert received_context == graph.nodes.get_recent_context(
        messages,
    )

    assert any(
        isinstance(message, ToolMessage)
        for message in received_context
    )

    tool_message_index = next(
        index
        for index, message in enumerate(received_context)
        if isinstance(message, ToolMessage)
    )

    assert isinstance(
        received_context[tool_message_index - 1],
        AIMessage,
    )

    assert (
        received_context[
            tool_message_index - 1
        ].tool_calls[0]["name"]
        == "read_file"
    )

    assert isinstance(
        received_context[tool_message_index + 1],
        AIMessage,
    )


def test_agent_node_returns_tool_calling_ai_response_unchanged(
    monkeypatch: pytest.MonkeyPatch,
):
    import graph.nodes

    fake_response = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "read_file",
                "args": {
                    "path": "notes.txt",
                },
                "id": "tool-call-response-test",
                "type": "tool_call",
            }
        ],
    )

    fake_model = FakeAgentModel(
        response=fake_response,
    )

    monkeypatch.setattr(
        graph.nodes,
        "get_agent_model",
        lambda: fake_model,
    )

    state = {
        "messages": [
            HumanMessage(content="Read notes.txt"),
        ]
    }

    result = graph.nodes.agent_node(state)

    assert result["messages"] == [
        fake_response,
    ]

    assert (
        result["messages"][0].tool_calls[0]["name"]
        == "read_file"
    )


def test_agent_node_propagates_model_exception(
    monkeypatch: pytest.MonkeyPatch,
):
    import graph.nodes

    fake_model = FakeAgentModel(
        error=RuntimeError(
            "Fake provider failure",
        ),
    )

    monkeypatch.setattr(
        graph.nodes,
        "get_agent_model",
        lambda: fake_model,
    )

    state = {
        "messages": [
            HumanMessage(content="Hello"),
        ]
    }

    with pytest.raises(
        RuntimeError,
        match="Fake provider failure",
    ):
        graph.nodes.agent_node(state)

    assert fake_model.invoke_count == 1


def test_agent_node_does_not_modify_persisted_state(
    monkeypatch: pytest.MonkeyPatch,
):
    import graph.nodes

    fake_response = AIMessage(
        content="Fake response",
    )

    fake_model = FakeAgentModel(
        response=fake_response,
    )

    monkeypatch.setattr(
        graph.nodes,
        "get_agent_model",
        lambda: fake_model,
    )

    messages = [
        HumanMessage(content="Hello"),
        AIMessage(content="Previous response"),
        HumanMessage(content="New request"),
    ]

    original_messages = messages.copy()

    state = {
        "messages": messages,
    }

    graph.nodes.agent_node(state)

    assert state["messages"] == original_messages

    assert state["messages"] is messages


# =============================================================================
# agent_node Tests
# =============================================================================


class FakeAgentModel:
    """
    Deterministic fake model used to test agent_node without calling Groq.
    """

    def __init__(
        self,
        response=None,
        error=None,
    ):
        self.response = response
        self.error = error
        self.received_messages = None
        self.invoke_count = 0

    def invoke(self, messages):
        self.invoke_count += 1
        self.received_messages = messages

        if self.error is not None:
            raise self.error

        return self.response


def test_agent_node_injects_system_prompt_and_invokes_model_once(
    monkeypatch: pytest.MonkeyPatch,
):
    import graph.nodes

    fake_response = AIMessage(
        content="Fake response",
    )

    fake_model = FakeAgentModel(
        response=fake_response,
    )

    monkeypatch.setattr(
        graph.nodes,
        "get_agent_model",
        lambda: fake_model,
    )

    state = {
        "messages": [
            HumanMessage(content="Hello"),
        ]
    }

    result = graph.nodes.agent_node(state)

    assert fake_model.invoke_count == 1

    assert isinstance(
        fake_model.received_messages[0],
        graph.nodes.SystemMessage,
    )

    assert (
        fake_model.received_messages[0].content
        == graph.nodes.SYSTEM_PROMPT
    )

    assert fake_model.received_messages[1:] == state["messages"]

    assert result == {
        "messages": [
            fake_response,
        ]
    }


def test_agent_node_passes_only_bounded_recent_context_to_model(
    monkeypatch: pytest.MonkeyPatch,
):
    import graph.nodes

    fake_response = AIMessage(
        content="Bounded response",
    )

    fake_model = FakeAgentModel(
        response=fake_response,
    )

    monkeypatch.setattr(
        graph.nodes,
        "get_agent_model",
        lambda: fake_model,
    )

    messages = []

    for turn_number in range(
        1,
        graph.nodes.MAX_CONTEXT_TURNS + 6,
    ):
        messages.extend(
            [
                HumanMessage(
                    content=f"User turn {turn_number}",
                ),
                AIMessage(
                    content=f"Assistant turn {turn_number}",
                ),
            ]
        )

    original_messages = messages.copy()

    state = {
        "messages": messages,
    }

    result = graph.nodes.agent_node(state)

    received_context = (
        fake_model.received_messages[1:]
    )

    expected_context = graph.nodes.get_recent_context(
        messages,
    )

    assert received_context == expected_context

    assert received_context[0].content == "User turn 6"

    assert received_context[-1].content == "Assistant turn 15"

    assert state["messages"] == original_messages

    assert result == {
        "messages": [
            fake_response,
        ]
    }


def test_agent_node_preserves_tool_sequence_in_bounded_context(
    monkeypatch: pytest.MonkeyPatch,
):
    import graph.nodes

    fake_response = AIMessage(
        content="Final response",
    )

    fake_model = FakeAgentModel(
        response=fake_response,
    )

    monkeypatch.setattr(
        graph.nodes,
        "get_agent_model",
        lambda: fake_model,
    )

    messages = [
        HumanMessage(content="Old request"),
        AIMessage(content="Old response"),
    ]

    for turn_number in range(
        1,
        graph.nodes.MAX_CONTEXT_TURNS,
    ):
        messages.extend(
            [
                HumanMessage(
                    content=f"User turn {turn_number}",
                ),
                AIMessage(
                    content=f"Assistant turn {turn_number}",
                ),
            ]
        )

    messages.extend(
        [
            HumanMessage(content="Read notes.txt"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "read_file",
                        "args": {
                            "path": "notes.txt",
                        },
                        "id": "tool-call-agent-test",
                        "type": "tool_call",
                    }
                ],
            ),
            ToolMessage(
                content='{"ok": true}',
                tool_call_id="tool-call-agent-test",
            ),
            AIMessage(content="File read successfully."),
        ]
    )

    state = {
        "messages": messages,
    }

    graph.nodes.agent_node(state)

    received_context = (
        fake_model.received_messages[1:]
    )

    assert received_context == graph.nodes.get_recent_context(
        messages,
    )

    assert any(
        isinstance(message, ToolMessage)
        for message in received_context
    )

    tool_message_index = next(
        index
        for index, message in enumerate(received_context)
        if isinstance(message, ToolMessage)
    )

    assert isinstance(
        received_context[tool_message_index - 1],
        AIMessage,
    )

    assert (
        received_context[
            tool_message_index - 1
        ].tool_calls[0]["name"]
        == "read_file"
    )

    assert isinstance(
        received_context[tool_message_index + 1],
        AIMessage,
    )


def test_agent_node_returns_tool_calling_ai_response_unchanged(
    monkeypatch: pytest.MonkeyPatch,
):
    import graph.nodes

    fake_response = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "read_file",
                "args": {
                    "path": "notes.txt",
                },
                "id": "tool-call-response-test",
                "type": "tool_call",
            }
        ],
    )

    fake_model = FakeAgentModel(
        response=fake_response,
    )

    monkeypatch.setattr(
        graph.nodes,
        "get_agent_model",
        lambda: fake_model,
    )

    state = {
        "messages": [
            HumanMessage(content="Read notes.txt"),
        ]
    }

    result = graph.nodes.agent_node(state)

    assert result["messages"] == [
        fake_response,
    ]

    assert (
        result["messages"][0].tool_calls[0]["name"]
        == "read_file"
    )


def test_agent_node_propagates_model_exception(
    monkeypatch: pytest.MonkeyPatch,
):
    import graph.nodes

    fake_model = FakeAgentModel(
        error=RuntimeError(
            "Fake provider failure",
        ),
    )

    monkeypatch.setattr(
        graph.nodes,
        "get_agent_model",
        lambda: fake_model,
    )

    state = {
        "messages": [
            HumanMessage(content="Hello"),
        ]
    }

    with pytest.raises(
        RuntimeError,
        match="Fake provider failure",
    ):
        graph.nodes.agent_node(state)

    assert fake_model.invoke_count == 1


def test_agent_node_does_not_modify_persisted_state(
    monkeypatch: pytest.MonkeyPatch,
):
    import graph.nodes

    fake_response = AIMessage(
        content="Fake response",
    )

    fake_model = FakeAgentModel(
        response=fake_response,
    )

    monkeypatch.setattr(
        graph.nodes,
        "get_agent_model",
        lambda: fake_model,
    )

    messages = [
        HumanMessage(content="Hello"),
        AIMessage(content="Previous response"),
        HumanMessage(content="New request"),
    ]

    original_messages = messages.copy()

    state = {
        "messages": messages,
    }

    graph.nodes.agent_node(state)

    assert state["messages"] == original_messages

    assert state["messages"] is messages


# =============================================================================
# Compiled Graph Execution Tests
# =============================================================================


class SequencedFakeAgentModel:
    """
    Deterministic fake model that returns responses in sequence.

    Used to test the complete compiled graph execution loop without calling
    an external LLM provider.
    """

    def __init__(self, responses):
        self.responses = list(responses)
        self.received_message_batches = []
        self.invoke_count = 0

    def invoke(self, messages):
        self.received_message_batches.append(
            list(messages)
        )

        if self.invoke_count >= len(self.responses):
            raise AssertionError(
                "Fake model received more invocations than expected."
            )

        response = self.responses[
            self.invoke_count
        ]

        self.invoke_count += 1

        return response


def test_compiled_graph_executes_agent_tool_agent_end_loop(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
):
    import core.paths
    import graph.nodes

    from graph.builder import build_graph

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    test_file = workspace / "notes.txt"

    test_file.write_text(
        "LangGraph tool loop test content",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        core.paths,
        "WORKSPACE_ROOT",
        workspace,
    )

    tool_call_id = "compiled-loop-tool-call"

    first_response = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "read_file",
                "args": {
                    "path": "notes.txt",
                },
                "id": tool_call_id,
                "type": "tool_call",
            }
        ],
    )

    final_response = AIMessage(
        content="The file was read successfully.",
    )

    fake_model = SequencedFakeAgentModel(
        responses=[
            first_response,
            final_response,
        ]
    )

    monkeypatch.setattr(
        graph.nodes,
        "get_agent_model",
        lambda: fake_model,
    )

    graph = build_graph()

    result = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content="Read notes.txt",
                )
            ],
        }
    )

    messages = result["messages"]

    assert fake_model.invoke_count == 2

    assert len(messages) == 4

    assert isinstance(
        messages[0],
        HumanMessage,
    )

    assert messages[1] == first_response

    assert isinstance(
        messages[2],
        ToolMessage,
    )

    assert (
        messages[2].tool_call_id
        == tool_call_id
    )

    assert (
        "LangGraph tool loop test content"
        in messages[2].content
    )

    assert messages[3] == final_response

    assert (
        messages[-1].content
        == "The file was read successfully."
    )


def test_compiled_graph_ends_without_executing_tools_when_agent_returns_final_response(
    monkeypatch: pytest.MonkeyPatch,
):
    import graph.nodes

    from graph.builder import build_graph

    final_response = AIMessage(
        content="Direct final response.",
    )

    fake_model = SequencedFakeAgentModel(
        responses=[
            final_response,
        ]
    )

    monkeypatch.setattr(
        graph.nodes,
        "get_agent_model",
        lambda: fake_model,
    )

    graph = build_graph()

    result = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content="Hello",
                )
            ],
        }
    )

    assert fake_model.invoke_count == 1

    messages = result["messages"]

    assert len(messages) == 2

    assert isinstance(
        messages[0],
        HumanMessage,
    )

    assert messages[0].content == "Hello"

    assert isinstance(
        messages[1],
        AIMessage,
    )

    assert (
        messages[1].content
        == "Direct final response."
    )

    assert messages[1].tool_calls == []


def test_compiled_graph_passes_tool_result_back_to_second_agent_invocation(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
):
    import core.paths
    import graph.nodes

    from graph.builder import build_graph

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    (workspace / "context.txt").write_text(
        "Tool result visible to model",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        core.paths,
        "WORKSPACE_ROOT",
        workspace,
    )

    tool_call_id = "tool-result-context-call"

    first_response = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "read_file",
                "args": {
                    "path": "context.txt",
                },
                "id": tool_call_id,
                "type": "tool_call",
            }
        ],
    )

    final_response = AIMessage(
        content="I received the tool result.",
    )

    fake_model = SequencedFakeAgentModel(
        responses=[
            first_response,
            final_response,
        ]
    )

    monkeypatch.setattr(
        graph.nodes,
        "get_agent_model",
        lambda: fake_model,
    )

    graph = build_graph()

    graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content="Read context.txt",
                )
            ],
        }
    )

    assert fake_model.invoke_count == 2

    second_model_messages = (
        fake_model.received_message_batches[1]
    )

    tool_messages = [
        message
        for message in second_model_messages
        if isinstance(message, ToolMessage)
    ]

    assert len(tool_messages) == 1

    assert (
        tool_messages[0].tool_call_id
        == tool_call_id
    )

    assert (
        "Tool result visible to model"
        in tool_messages[0].content
    )


def test_compiled_graph_preserves_message_order_across_tool_loop(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
):
    import core.paths
    import graph.nodes

    from graph.builder import build_graph

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    (workspace / "order.txt").write_text(
        "Order test content",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        core.paths,
        "WORKSPACE_ROOT",
        workspace,
    )

    first_response = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "read_file",
                "args": {
                    "path": "order.txt",
                },
                "id": "message-order-tool-call",
                "type": "tool_call",
            }
        ],
    )

    final_response = AIMessage(
        content="Order preserved.",
    )

    fake_model = SequencedFakeAgentModel(
        responses=[
            first_response,
            final_response,
        ]
    )

    monkeypatch.setattr(
        graph.nodes,
        "get_agent_model",
        lambda: fake_model,
    )

    graph = build_graph()

    result = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content="Read order.txt",
                )
            ],
        }
    )

    message_types = [
        type(message)
        for message in result["messages"]
    ]

    assert message_types == [
        HumanMessage,
        AIMessage,
        ToolMessage,
        AIMessage,
    ]


# =============================================================================
# SQLite Checkpoint Persistence Tests
# =============================================================================


def test_compiled_graph_persists_messages_across_same_thread_invocations(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
):
    import sqlite3

    import graph.nodes

    from graph.builder import build_graph
    from langgraph.checkpoint.sqlite import SqliteSaver

    database_path = tmp_path / "checkpoints.db"

    connection = sqlite3.connect(
        database_path,
        check_same_thread=False,
    )

    checkpointer = SqliteSaver(connection)

    class ContextAwareFakeModel:
        def __init__(self):
            self.invoke_count = 0
            self.received_message_batches = []

        def invoke(self, messages):
            self.invoke_count += 1
            self.received_message_batches.append(
                list(messages)
            )

            human_contents = [
                message.content
                for message in messages
                if isinstance(message, HumanMessage)
            ]

            if (
                "What is my codename?"
                in human_contents
            ):
                return AIMessage(
                    content="Your codename is Atlas.",
                )

            return AIMessage(
                content="I will remember Atlas.",
            )

    fake_model = ContextAwareFakeModel()

    monkeypatch.setattr(
        graph.nodes,
        "get_agent_model",
        lambda: fake_model,
    )

    graph = build_graph(
        checkpointer=checkpointer,
    )

    config = {
        "configurable": {
            "thread_id": "same-thread",
        }
    }

    try:
        first_result = graph.invoke(
            {
                "messages": [
                    HumanMessage(
                        content="My codename is Atlas.",
                    )
                ],
            },
            config=config,
        )

        second_result = graph.invoke(
            {
                "messages": [
                    HumanMessage(
                        content="What is my codename?",
                    )
                ],
            },
            config=config,
        )

        persisted_state = graph.get_state(
            config,
        )

        persisted_messages = (
            persisted_state.values["messages"]
        )

        assert fake_model.invoke_count == 2

        assert len(first_result["messages"]) == 2

        assert len(second_result["messages"]) == 4

        assert [
            message.content
            for message in persisted_messages
        ] == [
            "My codename is Atlas.",
            "I will remember Atlas.",
            "What is my codename?",
            "Your codename is Atlas.",
        ]

        second_model_human_messages = [
            message.content
            for message
            in fake_model.received_message_batches[1]
            if isinstance(message, HumanMessage)
        ]

        assert second_model_human_messages == [
            "My codename is Atlas.",
            "What is my codename?",
        ]

    finally:
        connection.close()


def test_compiled_graph_keeps_different_threads_isolated(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
):
    import sqlite3

    import graph.nodes

    from graph.builder import build_graph
    from langgraph.checkpoint.sqlite import SqliteSaver

    database_path = tmp_path / "checkpoints.db"

    connection = sqlite3.connect(
        database_path,
        check_same_thread=False,
    )

    checkpointer = SqliteSaver(connection)

    class EchoFakeModel:
        def invoke(self, messages):
            latest_human_message = next(
                message
                for message in reversed(messages)
                if isinstance(message, HumanMessage)
            )

            return AIMessage(
                content=(
                    f"Processed: "
                    f"{latest_human_message.content}"
                ),
            )

    fake_model = EchoFakeModel()

    monkeypatch.setattr(
        graph.nodes,
        "get_agent_model",
        lambda: fake_model,
    )

    graph = build_graph(
        checkpointer=checkpointer,
    )

    alpha_config = {
        "configurable": {
            "thread_id": "alpha-thread",
        }
    }

    beta_config = {
        "configurable": {
            "thread_id": "beta-thread",
        }
    }

    try:
        graph.invoke(
            {
                "messages": [
                    HumanMessage(
                        content="AlphaOne",
                    )
                ],
            },
            config=alpha_config,
        )

        graph.invoke(
            {
                "messages": [
                    HumanMessage(
                        content="BetaTwo",
                    )
                ],
            },
            config=beta_config,
        )

        alpha_state = graph.get_state(
            alpha_config,
        )

        beta_state = graph.get_state(
            beta_config,
        )

        alpha_contents = [
            message.content
            for message
            in alpha_state.values["messages"]
        ]

        beta_contents = [
            message.content
            for message
            in beta_state.values["messages"]
        ]

        assert alpha_contents == [
            "AlphaOne",
            "Processed: AlphaOne",
        ]

        assert beta_contents == [
            "BetaTwo",
            "Processed: BetaTwo",
        ]

        assert "BetaTwo" not in alpha_contents

        assert "AlphaOne" not in beta_contents

        assert (
            alpha_state.config[
                "configurable"
            ]["checkpoint_id"]
            !=
            beta_state.config[
                "configurable"
            ]["checkpoint_id"]
        )

    finally:
        connection.close()


def test_compiled_graph_recovers_persisted_thread_after_new_graph_instance(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
):
    import sqlite3

    import graph.nodes

    from graph.builder import build_graph
    from langgraph.checkpoint.sqlite import SqliteSaver

    database_path = tmp_path / "checkpoints.db"

    class RestartAwareFakeModel:
        def __init__(self):
            self.received_message_batches = []

        def invoke(self, messages):
            self.received_message_batches.append(
                list(messages)
            )

            human_contents = [
                message.content
                for message in messages
                if isinstance(message, HumanMessage)
            ]

            if (
                "What is my deployment codename?"
                in human_contents
            ):
                return AIMessage(
                    content=(
                        "Your deployment codename "
                        "is Phoenix."
                    ),
                )

            return AIMessage(
                content="I will remember Phoenix.",
            )

    fake_model = RestartAwareFakeModel()

    monkeypatch.setattr(
        graph.nodes,
        "get_agent_model",
        lambda: fake_model,
    )

    thread_config = {
        "configurable": {
            "thread_id": "restart-thread",
        }
    }

    first_connection = sqlite3.connect(
        database_path,
        check_same_thread=False,
    )

    first_checkpointer = SqliteSaver(
        first_connection,
    )

    first_graph = build_graph(
        checkpointer=first_checkpointer,
    )

    try:
        first_graph.invoke(
            {
                "messages": [
                    HumanMessage(
                        content=(
                            "My deployment codename "
                            "is Phoenix."
                        ),
                    )
                ],
            },
            config=thread_config,
        )

    finally:
        first_connection.close()

    second_connection = sqlite3.connect(
        database_path,
        check_same_thread=False,
    )

    second_checkpointer = SqliteSaver(
        second_connection,
    )

    second_graph = build_graph(
        checkpointer=second_checkpointer,
    )

    try:
        recovered_state = second_graph.get_state(
            thread_config,
        )

        recovered_contents = [
            message.content
            for message
            in recovered_state.values["messages"]
        ]

        assert recovered_contents == [
            "My deployment codename is Phoenix.",
            "I will remember Phoenix.",
        ]

        second_result = second_graph.invoke(
            {
                "messages": [
                    HumanMessage(
                        content=(
                            "What is my deployment "
                            "codename?"
                        ),
                    )
                ],
            },
            config=thread_config,
        )

        assert [
            message.content
            for message
            in second_result["messages"]
        ] == [
            "My deployment codename is Phoenix.",
            "I will remember Phoenix.",
            "What is my deployment codename?",
            "Your deployment codename is Phoenix.",
        ]

        second_invocation_messages = (
            fake_model.received_message_batches[-1]
        )

        second_invocation_human_contents = [
            message.content
            for message
            in second_invocation_messages
            if isinstance(message, HumanMessage)
        ]

        assert second_invocation_human_contents == [
            "My deployment codename is Phoenix.",
            "What is my deployment codename?",
        ]

    finally:
        second_connection.close()
