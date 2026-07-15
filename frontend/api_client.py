# =============================================================================
# Standard Library Imports
# =============================================================================


import os


# =============================================================================
# Third-Party Imports
# =============================================================================


import httpx


# =============================================================================
# API Configuration
# =============================================================================


DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"

API_BASE_URL = os.getenv(
    "FILE_ASSISTANT_API_URL",
    DEFAULT_API_BASE_URL,
).rstrip("/")

CHAT_TIMEOUT_SECONDS = 120.0

HEALTH_TIMEOUT_SECONDS = 5.0

HISTORY_TIMEOUT_SECONDS = 10.0

CONVERSATIONS_TIMEOUT_SECONDS = 10.0


# =============================================================================
# API Exceptions
# =============================================================================


class FileAssistantAPIError(RuntimeError):
    """Raised when communication with the File Assistant API fails."""


# =============================================================================
# Health Client
# =============================================================================


def check_api_health() -> bool:
    """
    Return whether the File Assistant API is reachable and healthy.

    The health check never raises frontend-facing exceptions.

    Unreachable APIs, unsuccessful responses, invalid JSON, or unexpected
    payloads are treated as an unhealthy backend.
    """
    try:
        response = httpx.get(
            f"{API_BASE_URL}/health",
            timeout=HEALTH_TIMEOUT_SECONDS,
        )

        response.raise_for_status()

        payload = response.json()

    except (
        httpx.RequestError,
        httpx.HTTPStatusError,
        ValueError,
    ):
        return False

    return payload.get(
        "status",
    ) == "healthy"


# =============================================================================
# Chat Client
# =============================================================================


def send_chat_message(
    message: str,
    thread_id: str,
    owner_id: str,
) -> str:
    """
    Send one chat interaction to the File Assistant API.

    The thread ID identifies the persistent LangGraph conversation.

    The owner ID identifies the anonymous browser owner used for conversation
    discovery and ownership isolation.

    Returns the assistant response text.

    Raises:
        FileAssistantAPIError:
            If the API cannot be reached, returns an unsuccessful response,
            returns invalid JSON, or returns an invalid response payload.
    """

    try:
        response = httpx.post(
            f"{API_BASE_URL}/chat",
            json={
                "message": message,
                "thread_id": thread_id,
                "owner_id": owner_id,
            },
            timeout=CHAT_TIMEOUT_SECONDS,
        )

        response.raise_for_status()

    except httpx.TimeoutException as exc:
        raise FileAssistantAPIError(
            "The File Assistant API request timed out."
        ) from exc

    except httpx.HTTPStatusError as exc:
        raise FileAssistantAPIError(
            f"The File Assistant API returned HTTP "
            f"{exc.response.status_code}."
        ) from exc

    except httpx.RequestError as exc:
        raise FileAssistantAPIError(
            "Could not connect to the File Assistant API."
        ) from exc

    try:
        payload = response.json()

    except ValueError as exc:
        raise FileAssistantAPIError(
            "The File Assistant API returned invalid JSON."
        ) from exc

    assistant_response = payload.get(
        "response",
    )

    if (
        not isinstance(
            assistant_response,
            str,
        )
        or not assistant_response.strip()
    ):
        raise FileAssistantAPIError(
            "The File Assistant API returned an invalid response payload."
        )

    return assistant_response


# =============================================================================
# Thread Message History Client
# =============================================================================


def get_thread_messages(
    thread_id: str,
) -> list[dict[str, str]]:
    """
    Retrieve persisted conversation messages for a File Assistant thread.

    Returns validated frontend-safe user and assistant messages.

    Raises:
        FileAssistantAPIError:
            If the API cannot be reached, returns an unsuccessful response,
            returns invalid JSON, or returns an invalid message history
            payload.
    """

    try:
        response = httpx.get(
            f"{API_BASE_URL}/threads/{thread_id}/messages",
            timeout=HISTORY_TIMEOUT_SECONDS,
        )

        response.raise_for_status()

    except httpx.TimeoutException as exc:
        raise FileAssistantAPIError(
            "The File Assistant message history request timed out."
        ) from exc

    except httpx.HTTPStatusError as exc:
        raise FileAssistantAPIError(
            f"The File Assistant API returned HTTP "
            f"{exc.response.status_code} while loading message history."
        ) from exc

    except httpx.RequestError as exc:
        raise FileAssistantAPIError(
            "Could not connect to the File Assistant API while loading "
            "message history."
        ) from exc

    try:
        payload = response.json()

    except ValueError as exc:
        raise FileAssistantAPIError(
            "The File Assistant API returned invalid JSON while loading "
            "message history."
        ) from exc

    messages = payload.get(
        "messages",
    )

    if not isinstance(
        messages,
        list,
    ):
        raise FileAssistantAPIError(
            "The File Assistant API returned an invalid message history "
            "payload."
        )

    validated_messages = []

    for message in messages:
        if not isinstance(
            message,
            dict,
        ):
            raise FileAssistantAPIError(
                "The File Assistant API returned an invalid message history "
                "payload."
            )

        role = message.get(
            "role",
        )

        content = message.get(
            "content",
        )

        if (
            role not in {
                "user",
                "assistant",
            }
            or not isinstance(
                content,
                str,
            )
        ):
            raise FileAssistantAPIError(
                "The File Assistant API returned an invalid message history "
                "payload."
            )

        validated_messages.append(
            {
                "role": role,
                "content": content,
            }
        )

    return validated_messages


# =============================================================================
# Conversation List Client
# =============================================================================


def get_conversations(
    owner_id: str,
) -> list[dict]:
    """
    Retrieve all conversations owned by the current browser owner.

    Returns validated conversation metadata ordered by most recent activity.

    Raises:
        FileAssistantAPIError:
            If the API cannot be reached, returns an unsuccessful response,
            returns invalid JSON, or returns an invalid conversation payload.
    """

    try:
        response = httpx.get(
            f"{API_BASE_URL}/conversations",
            params={
                "owner_id": owner_id,
            },
            timeout=CONVERSATIONS_TIMEOUT_SECONDS,
        )

        response.raise_for_status()

    except httpx.TimeoutException as exc:
        raise FileAssistantAPIError(
            "The File Assistant conversation request timed out."
        ) from exc

    except httpx.HTTPStatusError as exc:
        raise FileAssistantAPIError(
            f"The File Assistant API returned HTTP "
            f"{exc.response.status_code} while loading conversations."
        ) from exc

    except httpx.RequestError as exc:
        raise FileAssistantAPIError(
            "Could not connect to the File Assistant API while loading "
            "conversations."
        ) from exc

    try:
        payload = response.json()

    except ValueError as exc:
        raise FileAssistantAPIError(
            "The File Assistant API returned invalid JSON while loading "
            "conversations."
        ) from exc

    conversations = payload.get(
        "conversations",
    )

    if not isinstance(
        conversations,
        list,
    ):
        raise FileAssistantAPIError(
            "The File Assistant API returned an invalid conversation payload."
        )

    validated = []

    for conversation in conversations:
        if not isinstance(
            conversation,
            dict,
        ):
            raise FileAssistantAPIError(
                "The File Assistant API returned an invalid conversation payload."
            )

        thread_id = conversation.get(
            "thread_id",
        )

        title = conversation.get(
            "title",
        )

        updated_at = conversation.get(
            "updated_at",
        )

        if (
            not isinstance(
                thread_id,
                str,
            )
            or not isinstance(
                title,
                str,
            )
            or not isinstance(
                updated_at,
                str,
            )
        ):
            raise FileAssistantAPIError(
                "The File Assistant API returned an invalid conversation payload."
            )

        validated.append(
            {
                "thread_id": thread_id,
                "title": title,
                "updated_at": updated_at,
            }
        )

    return validated

# =============================================================================
# Workspace Client
# =============================================================================


def get_workspace(
    thread_id: str,
) -> list[dict]:
    """
    Retrieve the workspace tree for a conversation thread.
    """

    try:
        response = httpx.get(
            f"{API_BASE_URL}/workspace",
            params={
                "thread_id": thread_id,
            },
            timeout=CONVERSATIONS_TIMEOUT_SECONDS,
        )

        response.raise_for_status()

    except httpx.TimeoutException as exc:
        raise FileAssistantAPIError(
            "The workspace request timed out."
        ) from exc

    except httpx.HTTPStatusError as exc:
        raise FileAssistantAPIError(
            f"The File Assistant API returned HTTP "
            f"{exc.response.status_code} while loading the workspace."
        ) from exc

    except httpx.RequestError as exc:
        raise FileAssistantAPIError(
            "Could not connect to the File Assistant API while loading the workspace."
        ) from exc

    payload = response.json()

    return payload["items"] 

# =============================================================================
# File Preview Client
# =============================================================================


def get_file_preview(
    thread_id: str,
    relative_path: str,
) -> str:
    """
    Retrieve a UTF-8 text preview from the backend.
    """

    try:
        response = httpx.get(
            f"{API_BASE_URL}/preview",
            params={
                "thread_id": thread_id,
                "relative_path": relative_path,
            },
            timeout=CONVERSATIONS_TIMEOUT_SECONDS,
        )

        response.raise_for_status()

    except httpx.TimeoutException as exc:
        raise FileAssistantAPIError(
            "The preview request timed out."
        ) from exc

    except httpx.HTTPStatusError as exc:
        raise FileAssistantAPIError(
            f"The File Assistant API returned HTTP "
            f"{exc.response.status_code} while loading the preview."
        ) from exc

    except httpx.RequestError as exc:
        raise FileAssistantAPIError(
            "Could not connect to the File Assistant API while loading the preview."
        ) from exc

    payload = response.json()

    return payload["content"]