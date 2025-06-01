from dataclasses import dataclass
from typing import Callable

from src.api.types import MCPConcept


@dataclass(kw_only=True)
class Resource(MCPConcept):
    deprecated: bool
    func: Callable
    uri: str
