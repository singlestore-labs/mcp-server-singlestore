"""
Test suite for OAuth proxy integration with FastMCP.

This module tests the integration between the SingleStoreOAuthProxy
and FastMCP server, including:
- Proxy provider initialization
- Token verification with JWT
- FastMCP auth middleware integration
- Error handling in proxy scenarios
"""

import json
import jwt
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

import requests
from mcp.server.auth.provider import AccessToken
from fastmcp.server.auth.oauth_proxy import OAuthProxy

from src.auth.proxy_provider import SingleStoreOAuthProxy
from src.config.config import RemoteSettings


class TestSingleStoreOAuthProxy:
    """Test cases for SingleStoreOAuthProxy initialization and configuration."""

    @pytest.fixture
    def mock_openid_config(self):
        """Mock OpenID Connect configuration response."""
        return {
            "issuer": "https://authsvc.singlestore.com",
            "authorization_endpoint": "https://authsvc.singlestore.com/authorize",
            "token_endpoint": "https://authsvc.singlestore.com/token",
            "jwks_uri": "https://authsvc.singlestore.com/.well-known/jwks.json",
            "scopes_supported": ["openid", "profile", "email"],
        }

    @pytest.fixture
    def mock_requests_get(self, mock_openid_config):
        """Mock requests.get for OpenID configuration discovery."""
        with patch("src.auth.proxy_provider.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.json.return_value = mock_openid_config
            mock_get.return_value = mock_response
            yield mock_get

    def test_proxy_initialization_success(self, mock_requests_get):
        """Test successful OAuth proxy initialization with OpenID discovery."""
        proxy = SingleStoreOAuthProxy(
            issuer_url="https://authsvc.singlestore.com",
            client_id="test-client-id",
            client_secret="test-client-secret",
            base_url="http://localhost:8010",
            jwt_signing_key="test-jwt-key",
        )

        assert proxy.issuer_url == "https://authsvc.singlestore.com"
        assert proxy.client_id == "test-client-id"
        assert proxy.client_secret == "test-client-secret"
        assert proxy.base_url == "http://localhost:8010"
        assert proxy.jwt_signing_key == "test-jwt-key"

        # Should have fetched OpenID config
        mock_requests_get.assert_called_once()
        assert proxy._config is not None

        # Should have created verifier and provider
        assert proxy._verifier is not None
        assert proxy.provider is not None

    def test_proxy_initialization_discovery_failure(self):
        """Test proxy initialization when OpenID discovery fails."""
        with patch("src.auth.proxy_provider.requests.get") as mock_get:
            mock_get.side_effect = requests.RequestException("Connection failed")

            with pytest.raises(
                RuntimeError, match="Failed to fetch OpenID configuration"
            ):
                SingleStoreOAuthProxy(
                    issuer_url="https://invalid.example.com",
                    client_id="test-client-id",
                    jwt_signing_key="test-jwt-key",
                )

    def test_proxy_initialization_missing_endpoints(self, mock_requests_get):
        """Test proxy initialization with incomplete OpenID config."""
        # Mock incomplete config
        with patch("src.auth.proxy_provider.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.json.return_value = {
                "issuer": "https://authsvc.singlestore.com",
                # Missing authorization_endpoint and token_endpoint
            }
            mock_get.return_value = mock_response

            with pytest.raises(
                RuntimeError, match="Missing required fields in OpenID configuration"
            ):
                SingleStoreOAuthProxy(
                    issuer_url="https://authsvc.singlestore.com",
                    client_id="test-client-id",
                    jwt_signing_key="test-jwt-key",
                )

    def test_proxy_initialization_missing_jwt_key(self, mock_requests_get):
        """Test proxy initialization without JWT signing key."""
        with pytest.raises(RuntimeError, match="JWT signing key is not set"):
            SingleStoreOAuthProxy(
                issuer_url="https://authsvc.singlestore.com",
                client_id="test-client-id",
                jwt_signing_key=None,
            )

    def test_get_provider_returns_oauth_proxy(self, mock_requests_get):
        """Test that get_provider returns a properly configured OAuthProxy."""
        proxy = SingleStoreOAuthProxy(
            issuer_url="https://authsvc.singlestore.com",
            client_id="test-client-id",
            jwt_signing_key="test-jwt-key",
        )

        provider = proxy.get_provider()

        assert isinstance(provider, OAuthProxy)


class TestCustomJWTVerifier:
    """Test cases for the custom JWT token verifier."""

    @pytest.fixture
    def mock_jwks_client(self):
        """Mock PyJWKClient for JWT verification."""
        with patch("src.auth.proxy_provider.PyJWKClient") as mock_client_class:
            mock_client = Mock()
            mock_signing_key = Mock()
            mock_signing_key.key = "test-signing-key"
            mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
            mock_client_class.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def jwt_verifier(self, mock_jwks_client):
        """Create a JWT verifier instance for testing."""
        with patch("src.auth.proxy_provider.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.json.return_value = {
                "issuer": "https://authsvc.singlestore.com",
                "authorization_endpoint": "https://authsvc.singlestore.com/authorize",
                "token_endpoint": "https://authsvc.singlestore.com/token",
                "jwks_uri": "https://authsvc.singlestore.com/.well-known/jwks.json",
            }
            mock_get.return_value = mock_response

            proxy = SingleStoreOAuthProxy(
                issuer_url="https://authsvc.singlestore.com",
                client_id="test-client-id",
                jwt_signing_key="test-jwt-key",
            )

            return proxy._verifier

    @patch("src.auth.proxy_provider.jwt.decode")
    @pytest.mark.asyncio
    async def test_verify_token_success(
        self, mock_jwt_decode, jwt_verifier, mock_jwks_client
    ):
        """Test successful JWT token verification."""
        # Mock decoded token payload
        mock_jwt_decode.return_value = {
            "client_id": "test-client-id",
            "exp": int(datetime.now().timestamp()) + 3600,
            "aud": ["test-client-id"],
            "iss": "https://authsvc.singlestore.com",
            "sub": "user-123",
        }

        access_token = await jwt_verifier.verify_token("valid.jwt.token")

        assert access_token is not None
        assert isinstance(access_token, AccessToken)
        assert access_token.client_id == "test-client-id"
        assert access_token.scopes == ["openid"]
        assert access_token.resource == "test-client-id"

        # Should have called JWT decode with proper parameters
        mock_jwt_decode.assert_called_once()
        args, kwargs = mock_jwt_decode.call_args
        assert kwargs["audience"] == "test-client-id"
        assert kwargs["algorithms"] == ["ES512"]

    @patch("src.auth.proxy_provider.jwt.decode")
    @pytest.mark.asyncio
    async def test_verify_token_expired(
        self, mock_jwt_decode, jwt_verifier, mock_jwks_client
    ):
        """Test JWT token verification with expired token."""
        mock_jwt_decode.side_effect = jwt.ExpiredSignatureError("Token has expired")

        access_token = await jwt_verifier.verify_token("expired.jwt.token")

        assert access_token is None

    @patch("src.auth.proxy_provider.jwt.decode")
    @pytest.mark.asyncio
    async def test_verify_token_invalid_signature(
        self, mock_jwt_decode, jwt_verifier, mock_jwks_client
    ):
        """Test JWT token verification with invalid signature."""
        mock_jwt_decode.side_effect = jwt.InvalidSignatureError("Invalid signature")

        access_token = await jwt_verifier.verify_token("invalid.jwt.token")

        assert access_token is None

    @patch("src.auth.proxy_provider.jwt.decode")
    @pytest.mark.asyncio
    async def test_verify_token_malformed(
        self, mock_jwt_decode, jwt_verifier, mock_jwks_client
    ):
        """Test JWT token verification with malformed token."""
        mock_jwt_decode.side_effect = jwt.DecodeError("Invalid token format")

        access_token = await jwt_verifier.verify_token("malformed.token")

        assert access_token is None

    @pytest.mark.asyncio
    async def test_verify_token_jwks_error(self, jwt_verifier):
        """Test JWT token verification when JWKS retrieval fails."""
        with patch.object(jwt_verifier, "jwks_client") as mock_client:
            mock_client.get_signing_key_from_jwt.side_effect = Exception("JWKS error")

            # Should raise the JWKS error
            with pytest.raises(Exception, match="JWKS error"):
                await jwt_verifier.verify_token("test.jwt.token")


class TestOAuthProxyIntegration:
    """Test integration between OAuth proxy and MCP components."""

    @pytest.fixture
    def mock_storage(self):
        """Mock client storage for testing."""
        storage = AsyncMock()
        storage.get = AsyncMock(return_value=None)
        storage.set = AsyncMock()
        storage.delete = AsyncMock()
        return storage

    @pytest.fixture
    def oauth_proxy_with_storage(self, mock_storage):
        """Create OAuth proxy with mocked storage."""
        with patch("src.auth.proxy_provider.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.json.return_value = {
                "issuer": "https://authsvc.singlestore.com",
                "authorization_endpoint": "https://authsvc.singlestore.com/authorize",
                "token_endpoint": "https://authsvc.singlestore.com/token",
                "jwks_uri": "https://authsvc.singlestore.com/.well-known/jwks.json",
            }
            mock_get.return_value = mock_response

            proxy = SingleStoreOAuthProxy(
                issuer_url="https://authsvc.singlestore.com",
                client_id="test-client-id",
                jwt_signing_key="test-jwt-key",
                client_storage=mock_storage,
            )

            return proxy

    def test_proxy_with_encrypted_storage(self, mock_storage):
        """Test OAuth proxy with encrypted client storage."""
        with patch("src.auth.proxy_provider.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.json.return_value = {
                "issuer": "https://authsvc.singlestore.com",
                "authorization_endpoint": "https://authsvc.singlestore.com/authorize",
                "token_endpoint": "https://authsvc.singlestore.com/token",
                "jwks_uri": "https://authsvc.singlestore.com/.well-known/jwks.json",
            }
            mock_get.return_value = mock_response

            # Create proxy with encryption enabled (default)
            proxy = SingleStoreOAuthProxy(
                issuer_url="https://authsvc.singlestore.com",
                client_id="test-client-id",
                jwt_signing_key="test-jwt-key",
                client_storage=mock_storage,
                encrypt_db=True,
            )

            assert proxy.encrypt_db is True
            assert proxy.provider is not None

    def test_proxy_with_custom_scopes(self):
        """Test OAuth proxy with custom valid scopes."""
        with patch("src.auth.proxy_provider.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.json.return_value = {
                "issuer": "https://authsvc.singlestore.com",
                "authorization_endpoint": "https://authsvc.singlestore.com/authorize",
                "token_endpoint": "https://authsvc.singlestore.com/token",
                "jwks_uri": "https://authsvc.singlestore.com/.well-known/jwks.json",
            }
            mock_get.return_value = mock_response

            custom_scopes = ["openid", "profile", "email", "custom_scope"]
            proxy = SingleStoreOAuthProxy(
                issuer_url="https://authsvc.singlestore.com",
                client_id="test-client-id",
                jwt_signing_key="test-jwt-key",
                valid_scopes=custom_scopes,
            )

            assert proxy.valid_scopes == custom_scopes

    def test_proxy_with_custom_redirect_path(self):
        """Test OAuth proxy with custom redirect path."""
        with patch("src.auth.proxy_provider.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.json.return_value = {
                "issuer": "https://authsvc.singlestore.com",
                "authorization_endpoint": "https://authsvc.singlestore.com/authorize",
                "token_endpoint": "https://authsvc.singlestore.com/token",
                "jwks_uri": "https://authsvc.singlestore.com/.well-known/jwks.json",
            }
            mock_get.return_value = mock_response

            custom_redirect = "/custom/oauth/callback"
            proxy = SingleStoreOAuthProxy(
                issuer_url="https://authsvc.singlestore.com",
                client_id="test-client-id",
                jwt_signing_key="test-jwt-key",
                redirect_path=custom_redirect,
            )

            assert proxy.redirect_path == custom_redirect


class TestRemoteSettingsIntegration:
    """Test integration with RemoteSettings configuration."""

    @pytest.fixture
    def sample_remote_settings(self):
        """Create sample remote settings for testing."""
        return {
            "transport": "sse",
            "is_remote": True,
            "issuer_url": "https://authsvc.singlestore.com",
            "required_scopes": ["openid", "profile", "email"],
            "server_url": "http://localhost:8010",
            "client_id": "test-client-id-uuid",
            "callback_path": "/oauth/callback",
            "oauth_db_url": "mysql://test:test@localhost/oauth_test",
            "segment_write_key": "test-segment-key",
            "jwt_signing_key": "test-jwt-signing-key",
        }

    @patch("src.config.config.AnalyticsManager")
    @patch("src.config.config.SingleStoreKV")
    def test_remote_settings_creates_auth_provider(
        self, mock_kv, mock_analytics, sample_remote_settings
    ):
        """Test that RemoteSettings automatically creates auth provider."""
        mock_kv_instance = Mock()
        mock_kv.return_value = mock_kv_instance

        mock_analytics_instance = Mock()
        mock_analytics.return_value = mock_analytics_instance

        with patch("src.auth.proxy_provider.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.json.return_value = {
                "issuer": "https://authsvc.singlestore.com",
                "authorization_endpoint": "https://authsvc.singlestore.com/authorize",
                "token_endpoint": "https://authsvc.singlestore.com/token",
                "jwks_uri": "https://authsvc.singlestore.com/.well-known/jwks.json",
            }
            mock_get.return_value = mock_response

            settings = RemoteSettings(**sample_remote_settings)

            assert settings.auth_provider is not None
            assert isinstance(settings.auth_provider, OAuthProxy)
            assert settings.singlestore_kv == mock_kv_instance
            assert settings.analytics_manager == mock_analytics_instance

    @patch("src.config.config.AnalyticsManager")
    def test_remote_settings_without_oauth_db_url(
        self, mock_analytics, sample_remote_settings
    ):
        """Test RemoteSettings behavior without oauth_db_url."""
        mock_analytics_instance = Mock()
        mock_analytics.return_value = mock_analytics_instance

        # Remove oauth_db_url from settings
        settings_without_db = sample_remote_settings.copy()
        settings_without_db["oauth_db_url"] = None

        with patch("src.auth.proxy_provider.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.json.return_value = {
                "issuer": "https://authsvc.singlestore.com",
                "authorization_endpoint": "https://authsvc.singlestore.com/authorize",
                "token_endpoint": "https://authsvc.singlestore.com/token",
                "jwks_uri": "https://authsvc.singlestore.com/.well-known/jwks.json",
            }
            mock_get.return_value = mock_response

            settings = RemoteSettings(**settings_without_db)

            assert settings.singlestore_kv is None
            assert settings.auth_provider is not None


class TestErrorScenarios:
    """Test various error scenarios in OAuth proxy operation."""

    def test_openid_discovery_timeout(self):
        """Test OpenID discovery with timeout."""
        with patch("src.auth.proxy_provider.requests.get") as mock_get:
            mock_get.side_effect = requests.Timeout("Request timeout")

            with pytest.raises(
                RuntimeError, match="Failed to fetch OpenID configuration"
            ):
                SingleStoreOAuthProxy(
                    issuer_url="https://slow.example.com",
                    client_id="test-client-id",
                    jwt_signing_key="test-jwt-key",
                )

    def test_openid_discovery_http_error(self):
        """Test OpenID discovery with HTTP error."""
        with patch("src.auth.proxy_provider.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = requests.HTTPError(
                "404 Not Found"
            )
            mock_get.return_value = mock_response

            with pytest.raises(
                RuntimeError, match="Failed to fetch OpenID configuration"
            ):
                SingleStoreOAuthProxy(
                    issuer_url="https://notfound.example.com",
                    client_id="test-client-id",
                    jwt_signing_key="test-jwt-key",
                )

    def test_invalid_json_in_openid_config(self):
        """Test OpenID discovery with invalid JSON response."""
        with patch("src.auth.proxy_provider.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_get.return_value = mock_response

            with pytest.raises(
                RuntimeError, match="Failed to fetch OpenID configuration"
            ):
                SingleStoreOAuthProxy(
                    issuer_url="https://badjson.example.com",
                    client_id="test-client-id",
                    jwt_signing_key="test-jwt-key",
                )

    def test_missing_issuer_in_openid_config(self):
        """Test OpenID config missing required issuer field."""
        with patch("src.auth.proxy_provider.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.json.return_value = {
                # Missing "issuer" field
                "authorization_endpoint": "https://authsvc.singlestore.com/authorize",
                "token_endpoint": "https://authsvc.singlestore.com/token",
                "jwks_uri": "https://authsvc.singlestore.com/.well-known/jwks.json",
            }
            mock_get.return_value = mock_response

            with pytest.raises(
                RuntimeError, match="Missing required fields in OpenID configuration"
            ):
                SingleStoreOAuthProxy(
                    issuer_url="https://authsvc.singlestore.com",
                    client_id="test-client-id",
                    jwt_signing_key="test-jwt-key",
                )

    def test_missing_jwks_uri_in_openid_config(self):
        """Test OpenID config missing JWKS URI."""
        with patch("src.auth.proxy_provider.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.json.return_value = {
                "issuer": "https://authsvc.singlestore.com",
                "authorization_endpoint": "https://authsvc.singlestore.com/authorize",
                "token_endpoint": "https://authsvc.singlestore.com/token",
                # Missing "jwks_uri" field
            }
            mock_get.return_value = mock_response

            with pytest.raises(
                RuntimeError, match="Missing required fields in OpenID configuration"
            ):
                SingleStoreOAuthProxy(
                    issuer_url="https://authsvc.singlestore.com",
                    client_id="test-client-id",
                    jwt_signing_key="test-jwt-key",
                )
