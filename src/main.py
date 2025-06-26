import click
import logging

from src.commands.init import init_command
from src.commands import start_command
from src.utils.constants import TransportType, ClientType


@click.group()
def cli():
    pass


@cli.command()
@click.option(
    "--transport",
    type=click.Choice(TransportType.choices(), case_sensitive=True),
    required=False,
    default=TransportType.default(),
    help="Only stdio transport is currently supported for local development. ",
)
def start(transport: str):
    """
    Start the MCP server with the specified transport.

    The server will automatically handle authentication via browser OAuth.
    """

    transport = TransportType(transport).value
    logging.info(f"Starting MCP server with transport={transport}")
    start_command(transport)


@cli.command()
@click.option(
    "--client",
    type=click.Choice(ClientType.choices(), case_sensitive=True),
    default=ClientType.default(),
    help=f"LLM client to configure (default: {ClientType.default()})",
)
def init(client: str):
    """
    Shows configuration information for SingleStore MCP server with OAuth authentication.
    """
    client = ClientType(client).value
    logging.info(f"Initializing SingleStore MCP server for {client.capitalize()}...")
    init_command(client)


def main():
    """
    Main entry point for the MCP server CLI.
    """
    cli()


if __name__ == "__main__":
    main()
