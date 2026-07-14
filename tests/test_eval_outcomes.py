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
# Deterministic Scenario Assertion Tests
# =============================================================================


def test_collect_scenario_failures_returns_empty_tuple_when_expectations_pass(
    tmp_path,
):
    from evals.evaluator import collect_scenario_failures

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    (workspace / "output.txt").write_text(
        "expected content",
        encoding="utf-8",
    )

    scenario = EvaluationScenario(
        name="passing-assertions",
        user_request="Create output.txt",
        expected_tools=(
            "create_file",
        ),
        forbidden_tools=(
            "delete_file",
        ),
        expected_files={
            "output.txt": "expected content",
        },
        expected_absent_paths=(
            "forbidden.txt",
        ),
        required_response_substrings=(
            "created",
        ),
        forbidden_response_substrings=(
            "failed",
        ),
    )

    failures = collect_scenario_failures(
        scenario,
        workspace=workspace,
        observed_tools=(
            "create_file",
        ),
        final_response="The file was CREATED successfully.",
    )

    assert failures == ()


def test_collect_scenario_failures_reports_missing_expected_tool(
    tmp_path,
):
    from evals.evaluator import collect_scenario_failures

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    scenario = EvaluationScenario(
        name="missing-tool",
        user_request="Create file",
        expected_tools=(
            "create_file",
            "read_file",
        ),
    )

    failures = collect_scenario_failures(
        scenario,
        workspace=workspace,
        observed_tools=(
            "create_file",
        ),
    )

    assert failures == (
        "Expected tool was not called: read_file",
    )


def test_collect_scenario_failures_reports_forbidden_tool(
    tmp_path,
):
    from evals.evaluator import collect_scenario_failures

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    scenario = EvaluationScenario(
        name="forbidden-tool",
        user_request="Inspect file",
        forbidden_tools=(
            "delete_file",
        ),
    )

    failures = collect_scenario_failures(
        scenario,
        workspace=workspace,
        observed_tools=(
            "read_file",
            "delete_file",
        ),
    )

    assert failures == (
        "Forbidden tool was called: delete_file",
    )


def test_collect_scenario_failures_reports_missing_expected_file(
    tmp_path,
):
    from evals.evaluator import collect_scenario_failures

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    scenario = EvaluationScenario(
        name="missing-file",
        user_request="Create output.txt",
        expected_files={
            "output.txt": "expected",
        },
    )

    failures = collect_scenario_failures(
        scenario,
        workspace=workspace,
    )

    assert failures == (
        "Expected file does not exist: output.txt",
    )


def test_collect_scenario_failures_reports_expected_file_content_mismatch(
    tmp_path,
):
    from evals.evaluator import collect_scenario_failures

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    (workspace / "output.txt").write_text(
        "actual content",
        encoding="utf-8",
    )

    scenario = EvaluationScenario(
        name="content-mismatch",
        user_request="Create output.txt",
        expected_files={
            "output.txt": "expected content",
        },
    )

    failures = collect_scenario_failures(
        scenario,
        workspace=workspace,
    )

    assert failures == (
        "Expected file content mismatch: output.txt",
    )


def test_collect_scenario_failures_reports_directory_at_expected_file_path(
    tmp_path,
):
    from evals.evaluator import collect_scenario_failures

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    (workspace / "output.txt").mkdir()

    scenario = EvaluationScenario(
        name="directory-instead-of-file",
        user_request="Create output.txt",
        expected_files={
            "output.txt": "expected content",
        },
    )

    failures = collect_scenario_failures(
        scenario,
        workspace=workspace,
    )

    assert failures == (
        "Expected file path is not a regular file: output.txt",
    )


def test_collect_scenario_failures_reports_present_expected_absent_path(
    tmp_path,
):
    from evals.evaluator import collect_scenario_failures

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    (workspace / "forbidden.txt").write_text(
        "unexpected",
        encoding="utf-8",
    )

    scenario = EvaluationScenario(
        name="unexpected-path",
        user_request="Do not create forbidden.txt",
        expected_absent_paths=(
            "forbidden.txt",
        ),
    )

    failures = collect_scenario_failures(
        scenario,
        workspace=workspace,
    )

    assert failures == (
        "Expected path to be absent: forbidden.txt",
    )


def test_collect_scenario_failures_reports_missing_required_response_substring(
    tmp_path,
):
    from evals.evaluator import collect_scenario_failures

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    scenario = EvaluationScenario(
        name="missing-response-text",
        user_request="Create file",
        required_response_substrings=(
            "created",
        ),
    )

    failures = collect_scenario_failures(
        scenario,
        workspace=workspace,
        final_response="The operation completed.",
    )

    assert failures == (
        "Required response substring missing: created",
    )


def test_collect_scenario_failures_reports_forbidden_response_substring(
    tmp_path,
):
    from evals.evaluator import collect_scenario_failures

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    scenario = EvaluationScenario(
        name="forbidden-response-text",
        user_request="Create file",
        forbidden_response_substrings=(
            "failed",
        ),
    )

    failures = collect_scenario_failures(
        scenario,
        workspace=workspace,
        final_response="The operation FAILED.",
    )

    assert failures == (
        "Forbidden response substring present: failed",
    )


def test_collect_scenario_failures_accumulates_failures_in_deterministic_order(
    tmp_path,
):
    from evals.evaluator import collect_scenario_failures

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    (workspace / "unexpected.txt").write_text(
        "unexpected",
        encoding="utf-8",
    )

    scenario = EvaluationScenario(
        name="multiple-failures",
        user_request="Perform operation",
        expected_tools=(
            "create_file",
        ),
        forbidden_tools=(
            "delete_file",
        ),
        expected_files={
            "missing.txt": "expected",
        },
        expected_absent_paths=(
            "unexpected.txt",
        ),
        required_response_substrings=(
            "created",
        ),
        forbidden_response_substrings=(
            "failed",
        ),
    )

    failures = collect_scenario_failures(
        scenario,
        workspace=workspace,
        observed_tools=(
            "delete_file",
        ),
        final_response="The operation failed.",
    )

    assert failures == (
        "Expected tool was not called: create_file",
        "Forbidden tool was called: delete_file",
        "Expected file does not exist: missing.txt",
        "Expected path to be absent: unexpected.txt",
        "Required response substring missing: created",
        "Forbidden response substring present: failed",
    )


def test_evaluate_scenario_outcome_returns_passing_result(
    tmp_path,
):
    from evals.evaluator import evaluate_scenario_outcome

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    scenario = EvaluationScenario(
        name="passing-outcome",
        user_request="List files",
        expected_tools=(
            "list_directory",
        ),
        required_response_substrings=(
            "files",
        ),
    )

    result = evaluate_scenario_outcome(
        scenario,
        workspace=workspace,
        observed_tools=(
            "list_directory",
        ),
        final_response="The files are listed.",
    )

    assert result == EvaluationResult(
        scenario_name="passing-outcome",
        passed=True,
        observed_tools=(
            "list_directory",
        ),
        final_response="The files are listed.",
        failures=(),
    )


def test_evaluate_scenario_outcome_returns_failing_result(
    tmp_path,
):
    from evals.evaluator import evaluate_scenario_outcome

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    scenario = EvaluationScenario(
        name="failing-outcome",
        user_request="Create file",
        expected_tools=(
            "create_file",
        ),
    )

    result = evaluate_scenario_outcome(
        scenario,
        workspace=workspace,
        observed_tools=(),
        final_response="Nothing happened.",
    )

    assert result.passed is False

    assert result.failures == (
        "Expected tool was not called: create_file",
    )


