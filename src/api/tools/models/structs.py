"""
Structural models for SingleStore MCP server tools.

This module defines data structure models used within the tools.
"""

from dataclasses import dataclass
from typing import Callable, Optional

import singlestoredb.management.workspace as s2_wksp

from src.api.types import MCPConcept


@dataclass()
class Tool(MCPConcept):
    """Tool representation for MCP."""

    func: Callable = None


class WorkspaceTarget:
    """
    Wrapper class for workspace objects that includes additional metadata.
    """

    def __init__(
        self, workspace: s2_wksp.Workspace | s2_wksp.StarterWorkspace, is_shared: bool
    ):
        self.workspace = workspace
        self.is_shared = is_shared

    @property
    def endpoint(self) -> str:
        """Get the workspace endpoint."""
        return self.workspace.endpoint

    @property
    def name(self) -> str:
        """Get the workspace name."""
        return self.workspace.name

    @property
    def database_name(self) -> Optional[str]:
        """Get the database name (for virtual workspaces)."""
        if hasattr(self.workspace, "database_name"):
            return self.workspace.database_name
        return None
