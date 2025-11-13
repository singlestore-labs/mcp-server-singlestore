"""Unit tests for SingleStoreOAuthProxy class."""

import pytest
import json
from unittest.mock import Mock, patch
from fastmcp.server.auth.oauth_proxy import OAuthProxy
from mcp.server.auth.provider import AccessToken
import jwt

from src.auth.proxy_provider import SingleStoreOAuthProxy


class TestSingleStoreOAuthProxy:
    """Test cases for SingleStoreOAuthProxy class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.test_issuer_url = "https://authsvc.singlestore.com/"
        self.test_client_id = "b7dbf19e-d140-4334-bae4-e8cd03614485"
        self.test_client_secret = "test-secret"
        self.test_base_url = "http://localhost:8010/"
        self.test_redirect_path = "/callback"
        self.test_valid_scopes = ["openid", "profile"]
        self.test_jwt_signing_key = "test-jwt-key"

        # Mock OpenID configuration response
        self.mock_openid_config = {
            "issuer": "https://authsvc.singlestore.com",
            "authorization_endpoint": "https://authsvc.singlestore.com/authorize",
            "token_endpoint": "https://authsvc.singlestore.com/token",
            "jwks_uri": "https://authsvc.singlestore.com/.well-known/jwks.json",
            "response_types_supported": ["code"],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["ES512"],
        }

    @patch("requests.get")
    @patch("src.auth.proxy_provider.PyJWKClient")
    @patch("src.auth.proxy_provider.OAuthProxy")
    def test_init_success(self, mock_oauth_proxy, mock_jwks_client, mock_requests_get):
        """Test successful initialization of SingleStoreOAuthProxy."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = self.mock_openid_config
        mock_requests_get.return_value = mock_response

        mock_jwks_client_instance = Mock()
        mock_jwks_client.return_value = mock_jwks_client_instance

        mock_oauth_proxy_instance = Mock(spec=OAuthProxy)
        mock_oauth_proxy.return_value = mock_oauth_proxy_instance

        # Act
        proxy = SingleStoreOAuthProxy(
            issuer_url=self.test_issuer_url,
            client_id=self.test_client_id,
            client_secret=self.test_client_secret,
            base_url=self.test_base_url,
            redirect_path=self.test_redirect_path,
            valid_scopes=self.test_valid_scopes,
            jwt_signing_key=self.test_jwt_signing_key,
        )

        # Assert
        assert proxy.issuer_url == self.test_issuer_url
        assert proxy.client_id == self.test_client_id
        assert proxy.client_secret == self.test_client_secret
        assert proxy.base_url == self.test_base_url
        assert proxy.redirect_path == self.test_redirect_path
        assert proxy.valid_scopes == self.test_valid_scopes
        assert proxy.jwt_signing_key == self.test_jwt_signing_key

        # Verify OpenID config was fetched
        expected_config_url = (
            "https://authsvc.singlestore.com/.well-known/openid-configuration"
        )
        mock_requests_get.assert_called_once_with(expected_config_url, timeout=10.0)

        # Verify JWKS client was created
        mock_jwks_client.assert_called_once_with(self.mock_openid_config["jwks_uri"])

        # Verify OAuth proxy was created with correct parameters
        mock_oauth_proxy.assert_called_once()
        call_kwargs = mock_oauth_proxy.call_args[1]
        assert (
            call_kwargs["upstream_authorization_endpoint"]
            == self.mock_openid_config["authorization_endpoint"]
        )
        assert (
            call_kwargs["upstream_token_endpoint"]
            == self.mock_openid_config["token_endpoint"]
        )
        assert call_kwargs["upstream_client_id"] == self.test_client_id
        assert call_kwargs["upstream_client_secret"] == self.test_client_secret
        assert call_kwargs["base_url"] == self.test_base_url
        assert call_kwargs["redirect_path"] == self.test_redirect_path
        assert call_kwargs["valid_scopes"] == self.test_valid_scopes
        assert call_kwargs["jwt_signing_key"] == self.test_jwt_signing_key

        # Verify provider property works
        assert proxy.provider == mock_oauth_proxy_instance

    def test_init_with_default_values(self):
        """Test initialization with default values."""
        with (
            patch("requests.get") as mock_requests_get,
            patch("src.auth.proxy_provider.PyJWKClient"),
            patch("src.auth.proxy_provider.OAuthProxy"),
        ):
            # Arrange
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = self.mock_openid_config
            mock_requests_get.return_value = mock_response

            # Act
            proxy = SingleStoreOAuthProxy(
                issuer_url=self.test_issuer_url,
                client_id=self.test_client_id,
                jwt_signing_key=self.test_jwt_signing_key,
            )

            # Assert default values
            assert proxy.client_secret == "-"
            assert proxy.base_url == "http://localhost:8010/"
            assert proxy.redirect_path == "/callback"
            assert proxy.valid_scopes == ["openid"]

    @patch("requests.get")
    def test_fetch_openid_config_network_error(self, mock_requests_get):
        """Test OpenID configuration fetch with network error."""
        # Arrange
        mock_requests_get.side_effect = ConnectionError("Network error")

        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            SingleStoreOAuthProxy(
                issuer_url=self.test_issuer_url,
                client_id=self.test_client_id,
                jwt_signing_key=self.test_jwt_signing_key,
            )

        assert "Failed to fetch OpenID configuration" in str(exc_info.value)
        assert "Network error" in str(exc_info.value)

    @patch("requests.get")
    def test_fetch_openid_config_http_error(self, mock_requests_get):
        """Test OpenID configuration fetch with HTTP error."""
        # Arrange
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 404 Not Found")
        mock_requests_get.return_value = mock_response

        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            SingleStoreOAuthProxy(
                issuer_url=self.test_issuer_url,
                client_id=self.test_client_id,
                jwt_signing_key=self.test_jwt_signing_key,
            )

        assert "Failed to fetch OpenID configuration" in str(exc_info.value)
        assert "HTTP 404 Not Found" in str(exc_info.value)

    @patch("requests.get")
    def test_fetch_openid_config_json_error(self, mock_requests_get):
        """Test OpenID configuration fetch with JSON parsing error."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_requests_get.return_value = mock_response

        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            SingleStoreOAuthProxy(
                issuer_url=self.test_issuer_url,
                client_id=self.test_client_id,
                jwt_signing_key=self.test_jwt_signing_key,
            )

        assert "Failed to fetch OpenID configuration" in str(exc_info.value)

    @patch("requests.get")
    @patch("src.auth.proxy_provider.PyJWKClient")
    def test_create_verifier_missing_jwks_uri(
        self, mock_jwks_client, mock_requests_get
    ):
        """Test verifier creation with missing jwks_uri in config."""
        # Arrange
        incomplete_config = {
            "issuer": "https://authsvc.singlestore.com",
            "authorization_endpoint": "https://authsvc.singlestore.com/authorize",
            "token_endpoint": "https://authsvc.singlestore.com/token",
            # Missing jwks_uri
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = incomplete_config
        mock_requests_get.return_value = mock_response

        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            SingleStoreOAuthProxy(
                issuer_url=self.test_issuer_url,
                client_id=self.test_client_id,
                jwt_signing_key=self.test_jwt_signing_key,
            )

        assert "Missing required fields in OpenID configuration" in str(exc_info.value)
        assert "jwks_uri=None" in str(exc_info.value)

    @patch("requests.get")
    @patch("src.auth.proxy_provider.PyJWKClient")
    def test_create_verifier_missing_issuer(self, mock_jwks_client, mock_requests_get):
        """Test verifier creation with missing issuer in config."""
        # Arrange
        incomplete_config = {
            "authorization_endpoint": "https://authsvc.singlestore.com/authorize",
            "token_endpoint": "https://authsvc.singlestore.com/token",
            "jwks_uri": "https://authsvc.singlestore.com/.well-known/jwks.json",
            # Missing issuer
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = incomplete_config
        mock_requests_get.return_value = mock_response

        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            SingleStoreOAuthProxy(
                issuer_url=self.test_issuer_url,
                client_id=self.test_client_id,
                jwt_signing_key=self.test_jwt_signing_key,
            )

        assert "Missing required fields in OpenID configuration" in str(exc_info.value)
        assert "issuer=None" in str(exc_info.value)

    @patch("requests.get")
    @patch("src.auth.proxy_provider.PyJWKClient")
    @patch("src.auth.proxy_provider.OAuthProxy")
    def test_create_oauth_proxy_missing_authorization_endpoint(
        self, mock_oauth_proxy, mock_jwks_client, mock_requests_get
    ):
        """Test OAuth proxy creation with missing authorization_endpoint."""
        # Arrange
        incomplete_config = {
            "issuer": "https://authsvc.singlestore.com",
            "token_endpoint": "https://authsvc.singlestore.com/token",
            "jwks_uri": "https://authsvc.singlestore.com/.well-known/jwks.json",
            # Missing authorization_endpoint
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = incomplete_config
        mock_requests_get.return_value = mock_response

        mock_jwks_client_instance = Mock()
        mock_jwks_client.return_value = mock_jwks_client_instance

        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            SingleStoreOAuthProxy(
                issuer_url=self.test_issuer_url,
                client_id=self.test_client_id,
                jwt_signing_key=self.test_jwt_signing_key,
            )

        assert "Missing required fields in OpenID configuration" in str(exc_info.value)
        assert "authorization_endpoint=None" in str(exc_info.value)

    @patch("requests.get")
    @patch("src.auth.proxy_provider.PyJWKClient")
    @patch("src.auth.proxy_provider.OAuthProxy")
    def test_create_oauth_proxy_missing_token_endpoint(
        self, mock_oauth_proxy, mock_jwks_client, mock_requests_get
    ):
        """Test OAuth proxy creation with missing token_endpoint."""
        # Arrange
        incomplete_config = {
            "issuer": "https://authsvc.singlestore.com",
            "authorization_endpoint": "https://authsvc.singlestore.com/authorize",
            "jwks_uri": "https://authsvc.singlestore.com/.well-known/jwks.json",
            # Missing token_endpoint
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = incomplete_config
        mock_requests_get.return_value = mock_response

        mock_jwks_client_instance = Mock()
        mock_jwks_client.return_value = mock_jwks_client_instance

        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            SingleStoreOAuthProxy(
                issuer_url=self.test_issuer_url,
                client_id=self.test_client_id,
                jwt_signing_key=self.test_jwt_signing_key,
            )

        assert "Missing required fields in OpenID configuration" in str(exc_info.value)
        assert "token_endpoint=None" in str(exc_info.value)

    @patch("requests.get")
    @patch("src.auth.proxy_provider.PyJWKClient")
    @patch("src.auth.proxy_provider.OAuthProxy")
    def test_create_oauth_proxy_missing_jwt_signing_key(
        self, mock_oauth_proxy, mock_jwks_client, mock_requests_get
    ):
        """Test OAuth proxy creation with missing JWT signing key."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = self.mock_openid_config
        mock_requests_get.return_value = mock_response

        mock_jwks_client_instance = Mock()
        mock_jwks_client.return_value = mock_jwks_client_instance

        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            SingleStoreOAuthProxy(
                issuer_url=self.test_issuer_url,
                client_id=self.test_client_id,
                # Missing jwt_signing_key
            )

        assert "JWT signing key is not set" in str(exc_info.value)

    @patch("requests.get")
    @patch("src.auth.proxy_provider.PyJWKClient")
    @patch("src.auth.proxy_provider.OAuthProxy")
    def test_get_provider(self, mock_oauth_proxy, mock_jwks_client, mock_requests_get):
        """Test get_provider method returns the OAuth proxy instance."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = self.mock_openid_config
        mock_requests_get.return_value = mock_response

        mock_jwks_client_instance = Mock()
        mock_jwks_client.return_value = mock_jwks_client_instance

        mock_oauth_proxy_instance = Mock(spec=OAuthProxy)
        mock_oauth_proxy.return_value = mock_oauth_proxy_instance

        proxy = SingleStoreOAuthProxy(
            issuer_url=self.test_issuer_url,
            client_id=self.test_client_id,
            jwt_signing_key=self.test_jwt_signing_key,
        )

        # Act
        provider = proxy.get_provider()

        # Assert
        assert provider == mock_oauth_proxy_instance
        assert provider == proxy.provider

    @patch("requests.get")
    @patch("src.auth.proxy_provider.PyJWKClient")
    @patch("src.auth.proxy_provider.OAuthProxy")
    def test_issuer_url_normalization(
        self, mock_oauth_proxy, mock_jwks_client, mock_requests_get
    ):
        """Test that issuer URL is properly normalized for OpenID config URL."""
        # Arrange
        test_issuer_without_trailing_slash = "https://authsvc.singlestore.com"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = self.mock_openid_config
        mock_requests_get.return_value = mock_response

        mock_jwks_client_instance = Mock()
        mock_jwks_client.return_value = mock_jwks_client_instance

        mock_oauth_proxy_instance = Mock(spec=OAuthProxy)
        mock_oauth_proxy.return_value = mock_oauth_proxy_instance

        # Act
        proxy = SingleStoreOAuthProxy(
            issuer_url=test_issuer_without_trailing_slash,
            client_id=self.test_client_id,
            jwt_signing_key=self.test_jwt_signing_key,
        )

        # Assert
        expected_config_url = (
            "https://authsvc.singlestore.com/.well-known/openid-configuration"
        )
        mock_requests_get.assert_called_once_with(expected_config_url, timeout=10.0)
        assert proxy.openid_config_url == expected_config_url


class TestCustomJWTVerifier:
    """Test cases for the CustomJWTVerifier inner class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.test_jwks_uri = "https://authsvc.singlestore.com/.well-known/jwks.json"
        self.test_issuer = "https://authsvc.singlestore.com"
        self.test_audience = "b7dbf19e-d140-4334-bae4-e8cd03614485"
        self.test_base_url = "http://localhost:8010/"
        self.test_required_scopes = ["openid"]

        # Mock token data
        self.mock_decoded_token = {
            "iss": self.test_issuer,
            "aud": [self.test_audience],
            "client_id": self.test_audience,
            "exp": 1734567890,
            "iat": 1734564290,
            "sub": "user123",
        }

    @patch("requests.get")
    @patch("src.auth.proxy_provider.PyJWKClient")
    @patch("src.auth.proxy_provider.OAuthProxy")
    def test_verify_token_success(
        self, mock_oauth_proxy, mock_jwks_client, mock_requests_get
    ):
        """Test successful token verification."""
        # Arrange
        mock_openid_config = {
            "issuer": self.test_issuer,
            "authorization_endpoint": "https://authsvc.singlestore.com/authorize",
            "token_endpoint": "https://authsvc.singlestore.com/token",
            "jwks_uri": self.test_jwks_uri,
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_openid_config
        mock_requests_get.return_value = mock_response

        mock_signing_key = Mock()
        mock_jwks_client_instance = Mock()
        mock_jwks_client_instance.get_signing_key_from_jwt.return_value = (
            mock_signing_key
        )
        mock_jwks_client.return_value = mock_jwks_client_instance

        mock_oauth_proxy_instance = Mock(spec=OAuthProxy)
        mock_oauth_proxy.return_value = mock_oauth_proxy_instance

        test_token = "eyJhbGciOiJFUzUxMiIsInR5cCI6IkpXVCJ9..."

        with patch("jwt.decode") as mock_jwt_decode:
            mock_jwt_decode.return_value = self.mock_decoded_token

            # Create proxy which will create the verifier
            proxy = SingleStoreOAuthProxy(
                issuer_url="https://authsvc.singlestore.com/",
                client_id=self.test_audience,
                jwt_signing_key="test-key",
            )

            # Act
            import asyncio

            result = asyncio.run(proxy._verifier.verify_token(test_token))

            # Assert
            assert result is not None
            assert isinstance(result, AccessToken)
            assert result.token == test_token
            assert result.client_id == self.test_audience
            assert result.scopes == ["openid"]
            assert result.expires_at == 1734567890
            assert result.resource == self.test_audience

            # Verify JWT validation was called with correct parameters
            mock_jwt_decode.assert_called_once_with(
                test_token,
                mock_signing_key,
                audience=self.test_audience,
                options={"verify_exp": True},
                algorithms=["ES512"],
            )

    @patch("requests.get")
    @patch("src.auth.proxy_provider.PyJWKClient")
    @patch("src.auth.proxy_provider.OAuthProxy")
    def test_verify_token_audience_list(
        self, mock_oauth_proxy, mock_jwks_client, mock_requests_get
    ):
        """Test token verification with audience as a list."""
        # Arrange
        mock_openid_config = {
            "issuer": self.test_issuer,
            "authorization_endpoint": "https://authsvc.singlestore.com/authorize",
            "token_endpoint": "https://authsvc.singlestore.com/token",
            "jwks_uri": self.test_jwks_uri,
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_openid_config
        mock_requests_get.return_value = mock_response

        mock_signing_key = Mock()
        mock_jwks_client_instance = Mock()
        mock_jwks_client_instance.get_signing_key_from_jwt.return_value = (
            mock_signing_key
        )
        mock_jwks_client.return_value = mock_jwks_client_instance

        mock_oauth_proxy_instance = Mock(spec=OAuthProxy)
        mock_oauth_proxy.return_value = mock_oauth_proxy_instance

        test_token = "eyJhbGciOiJFUzUxMiIsInR5cCI6IkpXVCJ9..."

        # Mock decoded token with audience as list
        mock_decoded_with_list_aud = self.mock_decoded_token.copy()
        mock_decoded_with_list_aud["aud"] = [self.test_audience, "other-audience"]

        with patch("jwt.decode") as mock_jwt_decode:
            mock_jwt_decode.return_value = mock_decoded_with_list_aud

            # Create proxy which will create the verifier
            proxy = SingleStoreOAuthProxy(
                issuer_url="https://authsvc.singlestore.com/",
                client_id=self.test_audience,
                jwt_signing_key="test-key",
            )

            # Act
            import asyncio

            result = asyncio.run(proxy._verifier.verify_token(test_token))

            # Assert
            assert result is not None
            assert isinstance(result, AccessToken)
            assert result.resource == self.test_audience  # First item in list

    @patch("requests.get")
    @patch("src.auth.proxy_provider.PyJWKClient")
    @patch("src.auth.proxy_provider.OAuthProxy")
    def test_verify_token_audience_string(
        self, mock_oauth_proxy, mock_jwks_client, mock_requests_get
    ):
        """Test token verification with audience as a string."""
        # Arrange
        mock_openid_config = {
            "issuer": self.test_issuer,
            "authorization_endpoint": "https://authsvc.singlestore.com/authorize",
            "token_endpoint": "https://authsvc.singlestore.com/token",
            "jwks_uri": self.test_jwks_uri,
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_openid_config
        mock_requests_get.return_value = mock_response

        mock_signing_key = Mock()
        mock_jwks_client_instance = Mock()
        mock_jwks_client_instance.get_signing_key_from_jwt.return_value = (
            mock_signing_key
        )
        mock_jwks_client.return_value = mock_jwks_client_instance

        mock_oauth_proxy_instance = Mock(spec=OAuthProxy)
        mock_oauth_proxy.return_value = mock_oauth_proxy_instance

        test_token = "eyJhbGciOiJFUzUxMiIsInR5cCI6IkpXVCJ9..."

        # Mock decoded token with audience as string
        mock_decoded_with_str_aud = self.mock_decoded_token.copy()
        mock_decoded_with_str_aud["aud"] = self.test_audience

        with patch("jwt.decode") as mock_jwt_decode:
            mock_jwt_decode.return_value = mock_decoded_with_str_aud

            # Create proxy which will create the verifier
            proxy = SingleStoreOAuthProxy(
                issuer_url="https://authsvc.singlestore.com/",
                client_id=self.test_audience,
                jwt_signing_key="test-key",
            )

            # Act
            import asyncio

            result = asyncio.run(proxy._verifier.verify_token(test_token))

            # Assert
            assert result is not None
            assert isinstance(result, AccessToken)
            assert result.resource == self.test_audience  # String value

    @patch("requests.get")
    @patch("src.auth.proxy_provider.PyJWKClient")
    @patch("src.auth.proxy_provider.OAuthProxy")
    def test_verify_token_jwt_error(
        self, mock_oauth_proxy, mock_jwks_client, mock_requests_get
    ):
        """Test token verification with JWT validation error."""
        # Arrange
        mock_openid_config = {
            "issuer": self.test_issuer,
            "authorization_endpoint": "https://authsvc.singlestore.com/authorize",
            "token_endpoint": "https://authsvc.singlestore.com/token",
            "jwks_uri": self.test_jwks_uri,
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_openid_config
        mock_requests_get.return_value = mock_response

        mock_signing_key = Mock()
        mock_jwks_client_instance = Mock()
        mock_jwks_client_instance.get_signing_key_from_jwt.return_value = (
            mock_signing_key
        )
        mock_jwks_client.return_value = mock_jwks_client_instance

        mock_oauth_proxy_instance = Mock(spec=OAuthProxy)
        mock_oauth_proxy.return_value = mock_oauth_proxy_instance

        test_token = "invalid-token"

        with (
            patch("jwt.decode") as mock_jwt_decode,
            patch("builtins.print") as mock_print,
        ):
            mock_jwt_decode.side_effect = jwt.PyJWTError("Invalid token")

            # Create proxy which will create the verifier
            proxy = SingleStoreOAuthProxy(
                issuer_url="https://authsvc.singlestore.com/",
                client_id=self.test_audience,
                jwt_signing_key="test-key",
            )

            # Act
            import asyncio

            result = asyncio.run(proxy._verifier.verify_token(test_token))

            # Assert
            assert result is None
            mock_print.assert_called_with(
                "Token validation error:", mock_jwt_decode.side_effect
            )

    @patch("requests.get")
    @patch("src.auth.proxy_provider.PyJWKClient")
    @patch("src.auth.proxy_provider.OAuthProxy")
    def test_verify_token_jwks_client_error(
        self, mock_oauth_proxy, mock_jwks_client, mock_requests_get
    ):
        """Test token verification with JWKS client error."""
        # Arrange
        mock_openid_config = {
            "issuer": self.test_issuer,
            "authorization_endpoint": "https://authsvc.singlestore.com/authorize",
            "token_endpoint": "https://authsvc.singlestore.com/token",
            "jwks_uri": self.test_jwks_uri,
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_openid_config
        mock_requests_get.return_value = mock_response

        mock_jwks_client_instance = Mock()
        mock_jwks_client.return_value = mock_jwks_client_instance

        mock_oauth_proxy_instance = Mock(spec=OAuthProxy)
        mock_oauth_proxy.return_value = mock_oauth_proxy_instance

        test_token = "test-token"

        # Create proxy which will create the verifier
        proxy = SingleStoreOAuthProxy(
            issuer_url="https://authsvc.singlestore.com/",
            client_id=self.test_audience,
            jwt_signing_key="test-key",
        )

        # Now set up the error to occur during verification
        mock_jwks_client_instance.get_signing_key_from_jwt.side_effect = Exception(
            "JWKS client error"
        )

        # Act & Assert
        import asyncio

        with pytest.raises(Exception) as exc_info:
            asyncio.run(proxy._verifier.verify_token(test_token))

        assert "JWKS client error" in str(exc_info.value)


class TestSingleStoreOAuthProxyIntegration:
    """Integration test cases for SingleStoreOAuthProxy."""

    @patch("requests.get")
    @patch("src.auth.proxy_provider.PyJWKClient")
    @patch("src.auth.proxy_provider.OAuthProxy")
    def test_complete_initialization_workflow(
        self, mock_oauth_proxy, mock_jwks_client, mock_requests_get
    ):
        """Test the complete initialization workflow with all components."""
        # Arrange
        mock_openid_config = {
            "issuer": "https://authsvc.singlestore.com",
            "authorization_endpoint": "https://authsvc.singlestore.com/authorize",
            "token_endpoint": "https://authsvc.singlestore.com/token",
            "jwks_uri": "https://authsvc.singlestore.com/.well-known/jwks.json",
            "response_types_supported": ["code"],
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_openid_config
        mock_requests_get.return_value = mock_response

        mock_jwks_client_instance = Mock()
        mock_jwks_client.return_value = mock_jwks_client_instance

        mock_oauth_proxy_instance = Mock(spec=OAuthProxy)
        mock_oauth_proxy.return_value = mock_oauth_proxy_instance

        # Act
        proxy = SingleStoreOAuthProxy(
            issuer_url="https://authsvc.singlestore.com/",
            client_id="test-client-id",
            client_secret="test-secret",
            base_url="https://myapp.example.com",
            redirect_path="/oauth/callback",
            valid_scopes=["openid", "profile", "email"],
            jwt_signing_key="my-jwt-secret",
        )

        # Assert configuration was loaded
        assert proxy._config == mock_openid_config

        # Assert verifier was created with correct parameters
        assert proxy._verifier is not None

        # Assert OAuth proxy was created and is accessible
        provider = proxy.get_provider()
        assert provider == mock_oauth_proxy_instance

        # Verify the OAuth proxy was called with the correct configuration
        call_kwargs = mock_oauth_proxy.call_args[1]
        assert (
            call_kwargs["upstream_authorization_endpoint"]
            == "https://authsvc.singlestore.com/authorize"
        )
        assert (
            call_kwargs["upstream_token_endpoint"]
            == "https://authsvc.singlestore.com/token"
        )
        assert call_kwargs["upstream_client_id"] == "test-client-id"
        assert call_kwargs["upstream_client_secret"] == "test-secret"
        assert call_kwargs["base_url"] == "https://myapp.example.com"
        assert call_kwargs["redirect_path"] == "/oauth/callback"
        assert call_kwargs["valid_scopes"] == ["openid", "profile", "email"]
        assert call_kwargs["jwt_signing_key"] == "my-jwt-secret"

    def test_multiple_proxy_instances(self):
        """Test creating multiple proxy instances with different configurations."""
        with (
            patch("requests.get") as mock_requests_get,
            patch("src.auth.proxy_provider.PyJWKClient"),
            patch("src.auth.proxy_provider.OAuthProxy") as mock_oauth_proxy,
        ):
            # Arrange
            mock_openid_config = {
                "issuer": "https://authsvc.singlestore.com",
                "authorization_endpoint": "https://authsvc.singlestore.com/authorize",
                "token_endpoint": "https://authsvc.singlestore.com/token",
                "jwks_uri": "https://authsvc.singlestore.com/.well-known/jwks.json",
            }

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_openid_config
            mock_requests_get.return_value = mock_response

            mock_oauth_proxy.side_effect = [
                Mock(spec=OAuthProxy),
                Mock(spec=OAuthProxy),
            ]

            # Act - Create two different proxy instances
            proxy1 = SingleStoreOAuthProxy(
                issuer_url="https://authsvc.singlestore.com/",
                client_id="client-1",
                jwt_signing_key="key-1",
            )

            proxy2 = SingleStoreOAuthProxy(
                issuer_url="https://authsvc.singlestore.com/",
                client_id="client-2",
                jwt_signing_key="key-2",
                base_url="https://different.example.com",
                valid_scopes=["custom", "scopes"],
            )

            # Assert
            assert proxy1.client_id == "client-1"
            assert proxy2.client_id == "client-2"
            assert proxy1.base_url == "http://localhost:8010/"
            assert proxy2.base_url == "https://different.example.com"
            assert proxy1.valid_scopes == ["openid"]
            assert proxy2.valid_scopes == ["custom", "scopes"]
            assert proxy1.provider != proxy2.provider


class TestSingleStoreOAuthProxyErrorHandling:
    """Test cases for error handling scenarios in SingleStoreOAuthProxy."""

    def test_invalid_issuer_url_format(self):
        """Test initialization with invalid issuer URL format."""
        with patch("requests.get") as mock_requests_get:
            mock_requests_get.side_effect = Exception("Invalid URL")

            with pytest.raises(RuntimeError) as exc_info:
                SingleStoreOAuthProxy(
                    issuer_url="not-a-valid-url",
                    client_id="test-client",
                    jwt_signing_key="test-key",
                )

            assert "Failed to fetch OpenID configuration" in str(exc_info.value)

    @patch("requests.get")
    def test_timeout_during_config_fetch(self, mock_requests_get):
        """Test timeout during OpenID configuration fetch."""
        # Arrange
        import requests

        mock_requests_get.side_effect = requests.Timeout("Request timed out")

        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            SingleStoreOAuthProxy(
                issuer_url="https://authsvc.singlestore.com/",
                client_id="test-client",
                jwt_signing_key="test-key",
            )

        assert "Failed to fetch OpenID configuration" in str(exc_info.value)
        assert "Request timed out" in str(exc_info.value)

    @patch("requests.get")
    def test_malformed_openid_config(self, mock_requests_get):
        """Test handling of malformed OpenID configuration."""
        # Arrange
        malformed_config = {"invalid": "config", "missing_required_fields": True}

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = malformed_config
        mock_requests_get.return_value = mock_response

        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            SingleStoreOAuthProxy(
                issuer_url="https://authsvc.singlestore.com/",
                client_id="test-client",
                jwt_signing_key="test-key",
            )

        assert "Missing required fields in OpenID configuration" in str(exc_info.value)

    @patch("requests.get")
    @patch("src.auth.proxy_provider.PyJWKClient")
    def test_jwks_client_initialization_failure(
        self, mock_jwks_client, mock_requests_get
    ):
        """Test handling of JWKS client initialization failure."""
        # Arrange
        mock_openid_config = {
            "issuer": "https://authsvc.singlestore.com",
            "authorization_endpoint": "https://authsvc.singlestore.com/authorize",
            "token_endpoint": "https://authsvc.singlestore.com/token",
            "jwks_uri": "https://authsvc.singlestore.com/.well-known/jwks.json",
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_openid_config
        mock_requests_get.return_value = mock_response

        mock_jwks_client.side_effect = Exception("JWKS client initialization failed")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            SingleStoreOAuthProxy(
                issuer_url="https://authsvc.singlestore.com/",
                client_id="test-client",
                jwt_signing_key="test-key",
            )

        assert "JWKS client initialization failed" in str(exc_info.value)

    @patch("requests.get")
    @patch("src.auth.proxy_provider.PyJWKClient")
    @patch("src.auth.proxy_provider.OAuthProxy")
    def test_oauth_proxy_initialization_failure(
        self, mock_oauth_proxy, mock_jwks_client, mock_requests_get
    ):
        """Test handling of OAuth proxy initialization failure."""
        # Arrange
        mock_openid_config = {
            "issuer": "https://authsvc.singlestore.com",
            "authorization_endpoint": "https://authsvc.singlestore.com/authorize",
            "token_endpoint": "https://authsvc.singlestore.com/token",
            "jwks_uri": "https://authsvc.singlestore.com/.well-known/jwks.json",
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_openid_config
        mock_requests_get.return_value = mock_response

        mock_jwks_client_instance = Mock()
        mock_jwks_client.return_value = mock_jwks_client_instance

        mock_oauth_proxy.side_effect = Exception("OAuth proxy initialization failed")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            SingleStoreOAuthProxy(
                issuer_url="https://authsvc.singlestore.com/",
                client_id="test-client",
                jwt_signing_key="test-key",
            )

        assert "OAuth proxy initialization failed" in str(exc_info.value)
