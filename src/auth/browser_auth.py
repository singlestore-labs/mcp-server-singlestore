"""Browser-based OAuth authentication for local MCP server."""

import os
import json
import time
import webbrowser
import secrets
import base64
import hashlib
import http.server
import socketserver
import urllib.parse
import requests
import logging  # Keep for level constants (DEBUG, INFO) used in isEnabledFor() checks
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

# Import centralized logger
from src.auth.models.models import (
    CredentialsModel,
    TokenSetModel,
    OAuthServerConfig,
    PKCEData,
    AuthorizationParameters,
    CallbackParameters,
    TokenRequest,
    TokenResponse,
    RefreshTokenRequest,
    TokenValidationResult,
)
from src.logger import get_logger


# Get logger for this module
logger = get_logger()

ALWAYS_PRESENT_SCOPES = [
    "openid",
    "profile",
    "email",
    "phone",
    "address",
    "offline_access",
]

# Constants for file operations
CREDENTIALS_FOLDER = ".singlestore"
CREDENTIALS_FILE = "credentials.json"

# Default OAuth configuration
DEFAULT_OAUTH_HOST = "https://authsvc.singlestore.com"
DEFAULT_CLIENT_ID = "b7dbf19e-d140-4334-bae4-e8cd03614485"
DEFAULT_AUTH_TIMEOUT = 300  # 5 minutes


class AuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler to capture OAuth callback"""

    def __init__(self, *args, **kwargs):
        self.callback_params = None
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        """Silence the default logging"""
        pass

    def do_OPTIONS(self):
        """Handle OPTIONS requests (CORS preflight)"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Handle GET requests"""
        if not self.path.startswith("/callback"):
            self.send_response(404)
            self.end_headers()
            return

        parsed_path = urllib.parse.urlparse(self.path)
        self.callback_params = urllib.parse.parse_qs(parsed_path.query)

        # Convert multi-value dict to single value dict for auth process
        self.server.callback_params = {k: v[0] for k, v in self.callback_params.items()}

        # Send a simple response
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        # Load success page HTML from file
        try:
            success_page_path = Path(__file__).parent / "success_page.html"
            with open(success_page_path, "r", encoding="utf-8") as f:
                response = f.read()
        except Exception:
            # Fallback response if file cannot be read
            response = """
            <html>
            <head><title>Authentication Successful</title></head>
            <body>
                <h1>Authentication Successful</h1>
                <p>You have successfully authenticated with SingleStore.</p>
                <p>You can close this window now.</p>
            </body>
            </html>
            """

        self.wfile.write(response.encode())

        # Signal that we've received the callback
        self.server.received_callback = True


def generate_code_verifier() -> str:
    """Generate a code verifier for PKCE"""
    code_verifier = secrets.token_urlsafe(64)
    # Trim to appropriate length (43-128 chars)
    if len(code_verifier) > 128:
        code_verifier = code_verifier[:128]
    return code_verifier


def generate_code_challenge(code_verifier: str) -> str:
    """Generate a code challenge from the code verifier"""
    code_challenge = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode().rstrip("=")
    return code_challenge


def generate_state() -> str:
    """Generate a state parameter for OAuth flow"""
    return secrets.token_urlsafe(32)


def discover_oauth_server(oauth_host: str) -> Dict[str, Any]:
    """Discover OAuth server endpoints"""
    discovery_url = (
        f"{oauth_host}/auth/oidc/op/Customer/.well-known/openid-configuration"
    )
    try:
        response = requests.get(discovery_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise Exception(f"Failed to discover OAuth endpoints: {e}")


def load_validated_credentials() -> Optional[CredentialsModel]:
    """
    Load and validate authentication credentials from file.

    Returns:
        Validated CredentialsModel instance or None if not available or invalid
    """
    # Get home directory and construct credentials path
    home_dir = Path.home()
    credentials_dir = home_dir / CREDENTIALS_FOLDER
    credentials_path = credentials_dir / CREDENTIALS_FILE

    if not credentials_path.exists():
        return None

    try:
        # Read and parse the file
        with open(credentials_path, "r") as f:
            content = f.read().strip()
            if not content:
                return None
            raw_credentials = json.loads(content)

        # Validate structure using Pydantic
        return CredentialsModel.model_validate(raw_credentials)
    except Exception:
        return None


def save_credentials(token_set: TokenSetModel) -> None:
    """
    Save authentication token to credentials file.

    Args:
        token_set: OAuth token set
    """
    # Create credential data structure
    creds = {
        "token_set": token_set.model_dump(),
        "timestamp": time.time(),
    }

    # Get home directory and construct credentials path
    home_dir = Path.home()
    credentials_dir = home_dir / CREDENTIALS_FOLDER
    credentials_path = credentials_dir / CREDENTIALS_FILE

    # Ensure directory exists
    credentials_path.parent.mkdir(parents=True, exist_ok=True)

    # Write credentials to file with secure permissions
    with open(credentials_path, "w") as f:
        json.dump(creds, f, indent=2)

    # Set secure permissions (readable only by user)
    os.chmod(credentials_path, 0o600)


def refresh_token(
    token_set: TokenSetModel,
    client_id: str = DEFAULT_CLIENT_ID,
    oauth_host: str = DEFAULT_OAUTH_HOST,
) -> Optional[TokenSetModel]:
    """
    Refresh an OAuth token using the refresh token.

    Args:
        token_set: The token set containing the refresh token
        client_id: OAuth client ID
        oauth_host: OAuth server host

    Returns:
        A new token set or None if refresh failed
    """
    try:
        # Validate token set for refresh
        validation_result = validate_token_for_refresh(token_set)
        if not validation_result.has_refresh_token:
            logger.debug("No refresh token available")
            return None

        # Setup OAuth configuration
        oauth_config = setup_oauth_config(oauth_host)

        # Create refresh token request
        refresh_request = create_refresh_token_request(token_set, client_id)

        # Send refresh request
        token_response = send_refresh_token_request(oauth_config, refresh_request)

        # Process response and create new token set
        new_token_set = process_refresh_token_response(token_response)

        logger.info("Token refreshed successfully")
        return new_token_set

    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        return None


def authenticate(
    client_id: str = DEFAULT_CLIENT_ID,
    oauth_host: str = DEFAULT_OAUTH_HOST,
    auth_timeout: int = DEFAULT_AUTH_TIMEOUT,
) -> Tuple[bool, Optional[TokenSetModel]]:
    """
    Launch browser authentication flow and capture OAuth token.

    Args:
        client_id: OAuth client ID to use for authentication
        oauth_host: OAuth server host
        auth_timeout: Timeout in seconds for authentication

    Returns:
        Tuple of (success: bool, token_set: Optional[TokenSetModel])
    """
    try:
        oauth_config = setup_oauth_config(oauth_host)

        # Generate PKCE code verifier, challenge, and state
        pkce_data = generate_pkce_data()

        # Find an available port for the redirect server
        with socketserver.TCPServer(("127.0.0.1", 0), None) as s:
            port = s.server_address[1]

        # Redirect URI
        redirect_uri = f"http://127.0.0.1:{port}/callback"

        # Create server class with additional attributes
        class CallbackServer(socketserver.TCPServer):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.received_callback = False
                self.callback_params = None

        # Create a custom handler factory
        def handler(*args, **kwargs):
            return AuthCallbackHandler(*args, **kwargs)

        # Start a temporary web server to capture the callback
        with CallbackServer(("127.0.0.1", port), handler) as httpd:
            logger.debug(f"Starting temporary authentication server on port {port}")

            # Create OAuth authorization URL
            auth_url = create_authorization_url(
                oauth_config, pkce_data, client_id, redirect_uri
            )

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"Starting browser authentication with Client ID: {client_id}"
                )
                logger.debug(f"Redirect URI: {redirect_uri}")
                logger.debug(f"Auth URL: {auth_url}")

            # Open browser to auth URL
            logger.info("Opening browser for SingleStore authentication...")
            webbrowser.open(auth_url)

            if logger.isEnabledFor(logging.INFO):
                logger.info("If the browser doesn't open automatically, please visit:")
                logger.info(f"{auth_url}")

            # Wait for callback with timeout
            callback_params = wait_for_callback(httpd, auth_timeout)

            # Validate and process callback parameters
            code = validate_callback(callback_params, pkce_data.state)

            # Exchange authorization code for tokens
            token_set = exchange_code_for_tokens(
                oauth_config, code, pkce_data, client_id, redirect_uri
            )

            return True, token_set

    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        return False, None


def setup_oauth_config(oauth_host: str) -> OAuthServerConfig:
    """
    Discover and validate OAuth server endpoints.

    Args:
        oauth_host: OAuth server host

    Returns:
        Validated OAuth server configuration

    Raises:
        Exception: If OAuth server discovery fails or endpoints are invalid
    """
    logger.debug("Discovering OAuth server endpoints...")
    oauth_config = discover_oauth_server(oauth_host)

    # Validate the required endpoints exist
    authorization_endpoint = oauth_config.get("authorization_endpoint")
    token_endpoint = oauth_config.get("token_endpoint")

    if not authorization_endpoint or not token_endpoint:
        raise Exception(
            "Invalid OAuth server configuration - missing required endpoints"
        )

    return OAuthServerConfig(
        authorization_endpoint=authorization_endpoint, token_endpoint=token_endpoint
    )


def generate_pkce_data() -> PKCEData:
    """
    Generate PKCE code verifier, challenge, and state for OAuth flow.

    Returns:
        PKCEData containing code_verifier, code_challenge, and state
    """
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)
    state = generate_state()

    return PKCEData(
        code_verifier=code_verifier, code_challenge=code_challenge, state=state
    )


def create_authorization_url(
    oauth_config: OAuthServerConfig,
    pkce_data: PKCEData,
    client_id: str,
    redirect_uri: str,
) -> str:
    """
    Create OAuth authorization URL with all required parameters.

    Args:
        oauth_config: OAuth server configuration
        pkce_data: PKCE data (code challenge, state)
        client_id: OAuth client ID
        redirect_uri: Redirect URI for the callback

    Returns:
        Complete authorization URL
    """
    scopes = " ".join(ALWAYS_PRESENT_SCOPES)

    auth_params = AuthorizationParameters(
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scopes,
        state=pkce_data.state,
        code_challenge=pkce_data.code_challenge,
    )

    # Convert to URL parameters
    params_dict = auth_params.model_dump()
    auth_url = (
        f"{oauth_config.authorization_endpoint}?{urllib.parse.urlencode(params_dict)}"
    )

    return auth_url


def wait_for_callback(httpd, auth_timeout: int) -> CallbackParameters:
    """
    Wait for OAuth callback and return the parameters.

    Args:
        httpd: HTTP server instance
        auth_timeout: Timeout in seconds

    Returns:
        Callback parameters from the OAuth server

    Raises:
        Exception: If timeout occurs or no callback received
    """
    # Set timeout for each request
    httpd.timeout = 1

    # Serve until callback is received or timeout
    start_time = time.time()
    logger.debug(f"Waiting for authentication (timeout: {auth_timeout}s)...")

    while not httpd.received_callback:
        httpd.handle_request()
        elapsed = time.time() - start_time

        # Log progress every 30 seconds in debug mode
        if (
            logger.isEnabledFor(logging.DEBUG)
            and int(elapsed) % 30 == 0
            and elapsed > 0
        ):
            remaining = auth_timeout - elapsed
            if remaining > 0:
                logger.debug(f"Still waiting... ({remaining:.0f}s remaining)")

        if elapsed > auth_timeout:
            raise Exception("Authentication timed out")

    # Process callback parameters
    if not httpd.callback_params:
        raise Exception("No callback parameters received")

    return CallbackParameters.model_validate(httpd.callback_params)


def validate_callback(callback_params: CallbackParameters, expected_state: str) -> str:
    """
    Validate callback parameters and extract authorization code.

    Args:
        callback_params: Callback parameters from OAuth server
        expected_state: Expected state parameter value

    Returns:
        Authorization code

    Raises:
        Exception: If validation fails or error in callback
    """
    # Check for errors first (errors may not have state)
    if callback_params.error:
        error_description = callback_params.error_description or "Unknown error"
        raise Exception(
            f"Authorization failed: {callback_params.error} - {error_description}"
        )

    # Check state parameter
    if callback_params.state != expected_state:
        raise Exception("State parameter mismatch, possible CSRF attack")

    # Extract authorization code
    if not callback_params.code:
        raise Exception("No authorization code received")

    return callback_params.code


def exchange_code_for_tokens(
    oauth_config: OAuthServerConfig,
    code: str,
    pkce_data: PKCEData,
    client_id: str,
    redirect_uri: str,
) -> TokenSetModel:
    """
    Exchange authorization code for OAuth tokens.

    Args:
        oauth_config: OAuth server configuration
        code: Authorization code from callback
        pkce_data: PKCE data containing code_verifier
        client_id: OAuth client ID
        redirect_uri: Redirect URI used in authorization

    Returns:
        Token set with access token and other OAuth tokens

    Raises:
        Exception: If token exchange fails
    """
    logger.debug("Authorization code received, exchanging for tokens...")

    # Prepare token request
    token_request = TokenRequest(
        grant_type="authorization_code",
        code=code,
        redirect_uri=redirect_uri,
        client_id=client_id,
        code_verifier=pkce_data.code_verifier,
    )

    # Send token request
    response = requests.post(
        oauth_config.token_endpoint,
        data=token_request.model_dump(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )

    if response.status_code != 200:
        logger.error(f"Token exchange failed: {response.status_code}")
        logger.debug(f"Response: {response.text}")
        raise Exception(f"Token exchange failed with status {response.status_code}")

    # Parse token response
    token_response = TokenResponse.model_validate(response.json())

    if token_response.error:
        error_description = token_response.error_description or token_response.error
        raise Exception(f"Token exchange error: {error_description}")

    # Ensure we have required tokens
    if not token_response.access_token:
        raise Exception("No access token received from token exchange")

    # Add expires_at if we got expires_in
    token_data = token_response.model_dump(exclude_none=True)
    if token_response.expires_in and "expires_at" not in token_data:
        token_data["expires_at"] = int(
            datetime.now().timestamp() + token_response.expires_in
        )

    # Create and save token set
    token_set = TokenSetModel.model_validate(token_data)
    save_credentials(token_set)

    return token_set


def get_authentication_token(
    client_id: str = DEFAULT_CLIENT_ID,
    oauth_host: str = DEFAULT_OAUTH_HOST,
    auth_timeout: int = DEFAULT_AUTH_TIMEOUT,
    force_reauth: bool = False,
) -> Optional[str]:
    """
    Get authentication token for local MCP server.
    Checks saved credentials first, then launches browser auth if needed.

    Args:
        client_id: OAuth client ID to use for authentication
        oauth_host: OAuth server host
        auth_timeout: Timeout in seconds for authentication
        force_reauth: Force re-authentication even if valid token exists

    Returns:
        Access token if available, None otherwise
    """
    if not force_reauth:
        # Check saved credentials
        credentials = check_saved_credentials()
        if credentials and credentials.token_set:
            token_set = credentials.token_set
            validation_result = validate_token_for_refresh(token_set)

            # If token is valid, use it
            if validation_result.is_valid:
                logger.debug("Using saved authentication token")
                return token_set.access_token

            # If token needs refresh, try to refresh it
            if validation_result.needs_refresh:
                refreshed_token_set = attempt_token_refresh(
                    token_set, client_id, oauth_host
                )
                if refreshed_token_set:
                    return refreshed_token_set.access_token

        # If no valid credentials found, launch browser authentication
        logger.debug("No valid authentication token found")
        logger.debug("Starting browser-based authentication with SingleStore...")

    # Perform browser authentication
    success, token_set = authenticate(client_id, oauth_host, auth_timeout)

    if success and token_set and token_set.access_token:
        return token_set.access_token
    else:
        return None


def validate_token_for_refresh(token_set: TokenSetModel) -> TokenValidationResult:
    """
    Validate a token set to determine if refresh is needed or possible.

    Args:
        token_set: Token set to validate

    Returns:
        TokenValidationResult with validation status
    """
    has_refresh_token = bool(token_set.refresh_token)
    is_expired = token_set.is_expired()
    is_valid = bool(token_set.access_token) and not is_expired
    needs_refresh = is_expired and has_refresh_token

    return TokenValidationResult(
        is_valid=is_valid,
        is_expired=is_expired,
        needs_refresh=needs_refresh,
        has_refresh_token=has_refresh_token,
    )


def create_refresh_token_request(
    token_set: TokenSetModel, client_id: str
) -> RefreshTokenRequest:
    """
    Create a refresh token request from a token set.

    Args:
        token_set: Token set containing refresh token
        client_id: OAuth client ID

    Returns:
        Validated refresh token request

    Raises:
        Exception: If no refresh token is available
    """
    if not token_set.refresh_token:
        raise Exception("No refresh token available")

    return RefreshTokenRequest(
        refresh_token=token_set.refresh_token, client_id=client_id
    )


def send_refresh_token_request(
    oauth_config: OAuthServerConfig, refresh_request: RefreshTokenRequest
) -> TokenResponse:
    """
    Send refresh token request to OAuth server.

    Args:
        oauth_config: OAuth server configuration
        refresh_request: Refresh token request data

    Returns:
        Token response from server

    Raises:
        Exception: If refresh request fails
    """
    logger.debug(f"Refreshing token using endpoint: {oauth_config.token_endpoint}")

    # Send refresh token request
    response = requests.post(
        oauth_config.token_endpoint,
        data=refresh_request.model_dump(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )

    if response.status_code != 200:
        raise Exception(f"Token refresh failed with status {response.status_code}")

    # Parse and validate token response
    token_response = TokenResponse.model_validate(response.json())

    if token_response.error:
        error_description = token_response.error_description or token_response.error
        raise Exception(f"Token refresh error: {error_description}")

    if not token_response.access_token:
        raise Exception("No access token received from refresh")

    return token_response


def process_refresh_token_response(token_response: TokenResponse) -> TokenSetModel:
    """
    Process refresh token response and create new token set.

    Args:
        token_response: Token response from OAuth server

    Returns:
        New token set with refreshed tokens
    """
    # Add expires_at if we got expires_in
    token_data = token_response.model_dump(exclude_none=True)
    if token_response.expires_in and "expires_at" not in token_data:
        token_data["expires_at"] = int(
            datetime.now().timestamp() + token_response.expires_in
        )

    # Create and save new token set
    new_token_set = TokenSetModel.model_validate(token_data)
    save_credentials(new_token_set)

    return new_token_set


def check_saved_credentials() -> Optional[CredentialsModel]:
    """
    Check for saved credentials and validate them.

    Returns:
        Valid credentials if available, None otherwise
    """
    try:
        credentials = load_validated_credentials()
        if credentials and credentials.token_set:
            return credentials
    except Exception as e:
        logger.debug(f"Failed to load saved credentials: {e}")

    return None


def attempt_token_refresh(
    token_set: TokenSetModel, client_id: str, oauth_host: str
) -> Optional[TokenSetModel]:
    """
    Attempt to refresh an expired token.

    Args:
        token_set: Token set to refresh
        client_id: OAuth client ID
        oauth_host: OAuth server host

    Returns:
        Refreshed token set if successful, None otherwise
    """
    validation_result = validate_token_for_refresh(token_set)

    if not validation_result.needs_refresh:
        return None

    logger.debug("Access token expired, attempting to refresh...")

    try:
        refreshed_token_set = refresh_token(token_set, client_id, oauth_host)
        if refreshed_token_set:
            logger.debug("Token refreshed successfully")
            return refreshed_token_set
        else:
            logger.debug("Token refresh failed, proceeding to re-authentication")
            return None
    except Exception as e:
        logger.debug(f"Token refresh failed: {e}")
        return None
