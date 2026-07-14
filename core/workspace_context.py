# =============================================================================
# Standard Library Imports
# =============================================================================


from contextlib import contextmanager
from contextvars import ContextVar, Token
from hashlib import sha256
from pathlib import Path
from typing import Iterator


# =============================================================================
# Workspace Context State
# =============================================================================


_ACTIVE_WORKSPACE_ROOT: ContextVar[Path | None] = ContextVar(
    "active_workspace_root",
    default=None,
)


# =============================================================================
# Thread Workspace Identity
# =============================================================================


def create_thread_workspace_key(
    thread_id: str,
) -> str:
    """
    Create a deterministic filesystem-safe workspace key for a thread.

    The raw thread ID is never used directly as a filesystem path component.
    """
    if not isinstance(thread_id, str):
        raise TypeError(
            "Thread ID must be a string."
        )

    normalized_thread_id = thread_id.strip()

    if not normalized_thread_id:
        raise ValueError(
            "Thread ID cannot be empty."
        )

    return sha256(
        normalized_thread_id.encode("utf-8")
    ).hexdigest()


# =============================================================================
# Active Workspace Access
# =============================================================================


def get_active_workspace_root() -> Path | None:
    """Return the workspace root bound to the current execution context."""
    return _ACTIVE_WORKSPACE_ROOT.get()


# =============================================================================
# Workspace Context Binding
# =============================================================================


@contextmanager
def bind_workspace_root(
    workspace_root: Path,
) -> Iterator[Path]:
    """
    Temporarily bind a workspace root to the current execution context.

    ContextVar keeps concurrent execution contexts isolated and restores the
    previous workspace binding when execution leaves the context manager.
    """
    resolved_workspace_root = workspace_root.resolve()

    token: Token = _ACTIVE_WORKSPACE_ROOT.set(
        resolved_workspace_root,
    )

    try:
        yield resolved_workspace_root

    finally:
        _ACTIVE_WORKSPACE_ROOT.reset(token)