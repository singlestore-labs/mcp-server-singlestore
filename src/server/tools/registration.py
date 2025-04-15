import inspect
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP, Context

def register_tools(mcp: FastMCP, tools_dicts: List[Dict[str, Any]]) -> None:
    """
    Register tools with the FastMCP server instance.
    
    Args:
        mcp: The FastMCP server instance
        tools_dicts: List of tool definition dictionaries
    """
    # Register each tool using the proper FastMCP decorator pattern
    for tool_def in tools_dicts:
        # Extract tool information
        name = tool_def["name"]
        description = tool_def["description"]
        func = tool_def["func"]
        
        # Create a wrapper that preserves the function signature and adds Context
        tool_wrapper = create_tool_wrapper(func, name, description)
        
        # Register with FastMCP
        mcp.tool(name=name)(tool_wrapper)


def create_tool_wrapper(tool_function, tool_name, tool_description):
    """
    Create a wrapper function that preserves the original function signature 
    and adds Context support.
    
    Args:
        tool_function: The original function to wrap
        tool_name: Name of the tool
        tool_description: Description of the tool
        
    Returns:
        An async wrapper function with the proper signature
    """
    # Get original signature to preserve parameter structure
    sig = inspect.signature(tool_function)
    
    # Create a dynamic function that matches the original signature
    if len(sig.parameters) == 0:
        # For functions with no parameters
        async def wrapper(ctx: Optional[Context] = None):
            return tool_function()
    else:
        # For functions with parameters
        # This creates a wrapper that matches the original signature
        param_names = list(sig.parameters.keys())
        
        # Use exec to dynamically create a function with the right signature
        # This preserves named parameters which is crucial for Pydantic validation
        function_def = f"async def dynamic_wrapper({', '.join(param_names)}, ctx: Optional[Context] = None):\n"
        function_def += f"    return tool_function({', '.join(param_names)})\n"
        
        # Create a local namespace to hold our dynamic function
        local_namespace = {}
        
        # Execute the function definition in this namespace
        exec(function_def, {"tool_function": tool_function, "Optional": Optional, "Context": Context}, local_namespace)
        
        # Get the created function from the namespace
        wrapper = local_namespace["dynamic_wrapper"]
    
    # Set docstring from description
    wrapper.__doc__ = tool_description
    wrapper.__name__ = tool_name
    
    return wrapper
