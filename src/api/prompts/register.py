from typing import List
from mcp.server.fastmcp import FastMCP

from src.api.common import filter_mcp_concepts

from .types import Prompt
from .prompts import prompts as prompts_list


def register_prompts(mcp: FastMCP) -> None:
    filtered_prompts: List[Prompt] = filter_mcp_concepts(prompts_list)

    for prompt in filtered_prompts:
        func = prompt.func
        mcp.prompt(
            name=func.__name__, description=func.__doc__ or "", title=prompt.title
        )(func)
