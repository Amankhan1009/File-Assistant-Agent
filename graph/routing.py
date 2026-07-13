from typing import Literal

from langchain_core.messages import AIMessage

from core.logging import get_logger
from graph.state import AgentState


logger = get_logger(__name__)


def route_after_agent(
    state: AgentState,
) -> Literal["tools", "__end__"]:
    """
    Route graph execution after the agent node.

    If the latest AIMessage contains tool calls, execution continues to the
    tools node. Otherwise, the graph terminates.
    """
    messages = state["messages"]

    if not messages:
        logger.error(
            "Routing failed because message history is empty."
        )

        raise ValueError(
            "Cannot route an empty message history."
        )

    last_message = messages[-1]

    if not isinstance(last_message, AIMessage):
        logger.error(
            "Routing failed because latest message type is invalid | message_type=%s",
            type(last_message).__name__,
        )

        raise TypeError(
            "Expected the latest message to be an AIMessage after agent execution."
        )

    if last_message.tool_calls:
        logger.info(
            "Routing agent execution to tools | tool_call_count=%d | tool_names=%s",
            len(last_message.tool_calls),
            [
                tool_call["name"]
                for tool_call in last_message.tool_calls
            ],
        )

        return "tools"

    logger.info(
        "Routing agent execution to graph end."
    )

    return "__end__"