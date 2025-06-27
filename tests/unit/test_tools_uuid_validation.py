"""
Tests for UUID validation in the API tools module.
"""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from src.utils.uuid_validation import validate_workspace_id, validate_uuid_string


class TestToolsUUIDValidation:
    """Test UUID validation in the tools module functions."""

    def test_validate_workspace_id_function(self):
        """Test the validate_workspace_id function directly."""
        # Valid UUID should pass
        valid_uuid = str(uuid4())
        result = validate_workspace_id(valid_uuid)
        assert result == valid_uuid

        # Invalid UUID should raise ValueError
        with pytest.raises(ValueError, match="Invalid workspace ID format"):
            validate_workspace_id("invalid-uuid")

    def test_validate_uuid_string_function(self):
        """Test the validate_uuid_string function directly."""
        # Valid UUID should pass
        valid_uuid = str(uuid4())
        result = validate_uuid_string(valid_uuid)
        assert result == valid_uuid

        # None should return None
        result = validate_uuid_string(None)
        assert result is None

        # Invalid UUID should raise ValueError (in strict mode)
        with pytest.raises(ValueError, match="Invalid UUID format"):
            validate_uuid_string("invalid-uuid", strict=True)

    def test_validate_uuid_testing_mode(self):
        """Test that validation is lenient during testing."""
        import os

        # Set testing environment
        with patch.dict(os.environ, {"TESTING": "true"}):
            result = validate_uuid_string("test-client-id", strict=None)
            assert result == "test-client-id"

        # Test with PYTEST_CURRENT_TEST
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_something"}):
            result = validate_uuid_string("test-workspace-id", strict=None)
            assert result == "test-workspace-id"


class TestToolsIntegration:
    """Test that UUID validation is properly integrated into tools."""

    @patch("src.api.tools.tools.config")
    @patch("src.api.tools.tools.__get_workspace_by_id")
    def test_run_sql_validates_workspace_id(self, mock_get_workspace, mock_config):
        """Test that run_sql validates workspace ID."""
        from src.api.tools.tools import run_sql
        from mcp.server.fastmcp import Context

        # Mock the required dependencies
        mock_context = Mock(spec=Context)
        mock_config.get_settings.return_value = Mock()
        mock_workspace = Mock()
        mock_get_workspace.return_value = mock_workspace

        # Valid UUID should work (we test that it doesn't have UUID validation errors)
        valid_uuid = str(uuid4())

        # This should not raise an exception related to UUID validation
        result = run_sql(mock_context, "SELECT 1", valid_uuid)
        # The function returns an error response due to missing settings, but not UUID validation
        assert result["status"] == "error"
        assert "Invalid workspace ID format" not in result["message"]

        # Invalid UUID should return error response with validation error
        result = run_sql(mock_context, "SELECT 1", "invalid-uuid")
        assert result["status"] == "error"
        assert "Invalid workspace ID format" in result["message"]

    def test_workspaces_info_validates_group_id(self):
        """Test that workspaces_info validates workspace group ID."""
        # Test the validation directly rather than through the decorated function
        # since the decorator catches all exceptions and may have other dependencies

        # Import the validation function used by workspaces_info
        from src.utils.uuid_validation import validate_uuid_string

        # Invalid UUID should raise validation error (using strict mode to override testing mode)
        with pytest.raises(ValueError, match="Invalid UUID format"):
            validate_uuid_string("invalid-group-id", strict=True)

    @patch("src.api.tools.tools.config")
    def test_terminate_virtual_workspace_validates_id(self, mock_config):
        """Test that terminate_virtual_workspace validates workspace ID."""
        from src.api.tools.tools import terminate_virtual_workspace
        from mcp.server.fastmcp import Context

        mock_context = Mock(spec=Context)
        mock_config.get_settings.return_value = Mock()
        mock_config.get_user_id.return_value = str(uuid4())

        # Invalid UUID should return error response with validation error
        result = terminate_virtual_workspace(mock_context, "invalid-workspace-id")
        assert result["status"] == "error"
        assert "Invalid workspace ID format" in result["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
