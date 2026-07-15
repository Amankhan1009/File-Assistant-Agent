# =============================================================================
# Project Imports
# =============================================================================


from frontend.api_client import (
    get_workspace,
)


# =============================================================================
# Workspace Listing
# =============================================================================


def list_workspace_items(
    thread_id: str,
) -> list[dict]:
    """
    Return the workspace tree for the active conversation by querying
    the backend API.
    """

    return get_workspace(
        thread_id,
    )