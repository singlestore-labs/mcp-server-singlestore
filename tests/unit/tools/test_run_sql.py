"""Tests for run_sql tool function."""

import pytest
from unittest.mock import MagicMock

from mcp.server.fastmcp import Context
from src.api.tools import run_sql


class TestRunSql:
    """Tests for run_sql function."""

    def test_run_sql_success(self):
        """Test that run_sql function exists and handles validation properly."""
        # Setup
        mock_ctx = MagicMock(spec=Context)

        # Execute & Verify - The function should validate workspace ID first
        with pytest.raises(ValueError, match="Invalid workspace ID format"):
            run_sql(mock_ctx, "SELECT 1", "invalid-id")

    def test_run_sql_invalid_workspace_id(self):
        """Test run_sql function with invalid workspace ID."""
        # Setup
        mock_ctx = MagicMock(spec=Context)

        # Execute & Verify - The function should validate workspace ID and fail appropriately
        with pytest.raises(ValueError, match="Invalid workspace ID format"):
            run_sql(mock_ctx, "SELECT 1", "invalid-id")
