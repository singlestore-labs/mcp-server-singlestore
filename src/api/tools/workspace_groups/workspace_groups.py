"""Workspace Groups tools for SingleStore MCP server."""

import time
from datetime import datetime, timezone

from src.config import config
from src.api.common import build_request
from src.logger import get_logger

# Set up logger for this module
logger = get_logger()


def workspace_groups_info() -> dict:
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
    start_time = time.time()
    settings = config.get_settings()
    user_id = config.get_user_id()
    settings.analytics_manager.track_event(
        user_id, "tool_calling", {"name": "workspace_groups_info"}
    )

    groups_data = build_request("GET", "workspaceGroups")
    groups = [
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
        for group in groups_data
    ]

    # Calculate states summary
    state_counts = {}
    for group in groups:
        state = group["state"]
        state_counts[state] = state_counts.get(state, 0) + 1

    execution_time = (time.time() - start_time) * 1000

    return {
        "status": "success",
        "message": f"Retrieved {len(groups)} workspace groups",
        "data": {
            "result": groups,
        },
        "metadata": {
            "execution_time_ms": round(execution_time, 2),
            "count": len(groups),
            "state_summary": state_counts,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
