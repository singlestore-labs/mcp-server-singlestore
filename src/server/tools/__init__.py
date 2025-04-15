from .definitions import tools

# Create dictionaries for compatibility with the rest of the code
# Since Tool objects aren't subscriptable, we need to convert them to dictionaries
tools_dicts = [
    {
        "name": tool.name,
        "description": tool.description,
        "func": tool.func,
        "inputSchema": tool.inputSchema
    }
    for tool in tools
]

# Export all for easy imports
__all__ = ["tools_dicts"]
