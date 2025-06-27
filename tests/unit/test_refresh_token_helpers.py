"""Unit tests for refresh token helper functions."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.auth.browser_auth import (
    validate_token_for_refresh,
    create_refresh_token_request,
    send_refresh_token_request,
    process_refresh_token_response,
    check_saved_credentials,
    attempt_token_refresh,
)
from tests.models import (
    TokenSetModel,
    TokenValidationResult,
    RefreshTokenRequest,
    OAuthServerConfig,
    TokenResponse,
    CredentialsModel,
)


class TestValidateTokenForRefresh:
    """Test cases for validate_token_for_refresh function."""

    def test_validate_token_valid_not_expired(self):
        """Test validation of valid, non-expired token."""
        # Arrange
        future_timestamp = int(datetime.now().timestamp()) + 3600
        token_set = TokenSetModel(
            access_token="valid_token",
            token_type="Bearer",
            refresh_token="refresh_123",
            expires_at=future_timestamp,
        )

        # Act
        result = validate_token_for_refresh(token_set)

        # Assert
        assert isinstance(result, TokenValidationResult)
        assert result.is_valid is True
        assert result.is_expired is False
        assert result.needs_refresh is False
        assert result.has_refresh_token is True

    def test_validate_token_expired_with_refresh(self):
        """Test validation of expired token with refresh token."""
        # Arrange
        past_timestamp = int(datetime.now().timestamp()) - 3600
        token_set = TokenSetModel(
            access_token="expired_token",
            token_type="Bearer",
            refresh_token="refresh_123",
            expires_at=past_timestamp,
        )

        # Act
        result = validate_token_for_refresh(token_set)

        # Assert
        assert result.is_valid is False
        assert result.is_expired is True
        assert result.needs_refresh is True
        assert result.has_refresh_token is True

    def test_validate_token_expired_without_refresh(self):
        """Test validation of expired token without refresh token."""
        # Arrange
        past_timestamp = int(datetime.now().timestamp()) - 3600
        token_set = TokenSetModel(
            access_token="expired_token", token_type="Bearer", expires_at=past_timestamp
        )

        # Act
        result = validate_token_for_refresh(token_set)

        # Assert
        assert result.is_valid is False
        assert result.is_expired is True
        assert result.needs_refresh is False
        assert result.has_refresh_token is False

    def test_validate_token_no_expiry(self):
        """Test validation of token without expiry."""
        # Arrange
        token_set = TokenSetModel(
            access_token="token_no_expiry",
            token_type="Bearer",
            refresh_token="refresh_123",
        )

        # Act
        result = validate_token_for_refresh(token_set)

        # Assert
        assert result.is_valid is True
        assert result.is_expired is False
        assert result.needs_refresh is False
        assert result.has_refresh_token is True


class TestCreateRefreshTokenRequest:
    """Test cases for create_refresh_token_request function."""

    def test_create_refresh_token_request_success(self):
        """Test successful refresh token request creation."""
        # Arrange
        token_set = TokenSetModel(
            access_token="access_123", token_type="Bearer", refresh_token="refresh_456"
        )
        client_id = "client_789"

        # Act
        result = create_refresh_token_request(token_set, client_id)

        # Assert
        assert isinstance(result, RefreshTokenRequest)
        assert result.grant_type == "refresh_token"
        assert result.refresh_token == "refresh_456"
        assert result.client_id == "client_789"

    def test_create_refresh_token_request_no_refresh_token(self):
        """Test refresh token request creation without refresh token."""
        # Arrange
        token_set = TokenSetModel(access_token="access_123", token_type="Bearer")
        client_id = "client_789"

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            create_refresh_token_request(token_set, client_id)
        assert "No refresh token available" in str(exc_info.value)


class TestSendRefreshTokenRequest:
    """Test cases for send_refresh_token_request function."""

    @patch("requests.post")
    def test_send_refresh_token_request_success(self, mock_post):
        """Test successful refresh token request."""
        # Arrange
        oauth_config = OAuthServerConfig(
            authorization_endpoint="https://auth.example.com/authorize",
            token_endpoint="https://auth.example.com/token",
        )
        refresh_request = RefreshTokenRequest(
            refresh_token="refresh_123", client_id="client_456"
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        # Act
        result = send_refresh_token_request(oauth_config, refresh_request)

        # Assert
        assert isinstance(result, TokenResponse)
        assert result.access_token == "new_access_token"
        assert result.token_type == "Bearer"
        assert result.expires_in == 3600

        # Verify HTTP request
        mock_post.assert_called_once_with(
            oauth_config.token_endpoint,
            data=refresh_request.model_dump(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )

    @patch("requests.post")
    def test_send_refresh_token_request_http_error(self, mock_post):
        """Test refresh token request with HTTP error."""
        # Arrange
        oauth_config = OAuthServerConfig(
            authorization_endpoint="https://auth.example.com/authorize",
            token_endpoint="https://auth.example.com/token",
        )
        refresh_request = RefreshTokenRequest(
            refresh_token="refresh_123", client_id="client_456"
        )

        mock_response = Mock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            send_refresh_token_request(oauth_config, refresh_request)
        assert "Token refresh failed with status 400" in str(exc_info.value)

    @patch("requests.post")
    def test_send_refresh_token_request_oauth_error(self, mock_post):
        """Test refresh token request with OAuth error."""
        # Arrange
        oauth_config = OAuthServerConfig(
            authorization_endpoint="https://auth.example.com/authorize",
            token_endpoint="https://auth.example.com/token",
        )
        refresh_request = RefreshTokenRequest(
            refresh_token="refresh_123", client_id="client_456"
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Refresh token expired",
        }
        mock_post.return_value = mock_response

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            send_refresh_token_request(oauth_config, refresh_request)
        assert "Token refresh error: Refresh token expired" in str(exc_info.value)

    @patch("requests.post")
    def test_send_refresh_token_request_no_access_token(self, mock_post):
        """Test refresh token request with missing access token."""
        # Arrange
        oauth_config = OAuthServerConfig(
            authorization_endpoint="https://auth.example.com/authorize",
            token_endpoint="https://auth.example.com/token",
        )
        refresh_request = RefreshTokenRequest(
            refresh_token="refresh_123", client_id="client_456"
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"token_type": "Bearer"}
        mock_post.return_value = mock_response

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            send_refresh_token_request(oauth_config, refresh_request)
        assert "No access token received from refresh" in str(exc_info.value)


class TestProcessRefreshTokenResponse:
    """Test cases for process_refresh_token_response function."""

    @patch("src.auth.browser_auth.save_credentials")
    @patch("src.auth.browser_auth.datetime")
    def test_process_refresh_token_response_success(self, mock_datetime, mock_save):
        """Test successful token response processing."""
        # Arrange
        mock_now = Mock()
        mock_now.timestamp.return_value = 1609459200.0
        mock_datetime.now.return_value = mock_now

        token_response = TokenResponse(
            access_token="new_access_token",
            token_type="Bearer",
            expires_in=3600,
            refresh_token="new_refresh_token",
        )

        # Act
        result = process_refresh_token_response(token_response)

        # Assert
        assert isinstance(result, TokenSetModel)
        assert result.access_token == "new_access_token"
        assert result.token_type == "Bearer"
        assert result.refresh_token == "new_refresh_token"
        assert result.expires_at == 1609462800  # 1609459200 + 3600

        # Verify save_credentials was called
        mock_save.assert_called_once_with(result)

    @patch("src.auth.browser_auth.save_credentials")
    def test_process_refresh_token_response_no_expires_in(self, mock_save):
        """Test token response processing without expires_in."""
        # Arrange
        token_response = TokenResponse(
            access_token="new_access_token",
            token_type="Bearer",
            refresh_token="new_refresh_token",
        )

        # Act
        result = process_refresh_token_response(token_response)

        # Assert
        assert isinstance(result, TokenSetModel)
        assert result.access_token == "new_access_token"
        assert result.expires_at is None

        mock_save.assert_called_once_with(result)


class TestCheckSavedCredentials:
    """Test cases for check_saved_credentials function."""

    @patch("src.auth.browser_auth.load_validated_credentials")
    def test_check_saved_credentials_success(self, mock_load):
        """Test successful credential loading."""
        # Arrange
        token_set = TokenSetModel(access_token="saved_token", token_type="Bearer")
        credentials = CredentialsModel(token_set=token_set, timestamp=1609459200)
        mock_load.return_value = credentials

        # Act
        result = check_saved_credentials()

        # Assert
        assert result == credentials
        mock_load.assert_called_once()

    @patch("src.auth.browser_auth.load_validated_credentials")
    def test_check_saved_credentials_no_credentials(self, mock_load):
        """Test credential loading with no saved credentials."""
        # Arrange
        mock_load.return_value = None

        # Act
        result = check_saved_credentials()

        # Assert
        assert result is None

    @patch("src.auth.browser_auth.load_validated_credentials")
    def test_check_saved_credentials_load_failure(self, mock_load):
        """Test credential loading with load failure."""
        # Arrange
        mock_load.side_effect = Exception("Load failed")

        # Act
        result = check_saved_credentials()

        # Assert
        assert result is None


class TestAttemptTokenRefresh:
    """Test cases for attempt_token_refresh function."""

    @patch("src.auth.browser_auth.refresh_token")
    @patch("src.auth.browser_auth.validate_token_for_refresh")
    def test_attempt_token_refresh_success(self, mock_validate, mock_refresh):
        """Test successful token refresh attempt."""
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

        refreshed_token = TokenSetModel(
            access_token="new_token", token_type="Bearer", refresh_token="new_refresh"
        )
        mock_refresh.return_value = refreshed_token

        # Act
        result = attempt_token_refresh(token_set, client_id, oauth_host)

        # Assert
        assert result == refreshed_token
        mock_validate.assert_called_once_with(token_set)
        mock_refresh.assert_called_once_with(token_set, client_id, oauth_host)

    @patch("src.auth.browser_auth.validate_token_for_refresh")
    def test_attempt_token_refresh_no_refresh_needed(self, mock_validate):
        """Test token refresh attempt when no refresh is needed."""
        # Arrange
        token_set = TokenSetModel(access_token="valid_token", token_type="Bearer")
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
        result = attempt_token_refresh(token_set, client_id, oauth_host)

        # Assert
        assert result is None
        mock_validate.assert_called_once_with(token_set)

    @patch("src.auth.browser_auth.refresh_token")
    @patch("src.auth.browser_auth.validate_token_for_refresh")
    def test_attempt_token_refresh_failure(self, mock_validate, mock_refresh):
        """Test token refresh attempt failure."""
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
        mock_refresh.return_value = None

        # Act
        result = attempt_token_refresh(token_set, client_id, oauth_host)

        # Assert
        assert result is None
        mock_validate.assert_called_once_with(token_set)
        mock_refresh.assert_called_once_with(token_set, client_id, oauth_host)
