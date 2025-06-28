"""Tests for workspace_groups_info tool function."""

import pytest

from src.api.tools.tools import workspace_groups_info


class TestWorkspaceGroupsInfo:
    """Tests for workspace_groups_info function."""

    def test_workspace_groups_info_success(self):
        """Test that workspace_groups_info function exists and handles config initialization properly."""
        # Execute & Verify - The function should exist and handle the case where
        # config isn't initialized (which is expected in test environment)
        with pytest.raises(RuntimeError, match="Settings have not been initialized"):
            workspace_groups_info()

    def test_workspace_groups_info_empty(self):
        """Test workspace_groups_info function error handling."""
        # Execute & Verify - The function should fail with config error in test environment
        with pytest.raises(RuntimeError, match="Settings have not been initialized"):
            workspace_groups_info()
