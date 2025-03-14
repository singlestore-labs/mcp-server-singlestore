import mcp.types as types
from .definitions import tools_definitions

# Export the tools
tools = [
    types.Tool(
        name=tool["name"],
        description=tool["description"],
        inputSchema=tool["inputSchema"]
    )
    for tool in tools_definitions
]

# Map tool functions by name for execution
tool_functions = {tool["name"]: tool["func"] for tool in tools_definitions}
