from s2_ai_tools import tools_definitions

# Export the individual tool functions directly - for use with fastmcp.tool decorators
tool_functions = {tool["name"]: tool["func"] for tool in tools_definitions}

# We no longer need to explicitly create mcp.types.Tool objects as FastMCP will handle
# tool registration and schema generation based on function signatures and docstrings.
# The tools list can be removed or kept for backward compatibility if needed.
