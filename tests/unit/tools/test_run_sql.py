"""Tests for run_sql tool function."""

import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4

from mcp.server.fastmcp import Context
from src.api.tools.tools import run_sql


class TestRunSql:
    """Tests for run_sql function."""

    def setup_method(self):
        """Set up common test fixtures before each test method."""
        self.workspace_id = str(uuid4())
        self.sql_query = "SELECT * FROM users LIMIT 10"
        self.database = "test_db"

        # Mock context
        self.mock_ctx = MagicMock(spec=Context)
        self.mock_ctx.info = MagicMock()

        # Mock return values
        self.mock_user_id = "user-123"
        self.mock_access_token = "mock_token"

        # Mock settings
        self.mock_settings = MagicMock()
        self.mock_analytics = MagicMock()
        self.mock_settings.analytics_manager = self.mock_analytics

    @patch("src.api.tools.tools.__execute_sql_unified")
    @patch("src.api.tools.tools.__get_workspace_by_id")
    @patch("src.api.tools.tools.__get_user_id")
    @patch("src.api.tools.tools.get_access_token")
    @patch("src.api.tools.tools.validate_workspace_id")
    @patch("src.config.config.get_settings")
    def test_run_sql_success(
        self,
        mock_get_settings,
        mock_validate_workspace_id,
        mock_get_access_token,
        mock_get_user_id,
        mock_get_workspace,
        mock_execute_sql,
    ):
        """Test successful SQL execution."""
        # Setup mocks
        mock_validate_workspace_id.return_value = self.workspace_id
        mock_get_access_token.return_value = self.mock_access_token
        mock_get_user_id.return_value = self.mock_user_id
        mock_get_settings.return_value = self.mock_settings

        # Mock workspace target
        mock_target = MagicMock()
        mock_target.is_shared = False
        mock_target.name = "test-workspace"
        mock_target.database_name = None
        mock_get_workspace.return_value = mock_target

        # Mock SQL execution result
        mock_sql_result = {
            "results": [
                {"id": 1, "name": "John"},
                {"id": 2, "name": "Jane"},
            ],
            "status": "Success",
        }
        mock_execute_sql.return_value = mock_sql_result

        # Execute
        result = run_sql(
            self.mock_ctx, self.sql_query, self.workspace_id, self.database
        )

        # Verify
        assert result["status"] == "success"
        assert result["message"] == "Query executed successfully. 2 rows returned."
        assert result["data"]["results"] == mock_sql_result["results"]
        assert result["data"]["row_count"] == 2
        assert result["data"]["workspace_id"] == self.workspace_id
        assert result["data"]["workspace_name"] == "test-workspace"
        assert result["data"]["workspace_type"] == "dedicated"
        assert result["data"]["database"] == self.database

        # Verify function calls
        mock_validate_workspace_id.assert_called_once_with(self.workspace_id)
        mock_get_workspace.assert_called_once_with(self.workspace_id)
        mock_execute_sql.assert_called_once()

    @patch("src.api.tools.tools.validate_workspace_id")
    def test_run_sql_invalid_workspace_id(self, mock_validate_workspace_id):
        """Test run_sql with invalid workspace ID."""
        mock_validate_workspace_id.side_effect = ValueError(
            "Invalid workspace ID format"
        )

        # Execute & Verify
        with pytest.raises(ValueError, match="Invalid workspace ID format"):
            run_sql(self.mock_ctx, "SELECT 1", "invalid-id")
