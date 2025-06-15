from mcp.server.fastmcp import FastMCP
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
import logging

from src.auth.callback import make_auth_callback_handler
from src.api.tools import register_tools
from src.auth.provider import SingleStoreOAuthProvider
from src.api.resources.register import register_resources
from src.auth.browser_auth import get_authentication_token
import src.config.config as config

# Configure logging to enable debug messages
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)


def start_command(transport, api_key):
    # Handle browser authentication for stdio mode when no API key is provided
    if transport == config.Transport.STDIO and not api_key:
        print("No API key provided for stdio mode. Starting browser authentication...")
        oauth_token = get_authentication_token()
        if not oauth_token:
            print(
                "❌ Authentication failed. Cannot start MCP server without valid credentials."
            )
            return
        print("✅ Authentication successful. Starting MCP server...")

        # Create settings with OAuth token
        settings = config.init_settings(transport=transport, api_key=oauth_token)
        if isinstance(settings, config.LocalSettings):
            settings.set_oauth_token(oauth_token)
    else:
        settings = config.init_settings(transport=transport, api_key=api_key)

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

    mcp.run(transport=transport)
