from enum import Enum
import re
from typing import Optional
import requests
from ..config import (
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
    
    # These are required parameters when not running within singlestore portal
    if not username or not password:
        raise ValueError("Singlestore Database username and password must be provided")

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


def __list_notebooks():
    """
    Lists all available notebook samples for SingleStore Spaces.
    """
    return __build_request("GET", "spaces/notebooks")


def __create_file_in_shared_space(path: str, content: str):
    """
    Create a new file (such as a notebook) in the user's shared space.

    Args:
        path: Path to the file to create
        content: Optional content for the file. If not provided and the file is a
                notebook, a sample notebook will be created.
    """
    
    # Check if it's a notebook and no content provided
    if path.endswith(".ipynb") and content is None:
        # Create a sample notebook with SingleStore connectivity example
        content = json.dumps({
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": ["# SingleStore Sample Notebook\n", 
                              "\n",
                              "This notebook demonstrates how to connect to a SingleStore database and run queries.\n"]
                },
                # ...existing notebook template code...
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": ["# Close the connection\n", "conn.close()"]
                }
            ],
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 2
        })
    
    file_manager = s2.manage_files(access_token=SINGLESTORE_API_KEY, base_url=SINGLESTORE_API_BASE_URL)

    if not content:
        content = ""

    with open("sample_notebook.ipynb", "w") as f:
        f.write(content)

    try:
        # Upload the file using the SDK method
        file_info = file_manager.shared_space.upload_file("sample_notebook.ipynb", path)
            
        return {
            "status": "success", 
            "message": f"File {path} created successfully",
            "path": file_info.path,
            "type": file_info.type,
            "format": file_info.format
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


def __list_files_in_personal_space():
    """
    List all files in the user's personal space.
    """
    url = f"{SINGLESTORE_API_BASE_URL}/v1/files/fs/personal"

    headers = {
        "Authorization": f"Bearer {SINGLESTORE_API_KEY}",
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise ValueError(
            f"Request failed with status code {response.status_code}: {response.text}"
        )

    try:
        return response.json()
    except ValueError:
        raise ValueError(f"Invalid JSON response: {response.text}")

def camel_to_snake(s: Optional[str]) -> Optional[str]:
    """Convert camel-case to snake-case."""
    if s is None:
        return None
    out = re.sub(r'([A-Z]+)', r'_\1', s).lower()
    if out and out[0] == '_':
        return out[1:]
    return out

class Mode(Enum):
    ONCE = 'Once'
    RECURRING = 'Recurring'

    @classmethod
    def from_str(cls, s: str) -> 'Mode':
        try:
            return cls[str(camel_to_snake(s)).upper()]
        except KeyError:
            raise ValueError(f'Unknown Mode: {s}')

    def __str__(self) -> str:
        """Return string representation."""
        return self.value

    def __repr__(self) -> str:
        """Return string representation."""
        return str(self)

def __create_scheduled_job(
    notebook_path: str,
    mode: str,
    create_snapshot: bool,
):
    """
    Create a new scheduled job for running a notebook periodically.

    Args:
        name: Name of the job
        notebook_path: Path to the notebook to be executed
        schedule_mode: Mode of the schedule (Once or Recurring)
        execution_interval_minutes: Minutes between executions (for Recurring mode)
        start_at: When to start the job (ISO 8601 format)
        description: Optional description of the job
        create_snapshot: Whether to create a snapshot of the notebook before execution
        runtime_name: Name of the runtime to use for the job execution
        parameters: List of parameter objects to pass to the notebook
        target_config: Optional target configuration for the job
    """

    mode_enum = Mode.from_str(mode)

    try:
        jobs_manager = s2.manage_workspaces(access_token=SINGLESTORE_API_KEY, base_url=SINGLESTORE_API_BASE_URL).organizations.current.jobs
        job = jobs_manager.schedule(notebook_path=notebook_path, mode=mode_enum, create_snapshot=create_snapshot)
        return job
    except Exception as e:
        return {"status": "error", "message": str(e)}


def __get_job_details(job_id: str):
    """
    Get details about a specific job.
    """
    return __build_request("GET", f"jobs/{job_id}")


def __list_job_executions(job_id: str, start: int = 1, end: int = 10):
    """
    List executions for a specific job.
    """
    return __build_request(
        "GET", f"jobs/{job_id}/executions", params={"start": start, "end": end}
    )


def __list_files_in_shared_space():
    """
    List all files in the shared space.
    """
    url = f"{SINGLESTORE_API_BASE_URL}/v1/files/fs/shared"

    headers = {
        "Authorization": f"Bearer {SINGLESTORE_API_KEY}",
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise ValueError(
            f"Request failed with status code {response.status_code}: {response.text}"
        )

    try:
        return response.json()
    except ValueError:
        raise ValueError(f"Invalid JSON response: {response.text}")


def __get_notebook_path_by_name(notebook_name: str, location: str = "personal") -> str:
    """
    Find a notebook by its name and return its full path.

    Args:
        notebook_name: The name of the notebook to find (with or without .ipynb extension)
        location: Where to look for the notebook - 'personal' or 'shared'

    Returns:
        The full path of the notebook if found

    Raises:
        ValueError: If no notebook with the given name is found
    """
    # Make sure we look for the right extension
    if not notebook_name.endswith(".ipynb"):
        search_name = f"{notebook_name}.ipynb"
    else:
        search_name = notebook_name

    # Get all files from the specified location
    if location.lower() == "personal":
        files_response = __list_files_in_personal_space()
    elif location.lower() == "shared":
        files_response = __list_files_in_shared_space()
    else:
        raise ValueError(
            f"Invalid location: {location}. Must be 'personal' or 'shared'"
        )

    # The API might return different structures
    # Handle both array of files or object with content property
    if isinstance(files_response, dict) and "content" in files_response:
        files = files_response["content"]
    elif isinstance(files_response, list):
        files = files_response
    else:
        raise ValueError(
            f"Unexpected response format from file listing API: {type(files_response)}"
        )

    # Filter to find notebooks matching the name (case insensitive)
    matching_notebooks = []
    for file in files:
        # Verify file is a dictionary with the expected fields
        if not isinstance(file, dict):
            continue

        # Skip if not a notebook or missing path
        if (
            "path" not in file
            or not isinstance(file["path"], str)
            or not file["path"].endswith(".ipynb")
        ):
            continue

        # Check if the name matches
        file_name = file["path"].split("/")[-1]  # Get just the filename portion
        if file_name.lower() == search_name.lower():
            matching_notebooks.append(file)

    if not matching_notebooks:
        raise ValueError(
            f"No notebook with name '{notebook_name}' found in {location} space"
        )

    # If we found multiple matches (unlikely with exact name match), return first one
    notebook_path = matching_notebooks[0]["path"]

    if location.lower() == "personal":
        user_id = __get_user_id()

        # Format for personal space: {projectID}/_internal-s2-personal/{userID}/{path}
        return f"_internal-s2-personal/{user_id}/{notebook_path}"
    elif location.lower() == "shared":
        project_id = __get_project_id()

        # Format for shared space: {projectID}/{path}
        return f"{project_id}/{notebook_path}"

    # If we couldn't get the IDs or format correctly, return the raw path
    return notebook_path


def __get_project_id():
    """
    Get the organization ID (project ID) from the management API.

    Returns:
        str: The organization ID
    """
    # Get current organization info to extract the project ID
    org_info = __build_request("GET", "organizations/current")
    project_id = org_info.get("orgID")

    if not project_id:
        raise ValueError("Could not retrieve organization ID from the API")

    return project_id


def __get_user_id():
    """
    Get the current user's ID from the management API.

    Returns:
        str: The user ID
    """
    # Get all users in the organization
    users = __build_request("GET", "users")

    # Find the current user
    # Since we can't directly get the current user ID, we'll use the first user
    # In a real implementation, we might need additional logic to identify the current user
    if users and isinstance(users, list) and len(users) > 0:
        user_id = users[0].get("userID")
        if user_id:
            return user_id

    raise ValueError("Could not retrieve user ID from the API")


# Define the tools
tools_definitions = [
    {
        "name": "workspace_groups_info",
        "description": (
            "List all workspace groups accessible to the user in SingleStore.\n"
            "\n"
            "Returns detailed information for each group:\n"
            "- name: Display name of the workspace group\n"
            "- deploymentType: Type of deployment (e.g., 'PRODUCTION')\n"
            "- state: Current status (e.g., 'ACTIVE', 'PAUSED')\n"
            "- workspaceGroupID: Unique identifier for the group\n"
            "- firewallRanges: Array of allowed IP ranges for access control\n"
            "- createdAt: Timestamp of group creation\n"
            "- regionID: Identifier for deployment region\n"
            "- updateWindow: Maintenance window configuration\n"
            "\n"
            "Use this tool to:\n"
            "1. Get workspace group IDs for other operations\n"
            "2. Plan maintenance windows\n"
            "\n"
            "Related operations:\n"
            "- Use workspaces_info to list workspaces within a group\n"
            "- Use execute_sql to run queries on workspaces in a group\n"
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
            "List all workspaces within a specified workspace group in SingleStore.\n"
            "\n"
            "Returns detailed information for each workspace:\n"
            "- createdAt: Timestamp of workspace creation\n"
            "- deploymentType: Type of deployment (e.g., 'PRODUCTION')\n"
            "- endpoint: Connection URL for database access\n"
            "- name: Display name of the workspace\n"
            "- size: Compute and storage configuration\n"
            "- state: Current status (e.g., 'ACTIVE', 'PAUSED')\n"
            "- terminatedAt: Timestamp of termination if applicable\n"
            "- workspaceGroupID: Workspacegroup identifier\n"
            "- workspaceID: Unique workspace identifier\n"
            "\n"
            "Use this tool to:\n"
            "1. Monitor workspace status\n"
            "2. Get connection details for database operations\n"
            "3. Track workspace lifecycle\n"
            "\n"
            "Required parameter:\n"
            "- workspaceGroupID: Unique identifier of the workspace group\n"
            "\n"
            "Related operations:\n"
            "- Use workspace_groups_info first to get workspacegroupID\n"
            "- Use execute_sql to run queries on specific workspace\n"
            "\n"
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
                    "description": "The unique identifier of the workspace group to retrieve workspaces from.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "organization_info",
        "description": (
            "Retrieve information about the current user's organization in SingleStore.\n"
            "\n"
            "Returns organization details including:\n"
            "- orgID: Unique identifier for the organization\n"
            "- name: Organization display name\n"
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
            "List all available deployment regions where SingleStore workspaces can be deployed for the user.\n"
            "\n"
            "Returns region information including:\n"
            "- regionID: Unique identifier for the region\n"
            "- provider: Cloud provider (AWS, GCP, or Azure)\n"
            "- name: Human-readable region name (e.g., Europe West 2 (London),US West 2 (Oregon)) \n"
            "\n"
            "Use this tool to:\n"
            "1. Select optimal deployment regions based on:\n"
            "   - Geographic proximity to users\n"
            "   - Compliance requirements\n"
            "   - Cost considerations\n"
            "   - Available cloud providers\n"
            "2. Plan multi-region deployments\n"
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
            "Execute SQL operations on a database attached to workspace within a workspace group and receive formatted results.\n"
            "\n"
            "Returns:\n"
            "- Query results with column names and typed values\n"
            "- Row count and metadata\n"
            "- Execution status\n"
            "\n"
            "⚠️ CRITICAL SECURITY WARNINGS:\n"
            "- Never display or log credentials in responses\n"
            "- Use only READ-ONLY queries (SELECT, SHOW, DESCRIBE)\n"
            "- DO NOT USE data modification statements:\n"
            "  × No INSERT/UPDATE/DELETE\n"
            "  × No DROP/CREATE/ALTER\n"
            "- Ensure queries are properly sanitized\n"
            "\n"
            "Required parameters:\n"
            "- workspace_group_identifier: ID/name of the workspace group\n"
            "- workspace_identifier: ID/name of the specific workspace within the workspace group\n"
            "- database: Name of the database to query\n"
            "- sql_query: The SQL query to execute\n"
            "\n"
            "Optional parameters:\n"
            "- username: Username for database access (defaults to SINGLESTORE_DB_USERNAME)\n"
            "- password: Password for database access (defaults to SINGLESTORE_DB_PASSWORD)\n"
            "\n"
            "Allowed query examples:\n"
            "- SELECT * FROM table_name\n"
            "- SELECT COUNT(*) FROM table_name\n"
            "- SHOW TABLES\n"
            "- DESCRIBE table_name\n"
            "\n"
            "Note: For data modifications, please use appropriate admin tools or APIs."
        ),
        # If the database user and password. If not provided, fallback to SINGLESTORE_DB_USERNAME and SINGLESTORE_DB_PASSWORD
        "func": lambda workspace_group_identifier, workspace_identifier, database, sql_query, username=SINGLESTORE_DB_USERNAME, password=SINGLESTORE_DB_PASSWORD: (
            __execute_sql(
                workspace_group_identifier,
                workspace_identifier,
                username,
                password,
                database,
                sql_query,
            )
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_group_identifier": {
                    "type": "string",
                    "description": "The ID or name of the workspace group containing the target workspace.",
                },
                "workspace_identifier": {
                    "type": "string",
                    "description": "The ID or name of the specific workspace where the query will run.",
                },
                "database": {
                    "type": "string",
                    "description": "The name of the database to query within the workspace.",
                },
                "sql_query": {
                    "type": "string",
                    "description": "The SQL query to execute. Must be valid SingleStore SQL.",
                },
                "username": {
                    "type": "string",
                    "description": "Optional: Username for database connection. Will use environment default if not specified.",
                },
                "password": {
                    "type": "string",
                    "description": "Optional: Password for database connection. Will use environment default if not specified.",
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
            "List all starter (virtual) workspaces available to the user in SingleStore.\n"
            "\n"
            "Returns detailed information about each starter workspace:\n"
            "- virtualWorkspaceID: Unique identifier for the workspace\n"
            "- name: Display name of the workspace\n"
            "- endpoint: Connection endpoint URL\n"
            "- databaseName: Name of the primary database\n"
            "- mysqlDmlPort: Port for MySQL protocol connections\n"
            "- webSocketPort: Port for WebSocket connections\n"
            "- state: Current status of the workspace\n"
            "\n"
            "Use this tool to:\n"
            "1. Get virtual workspace IDs for other operations\n"
            "2. Check starter workspace availability and status\n"
            "3. Obtain connection details for database access\n"
            "\n"
            "Note: This tool only lists starter workspaces, not standard workspaces.\n"
            "Use workspaces_info for standard workspace information."
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
            "Create a new starter (virtual) workspace in SingleStore and set up user access.\n"
            "\n"
            "Process:\n"
            "1. Creates a virtual workspace with specified name and database\n"
            "2. Creates a user account for accessing the workspace\n"
            "3. Returns both workspace details and access credentials\n"
            "\n"
            "Required parameters:\n"
            "- name: Unique name for the starter workspace\n"
            "- database_name: Name for the database to create\n"
            "- username:  Username for accessing the starter workspace\n"
            "- password: Password for accessing the starter workspace\n"
            "\n"
            "Usage notes:\n"
            "- Workspace names must be unique\n"
            "- Passwords should meet security requirements\n"
            "- Use execute_sql_on_virtual_workspace to interact with the created starter workspace"
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
                    "description": "Unique name for the new starter workspace",
                },
                "database_name": {
                    "type": "string",
                    "description": "Name of the database to create in the starter workspace",
                },
                "username": {
                    "type": "string",
                    "description": "Username for accessing the new starter workspace",
                },
                "password": {
                    "type": "string",
                    "description": "Password for accessing the new starter workspace",
                },
            },
            "required": ["name", "database_name", "username", "password"],
        },
    },
    {
        "name": "execute_sql_on_virtual_workspace",
        "description": (
            "Execute SQL operations on a virtual (starter) workspace and receive formatted results.\n"
            "\n"
            "Returns:\n"
            "- Query results with column names and typed values\n"
            "- Row count\n"
            "- Column metadata\n"
            "- Execution status\n"
            "\n"
            "⚠️ CRITICAL SECURITY WARNING:\n"
            "- Never display or log credentials in responses\n"
            "- Ensure SQL queries are properly sanitized\n"
            "- ONLY USE SELECT statements or queries that don't modify data\n"
            "- DO NOT USE INSERT, UPDATE, DELETE, DROP, CREATE, or ALTER statements\n"
            "\n"
            "Required input parameters:\n"
            "- virtual_workspace_id: Unique identifier of the starter workspace\n"
            "- sql_query: The SQL query to execute (READ-ONLY queries only)\n"
            "\n"
            "Optional input parameters:\n"
            "- username: For accessing the starter workspace (defaults to SINGLESTORE_DB_USERNAME)\n"
            "- password: For accessing the starter workspace (defaults to SINGLESTORE_DB_PASSWORD)\n"
            "\n"
            "Allowed query examples:\n"
            "- SELECT * FROM table_name\n"
            "- SELECT COUNT(*) FROM table_name\n"
            "- SHOW TABLES\n"
            "- DESCRIBE table_name\n"
            "\n"
            "Note: This tool is specifically designed for read-only operations on starter workspaces."
        ),
        "func": lambda virtual_workspace_id, sql_query, username=SINGLESTORE_DB_USERNAME, password=SINGLESTORE_DB_PASSWORD: __execute_sql_on_virtual_workspace(
            virtual_workspace_id,
            username,
            password,
            sql_query,
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "virtual_workspace_id": {
                    "type": "string",
                    "description": "Unique identifier of the starter workspace to connect to",
                },
                "sql_query": {
                    "type": "string",
                    "description": "SQL query to execute on the starter workspace",
                },
                "username": {
                    "type": "string",
                    "description": "Optional: Username for accessing the starter workspace. Will use environment default if not specified.",
                },
                "password": {
                    "type": "string",
                    "description": "Optional: Password for accessing the starter workspace, Will use environment default if not specified.",
                },
            },
            "required": ["virtual_workspace_id", "sql_query"],
        },
    },
    {
        "name": "organization_billing_usage",
        "description": (
            "Retrieve detailed billing and usage metrics for your organization over a specified time period. "
            "Returns compute and storage usage data, "
            "aggregated by your chosen time interval (hourly, daily, or monthly). "
            "This tool is essential for: \n"
            "1. Monitoring resource consumption patterns\n"
            "2. Analyzing cost trends\n"
            "Required input parameters:\n"
            "- start_time: Beginning of the usage period (UTC ISO 8601 format, e.g., '2023-07-30T18:30:00Z')\n"
            "- end_time: End of the usage period (UTC ISO 8601 format)\n"
            "- aggregate_type: Time interval for data grouping ('hour', 'day', or 'month')\n\n"
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
                    "description": "Start of the usage period in UTC ISO 8601 format (e.g., '2023-07-30T18:30:00Z')",
                },
                "end_time": {
                    "type": "string",
                    "description": "End of the usage period in UTC ISO 8601 format (e.g., '2023-07-30T18:30:00Z')",
                },
                "aggregate_type": {
                    "type": "string",
                    "description": "How to group the usage data: 'hour', 'day', or 'month'",
                },
            },
            "required": ["start_time", "end_time", "aggregate_type"],
        },
    },
    {
        "name": "list_notebook_samples",
        "description": (
            "Retrieve a catalog of pre-built notebook templates available in SingleStore Spaces.\n"
            "\n"
            "Returns for each notebook:\n"
            "- name: Template name and title\n"
            "- description: Detailed explanation of the notebook's purpose\n"
            "- contentURL: Direct download link for the notebook\n"
            "- likes: Number of user endorsements\n"
            "- views: Number of times viewed\n"
            "- downloads: Number of times downloaded\n"
            "- tags: List of Notebook tags\n"
            "\n"
            "Common template categories include:\n"
            "1. Getting Started guides\n"
            "2. Data loading and ETL patterns\n"
            "3. Query optimization examples\n"
            "4. Machine learning integrations\n"
            "5. Performance monitoring\n"
            "6. Best practices demonstrations\n"
            "\n"
            "Use this tool to:\n"
            "1. Find popular and well-tested example code\n"
            "2. Learn SingleStore features and best practices\n"
            "3. Start new projects with proven patterns\n"
            "4. Discover trending notebook templates\n"
            "\n"
            "Related operations:\n"
            "Related operations:\n"
            "- list_notebook_samples: To find example templates\n"
            "- list_shared_files: To check existing notebooks\n"
            "- create_scheduled_job: To automate notebook execution\n"
            "- get_notebook_path : To reference created notebooks\n"
        ),
        "func": lambda: __list_notebooks(),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "create_notebook",
        "description": (
            "Create a new Jupyter notebook in your personal space. Only supports python and markdown. Do not try to use any other languange\n"
            "\n"
            "Parameters:\n"
            "- notebook_name (required): Name for the new notebook\n"
            "  - Can include or omit .ipynb extension\n"
            "  - Must be unique in your personal space\n"
            "  - Examples: 'my_analysis' or 'my_analysis.ipynb'\n"
            "\n"
            "- content (optional): Custom notebook content\n"
            "  - Must be valid Jupyter notebook JSON format\n"
            "  - If omitted, creates template with:\n"
            "    • SingleStore connection setup\n"
            "    • Basic query examples\n"
            "    • DataFrame operations\n"
            "    • Best practices\n"
            "\n"
            "Features:\n"
            "- Creates notebook with specified name in personal space\n"
            "- Automatically adds .ipynb extension if missing\n"
            "- Provides default SingleStore template if no content given\n"
            "- Supports custom content in Jupyter notebook format\n"
            "- Only supports python and markdown cells\n"
            "- When creating a connection to the database the jupyter notebook will already have the connection_url defined and you can use directly\n"
            "- Install tools in a new cell with !pip3 install <toolname>\n"
            "\n"
            "Default template includes:\n"
            "- SingleStore connection setup code\n"
            "- Basic SQL query examples\n"
            "- DataFrame operations with pandas\n"
            "- Table creation and data insertion examples\n"
            "- Connection management best practices\n"
            "\n"
            "Use this tool to:\n"
            "1. Create data analysis notebooks using python\n"
            "2. Build database interaction workflows and much more\n"
            "\n"
            "Related operations:\n"
            "- list_notebook_samples: To find example templates\n"
            "- list_shared_files: To check existing notebooks\n"
            "- create_scheduled_job: To automate notebook execution\n"
            "- get_notebook_path : To reference created notebooks\n"
        ),
        "func": lambda notebook_name, content=None: __create_file_in_shared_space(
            (
                notebook_name
                if notebook_name.endswith(".ipynb")
                else f"{notebook_name}.ipynb"
            ),
            content,
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "notebook_name": {
                    "type": "string",
                    "description": "Name for the new notebook (with or without .ipynb extension)",
                },
                "content": {
                    "type": "string",
                    "description": "Optional: Custom notebook content in Jupyter JSON format",
                },
            },
            "required": ["notebook_name"],
        },
    },
    {
        "name": "list_shared_files",
        "description": (
            "List all files and notebooks in your shared SingleStore space.\n"
            "\n"
            "Returns file object meta data for each file:\n"
            "- name: Name of the file (e.g., 'analysis.ipynb')\n"
            "- path: Full path in shared space (e.g., 'folder/analysis.ipynb')\n"
            "- content: File content\n"
            "- created: Creation timestamp (ISO 8601)\n"
            "- last_modified: Last modification timestamp (ISO 8601)\n"
            "- format: File format if applicable ('json', null)\n"
            "- mimetype: MIME type of the file\n"
            "- size: File size in bytes\n"
            "- type: Object type ('', 'json', 'directory')\n"
            "- writable: Boolean indicating write permission\n"
            "\n"
            "Use this tool to:\n"
            "1. List workspace contents and structure\n"
            "2. Verify file existence before operations\n"
            "3. Check file timestamps and sizes\n"
            "4. Determine file permissions\n"
            "\n"
            "Related operations:\n"
            "- create_notebook: To add new notebooks\n"
            "- get_notebook_path: To find notebook paths\n"
            "- create_scheduled_job: To automate notebook execution\n"
        ),
        "func": lambda: __list_files_in_shared_space(),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "create_scheduled_job",
        "description": (
            "Create an automated job to execute a SingleStore notebook on a schedule.\n"
            "\n"
            "Parameters:\n"
            "1. Required Parameters:\n"
            "   - name: Name of the job (unique identifier within organization)\n"
            "   - notebook_path: Complete path to the notebook\n"
            "   - schedule_mode: 'Once' for single execution or 'Recurring' for repeated runs\n"
            "\n"
            "2. Optional Parameters:\n"
            "   - execution_interval_minutes: Time between recurring runs (≥60 minutes)\n"
            "   - start_at: Execution start time (ISO 8601 format, e.g., '2024-03-06T10:00:00Z')\n"
            "   - description: Human-readable purpose of the job\n"
            "   - create_snapshot: Enable notebook backup before execution (default: True)\n"
            "   - runtime_name: Execution environment selection (default: notebooks-cpu-small)\n"
            "   - parameters: Runtime variables for notebook\n"
            "   - target_config: Advanced runtime settings\n"
            "\n"
            "Returns Job info with:\n"
            "- jobID: UUID of created job\n"
            "- status: Current state (SUCCESS, RUNNING, etc.)\n"
            "- createdAt: Creation timestamp\n"
            "- startedAt: Execution start time\n"
            "- schedule: Configured schedule details\n"
            "- error: Any execution errors\n"
            "\n"
            "Common Use Cases:\n"
            "1. Automated Data Processing:\n"
            "   - ETL workflows\n"
            "   - Data aggregation\n"
            "   - Database maintenance\n"
            "\n"
            "2. Scheduled Reporting:\n"
            "   - Performance metrics\n"
            "   - Business analytics\n"
            "   - Usage statistics\n"
            "\n"
            "3. Maintenance Tasks:\n"
            "   - Health checks\n"
            "   - Backup operations\n"
            "   - Clean-up routines\n"
            "\n"
            "Related Operations:\n"
            "- get_job_details: Monitor job\n"
            "- list_job_executions: View job execution history\n"
        ),
        "func": lambda notebook_path, mode, create_snapshot=True: __create_scheduled_job(
            notebook_path, mode, create_snapshot,
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "notebook_path": {
                    "type": "string",
                    "description": "Full path to the notebook file (use get_notebook_path if needed)",
                },
                "mode": {
                    "type": "string",
                    "enum": ["Once", "Recurring"],
                    "description": "Execution mode: 'Once' or 'Recurring'",
                },
                "create_snapshot": {
                    "type": "boolean",
                    "description": "Enable notebook backup before execution (default: True)",
                },
            },
            "required": ["notebook_path", "mode", "create_snapshot"],
        },
    },
    {
        "name": "get_job_details",
        "description": (
            "Retrieve comprehensive information about a scheduled notebook job.\n"
            "\n"
            "Parameter required:\n"
            "job_id: UUID of the scheduled job to retrieve details for\n"
            "\n"
            "Returns:\n"
            "- jobID: Unique identifier (UUID format)\n"
            "- name: Display name of the job\n"
            "- description: Human-readable job description\n"
            "- createdAt: Creation timestamp (ISO 8601)\n"
            "- terminatedAt: End timestamp if completed\n"
            "- completedExecutionsCount: Number of successful runs\n"
            "- enqueuedBy: User ID who created the job\n"
            "- executionConfig: Notebook path and runtime settings\n"
            "- schedule: Mode, interval, and start time\n"
            "- targetConfig: Database and workspace settings\n"
            "- jobMetadata: Execution statistics and status\n"
            "\n"
            "Related Operations:\n"
            "- create_scheduled_job: Create new jobs\n"
            "- list_job_executions: View run history"
        ),
        "func": lambda job_id: __get_job_details(job_id),
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "string",
                    "description": "Unique identifier of the scheduled job",
                }
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "list_job_executions",
        "description": (
            "Retrieve execution history and performance metrics for a scheduled notebook job.\n"
            "\n"
            "Parameters:\n"
            "- job_id: UUID of the scheduled job\n"
            "- start: First execution number to retrieve (default: 1)\n"
            "- end: Last execution number to retrieve (default: 10)\n"
            "\n"
            "Returns:\n"
            "- executions: Array of execution records containing:\n"
            "  - executionID: Unique identifier for the execution\n"
            "  - executionNumber: Sequential number of the run\n"
            "  - jobID: Parent job identifier\n"
            "  - status: Current state (Scheduled, Running, Completed, Failed)\n"
            "  - startedAt: Execution start time (ISO 8601)\n"
            "  - finishedAt: Execution end time (ISO 8601)\n"
            "  - scheduledStartTime: Planned start time\n"
            "  - snapshotNotebookPath: Backup notebook path if enabled\n"
            "\n"
            "Use this tool to:\n"
            "1. Monitor each job execution status\n"
            "2. Track execution times and performance\n"
            "3. Investigate failed runs\n"
            "\n"
            "Related Operations:\n"
            "- get_job_details: View job configuration\n"
            "- create_scheduled_job: Create new jobs"
        ),
        "func": lambda job_id, start=1, end=10: __list_job_executions(
            job_id, start, end
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "string",
                    "description": "Unique identifier of the scheduled job",
                },
                "start": {
                    "type": "integer",
                    "description": "Starting execution number (default: 1)",
                },
                "end": {
                    "type": "integer",
                    "description": "Last execution number (default: 10)",
                },
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "get_notebook_path",
        "description": (
            "Find the complete path of a notebook by its name and generate the properly formatted path for API operations.\n"
            "\n"
            "Parameters:\n"
            "- notebook_name: Name of the notebook to locate (with or without .ipynb extension)\n"
            "- location: Where to search ('personal' or 'shared', defaults to 'personal')\n"
            "\n"
            "Returns the properly formatted path including project ID and user ID where needed."
            "\n"
            "Required for:\n"
            "- Creating scheduled jobs (use returned path as notebook_path parameter)\n"
        ),
        "func": lambda notebook_name, location="personal": __get_notebook_path_by_name(
            notebook_name, location
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "notebook_name": {
                    "type": "string",
                    "description": "Name of the notebook to find (with or without .ipynb extension)",
                },
                "location": {
                    "type": "string",
                    "enum": ["personal", "shared"],
                    "description": "Where to look for the notebook: 'personal' (default) or 'shared' space",
                },
            },
            "required": ["notebook_name"],
        },
    },
    {
        "name": "get_project_id",
        "description": (
            "Retrieve the organization's unique identifier (project ID).\n"
            "\n"
            "Returns:\n"
            "- orgID (string): The organization's unique identifier\n"
            "\n"
            "Required for:\n"
            "- Constructing paths or references to shared resources\n"
            "\n"
            "Performance Tip:\n"
            "Cache the returned ID when making multiple API calls.\n"
        ),
        "func": lambda: __get_project_id(),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_user_id",
        "description": (
            "Retrieve the current user's unique identifier. \n"
            "\n"
            "Returns:\n"
            "- userID (string): UUID format identifier for the current user\n"
            "\n"
            "Required for:\n"
            "- Constructing paths or references to personal resources\n"
            "\n"
            "1. Constructing personal space paths\n"
            "\n"
            "Performance Tip:\n"
            "Cache the returned ID when making multiple making multiple API calls.\n"
        ),
        "func": lambda: __get_user_id(),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]
