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
# EvaluationScenario Tests
# =============================================================================


def test_evaluation_scenario_stores_required_fields():
    scenario = EvaluationScenario(
        name="create-file",
        user_request="Create notes.txt",
    )

    assert scenario.name == "create-file"
    assert scenario.user_request == "Create notes.txt"


def test_evaluation_scenario_uses_empty_defaults():
    scenario = EvaluationScenario(
        name="default-fields",
        user_request="List files",
    )

    assert scenario.expected_tools == ()
    assert scenario.forbidden_tools == ()
    assert scenario.initial_files == {}
    assert scenario.initial_directories == ()
    assert scenario.expected_files == {}
    assert scenario.expected_absent_paths == ()
    assert scenario.required_response_substrings == ()
    assert scenario.forbidden_response_substrings == ()


def test_evaluation_scenario_mutable_defaults_are_not_shared():
    first = EvaluationScenario(
        name="first",
        user_request="First request",
    )

    second = EvaluationScenario(
        name="second",
        user_request="Second request",
    )

    assert first.initial_files is not second.initial_files
    assert first.expected_files is not second.expected_files


def test_evaluation_scenario_stores_all_expectations():
    scenario = EvaluationScenario(
        name="complete-scenario",
        user_request="Create notes.txt",
        expected_tools=(
            "create_file",
            "read_file",
        ),
        forbidden_tools=(
            "delete_file",
        ),
        initial_files={
            "source.txt": "source content",
        },
        initial_directories=(
            "docs",
        ),
        expected_files={
            "notes.txt": "expected content",
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

    assert scenario.expected_tools == (
        "create_file",
        "read_file",
    )

    assert scenario.forbidden_tools == (
        "delete_file",
    )

    assert scenario.initial_files == {
        "source.txt": "source content",
    }

    assert scenario.initial_directories == (
        "docs",
    )

    assert scenario.expected_files == {
        "notes.txt": "expected content",
    }

    assert scenario.expected_absent_paths == (
        "forbidden.txt",
    )

    assert scenario.required_response_substrings == (
        "created",
    )

    assert scenario.forbidden_response_substrings == (
        "failed",
    )


def test_evaluation_scenario_is_frozen():
    scenario = EvaluationScenario(
        name="immutable-scenario",
        user_request="List files",
    )

    with pytest.raises(FrozenInstanceError):
        scenario.name = "modified"


def test_scenarios_registry_is_tuple():
    assert isinstance(
        SCENARIOS,
        tuple,
    )


# =============================================================================
# EvaluationResult Tests
# =============================================================================


def test_evaluation_result_stores_observed_data():
    result = EvaluationResult(
        scenario_name="create-file",
        passed=False,
        observed_tools=(
            "create_file",
        ),
        final_response="The file was created.",
        failures=(
            "Example failure.",
        ),
    )

    assert result.scenario_name == "create-file"
    assert result.passed is False

    assert result.observed_tools == (
        "create_file",
    )

    assert result.final_response == "The file was created."

    assert result.failures == (
        "Example failure.",
    )


def test_evaluation_result_uses_empty_defaults():
    result = EvaluationResult(
        scenario_name="default-result",
        passed=True,
    )

    assert result.observed_tools == ()
    assert result.final_response == ""
    assert result.failures == ()


def test_evaluation_result_is_frozen():
    result = EvaluationResult(
        scenario_name="immutable-result",
        passed=True,
    )

    with pytest.raises(FrozenInstanceError):
        result.passed = False


# =============================================================================
# create_evaluation_result Tests
# =============================================================================


def test_create_evaluation_result_passes_when_failures_are_empty():
    scenario = EvaluationScenario(
        name="passing-scenario",
        user_request="Create notes.txt",
    )

    result = create_evaluation_result(
        scenario,
        observed_tools=(
            "create_file",
        ),
        final_response="Created.",
    )

    assert result == EvaluationResult(
        scenario_name="passing-scenario",
        passed=True,
        observed_tools=(
            "create_file",
        ),
        final_response="Created.",
        failures=(),
    )


def test_create_evaluation_result_fails_when_failures_exist():
    scenario = EvaluationScenario(
        name="failing-scenario",
        user_request="Delete notes.txt",
    )

    failures = (
        "Expected tool was not called.",
        "Forbidden tool was called.",
    )

    result = create_evaluation_result(
        scenario,
        observed_tools=(
            "delete_file",
        ),
        final_response="Operation failed.",
        failures=failures,
    )

    assert result.scenario_name == "failing-scenario"
    assert result.passed is False

    assert result.observed_tools == (
        "delete_file",
    )

    assert result.final_response == "Operation failed."
    assert result.failures == failures


