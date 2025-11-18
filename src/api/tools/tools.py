"""Centralized tool definitions for SingleStore MCP server."""

from src.api.tools.types import Tool

# Import tools from organized directories
from src.api.tools.workspaces import (
    workspaces_info,
    resume_workspace,
    workspace_groups_info,
)
from src.api.tools.starter_workspaces import (
    list_starter_workspaces,
    create_starter_workspace,
    terminate_starter_workspace,
)
from src.api.tools.regions import list_regions, list_sharedtier_regions
from src.api.tools.database import run_sql
from src.api.tools.user import get_user_info
from src.api.tools.notebooks import (
    create_notebook_file,
    upload_notebook_file,
)
from src.api.tools.jobs import create_job_from_notebook, delete_job, get_job
from src.api.tools.organization import (
    organization_info,
    choose_organization,
    set_organization,
)

# Define the tools with their metadata
tools_definition = [
    {"tool": get_user_info},
    {"tool": organization_info},
    {"tool": choose_organization},
    {"tool": set_organization},
    {"tool": workspace_groups_info},
    {"tool": workspaces_info},
    {"tool": resume_workspace},
    {"tool": list_starter_workspaces},
    {"tool": create_starter_workspace},
    {"tool": terminate_starter_workspace},
    {"tool": list_regions},
    {"tool": list_sharedtier_regions},
    {"tool": run_sql},
    {"tool": create_notebook_file},
    {"tool": upload_notebook_file},
    {"tool": create_job_from_notebook},
    {"tool": get_job},
    {"tool": delete_job},
]

# Export the tools
tools = [Tool.create_from_dict(tool) for tool in tools_definition]

__all__ = ["tools", "tools_definition"]
