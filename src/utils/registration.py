import inspect
from typing import List, Optional
from mcp.server.fastmcp import FastMCP, Context

from src.utils.types import Resource, Tool

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
        tool_wrapper = create_mcp_concept_wrapper(func, name, description)
        
        # Register with FastMCP
        mcp.tool(name=name, description=description)(tool_wrapper)

def register_resources(mcp: FastMCP, resources: List[Resource]) -> None:
    """
    Register resources with the FastMCP server instance.
    
    Args:
        mcp: The FastMCP server instance
        resources: List of resource definition dictionaries
    """
    # Register each resource using the proper FastMCP decorator pattern
    for resource_def in resources:
        # Extract resource information
        name = resource_def.name
        description = resource_def.description
        func = resource_def.func
        uri = resource_def.uri
        
        # Create a wrapper that preserves the function signature and adds Context
        resource_wrapper = create_mcp_concept_wrapper(func, name, description, uri)
        
        # Register with FastMCP
        mcp.resource(name=name, description=description, uri=uri)(resource_wrapper)


def create_mcp_concept_wrapper(function, name, description, uri=None):
    """
    Create a wrapper function that preserves the original function signature 
    and adds Context support for tools. For resources, Context is not added.
    
    Args:
        function: The original function to wrap
        name: Name of the tool or resource
        description: Description of the tool or resource
        uri: Optional URI for resources
        
    Returns:
        An async wrapper function with the proper signature
    """
    # Get original signature to preserve parameter structure
    sig = inspect.signature(function)
    
    # Determine if this is a resource (no Context) or a tool (with Context)
    is_resource = uri is not None

    # Create a dynamic function that matches the original signature
    if len(sig.parameters) == 0:
        # For functions with no parameters
        if is_resource:
            async def wrapper():
                return function()
        else:
            async def wrapper(ctx: Optional[Context] = None):
                return function()
    else:
        # For functions with parameters
        param_names = list(sig.parameters.keys())
        
        local_namespace = {}
        # Create a local namespace to hold our dynamic function

        # Use exec to dynamically create a function with the right signature
        if is_resource:
            function_def = f"async def dynamic_wrapper({', '.join(param_names)}):\n"
            function_def += f"    return function({', '.join(param_names)})\n"
            exec(function_def, {"function": function}, local_namespace)

        else:
            function_def = f"async def dynamic_wrapper({', '.join(param_names)}, ctx: Optional[Context] = None):\n"
            function_def += f"    return function({', '.join(param_names)})\n"

            exec(function_def, {"function": function, "Optional": Optional, "Context": Context}, local_namespace)
        
        # Get the created function from the namespace
        wrapper = local_namespace["dynamic_wrapper"]
    
    # Set docstring from description
    wrapper.__doc__ = description
    wrapper.__name__ = name
    
    # If URI is provided, set it as an attribute for resources
    if uri:
        wrapper.uri = uri
    
    return wrapper
