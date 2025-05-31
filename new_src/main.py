import click
import logging

from fastmcp import FastMCP

import new_src.config.config as config
from new_src.api.tools import register_tools


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

    mcp = FastMCP(
        "SingleStore MCP Server",
    )

    register_tools(mcp)

    settings = config.get_settings()

    if settings.is_remote:
        mcp.run(transport=transport, host=settings.host, port=settings.port)
    else:
        mcp.run(transport=transport)


@cli.command()
def init():
    # Placeholder for init command logic
    click.echo("Init command placeholder")


if __name__ == "__main__":
    try:
        cli()
    except Exception as e:
        logging.error(e)
