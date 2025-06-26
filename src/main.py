import click
import logging

import src.config.config as config
from src.commands import start_command


@click.group()
def cli():
    pass


@cli.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse", "streamable-http"], case_sensitive=True),
    required=False,
    default="stdio",
    help="Transport mode: stdio (local) or sse/streamable-http (remote)",
)
def start(transport: config.Transport):
    """
    Start the MCP server with the specified transport. Available transports:
    - stdio: Local transport for development
    - sse: Server-Sent Events for remote connections
    - http: HTTP transport for remote connections

    The server will automatically handle authentication via browser OAuth.
    """
    logging.info(f"Starting MCP server with transport={transport}")
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


def main():
    """
    Main entry point for the MCP server CLI.
    """
    cli()


if __name__ == "__main__":
    main()
