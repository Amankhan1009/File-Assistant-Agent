from typing import Any

from langchain_core.tools import tool

from core.paths import PathSecurityError, resolve_workspace_path
from tools.common import MAX_WRITE_BYTES, error_result
from tools.schemas import CreateFileInput

from tools.schemas import AppendFileInput, CreateFileInput


@tool(args_schema=CreateFileInput)
def create_file(path: str, content: str) -> dict[str, Any]:
    """Create a new UTF-8 text file without overwriting an existing path."""
    try:
        file_path = resolve_workspace_path(path)

        if file_path.exists():
            return error_result("already_exists", f"Path already exists: {path}")

        parent_path = file_path.parent

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

        content_bytes = content.encode("utf-8")

        if len(content_bytes) > MAX_WRITE_BYTES:
            return error_result(
                "content_too_large",
                f"Content exceeds the maximum writable size of {MAX_WRITE_BYTES} bytes.",
            )

        with file_path.open("x", encoding="utf-8") as file:
            file.write(content)

        return {
            "ok": True,
            "path": path,
            "size_bytes": len(content_bytes),
        }

    except PathSecurityError as exc:
        return error_result("path_security_error", str(exc))

    except FileExistsError:
        return error_result("already_exists", f"Path already exists: {path}")

    except OSError:
        return error_result(
            "filesystem_error",
            "Unable to create the requested file.",
        )
    
## Append file
@tool(args_schema=AppendFileInput)
def append_file(path: str, content: str) -> dict[str, Any]:
    """Append UTF-8 text to an existing regular file inside the workspace."""
    try:
        file_path = resolve_workspace_path(path)

        if not file_path.exists():
            return error_result(
                "not_found",
                f"File does not exist: {path}",
            )

        if not file_path.is_file():
            return error_result(
                "not_a_file",
                f"Path is not a file: {path}",
            )

        current_size = file_path.stat().st_size

        if current_size > MAX_WRITE_BYTES:
            return error_result(
                "file_too_large",
                f"Existing file exceeds the maximum writable size of {MAX_WRITE_BYTES} bytes.",
            )

        try:
            file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return error_result(
                "unsupported_encoding",
                "File is not valid UTF-8 text.",
            )

        content_bytes = content.encode("utf-8")
        resulting_size = current_size + len(content_bytes)

        if resulting_size > MAX_WRITE_BYTES:
            return error_result(
                "content_too_large",
                f"Appending content would exceed the maximum writable size of {MAX_WRITE_BYTES} bytes.",
            )

        with file_path.open("a", encoding="utf-8") as file:
            file.write(content)

        return {
            "ok": True,
            "path": path,
            "appended_bytes": len(content_bytes),
            "size_bytes": resulting_size,
        }

    except PathSecurityError as exc:
        return error_result("path_security_error", str(exc))

    except OSError:
        return error_result(
            "filesystem_error",
            "Unable to append to the requested file.",
        )