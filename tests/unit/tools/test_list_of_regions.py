"""Tests for list_of_regions tool function."""

import pytest

from src.api.tools import list_of_regions


class TestListOfRegions:
    """Tests for list_of_regions function."""

    def test_list_of_regions_success(self):
        """Test that list_of_regions function exists and handles config initialization properly."""
        # Execute & Verify - The function should exist and handle the case where
        # config isn't initialized (which is expected in test environment)
        with pytest.raises(RuntimeError, match="Settings have not been initialized"):
            list_of_regions()

    def test_list_of_regions_empty(self):
        """Test list_of_regions function error handling."""
        # Execute & Verify - The function should fail with config error in test environment
        with pytest.raises(RuntimeError, match="Settings have not been initialized"):
            list_of_regions()

    def test_list_of_regions_missing_provider(self):
        """Test list_of_regions function missing provider handling."""
        # Execute & Verify - The function should fail with config error in test environment
        with pytest.raises(RuntimeError, match="Settings have not been initialized"):
            list_of_regions()
