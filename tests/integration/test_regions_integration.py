
import pytest
from unittest.mock import patch, AsyncMock
from src.api.tools.regions import regions

@pytest.mark.asyncio
async def test_list_regions_success():
    mock_regions = [
        {"regionID": "us-west-2", "provider": "AWS", "name": "US West 2 (Oregon)"},
        {"regionID": "europe-west1", "provider": "GCP", "name": "Europe West 1 (Belgium)"},
    ]
    mock_ctx = AsyncMock()
    with patch("src.api.tools.regions.regions.build_request", return_value=mock_regions):
        result = await regions.list_regions(mock_ctx)
        assert result["status"] == "success"
        assert result["data"]["result"] == mock_regions
        assert result["metadata"]["count"] == 2
        mock_ctx.info.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_regions_error():
    mock_ctx = AsyncMock()
    with patch("src.api.tools.regions.regions.build_request", side_effect=Exception("API error")):
        result = await regions.list_regions(mock_ctx)
        assert result["status"] == "error"
        assert "API error" in result["message"]
        mock_ctx.error.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_sharedtier_regions_success():
    mock_regions = [
        {"regionName": "us-west-2", "provider": "AWS", "name": "US West 2 (Oregon)"},
        {
            "regionName": "europe-west1",
            "provider": "GCP",
            "name": "Europe West 1 (Belgium)",
        },
    ]
    mock_ctx = AsyncMock()
    with patch(
        "src.api.tools.regions.regions.fetch_shared_tier_regions",
        return_value=mock_regions,
    ):
        result = await regions.list_sharedtier_regions(mock_ctx)
        assert result["status"] == "success"
        assert result["data"]["result"] == mock_regions
        assert result["metadata"]["count"] == 2
        mock_ctx.info.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_sharedtier_regions_error():
    mock_ctx = AsyncMock()
    with patch(
        "src.api.tools.regions.regions.fetch_shared_tier_regions",
        side_effect=Exception("API error"),
    ):
        result = await regions.list_sharedtier_regions(mock_ctx)
        assert result["status"] == "error"
        assert "API error" in result["message"]
        mock_ctx.error.assert_awaited_once()
