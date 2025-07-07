import os
from mcp.server.fastmcp import FastMCP
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions

from src.auth.callback import make_auth_callback_handler
from src.api.tools import register_tools
from src.auth.provider import SingleStoreOAuthProvider
from src.api.resources.register import register_resources
from src.auth.browser_auth import get_authentication_token
import src.config.config as config
from src.logger import get_logger

logger = get_logger()


def start_command(transport: str, host: str):
    api_key = os.environ.get("MCP_API_KEY")

    if transport == config.Transport.STDIO:
        if api_key:
            # Silent API key authentication for Docker containers
            logger.debug("Using API key authentication")
            settings = config.init_settings(transport=transport, host=host)
            # API key will be automatically loaded from env vars via Pydantic
        else:
            # Use browser authentication for stdio mode
            oauth_token = get_authentication_token()
            if not oauth_token:
                logger.error("Authentication failed. Please try again")
                return
            logger.info("Authentication successful")

            # Create settings with OAuth token as JWT token
            settings = config.init_settings(
                transport=transport, jwt_token=oauth_token, host=host
            )
    else:
        raise NotImplementedError("Only stdio transport is currently supported.")
        # settings = config.init_settings(transport=transport, jwt_token=None)

    mcp_args = {
        "name": "SingleStore MCP Server",
    }

    if settings.is_remote:
        mcp_args["auth"] = AuthSettings(
            issuer_url=settings.server_url,
            required_scopes=settings.required_scopes,
            client_registration_options=ClientRegistrationOptions(
                enabled=True,
                valid_scopes=settings.required_scopes,
                default_scopes=settings.required_scopes,
            ),
        )

        provider = SingleStoreOAuthProvider(settings=settings)

        mcp_args["auth_server_provider"] = provider

        mcp_args["host"] = settings.host
        mcp_args["port"] = settings.port

    mcp = FastMCP(**mcp_args)
    config._app_ctx.set(mcp)

    register_tools(mcp)
    register_resources(mcp)

    if settings.is_remote:
        # Register the callback handler with the captured oauth_provider
        mcp.custom_route("/callback", methods=["GET"])(
            make_auth_callback_handler(provider)
        )

    logger.info(
        f"Starting MCP server with transport={transport} on {settings.host}:{settings.port}"
    )

    mcp.run(transport=transport)
