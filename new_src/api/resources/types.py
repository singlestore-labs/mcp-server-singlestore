from dataclasses import dataclass
from typing import Callable

from new_src.api.types import MCPConcept


@dataclass(kw_only=True)
class Resource(MCPConcept):
    deprecated: bool
    func: Callable
    uri: str
