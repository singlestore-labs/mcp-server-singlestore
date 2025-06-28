"""Tests for get_user_id tool function."""

import pytest
from unittest.mock import patch, MagicMock

from mcp.server.fastmcp import Context
from src.api.tools.tools import get_user_id


class TestGetUserId:
    """Tests for get_user_id function."""

    @patch("src.config.config.get_settings")
    @patch("src.api.tools.tools.__get_user_id")
    def test_get_user_id_success(self, mock_get_user_id, mock_get_settings):
        """Test successful user ID retrieval."""
        # Setup
        mock_user_id = "user-12345"
        mock_get_user_id.return_value = mock_user_id

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.analytics_manager = MagicMock()
        mock_get_settings.return_value = mock_settings

        mock_ctx = MagicMock(spec=Context)

        # Execute
        result = get_user_id(mock_ctx)

        # Verify
        assert result["status"] == "success"
        assert result["message"] == "Retrieved user ID successfully"
        assert result["data"]["user_id"] == mock_user_id
        assert "metadata" in result
        mock_get_user_id.assert_called_once()

    @patch("src.config.config.get_settings")
    @patch("src.api.tools.tools.__get_user_id")
    def test_get_user_id_error(self, mock_get_user_id, mock_get_settings):
        """Test user ID retrieval with error."""
        # Setup
        mock_get_user_id.side_effect = Exception("Authentication failed")

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.analytics_manager = MagicMock()
        mock_get_settings.return_value = mock_settings

        mock_ctx = MagicMock(spec=Context)

        # Execute & Verify
        with pytest.raises(Exception, match="Authentication failed"):
            get_user_id(mock_ctx)
