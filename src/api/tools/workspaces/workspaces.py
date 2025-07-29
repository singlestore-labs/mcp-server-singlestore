"""Workspaces tools for SingleStore MCP server."""

import time
from datetime import datetime, timezone

from src.config import config
from src.api.common import build_request
from src.utils.uuid_validation import validate_uuid_string
from src.logger import get_logger

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

    workspaces_data = build_request(
        "GET",
        "workspaces",
        {"workspaceGroupID": validated_group_id},
    )

    workspaces = [
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
        for workspace in workspaces_data
    ]

    # Calculate state summary and sizes
    state_counts = {}
    size_counts = {}
    for workspace in workspaces:
        state = workspace["state"]
        state_counts[state] = state_counts.get(state, 0) + 1

        size = workspace["size"]
        size_counts[size] = size_counts.get(size, 0) + 1

    execution_time = (time.time() - start_time) * 1000

    return {
        "status": "success",
        "message": f"Retrieved {len(workspaces)} workspaces from group {workspace_group_id}",
        "data": {"result": workspaces},
        "metadata": {
            "execution_time_ms": round(execution_time, 2),
            "workspace_group_id": workspace_group_id,
            "count": len(workspaces),
            "state_summary": state_counts,
            "size_summary": size_counts,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
