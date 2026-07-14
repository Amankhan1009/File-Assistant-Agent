import os

import httpx


DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"

API_BASE_URL = os.getenv(
    "FILE_ASSISTANT_API_URL",
    DEFAULT_API_BASE_URL,
).rstrip("/")

CHAT_TIMEOUT_SECONDS = 120.0

HEALTH_TIMEOUT_SECONDS = 5.0
HISTORY_TIMEOUT_SECONDS = 10.0


class FileAssistantAPIError(RuntimeError):
    """Raised when communication with the File Assistant API fails."""


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

    return payload.get("status") == "healthy"


def send_chat_message(
    message: str,
    thread_id: str,
) -> str:
    """
    Send one chat interaction to the File Assistant API.

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

    assistant_response = payload.get("response")

    if (
        not isinstance(assistant_response, str)
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


    # -------------------------------------------------------------------------
    # Thread History Request
    # -------------------------------------------------------------------------


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


    # -------------------------------------------------------------------------
    # Response JSON Parsing
    # -------------------------------------------------------------------------


    try:
        payload = response.json()

    except ValueError as exc:
        raise FileAssistantAPIError(
            "The File Assistant API returned invalid JSON while loading "
            "message history."
        ) from exc


    # -------------------------------------------------------------------------
    # Message History Payload Validation
    # -------------------------------------------------------------------------


    messages = payload.get("messages")

    if not isinstance(messages, list):
        raise FileAssistantAPIError(
            "The File Assistant API returned an invalid message history payload."
        )

    validated_messages = []

    for message in messages:
        if not isinstance(message, dict):
            raise FileAssistantAPIError(
                "The File Assistant API returned an invalid message history payload."
            )

        role = message.get("role")
        content = message.get("content")

        if (
            role not in {
                "user",
                "assistant",
            }
            or not isinstance(content, str)
        ):
            raise FileAssistantAPIError(
                "The File Assistant API returned an invalid message history payload."
            )

        validated_messages.append(
            {
                "role": role,
                "content": content,
            }
        )


    # -------------------------------------------------------------------------
    # Validated Message History
    # -------------------------------------------------------------------------


    return validated_messages