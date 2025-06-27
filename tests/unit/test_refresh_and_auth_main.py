"""Unit tests for refactored refresh_token and get_authentication_token functions."""

from unittest.mock import patch

from src.auth.browser_auth import refresh_token, get_authentication_token
from tests.models import (
    TokenSetModel,
    TokenValidationResult,
    RefreshTokenRequest,
    OAuthServerConfig,
    TokenResponse,
    CredentialsModel,
)


class TestRefreshToken:
    """Test cases for the refactored refresh_token function."""

    @patch("src.auth.browser_auth.process_refresh_token_response")
    @patch("src.auth.browser_auth.send_refresh_token_request")
    @patch("src.auth.browser_auth.create_refresh_token_request")
    @patch("src.auth.browser_auth.setup_oauth_config")
    @patch("src.auth.browser_auth.validate_token_for_refresh")
    def test_refresh_token_success(
        self,
        mock_validate,
        mock_setup_oauth,
        mock_create_request,
        mock_send_request,
        mock_process_response,
    ):
        """Test successful token refresh."""
        # Arrange
        token_set = TokenSetModel(
            access_token="expired_token",
            token_type="Bearer",
            refresh_token="refresh_123",
        )
        client_id = "client_456"
        oauth_host = "https://auth.example.com"

        validation_result = TokenValidationResult(
            is_valid=False, is_expired=True, needs_refresh=True, has_refresh_token=True
        )
        mock_validate.return_value = validation_result

        oauth_config = OAuthServerConfig(
            authorization_endpoint="https://auth.example.com/authorize",
            token_endpoint="https://auth.example.com/token",
        )
        mock_setup_oauth.return_value = oauth_config

        refresh_request = RefreshTokenRequest(
            refresh_token="refresh_123", client_id="client_456"
        )
        mock_create_request.return_value = refresh_request

        token_response = TokenResponse(access_token="new_token", token_type="Bearer")
        mock_send_request.return_value = token_response

        new_token_set = TokenSetModel(access_token="new_token", token_type="Bearer")
        mock_process_response.return_value = new_token_set

        # Act
        result = refresh_token(token_set, client_id, oauth_host)

        # Assert
        assert result == new_token_set

        mock_validate.assert_called_once_with(token_set)
        mock_setup_oauth.assert_called_once_with(oauth_host)
        mock_create_request.assert_called_once_with(token_set, client_id)
        mock_send_request.assert_called_once_with(oauth_config, refresh_request)
        mock_process_response.assert_called_once_with(token_response)

    @patch("src.auth.browser_auth.validate_token_for_refresh")
    def test_refresh_token_no_refresh_token(self, mock_validate):
        """Test refresh token when no refresh token is available."""
        # Arrange
        token_set = TokenSetModel(access_token="token", token_type="Bearer")
        client_id = "client_456"
        oauth_host = "https://auth.example.com"

        validation_result = TokenValidationResult(
            is_valid=True,
            is_expired=False,
            needs_refresh=False,
            has_refresh_token=False,
        )
        mock_validate.return_value = validation_result

        # Act
        result = refresh_token(token_set, client_id, oauth_host)

        # Assert
        assert result is None
        mock_validate.assert_called_once_with(token_set)

    @patch("src.auth.browser_auth.validate_token_for_refresh")
    def test_refresh_token_failure(self, mock_validate):
        """Test refresh token failure."""
        # Arrange
        token_set = TokenSetModel(
            access_token="expired_token",
            token_type="Bearer",
            refresh_token="refresh_123",
        )
        client_id = "client_456"
        oauth_host = "https://auth.example.com"

        validation_result = TokenValidationResult(
            is_valid=False, is_expired=True, needs_refresh=True, has_refresh_token=True
        )
        mock_validate.return_value = validation_result

        # Mock an exception in the flow
        with patch(
            "src.auth.browser_auth.setup_oauth_config",
            side_effect=Exception("OAuth setup failed"),
        ):
            # Act
            result = refresh_token(token_set, client_id, oauth_host)

            # Assert
            assert result is None

    def test_refresh_token_with_default_parameters(self):
        """Test refresh token with default parameters."""
        # Arrange
        token_set = TokenSetModel(access_token="token", token_type="Bearer")

        with patch("src.auth.browser_auth.validate_token_for_refresh") as mock_validate:
            validation_result = TokenValidationResult(
                is_valid=True,
                is_expired=False,
                needs_refresh=False,
                has_refresh_token=False,
            )
            mock_validate.return_value = validation_result

            # Act
            result = refresh_token(token_set)

            # Assert
            assert result is None


class TestGetAuthenticationToken:
    """Test cases for the refactored get_authentication_token function."""

    @patch("src.auth.browser_auth.check_saved_credentials")
    @patch("src.auth.browser_auth.validate_token_for_refresh")
    def test_get_authentication_token_valid_saved_token(
        self, mock_validate, mock_check_creds
    ):
        """Test getting authentication token with valid saved token."""
        # Arrange
        token_set = TokenSetModel(access_token="valid_token", token_type="Bearer")
        credentials = CredentialsModel(token_set=token_set, timestamp=1609459200)
        mock_check_creds.return_value = credentials

        validation_result = TokenValidationResult(
            is_valid=True, is_expired=False, needs_refresh=False, has_refresh_token=True
        )
        mock_validate.return_value = validation_result

        # Act
        result = get_authentication_token()

        # Assert
        assert result == "valid_token"
        mock_check_creds.assert_called_once()
        mock_validate.assert_called_once_with(token_set)

    @patch("src.auth.browser_auth.attempt_token_refresh")
    @patch("src.auth.browser_auth.check_saved_credentials")
    @patch("src.auth.browser_auth.validate_token_for_refresh")
    def test_get_authentication_token_refresh_success(
        self, mock_validate, mock_check_creds, mock_attempt_refresh
    ):
        """Test getting authentication token with successful refresh."""
        # Arrange
        expired_token_set = TokenSetModel(
            access_token="expired_token",
            token_type="Bearer",
            refresh_token="refresh_123",
        )
        credentials = CredentialsModel(
            token_set=expired_token_set, timestamp=1609459200
        )
        mock_check_creds.return_value = credentials

        validation_result = TokenValidationResult(
            is_valid=False, is_expired=True, needs_refresh=True, has_refresh_token=True
        )
        mock_validate.return_value = validation_result

        refreshed_token_set = TokenSetModel(
            access_token="refreshed_token", token_type="Bearer"
        )
        mock_attempt_refresh.return_value = refreshed_token_set

        # Act
        result = get_authentication_token()

        # Assert
        assert result == "refreshed_token"
        mock_check_creds.assert_called_once()
        mock_validate.assert_called_once_with(expired_token_set)
        mock_attempt_refresh.assert_called_once()

    @patch("src.auth.browser_auth.authenticate")
    @patch("src.auth.browser_auth.attempt_token_refresh")
    @patch("src.auth.browser_auth.check_saved_credentials")
    @patch("src.auth.browser_auth.validate_token_for_refresh")
    def test_get_authentication_token_refresh_failed_auth_success(
        self, mock_validate, mock_check_creds, mock_attempt_refresh, mock_authenticate
    ):
        """Test getting authentication token when refresh fails but new auth succeeds."""
        # Arrange
        expired_token_set = TokenSetModel(
            access_token="expired_token",
            token_type="Bearer",
            refresh_token="refresh_123",
        )
        credentials = CredentialsModel(
            token_set=expired_token_set, timestamp=1609459200
        )
        mock_check_creds.return_value = credentials

        validation_result = TokenValidationResult(
            is_valid=False, is_expired=True, needs_refresh=True, has_refresh_token=True
        )
        mock_validate.return_value = validation_result

        mock_attempt_refresh.return_value = None

        new_token_set = TokenSetModel(
            access_token="new_auth_token", token_type="Bearer"
        )
        mock_authenticate.return_value = (True, new_token_set)

        # Act
        result = get_authentication_token()

        # Assert
        assert result == "new_auth_token"
        mock_check_creds.assert_called_once()
        mock_validate.assert_called_once_with(expired_token_set)
        mock_attempt_refresh.assert_called_once()
        mock_authenticate.assert_called_once()

    @patch("src.auth.browser_auth.authenticate")
    @patch("src.auth.browser_auth.check_saved_credentials")
    def test_get_authentication_token_no_saved_credentials(
        self, mock_check_creds, mock_authenticate
    ):
        """Test getting authentication token with no saved credentials."""
        # Arrange
        mock_check_creds.return_value = None

        new_token_set = TokenSetModel(access_token="new_token", token_type="Bearer")
        mock_authenticate.return_value = (True, new_token_set)

        # Act
        result = get_authentication_token()

        # Assert
        assert result == "new_token"
        mock_check_creds.assert_called_once()
        mock_authenticate.assert_called_once()

    @patch("src.auth.browser_auth.authenticate")
    def test_get_authentication_token_force_reauth(self, mock_authenticate):
        """Test getting authentication token with force reauth."""
        # Arrange
        new_token_set = TokenSetModel(
            access_token="force_auth_token", token_type="Bearer"
        )
        mock_authenticate.return_value = (True, new_token_set)

        # Act
        result = get_authentication_token(force_reauth=True)

        # Assert
        assert result == "force_auth_token"
        mock_authenticate.assert_called_once()

    @patch("src.auth.browser_auth.authenticate")
    @patch("src.auth.browser_auth.check_saved_credentials")
    def test_get_authentication_token_auth_failure(
        self, mock_check_creds, mock_authenticate
    ):
        """Test getting authentication token when authentication fails."""
        # Arrange
        mock_check_creds.return_value = None
        mock_authenticate.return_value = (False, None)

        # Act
        result = get_authentication_token()

        # Assert
        assert result is None
        mock_check_creds.assert_called_once()
        mock_authenticate.assert_called_once()

    @patch("src.auth.browser_auth.authenticate")
    @patch("src.auth.browser_auth.check_saved_credentials")
    def test_get_authentication_token_auth_success_no_token(
        self, mock_check_creds, mock_authenticate
    ):
        """Test getting authentication token when auth succeeds but no token returned."""
        # Arrange
        mock_check_creds.return_value = None
        mock_authenticate.return_value = (True, None)

        # Act
        result = get_authentication_token()

        # Assert
        assert result is None
        mock_check_creds.assert_called_once()
        mock_authenticate.assert_called_once()

    def test_get_authentication_token_with_custom_parameters(self):
        """Test getting authentication token with custom parameters."""
        # Arrange
        client_id = "custom_client"
        oauth_host = "https://custom.auth.com"
        auth_timeout = 600

        with (
            patch("src.auth.browser_auth.check_saved_credentials", return_value=None),
            patch("src.auth.browser_auth.authenticate") as mock_authenticate,
        ):
            new_token_set = TokenSetModel(
                access_token="custom_token", token_type="Bearer"
            )
            mock_authenticate.return_value = (True, new_token_set)

            # Act
            result = get_authentication_token(
                client_id=client_id, oauth_host=oauth_host, auth_timeout=auth_timeout
            )

            # Assert
            assert result == "custom_token"
            mock_authenticate.assert_called_once_with(
                client_id, oauth_host, auth_timeout
            )
