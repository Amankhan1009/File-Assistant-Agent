from datetime import datetime
from pathlib import Path

import pytest



import core.paths
from tools.directory_tools import create_directory, list_directory
from tools.metadata_tools import get_file_metadata
from tools.read_tools import read_file
from tools.write_tools import append_file, create_file
from tools.common import MAX_WRITE_BYTES


# =============================================================================
# Isolated Workspace Fixture
# =============================================================================


@pytest.fixture
def isolated_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """
    Replace the configured workspace root with an isolated temporary directory.

    This prevents automated tool tests from reading or modifying the real
    application workspace.
    """
    workspace = tmp_path / "workspace"

    workspace.mkdir()

    monkeypatch.setattr(
        core.paths,
        "WORKSPACE_ROOT",
        workspace,
    )

    return workspace


# =============================================================================
# list_directory Tests
# =============================================================================


def test_list_directory_lists_sorted_direct_entries(
    isolated_workspace: Path,
):
    (isolated_workspace / "beta.txt").write_text(
        "Beta content",
        encoding="utf-8",
    )

    (isolated_workspace / "Alpha.txt").write_text(
        "Alpha content",
        encoding="utf-8",
    )

    (isolated_workspace / "docs").mkdir()

    result = list_directory.invoke(
        {
            "path": ".",
        }
    )

    assert result == {
        "ok": True,
        "path": ".",
        "entries": [
            {
                "name": "Alpha.txt",
                "type": "file",
            },
            {
                "name": "beta.txt",
                "type": "file",
            },
            {
                "name": "docs",
                "type": "directory",
            },
        ],
        "count": 3,
    }


def test_list_directory_returns_not_found_for_missing_directory(
    isolated_workspace: Path,
):
    result = list_directory.invoke(
        {
            "path": "missing",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "not_found"


def test_list_directory_rejects_file_path(
    isolated_workspace: Path,
):
    (isolated_workspace / "notes.txt").write_text(
        "Notes",
        encoding="utf-8",
    )

    result = list_directory.invoke(
        {
            "path": "notes.txt",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "not_a_directory"


def test_list_directory_rejects_workspace_escape(
    isolated_workspace: Path,
):
    result = list_directory.invoke(
        {
            "path": "../outside",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "path_security_error"


# =============================================================================
# read_file Tests
# =============================================================================


def test_read_file_returns_utf8_file_content(
    isolated_workspace: Path,
):
    content = "LangGraph tool testing"

    (isolated_workspace / "notes.txt").write_text(
        content,
        encoding="utf-8",
    )

    result = read_file.invoke(
        {
            "path": "notes.txt",
        }
    )

    assert result == {
        "ok": True,
        "path": "notes.txt",
        "content": content,
        "size_bytes": len(
            content.encode("utf-8")
        ),
    }


def test_read_file_returns_not_found_for_missing_file(
    isolated_workspace: Path,
):
    result = read_file.invoke(
        {
            "path": "missing.txt",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "not_found"


def test_read_file_rejects_directory_path(
    isolated_workspace: Path,
):
    (isolated_workspace / "docs").mkdir()

    result = read_file.invoke(
        {
            "path": "docs",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "not_a_file"


def test_read_file_rejects_non_utf8_content(
    isolated_workspace: Path,
):
    (isolated_workspace / "binary.bin").write_bytes(
        b"\xff\xfe\xfa"
    )

    result = read_file.invoke(
        {
            "path": "binary.bin",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "unsupported_encoding"


def test_read_file_rejects_workspace_escape(
    isolated_workspace: Path,
):
    result = read_file.invoke(
        {
            "path": "../outside.txt",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "path_security_error"


# =============================================================================
# get_file_metadata Tests
# =============================================================================


def test_get_file_metadata_returns_file_metadata(
    isolated_workspace: Path,
):
    content = "Metadata test"

    (isolated_workspace / "metadata.txt").write_text(
        content,
        encoding="utf-8",
    )

    result = get_file_metadata.invoke(
        {
            "path": "metadata.txt",
        }
    )

    assert result["ok"] is True
    assert result["path"] == "metadata.txt"
    assert result["type"] == "file"

    assert result["size_bytes"] == len(
        content.encode("utf-8")
    )

    datetime.fromisoformat(
        result["modified_at"]
    )


def test_get_file_metadata_returns_directory_metadata(
    isolated_workspace: Path,
):
    (isolated_workspace / "docs").mkdir()

    result = get_file_metadata.invoke(
        {
            "path": "docs",
        }
    )

    assert result["ok"] is True
    assert result["path"] == "docs"
    assert result["type"] == "directory"

    datetime.fromisoformat(
        result["modified_at"]
    )


def test_get_file_metadata_returns_not_found_for_missing_path(
    isolated_workspace: Path,
):
    result = get_file_metadata.invoke(
        {
            "path": "missing.txt",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "not_found"


def test_get_file_metadata_rejects_workspace_escape(
    isolated_workspace: Path,
):
    result = get_file_metadata.invoke(
        {
            "path": "../outside.txt",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "path_security_error"


# =============================================================================
# create_directory Tests
# =============================================================================


def test_create_directory_creates_new_directory(
    isolated_workspace: Path,
):
    result = create_directory.invoke(
        {
            "path": "new_directory",
        }
    )

    created_path = (
        isolated_workspace
        / "new_directory"
    )

    assert result == {
        "ok": True,
        "path": "new_directory",
        "created": True,
    }

    assert created_path.exists()
    assert created_path.is_dir()


def test_create_directory_creates_nested_directory_with_existing_parent(
    isolated_workspace: Path,
):
    parent_path = isolated_workspace / "parent"

    parent_path.mkdir()

    result = create_directory.invoke(
        {
            "path": "parent/child",
        }
    )

    assert result["ok"] is True

    assert (
        isolated_workspace
        / "parent"
        / "child"
    ).is_dir()


def test_create_directory_rejects_existing_directory(
    isolated_workspace: Path,
):
    existing_path = (
        isolated_workspace
        / "existing"
    )

    existing_path.mkdir()

    result = create_directory.invoke(
        {
            "path": "existing",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "already_exists"

    assert existing_path.is_dir()


def test_create_directory_rejects_existing_file(
    isolated_workspace: Path,
):
    existing_file = (
        isolated_workspace
        / "existing.txt"
    )

    existing_file.write_text(
        "Preserve this content",
        encoding="utf-8",
    )

    result = create_directory.invoke(
        {
            "path": "existing.txt",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "already_exists"

    assert existing_file.read_text(
        encoding="utf-8",
    ) == "Preserve this content"


def test_create_directory_rejects_missing_parent(
    isolated_workspace: Path,
):
    result = create_directory.invoke(
        {
            "path": "missing/child",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "parent_not_found"

    assert not (
        isolated_workspace
        / "missing"
        / "child"
    ).exists()


def test_create_directory_rejects_file_as_parent(
    isolated_workspace: Path,
):
    parent_file = (
        isolated_workspace
        / "parent.txt"
    )

    parent_file.write_text(
        "Parent file",
        encoding="utf-8",
    )

    result = create_directory.invoke(
        {
            "path": "parent.txt/child",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "parent_not_directory"

    assert parent_file.read_text(
        encoding="utf-8",
    ) == "Parent file"


def test_create_directory_rejects_workspace_escape(
    isolated_workspace: Path,
):
    result = create_directory.invoke(
        {
            "path": "../outside_directory",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "path_security_error"


# =============================================================================
# create_file Tests
# =============================================================================


def test_create_file_creates_utf8_text_file(
    isolated_workspace: Path,
):
    content = "Created by automated tests"

    result = create_file.invoke(
        {
            "path": "created.txt",
            "content": content,
        }
    )

    created_file = (
        isolated_workspace
        / "created.txt"
    )

    assert result == {
        "ok": True,
        "path": "created.txt",
        "size_bytes": len(
            content.encode("utf-8")
        ),
    }

    assert created_file.read_text(
        encoding="utf-8",
    ) == content


def test_create_file_creates_file_inside_existing_directory(
    isolated_workspace: Path,
):
    docs_directory = (
        isolated_workspace
        / "docs"
    )

    docs_directory.mkdir()

    result = create_file.invoke(
        {
            "path": "docs/nested.txt",
            "content": "Nested content",
        }
    )

    assert result["ok"] is True

    assert (
        docs_directory
        / "nested.txt"
    ).read_text(
        encoding="utf-8",
    ) == "Nested content"


def test_create_file_rejects_existing_file_without_overwriting(
    isolated_workspace: Path,
):
    existing_file = (
        isolated_workspace
        / "existing.txt"
    )

    existing_file.write_text(
        "Original content",
        encoding="utf-8",
    )

    result = create_file.invoke(
        {
            "path": "existing.txt",
            "content": "Replacement content",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "already_exists"

    assert existing_file.read_text(
        encoding="utf-8",
    ) == "Original content"


def test_create_file_rejects_existing_directory(
    isolated_workspace: Path,
):
    existing_directory = (
        isolated_workspace
        / "existing_directory"
    )

    existing_directory.mkdir()

    result = create_file.invoke(
        {
            "path": "existing_directory",
            "content": "Content",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "already_exists"

    assert existing_directory.is_dir()


def test_create_file_rejects_missing_parent(
    isolated_workspace: Path,
):
    result = create_file.invoke(
        {
            "path": "missing/file.txt",
            "content": "Content",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "parent_not_found"

    assert not (
        isolated_workspace
        / "missing"
        / "file.txt"
    ).exists()


def test_create_file_rejects_file_as_parent(
    isolated_workspace: Path,
):
    parent_file = (
        isolated_workspace
        / "parent.txt"
    )

    parent_file.write_text(
        "Parent content",
        encoding="utf-8",
    )

    result = create_file.invoke(
        {
            "path": "parent.txt/child.txt",
            "content": "Child content",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "parent_not_directory"

    assert parent_file.read_text(
        encoding="utf-8",
    ) == "Parent content"


def test_create_file_rejects_content_over_write_limit(
    isolated_workspace: Path,
):
    oversized_content = "a" * (
        MAX_WRITE_BYTES + 1
    )

    result = create_file.invoke(
        {
            "path": "large.txt",
            "content": oversized_content,
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "content_too_large"

    assert not (
        isolated_workspace
        / "large.txt"
    ).exists()


def test_create_file_uses_utf8_byte_size_for_write_limit(
    isolated_workspace: Path,
):
    oversized_content = "€" * (
        (MAX_WRITE_BYTES // 3) + 1
    )

    assert len(
        oversized_content.encode("utf-8")
    ) > MAX_WRITE_BYTES

    result = create_file.invoke(
        {
            "path": "large_unicode.txt",
            "content": oversized_content,
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "content_too_large"

    assert not (
        isolated_workspace
        / "large_unicode.txt"
    ).exists()


def test_create_file_rejects_workspace_escape(
    isolated_workspace: Path,
):
    result = create_file.invoke(
        {
            "path": "../outside.txt",
            "content": "Unsafe content",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "path_security_error"


# =============================================================================
# append_file Tests
# =============================================================================


def test_append_file_appends_utf8_text(
    isolated_workspace: Path,
):
    file_path = (
        isolated_workspace
        / "append.txt"
    )

    file_path.write_text(
        "Original",
        encoding="utf-8",
    )

    appended_content = " + Appended"

    result = append_file.invoke(
        {
            "path": "append.txt",
            "content": appended_content,
        }
    )

    expected_content = (
        "Original"
        + appended_content
    )

    assert result == {
        "ok": True,
        "path": "append.txt",
        "appended_bytes": len(
            appended_content.encode("utf-8")
        ),
        "size_bytes": len(
            expected_content.encode("utf-8")
        ),
    }

    assert file_path.read_text(
        encoding="utf-8",
    ) == expected_content


def test_append_file_returns_not_found_for_missing_file(
    isolated_workspace: Path,
):
    result = append_file.invoke(
        {
            "path": "missing.txt",
            "content": "Content",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "not_found"


def test_append_file_rejects_directory_path(
    isolated_workspace: Path,
):
    directory_path = (
        isolated_workspace
        / "docs"
    )

    directory_path.mkdir()

    result = append_file.invoke(
        {
            "path": "docs",
            "content": "Content",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "not_a_file"

    assert directory_path.is_dir()


def test_append_file_rejects_non_utf8_existing_file(
    isolated_workspace: Path,
):
    file_path = (
        isolated_workspace
        / "binary.bin"
    )

    original_content = b"\xff\xfe\xfa"

    file_path.write_bytes(
        original_content
    )

    result = append_file.invoke(
        {
            "path": "binary.bin",
            "content": "Text",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "unsupported_encoding"

    assert file_path.read_bytes() == original_content


def test_append_file_rejects_existing_file_over_write_limit(
    isolated_workspace: Path,
):
    file_path = (
        isolated_workspace
        / "large.txt"
    )

    file_path.write_bytes(
        b"a" * (
            MAX_WRITE_BYTES + 1
        )
    )

    original_size = file_path.stat().st_size

    result = append_file.invoke(
        {
            "path": "large.txt",
            "content": "x",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "file_too_large"

    assert file_path.stat().st_size == original_size


def test_append_file_rejects_result_over_write_limit_without_modification(
    isolated_workspace: Path,
):
    file_path = (
        isolated_workspace
        / "almost_full.txt"
    )

    original_content = "a" * MAX_WRITE_BYTES

    file_path.write_text(
        original_content,
        encoding="utf-8",
    )

    result = append_file.invoke(
        {
            "path": "almost_full.txt",
            "content": "x",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "content_too_large"

    assert file_path.read_text(
        encoding="utf-8",
    ) == original_content


def test_append_file_uses_utf8_byte_size_for_result_limit(
    isolated_workspace: Path,
):
    file_path = (
        isolated_workspace
        / "unicode_limit.txt"
    )

    original_content = "a" * (
        MAX_WRITE_BYTES - 2
    )

    file_path.write_text(
        original_content,
        encoding="utf-8",
    )

    result = append_file.invoke(
        {
            "path": "unicode_limit.txt",
            "content": "€",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "content_too_large"

    assert file_path.read_text(
        encoding="utf-8",
    ) == original_content


def test_append_file_rejects_workspace_escape(
    isolated_workspace: Path,
):
    result = append_file.invoke(
        {
            "path": "../outside.txt",
            "content": "Unsafe append",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "path_security_error"


# =============================================================================
# Delete File Tool Tests
# =============================================================================


from tools.delete_tools import delete_file
from tools.directory_tools import delete_directory
from tools.move_tools import move_path


def test_delete_file_deletes_existing_regular_file(
    isolated_workspace,
):
    file_path = isolated_workspace / "delete_me.txt"
    file_path.write_text(
        "delete this file",
        encoding="utf-8",
    )

    result = delete_file.invoke(
        {
            "path": "delete_me.txt",
        }
    )

    assert result == {
        "ok": True,
        "path": "delete_me.txt",
        "deleted": True,
    }

    assert not file_path.exists()


def test_delete_file_returns_not_found_for_missing_file(
    isolated_workspace,
):
    result = delete_file.invoke(
        {
            "path": "missing.txt",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "not_found"


def test_delete_file_rejects_directory_path(
    isolated_workspace,
):
    directory_path = isolated_workspace / "directory"
    directory_path.mkdir()

    result = delete_file.invoke(
        {
            "path": "directory",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "not_a_file"
    assert directory_path.exists()


def test_delete_file_rejects_workspace_escape(
    isolated_workspace,
):
    result = delete_file.invoke(
        {
            "path": "../unsafe.txt",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "path_security_error"


# =============================================================================
# Delete Directory Tool Tests
# =============================================================================


def test_delete_directory_deletes_existing_empty_directory(
    isolated_workspace,
):
    directory_path = isolated_workspace / "empty_directory"
    directory_path.mkdir()

    result = delete_directory.invoke(
        {
            "path": "empty_directory",
        }
    )

    assert result == {
        "ok": True,
        "path": "empty_directory",
        "deleted": True,
    }

    assert not directory_path.exists()


def test_delete_directory_returns_not_found_for_missing_directory(
    isolated_workspace,
):
    result = delete_directory.invoke(
        {
            "path": "missing_directory",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "not_found"


def test_delete_directory_rejects_file_path(
    isolated_workspace,
):
    file_path = isolated_workspace / "file.txt"
    file_path.write_text(
        "preserve this file",
        encoding="utf-8",
    )

    result = delete_directory.invoke(
        {
            "path": "file.txt",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "not_a_directory"
    assert file_path.exists()


def test_delete_directory_rejects_non_empty_directory_without_modification(
    isolated_workspace,
):
    directory_path = isolated_workspace / "non_empty"
    directory_path.mkdir()

    child_file = directory_path / "child.txt"
    child_file.write_text(
        "must survive",
        encoding="utf-8",
    )

    result = delete_directory.invoke(
        {
            "path": "non_empty",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "directory_not_empty"

    assert directory_path.exists()
    assert child_file.exists()
    assert child_file.read_text(
        encoding="utf-8",
    ) == "must survive"


def test_delete_directory_protects_workspace_root(
    isolated_workspace,
):
    result = delete_directory.invoke(
        {
            "path": ".",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "protected_path"
    assert isolated_workspace.exists()


def test_delete_directory_rejects_workspace_escape(
    isolated_workspace,
):
    result = delete_directory.invoke(
        {
            "path": "../unsafe_directory",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "path_security_error"


# =============================================================================
# Move Path Tool Tests
# =============================================================================


def test_move_path_renames_existing_file(
    isolated_workspace,
):
    source_path = isolated_workspace / "source.txt"
    destination_path = isolated_workspace / "renamed.txt"

    source_path.write_text(
        "file content",
        encoding="utf-8",
    )

    result = move_path.invoke(
        {
            "source": "source.txt",
            "destination": "renamed.txt",
        }
    )

    assert result == {
        "ok": True,
        "source": "source.txt",
        "destination": "renamed.txt",
        "type": "file",
        "moved": True,
    }

    assert not source_path.exists()
    assert destination_path.read_text(
        encoding="utf-8",
    ) == "file content"


def test_move_path_moves_file_into_existing_directory(
    isolated_workspace,
):
    source_path = isolated_workspace / "source.txt"
    destination_directory = isolated_workspace / "destination"
    destination_path = destination_directory / "source.txt"

    source_path.write_text(
        "nested destination content",
        encoding="utf-8",
    )

    destination_directory.mkdir()

    result = move_path.invoke(
        {
            "source": "source.txt",
            "destination": "destination/source.txt",
        }
    )

    assert result["ok"] is True
    assert result["type"] == "file"
    assert result["moved"] is True

    assert not source_path.exists()
    assert destination_path.read_text(
        encoding="utf-8",
    ) == "nested destination content"


def test_move_path_renames_existing_directory_and_preserves_contents(
    isolated_workspace,
):
    source_directory = isolated_workspace / "source_directory"
    destination_directory = isolated_workspace / "renamed_directory"

    source_directory.mkdir()

    child_file = source_directory / "child.txt"
    child_file.write_text(
        "directory content",
        encoding="utf-8",
    )

    result = move_path.invoke(
        {
            "source": "source_directory",
            "destination": "renamed_directory",
        }
    )

    assert result["ok"] is True
    assert result["type"] == "directory"
    assert result["moved"] is True

    assert not source_directory.exists()

    assert (
        destination_directory
        / "child.txt"
    ).read_text(
        encoding="utf-8",
    ) == "directory content"


def test_move_path_returns_not_found_for_missing_source(
    isolated_workspace,
):
    result = move_path.invoke(
        {
            "source": "missing.txt",
            "destination": "destination.txt",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "not_found"


def test_move_path_rejects_existing_destination_without_modification(
    isolated_workspace,
):
    source_path = isolated_workspace / "source.txt"
    destination_path = isolated_workspace / "destination.txt"

    source_path.write_text(
        "source content",
        encoding="utf-8",
    )

    destination_path.write_text(
        "destination content",
        encoding="utf-8",
    )

    result = move_path.invoke(
        {
            "source": "source.txt",
            "destination": "destination.txt",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "already_exists"

    assert source_path.read_text(
        encoding="utf-8",
    ) == "source content"

    assert destination_path.read_text(
        encoding="utf-8",
    ) == "destination content"


def test_move_path_rejects_missing_destination_parent_and_preserves_source(
    isolated_workspace,
):
    source_path = isolated_workspace / "source.txt"

    source_path.write_text(
        "preserve source",
        encoding="utf-8",
    )

    result = move_path.invoke(
        {
            "source": "source.txt",
            "destination": "missing/destination.txt",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "parent_not_found"

    assert source_path.read_text(
        encoding="utf-8",
    ) == "preserve source"


def test_move_path_rejects_file_as_destination_parent_and_preserves_source(
    isolated_workspace,
):
    source_path = isolated_workspace / "source.txt"
    parent_file = isolated_workspace / "parent.txt"

    source_path.write_text(
        "source content",
        encoding="utf-8",
    )

    parent_file.write_text(
        "not a directory",
        encoding="utf-8",
    )

    result = move_path.invoke(
        {
            "source": "source.txt",
            "destination": "parent.txt/destination.txt",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "parent_not_directory"

    assert source_path.read_text(
        encoding="utf-8",
    ) == "source content"


def test_move_path_rejects_moving_directory_inside_itself(
    isolated_workspace,
):
    source_directory = isolated_workspace / "source_directory"
    source_directory.mkdir()

    child_file = source_directory / "child.txt"
    child_file.write_text(
        "must survive",
        encoding="utf-8",
    )

    result = move_path.invoke(
        {
            "source": "source_directory",
            "destination": "source_directory/nested/moved",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "invalid_destination"

    assert source_directory.exists()
    assert child_file.read_text(
        encoding="utf-8",
    ) == "must survive"


def test_move_path_protects_workspace_root(
    isolated_workspace,
):
    result = move_path.invoke(
        {
            "source": ".",
            "destination": "moved_workspace",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "protected_path"
    assert isolated_workspace.exists()


def test_move_path_rejects_source_workspace_escape(
    isolated_workspace,
):
    result = move_path.invoke(
        {
            "source": "../unsafe.txt",
            "destination": "destination.txt",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "path_security_error"


def test_move_path_rejects_destination_workspace_escape_and_preserves_source(
    isolated_workspace,
):
    source_path = isolated_workspace / "source.txt"

    source_path.write_text(
        "must survive",
        encoding="utf-8",
    )

    result = move_path.invoke(
        {
            "source": "source.txt",
            "destination": "../unsafe.txt",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "path_security_error"

    assert source_path.read_text(
        encoding="utf-8",
    ) == "must survive"


def test_move_path_rejects_same_source_and_destination(
    isolated_workspace,
):
    source_path = isolated_workspace / "source.txt"

    source_path.write_text(
        "must survive",
        encoding="utf-8",
    )

    result = move_path.invoke(
        {
            "source": "source.txt",
            "destination": "source.txt",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "already_exists"

    assert source_path.read_text(
        encoding="utf-8",
    ) == "must survive"


# =============================================================================
# Search Tool Imports
# =============================================================================


from tools.common import (
    MAX_MATCH_LINE_CHARS,
    MAX_READ_BYTES,
    MAX_SEARCH_RESULTS,
)

from tools.search_tools import (
    search_files,
    search_text,
)


# =============================================================================
# Search Files Tests
# =============================================================================


def test_search_files_finds_matching_files_recursively(
    isolated_workspace: Path,
):
    root_file = isolated_workspace / "report.txt"
    nested_directory = isolated_workspace / "docs"
    nested_file = nested_directory / "annual_report.md"
    unrelated_file = nested_directory / "notes.txt"

    nested_directory.mkdir()

    root_file.write_text(
        "root",
        encoding="utf-8",
    )

    nested_file.write_text(
        "nested",
        encoding="utf-8",
    )

    unrelated_file.write_text(
        "unrelated",
        encoding="utf-8",
    )

    result = search_files.invoke(
        {
            "query": "report",
        }
    )

    assert result["ok"] is True
    assert result["path"] == "."
    assert result["query"] == "report"
    assert result["matches"] == [
        "docs/annual_report.md",
        "report.txt",
    ]
    assert result["count"] == 2
    assert result["truncated"] is False


def test_search_files_is_case_insensitive(
    isolated_workspace: Path,
):
    matching_file = isolated_workspace / "ProjectNotes.TXT"

    matching_file.write_text(
        "content",
        encoding="utf-8",
    )

    result = search_files.invoke(
        {
            "query": "projectnotes",
        }
    )

    assert result["ok"] is True
    assert result["matches"] == [
        "ProjectNotes.TXT",
    ]
    assert result["count"] == 1


def test_search_files_searches_only_requested_subdirectory(
    isolated_workspace: Path,
):
    docs_directory = isolated_workspace / "docs"
    other_directory = isolated_workspace / "other"

    docs_directory.mkdir()
    other_directory.mkdir()

    docs_file = docs_directory / "target.txt"
    other_file = other_directory / "target.txt"

    docs_file.write_text(
        "docs",
        encoding="utf-8",
    )

    other_file.write_text(
        "other",
        encoding="utf-8",
    )

    result = search_files.invoke(
        {
            "query": "target",
            "path": "docs",
        }
    )

    assert result["ok"] is True
    assert result["path"] == "docs"
    assert result["matches"] == [
        "docs/target.txt",
    ]
    assert result["count"] == 1
    assert result["truncated"] is False


def test_search_files_returns_empty_result_when_no_match_exists(
    isolated_workspace: Path,
):
    file_path = isolated_workspace / "notes.txt"

    file_path.write_text(
        "content",
        encoding="utf-8",
    )

    result = search_files.invoke(
        {
            "query": "missing",
        }
    )

    assert result["ok"] is True
    assert result["matches"] == []
    assert result["count"] == 0
    assert result["truncated"] is False


def test_search_files_returns_sorted_matches(
    isolated_workspace: Path,
):
    for file_name in [
        "z_match.txt",
        "a_match.txt",
        "m_match.txt",
    ]:
        (
            isolated_workspace
            / file_name
        ).write_text(
            "content",
            encoding="utf-8",
        )

    result = search_files.invoke(
        {
            "query": "match",
        }
    )

    assert result["ok"] is True
    assert result["matches"] == sorted(
        result["matches"]
    )


def test_search_files_truncates_results_at_search_limit(
    isolated_workspace: Path,
):
    for index in range(
        MAX_SEARCH_RESULTS + 1
    ):
        file_path = (
            isolated_workspace
            / f"match_{index:03d}.txt"
        )

        file_path.write_text(
            "content",
            encoding="utf-8",
        )

    result = search_files.invoke(
        {
            "query": "match_",
        }
    )

    assert result["ok"] is True
    assert result["count"] == MAX_SEARCH_RESULTS
    assert len(result["matches"]) == MAX_SEARCH_RESULTS
    assert result["matches"] == sorted(
        result["matches"]
    )
    assert result["truncated"] is True


def test_search_files_returns_not_found_for_missing_directory():
    result = search_files.invoke(
        {
            "query": "target",
            "path": "missing",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "not_found"


def test_search_files_rejects_file_path(
    isolated_workspace: Path,
):
    file_path = isolated_workspace / "notes.txt"

    file_path.write_text(
        "content",
        encoding="utf-8",
    )

    result = search_files.invoke(
        {
            "query": "notes",
            "path": "notes.txt",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "not_a_directory"


def test_search_files_rejects_workspace_escape():
    result = search_files.invoke(
        {
            "query": "target",
            "path": "../outside",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "path_security_error"


# =============================================================================
# Search Text Tests
# =============================================================================


def test_search_text_finds_literal_text_recursively(
    isolated_workspace: Path,
):
    root_file = isolated_workspace / "root.txt"
    nested_directory = isolated_workspace / "docs"
    nested_file = nested_directory / "nested.txt"

    nested_directory.mkdir()

    root_file.write_text(
        "LangGraph is useful.\nOther line.\n",
        encoding="utf-8",
    )

    nested_file.write_text(
        "First line.\nLearning LangGraph tools.\n",
        encoding="utf-8",
    )

    result = search_text.invoke(
        {
            "query": "LangGraph",
        }
    )

    assert result["ok"] is True
    assert result["path"] == "."
    assert result["query"] == "LangGraph"
    assert result["count"] == 2
    assert result["truncated"] is False

    assert {
        (
            match["path"],
            match["line_number"],
            match["line"],
        )
        for match in result["matches"]
    } == {
        (
            "root.txt",
            1,
            "LangGraph is useful.",
        ),
        (
            "docs/nested.txt",
            2,
            "Learning LangGraph tools.",
        ),
    }


def test_search_text_is_case_insensitive(
    isolated_workspace: Path,
):
    file_path = isolated_workspace / "notes.txt"

    file_path.write_text(
        "Learning LANGGRAPH tools.\n",
        encoding="utf-8",
    )

    result = search_text.invoke(
        {
            "query": "langgraph",
        }
    )

    assert result["ok"] is True
    assert result["count"] == 1
    assert result["matches"][0]["line_number"] == 1
    assert result["matches"][0]["line"] == (
        "Learning LANGGRAPH tools."
    )


def test_search_text_returns_multiple_matching_lines_from_same_file(
    isolated_workspace: Path,
):
    file_path = isolated_workspace / "notes.txt"

    file_path.write_text(
        (
            "target first\n"
            "unrelated\n"
            "target second\n"
        ),
        encoding="utf-8",
    )

    result = search_text.invoke(
        {
            "query": "target",
        }
    )

    assert result["ok"] is True
    assert result["count"] == 2

    assert [
        match["line_number"]
        for match in result["matches"]
    ] == [
        1,
        3,
    ]


def test_search_text_searches_only_requested_subdirectory(
    isolated_workspace: Path,
):
    docs_directory = isolated_workspace / "docs"
    other_directory = isolated_workspace / "other"

    docs_directory.mkdir()
    other_directory.mkdir()

    (
        docs_directory
        / "notes.txt"
    ).write_text(
        "target text",
        encoding="utf-8",
    )

    (
        other_directory
        / "notes.txt"
    ).write_text(
        "target text",
        encoding="utf-8",
    )

    result = search_text.invoke(
        {
            "query": "target",
            "path": "docs",
        }
    )

    assert result["ok"] is True
    assert result["count"] == 1
    assert result["matches"][0]["path"] == (
        "docs/notes.txt"
    )


def test_search_text_returns_empty_result_when_no_match_exists(
    isolated_workspace: Path,
):
    file_path = isolated_workspace / "notes.txt"

    file_path.write_text(
        "unrelated content",
        encoding="utf-8",
    )

    result = search_text.invoke(
        {
            "query": "missing",
        }
    )

    assert result["ok"] is True
    assert result["matches"] == []
    assert result["count"] == 0
    assert result["truncated"] is False


def test_search_text_skips_non_utf8_files(
    isolated_workspace: Path,
):
    binary_file = isolated_workspace / "binary.bin"

    binary_file.write_bytes(
        b"\xff\xfe\x00target"
    )

    result = search_text.invoke(
        {
            "query": "target",
        }
    )

    assert result["ok"] is True
    assert result["matches"] == []
    assert result["count"] == 0


def test_search_text_skips_files_over_read_limit(
    isolated_workspace: Path,
):
    large_file = isolated_workspace / "large.txt"

    large_file.write_bytes(
        b"a" * (MAX_READ_BYTES + 1)
    )

    result = search_text.invoke(
        {
            "query": "a",
        }
    )

    assert result["ok"] is True
    assert result["matches"] == []
    assert result["count"] == 0


def test_search_text_truncates_returned_matching_line(
    isolated_workspace: Path,
):
    file_path = isolated_workspace / "long_line.txt"

    long_line = (
        "target"
        + "x" * MAX_MATCH_LINE_CHARS
    )

    file_path.write_text(
        long_line,
        encoding="utf-8",
    )

    result = search_text.invoke(
        {
            "query": "target",
        }
    )

    assert result["ok"] is True
    assert result["count"] == 1
    assert len(
        result["matches"][0]["line"]
    ) == MAX_MATCH_LINE_CHARS
    assert result["matches"][0]["line"] == (
        long_line[:MAX_MATCH_LINE_CHARS]
    )


def test_search_text_truncates_results_at_search_limit(
    isolated_workspace: Path,
):
    file_path = isolated_workspace / "matches.txt"

    file_path.write_text(
        "\n".join(
            f"target line {index}"
            for index in range(
                MAX_SEARCH_RESULTS + 1
            )
        ),
        encoding="utf-8",
    )

    result = search_text.invoke(
        {
            "query": "target",
        }
    )

    assert result["ok"] is True
    assert result["count"] == MAX_SEARCH_RESULTS
    assert len(result["matches"]) == MAX_SEARCH_RESULTS
    assert result["truncated"] is True


def test_search_text_returns_not_found_for_missing_directory():
    result = search_text.invoke(
        {
            "query": "target",
            "path": "missing",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "not_found"


def test_search_text_rejects_file_path(
    isolated_workspace: Path,
):
    file_path = isolated_workspace / "notes.txt"

    file_path.write_text(
        "target",
        encoding="utf-8",
    )

    result = search_text.invoke(
        {
            "query": "target",
            "path": "notes.txt",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "not_a_directory"


def test_search_text_rejects_workspace_escape():
    result = search_text.invoke(
        {
            "query": "target",
            "path": "../outside",
        }
    )

    assert result["ok"] is False
    assert result["error"]["type"] == "path_security_error"
