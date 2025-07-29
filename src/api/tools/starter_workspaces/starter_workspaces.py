"""Starter workspaces tools for SingleStore MCP server."""

from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel, Field

from mcp.server.fastmcp import Context

from src.config import config
from src.api.common import build_request
from src.utils.uuid_validation import validate_workspace_id
from src.utils.elicitation import try_elicitation, ElicitationError
from src.logger import get_logger

# Set up logger for this module
logger = get_logger()


def list_virtual_workspaces() -> Dict[str, Any]:
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
    workspaces = build_request("GET", "sharedtier/virtualWorkspaces")

    return {
        "status": "success",
        "message": f"Retrieved {len(workspaces)} virtual workspaces",
        "data": {"result": workspaces, "count": len(workspaces)},
        "metadata": {
            "total_count": len(workspaces),
            "active_count": sum(1 for w in workspaces if w.get("state") == "ACTIVE"),
            "retrieved_at": datetime.now().isoformat(),
        },
    }


async def create_starter_workspace(
    ctx: Context, name: str, database_name: str
) -> Dict[str, Any]:
    """
    Create a new starter workspace using the SingleStore SDK.

    This tool provides a modern SDK-based approach to creating starter workspaces,
    offering improved reliability and better error handling compared to direct API calls.

    Args:
        name: Unique name for the new starter workspace
        database_name: Name of the database to create in the starter workspace

    Returns:
        Dictionary with starter workspace creation details including:
        - workspace_id: Unique identifier for the created workspace
        - name: Display name of the workspace
        - endpoint: Connection endpoint URL
        - database_name: Name of the primary database

    Example Usage:
    ```python
    result = create_starter_workspace(
        ctx=ctx,
        name="my-test-workspace",
        database_name="analytics_db"
    )
    workspace_id = result["workspace_id"]
    endpoint = result["endpoint"]
    ```
    """
    await ctx.info(
        f"Creating starter workspace '{name}' with database '{database_name}'"
    )

    settings = config.get_settings()
    user_id = config.get_user_id()

    # Track analytics event
    settings.analytics_manager.track_event(
        user_id,
        "tool_calling",
        {
            "name": "create_starter_workspace",
            "workspace_name": name,
            "database_name": database_name,
        },
    )

    try:
        # Create the starter workspace using the API
        payload = {
            "name": name,
            "databaseName": database_name,
            # TODO: Dinamically set region_id if needed
            "workspaceGroup": {"cellID": "3482219c-a389-4079-b18b-d50662524e8a"},
        }

        starter_workspace_data = build_request(
            "POST", "sharedtier/virtualWorkspaces", data=payload
        )

        await ctx.info(
            f"Starter workspace '{name}' created successfully with ID: {starter_workspace_data.get('virtualWorkspaceID')}"
        )

        return {
            "status": "success",
            "message": f"Starter workspace '{name}' created successfully",
            "workspace_id": starter_workspace_data.get("virtualWorkspaceID"),
            "name": starter_workspace_data.get("name"),
            "endpoint": starter_workspace_data.get("endpoint"),
            "database_name": starter_workspace_data.get("databaseName"),
        }

    except Exception as e:
        error_msg = f"Failed to create starter workspace '{name}': {str(e)}"
        ctx.error(error_msg)

        return {
            "status": "error",
            "message": error_msg,
            "error": str(e),
            "workspace_name": name,
            "database_name": database_name,
        }


async def terminate_virtual_workspace(
    ctx: Context,
    workspace_id: str,
) -> Dict[str, Any]:
    """
    Permanently delete a virtual workspace in SingleStore with safety confirmations.

    ⚠️  WARNING: This action CANNOT be undone. All workspace data will be permanently lost.
    Make sure to backup important data before proceeding.

    Safety Features:
    - Requires explicit user confirmation (if elicitation is supported)
    - Validates workspace existence
    - Provides warning messages
    - Includes error handling

    Args:
        ctx: Context for user interaction and logging
        workspace_id: Workspace identifier (format: "ws-" followed by alphanumeric chars)

    Returns:
        {
            "status": "success" | "error" | "cancelled",
            "message": str,  # Human-readable result
            "workspace_id": str,
            "workspace_name": str,  # If available
            "termination_time": str,  # ISO 8601 (if successful)
            "error": str  # If status="error"
        }

    Example:
    ```python
    result = await terminate_virtual_workspace(ctx, "ws-abc123")
    if result["status"] == "success":
        print(f"Workspace {result['workspace_name']} terminated")
    ```

    Related:
    - list_virtual_workspaces()
    - create_starter_workspace()
    """
    # Validate workspace ID format
    validated_workspace_id = validate_workspace_id(workspace_id)

    settings = config.get_settings()
    user_id = config.get_user_id()

    try:
        starter_workspace_data = build_request(
            "GET", f"sharedtier/virtualWorkspaces/{validated_workspace_id}"
        )
        workspace_name = starter_workspace_data.get("name")
        await ctx.info(
            f"Found virtual workspace '{workspace_name}' (ID: {validated_workspace_id})"
        )

        class TerminationConfirmation(BaseModel):
            """Schema for collecting organization selection."""

            confirm: bool = Field(
                description="Do you really want to terminate this virtual workspace?",
                default=False,
            )

        # Check if elicitation is supported
        elicit_result, error = await try_elicitation(
            ctx=ctx,
            message=f"⚠️ **WARNING**: You are about to terminate the virtual workspace '{workspace_name}'.\n\n"
            "This action is permanent and cannot be undone. All data in the workspace will be lost.\n\n"
            "Do you want to proceed with the termination?",
            schema=TerminationConfirmation,
        )

        # Skip confirmation if elicitation is not supported
        if error == ElicitationError.NOT_SUPPORTED:
            await ctx.info(
                "Proceeding with termination without confirmation since interactive confirmation is not supported."
            )
        else:
            # Only check confirmation if elicitation was supported
            if not (
                elicit_result.status == "success"
                and elicit_result.data
                and elicit_result.data.confirm
            ):
                return {
                    "status": "cancelled",
                    "message": "Workspace termination was cancelled by the user",
                    "workspace_id": validated_workspace_id,
                    "workspace_name": workspace_name,
                }

        # Track analytics event
        settings.analytics_manager.track_event(
            user_id,
            "tool_calling",
            {
                "name": "terminate_virtual_workspace",
                "workspace_id": validated_workspace_id,
            },
        )

        await ctx.info(
            f"Proceeding with termination of virtual workspace: {validated_workspace_id}"
        )

        # Terminate the virtual workspace
        build_request(
            "DELETE", f"sharedtier/virtualWorkspaces/{validated_workspace_id}"
        )

        success_message = (
            f"Virtual workspace '{workspace_name}' terminated successfully"
        )
        await ctx.info(success_message)

        return {
            "status": "success",
            "message": success_message,
            "workspace_id": validated_workspace_id,
            "workspace_name": workspace_name,
            "termination_time": datetime.now().isoformat(),
        }

    except Exception as e:
        error_msg = f"Failed to terminate virtual workspace '{validated_workspace_id}': {str(e)}"
        ctx.error(error_msg)

        return {
            "status": "error",
            "message": error_msg,
            "error": str(e),
            "workspace_id": validated_workspace_id,
        }
