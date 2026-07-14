from uuid import uuid4

import streamlit as st

from frontend.api_client import (
    FileAssistantAPIError,
    check_api_health,
    send_chat_message,
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
# Session State
# =============================================================================


def create_thread_id() -> str:
    """Create a unique conversation thread identifier."""
    return f"web-{uuid4()}"


def initialize_session_state() -> None:
    """Initialize frontend conversation state."""
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = create_thread_id()

    if "messages" not in st.session_state:
        st.session_state.messages = []


def start_new_conversation() -> None:
    """Reset frontend chat history and start a new backend thread."""
    st.session_state.thread_id = create_thread_id()
    st.session_state.messages = []


initialize_session_state()


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
        start_new_conversation()
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
            "Built with LangGraph, FastAPI, Streamlit, Groq, and SQLite."
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
    user_message = st.session_state.pop("pending_prompt")


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