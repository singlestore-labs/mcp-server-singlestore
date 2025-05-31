from dataclasses import dataclass
from typing import Callable


@dataclass
class Tool:
    func: Callable
    deprecated: bool = False
