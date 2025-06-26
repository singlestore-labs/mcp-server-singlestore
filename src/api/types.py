from dataclasses import dataclass
from enum import Flag, auto
from typing import Set


# Define all possible flags here - ADD NEW FLAGS TO THIS LIST ONLY!
AVAILABLE_FLAGS = ["deprecated", "internal"]


def _create_flag_enum():
    """Dynamically create MCPConceptFlags enum from AVAILABLE_FLAGS list."""
    flag_dict = {"NONE": 0}

    for flag_name in AVAILABLE_FLAGS:
        flag_dict[flag_name.upper()] = auto()

    return Flag("MCPConceptFlags", flag_dict)


# Dynamically generated enum
MCPConceptFlags = _create_flag_enum()


@dataclass
class MCPConcept:
    """
    Represents an MCP concept (Tool, Resource, ...etc).

    Attributes:
        title: The title/name of the concept.
        flags: Bitwise flags indicating concept properties.
    """

    title: str = ""
    flags: MCPConceptFlags = MCPConceptFlags.NONE

    def has_flag(self, flag_name: str) -> bool:
        """Check if concept has a specific flag by name."""
        try:
            flag_enum = getattr(MCPConceptFlags, flag_name.upper())
            return flag_enum in self.flags
        except AttributeError:
            return False

    def get_flag_names(self) -> Set[str]:
        """Get all flag names that are set on this concept."""
        flag_names = set()
        for flag_name in AVAILABLE_FLAGS:
            if self.has_flag(flag_name):
                flag_names.add(flag_name)
        return flag_names

    # Dynamic properties for backward compatibility
    def __getattr__(self, name):
        if name in AVAILABLE_FLAGS:
            return self.has_flag(name)
        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )

    @classmethod
    def create_from_dict(cls, concept_def: dict):
        """
        Create an MCPConcept instance from a dictionary definition.

        Args:
            concept_def: Dictionary with concept attributes and optional flag keys

        Example:
            {"func": my_function, "internal": True, "deprecated": True}
            {"title": "my_resource", "uri": "resource://example", "internal": True}
        """
        # Extract non-flag attributes for the concept
        concept_attrs = {}
        for key, value in concept_def.items():
            if key not in AVAILABLE_FLAGS:
                concept_attrs[key] = value

        # Build flags dynamically from AVAILABLE_FLAGS
        flags = MCPConceptFlags.NONE
        for flag_name in AVAILABLE_FLAGS:
            if concept_def.get(flag_name, False):
                flag_enum = getattr(MCPConceptFlags, flag_name.upper())
                flags |= flag_enum

        # Set title if not explicitly provided and we have a function
        if "title" not in concept_attrs and "func" in concept_attrs:
            concept_attrs["title"] = getattr(concept_attrs["func"], "__name__", "")

        concept_attrs["flags"] = flags
        return cls(**concept_attrs)
