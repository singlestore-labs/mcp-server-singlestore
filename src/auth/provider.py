import base64
import hashlib
import secrets
import time

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    construct_redirect_uri,
)
from mcp.shared._httpx_utils import create_mcp_http_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from pydantic import AnyHttpUrl
from starlette.exceptions import HTTPException
from urllib.parse import urlencode

from src.config.config import RemoteSettings


class SingleStoreOAuthProvider(OAuthAuthorizationServerProvider):
    """Simple SingleStore OAuth provider with essential functionality."""

    def __init__(self, settings: RemoteSettings):
        self.settings = settings
        self.clients: dict[str, OAuthClientInformationFull] = {
            # Predefined client for SingleStore MCP server
            # Claude Desktop Client
            "e651c153-8cfb-43cf-aece-bf82cbe1b34d": OAuthClientInformationFull(
                client_id="b7dbf19e-d140-4334-bae4-e8cd03614485",
                client_name="Simple SingleStore MCP Server",
                redirect_uris=[AnyHttpUrl("http://localhost:18089/oauth/callback")],
                response_types=["code"],
                grant_types=["authorization_code", "refresh_token"],
            )
        }
        self.auth_codes: dict[str, AuthorizationCode] = {}
        self.tokens: dict[str, AccessToken] = {}
        self.state_mapping: dict[str, dict[str, str]] = {}
        # Store SingleStore tokens with MCP tokens using the format:
        # {"mcp_token": "singlestore_token"}
        self.token_mapping: dict[str, str] = {}

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        """Get OAuth client information."""
        return self.clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull):
        """Register a new OAuth client."""
        self.clients[client_info.client_id] = client_info

    def _generate_code_verifier(self) -> str:
        """Generate a code verifier for PKCE"""
        code_verifier = secrets.token_urlsafe(64)
        # Trim to appropriate length (43-128 chars)
        if len(code_verifier) > 128:
            code_verifier = code_verifier[:128]

        self.singlestore_code_verifier = code_verifier
        return code_verifier

    def _generate_code_challenge(self, code_verifier: str) -> str:
        """Generate a code challenge from the code verifier"""
        code_challenge = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = base64.urlsafe_b64encode(code_challenge).decode().rstrip("=")
        return code_challenge

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        """Generate an authorization URL for SingleStore OAuth flow."""
        state = params.state or secrets.token_hex(16)

        # Store the state mapping
        self.state_mapping[state] = {
            "code": state,  # Temporarily use state as code
            "state": state,
            "redirect_uri": str(params.redirect_uri),
            "code_challenge": params.code_challenge,
            "redirect_uri_provided_explicitly": str(
                params.redirect_uri_provided_explicitly
            ),
            "client_id": client.client_id,
        }

        # Generate PKCE code verifier and challenge for our own use with
        # SingleStore OAuth
        code_verifier = self._generate_code_verifier()
        code_challenge = self._generate_code_challenge(code_verifier)

        auth_params = {
            "client_id": self.settings.client_id,
            "redirect_uri": self.settings.callback_path,  # Our server's callback endpoint
            "response_type": "code",
            "scope": self.settings.required_scopes[0],  # Use the first scope
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        # Create the authorization URL for SingleStore OAuth
        auth_url = f"{self.settings.singlestore_auth_url}?{urlencode(auth_params)}"

        return auth_url

    async def handle_singlestore_callback(self, code: str, state: str) -> str:
        """Handle SingleStore OAuth callback."""
        state_data = self.state_mapping.get(state)
        if not state_data:
            raise HTTPException(400, "Invalid state parameter")

        redirect_uri = state_data["redirect_uri"]
        code_challenge = state_data["code_challenge"]
        redirect_uri_provided_explicitly = (
            state_data["redirect_uri_provided_explicitly"] == "True"
        )
        client_id = state_data["client_id"]

        # Create MCP authorization code
        new_code = code
        auth_code = AuthorizationCode(
            code=new_code,
            client_id=client_id,
            redirect_uri=AnyHttpUrl(redirect_uri),
            redirect_uri_provided_explicitly=redirect_uri_provided_explicitly,
            expires_at=time.time() + 300,
            scopes=[self.settings.required_scopes[0]],  # Use the first scope
            code_challenge=code_challenge,
        )
        self.auth_codes[new_code] = auth_code

        del self.state_mapping[state]
        return construct_redirect_uri(redirect_uri, code=new_code, state=state)

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        """Load an authorization code."""
        return self.auth_codes.get(authorization_code)

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        """Exchange authorization code for tokens."""
        if authorization_code.code not in self.auth_codes:
            raise ValueError("Invalid authorization code")

        data = None
        # Get the S2 token from the S2 authentication server
        async with create_mcp_http_client() as http_client:
            response = await http_client.post(
                self.settings.singlestore_token_url,
                params={
                    "grant_type": "authorization_code",
                    "code_verifier": self.singlestore_code_verifier,
                    "client_id": self.settings.client_id,
                },
                data={
                    "code": authorization_code.code,
                    "redirect_uri": self.settings.callback_path,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                print(
                    f"Failed to exchange code for token: {response.status_code} - {response.text}"
                )
                raise HTTPException(400, "Failed to exchange code for token")

            data = response.json()

            if "error" in data:
                raise HTTPException(400, data.get("error_description", data["error"]))

            mcp_token = data["access_token"]

        if not mcp_token:
            raise HTTPException(400, "No access token received from SingleStore")

        expires_in = data.get("expires_in", 3600)
        if expires_in <= 0:
            raise HTTPException(
                400, "Invalid expiration time received from SingleStore"
            )

        token_type: str = data.get("token_type")
        if token_type != "Bearer":
            raise HTTPException(400, "Unsupported token type received from SingleStore")

        # Store MCP token
        self.tokens[mcp_token] = AccessToken(
            token=mcp_token,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            expires_at=int(time.time()) + expires_in,
        )

        # Find SingleStore token for this client
        singlestore_token = next(
            (
                token
                for token, data in self.tokens.items()
                if data.client_id == client.client_id
            ),
            None,
        )

        # Store mapping between MCP token and SingleStore token
        if singlestore_token:
            self.token_mapping[mcp_token] = singlestore_token

        print(self.token_mapping)

        del self.singlestore_code_verifier  # Remove after use
        del self.auth_codes[authorization_code.code]

        return OAuthToken(
            access_token=mcp_token,
            token_type="bearer",
            expires_in=expires_in,
            scope=" ".join(authorization_code.scopes),
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        """Load and validate an access token."""
        access_token = self.tokens.get(token)
        print(f"Loading access token: {token} -> {access_token}")

        if not access_token:
            return None

        # Check if expired
        if access_token.expires_at and access_token.expires_at < time.time():
            del self.tokens[token]
            return None

        return access_token

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        """Load a refresh token - not supported."""
        return None

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        """Exchange refresh token"""
        raise NotImplementedError("Not supported")

    async def revoke_token(
        self, token: str, token_type_hint: str | None = None
    ) -> None:
        """Revoke a token."""
        if token in self.tokens:
            del self.tokens[token]
