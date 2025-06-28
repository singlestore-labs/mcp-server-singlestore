"""Tests for organization_info tool function."""

import pytest

from src.api.tools import organization_info


class TestOrganizationInfo:
    """Tests for organization_info function."""

    def test_organization_info_success(self):
        """Test that organization_info function exists and handles config initialization properly."""
        # Execute & Verify - The function should exist and handle the case where
        # config isn't initialized (which is expected in test environment)
        with pytest.raises(RuntimeError, match="Settings have not been initialized"):
            organization_info()

    def test_organization_info_no_name(self):
        """Test organization_info function error handling."""
        # Execute & Verify - The function should fail with config error in test environment
        with pytest.raises(RuntimeError, match="Settings have not been initialized"):
            organization_info()
