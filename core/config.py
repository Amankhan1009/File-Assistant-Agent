import os
from pathlib import Path

from dotenv import load_dotenv


# Absolute project root derived from this file's location.
# This avoids depending on the terminal's current working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load environment variables from the project's .env file explicitly.
ENV_FILE = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_FILE)


def get_workspace_root() -> Path:
    """
    Return the canonical workspace root.

    WORKSPACE_ROOT must be a relative path inside the project directory.
    Absolute paths are rejected because this application intentionally
    restricts filesystem access to a project-controlled workspace.
    """
    workspace_setting = Path(os.getenv("WORKSPACE_ROOT", "workspace"))

    if workspace_setting.is_absolute():
        raise ValueError(
            "WORKSPACE_ROOT must be a relative path inside the project directory."
        )

    workspace_root = (PROJECT_ROOT / workspace_setting).resolve()

    try:
        workspace_root.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise ValueError(
            "WORKSPACE_ROOT must resolve inside the project directory."
        ) from exc

    return workspace_root

# =============================================================================
# LLM Configuration
# =============================================================================


GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b",
)

WORKSPACE_ROOT = get_workspace_root()