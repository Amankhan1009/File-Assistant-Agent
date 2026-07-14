import argparse

from langchain_core.messages import HumanMessage
from langgraph.errors import GraphRecursionError

from core.logging import get_logger
from database.checkpointer import checkpointer_runtime
from graph.builder import build_graph


RECURSION_LIMIT = 20

DEFAULT_THREAD_ID = "file-assistant-cli"

SAFE_ASSISTANT_ERROR_MESSAGE = (
    "The assistant could not complete the request due to an internal error. "
    "Please try again."
)

RECURSION_LIMIT_ERROR_MESSAGE = (
    "The assistant could not complete the request because it reached "
    "the maximum number of execution steps. Please simplify the request "
    "or try again."
)

logger = get_logger(__name__)


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments for the File Assistant."""
    parser = argparse.ArgumentParser(
        description="Run the persistent File Assistant.",
    )

    parser.add_argument(
        "--thread",
        default=DEFAULT_THREAD_ID,
        help=(
            "Persistent conversation thread ID. "
            f"Defaults to '{DEFAULT_THREAD_ID}'."
        ),
    )

    return parser.parse_args()


def main() -> None:
    """Run the persistent File Assistant command-line application."""
    args = parse_arguments()

    thread_id = args.thread.strip()

    if not thread_id:
        raise SystemExit(
            "Error: --thread must not be empty."
        )

    logger.info(
        "File Assistant startup initiated | thread_id=%s",
        thread_id,
    )

    # =========================================================================
    # Persistent Storage Initialization
    # =========================================================================

    try:
        runtime = checkpointer_runtime()
        checkpointer = runtime.__enter__()

    except Exception:
        logger.exception(
            "Checkpointer initialization failed | thread_id=%s",
            thread_id,
        )

        print(
            "Error: File Assistant could not initialize persistent storage."
        )

        return

    # =========================================================================
    # Application Runtime
    # =========================================================================

    try:
        graph = build_graph(
            checkpointer=checkpointer,
        )

        config = {
            "configurable": {
                "thread_id": thread_id,
            },
            "recursion_limit": RECURSION_LIMIT,
        }

        logger.info(
            "File Assistant started | thread_id=%s | recursion_limit=%d",
            thread_id,
            RECURSION_LIMIT,
        )

        print("File Assistant started.")
        print(f"Session: {thread_id}")
        print("Type 'exit' or 'quit' to stop.")

        while True:
            try:
                user_input = input("\nYou: ").strip()

            except (EOFError, KeyboardInterrupt):
                print("\nFile Assistant stopped.")

                logger.info(
                    "File Assistant stopped by input interruption | thread_id=%s",
                    thread_id,
                )

                break

            if not user_input:
                continue

            if user_input.lower() in {"exit", "quit"}:
                print("File Assistant stopped.")

                logger.info(
                    "File Assistant stopped by user command | thread_id=%s",
                    thread_id,
                )

                break

            # =================================================================
            # Graph Execution
            # =================================================================

            try:
                result = graph.invoke(
                    {
                        "messages": [
                            HumanMessage(
                                content=user_input,
                            )
                        ],
                    },
                    config=config,
                )

            except GraphRecursionError:
                logger.exception(
                    "Graph recursion limit reached | "
                    "thread_id=%s | recursion_limit=%d",
                    thread_id,
                    RECURSION_LIMIT,
                )

                print(
                    f"\nAssistant: {RECURSION_LIMIT_ERROR_MESSAGE}"
                )

                continue

            except Exception:
                logger.exception(
                    "Graph invocation failed | thread_id=%s",
                    thread_id,
                )

                print(
                    f"\nAssistant: {SAFE_ASSISTANT_ERROR_MESSAGE}"
                )

                continue

            final_message = result["messages"][-1]

            print(
                f"\nAssistant: {final_message.content}"
            )

    except Exception:
        logger.exception(
            "File Assistant runtime failed unexpectedly | thread_id=%s",
            thread_id,
        )

        print(
            "Error: File Assistant stopped because of an internal error."
        )

    # =========================================================================
    # Resource Cleanup
    # =========================================================================

    finally:
        try:
            runtime.__exit__(
                None,
                None,
                None,
            )

        except Exception:
            logger.exception(
                "Checkpointer cleanup failed | thread_id=%s",
                thread_id,
            )

        else:
            logger.info(
                "Checkpointer cleanup completed | thread_id=%s",
                thread_id,
            )


if __name__ == "__main__":
    main()