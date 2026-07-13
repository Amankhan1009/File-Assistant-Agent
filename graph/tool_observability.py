import json
from time import perf_counter
from typing import Any

from langchain_core.messages import ToolMessage
from langgraph.prebuilt import ToolNode

from core.logging import get_logger
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
# Tool Execution Observability Wrapper
# =============================================================================


def observe_tool_call(
    request: Any,
    execute: Any,
) -> ToolMessage:
    """
    Observe one synchronous ToolNode execution.

    Logs execution metadata without logging tool arguments, file contents,
    or complete tool results.
    """
    tool_call = request.tool_call

    tool_name = tool_call["name"]

    logger.info(
        "Tool execution started | tool_name=%s",
        tool_name,
    )

    start_time = perf_counter()

    try:
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

    duration_ms = (
        perf_counter()
        - start_time
    ) * 1000

    succeeded, error_type = (
        _inspect_tool_result(
            result,
        )
    )

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
    Create the native LangGraph ToolNode configured with application tools
    and tool-execution observability.
    """
    return ToolNode(
        get_tools(),
        wrap_tool_call=observe_tool_call,
    )