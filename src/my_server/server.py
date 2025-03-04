import asyncio

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl
import mcp.server.stdio
import singlestoredb as s2
from config import SINGLESTORE_API_KEY
import singlestoredb as s2
from my_server.tools import tools, tool_functions

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


@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    """
    List available prompts.
    Each prompt can have optional arguments to customize its behavior.
    """
    return [
        types.Prompt(
            name="list_resources",
            description="List all available resources managed by the server."
        ),
        types.Prompt(
            name="get_resource_details",
            description="Get detailed information about a specific resource.",
            arguments=[
                {
                    "name": "resource_id",
                    "type": "string",
                    "description": "The ID of the resource to retrieve details for."
                }
            ]
        ),
        types.Prompt(
            name="server_status",
            description="Check the current status of the server."
        ),
        types.Prompt(
            name="get_workspace_endpoint",
            description="Get the endpoint of a specific workspace.",
            arguments=[
                {
                    "name": "workspace_identifier",
                    "type": "string",
                    "description": "The ID or name of the workspace to retrieve the endpoint for."
                },
                {
                    "name": "workspaceGroup_identifier",
                    "type": "string",
                    "description": "The ID or name of the workspace group to retrieve the endpoint for."
                }
            ]
        )
    ]

@server.get_prompt()
async def handle_get_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    """
    Generate a prompt by combining arguments with server state.
    """
    # Get user session ID - if not provided, use a default
    user_id = arguments.get("user_id", "default_user") if arguments else "default_user"
    
    # Initialize session state for this user if it doesn't exist
    if user_id not in session_state:
        session_state[user_id] = {}
    
    # Update session state with any provided arguments
    if arguments:
        for key, value in arguments.items():
            if value and key not in ["user_id"]:  # Don't store the user_id itself in the state
                session_state[user_id][key] = value
    
    # Use cached values for missing arguments
    effective_arguments = {}
    if arguments:
        effective_arguments.update(arguments)
    
    # Fill in missing arguments from session state
    if name == "get_workspace_endpoint":
        for arg_name in ["workspace_identifier", "workspaceGroup_identifier", "username", "password", "database"]:
            if (arg_name not in effective_arguments or not effective_arguments.get(arg_name)) and arg_name in session_state[user_id]:
                effective_arguments[arg_name] = session_state[user_id][arg_name]
                
    # Now handle the prompts with potentially filled-in arguments
    if name == "list_resources":
        resources = await handle_list_resources()
        return types.GetPromptResult(
            result=[resource.name for resource in resources],
            messages=[]
        )
    elif name == "get_resource_details":
        resource_id = effective_arguments.get("resource_id")
        resource = await handle_read_resource(AnyUrl(f"note://internal/{resource_id}"))
        return types.GetPromptResult(
            result=resource,
            messages=[]
        )
    elif name == "server_status":
        return types.GetPromptResult(
            result="Server is running and operational.",
            messages=[]
        )
    elif name == "get_workspace_endpoint":
        workspace_group_identifier = effective_arguments.get("workspaceGroup_identifier")
        workspace_identifier = effective_arguments.get("workspace_identifier")
        
        if not workspace_group_identifier or not workspace_identifier:
            return types.GetPromptResult(
                result="Missing required arguments. Please provide both workspace_identifier and workspaceGroup_identifier.",
                messages=[]
            )
            
        endpoint = await get_workspace_endpoint(workspace_group_identifier, workspace_identifier)
        return types.GetPromptResult(
            result=endpoint,
            messages=[]
        )
    else:
        raise ValueError(f"Unknown prompt: {name}")


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

    return [
        types.TextContent(
            type="text",
            text=str(result)
        )
    ]

async def run():
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


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())
