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
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime


# Scopes that are always required
ALWAYS_PRESENT_SCOPES = [
    "openid",
    "profile",
    "email",
    "phone",
    "address",
    "offline_access",
]

# Credential file path
CREDENTIALS_FILE = Path.home() / ".singlestore-mcp-credentials.json"

# Default OAuth configuration
DEFAULT_OAUTH_HOST = "https://authsvc.singlestore.com"
DEFAULT_CLIENT_ID = "b7dbf19e-d140-4334-bae4-e8cd03614485"
DEFAULT_AUTH_TIMEOUT = 300  # 5 minutes


class TokenSet:
    """Class representing an OAuth token set"""

    def __init__(self, data: Dict[str, Any]):
        self.access_token = data.get("access_token")
        self.token_type = data.get("token_type")
        self.id_token = data.get("id_token")
        self.refresh_token = data.get("refresh_token")
        self.expires_at = data.get("expires_at")
        self.raw_data = data

    def is_expired(self) -> bool:
        """Check if the access token is expired"""
        if not self.expires_at:
            return True
        return datetime.now().timestamp() >= self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert token set to dictionary for serialization"""
        return self.raw_data


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

        # Success response HTML
        response = """
        <html>
        <head>
            <title>Authentication Successful</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                h1 { color: #4CAF50; }
                p { font-size: 16px; margin: 20px 0; }
                .success { color: #4CAF50; }
            </style>
        </head>
        <body>
            <h1>✓ Authentication Successful</h1>
            <p class="success">You have successfully authenticated with SingleStore.</p>
            <p>You can close this window now and return to your terminal.</p>
            <script>
                setTimeout(() => {
                    window.close();
                }, 3000);
            </script>
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


def save_credentials(token_set: TokenSet) -> None:
    """
    Save authentication token to credentials file.

    Args:
        token_set: OAuth token set
    """
    # Create credential data structure
    creds = {
        "token_set": token_set.to_dict(),
        "timestamp": time.time(),
    }

    # Ensure directory exists
    CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Write credentials to file with secure permissions
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(creds, f, indent=2)

    # Set secure permissions (readable only by user)
    os.chmod(CREDENTIALS_FILE, 0o600)
    print(f"Credentials saved to {CREDENTIALS_FILE}")


def load_credentials() -> Optional[Dict[str, Any]]:
    """
    Load authentication credentials from file.

    Returns:
        Dict containing credentials or None if not available
    """
    if not CREDENTIALS_FILE.exists():
        return None

    try:
        with open(CREDENTIALS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Failed to load credentials: {e}")
        return None


def refresh_token(
    token_set: TokenSet,
    client_id: str = DEFAULT_CLIENT_ID,
    oauth_host: str = DEFAULT_OAUTH_HOST,
) -> Optional[TokenSet]:
    """
    Refresh an OAuth token using the refresh token.

    Args:
        token_set: The token set containing the refresh token
        client_id: OAuth client ID
        oauth_host: OAuth server host

    Returns:
        A new token set or None if refresh failed
    """
    if not token_set.refresh_token:
        print("No refresh token available")
        return None

    try:
        # Discover OAuth server endpoints
        oauth_config = discover_oauth_server(oauth_host)
        token_endpoint = oauth_config.get("token_endpoint")

        if not token_endpoint:
            print("Invalid OAuth server configuration")
            return None

        # Prepare refresh token request
        data = {
            "grant_type": "refresh_token",
            "refresh_token": token_set.refresh_token,
            "client_id": client_id,
        }

        # Send refresh token request
        response = requests.post(
            token_endpoint,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        response.raise_for_status()

        # Parse token response
        token_data = response.json()

        # Add expires_at if we got expires_in
        if "expires_in" in token_data and "expires_at" not in token_data:
            token_data["expires_at"] = (
                datetime.now().timestamp() + token_data["expires_in"]
            )

        # Create new token set
        new_token_set = TokenSet(token_data)
        save_credentials(new_token_set)

        print("Token refreshed successfully")
        return new_token_set

    except Exception as e:
        print(f"Token refresh failed: {e}")
        return None


def authenticate(
    client_id: str = DEFAULT_CLIENT_ID,
    oauth_host: str = DEFAULT_OAUTH_HOST,
    auth_timeout: int = DEFAULT_AUTH_TIMEOUT,
) -> Tuple[bool, Optional[TokenSet]]:
    """
    Launch browser authentication flow and capture OAuth token.

    Args:
        client_id: OAuth client ID to use for authentication
        oauth_host: OAuth server host
        auth_timeout: Timeout in seconds for authentication

    Returns:
        Tuple of (success: bool, token_set: Optional[TokenSet])
    """
    try:
        # Discover OAuth server endpoints
        print("Discovering OAuth server endpoints...")
        oauth_config = discover_oauth_server(oauth_host)
        authorization_endpoint = oauth_config.get("authorization_endpoint")
        token_endpoint = oauth_config.get("token_endpoint")

        if not authorization_endpoint or not token_endpoint:
            print("Invalid OAuth server configuration")
            return False, None

        # Generate PKCE code verifier and challenge
        code_verifier = generate_code_verifier()
        code_challenge = generate_code_challenge(code_verifier)

        # Generate state for security
        state = generate_state()

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
            print(f"Starting temporary authentication server on port {port}...")

            # Prepare authorization URL
            scopes = " ".join(ALWAYS_PRESENT_SCOPES)
            auth_params = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": scopes,
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }

            auth_url = f"{authorization_endpoint}?{urllib.parse.urlencode(auth_params)}"

            print(f"\n{'=' * 60}")
            print("🚀 Starting browser authentication...")
            print(f"Client ID: {client_id}")
            print(f"Redirect URI: {redirect_uri}")
            print(f"{'=' * 60}")

            # Open browser to auth URL
            print("Opening browser for SingleStore authentication...")
            webbrowser.open(auth_url)

            print("If the browser doesn't open automatically, please visit:")
            print(f"{auth_url}")

            # Set timeout for each request
            httpd.timeout = 1

            # Serve until callback is received or timeout
            start_time = time.time()
            print(f"\nWaiting for authentication (timeout: {auth_timeout}s)...")

            while not httpd.received_callback:
                httpd.handle_request()
                elapsed = time.time() - start_time

                # Print progress every 30 seconds
                if int(elapsed) % 30 == 0 and elapsed > 0:
                    remaining = auth_timeout - elapsed
                    if remaining > 0:
                        print(f"Still waiting... ({remaining:.0f}s remaining)")

                if elapsed > auth_timeout:
                    print("\n❌ Authentication timed out")
                    print(
                        "Please try again or check your browser for any blocked popups."
                    )
                    return False, None

            # Process callback parameters
            if not httpd.callback_params:
                print("❌ No callback parameters received")
                return False, None

            # Check state parameter
            if httpd.callback_params.get("state") != state:
                print("❌ State parameter mismatch, possible CSRF attack")
                return False, None

            # Extract authorization code
            code = httpd.callback_params.get("code")
            if not code:
                error = httpd.callback_params.get("error")
                error_description = httpd.callback_params.get(
                    "error_description", "Unknown error"
                )
                print(f"❌ Authorization failed: {error} - {error_description}")
                return False, None

            print("✅ Authorization code received, exchanging for tokens...")

            # Exchange code for tokens
            token_data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "code_verifier": code_verifier,
            }

            # Send token request
            response = requests.post(
                token_endpoint,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )

            if response.status_code != 200:
                print(f"❌ Token exchange failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False, None

            # Parse token response
            token_response = response.json()

            if "error" in token_response:
                print(
                    f"❌ Token exchange error: {token_response.get('error_description', token_response['error'])}"
                )
                return False, None

            # Add expires_at if we got expires_in
            if "expires_in" in token_response and "expires_at" not in token_response:
                token_response["expires_at"] = (
                    datetime.now().timestamp() + token_response["expires_in"]
                )

            # Create token set
            token_set = TokenSet(token_response)
            save_credentials(token_set)

            print("✅ Authentication successful!")
            return True, token_set

    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False, None


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
        # Check saved credentials file
        credentials = load_credentials()
        if credentials and "token_set" in credentials:
            token_set = TokenSet(credentials["token_set"])

            # If token is expired, try to refresh it
            if token_set.is_expired() and token_set.refresh_token:
                print("Access token expired, attempting to refresh...")
                refreshed_token_set = refresh_token(token_set, client_id, oauth_host)
                if refreshed_token_set:
                    print("✅ Token refreshed successfully")
                    return refreshed_token_set.access_token
                else:
                    print("Token refresh failed, proceeding to re-authentication")

            # If we have a valid token, use it
            if not token_set.is_expired() and token_set.access_token:
                print("✅ Using saved authentication token")
                return token_set.access_token

    # If no valid credentials found, launch browser authentication
    print("\n🔐 No valid authentication token found")
    print("Starting browser-based authentication with SingleStore...")

    success, token_set = authenticate(client_id, oauth_host, auth_timeout)

    if success and token_set and token_set.access_token:
        print("🎉 Authentication completed successfully!")
        return token_set.access_token
    else:
        print("❌ Authentication failed")
        print("Please try again or check your network connection.")
        return None


def clear_credentials() -> bool:
    """
    Clear saved credentials.

    Returns:
        True if credentials were cleared, False if no credentials exist
    """
    if CREDENTIALS_FILE.exists():
        try:
            CREDENTIALS_FILE.unlink()
            print(f"✅ Credentials cleared from {CREDENTIALS_FILE}")
            return True
        except Exception as e:
            print(f"❌ Failed to clear credentials: {e}")
            return False
    else:
        print("No saved credentials found")
        return False
