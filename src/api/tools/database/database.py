"""Database tools for SingleStore MCP server."""

import time
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from mcp.server.fastmcp import Context

from src.config import config
from src.api.common import fetch_user, get_access_token
from src.api.tools.s2_manager import S2Manager
from src.api.tools.types import WorkspaceTarget
from src.auth.session_credentials_manager import (
    get_session_credentials_manager,
    invalidate_credentials,
)
from src.utils.uuid_validation import validate_workspace_id
from src.utils.elicitation import try_elicitation, ElicitationError
from src.logger import get_logger

# Set up logger for this module
logger = get_logger()


class DatabaseCredentials(BaseModel):
    """Schema for database authentication credentials when using API key."""

    username: str = Field(..., description="Database username for authentication")
    password: str = Field(..., description="Database password for authentication")


async def _get_database_credentials(
    ctx: Context, target: WorkspaceTarget, database_name: str | None = None
) -> tuple[str, str]:
    """
    Get database credentials based on the authentication method.

    Args:
        ctx: The MCP context
        target: The workspace target
        database_name: The database name to use for key generation

    Returns:
        Tuple of (username, password)

    Raises:
        Exception: If credentials cannot be obtained
    """
    settings = config.get_settings()

    # Check if we're using API key authentication
    is_using_api_key = (
        not settings.is_remote
        and isinstance(settings, config.LocalSettings)
        and settings.api_key is not None
    )

    if is_using_api_key:
        # For API key authentication, we need database credentials
        # Generate database key using credentials manager
        credentials_manager = get_session_credentials_manager()
        database_key = credentials_manager.generate_database_key(
            workspace_name=target.name, database_name=database_name
        )

        # Check if we have cached credentials for this database
        if credentials_manager.has_credentials(database_key):
            cached_creds = credentials_manager.get_credentials(database_key)
            if cached_creds:
                logger.debug(f"Using cached credentials for workspace: {target.name}")
                return cached_creds

        # Dedicated workspaces: need to request database credentials from user
        elicitation_message = (
            f"API key authentication detected. To connect to the dedicated workspace '{target.name}', "
            f"please provide your database username and password for this workspace."
        )

        try:
            elicitation_result, error = await try_elicitation(
                ctx=ctx, message=elicitation_message, schema=DatabaseCredentials
            )

            if error == ElicitationError.NOT_SUPPORTED:
                # Fallback: raise exception with clear message
                raise Exception(
                    "Database credentials required for API key authentication on dedicated workspaces. "
                    f"Please provide your database username and password for workspace '{target.name}'. "
                    "You can obtain these credentials from your SingleStore portal. "
                    "Note: This is different from your SingleStore account credentials - these are "
                    "database-specific credentials for connecting to the workspace."
                )
            elif elicitation_result.status == "success" and elicitation_result.data:
                username = elicitation_result.data.username
                password = elicitation_result.data.password

                # Store credentials in session cache for future use
                try:
                    credentials_manager.store_credentials(
                        database_key, username, password
                    )
                    logger.debug(f"Cached credentials for workspace: {target.name}")
                except Exception as e:
                    logger.warning(f"Failed to cache credentials: {e}")

                return (username, password)
            else:
                raise Exception(
                    "Database credentials are required but were not provided. Please ask the user to provide the database credentials"
                )
        except Exception as e:
            if "Database credentials required" in str(e):
                raise  # Re-raise our specific credential error
            logger.error(f"Error during credential elicitation: {e}")
            raise Exception(f"Failed to obtain database credentials: {str(e)}")
    else:
        # JWT authentication: use user_id and access_token as before
        user = fetch_user()
        return user.get("userID"), get_access_token()


async def __execute_sql_unified(
    ctx: Context,
    target: WorkspaceTarget,
    sql_query: str,
    username: str,
    password: str,
    database: str | None = None,
) -> dict:
    """
    Execute SQL operations on a connected workspace or starter workspace.
    Returns results and column names in a dictionary format.
    """

    if target.endpoint is None:
        raise ValueError("Workspace or starter workspace does not have an endpoint. ")
    endpoint = target.endpoint
    database_name = database

    # Parse host and port from endpoint
    if ":" in endpoint:
        host, port = endpoint.split(":", 1)
    else:
        host = endpoint
        port = None

    # Generate database key for credential management
    credentials_manager = get_session_credentials_manager()
    database_key = credentials_manager.generate_database_key(
        workspace_name=target.name, database_name=database_name
    )

    try:
        s2_manager = S2Manager(
            host=host,
            port=port,
            user=username,
            password=password,
            database=database_name,
        )

        workspace_type = "shared/virtual" if target.is_shared else "dedicated"
        await ctx.info(
            f"Executing SQL query on {workspace_type} workspace '{target.name}' with database '{database_name}': {sql_query}"
            "This query may take some time depending on the complexity and size of the data."
        )
        s2_manager.execute(sql_query)
        columns = (
            [desc[0] for desc in s2_manager.cursor.description]
            if s2_manager.cursor.description
            else []
        )
        rows = s2_manager.fetchmany()
        results = []
        for row in rows:
            result_dict = {}
            for i, column in enumerate(columns):
                result_dict[column] = row[i]
            results.append(result_dict)
        s2_manager.close()
        return {
            "data": results,
            "row_count": len(rows),
            "columns": columns,
            "status": "Success",
        }
    except Exception as e:
        # Check if this is an authentication error
        error_msg = str(e).lower()
        is_auth_error = any(
            auth_keyword in error_msg
            for auth_keyword in [
                "access denied",
                "authentication failed",
                "invalid credentials",
                "login failed",
                "permission denied",
                "unauthorized",
                "auth",
            ]
        )

        if is_auth_error:
            logger.warning(
                f"Authentication failed for database {database_key}, invalidating cached credentials"
            )
            invalidate_credentials(database_key)
            raise Exception(f"Authentication failed: {str(e)}")
        else:
            # Non-authentication error, re-raise as-is
            raise


def __get_workspace_by_id(workspace_id: str) -> WorkspaceTarget:
    """
    Get a workspace or starter workspace by ID.

    Args:
        workspace_id: The workspace ID to look up

    Returns:
        WorkspaceTarget object with is_shared flag indicating if it's a starter workspace

    Raises:
        ValueError: If workspace cannot be found
    """
    from src.api.common import build_request

    target = None
    is_shared = False

    try:
        # Try as dedicated workspace first
        workspace_data = build_request("GET", f"workspaces/{workspace_id}")

        # Create a simple object to match the SDK interface
        class SimpleWorkspace:
            def __init__(self, data):
                self.name = data.get("name", "")
                self.id = data.get("workspaceID", workspace_id)
                self.endpoint = data.get("endpoint")

        target = SimpleWorkspace(workspace_data)
        is_shared = False  # Dedicated workspace
    except Exception as e:
        if "404" in str(e):
            # Try as starter workspace
            try:
                starter_workspace_data = build_request(
                    "GET", f"sharedtier/virtualWorkspaces/{workspace_id}"
                )

                # Create a simple object to match the SDK interface
                class SimpleVirtualWorkspace:
                    def __init__(self, data):
                        self.name = data.get("name", "")
                        self.id = data.get("virtualWorkspaceID", workspace_id)
                        self.endpoint = data.get("endpoint")
                        self.database_name = data.get("databaseName", "")

                target = SimpleVirtualWorkspace(starter_workspace_data)
                is_shared = True  # Shared/starter workspace
            except Exception:
                raise ValueError(f"Cannot find workspace {workspace_id}")
        else:
            raise e

    if not target:
        raise ValueError(f"Cannot find workspace {workspace_id}")

    return WorkspaceTarget(target, is_shared)


async def run_sql(
    ctx: Context, sql_query: str, id: str, database: Optional[str] = None
) -> Dict[str, Any]:
    """
    Use this tool to execute a single SQL statement against a SingleStore database.

    Returns:
    - Query results with column names and typed values
    - Row count and metadata
    - Execution status
    - Workspace type ("shared" for starter workspaces, "dedicated" for regular workspaces)
    - Workspace name

    Args:
        id: Workspace or starter workspace ID
        sql_query: The SQL query to execute
        database: (optional) Database name to use

    Returns:
        Standardized response with query results and metadata
    """
    # Validate workspace ID format
    validated_id = validate_workspace_id(id)

    await ctx.info(
        f"Running SQL query on workspace ID '{validated_id}' with database '{database}': {sql_query}"
    )

    settings = config.get_settings()

    # Target can either be a workspace or a starter workspace
    target = __get_workspace_by_id(validated_id)
    database_name = database

    # For starter workspaces, use their database name if not specified
    if target.is_shared and target.database_name and not database_name:
        database_name = target.database_name

    # Get database credentials based on authentication method
    try:
        username, password = await _get_database_credentials(ctx, target, database_name)
    except Exception as e:
        if "Database credentials required" in str(e):
            # Handle the specific case where elicitation is not supported
            return {
                "status": "error",
                "message": str(e),
                "errorCode": "CREDENTIALS_REQUIRED",
                "workspace_id": validated_id,
                "workspace_name": target.name,
                "workspace_type": "shared" if target.is_shared else "dedicated",
                "instruction": (
                    "Please call this function again with the same parameters once you have "
                    "the database credentials available, or ask the user to provide their "
                    "database username and password for this workspace."
                ),
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to obtain database credentials: {str(e)}",
                "errorCode": "AUTHENTICATION_ERROR",
            }

    logger.debug(
        f"Credentials obtained for workspace '{target.name}': username='{username}', database='{database_name}, password='{password}'"
    )

    # Execute the SQL query
    start_time = time.time()
    try:
        result = await __execute_sql_unified(
            ctx=ctx,
            target=target,
            sql_query=sql_query,
            username=username,
            password=password,
            database=database_name,
        )
    except Exception as e:
        # Check if this is an authentication error from __execute_sql_unified
        if "Authentication failed:" in str(e):
            # Authentication error already handled by __execute_sql_unified (credentials invalidated)
            return {
                "status": "error",
                "message": str(e),
                "errorCode": "AUTHENTICATION_ERROR",
                "workspace_id": validated_id,
                "workspace_name": target.name,
                "workspace_type": "shared" if target.is_shared else "dedicated",
                "instruction": (
                    "Authentication failed. Please provide valid database credentials "
                    "for this workspace and try again."
                ),
            }
        else:
            # Non-authentication error, re-raise
            raise

    results_data = result.get("data", [])

    logger.debug(
        f"result: {results_data}, type: {type(results_data)}, id: {id}, database_name: {database_name}"
    )

    execution_time_ms = int((time.time() - start_time) * 1000)

    # Track analytics
    settings.analytics_manager.track_event(
        username,
        "tool_calling",
        {
            "name": "run_sql",
            "starter_workspace_id": id,
            "workspace_type": "shared" if target.is_shared else "dedicated",
        },
    )

    # Build standardized response
    workspace_type = "shared" if target.is_shared else "dedicated"
    row_count = len(results_data)

    return {
        "status": "success",
        "message": f"Query executed successfully. {row_count} rows returned.",
        "data": {
            "result": results_data,
            "row_count": row_count,
            "workspace_id": id,
            "workspace_name": target.name,
            "database": database_name,
            "status": result.get("status", "Success"),
        },
        "metadata": {
            "query_length": len(sql_query),
            "execution_time_ms": execution_time_ms,
            "workspace_type": workspace_type,
            "database_used": database_name,
            "executed_at": datetime.now().isoformat(),
        },
    }
