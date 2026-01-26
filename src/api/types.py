from dataclasses import dataclass

from src.api.context import tool_wrapper


@dataclass
class MCPConcept:
    """
    Represents an MCP concept (Tool, Resource, Prompt).

    Attributes:
        title: The title/name of the concept.
        disabled: Optional flag indicating if the concept is disabled.
    """

    title: str = ""
    disabled: bool | None = False

    @classmethod
    def create_from_dict(cls, concept_def: dict):
        """
        Create an MCPConcept instance from a dictionary definition.

        Args:
            concept_def: Dictionary with concept attributes and optional flag keys

        Example:
            {"func": my_function, "disabled": True}
            {"title": "my_resource", "uri": "resource://example", "disabled": True}
        """
        # Extract non-flag attributes for the concept
        concept_attrs = {}
        for key, value in concept_def.items():
            concept_attrs[key] = value

        if "tool" in concept_attrs:
            concept_attrs["func"] = tool_wrapper(concept_attrs["tool"])
            del concept_attrs["tool"]

        # Set title if not explicitly provided and we have a function
        if "title" not in concept_attrs and "func" in concept_attrs:
            concept_attrs["title"] = getattr(concept_attrs["func"], "__name__", "")

        return cls(**concept_attrs)
