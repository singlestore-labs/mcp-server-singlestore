import asyncio

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl
import mcp.server.stdio
from .config import SINGLESTORE_API_KEY
from .tools import tools, tool_functions

# Store notes as a simple key-value dict to demonstrate state management
notes: dict[str, str] = {}

# Store custom text resources
custom_text_resources: dict[str, str] = {}

# Store session state for caching user inputs
session_state: dict[str, dict] = {}

server = Server("SingleStore MCP Server")


@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """
    List available note resources.
    Each note is exposed as a resource with a custom note:// URI scheme.
    """
    return [
        types.Resource(
            uri=AnyUrl(f"note://internal/{name}"),
            name=f"Note: {name}",
            description=f"A simple note named {name}",
            mimeType="text/plain",
        )
        for name in notes
    ]


@server.read_resource()
async def handle_read_resource(uri: AnyUrl) -> str:
    """
    Read a specific note's content by its URI.
    The note name is extracted from the URI host component.
    """
    if uri.scheme != "note":
        raise ValueError(f"Unsupported URI scheme: {uri.scheme}")

    name = uri.path
    if name is not None:
        name = name.lstrip("/")
        return notes[name]
    raise ValueError(f"Note not found: {name}")


@server.list_resources()
async def handle_list_custom_text_resources() -> list[types.Resource]:
    """
    List available custom text resources.
    Each resource is exposed with a custom text:// URI scheme.
    """
    return [
        types.Resource(
            uri=AnyUrl(f"text://internal/{name}"),
            name=f"Text Resource: {name}",
            description=f"A custom text resource named {name}",
            mimeType="text/plain",
        )
        for name in custom_text_resources
    ]


@server.read_resource()
async def handle_read_custom_text_resource(uri: AnyUrl) -> str:
    """
    Read a specific custom text resource's content by its URI.
    The resource name is extracted from the URI host component.
    """
    if uri.scheme != "text":
        raise ValueError(f"Unsupported URI scheme: {uri.scheme}")

    name = uri.path
    if name is not None:
        name = name.lstrip("/")
        return custom_text_resources[name]
    raise ValueError(f"Resource not found: {name}")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return tools


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    Tools can modify server state and notify clients of changes.
    """
    if name not in tool_functions:
        raise ValueError(f"Unknown tool: {name}")

    result = tool_functions[name](**arguments)

    return [types.TextContent(type="text", text=str(result))]


async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="SingleStore MCP Server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
                initialization_options={
                    "singlestore_api_key": SINGLESTORE_API_KEY,
                },
            ),
        )

# Add this block to run the main function when the script is executed directly
if __name__ == "__main__":
    asyncio.run(main())
