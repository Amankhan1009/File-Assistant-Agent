from typing import Annotated

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """
    State shared across the File Assistant graph.

    The messages field stores the complete conversation and tool-execution
    history for the current graph execution.
    """

    messages: Annotated[list[BaseMessage], add_messages]