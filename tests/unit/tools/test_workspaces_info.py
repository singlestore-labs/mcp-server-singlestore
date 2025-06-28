"""Tests for workspaces_info tool function."""

import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4

from src.api.tools.tools import workspaces_info


class TestWorkspacesInfo:
    """Tests for workspaces_info function."""

    @patch("src.api.tools.tools.build_request")
    @patch("src.api.tools.tools.validate_uuid_string")
    @patch("src.config.config.get_settings")
    @patch("src.config.config.get_user_id")
    def test_workspaces_info_success(
        self,
        mock_get_user_id,
        mock_get_settings,
        mock_validate_uuid,
        mock_build_request,
    ):
        """Test successful workspaces retrieval."""
        # Setup
        workspace_group_id = str(uuid4())
        mock_validate_uuid.return_value = workspace_group_id
        mock_get_user_id.return_value = "user-123"

        mock_settings = MagicMock()
        mock_settings.analytics_manager = MagicMock()
        mock_get_settings.return_value = mock_settings

        mock_workspaces_data = [
            {
                "createdAt": "2023-01-01T00:00:00Z",
                "deploymentType": "PRODUCTION",
                "endpoint": "https://workspace1.example.com",
                "name": "prod-workspace",
                "size": "S-00",
                "state": "ACTIVE",
                "terminatedAt": None,
                "workspaceGroupID": workspace_group_id,
                "workspaceID": str(uuid4()),
            },
            {
                "createdAt": "2023-01-02T00:00:00Z",
                "deploymentType": "DEVELOPMENT",
                "endpoint": "https://workspace2.example.com",
                "name": "dev-workspace",
                "size": "S-01",
                "state": "PAUSED",
                "terminatedAt": False,
                "workspaceGroupID": workspace_group_id,
                "workspaceID": str(uuid4()),
            },
        ]
        mock_build_request.return_value = mock_workspaces_data

        # Execute
        result = workspaces_info(workspace_group_id)

        # Verify
        assert result["status"] == "success"
        assert (
            result["message"]
            == f"Retrieved 2 workspaces from group {workspace_group_id}"
        )
        assert len(result["data"]["workspaces"]) == 2
        assert result["metadata"]["count"] == 2
        assert result["metadata"]["state_summary"] == {"ACTIVE": 1, "PAUSED": 1}
        assert result["metadata"]["size_summary"] == {"S-00": 1, "S-01": 1}

        # Verify API call
        mock_build_request.assert_called_once_with(
            "GET", "workspaces", {"workspaceGroupID": workspace_group_id}
        )

    @patch("src.api.tools.tools.validate_uuid_string")
    def test_workspaces_info_invalid_group_id(self, mock_validate_uuid):
        """Test workspaces info with invalid group ID."""
        # Setup
        mock_validate_uuid.side_effect = ValueError("Invalid UUID format")

        # Execute & Verify
        with pytest.raises(ValueError, match="Invalid UUID format"):
            workspaces_info("invalid-uuid")
