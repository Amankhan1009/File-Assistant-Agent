# =============================================================================
# Standard Library Imports
# =============================================================================


from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


# =============================================================================
# Conversation Record
# =============================================================================


@dataclass(
    frozen=True,
    slots=True,
)
class ConversationRecord:
    """
    Application-owned metadata describing one File Assistant conversation.

    LangGraph checkpoint persistence remains responsible for agent state and
    message history. ConversationRecord contains only metadata required for
    conversation discovery, ownership isolation, and sidebar presentation.
    """

    thread_id: str

    owner_id: str

    title: str

    created_at: datetime

    updated_at: datetime


# =============================================================================
# Conversation Repository Interface
# =============================================================================


class ConversationRepository(ABC):
    """
    Abstract persistence contract for application-owned conversation metadata.

    Concrete implementations may use SQLite, PostgreSQL, or another durable
    database backend without exposing database-specific behavior to the API
    and frontend layers.

    LangGraph checkpoint persistence remains separate from this repository.
    """

    # -------------------------------------------------------------------------
    # Conversation Creation
    # -------------------------------------------------------------------------


    @abstractmethod
    def ensure_conversation(
        self,
        thread_id: str,
        owner_id: str,
        title: str,
    ) -> ConversationRecord:
        """
        Return the requested conversation, creating it when it does not exist.

        Implementations must preserve the original creation timestamp and must
        not transfer an existing thread to another owner.
        """
        raise NotImplementedError


    # -------------------------------------------------------------------------
    # Conversation Retrieval
    # -------------------------------------------------------------------------


    @abstractmethod
    def get_conversation(
        self,
        thread_id: str,
        owner_id: str,
    ) -> ConversationRecord | None:
        """
        Return one conversation owned by the requested owner.

        Return None when the conversation does not exist or belongs to another
        owner.
        """
        raise NotImplementedError


    # -------------------------------------------------------------------------
    # Conversation Listing
    # -------------------------------------------------------------------------


    @abstractmethod
    def list_conversations(
        self,
        owner_id: str,
    ) -> list[ConversationRecord]:
        """
        Return conversations owned by the requested owner.

        Implementations must order conversations by most recent activity
        first.
        """
        raise NotImplementedError


    # -------------------------------------------------------------------------
    # Conversation Activity Update
    # -------------------------------------------------------------------------


    @abstractmethod
    def touch_conversation(
        self,
        thread_id: str,
        owner_id: str,
    ) -> ConversationRecord | None:
        """
        Update the conversation activity timestamp.

        Return the updated conversation when it exists and belongs to the
        requested owner.

        Return None when the conversation does not exist or belongs to another
        owner.
        """
        raise NotImplementedError
# =============================================================================
# PostgreSQL Conversation Repository
# =============================================================================


class PostgresConversationRepository(
    ConversationRepository,
):
    """
    PostgreSQL-backed repository for application-owned conversation metadata.

    The repository receives an application-owned connection pool through
    constructor injection. It does not create, open, or close the pool.

    LangGraph checkpoint persistence remains separate from conversation
    metadata persistence.
    """


    # -------------------------------------------------------------------------
    # Repository Initialization
    # -------------------------------------------------------------------------


    def __init__(
        self,
        pool,
    ):
        """
        Initialize the repository with an application-owned PostgreSQL pool.
        """
        self.pool = pool


    # -------------------------------------------------------------------------
    # Conversation Record Conversion
    # -------------------------------------------------------------------------


    @staticmethod
    def _row_to_record(
        row,
    ) -> ConversationRecord:
        """Convert one PostgreSQL result row into a ConversationRecord."""
        return ConversationRecord(
            thread_id=row["thread_id"],
            owner_id=row["owner_id"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


    # -------------------------------------------------------------------------
    # Conversation Schema Initialization
    # -------------------------------------------------------------------------


    def setup(self) -> None:
        """
        Create the conversation metadata table and owner activity index.

        Schema initialization is idempotent so setup can safely run during
        application startup.
        """
        create_table_query = """
            CREATE TABLE IF NOT EXISTS conversations (
                thread_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """

        create_index_query = """
            CREATE INDEX IF NOT EXISTS
                conversations_owner_updated_at_idx
            ON conversations (
                owner_id,
                updated_at DESC
            )
        """

        with self.pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    create_table_query,
                )

                cursor.execute(
                    create_index_query,
                )


    # -------------------------------------------------------------------------
    # Conversation Creation
    # -------------------------------------------------------------------------


    def ensure_conversation(
        self,
        thread_id: str,
        owner_id: str,
        title: str,
    ) -> ConversationRecord:
        """
        Return owned conversation metadata, creating it when missing.

        The insert is conflict-safe. When the thread already exists, a second
        owner cannot claim or modify the existing conversation.

        Raises:
            PermissionError:
                If the requested thread ID already belongs to another owner.
        """
        insert_query = """
            INSERT INTO conversations (
                thread_id,
                owner_id,
                title
            )
            VALUES (
                %s,
                %s,
                %s
            )
            ON CONFLICT (
                thread_id
            )
            DO NOTHING
            RETURNING
                thread_id,
                owner_id,
                title,
                created_at,
                updated_at
        """

        select_query = """
            SELECT
                thread_id,
                owner_id,
                title,
                created_at,
                updated_at
            FROM conversations
            WHERE thread_id = %s
        """

        with self.pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    insert_query,
                    (
                        thread_id,
                        owner_id,
                        title,
                    ),
                )

                row = cursor.fetchone()

                if row is None:
                    cursor.execute(
                        select_query,
                        (
                            thread_id,
                        ),
                    )

                    row = cursor.fetchone()

        if row is None:
            raise RuntimeError(
                "Conversation could not be created or retrieved."
            )

        record = self._row_to_record(
            row,
        )

        if record.owner_id != owner_id:
            raise PermissionError(
                "Conversation belongs to another owner."
            )

        return record


    # -------------------------------------------------------------------------
    # Conversation Retrieval
    # -------------------------------------------------------------------------


    def get_conversation(
        self,
        thread_id: str,
        owner_id: str,
    ) -> ConversationRecord | None:
        """
        Return one conversation owned by the requested owner.

        Conversations belonging to another owner are not exposed.
        """
        query = """
            SELECT
                thread_id,
                owner_id,
                title,
                created_at,
                updated_at
            FROM conversations
            WHERE thread_id = %s
              AND owner_id = %s
        """

        with self.pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        thread_id,
                        owner_id,
                    ),
                )

                row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_record(
            row,
        )


    # -------------------------------------------------------------------------
    # Conversation Listing
    # -------------------------------------------------------------------------


    def list_conversations(
        self,
        owner_id: str,
    ) -> list[ConversationRecord]:
        """
        Return conversations owned by one owner.

        Conversations are ordered by most recent activity first. Thread ID is
        used as a deterministic secondary ordering key.
        """
        query = """
            SELECT
                thread_id,
                owner_id,
                title,
                created_at,
                updated_at
            FROM conversations
            WHERE owner_id = %s
            ORDER BY
                updated_at DESC,
                thread_id ASC
        """

        with self.pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        owner_id,
                    ),
                )

                rows = cursor.fetchall()

        return [
            self._row_to_record(
                row,
            )
            for row in rows
        ]


    # -------------------------------------------------------------------------
    # Conversation Activity Update
    # -------------------------------------------------------------------------


    def touch_conversation(
        self,
        thread_id: str,
        owner_id: str,
    ) -> ConversationRecord | None:
        """
        Update activity time for one owned conversation.

        Missing conversations and conversations belonging to another owner are
        not modified.
        """
        query = """
            UPDATE conversations
            SET updated_at = CURRENT_TIMESTAMP
            WHERE thread_id = %s
              AND owner_id = %s
            RETURNING
                thread_id,
                owner_id,
                title,
                created_at,
                updated_at
        """

        with self.pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        thread_id,
                        owner_id,
                    ),
                )

                row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_record(
            row,
        )

