from uuid import uuid4


# =============================================================================
# Conversation Configuration
# =============================================================================


THREAD_QUERY_PARAMETER = "thread"

THREAD_ID_PREFIX = "web"


# =============================================================================
# Thread ID Creation
# =============================================================================


def create_thread_id() -> str:
    """
    Create a unique thread ID for a frontend conversation.

    The generated thread ID is safe to expose in the browser URL and is used
    by LangGraph to identify persisted conversation state.
    """
    return (
        f"{THREAD_ID_PREFIX}-"
        f"{uuid4().hex}"
    )


# =============================================================================
# Thread ID Resolution
# =============================================================================


def resolve_thread_id(
    query_params,
) -> str:
    """
    Resolve the active conversation thread ID from URL query parameters.

    If the URL already contains a valid thread ID, return it unchanged.

    Otherwise, create a new thread ID, store it in the URL query parameters,
    and return the generated ID.
    """
    thread_id = query_params.get(
        THREAD_QUERY_PARAMETER,
    )

    if (
        isinstance(thread_id, str)
        and thread_id.strip()
    ):
        return thread_id.strip()

    thread_id = create_thread_id()

    query_params[
        THREAD_QUERY_PARAMETER
    ] = thread_id

    return thread_id


# =============================================================================
# Conversation Session Initialization
# =============================================================================


def initialize_conversation_state(
    session_state,
    query_params,
    load_thread_messages,
) -> str:
    """
    Initialize frontend conversation state for the active URL thread.

    The URL query parameter is the source of conversation identity.

    If the active thread changes, persisted message history is loaded from the
    backend and copied into frontend session state.

    Returns the active thread ID.
    """
    thread_id = resolve_thread_id(
        query_params=query_params,
    )

    current_thread_id = session_state.get(
        "thread_id",
    )

    if current_thread_id == thread_id:
        return thread_id

    messages = load_thread_messages(
        thread_id=thread_id,
    )

    session_state["thread_id"] = thread_id

    session_state["messages"] = messages

    return thread_id


# =============================================================================
# New Conversation Creation
# =============================================================================


def start_new_conversation(
    session_state,
    query_params,
) -> str:
    """
    Start a new frontend conversation.

    A new thread ID is generated and written to the URL.

    Frontend message history is cleared so the next interaction starts with a
    fresh LangGraph conversation.
    """
    thread_id = create_thread_id()

    query_params[
        THREAD_QUERY_PARAMETER
    ] = thread_id

    session_state["thread_id"] = thread_id

    session_state["messages"] = []

    return thread_id