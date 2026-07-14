import streamlit as st

from frontend.api_client import (
    FileAssistantAPIError,
    check_api_health,
    get_thread_messages,
    send_chat_message,
)
from frontend.conversation import (
    initialize_conversation_state,
    start_new_conversation,
)


# =============================================================================
# Page Configuration
# =============================================================================


st.set_page_config(
    page_title="File Assistant",
    page_icon="📁",
    layout="centered",
    initial_sidebar_state="expanded",
)


# =============================================================================
# Custom Styling
# =============================================================================


st.markdown(
    """
    <style>
        .block-container {
            max-width: 900px;
            padding-top: 2rem;
            padding-bottom: 6rem;
        }

        .hero-container {
            padding: 1.5rem 0 1rem 0;
        }

        .hero-title {
            font-size: 2.6rem;
            font-weight: 700;
            margin-bottom: 0.35rem;
        }

        .hero-subtitle {
            font-size: 1.05rem;
            opacity: 0.75;
            margin-bottom: 1rem;
        }

        .status-badge {
            display: inline-block;
            padding: 0.3rem 0.7rem;
            border: 1px solid rgba(128, 128, 128, 0.35);
            border-radius: 999px;
            font-size: 0.82rem;
            margin-right: 0.35rem;
        }

        .example-heading {
            font-size: 0.9rem;
            font-weight: 600;
            opacity: 0.7;
            margin-top: 1.5rem;
            margin-bottom: 0.5rem;
        }

        [data-testid="stSidebar"] {
            border-right: 1px solid rgba(128, 128, 128, 0.2);
        }

        [data-testid="stChatMessage"] {
            border-radius: 0.75rem;
            padding: 0.3rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# Persisted Conversation Loading
# =============================================================================


def load_persisted_conversation(
    thread_id: str,
) -> list[dict[str, str]]:
    """
    Load persisted messages for the requested conversation thread.

    The API client owns HTTP communication and payload validation.
    """
    return get_thread_messages(
        thread_id=thread_id,
    )


# =============================================================================
# Conversation State Initialization
# =============================================================================


try:
    initialize_conversation_state(
        session_state=st.session_state,
        query_params=st.query_params,
        load_thread_messages=load_persisted_conversation,
    )

except FileAssistantAPIError as exc:
    st.session_state.history_load_error = str(exc)

    if "thread_id" not in st.session_state:
        st.session_state.thread_id = st.query_params.get(
            "thread",
            "",
        )

    if "messages" not in st.session_state:
        st.session_state.messages = []

else:
    st.session_state.pop(
        "history_load_error",
        None,
    )


# =============================================================================
# New Conversation Handler
# =============================================================================


def handle_new_conversation() -> None:
    """
    Start a new URL-backed conversation and clear transient frontend state.
    """
    start_new_conversation(
        session_state=st.session_state,
        query_params=st.query_params,
    )

    st.session_state.pop(
        "history_load_error",
        None,
    )

    st.session_state.pop(
        "pending_prompt",
        None,
    )


# =============================================================================
# Sidebar
# =============================================================================


with st.sidebar:
    st.title("📁 File Assistant")

    st.caption(
        "A secure agentic AI application for managing files "
        "with natural language."
    )

    if check_api_health():
        st.success("Backend connected")
    else:
        st.error("Backend unavailable")

    st.divider()

    if st.button(
        "＋ New conversation",
        use_container_width=True,
        type="primary",
    ):
        handle_new_conversation()
        st.rerun()

    st.subheader("Capabilities")

    st.markdown(
        """
        - Create and edit files
        - Read file contents
        - Search files and directories
        - Move and rename paths
        - Create and extract archives
        - Maintain conversation context
        """
    )

    st.divider()

    with st.expander("Technical details"):
        st.caption("Conversation thread")

        st.code(
            st.session_state.thread_id,
            language=None,
        )

        st.caption(
            "The conversation thread is stored in the page URL so the same "
            "persisted conversation can be reopened after refresh."
        )

        st.caption(
            "Built with LangGraph, FastAPI, Streamlit, Groq, "
            "SQLite, and PostgreSQL."
        )


# =============================================================================
# Main Interface
# =============================================================================


st.markdown(
    """
    <div class="hero-container">
        <div class="hero-title">File Assistant</div>
        <div class="hero-subtitle">
            Manage files and directories through a secure,
            persistent AI agent.
        </div>
        <span class="status-badge">LangGraph Agent</span>
        <span class="status-badge">Persistent Memory</span>
        <span class="status-badge">Secure Workspace</span>
    </div>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# Conversation History Loading Error
# =============================================================================


if "history_load_error" in st.session_state:
    st.warning(
        "The conversation history could not be restored. "
        f"{st.session_state.history_load_error}"
    )


# =============================================================================
# Empty Conversation State
# =============================================================================


if not st.session_state.messages:
    st.info(
        "Describe a filesystem task below. The agent will reason about "
        "your request, select the required tools, execute them, and return "
        "the result."
    )

    st.markdown(
        '<div class="example-heading">TRY AN EXAMPLE</div>',
        unsafe_allow_html=True,
    )

    example_prompts = (
        "Create a file called notes.txt containing: Learn LangGraph.",
        "List the files and directories in the workspace.",
        "Search for files with summary in their name.",
        "Create an archive of the reports directory.",
    )

    for example_prompt in example_prompts:
        if st.button(
            example_prompt,
            use_container_width=True,
        ):
            st.session_state.pending_prompt = example_prompt
            st.rerun()


# =============================================================================
# Conversation History
# =============================================================================


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# =============================================================================
# Chat Input
# =============================================================================


user_message = st.chat_input(
    "Ask the File Assistant to perform a filesystem task..."
)


if "pending_prompt" in st.session_state:
    user_message = st.session_state.pop(
        "pending_prompt",
    )


# =============================================================================
# Chat Interaction
# =============================================================================


if user_message:
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_message,
        }
    )

    with st.chat_message("user"):
        st.markdown(user_message)

    with st.chat_message("assistant"):
        with st.spinner("Executing agent workflow..."):
            try:
                assistant_response = send_chat_message(
                    message=user_message,
                    thread_id=st.session_state.thread_id,
                )

            except FileAssistantAPIError as exc:
                st.error(str(exc))

            else:
                st.markdown(assistant_response)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": assistant_response,
                    }
                )