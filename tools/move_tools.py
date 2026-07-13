# =============================================================================
# Imports
# =============================================================================


from typing import Any

from langchain_core.tools import tool

from core.paths import PathSecurityError, resolve_workspace_path
from tools.common import error_result
from tools.schemas import MovePathInput


# =============================================================================
# Move Path Tool
# =============================================================================


@tool(args_schema=MovePathInput)
def move_path(source: str, destination: str) -> dict[str, Any]:
    """
    Move or rename an existing file or directory inside the allowed workspace.

    The destination parent directory must already exist. Existing destination
    paths are never overwritten, and the workspace root cannot be moved.
    """
    try:
        # =====================================================================
        # Resolve and Validate Workspace Paths
        # =====================================================================

        source_path = resolve_workspace_path(source)
        destination_path = resolve_workspace_path(destination)
        workspace_root = resolve_workspace_path(".")

        # =====================================================================
        # Validate Source Path
        # =====================================================================

        if source_path == workspace_root:
            return error_result(
                "protected_path",
                "The workspace root cannot be moved.",
            )

        if not source_path.exists():
            return error_result(
                "not_found",
                f"Source path does not exist: {source}",
            )

        # =====================================================================
        # Prevent Destination Overwrite
        # =====================================================================

        if destination_path.exists():
            return error_result(
                "already_exists",
                f"Destination path already exists: {destination}",
            )

        # =============================================================================
        # Prevent Moving a Directory Inside Itself
        # =============================================================================


        if source_path.is_dir() and destination_path.is_relative_to(source_path):
            return error_result(
                "invalid_destination",
                "A directory cannot be moved inside itself.",
            )

        # =====================================================================
        # Validate Destination Parent Directory
        # =====================================================================

        destination_parent = destination_path.parent

        if not destination_parent.exists():
            return error_result(
                "parent_not_found",
                f"Destination parent directory does not exist: {destination}",
            )

        if not destination_parent.is_dir():
            return error_result(
                "parent_not_directory",
                f"Destination parent path is not a directory: {destination}",
            )

        # =====================================================================
        # Move or Rename Path
        # =====================================================================

        source_type = "directory" if source_path.is_dir() else "file"

        source_path.rename(destination_path)

        # =====================================================================
        # Successful Result
        # =====================================================================

        return {
            "ok": True,
            "source": source,
            "destination": destination,
            "type": source_type,
            "moved": True,
        }

    # =========================================================================
    # Workspace Security Error Handling
    # =========================================================================

    except PathSecurityError as exc:
        return error_result(
            "path_security_error",
            str(exc),
        )

    # =========================================================================
    # Filesystem Error Handling
    # =========================================================================

    except OSError:
        return error_result(
            "filesystem_error",
            "Unable to move the requested path.",
        )