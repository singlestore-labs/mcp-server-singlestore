from src.api.resources.types import Resource


resources_definitions = []

# Export the resources using create_from_dict for consistency
resources = [Resource.create_from_dict(resource) for resource in resources_definitions]
