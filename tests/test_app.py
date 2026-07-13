import argparse

import pytest

from langchain_core.messages import AIMessage
from langgraph.errors import GraphRecursionError

import app


# =============================================================================
# Test Doubles
# =============================================================================


class FakeConnection:
    def __init__(
        self,
        close_error: Exception | None = None,
    ):
        self.close_error = close_error
        self.close_calls = 0

    def close(self):
        self.close_calls += 1

        if self.close_error is not None:
            raise self.close_error


class FakeCheckpointer:
    def __init__(
        self,
        close_error: Exception | None = None,
    ):
        self.conn = FakeConnection(
            close_error=close_error,
        )


class FakeGraph:
    def __init__(
        self,
        results=None,
        errors=None,
    ):
        self.results = list(results or [])
        self.errors = list(errors or [])
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

        if self.errors:
            error = self.errors.pop(0)

            if error is not None:
                raise error

        if self.results:
            return self.results.pop(0)

        return {
            "messages": [
                AIMessage(
                    content="Default fake response.",
                )
            ]
        }


# =============================================================================
# Helpers
# =============================================================================


def configure_cli(
    monkeypatch: pytest.MonkeyPatch,
    inputs: list[str],
    thread_id: str = "test-thread",
):
    input_iterator = iter(inputs)

    monkeypatch.setattr(
        app,
        "parse_arguments",
        lambda: argparse.Namespace(
            thread=thread_id,
        ),
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(input_iterator),
    )


def install_runtime(
    monkeypatch: pytest.MonkeyPatch,
    graph: FakeGraph,
    checkpointer: FakeCheckpointer | None = None,
):
    if checkpointer is None:
        checkpointer = FakeCheckpointer()

    build_calls = []

    monkeypatch.setattr(
        app,
        "create_checkpointer",
        lambda: checkpointer,
    )

    def fake_build_graph(
        checkpointer,
    ):
        build_calls.append(checkpointer)

        return graph

    monkeypatch.setattr(
        app,
        "build_graph",
        fake_build_graph,
    )

    return checkpointer, build_calls


# =============================================================================
# Argument Parsing Tests
# =============================================================================


def test_parse_arguments_uses_default_thread_id(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "sys.argv",
        ["app.py"],
    )

    args = app.parse_arguments()

    assert args.thread == app.DEFAULT_THREAD_ID


def test_parse_arguments_accepts_custom_thread_id(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "sys.argv",
        [
            "app.py",
            "--thread",
            "project-alpha",
        ],
    )

    args = app.parse_arguments()

    assert args.thread == "project-alpha"


# =============================================================================
# Thread Validation Tests
# =============================================================================


def test_main_rejects_empty_thread_id(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        app,
        "parse_arguments",
        lambda: argparse.Namespace(
            thread="   ",
        ),
    )

    with pytest.raises(
        SystemExit,
        match="--thread must not be empty",
    ):
        app.main()


# =============================================================================
# Successful Execution Tests
# =============================================================================


def test_main_invokes_graph_with_thread_and_recursion_configuration(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    graph = FakeGraph(
        results=[
            {
                "messages": [
                    AIMessage(
                        content="Successful response.",
                    )
                ]
            }
        ]
    )

    checkpointer, build_calls = install_runtime(
        monkeypatch,
        graph,
    )

    configure_cli(
        monkeypatch,
        inputs=[
            "Hello",
            "exit",
        ],
        thread_id="project-alpha",
    )

    app.main()

    output = capsys.readouterr().out

    assert len(build_calls) == 1
    assert build_calls[0] is checkpointer

    assert len(graph.invoke_calls) == 1

    invocation = graph.invoke_calls[0]

    assert invocation["config"] == {
        "configurable": {
            "thread_id": "project-alpha",
        },
        "recursion_limit": app.RECURSION_LIMIT,
    }

    assert len(
        invocation["state"]["messages"]
    ) == 1

    assert (
        invocation["state"]["messages"][0].content
        == "Hello"
    )

    assert "Assistant: Successful response." in output

    assert checkpointer.conn.close_calls == 1


def test_main_ignores_empty_input_without_invoking_graph(
    monkeypatch: pytest.MonkeyPatch,
):
    graph = FakeGraph()

    checkpointer, _ = install_runtime(
        monkeypatch,
        graph,
    )

    configure_cli(
        monkeypatch,
        inputs=[
            "   ",
            "exit",
        ],
    )

    app.main()

    assert graph.invoke_calls == []
    assert checkpointer.conn.close_calls == 1


def test_main_stops_cleanly_on_eof(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    graph = FakeGraph()

    checkpointer, _ = install_runtime(
        monkeypatch,
        graph,
    )

    monkeypatch.setattr(
        app,
        "parse_arguments",
        lambda: argparse.Namespace(
            thread="eof-thread",
        ),
    )

    def raise_eof(_):
        raise EOFError

    monkeypatch.setattr(
        "builtins.input",
        raise_eof,
    )

    app.main()

    output = capsys.readouterr().out

    assert "File Assistant stopped." in output
    assert graph.invoke_calls == []
    assert checkpointer.conn.close_calls == 1


# =============================================================================
# Graph Failure Boundary Tests
# =============================================================================


def test_main_handles_graph_invocation_error_with_safe_message_and_continues(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    graph = FakeGraph(
        errors=[
            RuntimeError(
                "SECRET_PROVIDER_ERROR"
            ),
        ]
    )

    checkpointer, _ = install_runtime(
        monkeypatch,
        graph,
    )

    configure_cli(
        monkeypatch,
        inputs=[
            "Trigger failure",
            "exit",
        ],
        thread_id="failure-thread",
    )

    app.main()

    output = capsys.readouterr().out

    assert (
        f"Assistant: {app.SAFE_ASSISTANT_ERROR_MESSAGE}"
        in output
    )

    assert "SECRET_PROVIDER_ERROR" not in output

    assert len(graph.invoke_calls) == 1

    assert checkpointer.conn.close_calls == 1


def test_main_handles_graph_recursion_error_with_specific_message(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    graph = FakeGraph(
        errors=[
            GraphRecursionError(
                "SECRET_RECURSION_DETAILS"
            ),
        ]
    )

    checkpointer, _ = install_runtime(
        monkeypatch,
        graph,
    )

    configure_cli(
        monkeypatch,
        inputs=[
            "Trigger recursion",
            "exit",
        ],
        thread_id="recursion-thread",
    )

    app.main()

    output = capsys.readouterr().out

    assert (
        f"Assistant: {app.RECURSION_LIMIT_ERROR_MESSAGE}"
        in output
    )

    assert app.SAFE_ASSISTANT_ERROR_MESSAGE not in output

    assert "SECRET_RECURSION_DETAILS" not in output

    assert len(graph.invoke_calls) == 1

    assert checkpointer.conn.close_calls == 1


# =============================================================================
# Startup Failure Tests
# =============================================================================


def test_main_handles_checkpointer_initialization_failure_without_building_graph(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    build_calls = []

    configure_cli(
        monkeypatch,
        inputs=[],
        thread_id="storage-failure-thread",
    )

    def fail_create_checkpointer():
        raise RuntimeError(
            "SECRET_DATABASE_INITIALIZATION_ERROR"
        )

    def fake_build_graph(
        checkpointer,
    ):
        build_calls.append(checkpointer)

        raise AssertionError(
            "Graph must not be built."
        )

    monkeypatch.setattr(
        app,
        "create_checkpointer",
        fail_create_checkpointer,
    )

    monkeypatch.setattr(
        app,
        "build_graph",
        fake_build_graph,
    )

    app.main()

    output = capsys.readouterr().out

    assert (
        "Error: File Assistant could not initialize "
        "persistent storage."
        in output
    )

    assert (
        "SECRET_DATABASE_INITIALIZATION_ERROR"
        not in output
    )

    assert build_calls == []


# =============================================================================
# Runtime Failure Tests
# =============================================================================


def test_main_handles_unexpected_runtime_failure_and_closes_connection(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    checkpointer = FakeCheckpointer()

    configure_cli(
        monkeypatch,
        inputs=[],
        thread_id="runtime-failure-thread",
    )

    monkeypatch.setattr(
        app,
        "create_checkpointer",
        lambda: checkpointer,
    )

    def fail_build_graph(
        checkpointer,
    ):
        raise RuntimeError(
            "SECRET_RUNTIME_ERROR"
        )

    monkeypatch.setattr(
        app,
        "build_graph",
        fail_build_graph,
    )

    app.main()

    output = capsys.readouterr().out

    assert (
        "Error: File Assistant stopped because of "
        "an internal error."
        in output
    )

    assert "SECRET_RUNTIME_ERROR" not in output

    assert checkpointer.conn.close_calls == 1


# =============================================================================
# Cleanup Failure Tests
# =============================================================================


def test_main_handles_connection_cleanup_failure_without_exposing_details(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    graph = FakeGraph()

    checkpointer = FakeCheckpointer(
        close_error=RuntimeError(
            "SECRET_DATABASE_CLEANUP_ERROR"
        )
    )

    install_runtime(
        monkeypatch,
        graph,
        checkpointer=checkpointer,
    )

    configure_cli(
        monkeypatch,
        inputs=[
            "exit",
        ],
        thread_id="cleanup-failure-thread",
    )

    app.main()

    output = capsys.readouterr().out

    assert "File Assistant started." in output
    assert "File Assistant stopped." in output

    assert (
        "SECRET_DATABASE_CLEANUP_ERROR"
        not in output
    )

    assert checkpointer.conn.close_calls == 1
