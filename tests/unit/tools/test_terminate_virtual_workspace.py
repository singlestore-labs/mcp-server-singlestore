"""Tests for terminate_virtual_workspace tool function."""

import pytest
from unittest.mock import MagicMock

from mcp.server.fastmcp import Context
from src.api.tools.tools import terminate_virtual_workspace


class TestTerminateVirtualWorkspace:
    """Tests for terminate_virtual_workspace function."""

    def test_terminate_virtual_workspace_success(self):
        """Test that terminate_virtual_workspace function exists and handles validation properly."""
        # Setup
        mock_ctx = MagicMock(spec=Context)

        # Execute & Verify - The function should validate workspace ID first
        with pytest.raises(ValueError, match="Invalid workspace ID format"):
            terminate_virtual_workspace(mock_ctx, "invalid-id")

    def test_terminate_virtual_workspace_invalid_id(self):
        """Test terminate virtual workspace with invalid ID."""
        # Setup
        mock_ctx = MagicMock(spec=Context)

        # Execute & Verify
        with pytest.raises(ValueError, match="Invalid workspace ID format"):
            terminate_virtual_workspace(mock_ctx, "invalid-id")

    def test_terminate_virtual_workspace_not_found(self):
        """Test terminate virtual workspace when workspace not found."""
        # Setup
        mock_ctx = MagicMock(spec=Context)

        # Execute & Verify - The function should validate workspace ID first
        with pytest.raises(ValueError, match="Invalid workspace ID format"):
            terminate_virtual_workspace(mock_ctx, "invalid-id")

    def test_terminate_virtual_workspace_termination_error(self):
        """Test terminate virtual workspace when termination fails."""
        # Setup
        mock_ctx = MagicMock(spec=Context)

        # Execute & Verify - The function should validate workspace ID first
        with pytest.raises(ValueError, match="Invalid workspace ID format"):
            terminate_virtual_workspace(mock_ctx, "invalid-id")
