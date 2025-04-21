from typing import Any, Dict, List

from server.utils.common import __build_request, __get_project_id, __get_user_id, __query_graphql_organizations
from server.utils.types import Resource

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
        files_response = __build_request("GET", "files/fs/personal")
    elif location.lower() == "shared":
        files_response = __build_request("GET", "files/fs/shared")
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
            "GET", "workspaces", {"workspaceGroupID": workspace_group_id}
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
    return __build_request("GET", "sharedtier/virtualWorkspaces")


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
    return __build_request("GET", "spaces/notebooks")


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
    return __build_request("GET", "files/fs/shared")

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
    return __build_request("GET", f"jobs/{job_id}")


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
    return __build_request(
        "GET", f"jobs/{job_id}/executions", params={"start": start, "end": end}
    )


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


resources_definitions = [
    {
        "name": "get_organizations",
        "description": get_organizations.__doc__,
        "func": get_organizations,
        "uri": "organizations://list",
    },
    {
        "name": "workspace_groups_info",
        "description": workspace_groups_info.__doc__,
        "func": workspace_groups_info,
        "uri": "workspaceGroups://list",
    },
    {
        "name": "workspaces_info",
        "description": workspaces_info.__doc__,
        "func": workspaces_info,
        "uri": "workspaceGroups://workspaces/{workspace_group_id}",
    },
    {
        "name": "organization_info",
        "description": organization_info.__doc__,
        "func": organization_info,
        "uri": "organizations://current",
    },
    {
        "name": "list_of_regions",
        "description": list_of_regions.__doc__,
        "func": list_of_regions,
        "uri": "regions://list",
    },
    {
        "name": "list_virtual_workspaces",
        "description": list_virtual_workspaces.__doc__,
        "func": list_virtual_workspaces,
        "uri": "virtualWorkspaces://list",
    },
    {
        "name": "organization_billing_usage",
        "description": organization_billing_usage.__doc__,
        "func": organization_billing_usage,
        "uri": "billing://usage/{aggregate_type}/{start_time}/{end_time}",
    },
    {
        "name": "list_notebook_samples",
        "description": list_notebook_samples.__doc__,
        "func": list_notebook_samples,
        "uri": "notebooks://list",
    },
    {
        "name": "list_shared_files",
        "description": list_shared_files.__doc__,
        "func": list_shared_files,
        "uri": "files://shared/list",
    },
    {
        "name": "get_job_details",
        "description": get_job_details.__doc__,
        "func": get_job_details,
        "uri": "executionJobs://{job_id}/details",
    },
    {
        "name": "list_job_executions",
        "description": list_job_executions.__doc__,
        "func": list_job_executions,
        "uri": "executionJobs://{job_id}/executions/{start}/{end}",
    },
    {
        "name": "get_notebook_path",
        "description": get_notebook_path.__doc__,
        "func": get_notebook_path,
        "uri": "notebooks://{notebook_name}/{location}/path",
    },
    {
        "name": "get_project_id",
        "description": get_project_id.__doc__,
        "func": get_project_id,
        "uri": "organizations://project/current",
    },
    {
        "name": "get_user_id",
        "description": get_user_id.__doc__,
        "func": get_user_id,
        "uri": "users://current",
    },
]

resources = [
    Resource(
        name=resource["name"],
        description=resource["description"],
        func=resource["func"],
        uri=resource["uri"],
    )
    for resource in resources_definitions
]