from src.utils.types import Resource


resources_definitions = [
    
]

resources = [
    Resource(
        name=resource["name"],
        description=resource["description"],
        func=resource["func"],
        uri=resource["uri"],
    )
    for resource in resources_definitions
]