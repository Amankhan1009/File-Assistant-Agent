import frontend.conversation as conversation


# =============================================================================
# Test Doubles
# =============================================================================


class FakeQueryParams:
    """
    Minimal test double for Streamlit query parameters.
    """

    def __init__(
        self,
        values=None,
    ):
        self.values = dict(
            values or {},
        )


    def get(
        self,
        key,
        default=None,
    ):
        return self.values.get(
            key,
            default,
        )


    def __setitem__(
        self,
        key,
        value,
    ):
        self.values[key] = value


# =============================================================================
# Thread ID Creation Tests
# =============================================================================


def test_create_thread_id_returns_unique_prefixed_values():
    """
    Verify that generated thread IDs are unique and use the expected prefix.
    """
    first_thread_id = conversation.create_thread_id()

    second_thread_id = conversation.create_thread_id()

    assert first_thread_id.startswith(
        "web-",
    )

    assert second_thread_id.startswith(
        "web-",
    )

    assert first_thread_id != second_thread_id


# =============================================================================
# Thread ID Resolution Tests
# =============================================================================


def test_resolve_thread_id_returns_existing_url_thread():
    """
    Verify that an existing URL thread ID is reused.
    """
    query_params = FakeQueryParams(
        {
            "thread": "existing-thread",
        }
    )

    thread_id = conversation.resolve_thread_id(
        query_params=query_params,
    )

    assert thread_id == "existing-thread"

    assert query_params.values == {
        "thread": "existing-thread",
    }


def test_resolve_thread_id_creates_and_stores_missing_url_thread(
    monkeypatch,
):
    """
    Verify that a missing URL thread ID is generated and written to the URL.
    """
    query_params = FakeQueryParams()

    monkeypatch.setattr(
        conversation,
        "create_thread_id",
        lambda: "web-generated-thread",
    )

    thread_id = conversation.resolve_thread_id(
        query_params=query_params,
    )

    assert thread_id == "web-generated-thread"

    assert query_params.values == {
        "thread": "web-generated-thread",
    }


# =============================================================================
# Conversation Session Initialization Tests
# =============================================================================


def test_initialize_conversation_state_loads_persisted_messages(
    monkeypatch,
):
    """
    Verify that persisted backend messages are loaded when the active URL
    thread differs from the current frontend session thread.
    """
    session_state = {}

    query_params = FakeQueryParams(
        {
            "thread": "existing-thread",
        }
    )

    load_calls = []

    persisted_messages = [
        {
            "role": "user",
            "content": "Hello",
        },
        {
            "role": "assistant",
            "content": "Hi there",
        },
    ]

    def fake_load_thread_messages(
        thread_id,
    ):
        load_calls.append(thread_id)

        return persisted_messages

    thread_id = conversation.initialize_conversation_state(
        session_state=session_state,
        query_params=query_params,
        load_thread_messages=fake_load_thread_messages,
    )

    assert thread_id == "existing-thread"

    assert load_calls == [
        "existing-thread",
    ]

    assert session_state["thread_id"] == "existing-thread"

    assert session_state["messages"] == persisted_messages


def test_initialize_conversation_state_does_not_reload_active_thread():
    """
    Verify that Streamlit reruns do not repeatedly request persisted history
    when the frontend session already owns the active URL thread.
    """
    existing_messages = [
        {
            "role": "user",
            "content": "Existing message",
        }
    ]

    session_state = {
        "thread_id": "existing-thread",
        "messages": existing_messages,
    }

    query_params = FakeQueryParams(
        {
            "thread": "existing-thread",
        }
    )

    load_calls = []

    def fake_load_thread_messages(
        thread_id,
    ):
        load_calls.append(thread_id)

        return []

    thread_id = conversation.initialize_conversation_state(
        session_state=session_state,
        query_params=query_params,
        load_thread_messages=fake_load_thread_messages,
    )

    assert thread_id == "existing-thread"

    assert load_calls == []

    assert session_state["messages"] is existing_messages


# =============================================================================
# New Conversation Tests
# =============================================================================


def test_start_new_conversation_replaces_thread_and_clears_messages(
    monkeypatch,
):
    """
    Verify that starting a new conversation creates a new URL thread and clears
    frontend message history.
    """
    session_state = {
        "thread_id": "old-thread",
        "messages": [
            {
                "role": "user",
                "content": "Old message",
            }
        ],
    }

    query_params = FakeQueryParams(
        {
            "thread": "old-thread",
        }
    )

    monkeypatch.setattr(
        conversation,
        "create_thread_id",
        lambda: "web-new-thread",
    )

    thread_id = conversation.start_new_conversation(
        session_state=session_state,
        query_params=query_params,
    )

    assert thread_id == "web-new-thread"

    assert query_params.values == {
        "thread": "web-new-thread",
    }

    assert session_state["thread_id"] == "web-new-thread"

    assert session_state["messages"] == []