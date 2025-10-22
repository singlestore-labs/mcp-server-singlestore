import os
from urllib.parse import urljoin
from mcp.server.fastmcp import FastMCP
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
from pydantic import AnyHttpUrl
from src.auth.proxy_provider import SingleStoreOAuthProxy
from src.api.prompts.register import register_prompts
from src.api.tools import register_tools
from src.api.resources.register import register_resources
from src.auth.browser_auth import get_authentication_token
import src.config.config as config
from src.logger import get_logger

logger = get_logger()


def start_command(transport: str, host: str):
    api_key = os.environ.get("MCP_API_KEY")
    jwt_token = os.environ.get("MCP_JWT_TOKEN")
    org_id = os.environ.get("MCP_ORG_ID")

    if transport == config.Transport.STDIO:
        if api_key:
            logger.debug("Using API key authentication")
            settings = config.init_settings(transport=transport, host=host)
            # API key will be automatically loaded from env vars via Pydantic
        elif jwt_token and org_id:
            logger.debug("Using JWT token authentication")
            settings = config.init_settings(
                transport=transport, jwt_token=jwt_token, org_id=org_id, host=host
            )
            # JWT token and org_id will be automatically loaded from env vars via Pydantic
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
        # raise NotImplementedError("Only stdio transport is currently supported.")
        settings = config.init_settings(transport=transport, jwt_token=jwt_token)

    mcp_args = {
        "name": "SingleStore MCP Server",
        "auth": None,
    }

    if isinstance(settings, config.RemoteSettings) and settings.server_url:
        server_endpoint = urljoin(settings.server_url.unicode_string(), "mcp")

        mcp_args["auth"] = AuthSettings(
            issuer_url=settings.server_url,  # Points to self because it hosts the auth endpoints through a proxy
            required_scopes=settings.required_scopes,
            resource_server_url=AnyHttpUrl(server_endpoint),
            client_registration_options=ClientRegistrationOptions(
                enabled=True,
                valid_scopes=settings.required_scopes,
                default_scopes=settings.required_scopes,
            ),
        )

        auth_provider = SingleStoreOAuthProxy().get_provider()

        mcp_args["auth_server_provider"] = auth_provider

        mcp_args["host"] = settings.host
        mcp_args["port"] = settings.port

    mcp = FastMCP(**mcp_args)
    config._app_ctx.set(mcp)

    register_tools(mcp)
    register_resources(mcp)
    register_prompts(mcp)

    if settings.is_remote:
        mcp._custom_starlette_routes = auth_provider.get_routes()

    logger.info(
        f"Starting MCP server with transport={transport} on {settings.host}:{settings.port}"
    )

    mcp.run(transport=transport)
