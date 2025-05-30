import logging
import sys

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from fastmcp import FastMCP
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from src import logger
from src.api.resources import resources
from src.api.tools import tools, register_tools
from src.auth.settings import ServerSettings
from src.config import app_config
from utils.middleware import apply_auth_middleware
from src.api.resources import register_resources
from src.commands import register_all_commands
from src.auth import SimpleSingleStoreOAuthProvider


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


settings = ServerSettings(
    host=app_config.settings.server_host, port=app_config.settings.server_port
)

oauth_provider = SimpleSingleStoreOAuthProvider(settings)

client_registration_options = ClientRegistrationOptions(
    enabled=True,
)

auth_settings = AuthSettings(
    issuer_url=settings.server_url,
    required_scopes=[settings.mcp_scope],
    client_registration_options=client_registration_options,
)


# Create FastMCP server instance with lifespan
mcp = FastMCP(
    "SingleStore MCP Server",
    lifespan=app_lifespan,
    auth_server_provider=oauth_provider,
    auth=auth_settings,
    host=settings.host,
    port=settings.port,
)


@mcp.custom_route("/callback", methods=["GET"])
async def singlestore_callback_handler(request: Request) -> Response:
    """Handle SingleStore OAuth callback."""
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not code:
        raise HTTPException(400, "Missing code parameter")
    if not state:
        raise HTTPException(400, "Missing state parameter")

    try:
        redirect_uri = await oauth_provider.handle_singlestore_callback(code, state)
        return RedirectResponse(status_code=302, url=redirect_uri)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error", exc_info=e)
        return JSONResponse(
            status_code=500,
            content={
                "error": "server_error",
                "error_description": "Unexpected error",
            },
        )


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
        args.func(args, mcp)
    else:
        parser.print_help()
        sys.exit(1)
