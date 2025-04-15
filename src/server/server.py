from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Optional
from mcp.server.fastmcp import FastMCP, Context

# Import tools from our definitions
from .tools import tools_dicts
from .tools.registration import register_tools

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
    mcp.run()

# Add this block to run the main function when the script is executed directly
if __name__ == "__main__":
    main()
