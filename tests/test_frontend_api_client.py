import httpx
import pytest

import frontend.api_client as api_client


# =============================================================================
# Test Doubles
# =============================================================================


class FakeResponse:
    """
    Test double for an httpx response.

    Supports configurable JSON payloads, HTTP status failures, and invalid JSON
    responses so API-client behavior can be tested without real network calls.
    """

    def __init__(
        self,
        payload=None,
        status_code=200,
        json_error=None,
    ):
        self.payload = payload
        self.status_code = status_code
        self.json_error = json_error


    def raise_for_status(self):
        """Raise HTTPStatusError when the configured status is unsuccessful."""
        if self.status_code >= 400:
            request = httpx.Request(
                "GET",
                "http://test-api",
            )

            response = httpx.Response(
                self.status_code,
                request=request,
            )

            raise httpx.HTTPStatusError(
                "HTTP request failed.",
                request=request,
                response=response,
            )


    def json(self):
        """Return the configured payload or raise the configured JSON error."""
        if self.json_error is not None:
            raise self.json_error

        return self.payload


# =============================================================================
# Thread Message History Client Tests
# =============================================================================


def test_get_thread_messages_returns_persisted_messages(
    monkeypatch,
):
    """
    Verify that the API client requests the expected thread-history endpoint
    and returns validated persisted messages.
    """


    # -------------------------------------------------------------------------
    # Test Data
    # -------------------------------------------------------------------------


    thread_id = "existing-thread"

    expected_messages = [
        {
            "role": "user",
            "content": "Hello",
        },
        {
            "role": "assistant",
            "content": "Hi there",
        },
    ]


    # -------------------------------------------------------------------------
    # Fake HTTP Request
    # -------------------------------------------------------------------------


    get_calls = []

    def fake_get(
        url,
        timeout,
    ):
        get_calls.append(
            {
                "url": url,
                "timeout": timeout,
            }
        )

        return FakeResponse(
            payload={
                "thread_id": thread_id,
                "messages": expected_messages,
            }
        )


    monkeypatch.setattr(
        api_client.httpx,
        "get",
        fake_get,
    )


    # -------------------------------------------------------------------------
    # Client Execution
    # -------------------------------------------------------------------------


    messages = api_client.get_thread_messages(
        thread_id=thread_id,
    )


    # -------------------------------------------------------------------------
    # Response Assertions
    # -------------------------------------------------------------------------


    assert messages == expected_messages

    assert get_calls == [
        {
            "url": (
                f"{api_client.API_BASE_URL}"
                f"/threads/{thread_id}/messages"
            ),
            "timeout": api_client.HISTORY_TIMEOUT_SECONDS,
        }
    ]


def test_get_thread_messages_returns_empty_list_for_missing_thread(
    monkeypatch,
):
    """
    Verify that an API response containing an empty persisted message list is
    returned as an empty frontend conversation.
    """
    monkeypatch.setattr(
        api_client.httpx,
        "get",
        lambda url, timeout: FakeResponse(
            payload={
                "thread_id": "missing-thread",
                "messages": [],
            }
        ),
    )

    messages = api_client.get_thread_messages(
        thread_id="missing-thread",
    )

    assert messages == []


def test_get_thread_messages_rejects_invalid_message_payload(
    monkeypatch,
):
    """
    Verify that malformed persisted messages are rejected instead of being
    copied into frontend session state.
    """
    monkeypatch.setattr(
        api_client.httpx,
        "get",
        lambda url, timeout: FakeResponse(
            payload={
                "thread_id": "invalid-thread",
                "messages": [
                    {
                        "role": "invalid-role",
                        "content": "Unexpected message",
                    }
                ],
            }
        ),
    )

    with pytest.raises(
        api_client.FileAssistantAPIError,
        match="invalid message history payload",
    ):
        api_client.get_thread_messages(
            thread_id="invalid-thread",
        )
