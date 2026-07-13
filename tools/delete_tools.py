# =============================================================================
# Imports
# =============================================================================


from typing import Any

from langchain_core.tools import tool

from core.paths import PathSecurityError, resolve_workspace_path
from tools.common import error_result
from tools.schemas import DeleteFileInput


# =============================================================================
# Delete File Tool
# =============================================================================


@tool(args_schema=DeleteFileInput)
def delete_file(path: str) -> dict[str, Any]:
    """
    Delete an existing regular file inside the allowed workspace.

    Directories cannot be deleted by this tool.
    """
    try:
        file_path = resolve_workspace_path(path)

        # =====================================================================
        # Path Existence Validation
        # =====================================================================

        if not file_path.exists():
            return error_result(
                "not_found",
                f"File does not exist: {path}",
            )

        # =====================================================================
        # File Type Validation
        # =====================================================================

        if not file_path.is_file():
            return error_result(
                "not_a_file",
                f"Path is not a file: {path}",
            )

        # =====================================================================
        # File Deletion
        # =====================================================================

        file_path.unlink()

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

    except OSError:
        return error_result(
            "filesystem_error",
            "Unable to delete the requested file.",
        )