# =============================================================================
# Standard Library Imports
# =============================================================================


import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


# =============================================================================
# Third-Party Imports
# =============================================================================


from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


# =============================================================================
# Project Imports
# =============================================================================


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
# Database Runtime Resources
# =============================================================================


@dataclass(
    frozen=True,
    slots=True,
)
class DatabaseRuntime:
    """
    Application-owned database resources available during one runtime.

    The checkpointer stores LangGraph state.

    PostgreSQL exposes its shared connection pool so additional persistence
    components can reuse the same application-owned pool.

    SQLite does not expose a PostgreSQL pool.
    """

    checkpointer: BaseCheckpointSaver

    pool: ConnectionPool | None


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
# Database Runtime Lifecycle
# =============================================================================


@contextmanager
def database_runtime() -> Iterator[DatabaseRuntime]:
    """
    Create, initialize, yield, and clean up shared database resources.

    SQLite owns a direct sqlite3 connection that is closed during cleanup.

    PostgreSQL owns one bounded psycopg ConnectionPool for the application
    runtime. LangGraph checkpoint persistence and application-owned database
    repositories can reuse this pool.

    The runtime owns resource cleanup. Consumers must not close the shared
    connection pool or SQLite checkpoint connection directly.
    """
    if CHECKPOINT_BACKEND == "sqlite":
        checkpointer = create_sqlite_checkpointer()

        try:
            yield DatabaseRuntime(
                checkpointer=checkpointer,
                pool=None,
            )

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
            checkpointer = PostgresSaver(
                pool,
            )

            checkpointer.setup()

            yield DatabaseRuntime(
                checkpointer=checkpointer,
                pool=pool,
            )

        return

    raise RuntimeError(
        f"Unsupported checkpoint backend: {CHECKPOINT_BACKEND}"
    )


# =============================================================================
# Backward-Compatible Checkpointer Runtime
# =============================================================================


@contextmanager
def checkpointer_runtime() -> Iterator[BaseCheckpointSaver]:
    """
    Yield only the configured LangGraph checkpointer.

    This compatibility wrapper preserves the existing runtime interface while
    database_runtime() exposes shared database resources to application layers
    that require them.
    """
    with database_runtime() as runtime:
        yield runtime.checkpointer