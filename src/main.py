import sys
import click
import logging

import src.config.config as config
from src.commands import init_command, start_command


@click.group()
def cli():
    pass


@cli.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse", "http"], case_sensitive=True),
    required=False,
    default="stdio",
    help="Transport mode: stdio (local) or sse/http (remote)",
)
@click.option(
    "--api-key",
    type=str,
    default=None,
    help="API key for authentication on stdio transport",
)
def start(transport: config.Transport, api_key: str | None):
    logging.info(f"Starting MCP server with transport={transport}")
    start_command(transport, api_key)


@cli.command()
@click.option(
    "--api-key",
    type=str,
    required=True,
    help="API key for authentication on stdio transport",
)
@click.option(
    "--client",
    type=click.Choice(["claude", "cursor"], case_sensitive=False),
    required=False,
    default="claude",
    help="LLM client to configure (default: claude)",
)
def init(api_key: str, client: str):
    """
    Initialize the MCP server with the given API key and client.
    """
    logging.info(f"Configuring SingleStore MCP server for {client}")
    sys.exit(init_command(api_key, client))


def main():
    """
    Main entry point for the MCP server CLI.
    """
    cli()


if __name__ == "__main__":
    main()
