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
    {"func": get_user_info},
    {"func": organization_info},
    {"func": choose_organization},
    {"func": set_organization},
    {"func": workspace_groups_info},
    {"func": workspaces_info},
    {"func": resume_workspace},
    {"func": list_starter_workspaces},
    {"func": create_starter_workspace},
    {"func": terminate_starter_workspace},
    {"func": list_regions},
    {"func": list_sharedtier_regions},
    {"func": run_sql},
    {"func": create_notebook_file},
    {"func": upload_notebook_file},
    {"func": create_job_from_notebook},
    {"func": get_job},
    {"func": delete_job},
]

# Export the tools
tools = [Tool.create_from_dict(tool) for tool in tools_definition]

__all__ = ["tools", "tools_definition"]
