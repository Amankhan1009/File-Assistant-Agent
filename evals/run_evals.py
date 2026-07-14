# =============================================================================
# Imports
# =============================================================================


import sys
import tempfile
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver
from evals.evaluator import EvaluationResult, run_scenario
from evals.scenarios import SCENARIOS
from graph.builder import build_graph


# =============================================================================
# Result Reporting
# =============================================================================


def print_result(
    result: EvaluationResult,
) -> None:
    """Print one live evaluation result."""

    status = "PASS" if result.passed else "FAIL"

    print()
    print("=" * 70)
    print(f"{status}: {result.scenario_name}")
    print("=" * 70)

    print("Observed tools:")

    if result.observed_tools:
        for tool_name in result.observed_tools:
            print(f"- {tool_name}")
    else:
        print("- none")

    print()
    print("Final response:")
    print(result.final_response)

    if result.failures:
        print()
        print("Failures:")

        for failure in result.failures:
            print(f"- {failure}")


# =============================================================================
# Single Live Scenario Execution
# =============================================================================


def run_live_scenario(
    scenario,
    *,
    base_directory: Path,
) -> EvaluationResult:
    """
    Execute one scenario with a fresh persistent checkpointer.

    A separate checkpointer connection is created and closed for each scenario
    so evaluation executions do not share graph conversation state.
    """
    checkpointer = InMemorySaver()

    graph = build_graph(
        checkpointer=checkpointer,
    )

    return run_scenario(
        scenario,
        graph,
        base_directory=base_directory,
    )


# =============================================================================
# Live Evaluation Suite
# =============================================================================


def main() -> int:
    """Run all registered scenarios against the live File Assistant."""

    print("=" * 70)
    print("FILE ASSISTANT LIVE EVALUATION SUITE")
    print("=" * 70)
    print(f"Scenario count: {len(SCENARIOS)}")

    results: list[EvaluationResult] = []

    with tempfile.TemporaryDirectory(
        prefix="file-assistant-evals-",
    ) as temporary_directory:
        base_directory = Path(temporary_directory)

        for index, scenario in enumerate(
            SCENARIOS,
            start=1,
        ):
            print()
            print(
                f"Running scenario {index}/{len(SCENARIOS)}: "
                f"{scenario.name}"
            )

            scenario_base_directory = (
                base_directory
                / f"{index:02d}-{scenario.name}"
            )

            scenario_base_directory.mkdir()

            try:
                result = run_live_scenario(
                    scenario,
                    base_directory=scenario_base_directory,
                )

            except Exception as exc:
                result = EvaluationResult(
                    scenario_name=scenario.name,
                    passed=False,
                    failures=(
                        f"Evaluation execution error: "
                        f"{type(exc).__name__}: {exc}",
                    ),
                )

            results.append(result)

            print_result(result)

    passed_count = sum(
        result.passed
        for result in results
    )

    failed_count = len(results) - passed_count

    print()
    print("=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)
    print(f"Total:  {len(results)}")
    print(f"Passed: {passed_count}")
    print(f"Failed: {failed_count}")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
