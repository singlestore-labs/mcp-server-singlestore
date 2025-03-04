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
from my_server.tools.definitions import __build_request

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
        ),
        types.Prompt(
            name="execute_sql",
            description="Execute SQL operations on a connected workspace.",
            arguments=[
                {
                    "name": "workspace_identifier",
                    "type": "string",
                    "description": "The ID or name of the workspace to connect to."
                },
                {
                    "name": "workspaceGroup_identifier",
                    "type": "string",
                    "description": "The ID or name of the workspace group to connect to."
                },
                {
                    "name": "username",
                    "type": "string",
                    "description": "The username to connect to the workspace."
                },
                {
                    "name": "password",
                    "type": "string",
                    "description": "The password to connect to the workspace."
                },
                {
                    "name": "database",
                    "type": "string",
                    "description": "The database to connect to."
                },
                {
                    "name": "sql_query",
                    "type": "string",
                    "description": "The SQL query to execute."
                }
            ]
        )
    ]

async def list_all_workspaces() -> list[dict]:
    """
    List all available workspaces.
    """
    response = tool_functions["workspaces_info"]()
    if not response:
        raise ValueError("Failed to retrieve workspaces")
    return response

async def list_all_workspace_groups() -> list[dict]:
    """
    List all available workspace groups.
    """
    response = tool_functions["workspace_groups_info"]()
    if not response:
        raise ValueError("Failed to retrieve workspace groups")
    return response

async def find_workspace_group(workspace_group_identifier: str) -> dict:
    """
    Find a workspace group by its name or ID.
    """
    workspace_groups = await list_all_workspace_groups()
    for workspace_group in workspace_groups:
        if workspace_group["workspaceGroupID"] == workspace_group_identifier or workspace_group["name"] == workspace_group_identifier:
            return workspace_group
    raise ValueError(f"Workspace group not found: {workspace_group_identifier}")

async def get_workspace_group_id(workspace_group_identifier: str) -> str:
    """
    Get the ID of a workspace group by its name or ID.
    """
    workspace_group = await find_workspace_group(workspace_group_identifier)
    return workspace_group["workspaceGroupID"]

async def find_workspace(workspace_group_identifier: str, workspace_identifier: str) -> dict:
    """
    Find a workspace by its name or ID within a specific workspace group.
    """
    workspace_group_id = await get_workspace_group_id(workspace_group_identifier)
    workspaces = tool_functions["workspaces_info"](workspace_group_id)
    for workspace in workspaces:
        if workspace["workspaceID"] == workspace_identifier or workspace["name"] == workspace_identifier:
            return workspace
    raise ValueError(f"Workspace not found: {workspace_identifier}")

async def get_workspace_endpoint(workspace_group_identifier: str, workspace_identifier: str) -> str:
    """
    Retrieve the endpoint of a specific workspace by its name or ID within a specific workspace group.
    """
    workspace = await find_workspace(workspace_group_identifier, workspace_identifier)
    return workspace["endpoint"]

async def execute_sql(workspace_group_identifier: str, workspace_identifier: str, username: str, password: str, database: str, sql_query: str) -> dict:
    """
    Execute SQL operations on a connected workspace.
    Returns results and column names in a dictionary format.
    """
    endpoint = await get_workspace_endpoint(workspace_group_identifier, workspace_identifier)
    if not endpoint:
        raise ValueError(f"Endpoint not found for workspace: {workspace_identifier}")

    connection = s2.connect(
        host=endpoint,
        user=username,
        password=password,
        database=database
    )
    cursor = connection.cursor()
    cursor.execute(sql_query)
    
    # Get column names
    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    
    # Get results
    rows = cursor.fetchall()
    
    # Format results as list of dictionaries
    results = []
    for row in rows:
        result_dict = {}
        for i, column in enumerate(columns):
            result_dict[column] = row[i]
        results.append(result_dict)
    
    cursor.close()
    connection.close()
    
    return {
        "data": results,
        "row_count": len(rows)
    }


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
    if name == "get_workspace_endpoint" or name == "execute_sql":
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
    elif name == "execute_sql":
        workspace_group_identifier = effective_arguments.get("workspaceGroup_identifier")
        workspace_identifier = effective_arguments.get("workspace_identifier")
        username = effective_arguments.get("username")
        password = effective_arguments.get("password")
        database = effective_arguments.get("database")
        sql_query = effective_arguments.get("sql_query")
        
        # Check for required fields
        missing = []
        if not workspace_group_identifier: missing.append("workspaceGroup_identifier")
        if not workspace_identifier: missing.append("workspace_identifier")
        if not username: missing.append("username")
        if not password: missing.append("password")
        if not database: missing.append("database")
        if not sql_query: missing.append("sql_query")
        
        if missing:
            return types.GetPromptResult(
                result=f"Missing required arguments: {', '.join(missing)}",
                messages=[]
            )
            
        result = await execute_sql(workspace_group_identifier, workspace_identifier, username, password, database, sql_query)
        return types.GetPromptResult(
            result=result,
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
