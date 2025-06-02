from dataclasses import dataclass
from typing import Callable

from src.api.types import MCPConcept


@dataclass()
class Resource(MCPConcept):
    func: Callable = None
    uri: str = None
