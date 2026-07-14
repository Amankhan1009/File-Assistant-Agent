# =============================================================================
# Imports
# =============================================================================


import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from core.config import CHECKPOINT_BACKEND, DATABASE_URL


# =============================================================================
# Checkpoint Database Configuration
# =============================================================================


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_DIRECTORY = PROJECT_ROOT / "database"

CHECKPOINT_DATABASE_PATH = (
    DATABASE_DIRECTORY
    / "checkpoints.db"
)


# =============================================================================
# Database Directory Initialization
# =============================================================================


def ensure_database_directory() -> None:
    """Ensure the application database directory exists."""
    DATABASE_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )


# =============================================================================
# SQLite Checkpointer
# =============================================================================


def create_checkpoint_connection() -> sqlite3.Connection:
    """
    Create the SQLite connection used for local checkpoint persistence.
    """
    ensure_database_directory()

    return sqlite3.connect(
        CHECKPOINT_DATABASE_PATH,
        check_same_thread=False,
    )


def create_sqlite_checkpointer() -> SqliteSaver:
    """Create a SQLite-backed LangGraph checkpointer."""
    connection = create_checkpoint_connection()

    return SqliteSaver(connection)


# =============================================================================
# Checkpointer Runtime Lifecycle
# =============================================================================


@contextmanager
def checkpointer_runtime() -> Iterator[BaseCheckpointSaver]:
    """
    Create, initialize, yield, and clean up the configured checkpointer.

    SQLite owns a direct sqlite3 connection that is closed during cleanup.

    PostgreSQL uses a bounded psycopg ConnectionPool for long-running
    application processes. PostgresSaver borrows connections from the pool,
    and setup() initializes or migrates the LangGraph checkpoint schema
    before the checkpointer is used.
    """
    if CHECKPOINT_BACKEND == "sqlite":
        checkpointer = create_sqlite_checkpointer()

        try:
            yield checkpointer

        finally:
            checkpointer.conn.close()

        return

    if CHECKPOINT_BACKEND == "postgres":
        with ConnectionPool(
            conninfo=DATABASE_URL,
            min_size=1,
            max_size=5,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
            },
        ) as pool:
            checkpointer = PostgresSaver(pool)

            checkpointer.setup()

            yield checkpointer

        return

    raise RuntimeError(
        f"Unsupported checkpoint backend: {CHECKPOINT_BACKEND}"
    )
