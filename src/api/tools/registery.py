from typing import List
from mcp.server.fastmcp import FastMCP

from src.api.common import get_active_mcp_concepts
from .types import Tool
from .tools import tools as tool_list
from src.logger import get_logger

logger = get_logger()


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

    filtered_tools: List[Tool] = get_active_mcp_concepts(tool_list)

    # Check if we're using API key authentication in local mode
    settings = get_settings()
    using_api_key = isinstance(settings, LocalSettings) and (
        settings.api_key or settings.jwt_token and settings.org_id
    )

    # List of tools to exclude when using API key authentication
    api_key_excluded_tools = ["choose_organization", "set_organization"]

    for tool in filtered_tools:
        func = tool.func
        # Skip if func is not defined
        if func is None:
            logger.warning(f"Tool {tool.title} has no associated function, skipping.")
            continue
        # Skip organization-related tools when using API key authentication
        if using_api_key and func.__name__ in api_key_excluded_tools:
            continue
        mcp.tool(name=func.__name__, description=func.__doc__)(func)
