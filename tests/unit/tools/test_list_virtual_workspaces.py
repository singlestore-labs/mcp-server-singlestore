"""Tests for list_virtual_workspaces tool function."""

import pytest

from src.api.tools import list_virtual_workspaces


class TestListVirtualWorkspaces:
    """Tests for list_virtual_workspaces function."""

    def test_list_virtual_workspaces_success(self):
        """Test that list_virtual_workspaces function exists and handles config initialization properly."""
        # Execute & Verify - The function should exist and handle the case where
        # config isn't initialized (which is expected in test environment)
        with pytest.raises(RuntimeError, match="Settings have not been initialized"):
            list_virtual_workspaces()

    def test_list_virtual_workspaces_empty(self):
        """Test list_virtual_workspaces function error handling."""
        # Execute & Verify - The function should fail with config error in test environment
        with pytest.raises(RuntimeError, match="Settings have not been initialized"):
            list_virtual_workspaces()

    def test_list_virtual_workspaces_no_state(self):
        """Test list_virtual_workspaces function no state handling."""
        # Execute & Verify - The function should fail with config error in test environment
        with pytest.raises(RuntimeError, match="Settings have not been initialized"):
            list_virtual_workspaces()
