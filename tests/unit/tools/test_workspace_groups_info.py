"""Tests for workspace_groups_info tool function."""

from unittest.mock import patch, MagicMock
from uuid import uuid4

from src.api.tools.tools import workspace_groups_info


class TestWorkspaceGroupsInfo:
    """Tests for workspace_groups_info function."""

    @patch("src.api.tools.tools.build_request")
    @patch("src.config.config.get_settings")
    @patch("src.config.config.get_user_id")
    def test_workspace_groups_info_success(
        self, mock_get_user_id, mock_get_settings, mock_build_request
    ):
        """Test successful workspace groups retrieval."""
        # Setup
        mock_user_id = "user-123"
        mock_get_user_id.return_value = mock_user_id

        mock_settings = MagicMock()
        mock_analytics = MagicMock()
        mock_settings.analytics_manager = mock_analytics
        mock_get_settings.return_value = mock_settings

        mock_groups_data = [
            {
                "name": "production-group",
                "deploymentType": "PRODUCTION",
                "state": "ACTIVE",
                "workspaceGroupID": str(uuid4()),
                "firewallRanges": ["192.168.1.0/24"],
                "createdAt": "2023-01-01T00:00:00Z",
                "regionID": "us-west-2",
                "updateWindow": {"start": "02:00", "end": "04:00"},
            },
            {
                "name": "development-group",
                "deploymentType": "DEVELOPMENT",
                "state": "PAUSED",
                "workspaceGroupID": str(uuid4()),
                "firewallRanges": [],
                "createdAt": "2023-01-02T00:00:00Z",
                "regionID": "us-east-1",
                "updateWindow": {"start": "01:00", "end": "03:00"},
            },
        ]
        mock_build_request.return_value = mock_groups_data

        # Execute
        result = workspace_groups_info()

        # Verify
        assert result["status"] == "success"
        assert result["message"] == "Retrieved 2 workspace groups"
        assert len(result["data"]["workspace_groups"]) == 2
        assert result["metadata"]["count"] == 2
        assert result["metadata"]["state_summary"] == {"ACTIVE": 1, "PAUSED": 1}

        # Verify API call
        mock_build_request.assert_called_once_with("GET", "workspaceGroups")

        # Verify analytics tracking
        mock_analytics.track_event.assert_called_once_with(
            mock_user_id, "tool_calling", {"name": "workspace_groups_info"}
        )

    @patch("src.api.tools.tools.build_request")
    @patch("src.config.config.get_settings")
    @patch("src.config.config.get_user_id")
    def test_workspace_groups_info_empty(
        self, mock_get_user_id, mock_get_settings, mock_build_request
    ):
        """Test workspace groups retrieval with empty result."""
        # Setup
        mock_get_user_id.return_value = "user-123"
        mock_settings = MagicMock()
        mock_settings.analytics_manager = MagicMock()
        mock_get_settings.return_value = mock_settings
        mock_build_request.return_value = []

        # Execute
        result = workspace_groups_info()

        # Verify
        assert result["status"] == "success"
        assert result["message"] == "Retrieved 0 workspace groups"
        assert len(result["data"]["workspace_groups"]) == 0
        assert result["metadata"]["count"] == 0
        assert result["metadata"]["state_summary"] == {}
