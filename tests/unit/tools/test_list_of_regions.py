"""Tests for list_of_regions tool function."""

from unittest.mock import patch

from src.api.tools.tools import list_of_regions


class TestListOfRegions:
    """Tests for list_of_regions function."""

    @patch("src.api.tools.tools.build_request")
    def test_list_of_regions_success(self, mock_build_request):
        """Test successful regions list retrieval."""
        # Setup
        mock_regions_data = [
            {
                "regionID": "us-west-2",
                "provider": "AWS",
                "name": "US West 2 (Oregon)",
            },
            {
                "regionID": "us-east-1",
                "provider": "AWS",
                "name": "US East 1 (Virginia)",
            },
            {
                "regionID": "europe-west2",
                "provider": "GCP",
                "name": "Europe West 2 (London)",
            },
        ]
        mock_build_request.return_value = mock_regions_data

        # Execute
        result = list_of_regions()

        # Verify
        assert result["status"] == "success"
        assert result["message"] == "Retrieved 3 available deployment regions"
        assert result["data"]["regions"] == mock_regions_data
        assert result["metadata"]["count"] == 3
        assert result["metadata"]["provider_summary"] == {"AWS": 2, "GCP": 1}

        # Verify API call
        mock_build_request.assert_called_once_with("GET", "regions")

    @patch("src.api.tools.tools.build_request")
    def test_list_of_regions_empty(self, mock_build_request):
        """Test regions list retrieval with empty result."""
        # Setup
        mock_build_request.return_value = []

        # Execute
        result = list_of_regions()

        # Verify
        assert result["status"] == "success"
        assert result["message"] == "Retrieved 0 available deployment regions"
        assert len(result["data"]["regions"]) == 0
        assert result["metadata"]["count"] == 0
        assert result["metadata"]["provider_summary"] == {}

    @patch("src.api.tools.tools.build_request")
    def test_list_of_regions_missing_provider(self, mock_build_request):
        """Test regions list with missing provider information."""
        # Setup
        mock_regions_data = [
            {
                "regionID": "unknown-region",
                "name": "Unknown Region",
                # Missing provider field
            }
        ]
        mock_build_request.return_value = mock_regions_data

        # Execute
        result = list_of_regions()

        # Verify
        assert result["status"] == "success"
        assert result["metadata"]["provider_summary"] == {"Unknown": 1}
