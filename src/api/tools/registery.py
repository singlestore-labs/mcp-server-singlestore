from functools import wraps
from typing import Callable, List
from mcp.server.fastmcp import FastMCP

from src.api.common import filter_mcp_concepts
from .types import Tool
from .tools import tools as tool_list


def create_tool_wrapper(func: Callable, name: str, description: str):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    wrapper.__name__ = name
    wrapper.__doc__ = description
    return wrapper


def register_tools(mcp: FastMCP) -> None:
    filtered_tool: List[Tool] = filter_mcp_concepts(tool_list)

    for tool in filtered_tool:
        func = tool.func
        # Add context support for MCP
        wrapper = create_tool_wrapper(func, func.__name__, func.__doc__ or "")

        mcp.tool(name=func.__name__, description=func.__doc__ or "")(wrapper)
