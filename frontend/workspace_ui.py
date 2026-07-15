# =============================================================================
# Third-Party Imports
# =============================================================================


import streamlit as st


# =============================================================================
# Workspace Tree Rendering
# =============================================================================


def render_workspace_tree(
    items: list[dict],
) -> None:
    """
    Recursively render the workspace tree.

    Directories are rendered as expandable sections.

    Files are rendered as clickable buttons.
    """

    for item in items:

        # -------------------------------------------------------------
        # Directory
        # -------------------------------------------------------------

        if item["is_directory"]:

            with st.expander(
                f"📁 {item['name']}",
                expanded=False,
            ):

                render_workspace_tree(
                    item.get(
                        "children",
                        [],
                    )
                )

        # -------------------------------------------------------------
        # File
        # -------------------------------------------------------------

        else:

            if st.button(
                f"📄 {item['name']}",
                key=str(item["relative_path"]),
                use_container_width=True,
            ):

                st.session_state.selected_file = {
                    "name": item["name"],
                    "relative_path": item["relative_path"],
                }