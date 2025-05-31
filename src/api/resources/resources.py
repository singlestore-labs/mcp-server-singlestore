from dataclasses import dataclass


@dataclass
class Resource:
    name: str
    description: str
    func: callable
    uri: str


resources_definitions = []

resources = [
    Resource(
        name=resource["name"],
        description=resource["description"],
        func=resource["func"],
        uri=resource["uri"],
    )
    for resource in resources_definitions
]
