from typing import List
import requests
import json

from starlette.exceptions import HTTPException

from src.api.types import MCPConcept, AVAILABLE_FLAGS
import src.config.config as config
from src.config.config import get_session_request, get_settings
from src.logger import get_logger

# Set up logger for this module
logger = get_logger()


def filter_mcp_concepts(mcp_concepts: List[MCPConcept], **flags) -> List[MCPConcept]:
    """
    Filter MCP concepts based on boolean flags (backward compatibility).

    Args:
        mcp_concepts: List of MCP concepts to filter
        **flags: Boolean flags to filter by (e.g., deprecated=True, private=False)
                If no flags are provided, defaults to excluding deprecated concepts.

    Returns:
        Filtered list of MCP concepts
    """
    # Default behavior: exclude deprecated concepts if no flags provided
    if not flags:
        flags = {"deprecated": False}

    def matches_flags(concept):
        for flag_name, expected_value in flags.items():
            if hasattr(concept, flag_name):
                actual_value = getattr(concept, flag_name)
                if actual_value != expected_value:
                    return False
            else:
                # If the flag doesn't exist on the concept, skip this filter
                continue
        return True

    return [concept for concept in mcp_concepts if matches_flags(concept)]


def filter_tools_by_flags(
    mcp_concepts: List[MCPConcept], **flag_filters
) -> List[MCPConcept]:
    """
    Filter MCP concepts using simple string flag names.

    Args:
        mcp_concepts: List of MCP concepts to filter
        **flag_filters: Flag names with True/False values

    Returns:
        Filtered list of MCP concepts

    Examples:
        # Get only private tools
        filter_tools_by_flags(tools, private=True)

        # Get non-deprecated, non-private tools
        filter_tools_by_flags(tools, deprecated=False, private=False)

        # Get remote experimental tools
        filter_tools_by_flags(tools, remote=True, experimental=True)

        # Get admin tools that aren't deprecated
        filter_tools_by_flags(tools, admin=True, deprecated=False)
    """

    def matches_filters(concept: MCPConcept) -> bool:
        for flag_name, expected_value in flag_filters.items():
            if flag_name in AVAILABLE_FLAGS:
                actual_value = concept.has_flag(flag_name)
                if actual_value != expected_value:
                    return False
            else:
                # Invalid flag name - skip or warn
                continue
        return True

    return [concept for concept in mcp_concepts if matches_filters(concept)]


def query_graphql_organizations():
    """
    Query the GraphQL endpoint to get a list of organizations the user has access to.

    Returns:
        List of organizations with their IDs and names
    """
    settings = get_settings()
    graphql_endpoint = settings.graphql_public_endpoint

    logger.debug(f"GraphQL endpoint: {graphql_endpoint}")
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
        access_token = get_access_token()
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

        # Get organization ID (might be None for API key auth)
        org_id = get_org_id()

        # Only add organizationID if it's not None (not using API key)
        if org_id is not None:
            params["organizationID"] = org_id

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

    access_token = get_access_token()

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


def get_org_id() -> str | None:
    """
    Get the organization ID from the management API.

    For API key authentication, organization ID is not required.
    For JWT token authentication, organization ID is required.

    Returns:
        str or None: The organization ID, or None if using API key authentication
    """
    settings = get_settings()

    # If using API key authentication, no org_id is needed
    if not settings.is_remote and settings.api_key:
        logger.debug("Using API key authentication, no organization ID needed")
        return None

    org_id = settings.org_id

    if not org_id:
        logger.debug(
            "Organization ID not set in settings, fetching current organization"
        )
        raise ValueError("OrganizationID is not set. Please set an organization first.")

    return org_id


def get_access_token() -> str:
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
        # Check for API key first, then fall back to JWT token
        if isinstance(settings, config.LocalSettings) and settings.api_key:
            access_token = settings.api_key
            logger.debug("Using API key for authentication")
        else:
            access_token = settings.jwt_token
            logger.debug(
                f"Local JWT token retrieved (length: {len(access_token) if access_token else 0})"
            )

    if not access_token:
        logger.warning("No access token available!")
        raise HTTPException(401, "Unauthorized: No access token provided")

    return access_token
