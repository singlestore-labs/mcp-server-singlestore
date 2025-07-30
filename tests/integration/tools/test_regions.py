import pytest
import src.api.tools as tools


@pytest.mark.integration
class TestRegionsIntegration:
    @pytest.mark.asyncio
    async def test_list_regions(self, mock_context):
        result = await tools.list_regions(ctx=mock_context)

        assert result["status"] == "success"

        assert "data" in result

        # Verify the data structure
        data = result["data"]
        assert "result" in data
        regions_data = data["result"]

        assert isinstance(regions_data, list)
        assert len(regions_data) > 0
        for region in regions_data:
            assert "regionID" in region
            assert "provider" in region
            assert "region" in region
            assert region["regionID"] is not None
            assert region["provider"] in ["AWS", "GCP", "Azure"]
            assert region["region"] is not None

    @pytest.mark.asyncio
    async def test_list_sharedtier_regions(self, mock_context):
        result = await tools.list_sharedtier_regions(ctx=mock_context)

        assert result["status"] == "success"

        assert "data" in result

        # Verify the data structure

        data = result["data"]
        assert "result" in data
        sharedtier_regions_data = data["result"]

        assert isinstance(sharedtier_regions_data, list)
        assert len(sharedtier_regions_data) > 0
        for region in sharedtier_regions_data:
            assert "regionName" in region
            assert "provider" in region
            assert "region" in region
            assert region["regionName"] is not None
            assert region["provider"] in ["AWS", "GCP", "Azure"]
            assert region["region"] is not None
