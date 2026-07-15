# =============================================================================
# Standard Library Imports
# =============================================================================


from pathlib import Path


# =============================================================================
# File Preview
# =============================================================================


def get_file_preview(
    file_path: Path,
) -> str:
    """
    Return the text contents of a file for preview.

    Binary files or unreadable files return a friendly message instead.
    """

    try:

        return file_path.read_text(
            encoding="utf-8",
        )

    except UnicodeDecodeError:

        return (
            "This file cannot be previewed because it is "
            "not a UTF-8 text file."
        )

    except Exception as exc:

        return (
            "Unable to preview file.\n\n"
            f"{exc}"
        )