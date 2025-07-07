"""
Data models for SingleStore MCP server tools.

This module provides the core data models used by the SingleStore MCP server tools.
These models are designed to provide a consistent interface for working with SingleStore
workspaces and other resources.

The models in this file are separate from the response models (in response_models.py)
and focus on the internal data structures needed by the tools.

For usage examples and more details, see the README.md in this directory.
"""

from dataclasses import dataclass
from typing import Optional, Union
import singlestoredb.management.workspace as s2_wksp


@dataclass
class WorkspaceTarget:
    """
    A wrapper for SingleStore workspace objects that provides additional metadata
    and a consistent interface for both regular and starter workspaces.

    This class abstracts the differences between regular workspaces and starter
    (virtual) workspaces, providing a unified way to access common properties.

    Args:
        workspace: Either a regular Workspace or StarterWorkspace instance
        is_shared: Whether this is a shared workspace (true for starter workspaces)

    Properties:
        endpoint: The connection endpoint for the workspace
        name: The display name of the workspace
        database_name: The database name (for virtual workspaces only)

    Example:
        ```python
        # Create a workspace target
        target = WorkspaceTarget(workspace=my_workspace, is_shared=True)

        # Access properties
        print(f"Connecting to {target.name} at {target.endpoint}")
        if target.is_shared:
            print(f"Using database: {target.database_name}")
        ```
    """

    workspace: Union[s2_wksp.Workspace, s2_wksp.StarterWorkspace]
    is_shared: bool

    @property
    def endpoint(self) -> str:
        """Get the workspace connection endpoint."""
        return self.workspace.endpoint

    @property
    def name(self) -> str:
        """Get the workspace display name."""
        return self.workspace.name

    @property
    def database_name(self) -> Optional[str]:
        """
        Get the database name for virtual workspaces.

        Returns:
            str: The database name for virtual workspaces
            None: For regular workspaces that don't have a specific database name
        """
        if hasattr(self.workspace, "database_name"):
            return self.workspace.database_name
        return None

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        workspace_type = "Shared" if self.is_shared else "Dedicated"
        return f"{workspace_type} Workspace '{self.name}' at {self.endpoint}"

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"WorkspaceTarget(name='{self.name}', "
            f"endpoint='{self.endpoint}', "
            f"is_shared={self.is_shared}, "
            f"database_name={self.database_name!r})"
        )
