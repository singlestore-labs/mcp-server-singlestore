from fastmcp import Context
from new_src.api.common import (
    __get_user_id,
)
from new_src.api.tools.types import Tool


def get_user_id(ctx: Context) -> str:
    """
    Retrieve the current user's unique identifier.

    Returns:
        str: UUID format identifier for the current user

    Required for:
    - Constructing paths or references to personal resources

    Performance Tip:
    Cache the returned ID when making multiple API calls.
    """
    return __get_user_id()


tools_definition = [{"func": get_user_id}]

# Export the tools
tools = [Tool(**tool) for tool in tools_definition]
