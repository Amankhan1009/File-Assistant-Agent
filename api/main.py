from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
)
from database.checkpointer import checkpointer_runtime
from graph.builder import build_graph


# =============================================================================
# Application Lifespan
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize shared application resources during startup and clean them up
    during shutdown.

    The configured checkpointer backend owns its database-specific lifecycle.
    The compiled LangGraph instance is shared across API requests.
    """
    with checkpointer_runtime() as checkpointer:
        graph = build_graph(
            checkpointer=checkpointer,
        )

        app.state.checkpointer = checkpointer
        app.state.graph = graph

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
    """
    graph = app.state.graph

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

    return ChatResponse(
        response=assistant_message.content,
        thread_id=request.thread_id,
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


    checkpoint = checkpointer.get(config)


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