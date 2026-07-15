# =============================================================================
# Standard Library Imports
# =============================================================================


from pathlib import Path


# =============================================================================
# Project Imports
# =============================================================================


from core.paths import get_thread_workspace_root


# =============================================================================
# Workspace Tree Builder
# =============================================================================


def _build_tree(
    directory: Path,
) -> list[dict]:
    """
    Recursively build a tree representing the contents of a directory.

    Directories appear before files and both are sorted alphabetically.
    """

    items = []

    for path in sorted(
        directory.iterdir(),
        key=lambda entry: (
            not entry.is_dir(),
            entry.name.lower(),
        ),
    ):

        node = {
            "name": path.name,
            "path": path,
            "is_directory": path.is_dir(),
        }

        if path.is_dir():

            node["children"] = _build_tree(
                path,
            )

        items.append(
            node,
        )

    return items


# =============================================================================
# Workspace Listing
# =============================================================================


def list_workspace_items(
    thread_id: str,
) -> list[dict]:
    """
    Return the complete workspace tree for the active conversation.
    """

    workspace_root = get_thread_workspace_root(
        thread_id,
    )

    return _build_tree(
        workspace_root,
    )