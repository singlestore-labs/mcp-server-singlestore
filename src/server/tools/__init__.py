from s2_ai_tools.tools import tools_definitions

# Create dictionaries for compatibility with the rest of the code
# Since Tool objects aren't subscriptable, we need to convert them to dictionaries
tools_dicts = [
    {
        "name": tool.name,
        "description": tool.description,
        "func": tool.func,
        "inputSchema": tool.inputSchema
    }
    for tool in tools_definitions
]

# Export tool functions directly
tool_functions = {tool.name: tool.func for tool in tools_definitions}

# Export all for easy imports
__all__ = ["tools_definitions", "tools_dicts", "tool_functions"]
