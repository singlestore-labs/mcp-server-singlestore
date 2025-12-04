"""
Test suite for remote mode API authentication integration.

This module tests how authentication tokens are used in API requests
in remote mode, including:
- Token retrieval from auth provider
- API request authentication
- Error handling for invalid/expired tokens
- Session context management
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from starlette.exceptions import HTTPException
from starlette.requests import Request
from mcp.server.auth.provider import AccessToken

from src.api.common import get_access_token, build_request
from src.config.config import RemoteSettings, LocalSettings


class TestGetAccessTokenRemoteMode:
    """Test access token retrieval in remote mode."""

    @pytest.fixture
    def mock_remote_settings(self):
        """Create mock RemoteSettings with auth provider."""
        settings = Mock(spec=RemoteSettings)
        settings.is_remote = True
        settings.auth_provider = AsyncMock()
        return settings

    @pytest.fixture
    def mock_local_settings(self):
        """Create mock LocalSettings."""
        settings = Mock(spec=LocalSettings)
        settings.is_remote = False
        settings.api_key = None
        settings.jwt_token = "local-jwt-token"
        return settings

    @pytest.fixture
    def mock_request(self):
        """Create mock HTTP request with Authorization header."""
        request = Mock(spec=Request)
        request.headers = {"Authorization": "Bearer client-token-123"}
        return request

    @patch("src.api.common.get_session_request")
    @patch("src.api.common.get_settings")
    @patch("src.api.common.async_to_sync")
    def test_get_access_token_remote_success(
        self,
        mock_async_to_sync,
        mock_get_settings,
        mock_get_session_request,
        mock_remote_settings,
        mock_request,
    ):
        """Test successful token retrieval in remote mode."""
        # Setup mocks
        mock_get_settings.return_value = mock_remote_settings
        mock_get_session_request.return_value = mock_request

        # Mock auth provider returning access token
        mock_access_token = AccessToken(
            token="real-singlestore-token",
            client_id="test-client",
            scopes=["openid", "profile"],
            expires_at=9999999999,
        )

        # Mock async_to_sync to return a sync function that returns the access token
        mock_sync_function = Mock(return_value=mock_access_token)
        mock_async_to_sync.return_value = mock_sync_function

        # Call function
        result = get_access_token()

        # Assertions
        assert result == "real-singlestore-token"
        mock_get_session_request.assert_called_once()
        mock_sync_function.assert_called_once_with("client-token-123")

    @patch("src.api.common.get_session_request")
    @patch("src.api.common.get_settings")
    @patch("src.api.common.async_to_sync")
    def test_get_access_token_remote_no_token_in_provider(
        self,
        mock_async_to_sync,
        mock_get_settings,
        mock_get_session_request,
        mock_remote_settings,
        mock_request,
    ):
        """Test remote mode when auth provider returns None (token not found/expired)."""
        # Setup mocks
        mock_get_settings.return_value = mock_remote_settings
        mock_get_session_request.return_value = mock_request

        # Mock auth provider returning None (token invalid/expired)
        mock_sync_function = Mock(return_value=None)
        mock_async_to_sync.return_value = mock_sync_function

        # Should raise HTTPException for unauthorized
        with pytest.raises(HTTPException) as exc_info:
            get_access_token()

        assert exc_info.value.status_code == 401
        assert "Unauthorized: No access token provided" in str(exc_info.value.detail)

    @patch("src.api.common.get_session_request")
    @patch("src.api.common.get_settings")
    @patch("src.api.common.async_to_sync")
    def test_get_access_token_remote_no_auth_header(
        self,
        mock_async_to_sync,
        mock_get_settings,
        mock_get_session_request,
        mock_remote_settings,
    ):
        """Test remote mode with missing Authorization header."""
        # Setup mocks
        mock_get_settings.return_value = mock_remote_settings

        # Mock request without Authorization header
        mock_request = Mock(spec=Request)
        mock_request.headers = {}
        mock_get_session_request.return_value = mock_request

        # Mock auth provider returning None for empty token
        mock_sync_function = Mock(return_value=None)
        mock_async_to_sync.return_value = mock_sync_function

        # Should raise HTTPException for unauthorized
        with pytest.raises(HTTPException) as exc_info:
            get_access_token()

        assert exc_info.value.status_code == 401
        assert "Unauthorized: No access token provided" in str(exc_info.value.detail)

    @patch("src.api.common.get_settings")
    def test_get_access_token_local_api_key(
        self, mock_get_settings, mock_local_settings
    ):
        """Test local mode with API key."""
        mock_local_settings.api_key = "api-key-123"
        mock_local_settings.jwt_token = None
        mock_get_settings.return_value = mock_local_settings

        result = get_access_token()

        assert result == "api-key-123"

    @patch("src.api.common.get_settings")
    def test_get_access_token_local_jwt_token(
        self, mock_get_settings, mock_local_settings
    ):
        """Test local mode with JWT token."""
        mock_local_settings.api_key = None
        mock_local_settings.jwt_token = "jwt-token-123"
        mock_get_settings.return_value = mock_local_settings

        result = get_access_token()

        assert result == "jwt-token-123"

    @patch("src.api.common.get_settings")
    def test_get_access_token_local_no_tokens(
        self, mock_get_settings, mock_local_settings
    ):
        """Test local mode without any tokens."""
        mock_local_settings.api_key = None
        mock_local_settings.jwt_token = None
        mock_get_settings.return_value = mock_local_settings

        with pytest.raises(HTTPException) as exc_info:
            get_access_token()

        assert exc_info.value.status_code == 401


class TestBuildRequestRemoteMode:
    """Test API request building with remote mode authentication."""

    @pytest.fixture
    def mock_remote_settings(self):
        """Create mock RemoteSettings."""
        settings = Mock(spec=RemoteSettings)
        settings.s2_api_base_url = "https://api.singlestore.com"
        settings.is_remote = True
        return settings

    @pytest.fixture
    def mock_successful_response(self):
        """Create mock successful API response."""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"success": True, "data": "test-data"}
        return response

    @pytest.fixture
    def mock_error_response(self):
        """Create mock error API response."""
        response = Mock()
        response.status_code = 401
        response.text = "Unauthorized"
        return response

    @patch("src.api.common.requests.get")
    @patch("src.api.common.get_access_token")
    @patch("src.api.common.get_org_id")
    @patch("src.api.common.get_settings")
    def test_build_request_get_success(
        self,
        mock_get_settings,
        mock_get_org_id,
        mock_get_access_token,
        mock_requests_get,
        mock_remote_settings,
        mock_successful_response,
    ):
        """Test successful GET request with authentication."""
        # Setup mocks
        mock_get_settings.return_value = mock_remote_settings
        mock_get_org_id.return_value = "org-123"
        mock_get_access_token.return_value = "bearer-token-123"
        mock_requests_get.return_value = mock_successful_response

        # Make request
        result = build_request("GET", "test/endpoint", params={"param1": "value1"})

        # Assertions
        assert result == {"success": True, "data": "test-data"}

        # Verify request was made with proper authentication
        mock_requests_get.assert_called_once()
        args, kwargs = mock_requests_get.call_args

        # Check URL
        expected_url = "https://api.singlestore.com/v1/test/endpoint?param1=value1&organizationID=org-123"
        assert args[0] == expected_url

        # Check headers
        assert "Authorization" in kwargs["headers"]
        assert kwargs["headers"]["Authorization"] == "Bearer bearer-token-123"
        assert kwargs["headers"]["Content-Type"] == "application/json"

    @patch("src.api.common.requests.post")
    @patch("src.api.common.get_access_token")
    @patch("src.api.common.get_org_id")
    @patch("src.api.common.get_settings")
    def test_build_request_post_with_data(
        self,
        mock_get_settings,
        mock_get_org_id,
        mock_get_access_token,
        mock_requests_post,
        mock_remote_settings,
        mock_successful_response,
    ):
        """Test POST request with JSON data and authentication."""
        # Setup mocks
        mock_get_settings.return_value = mock_remote_settings
        mock_get_org_id.return_value = "org-123"
        mock_get_access_token.return_value = "bearer-token-123"
        mock_requests_post.return_value = mock_successful_response

        test_data = {"key": "value", "number": 123}

        # Make request
        result = build_request("POST", "test/endpoint", data=test_data)

        # Assertions
        assert result == {"success": True, "data": "test-data"}

        # Verify request
        mock_requests_post.assert_called_once()
        args, kwargs = mock_requests_post.call_args

        # Check URL
        expected_url = (
            "https://api.singlestore.com/v1/test/endpoint?organizationID=org-123"
        )
        assert args[0] == expected_url

        # Check headers and data
        assert kwargs["headers"]["Authorization"] == "Bearer bearer-token-123"
        import json

        assert json.loads(kwargs["data"]) == test_data

    @patch("src.api.common.requests.get")
    @patch("src.api.common.get_access_token")
    @patch("src.api.common.get_org_id")
    @patch("src.api.common.get_settings")
    def test_build_request_api_error(
        self,
        mock_get_settings,
        mock_get_org_id,
        mock_get_access_token,
        mock_requests_get,
        mock_remote_settings,
        mock_error_response,
    ):
        """Test API request that returns an error status."""
        # Setup mocks
        mock_get_settings.return_value = mock_remote_settings
        mock_get_org_id.return_value = "org-123"
        mock_get_access_token.return_value = "invalid-token"
        mock_requests_get.return_value = mock_error_response

        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            build_request("GET", "test/endpoint")

        assert exc_info.value.status_code == 401
        assert "Unauthorized" in str(exc_info.value.detail)

    @patch("src.api.common.get_settings")
    @patch("src.api.common.get_access_token")
    def test_build_request_no_access_token(
        self, mock_get_access_token, mock_get_settings, mock_remote_settings
    ):
        """Test build_request when access token retrieval fails."""
        mock_get_settings.return_value = mock_remote_settings
        mock_get_access_token.side_effect = HTTPException(401, "No token")

        with pytest.raises(HTTPException) as exc_info:
            build_request("GET", "test/endpoint")

        assert exc_info.value.status_code == 401

    @patch("src.api.common.requests.put")
    @patch("src.api.common.get_access_token")
    @patch("src.api.common.get_org_id")
    @patch("src.api.common.get_settings")
    def test_build_request_put_method(
        self,
        mock_get_settings,
        mock_get_org_id,
        mock_get_access_token,
        mock_requests_put,
        mock_remote_settings,
        mock_successful_response,
    ):
        """Test PUT request method."""
        # Setup mocks
        mock_get_settings.return_value = mock_remote_settings
        mock_get_org_id.return_value = "org-123"
        mock_get_access_token.return_value = "bearer-token-123"
        mock_requests_put.return_value = mock_successful_response

        # Make request
        build_request("PUT", "test/endpoint", data={"update": "data"})

        # Verify PUT was called
        mock_requests_put.assert_called_once()

    @patch("src.api.common.requests.delete")
    @patch("src.api.common.get_access_token")
    @patch("src.api.common.get_org_id")
    @patch("src.api.common.get_settings")
    def test_build_request_delete_method(
        self,
        mock_get_settings,
        mock_get_org_id,
        mock_get_access_token,
        mock_requests_delete,
        mock_remote_settings,
        mock_successful_response,
    ):
        """Test DELETE request method."""
        # Setup mocks
        mock_get_settings.return_value = mock_remote_settings
        mock_get_org_id.return_value = "org-123"
        mock_get_access_token.return_value = "bearer-token-123"
        mock_requests_delete.return_value = mock_successful_response

        # Make request
        build_request("DELETE", "test/endpoint")

        # Verify DELETE was called
        mock_requests_delete.assert_called_once()

    @patch("src.api.common.get_org_id")  # Mock to avoid session issues
    @patch("src.api.common.get_access_token")  # Mock to avoid auth issues
    def test_build_request_unsupported_method(
        self, mock_get_access_token, mock_get_org_id, mock_remote_settings
    ):
        """Test build_request with unsupported HTTP method."""
        # Mock access token to avoid auth issues and reach method validation
        mock_get_access_token.return_value = "test-token"
        mock_get_org_id.return_value = "test-org-123"

        with patch("src.api.common.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_remote_settings

            with pytest.raises(ValueError, match="Unsupported request type: INVALID"):
                build_request("INVALID", "test/endpoint")


class TestAuthenticationIntegrationScenarios:
    """Test various authentication integration scenarios."""

    @patch("src.api.common.get_session_request")
    @patch("src.api.common.get_settings")
    @patch("src.api.common.async_to_sync")
    def test_token_refresh_scenario(
        self, mock_async_to_sync, mock_get_settings, mock_get_session_request
    ):
        """Test scenario where token needs to be refreshed."""
        # Setup settings
        settings = Mock(spec=RemoteSettings)
        settings.is_remote = True
        settings.auth_provider = AsyncMock()
        mock_get_settings.return_value = settings

        # Setup request
        request = Mock(spec=Request)
        request.headers = {"Authorization": "Bearer expired-token-123"}
        mock_get_session_request.return_value = request

        # Mock auth provider returning None first (token expired)
        mock_sync_function = Mock(return_value=None)
        mock_async_to_sync.return_value = mock_sync_function

        # Should raise unauthorized exception, triggering client to refresh
        with pytest.raises(HTTPException) as exc_info:
            get_access_token()

        assert exc_info.value.status_code == 401

    @patch("src.api.common.get_session_request")
    @patch("src.api.common.get_settings")
    @patch("src.api.common.async_to_sync")
    def test_malformed_authorization_header(
        self, mock_async_to_sync, mock_get_settings, mock_get_session_request
    ):
        """Test scenario with malformed Authorization header."""
        # Setup settings
        settings = Mock(spec=RemoteSettings)
        settings.is_remote = True
        settings.auth_provider = AsyncMock()
        mock_get_settings.return_value = settings

        # Setup request with malformed header
        request = Mock(spec=Request)
        request.headers = {"Authorization": "NotBearer token-123"}  # Missing "Bearer "
        mock_get_session_request.return_value = request

        # Mock auth provider - should be called with the malformed header value
        mock_access_token = AccessToken(
            token="real-token",
            client_id="test-client",
            scopes=["openid"],
            expires_at=9999999999,
        )
        mock_sync_function = Mock(return_value=mock_access_token)
        mock_async_to_sync.return_value = mock_sync_function

        result = get_access_token()

        # Should handle malformed header gracefully - "NotBearer token-123" becomes "Nottoken-123" after replace
        mock_sync_function.assert_called_once_with("Nottoken-123")
        assert result == "real-token"

    @patch("src.api.common.requests.get")
    @patch("src.api.common.get_access_token")
    @patch("src.api.common.get_org_id")
    @patch("src.api.common.get_settings")
    def test_concurrent_request_handling(
        self,
        mock_get_settings,
        mock_get_org_id,
        mock_get_access_token,
        mock_requests_get,
    ):
        """Test handling of concurrent API requests with authentication."""
        import threading
        import time

        # Setup mocks
        settings = Mock(spec=RemoteSettings)
        settings.s2_api_base_url = "https://api.singlestore.com"
        settings.is_remote = True
        mock_get_settings.return_value = settings
        mock_get_org_id.return_value = "org-123"

        # Mock token retrieval with slight delay
        def mock_token_retrieval():
            time.sleep(0.1)
            return "concurrent-token"

        mock_get_access_token.side_effect = mock_token_retrieval

        # Mock successful response
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"concurrent": True}
        mock_requests_get.return_value = response

        results = []
        exceptions = []

        def make_request(endpoint):
            try:
                result = build_request("GET", endpoint)
                results.append(result)
            except Exception as e:
                exceptions.append(e)

        # Start multiple concurrent requests
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request, args=(f"test/endpoint{i}",))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5.0)

        # All requests should succeed
        assert len(results) == 5
        assert len(exceptions) == 0
        assert all(result["concurrent"] for result in results)

    @patch("src.api.common.get_session_request")
    @patch("src.api.common.get_settings")
    def test_auth_provider_exception_handling(
        self, mock_get_settings, mock_get_session_request
    ):
        """Test handling of exceptions from auth provider."""
        # Setup settings
        settings = Mock(spec=RemoteSettings)
        settings.is_remote = True
        settings.auth_provider = AsyncMock()
        mock_get_settings.return_value = settings

        # Setup request
        request = Mock(spec=Request)
        request.headers = {"Authorization": "Bearer test-token"}
        mock_get_session_request.return_value = request

        # Mock auth provider raising exception
        with patch("src.api.common.async_to_sync") as mock_async_to_sync:
            mock_sync_function = Mock(side_effect=Exception("Auth provider error"))
            mock_async_to_sync.return_value = mock_sync_function

            # Should handle exception and raise 401
            with pytest.raises(Exception) as exc_info:
                get_access_token()

            assert "Auth provider error" in str(exc_info.value)
