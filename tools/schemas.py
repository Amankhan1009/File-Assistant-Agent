from pydantic import BaseModel, Field


# =============================================================================
# Directory Tool Schemas
# =============================================================================


class ListDirectoryInput(BaseModel):
    """Input schema for the list_directory tool."""

    path: str = Field(
        default=".",
        description=(
            "Relative path of the directory to list inside the allowed workspace. "
            "Use '.' to list the workspace root."
        ),
    )


# =============================================================================
# File Read Tool Schemas
# =============================================================================


class ReadFileInput(BaseModel):
    """Input schema for the read_file tool."""

    path: str = Field(
        ...,
        min_length=1,
        description=(
            "Relative path of the text file to read inside the allowed workspace."
        ),
    )


# =============================================================================
# File Write Tool Schemas
# =============================================================================


class CreateFileInput(BaseModel):
    """Input schema for the create_file tool."""

    path: str = Field(
        ...,
        min_length=1,
        description=(
            "Relative path of the new text file to create inside the allowed workspace."
        ),
    )

    content: str = Field(
        ...,
        description="UTF-8 text content to write to the new file.",
    )


class AppendFileInput(BaseModel):
    """Input schema for the append_file tool."""

    path: str = Field(
        ...,
        min_length=1,
        description=(
            "Relative path of the existing text file to append inside the allowed workspace."
        ),
    )

    content: str = Field(
        ...,
        description="UTF-8 text content to append to the existing file.",
    )


# =============================================================================
# File Search Tool Schemas
# =============================================================================


class SearchFilesInput(BaseModel):
    """Input schema for the search_files tool."""

    query: str = Field(
        ...,
        min_length=1,
        description="Case-insensitive text to search for in file names.",
    )

    path: str = Field(
        default=".",
        description=(
            "Relative directory path inside the allowed workspace "
            "from which the recursive search should begin."
        ),
    )


class SearchTextInput(BaseModel):
    """Input schema for the search_text tool."""

    query: str = Field(
        ...,
        min_length=1,
        description=(
            "Case-insensitive literal text to search for inside UTF-8 text files."
        ),
    )

    path: str = Field(
        default=".",
        description=(
            "Relative directory path inside the allowed workspace "
            "from which the recursive content search should begin."
        ),
    )

# =============================================================================
# File Metadata Tool Schemas
# =============================================================================


class GetFileMetadataInput(BaseModel):
    """Input schema for the get_file_metadata tool."""

    path: str = Field(
        ...,
        min_length=1,
        description=(
            "Relative path of the file or directory whose metadata "
            "should be retrieved inside the allowed workspace."
        ),
    )


# =============================================================================
# Delete File Tool Schema
# =============================================================================


class DeleteFileInput(BaseModel):
    """Input schema for the delete_file tool."""

    path: str = Field(
        ...,
        min_length=1,
        description=(
            "Relative path of the existing regular file to delete "
            "inside the allowed workspace."
        ),
    )


# =============================================================================
# Create Directory Tool Schema
# =============================================================================


class CreateDirectoryInput(BaseModel):
    """Input schema for the create_directory tool."""

    path: str = Field(
        ...,
        min_length=1,
        description=(
            "Relative path of the new directory to create "
            "inside the allowed workspace."
        ),
    )


# =============================================================================
# Delete Directory Tool Schema
# =============================================================================


class DeleteDirectoryInput(BaseModel):
    """Input schema for the delete_directory tool."""

    path: str = Field(
        ...,
        min_length=1,
        description=(
            "Relative path of the existing empty directory to delete "
            "inside the allowed workspace."
        ),
    )


# =============================================================================
# Move Path Tool Schema
# =============================================================================


class MovePathInput(BaseModel):
    """Input schema for the move_path tool."""

    source: str = Field(
        ...,
        min_length=1,
        description=(
            "Relative path of the existing file or directory to move "
            "inside the allowed workspace."
        ),
    )

    destination: str = Field(
        ...,
        min_length=1,
        description=(
            "Relative destination path inside the allowed workspace. "
            "The destination must not already exist."
        ),
    )


# =============================================================================
# Compress Paths Tool Schema
# =============================================================================


class CompressPathsInput(BaseModel):
    """Input schema for the compress_paths tool."""

    paths: list[str] = Field(
        ...,
        min_length=1,
        description=(
            "Relative paths of one or more existing files or directories "
            "inside the allowed workspace to include in the ZIP archive."
        ),
    )

    destination: str = Field(
        ...,
        min_length=1,
        description=(
            "Relative path of the new ZIP archive to create inside the "
            "allowed workspace. The destination must not already exist."
        ),
    )

# =============================================================================
# Extract Archive Input Schema
# =============================================================================


class ExtractArchiveInput(BaseModel):
    """Input schema for the extract_archive tool."""

    archive: str = Field(
        ...,
        min_length=1,
        description=(
            "Relative path of the existing ZIP archive to extract "
            "inside the allowed workspace."
        ),
    )

    destination: str = Field(
        ...,
        min_length=1,
        description=(
            "Relative path of the existing empty destination directory "
            "inside the allowed workspace."
        ),
    )