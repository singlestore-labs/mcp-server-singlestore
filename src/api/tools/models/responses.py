"""
Response models for SingleStore MCP server tools.

This module defines structured output models for the tool responses, ensuring
consistency across the API and enabling automatic schema generation.
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from pydantic import BaseModel, Field


class ToolMetadata(BaseModel):
    """Common metadata fields for tool responses."""

    execution_time_ms: Optional[float] = Field(
        None, description="Time taken to execute the tool in milliseconds"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO 8601 timestamp when the response was generated",
    )
    user_id: Optional[str] = Field(
        None, description="ID of the user who executed the tool"
    )


class ToolResponseBase(BaseModel):
    """Base model for all tool responses."""

    status: str = Field(
        ..., description="Status of the tool execution (success, error, warning)"
    )
    message: str = Field(
        ..., description="Human-readable message describing the result"
    )


T = TypeVar("T")


class ToolResponse(ToolResponseBase, Generic[T]):
    """
    Generic tool response model for SingleStore tools.

    This provides a consistent structure for all tool responses while allowing
    for type-specific data payloads.
    """

    data: Optional[T] = Field(None, description="The main payload of the response")
    metadata: Optional[ToolMetadata] = Field(
        None, description="Additional metadata about the execution"
    )
    error_code: Optional[str] = Field(
        None, description="Error code if status is 'error'"
    )
    error_details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details if status is 'error'"
    )
    warning_details: Optional[str] = Field(
        None, description="Warning details if status is 'warning'"
    )


# Specific data models for different tools


class Organization(BaseModel):
    """Organization information."""

    orgID: str = Field(..., description="Unique identifier for the organization")
    name: str = Field(..., description="Display name of the organization")


class GetOrganizationsData(BaseModel):
    """Data returned by get_organizations tool."""

    organizations: List[Organization] = Field(
        ..., description="List of available organizations"
    )
    count: int = Field(..., description="Number of organizations")
    instructions: Optional[str] = Field(
        None, description="Instructions for using the organizations"
    )


class OrganizationInfoData(BaseModel):
    """Data returned by organization_info tool."""

    organization: Organization = Field(
        ..., description="Current organization information"
    )


class SetOrganizationData(BaseModel):
    """Data returned by set_organization tool."""

    organization: Organization = Field(
        ..., description="Selected organization information"
    )
    previous_org_id: Optional[str] = Field(
        None, description="Previous organization ID before change"
    )
    operation: str = Field(
        ..., description="Operation performed (organization_set, etc.)"
    )
    errors: Optional[Dict[str, str]] = Field(
        None, description="Any errors encountered during validation"
    )


class Region(BaseModel):
    """Region information."""

    regionID: str = Field(..., description="Unique identifier for the region")
    provider: str = Field(..., description="Cloud provider (AWS, GCP, or Azure)")
    name: str = Field(..., description="Human-readable region name")


class RegionsData(BaseModel):
    """Data returned by list_of_regions tool."""

    regions: List[Region] = Field(..., description="List of available regions")


class VirtualWorkspace(BaseModel):
    """Virtual workspace information."""

    virtualWorkspaceID: str = Field(
        ..., description="Unique identifier for the workspace"
    )
    name: str = Field(..., description="Display name of the workspace")
    endpoint: str = Field(..., description="Connection endpoint URL")
    databaseName: str = Field(..., description="Name of the primary database")
    mysqlDmlPort: Optional[int] = Field(
        None, description="Port for MySQL protocol connections"
    )
    webSocketPort: Optional[int] = Field(
        None, description="Port for WebSocket connections"
    )
    state: str = Field(..., description="Current status of the workspace")


class VirtualWorkspacesData(BaseModel):
    """Data returned by list_virtual_workspaces tool."""

    workspaces: List[VirtualWorkspace] = Field(
        ..., description="List of virtual workspaces"
    )
    count: int = Field(..., description="Number of workspaces")


class WorkspaceGroup(BaseModel):
    """Workspace group information."""

    name: str = Field(..., description="Display name of the workspace group")
    deploymentType: str = Field(..., description="Type of deployment")
    state: str = Field(..., description="Current status")
    workspaceGroupID: str = Field(..., description="Unique identifier for the group")
    firewallRanges: List[str] = Field(..., description="Array of allowed IP ranges")
    createdAt: str = Field(..., description="Timestamp of group creation")
    regionID: str = Field(..., description="Identifier for deployment region")
    updateWindow: Dict[str, Any] = Field(
        ..., description="Maintenance window configuration"
    )


class WorkspaceGroupsData(BaseModel):
    """Data returned by workspace_groups_info tool."""

    workspace_groups: List[WorkspaceGroup] = Field(
        ..., description="List of workspace groups"
    )


class Workspace(BaseModel):
    """Workspace information."""

    createdAt: str = Field(..., description="Timestamp of workspace creation")
    deploymentType: str = Field(..., description="Type of deployment")
    endpoint: str = Field(..., description="Connection URL for database access")
    name: str = Field(..., description="Display name of the workspace")
    size: str = Field(..., description="Compute and storage configuration")
    state: str = Field(..., description="Current status")
    terminatedAt: Union[str, bool] = Field(
        ..., description="End timestamp if applicable"
    )
    workspaceGroupID: str = Field(..., description="Workspacegroup identifier")
    workspaceID: str = Field(..., description="Unique workspace identifier")


class WorkspacesData(BaseModel):
    """Data returned by workspaces_info tool."""

    workspaces: List[Workspace] = Field(..., description="List of workspaces")


class SqlResult(BaseModel):
    """SQL query result."""

    columns: List[str] = Field(..., description="Column names")
    rows: List[List[Any]] = Field(..., description="Data rows")
    row_count: int = Field(..., description="Number of rows returned")
    workspace_type: str = Field(
        ..., description="Type of workspace (shared or dedicated)"
    )
    workspace_name: str = Field(..., description="Name of the workspace")


class CreateStarterWorkspaceResponse(BaseModel):
    """Response for create_starter_workspace tool."""

    status: str = Field(..., description="Status of the operation")
    message: str = Field(..., description="Human-readable message")
    workspace_id: Optional[str] = Field(None, description="ID of the created workspace")
    name: Optional[str] = Field(None, description="Name of the created workspace")
    endpoint: Optional[str] = Field(
        None, description="Endpoint of the created workspace"
    )
    database_name: Optional[str] = Field(
        None, description="Database name of the created workspace"
    )
    error: Optional[str] = Field(None, description="Error message if status is error")


class TerminateVirtualWorkspaceResponse(BaseModel):
    """Response for terminate_virtual_workspace tool."""

    status: str = Field(..., description="Status of the operation")
    message: str = Field(..., description="Human-readable message")
    workspace_id: str = Field(..., description="ID of the terminated workspace")
    workspace_name: Optional[str] = Field(
        None, description="Name of the terminated workspace"
    )
    termination_time: Optional[str] = Field(None, description="Time of termination")
    error: Optional[str] = Field(None, description="Error message if status is error")


# User ID response model
class UserIDData(BaseModel):
    """Data returned by get_user_id tool."""

    user_id: str = Field(..., description="Unique identifier for the current user")


# Type aliases for commonly used response types
OrganizationsResponse = ToolResponse[GetOrganizationsData]
SetOrganizationResponse = ToolResponse[SetOrganizationData]
OrganizationInfoResponse = ToolResponse[OrganizationInfoData]
RegionsResponse = ToolResponse[RegionsData]
VirtualWorkspacesResponse = ToolResponse[VirtualWorkspacesData]
WorkspaceGroupsResponse = ToolResponse[WorkspaceGroupsData]
WorkspacesResponse = ToolResponse[WorkspacesData]
SqlResponse = ToolResponse[SqlResult]
UserIDResponse = ToolResponse[UserIDData]
