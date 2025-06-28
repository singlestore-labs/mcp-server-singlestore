"""Unit tests for the set_organization function."""

import pytest
from unittest.mock import MagicMock, patch

from mcp.server.fastmcp import Context
from src.api.tools.tools import set_organization


class TestSetOrganization:
    """Test cases for the set_organization function."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock Context object."""
        context = MagicMock(spec=Context)
        return context

    @pytest.fixture
    def mock_settings(self):
        """Create a mock settings object."""
        settings = MagicMock()
        settings.analytics_manager = MagicMock()
        settings.analytics_manager.track_event = MagicMock()
        return settings

    @pytest.fixture
    def sample_organizations(self):
        """Sample organizations data for testing."""
        return [
            {"orgID": "org-123", "name": "Test Organization"},
            {"orgID": "org-456", "name": "Another Org"},
        ]

    @patch("src.api.tools.tools.config")
    @patch("src.api.tools.tools.query_graphql_organizations")
    @patch("src.api.tools.tools.logger")
    @pytest.mark.asyncio
    async def test_set_organization_success_with_org_id(
        self,
        mock_logger,
        mock_query_graphql,
        mock_config,
        mock_context,
        mock_settings,
        sample_organizations,
    ):
        """Test successful organization selection using organization ID."""
        # Arrange
        mock_config.get_settings.return_value = mock_settings
        mock_config.get_user_id.return_value = "user-123"
        mock_query_graphql.return_value = sample_organizations

        # Mock that settings doesn't have org_id initially
        mock_settings.org_id = None

        # Act
        result = await set_organization("org-123", mock_context)
        result = result

        # Assert
        assert result["status"] == "success"
        assert (
            "Successfully selected organization: Test Organization" in result["message"]
        )
        assert result["data"]["organization"]["orgID"] == "org-123"
        assert result["data"]["organization"]["name"] == "Test Organization"
        assert result["data"]["operation"] == "organization_set"

        # Verify analytics tracking was called
        mock_settings.analytics_manager.track_event.assert_called_once_with(
            "user-123", "tool_calling", {"name": "set_organization", "orgID": "org-123"}
        )

        # Verify organization ID was set in settings
        assert mock_settings.org_id == "org-123"

        # Verify GraphQL query was called
        mock_query_graphql.assert_called_once()

    @patch("src.api.tools.tools.config")
    @patch("src.api.tools.tools.query_graphql_organizations")
    @patch("src.api.tools.tools.logger")
    @pytest.mark.asyncio
    async def test_set_organization_success_with_org_name(
        self,
        mock_logger,
        mock_query_graphql,
        mock_config,
        mock_context,
        mock_settings,
        sample_organizations,
    ):
        """Test successful organization selection using organization name."""
        # Arrange
        mock_config.get_settings.return_value = mock_settings
        mock_config.get_user_id.return_value = "user-123"
        mock_query_graphql.return_value = sample_organizations

        # Mock that settings doesn't have org_id initially
        mock_settings.org_id = None

        # Act
        result = await set_organization("Test Organization", mock_context)
        result = result

        # Assert
        assert result["status"] == "success"
        assert (
            "Successfully selected organization: Test Organization" in result["message"]
        )
        assert result["data"]["organization"]["orgID"] == "org-123"
        assert result["data"]["organization"]["name"] == "Test Organization"
        assert result["data"]["operation"] == "organization_set"

        # Verify analytics tracking was called
        mock_settings.analytics_manager.track_event.assert_called_once_with(
            "user-123",
            "tool_calling",
            {"name": "set_organization", "orgID": "Test Organization"},
        )

        # Verify organization ID was set in settings
        assert mock_settings.org_id == "org-123"

        # Verify GraphQL query was called
        mock_query_graphql.assert_called_once()

    @patch("src.api.tools.tools.config")
    @patch("src.api.tools.tools.query_graphql_organizations")
    @patch("src.api.tools.tools.logger")
    @pytest.mark.asyncio
    async def test_set_organization_success_case_insensitive(
        self,
        mock_logger,
        mock_query_graphql,
        mock_config,
        mock_context,
        mock_settings,
        sample_organizations,
    ):
        """Test successful organization selection with case insensitive name matching."""
        # Arrange
        mock_config.get_settings.return_value = mock_settings
        mock_config.get_user_id.return_value = "user-123"
        mock_query_graphql.return_value = sample_organizations

        # Mock that settings doesn't have org_id initially
        mock_settings.org_id = None

        # Act - use lowercase version of organization name
        result = await set_organization("test organization", mock_context)
        result = result

        # Assert
        assert result["status"] == "success"
        assert (
            "Successfully selected organization: Test Organization" in result["message"]
        )
        assert result["data"]["organization"]["orgID"] == "org-123"
        assert result["data"]["organization"]["name"] == "Test Organization"
        assert result["data"]["operation"] == "organization_set"

        # Verify organization ID was set in settings
        assert mock_settings.org_id == "org-123"

    @patch("src.api.tools.tools.config")
    @patch("src.api.tools.tools.query_graphql_organizations")
    @patch("src.api.tools.tools.logger")
    @pytest.mark.asyncio
    async def test_set_organization_success_with_existing_org_id_attribute(
        self,
        mock_logger,
        mock_query_graphql,
        mock_config,
        mock_context,
        sample_organizations,
    ):
        """Test successful organization selection when settings already has org_id attribute."""
        # Arrange
        mock_settings = MagicMock()
        mock_settings.analytics_manager = MagicMock()
        mock_settings.analytics_manager.track_event = MagicMock()
        mock_settings.org_id = "old-org-id"  # Existing org_id

        mock_config.get_settings.return_value = mock_settings
        mock_config.get_user_id.return_value = "user-123"
        mock_query_graphql.return_value = sample_organizations

        # Act
        result = await set_organization("org-456", mock_context)
        result = result

        # Assert
        assert result["status"] == "success"
        assert "Successfully selected organization: Another Org" in result["message"]
        assert result["data"]["organization"]["orgID"] == "org-456"
        assert result["data"]["organization"]["name"] == "Another Org"
        assert result["data"]["operation"] == "organization_set"
        assert result["data"]["previous_org_id"] == "old-org-id"

        # Verify organization ID was updated in settings
        assert mock_settings.org_id == "org-456"

    @patch("src.api.tools.tools.config")
    @patch("src.api.tools.tools.query_graphql_organizations")
    @patch("src.api.tools.tools.logger")
    @pytest.mark.asyncio
    async def test_set_organization_validates_metadata_structure(
        self,
        mock_logger,
        mock_query_graphql,
        mock_config,
        mock_context,
        mock_settings,
        sample_organizations,
    ):
        """Test that the response includes proper metadata structure."""
        # Arrange
        mock_config.get_settings.return_value = mock_settings
        mock_config.get_user_id.return_value = "user-123"
        mock_query_graphql.return_value = sample_organizations
        mock_settings.org_id = None

        # Act
        result = await set_organization("org-123", mock_context)
        result = result

        # Assert metadata structure
        assert "metadata" in result
        metadata = result["metadata"]
        assert "user_id" in metadata
        assert "timestamp" in metadata
        assert "validation_method" in metadata

        # Verify expected values
        assert metadata["user_id"] == "user-123"
        assert metadata["validation_method"] == "graphql_query"
        assert metadata["timestamp"]  # Just verify it exists
