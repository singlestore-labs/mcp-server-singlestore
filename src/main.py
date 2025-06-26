import click
import logging

<<<<<<< HEAD
from src.commands.constants import (
    CLIENT_CHOICES,
    DEFAULT_CLIENT,
    TRANSPORT_CHOICES,
    DEFAULT_TRANSPORT,
)
from src.commands.init import init_command
=======
import src.config.config as config
>>>>>>> fad6c76 (remove api key)
from src.commands import start_command


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
<<<<<<< HEAD
def start(transport: str):
=======
def start(transport: config.Transport):
>>>>>>> fad6c76 (remove api key)
    """
    Start the MCP server with the specified transport.

    The server will automatically handle authentication via browser OAuth.
    """

    # transport is already a string, no need to convert
    logging.info(f"Starting MCP server with transport={transport}")
<<<<<<< HEAD
    start_command(transport)


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
    logging.info(f"Initializing SingleStore MCP server for {client.capitalize()}...")
    init_command(client)
=======
    start_command(transport, None)


@cli.command()
def init():
    """
    Shows configuration information for SingleStore MCP server with OAuth authentication.
    """
    print("SingleStore MCP Server Configuration")
    print("=" * 40)
    print("\nAuthentication Method: OAuth (Browser-based)")
    print("\nTo use this MCP server:")
    print("1. Start the server: singlestore-mcp-server start")
    print("2. The server will automatically open a browser for OAuth authentication")
    print("\nClient Configuration:")
    print("For Claude Desktop, add to your config:")
    print('"mcpServers": {')
    print('  "singlestore-mcp-server": {')
    print('    "command": "uvx",')
    print('    "args": ["singlestore-mcp-server", "start"]')
    print("  }")
    print("}")
    print("\nNo API keys or tokens required - authentication is handled automatically!")


@cli.command()
def clear_auth():
    """
    Clear saved authentication credentials.
    """
    from src.auth.browser_auth import clear_credentials

    if clear_credentials():
        print("✅ Authentication credentials cleared successfully.")
    else:
        print("No credentials found to clear.")


@cli.command()
def test_auth():
    """
    Test browser authentication without starting the server.
    """
    from src.auth.browser_auth import get_authentication_token

    print("Testing browser authentication...")
    token = get_authentication_token()

    if token:
        print("✅ Authentication successful!")
        print(f"Token received (first 20 chars): {token[:20]}...")
    else:
        print("❌ Authentication failed!")
>>>>>>> fad6c76 (remove api key)


def main():
    """
    Main entry point for the MCP server CLI.
    """
    cli()


if __name__ == "__main__":
    main()
