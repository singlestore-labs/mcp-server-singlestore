from dataclasses import dataclass
from typing import Callable

from src.api.types import MCPConcept


@dataclass()
class Tool(MCPConcept):
    func: Callable = None
