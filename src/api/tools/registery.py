from typing import List
from mcp.server.fastmcp import FastMCP

from src.api.common import filter_tools_by_flags
from .types import Tool
from .tools import tools as tool_list


def filter_tools(**flag_filters) -> List[Tool]:
    """
    Filter tools by flag names - SUPER SIMPLE!

    Args:
        **flag_filters: Flag names with True/False values

    Examples:
        # Get only private tools
        filter_tools(private=True)

        # Get public tools (non-private, non-deprecated)
        filter_tools(private=False, deprecated=False)
    """
    return filter_tools_by_flags(tool_list, **flag_filters)


def register_tools(mcp: FastMCP, **filter_flags) -> None:
    """
    Register tools with the MCP server with optional filtering.

    Args:
        mcp: FastMCP server instance
        **filter_flags: Optional flag filters to apply

    Examples:
        # Register all public tools (default)
        register_tools(mcp)

        # Register only public tools explicitly
        register_tools(mcp, private=False, deprecated=False)
    """
    # Import here to avoid circular imports
    from src.config.config import get_settings, LocalSettings

    # Default: only register public tools (non-private, non-deprecated)
    if not filter_flags:
        filter_flags = {"internal": False, "deprecated": False}

    filtered_tools: List[Tool] = filter_tools(**filter_flags)

    # Check if we're using API key authentication in local mode
    settings = get_settings()
    using_api_key = (
        not settings.is_remote
        and isinstance(settings, LocalSettings)
        and settings.api_key
    )

    # List of tools to exclude when using API key authentication
    api_key_excluded_tools = ["choose_organization", "set_organization"]

    for tool in filtered_tools:
        func = tool.func
        # Skip organization-related tools when using API key authentication
        if using_api_key and func.__name__ in api_key_excluded_tools:
            continue
        mcp.tool(name=func.__name__, description=func.__doc__)(func)
