import json
from time import perf_counter
from typing import Any

from langchain_core.messages import ToolMessage
from langgraph.prebuilt import ToolNode

from core.logging import get_logger
from core.paths import get_thread_workspace_root
from core.workspace_context import bind_workspace_root
from tools.registry import get_tools


logger = get_logger("graph.tools")


# =============================================================================
# Tool Result Inspection
# =============================================================================


def _inspect_tool_result(
    message: ToolMessage,
) -> tuple[bool, str | None]:
    """
    Inspect a ToolMessage result without logging its full content.

    Returns:
        A tuple containing:

        - Whether the tool execution succeeded.
        - The structured error type when available.
    """
    try:
        result = json.loads(
            message.content,
        )

    except (
        TypeError,
        json.JSONDecodeError,
    ):
        return True, None

    if not isinstance(
        result,
        dict,
    ):
        return True, None

    if result.get("ok") is not False:
        return True, None

    error = result.get("error")

    if not isinstance(
        error,
        dict,
    ):
        return False, None

    error_type = error.get("type")

    if not isinstance(
        error_type,
        str,
    ):
        return False, None

    return False, error_type


# =============================================================================
# Trusted Thread Identity Extraction
# =============================================================================


def _get_request_thread_id(
    request: Any,
) -> str:
    """
    Extract and validate the trusted LangGraph thread ID from the tool runtime.

    The thread ID originates from the graph invocation configuration and is
    used to derive the isolated filesystem workspace for tool execution.
    """
    runtime = getattr(
        request,
        "runtime",
        None,
    )

    config = getattr(
        runtime,
        "config",
        None,
    )

    if not isinstance(
        config,
        dict,
    ):
        raise RuntimeError(
            "Tool execution requires a valid thread_id."
        )

    configurable = config.get(
        "configurable",
    )

    if not isinstance(
        configurable,
        dict,
    ):
        raise RuntimeError(
            "Tool execution requires a valid thread_id."
        )

    thread_id = configurable.get(
        "thread_id",
    )

    if (
        not isinstance(thread_id, str)
        or not thread_id.strip()
    ):
        raise RuntimeError(
            "Tool execution requires a valid thread_id."
        )

    return thread_id.strip()


# =============================================================================
# Thread Workspace Resolution
# =============================================================================


def _get_request_workspace_root(
    request: Any,
):
    """
    Resolve the isolated filesystem workspace for one tool execution request.
    """
    thread_id = _get_request_thread_id(
        request,
    )

    return get_thread_workspace_root(
        thread_id,
    )


# =============================================================================
# Tool Execution Observability Wrapper
# =============================================================================


def observe_tool_call(
    request: Any,
    execute: Any,
) -> ToolMessage:
    """
    Execute one synchronous ToolNode request inside its isolated thread
    workspace while recording safe tool execution metadata.

    The wrapper:

    1. Validates the trusted LangGraph thread ID.
    2. Resolves the thread-specific workspace.
    3. Binds that workspace for filesystem path resolution.
    4. Executes the native ToolNode operation.
    5. Restores the previous workspace context automatically.
    6. Logs execution metadata without exposing arguments or file contents.
    """
    tool_call = request.tool_call

    tool_name = tool_call["name"]


    # -------------------------------------------------------------------------
    # Resolve Trusted Thread Workspace
    # -------------------------------------------------------------------------


    workspace_root = _get_request_workspace_root(
        request,
    )


    # -------------------------------------------------------------------------
    # Tool Execution Start
    # -------------------------------------------------------------------------


    logger.info(
        "Tool execution started | tool_name=%s",
        tool_name,
    )

    start_time = perf_counter()


    # -------------------------------------------------------------------------
    # Isolated Tool Execution
    # -------------------------------------------------------------------------


    try:
        with bind_workspace_root(
            workspace_root,
        ):
            result = execute(
                request,
            )

    except Exception:
        duration_ms = (
            perf_counter()
            - start_time
        ) * 1000

        logger.exception(
            "Tool execution failed unexpectedly | "
            "tool_name=%s | "
            "duration_ms=%.2f",
            tool_name,
            duration_ms,
        )

        raise


    # -------------------------------------------------------------------------
    # Tool Result Inspection
    # -------------------------------------------------------------------------


    duration_ms = (
        perf_counter()
        - start_time
    ) * 1000

    succeeded, error_type = (
        _inspect_tool_result(
            result,
        )
    )


    # -------------------------------------------------------------------------
    # Tool Execution Completion
    # -------------------------------------------------------------------------


    logger.info(
        "Tool execution completed | "
        "tool_name=%s | "
        "success=%s | "
        "error_type=%s | "
        "duration_ms=%.2f",
        tool_name,
        succeeded,
        error_type,
        duration_ms,
    )

    return result


# =============================================================================
# Observable ToolNode Factory
# =============================================================================


def create_observable_tool_node() -> ToolNode:
    """
    Create the native LangGraph ToolNode configured with application tools,
    thread-isolated workspace execution, and safe tool observability.
    """
    return ToolNode(
        get_tools(),
        wrap_tool_call=observe_tool_call,
    )