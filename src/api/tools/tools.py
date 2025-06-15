from enum import Enum
import json
import logging
import os
import re
import singlestoredb as s2
import nbformat as nbf
import nbformat.v4 as nbfv4

from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import Context

from src.api.common import (
    build_request,
    __get_org_id,
    __get_user_id,
    __get_workspace_endpoint,
    query_graphql_organizations,
    get_current_organization,
)
from src.api.tools.types import Tool
from src.config.config import get_settings

# Set up logger for this module
logger = logging.getLogger(__name__)


SAMPLE_NOTEBOOK_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "sample_notebook.ipynb"
)


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
        host=endpoint,
        user=username,
        password=password,
        database=database,
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
    return build_request("GET", f"sharedtier/virtualWorkspaces/{virtual_workspace_id}")


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

    return build_request("POST", "sharedtier/virtualWorkspaces", data=payload)


def __create_virtual_workspace_user(
    virtual_workspace_id: str, username: str, password: str
):
    """
    Create a new user for a virtual workspace.
    """
    payload = {"userName": username, "password": password}
    return build_request(
        "POST",
        f"sharedtier/virtualWorkspaces/{virtual_workspace_id}/users",
        data=payload,
    )


def __execute_sql_on_virtual_workspace(
    virtual_workspace_id: str,
    username: str,
    password: str,
    sql_query: str,
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


def camel_to_snake(s: Optional[str]) -> Optional[str]:
    """Convert camel-case to snake-case."""
    if s is None:
        return None
    out = re.sub(r"([A-Z]+)", r"_\1", s).lower()
    if out and out[0] == "_":
        return out[1:]
    return out


class Mode(Enum):
    ONCE = "Once"
    RECURRING = "Recurring"

    @classmethod
    def from_str(cls, s: str) -> "Mode":
        try:
            return cls[str(camel_to_snake(s)).upper()]
        except KeyError:
            raise ValueError(f"Unknown Mode: {s}")

    def __str__(self) -> str:
        """Return string representation."""
        return self.value

    def __repr__(self) -> str:
        """Return string representation."""
        return str(self)


def __create_scheduled_job(
    notebook_path: str, mode: str, create_snapshot: bool, access_token: str = None
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

    settings = get_settings()

    try:
        jobs_manager = s2.manage_workspaces(
            access_token=access_token,
            base_url=settings.s2_api_base_url,
        ).organizations.current.jobs
        job = jobs_manager.schedule(
            notebook_path=notebook_path,
            mode=mode_enum,
            create_snapshot=create_snapshot,
        )
        return job
    except Exception as e:
        return {"status": "error", "message": str(e)}


def execute_sql(
    workspace_group_identifier: str,
    workspace_identifier: str,
    database: str,
    sql_query: str,
    username: str = None,
    password: str = None,
    access_token: str = None,
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
      x No INSERT/UPDATE/DELETE
      x No DROP/CREATE/ALTER
    - Ensure queries are properly sanitized

    Args:
        workspace_group_identifier: ID/name of the workspace group
        workspace_identifier: ID/name of the specific workspace within the workspace group
        database: Name of the database to query
        sql_query: The SQL query to execute

    Returns:
        Dictionary with query results and metadata
    """

    settings = get_settings()

    empty_credentials = not username or not password
    if settings.is_remote:
        # If using JWT token, we can use the token to authenticate
        # The username is the user id that we can get from the management API
        username: str = __get_user_id()
        password: str = access_token
    elif empty_credentials:
        # If using API key, we need to request to the user to provide the username and password
        return {
            "status": "error",
            "message": (
                f"API key authentication is not supported for executing SQL queries. Please ask the user to provide their username and password for database {database}."
            ),
        }

    else:
        # If no authentication method is set, we need to ask the user to provide their username and password
        return {
            "status": "error",
            "message": (
                f"No authentication method set. Please ask the user to provide their username and password for database {database}."
            ),
        }

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
    workspace_group: Dict[str, str] = {
        "cellID": "452cc4b1-df20-4130-9e2f-e72ba79e3d46"
    },
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
            workspace_data.get("virtualWorkspaceID"),
            username,
            password,
        ),
    }


def execute_sql_on_virtual_workspace(
    virtual_workspace_id: str,
    sql_query: str,
    username: str = None,
    password: str = None,
    access_token: str = None,
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

    settings = get_settings()

    empty_credentials = not username or not password
    if settings.is_remote:
        # If using JWT token, we can use the token to authenticate
        # The username is the user id that we can get from the management API
        username: str = __get_user_id()
        password: str = access_token
    elif empty_credentials:
        # If using API key, we need to request to the user to provide the username and password
        return {
            "status": "error",
            "message": (
                f"API key authentication is not supported for executing SQL queries. Please ask the user to provide their username and password for virtual workspace {virtual_workspace_id}."
            ),
        }
    else:
        # If no authentication method is set, we need to ask the user to provide their username and password
        return {
            "status": "error",
            "message": (
                f"No authentication method set. Please ask the user to provide their username and password for virtual workspace {virtual_workspace_id}."
            ),
        }

    return __execute_sql_on_virtual_workspace(
        virtual_workspace_id,
        username,
        password,
        sql_query,
    )


def __create_file_in_shared_space(
    path: str, content: Optional[Dict[str, Any]] = None, access_token: str = None
) -> Dict[str, Any]:
    """
    Create a new file (such as a notebook) in the user's shared space.

    Args:
        path: Path to the file to create
        content: Optional JSON object with a 'cells' field containing an array of objects.
                 Each object must have 'type' (markdown or code) and 'content' fields.
                 If None, a sample notebook will be created for .ipynb files.
    """
    settings = get_settings()

    org_id = __get_org_id()

    file_manager = s2.manage_files(
        access_token=access_token,
        base_url=settings.s2_api_base_url,
        organization_id=org_id,
    )

    # Check if it's a notebook
    if path.endswith(".ipynb"):
        nb = nbfv4.new_notebook()
        nb["cells"] = []

        if content and "cells" in content:
            for cell in content["cells"]:
                if cell["type"] == "markdown":
                    nb["cells"].append(nbfv4.new_markdown_cell(cell["content"]))
                elif cell["type"] == "code":
                    nb["cells"].append(nbfv4.new_code_cell(cell["content"]))
                else:
                    raise ValueError(
                        f"Invalid cell type: {cell['type']}. Only 'markdown' and 'code' are supported."
                    )
        else:
            # Create a sample notebook with SingleStore connectivity example
            nb["cells"] = [
                nbfv4.new_markdown_cell(
                    "# SingleStore Sample Notebook\n\nThis notebook demonstrates how to connect to a SingleStore database and run queries."
                ),
                nbfv4.new_code_cell(
                    "import singlestoredb as s2\n\n# Connect to your database\nconn = s2.connect('hostname', user='username', password='password', database='database')"
                ),
                nbfv4.new_code_cell(
                    "result = conn.execute('SELECT * FROM your_table LIMIT 10')\n\nfor row in result:\n    print(row)"
                ),
                nbfv4.new_code_cell("conn.close()"),
            ]

        # Write notebook to file
        with open(SAMPLE_NOTEBOOK_PATH, "w") as f:
            nbf.write(nb, f)
    else:
        # For non-notebook files, just write an empty file
        with open(SAMPLE_NOTEBOOK_PATH, "w") as f:
            f.write("")

    # Upload the file using the SDK method
    file_info = file_manager.shared_space.upload_file(SAMPLE_NOTEBOOK_PATH, path)

    return {
        "status": "success",
        "message": f"File {path} created successfully",
        "path": file_info.path,
        "type": file_info.type,
        "format": file_info.format,
    }


def check_if_file_exists(file_name: str, access_token: str = None) -> Dict[str, Any]:
    """
    Check if a file (notebook) exists in the user's shared space.

    Args:
        file_name: Name of the file to check (with or without .ipynb extension)

    Returns:
        JSON object with the file existence status
        {
            "exists": True/False,
            "message": "File exists" or "File does not exist"
        }
    """

    org_id = __get_org_id()

    settings = get_settings()

    file_manager = s2.manage_files(
        access_token=access_token,
        base_url=settings.s2_api_base_url,
        organization_id=org_id,
    )

    exists = file_manager.shared_space.exists(file_name)

    return {
        "exists": exists,
        "message": (f"File {file_name} {'exists' if exists else 'does not exist'}"),
    }


def create_notebook(
    notebook_name: str, content: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a new Jupyter notebook in your personal space. Only supports python and markdown.

    Parameters:
    - notebook_name (required): Name for the new notebook
      - Can include or omit .ipynb extension
      - Must be unique in your personal space

    - content (optional): JSON object with the following structure:
        {
            "cells": [
                {"type": "markdown", "content": "Markdown content here"},
                {"type": "code", "content": "Python code here"}
            ]
        }
        - 'type' must be either 'markdown' or 'code'
        - 'content' is the text content of the cell
        IMPORTANT: The content must be valid JSON.

    How to use:
        - Before creating the notebook, call check_if_file_exists tool to verify if the notebook already exists.
        - Always install the dependencies on the first cell. Example:
            {
                "cells": [
                    {"type": "code", "content": "!pip install singlestoredb --quiet"},
                    // other cells...
                ]
            }
        - To connect to the database, use the variable "connection_url" that already exists in the notebook platform. Example:
            {
                "cells": [
                    {"type": "code", "content": "conn = s2.connect(connection_url)"},
                    // other cells...
                ]
            }
    """
    path = (
        notebook_name if notebook_name.endswith(".ipynb") else f"{notebook_name}.ipynb"
    )

    return __create_file_in_shared_space(path, content)


def create_scheduled_job(
    notebook_path: str, mode: str, create_snapshot: bool = True
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
        files_response = build_request("GET", "files/fs/personal")
    elif location.lower() == "shared":
        files_response = build_request("GET", "files/fs/shared")
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
    """ elif location.lower() == "shared":
        project_id = __get_project_id()

        # Format for shared space: {projectID}/{path}
        return f"{project_id}/{notebook_path}" """

    # If we couldn't get the IDs or format correctly, return the raw path
    return notebook_path


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
        for group in build_request("GET", "workspaceGroups")
    ]


def workspaces_info(workspace_group_id: str) -> List[Dict[str, Any]]:
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
        workspace_group_id: Unique identifier of the workspace group

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
        for workspace in build_request(
            "GET",
            "workspaces",
            {"workspaceGroupID": workspace_group_id},
        )
    ]


def organization_info() -> Dict[str, Any]:
    """
    Retrieve information about the current user's organization in SingleStore.

    Returns organization details including:
    - orgID: Unique identifier for the organization
    - name: Organization display name
    """
    return build_request("GET", "organizations/current")


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
    return build_request("GET", "regions")


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
    return build_request("GET", "sharedtier/virtualWorkspaces")


def organization_billing_usage(
    start_time: str, end_time: str, aggregate_type: str
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
    return build_request(
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
    return build_request("GET", "spaces/notebooks")


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
    return build_request("GET", "files/fs/shared")


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
    return build_request("GET", f"jobs/{job_id}")


def list_job_executions(job_id: str, start: int = 1, end: int = 10) -> Dict[str, Any]:
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
    return build_request(
        "GET",
        f"jobs/{job_id}/executions",
        params={"start": start, "end": end},
    )


def get_notebook_path(notebook_name: str, location: str = "personal") -> str:
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


async def get_organizations(ctx: Context) -> str:
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

    After viewing the list, the tool will prompt you to select an organization:
    - If only one organization is available, it will be selected automatically
    - If multiple organizations are available, you'll be prompted to select one by name or ID
    - You can change your organization selection anytime using the `set_organization` tool
    - If no organizations are available, an error will be returned
    """
    settings = get_settings()

    logger.debug("get_organizations called")
    logger.debug(f"Auth method: {settings.auth_method}")
    logger.debug(f"Is remote: {settings.is_remote}")

    # Only show organization selection for OAuth token authentication
    if settings.auth_method != "oauth_token":
        logger.debug("Skipping org selection - not OAuth token auth")
        return "✅ Organization selection is only required for OAuth token authentication. Your current authentication method doesn't require this step."

    try:
        logger.debug("Calling query_graphql_organizations...")
        # Get the list of organizations via GraphQL
        organizations = query_graphql_organizations()
        logger.debug(f"Retrieved {len(organizations)} organizations")

        if not organizations:
            logger.warning("No organizations available")
            return "❌ No organizations available for your account. Please check your access permissions."

        # Always return the list for user to choose from
        org_list = "\n".join(
            [f"- {org['name']} (ID: {org['orgID']})" for org in organizations]
        )

        logger.info(f"Found {len(organizations)} available organizations")

        return f"""📋 **Available SingleStore Organizations:**

{org_list}

✅ To select an organization, please use the `set_organization` tool with either the organization name or ID.

**Example:**
- `set_organization("your-org-name")`
- `set_organization("org-id-12345")`

Once you select an organization, all subsequent API calls will use that organization."""

    except Exception as e:
        logger.error(f"Error retrieving organizations: {str(e)}")
        return f"Error retrieving organizations: {e.with_traceback(None)}\n{str(e)}"


async def set_organization(orgID: str, ctx: Context) -> str:
    """
    Select which SingleStore organization to use for all subsequent API calls.

    This tool must be called after logging in and before making other API requests.
    Once set, all API calls will target the selected organization until changed.

    Args:
        orgID: Name or ID of the organization to select (use get_organizations to see available options)

    Returns:
        Success message with the selected organization details

    Usage:
    - Call get_organizations first to see available options
    - Then call this tool with either the organization's name or ID
    - All subsequent API calls will use the selected organization
    - You can call this tool anytime to switch to a different organization
    """
    settings = get_settings()

    logger.debug(f"set_organization called with orgID: {orgID}")
    logger.debug(f"Auth method: {settings.auth_method}")
    logger.debug(f"Is remote: {settings.is_remote}")

    try:
        # For OAuth token authentication, get the list of available organizations
        # and validate that the provided orgID is one the user has access to
        if settings.auth_method == "oauth_token":
            logger.debug("Getting available organizations for validation...")
            available_orgs = query_graphql_organizations()

            # Find the organization by ID or name
            selected_org = None
            for org in available_orgs:
                if orgID == org["orgID"] or orgID.lower() == org["name"].lower():
                    selected_org = org
                    break

            if not selected_org:
                available_names = [
                    f"{org['name']} (ID: {org['orgID']})" for org in available_orgs
                ]
                return (
                    f"Organization '{orgID}' not found. Available organizations:\n"
                    + "\n".join(available_names)
                )

            # Update the settings with the organization ID
            logger.debug(f"Setting org_id to: {selected_org['orgID']}")
            if hasattr(settings, "org_id"):
                settings.org_id = selected_org["orgID"]
            else:
                # For LocalSettings, we need to add the org_id attribute
                setattr(settings, "org_id", selected_org["orgID"])

            logger.info(f"Settings updated with org_id: {selected_org['orgID']}")
            return f"Successfully selected organization: {selected_org['name']} (ID: {selected_org['orgID']})"

        else:
            # For other authentication methods, try to get current organization
            logger.debug("Getting current organization...")
            current_org = get_current_organization()

            if not current_org:
                logger.error("Unable to get current organization")
                return "Unable to get current organization information."

            current_org_id = current_org.get("orgID") or current_org.get("id")
            current_org_name = current_org.get("name")

            logger.debug(f"Current org: {current_org_name} (ID: {current_org_id})")

            # Check if the provided orgID matches the current organization
            if orgID != current_org_id and orgID.lower() != current_org_name.lower():
                logger.warning(
                    f"Org mismatch: provided '{orgID}' vs current '{current_org_id}'"
                )
                return f"Organization '{orgID}' does not match your current organization '{current_org_name}' (ID: {current_org_id})"

            logger.debug("Organization match confirmed, updating settings...")
            # Update the settings with the organization ID
            if hasattr(settings, "org_id"):
                settings.org_id = current_org_id
            else:
                # For LocalSettings, we need to add the org_id attribute
                setattr(settings, "org_id", current_org_id)

            logger.info(f"Settings updated with org_id: {current_org_id}")
            return f"Successfully selected organization: {current_org_name} (ID: {current_org_id})"

    except Exception as e:
        logger.error(f"Error in set_organization: {str(e)}")
        return f"Error setting organization: {str(e)}"


def get_user_id(ctx: Context) -> str:
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


tools_definition = [
    {"func": get_user_id},
    {"func": workspace_groups_info},
    {"func": workspaces_info},
    {"func": organization_info},
    {"func": list_of_regions},
    {"func": list_virtual_workspaces},
    {"func": organization_billing_usage},
    {"func": list_notebook_samples},
    {"func": list_shared_files},
    {"func": create_notebook},
    {"func": check_if_file_exists},
    {"func": create_scheduled_job},
    {"func": get_job_details},
    {"func": list_job_executions},
    {"func": get_notebook_path},
    {"func": get_organizations},
    {"func": set_organization},
]

# Export the tools
tools = [Tool(**tool) for tool in tools_definition]
