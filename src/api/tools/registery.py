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

        # Get remote experimental tools
        filter_tools(remote=True, experimental=True)

        # Get admin tools that aren't deprecated
        filter_tools(admin=True, deprecated=False)

        # Get beta tools
        filter_tools(beta=True)
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
    # Default: only register public tools (non-private, non-deprecated)
    if not filter_flags:
        filter_flags = {"internal": False, "deprecated": False}

    filtered_tools: List[Tool] = filter_tools(**filter_flags)

    for tool in filtered_tools:
        func = tool.func
        mcp.tool(name=func.__name__, description=func.__doc__)(func)
