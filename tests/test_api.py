# =============================================================================
# Standard Library Imports
# =============================================================================


from contextlib import contextmanager
from types import SimpleNamespace


# =============================================================================
# Third-Party Imports
# =============================================================================


from fastapi.testclient import TestClient
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
)


# =============================================================================
# Project Imports
# =============================================================================


import api.main as api_main


# =============================================================================
# Test Doubles
# =============================================================================


class FakeCheckpointer:
    """
    Test double for the application checkpointer.

    Stores a configurable checkpoint result and records every get() call so
    API tests can verify checkpoint retrieval behavior.
    """

    def __init__(
        self,
        checkpoint=None,
    ):
        self.checkpoint = checkpoint

        self.get_calls = []


    def get(
        self,
        config,
    ):
        """
        Record the checkpoint lookup configuration and return the configured
        checkpoint result.
        """
        self.get_calls.append(
            config,
        )

        return self.checkpoint


class FakeGraph:
    """
    Test double for the compiled LangGraph application.

    Records graph invocations and returns a predictable assistant response.
    """

    def __init__(self):
        self.invoke_calls = []


    def invoke(
        self,
        state,
        config,
    ):
        """
        Record a graph invocation and return a deterministic assistant message.
        """
        self.invoke_calls.append(
            {
                "state": state,
                "config": config,
            }
        )

        return {
            "messages": [
                AIMessage(
                    content="Fake API response.",
                )
            ]
        }


# =============================================================================
# Test Runtime Installation Helper
# =============================================================================


def install_api_runtime(
    monkeypatch,
    checkpoint=None,
):
    """
    Replace the production database runtime and graph builder with test
    doubles.

    An optional checkpoint can be supplied for tests that exercise checkpoint
    retrieval behavior.

    The fake runtime exposes the same resource boundary as the production
    DatabaseRuntime object.
    """
    checkpointer = FakeCheckpointer(
        checkpoint=checkpoint,
    )

    graph = FakeGraph()

    runtime_events = []


    # -------------------------------------------------------------------------
    # Fake Database Runtime
    # -------------------------------------------------------------------------


    fake_runtime = SimpleNamespace(
        checkpointer=checkpointer,
        pool=None,
    )


    @contextmanager
    def fake_database_runtime():
        runtime_events.append(
            "enter",
        )

        try:
            yield fake_runtime

        finally:
            runtime_events.append(
                "exit",
            )


    # -------------------------------------------------------------------------
    # Fake Graph Builder
    # -------------------------------------------------------------------------


    build_calls = []


    def fake_build_graph(
        checkpointer,
    ):
        build_calls.append(
            checkpointer,
        )

        return graph


    # -------------------------------------------------------------------------
    # Runtime Dependency Replacement
    # -------------------------------------------------------------------------


    monkeypatch.setattr(
        api_main,
        "database_runtime",
        fake_database_runtime,
    )

    monkeypatch.setattr(
        api_main,
        "build_graph",
        fake_build_graph,
    )


    # -------------------------------------------------------------------------
    # Installed Runtime Resources
    # -------------------------------------------------------------------------


    return (
        checkpointer,
        graph,
        runtime_events,
        build_calls,
    )


# =============================================================================
# Application Lifespan Tests
# =============================================================================


def test_lifespan_initializes_graph_and_cleans_up_runtime(
    monkeypatch,
):
    """
    Verify that application startup initializes the shared database runtime
    and graph, and application shutdown cleans up the runtime.
    """
    (
        checkpointer,
        graph,
        runtime_events,
        build_calls,
    ) = install_api_runtime(
        monkeypatch,
    )

    with TestClient(api_main.app):
        assert runtime_events == [
            "enter",
        ]

        assert build_calls == [
            checkpointer,
        ]

        assert (
            api_main.app.state.checkpointer
            is checkpointer
        )

        assert (
            api_main.app.state.graph
            is graph
        )

        assert (
            api_main.app.state.conversation_repository
            is None
        )

    assert runtime_events == [
        "enter",
        "exit",
    ]


# =============================================================================
# Health Endpoint Tests
# =============================================================================


def test_health_endpoint_returns_healthy_status(
    monkeypatch,
):
    """
    Verify that the health endpoint reports a healthy API status.
    """
    install_api_runtime(
        monkeypatch,
    )

    with TestClient(api_main.app) as client:
        response = client.get(
            "/health",
        )

    assert response.status_code == 200

    assert response.json() == {
        "status": "healthy",
    }


# =============================================================================
# Chat Endpoint Tests
# =============================================================================


def test_chat_endpoint_invokes_graph_with_thread_id(
    monkeypatch,
):
    """
    Verify that the chat endpoint accepts conversation ownership metadata and
    forwards the user message and thread ID to the shared LangGraph instance.
    """
    (
        _,
        graph,
        _,
        _,
    ) = install_api_runtime(
        monkeypatch,
    )

    with TestClient(
        api_main.app,
    ) as client:
        response = client.post(
            "/chat",
            json={
                "message": "Create notes.txt",
                "thread_id": "api-test-thread",
                "owner_id": "browser-test-owner",
            },
        )

    assert response.status_code == 200

    assert response.json() == {
        "response": "Fake API response.",
        "thread_id": "api-test-thread",
    }

    assert len(
        graph.invoke_calls,
    ) == 1

    invoke_call = graph.invoke_calls[0]

    assert invoke_call["state"] == {
        "messages": [
            (
                "user",
                "Create notes.txt",
            )
        ]
    }

    assert invoke_call["config"] == {
        "configurable": {
            "thread_id": "api-test-thread",
        }
    }


# =============================================================================
# Thread Message History Endpoint Tests
# =============================================================================


def test_get_thread_messages_returns_persisted_conversation(
    monkeypatch,
):
    """
    Verify that the thread history endpoint retrieves the latest checkpoint
    using the requested thread ID and returns persisted user and assistant
    messages in frontend-safe JSON format.
    """


    # -------------------------------------------------------------------------
    # Test Data
    # -------------------------------------------------------------------------


    thread_id = "existing-thread"

    checkpoint = {
        "channel_values": {
            "messages": [
                HumanMessage(
                    content="Hello",
                ),
                AIMessage(
                    content="Hi there",
                ),
            ]
        }
    }


    # -------------------------------------------------------------------------
    # Install Test Runtime
    # -------------------------------------------------------------------------


    (
        checkpointer,
        _,
        _,
        _,
    ) = install_api_runtime(
        monkeypatch,
        checkpoint=checkpoint,
    )


    # -------------------------------------------------------------------------
    # Request Execution
    # -------------------------------------------------------------------------


    with TestClient(
        api_main.app,
    ) as client:
        response = client.get(
            f"/threads/{thread_id}/messages",
        )


    # -------------------------------------------------------------------------
    # Response Assertions
    # -------------------------------------------------------------------------


    assert response.status_code == 200

    assert response.json() == {
        "thread_id": thread_id,
        "messages": [
            {
                "role": "user",
                "content": "Hello",
            },
            {
                "role": "assistant",
                "content": "Hi there",
            },
        ],
    }


    # -------------------------------------------------------------------------
    # Checkpointer Interaction Assertions
    # -------------------------------------------------------------------------


    assert checkpointer.get_calls == [
        {
            "configurable": {
                "thread_id": thread_id,
            }
        }
    ]


def test_get_thread_messages_returns_empty_messages_for_missing_thread(
    monkeypatch,
):
    """
    Verify that requesting message history for a nonexistent thread returns
    HTTP 200 with an empty message list.
    """


    # -------------------------------------------------------------------------
    # Test Data
    # -------------------------------------------------------------------------


    thread_id = "missing-thread"


    # -------------------------------------------------------------------------
    # Install Test Runtime
    # -------------------------------------------------------------------------


    (
        checkpointer,
        _,
        _,
        _,
    ) = install_api_runtime(
        monkeypatch,
        checkpoint=None,
    )


    # -------------------------------------------------------------------------
    # Request Execution
    # -------------------------------------------------------------------------


    with TestClient(
        api_main.app,
    ) as client:
        response = client.get(
            f"/threads/{thread_id}/messages",
        )


    # -------------------------------------------------------------------------
    # Response Assertions
    # -------------------------------------------------------------------------


    assert response.status_code == 200

    assert response.json() == {
        "thread_id": thread_id,
        "messages": [],
    }


    # -------------------------------------------------------------------------
    # Checkpointer Interaction Assertions
    # -------------------------------------------------------------------------


    assert checkpointer.get_calls == [
        {
            "configurable": {
                "thread_id": thread_id,
            }
        }
    ]