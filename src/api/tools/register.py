import inspect
from typing import List, Optional
from mcp.server.fastmcp import FastMCP, Context

from src.api.tools.tools import Tool


def register_tools(mcp: FastMCP, tools: List[Tool]) -> None:
    """
    Register tools with the FastMCP server instance.

    Args:
        mcp: The FastMCP server instance
        tools: List of tool definition dictionaries
    """
    # Register each tool using the proper FastMCP decorator pattern
    for tool_def in tools:
        # Extract tool information
        name = tool_def.name
        description = tool_def.description
        func = tool_def.func

        # Create a wrapper that preserves the function signature and adds Context
        tool_wrapper = _create_tool_wrapper(func, name, description)

        # Register with FastMCP
        mcp.tool(name=name, description=description)(tool_wrapper)


def _create_tool_wrapper(function, name, description):
    """
    Create a wrapper function that preserves the original function signature
    and adds Context support for tools.

    Args:
        function: The original function to wrap
        name: Name of the tool
        description: Description of the tool

    Returns:
        An async wrapper function with the proper signature
    """
    # Get original signature to preserve parameter structure
    sig = inspect.signature(function)

    # Create a dynamic function that matches the original signature
    if len(sig.parameters) == 0:
        # For functions with no parameters
        async def wrapper(ctx: Optional[Context] = None):
            return function()

    else:
        # For functions with parameters
        param_names = list(sig.parameters.keys())

        local_namespace = {}
        # Create a local namespace to hold our dynamic function

        function_def = f"async def dynamic_wrapper({', '.join(param_names)}, ctx: Optional[Context] = None):\n"
        function_def += f"    return function({', '.join(param_names)})\n"

        exec(
            function_def,
            {
                "function": function,
                "Optional": Optional,
                "Context": Context,
            },
            local_namespace,
        )

        # Get the created function from the namespace
        wrapper = local_namespace["dynamic_wrapper"]

    # Set docstring from description
    wrapper.__doc__ = description
    wrapper.__name__ = name

    return wrapper
