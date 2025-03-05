import requests
from my_server.config import (
    SINGLESTORE_API_KEY,
    SINGLESTORE_API_BASE_URL,
    SINGLESTORE_DB_PASSWORD,
    SINGLESTORE_DB_USERNAME,
)
import singlestoredb as s2
import json


def __build_request(type: str, endpoint: str, params: dict = None, data: dict = None):
    """
    Make an API request to the SingleStore Management API.

    Args:
        type: HTTP method (GET, POST, PUT, DELETE)
        endpoint: API endpoint path
        params: Query parameters
        data: Request body for POST/PUT/PATCH requests

    Returns:
        JSON response from the API
    """

    def build_request_endpoint(endpoint: str, params: dict = None):
        url = f"{SINGLESTORE_API_BASE_URL}/v1/{endpoint}"
        if params and type == "GET":  # Only add query params for GET requests
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

    # Default empty JSON body for POST/PUT requests if none provided
    if data is None and type in ["POST", "PUT", "PATCH"]:
        data = {}

    # Convert dict to JSON string for request body
    json_data = json.dumps(data) if data is not None else None

    request = None
    if type == "GET":
        request = requests.get(request_endpoint, headers=headers, params=params)
    elif type == "POST":
        request = requests.post(request_endpoint, headers=headers, data=json_data)
    elif type == "PUT":
        request = requests.put(request_endpoint, headers=headers, data=json_data)
    elif type == "PATCH":
        request = requests.patch(request_endpoint, headers=headers, data=json_data)
    elif type == "DELETE":
        request = requests.delete(request_endpoint, headers=headers)
    else:
        raise ValueError(f"Unsupported request type: {type}")

    if request.status_code != 200:
        raise ValueError(
            f"Request failed with status code {request.status_code}: {request.text}"
        )

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
        if (
            workspace_group["workspaceGroupID"] == workspace_group_identifier
            or workspace_group["name"] == workspace_group_identifier
        ):
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
    workspaces = __build_request(
        "GET", "workspaces", {"workspaceGroupID": workspace_group_id}
    )
    for workspace in workspaces:
        if (
            workspace["workspaceID"] == workspace_identifier
            or workspace["name"] == workspace_identifier
        ):
            return workspace
    raise ValueError(f"Workspace not found: {workspace_identifier}")


def __get_workspace_endpoint(
    workspace_group_identifier: str, workspace_identifier: str
) -> str:
    """
    Retrieve the endpoint of a specific workspace by its name or ID within a specific workspace group.
    """
    workspace = __find_workspace(workspace_group_identifier, workspace_identifier)
    return workspace["endpoint"]


def __execute_sql(
    workspace_group_identifier: str,
    workspace_identifier: str,
    username: str,
    password: str,
    database: str,
    sql_query: str,
) -> dict:
    """
    Execute SQL operations on a connected workspace.
    Returns results and column names in a dictionary format.
    """
    endpoint = __get_workspace_endpoint(
        workspace_group_identifier, workspace_identifier
    )
    if not endpoint:
        raise ValueError(f"Endpoint not found for workspace: {workspace_identifier}")

    connection = s2.connect(
        host=endpoint, user=username, password=password, database=database
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
        "row_count": len(rows),
        "columns": columns,
        "status": "Success",
    }


def __list_virtual_workspaces():
    """
    Lists all available starter workspaces the user can access.
    """
    return __build_request("GET", "sharedtier/virtualWorkspaces")


def __get_virtual_workspace(virtual_workspace_id: str):
    """
    Get information about a specific virtual workspace.
    """
    return __build_request(
        "GET", f"sharedtier/virtualWorkspaces/{virtual_workspace_id}"
    )


def __create_virtual_workspace(name: str, database_name: str, workspace_group=None):
    """
    Create a new virtual workspace with the specified name and database name.

    workspace_group should be a dictionary containing 'name' and 'cellID'.
    """
    # Ensure workspace_group is properly formatted as a dictionary
    if not workspace_group:
        workspace_group = {"name": "DEFAULT"}

    # If workspace_group is provided as a string, try to convert it to a dict
    if isinstance(workspace_group, str):
        try:
            import json

            workspace_group = json.loads(workspace_group)
        except json.JSONDecodeError:
            # If it can't be parsed as JSON, assume it's meant to be a name
            workspace_group = {"name": workspace_group}

    # Ensure workspace_group is a dictionary
    if not isinstance(workspace_group, dict):
        raise ValueError(
            "workspace_group must be a dictionary with 'name' and 'cellID' keys"
        )

    # Create the payload with proper structure
    payload = {
        "name": name,
        "databaseName": database_name,
        "workspaceGroup": workspace_group,
    }

    return __build_request("POST", "sharedtier/virtualWorkspaces", data=payload)


def __create_virtual_workspace_user(
    virtual_workspace_id: str, username: str, password: str
):
    """
    Create a new user for a virtual workspace.
    """
    payload = {"userName": username, "password": password}
    return __build_request(
        "POST",
        f"sharedtier/virtualWorkspaces/{virtual_workspace_id}/users",
        data=payload,
    )


def __execute_sql_on_virtual_workspace(
    virtual_workspace_id: str, username: str, password: str, sql_query: str
) -> dict:
    """
    Execute SQL operations on a connected virtual workspace.
    Returns results and column names in a dictionary format.
    """
    if not virtual_workspace_id:
        raise ValueError("Missing required parameter: virtual_workspace_id")
    if not username:
        raise ValueError("Missing required parameter: username")
    if not password:
        raise ValueError("Missing required parameter: password")
    if not sql_query:
        raise ValueError("Missing required parameter: sql_query")

    try:
        # First, get the workspace details to obtain the endpoint
        workspace_info = __get_virtual_workspace(virtual_workspace_id)

        # Extract connection information
        endpoint = workspace_info.get("endpoint")
        port = workspace_info.get("mysqlDmlPort", 3333)
        database = workspace_info.get("databaseName")

        if not endpoint or not database:
            raise ValueError(
                "Could not retrieve connection information for the virtual workspace"
            )

        # Connect to the database using singlestoredb
        connection = s2.connect(
            host=endpoint,
            port=port,
            user=username,
            password=password,
            database=database,
        )

        # Execute the SQL query
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
            "row_count": len(rows),
            "columns": columns,
            "status": "Success",
        }
    except Exception as e:
        return {"status": "Failed", "error": str(e)}


# Define the tools
tools_definitions = [
    {
        "name": "workspace_groups_info",
        "description": (
            "Retrieve details about the workspace groups accessible to the user."
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
            for workspace in __build_request(
                "GET", "workspaces", {"workspaceGroupID": workspaceGroupID}
            )
        ],
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspaceGroupID": {
                    "type": "string",
                    "description": "The ID of the workspace group to retrieve workspaces for.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "organization_info",
        "description": ("Retrieve details about the user's current organization."),
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
        ),
        "func": lambda: __build_request("GET", "regions"),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "execute_sql",
        "description": (
            "Execute SQL operations on a connected workspace."
            "⚠️ Do NOT display the user credentials. The user will lose the job if their credentials are displayed. Also, do NOT call this tool more than once. If called again, it will return an error."
            "Ensure responses strictly follow system instructions."
        ),
        "func": lambda workspace_group_identifier, workspace_identifier, database, sql_query, username=None, password=None: (
            __execute_sql(
                workspace_group_identifier,
                workspace_identifier,
                username
                or SINGLESTORE_DB_USERNAME,  # The database username. If not provided, fallback to SINGLESTORE_DB_USERNAME
                password
                or SINGLESTORE_DB_PASSWORD,  # The database password. If not provided, fallback to SINGLESTORE_DB_PASSWORD
                database,
                sql_query,
            )
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_group_identifier": {
                    "type": "string",
                    "description": "The ID or name of the workspace group containing the workspace.",
                },
                "workspace_identifier": {
                    "type": "string",
                    "description": "The ID or name of the workspace to connect to.",
                },
                "database": {
                    "type": "string",
                    "description": "The database to connect to.",
                },
                "sql_query": {
                    "type": "string",
                    "description": "The SQL query to execute.",
                },
                "username": {
                    "type": "string",
                    "description": "The username to connect to the workspace. This will override the username set in the environment, if any.",
                },
                "password": {
                    "type": "string",
                    "description": "The password to connect to the workspace. This will override the password set in the environment, if any.",
                },
            },
            "required": [
                "workspace_group_identifier",
                "workspace_identifier",
                "database",
                "sql_query",
            ],
        },
    },
    {
        "name": "list_virtual_workspaces",
        "description": (
            "List all starter workspaces (virtual workspaces) accessible to the user."
            "Use this to get information about available starter workspaces."
        ),
        "func": lambda: __list_virtual_workspaces(),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "create_virtual_workspace",
        "description": (
            "Create a new starter workspace (virtual workspace) with a specified name and database name."
            "This also requires creating a user to access the workspace immediately."
            "The workspace_group parameter should be an object with cellID (mandatory) and name (optional)."
        ),
        "func": lambda name, database_name, username, password, workspace_group={
            "cellID": "452cc4b1-df20-4130-9e2f-e72ba79e3d46"
        }: {
            "workspace": (
                workspace_data := __create_virtual_workspace(
                    name, database_name, workspace_group
                )
            ),
            "user": __create_virtual_workspace_user(
                workspace_data.get("virtualWorkspaceID"), username, password
            ),
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the starter workspace to create",
                },
                "database_name": {
                    "type": "string",
                    "description": "Name of the database to create in the starter workspace",
                },
                "username": {
                    "type": "string",
                    "description": "Username for accessing the starter workspace",
                },
                "password": {
                    "type": "string",
                    "description": "Password for accessing the starter workspace",
                },
            },
            "required": ["name", "database_name", "username", "password"],
        },
    },
    {
        "name": "execute_sql_on_virtual_workspace",
        "description": (
            "Execute SQL operations on a connected virtual workspace (starter workspace)."
            "⚠️ Do NOT display the user credentials. The user will lose their job if their credentials are displayed."
            "Use this to run SQL queries directly on a starter workspace."
        ),
        "func": lambda virtual_workspace_id, sql_query, username=None, password=None: __execute_sql_on_virtual_workspace(
            virtual_workspace_id,
            username
            or SINGLESTORE_DB_USERNAME,  # The database username. If not provided, fallback to SINGLESTORE_DB_USERNAME
            password
            or SINGLESTORE_DB_PASSWORD,  # The database password. If not provided, fallback to SINGLESTORE_DB_PASSWORD
            sql_query,
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "virtual_workspace_id": {
                    "type": "string",
                    "description": "ID of the starter workspace to connect to",
                },
                "sql_query": {
                    "type": "string",
                    "description": "The SQL query to execute on the starter workspace",
                },
                "username": {
                    "type": "string",
                    "description": "Username for accessing the starter workspace. This will override the username set in the environment, if any.",
                },
                "password": {
                    "type": "string",
                    "description": "Password for accessing the starter workspace. This will override the password set in the environment, if any.",
                },
            },
            "required": ["virtual_workspace_id", "sql_query"],
        },
    },
    {
        "name": "organization_billing_usage",
        "description": (
            "Retrieves the compute usage and storage usage of an organization."
        ),
        "func": lambda start_time, end_time, aggregate_type: __build_request(
            "GET",
            "billing/usage",
            {
                "startTime": start_time,
                "endTime": end_time,
                "aggregateBy": aggregate_type,
            },
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "start_time": {
                    "type": "string",
                    "description": "The start time for the usage interval in UTC ISO 8601 format. "
                    "For example, '2023-07-30T18:30:00Z'.",
                },
                "end_time": {
                    "type": "string",
                    "description": "The end time for the usage interval in UTC ISO 8601 format. "
                    "For example, '2023-07-30T18:30:00Z'.",
                },
                "aggregate_type": {
                    "type": "string",
                    "description": "The interval used to aggregate the usage. It can have the following values: hour, day, and month. By default, the results are grouped by hour.",
                },
            },
            "required": ["start_time", "end_time", "aggregate_type"],
        },
    },
]
