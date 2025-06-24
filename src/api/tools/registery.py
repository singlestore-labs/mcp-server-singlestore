from typing import List
from mcp.server.fastmcp import FastMCP

from src.api.common import filter_mcp_concepts
from .types import Tool
from .tools import tools as tool_list


def register_tools(mcp: FastMCP) -> None:
    filtered_tool: List[Tool] = filter_mcp_concepts(tool_list)

    for tool in filtered_tool:
        func = tool.func

        mcp.tool(name=func.__name__, description=func.__doc__)(func)
