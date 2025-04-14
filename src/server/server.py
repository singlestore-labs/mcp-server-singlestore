from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
import inspect
from typing import Optional
from mcp.server.fastmcp import FastMCP, Context

# Import tools from our definitions
from .tools import tools_dicts

# Store notes as a simple key-value dict to demonstrate state management
notes: dict[str, str] = {}

# Store custom text resources
custom_text_resources: dict[str, str] = {}

# Store session state for caching user inputs
session_state: dict[str, dict] = {}

@dataclass
class AppContext:
    """Application context for lifespan management"""
    notes: dict[str, str]
    custom_text_resources: dict[str, str]
    session_state: dict[str, dict]

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context"""
    # Initialize on startup
    try:
        yield AppContext(
            notes=notes,
            custom_text_resources=custom_text_resources,
            session_state=session_state
        )
    finally:
        # Cleanup on shutdown
        pass

# Create FastMCP server instance with lifespan
mcp = FastMCP(
    "SingleStore MCP Server", 
    lifespan=app_lifespan,
    dependencies=["mcp-server", "singlestoredb"]
)

# Register each tool using the proper FastMCP decorator pattern
# This dynamically creates tools from our definitions
for tool_def in tools_dicts:  # Use tools_dicts instead of tools_definitions
    # Extract tool information
    name = tool_def["name"]
    description = tool_def["description"]
    func = tool_def["func"]
    input_schema = tool_def["inputSchema"]
    
    # Create a wrapper that preserves the function signature and adds Context
    def create_tool_wrapper(tool_function, tool_name, tool_description):
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
    
    # Create the wrapper with proper signature
    tool_wrapper = create_tool_wrapper(func, name, description)
    
    # Register with FastMCP
    mcp.tool(name=name)(tool_wrapper)

def main():
    mcp.run()

# Add this block to run the main function when the script is executed directly
if __name__ == "__main__":
    main()
