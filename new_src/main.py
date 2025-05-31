import click
import logging

from fastmcp import FastMCP
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions


from new_src.auth.callback import make_auth_callback_handler
import new_src.config.config as config
from new_src.api.tools import register_tools
from new_src.auth.provider import SingleStoreOAuthProvider


@click.group()
def cli():
    pass


@cli.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse", "http"], case_sensitive=True),
    required=True,
    help="Transport mode: stdio (local) or sse/http (remote)",
)
@click.option(
    "--api-key",
    type=str,
    default=None,
    help="API key for authentication on stdio transport",
)
def start(transport: config.Transport, api_key: str | None):
    config.init_settings(transport=transport, api_key=api_key)
    logging.info(f"Starting MCP server with transport={transport}")

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

    mcp = mcp = FastMCP(**mcp_args)

    register_tools(mcp)

    if settings.is_remote:
        # Register the callback handler with the captured oauth_provider
        mcp.custom_route("/callback", methods=["GET"])(
            make_auth_callback_handler(provider)
        )
        mcp.run(transport=transport, host=settings.host, port=settings.port)
    else:
        mcp.run(transport=transport)


@cli.command()
def init():
    # Placeholder for init command logic
    click.echo("Init command placeholder")


if __name__ == "__main__":
    cli()
