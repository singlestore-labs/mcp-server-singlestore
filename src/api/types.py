from dataclasses import dataclass


@dataclass
class MCPConcept:
    """
    Represents an MCP concept (Tool, Resource, ...etc).

    Attributes:
        deprecated: Whether the concept is deprecated.
    """

    deprecated: bool = False
