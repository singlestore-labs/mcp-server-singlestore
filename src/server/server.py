import asyncio

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions
from mcp.server.fastmcp import FastMCP
from pydantic import AnyUrl
import mcp.server.stdio
from .tools import tools, tool_functions

# Store notes as a simple key-value dict to demonstrate state management
notes: dict[str, str] = {}

# Store custom text resources
custom_text_resources: dict[str, str] = {}

# Store session state for caching user inputs
session_state: dict[str, dict] = {}

# Create FastMCP server instance
mcp = FastMCP("SingleStore MCP Server")


@mcp.resource("text://{name}")
def get_custom_text(name: str) -> str:
    """Read a specific custom text resource's content by its name."""
    if name in custom_text_resources:
        return custom_text_resources[name]
    raise ValueError(f"Resource not found: {name}")


# List resources
@mcp.list_resources()
def list_all_resources() -> list[types.Resource]:
    """List all available resources (notes and custom text)."""
    resources = []
    
    return resources


# Register tools with the @mcp.tool() decorator
for tool_name, tool_func in tool_functions.items():
    # Register each tool function with the FastMCP decorator
    decorated_func = mcp.tool()(tool_func)
    # Keep the original name since decorating might change it
    decorated_func.__name__ = tool_name
    
    # Optionally, add the decorated function back to globals()
    globals()[f"tool_{tool_name}"] = decorated_func


async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await mcp.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="SingleStore MCP Server",
                server_version="0.1.2",
                capabilities=mcp.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
            ),
        )

# Add this block to run the main function when the script is executed directly
if __name__ == "__main__":
    asyncio.run(main())
