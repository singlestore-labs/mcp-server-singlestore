import logging
from src.auth.provider import SingleStoreOAuthProvider
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response


def make_auth_callback_handler(oauth_provider: SingleStoreOAuthProvider):
    async def auth_callback_handler(request: Request) -> Response:
        code = request.query_params.get("code")
        state = request.query_params.get("state")

        if not code:
            raise HTTPException(400, "Missing code parameter")
        if not state:
            raise HTTPException(400, "Missing state parameter")

        try:
            redirect_uri = await oauth_provider.handle_singlestore_callback(code, state)
            return RedirectResponse(status_code=302, url=redirect_uri)
        except HTTPException:
            raise
        except Exception as e:
            logging.error("Unexpected error", exc_info=e)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "server_error",
                    "error_description": "Unexpected error",
                },
            )

    return auth_callback_handler
