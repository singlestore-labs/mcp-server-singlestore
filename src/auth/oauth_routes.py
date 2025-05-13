from urllib.parse import urlencode

from fastapi import APIRouter, Query, Request, Response, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from mcp.shared.auth import OAuthClientInformationFull

from .auth_provider import SingleStoreOAuthProvider, authorization_codes
from src.config.auth_settings import auth_settings
from src.config.app_config import app_config, AuthMethod

# Create OAuth routes
oauth_router = APIRouter(prefix="/auth")

# Initialize the OAuth provider
oauth_provider = SingleStoreOAuthProvider()

# Discovery endpoint
@oauth_router.get("/.well-known/openid-configuration")
async def openid_configuration():
    """
    OIDC discovery endpoint that provides information about the server's capabilities.
    """
    return {
        "issuer": auth_settings.issuer_url,
        "authorization_endpoint": f"{auth_settings.issuer_url}/auth/authorize",
        "token_endpoint": f"{auth_settings.issuer_url}/auth/token",
        "revocation_endpoint": f"{auth_settings.issuer_url}/auth/revoke",
        "jwks_uri": f"{auth_settings.issuer_url}/auth/jwks",
        "scopes_supported": auth_settings.client_registration_options.valid_scopes,
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["none"],
        "revocation_endpoint_auth_methods_supported": ["none"],
        "code_challenge_methods_supported": ["S256"],
        "service_documentation": "https://singlestore.com/docs/",
    }

# Client registration endpoint
@oauth_router.post("/register")
async def register_client(client_info: OAuthClientInformationFull):
    """
    Register a new OAuth client.
    """
    await oauth_provider.register_client(client_info)
    return {"status": "success", "client_id": client_info.client_id}

# Authorize endpoint
@oauth_router.get("/authorize")
async def authorize(
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    response_type: str = Query(...),
    scope: str = Query(None),
    state: str = Query(None),
    code_challenge: str = Query(None),
    code_challenge_method: str = Query(None),
):
    """
    Authorize endpoint that initiates the OAuth flow.
    This endpoint validates the request and redirects to the SingleStore OAuth server.
    """
    # Parse scopes
    scopes = scope.split() if scope else []
    
    # Load client
    client = await oauth_provider.get_client(client_id)
    if not client:
        error_params = {
            "error": "invalid_client",
            "error_description": "Client not found",
        }
        if redirect_uri and state:
            error_params["state"] = state
            return RedirectResponse(f"{redirect_uri}?{urlencode(error_params)}")
        else:
            raise HTTPException(status_code=400, detail="Invalid client")
    
    # Create authorization params
    auth_params = {
        "redirect_uri": redirect_uri,
        "redirect_uri_provided_explicitly": True,
        "response_type": response_type,
        "scopes": scopes,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
    }
    
    try:
        # Get authorization URL from provider
        auth_url = await oauth_provider.authorize(client, auth_params)
        return RedirectResponse(auth_url)
    except Exception as e:
        error_params = {
            "error": "server_error",
            "error_description": str(e),
        }
        if state:
            error_params["state"] = state
        return RedirectResponse(f"{redirect_uri}?{urlencode(error_params)}")

# Callback endpoint
@oauth_router.get("/callback")
async def callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    error_description: str = Query(None),
):
    """
    Callback endpoint for handling the response from the SingleStore OAuth server.
    This will validate the response and redirect back to the client's redirect URI.
    """
    if error:
        # Handle error from OAuth server
        return JSONResponse(
            content={
                "error": error,
                "error_description": error_description or "An error occurred during authentication"
            },
            status_code=400
        )
    
    if not code or not state:
        return JSONResponse(
            content={
                "error": "invalid_request",
                "error_description": "Missing required parameters"
            },
            status_code=400
        )
    
    # Get the authorization code from our store
    auth_code = authorization_codes.get(state)
    if not auth_code:
        return JSONResponse(
            content={
                "error": "invalid_request",
                "error_description": "Invalid state parameter"
            },
            status_code=400
        )
    
    # Update the authorization code with the real code
    auth_code.code = code
    
    # Redirect back to the client's redirect URI
    redirect_params = {
        "code": code,
        "state": auth_code.original_state
    }
    
    return RedirectResponse(f"{auth_code.redirect_uri}?{urlencode(redirect_params)}")

# Token endpoint
@oauth_router.post("/token")
async def token(request: Request):
    """
    Token endpoint for exchanging authorization code for access tokens.
    """
    form_data = await request.form()
    grant_type = form_data.get("grant_type")
    
    if grant_type == "authorization_code":
        client_id = form_data.get("client_id")
        code = form_data.get("code")
        redirect_uri = form_data.get("redirect_uri")
        code_verifier = form_data.get("code_verifier")
        
        if not all([client_id, code, redirect_uri]):
            return JSONResponse(
                content={
                    "error": "invalid_request",
                    "error_description": "Missing required parameters"
                },
                status_code=400
            )
        
        # Load client
        client = await oauth_provider.get_client(client_id)
        if not client:
            return JSONResponse(
                content={
                    "error": "invalid_client",
                    "error_description": "Client not found"
                },
                status_code=400
            )
        
        # Load authorization code
        auth_code = await oauth_provider.load_authorization_code(client, code)
        if not auth_code:
            return JSONResponse(
                content={
                    "error": "invalid_grant",
                    "error_description": "Invalid authorization code"
                },
                status_code=400
            )
        
        # Verify redirect URI matches
        if auth_code.redirect_uri_provided_explicitly and auth_code.redirect_uri != redirect_uri:
            return JSONResponse(
                content={
                    "error": "invalid_grant",
                    "error_description": "Redirect URI mismatch"
                },
                status_code=400
            )
        
        # Verify PKCE code verifier if challenge was provided
        if auth_code.code_challenge and not code_verifier:
            return JSONResponse(
                content={
                    "error": "invalid_grant",
                    "error_description": "Code verifier required"
                },
                status_code=400
            )
        
        try:
            # Exchange code for tokens
            token = await oauth_provider.exchange_authorization_code(client, auth_code)
            return token.model_dump()
        except Exception as e:
            return JSONResponse(
                content={
                    "error": "server_error",
                    "error_description": str(e)
                },
                status_code=500
            )
    
    elif grant_type == "refresh_token":
        client_id = form_data.get("client_id")
        refresh_token = form_data.get("refresh_token")
        scope = form_data.get("scope")
        
        if not all([client_id, refresh_token]):
            return JSONResponse(
                content={
                    "error": "invalid_request",
                    "error_description": "Missing required parameters"
                },
                status_code=400
            )
        
        # Load client
        client = await oauth_provider.get_client(client_id)
        if not client:
            return JSONResponse(
                content={
                    "error": "invalid_client",
                    "error_description": "Client not found"
                },
                status_code=400
            )
        
        # Load refresh token
        token_obj = await oauth_provider.load_refresh_token(client, refresh_token)
        if not token_obj:
            return JSONResponse(
                content={
                    "error": "invalid_grant",
                    "error_description": "Invalid refresh token"
                },
                status_code=400
            )
        
        # Parse scopes
        scopes = scope.split() if scope else []
        
        try:
            # Exchange refresh token for new tokens
            token = await oauth_provider.exchange_refresh_token(client, token_obj, scopes)
            return token.model_dump()
        except Exception as e:
            return JSONResponse(
                content={
                    "error": "server_error",
                    "error_description": str(e)
                },
                status_code=500
            )
    
    else:
        return JSONResponse(
            content={
                "error": "unsupported_grant_type",
                "error_description": f"Unsupported grant type: {grant_type}"
            },
            status_code=400
        )

# Token revocation endpoint
@oauth_router.post("/revoke")
async def revoke_token(request: Request):
    """
    Revoke an access or refresh token.
    """
    form_data = await request.form()
    token = form_data.get("token")
    token_type_hint = form_data.get("token_type_hint")
    client_id = form_data.get("client_id")
    
    if not token or not client_id:
        return JSONResponse(
            content={
                "error": "invalid_request",
                "error_description": "Missing required parameters"
            },
            status_code=400
        )
    
    # Load client
    client = await oauth_provider.get_client(client_id)
    if not client:
        return JSONResponse(
            content={
                "error": "invalid_client",
                "error_description": "Client not found"
            },
            status_code=400
        )
    
    # Try to load as access token first
    token_obj = await oauth_provider.load_access_token(token)
    
    # If not found and token_type_hint is refresh_token or not provided, try as refresh token
    if not token_obj and (not token_type_hint or token_type_hint == "refresh_token"):
        token_obj = await oauth_provider.load_refresh_token(client, token)
    
    # If token was found, revoke it
    if token_obj:
        await oauth_provider.revoke_token(token_obj)
    
    # Always return success, even if token wasn't found, to prevent token enumeration
    return Response(status_code=200)
