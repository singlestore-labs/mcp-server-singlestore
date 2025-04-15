from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
import argparse
import sys
import os
from mcp.server.fastmcp import FastMCP

# Import tools from our definitions
from .tools import tools_dicts
from .tools.registration import register_tools
from .init import init_command

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
        pass

# Create FastMCP server instance with lifespan
mcp = FastMCP(
    "SingleStore MCP Server", 
    lifespan=app_lifespan,
    dependencies=["mcp-server", "singlestoredb"]
)

# Register all tools using the registration module
register_tools(mcp, tools_dicts)

def main():
    # Set up command-line parser
    parser = argparse.ArgumentParser(description="SingleStore MCP Server")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Add start command (default behavior when no command is provided)
    start_parser = subparsers.add_parser("start", help="Start the MCP server")
    start_parser.add_argument("api_key", help="SingleStore API key")
    
    # Add init command
    init_parser = subparsers.add_parser("init", help="Initialize client configuration")
    init_parser.add_argument("api_key", help="SingleStore API key")
    init_parser.add_argument("--client", default="claude", 
                            choices=["claude", "cursor", "windsurf", "copilot"],
                            help="LLM client to configure (default: claude)")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle commands
    if args.command == "init":
        # Run the init command and exit with its return code
        sys.exit(init_command(args.api_key, args.client))
    elif args.command == "start" or args.command is None:
        # When no command is provided, default to running the server
        # with the API key if provided
        if getattr(args, "api_key", None):
            os.environ["SINGLESTORE_API_KEY"] = args.api_key
        mcp.run()
    else:
        parser.print_help()
        sys.exit(1)

# Add this block to run the main function when the script is executed directly
if __name__ == "__main__":
    main()
