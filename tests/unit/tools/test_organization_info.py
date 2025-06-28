"""Tests for organization_info tool function."""

from unittest.mock import patch, MagicMock
from uuid import uuid4

from src.api.tools.tools import organization_info


class TestOrganizationInfo:
    """Tests for organization_info function."""

    @patch("src.api.tools.tools.build_request")
    @patch("src.config.config.get_settings")
    @patch("src.config.config.get_user_id")
    def test_organization_info_success(
        self, mock_get_user_id, mock_get_settings, mock_build_request
    ):
        """Test successful organization info retrieval."""
        # Setup
        mock_get_user_id.return_value = "user-123"

        mock_settings = MagicMock()
        mock_settings.analytics_manager = MagicMock()
        mock_get_settings.return_value = mock_settings

        mock_org_data = {
            "orgID": str(uuid4()),
            "name": "Acme Corporation",
            "description": "A test organization",
            "createdAt": "2023-01-01T00:00:00Z",
        }
        mock_build_request.return_value = mock_org_data

        # Execute
        result = organization_info()

        # Verify
        assert result["status"] == "success"
        assert (
            result["message"]
            == "Retrieved organization information for 'Acme Corporation'"
        )
        assert result["data"]["organization"] == mock_org_data
        assert result["metadata"]["org_id"] == mock_org_data["orgID"]

        # Verify API call
        mock_build_request.assert_called_once_with("GET", "organizations/current")

    @patch("src.api.tools.tools.build_request")
    @patch("src.config.config.get_settings")
    @patch("src.config.config.get_user_id")
    def test_organization_info_no_name(
        self, mock_get_user_id, mock_get_settings, mock_build_request
    ):
        """Test organization info retrieval when name is missing."""
        # Setup
        mock_get_user_id.return_value = "user-123"

        mock_settings = MagicMock()
        mock_settings.analytics_manager = MagicMock()
        mock_get_settings.return_value = mock_settings

        mock_org_data = {
            "orgID": str(uuid4()),
            "description": "A test organization",
        }
        mock_build_request.return_value = mock_org_data

        # Execute
        result = organization_info()

        # Verify
        assert result["status"] == "success"
        assert result["message"] == "Retrieved organization information for 'Unknown'"
        assert result["data"]["organization"] == mock_org_data
