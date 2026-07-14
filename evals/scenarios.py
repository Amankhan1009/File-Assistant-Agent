from dataclasses import dataclass, field


@dataclass(frozen=True)
class EvaluationScenario:
    """
    Declarative definition of one live agent evaluation scenario.

    A scenario describes the user request, expected tool behavior, forbidden
    tool behavior, and filesystem state required before and after execution.

    Scenario objects contain evaluation data only. They do not execute graphs,
    call language models, or modify the filesystem.
    """

    name: str

    user_request: str

    expected_tools: tuple[str, ...] = ()

    forbidden_tools: tuple[str, ...] = ()

    initial_files: dict[str, str] = field(
        default_factory=dict,
    )

    initial_directories: tuple[str, ...] = ()

    expected_files: dict[str, str] = field(
        default_factory=dict,
    )

    expected_absent_paths: tuple[str, ...] = ()

    required_response_substrings: tuple[str, ...] = ()

    forbidden_response_substrings: tuple[str, ...] = ()


SCENARIOS: tuple[EvaluationScenario, ...] = (
    EvaluationScenario(
        name="create-file-with-content",
        user_request=(
            "Create a new file called evaluation.txt containing exactly: "
            "LangGraph agents can safely execute filesystem tools."
        ),
        expected_tools=(
            "create_file",
        ),
        forbidden_tools=(
            "delete_file",
            "delete_directory",
        ),
        expected_files={
            "evaluation.txt": (
                "LangGraph agents can safely execute filesystem tools."
            ),
        },
        required_response_substrings=(
            "created",
        ),
        forbidden_response_substrings=(
            "failed",
        ),
    ),
    EvaluationScenario(
        name="read-and-append-file",
        user_request=(
            "Read notes.txt and append a new line containing exactly: "
            "The agent loop continues until no more tools are required."
        ),
        expected_tools=(
            "read_file",
            "append_file",
        ),
        forbidden_tools=(
            "create_file",
            "delete_file",
            "delete_directory",
        ),
        initial_files={
            "notes.txt": (
                "LangGraph agents can call tools.\n"
            ),
        },
        expected_files={
            "notes.txt": (
                "LangGraph agents can call tools.\n"
                "The agent loop continues until no more tools are required.\n"
            ),
        },
        required_response_substrings=(
            "appended",
        ),
        forbidden_response_substrings=(
            "failed",
        ),
    ),
    EvaluationScenario(
        name="search-files-by-name",
        user_request=(
            "Find all files whose names contain summary."
        ),
        expected_tools=(
            "search_files",
        ),
        forbidden_tools=(
            "read_file",
            "create_file",
            "append_file",
            "delete_file",
            "delete_directory",
            "move_path",
        ),
        initial_files={
            "reports/summary.txt": "Current summary.",
            "archive/summary_old.txt": "Archived summary.",
            "notes.txt": "General notes.",
        },
        expected_files={
            "reports/summary.txt": "Current summary.",
            "archive/summary_old.txt": "Archived summary.",
            "notes.txt": "General notes.",
        },
        required_response_substrings=(
            "reports/summary.txt",
            "archive/summary_old.txt",
        ),
        forbidden_response_substrings=(
            "failed",
        ),
    ),
)
