import logging
import sys

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from fastmcp import FastMCP

""" from src.api.resources import resources
from src.api.tools import tools, register_tools
from utils.middleware import apply_auth_middleware
from src.api.resources import register_resources """
from src.cli.commands import register_all_commands


# Store notes as a simple key-value dict to demonstrate state management
notes: dict[str, str] = {}

# Store custom text resources
custom_text_resources: dict[str, str] = {}

# Store session state for caching user inputs
session_state: dict[str, dict] = {}


@dataclass
class AppContext:
    """Application context for lifespan management"""

    notes: dict[str, str]
    custom_text_resources: dict[str, str]
    session_state: dict[str, dict]


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context"""
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


""" # Apply auth middleware to tools and filter out login/refresh tools from public API
public_tools = apply_auth_middleware(tools)

register_resources(mcp, resources)
register_tools(mcp, public_tools) """


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
        sys.exit(1)
