"""Starter workspaces tools for SingleStore MCP server."""

from .starter_workspaces import (
    list_virtual_workspaces,
    create_starter_workspace,
    terminate_virtual_workspace,
)

__all__ = [
    "list_virtual_workspaces",
    "create_starter_workspace",
    "terminate_virtual_workspace",
]
