from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
import argparse
import sys
import os
from mcp.server.fastmcp import FastMCP

from src.config.app_config import AuthMethod, app_config
from src.utils.resources import resources
from src.utils.tools import tools, filter_tools
from src.utils.middleware import apply_auth_middleware
from src.utils.registration import register_resources, register_tools
from init import init_command
from auth import get_authentication_token

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
            session_state=session_state
        )
    finally:
        # Cleanup on shutdown
        notes.clear()
        custom_text_resources.clear()
        session_state.clear()
        print("Application context cleared.")

# Create FastMCP server instance with lifespan
mcp = FastMCP(
    "SingleStore MCP Server",
    lifespan=app_lifespan,
    dependencies=["mcp-server", "singlestoredb"]
)

# Apply auth middleware to tools and filter out login/refresh tools from public API
public_tools = apply_auth_middleware(tools)

register_resources(mcp, resources)
register_tools(mcp, public_tools)

def main():
    # Set up command-line parser
    parser = argparse.ArgumentParser(description="SingleStore MCP Server")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Add start command (default behavior when no command is provided)
    start_parser = subparsers.add_parser("start", help="Start the MCP server")
    start_parser.add_argument("api_key", nargs="?", help="SingleStore API key (optional, will use web auth if not provided)")
    start_parser.add_argument("--protocol", default="stdio", choices=["stdio", "sse", "http"], help="Protocol to run the server on (default: stdio)")
    start_parser.add_argument("--port", default=8000, type=int, help="Port to run the server on (default: 8000) if protocol is sse")


    # Add init command
    init_parser = subparsers.add_parser("init", help="Initialize client configuration")
    init_parser.add_argument("api_key", nargs="?", help="SingleStore API key (optional, will use web auth if not provided)")
    init_parser.add_argument("--client", default="claude",
                            choices=["claude", "cursor"],
                            help="LLM client to configure (default: claude)")

    # Parse arguments
    args = parser.parse_args()
    # Handle commands
    if args.command == "init":
        # Get API key from arguments or authentication flow
        api_key = getattr(args, "api_key", None)
        auth_token = None
        if not api_key:
            auth_token = get_authentication_token()
            if not auth_token:
                # If no API key is provided and authentication fails, exit
                print("No API key provided and authentication failed.")
                sys.exit(1)

        # Run the init command and exit with its return code
        sys.exit(init_command(api_key, auth_token, args.client))
    elif args.command == "start":
        # Ensure protocol is set for the start command
        protocol = getattr(args, "protocol", "stdio")

        if getattr(args, "api_key", None):
            print(f"Using provided API key: {args.api_key[:10]}{'*' * (len(args.api_key)-10)}")
            app_config.set_auth_token(args.api_key, AuthMethod.API_KEY)

        elif os.getenv("SINGLESTORE_API_KEY"):
            print("Using API key from environment variable SINGLESTORE_API_KEY")
            app_config.set_auth_token(os.getenv("SINGLESTORE_API_KEY"), AuthMethod.API_KEY)

        if protocol == "sse":
            print(f"Running server with protocol {protocol.upper()} on port {args.port}")
            mcp.settings.port = args.port
        if protocol == "http":
            protocol = "streamable-http"
            print(f"Running server with protocol {protocol.upper()} on port {args.port}")
            mcp.settings.port = args.port
        else:
            print(f"Running server with protocol {protocol.upper()}")

        mcp.run(transport=protocol)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
