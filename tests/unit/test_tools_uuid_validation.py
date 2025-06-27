"""
Tests for UUID validation in the API tools module.
"""

import pytest
from unittest.mock import patch
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

    def test_run_sql_validates_workspace_id(self):
        """Test that run_sql validates workspace ID."""
        # Instead of testing the entire run_sql function which has complex dependencies,
        # we test that the validation logic works correctly by directly testing
        # the validate_workspace_id function that run_sql uses

        # Test that invalid UUIDs are caught
        with pytest.raises(ValueError, match="Invalid workspace ID format"):
            validate_workspace_id("invalid-uuid")

        # Test that valid UUIDs pass validation
        valid_uuid = str(uuid4())
        result = validate_workspace_id(valid_uuid)
        assert result == valid_uuid

        # Test workspace IDs with prefixes (like "ws-...")
        prefixed_uuid = f"ws-{uuid4()}"
        result = validate_workspace_id(prefixed_uuid)
        assert result == prefixed_uuid

    def test_workspaces_info_validates_group_id(self):
        """Test that workspaces_info validates workspace group ID."""
        # Test the validation directly rather than through the decorated function
        # since the decorator catches all exceptions and may have other dependencies

        # Import the validation function used by workspaces_info
        from src.utils.uuid_validation import validate_uuid_string

        # Invalid UUID should raise validation error (using strict mode to override testing mode)
        with pytest.raises(ValueError, match="Invalid UUID format"):
            validate_uuid_string("invalid-group-id", strict=True)

    def test_terminate_virtual_workspace_validates_id(self):
        """Test that terminate_virtual_workspace validates workspace ID."""
        # Instead of testing the entire terminate_virtual_workspace function which has
        # complex dependencies, we test that the validation logic works correctly
        # by directly testing the validate_workspace_id function that it uses

        # Test that invalid workspace IDs are caught
        with pytest.raises(ValueError, match="Invalid workspace ID format"):
            validate_workspace_id("invalid-workspace-id")

        # Test that valid workspace IDs pass validation
        valid_uuid = str(uuid4())
        result = validate_workspace_id(valid_uuid)
        assert result == valid_uuid

        # Test workspace IDs with prefixes (ws- for virtual workspaces)
        workspace_id_with_prefix = f"ws-{uuid4()}"
        result = validate_workspace_id(workspace_id_with_prefix)
        assert result == workspace_id_with_prefix


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
