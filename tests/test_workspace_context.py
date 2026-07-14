# =============================================================================
# Standard Library Imports
# =============================================================================


from pathlib import Path


# =============================================================================
# Project Imports
# =============================================================================


from core.workspace_context import (
    bind_workspace_root,
    create_thread_workspace_key,
    get_active_workspace_root,
)


# =============================================================================
# Thread Workspace Identity Tests
# =============================================================================


def test_create_thread_workspace_key_is_deterministic():
    """
    Verify that the same thread ID always produces the same workspace key.
    """
    first_key = create_thread_workspace_key(
        "thread-123",
    )

    second_key = create_thread_workspace_key(
        "thread-123",
    )

    assert first_key == second_key


def test_create_thread_workspace_key_separates_threads():
    """
    Verify that different thread IDs produce different workspace keys.
    """
    first_key = create_thread_workspace_key(
        "thread-123",
    )

    second_key = create_thread_workspace_key(
        "thread-456",
    )

    assert first_key != second_key


def test_create_thread_workspace_key_is_filesystem_safe():
    """
    Verify that unsafe raw thread ID characters are not exposed in the
    generated workspace key.
    """
    workspace_key = create_thread_workspace_key(
        "../../another-user/thread?id=secret",
    )

    assert len(workspace_key) == 64
    assert workspace_key.isalnum()

    assert "/" not in workspace_key
    assert "." not in workspace_key
    assert "?" not in workspace_key


def test_create_thread_workspace_key_rejects_empty_thread_id():
    """
    Verify that empty thread IDs cannot create workspace identities.
    """
    try:
        create_thread_workspace_key(
            "   ",
        )

    except ValueError as exc:
        assert str(exc) == "Thread ID cannot be empty."

    else:
        raise AssertionError(
            "Expected ValueError for empty thread ID."
        )


# =============================================================================
# Active Workspace Access Tests
# =============================================================================


def test_active_workspace_root_is_unbound_by_default():
    """
    Verify that no execution workspace is active outside a binding context.
    """
    assert get_active_workspace_root() is None


# =============================================================================
# Workspace Context Binding Tests
# =============================================================================


def test_bind_workspace_root_sets_and_restores_context(
    tmp_path: Path,
):
    """
    Verify that workspace binding is active only inside the context manager.
    """
    workspace_root = tmp_path / "workspace"

    assert get_active_workspace_root() is None

    with bind_workspace_root(
        workspace_root,
    ) as active_workspace_root:
        assert active_workspace_root == workspace_root.resolve()

        assert (
            get_active_workspace_root()
            == workspace_root.resolve()
        )

    assert get_active_workspace_root() is None


def test_bind_workspace_root_restores_nested_context(
    tmp_path: Path,
):
    """
    Verify that nested workspace bindings restore the previous workspace.
    """
    outer_workspace = tmp_path / "outer"
    inner_workspace = tmp_path / "inner"

    with bind_workspace_root(
        outer_workspace,
    ):
        assert (
            get_active_workspace_root()
            == outer_workspace.resolve()
        )

        with bind_workspace_root(
            inner_workspace,
        ):
            assert (
                get_active_workspace_root()
                == inner_workspace.resolve()
            )

        assert (
            get_active_workspace_root()
            == outer_workspace.resolve()
        )

    assert get_active_workspace_root() is None