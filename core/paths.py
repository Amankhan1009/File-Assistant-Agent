from pathlib import Path

from core.config import WORKSPACE_ROOT


class PathSecurityError(ValueError):
    """Raised when a requested path violates the workspace security boundary."""


def resolve_workspace_path(user_path: str) -> Path:
    """
    Resolve an untrusted user-provided path inside the configured workspace.

    The function guarantees that the returned path remains inside
    WORKSPACE_ROOT after canonical path resolution.

    Args:
        user_path: Relative path requested by the user or LLM.

    Returns:
        Canonical absolute Path inside WORKSPACE_ROOT.

    Raises:
        PathSecurityError:
            If the path is absolute or resolves outside WORKSPACE_ROOT.
    """
    requested_path = Path(user_path)

    if requested_path.is_absolute():
        raise PathSecurityError(
            "Absolute paths are not allowed."
        )

    resolved_path = (WORKSPACE_ROOT / requested_path).resolve()

    try:
        resolved_path.relative_to(WORKSPACE_ROOT)
    except ValueError as exc:
        raise PathSecurityError(
            "Requested path escapes the allowed workspace."
        ) from exc

    return resolved_path