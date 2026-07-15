# =============================================================================
# Standard Library Imports
# =============================================================================


from datetime import datetime, timezone

import pytest


# =============================================================================
# Project Imports
# =============================================================================


from database.conversations import ConversationRecord


# =============================================================================
# Conversation Record Tests
# =============================================================================


def test_conversation_record_stores_conversation_metadata():
    """
    Verify that ConversationRecord stores application-owned conversation
    metadata independently from LangGraph checkpoint state.
    """
    created_at = datetime(
        2026,
        7,
        14,
        10,
        30,
        tzinfo=timezone.utc,
    )

    updated_at = datetime(
        2026,
        7,
        14,
        11,
        45,
        tzinfo=timezone.utc,
    )

    record = ConversationRecord(
        thread_id="web-thread-1",
        owner_id="browser-owner-1",
        title="Create project notes",
        created_at=created_at,
        updated_at=updated_at,
    )

    assert record.thread_id == "web-thread-1"

    assert record.owner_id == "browser-owner-1"

    assert record.title == "Create project notes"

    assert record.created_at == created_at

    assert record.updated_at == updated_at


def test_conversation_record_is_immutable():
    """
    Verify that conversation records cannot be mutated accidentally after
    retrieval from persistence.
    """
    timestamp = datetime.now(
        timezone.utc,
    )

    record = ConversationRecord(
        thread_id="web-thread-1",
        owner_id="browser-owner-1",
        title="Conversation",
        created_at=timestamp,
        updated_at=timestamp,
    )

    with pytest.raises(
        AttributeError,
    ):
        record.title = "Changed title"

# =============================================================================
# Conversation Repository Contract Tests
# =============================================================================


def test_conversation_repository_defines_required_operations():
    """
    Verify that the repository abstraction exposes the application-level
    operations required by the conversation registry.
    """
    from database.conversations import ConversationRepository

    required_methods = (
        "ensure_conversation",
        "get_conversation",
        "list_conversations",
        "touch_conversation",
    )

    for method_name in required_methods:
        assert hasattr(
            ConversationRepository,
            method_name,
        )


def test_conversation_repository_cannot_be_instantiated_directly():
    """
    Verify that the repository abstraction requires a concrete persistence
    implementation before it can be used.
    """
    from database.conversations import ConversationRepository

    with pytest.raises(
        TypeError,
    ):
        ConversationRepository()


# =============================================================================
# PostgreSQL Repository Test Doubles
# =============================================================================


class FakeCursor:
    """
    Test double for a PostgreSQL cursor.

    Records executed SQL statements and returns configurable query results.
    """

    def __init__(
        self,
        fetchone_results=None,
        fetchall_results=None,
    ):
        self.fetchone_results = list(
            fetchone_results or [],
        )

        self.fetchall_results = list(
            fetchall_results or [],
        )

        self.execute_calls = []


    def execute(
        self,
        query,
        params=None,
    ):
        """Record one SQL execution."""
        self.execute_calls.append(
            {
                "query": query,
                "params": params,
            }
        )


    def fetchone(self):
        """Return the next configured single-row result."""
        if not self.fetchone_results:
            return None

        return self.fetchone_results.pop(0)


    def fetchall(self):
        """Return the next configured multi-row result."""
        if not self.fetchall_results:
            return []

        return self.fetchall_results.pop(0)


class FakeCursorContext:
    """Context manager test double that yields a fake cursor."""

    def __init__(
        self,
        cursor,
    ):
        self.cursor = cursor


    def __enter__(self):
        return self.cursor


    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        return False


class FakeConnection:
    """Test double for a PostgreSQL connection."""

    def __init__(
        self,
        cursor,
    ):
        self.cursor_instance = cursor


    def cursor(self):
        return FakeCursorContext(
            self.cursor_instance,
        )


class FakeConnectionContext:
    """Context manager test double that yields a fake connection."""

    def __init__(
        self,
        connection,
    ):
        self.connection = connection


    def __enter__(self):
        return self.connection


    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        return False


class FakeConnectionPool:
    """Test double for the application-owned PostgreSQL connection pool."""

    def __init__(
        self,
        cursor,
    ):
        self.connection_instance = FakeConnection(
            cursor=cursor,
        )

        self.connection_calls = 0


    def connection(self):
        self.connection_calls += 1

        return FakeConnectionContext(
            self.connection_instance,
        )


# =============================================================================
# PostgreSQL Repository Schema Tests
# =============================================================================


def test_postgres_conversation_repository_setup_creates_schema():
    """
    Verify that repository setup creates the conversations table and owner
    activity index using the injected connection pool.
    """
    from database.conversations import PostgresConversationRepository

    cursor = FakeCursor()

    pool = FakeConnectionPool(
        cursor=cursor,
    )

    repository = PostgresConversationRepository(
        pool=pool,
    )

    repository.setup()

    assert pool.connection_calls == 1

    assert len(cursor.execute_calls) == 2

    create_table_call = cursor.execute_calls[0]

    create_index_call = cursor.execute_calls[1]

    assert "CREATE TABLE IF NOT EXISTS conversations" in (
        create_table_call["query"]
    )

    assert "thread_id" in create_table_call["query"]

    assert "owner_id" in create_table_call["query"]

    assert "title" in create_table_call["query"]

    assert "created_at" in create_table_call["query"]

    assert "updated_at" in create_table_call["query"]

    assert "CREATE INDEX IF NOT EXISTS" in (
        create_index_call["query"]
    )

    assert "owner_id" in create_index_call["query"]

    assert "updated_at" in create_index_call["query"]


# =============================================================================
# PostgreSQL Repository Creation Tests
# =============================================================================


def test_postgres_conversation_repository_ensures_new_conversation():
    """
    Verify that ensure_conversation inserts missing conversation metadata and
    returns the stored conversation record.
    """
    from database.conversations import PostgresConversationRepository


    # -------------------------------------------------------------------------
    # Test Data
    # -------------------------------------------------------------------------


    created_at = datetime(
        2026,
        7,
        15,
        8,
        30,
        tzinfo=timezone.utc,
    )

    row = {
        "thread_id": "web-thread-1",
        "owner_id": "browser-owner-1",
        "title": "Create project notes",
        "created_at": created_at,
        "updated_at": created_at,
    }


    # -------------------------------------------------------------------------
    # Fake PostgreSQL Runtime
    # -------------------------------------------------------------------------


    cursor = FakeCursor(
        fetchone_results=[
            row,
        ],
    )

    pool = FakeConnectionPool(
        cursor=cursor,
    )

    repository = PostgresConversationRepository(
        pool=pool,
    )


    # -------------------------------------------------------------------------
    # Repository Execution
    # -------------------------------------------------------------------------


    record = repository.ensure_conversation(
        thread_id="web-thread-1",
        owner_id="browser-owner-1",
        title="Create project notes",
    )


    # -------------------------------------------------------------------------
    # Record Assertions
    # -------------------------------------------------------------------------


    assert record == ConversationRecord(
        thread_id="web-thread-1",
        owner_id="browser-owner-1",
        title="Create project notes",
        created_at=created_at,
        updated_at=created_at,
    )


    # -------------------------------------------------------------------------
    # Database Interaction Assertions
    # -------------------------------------------------------------------------


    assert pool.connection_calls == 1

    assert len(cursor.execute_calls) == 1

    execute_call = cursor.execute_calls[0]

    assert "INSERT INTO conversations" in execute_call["query"]

    assert "ON CONFLICT" in execute_call["query"]

    assert "RETURNING" in execute_call["query"]

    assert execute_call["params"] == (
        "web-thread-1",
        "browser-owner-1",
        "Create project notes",
    )


# =============================================================================
# PostgreSQL Repository Existing Conversation Tests
# =============================================================================


def test_postgres_conversation_repository_returns_existing_owned_conversation():
    """
    Verify that an existing conversation is retrieved after an insert conflict
    when it belongs to the requested owner.
    """
    from database.conversations import PostgresConversationRepository

    timestamp = datetime(
        2026,
        7,
        15,
        9,
        0,
        tzinfo=timezone.utc,
    )

    existing_row = {
        "thread_id": "existing-thread",
        "owner_id": "browser-owner-1",
        "title": "Existing conversation",
        "created_at": timestamp,
        "updated_at": timestamp,
    }

    cursor = FakeCursor(
        fetchone_results=[
            None,
            existing_row,
        ],
    )

    repository = PostgresConversationRepository(
        pool=FakeConnectionPool(
            cursor=cursor,
        ),
    )

    record = repository.ensure_conversation(
        thread_id="existing-thread",
        owner_id="browser-owner-1",
        title="Ignored replacement title",
    )

    assert record == ConversationRecord(
        thread_id="existing-thread",
        owner_id="browser-owner-1",
        title="Existing conversation",
        created_at=timestamp,
        updated_at=timestamp,
    )

    assert len(cursor.execute_calls) == 2

    assert "INSERT INTO conversations" in (
        cursor.execute_calls[0]["query"]
    )

    assert "SELECT" in (
        cursor.execute_calls[1]["query"]
    )

    assert cursor.execute_calls[1]["params"] == (
        "existing-thread",
    )


def test_postgres_conversation_repository_rejects_cross_owner_thread_claim():
    """
    Verify that an existing thread cannot be claimed by another owner.
    """
    from database.conversations import PostgresConversationRepository

    timestamp = datetime(
        2026,
        7,
        15,
        9,
        30,
        tzinfo=timezone.utc,
    )

    existing_row = {
        "thread_id": "private-thread",
        "owner_id": "original-owner",
        "title": "Private conversation",
        "created_at": timestamp,
        "updated_at": timestamp,
    }

    cursor = FakeCursor(
        fetchone_results=[
            None,
            existing_row,
        ],
    )

    repository = PostgresConversationRepository(
        pool=FakeConnectionPool(
            cursor=cursor,
        ),
    )

    with pytest.raises(
        PermissionError,
        match="another owner",
    ):
        repository.ensure_conversation(
            thread_id="private-thread",
            owner_id="different-owner",
            title="Attempted claim",
        )


# =============================================================================
# PostgreSQL Repository Retrieval Tests
# =============================================================================


def test_postgres_conversation_repository_gets_owned_conversation():
    """
    Verify that get_conversation returns one owned conversation.
    """
    from database.conversations import PostgresConversationRepository

    timestamp = datetime(
        2026,
        7,
        15,
        10,
        0,
        tzinfo=timezone.utc,
    )

    row = {
        "thread_id": "owned-thread",
        "owner_id": "browser-owner-1",
        "title": "Owned conversation",
        "created_at": timestamp,
        "updated_at": timestamp,
    }

    cursor = FakeCursor(
        fetchone_results=[
            row,
        ],
    )

    repository = PostgresConversationRepository(
        pool=FakeConnectionPool(
            cursor=cursor,
        ),
    )

    record = repository.get_conversation(
        thread_id="owned-thread",
        owner_id="browser-owner-1",
    )

    assert record == ConversationRecord(
        thread_id="owned-thread",
        owner_id="browser-owner-1",
        title="Owned conversation",
        created_at=timestamp,
        updated_at=timestamp,
    )

    execute_call = cursor.execute_calls[0]

    assert "WHERE thread_id = %s" in (
        execute_call["query"]
    )

    assert "AND owner_id = %s" in (
        execute_call["query"]
    )

    assert execute_call["params"] == (
        "owned-thread",
        "browser-owner-1",
    )


def test_postgres_conversation_repository_hides_inaccessible_conversation():
    """
    Verify that missing and foreign conversations are represented as missing.
    """
    from database.conversations import PostgresConversationRepository

    cursor = FakeCursor(
        fetchone_results=[
            None,
        ],
    )

    repository = PostgresConversationRepository(
        pool=FakeConnectionPool(
            cursor=cursor,
        ),
    )

    record = repository.get_conversation(
        thread_id="foreign-thread",
        owner_id="browser-owner-1",
    )

    assert record is None


# =============================================================================
# PostgreSQL Repository Listing Tests
# =============================================================================


def test_postgres_conversation_repository_lists_owned_conversations():
    """
    Verify that list_conversations returns owner-scoped conversation records.
    """
    from database.conversations import PostgresConversationRepository

    older_timestamp = datetime(
        2026,
        7,
        15,
        10,
        0,
        tzinfo=timezone.utc,
    )

    newer_timestamp = datetime(
        2026,
        7,
        15,
        11,
        0,
        tzinfo=timezone.utc,
    )

    rows = [
        {
            "thread_id": "newer-thread",
            "owner_id": "browser-owner-1",
            "title": "Newer conversation",
            "created_at": newer_timestamp,
            "updated_at": newer_timestamp,
        },
        {
            "thread_id": "older-thread",
            "owner_id": "browser-owner-1",
            "title": "Older conversation",
            "created_at": older_timestamp,
            "updated_at": older_timestamp,
        },
    ]

    cursor = FakeCursor(
        fetchall_results=[
            rows,
        ],
    )

    repository = PostgresConversationRepository(
        pool=FakeConnectionPool(
            cursor=cursor,
        ),
    )

    records = repository.list_conversations(
        owner_id="browser-owner-1",
    )

    assert [
        record.thread_id
        for record in records
    ] == [
        "newer-thread",
        "older-thread",
    ]

    execute_call = cursor.execute_calls[0]

    assert "WHERE owner_id = %s" in (
        execute_call["query"]
    )

    assert "updated_at DESC" in (
        execute_call["query"]
    )

    assert execute_call["params"] == (
        "browser-owner-1",
    )


# =============================================================================
# PostgreSQL Repository Activity Tests
# =============================================================================


def test_postgres_conversation_repository_touches_owned_conversation():
    """
    Verify that touch_conversation updates and returns an owned conversation.
    """
    from database.conversations import PostgresConversationRepository

    created_at = datetime(
        2026,
        7,
        15,
        10,
        0,
        tzinfo=timezone.utc,
    )

    updated_at = datetime(
        2026,
        7,
        15,
        12,
        0,
        tzinfo=timezone.utc,
    )

    row = {
        "thread_id": "active-thread",
        "owner_id": "browser-owner-1",
        "title": "Active conversation",
        "created_at": created_at,
        "updated_at": updated_at,
    }

    cursor = FakeCursor(
        fetchone_results=[
            row,
        ],
    )

    repository = PostgresConversationRepository(
        pool=FakeConnectionPool(
            cursor=cursor,
        ),
    )

    record = repository.touch_conversation(
        thread_id="active-thread",
        owner_id="browser-owner-1",
    )

    assert record == ConversationRecord(
        thread_id="active-thread",
        owner_id="browser-owner-1",
        title="Active conversation",
        created_at=created_at,
        updated_at=updated_at,
    )

    execute_call = cursor.execute_calls[0]

    assert "UPDATE conversations" in (
        execute_call["query"]
    )

    assert "CURRENT_TIMESTAMP" in (
        execute_call["query"]
    )

    assert "AND owner_id = %s" in (
        execute_call["query"]
    )

    assert execute_call["params"] == (
        "active-thread",
        "browser-owner-1",
    )


def test_postgres_conversation_repository_does_not_touch_inaccessible_conversation():
    """
    Verify that missing or foreign conversations are not exposed after touch.
    """
    from database.conversations import PostgresConversationRepository

    cursor = FakeCursor(
        fetchone_results=[
            None,
        ],
    )

    repository = PostgresConversationRepository(
        pool=FakeConnectionPool(
            cursor=cursor,
        ),
    )

    record = repository.touch_conversation(
        thread_id="foreign-thread",
        owner_id="browser-owner-1",
    )

    assert record is None
