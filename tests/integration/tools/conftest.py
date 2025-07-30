"""Common configuration and fixtures for integration tests."""

import os
import pytest
from unittest.mock import MagicMock, AsyncMock
from src.config.config import LocalSettings, _settings_ctx, _user_id_ctx
from src.analytics.manager import AnalyticsManager


@pytest.fixture(scope="module", autouse=True)
def mock_context():
    """Create a mock Context object for testing async tools."""
    context = AsyncMock()
    context.info = AsyncMock()
    context.error = AsyncMock()
    context.warning = AsyncMock()
    return context


@pytest.fixture(scope="module", autouse=True)
def api_key_settings():
    """Create LocalSettings configured for API key authentication."""
    api_key = os.getenv("MCP_API_KEY")
    if not api_key:
        pytest.skip(
            "MCP_API_KEY environment variable is required for integration tests"
        )

    # Create settings with API key configuration
    settings = LocalSettings(
        api_key=api_key,
        transport="stdio",
        is_remote=False,
        s2_api_base_url="https://api.singlestore.com",
        graphql_public_endpoint="https://backend.singlestore.com/public",
    )

    # Mock analytics manager to avoid tracking in tests
    settings.analytics_manager = MagicMock(spec=AnalyticsManager)
    settings.analytics_manager.track_event = MagicMock()

    return settings


@pytest.fixture
def mock_api_key_settings():
    """Create LocalSettings configured for API key authentication with mock data."""
    # Create settings with mock API key configuration
    settings = LocalSettings(
        api_key="mock_api_key_12345",
        transport="stdio",
        is_remote=False,
        s2_api_base_url="https://api.singlestore.com",
        graphql_public_endpoint="https://backend.singlestore.com/public",
    )

    # Mock analytics manager to avoid tracking in tests
    settings.analytics_manager = MagicMock(spec=AnalyticsManager)
    settings.analytics_manager.track_event = MagicMock()

    return settings


@pytest.fixture(scope="module", autouse=True)
def mock_user_id():
    """Mock user ID for testing."""
    return "test-user-12345"


@pytest.fixture(scope="module", autouse=True)
def setup_integration_test_environment(request, api_key_settings, mock_user_id):
    _settings_ctx.set(api_key_settings)
    _user_id_ctx.set(mock_user_id)
    try:
        yield
    finally:
        _settings_ctx.set(None)
        _user_id_ctx.set(None)


@pytest.fixture
def setup_mock_integration_test_environment(mock_api_key_settings, mock_user_id):
    """Set up the test environment with mock settings and user ID for testing without real API key."""
    # Set the settings in the context variable
    _settings_ctx.set(mock_api_key_settings)
    _user_id_ctx.set(mock_user_id)

    try:
        yield
    finally:
        # Reset the context variables after the test
        _settings_ctx.set(None)
        _user_id_ctx.set(None)
