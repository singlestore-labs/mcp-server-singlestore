"""
Response standardization decorator for SingleStore MCP Server tools.

This module provides decorators to ensure all tool functions return
standardized ToolResponse objects.
"""

from functools import wraps
from typing import Callable
import logging

from .types import ToolResponse, ToolResponseBuilder

logger = logging.getLogger("MCP_SERVER")


def standardize_response(func: Callable) -> Callable:
    """
    Decorator to ensure all tool functions return ToolResponse objects.

    This decorator:
    1. Wraps existing tool functions to return standardized responses
    2. Handles exceptions gracefully with error responses
    3. Auto-converts legacy return types to standard format
    4. Maintains function signature and docstring

    Args:
        func: The tool function to wrap

    Returns:
        Wrapped function that returns ToolResponse objects
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> ToolResponse:
        try:
            result = func(*args, **kwargs)

            # If already a ToolResponse, return as-is
            if isinstance(result, ToolResponse):
                return result

            # Convert legacy responses to standardized format
            return ToolResponseBuilder.from_legacy(result, func.__name__)

        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)

            # Extract function name for better error messages
            function_name = func.__name__

            # Determine error code based on exception type
            error_code = type(e).__name__

            # Build error details
            error_details = {
                "exception": str(e),
                "function": function_name,
                "args": [str(arg)[:100] for arg in args],  # Truncate long args
                "kwargs": {
                    k: str(v)[:100] for k, v in kwargs.items()
                },  # Truncate long values
            }

            return ToolResponseBuilder.error(
                message=f"Failed to execute {function_name}: {str(e)}",
                error_code=error_code,
                error_details=error_details,
            )

    return wrapper


def convert_to_dict(response: ToolResponse) -> dict:
    """
    Convert ToolResponse to dictionary for MCP compatibility.

    Args:
        response: ToolResponse object to convert

    Returns:
        Dictionary representation of the response
    """
    return response.model_dump(exclude_none=True)


def tool_response(func: Callable) -> Callable:
    """
    Decorator to standardize tool responses for MCP compatibility.

    This decorator:
    1. Standardizes the response using ToolResponseBuilder
    2. Converts the ToolResponse to a dictionary for MCP
    3. Handles exceptions automatically

    Args:
        func: The tool function to wrap

    Returns:
        Wrapped function that returns standardized dictionaries
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> dict:
        # First standardize the response
        standardized_func = standardize_response(func)
        response = standardized_func(*args, **kwargs)

        # Then convert to dictionary
        return convert_to_dict(response)

    return wrapper


def convert_resource_to_dict(response) -> dict:
    """Convert ResourceResponse to dictionary, excluding None values."""
    from .types import ResourceResponse

    if isinstance(response, ResourceResponse):
        return {k: v for k, v in response.model_dump().items() if v is not None}
    return response


def convert_prompt_to_dict(response) -> dict:
    """Convert PromptResponse to dictionary, excluding None values."""
    from .types import PromptResponse

    if isinstance(response, PromptResponse):
        return {k: v for k, v in response.model_dump().items() if v is not None}
    return response


def standardize_resource_response(func):
    """Decorator to standardize resource function responses."""
    from .types import ResourceResponse, ResourceResponseBuilder

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Look for URI on wrapper first (set after decoration), then func, then kwargs
        def get_uri():
            return getattr(
                wrapper,
                "uri",
                getattr(func, "uri", kwargs.get("uri", "unknown://resource")),
            )

        uri = kwargs.get("uri", get_uri())

        try:
            result = func(*args, **kwargs)

            # If already a ResourceResponse, return as-is
            if isinstance(result, ResourceResponse):
                return result

            # Convert legacy response
            return ResourceResponseBuilder.from_legacy(
                result, uri=uri, function_name=func.__name__
            )

        except Exception as e:
            return ResourceResponseBuilder.error(
                message=f"Failed to execute resource function {func.__name__}: {str(e)}",
                uri=uri,
                error_code=type(e).__name__,
                error_details={"exception": str(e), "function": func.__name__},
            )

    return wrapper


def standardize_prompt_response(func):
    """Decorator to standardize prompt function responses."""
    from .types import PromptResponse, PromptResponseBuilder

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)

            # If already a PromptResponse, return as-is
            if isinstance(result, PromptResponse):
                return result

            # Convert legacy response
            return PromptResponseBuilder.from_legacy(
                result, function_name=func.__name__, arguments=kwargs
            )

        except Exception as e:
            return PromptResponseBuilder.error(
                message=f"Failed to execute prompt function {func.__name__}: {str(e)}",
                error_code=type(e).__name__,
                error_details={"exception": str(e), "function": func.__name__},
                arguments=kwargs,
            )

    return wrapper


def resource_response(func):
    """Decorator that ensures resource functions return standardized dict responses."""
    from .types import ResourceResponse, ResourceResponseBuilder

    def get_uri():
        # Try to get URI from the wrapper function first
        return getattr(wrapper, "uri", getattr(func, "uri", "unknown://resource"))

    @wraps(func)
    def wrapper(*args, **kwargs):
        uri = kwargs.get("uri", get_uri())

        try:
            result = func(*args, **kwargs)

            # If already a ResourceResponse, convert to dict
            if isinstance(result, ResourceResponse):
                return convert_resource_to_dict(result)

            # Convert legacy response and then to dict
            response = ResourceResponseBuilder.from_legacy(
                result, uri=uri, function_name=func.__name__
            )
            return convert_resource_to_dict(response)

        except Exception as e:
            error_response = ResourceResponseBuilder.error(
                message=f"Failed to execute resource function {func.__name__}: {str(e)}",
                uri=uri,
                error_code=type(e).__name__,
                error_details={"exception": str(e), "function": func.__name__},
            )
            return convert_resource_to_dict(error_response)

    return wrapper


def prompt_response(func):
    """Decorator that ensures prompt functions return standardized dict responses."""
    from .types import PromptResponse, PromptResponseBuilder

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)

            # If already a PromptResponse, convert to dict
            if isinstance(result, PromptResponse):
                return convert_prompt_to_dict(result)

            # Convert legacy response and then to dict
            response = PromptResponseBuilder.from_legacy(
                result, function_name=func.__name__, arguments=kwargs
            )
            return convert_prompt_to_dict(response)

        except Exception as e:
            error_response = PromptResponseBuilder.error(
                message=f"Failed to execute prompt function {func.__name__}: {str(e)}",
                error_code=type(e).__name__,
                error_details={"exception": str(e), "function": func.__name__},
                arguments=kwargs,
            )
            return convert_prompt_to_dict(error_response)

    return wrapper
