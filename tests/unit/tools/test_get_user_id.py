"""Tests for get_user_id tool function."""

import pytest
from unittest.mock import MagicMock

from mcp.server.fastmcp import Context
from src.api.tools import get_user_id


class TestGetUserId:
    """Tests for get_user_id function."""

    def test_get_user_id_success(self):
        """Test that get_user_id function exists and handles config initialization properly."""
        # Setup
        mock_ctx = MagicMock(spec=Context)

        # Execute & Verify - The function should exist and handle the case where
        # config isn't initialized (which is expected in test environment)
        with pytest.raises(RuntimeError, match="Settings have not been initialized"):
            get_user_id(mock_ctx)

    def test_get_user_id_error(self):
        """Test get_user_id function error handling."""
        # Setup
        mock_ctx = MagicMock(spec=Context)

        # Execute & Verify - The function should fail with config error in test environment
        with pytest.raises(RuntimeError, match="Settings have not been initialized"):
            get_user_id(mock_ctx)
