"""Unit tests for the get_organizations function."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from mcp.server.fastmcp import Context
from src.api.tools.tools import get_organizations


class TestGetOrganizations:
    """Test cases for the get_organizations function."""

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
        settings.is_remote = True
        return settings

    @pytest.fixture
    def sample_organizations(self):
        """Sample organizations data for testing."""
        return [
            {"orgID": "org-123", "name": "Test Organization"},
            {"orgID": "org-456", "name": "Another Org"},
            {"orgID": "org-789", "name": "Third Organization"},
        ]

    @pytest.fixture
    def single_organization(self):
        """Single organization data for testing."""
        return [
            {"orgID": "org-123", "name": "Single Organization"},
        ]

    @patch("src.api.tools.tools.config")
    @patch("src.api.tools.tools.query_graphql_organizations")
    @patch("src.api.tools.tools.logger")
    @pytest.mark.asyncio
    async def test_get_organizations_success_multiple_orgs(
        self,
        mock_logger,
        mock_query_graphql,
        mock_config,
        mock_context,
        mock_settings,
        sample_organizations,
    ):
        """Test successful retrieval of multiple organizations."""
        # Arrange
        mock_config.get_settings.return_value = mock_settings
        mock_config.get_user_id.return_value = "user-123"
        mock_query_graphql.return_value = sample_organizations

        # Act
        result = await get_organizations(mock_context)
        result = result

        # Assert
        assert result["status"] == "success"
        assert "Available SingleStore Organizations:" in result["message"]
        assert "Test Organization (ID: org-123)" in result["message"]
        assert "Another Org (ID: org-456)" in result["message"]
        assert "Third Organization (ID: org-789)" in result["message"]
        assert "set_organization" in result["message"]

        # Verify data structure
        assert result["data"]["organizations"] == sample_organizations
        assert result["data"]["count"] == 3
        assert (
            result["data"]["instructions"]
            == "Use set_organization tool to select an organization"
        )

        # Verify metadata
        metadata = result["metadata"]
        assert metadata["total_organizations"] == 3
        assert metadata["user_id"] == "user-123"
        assert "timestamp" in metadata

        # Verify analytics tracking was called
        mock_settings.analytics_manager.track_event.assert_called_once_with(
            "user-123", "tool_calling", {"name": "get_organizations"}
        )

        # Verify GraphQL query was called
        mock_query_graphql.assert_called_once()

    @patch("src.api.tools.tools.config")
    @patch("src.api.tools.tools.query_graphql_organizations")
    @patch("src.api.tools.tools.logger")
    @pytest.mark.asyncio
    async def test_get_organizations_success_single_org(
        self,
        mock_logger,
        mock_query_graphql,
        mock_config,
        mock_context,
        mock_settings,
        single_organization,
    ):
        """Test successful retrieval of a single organization."""
        # Arrange
        mock_config.get_settings.return_value = mock_settings
        mock_config.get_user_id.return_value = "user-456"
        mock_query_graphql.return_value = single_organization

        # Act
        result = await get_organizations(mock_context)
        result = result

        # Assert
        assert result["status"] == "success"
        assert "Available SingleStore Organizations:" in result["message"]
        assert "Single Organization (ID: org-123)" in result["message"]
        assert result["data"]["count"] == 1
        assert result["data"]["organizations"] == single_organization

        # Verify metadata reflects single organization
        assert result["metadata"]["total_organizations"] == 1

    @patch("src.api.tools.tools.config")
    @patch("src.api.tools.tools.query_graphql_organizations")
    @patch("src.api.tools.tools.logger")
    @pytest.mark.asyncio
    async def test_get_organizations_no_organizations_available(
        self,
        mock_logger,
        mock_query_graphql,
        mock_config,
        mock_context,
        mock_settings,
    ):
        """Test handling when no organizations are available."""
        # Arrange
        mock_config.get_settings.return_value = mock_settings
        mock_config.get_user_id.return_value = "user-789"
        mock_query_graphql.return_value = []  # Empty list

        # Act
        result = await get_organizations(mock_context)
        result = result

        # Assert
        assert result["status"] == "error"
        assert "No organizations available" in result["message"]
        assert "check your access permissions" in result["message"]

        # Verify analytics tracking was still called
        mock_settings.analytics_manager.track_event.assert_called_once_with(
            "user-789", "tool_calling", {"name": "get_organizations"}
        )

    @patch("src.api.tools.tools.config")
    @patch("src.api.tools.tools.query_graphql_organizations")
    @patch("src.api.tools.tools.logger")
    @pytest.mark.asyncio
    async def test_get_organizations_graphql_exception(
        self,
        mock_logger,
        mock_query_graphql,
        mock_config,
        mock_context,
        mock_settings,
    ):
        """Test error handling when GraphQL query fails."""
        # Arrange
        mock_config.get_settings.return_value = mock_settings
        mock_config.get_user_id.return_value = "user-error"
        mock_query_graphql.side_effect = Exception("GraphQL connection failed")

        # Act
        result = await get_organizations(mock_context)
        result = result

        # Assert
        assert result["status"] == "error"
        assert "Failed to retrieve organizations" in result["message"]
        assert "GraphQL connection failed" in result["message"]
        assert result["error_code"] == "ORGANIZATION_QUERY_FAILED"
        assert result["error_details"]["exception_type"] == "Exception"

        # Verify analytics tracking was still called
        mock_settings.analytics_manager.track_event.assert_called_once_with(
            "user-error", "tool_calling", {"name": "get_organizations"}
        )

    @patch("src.api.tools.tools.config")
    @patch("src.api.tools.tools.query_graphql_organizations")
    @patch("src.api.tools.tools.logger")
    @pytest.mark.asyncio
    async def test_get_organizations_validates_message_format(
        self,
        mock_logger,
        mock_query_graphql,
        mock_config,
        mock_context,
        mock_settings,
        sample_organizations,
    ):
        """Test that the response message includes proper formatting and instructions."""
        # Arrange
        mock_config.get_settings.return_value = mock_settings
        mock_config.get_user_id.return_value = "user-format"
        mock_query_graphql.return_value = sample_organizations

        # Act
        result = await get_organizations(mock_context)
        result = result

        # Assert message formatting
        message = result["message"]
        assert "📋 **Available SingleStore Organizations:**" in message
        assert "✅ To select an organization" in message
        assert "set_organization" in message
        assert "**Example:**" in message
        assert '`set_organization("your-org-name")`' in message
        assert '`set_organization("org-id-12345")`' in message
        assert "Once you select an organization" in message

        # Verify each organization is listed correctly
        for org in sample_organizations:
            expected_line = f"- {org['name']} (ID: {org['orgID']})"
            assert expected_line in message

    @patch("src.api.tools.tools.config")
    @patch("src.api.tools.tools.query_graphql_organizations")
    @patch("src.api.tools.tools.logger")
    @pytest.mark.asyncio
    async def test_get_organizations_validates_metadata_structure(
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
        mock_config.get_user_id.return_value = "user-metadata"
        mock_query_graphql.return_value = sample_organizations

        # Act
        result = await get_organizations(mock_context)
        result = result

        # Assert metadata structure
        assert "metadata" in result
        metadata = result["metadata"]
        assert "total_organizations" in metadata
        assert "timestamp" in metadata
        assert "user_id" in metadata

        # Verify expected values
        assert metadata["user_id"] == "user-metadata"
        assert metadata["total_organizations"] == len(sample_organizations)
        assert metadata["timestamp"]  # Just verify it exists

        # Verify timestamp is ISO format (basic validation)
        timestamp_str = metadata["timestamp"]
        try:
            datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except ValueError:
            pytest.fail(f"Timestamp '{timestamp_str}' is not in valid ISO format")
