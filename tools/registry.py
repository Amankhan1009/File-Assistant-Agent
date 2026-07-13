# =============================================================================
# Third-Party Imports
# =============================================================================


from langchain_core.tools import BaseTool


# =============================================================================
# Tool Imports
# =============================================================================


from tools.directory_tools import (
    create_directory,
    delete_directory,
    list_directory,
)

from tools.read_tools import read_file

from tools.write_tools import (
    append_file,
    create_file,
)

from tools.search_tools import (
    search_files,
    search_text,
)

from tools.metadata_tools import get_file_metadata

from tools.delete_tools import delete_file

from tools.move_tools import move_path

from tools.archive_tools import compress_paths, extract_archive


# =============================================================================
# Tool Registry
# =============================================================================


TOOLS: list[BaseTool] = [
    list_directory,
    create_directory,
    delete_directory,
    read_file,
    create_file,
    append_file,
    search_files,
    search_text,
    get_file_metadata,
    delete_file,
    move_path,
    compress_paths,
    extract_archive,
]


# =============================================================================
# Tool Lookup Table
# =============================================================================


TOOL_BY_NAME: dict[str, BaseTool] = {
    tool.name: tool
    for tool in TOOLS
}


# =============================================================================
# Registry Access Functions
# =============================================================================


def get_tools() -> list[BaseTool]:
    """Return a copy of the tools currently exposed to the agent."""
    return TOOLS.copy()


def get_tool_by_name(name: str) -> BaseTool | None:
    """Return a registered tool by name, or None if it is not registered."""
    return TOOL_BY_NAME.get(name)