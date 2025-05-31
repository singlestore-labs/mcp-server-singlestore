from dataclasses import dataclass


@dataclass
class Tool:
    name: str
    description: str
    func: callable
