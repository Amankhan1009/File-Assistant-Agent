import logging
from pathlib import Path


# =============================================================================
# Logging Configuration
# =============================================================================


PROJECT_ROOT = Path(__file__).resolve().parent.parent

LOG_DIRECTORY = PROJECT_ROOT / "logs"

LOG_FILE_PATH = LOG_DIRECTORY / "file_assistant.log"

LOGGER_NAME = "file_assistant"

DEFAULT_LOG_LEVEL = logging.INFO


# =============================================================================
# Logging Initialization
# =============================================================================


def configure_logging(
    level: int = DEFAULT_LOG_LEVEL,
) -> logging.Logger:
    """
    Configure and return the application's root File Assistant logger.

    Logging is written to both the console and the persistent application
    log file.

    Repeated calls do not add duplicate handlers.
    """
    LOG_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    logger = logging.getLogger(
        LOGGER_NAME,
    )

    logger.setLevel(level)

    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()

    console_handler.setLevel(level)

    console_handler.setFormatter(
        formatter,
    )

    file_handler = logging.FileHandler(
        LOG_FILE_PATH,
        encoding="utf-8",
    )

    file_handler.setLevel(level)

    file_handler.setFormatter(
        formatter,
    )

    logger.addHandler(
        console_handler,
    )

    logger.addHandler(
        file_handler,
    )

    return logger


# =============================================================================
# Logger Factory
# =============================================================================


def get_logger(
    name: str,
) -> logging.Logger:
    """
    Return a child logger under the File Assistant logger hierarchy.

    Logging is configured automatically on first use.
    """
    configure_logging()

    return logging.getLogger(
        f"{LOGGER_NAME}.{name}"
    )