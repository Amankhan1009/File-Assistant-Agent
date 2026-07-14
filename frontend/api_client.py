import os

import httpx


DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"

API_BASE_URL = os.getenv(
    "FILE_ASSISTANT_API_URL",
    DEFAULT_API_BASE_URL,
).rstrip("/")

CHAT_TIMEOUT_SECONDS = 120.0

HEALTH_TIMEOUT_SECONDS = 5.0


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