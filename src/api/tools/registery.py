from functools import wraps
from typing import Callable
from mcp.server.fastmcp import FastMCP

from .tools import tools as tool_list
from .types import Tool


def filter_tools(tools: list[Tool]) -> list[Tool]:
    """
    Filter tools to exclude deprecated ones.
    """
    return [tool for tool in tools if not tool.deprecated]


def create_tool_wrapper(func: Callable, name: str, description: str):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    wrapper.__name__ = name
    wrapper.__doc__ = description
    return wrapper


def register_tools(mcp: FastMCP) -> None:
    filtered_tool = filter_tools(tool_list)

    for tool in filtered_tool:
        func: Callable = tool.func
        # Add context support for MCP
        wrapper = create_tool_wrapper(func, func.__name__, func.__doc__ or "")

        mcp.tool(name=func.__name__, description=func.__doc__ or "")(wrapper)
