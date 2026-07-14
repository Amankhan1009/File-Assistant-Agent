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
