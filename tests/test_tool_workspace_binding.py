from pathlib import Path
from types import SimpleNamespace

import pytest
from langchain_core.messages import ToolMessage

from core.workspace_context import (
    bind_workspace_root,
    get_active_workspace_root,
)
from graph.tool_observability import observe_tool_call


# =============================================================================
# Test Helpers
# =============================================================================


def create_tool_request(
    thread_id,
):
    """
    Create the minimum ToolCallRequest-like object required by the observable
    tool execution wrapper.
    """
    return SimpleNamespace(
        tool_call={
            "name": "test_tool",
            "args": {},
            "id": "test-tool-call",
            "type": "tool_call",
        },
        runtime=SimpleNamespace(
            config={
                "configurable": {
                    "thread_id": thread_id,
                }
            }
        ),
    )


def create_tool_message() -> ToolMessage:
    """Create a deterministic successful tool result."""
    return ToolMessage(
        content='{"ok": true}',
        tool_call_id="test-tool-call",
    )


# =============================================================================
# Thread Workspace Binding Tests
# =============================================================================


def test_observe_tool_call_binds_thread_workspace_during_execution(
    tmp_path: Path,
    monkeypatch,
):
    """
    Verify that tool execution runs with the workspace derived from the trusted
    LangGraph thread ID.
    """
    import graph.tool_observability as tool_observability


    # -------------------------------------------------------------------------
    # Test Data
    # -------------------------------------------------------------------------


    thread_id = "thread-alpha"

    expected_workspace = (
        tmp_path
        / "threads"
        / "derived-thread-workspace"
    ).resolve()


    # -------------------------------------------------------------------------
    # Workspace Derivation Replacement
    # -------------------------------------------------------------------------


    monkeypatch.setattr(
        tool_observability,
        "get_thread_workspace_root",
        lambda value: (
            expected_workspace
            if value == thread_id
            else None
        ),
    )


    # -------------------------------------------------------------------------
    # Tool Execution Probe
    # -------------------------------------------------------------------------


    observed_workspace = None

    def execute(request):
        nonlocal observed_workspace

        observed_workspace = (
            get_active_workspace_root()
        )

        return create_tool_message()


    # -------------------------------------------------------------------------
    # Wrapper Execution
    # -------------------------------------------------------------------------


    result = observe_tool_call(
        create_tool_request(thread_id),
        execute,
    )


    # -------------------------------------------------------------------------
    # Assertions
    # -------------------------------------------------------------------------


    assert result == create_tool_message()

    assert observed_workspace == expected_workspace

    assert get_active_workspace_root() is None


def test_observe_tool_call_restores_previous_workspace_after_execution(
    tmp_path: Path,
    monkeypatch,
):
    """
    Verify that leaving tool execution restores the workspace that was active
    before the thread-specific workspace binding.
    """
    import graph.tool_observability as tool_observability


    # -------------------------------------------------------------------------
    # Test Data
    # -------------------------------------------------------------------------


    previous_workspace = (
        tmp_path
        / "previous-workspace"
    ).resolve()

    thread_workspace = (
        tmp_path
        / "thread-workspace"
    ).resolve()


    # -------------------------------------------------------------------------
    # Workspace Derivation Replacement
    # -------------------------------------------------------------------------


    monkeypatch.setattr(
        tool_observability,
        "get_thread_workspace_root",
        lambda thread_id: thread_workspace,
    )


    # -------------------------------------------------------------------------
    # Tool Execution Probe
    # -------------------------------------------------------------------------


    observed_workspace = None

    def execute(request):
        nonlocal observed_workspace

        observed_workspace = (
            get_active_workspace_root()
        )

        return create_tool_message()


    # -------------------------------------------------------------------------
    # Wrapper Execution
    # -------------------------------------------------------------------------


    with bind_workspace_root(
        previous_workspace,
    ):
        observe_tool_call(
            create_tool_request("thread-alpha"),
            execute,
        )

        restored_workspace = (
            get_active_workspace_root()
        )


    # -------------------------------------------------------------------------
    # Assertions
    # -------------------------------------------------------------------------


    assert observed_workspace == thread_workspace

    assert restored_workspace == previous_workspace

    assert get_active_workspace_root() is None


def test_observe_tool_call_restores_workspace_when_tool_execution_raises(
    tmp_path: Path,
    monkeypatch,
):
    """
    Verify that the thread workspace binding is cleaned up even when the
    underlying tool execution raises unexpectedly.
    """
    import graph.tool_observability as tool_observability


    # -------------------------------------------------------------------------
    # Test Data
    # -------------------------------------------------------------------------


    thread_workspace = (
        tmp_path
        / "thread-workspace"
    ).resolve()


    # -------------------------------------------------------------------------
    # Workspace Derivation Replacement
    # -------------------------------------------------------------------------


    monkeypatch.setattr(
        tool_observability,
        "get_thread_workspace_root",
        lambda thread_id: thread_workspace,
    )


    # -------------------------------------------------------------------------
    # Failing Tool Execution
    # -------------------------------------------------------------------------


    def execute(request):
        assert (
            get_active_workspace_root()
            == thread_workspace
        )

        raise RuntimeError(
            "tool execution failed"
        )


    # -------------------------------------------------------------------------
    # Wrapper Execution
    # -------------------------------------------------------------------------


    with pytest.raises(
        RuntimeError,
        match="tool execution failed",
    ):
        observe_tool_call(
            create_tool_request("thread-alpha"),
            execute,
        )


    # -------------------------------------------------------------------------
    # Assertions
    # -------------------------------------------------------------------------


    assert get_active_workspace_root() is None


# =============================================================================
# Invalid Thread Configuration Tests
# =============================================================================


@pytest.mark.parametrize(
    "thread_id",
    [
        None,
        "",
        "   ",
        123,
    ],
)
def test_observe_tool_call_rejects_invalid_thread_id(
    thread_id,
):
    """
    Verify that filesystem tool execution cannot continue without a valid
    trusted LangGraph thread ID.
    """
    execute_called = False

    def execute(request):
        nonlocal execute_called

        execute_called = True

        return create_tool_message()

    with pytest.raises(
        RuntimeError,
        match="valid thread_id",
    ):
        observe_tool_call(
            create_tool_request(thread_id),
            execute,
        )

    assert execute_called is False
