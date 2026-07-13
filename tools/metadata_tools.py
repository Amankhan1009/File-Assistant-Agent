from datetime import datetime, timezone
from typing import Any

from langchain_core.tools import tool

from core.paths import PathSecurityError, resolve_workspace_path
from tools.common import error_result
from tools.schemas import GetFileMetadataInput


# =============================================================================
# File Metadata Tools
# =============================================================================


@tool(args_schema=GetFileMetadataInput)
def get_file_metadata(path: str) -> dict[str, Any]:
    """Return safe metadata for a file or directory inside the workspace."""
    try:
        target_path = resolve_workspace_path(path)

        if not target_path.exists():
            return error_result(
                "not_found",
                f"Path does not exist: {path}",
            )

        stat_result = target_path.stat()

        return {
            "ok": True,
            "path": path,
            "type": "directory" if target_path.is_dir() else "file",
            "size_bytes": stat_result.st_size,
            "modified_at": datetime.fromtimestamp(
                stat_result.st_mtime,
                tz=timezone.utc,
            ).isoformat(),
        }

    except PathSecurityError as exc:
        return error_result(
            "path_security_error",
            str(exc),
        )

    except OSError:
        return error_result(
            "filesystem_error",
            "Unable to retrieve metadata for the requested path.",
        )