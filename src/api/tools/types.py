from dataclasses import dataclass
from typing import Callable

from src.api.types import MCPConcept


@dataclass(kw_only=True)
class Tool(MCPConcept):
    deprecated: bool
    func: Callable
