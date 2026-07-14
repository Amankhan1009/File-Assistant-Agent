from contextlib import contextmanager

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

import api.main as api_main


# =============================================================================
# Test Doubles
# =============================================================================


class FakeCheckpointer:
    pass


class FakeGraph:
    def __init__(self):
        self.invoke_calls = []

    def invoke(
        self,
        state,
        config,
    ):
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
# Helpers
# =============================================================================


def install_api_runtime(
    monkeypatch,
):
    checkpointer = FakeCheckpointer()
    graph = FakeGraph()

    runtime_events = []

    @contextmanager
    def fake_checkpointer_runtime():
        runtime_events.append("enter")

        try:
            yield checkpointer

        finally:
            runtime_events.append("exit")

    build_calls = []

    def fake_build_graph(
        checkpointer,
    ):
        build_calls.append(checkpointer)

        return graph

    monkeypatch.setattr(
        api_main,
        "checkpointer_runtime",
        fake_checkpointer_runtime,
    )

    monkeypatch.setattr(
        api_main,
        "build_graph",
        fake_build_graph,
    )

    return (
        checkpointer,
        graph,
        runtime_events,
        build_calls,
    )


# =============================================================================
# API Tests
# =============================================================================


def test_lifespan_initializes_graph_and_cleans_up_runtime(
    monkeypatch,
):
    (
        checkpointer,
        graph,
        runtime_events,
        build_calls,
    ) = install_api_runtime(monkeypatch)

    with TestClient(api_main.app):
        assert runtime_events == ["enter"]
        assert build_calls == [checkpointer]
        assert api_main.app.state.checkpointer is checkpointer
        assert api_main.app.state.graph is graph

    assert runtime_events == [
        "enter",
        "exit",
    ]


def test_health_endpoint_returns_healthy_status(
    monkeypatch,
):
    install_api_runtime(monkeypatch)

    with TestClient(api_main.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
    }


def test_chat_endpoint_invokes_graph_with_thread_id(
    monkeypatch,
):
    (
        _,
        graph,
        _,
        _,
    ) = install_api_runtime(monkeypatch)

    with TestClient(api_main.app) as client:
        response = client.post(
            "/chat",
            json={
                "message": "Create notes.txt",
                "thread_id": "api-test-thread",
            },
        )

    assert response.status_code == 200

    assert response.json() == {
        "response": "Fake API response.",
        "thread_id": "api-test-thread",
    }

    assert len(graph.invoke_calls) == 1

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
