"""Centralized tool definitions for SingleStore MCP server."""

from src.api.tools.types import Tool

# Import tools from organized directories
from src.api.tools.workspaces import workspaces_info
from src.api.tools.workspace_groups import workspace_groups_info
from src.api.tools.starter_workspaces import (
    list_virtual_workspaces,
    create_starter_workspace,
    terminate_virtual_workspace,
)
from src.api.tools.regions import list_regions
from src.api.tools.database import run_sql
from src.api.tools.user import get_user_id
from src.api.tools.notebooks import (
    create_notebook_file,
    list_shared_files,
    upload_notebook_file,
)
from src.api.tools.organization import (
    organization_info,
    choose_organization,
    set_organization,
)

# Define the tools with their metadata
tools_definition = [
    {"func": get_user_id},
    {"func": organization_info},
    {"func": choose_organization},
    {"func": set_organization},
    {"func": workspace_groups_info},
    {"func": workspaces_info},
    {"func": list_virtual_workspaces},
    {"func": create_starter_workspace, "internal": True},
    {"func": terminate_virtual_workspace},
    {"func": list_regions},
    {"func": run_sql},
    {"func": create_notebook_file},
    {"func": upload_notebook_file},
    {"func": list_shared_files, "internal": True},
]

# Export the tools
tools = [Tool.create_from_dict(tool) for tool in tools_definition]

__all__ = ["tools", "tools_definition"]
