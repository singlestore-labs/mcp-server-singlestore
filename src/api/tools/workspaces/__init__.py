"""Workspaces tools for SingleStore MCP server."""

from .workspaces import workspaces_info
from .workspace_groups import workspace_groups_info

__all__ = ["workspaces_info", "workspace_groups_info"]
