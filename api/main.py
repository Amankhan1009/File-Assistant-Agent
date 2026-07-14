from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.errors import GraphRecursionError

from api.schemas import ChatRequest, ChatResponse

from core.logging import get_logger
from database.checkpointer import create_checkpointer
from graph.builder import build_graph


RECURSION_LIMIT = 20

logger = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize and clean up long-lived application resources.

    One SQLite checkpointer and one compiled LangGraph instance are created
    for the FastAPI application lifecycle and reused across requests.
    """
    logger.info("API startup initiated")

    checkpointer = create_checkpointer()

    graph = build_graph(
        checkpointer=checkpointer,
    )

    app.state.checkpointer = checkpointer
    app.state.graph = graph

    logger.info("API startup completed")

    try:
        yield

    finally:
        checkpointer.conn.close()
        logger.info("API shutdown completed")


app = FastAPI(
    title="File Assistant API",
    description=(
        "HTTP API for the secure, persistent LangGraph File Assistant."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Return API health status."""

    return {
        "status": "healthy",
    }


@app.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(
    payload: ChatRequest,
    request: Request,
) -> ChatResponse:
    """
    Execute one File Assistant interaction for a persistent conversation thread.
    """
    graph = request.app.state.graph

    logger.info(
        "API chat request started | thread_id=%s",
        payload.thread_id,
    )

    config = {
        "configurable": {
            "thread_id": payload.thread_id,
        },
        "recursion_limit": RECURSION_LIMIT,
    }

    try:
        completed_state = graph.invoke(
            {
                "messages": [
                    HumanMessage(
                        content=payload.message,
                    ),
                ],
            },
            config=config,
        )

    except GraphRecursionError as exc:
        logger.warning(
            "API chat request reached recursion limit | thread_id=%s",
            payload.thread_id,
        )

        raise HTTPException(
            status_code=422,
            detail=(
                "The assistant reached the maximum number of execution steps."
            ),
        ) from exc

    except Exception as exc:
        logger.exception(
            "API chat request failed | thread_id=%s",
            payload.thread_id,
        )

        raise HTTPException(
            status_code=500,
            detail="The assistant could not complete the request.",
        ) from exc

    messages = completed_state.get("messages", [])

    for message in reversed(messages):
        if (
            isinstance(message, AIMessage)
            and not message.tool_calls
            and isinstance(message.content, str)
            and message.content
        ):
            logger.info(
                "API chat request completed | thread_id=%s",
                payload.thread_id,
            )

            return ChatResponse(
                thread_id=payload.thread_id,
                response=message.content,
            )

    logger.error(
        "API chat request completed without final response | thread_id=%s",
        payload.thread_id,
    )

    raise HTTPException(
        status_code=500,
        detail="The assistant did not produce a final response.",
    )

