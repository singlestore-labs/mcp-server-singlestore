"""
Shared test fixtures and configuration for remote authentication tests.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import time

from mcp.shared.auth import OAuthClientInformationFull
from mcp.server.auth.provider import AccessToken
from src.config.config import RemoteSettings


@pytest.fixture
def sample_oauth_client():
    """Create a sample OAuth client for testing."""
    return OAuthClientInformationFull(
        client_id="test-client-12345",
        client_name="Test OAuth Client",
        redirect_uris=["http://localhost:3000/callback", "http://localhost:8080/auth"],
    )


@pytest.fixture
def sample_access_token():
    """Create a sample access token for testing."""
    return AccessToken(
        token="sample-access-token-123",
        client_id="test-client-12345",
        scopes=["openid", "profile", "email"],
        expires_at=int(time.time()) + 3600,  # Expires in 1 hour
    )


@pytest.fixture
def expired_access_token():
    """Create an expired access token for testing."""
    return AccessToken(
        token="expired-access-token-123",
        client_id="test-client-12345",
        scopes=["openid", "profile"],
        expires_at=int(time.time()) - 3600,  # Expired 1 hour ago
    )


@pytest.fixture
def mock_database_connection():
    """Create a mock database connection and cursor."""
    mock_conn = Mock()
    mock_cursor = Mock()

    # Setup connection context manager
    mock_conn.__enter__ = Mock(return_value=mock_conn)
    mock_conn.__exit__ = Mock(return_value=None)
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.commit = Mock()

    # Setup cursor methods
    mock_cursor.execute = Mock()
    mock_cursor.fetchone = Mock()
    mock_cursor.fetchall = Mock()

    return mock_conn, mock_cursor


@pytest.fixture
def mock_remote_settings():
    """Create comprehensive mock RemoteSettings for testing."""
    settings = Mock(spec=RemoteSettings)
    settings.is_remote = True
    settings.auth_provider = None  # Add missing auth_provider attribute
    settings.client_id = "test-mcp-client-id"
    settings.org_id = "test-organization-id"
    settings.oauth_db_url = "mysql://test:test@localhost/test_oauth_db"
    settings.callback_path = "http://localhost:8010/oauth/callback"
    settings.required_scopes = ["openid", "profile", "email"]
    settings.singlestore_auth_url = "https://authsvc.singlestore.com/authorize"
    settings.singlestore_token_url = "https://authsvc.singlestore.com/token"
    settings.s2_api_base_url = "https://api.singlestore.com"
    settings.server_url = "http://localhost:8010"
    settings.issuer_url = "https://authsvc.singlestore.com"
    settings.segment_write_key = "test-segment-key"
    settings.jwt_signing_key = "test-jwt-signing-key-for-remote"

    # Mock auth provider
    settings.auth_provider = AsyncMock()

    # Mock analytics manager
    settings.analytics_manager = Mock()
    settings.analytics_manager.identify = Mock()
    settings.analytics_manager.track_event = Mock()

    return settings


@pytest.fixture
def mock_openid_configuration():
    """Create a mock OpenID Connect configuration response."""
    return {
        "issuer": "https://authsvc.singlestore.com",
        "authorization_endpoint": "https://authsvc.singlestore.com/authorize",
        "token_endpoint": "https://authsvc.singlestore.com/token",
        "jwks_uri": "https://authsvc.singlestore.com/.well-known/jwks.json",
        "userinfo_endpoint": "https://authsvc.singlestore.com/userinfo",
        "scopes_supported": ["openid", "profile", "email", "phone", "address"],
        "response_types_supported": ["code", "token", "id_token"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["plain", "S256"],
        "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post",
        ],
    }


@pytest.fixture
def mock_singlestore_token_response():
    """Create a mock token response from SingleStore OAuth."""
    return {
        "access_token": "singlestore_access_token_12345",
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": "singlestore_refresh_token_67890",
        "scope": "openid profile email",
    }


@pytest.fixture
def mock_singlestore_error_response():
    """Create a mock error response from SingleStore OAuth."""
    return {
        "error": "invalid_grant",
        "error_description": "The provided authorization grant is invalid, expired, revoked, or does not match the redirection URI.",
    }


@pytest.fixture
def mock_user_info_response():
    """Create a mock user info response from SingleStore API."""
    return [
        {
            "userID": "test-user-12345",
            "email": "test@example.com",
            "firstName": "Test",
            "lastName": "User",
            "organizationID": "test-organization-id",
        }
    ]


@pytest.fixture
def mock_http_requests():
    """Mock all HTTP requests made during testing."""
    with (
        patch("requests.get") as mock_get,
        patch("requests.post") as mock_post,
        patch("requests.put") as mock_put,
        patch("requests.patch") as mock_patch,
        patch("requests.delete") as mock_delete,
    ):
        yield {
            "get": mock_get,
            "post": mock_post,
            "put": mock_put,
            "patch": mock_patch,
            "delete": mock_delete,
        }


@pytest.fixture
def mock_fastmcp_context():
    """Create a mock FastMCP context for testing."""
    context = Mock()
    context.info = AsyncMock()
    context.error = AsyncMock()
    context.warning = AsyncMock()
    context.request_context = Mock()
    context.request_context.request = Mock()
    context.request_context.request.headers = {"Authorization": "Bearer test-token"}
    context.request_context.lifespan_context = {"org_id": "test-org-123"}
    return context


@pytest.fixture(autouse=True)
def reset_context_vars():
    """Reset context variables before each test to ensure isolation."""
    from src.config.config import _settings_ctx, _user_id_ctx, _app_ctx

    # Store original values
    original_settings = _settings_ctx.get(None)
    original_user_id = _user_id_ctx.get(None)
    original_app = _app_ctx.get(None)

    # Reset to None
    _settings_ctx.set(None)
    _user_id_ctx.set(None)
    _app_ctx.set(None)

    yield

    # Restore original values
    if original_settings is not None:
        _settings_ctx.set(original_settings)
    if original_user_id is not None:
        _user_id_ctx.set(original_user_id)
    if original_app is not None:
        _app_ctx.set(original_app)


class MockAsyncHttpClient:
    """Mock async HTTP client for testing."""

    def __init__(self, response_data=None, status_code=200, raise_exception=None):
        self.response_data = response_data or {}
        self.status_code = status_code
        self.raise_exception = raise_exception
        self.request_history = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def post(self, url, **kwargs):
        self.request_history.append({"method": "POST", "url": url, "kwargs": kwargs})

        if self.raise_exception:
            raise self.raise_exception

        response = AsyncMock()
        response.status_code = self.status_code
        response.json.return_value = self.response_data
        response.text = str(self.response_data)
        return response

    async def get(self, url, **kwargs):
        self.request_history.append({"method": "GET", "url": url, "kwargs": kwargs})

        if self.raise_exception:
            raise self.raise_exception

        response = AsyncMock()
        response.status_code = self.status_code
        response.json.return_value = self.response_data
        response.text = str(self.response_data)
        return response


@pytest.fixture
def mock_async_http_client():
    """Create a mock async HTTP client factory."""

    def create_client(response_data=None, status_code=200, raise_exception=None):
        return MockAsyncHttpClient(response_data, status_code, raise_exception)

    return create_client


# Common test data
VALID_JWT_PAYLOAD = {
    "client_id": "test-client-12345",
    "exp": int(time.time()) + 3600,  # Expires in 1 hour
    "iat": int(time.time()),
    "iss": "https://authsvc.singlestore.com",
    "aud": ["test-client-12345"],
    "sub": "test-user-12345",
    "scope": "openid profile email",
}

EXPIRED_JWT_PAYLOAD = {
    "client_id": "test-client-12345",
    "exp": int(time.time()) - 3600,  # Expired 1 hour ago
    "iat": int(time.time()) - 7200,  # Issued 2 hours ago
    "iss": "https://authsvc.singlestore.com",
    "aud": ["test-client-12345"],
    "sub": "test-user-12345",
    "scope": "openid profile email",
}


@pytest.fixture
def valid_jwt_payload():
    """Provide a valid JWT payload for testing."""
    return VALID_JWT_PAYLOAD.copy()


@pytest.fixture
def expired_jwt_payload():
    """Provide an expired JWT payload for testing."""
    return EXPIRED_JWT_PAYLOAD.copy()


@pytest.fixture
def mock_jwks_response():
    """Create a mock JWKS (JSON Web Key Set) response."""
    return {
        "keys": [
            {
                "kty": "EC",
                "use": "sig",
                "crv": "P-521",
                "kid": "test-key-id",
                "x": "test-x-coordinate",
                "y": "test-y-coordinate",
                "alg": "ES512",
            }
        ]
    }


# Test utilities
def create_mock_auth_code(client_id="test-client", code="test-code", expires_in=300):
    """Utility function to create mock authorization code data."""
    import json

    return [
        client_id,  # client_id
        "http://localhost:3000/callback",  # redirect_uri
        True,  # redirect_uri_provided_explicitly
        time.time() + expires_in,  # expires_at
        json.dumps(["openid", "profile", "email"]),  # scopes
        "test-code-challenge",  # code_challenge
    ]


def create_mock_token_data(client_id="test-client", expires_in=3600):
    """Utility function to create mock token data."""
    import json

    return [
        client_id,  # client_id
        json.dumps(["openid", "profile", "email"]),  # scopes
        time.time() + expires_in,  # expires_at
    ]


# Mark all tests as asyncio by default for async test functions
pytest_plugins = ["pytest_asyncio"]
