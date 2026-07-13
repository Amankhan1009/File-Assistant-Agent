from typing import Any

from langchain_core.tools import tool

from core.paths import PathSecurityError, resolve_workspace_path
from tools.common import error_result
from tools.schemas import CreateDirectoryInput, ListDirectoryInput, DeleteDirectoryInput


@tool(args_schema=ListDirectoryInput)
def list_directory(path: str = ".") -> dict[str, Any]:
    """List the direct contents of a directory inside the allowed workspace."""
    try:
        directory_path = resolve_workspace_path(path)

        if not directory_path.exists():
            return error_result(
                "not_found",
                f"Directory does not exist: {path}",
            )

        if not directory_path.is_dir():
            return error_result(
                "not_a_directory",
                f"Path is not a directory: {path}",
            )

        entries = [
            {
                "name": entry.name,
                "type": "directory" if entry.is_dir() else "file",
            }
            for entry in sorted(
                directory_path.iterdir(),
                key=lambda item: item.name.lower(),
            )
        ]

        return {
            "ok": True,
            "path": path,
            "entries": entries,
            "count": len(entries),
        }

    except PathSecurityError as exc:
        return error_result("path_security_error", str(exc))

    except OSError:
        return error_result(
            "filesystem_error",
            "Unable to list the requested directory.",
        )
    

# =============================================================================
# Create Directory Tool
# =============================================================================


@tool(args_schema=CreateDirectoryInput)
def create_directory(path: str) -> dict[str, Any]:
    """
    Create a new directory inside the allowed workspace.

    The parent directory must already exist. Existing files and directories
    are never overwritten.
    """
    try:
        directory_path = resolve_workspace_path(path)

        # =====================================================================
        # Existing Path Validation
        # =====================================================================

        if directory_path.exists():
            return error_result(
                "already_exists",
                f"Path already exists: {path}",
            )

        # =====================================================================
        # Parent Path Validation
        # =====================================================================

        parent_path = directory_path.parent

        if not parent_path.exists():
            return error_result(
                "parent_not_found",
                f"Parent directory does not exist: {path}",
            )

        if not parent_path.is_dir():
            return error_result(
                "parent_not_directory",
                f"Parent path is not a directory: {path}",
            )

        # =====================================================================
        # Directory Creation
        # =====================================================================

        directory_path.mkdir()

        # =====================================================================
        # Success Result
        # =====================================================================

        return {
            "ok": True,
            "path": path,
            "created": True,
        }

    except PathSecurityError as exc:
        return error_result(
            "path_security_error",
            str(exc),
        )

    except FileExistsError:
        # Handles a race where the path appears after our exists() check.
        return error_result(
            "already_exists",
            f"Path already exists: {path}",
        )

    except OSError:
        return error_result(
            "filesystem_error",
            "Unable to create the requested directory.",
        )
    


# =============================================================================
# Delete Directory Tool
# =============================================================================


@tool(args_schema=DeleteDirectoryInput)
def delete_directory(path: str) -> dict[str, Any]:
    """
    Delete an existing empty directory inside the allowed workspace.

    Files, non-empty directories, and the workspace root cannot be deleted
    by this tool.
    """
    try:
        directory_path = resolve_workspace_path(path)
        workspace_root = resolve_workspace_path(".")

        # =====================================================================
        # Workspace Root Protection
        # =====================================================================

        if directory_path == workspace_root:
            return error_result(
                "protected_path",
                "The workspace root cannot be deleted.",
            )

        # =====================================================================
        # Path Existence Validation
        # =====================================================================

        if not directory_path.exists():
            return error_result(
                "not_found",
                f"Directory does not exist: {path}",
            )

        # =====================================================================
        # Directory Type Validation
        # =====================================================================

        if not directory_path.is_dir():
            return error_result(
                "not_a_directory",
                f"Path is not a directory: {path}",
            )

        # =====================================================================
        # Directory Deletion
        # =====================================================================

        directory_path.rmdir()

        # =====================================================================
        # Success Result
        # =====================================================================

        return {
            "ok": True,
            "path": path,
            "deleted": True,
        }

    except PathSecurityError as exc:
        return error_result(
            "path_security_error",
            str(exc),
        )

    except OSError as exc:
        # =====================================================================
        # Non-Empty Directory Handling
        # =====================================================================

        if directory_path.exists() and directory_path.is_dir():
            try:
                next(directory_path.iterdir())
            except StopIteration:
                pass
            except OSError:
                pass
            else:
                return error_result(
                    "directory_not_empty",
                    f"Directory is not empty: {path}",
                )

        return error_result(
            "filesystem_error",
            "Unable to delete the requested directory.",
        )