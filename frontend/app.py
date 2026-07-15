# =============================================================================
# Third-Party Imports
# =============================================================================


import streamlit as st
from textwrap import dedent

# =============================================================================
# Project Imports
# =============================================================================


from frontend.api_client import (
    FileAssistantAPIError,
    check_api_health,
    get_conversations,
    get_thread_messages,
    send_chat_message,
)
from frontend.conversation import (
    initialize_conversation_state,
    start_new_conversation,
)
from frontend.owner_identity import (
    resolve_owner_id,
)
from frontend.workspace import (
    list_workspace_items,
)
from frontend.workspace_ui import (
    render_workspace_tree,
)
from frontend.preview import (
    get_file_preview,
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
            border: 1px solid rgba(128,128,128,.35);
            border-radius: 999px;
            font-size: .82rem;
            margin-right: .35rem;
        }

        .example-heading {
            font-size: .9rem;
            font-weight: 600;
            opacity: .7;
            margin-top: 1.5rem;
            margin-bottom: .5rem;
        }

        [data-testid="stSidebar"] {
            border-right: 1px solid rgba(128,128,128,.20);
        }

        [data-testid="stChatMessage"] {
            border-radius: .75rem;
            padding: .3rem;
        }

    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# Owner Identity Initialization
# =============================================================================


resolve_owner_id(
    session_state=st.session_state,
    query_params=st.query_params,
)

# =============================================================================
# Persisted Conversation Loading
# =============================================================================


def load_persisted_conversation(
    thread_id: str,
) -> list[dict[str, str]]:
    """
    Load the persisted messages for one conversation thread.

    The API client owns HTTP communication and payload validation.
    """
    return get_thread_messages(
        thread_id=thread_id,
    )


# =============================================================================
# Conversation List Loading
# =============================================================================


def load_conversations() -> list[dict]:
    """
    Load every conversation owned by the current browser owner.

    If the backend cannot be reached, an empty list is returned so the
    application remains usable.
    """

    try:
        return get_conversations(
            owner_id=st.session_state.owner_id,
        )

    except FileAssistantAPIError:
        return []


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

    st.session_state.history_load_error = str(
        exc,
    )

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
# Recent Conversation Loading
# =============================================================================


if "conversations" not in st.session_state:

    st.session_state["conversations"] = (
        load_conversations()
    )


# =============================================================================
# New Conversation Handler
# =============================================================================


def handle_new_conversation() -> None:
    """
    Start a brand-new conversation.

    A new thread ID is generated while the owner identity remains unchanged,
    allowing all conversations created from this browser session to be grouped
    together.
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

    st.session_state["conversations"] = (
        load_conversations()
    )


# =============================================================================
# Conversation Switching
# =============================================================================


def switch_conversation(
    thread_id: str,
) -> None:
    """
    Switch to another conversation.

    Updating the URL thread parameter is enough because
    initialize_conversation_state() restores the persisted history on the next
    Streamlit rerun.
    """

    st.query_params["thread"] = thread_id

    st.rerun()


# =============================================================================
# Sidebar
# =============================================================================


with st.sidebar:
    st.title("📁 File Assistant")

    st.caption(
        "A secure agentic AI application for managing files "
        "with natural language."
    )


    # -------------------------------------------------------------------------
    # Backend Status
    # -------------------------------------------------------------------------


    if check_api_health():
        st.success(
            "Backend connected",
        )

    else:
        st.error(
            "Backend unavailable",
        )


    st.divider()


    # -------------------------------------------------------------------------
    # New Conversation
    # -------------------------------------------------------------------------


    if st.button(
        "＋ New conversation",
        use_container_width=True,
        type="primary",
    ):
        handle_new_conversation()

        st.rerun()


    # -------------------------------------------------------------------------
    # Recent Conversations
    # -------------------------------------------------------------------------


    st.subheader(
        "Recent conversations",
    )

    conversations = st.session_state.get(
        "conversations",
        [],
    )

    if not conversations:
        st.caption(
            "No conversations yet.",
        )

    else:
        for conversation in conversations:

            thread_id = conversation[
                "thread_id"
            ]

            title = conversation[
                "title"
            ]

            updated_at = conversation.get(
                "updated_at",
                "",
            )

            is_current = (
                thread_id
                ==
                st.session_state.thread_id
            )

            label = title

            if is_current:
                label = f"🟢 {title}"

            if st.button(
                label,
                key=f"conversation-{thread_id}",
                use_container_width=True,
            ):
                switch_conversation(
                    thread_id,
                )

            if updated_at:
                st.caption(
                    updated_at,
                )


    st.divider()


    # -------------------------------------------------------------------------
    # Workspace
    # -------------------------------------------------------------------------


    st.subheader(
        "Workspace",
    )

    workspace_items = list_workspace_items(
    st.session_state.thread_id,
    )

    if not workspace_items:

        st.caption(
            "No files yet.",
        )

    else:

        render_workspace_tree(
            workspace_items,
        )


    st.divider()


    # -------------------------------------------------------------------------
    # Capabilities
    # -------------------------------------------------------------------------


    st.subheader(
        "Capabilities",
    )



    # -------------------------------------------------------------------------
    # Capabilities
    # -------------------------------------------------------------------------


    st.subheader(
        "Capabilities",
    )

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


    # -------------------------------------------------------------------------
    # Technical Details
    # -------------------------------------------------------------------------


    with st.expander(
        "Technical details",
    ):

        st.caption(
            "Conversation thread",
        )

        st.code(
            st.session_state.thread_id,
            language=None,
        )

        st.caption(
            "Anonymous owner",
        )

        st.code(
            st.session_state.owner_id,
            language=None,
        )

        st.caption(
            "The conversation thread is stored in the page URL "
            "so the same persisted conversation can be reopened "
            "after refresh."
        )

        st.caption(
            "The anonymous owner identity groups conversations "
            "created from the current frontend session."
        )

        st.caption(
            "Built with LangGraph, FastAPI, Streamlit, "
            "Groq, SQLite, and PostgreSQL."
        )


# =============================================================================
# Main Interface
# =============================================================================


from textwrap import dedent

st.html(
    dedent(
        """
        <div class="hero-container">
            <div class="hero-title">
                File Assistant
            </div>

            <div class="hero-subtitle">
                Manage files and directories through a secure,
                persistent AI agent.
            </div>

            <span class="status-badge">LangGraph Agent</span>
            <span class="status-badge">Persistent Memory</span>
            <span class="status-badge">Secure Workspace</span>
        </div>
        """
    )
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
        "Describe a filesystem task below. The agent will reason "
        "about your request, select the required tools, execute "
        "them, and return the result."
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

            st.session_state.pending_prompt = (
                example_prompt
            )

            st.rerun()


# =============================================================================
# Conversation History
# =============================================================================


for message in st.session_state.messages:

    with st.chat_message(
        message["role"],
    ):

        st.markdown(
            message["content"],
        )

# =============================================================================
# Selected File Preview
# =============================================================================


selected_file = st.session_state.get(
    "selected_file",
)

if selected_file is not None:

    st.divider()

    st.subheader(
        f"📄 {selected_file['name']}",
    )

    preview = get_file_preview(
        selected_file["path"],
    )

    st.code(
        preview,
        language=None,
    )
    
# =============================================================================
# Conversation Statistics
# =============================================================================


if st.session_state.messages:

    user_messages = sum(
        1
        for message in st.session_state.messages
        if message["role"] == "user"
    )

    assistant_messages = sum(
        1
        for message in st.session_state.messages
        if message["role"] == "assistant"
    )

    with st.expander(
        "Conversation statistics",
    ):

        st.caption(
            f"User messages: {user_messages}"
        )

        st.caption(
            f"Assistant messages: {assistant_messages}"
        )

        st.caption(
            f"Total messages: {len(st.session_state.messages)}"
        )


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

    # -------------------------------------------------------------------------
    # Store User Message
    # -------------------------------------------------------------------------


    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_message,
        }
    )


    # -------------------------------------------------------------------------
    # Render User Message
    # -------------------------------------------------------------------------


    with st.chat_message(
        "user",
    ):
        st.markdown(
            user_message,
        )


    # -------------------------------------------------------------------------
    # Execute Agent
    # -------------------------------------------------------------------------


    with st.chat_message(
        "assistant",
    ):

        with st.spinner(
            "Executing agent workflow...",
        ):

            try:

                assistant_response = send_chat_message(
                    message=user_message,
                    thread_id=st.session_state.thread_id,
                    owner_id=st.session_state.owner_id,
                )

            except FileAssistantAPIError as exc:

                st.error(
                    str(exc),
                )

            else:

                st.markdown(
                    assistant_response,
                )


                # -------------------------------------------------------------
                # Persist Assistant Message
                # -------------------------------------------------------------


                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": assistant_response,
                    }
                )
            
                # -------------------------------------------------------------
                # Refresh Conversation List
                # -------------------------------------------------------------

                st.session_state["conversations"] = (
                    load_conversations()
                )

                # -------------------------------------------------------------
                # Refresh UI
                # -------------------------------------------------------------

                st.rerun()

