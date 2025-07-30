"""Utility functions for regions operations."""

from typing import List, Dict, Any
from src.api.common import build_request


def fetch_shared_tier_regions() -> List[Dict[str, Any]]:
    """
    Fetch shared tier regions data from the API.

    Returns:
        List of region dictionaries containing region information

    Raises:
        Exception: If the API request fails or returns an error
    """
    try:
        regions_data = build_request("GET", "regions/sharedtier")
        return regions_data
    except Exception as e:
        raise Exception(f"Failed to list shared tier regions: {str(e)}")
