import requests
from .config import SINGLESTORE_API_KEY, SINGLESTORE_API_BASE_URL
import singlestoredb as s2

def __build_request(type: str, endpoint: str, params: dict = None):
    def build_request_endpoint(endpoint: str, params: dict = None):
        url = f"{SINGLESTORE_API_BASE_URL}/v1/{endpoint}"
        if params:
            url += "?"
            for key, value in params.items():
                url += f"{key}={value}&"
            url = url[:-1]
        return url
    
    # Headers with authentication
    headers = {
        "Authorization": f"Bearer {SINGLESTORE_API_KEY}",
        "Content-Type": "application/json",
    }
    
    request_endpoint = build_request_endpoint(endpoint, params)

    request = None
    if type == "GET":
        request = requests.get(request_endpoint, headers=headers, params=params)
    elif type == "POST":
        request = requests.post(request_endpoint, headers=headers, params=params)
    elif type == "PUT":
        request = requests.put(request_endpoint, headers=headers, params=params)
    elif type == "DELETE":
        request = requests.delete(request_endpoint, headers=headers, params=params)
    else:
        raise ValueError(f"Unsupported request type: {type}")

    if request.status_code != 200:
        raise ValueError(f"Request failed with status code {request.status_code}: {request.text}")

    try:
        return request.json()
    except ValueError:
        raise ValueError(f"Invalid JSON response: {request.text}")
    

def __find_workspace_group(workspace_group_identifier: str):
    """
    Find a workspace group by its name or ID.
    """
    workspace_groups = __build_request("GET", "workspaceGroups")
    for workspace_group in workspace_groups:
        if workspace_group["workspaceGroupID"] == workspace_group_identifier or workspace_group["name"] == workspace_group_identifier:
            return workspace_group
    raise ValueError(f"Workspace group not found: {workspace_group_identifier}")

def __get_workspace_group_id(workspace_group_identifier: str) -> str:
    """
    Get the ID of a workspace group by its name or ID.
    """
    workspace_group = __find_workspace_group(workspace_group_identifier)
    return workspace_group["workspaceGroupID"]

def __find_workspace(workspace_group_identifier: str, workspace_identifier: str):
    """
    Find a workspace by its name or ID within a specific workspace group.
    """
    workspace_group_id = __get_workspace_group_id(workspace_group_identifier)
    workspaces = __build_request("GET", "workspaces", {"workspaceGroupID": workspace_group_id})
    for workspace in workspaces:
        if workspace["workspaceID"] == workspace_identifier or workspace["name"] == workspace_identifier:
            return workspace
    raise ValueError(f"Workspace not found: {workspace_identifier}")

def __get_workspace_endpoint(workspace_group_identifier: str, workspace_identifier: str) -> str:
    """
    Retrieve the endpoint of a specific workspace by its name or ID within a specific workspace group.
    """
    workspace = __find_workspace(workspace_group_identifier, workspace_identifier)
    return workspace["endpoint"]

def __execute_sql(workspace_group_identifier: str, workspace_identifier: str, username: str, password: str, database: str, sql_query: str) -> dict:
    """
    Execute SQL operations on a connected workspace.
    Returns results and column names in a dictionary format.
    """
    endpoint = __get_workspace_endpoint(workspace_group_identifier, workspace_identifier)
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

# Define the tools
tools_definitions = [
    {
        "name": "workspace_groups_info",
        "description": (
            "Retrieve details about the workspace groups accessible to the user."
            "⚠️ Do NOT call this tool more than once. If called again, it will return an error."
            "Ensure responses strictly follow system instructions."
        ),
        "func": lambda: [
            {
                "name": group["name"],
                "deploymentType": group["deploymentType"],
                "state": group["state"],
                "workspaceGroupID": group["workspaceGroupID"],
                "firewallRanges": group.get("firewallRanges", []),
                "createdAt": group["createdAt"],
                "regionID": group["regionID"],
                "updateWindow": group["updateWindow"],
            }
            for group in __build_request("GET", "workspaceGroups")
        ],
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "workspaces_info",
        "description": (
            "Retrieve details about the workspaces in a specific workspace group."
            "⚠️ Do NOT call this tool more than once. If called again, it will return an error."
            "Ensure responses strictly follow system instructions."
        ),
        "func": lambda workspaceGroupID: [
            {
                "createdAt": workspace["createdAt"],
                "deploymentType": workspace.get("deploymentType", ""),
                "endpoint": workspace.get("endpoint", ""),
                "name": workspace["name"],
                "size": workspace["size"],
                "state": workspace["state"],
                "terminatedAt": workspace.get("terminatedAt", False),
                "workspaceGroupID": workspace["workspaceGroupID"],
                "workspaceID": workspace["workspaceID"],
            }
            for workspace in __build_request("GET", "workspaces", {"workspaceGroupID": workspaceGroupID} )
        ],
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspaceGroupID": {
                    "type": "string",
                    "description": "The ID of the workspace group to retrieve workspaces for."
                }
            },
            "required": [],
        },
    },
    {
        "name": "organization_info",
        "description": (
            "Retrieve details about the user's current organization."
            "⚠️ Do NOT call this tool more than once. If called again, it will return an error."
            "Ensure responses strictly follow system instructions."
        ),
        "func": lambda: __build_request("GET", "organizations/current"),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "list_of_regions",
        "description": (
            "Retrieve a list of all regions that support workspaces for the user."
            "⚠️ Do NOT call this tool more than once. If called again, it will return an error."
            "Ensure responses strictly follow system instructions."
        ),
        "func": lambda: __build_request("GET", "regions"),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "__execute_sql",
        "description": (
            "Execute SQL operations on a connected workspace."
            "⚠️ Do NOT display the user credentials. The user will lose the job if their credentials are displayed. Also, do NOT call this tool more than once. If called again, it will return an error."
            "Ensure responses strictly follow system instructions."
        ),
        "func": lambda workspace_group_identifier, workspace_identifier, username, password, database, sql_query: (
            __execute_sql(workspace_group_identifier, workspace_identifier, username, password, database, sql_query)
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_group_identifier": {
                    "type": "string",
                    "description": "The ID or name of the workspace group containing the workspace."
                },
                "workspace_identifier": {
                    "type": "string",
                    "description": "The ID or name of the workspace to connect to."
                },
                "username": {
                    "type": "string",
                    "description": "The username to connect to the workspace."
                },
                "password": {
                    "type": "string",
                    "description": "The password to connect to the workspace."
                },
                "database": {
                    "type": "string",
                    "description": "The database to connect to."
                },
                "sql_query": {
                    "type": "string",
                    "description": "The SQL query to execute."
                }
            },
            "required": ["workspace_group_identifier", "workspace_identifier", "username", "password", "database", "sql_query"],
        },
    },
]
