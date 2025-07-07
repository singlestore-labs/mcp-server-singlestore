import click

from src.commands.constants import (
    CLIENT_CHOICES,
    DEFAULT_CLIENT,
    TRANSPORT_CHOICES,
    DEFAULT_TRANSPORT,
)
from src.commands.init import init_command
from src.commands import start_command
from src.logger import get_logger

# Get logger for this module
logger = get_logger()


@click.group()
def cli():
    pass


@cli.command()
@click.option(
    "--transport",
    type=click.Choice(TRANSPORT_CHOICES, case_sensitive=True),
    required=False,
    default=DEFAULT_TRANSPORT,
    help="Only stdio transport is currently supported for local development. ",
)
@click.option(
    "--host",
    type=str,
    default="localhost",
    help="Host to bind the MCP server to (default: localhost)",
)
def start(transport: str, host: str):
    """
    Start the MCP server with the specified transport.

    The server will automatically handle authentication via browser OAuth.
    """
    start_command(transport, host)


@cli.command()
@click.option(
    "--client",
    type=click.Choice(CLIENT_CHOICES, case_sensitive=True),
    default=DEFAULT_CLIENT,
    help=f"LLM client to configure (default: {DEFAULT_CLIENT})",
)
def init(client: str):
    """
    Shows configuration information for SingleStore MCP server with OAuth authentication.
    """
    # client is already a string, no need to convert
    logger.info(f"Initializing SingleStore MCP server for {client.capitalize()}...")
    init_command(client)


def main():
    """
    Main entry point for the MCP server CLI.
    """
    cli()


if __name__ == "__main__":
    main()
