"""
Test suite for remote mode OAuth authentication flow.

This module tests the complete remote authentication flow including:
- OAuth provider initialization
- Authorization code generation and exchange
- Token storage and retrieval
- Token validation and expiration
- Error handling scenarios
"""

import json
import time
import pytest
from unittest.mock import Mock, AsyncMock, patch

from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from mcp.server.auth.provider import AuthorizationCode, AuthorizationParams, AccessToken
from pydantic import AnyHttpUrl
from starlette.exceptions import HTTPException

from src.auth.provider import SingleStoreOAuthProvider
from src.config.config import RemoteSettings


class TestSingleStoreOAuthProvider:
    """Test cases for the SingleStoreOAuthProvider class."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock RemoteSettings for testing."""
        settings = Mock(spec=RemoteSettings)
        settings.client_id = "test-client-id"
        settings.org_id = "test-org-id"
        settings.oauth_db_url = "mysql://test:test@localhost/test_oauth"
        settings.callback_path = "http://localhost:8010/callback"
        settings.required_scopes = ["openid", "profile"]
        settings.singlestore_auth_url = "https://auth.singlestore.com/authorize"
        settings.singlestore_token_url = "https://auth.singlestore.com/token"
        settings.s2_api_base_url = "https://api.singlestore.com"
        return settings

    @pytest.fixture
    def mock_db_connection(self):
        """Mock database connection and cursor."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        return mock_conn, mock_cursor

    @pytest.fixture
    def oauth_provider(self, mock_settings, mock_db_connection):
        """Create OAuth provider instance with mocked dependencies."""
        mock_conn, mock_cursor = mock_db_connection

        with patch.object(SingleStoreOAuthProvider, "_ensure_tables"):
            provider = SingleStoreOAuthProvider(mock_settings)
            provider._mock_conn = mock_conn
            provider._mock_cursor = mock_cursor

            # Mock the _get_conn method to return our mock connection
            provider._get_conn = lambda: mock_conn

            return provider

    @pytest.fixture
    def sample_client(self):
        """Create a sample OAuth client for testing."""
        return OAuthClientInformationFull(
            client_id="test-client-123",
            client_name="Test Client",
            redirect_uris=["http://localhost:3000/callback"],
        )

    def test_provider_initialization(self, mock_settings):
        """Test that the OAuth provider initializes correctly."""
        with patch.object(SingleStoreOAuthProvider, "_ensure_tables") as mock_ensure:
            provider = SingleStoreOAuthProvider(mock_settings)

            assert provider.settings == mock_settings
            assert isinstance(provider.state_mapping, dict)
            mock_ensure.assert_called_once()

    def test_ensure_tables_creates_schema(self, oauth_provider):
        """Test that database tables are created properly."""
        with patch("builtins.open") as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = """
                CREATE TABLE oauth_clients (client_id VARCHAR(255) PRIMARY KEY);
                CREATE TABLE oauth_tokens (token VARCHAR(255) PRIMARY KEY);
            """
            with patch.object(oauth_provider, "_get_conn") as mock_get_conn:
                mock_get_conn.return_value = oauth_provider._mock_conn

                oauth_provider._ensure_tables()

                # Should execute SQL statements
                oauth_provider._mock_cursor.execute.assert_called()

    @pytest.mark.asyncio
    async def test_get_client_existing(self, oauth_provider, sample_client):
        """Test retrieving an existing client from database."""
        # Mock database response
        oauth_provider._mock_cursor.fetchone.return_value = [
            sample_client.model_dump_json()
        ]

        result = await oauth_provider.get_client("test-client-123")

        assert result is not None
        assert result.client_id == "test-client-123"
        oauth_provider._mock_cursor.execute.assert_called_with(
            "SELECT client_info FROM oauth_clients WHERE client_id=%s",
            ("test-client-123",),
        )

    @pytest.mark.asyncio
    async def test_get_client_not_found(self, oauth_provider):
        """Test retrieving a non-existent client."""
        oauth_provider._mock_cursor.fetchone.return_value = None

        result = await oauth_provider.get_client("nonexistent-client")

        assert result is None

    @pytest.mark.asyncio
    async def test_register_client(self, oauth_provider, sample_client):
        """Test registering a new client."""
        await oauth_provider.register_client(sample_client)

        oauth_provider._mock_cursor.execute.assert_called_with(
            "REPLACE INTO oauth_clients (client_id, client_info) VALUES (%s, %s)",
            (sample_client.client_id, sample_client.model_dump_json()),
        )
        oauth_provider._mock_conn.commit.assert_called_once()

    def test_generate_code_verifier(self, oauth_provider):
        """Test PKCE code verifier generation."""
        code_verifier = oauth_provider._generate_code_verifier()

        assert isinstance(code_verifier, str)
        assert 43 <= len(code_verifier) <= 128
        assert hasattr(oauth_provider, "singlestore_code_verifier")
        assert oauth_provider.singlestore_code_verifier == code_verifier

    def test_generate_code_challenge(self, oauth_provider):
        """Test PKCE code challenge generation."""
        code_verifier = "test_code_verifier"
        code_challenge = oauth_provider._generate_code_challenge(code_verifier)

        assert isinstance(code_challenge, str)
        assert len(code_challenge) > 0
        # Base64 URL-safe encoded SHA256 hash should not have padding
        assert "=" not in code_challenge

    @pytest.mark.asyncio
    async def test_authorize_creates_auth_url(self, oauth_provider, sample_client):
        """Test that authorization creates proper SingleStore OAuth URL."""
        params = AuthorizationParams(
            state="test-state",
            scopes=["openid", "profile"],
            code_challenge="test-challenge",
            redirect_uri=AnyHttpUrl("http://localhost:3000/callback"),
            redirect_uri_provided_explicitly=True,
        )

        auth_url = await oauth_provider.authorize(sample_client, params)

        assert auth_url.startswith(oauth_provider.settings.singlestore_auth_url)
        assert "client_id=" + oauth_provider.settings.client_id in auth_url
        assert "redirect_uri=" in auth_url
        assert "code_challenge=" in auth_url
        assert "state=" in auth_url

        # Check that state mapping was created
        state_key = list(oauth_provider.state_mapping.keys())[0]
        assert (
            oauth_provider.state_mapping[state_key]["client_id"]
            == sample_client.client_id
        )

    @pytest.mark.asyncio
    async def test_handle_singlestore_callback(self, oauth_provider, sample_client):
        """Test handling callback from SingleStore OAuth."""
        # Set up state mapping
        test_state = "test-state-123"
        oauth_provider.state_mapping[test_state] = {
            "code": "test-code",
            "state": test_state,
            "redirect_uri": "http://localhost:3000/callback",
            "code_challenge": "test-challenge",
            "redirect_uri_provided_explicitly": "True",
            "client_id": sample_client.client_id,
        }

        redirect_url = await oauth_provider.handle_singlestore_callback(
            "auth-code-123", test_state
        )

        # Should store authorization code in database
        oauth_provider._mock_cursor.execute.assert_called()
        oauth_provider._mock_conn.commit.assert_called()

        # Should return redirect URL with code and state
        assert "code=auth-code-123" in redirect_url
        assert "state=" + test_state in redirect_url

        # Should clean up state mapping
        assert test_state not in oauth_provider.state_mapping

    @pytest.mark.asyncio
    async def test_handle_callback_invalid_state(self, oauth_provider):
        """Test handling callback with invalid state."""
        with pytest.raises(HTTPException) as exc_info:
            await oauth_provider.handle_singlestore_callback(
                "auth-code", "invalid-state"
            )

        assert exc_info.value.status_code == 400
        assert "Invalid state parameter" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_load_authorization_code(self, oauth_provider, sample_client):
        """Test loading authorization code from database."""
        # Mock database response
        oauth_provider._mock_cursor.fetchone.return_value = [
            sample_client.client_id,  # client_id
            "http://localhost:3000/callback",  # redirect_uri
            True,  # redirect_uri_provided_explicitly
            time.time() + 300,  # expires_at
            json.dumps(["openid", "profile"]),  # scopes
            "test-challenge",  # code_challenge
        ]

        auth_code = await oauth_provider.load_authorization_code(
            sample_client, "test-code"
        )

        assert auth_code is not None
        assert auth_code.code == "test-code"
        assert auth_code.client_id == sample_client.client_id
        assert auth_code.scopes == ["openid", "profile"]

        oauth_provider._mock_cursor.execute.assert_called_with(
            "SELECT client_id, redirect_uri, redirect_uri_provided_explicitly, expires_at, scopes, code_challenge FROM oauth_auth_codes WHERE code=%s",
            ("test-code",),
        )

    @pytest.mark.asyncio
    async def test_load_authorization_code_not_found(
        self, oauth_provider, sample_client
    ):
        """Test loading non-existent authorization code."""
        oauth_provider._mock_cursor.fetchone.return_value = None

        auth_code = await oauth_provider.load_authorization_code(
            sample_client, "nonexistent-code"
        )

        assert auth_code is None

    @patch("src.auth.provider.create_mcp_http_client")
    @pytest.mark.asyncio
    async def test_exchange_authorization_code_success(
        self, mock_http_client, oauth_provider, sample_client
    ):
        """Test successful authorization code exchange."""
        # Mock database check for code existence
        oauth_provider._mock_cursor.fetchone.return_value = ["test-code"]

        # Mock HTTP client response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "access-token-123",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_http_client.return_value.__aenter__.return_value = mock_client

        # Create authorization code
        auth_code = AuthorizationCode(
            code="test-code",
            client_id=sample_client.client_id,
            redirect_uri=AnyHttpUrl("http://localhost:3000/callback"),
            redirect_uri_provided_explicitly=True,
            expires_at=time.time() + 300,
            scopes=["openid", "profile"],
            code_challenge="test-challenge",
        )

        oauth_provider.singlestore_code_verifier = "test-verifier"

        token = await oauth_provider.exchange_authorization_code(
            sample_client, auth_code
        )

        assert isinstance(token, OAuthToken)
        assert token.access_token == "access-token-123"
        assert token.token_type == "Bearer"
        assert token.expires_in == 3600

        # Should store token in database
        assert oauth_provider._mock_cursor.execute.call_count >= 2
        oauth_provider._mock_conn.commit.assert_called()

    @patch("src.auth.provider.create_mcp_http_client")
    @pytest.mark.asyncio
    async def test_exchange_authorization_code_invalid_code(
        self, mock_http_client, oauth_provider, sample_client
    ):
        """Test exchange with invalid authorization code."""
        # Mock database check - code not found
        oauth_provider._mock_cursor.fetchone.return_value = None

        auth_code = AuthorizationCode(
            code="invalid-code",
            client_id=sample_client.client_id,
            redirect_uri=AnyHttpUrl("http://localhost:3000/callback"),
            redirect_uri_provided_explicitly=True,
            expires_at=time.time() + 300,
            scopes=["openid", "profile"],
            code_challenge="test-challenge",
        )

        with pytest.raises(ValueError, match="Invalid authorization code"):
            await oauth_provider.exchange_authorization_code(sample_client, auth_code)

    @patch("src.auth.provider.create_mcp_http_client")
    @pytest.mark.asyncio
    async def test_exchange_authorization_code_singlestore_error(
        self, mock_http_client, oauth_provider, sample_client
    ):
        """Test exchange when SingleStore returns an error."""
        # Mock database check for code existence
        oauth_provider._mock_cursor.fetchone.return_value = ["test-code"]

        # Mock HTTP client error response
        mock_response = AsyncMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid request"

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_http_client.return_value.__aenter__.return_value = mock_client

        auth_code = AuthorizationCode(
            code="test-code",
            client_id=sample_client.client_id,
            redirect_uri=AnyHttpUrl("http://localhost:3000/callback"),
            redirect_uri_provided_explicitly=True,
            expires_at=time.time() + 300,
            scopes=["openid", "profile"],
            code_challenge="test-challenge",
        )

        oauth_provider.singlestore_code_verifier = "test-verifier"

        with pytest.raises(HTTPException) as exc_info:
            await oauth_provider.exchange_authorization_code(sample_client, auth_code)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_load_access_token_valid(self, oauth_provider):
        """Test loading a valid access token."""
        future_time = int(time.time() + 3600)  # Convert to int
        oauth_provider._mock_cursor.fetchone.return_value = [
            "test-client-id",  # client_id
            json.dumps(["openid", "profile"]),  # scopes
            future_time,  # expires_at
        ]

        with patch.object(oauth_provider, "get_client") as mock_get_client:
            mock_client = Mock()
            mock_client.client_name = "Test Client"
            mock_get_client.return_value = mock_client

            with patch.object(oauth_provider, "get_user_id", return_value="user-123"):
                with patch("src.auth.provider.get_settings") as mock_get_settings:
                    mock_settings = Mock()
                    mock_settings.analytics_manager.identify = Mock()
                    mock_get_settings.return_value = mock_settings

                    access_token = await oauth_provider.load_access_token("valid-token")

        assert access_token is not None
        assert isinstance(access_token, AccessToken)
        assert access_token.token == "valid-token"
        assert access_token.client_id == "test-client-id"
        assert access_token.scopes == ["openid", "profile"]
        assert access_token.expires_at == future_time

    @pytest.mark.asyncio
    async def test_load_access_token_not_found(self, oauth_provider):
        """Test loading non-existent access token."""
        oauth_provider._mock_cursor.fetchone.return_value = None

        access_token = await oauth_provider.load_access_token("nonexistent-token")

        assert access_token is None

    @pytest.mark.asyncio
    async def test_load_access_token_expired(self, oauth_provider):
        """Test loading expired access token."""
        past_time = time.time() - 3600
        oauth_provider._mock_cursor.fetchone.return_value = [
            "test-client-id",
            json.dumps(["openid", "profile"]),
            past_time,
        ]

        access_token = await oauth_provider.load_access_token("expired-token")

        assert access_token is None
        # Should delete expired token
        oauth_provider._mock_cursor.execute.assert_called_with(
            "DELETE FROM oauth_tokens WHERE token=%s", ("expired-token",)
        )

    @pytest.mark.asyncio
    async def test_revoke_token(self, oauth_provider):
        """Test token revocation."""
        await oauth_provider.revoke_token("token-to-revoke")

        oauth_provider._mock_cursor.execute.assert_called_with(
            "DELETE FROM oauth_tokens WHERE token=%s", ("token-to-revoke",)
        )
        oauth_provider._mock_conn.commit.assert_called_once()

    @patch("src.auth.provider.requests.get")
    def test_get_user_id_success(self, mock_get, oauth_provider):
        """Test successful user ID extraction."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"userID": "user-123", "email": "test@example.com"}
        ]
        mock_get.return_value = mock_response

        with patch("src.auth.provider.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.s2_api_base_url = "https://api.singlestore.com"
            mock_settings.org_id = "org-123"
            mock_get_settings.return_value = mock_settings

            user_id = oauth_provider.get_user_id("valid-token")

        assert user_id == "user-123"
        mock_get.assert_called_once()

    @patch("src.auth.provider.requests.get")
    def test_get_user_id_api_error(self, mock_get, oauth_provider):
        """Test user ID extraction with API error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response

        with patch("src.auth.provider.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.s2_api_base_url = "https://api.singlestore.com"
            mock_settings.org_id = "org-123"
            mock_get_settings.return_value = mock_settings

            with pytest.raises(HTTPException) as exc_info:
                oauth_provider.get_user_id("invalid-token")

            assert exc_info.value.status_code == 401


class TestRemoteAuthFlowIntegration:
    """Integration tests for the complete remote auth flow."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for integration tests."""
        settings = Mock(spec=RemoteSettings)
        settings.client_id = "integration-client-id"
        settings.org_id = "integration-org-id"
        settings.oauth_db_url = "mysql://test:test@localhost/integration_test"
        settings.callback_path = "http://localhost:8010/callback"
        settings.required_scopes = ["openid", "profile", "email"]
        settings.singlestore_auth_url = "https://auth.singlestore.com/authorize"
        settings.singlestore_token_url = "https://auth.singlestore.com/token"
        settings.s2_api_base_url = "https://api.singlestore.com"
        return settings

    @pytest.fixture
    def sample_client(self):
        """Create sample client for integration tests."""
        return OAuthClientInformationFull(
            client_id="integration-client-123",
            client_name="Integration Test Client",
            redirect_uris=["http://localhost:3000/callback"],
        )

    @patch("src.auth.provider.s2.connect")
    @patch("src.auth.provider.create_mcp_http_client")
    @patch("src.auth.provider.requests.get")
    @pytest.mark.asyncio
    async def test_complete_auth_flow_success(
        self,
        mock_requests_get,
        mock_http_client,
        mock_s2_connect,
        mock_settings,
        sample_client,
    ):
        """Test the complete authentication flow from start to finish."""
        # Setup mocks
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        mock_s2_connect.return_value = mock_conn

        # Mock SingleStore token exchange
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "singlestore-access-token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_http_client.return_value.__aenter__.return_value = mock_client

        # Mock user API response
        mock_user_response = Mock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = [{"userID": "test-user-123"}]
        mock_requests_get.return_value = mock_user_response

        # Initialize provider
        with patch.object(SingleStoreOAuthProvider, "_ensure_tables"):
            provider = SingleStoreOAuthProvider(mock_settings)

        # Step 1: Register client
        await provider.register_client(sample_client)

        # Step 2: Generate authorization URL
        params = AuthorizationParams(
            state="integration-test-state",
            scopes=["openid", "profile", "email"],
            code_challenge="test-challenge-integration",
            redirect_uri=AnyHttpUrl("http://localhost:3000/callback"),
            redirect_uri_provided_explicitly=True,
        )

        auth_url = await provider.authorize(sample_client, params)
        assert "https://auth.singlestore.com/authorize" in auth_url

        # Step 3: Handle callback from SingleStore
        test_state = list(provider.state_mapping.keys())[0]
        redirect_url = await provider.handle_singlestore_callback(
            "singlestore-auth-code", test_state
        )
        assert "code=singlestore-auth-code" in redirect_url

        # Step 4: Exchange authorization code for token
        # Mock code exists in DB - reset mock for this step
        mock_cursor.fetchone.side_effect = None
        mock_cursor.fetchone.return_value = [
            sample_client.client_id,
            "http://localhost:3000/callback",
            True,
            time.time() + 300,
            json.dumps(["openid", "profile", "email"]),
            "test-challenge-integration",
        ]

        auth_code = await provider.load_authorization_code(
            sample_client, "singlestore-auth-code"
        )
        assert auth_code is not None

        provider.singlestore_code_verifier = "integration-verifier"
        token = await provider.exchange_authorization_code(sample_client, auth_code)

        assert token.access_token == "singlestore-access-token"
        assert token.token_type == "Bearer"
        assert token.expires_in == 3600

        # Step 5: Load and validate access token
        # Mock token lookup
        future_time = time.time() + 3600
        mock_cursor.fetchone.side_effect = [
            [
                sample_client.client_id,
                json.dumps(["openid", "profile", "email"]),
                future_time,
            ],  # Token lookup
            [sample_client.model_dump_json()],  # Client lookup
        ]

        with patch("src.auth.provider.get_settings") as mock_get_settings:
            mock_analytics = Mock()
            mock_analytics.analytics_manager.identify = Mock()
            mock_get_settings.return_value = mock_analytics

            with patch("src.auth.provider.set_user_id") as mock_set_user_id:
                access_token = await provider.load_access_token(
                    "singlestore-access-token"
                )

        assert access_token is not None
        assert access_token.token == "singlestore-access-token"
        assert access_token.client_id == sample_client.client_id

        # Verify user ID was extracted and set
        mock_set_user_id.assert_called_with("test-user-123")

    @patch("src.auth.provider.s2.connect")
    @pytest.mark.asyncio
    async def test_auth_flow_with_expired_tokens(self, mock_s2_connect, mock_settings):
        """Test auth flow behavior with expired tokens."""
        # Setup mocks
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        mock_s2_connect.return_value = mock_conn

        with patch.object(SingleStoreOAuthProvider, "_ensure_tables"):
            provider = SingleStoreOAuthProvider(mock_settings)

        # Mock expired token
        past_time = time.time() - 3600
        mock_cursor.fetchone.return_value = [
            "test-client",
            json.dumps(["openid"]),
            past_time,
        ]

        access_token = await provider.load_access_token("expired-token")

        # Should return None and delete expired token
        assert access_token is None
        mock_cursor.execute.assert_any_call(
            "DELETE FROM oauth_tokens WHERE token=%s", ("expired-token",)
        )

    @patch("src.auth.provider.s2.connect")
    @pytest.mark.asyncio
    async def test_error_handling_scenarios(self, mock_s2_connect, mock_settings):
        """Test various error scenarios in the auth flow."""
        # Setup mocks
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        mock_s2_connect.return_value = mock_conn

        with patch.object(SingleStoreOAuthProvider, "_ensure_tables"):
            provider = SingleStoreOAuthProvider(mock_settings)

        # Test 1: Invalid state in callback
        with pytest.raises(HTTPException, match="Invalid state parameter"):
            await provider.handle_singlestore_callback("code", "invalid-state")

        # Test 2: Non-existent authorization code
        mock_cursor.fetchone.return_value = None
        with pytest.raises(ValueError, match="Invalid authorization code"):
            auth_code = AuthorizationCode(
                code="nonexistent",
                client_id="test",
                redirect_uri=AnyHttpUrl("http://localhost/callback"),
                redirect_uri_provided_explicitly=True,
                expires_at=time.time() + 300,
                scopes=["openid"],
                code_challenge="challenge",
            )
            await provider.exchange_authorization_code(
                OAuthClientInformationFull(
                    client_id="test",
                    client_name="test",
                    redirect_uris=[AnyHttpUrl("http://localhost/callback")],
                ),
                auth_code,
            )
