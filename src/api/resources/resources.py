from pathlib import Path
from src.api.resources.types import Resource


def get_singlestore_drizzle_guide() -> str:
    """
    SingleStore and Drizzle ORM Integration Guide

    Provides comprehensive documentation for integrating SingleStore database
    with Drizzle ORM. This guide covers integration patterns, best practices,
    performance optimizations, and practical examples for building applications
    with SingleStore's high-performance capabilities using Drizzle ORM.

    The content includes setup instructions, configuration examples, and
    implementation guidance for effective SingleStore + Drizzle integration.
    """
    current_dir = Path(__file__).parent
    docs_path = current_dir / "docs" / "singlestore-drizzle.mdc"

    try:
        with open(docs_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "SingleStore Drizzle integration guide not found."


resources_definitions = [
    {
        "title": "SingleStore + Drizzle ORM Integration Guide",
        "func": get_singlestore_drizzle_guide,
        "uri": "docs://singlestore/drizzle-integration",
    }
]

# Export the resources using create_from_dict for consistency
resources = [Resource.create_from_dict(resource) for resource in resources_definitions]
