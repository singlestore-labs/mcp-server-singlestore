"""
Response standardization module for SingleStore MCP Server.

This module provides:
- Standardized response types (ToolResponse, ResourceResponse, PromptResponse)
- Response builder patterns (ToolResponseBuilder, ResourceResponseBuilder, PromptResponseBuilder)
- Decorators for automatic response standardization
- Legacy response conversion utilities

Usage:
    from src.api.responses import ToolResponseBuilder, tool_response

    @tool_response
    def my_tool(ctx: Context) -> Dict[str, Any]:
        return {"result": "success"}

    @resource_response
    def my_resource() -> str:
        return "resource content"

    @prompt_response
    def my_prompt(**kwargs) -> str:
        return "prompt content"
"""

from .types import (
    ResponseStatus,
    ToolResponse,
    ToolResponseBuilder,
    ResourceResponse,
    PromptResponse,
    ResourceResponseBuilder,
    PromptResponseBuilder,
)

from .decorators import (
    standardize_response,
    convert_to_dict,
    tool_response,
    convert_resource_to_dict,
    convert_prompt_to_dict,
    standardize_resource_response,
    standardize_prompt_response,
    resource_response,
    prompt_response,
)

__all__ = [
    # Core tool response system
    "ResponseStatus",
    "ToolResponse",
    "ToolResponseBuilder",
    "standardize_response",
    "convert_to_dict",
    "tool_response",
    # MCP resource response system
    "ResourceResponse",
    "ResourceResponseBuilder",
    "convert_resource_to_dict",
    "standardize_resource_response",
    "resource_response",
    # MCP prompt response system
    "PromptResponse",
    "PromptResponseBuilder",
    "convert_prompt_to_dict",
    "standardize_prompt_response",
    "prompt_response",
]
