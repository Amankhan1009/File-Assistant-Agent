# =============================================================================
# Project Imports
# =============================================================================


from frontend.api_client import (
    get_file_preview as get_file_preview_from_api,
)


# =============================================================================
# File Preview
# =============================================================================


def get_file_preview(
    thread_id: str,
    relative_path: str,
) -> str:
    """
    Retrieve the file preview from the backend API.
    """

    return get_file_preview_from_api(
        thread_id,
        relative_path,
    )