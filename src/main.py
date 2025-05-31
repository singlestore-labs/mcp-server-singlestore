"""import logging
import sys

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from fastmcp import FastMCP

from src.api.resources import resources
from src.api.tools import tools, register_tools
from utils.middleware import apply_auth_middleware
from src.api.resources import register_resources
from src.cli.commands import register_all_commands


# Store notes as a simple key-value dict to demonstrate state management
notes: dict[str, str] = {}

# Store custom text resources
custom_text_resources: dict[str, str] = {}

# Store session state for caching user inputs
session_state: dict[str, dict] = {}


@dataclass
class AppContext:
    Application context for lifespan management

    notes: dict[str, str]
    custom_text_resources: dict[str, str]
    session_state: dict[str, dict]


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    Manage application lifecycle with type-safe context
    # Initialize on startup
    try:
        yield AppContext(
            notes=notes,
            custom_text_resources=custom_text_resources,
            session_state=session_state,
        )
    finally:
        # Cleanup on shutdown
        notes.clear()
        custom_text_resources.clear()
        session_state.clear()
        print("Application context cleared.")


# Apply auth middleware to tools and filter out login/refresh tools from public API
public_tools = apply_auth_middleware(tools)

register_resources(mcp, resources)
register_tools(mcp, public_tools)


def main():
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="SingleStore MCP Server")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Register all commands from commands.py
    register_all_commands(subparsers)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
        sys.exit(1)"""

import click
import logging

from fastmcp import FastMCP
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions

from src.auth.provider import SingleStoreOAuthProvider
import src.config.config as config
from src.api.tools.registery import register_tools


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
def start(transport):

    config.init_settings(transport=transport)
    logging.info(f"Starting MCP server with transport={transport}")

    auth_settings = AuthSettings(
        issuer_url=config.settings.server_url,
        required_scopes=config.settings.required_scopes.split(","),
        client_registration_options=ClientRegistrationOptions(enabled=True),
    )

    oauth_provider = SingleStoreOAuthProvider(settings=config.settings)

    mcp = mcp = FastMCP(
        "SingleStore MCP Server",
        # lifespan=app_lifespan,
        auth_server_provider=oauth_provider,
        auth=auth_settings,
    )

    register_tools(mcp)

    mcp.run(transport=transport, host=config.settings.host, port=config.settings.port)


@cli.command()
def init():
    # Placeholder for init command logic
    click.echo("Init command placeholder")


if __name__ == "__main__":
    cli()
