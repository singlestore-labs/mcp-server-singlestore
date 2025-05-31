import inspect
from typing import List
from mcp.server.fastmcp import FastMCP

from src.api.resources.resources import Resource


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

        # Create a wrapper that preserves the function signature
        resource_wrapper = _create_resource_wrapper(func, name, description, uri)

        # Register with FastMCP
        mcp.resource(name=name, description=description, uri=uri)(resource_wrapper)


def _create_resource_wrapper(function, name, description, uri):
    """
    Create a wrapper function that preserves the original function signature
    for resources.

    Args:
        function: The original function to wrap
        name: Name of the resource
        description: Description of the resource
        uri: URI of the resource

    Returns:
        An async wrapper function with the proper signature
    """
    # Get original signature to preserve parameter structure
    sig = inspect.signature(function)

    # Create a dynamic function that matches the original signature
    if len(sig.parameters) == 0:
        # For functions with no parameters
        async def wrapper():
            return function()

    else:
        # For functions with parameters
        param_names = list(sig.parameters.keys())

        local_namespace = {}
        # Create a local namespace to hold our dynamic function

        function_def = f"async def dynamic_wrapper({', '.join(param_names)}):\n"
        function_def += f"    return function({', '.join(param_names)})\n"
        exec(function_def, {"function": function}, local_namespace)

        # Get the created function from the namespace
        wrapper = local_namespace["dynamic_wrapper"]

    # Set docstring from description
    wrapper.__doc__ = description
    wrapper.__name__ = name

    # If URI is provided, set it as an attribute for resources
    wrapper.uri = uri

    return wrapper
