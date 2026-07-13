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
