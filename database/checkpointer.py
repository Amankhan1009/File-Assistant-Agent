# =============================================================================
# Imports
# =============================================================================


import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver


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
    """
    Ensure the application database directory exists.
    """
    DATABASE_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )


# =============================================================================
# SQLite Connection Factory
# =============================================================================


def create_checkpoint_connection() -> sqlite3.Connection:
    """
    Create a SQLite connection for LangGraph checkpoint persistence.

    check_same_thread=False allows the connection to be used by graph
    executions that may run from different threads.
    """
    ensure_database_directory()

    return sqlite3.connect(
        CHECKPOINT_DATABASE_PATH,
        check_same_thread=False,
    )


# =============================================================================
# SQLite Checkpointer Factory
# =============================================================================


def create_checkpointer() -> SqliteSaver:
    """
    Create a LangGraph SQLite checkpointer backed by the application's
    persistent checkpoint database.
    """
    connection = create_checkpoint_connection()

    return SqliteSaver(connection)