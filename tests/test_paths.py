from pathlib import Path

import pytest

from core.config import WORKSPACE_ROOT
from core.paths import (
    PathSecurityError,
    resolve_workspace_path,
)


# =============================================================================
# Valid Workspace Path Resolution
# =============================================================================


def test_resolve_workspace_path_returns_workspace_root_for_dot():
    resolved_path = resolve_workspace_path(".")

    assert resolved_path == WORKSPACE_ROOT.resolve()
    assert resolved_path.is_absolute()


def test_resolve_workspace_path_resolves_relative_file_path():
    resolved_path = resolve_workspace_path("notes.txt")

    assert resolved_path == (
        WORKSPACE_ROOT
        / "notes.txt"
    ).resolve()

    assert resolved_path.is_absolute()


def test_resolve_workspace_path_resolves_nested_relative_path():
    resolved_path = resolve_workspace_path(
        "docs/nested/example.txt"
    )

    assert resolved_path == (
        WORKSPACE_ROOT
        / "docs"
        / "nested"
        / "example.txt"
    ).resolve()

    assert resolved_path.is_absolute()


def test_resolve_workspace_path_returns_path_instance():
    resolved_path = resolve_workspace_path(
        "example.txt"
    )

    assert isinstance(
        resolved_path,
        Path,
    )


# =============================================================================
# Absolute Path Rejection
# =============================================================================


def test_resolve_workspace_path_rejects_absolute_path():
    with pytest.raises(
        PathSecurityError,
        match="Absolute paths are not allowed",
    ):
        resolve_workspace_path(
            "/tmp/unsafe.txt"
        )


# =============================================================================
# Workspace Escape Rejection
# =============================================================================


def test_resolve_workspace_path_rejects_parent_traversal():
    with pytest.raises(
        PathSecurityError,
        match="Requested path escapes the allowed workspace",
    ):
        resolve_workspace_path(
            "../unsafe.txt"
        )


def test_resolve_workspace_path_rejects_nested_parent_traversal():
    with pytest.raises(
        PathSecurityError,
        match="Requested path escapes the allowed workspace",
    ):
        resolve_workspace_path(
            "docs/../../../unsafe.txt"
        )


# =============================================================================
# Canonical Path Resolution
# =============================================================================


def test_resolve_workspace_path_normalizes_internal_parent_segments():
    resolved_path = resolve_workspace_path(
        "docs/nested/../example.txt"
    )

    expected_path = (
        WORKSPACE_ROOT
        / "docs"
        / "example.txt"
    ).resolve()

    assert resolved_path == expected_path


def test_resolve_workspace_path_normalizes_current_directory_segments():
    resolved_path = resolve_workspace_path(
        "./docs/./example.txt"
    )

    expected_path = (
        WORKSPACE_ROOT
        / "docs"
        / "example.txt"
    ).resolve()

    assert resolved_path == expected_path


# =============================================================================
# Active Workspace Resolution
# =============================================================================


def test_resolve_workspace_path_uses_bound_workspace(
    tmp_path: Path,
):
    """
    Verify that path resolution uses the active execution workspace when one
    is bound to the current context.
    """
    from core.workspace_context import bind_workspace_root

    thread_workspace = tmp_path / "thread-workspace"

    with bind_workspace_root(
        thread_workspace,
    ):
        resolved_path = resolve_workspace_path(
            "notes.txt",
        )

    assert resolved_path == (
        thread_workspace
        / "notes.txt"
    ).resolve()


def test_resolve_workspace_path_returns_bound_workspace_for_dot(
    tmp_path: Path,
):
    """
    Verify that resolving the workspace root returns the active execution
    workspace while a workspace binding is active.
    """
    from core.workspace_context import bind_workspace_root

    thread_workspace = tmp_path / "thread-workspace"

    with bind_workspace_root(
        thread_workspace,
    ):
        resolved_path = resolve_workspace_path(
            ".",
        )

    assert resolved_path == thread_workspace.resolve()


# =============================================================================
# Bound Workspace Security Tests
# =============================================================================


def test_resolve_workspace_path_rejects_escape_from_bound_workspace(
    tmp_path: Path,
):
    """
    Verify that parent traversal cannot escape an active execution workspace.
    """
    from core.workspace_context import bind_workspace_root

    thread_workspace = tmp_path / "thread-workspace"

    with bind_workspace_root(
        thread_workspace,
    ):
        with pytest.raises(
            PathSecurityError,
            match="Requested path escapes the allowed workspace",
        ):
            resolve_workspace_path(
                "../unsafe.txt"
            )


def test_resolve_workspace_path_rejects_nested_escape_from_bound_workspace(
    tmp_path: Path,
):
    """
    Verify that nested parent traversal cannot escape an active execution
    workspace.
    """
    from core.workspace_context import bind_workspace_root

    thread_workspace = tmp_path / "thread-workspace"

    with bind_workspace_root(
        thread_workspace,
    ):
        with pytest.raises(
            PathSecurityError,
            match="Requested path escapes the allowed workspace",
        ):
            resolve_workspace_path(
                "docs/../../../unsafe.txt"
            )


# =============================================================================
# Workspace Context Restoration Tests
# =============================================================================


def test_resolve_workspace_path_restores_default_workspace_after_binding(
    tmp_path: Path,
):
    """
    Verify that leaving a workspace binding restores default path resolution.
    """
    from core.workspace_context import bind_workspace_root

    thread_workspace = tmp_path / "thread-workspace"

    with bind_workspace_root(
        thread_workspace,
    ):
        assert resolve_workspace_path(
            "notes.txt",
        ) == (
            thread_workspace
            / "notes.txt"
        ).resolve()

    assert resolve_workspace_path(
        "notes.txt",
    ) == (
        WORKSPACE_ROOT
        / "notes.txt"
    ).resolve()


def test_resolve_workspace_path_supports_nested_workspace_bindings(
    tmp_path: Path,
):
    """
    Verify that nested workspace bindings resolve paths against the currently
    active workspace and restore the previous binding afterward.
    """
    from core.workspace_context import bind_workspace_root

    outer_workspace = tmp_path / "outer"
    inner_workspace = tmp_path / "inner"

    with bind_workspace_root(
        outer_workspace,
    ):
        assert resolve_workspace_path(
            "notes.txt",
        ) == (
            outer_workspace
            / "notes.txt"
        ).resolve()

        with bind_workspace_root(
            inner_workspace,
        ):
            assert resolve_workspace_path(
                "notes.txt",
            ) == (
                inner_workspace
                / "notes.txt"
            ).resolve()

        assert resolve_workspace_path(
            "notes.txt",
        ) == (
            outer_workspace
            / "notes.txt"
        ).resolve()
