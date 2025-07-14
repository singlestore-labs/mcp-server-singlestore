"""Utility functions for handling elicitation with fallbacks."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, Literal, Optional, Tuple, Type, TypeVar
from mcp.server.fastmcp import Context
from pydantic import BaseModel


class ElicitationError(Enum):
    """Possible elicitation error types."""

    NOT_SUPPORTED = auto()
    FAILED = auto()


T = TypeVar("T", bound=BaseModel)


@dataclass
class ElicitationResult:
    """Result of an elicitation attempt."""

    status: Literal["success", "error", "cancelled"]
    message: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


async def try_elicitation(
    ctx: Context,
    message: str,
    schema: Type[T],
) -> Tuple[ElicitationResult, Optional[ElicitationError]]:
    """
    Try to elicit a response from the user, handling cases where elicitation is not supported.

    Args:
        ctx: The Context object from MCP.
        message: The message to display to the user for elicitation.
        schema: The Pydantic schema for elicitation validation.

    Returns:
        A tuple containing:
        1. ElicitationResult with:
           - status: 'success', 'error', or 'cancelled'
           - message: Description of what happened
           - data: The elicited data if successful
           - error_code: Error code if there was an error
           - error_details: Additional error details
        2. ElicitationError: The type of error if one occurred, None if successful

    Raises:
        Exception: If elicitation fails for any reason other than not being supported
    """
    try:
        result = await ctx.elicit(message=message, schema=schema)
        if result.action == "accept" and result.data:
            return (
                ElicitationResult(
                    status="success",
                    message="Elicitation successful",
                    data=result.data,
                ),
                None,
            )
        return (
            ElicitationResult(
                status="cancelled", message="Elicitation was cancelled by the user"
            ),
            None,
        )
    except Exception as e:
        # Elicitation not supported by the client
        if type(e).__name__ == "McpError" and str(e) == "Method not found":
            return (
                ElicitationResult(
                    status="error",
                    message="Client doesn't support elicitation",
                    error_code="ELICITATION_NOT_SUPPORTED",
                    error_details={"error_message": str(e)},
                ),
                ElicitationError.NOT_SUPPORTED,
            )
        # For all other errors, re-raise the original exception
        raise
