from typing import Dict, Any, List
from pydantic import AnyHttpUrl
from mcp.server.auth.settings import AuthSettings, RevocationOptions, ClientRegistrationOptions

from src.config.config import OAUTH_HOST
from src.config.config import CLIENT_URI

# Define authentication settings for OAuth server
auth_settings = AuthSettings(
    issuer_url=OAUTH_HOST,
    audience=CLIENT_URI,  # The intended recipient of the tokens
    jwt_config={
        "algorithm": "RS256",
        "private_key_path": None,  # Path to private key if using a file-based key
        "public_key_path": None,   # Path to public key if using a file-based key
        "private_key": None,       # Or provide the key directly
        "public_key": None,        # Or provide the key directly
    },
    token_expires_in=3600,  # 1 hour
    refresh_token_expires_in=30 * 24 * 3600,  # 30 days
    authorization_code_expires_in=600,  # 10 minutes
    revocation_options=RevocationOptions(
        enabled=True,  # Enable token revocation
        revoke_refresh_token_with_access=True,  # Revoke refresh token when access token is revoked
    ),
    client_registration_options=ClientRegistrationOptions(
        enabled=True,
        valid_scopes=["api", "admin", "read", "write", "openid", "offline", "offline_access"],
        default_scopes=["api", "read", "openid"],
    ),
    required_scopes=["api"],  # Scopes required for access
    include_token_id=True,  # Include jti claim in tokens
    include_refresh_token=True,  # Include refresh tokens in token response
)
