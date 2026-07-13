from typing import Any

from langchain_core.tools import tool

from core.paths import PathSecurityError, resolve_workspace_path
from tools.common import MAX_READ_BYTES, error_result
from tools.schemas import ReadFileInput


@tool(args_schema=ReadFileInput)
def read_file(path: str) -> dict[str, Any]:
    """Read a UTF-8 text file inside the allowed workspace."""
    try:
        file_path = resolve_workspace_path(path)

        if not file_path.exists():
            return error_result("not_found", f"File does not exist: {path}")

        if not file_path.is_file():
            return error_result("not_a_file", f"Path is not a file: {path}")

        file_size = file_path.stat().st_size

        if file_size > MAX_READ_BYTES:
            return error_result(
                "file_too_large",
                f"File exceeds the maximum readable size of {MAX_READ_BYTES} bytes.",
            )

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return error_result(
                "unsupported_encoding",
                "File is not valid UTF-8 text.",
            )

        return {
            "ok": True,
            "path": path,
            "content": content,
            "size_bytes": file_size,
        }

    except PathSecurityError as exc:
        return error_result("path_security_error", str(exc))

    except OSError:
        return error_result(
            "filesystem_error",
            "Unable to read the requested file.",
        )