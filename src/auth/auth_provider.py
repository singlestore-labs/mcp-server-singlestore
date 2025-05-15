"""
OAuth Authorization Server Provider for SingleStore MCP Server.
This module provides the implementation of the OAuth 2.1/OpenID Connect
authentication server functionality for the SingleStore MCP server.
"""

import time
from typing import Dict, List, Optional
from urllib.parse import urlencode
import secrets
import hashlib
import base64

from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    TokenError,
    AuthorizeError,
    RegistrationError,
)

from src.auth.auth import (
    discover_oauth_server, 
    ALWAYS_PRESENT_SCOPES,
    TokenSet as SingleStoreTokenSet
)
from src.config.app_config import app_config, AuthMethod
from src.config.config import CLIENT_ID, OAUTH_HOST, CLIENT_URI

# Store authorization codes, refresh tokens, and access tokens in memory
# In a production environment, these should be stored in a database
authorization_codes: Dict[str, "SingleStoreAuthorizationCode"] = {}
refresh_tokens: Dict[str, "SingleStoreRefreshToken"] = {}
access_tokens: Dict[str, "SingleStoreAccessToken"] = {}
clients: Dict[str, OAuthClientInformationFull] = {}

# Default expiry times
DEFAULT_AUTH_CODE_EXPIRY = 600  # 10 minutes
DEFAULT_ACCESS_TOKEN_EXPIRY = 3600  # 1 hour
DEFAULT_REFRESH_TOKEN_EXPIRY = 30 * 24 * 3600  # 30 days


class SingleStoreAuthorizationCode(AuthorizationCode):
    """Extended authorization code for SingleStore authentication"""
    original_state: str


class SingleStoreRefreshToken(RefreshToken):
    """Extended refresh token for SingleStore authentication"""
    singlestore_refresh_token: str


class SingleStoreAccessToken(AccessToken):
    """Extended access token for SingleStore authentication"""
    singlestore_access_token: str


class SingleStoreOAuthProvider(OAuthAuthorizationServerProvider[
    SingleStoreAuthorizationCode, 
    SingleStoreRefreshToken, 
    SingleStoreAccessToken
]):
    """
    Implementation of the OAuthAuthorizationServerProvider protocol for SingleStore.
    This provider delegates OAuth authentication to the SingleStore authentication service.
    """

    async def get_client(self, client_id: str) -> Optional[OAuthClientInformationFull]:
        """
        Retrieves client information by client ID.
        
        Args:
            client_id: The ID of the client to retrieve.
            
        Returns:
            The client information, or None if the client does not exist.
        """
        return clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        """
        Saves client information as part of registering it.
        
        Args:
            client_info: The client metadata to register.
            
        Raises:
            RegistrationError: If the client metadata is invalid.
        """
        # Validate redirect URIs
        if not client_info.redirect_uris or not all(client_info.redirect_uris):
            raise RegistrationError(
                error="invalid_redirect_uri",
                error_description="At least one valid redirect URI must be provided"
            )
            
        # Store the client
        clients[client_info.client_id] = client_info

    def _generate_code_verifier(self) -> str:
        """Generate a code verifier for PKCE"""
        code_verifier = secrets.token_urlsafe(64)
        # Trim to appropriate length (43-128 chars)
        if len(code_verifier) > 128:
            code_verifier = code_verifier[:128]
        return code_verifier

    def _generate_code_challenge(self, code_verifier: str) -> str:
        """Generate a code challenge from the code verifier"""
        code_challenge = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = base64.urlsafe_b64encode(code_challenge).decode().rstrip('=')
        return code_challenge

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        """
        Called as part of the authorization endpoint, and returns a URL that the client
        will be redirected to for authentication with SingleStore's OAuth service.
        
        Args:
            client: The client requesting authorization.
            params: The parameters of the authorization request.
            
        Returns:
            A URL to redirect the client to for authorization.
            
        Raises:
            AuthorizeError: If the authorization request is invalid.
        """
        # Validate required parameters
        if not params.redirect_uri:
            raise AuthorizeError(
                error="invalid_request",
                error_description="Missing redirect_uri parameter"
            )
            
        # Check if the redirect URI is registered for this client
        if params.redirect_uri_provided_explicitly and str(params.redirect_uri) not in client.redirect_uris:
            raise AuthorizeError(
                error="invalid_request",
                error_description="The provided redirect_uri is not registered for this client"
            )
        
        # Generate PKCE code verifier and challenge for our own use with SingleStore OAuth
        code_verifier = self._generate_code_verifier()
        code_challenge = self._generate_code_challenge(code_verifier)
        
        # Discover SingleStore OAuth endpoints
        oauth_config = discover_oauth_server(OAUTH_HOST)
        authorization_endpoint = oauth_config.get("authorization_endpoint")
        
        if not authorization_endpoint:
            raise AuthorizeError(
                error="server_error",
                error_description="Failed to discover OAuth endpoints"
            )
        
        # Create state for SingleStore OAuth that includes our own state
        # We'll use this to correlate the responses
        singlestore_state = secrets.token_urlsafe(32)
        
        # Store the original state and code challenge for verification later
        # We'll store this correlation so we can retrieve it when SingleStore redirects back
        authorization_codes[singlestore_state] = SingleStoreAuthorizationCode(
            code=singlestore_state,  # Temporarily use state as code
            scopes=params.scopes or [],
            expires_at=time.time() + DEFAULT_AUTH_CODE_EXPIRY,
            client_id=client.client_id,
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            original_state=params.state or "",
        )
        
        # Prepare scopes - combine client scopes with our required ones
        all_scopes = list(set(ALWAYS_PRESENT_SCOPES + (params.scopes or [])))
        scopes_str = " ".join(all_scopes)
        
        # Prepare SingleStore authorization URL parameters
        auth_params = {
            "client_id": CLIENT_ID,
            "redirect_uri": f"{CLIENT_URI}/auth/callback",  # Our server's callback endpoint
            "response_type": "code",
            "scope": scopes_str,
            "state": singlestore_state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }
        
        # Create the authorization URL for SingleStore OAuth
        auth_url = f"{authorization_endpoint}?{urlencode(auth_params)}"
        
        return auth_url

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> Optional[SingleStoreAuthorizationCode]:
        """
        Loads an AuthorizationCode by its code.
        
        Args:
            client: The client that requested the authorization code.
            authorization_code: The authorization code to get the challenge for.
            
        Returns:
            The AuthorizationCode, or None if not found
        """
        code_obj = authorization_codes.get(authorization_code)
        
        if not code_obj:
            return None
            
        # Validate client ID
        if code_obj.client_id != client.client_id:
            return None
            
        # Check if code is expired
        if code_obj.expires_at < time.time():
            # Clean up expired code
            authorization_codes.pop(authorization_code, None)
            return None
            
        return code_obj

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: SingleStoreAuthorizationCode
    ) -> OAuthToken:
        """
        Exchanges an authorization code for an access token and refresh token.
        
        Args:
            client: The client exchanging the authorization code.
            authorization_code: The authorization code to exchange.
            
        Returns:
            The OAuth token, containing access and refresh tokens.
            
        Raises:
            TokenError: If the request is invalid
        """
        # Get the SingleStore token from our authentication flow
        from src.auth.auth import authenticate
        
        success, singlestore_token_set = authenticate()
        
        if not success or not singlestore_token_set:
            raise TokenError(
                error="invalid_grant",
                error_description="Failed to authenticate with SingleStore"
            )
        
        # Store SingleStore token in app_config
        app_config.set_auth_token(singlestore_token_set.access_token, AuthMethod.OAUTH)
        
        # Generate our tokens
        access_token_value = secrets.token_urlsafe(32)
        refresh_token_value = secrets.token_urlsafe(32)
        
        # Calculate expiry times
        current_time = int(time.time())
        access_token_expires = current_time + DEFAULT_ACCESS_TOKEN_EXPIRY
        refresh_token_expires = current_time + DEFAULT_REFRESH_TOKEN_EXPIRY
        
        # Create access token
        access_token = SingleStoreAccessToken(
            token=access_token_value,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            expires_at=access_token_expires,
            singlestore_access_token=singlestore_token_set.access_token
        )
        
        # Create refresh token
        refresh_token = SingleStoreRefreshToken(
            token=refresh_token_value,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            expires_at=refresh_token_expires,
            singlestore_refresh_token=singlestore_token_set.refresh_token
        )
        
        # Store tokens
        access_tokens[access_token_value] = access_token
        refresh_tokens[refresh_token_value] = refresh_token
        
        # Remove the used authorization code
        authorization_codes.pop(authorization_code.code, None)
        
        # Return the OAuth token
        return OAuthToken(
            access_token=access_token_value,
            token_type="Bearer",
            expires_in=DEFAULT_ACCESS_TOKEN_EXPIRY,
            refresh_token=refresh_token_value,
            scope=" ".join(authorization_code.scopes)
        )

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> Optional[SingleStoreRefreshToken]:
        """
        Loads a RefreshToken by its token string.
        
        Args:
            client: The client that is requesting to load the refresh token.
            refresh_token: The refresh token string to load.
            
        Returns:
            The RefreshToken object if found, or None if not found.
        """
        token_obj = refresh_tokens.get(refresh_token)
        
        if not token_obj:
            return None
            
        # Validate client ID
        if token_obj.client_id != client.client_id:
            return None
            
        # Check if token is expired
        if token_obj.expires_at and token_obj.expires_at < int(time.time()):
            # Clean up expired token
            refresh_tokens.pop(refresh_token, None)
            return None
            
        return token_obj

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: SingleStoreRefreshToken,
        scopes: List[str],
    ) -> OAuthToken:
        """
        Exchanges a refresh token for an access token and refresh token.
        
        Args:
            client: The client exchanging the refresh token.
            refresh_token: The refresh token to exchange.
            scopes: Optional scopes to request with the new access token.
            
        Returns:
            The OAuth token, containing access and refresh tokens.
            
        Raises:
            TokenError: If the request is invalid
        """
        # Create a SingleStore token set from the singlestore_refresh_token
        singlestore_token_data = {
            "refresh_token": refresh_token.singlestore_refresh_token,
            "expires_at": refresh_token.expires_at
        }
        singlestore_token_set = SingleStoreTokenSet(singlestore_token_data)
        
        # Refresh the SingleStore token
        from src.auth.auth import refresh_token as refresh_singlestore_token
        
        refreshed_token_set = refresh_singlestore_token(singlestore_token_set)
        
        if not refreshed_token_set or not refreshed_token_set.access_token:
            raise TokenError(
                error="invalid_grant",
                error_description="Failed to refresh token with SingleStore"
            )
        
        # Store refreshed token in app_config
        app_config.set_auth_token(refreshed_token_set.access_token, AuthMethod.OAUTH)
        
        # Generate new tokens
        new_access_token_value = secrets.token_urlsafe(32)
        new_refresh_token_value = secrets.token_urlsafe(32)
        
        # Calculate expiry times
        current_time = int(time.time())
        access_token_expires = current_time + DEFAULT_ACCESS_TOKEN_EXPIRY
        refresh_token_expires = current_time + DEFAULT_REFRESH_TOKEN_EXPIRY
        
        # Use requested scopes or fall back to the original scopes
        final_scopes = scopes or refresh_token.scopes
        
        # Create access token
        access_token = SingleStoreAccessToken(
            token=new_access_token_value,
            client_id=client.client_id,
            scopes=final_scopes,
            expires_at=access_token_expires,
            singlestore_access_token=refreshed_token_set.access_token
        )
        
        # Create refresh token
        new_refresh_token = SingleStoreRefreshToken(
            token=new_refresh_token_value,
            client_id=client.client_id,
            scopes=final_scopes,
            expires_at=refresh_token_expires,
            singlestore_refresh_token=refreshed_token_set.refresh_token
        )
        
        # Store tokens
        access_tokens[new_access_token_value] = access_token
        refresh_tokens[new_refresh_token_value] = new_refresh_token
        
        # Remove the used refresh token
        refresh_tokens.pop(refresh_token.token, None)
        
        # Return the OAuth token
        return OAuthToken(
            access_token=new_access_token_value,
            token_type="Bearer",
            expires_in=DEFAULT_ACCESS_TOKEN_EXPIRY,
            refresh_token=new_refresh_token_value,
            scope=" ".join(final_scopes)
        )

    async def load_access_token(self, token: str) -> Optional[SingleStoreAccessToken]:
        """
        Loads an access token by its token.
        
        Args:
            token: The access token to verify.
            
        Returns:
            The AccessToken, or None if the token is invalid.
        """
        token_obj = access_tokens.get(token)
        
        if not token_obj:
            return None
            
        # Check if token is expired
        if token_obj.expires_at and token_obj.expires_at < int(time.time()):
            # Clean up expired token
            access_tokens.pop(token, None)
            return None
            
        return token_obj

    async def revoke_token(
        self,
        token: SingleStoreAccessToken | SingleStoreRefreshToken,
    ) -> None:
        """
        Revokes an access or refresh token.
        
        Args:
            token: the token to revoke
        """
        # Determine token type and revoke accordingly
        if isinstance(token, SingleStoreAccessToken):
            # Revoke access token
            access_tokens.pop(token.token, None)
            
            # Find and revoke the corresponding refresh token
            for rt_key, rt in list(refresh_tokens.items()):
                if rt.client_id == token.client_id and set(rt.scopes) == set(token.scopes):
                    refresh_tokens.pop(rt_key, None)
                    break
                    
        elif isinstance(token, SingleStoreRefreshToken):
            # Revoke refresh token
            refresh_tokens.pop(token.token, None)
            
            # Find and revoke corresponding access tokens
            for at_key, at in list(access_tokens.items()):
                if at.client_id == token.client_id and set(at.scopes) == set(token.scopes):
                    access_tokens.pop(at_key, None)
