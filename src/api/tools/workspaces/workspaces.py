"""Workspaces tools for SingleStore MCP server."""

import time

from datetime import datetime, timezone

from src.config import config
from src.utils.uuid_validation import validate_uuid_string
from src.logger import get_logger
import src.api.tools.workspaces.utils as utils

# Set up logger for this module
logger = get_logger()


def workspaces_info(workspace_group_id: str) -> dict:
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
    # Validate workspace group ID format
    validated_group_id = validate_uuid_string(workspace_group_id)

    start_time = time.time()
    settings = config.get_settings()
    user_id = config.get_user_id()
    settings.analytics_manager.track_event(
        user_id,
        "tool_calling",
        {"name": "workspaces_info", "workspace_group_id": validated_group_id},
    )

    # Use the SDK to get workspaces for the group
    workspace_manager = utils.get_workspace_manager()
    try:
        group = workspace_manager.get_workspace_group(validated_group_id)
    except Exception as e:
        logger.error(f"Failed to fetch workspaces for group {validated_group_id}: {e}")
        return {
            "status": "error",
            "message": f"Failed to fetch workspaces for group {validated_group_id}: {str(e)}",
            "errorCode": "WORKSPACES_FETCH_FAILED",
        }

    workspaces = []
    for ws in group.workspaces:
        wdict = {
            "workspaceID": ws.id,
            "name": ws.name,
            "workspaceGroupID": getattr(ws, "group_id", None),
            "size": ws.size,
            "state": ws.state,
            "endpoint": ws.endpoint,
            "auto_suspend": ws.auto_suspend,
            "cache_config": ws.cache_config,
            "deployment_type": ws.deployment_type,
            "resume_attachments": ws.resume_attachments,
            "scaling_progress": ws.scaling_progress,
            "last_resumed_at": (
                ws.last_resumed_at.isoformat()
                if getattr(ws, "last_resumed_at", None)
                else None
            ),
            "created_at": (
                ws.created_at.isoformat() if getattr(ws, "created_at", None) else None
            ),
            "terminated_at": (
                ws.terminated_at.isoformat()
                if getattr(ws, "terminated_at", None)
                else None
            ),
        }
        workspaces.append(wdict)

    execution_time = (time.time() - start_time) * 1000

    return {
        "status": "success",
        "message": f"Retrieved {len(workspaces)} workspaces from group {workspace_group_id}",
        "data": workspaces,
        "metadata": {
            "execution_time_ms": round(execution_time, 2),
            "count": len(workspaces),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }


def resume_workspace(workspace_id: str) -> dict:
    """
    Resume a workspace within a specified workspace group in SingleStore.

    Args:
        workspace_group_id: Unique identifier of the workspace group
        workspace_id: Unique identifier of the workspace to resume

    Returns:
        Dictionary with status, message, and metadata about the resume operation
    """
    # Validate IDs
    try:
        validated_workspace_id = validate_uuid_string(workspace_id)
    except Exception as e:
        logger.error(f"Invalid ID(s): {e}")
        return {
            "status": "error",
            "message": f"Invalid ID(s): {str(e)}",
            "errorCode": "INVALID_ID",
        }

    start_time = time.time()
    settings = config.get_settings()
    user_id = config.get_user_id()

    # Analytics tracking
    try:
        settings.analytics_manager.track_event(
            user_id,
            "tool_calling",
            {
                "name": "resume_workspace",
                "workspace_id": validated_workspace_id,
            },
        )
    except Exception as e:
        logger.warning(f"Analytics tracking failed: {e}")

    workspace_manager = utils.get_workspace_manager()

    workspace = None
    # Get the workspace group
    try:
        workspace = workspace_manager.get_workspace(validated_workspace_id)
    except Exception as e:
        logger.error(f"Failed to fetch workspace {validated_workspace_id}: {e}")
        return {
            "status": "error",
            "message": f"Failed to fetch workspace {validated_workspace_id}: {str(e)}",
            "errorCode": "WORKSPACE_GROUP_FETCH_FAILED",
        }

    # Resume the workspace
    try:
        workspace.resume(wait_on_resumed=True)
        logger.info(f"Workspace {validated_workspace_id} resumed successfully")
    except Exception as e:
        logger.error(f"Failed to resume workspace {validated_workspace_id}: {e}")
        return {
            "status": "error",
            "message": f"Failed to resume workspace {validated_workspace_id}: {str(e)}",
            "errorCode": "WORKSPACE_RESUME_FAILED",
        }

    execution_time = (time.time() - start_time) * 1000

    return {
        "status": "success",
        "message": f"Workspace {workspace.name} resumed successfully",
        "data": {
            "workspaceID": workspace.id,
            "name": workspace.name,
            "workspaceGroupID": workspace.group_id,
            "state": workspace.state,
            "endpoint": workspace.endpoint,
            "last_resumed_at": (
                workspace.last_resumed_at.isoformat()
                if getattr(workspace, "last_resumed_at", None)
                else None
            ),
        },
        "metadata": {
            "execution_time_ms": round(execution_time, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
