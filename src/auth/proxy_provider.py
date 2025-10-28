"""
SingleStore OAuth Proxy Provider with automatic configuration from OpenID Connect discovery.
"""

from urllib.parse import urljoin
import jwt
from jwt import PyJWKClient
import requests
from fastmcp.server.auth.oauth_proxy import OAuthProxy
from fastmcp.server.auth import TokenVerifier
from mcp.server.auth.provider import AccessToken


class SingleStoreOAuthProxy:
    """
    A consolidated OAuth proxy for SingleStore that automatically discovers
    endpoints from OpenID Connect configuration and provides JWT token verification.

    Args:
        issuer_url: The issuer URL for SingleStore's OAuth server, e.g.,
            "https://authsvc.singlestore.com/")
        client_id: OAuth client ID (defaults to SingleStore's MCP client ID)
        client_secret: OAuth client secret (defaults to "-")
        base_url: Your FastMCP server's public URL (defaults to "http://localhost:8010/")
        redirect_path: The callback path for OAuth (defaults to "/callback")
        valid_scopes: List of valid OAuth scopes (defaults to ["openid"])
        jwt_signing_key: Secret for signing FastMCP JWT tokens (defaults to the MCP_JWT_SIGNING_KEY env variable)
    """

    def __init__(
        self,
        issuer_url: str,
        client_id: str,
        client_secret: str = "-",
        base_url: str = "http://localhost:8010/",
        redirect_path: str | None = "/callback",
        valid_scopes: list[str] | None = None,
        jwt_signing_key: str | None = None,
    ):
        self.issuer_url = issuer_url
        # Assumes the default path for SingleStore's OpenID configuration
        self.openid_config_url = urljoin(
            issuer_url, "/.well-known/openid-configuration"
        )
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url
        self.redirect_path = redirect_path
        self.valid_scopes = valid_scopes or ["openid"]
        self.jwt_signing_key = jwt_signing_key

        # Fetch OpenID configuration
        self._config = self._fetch_openid_config()

        # Create the token verifier
        self._verifier = self._create_verifier()

        # Create the OAuth proxy
        self.provider = self._create_oauth_proxy()

    def _fetch_openid_config(self) -> dict:
        """Fetch the OpenID Connect configuration from the discovery endpoint."""
        try:
            response = requests.get(self.openid_config_url, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise RuntimeError(
                f"Failed to fetch OpenID configuration from {self.openid_config_url}: {e}"
            )

    def _create_verifier(self) -> TokenVerifier:
        """Create a custom JWT verifier using the OpenID configuration."""

        # Extract and validate required config values
        jwks_uri = self._config.get("jwks_uri")
        issuer = self._config.get("issuer")

        if not jwks_uri or not issuer:
            raise RuntimeError(
                "Missing required fields in OpenID configuration: "
                f"jwks_uri={jwks_uri}, issuer={issuer}"
            )

        class CustomJWTVerifier(TokenVerifier):
            def __init__(
                self,
                jwks_uri: str,
                issuer: str,
                audience: str,
                base_url: str | None = None,
                required_scopes: list[str] | None = None,
            ):
                super().__init__(base_url=base_url, required_scopes=required_scopes)
                self.jwks_uri = jwks_uri
                self.issuer = issuer
                self.audience = audience
                self.jwks_client = PyJWKClient(self.jwks_uri)

            async def verify_token(self, token: str) -> AccessToken | None:
                signing_key = self.jwks_client.get_signing_key_from_jwt(token)
                try:
                    decoded_token = jwt.decode(
                        token,
                        signing_key,
                        audience=self.audience,
                        options={"verify_exp": True},
                        algorithms=["ES512"],
                    )

                    return AccessToken(
                        token=token,
                        client_id=decoded_token.get("client_id"),
                        scopes=["openid"],
                        expires_at=decoded_token.get("exp"),
                        resource=decoded_token.get("aud")[0]
                        if isinstance(decoded_token.get("aud"), list)
                        else decoded_token.get("aud"),
                    )
                except jwt.PyJWTError as e:
                    print("Token validation error:", e)
                    return None
                except Exception as e:
                    print("Unexpected error during token validation:", e)
                    return None

        return CustomJWTVerifier(
            jwks_uri=jwks_uri,
            issuer=issuer,
            audience=self.client_id,
            base_url=self.base_url,
        )

    def _create_oauth_proxy(self) -> OAuthProxy:
        """Create the OAuth proxy with discovered endpoints."""
        # Extract and validate required config values
        authorization_endpoint = self._config.get("authorization_endpoint")
        token_endpoint = self._config.get("token_endpoint")

        if not authorization_endpoint or not token_endpoint:
            raise RuntimeError(
                "Missing required fields in OpenID configuration: "
                f"authorization_endpoint={authorization_endpoint}, token_endpoint={token_endpoint}"
            )

        if not self.jwt_signing_key:
            raise RuntimeError("JWT signing key is not set.")

        return OAuthProxy(
            upstream_authorization_endpoint=authorization_endpoint,
            upstream_token_endpoint=token_endpoint,
            upstream_client_id=self.client_id,
            upstream_client_secret=self.client_secret,
            token_verifier=self._verifier,
            base_url=self.base_url,
            redirect_path=self.redirect_path,
            valid_scopes=self.valid_scopes,
            jwt_signing_key=self.jwt_signing_key,
        )

    def get_provider(self) -> OAuthProxy:
        """Get the configured OAuth proxy provider."""
        return self.provider
