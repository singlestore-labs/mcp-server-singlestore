from functools import wraps
from typing import Callable, List
import inspect
from mcp.server.fastmcp import FastMCP

from src.api.common import filter_mcp_concepts
from .types import Tool
from .tools import tools as tool_list


def create_tool_wrapper(func: Callable, name: str, description: str):
    # Check if the function is async and has a Context parameter
    is_async = inspect.iscoroutinefunction(func)
    sig = inspect.signature(func)
    has_context = "ctx" in sig.parameters

    if is_async and has_context:
        # For async functions with Context, keep them as-is since FastMCP handles Context injection
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        async_wrapper.__name__ = name
        async_wrapper.__doc__ = description
        return async_wrapper
    elif has_context:
        # For sync functions with Context, wrap to handle Context properly
        @wraps(func)
        async def sync_with_context_wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        sync_with_context_wrapper.__name__ = name
        sync_with_context_wrapper.__doc__ = description
        return sync_with_context_wrapper
    else:
        # For regular functions without Context
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
