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
    type=click.Choice(["stdio", "sse", "streamable-http"], case_sensitive=True),
    required=False,
    default="stdio",
    help="Transport mode: stdio (local) or sse/streamable-http (remote)",
)
@click.option(
    "--api-key",
    type=str,
    default=None,
    help="API key for authentication on stdio transport (optional - will use browser authentication if not provided)",
)
def start(transport: config.Transport, api_key: str | None):
    """
    Start the MCP server with the specified transport. Available transports:
    - stdio: Local transport for development
    - sse: Server-Sent Events for remote connections
    - http: HTTP transport for remote connections

    If no API key is provided for stdio transport, it will trigger browser authentication.
    """
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
    Configures the SingleStore MCP server for a specific LLM client. Available clients:
    - claude: Configure for Anthropic's Claude
    - cursor: Configure for Cursor's LLM
    """
    logging.info(f"Configuring SingleStore MCP server for {client}")
    sys.exit(init_command(api_key, client))


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
