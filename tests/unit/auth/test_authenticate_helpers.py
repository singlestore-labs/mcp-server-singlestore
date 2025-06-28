"""Unit tests for OAuth authentication helper functions."""

import pytest
from unittest.mock import Mock, patch

from src.auth.browser_auth import (
    setup_oauth_config,
    generate_pkce_data,
    create_authorization_url,
    wait_for_callback,
    validate_callback,
    exchange_code_for_tokens,
)
from tests.models import (
    OAuthServerConfig,
    PKCEData,
    CallbackParameters,
    TokenSetModel,
)


class TestSetupOAuthConfig:
    """Test cases for setup_oauth_config function."""

    @patch("src.auth.browser_auth.discover_oauth_server")
    def test_setup_oauth_config_success(self, mock_discover):
        """Test successful OAuth configuration setup."""
        # Arrange
        oauth_host = "https://auth.example.com"
        mock_config = {
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
        }
        mock_discover.return_value = mock_config

        # Act
        result = setup_oauth_config(oauth_host)

        # Assert
        assert isinstance(result, OAuthServerConfig)
        assert result.authorization_endpoint == mock_config["authorization_endpoint"]
        assert result.token_endpoint == mock_config["token_endpoint"]
        mock_discover.assert_called_once_with(oauth_host)

    @patch("src.auth.browser_auth.discover_oauth_server")
    def test_setup_oauth_config_missing_authorization_endpoint(self, mock_discover):
        """Test OAuth config setup with missing authorization endpoint."""
        # Arrange
        oauth_host = "https://auth.example.com"
        mock_config = {"token_endpoint": "https://auth.example.com/token"}
        mock_discover.return_value = mock_config

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            setup_oauth_config(oauth_host)
        assert "missing required endpoints" in str(exc_info.value)

    @patch("src.auth.browser_auth.discover_oauth_server")
    def test_setup_oauth_config_missing_token_endpoint(self, mock_discover):
        """Test OAuth config setup with missing token endpoint."""
        # Arrange
        oauth_host = "https://auth.example.com"
        mock_config = {"authorization_endpoint": "https://auth.example.com/authorize"}
        mock_discover.return_value = mock_config

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            setup_oauth_config(oauth_host)
        assert "missing required endpoints" in str(exc_info.value)

    @patch("src.auth.browser_auth.discover_oauth_server")
    def test_setup_oauth_config_discovery_failure(self, mock_discover):
        """Test OAuth config setup when discovery fails."""
        # Arrange
        oauth_host = "https://auth.example.com"
        mock_discover.side_effect = Exception("Discovery failed")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            setup_oauth_config(oauth_host)
        assert "Discovery failed" in str(exc_info.value)


class TestGeneratePKCEData:
    """Test cases for generate_pkce_data function."""

    @patch("src.auth.browser_auth.generate_code_verifier")
    @patch("src.auth.browser_auth.generate_code_challenge")
    @patch("src.auth.browser_auth.generate_state")
    def test_generate_pkce_data_success(
        self, mock_state, mock_challenge, mock_verifier
    ):
        """Test successful PKCE data generation."""
        # Arrange
        mock_verifier.return_value = "code_verifier_123"
        mock_challenge.return_value = "code_challenge_abc"
        mock_state.return_value = "state_xyz"

        # Act
        result = generate_pkce_data()

        # Assert
        assert isinstance(result, PKCEData)
        assert result.code_verifier == "code_verifier_123"
        assert result.code_challenge == "code_challenge_abc"
        assert result.state == "state_xyz"
        mock_verifier.assert_called_once()
        mock_challenge.assert_called_once_with("code_verifier_123")
        mock_state.assert_called_once()


class TestCreateAuthorizationUrl:
    """Test cases for create_authorization_url function."""

    def test_create_authorization_url_success(self):
        """Test successful authorization URL creation."""
        # Arrange
        oauth_config = OAuthServerConfig(
            authorization_endpoint="https://auth.example.com/authorize",
            token_endpoint="https://auth.example.com/token",
        )
        pkce_data = PKCEData(
            code_verifier="verifier123", code_challenge="challenge456", state="state789"
        )
        client_id = "b7dbf19e-d140-4334-bae4-e8cd03614485"
        redirect_uri = "http://localhost:8080/callback"

        # Act
        result = create_authorization_url(
            oauth_config, pkce_data, client_id, redirect_uri
        )

        # Assert
        assert result.startswith("https://auth.example.com/authorize?")
        assert f"client_id={client_id}" in result
        assert (
            f"redirect_uri={redirect_uri.replace('/', '%2F').replace(':', '%3A')}"
            in result
        )
        assert "response_type=code" in result
        assert f"state={pkce_data.state}" in result
        assert f"code_challenge={pkce_data.code_challenge}" in result
        assert "code_challenge_method=S256" in result
        assert "scope=" in result


class TestWaitForCallback:
    """Test cases for wait_for_callback function."""

    def test_wait_for_callback_success(self):
        """Test successful callback reception."""
        # Arrange
        mock_httpd = Mock()
        mock_httpd.received_callback = False
        mock_httpd.callback_params = {"code": "auth_code_123", "state": "state_xyz"}
        auth_timeout = 10

        # Simulate callback received after 2 handle_request calls
        def side_effect():
            if mock_httpd.handle_request.call_count >= 2:
                mock_httpd.received_callback = True

        mock_httpd.handle_request.side_effect = side_effect

        # Act
        result = wait_for_callback(mock_httpd, auth_timeout)

        # Assert
        assert isinstance(result, CallbackParameters)
        assert result.code == "auth_code_123"
        assert result.state == "state_xyz"
        assert mock_httpd.timeout == 1
        assert mock_httpd.handle_request.call_count >= 2

    def test_wait_for_callback_timeout(self):
        """Test callback wait timeout."""
        # Arrange
        mock_httpd = Mock()
        mock_httpd.received_callback = False
        auth_timeout = 0.1  # Very short timeout

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            wait_for_callback(mock_httpd, auth_timeout)
        assert "Authentication timed out" in str(exc_info.value)

    def test_wait_for_callback_no_params(self):
        """Test callback wait with no parameters received."""
        # Arrange
        mock_httpd = Mock()
        mock_httpd.received_callback = True
        mock_httpd.callback_params = None
        auth_timeout = 10

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            wait_for_callback(mock_httpd, auth_timeout)
        assert "No callback parameters received" in str(exc_info.value)


class TestValidateCallback:
    """Test cases for validate_callback function."""

    def test_validate_callback_success(self):
        """Test successful callback validation."""
        # Arrange
        callback_params = CallbackParameters(
            code="auth_code_123", state="expected_state"
        )
        expected_state = "expected_state"

        # Act
        result = validate_callback(callback_params, expected_state)

        # Assert
        assert result == "auth_code_123"

    def test_validate_callback_state_mismatch(self):
        """Test callback validation with state mismatch."""
        # Arrange
        callback_params = CallbackParameters(code="auth_code_123", state="wrong_state")
        expected_state = "expected_state"

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            validate_callback(callback_params, expected_state)
        assert "State parameter mismatch" in str(exc_info.value)

    def test_validate_callback_with_error(self):
        """Test callback validation with OAuth error."""
        # Arrange
        callback_params = CallbackParameters(
            error="access_denied", error_description="User denied access"
        )
        expected_state = "expected_state"

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            validate_callback(callback_params, expected_state)
        assert "Authorization failed: access_denied - User denied access" in str(
            exc_info.value
        )

    def test_validate_callback_no_code(self):
        """Test callback validation with no authorization code."""
        # Arrange
        callback_params = CallbackParameters(state="expected_state")
        expected_state = "expected_state"

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            validate_callback(callback_params, expected_state)
        assert "No authorization code received" in str(exc_info.value)


class TestExchangeCodeForTokens:
    """Test cases for exchange_code_for_tokens function."""

    @patch("src.auth.browser_auth.save_credentials")
    @patch("requests.post")
    @patch("src.auth.browser_auth.datetime")
    def test_exchange_code_for_tokens_success(
        self, mock_datetime, mock_post, mock_save
    ):
        """Test successful token exchange."""
        # Arrange
        oauth_config = OAuthServerConfig(
            authorization_endpoint="https://auth.example.com/authorize",
            token_endpoint="https://auth.example.com/token",
        )
        pkce_data = PKCEData(
            code_verifier="verifier123", code_challenge="challenge456", state="state789"
        )
        code = "auth_code_123"
        client_id = "b7dbf19e-d140-4334-bae4-e8cd03614485"
        redirect_uri = "http://localhost:8080/callback"

        # Mock datetime.now()
        mock_now = Mock()
        mock_now.timestamp.return_value = 1609459200.0
        mock_datetime.now.return_value = mock_now

        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "access_token_123",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "refresh_token_456",
        }
        mock_post.return_value = mock_response

        # Act
        result = exchange_code_for_tokens(
            oauth_config, code, pkce_data, client_id, redirect_uri
        )

        # Assert
        assert isinstance(result, TokenSetModel)
        assert result.access_token == "access_token_123"
        assert result.token_type == "Bearer"
        assert result.refresh_token == "refresh_token_456"
        assert result.expires_at == 1609462800  # 1609459200 + 3600

        # Verify HTTP request
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == oauth_config.token_endpoint
        assert call_args[1]["data"]["grant_type"] == "authorization_code"
        assert call_args[1]["data"]["code"] == code
        assert call_args[1]["data"]["client_id"] == client_id
        assert call_args[1]["data"]["code_verifier"] == pkce_data.code_verifier

        # Verify save_credentials was called
        mock_save.assert_called_once_with(result)

    @patch("requests.post")
    def test_exchange_code_for_tokens_http_error(self, mock_post):
        """Test token exchange with HTTP error."""
        # Arrange
        oauth_config = OAuthServerConfig(
            authorization_endpoint="https://auth.example.com/authorize",
            token_endpoint="https://auth.example.com/token",
        )
        pkce_data = PKCEData(
            code_verifier="verifier123", code_challenge="challenge456", state="state789"
        )
        code = "auth_code_123"
        client_id = "b7dbf19e-d140-4334-bae4-e8cd03614485"
        redirect_uri = "http://localhost:8080/callback"

        # Mock HTTP error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            exchange_code_for_tokens(
                oauth_config, code, pkce_data, client_id, redirect_uri
            )
        assert "Token exchange failed with status 400" in str(exc_info.value)

    @patch("requests.post")
    def test_exchange_code_for_tokens_oauth_error(self, mock_post):
        """Test token exchange with OAuth error response."""
        # Arrange
        oauth_config = OAuthServerConfig(
            authorization_endpoint="https://auth.example.com/authorize",
            token_endpoint="https://auth.example.com/token",
        )
        pkce_data = PKCEData(
            code_verifier="verifier123", code_challenge="challenge456", state="state789"
        )
        code = "auth_code_123"
        client_id = "b7dbf19e-d140-4334-bae4-e8cd03614485"
        redirect_uri = "http://localhost:8080/callback"

        # Mock OAuth error response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Authorization code expired",
        }
        mock_post.return_value = mock_response

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            exchange_code_for_tokens(
                oauth_config, code, pkce_data, client_id, redirect_uri
            )
        assert "Token exchange error: Authorization code expired" in str(exc_info.value)

    @patch("requests.post")
    def test_exchange_code_for_tokens_no_access_token(self, mock_post):
        """Test token exchange with missing access token."""
        # Arrange
        oauth_config = OAuthServerConfig(
            authorization_endpoint="https://auth.example.com/authorize",
            token_endpoint="https://auth.example.com/token",
        )
        pkce_data = PKCEData(
            code_verifier="verifier123", code_challenge="challenge456", state="state789"
        )
        code = "auth_code_123"
        client_id = "b7dbf19e-d140-4334-bae4-e8cd03614485"
        redirect_uri = "http://localhost:8080/callback"

        # Mock response without access token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"token_type": "Bearer"}
        mock_post.return_value = mock_response

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            exchange_code_for_tokens(
                oauth_config, code, pkce_data, client_id, redirect_uri
            )
        assert "No access token received from token exchange" in str(exc_info.value)
