# =============================================================================
# Standard Library Imports
# =============================================================================


from contextlib import asynccontextmanager


# =============================================================================
# Third-Party Imports
# =============================================================================


from fastapi import FastAPI


# =============================================================================
# Project Imports
# =============================================================================


from api.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationSummary,
    ConversationListResponse,
    HealthResponse,
)
from database.checkpointer import database_runtime
from database.conversations import PostgresConversationRepository
from graph.builder import build_graph


# =============================================================================
# Application Lifespan
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize shared application resources during startup and clean them up
    during shutdown.

    The database runtime owns database-specific resources.

    LangGraph checkpoint persistence stores agent state and message history.

    PostgreSQL conversation metadata persistence uses the same application-owned
    connection pool for conversation discovery and sidebar presentation.

    The compiled LangGraph instance and conversation repository are shared
    across API requests.
    """
    with database_runtime() as runtime:
        graph = build_graph(
            checkpointer=runtime.checkpointer,
        )


        # ---------------------------------------------------------------------
        # Conversation Repository Initialization
        # ---------------------------------------------------------------------


        if runtime.pool is None:
            conversation_repository = None

        else:
            conversation_repository = PostgresConversationRepository(
                pool=runtime.pool,
            )

            conversation_repository.setup()


        # ---------------------------------------------------------------------
        # Shared Application State
        # ---------------------------------------------------------------------


        app.state.checkpointer = runtime.checkpointer

        app.state.graph = graph

        app.state.conversation_repository = conversation_repository


        # ---------------------------------------------------------------------
        # Application Runtime
        # ---------------------------------------------------------------------


        yield


# =============================================================================
# FastAPI Application
# =============================================================================


app = FastAPI(
    title="File Assistant API",
    description=(
        "HTTP API for the secure, persistent LangGraph File Assistant."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# =============================================================================
# Health Endpoint
# =============================================================================


@app.get(
    "/health",
    response_model=HealthResponse,
)
def health() -> HealthResponse:
    """Return the API health status."""
    return HealthResponse(
        status="healthy",
    )


# =============================================================================
# Chat Endpoint
# =============================================================================


@app.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(
    request: ChatRequest,
) -> ChatResponse:
    """
    Execute one File Assistant interaction using a persistent LangGraph thread.

    PostgreSQL deployments also register conversation metadata for discovery
    and sidebar presentation.
    """
    graph = app.state.graph

    conversation_repository = (
        app.state.conversation_repository
    )


    # -------------------------------------------------------------------------
    # Conversation Metadata Registration
    # -------------------------------------------------------------------------


    if conversation_repository is not None:
        conversation_repository.ensure_conversation(
            thread_id=request.thread_id,
            owner_id=request.owner_id,
            title=request.message,
        )


    # -------------------------------------------------------------------------
    # Graph Execution
    # -------------------------------------------------------------------------


    result = graph.invoke(
        {
            "messages": [
                (
                    "user",
                    request.message,
                )
            ]
        },
        config={
            "configurable": {
                "thread_id": request.thread_id,
            }
        },
    )

    assistant_message = result["messages"][-1]


    # -------------------------------------------------------------------------
    # Conversation Activity Update
    # -------------------------------------------------------------------------


    if conversation_repository is not None:
        conversation_repository.touch_conversation(
            thread_id=request.thread_id,
            owner_id=request.owner_id,
        )


    # -------------------------------------------------------------------------
    # Chat Response
    # -------------------------------------------------------------------------


    return ChatResponse(
        response=assistant_message.content,
        thread_id=request.thread_id,
    )


# =============================================================================
# Conversation Listing Endpoint
# =============================================================================


@app.get(
    "/conversations",
    response_model=ConversationListResponse,
)
def list_conversations(
    owner_id: str,
) -> ConversationListResponse:
    """
    Return conversation metadata owned by the requested anonymous owner.

    PostgreSQL deployments persist application-owned conversation metadata.

    Local SQLite deployments currently do not expose a conversation metadata
    repository and therefore return an empty conversation list.
    """
    conversation_repository = (
        app.state.conversation_repository
    )


    # -------------------------------------------------------------------------
    # Missing Conversation Repository
    # -------------------------------------------------------------------------


    if conversation_repository is None:
        return ConversationListResponse(
            conversations=[],
        )


    # -------------------------------------------------------------------------
    # Conversation Metadata Retrieval
    # -------------------------------------------------------------------------


    conversation_records = (
        conversation_repository.list_conversations(
            owner_id=owner_id,
        )
    )


    # -------------------------------------------------------------------------
    # Conversation Response Serialization
    # -------------------------------------------------------------------------


    conversations = [
        ConversationSummary(
            thread_id=record.thread_id,
            title=record.title,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        for record in conversation_records
    ]


    # -------------------------------------------------------------------------
    # Conversation List Response
    # -------------------------------------------------------------------------


    return ConversationListResponse(
        conversations=conversations,
    )


# =============================================================================
# Thread Message History Endpoint
# =============================================================================


@app.get(
    "/threads/{thread_id}/messages",
)
def get_thread_messages(
    thread_id: str,
) -> dict:
    """
    Return persisted conversation messages from the latest LangGraph checkpoint
    for the requested thread.

    A missing thread returns an empty message list.
    """
    checkpointer = app.state.checkpointer


    # -------------------------------------------------------------------------
    # Checkpoint Retrieval Configuration
    # -------------------------------------------------------------------------


    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }


    # -------------------------------------------------------------------------
    # Latest Checkpoint Retrieval
    # -------------------------------------------------------------------------


    checkpoint = checkpointer.get(
        config,
    )


    # -------------------------------------------------------------------------
    # Missing Thread Response
    # -------------------------------------------------------------------------


    if checkpoint is None:
        return {
            "thread_id": thread_id,
            "messages": [],
        }


    # -------------------------------------------------------------------------
    # Persisted Message Extraction
    # -------------------------------------------------------------------------


    persisted_messages = checkpoint.get(
        "channel_values",
        {},
    ).get(
        "messages",
        [],
    )


    # -------------------------------------------------------------------------
    # Frontend Message Serialization
    # -------------------------------------------------------------------------


    messages = []

    for message in persisted_messages:
        if message.type == "human":
            role = "user"

        elif message.type == "ai":
            role = "assistant"

        else:
            continue

        messages.append(
            {
                "role": role,
                "content": message.content,
            }
        )


    # -------------------------------------------------------------------------
    # Thread History Response
    # -------------------------------------------------------------------------


    return {
        "thread_id": thread_id,
        "messages": messages,
    }