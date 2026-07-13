from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
)

from core.llm import get_agent_model
from core.logging import get_logger
from core.prompts import SYSTEM_PROMPT
from graph.state import AgentState


MAX_CONTEXT_TURNS = 10

logger = get_logger(__name__)


def get_recent_context(
    messages: list[BaseMessage],
    max_turns: int = MAX_CONTEXT_TURNS,
) -> list[BaseMessage]:
    """
    Return the most recent complete conversation turns for model context.

    The original message list is never modified.
    """
    if max_turns <= 0:
        return []

    turn_start_indexes = [
        index
        for index, message in enumerate(messages)
        if isinstance(message, HumanMessage)
    ]

    if len(turn_start_indexes) <= max_turns:
        return messages.copy()

    first_retained_turn_index = turn_start_indexes[-max_turns]

    return messages[first_retained_turn_index:].copy()


def agent_node(state: AgentState) -> dict[str, list]:
    """
    Invoke the tool-calling model with bounded recent conversation context.
    """
    persisted_message_count = len(state["messages"])

    recent_messages = get_recent_context(
        state["messages"],
    )

    logger.info(
        "Agent invocation started | persisted_messages=%d | context_messages=%d",
        persisted_message_count,
        len(recent_messages),
    )

    model = get_agent_model()

    model_messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *recent_messages,
    ]

    try:
        response = model.invoke(model_messages)

    except Exception:
        logger.exception(
            "Agent model invocation failed | persisted_messages=%d | context_messages=%d",
            persisted_message_count,
            len(recent_messages),
        )
        raise

    logger.info(
        "Agent invocation completed | tool_calls=%d | response_content_length=%d",
        len(response.tool_calls),
        len(response.content),
    )

    return {
        "messages": [response],
    }