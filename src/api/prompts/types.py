from dataclasses import dataclass
from typing import Callable

from src.api.types import MCPConcept


@dataclass()
class Prompt(MCPConcept):
    func: Callable = None
