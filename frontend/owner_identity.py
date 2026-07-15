# =============================================================================
# Standard Library Imports
# =============================================================================


from uuid import uuid4


# =============================================================================
# Owner Identity Configuration
# =============================================================================


OWNER_QUERY_PARAMETER = "owner"

OWNER_ID_SESSION_KEY = "owner_id"

OWNER_ID_PREFIX = "browser-"


# =============================================================================
# Owner ID Creation
# =============================================================================


def create_owner_id() -> str:
    """Create a unique anonymous browser owner identifier."""
    return f"{OWNER_ID_PREFIX}{uuid4()}"


# =============================================================================
# URL Owner Identity Resolution
# =============================================================================


def get_owner_id_from_url(
    query_params,
) -> str | None:
    """Return a valid anonymous owner ID stored in the page URL."""
    owner_id = query_params.get(
        OWNER_QUERY_PARAMETER,
    )

    if (
        not isinstance(owner_id, str)
        or not owner_id.strip()
    ):
        return None

    return owner_id.strip()


def store_owner_id_in_url(
    query_params,
    owner_id: str,
) -> None:
    """Store the active anonymous owner ID in the page URL."""
    query_params[
        OWNER_QUERY_PARAMETER
    ] = owner_id


# =============================================================================
# Owner Identity Resolution
# =============================================================================


def resolve_owner_id(
    session_state,
    query_params,
) -> str:
    """
    Resolve the anonymous owner identity for the current frontend.

    Resolution order:

    1. Use the owner ID from the page URL when one exists.
    2. Reuse the owner ID from the current Streamlit session.
    3. Create a new anonymous owner ID.

    The resolved owner ID is stored in both session state and the page URL.
    """
    url_owner_id = get_owner_id_from_url(
        query_params=query_params,
    )

    session_owner_id = session_state.get(
        OWNER_ID_SESSION_KEY,
    )


    # -------------------------------------------------------------------------
    # Resolve Active Owner Identity
    # -------------------------------------------------------------------------


    if url_owner_id is not None:
        owner_id = url_owner_id

    elif (
        isinstance(session_owner_id, str)
        and session_owner_id.strip()
    ):
        owner_id = session_owner_id.strip()

    else:
        owner_id = create_owner_id()


    # -------------------------------------------------------------------------
    # Persist Active Owner Identity
    # -------------------------------------------------------------------------


    session_state[
        OWNER_ID_SESSION_KEY
    ] = owner_id

    store_owner_id_in_url(
        query_params=query_params,
        owner_id=owner_id,
    )

    return owner_id