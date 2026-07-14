# =============================================================================
# Standard Library Imports
# =============================================================================


from pathlib import Path


# =============================================================================
# Project Imports
# =============================================================================


from core.config import WORKSPACE_ROOT
from core.workspace_context import (
    create_thread_workspace_key,
    get_active_workspace_root,
)


# =============================================================================
# Path Security Exceptions
# =============================================================================


class PathSecurityError(ValueError):
    """Raised when a requested path violates the workspace security boundary."""


# =============================================================================
# Active Workspace Resolution
# =============================================================================


def get_workspace_root() -> Path:
    """
    Return the workspace root for the current execution context.

    Resolution order:

    1. Use the active execution workspace when one is bound through
       workspace_context.
    2. Fall back to WORKSPACE_ROOT when no execution workspace is active.

    The fallback preserves local development, existing filesystem behavior,
    and evaluation workspace rebinding.
    """
    active_workspace_root = get_active_workspace_root()

    if active_workspace_root is not None:
        return active_workspace_root.resolve()

    return WORKSPACE_ROOT.resolve()


# =============================================================================
# Thread Workspace Resolution
# =============================================================================


def get_thread_workspace_root(
    thread_id: str,
) -> Path:
    """
    Return the deterministic isolated workspace root for a conversation thread.

    The raw thread ID is converted to a filesystem-safe SHA-256 workspace key
    before being used as a path component.

    Thread workspaces are stored below:

        WORKSPACE_ROOT / "threads" / <workspace-key>

    The directory is created lazily when the thread workspace is first used.
    """
    workspace_key = create_thread_workspace_key(
        thread_id,
    )

    thread_workspace_root = (
        WORKSPACE_ROOT
        / "threads"
        / workspace_key
    ).resolve()

    thread_workspace_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    return thread_workspace_root


# =============================================================================
# Secure Workspace Path Resolution
# =============================================================================


def resolve_workspace_path(
    user_path: str,
) -> Path:
    """
    Resolve an untrusted user-provided path inside the active workspace.

    When a thread workspace is bound to the current execution context, paths
    resolve inside that workspace. Otherwise, paths resolve inside the
    configured WORKSPACE_ROOT.

    The function guarantees that the returned path remains inside the active
    workspace security boundary after canonical path resolution.

    Args:
        user_path:
            Relative path requested by the user or LLM.

    Returns:
        Canonical absolute Path inside the active workspace.

    Raises:
        PathSecurityError:
            If the path is absolute or resolves outside the active workspace.
    """
    requested_path = Path(user_path)

    if requested_path.is_absolute():
        raise PathSecurityError(
            "Absolute paths are not allowed."
        )

    workspace_root = get_workspace_root()

    resolved_path = (
        workspace_root
        / requested_path
    ).resolve()

    try:
        resolved_path.relative_to(
            workspace_root,
        )

    except ValueError as exc:
        raise PathSecurityError(
            "Requested path escapes the allowed workspace."
        ) from exc

    return resolved_path