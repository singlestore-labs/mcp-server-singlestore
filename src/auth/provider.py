import base64
import hashlib
import secrets
import time
import requests
import singlestoredb as s2
import json

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

from src.config.config import RemoteSettings, get_settings, set_user_id


class SingleStoreOAuthProvider(OAuthAuthorizationServerProvider):
    """Simple SingleStore OAuth provider with essential functionality."""

    def __init__(self, settings: RemoteSettings):
        self.settings = settings

        # In-memory state mapping for short-lived state (not persisted)
        self.state_mapping: dict[str, dict[str, str]] = {}

        # Ensure tables exist from external SQL file
        self._ensure_tables()

    def _get_conn(self):
        return s2.connect(self.settings.oauth_db_url)

    def _ensure_tables(self):
        schema_path = __import__("os").path.join(
            __import__("os").path.dirname(__file__), "oauth_schema.sql"
        )
        with open(schema_path, "r") as f:
            sql = f.read()
        stmts = [stmt.strip() for stmt in sql.split(";") if stmt.strip()]
        with self._get_conn() as conn:
            cur = conn.cursor()
            for stmt in stmts:
                cur.execute(stmt)
            conn.commit()

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT client_info FROM oauth_clients WHERE client_id=%s", (client_id,)
            )
            row = cur.fetchone()
            if row:
                val = row[0]
                if isinstance(val, dict):
                    return OAuthClientInformationFull.model_validate(val)
                else:
                    return OAuthClientInformationFull.parse_raw(val)
        return None

    async def register_client(self, client_info: OAuthClientInformationFull):

        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "REPLACE INTO oauth_clients (client_id, client_info) VALUES (%s, %s)",
                (client_info.client_id, client_info.json()),
            )
            conn.commit()

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
            scopes=[self.settings.required_scopes[0]],
            code_challenge=code_challenge,
        )
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "REPLACE INTO oauth_auth_codes (code, client_id, redirect_uri, redirect_uri_provided_explicitly, expires_at, scopes, code_challenge) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    new_code,
                    client_id,
                    redirect_uri,
                    redirect_uri_provided_explicitly,
                    int(auth_code.expires_at),
                    json.dumps(auth_code.scopes),
                    code_challenge,
                ),
            )
            conn.commit()

        del self.state_mapping[state]
        return construct_redirect_uri(redirect_uri, code=new_code, state=state)

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT client_id, redirect_uri, redirect_uri_provided_explicitly, expires_at, scopes, code_challenge FROM oauth_auth_codes WHERE code=%s",
                (authorization_code,),
            )
            row = cur.fetchone()
            if row:
                import json

                scopes = row[4]
                if isinstance(scopes, str):
                    scopes = json.loads(scopes)
                return AuthorizationCode(
                    code=authorization_code,
                    client_id=row[0],
                    redirect_uri=AnyHttpUrl(row[1]),
                    redirect_uri_provided_explicitly=row[2],
                    expires_at=row[3],
                    scopes=scopes,
                    code_challenge=row[5],
                )
        return None

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        import json

        # Check if code exists in DB
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT code FROM oauth_auth_codes WHERE code=%s",
                (authorization_code.code,),
            )
            if not cur.fetchone():
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

        # Store MCP token in DB
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "REPLACE INTO oauth_tokens (token, client_id, scopes, expires_at) VALUES (%s, %s, %s, %s)",
                (
                    mcp_token,
                    client.client_id,
                    json.dumps(authorization_code.scopes),
                    int(time.time()) + expires_in,
                ),
            )
            conn.commit()

        # Store mapping between MCP token and SingleStore token (if needed)
        # For now, just map MCP token to itself
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "REPLACE INTO oauth_token_mapping (mcp_token, singlestore_token) VALUES (%s, %s)",
                (mcp_token, mcp_token),
            )
            conn.commit()

        # Remove used code from DB
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM oauth_auth_codes WHERE code=%s", (authorization_code.code,)
            )
            conn.commit()

        if hasattr(self, "singlestore_code_verifier"):
            del self.singlestore_code_verifier

        return OAuthToken(
            access_token=mcp_token,
            token_type="bearer",
            expires_in=expires_in,
            scope=" ".join(authorization_code.scopes),
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        import json

        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT client_id, scopes, expires_at FROM oauth_tokens WHERE token=%s",
                (token,),
            )
            row = cur.fetchone()
            if not row:
                return None
            client_id, scopes, expires_at = row
            if expires_at and expires_at < time.time():
                # Expired, remove
                cur.execute("DELETE FROM oauth_tokens WHERE token=%s", (token,))
                conn.commit()
                return None
            if isinstance(scopes, str):
                scopes = json.loads(scopes)

            settings = get_settings()

            # Fetch the client name from the client information
            client_info = await self.get_client(client_id)
            if client_info:
                client_name = client_info.client_name
            else:
                # If client information is not found, use a default name
                client_name = "Unknown Client"

            user_id = self.__get_user_id(token)
            settings.analytics_manager.identify(
                user_id=user_id,
                traits={
                    "client_id": client_id,
                    "client_name": client_name,
                    "scopes": scopes,
                    "expires_at": expires_at,
                },
            )

            set_user_id(user_id)

            return AccessToken(
                token=token,
                client_id=client_id,
                scopes=scopes,
                expires_at=expires_at,
            )

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
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM oauth_tokens WHERE token=%s", (token,))
            conn.commit()

    def __get_user_id(self, token: str) -> str | None:
        """Extract user ID from the token if available."""
        settings = get_settings()

        url = f"{settings.s2_api_base_url}/v1/users"

        # Headers with authentication
        headers = {
            "Content-Type": "application/json",
        }

        headers["Authorization"] = f"Bearer {token}"

        request = requests.get(
            url, headers=headers, params={"organizationID": settings.org_id}
        )

        if request.status_code != 200:
            raise HTTPException(request.status_code, request.text)

        try:
            users = request.json()
        except ValueError:
            raise ValueError(f"Invalid JSON response: {request.text}")

        if users and isinstance(users, list) and len(users) > 0:
            user_id = users[0].get("userID")
            if user_id:
                return user_id
