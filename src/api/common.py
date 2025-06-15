from typing import List
import requests
import json
import logging

from starlette.exceptions import HTTPException

from src.api.types import MCPConcept
from src.config.config import get_session_request, get_settings

# Set up logger for this module
logger = logging.getLogger(__name__)


def filter_mcp_concepts(mcp_concepts: List[MCPConcept]) -> List[MCPConcept]:
    """
    Filter mcp concepts to exclude deprecated ones.
    """
    return [mcp_concept for mcp_concept in mcp_concepts if not mcp_concept.deprecated]


def query_graphql_organizations():
    """
    Query the GraphQL endpoint to get a list of organizations the user has access to.

    Returns:
        List of organizations with their IDs and names
    """
    settings = get_settings()
    graphql_endpoint = settings.graphql_public_endpoint

    logger.debug(f"GraphQL endpoint: {graphql_endpoint}")
    logger.debug(f"Settings auth method: {settings.auth_method}")
    logger.debug(f"Settings is_remote: {settings.is_remote}")

    # GraphQL query for organizations
    query = """
    query {
        organizations {
            orgID
            name
        }
    }
    """

    # Get access token with logging
    try:
        access_token = __get_access_token()
        # Only log first/last 8 chars for security
        token_preview = (
            f"{access_token[:8]}...{access_token[-8:]}"
            if len(access_token) > 16
            else "***"
        )
        logger.debug(f"Access token (preview): {token_preview}")
    except Exception as e:
        logger.error(f"Failed to get access token: {str(e)}")
        raise

    # Headers with authentication
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "SingleStore-MCP-Server",
    }

    # Payload for the GraphQL request
    payload = {"query": query.strip()}

    logger.debug(f"Request headers: {dict(headers)}")
    logger.debug(f"Request payload: {payload}")

    try:
        logger.debug(f"Making POST request to: {graphql_endpoint}")

        # Use the base GraphQL endpoint without query parameters
        response = requests.post(
            graphql_endpoint, headers=headers, json=payload, timeout=30
        )

        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response headers: {dict(response.headers)}")
        logger.debug(f"Raw response text: {response.text}")

        if response.status_code != 200:
            error_msg = f"GraphQL request failed with status code {response.status_code}: {response.text}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        data = response.json()
        logger.debug(f"Parsed response data: {data}")

        if "errors" in data:
            errors = data["errors"]
            error_message = "; ".join(
                [error.get("message", "Unknown error") for error in errors]
            )
            logger.error(f"GraphQL errors: {errors}")
            raise ValueError(f"GraphQL query error: {error_message}")

        if "data" in data and "organizations" in data["data"]:
            organizations = data["data"]["organizations"]
            logger.info(f"Found {len(organizations)} organizations")
            return organizations
        else:
            logger.warning("No organizations found in response")
            return []

    except requests.exceptions.RequestException as e:
        error_msg = f"Network error when querying organizations: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    except Exception as e:
        error_msg = f"Failed to query organizations: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)


def build_request(
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

    settings = get_settings()

    def build_request_endpoint(endpoint: str, params: dict = None):
        url = f"{settings.s2_api_base_url}/v1/{endpoint}"

        if params is None:
            params = {}

        # Add organization ID as a query parameter
        if settings.is_remote:
            params["organizationID"] = settings.org_id
        elif (
            hasattr(settings, "org_id")
            and settings.org_id
            and settings.auth_method == "oauth_token"
        ):
            # For local OAuth token authentication, also add organization ID
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
    match type:
        case "GET":
            request = requests.get(request_endpoint, headers=headers, params=params)
        case "POST":
            request = requests.post(request_endpoint, headers=headers, data=json_data)
        case "PUT":
            request = requests.put(request_endpoint, headers=headers, data=json_data)
        case "PATCH":
            request = requests.patch(request_endpoint, headers=headers, data=json_data)
        case "DELETE":
            request = requests.delete(request_endpoint, headers=headers)
        case _:
            raise ValueError(f"Unsupported request type: {type}")

    if request.status_code != 200:
        raise HTTPException(request.status_code, request.text)

    try:
        return request.json()
    except ValueError:
        raise ValueError(f"Invalid JSON response: {request.text}")


def __find_workspace_group(workspace_group_identifier: str):
    """
    Find a workspace group by its name or ID.
    """
    workspace_groups = build_request("GET", "workspaceGroups")
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
    workspaces = build_request(
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
    users = build_request("GET", "users")

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
        # For local settings with OAuth token authentication, check if org_id is already set
        if (
            hasattr(settings, "org_id")
            and settings.org_id
            and settings.auth_method == "oauth_token"
        ):
            return settings.org_id

        organization = build_request("GET", "organizations/current")
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

    logger.debug(f"Getting access token, is_remote: {settings.is_remote}")

    access_token: str
    if settings.is_remote:
        request = get_session_request()
        access_token = request.headers.get("Authorization", "").replace("Bearer ", "")
        logger.debug(
            f"Remote access token retrieved (length: {len(access_token) if access_token else 0})"
        )
    else:
        access_token = settings.api_key
        logger.debug(
            f"Local access token retrieved (length: {len(access_token) if access_token else 0})"
        )

    if not access_token:
        logger.warning("No access token available!")
        raise HTTPException(401, "Unauthorized: No access token provided")

    return access_token


def get_current_organization():
    """
    Get the current organization details from the management API.

    Returns:
        dict: Organization details including orgID and name
    """
    try:
        organization = build_request("GET", "organizations/current")
        logger.debug(f"Current organization response: {organization}")
        return organization
    except Exception as e:
        logger.error(f"Failed to get current organization: {str(e)}")
        raise ValueError(
            f"Could not retrieve current organization from the API: {str(e)}"
        )
