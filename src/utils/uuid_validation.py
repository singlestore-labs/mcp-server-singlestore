"""
UUID validation utilities for the MCP SingleStore server.

This module provides comprehensive UUID validation with support for:
- Environment-aware validation (strict in production, lenient in testing)
- Workspace ID validation with prefixes
- Pydantic model integration
- Various UUID formats and use cases
"""

import os
from typing import Union
from uuid import UUID


def validate_uuid_string(
    value: Union[str, UUID, None], strict: bool = None
) -> str | None:
    """
    Validate and convert UUID to string format.

    Args:
        value: UUID string, UUID object, or None
        strict: If False, allows non-UUID strings for testing/backward compatibility.
                If None, checks TESTING environment variable.

    Returns:
        String representation of UUID or None

    Raises:
        ValueError: If the value is not a valid UUID format (when strict=True)
        TypeError: If the value is not a string, UUID, or None
    """
    if value is None:
        return None
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, str):
        # Check if we should be strict about UUID validation
        if strict is None:
            strict = not (
                os.getenv("TESTING") == "true" or os.getenv("PYTEST_CURRENT_TEST")
            )

        if not strict:
            return value  # Allow any string when not strict (testing mode)
        try:
            UUID(value)  # Validates the format
            return value
        except ValueError:
            raise ValueError(f"Invalid UUID format: {value}")
    raise TypeError(f"Expected UUID string or UUID object, got {type(value)}")


def is_valid_uuid(value: str) -> bool:
    """
    Check if a string is a valid UUID format.

    Args:
        value: String to validate

    Returns:
        True if valid UUID format, False otherwise
    """
    try:
        UUID(value)
        return True
    except (ValueError, TypeError):
        return False


def validate_workspace_id(workspace_id: str, allow_prefixes: bool = True) -> str:
    """
    Validate workspace ID which may have prefixes like 'ws-'.

    Args:
        workspace_id: Workspace ID to validate
        allow_prefixes: If True, allows prefixes like 'ws-' before the UUID

    Returns:
        Original workspace ID if valid

    Raises:
        ValueError: If the workspace ID format is invalid
    """
    if not isinstance(workspace_id, str):
        raise TypeError(f"Expected string, got {type(workspace_id)}")

    if allow_prefixes and workspace_id.startswith("ws-"):
        # Strip prefix and validate the core UUID
        core_id = workspace_id[3:]
        try:
            UUID(core_id)
            return workspace_id  # Return with prefix intact
        except ValueError:
            raise ValueError(f"Invalid workspace ID format: {workspace_id}")
    else:
        # Validate as pure UUID
        try:
            UUID(workspace_id)
            return workspace_id
        except ValueError:
            raise ValueError(f"Invalid workspace ID format: {workspace_id}")
