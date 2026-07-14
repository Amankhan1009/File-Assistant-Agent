from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request payload for one File Assistant interaction."""

    message: str = Field(
        ...,
        min_length=1,
        description="Natural-language request sent to the File Assistant.",
    )

    thread_id: str = Field(
        ...,
        min_length=1,
        description="Conversation thread identifier used for persistent state.",
    )


class ChatResponse(BaseModel):
    """Response payload returned after graph execution."""

    thread_id: str

    response: str
