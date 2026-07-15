# =============================================================================
# Standard Library Imports
# =============================================================================


from datetime import datetime


# =============================================================================
# Third-Party Imports
# =============================================================================


from pydantic import BaseModel, Field


# =============================================================================
# Chat Request Schema
# =============================================================================


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

    owner_id: str = Field(
        ...,
        min_length=1,
        description=(
            "Anonymous owner identifier used for conversation discovery "
            "and ownership isolation."
        ),
    )


# =============================================================================
# Chat Response Schema
# =============================================================================


class ChatResponse(BaseModel):
    """Response payload returned after graph execution."""

    thread_id: str

    response: str


# =============================================================================
# Conversation Summary Schema
# =============================================================================


class ConversationSummary(BaseModel):
    """
    Serializable metadata describing one conversation shown in the frontend
    conversation list.
    """

    thread_id: str

    title: str

    created_at: datetime

    updated_at: datetime


# =============================================================================
# Conversation List Response Schema
# =============================================================================


class ConversationListResponse(BaseModel):
    """
    Response payload containing all conversations owned by one browser owner.
    """

    conversations: list[ConversationSummary]


# =============================================================================
# Health Response Schema
# =============================================================================


class HealthResponse(BaseModel):
    """Response payload returned by the API health endpoint."""

    status: str

# =============================================================================
# Workspace Schemas
# =============================================================================

from pydantic import BaseModel


class WorkspaceItem(BaseModel):
    """
    One file or directory in the workspace tree.
    """

    name: str
    relative_path: str
    is_directory: bool
    children: list["WorkspaceItem"] = []


class WorkspaceResponse(BaseModel):
    """
    Workspace tree returned to the frontend.
    """

    items: list[WorkspaceItem]


WorkspaceItem.model_rebuild()

# =============================================================================
# Preview Schemas
# =============================================================================


class FilePreviewResponse(BaseModel):
    """
    File preview returned to the frontend.
    """

    content: str