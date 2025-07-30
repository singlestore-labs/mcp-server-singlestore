"""User tools for SingleStore MCP server."""

import time
from datetime import datetime, timezone
from typing import Dict, Any

from mcp.server.fastmcp import Context

from src.config import config
from src.api.common import fetch_user
from src.logger import get_logger

# Set up logger for this module
logger = get_logger()


def get_user_info(ctx: Context) -> Dict[str, Any]:
    """
    Retrieve all information about the current user.

    Returns:
        dict: User information including userID, email, firstName, lastName.

    Performance Tip:
    Cache the returned info when making multiple API calls.
    """
    start_time = time.time()
    settings = config.get_settings()
    user_id = config.get_user_id()
    # Track tool call event
    settings.analytics_manager.track_event(
        user_id, "tool_calling", {"name": "get_user_info"}
    )

    # Simulate retrieving user info (replace with actual API call if available)
    user_info = fetch_user()
    execution_time = (time.time() - start_time) * 1000

    return {
        "status": "success",
        "message": "Retrieved user information successfully",
        "data": {"result": user_info},
        "metadata": {
            "execution_time_ms": round(execution_time, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
