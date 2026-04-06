from typing import Any, Callable, Dict, List, TypeVar
import requests
import json

from singlestoredb.exceptions import ManagementError
from starlette.exceptions import HTTPException

from src.api.types import MCPConcept, AVAILABLE_FLAGS
from src.config.config import (
    LocalSettings,
    RemoteSettings,
    get_session_request,
    get_settings,
)
from src.logger import get_logger

# Set up logger for this module
logger = get_logger()

T = TypeVar("T")


def call_sdk_with_retry(fn: Callable[[], T]) -> T:
    """
    Call a SingleStore SDK function and retry once on 401 after refreshing the token.

    Usage:
        result = call_sdk_with_retry(lambda: do_sdk_call())

    Args:
        fn: A callable that performs the SDK operation. Will be called again on retry
            so it should re-fetch the access token internally if needed.
    """
    try:
        return fn()
    except ManagementError as e:
        logger.warning(
            f"SDK call failed: type={type(e).__module__}.{type(e).__qualname__}, msg={e}"
        )
        if e.errno != 401:
            raise

        settings = get_settings()
        if not isinstance(settings, LocalSettings) or settings.api_key:
            raise

        logger.warning("Attempting token refresh due to 401 Unauthorized response.")
        refresh_succeeded = settings.force_token_refresh()
        if not refresh_succeeded:
            logger.error("Token refresh failed.")
            raise

        logger.info("Token refresh succeeded, retrying SDK call...")
        return fn()


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


def query_graphql_organizations(_retry_on_401: bool = True) -> List[Dict[str, Any]]:
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

        if response.status_code == 401 and _retry_on_401:
            logger.warning(
                f"GraphQL request failed with status code {response.status_code}: {response.text}"
            )
            logger.warning("Attempting token refresh due to 401 Unauthorized response.")
            if isinstance(settings, LocalSettings) and not settings.api_key:
                refresh_succeeded = settings.force_token_refresh()
                if refresh_succeeded:
                    logger.info("Token refresh succeeded, retrying GraphQL request...")
                    return query_graphql_organizations(
                        _retry_on_401=False
                    )  # Retry after refreshing token
                else:
                    logger.error("Token refresh failed.")
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
    files: dict = None,
    raw_response: bool = False,
    allow_redirects: bool = True,
    _retry_on_401: bool = True,
):
    """
    Make an API request to the SingleStore Management API.

    Args:
        type: HTTP method (GET, POST, PUT, DELETE)
        endpoint: API endpoint path
        params: Query parameters
        data: Request body for POST/PUT/PATCH requests
        raw_response: If True, return the raw requests.Response object
            instead of parsed JSON. Useful for non-JSON responses or
            custom status code handling.
        allow_redirects: Whether to follow HTTP redirects. Defaults to True.
            Set to False to capture redirect responses (e.g. 307 with Location header).
        _retry_on_401: Internal flag to prevent infinite retry loops.
            Do not set this manually.

    Returns:
        JSON response from the API, or raw requests.Response if raw_response=True
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

        if params:
            url += "?"
            for key, value in params.items():
                url += f"{key}={value}&"
            url = url[:-1]
        return url

    # Headers with authentication
    headers = {}

    # Only set Content-Type for JSON requests (not multipart file uploads)
    if files is None:
        headers["Content-Type"] = "application/json"

    access_token = get_access_token()

    if access_token is not None:
        headers["Authorization"] = f"Bearer {access_token}"

    request_endpoint = build_request_endpoint(endpoint, params)

    # When files are provided, skip JSON serialization (requests handles multipart)
    json_data = None
    if files is None:
        # Default empty JSON body for POST/PUT requests if none provided
        if data is None and type in ["POST", "PUT", "PATCH"]:
            data = {}

        # Convert dict to JSON string for request body
        json_data = json.dumps(data) if data is not None else None

    request = None
    match type:
        case "GET":
            request = requests.get(
                request_endpoint,
                headers=headers,
                params=params,
                allow_redirects=allow_redirects,
            )
        case "POST":
            request = requests.post(
                request_endpoint,
                headers=headers,
                data=json_data,
                files=files,
                allow_redirects=allow_redirects,
            )
        case "PUT":
            request = requests.put(
                request_endpoint,
                headers=headers,
                data=json_data,
                files=files,
                allow_redirects=allow_redirects,
            )
        case "PATCH":
            request = requests.patch(
                request_endpoint,
                headers=headers,
                data=json_data,
                allow_redirects=allow_redirects,
            )
        case "DELETE":
            request = requests.delete(
                request_endpoint,
                headers=headers,
                allow_redirects=allow_redirects,
            )
        case _:
            raise ValueError(f"Unsupported request type: {type}")

    # Handle 401 Unauthorized - attempt token refresh and retry once
    if request.status_code == 401 and _retry_on_401:
        logger.warning("Attempting token refresh due to 401 Unauthorized response.")

        # Only attempt refresh for LocalSettings with OAuth tokens
        if isinstance(settings, LocalSettings) and not settings.api_key:
            refresh_succeeded = settings.force_token_refresh()

            if refresh_succeeded:
                logger.info("Token refresh succeeded, retrying request...")
                # Retry the request with _retry_on_401=False to prevent infinite loops
                return build_request(
                    type=type,
                    endpoint=endpoint,
                    params=params,
                    data=data,
                    files=files,
                    raw_response=raw_response,
                    allow_redirects=allow_redirects,
                    _retry_on_401=False,  # Prevent infinite retry
                )
            else:
                logger.error("Token refresh failed.")

    if raw_response:
        return request

    if request.status_code != 200:
        raise HTTPException(request.status_code, request.text)

    return request.json()


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


def fetch_user() -> Dict[str, Any]:
    """
    Get the current user's information from the management API.

    Returns:
    Dict[str, Any]: User information including userID, email, firstName, lastName
    """

    # Get all users in the organization
    user = build_request("GET", "users/current")

    if user is not None:
        return user

    raise ValueError("Could not retrieve user information from the API")


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

    access_token: str | None
    if isinstance(settings, RemoteSettings):
        request = get_session_request()
        access_token = request.headers.get("Authorization", "").replace("Bearer ", "")
        logger.debug(
            f"Remote access token retrieved (length: {len(access_token) if access_token else 0})"
        )
    else:
        # Checks for API key first, then fall back to JWT token
        access_token = settings.get_access_token()

    if not access_token:
        logger.warning("No access token available!")
        raise HTTPException(401, "Unauthorized: No access token provided or expired.")

    return access_token
