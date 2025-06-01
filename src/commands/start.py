from fastmcp import FastMCP
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions


from src.auth.callback import make_auth_callback_handler
import src.config.config as config
from src.api.tools import register_tools
from src.auth.provider import SingleStoreOAuthProvider


def start_command(transport, api_key):
    config.init_settings(transport=transport, api_key=api_key)

    settings = config.get_settings()

    mcp_args = {
        "name": "SingleStore MCP Server",
    }

    if settings.is_remote:
        mcp_args["auth"] = AuthSettings(
            issuer_url=settings.server_url,
            required_scopes=settings.required_scopes,
            client_registration_options=ClientRegistrationOptions(enabled=True),
        )

        provider = SingleStoreOAuthProvider(settings=settings)

        mcp_args["auth_server_provider"] = provider

    mcp = FastMCP(**mcp_args)

    register_tools(mcp)

    if settings.is_remote:
        # Register the callback handler with the captured oauth_provider
        mcp.custom_route("/callback", methods=["GET"])(
            make_auth_callback_handler(provider)
        )
        mcp.run(transport=transport, host=settings.host, port=settings.port)
    else:
        mcp.run(transport=transport)
