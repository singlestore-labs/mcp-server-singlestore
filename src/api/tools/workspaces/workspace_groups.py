"""Workspace Groups tools for SingleStore MCP server."""

import time
from datetime import datetime, timezone

from src.config import config
from src.logger import get_logger

import src.api.tools.workspaces.utils as utils

# Set up logger for this module
logger = get_logger()


def workspace_groups_info() -> dict:
    """
    List all workspace groups accessible to the user in SingleStore.

    Returns detailed information for each group:
    - workspaceGroupID: Unique identifier for the group
    - name: Display name of the workspace group
    - region: Region information (name, provider)
    - firewallRanges: List of allowed IP ranges for the group
    - allowAllTraffic: Whether all traffic is allowed to the group
    - createdAt: Timestamp of group creation
    - terminatedAt: Timestamp when the group was terminated (if applicable)


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

    # Use workspace manager to get workspace groups
    workspace_manager = utils.get_workspace_manager()
    workspace_groups = workspace_manager.workspace_groups

    groups = [
        {
            "workspaceGroupID": group.id,
            "name": group.name,
            "region": {
                "regionName": group.region.name,
                "provider": group.region.provider,
            },
            "firewallRanges": group.firewall_ranges,
            "allowAllTraffic": group.allow_all_traffic,
            "createdAt": group.created_at.isoformat() if group.created_at else None,
            "terminatedAt": (
                group.terminated_at.isoformat() if group.terminated_at else None
            ),
        }
        for group in workspace_groups
    ]

    execution_time = (time.time() - start_time) * 1000

    return {
        "status": "success",
        "message": f"Retrieved {len(groups)} workspace groups",
        "data": groups,
        "metadata": {
            "execution_time_ms": round(execution_time, 2),
            "count": len(groups),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
