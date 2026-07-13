from typing import Any


MAX_READ_BYTES = 1_000_000
MAX_WRITE_BYTES = 1_000_000
MAX_SEARCH_RESULTS = 100
MAX_MATCH_LINE_CHARS = 500
# =============================================================================
# Archive Extraction Limits
# =============================================================================

MAX_ARCHIVE_ENTRIES = 1000
MAX_EXTRACTED_BYTES = 10_000_000

def error_result(error_type: str, message: str) -> dict[str, Any]:
    """Create a consistent structured tool error result."""
    return {
        "ok": False,
        "error": {
            "type": error_type,
            "message": message,
        },
    }