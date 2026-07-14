import core.paths

from langchain_core.messages import HumanMessage

import pytest

from dataclasses import FrozenInstanceError

from evals.evaluator import (
    EvaluationResult,
    create_evaluation_result,
)
from evals.scenarios import (
    EvaluationScenario,
    SCENARIOS,
)



# =============================================================================
# Isolated Evaluation Workspace Tests
# =============================================================================


def test_create_isolated_workspace_creates_empty_workspace(
    tmp_path,
):
    from evals.evaluator import create_isolated_workspace

    workspace = create_isolated_workspace(
        tmp_path,
    )

    assert workspace == tmp_path / "workspace"
    assert workspace.exists()
    assert workspace.is_dir()
    assert list(workspace.iterdir()) == []


def test_create_isolated_workspace_does_not_modify_real_workspace(
    tmp_path,
):
    from core.config import WORKSPACE_ROOT
    from evals.evaluator import create_isolated_workspace

    marker_path = WORKSPACE_ROOT / "evaluation-isolation-marker.txt"

    marker_path.write_text(
        "real workspace marker",
        encoding="utf-8",
    )

    try:
        workspace = create_isolated_workspace(
            tmp_path,
        )

        assert workspace != WORKSPACE_ROOT
        assert marker_path.exists()

    finally:
        marker_path.unlink(
            missing_ok=True,
        )


# =============================================================================
# Scenario Workspace Seeding Tests
# =============================================================================


def test_seed_scenario_workspace_creates_initial_directories(
    tmp_path,
):
    from evals.evaluator import (
        create_isolated_workspace,
        seed_scenario_workspace,
    )

    scenario = EvaluationScenario(
        name="directory-seeding",
        user_request="List files",
        initial_directories=(
            "docs",
            "nested/data",
        ),
    )

    workspace = create_isolated_workspace(
        tmp_path,
    )

    seed_scenario_workspace(
        scenario,
        workspace,
    )

    assert (workspace / "docs").is_dir()
    assert (workspace / "nested/data").is_dir()


def test_seed_scenario_workspace_creates_initial_files(
    tmp_path,
):
    from evals.evaluator import (
        create_isolated_workspace,
        seed_scenario_workspace,
    )

    scenario = EvaluationScenario(
        name="file-seeding",
        user_request="Read files",
        initial_files={
            "notes.txt": "notes content",
            "docs/report.txt": "report content",
        },
    )

    workspace = create_isolated_workspace(
        tmp_path,
    )

    seed_scenario_workspace(
        scenario,
        workspace,
    )

    assert (
        workspace / "notes.txt"
    ).read_text(
        encoding="utf-8",
    ) == "notes content"

    assert (
        workspace / "docs/report.txt"
    ).read_text(
        encoding="utf-8",
    ) == "report content"


def test_seed_scenario_workspace_preserves_declared_empty_directories(
    tmp_path,
):
    from evals.evaluator import (
        create_isolated_workspace,
        seed_scenario_workspace,
    )

    scenario = EvaluationScenario(
        name="empty-directory-seeding",
        user_request="Inspect workspace",
        initial_directories=(
            "empty-directory",
        ),
    )

    workspace = create_isolated_workspace(
        tmp_path,
    )

    seed_scenario_workspace(
        scenario,
        workspace,
    )

    empty_directory = workspace / "empty-directory"

    assert empty_directory.is_dir()
    assert list(empty_directory.iterdir()) == []


def test_seed_scenario_workspace_does_not_create_expected_files(
    tmp_path,
):
    from evals.evaluator import (
        create_isolated_workspace,
        seed_scenario_workspace,
    )

    scenario = EvaluationScenario(
        name="expected-files-not-seeded",
        user_request="Create output.txt",
        expected_files={
            "output.txt": "expected output",
        },
    )

    workspace = create_isolated_workspace(
        tmp_path,
    )

    seed_scenario_workspace(
        scenario,
        workspace,
    )

    assert not (
        workspace / "output.txt"
    ).exists()


def test_seed_scenario_workspace_returns_none(
    tmp_path,
):
    from evals.evaluator import (
        create_isolated_workspace,
        seed_scenario_workspace,
    )

    scenario = EvaluationScenario(
        name="return-value",
        user_request="List files",
    )

    workspace = create_isolated_workspace(
        tmp_path,
    )

    result = seed_scenario_workspace(
        scenario,
        workspace,
    )

    assert result is None


# =============================================================================
# Evaluation Workspace Binding Tests
# =============================================================================


def test_bind_workspace_temporarily_replaces_workspace_root(
    tmp_path,
):
    import core.paths

    from evals.evaluator import (
        bind_workspace,
        create_isolated_workspace,
    )

    original_workspace_root = core.paths.WORKSPACE_ROOT

    workspace = create_isolated_workspace(
        tmp_path,
    )

    with bind_workspace(workspace):
        assert core.paths.WORKSPACE_ROOT == workspace.resolve()

    assert core.paths.WORKSPACE_ROOT == original_workspace_root


def test_bind_workspace_restores_workspace_after_exception(
    tmp_path,
):
    import core.paths

    from evals.evaluator import (
        bind_workspace,
        create_isolated_workspace,
    )

    original_workspace_root = core.paths.WORKSPACE_ROOT

    workspace = create_isolated_workspace(
        tmp_path,
    )

    with pytest.raises(
        RuntimeError,
        match="evaluation failure",
    ):
        with bind_workspace(workspace):
            assert core.paths.WORKSPACE_ROOT == workspace.resolve()

            raise RuntimeError(
                "evaluation failure"
            )

    assert core.paths.WORKSPACE_ROOT == original_workspace_root


def test_bind_workspace_redirects_real_create_file_tool(
    tmp_path,
):
    from evals.evaluator import (
        bind_workspace,
        create_isolated_workspace,
    )
    from tools.write_tools import create_file

    workspace = create_isolated_workspace(
        tmp_path,
    )

    with bind_workspace(workspace):
        result = create_file.invoke(
            {
                "path": "created-by-tool.txt",
                "content": "evaluation content",
            }
        )

    assert result["ok"] is True

    assert (
        workspace / "created-by-tool.txt"
    ).read_text(
        encoding="utf-8",
    ) == "evaluation content"


def test_bind_workspace_redirects_real_read_file_tool(
    tmp_path,
):
    from evals.evaluator import (
        bind_workspace,
        create_isolated_workspace,
    )
    from tools.read_tools import read_file

    workspace = create_isolated_workspace(
        tmp_path,
    )

    file_path = workspace / "notes.txt"

    file_path.write_text(
        "isolated evaluation content",
        encoding="utf-8",
    )

    with bind_workspace(workspace):
        result = read_file.invoke(
            {
                "path": "notes.txt",
            }
        )

    assert result["ok"] is True
    assert result["content"] == "isolated evaluation content"


def test_bind_workspace_production_tool_does_not_modify_real_workspace(
    tmp_path,
):
    from core.config import WORKSPACE_ROOT

    from evals.evaluator import (
        bind_workspace,
        create_isolated_workspace,
    )
    from tools.write_tools import create_file

    real_file = WORKSPACE_ROOT / "must-not-be-created.txt"

    real_file.unlink(
        missing_ok=True,
    )

    workspace = create_isolated_workspace(
        tmp_path,
    )

    with bind_workspace(workspace):
        result = create_file.invoke(
            {
                "path": "must-not-be-created.txt",
                "content": "isolated content",
            }
        )

    assert result["ok"] is True

    assert (
        workspace / "must-not-be-created.txt"
    ).exists()

    assert not real_file.exists()


def test_bind_workspace_restores_production_tool_behavior_after_context(
    tmp_path,
):
    import core.paths

    from evals.evaluator import (
        bind_workspace,
        create_isolated_workspace,
    )
    from tools.write_tools import create_file

    original_workspace_root = core.paths.WORKSPACE_ROOT

    workspace = create_isolated_workspace(
        tmp_path,
    )

    with bind_workspace(workspace):
        result = create_file.invoke(
            {
                "path": "temporary-evaluation-file.txt",
                "content": "temporary",
            }
        )

        assert result["ok"] is True

    assert core.paths.WORKSPACE_ROOT == original_workspace_root

    assert (
        workspace / "temporary-evaluation-file.txt"
    ).exists()


