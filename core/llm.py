from functools import lru_cache

from langchain_groq import ChatGroq

from core.config import GROQ_MODEL
from tools.registry import get_tools


# =============================================================================
# Base LLM Factory
# =============================================================================


def create_llm() -> ChatGroq:
    """Create the base Groq chat model."""

    return ChatGroq(
        model=GROQ_MODEL,
        temperature=0,
    )


# =============================================================================
# Tool-Bound Agent Model
# =============================================================================


@lru_cache(maxsize=1)
def get_agent_model():
    """Create and cache the Groq model with registered tools bound to it."""

    return create_llm().bind_tools(get_tools())