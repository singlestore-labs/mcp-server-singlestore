import asyncio
import sys
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl
import mcp.server.stdio
import singlestoredb as s2
from my_server.tools import tools, tool_functions
from my_server.tools.config import settings

# Store notes as a simple key-value dict to demonstrate state management
notes: dict[str, str] = {}

# Store custom text resources
custom_text_resources: dict[str, str] = {}

if not settings.singlestore_api_key:
    print("Error: SingleStore API key is not defined. Please set the SINGLESTORE_API_KEY environment variable.")
    sys.exit(1)

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
            name="get-workspace-details",
            description="Get details of a specific workspace",
            arguments=[
                types.PromptArgument(
                    name="workspace_id",
                    description="ID of the workspace",
                    required=True,
                )
            ],
        ),
        types.Prompt(
            name="get-workspace-group-details",
            description="Get details of a specific workspace group",
            arguments=[
                types.PromptArgument(
                    name="workspace_group_id",
                    description="ID of the workspace group",
                    required=True,
                )
            ],
        ),
        types.Prompt(
            name="get-starter-workspace-details",
            description="Get details of a specific starter workspace",
            arguments=[
                types.PromptArgument(
                    name="starter_workspace_id",
                    description="ID of the starter workspace",
                    required=True,
                )
            ],
        )
    ]

@server.get_prompt()
async def handle_get_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    """
    Generate a prompt by combining arguments with server state.
    """
    if name == "get-workspace-details":
        workspace_id = arguments.get("workspace_id")
        if not workspace_id:
            raise ValueError("Missing workspace_id argument")

        manager = s2.manage_workspaces(access_token=settings.singlestore_api_key)
        workspace = manager.get_workspace(workspace_id)

        return types.GetPromptResult(
            description="Workspace details",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=(
                            f"Workspace ID: {workspace.id}\n"
                            f"Name: {workspace.name}\n"
                            f"State: {workspace.state}\n"
                            f"Created At: {workspace.created_at}\n"
                            f"Terminated At: {workspace.terminated_at}\n"
                            f"Endpoint: {workspace.endpoint}\n"
                            f"Auto Suspend: {workspace.auto_suspend}\n"
                            f"Cache Config: {workspace.cache_config}\n"
                            f"Deployment Type: {workspace.deployment_type}\n"
                            f"Scaling Progress: {workspace.scaling_progress}\n"
                            f"Last Resumed At: {workspace.last_resumed_at}\n"
                        ),
                    ),
                )
            ],
        )
    elif name == "get-workspace-group-details":
        workspace_group_id = arguments.get("workspace_group_id")
        if not workspace_group_id:
            raise ValueError("Missing workspace_group_id argument")

        manager = s2.manage_workspaces(access_token=settings.singlestore_api_key)
        workspace_group = manager.get_workspace_group(workspace_group_id)

        return types.GetPromptResult(
            description="Workspace Group details",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=(
                            f"Workspace Group ID: {workspace_group.id}\n"
                            f"Name: {workspace_group.name}\n"
                            f"Created At: {workspace_group.created_at}\n"
                            f"Region: {workspace_group.region}\n"
                            f"Firewall Ranges: {', '.join(workspace_group.firewall_ranges)}\n"
                            f"Terminated At: {workspace_group.terminated_at}\n"
                            f"Allow All Traffic: {workspace_group.allow_all_traffic}\n"
                        ),
                    ),
                )
            ],
        )
    elif name == "get-starter-workspace-details":
        starter_workspace_id = arguments.get("starter_workspace_id")
        if not starter_workspace_id:
            raise ValueError("Missing starter_workspace_id argument")

        manager = s2.manage_workspaces(access_token=settings.singlestore_api_key)
        starter_workspace = manager.get_starter_workspace(starter_workspace_id)

        return types.GetPromptResult(
            description="Starter Workspace details",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=(
                            f"Starter Workspace ID: {starter_workspace.id}\n"
                            f"Name: {starter_workspace.name}\n"
                        ),
                    ),
                )
            ],
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

    result = tool_functions[name]()
    try:
        import os
        tool_result_path = 'tool_result.txt'
        with open(tool_result_path, 'w') as f:
            f.write(str(result))
    except IOError as e:
        print(f"Error writing to file: {e}")
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
                    "singlestore_api_key": settings.singlestore_api_key,
                },
            ),
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
