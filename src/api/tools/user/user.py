"""User tools for SingleStore MCP server."""

import time
from datetime import datetime, timezone
from typing import Dict, Any

from mcp.server.fastmcp import Context

from src.config import config
from src.api.common import __get_user_id
from src.logger import get_logger

# Set up logger for this module
logger = get_logger()


def get_user_id(ctx: Context) -> Dict[str, Any]:
    """
    Retrieve the current user's unique identifier.

    Returns:
        str: UUID format identifier for the current user

    Required for:
    - Constructing paths or references to personal resources

    Performance Tip:
    Cache the returned ID when making multiple API calls.
    """
    start_time = time.time()
    settings = config.get_settings()
    user_id = config.get_user_id()
    # Track tool call event
    settings.analytics_manager.track_event(
        user_id, "tool_calling", {"name": "get_user_id"}
    )

    retrieved_user_id = __get_user_id()
    execution_time = (time.time() - start_time) * 1000

    return {
        "status": "success",
        "message": "Retrieved user ID successfully",
        "data": {"result": retrieved_user_id},
        "metadata": {
            "execution_time_ms": round(execution_time, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
