"""Notebook tools for SingleStore MCP server."""

import json
import jsonschema
import os
import tempfile
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import nbformat as nbf
import nbformat.v4 as nbfv4

from mcp.server.fastmcp import Context

from src.config import config
from src.api.common import build_request, get_org_id
from src.logger import get_logger

# Set up logger for this module
logger = get_logger()

SAMPLE_NOTEBOOK_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "sample_notebook.ipynb"
)


def _get_notebook_schema() -> dict:
    """
    Get the Jupyter notebook schema by loading it from the notebook-schema.json file.

    Returns:
        Dictionary containing the notebook schema

    Raises:
        FileNotFoundError: If the schema file cannot be found
        json.JSONDecodeError: If the schema file is not valid JSON
    """
    # Path to the schema file relative to this module
    schema_file_path = os.path.join(os.path.dirname(__file__), "notebook-schema.json")

    try:
        with open(schema_file_path, "r") as f:
            schema = json.load(f)
        return schema
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Notebook schema file not found at {schema_file_path}. "
            "Please ensure the notebook-schema.json file exists in the tools directory."
        )
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in schema file {schema_file_path}: {str(e)}", e.doc, e.pos
        )


def __create_file_in_shared_space(
    path: str, content: Optional[Dict[str, Any]] = None, access_token: str = None
) -> Dict[str, Any]:
    """
    Create a new file (such as a notebook) in the user's shared space.

    Args:
        path: Path to the file to create
        content: Optional JSON object with a 'cells' field containing an array of objects.
                 Each object must have 'type' (markdown or code) and 'content' fields.
                 If None, a sample notebook will be created for .ipynb files.
    """
    import singlestoredb as s2

    settings = config.get_settings()

    org_id = get_org_id()

    file_manager = s2.manage_files(
        access_token=access_token,
        base_url=settings.s2_api_base_url,
        organization_id=org_id,
    )

    # Check if it's a notebook
    if path.endswith(".ipynb"):
        nb = nbfv4.new_notebook()
        nb["cells"] = []

        if content and "cells" in content:
            for cell in content["cells"]:
                if cell["type"] == "markdown":
                    nb["cells"].append(nbfv4.new_markdown_cell(cell["content"]))
                elif cell["type"] == "code":
                    nb["cells"].append(nbfv4.new_code_cell(cell["content"]))
                else:
                    raise ValueError(
                        f"Invalid cell type: {cell['type']}. Only 'markdown' and 'code' are supported."
                    )
        else:
            # Create a sample notebook with SingleStore connectivity example
            nb["cells"] = [
                nbfv4.new_markdown_cell(
                    "# SingleStore Sample Notebook\n\nThis notebook demonstrates how to connect to a SingleStore database and run queries."
                ),
                nbfv4.new_code_cell(
                    "import singlestoredb as s2\n\n# Connect to your database\nconn = s2.connect('hostname', user='username', password='password', database='database')"
                ),
                nbfv4.new_code_cell(
                    "result = conn.execute('SELECT * FROM your_table LIMIT 10')\n\nfor row in result:\n    print(row)"
                ),
                nbfv4.new_code_cell("conn.close()"),
            ]

        # Write notebook to file
        with open(SAMPLE_NOTEBOOK_PATH, "w") as f:
            nbf.write(nb, f)
    else:
        # For non-notebook files, just write an empty file
        with open(SAMPLE_NOTEBOOK_PATH, "w") as f:
            f.write("")

    # Upload the file using the SDK method
    file_info = file_manager.shared_space.upload_file(SAMPLE_NOTEBOOK_PATH, path)

    return {
        "status": "success",
        "message": f"File {path} created successfully",
        "path": file_info.path,
        "type": file_info.type,
        "format": file_info.format,
    }


def create_notebook_file(ctx: Context, content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call this tool to create a Jupyter notebook file.

    This tool validates the provided content and creates a properly formatted .ipynb file
    in a temporary location. The content is converted from the simplified format
    to the full Jupyter notebook format.

    Args:
        content: Notebook content in the format: {
            "cells": [
                {"type": "markdown", "content": "Markdown content here"},
                {"type": "code", "content": "Python code here"}
            ]
        }

    Returns:
        Dictionary with the temporary file path and validation status

    Example:
        content = {
            "cells": [
                {"type": "markdown", "content": "# My Notebook\nThis is a sample notebook"},
                {"type": "code", "content": "import pandas as pd\nprint('Hello World')"}
            ]
        }
    """
    settings = config.get_settings()
    user_id = config.get_user_id()
    settings.analytics_manager.track_event(
        user_id,
        "tool_calling",
        {"name": "create_notebook_file"},
    )

    start_time = time.time()

    try:
        # Validate content structure
        if not isinstance(content, dict):
            return {
                "status": "error",
                "message": "Content must be a dictionary",
                "error_code": "INVALID_CONTENT_TYPE",
            }

        if "cells" not in content:
            return {
                "status": "error",
                "message": "Content must contain a 'cells' field",
                "error_code": "MISSING_CELLS_FIELD",
            }

        if not isinstance(content["cells"], list):
            return {
                "status": "error",
                "message": "Cells field must be an array",
                "error_code": "INVALID_CELLS_TYPE",
            }

        # Convert simplified format to full Jupyter notebook format
        notebook_cells = []
        for i, cell in enumerate(content["cells"]):
            if not isinstance(cell, dict):
                return {
                    "status": "error",
                    "message": f"Cell {i} must be a dictionary",
                    "error_code": "INVALID_CELL_TYPE",
                }

            if "type" not in cell or "content" not in cell:
                return {
                    "status": "error",
                    "message": f"Cell {i} must have 'type' and 'content' fields",
                    "error_code": "MISSING_CELL_FIELDS",
                }

            cell_type = cell["type"]
            cell_content = cell["content"]

            if cell_type not in ["markdown", "code"]:
                return {
                    "status": "error",
                    "message": f"Cell {i} type must be 'markdown' or 'code', got '{cell_type}'",
                    "error_code": "INVALID_CELL_TYPE_VALUE",
                }

            # Create cell ID
            cell_id = str(uuid.uuid4())[:8]

            if cell_type == "markdown":
                notebook_cell = {
                    "id": cell_id,
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": [cell_content],
                }
            else:  # code cell
                notebook_cell = {
                    "id": cell_id,
                    "cell_type": "code",
                    "metadata": {},
                    "source": [cell_content],
                    "outputs": [],
                    "execution_count": None,
                }

            notebook_cells.append(notebook_cell)

        # Create full notebook structure
        notebook_content = {
            "nbformat": 4,
            "nbformat_minor": 5,
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                },
                "language_info": {
                    "name": "python",
                    "version": "3.8.0",
                    "mimetype": "text/x-python",
                    "codemirror_mode": {"name": "ipython", "version": 3},
                    "pygments_lexer": "ipython3",
                    "file_extension": ".py",
                },
            },
            "cells": notebook_cells,
        }

        # Load and validate against Jupyter notebook schema
        try:
            # Load schema from external file
            schema = _get_notebook_schema()

            # Validate notebook content against schema
            jsonschema.validate(notebook_content, schema)
            logger.info("Notebook content validated successfully against schema file")
            schema_validated = True

        except FileNotFoundError as e:
            logger.warning(f"Schema file not found: {str(e)}")
            # Continue without validation if schema file is missing
            schema_validated = False
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in schema file: {str(e)}")
            return {
                "status": "error",
                "message": f"Schema file contains invalid JSON: {str(e)}",
                "error_code": "INVALID_SCHEMA_FILE",
                "error_details": {"json_error": str(e)},
            }
        except jsonschema.ValidationError as e:
            return {
                "status": "error",
                "message": f"Notebook content validation failed: {e.message}",
                "error_code": "SCHEMA_VALIDATION_FAILED",
                "error_details": {"validation_error": str(e)},
            }
        except Exception as e:
            logger.warning(f"Schema validation failed: {str(e)}")
            # Continue without validation if schema can't be loaded
            schema_validated = False

        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".ipynb",
            prefix="notebook_",
            delete=False,
        )

        try:
            # Write notebook content to temporary file
            json.dump(notebook_content, temp_file, indent=2)
            temp_file_path = temp_file.name
        finally:
            temp_file.close()

        execution_time = (time.time() - start_time) * 1000

        return {
            "status": "success",
            "message": "Notebook file created successfully at temporary location",
            "data": {
                "temp_file_path": temp_file_path,
                "cell_count": len(notebook_cells),
                "schema_validated": schema_validated,
                "notebook_format": {"nbformat": 4, "nbformat_minor": 5},
            },
            "metadata": {
                "execution_time_ms": round(execution_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "temp_file_size": os.path.getsize(temp_file_path),
            },
        }

    except Exception as e:
        logger.error(f"Error creating notebook file: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to create notebook file: {str(e)}",
            "error_code": "NOTEBOOK_CREATION_FAILED",
            "error_details": {"exception_type": type(e).__name__},
        }


def check_if_file_exists(file_name: str, access_token: str = None) -> Dict[str, Any]:
    """
    Check if a file (notebook) exists in the user's shared space.

    Args:
        file_name: Name of the file to check (with or without .ipynb extension)

    Returns:
        Standardized response with file existence status
    """
    import singlestoredb as s2

    settings = config.get_settings()
    user_id = config.get_user_id()
    settings.analytics_manager.track_event(
        user_id,
        "tool_calling",
        {"name": "check_if_file_exists", "file_name": file_name},
    )
    org_id = get_org_id()
    file_manager = s2.manage_files(
        access_token=access_token,
        base_url=settings.s2_api_base_url,
        organization_id=org_id,
    )
    exists = file_manager.shared_space.exists(file_name)

    # Return using the new standardized response builder
    message = f"File {file_name} {'exists' if exists else 'does not exist'}"
    return {
        "status": "success",
        "message": message,
        "data": {"exists": exists, "file_name": file_name},
        "metadata": {"checked_at": datetime.now().isoformat()},
    }


def list_shared_files() -> Dict[str, Any]:
    """
    List all files and notebooks in your shared SingleStore space.

    Returns file object meta data for each file:
    - name: Name of the file (e.g., 'analysis.ipynb')
    - path: Full path in shared space (e.g., 'folder/analysis.ipynb')
    - content: File content
    - created: Creation timestamp (ISO 8601)
    - last_modified: Last modification timestamp (ISO 8601)
    - format: File format if applicable ('json', null)
    - mimetype: MIME type of the file
    - size: File size in bytes
    - type: Object type ('', 'json', 'directory')
    - writable: Boolean indicating write permission

    Use this tool to:
    1. List workspace contents and structure
    2. Verify file existence before operations
    3. Check file timestamps and sizes
    4. Determine file permissions
    """
    start_time = time.time()
    files_data = build_request("GET", "files/fs/shared")

    # Calculate file statistics
    total_size = sum(f.get("size", 0) for f in files_data.get("content", []))
    file_types = {}
    mime_types = {}

    for file_info in files_data.get("content", []):
        file_type = file_info.get("type", "unknown")
        file_types[file_type] = file_types.get(file_type, 0) + 1

        mime_type = file_info.get("mimetype", "unknown")
        mime_types[mime_type] = mime_types.get(mime_type, 0) + 1

    execution_time = (time.time() - start_time) * 1000

    return {
        "status": "success",
        "message": f"Retrieved {len(files_data.get('content', []))} files from shared space",
        "data": {
            "result": files_data,
        },
        "metadata": {
            "execution_time_ms": round(execution_time, 2),
            "file_count": len(files_data.get("content", [])),
            "total_size_bytes": total_size,
            "file_type_summary": file_types,
            "mime_type_summary": mime_types,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
