import os
import re

from enum import Enum
from typing import List, Optional, Dict, Any
import json
import nbformat as nbf
import nbformat.v4 as nbfv4

import src.config.config as config
from src.utils.common import (
    __build_request,
    __get_project_id,
    __get_user_id,
    __get_workspace_endpoint,
    __query_graphql_organizations,
)
import singlestoredb as s2


def get_user_id() -> str:
    """
    Retrieve the current user's unique identifier.

    Returns:
        str: UUID format identifier for the current user

    Required for:
    - Constructing paths or references to personal resources

    Performance Tip:
    Cache the returned ID when making multiple API calls.
    """
    return __get_user_id(config.settings)


def filter_tools(
    tools_list: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Filter out the login and refresh_token tools from the public API.

    These tools will still be available internally but will be hidden from
    the user as they'll be handled automatically by the auth middleware.

    Args:
        tools_list: List of Tool objects

    Returns:
        List of Tool objects with login and refresh_token removed
    """
    excluded_tools = ["login", "refresh_auth_token"]

    return [tool for tool in tools_list if tool["name"] not in excluded_tools]


""" set_organization,
    execute_sql,
    create_virtual_workspace,
    execute_sql_on_virtual_workspace,
    create_notebook,
    create_scheduled_job,
    get_organizations,
    workspace_groups_info,
    workspaces_info,
    list_of_regions,
    list_virtual_workspaces,
    organization_billing_usage,
    list_notebook_samples,
    list_shared_files,
    get_job_details,
    list_job_executions,
    get_notebook_path,
    get_project_id, """

# Export the tools
tools = [
    get_user_id,
    # check_if_file_exists,
]
