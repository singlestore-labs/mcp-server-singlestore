"""Tests for terminate_virtual_workspace tool function."""

import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4

from mcp.server.fastmcp import Context
from src.api.tools.tools import terminate_virtual_workspace


class TestTerminateVirtualWorkspace:
    """Tests for terminate_virtual_workspace function."""

    def setup_method(self):
        """Set up common test fixtures before each test method."""
        self.workspace_id = f"ws-{uuid4()}"
        self.workspace_name = "test-workspace"

        # Mock context
        self.mock_ctx = MagicMock(spec=Context)
        self.mock_ctx.info = MagicMock()
        self.mock_ctx.warning = MagicMock()
        self.mock_ctx.error = MagicMock()

        # Mock return values
        self.mock_user_id = "user-123"
        self.mock_org_id = "org-456"
        self.mock_access_token = "token-789"
        self.mock_api_base_url = "https://api.singlestore.com"

        # Mock settings
        self.mock_settings = MagicMock()
        self.mock_settings.analytics_manager = MagicMock()
        self.mock_settings.s2_api_base_url = self.mock_api_base_url

    @patch("src.api.tools.tools.s2.manage_workspaces")
    @patch("src.api.tools.tools.get_access_token")
    @patch("src.api.tools.tools.get_org_id")
    @patch("src.api.tools.tools.validate_workspace_id")
    @patch("src.config.config.get_settings")
    @patch("src.config.config.get_user_id")
    def test_terminate_virtual_workspace_success(
        self,
        mock_get_user_id,
        mock_get_settings,
        mock_validate_workspace_id,
        mock_get_org_id,
        mock_get_access_token,
        mock_manage_workspaces,
    ):
        """Test successful virtual workspace termination."""
        # Setup mocks
        mock_validate_workspace_id.return_value = self.workspace_id
        mock_get_user_id.return_value = self.mock_user_id
        mock_get_org_id.return_value = self.mock_org_id
        mock_get_access_token.return_value = self.mock_access_token
        mock_get_settings.return_value = self.mock_settings

        # Mock workspace manager
        mock_workspace_manager = MagicMock()
        mock_manage_workspaces.return_value = mock_workspace_manager

        mock_starter_workspace = MagicMock()
        mock_starter_workspace.name = self.workspace_name
        mock_workspace_manager.get_starter_workspace.return_value = (
            mock_starter_workspace
        )
        mock_workspace_manager.terminate_starter_workspace.return_value = None

        # Execute
        result = terminate_virtual_workspace(self.mock_ctx, self.workspace_id)

        # Verify
        assert result["status"] == "success"
        assert (
            result["message"]
            == f"Virtual workspace '{self.workspace_name}' terminated successfully"
        )
        assert result["workspace_id"] == self.workspace_id
        assert result["workspace_name"] == self.workspace_name
        assert "termination_time" in result

        # Verify function calls
        mock_validate_workspace_id.assert_called_once_with(self.workspace_id)
        mock_manage_workspaces.assert_called_once_with(
            access_token=self.mock_access_token,
            base_url=self.mock_api_base_url,
            organization_id=self.mock_org_id,
        )
        mock_workspace_manager.get_starter_workspace.assert_called_once_with(
            self.workspace_id
        )
        mock_workspace_manager.terminate_starter_workspace.assert_called_once_with(
            self.workspace_id
        )

        # Verify analytics tracking
        self.mock_settings.analytics_manager.track_event.assert_called_once_with(
            self.mock_user_id,
            "tool_calling",
            {
                "name": "terminate_virtual_workspace",
                "workspace_id": self.workspace_id,
            },
        )

    @patch("src.api.tools.tools.validate_workspace_id")
    def test_terminate_virtual_workspace_invalid_id(self, mock_validate_workspace_id):
        """Test terminate virtual workspace with invalid ID."""
        mock_validate_workspace_id.side_effect = ValueError(
            "Invalid workspace ID format"
        )

        # Execute & Verify
        with pytest.raises(ValueError, match="Invalid workspace ID format"):
            terminate_virtual_workspace(self.mock_ctx, "invalid-id")

    @patch("src.api.tools.tools.s2.manage_workspaces")
    @patch("src.api.tools.tools.get_access_token")
    @patch("src.api.tools.tools.get_org_id")
    @patch("src.api.tools.tools.validate_workspace_id")
    @patch("src.config.config.get_settings")
    @patch("src.config.config.get_user_id")
    def test_terminate_virtual_workspace_not_found(
        self,
        mock_get_user_id,
        mock_get_settings,
        mock_validate_workspace_id,
        mock_get_org_id,
        mock_get_access_token,
        mock_manage_workspaces,
    ):
        """Test terminate virtual workspace when workspace not found."""
        # Setup mocks
        mock_validate_workspace_id.return_value = self.workspace_id
        mock_get_user_id.return_value = self.mock_user_id
        mock_get_org_id.return_value = self.mock_org_id
        mock_get_access_token.return_value = self.mock_access_token
        mock_get_settings.return_value = self.mock_settings

        # Mock workspace manager
        mock_workspace_manager = MagicMock()
        mock_manage_workspaces.return_value = mock_workspace_manager
        mock_workspace_manager.get_starter_workspace.side_effect = Exception(
            "404: Not Found"
        )

        # Execute
        result = terminate_virtual_workspace(self.mock_ctx, self.workspace_id)

        # Verify
        assert result["status"] == "error"
        assert "does not exist or has already been terminated" in result["message"]
        assert result["workspace_id"] == self.workspace_id

    @patch("src.api.tools.tools.s2.manage_workspaces")
    @patch("src.api.tools.tools.get_access_token")
    @patch("src.api.tools.tools.get_org_id")
    @patch("src.api.tools.tools.validate_workspace_id")
    @patch("src.config.config.get_settings")
    @patch("src.config.config.get_user_id")
    def test_terminate_virtual_workspace_termination_error(
        self,
        mock_get_user_id,
        mock_get_settings,
        mock_validate_workspace_id,
        mock_get_org_id,
        mock_get_access_token,
        mock_manage_workspaces,
    ):
        """Test terminate virtual workspace when termination fails."""
        # Setup mocks
        mock_validate_workspace_id.return_value = self.workspace_id
        mock_get_user_id.return_value = self.mock_user_id
        mock_get_org_id.return_value = self.mock_org_id
        mock_get_access_token.return_value = self.mock_access_token
        mock_get_settings.return_value = self.mock_settings

        # Mock workspace manager
        mock_workspace_manager = MagicMock()
        mock_manage_workspaces.return_value = mock_workspace_manager

        mock_starter_workspace = MagicMock()
        mock_starter_workspace.name = self.workspace_name
        mock_workspace_manager.get_starter_workspace.return_value = (
            mock_starter_workspace
        )
        mock_workspace_manager.terminate_starter_workspace.side_effect = Exception(
            "Termination failed"
        )

        # Execute
        result = terminate_virtual_workspace(self.mock_ctx, self.workspace_id)

        # Verify
        assert result["status"] == "error"
        assert "Failed to terminate virtual workspace" in result["message"]
        assert result["workspace_id"] == self.workspace_id
        assert "Termination failed" in result["error"]
