"""Unit tests for the main authenticate function."""

from unittest.mock import Mock, patch

from src.auth.browser_auth import authenticate
from tests.models import (
    OAuthServerConfig,
    PKCEData,
    CallbackParameters,
    TokenSetModel,
)


class TestAuthenticate:
    """Test cases for the main authenticate function."""

    @patch("src.auth.browser_auth.exchange_code_for_tokens")
    @patch("src.auth.browser_auth.validate_callback")
    @patch("src.auth.browser_auth.wait_for_callback")
    @patch("webbrowser.open")
    @patch("socketserver.TCPServer")
    @patch("src.auth.browser_auth.create_authorization_url")
    @patch("src.auth.browser_auth.generate_pkce_data")
    @patch("src.auth.browser_auth.setup_oauth_config")
    def test_authenticate_success(
        self,
        mock_setup_oauth,
        mock_generate_pkce,
        mock_create_auth_url,
        mock_tcp_server,
        mock_webbrowser,
        mock_wait_callback,
        mock_validate_callback,
        mock_exchange_tokens,
    ):
        """Test successful authentication flow."""
        # Arrange
        client_id = "test_client_id"
        oauth_host = "https://auth.example.com"
        auth_timeout = 300

        # Mock OAuth configuration
        oauth_config = OAuthServerConfig(
            authorization_endpoint="https://auth.example.com/authorize",
            token_endpoint="https://auth.example.com/token",
        )
        mock_setup_oauth.return_value = oauth_config

        # Mock PKCE data
        pkce_data = PKCEData(
            code_verifier="verifier123", code_challenge="challenge456", state="state789"
        )
        mock_generate_pkce.return_value = pkce_data

        # Mock authorization URL
        auth_url = "https://auth.example.com/authorize?client_id=test&..."
        mock_create_auth_url.return_value = auth_url

        # Mock TCP server for finding available port
        mock_port_server = Mock()
        mock_port_server.server_address = ("127.0.0.1", 8080)
        mock_tcp_server.return_value.__enter__.return_value = mock_port_server

        # Mock callback parameters
        callback_params = CallbackParameters(code="auth_code_123", state="state789")
        mock_wait_callback.return_value = callback_params
        mock_validate_callback.return_value = "auth_code_123"

        # Mock token exchange
        token_set = TokenSetModel(
            access_token="access_token_123",
            token_type="Bearer",
            refresh_token="refresh_token_456",
            expires_in=3600,
            expires_at=1609462800,
        )
        mock_exchange_tokens.return_value = token_set

        # Act
        success, result_token_set = authenticate(client_id, oauth_host, auth_timeout)

        # Assert
        assert success is True
        assert result_token_set == token_set

        # Verify all functions were called correctly
        mock_setup_oauth.assert_called_once_with(oauth_host)
        mock_generate_pkce.assert_called_once()
        mock_create_auth_url.assert_called_once_with(
            oauth_config, pkce_data, client_id, "http://127.0.0.1:8080/callback"
        )
        mock_webbrowser.assert_called_once_with(auth_url)
        mock_wait_callback.assert_called_once()
        mock_validate_callback.assert_called_once_with(callback_params, pkce_data.state)
        mock_exchange_tokens.assert_called_once_with(
            oauth_config,
            "auth_code_123",
            pkce_data,
            client_id,
            "http://127.0.0.1:8080/callback",
        )

    @patch("src.auth.browser_auth.setup_oauth_config")
    def test_authenticate_oauth_config_failure(self, mock_setup_oauth):
        """Test authentication failure during OAuth config setup."""
        # Arrange
        client_id = "test_client_id"
        oauth_host = "https://auth.example.com"
        auth_timeout = 300

        mock_setup_oauth.side_effect = Exception("OAuth discovery failed")

        # Act
        success, result_token_set = authenticate(client_id, oauth_host, auth_timeout)

        # Assert
        assert success is False
        assert result_token_set is None

    @patch("src.auth.browser_auth.generate_pkce_data")
    @patch("src.auth.browser_auth.setup_oauth_config")
    def test_authenticate_pkce_generation_failure(
        self, mock_setup_oauth, mock_generate_pkce
    ):
        """Test authentication failure during PKCE generation."""
        # Arrange
        client_id = "test_client_id"
        oauth_host = "https://auth.example.com"
        auth_timeout = 300

        oauth_config = OAuthServerConfig(
            authorization_endpoint="https://auth.example.com/authorize",
            token_endpoint="https://auth.example.com/token",
        )
        mock_setup_oauth.return_value = oauth_config
        mock_generate_pkce.side_effect = Exception("PKCE generation failed")

        # Act
        success, result_token_set = authenticate(client_id, oauth_host, auth_timeout)

        # Assert
        assert success is False
        assert result_token_set is None

    @patch("src.auth.browser_auth.wait_for_callback")
    @patch("webbrowser.open")
    @patch("socketserver.TCPServer")
    @patch("src.auth.browser_auth.create_authorization_url")
    @patch("src.auth.browser_auth.generate_pkce_data")
    @patch("src.auth.browser_auth.setup_oauth_config")
    def test_authenticate_callback_timeout(
        self,
        mock_setup_oauth,
        mock_generate_pkce,
        mock_create_auth_url,
        mock_tcp_server,
        mock_webbrowser,
        mock_wait_callback,
    ):
        """Test authentication failure due to callback timeout."""
        # Arrange
        client_id = "test_client_id"
        oauth_host = "https://auth.example.com"
        auth_timeout = 300

        # Setup successful initial steps
        oauth_config = OAuthServerConfig(
            authorization_endpoint="https://auth.example.com/authorize",
            token_endpoint="https://auth.example.com/token",
        )
        mock_setup_oauth.return_value = oauth_config

        pkce_data = PKCEData(
            code_verifier="verifier123", code_challenge="challenge456", state="state789"
        )
        mock_generate_pkce.return_value = pkce_data

        auth_url = "https://auth.example.com/authorize?client_id=test&..."
        mock_create_auth_url.return_value = auth_url

        mock_port_server = Mock()
        mock_port_server.server_address = ("127.0.0.1", 8080)
        mock_tcp_server.return_value.__enter__.return_value = mock_port_server

        # Mock callback timeout
        mock_wait_callback.side_effect = Exception("Authentication timed out")

        # Act
        success, result_token_set = authenticate(client_id, oauth_host, auth_timeout)

        # Assert
        assert success is False
        assert result_token_set is None

    @patch("src.auth.browser_auth.validate_callback")
    @patch("src.auth.browser_auth.wait_for_callback")
    @patch("webbrowser.open")
    @patch("socketserver.TCPServer")
    @patch("src.auth.browser_auth.create_authorization_url")
    @patch("src.auth.browser_auth.generate_pkce_data")
    @patch("src.auth.browser_auth.setup_oauth_config")
    def test_authenticate_state_mismatch(
        self,
        mock_setup_oauth,
        mock_generate_pkce,
        mock_create_auth_url,
        mock_tcp_server,
        mock_webbrowser,
        mock_wait_callback,
        mock_validate_callback,
    ):
        """Test authentication failure due to state parameter mismatch."""
        # Arrange
        client_id = "test_client_id"
        oauth_host = "https://auth.example.com"
        auth_timeout = 300

        # Setup successful initial steps
        oauth_config = OAuthServerConfig(
            authorization_endpoint="https://auth.example.com/authorize",
            token_endpoint="https://auth.example.com/token",
        )
        mock_setup_oauth.return_value = oauth_config

        pkce_data = PKCEData(
            code_verifier="verifier123", code_challenge="challenge456", state="state789"
        )
        mock_generate_pkce.return_value = pkce_data

        auth_url = "https://auth.example.com/authorize?client_id=test&..."
        mock_create_auth_url.return_value = auth_url

        mock_port_server = Mock()
        mock_port_server.server_address = ("127.0.0.1", 8080)
        mock_tcp_server.return_value.__enter__.return_value = mock_port_server

        callback_params = CallbackParameters(code="auth_code_123", state="wrong_state")
        mock_wait_callback.return_value = callback_params

        # Mock state validation failure
        mock_validate_callback.side_effect = Exception("State parameter mismatch")

        # Act
        success, result_token_set = authenticate(client_id, oauth_host, auth_timeout)

        # Assert
        assert success is False
        assert result_token_set is None

    @patch("src.auth.browser_auth.exchange_code_for_tokens")
    @patch("src.auth.browser_auth.validate_callback")
    @patch("src.auth.browser_auth.wait_for_callback")
    @patch("webbrowser.open")
    @patch("socketserver.TCPServer")
    @patch("src.auth.browser_auth.create_authorization_url")
    @patch("src.auth.browser_auth.generate_pkce_data")
    @patch("src.auth.browser_auth.setup_oauth_config")
    def test_authenticate_token_exchange_failure(
        self,
        mock_setup_oauth,
        mock_generate_pkce,
        mock_create_auth_url,
        mock_tcp_server,
        mock_webbrowser,
        mock_wait_callback,
        mock_validate_callback,
        mock_exchange_tokens,
    ):
        """Test authentication failure during token exchange."""
        # Arrange
        client_id = "test_client_id"
        oauth_host = "https://auth.example.com"
        auth_timeout = 300

        # Setup successful initial steps
        oauth_config = OAuthServerConfig(
            authorization_endpoint="https://auth.example.com/authorize",
            token_endpoint="https://auth.example.com/token",
        )
        mock_setup_oauth.return_value = oauth_config

        pkce_data = PKCEData(
            code_verifier="verifier123", code_challenge="challenge456", state="state789"
        )
        mock_generate_pkce.return_value = pkce_data

        auth_url = "https://auth.example.com/authorize?client_id=test&..."
        mock_create_auth_url.return_value = auth_url

        mock_port_server = Mock()
        mock_port_server.server_address = ("127.0.0.1", 8080)
        mock_tcp_server.return_value.__enter__.return_value = mock_port_server

        callback_params = CallbackParameters(code="auth_code_123", state="state789")
        mock_wait_callback.return_value = callback_params
        mock_validate_callback.return_value = "auth_code_123"

        # Mock token exchange failure
        mock_exchange_tokens.side_effect = Exception("Token exchange failed")

        # Act
        success, result_token_set = authenticate(client_id, oauth_host, auth_timeout)

        # Assert
        assert success is False
        assert result_token_set is None

    def test_authenticate_with_default_parameters(self):
        """Test authenticate function with default parameters."""
        # Arrange & Act
        with patch.multiple(
            "src.auth.browser_auth",
            setup_oauth_config=Mock(side_effect=Exception("Test exception")),
        ):
            success, result_token_set = authenticate()

        # Assert
        assert success is False
        assert result_token_set is None
