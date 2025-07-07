"""
Models for the SingleStore MCP server tools.

This package contains models used by the SingleStore MCP server tools:
- responses: Response models returned by tool functions
- structs: Data structure models used within the tools
"""

from src.api.tools.models.responses import (
    ToolMetadata,
    ToolResponse,
    ToolResponseBase,
    # Organization models
    Organization,
    GetOrganizationsData,
    OrganizationsResponse,
    OrganizationInfoData,
    OrganizationInfoResponse,
    SetOrganizationData,
    SetOrganizationResponse,
    # User models
    UserIDData,
    UserIDResponse,
    # Region models
    Region,
    RegionsData,
    RegionsResponse,
    # Workspace models
    Workspace,
    WorkspacesData,
    WorkspacesResponse,
    WorkspaceGroup,
    WorkspaceGroupsData,
    WorkspaceGroupsResponse,
    VirtualWorkspace,
    VirtualWorkspacesData,
    VirtualWorkspacesResponse,
    CreateStarterWorkspaceResponse,
    TerminateVirtualWorkspaceResponse,
    # SQL models
    SqlResult,
    SqlResponse,
)

from src.api.tools.models.structs import WorkspaceTarget, Tool

__all__ = [
    # Response models
    "ToolMetadata",
    "ToolResponse",
    "ToolResponseBase",
    # Organization models
    "Organization",
    "GetOrganizationsData",
    "OrganizationsResponse",
    "OrganizationInfoData",
    "OrganizationInfoResponse",
    "SetOrganizationData",
    "SetOrganizationResponse",
    # User models
    "UserIDData",
    "UserIDResponse",
    # Region models
    "Region",
    "RegionsData",
    "RegionsResponse",
    # Workspace models
    "Workspace",
    "WorkspacesData",
    "WorkspacesResponse",
    "WorkspaceGroup",
    "WorkspaceGroupsData",
    "WorkspaceGroupsResponse",
    "VirtualWorkspace",
    "VirtualWorkspacesData",
    "VirtualWorkspacesResponse",
    "CreateStarterWorkspaceResponse",
    "TerminateVirtualWorkspaceResponse",
    # SQL models
    "SqlResult",
    "SqlResponse",
    # Struct models
    "WorkspaceTarget",
    "Tool",
]
