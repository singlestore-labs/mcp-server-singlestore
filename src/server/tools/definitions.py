from enum import Enum
import re
import os
from typing import Optional, List, Dict, Any, Union
import requests
import json

# Import the refresh_token function from auth.py
from ..auth import refresh_token, TokenSet, load_credentials
from .classes import Tool
from ..config import (
    SINGLESTORE_API_KEY,
    SINGLESTORE_API_BASE_URL,
    SINGLESTORE_DB_PASSWORD,
    SINGLESTORE_DB_USERNAME,
    SINGLESTORE_GRAPHQL_PUBLIC_ENDPOINT,
)
from ..auth import get_authentication_token
import singlestoredb as s2

# Global variable to store selected organization
SELECTED_ORGANIZATION_ID = None
SELECTED_ORGANIZATION_NAME = None
AUTH_TOKEN = SINGLESTORE_API_KEY


def __query_graphql_organizations():
    """
    Query the GraphQL endpoint to get a list of organizations the user has access to.
    
    Returns:
        List of organizations with their IDs and names
    """
    graphql_endpoint = SINGLESTORE_GRAPHQL_PUBLIC_ENDPOINT
    
    # GraphQL query for organizations
    query = """
    query GetOrganizations {
        organizations {
            orgID
            name
        }
    }
    """
    
    # Headers with authentication
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json",
    }
    
    # Payload for the GraphQL request
    payload = {
        "operationName": "GetOrganizations",
        "query": query,
        "variables": {}
    }
    
    try:
        response = requests.post(
            f"{graphql_endpoint}?q=GetOrganizations",
            headers=headers, 
            json=payload
        )
        
        if response.status_code != 200:
            raise ValueError(
                f"GraphQL request failed with status code {response.status_code}: {response.text}"
            )
            
        data = response.json()
        if "errors" in data:
            errors = data["errors"]
            error_message = "; ".join([error.get("message", "Unknown error") for error in errors])
            raise ValueError(f"GraphQL query error: {error_message}")
            
        if "data" in data and "organizations" in data["data"]:
            return data["data"]["organizations"]
        else:
            return []
            
    except Exception as e:
        raise ValueError(f"Failed to query organizations: {str(e)}")


def select_organization():
    """
    Query available organizations and prompt the user to select one.
    
    This must be called after authentication and before making other API calls.
    Sets the global SELECTED_ORGANIZATION_ID and SELECTED_ORGANIZATION_NAME variables.
    
    Returns:
        Dictionary with the selected organization ID and name
    """
    global SELECTED_ORGANIZATION_ID, SELECTED_ORGANIZATION_NAME
    
    # If organization is already selected, return it
    if SELECTED_ORGANIZATION_ID and SELECTED_ORGANIZATION_NAME:
        return {
            "orgID": SELECTED_ORGANIZATION_ID,
            "name": SELECTED_ORGANIZATION_NAME
        }
    
    # Get available organizations
    organizations = __query_graphql_organizations()
    
    if not organizations:
        raise ValueError("No organizations found. Please check your account access.")
    
    # If only one organization is available, select it automatically
    if len(organizations) == 1:
        org = organizations[0]
        SELECTED_ORGANIZATION_ID = org["orgID"]
        SELECTED_ORGANIZATION_NAME = org["name"]
        
        return {
            "orgID": SELECTED_ORGANIZATION_ID,
            "name": SELECTED_ORGANIZATION_NAME
        }
    
    # Create a formatted list of organizations for the user to choose from
    org_list = "\n".join([f"{i+1}. {org['name']} (ID: {org['orgID']})" for i, org in enumerate(organizations)])
    
    # This will be handled by the LLM to ask the user which organization to use
    raise ValueError(
        f"Multiple organizations found. Please specify which organization to use either by name or ID:\n\n{org_list}"
    )


def __set_selected_organization(org_identifier):
    """
    Set the selected organization by name or ID.
    
    Args:
        org_identifier: Organization name or ID
    
    Returns:
        Dictionary with the selected organization ID and name
    """
    global SELECTED_ORGANIZATION_ID, SELECTED_ORGANIZATION_NAME
    
    # Get available organizations
    organizations = __query_graphql_organizations()
    
    if not organizations:
        raise ValueError("No organizations found. Please check your account access.")
    
    # Find the organization by name or ID
    for org in organizations:
        if org["orgID"] == org_identifier or org["name"] == org_identifier:
            SELECTED_ORGANIZATION_ID = org["orgID"]
            SELECTED_ORGANIZATION_NAME = org["name"]
            
            return {
                "orgID": SELECTED_ORGANIZATION_ID,
                "name": SELECTED_ORGANIZATION_NAME
            }
    
    # If no matching organization is found
    raise ValueError(f"Organization not found: {org_identifier}")


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
    # Ensure an organization is selected before making API requests
    if not SELECTED_ORGANIZATION_ID:
        select_organization()

    def build_request_endpoint(endpoint: str, params: dict = None):
        url = f"{SINGLESTORE_API_BASE_URL}/v1/{endpoint}"
        
        # Add organization ID as a query parameter
        if params is None:
            params = {}
        
        if SELECTED_ORGANIZATION_ID:
            params["organizationID"] = SELECTED_ORGANIZATION_ID
            
        if params and type == "GET":  # Only add query params for GET requests
            url += "?"
            for key, value in params.items():
                url += f"{key}={value}&"
            url = url[:-1]
        return url

    # Headers with authentication
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
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
    
    file_manager = s2.manage_files(access_token=AUTH_TOKEN, base_url=SINGLESTORE_API_BASE_URL)

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
        "Authorization": f"Bearer {AUTH_TOKEN}",
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
        jobs_manager = s2.manage_workspaces(access_token=AUTH_TOKEN, base_url=SINGLESTORE_API_BASE_URL).organizations.current.jobs
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
        "Authorization": f"Bearer {AUTH_TOKEN}",
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


def workspace_groups_info() -> List[Dict[str, Any]]:
    """
    List all workspace groups accessible to the user in SingleStore.
    
    Returns detailed information for each group:
    - name: Display name of the workspace group
    - deploymentType: Type of deployment (e.g., 'PRODUCTION')
    - state: Current status (e.g., 'ACTIVE', 'PAUSED')
    - workspaceGroupID: Unique identifier for the group
    - firewallRanges: Array of allowed IP ranges for access control
    - createdAt: Timestamp of group creation
    - regionID: Identifier for deployment region
    - updateWindow: Maintenance window configuration
    
    Use this tool to:
    1. Get workspace group IDs for other operations
    2. Plan maintenance windows
    
    Related operations:
    - Use workspaces_info to list workspaces within a group
    - Use execute_sql to run queries on workspaces in a group
    """
    return [
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
    ]


def workspaces_info(workspaceGroupID: str) -> List[Dict[str, Any]]:
    """
    List all workspaces within a specified workspace group in SingleStore.
    
    Returns detailed information for each workspace:
    - createdAt: Timestamp of workspace creation
    - deploymentType: Type of deployment (e.g., 'PRODUCTION')
    - endpoint: Connection URL for database access
    - name: Display name of the workspace
    - size: Compute and storage configuration
    - state: Current status (e.g., 'ACTIVE', 'PAUSED')
    - terminatedAt: End timestamp if applicable
    - workspaceGroupID: Workspacegroup identifier
    - workspaceID: Unique workspace identifier
    
    Args:
        workspaceGroupID: Unique identifier of the workspace group
    
    Returns:
        List of workspace information dictionaries
    """
    return [
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
    ]


def organization_info() -> Dict[str, Any]:
    """
    Retrieve information about the current user's organization in SingleStore.
    
    Returns organization details including:
    - orgID: Unique identifier for the organization
    - name: Organization display name
    """
    return __build_request("GET", "organizations/current")


def list_of_regions() -> List[Dict[str, Any]]:
    """
    List all available deployment regions where SingleStore workspaces can be deployed for the user.
    
    Returns region information including:
    - regionID: Unique identifier for the region
    - provider: Cloud provider (AWS, GCP, or Azure)
    - name: Human-readable region name (e.g., Europe West 2 (London), US West 2 (Oregon))
    
    Use this tool to:
    1. Select optimal deployment regions based on:
       - Geographic proximity to users
       - Compliance requirements
       - Cost considerations
       - Available cloud providers
    2. Plan multi-region deployments
    """
    return __build_request("GET", "regions")


def execute_sql(
    workspace_group_identifier: str,
    workspace_identifier: str,
    database: str,
    sql_query: str,
    username: str = SINGLESTORE_DB_USERNAME,
    password: str = SINGLESTORE_DB_PASSWORD
) -> Dict[str, Any]:
    """
    Execute SQL operations on a database attached to workspace within a workspace group and receive formatted results.
    
    Returns:
    - Query results with column names and typed values
    - Row count and metadata
    - Execution status
    
    ⚠️ CRITICAL SECURITY WARNINGS:
    - Never display or log credentials in responses
    - Use only READ-ONLY queries (SELECT, SHOW, DESCRIBE)
    - DO NOT USE data modification statements:
      × No INSERT/UPDATE/DELETE
      × No DROP/CREATE/ALTER
    - Ensure queries are properly sanitized
    
    Args:
        workspace_group_identifier: ID/name of the workspace group
        workspace_identifier: ID/name of the specific workspace within the workspace group
        database: Name of the database to query
        sql_query: The SQL query to execute
        username: Username for database access (defaults to SINGLESTORE_DB_USERNAME)
        password: Password for database access (defaults to SINGLESTORE_DB_PASSWORD)
    
    Returns:
        Dictionary with query results and metadata
    """
    return __execute_sql(
        workspace_group_identifier,
        workspace_identifier,
        username,
        password,
        database,
        sql_query,
    )


def list_virtual_workspaces() -> List[Dict[str, Any]]:
    """
    List all starter (virtual) workspaces available to the user in SingleStore.
    
    Returns detailed information about each starter workspace:
    - virtualWorkspaceID: Unique identifier for the workspace
    - name: Display name of the workspace
    - endpoint: Connection endpoint URL
    - databaseName: Name of the primary database
    - mysqlDmlPort: Port for MySQL protocol connections
    - webSocketPort: Port for WebSocket connections
    - state: Current status of the workspace
    
    Use this tool to:
    1. Get virtual workspace IDs for other operations
    2. Check starter workspace availability and status
    3. Obtain connection details for database access
    """
    return __list_virtual_workspaces()


def create_virtual_workspace(
    name: str,
    database_name: str,
    username: str,
    password: str,
    workspace_group: Dict[str, str] = {"cellID": "452cc4b1-df20-4130-9e2f-e72ba79e3d46"}
) -> Dict[str, Any]:
    """
    Create a new starter (virtual) workspace in SingleStore and set up user access.
    
    Process:
    1. Creates a virtual workspace with specified name and database
    2. Creates a user account for accessing the workspace
    3. Returns both workspace details and access credentials
    
    Args:
        name: Unique name for the new starter workspace
        database_name: Name of the database to create in the starter workspace
        username: Username for accessing the new starter workspace
        password: Password for accessing the new starter workspace
        workspace_group: Optional workspace group configuration
    
    Returns:
        Dictionary with workspace and user creation details
    """
    workspace_data = __create_virtual_workspace(name, database_name, workspace_group)
    return {
        "workspace": workspace_data,
        "user": __create_virtual_workspace_user(
            workspace_data.get("virtualWorkspaceID"), username, password
        ),
    }


def execute_sql_on_virtual_workspace(
    virtual_workspace_id: str,
    sql_query: str,
    username: str = SINGLESTORE_DB_USERNAME,
    password: str = SINGLESTORE_DB_PASSWORD
) -> Dict[str, Any]:
    """
    Execute SQL operations on a virtual (starter) workspace and receive formatted results.
    
    Returns:
    - Query results with column names and typed values
    - Row count
    - Column metadata
    - Execution status
    
    ⚠️ CRITICAL SECURITY WARNING:
    - Never display or log credentials in responses
    - Ensure SQL queries are properly sanitized
    - ONLY USE SELECT statements or queries that don't modify data
    - DO NOT USE INSERT, UPDATE, DELETE, DROP, CREATE, or ALTER statements
    
    Args:
        virtual_workspace_id: Unique identifier of the starter workspace
        sql_query: The SQL query to execute (READ-ONLY queries only)
        username: For accessing the starter workspace (defaults to SINGLESTORE_DB_USERNAME)
        password: For accessing the starter workspace (defaults to SINGLESTORE_DB_PASSWORD)
    
    Returns:
        Dictionary with query results and metadata
    """
    return __execute_sql_on_virtual_workspace(
        virtual_workspace_id,
        username,
        password,
        sql_query,
    )


def organization_billing_usage(
    start_time: str,
    end_time: str,
    aggregate_type: str
) -> Dict[str, Any]:
    """
    Retrieve detailed billing and usage metrics for your organization over a specified time period.
    
    Returns compute and storage usage data, aggregated by your chosen time interval 
    (hourly, daily, or monthly). This tool is essential for:
    1. Monitoring resource consumption patterns
    2. Analyzing cost trends
    
    Args:
        start_time: Beginning of the usage period (UTC ISO 8601 format, e.g., '2023-07-30T18:30:00Z')
        end_time: End of the usage period (UTC ISO 8601 format)
        aggregate_type: Time interval for data grouping ('hour', 'day', or 'month')
    
    Returns:
        Usage metrics and billing information
    """
    return __build_request(
        "GET",
        "billing/usage",
        {
            "startTime": start_time,
            "endTime": end_time,
            "aggregateBy": aggregate_type,
        },
    )


def list_notebook_samples() -> List[Dict[str, Any]]:
    """
    Retrieve a catalog of pre-built notebook templates available in SingleStore Spaces.
    
    Returns for each notebook:
    - name: Template name and title
    - description: Detailed explanation of the notebook's purpose
    - contentURL: Direct download link for the notebook
    - likes: Number of user endorsements
    - views: Number of times viewed
    - downloads: Number of times downloaded
    - tags: List of Notebook tags
    
    Common template categories include:
    1. Getting Started guides
    2. Data loading and ETL patterns
    3. Query optimization examples
    4. Machine learning integrations
    5. Performance monitoring
    6. Best practices demonstrations
    """
    return __list_notebooks()


def create_notebook(notebook_name: str, content: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a new Jupyter notebook in your personal space. Only supports python and markdown.
    
    Parameters:
    - notebook_name (required): Name for the new notebook
      - Can include or omit .ipynb extension
      - Must be unique in your personal space
    
    - content (optional): Custom notebook content
      - Must be valid Jupyter notebook JSON format
      - If omitted, creates template with:
      • SingleStore connection setup
      • Basic query examples
      • DataFrame operations
      • Best practices
    
    Features:
    - Creates notebook with specified name in personal space
    - Automatically adds .ipynb extension if missing
    - Provides default SingleStore template if no content given
    - Supports custom content in Jupyter notebook format
    - Only supports python and markdown cells
    
    Default template includes:
    - SingleStore connection setup code
    - Basic SQL query examples
    - DataFrame operations with pandas
    - Table creation and data insertion examples
    - Connection management best practices
    
    Use this tool to:
    1. Create data analysis notebooks using python
    2. Build database interaction workflows and much more
    
    Related operations:
    - list_notebook_samples: To find example templates
    - list_shared_files: To check existing notebooks
    - create_scheduled_job: To automate notebook execution
    - get_notebook_path : To reference created notebooks
    """
    path = notebook_name if notebook_name.endswith(".ipynb") else f"{notebook_name}.ipynb"
    return __create_file_in_shared_space(path, content)


def list_shared_files() -> Dict[str, Any]:
    """
    List all files and notebooks in your shared SingleStore space.
    
    Returns file object meta data for each file:
    - name: Name of the file (e.g., 'analysis.ipynb')
    - path: Full path in shared space (e.g., 'folder/analysis.ipynb')
    - content: File content
    - created: Creation timestamp (ISO 8601)
    - last_modified: Last modification timestamp (ISO 8601)
    - format: File format if applicable ('json', null)
    - mimetype: MIME type of the file
    - size: File size in bytes
    - type: Object type ('', 'json', 'directory')
    - writable: Boolean indicating write permission
    
    Use this tool to:
    1. List workspace contents and structure
    2. Verify file existence before operations
    3. Check file timestamps and sizes
    4. Determine file permissions
    """
    return __list_files_in_shared_space()


def create_scheduled_job(
    notebook_path: str,
    mode: str,
    create_snapshot: bool = True
) -> Dict[str, Any]:
    """
    Create an automated job to execute a SingleStore notebook on a schedule.
    
    Parameters:
    - notebook_path: Complete path to the notebook
    - mode: 'Once' for single execution or 'Recurring' for repeated runs
    - create_snapshot: Enable notebook backup before execution (default: True)
    
    Returns Job info with:
    - jobID: UUID of created job
    - status: Current state (SUCCESS, RUNNING, etc.)
    - createdAt: Creation timestamp
    - startedAt: Execution start time
    - schedule: Configured schedule details
    - error: Any execution errors
    
    Common Use Cases:
    1. Automated Data Processing:
       - ETL workflows
       - Data aggregation
       - Database maintenance
    
    2. Scheduled Reporting:
       - Performance metrics
       - Business analytics
       - Usage statistics
    
    3. Maintenance Tasks:
       - Health checks
       - Backup operations
       - Clean-up routines
    
    Related Operations:
    - get_job_details: Monitor job
    - list_job_executions: View job execution history
    """
    return __create_scheduled_job(notebook_path, mode, create_snapshot)


def get_job_details(job_id: str) -> Dict[str, Any]:
    """
    Retrieve comprehensive information about a scheduled notebook job.
    
    Returns:
    - jobID: Unique identifier (UUID format)
    - name: Display name of the job
    - description: Human-readable job description
    - createdAt: Creation timestamp (ISO 8601)
    - terminatedAt: End timestamp if completed
    - completedExecutionsCount: Number of successful runs
    - enqueuedBy: User ID who created the job
    - executionConfig: Notebook path and runtime settings
    - schedule: Mode, interval, and start time
    - targetConfig: Database and workspace settings
    - jobMetadata: Execution statistics and status
    
    Args:
        job_id: UUID of the scheduled job to retrieve details for
    
    Returns:
        Dictionary with job details
    """
    return __get_job_details(job_id)


def list_job_executions(
    job_id: str,
    start: int = 1,
    end: int = 10
) -> Dict[str, Any]:
    """
    Retrieve execution history and performance metrics for a scheduled notebook job.
    
    Returns:
    - executions: Array of execution records containing:
      - executionID: Unique identifier for the execution
      - executionNumber: Sequential number of the run
      - jobID: Parent job identifier
      - status: Current state (Scheduled, Running, Completed, Failed)
      - startedAt: Execution start time (ISO 8601)
      - finishedAt: Execution end time (ISO 8601)
      - scheduledStartTime: Planned start time
      - snapshotNotebookPath: Backup notebook path if enabled
    
    Args:
        job_id: UUID of the scheduled job
        start: First execution number to retrieve (default: 1)
        end: Last execution number to retrieve (default: 10)
    
    Returns:
        Dictionary with execution records
    """
    return __list_job_executions(job_id, start, end)


def get_notebook_path(
    notebook_name: str,
    location: str = "personal"
) -> str:
    """
    Find the complete path of a notebook by its name and generate the properly formatted path for API operations.
    
    Args:
        notebook_name: The name of the notebook to find (with or without .ipynb extension)
        location: Where to look for the notebook - 'personal' or 'shared'
    
    Returns:
        Properly formatted path including project ID and user ID where needed
        
    Required for:
    - Creating scheduled jobs (use returned path as notebook_path parameter)
    """
    return __get_notebook_path_by_name(notebook_name, location)


def get_project_id() -> str:
    """
    Retrieve the organization's unique identifier (project ID).
    
    Returns:
        str: The organization's unique identifier
    
    Required for:
    - Constructing paths or references to shared resources
    
    Performance Tip:
    Cache the returned ID when making multiple API calls.
    """
    return __get_project_id()


def get_user_id() -> str:
    """
    Retrieve the current user's unique identifier.
    
    Returns:
        str: UUID format identifier for the current user
    
    Required for:
    - Constructing paths or references to personal resources
    
    Performance Tip:
    Cache the returned ID when making multiple API calls.
    """
    return __get_user_id()


def get_organizations() -> List[Dict[str, Any]]:
    """
    List all available SingleStore organizations your account has access to.
    
    After logging in, this tool must be called first to identify which organization
    your queries should run against. Returns a list of organizations with:
    
    - orgID: Unique identifier for the organization
    - name: Display name of the organization
    
    Use this tool when:
    1. Starting a new session to see available organizations
    2. To verify permissions across multiple organizations
    3. Before switching context to a different organization
    
    After reviewing the list, use select_organization to choose one.
    """
    return __query_graphql_organizations()


def set_organization(orgID: str) -> Dict[str, Any]:
    """
    Select which SingleStore organization to use for all subsequent API calls.
    
    This tool must be called after logging in and before making other API requests.
    Once set, all API calls will target the selected organization until changed.
    
    Args:
        orgID: Name or ID of the organization to select
    
    Returns:
        Dictionary with the selected organization ID and name
    
    Usage:
    - Call get_organizations first to see available options
    - Then call this tool with either the organization's name or ID
    - All subsequent API calls will use the selected organization
    """
    return __set_selected_organization(orgID)


def login(api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Authenticate with SingleStore and obtain the necessary token for API access.
    
    This should be the first tool called before using any other SingleStore API tools.
    You can provide an API key directly, or if left empty, the tool will attempt to:
    1. Use any existing API key from the environment
    2. Use any saved credentials
    3. Launch browser-based authentication if needed
    
    Args:
        api_key: Optional SingleStore API key. If provided, it will be used instead of
                launching the browser authentication flow.
    
    Returns:
        Dictionary with authentication status and instructions for next steps
        
    After successful login, call get_organizations to list available organizations
    and then select one with set_organization before making other API calls.
    """
    global AUTH_TOKEN
    
    # If API key is provided, store it and return success
    if api_key:
        AUTH_TOKEN = api_key
        return {
            "status": "success",
            "message": "Successfully authenticated with provided API key. Please call get_organizations next to list available organizations."
        }
    
    # Otherwise, use the authentication flow from auth.py
    auth_token = get_authentication_token()
    
    if auth_token:
        AUTH_TOKEN = auth_token
        return {
            "status": "success",
            "message": "Successfully authenticated. Please call get_organizations next to list available organizations."
        }
    else:
        return {
            "status": "failed",
            "message": "Authentication failed. Please try again with a valid API key."
        }


def refresh_auth_token() -> Dict[str, Any]:
    """
    Refresh the current authentication token with SingleStore.
    
    Use this tool when:
    1. Your current token has expired
    2. You encounter authentication errors with other API calls
    3. You want to ensure you have a fresh token for an extended session
    
    This tool will attempt to refresh the existing token using the refresh token
    stored during the initial authentication. If no valid refresh token exists,
    you'll need to call the login tool again.
    
    Returns:
        Dictionary with refresh status and instructions
    
    Note: After a successful refresh, you can continue using all other API tools
    with the new token. No need to select an organization again.
    """
    global AUTH_TOKEN
    
    # Check if we have credentials stored
    credentials = load_credentials()
    
    if not credentials or "token_set" not in credentials:
        return {
            "status": "failed",
            "message": "No existing credentials found. Please use the login tool first."
        }
    
    # Create a token set from the stored credentials
    token_set = TokenSet(credentials["token_set"])
    
    # Try to refresh the token
    refreshed_token_set = refresh_token(token_set)
    
    if refreshed_token_set and refreshed_token_set.access_token:
        # Update the global token
        AUTH_TOKEN = refreshed_token_set.access_token
        
        return {
            "status": "success",
            "message": "Authentication token successfully refreshed. You can continue using SingleStore tools."
        }
    else:
        return {
            "status": "failed", 
            "message": "Failed to refresh the token. Please use the login tool again to authenticate."
        }


# Create a list of tool definitions to maintain compatibility with existing code
# This will allow us to iterate through tools in server.py
tools_definitions = [
    {
        "name": "login",
        "description": login.__doc__,
        "func": login,
        "inputSchema": {
            "type": "object",
            "properties": {
                "api_key": {
                    "type": "string",
                    "description": "Optional SingleStore API key. If provided, it will be used instead of launching the browser authentication flow."
                }
            },
            "required": [],
        }
    },
    {
        "name": "refresh_auth_token",
        "description": refresh_auth_token.__doc__,
        "func": refresh_auth_token,
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        }
    },
    {
        "name": "get_organizations",
        "description": get_organizations.__doc__,
        "func": get_organizations,
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        }
    },
    {
        "name": "set_organization",
        "description": set_organization.__doc__,
        "func": set_organization,
        "inputSchema": {
            "type": "object",
            "properties": {
                "orgID": {
                    "type": "string",
                    "description": "Name or ID of the organization to select",
                }
            },
            "required": ["orgID"],
        }
    },
    {
        "name": "workspace_groups_info",
        "description": workspace_groups_info.__doc__,
        "func": workspace_groups_info,
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        }
    },
    {
        "name": "workspaces_info",
        "description": workspaces_info.__doc__,
        "func": workspaces_info,
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspaceGroupID": {
                    "type": "string",
                    "description": "The unique identifier of the workspace group to retrieve workspaces from.",
                }
            },
            "required": ["workspaceGroupID"],
        }
    },
    {
        "name": "organization_info",
        "description": organization_info.__doc__,
        "func": organization_info,
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        }
    },
    {
        "name": "list_of_regions",
        "description": list_of_regions.__doc__,
        "func": list_of_regions,
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        }
    },
    {
        "name": "execute_sql",
        "description": execute_sql.__doc__,
        "func": execute_sql,
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
        "description": list_virtual_workspaces.__doc__,
        "func": list_virtual_workspaces,
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        }
    },
    {
        "name": "create_virtual_workspace",
        "description": create_virtual_workspace.__doc__,
        "func": create_virtual_workspace,
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
        "description": execute_sql_on_virtual_workspace.__doc__,
        "func": execute_sql_on_virtual_workspace,
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
        "description": organization_billing_usage.__doc__,
        "func": organization_billing_usage,
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
        "description": list_notebook_samples.__doc__,
        "func": list_notebook_samples,
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        }
    },
    {
        "name": "create_notebook",
        "description": create_notebook.__doc__,
        "func": create_notebook,
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
        "description": list_shared_files.__doc__,
        "func": list_shared_files,
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        }
    },
    {
        "name": "create_scheduled_job",
        "description": create_scheduled_job.__doc__,
        "func": create_scheduled_job,
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
        "description": get_job_details.__doc__,
        "func": get_job_details,
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
        "description": list_job_executions.__doc__,
        "func": list_job_executions,
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
        "description": get_notebook_path.__doc__,
        "func": get_notebook_path,
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
        "description": get_project_id.__doc__,
        "func": get_project_id,
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_user_id",
        "description": get_user_id.__doc__,
        "func": get_user_id,
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]

# Export the tools
tools = [
    Tool(
        name=tool["name"],
        description=tool["description"],
        func=tool["func"],
        inputSchema=tool["inputSchema"],
    )
    for tool in tools_definitions
]