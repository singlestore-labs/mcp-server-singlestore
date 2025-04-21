from enum import Enum
import re
from typing import Optional, List, Dict, Any
import requests
import json

from server.utils.common import __build_request, __get_user_id, __get_workspace_endpoint, __query_graphql_organizations

# Import the refresh_token function from auth.py
from ..auth import refresh_token, TokenSet, load_credentials
from .types import Tool
from ..config import (
    SINGLESTORE_API_BASE_URL,
)
from ..auth import get_authentication_token
import singlestoredb as s2


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

def execute_sql(
    workspace_group_identifier: str,
    workspace_identifier: str,
    database: str,
    sql_query: str,
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
    
    Returns:
        Dictionary with query results and metadata
    """

    # The username is the user id that we can get from the management API
    username: str = __get_user_id()
    password: str = AUTH_TOKEN

    return __execute_sql(
        workspace_group_identifier,
        workspace_identifier,
        username,
        password,
        database,
        sql_query,
    )


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
    sql_query: str
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
    
    Returns:
        Dictionary with query results and metadata
    """
    username: str = __get_user_id()
    password: str = AUTH_TOKEN

    return __execute_sql_on_virtual_workspace(
        virtual_workspace_id,
        username,
        password,
        sql_query,
    )


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
    },
    {
        "name": "refresh_auth_token",
        "description": refresh_auth_token.__doc__,
        "func": refresh_auth_token,
    },
    {
        "name": "set_organization",
        "description": set_organization.__doc__,
        "func": set_organization,
    },
    {
        "name": "execute_sql",
        "description": execute_sql.__doc__,
        "func": execute_sql,
    },
    {
        "name": "create_virtual_workspace",
        "description": create_virtual_workspace.__doc__,
        "func": create_virtual_workspace,
    },
    {
        "name": "execute_sql_on_virtual_workspace",
        "description": execute_sql_on_virtual_workspace.__doc__,
        "func": execute_sql_on_virtual_workspace,
    },
    {
        "name": "create_notebook",
        "description": create_notebook.__doc__,
        "func": create_notebook,
    },
    {
        "name": "create_scheduled_job",
        "description": create_scheduled_job.__doc__,
        "func": create_scheduled_job,
    },
]

# Export the tools
tools = [
    Tool(
        name=tool["name"],
        description=tool["description"],
        func=tool["func"],
    )
    for tool in tools_definitions
]