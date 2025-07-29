"""Regions tools for SingleStore MCP server."""

import time
from datetime import datetime, timezone

from src.api.common import build_request
from src.logger import get_logger

# Set up logger for this module
logger = get_logger()


def list_regions() -> dict:
    """
    List all available deployment regions where SingleStore workspaces can be deployed by the user.

    Returns region information including:
    - regionID: Unique identifier for the region
    - provider: Cloud provider (AWS, GCP, or Azure)
    - name: Human-readable region name (e.g., Europe West 2 (London), US West 2 (Oregon))

    Use this tool to:
    1. Select optimal deployment regions based on:
       - Geographic proximity to users
       - Compliance requirements
       - Cost considerations
       - Available cloud providers
    2. Plan multi-region deployments
    """
    start_time = time.time()
    regions_data = build_request("GET", "regions")

    # Group regions by provider
    provider_counts = {}
    for region in regions_data:
        provider = region.get("provider", "Unknown")
        provider_counts[provider] = provider_counts.get(provider, 0) + 1

    execution_time = (time.time() - start_time) * 1000

    return {
        "status": "success",
        "message": f"Retrieved {len(regions_data)} available deployment regions",
        "data": {"result": regions_data},
        "metadata": {
            "execution_time_ms": round(execution_time, 2),
            "count": len(regions_data),
            "provider_summary": provider_counts,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
