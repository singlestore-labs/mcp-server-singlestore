import requests
import json

from starlette.exceptions import HTTPException
from fastmcp.server.dependencies import get_http_request

from src.config.config import get_settings


def __query_graphql_organizations():
    """
    Query the GraphQL endpoint to get a list of organizations the user has access to.

    Returns:
        List of organizations with their IDs and names
    """
    settings = get_settings()

    graphql_endpoint = settings.graphql_public_endpoint

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
        "Authorization": f"Bearer {__get_access_token()}",
        "Content-Type": "application/json",
    }

    # Payload for the GraphQL request
    payload = {
        "operationName": "GetOrganizations",
        "query": query,
        "variables": {},
    }

    try:
        response = requests.post(
            f"{graphql_endpoint}?q=GetOrganizations",
            headers=headers,
            json=payload,
        )

        if response.status_code != 200:
            raise ValueError(
                f"GraphQL request failed with status code {response.status_code}: {response.text}"
            )

        data = response.json()
        if "errors" in data:
            errors = data["errors"]
            error_message = "; ".join(
                [error.get("message", "Unknown error") for error in errors]
            )
            raise ValueError(f"GraphQL query error: {error_message}")

        if "data" in data and "organizations" in data["data"]:
            return data["data"]["organizations"]
        else:
            return []

    except Exception as e:
        raise ValueError(f"Failed to query organizations: {str(e)}")


def __build_request(
    type: str,
    endpoint: str,
    params: dict = None,
    data: dict = None,
):
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

    # __set_organzation_id()

    settings = get_settings()

    def build_request_endpoint(endpoint: str, params: dict = None):
        url = f"{settings.s2_api_base_url}/v1/{endpoint}"

        # Add organization ID as a query parameter
        if params is None:
            params = {}

        if settings.is_remote:
            params["organizationID"] = settings.org_id

        if params and type == "GET":  # Only add query params for GET requests
            url += "?"
            for key, value in params.items():
                url += f"{key}={value}&"
            url = url[:-1]
        return url

    # Headers with authentication
    headers = {
        "Content-Type": "application/json",
    }

    access_token = __get_access_token()

    if access_token is not None:
        headers["Authorization"] = f"Bearer {access_token}"

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


def __get_user_id() -> str:
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


def __get_org_id() -> str:
    """
    Get the organization ID from the management API.

    Returns:
        str: The organization ID
    """
    settings = get_settings()

    if settings.is_remote:
        return settings.org_id
    else:
        organization = __build_request("GET", "organizations/current")
        if "orgID" in organization:
            return organization["orgID"]
        else:
            raise ValueError("Could not retrieve organization ID from the API")


def __get_access_token() -> str:
    """
    Get the access token for the current session.

    Returns:
        str: The access token
    """
    settings = get_settings()

    access_token: str
    if settings.is_remote:
        request = get_http_request()
        access_token = request.headers.get("Authorization", "").replace("Bearer ", "")
    else:
        access_token = settings.api_key

    if not access_token:
        raise HTTPException(401, "Unauthorized: No access token provided")

    return access_token
