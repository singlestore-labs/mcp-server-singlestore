"""Regions tools for SingleStore MCP server."""

import time
from datetime import datetime, timezone
from typing import Any, Dict

from mcp.server.fastmcp import Context

from src.api.common import build_request
from src.api.tools.regions.utils import fetch_shared_tier_regions
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


async def list_sharedtier_regions(ctx: Context) -> Dict[str, Any]:
    """
    List all regions where shared tier workspaces can be created.

    This tool provides information about available regions for creating starter workspaces,
    including region names and cloud providers.

    Args:
        ctx: Context for user interaction and logging

    Returns:
        Dictionary with region information including:
        - regionName: Name of the region (e.g., "us-west-2", "europe-west1")
        - provider: Cloud provider (AWS, GCP, or Azure)
        - name: Human-readable region name (e.g., Europe West 2 (London), US West 2 (Oregon))

    Example Usage:
    ```python
    result = await list_shared_tier_regions(ctx)
    regions = result["data"]["result"]
    ```
    """
    await ctx.info("Listing available shared tier regions...")

    try:
        regions_data = fetch_shared_tier_regions()

        return {
            "status": "success",
            "message": f"Retrieved {len(regions_data)} shared tier regions",
            "data": {"result": regions_data},
            "metadata": {
                "execution_time_ms": 100,  # Placeholder for actual execution time
                "count": len(regions_data),
                "timestamp": datetime.now().isoformat(),
            },
        }

    except Exception as e:
        error_msg = str(e)
        await ctx.error(error_msg)

        return {
            "status": "error",
            "message": error_msg,
            "error": str(e),
        }
