from dataclasses import dataclass
from typing import Callable

import singlestoredb.management.workspace as s2_wksp

from src.api.types import MCPConcept, MCPConceptFlags, AVAILABLE_FLAGS


@dataclass()
class Tool(MCPConcept):
    func: Callable = None

    @classmethod
    def create_from_dict(cls, tool_def: dict):
        """
        Create a Tool instance from a dictionary definition.

        Args:
            tool_def: Dictionary with 'func' and optional flag keys

        Example:
            {"func": my_function, "private": True, "experimental": True, "remote": True}
        """
        func = tool_def["func"]
        title = getattr(func, "__name__", "")

        # Build flags dynamically from AVAILABLE_FLAGS
        flags = MCPConceptFlags.NONE
        for flag_name in AVAILABLE_FLAGS:
            if tool_def.get(flag_name, False):
                flag_enum = getattr(MCPConceptFlags, flag_name.upper())
                flags |= flag_enum

        return cls(title=title, flags=flags, func=func)


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
    def database_name(self) -> str:
        """Get the database name (for virtual workspaces)."""
        if hasattr(self.workspace, "database_name"):
            return self.workspace.database_name
        return None
