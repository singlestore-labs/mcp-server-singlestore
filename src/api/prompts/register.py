from functools import wraps
from typing import Callable, List
from mcp.server.fastmcp import FastMCP

from src.api.common import filter_mcp_concepts

from .types import Prompt
from .prompts import prompts as prompts_list


def create_prompts_wrapper(func: Callable, name: str, description: str):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    wrapper.__name__ = name
    wrapper.__doc__ = description
    return wrapper


def register_prompts(mcp: FastMCP) -> None:
    filtered_prompts: List[Prompt] = filter_mcp_concepts(prompts_list)

    for prompt in filtered_prompts:
        func = prompt.func
        # Add context support for MCP
        wrapper = create_prompts_wrapper(func, func.__name__, func.__doc__ or "")

        mcp.prompt(name=func.__name__, description=func.__doc__ or "")(wrapper)
