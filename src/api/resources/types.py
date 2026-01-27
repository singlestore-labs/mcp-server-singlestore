from dataclasses import dataclass
from typing import Callable, Optional

from src.api.types import MCPConcept


@dataclass()
class Resource(MCPConcept):
    func: Optional[Callable] = None
    uri: Optional[str] = None
