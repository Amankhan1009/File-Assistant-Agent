from typing import Any

from langchain_core.tools import tool

from core.paths import PathSecurityError, resolve_workspace_path
from tools.common import (
    MAX_MATCH_LINE_CHARS,
    MAX_READ_BYTES,
    MAX_SEARCH_RESULTS,
    error_result,
)
from tools.schemas import SearchFilesInput, SearchTextInput


# =============================================================================
# File Name Search Tools
# =============================================================================


@tool(args_schema=SearchFilesInput)
def search_files(query: str, path: str = ".") -> dict[str, Any]:
    """Recursively search for regular files by name inside the workspace."""
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

        workspace_root = resolve_workspace_path(".")
        normalized_query = query.casefold()

        matches: list[str] = []
        truncated = False

        for candidate in directory_path.rglob("*"):
            if not candidate.is_file():
                continue

            if normalized_query not in candidate.name.casefold():
                continue

            relative_path = candidate.relative_to(workspace_root)

            if len(matches) >= MAX_SEARCH_RESULTS:
                truncated = True
                break

            matches.append(relative_path.as_posix())

        matches.sort()

        return {
            "ok": True,
            "path": path,
            "query": query,
            "matches": matches,
            "count": len(matches),
            "truncated": truncated,
        }

    except PathSecurityError as exc:
        return error_result(
            "path_security_error",
            str(exc),
        )

    except OSError:
        return error_result(
            "filesystem_error",
            "Unable to search for files.",
        )


# =============================================================================
# File Content Search Tools
# =============================================================================


@tool(args_schema=SearchTextInput)
def search_text(query: str, path: str = ".") -> dict[str, Any]:
    """Recursively search for literal text inside UTF-8 files in the workspace."""
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

        workspace_root = resolve_workspace_path(".")
        normalized_query = query.casefold()

        matches: list[dict[str, Any]] = []
        truncated = False

        for candidate in directory_path.rglob("*"):
            if not candidate.is_file():
                continue

            try:
                file_size = candidate.stat().st_size
            except OSError:
                continue

            if file_size > MAX_READ_BYTES:
                continue

            try:
                content = candidate.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue

            for line_number, line in enumerate(
                content.splitlines(),
                start=1,
            ):
                if normalized_query not in line.casefold():
                    continue

                if len(matches) >= MAX_SEARCH_RESULTS:
                    truncated = True
                    break

                relative_path = candidate.relative_to(workspace_root)

                matches.append(
                    {
                        "path": relative_path.as_posix(),
                        "line_number": line_number,
                        "line": line[:MAX_MATCH_LINE_CHARS],
                    }
                )

            if truncated:
                break

        return {
            "ok": True,
            "path": path,
            "query": query,
            "matches": matches,
            "count": len(matches),
            "truncated": truncated,
        }

    except PathSecurityError as exc:
        return error_result(
            "path_security_error",
            str(exc),
        )

    except OSError:
        return error_result(
            "filesystem_error",
            "Unable to search file contents.",
        )