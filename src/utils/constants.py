from enum import Enum
from typing import List


class TransportType(Enum):
    """Transport protocols supported by the MCP server."""

    STDIO = "stdio"
    # SSE = "sse"
    # STREAMABLE_HTTP = "streamable-http"

    @classmethod
    def choices(cls) -> List[str]:
        """Return list of transport choices for Click options."""
        return [transport.value for transport in cls]

    @classmethod
    def default(cls) -> "TransportType":
        """Return the default transport type."""
        return cls.STDIO.value


class ClientType(Enum):
    """LLM clients that the MCP server can configure."""

    CLAUDE = "claude"
    CURSOR = "cursor"

    @classmethod
    def choices(cls) -> List[str]:
        """Return list of client choices for Click options."""
        return [client.value for client in cls]

    @classmethod
    def default(cls) -> "ClientType":
        """Return the default client type."""
        return cls.CLAUDE.value
