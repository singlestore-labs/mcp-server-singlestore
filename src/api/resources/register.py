from functools import wraps
from typing import Callable, List
from mcp.server.fastmcp import FastMCP

from src.api.common import filter_mcp_concepts
from .types import Resource
from .resources import resources as resources_list


def create_resources_wrapper(func: Callable, name: str, description: str, uri: str):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    wrapper.__name__ = name
    wrapper.__doc__ = description
    wrapper.uri = uri
    return wrapper


def register_resources(mcp: FastMCP) -> None:
    filtered_resources: List[Resource] = filter_mcp_concepts(resources_list)

    for resource in filtered_resources:
        func = resource.func
        uri = resource.uri
        # Add context support for MCP
        wrapper = create_resources_wrapper(func, func.__name__, func.__doc__ or "", uri)

        mcp.resource(uri=uri, name=func.__name__, description=func.__doc__ or "")(
            wrapper
        )
