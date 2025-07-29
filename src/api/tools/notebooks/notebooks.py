"""Notebook tools for SingleStore MCP server."""

import json
import jsonschema
import os
import tempfile
import time
import uuid
import singlestoredb as s2

from datetime import datetime, timezone
from typing import Any, Dict, Optional

import nbformat as nbf
import nbformat.v4 as nbfv4
from pydantic import BaseModel

from mcp.server.fastmcp import Context

from src.config import config
from src.api.common import build_request, get_access_token, get_org_id
from src.logger import get_logger
from src.utils.elicitation import try_elicitation

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


def _validate_content_structure(content: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validate the basic structure of the content dictionary.

    Returns:
        None if validation passes, error dict if validation fails
    """
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

    return None


def _convert_to_notebook_cells(cells: list) -> tuple[list, Optional[Dict[str, Any]]]:
    """
    Convert simplified cell format to full Jupyter notebook cell format.

    Returns:
        Tuple of (notebook_cells, error_dict). error_dict is None if successful.
    """
    notebook_cells = []

    for i, cell in enumerate(cells):
        if not isinstance(cell, dict):
            return [], {
                "status": "error",
                "message": f"Cell {i} must be a dictionary",
                "error_code": "INVALID_CELL_TYPE",
            }

        if "type" not in cell or "content" not in cell:
            return [], {
                "status": "error",
                "message": f"Cell {i} must have 'type' and 'content' fields",
                "error_code": "MISSING_CELL_FIELDS",
            }

        cell_type = cell["type"]
        cell_content = cell["content"]

        if cell_type not in ["markdown", "code"]:
            return [], {
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

    return notebook_cells, None


def _create_notebook_structure(notebook_cells: list) -> Dict[str, Any]:
    """
    Create the full Jupyter notebook structure.

    Returns:
        Complete notebook dictionary ready for serialization
    """
    return {
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


def _validate_notebook_schema(
    notebook_content: Dict[str, Any],
) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    Validate notebook content against Jupyter notebook schema.

    Returns:
        Tuple of (schema_validated, error_dict). error_dict is None if successful or skipped.
    """
    try:
        # Load schema from external file
        schema = _get_notebook_schema()

        # Validate notebook content against schema
        jsonschema.validate(notebook_content, schema)
        logger.info("Notebook content validated successfully against schema file")
        return True, None

    except FileNotFoundError as e:
        logger.warning(f"Schema file not found: {str(e)}")
        # Continue without validation if schema file is missing
        return False, None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in schema file: {str(e)}")
        return False, {
            "status": "error",
            "message": f"Schema file contains invalid JSON: {str(e)}\nPlease call create_notebook_file tool to create a jupyter notebook in the correct format",
            "error_code": "INVALID_SCHEMA_FILE",
            "error_details": {"json_error": str(e)},
        }
    except jsonschema.ValidationError as e:
        return False, {
            "status": "error",
            "message": f"Notebook content validation failed: {e.message}",
            "error_code": "SCHEMA_VALIDATION_FAILED",
            "error_details": {"validation_error": str(e)},
        }
    except Exception as e:
        logger.warning(f"Schema validation failed: {str(e)}")
        # Continue without validation if schema can't be loaded
        return False, None


def create_notebook_file(ctx: Context, content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a Jupyter notebook file in the correct singlestore format and saves it to a temporary location.

    This tool validates the provided content against the Jupyter notebook schema and creates a properly
    formatted .ipynb file in a temporary location. The content is converted from the simplified format
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
        content_error = _validate_content_structure(content)
        if content_error:
            return content_error

        # Convert simplified format to full Jupyter notebook format
        notebook_cells, cells_error = _convert_to_notebook_cells(content["cells"])
        if cells_error:
            return cells_error

        # Create full notebook structure
        notebook_content = _create_notebook_structure(notebook_cells)

        # Validate against Jupyter notebook schema
        schema_validated, schema_error = _validate_notebook_schema(notebook_content)
        if schema_error:
            return schema_error

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


def _check_if_file_exists(file_name: str, location: str = "shared") -> bool:
    """
    Check if a file exists in the user's shared or personal space.

    Args:
        file_name: Name of the file to check (with or without .ipynb extension)
        location: Location to check ("shared" or "personal")

    Returns:
        Boolean indicating whether the file exists
    """
    settings = config.get_settings()
    org_id = get_org_id()
    access_token = get_access_token()

    file_manager = s2.manage_files(
        access_token=access_token,
        base_url=settings.s2_api_base_url,
        organization_id=org_id,
    )

    if location == "shared":
        return file_manager.shared_space.exists(file_name)
    else:  # personal
        try:
            return file_manager.personal_space.exists(file_name)
        except AttributeError:
            # If personal space is not supported, return False
            logger.warning("Personal space not supported by SDK")
            return False


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


class UploadLocation(BaseModel):
    """Schema for upload location elicitation."""

    location: str  # "shared" or "personal"


class UploadName(BaseModel):
    """Schema for upload name elicitation."""

    name: str  # Name for the uploaded file


async def upload_notebook_file(
    ctx: Context,
    local_path: str,
    upload_name: Optional[str] = None,
    upload_location: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Upload a notebook file from a local local_path to SingleStore shared or personal space.

    This tool validates the notebook schema before uploading. If upload_name or upload_location
    are not provided, the user will be prompted through elicitation.

    Args:
        local_path: Local file system path to the notebook file (.ipynb)
        upload_name: Optional. Name of the file after upload (with or without .ipynb extension).
                    If not provided, user will be prompted.
        upload_location: Optional. Either "shared" or "personal". If not provided, user will be prompted.

    Returns:
        Dictionary with upload status and file information

    Example:
        local_path = "/path/to/my_notebook.ipynb"
        upload_name = "analysis_notebook"  # Optional
        upload_location = "shared"  # Optional
    """
    settings = config.get_settings()

    start_time = time.time()

    try:
        # Validate local file exists and is a notebook
        if not os.path.exists(local_path):
            return {
                "status": "error",
                "message": f"Local file not found: {local_path}",
                "error_code": "FILE_NOT_FOUND",
            }

        if not local_path.endswith(".ipynb"):
            return {
                "status": "error",
                "message": "File must be a Jupyter notebook (.ipynb)",
                "error_code": "INVALID_FILE_TYPE",
            }
    except Exception as e:
        error_msg = f"Failed to validate local file '{local_path}': {str(e)}"
        ctx.error(error_msg)

        return {
            "status": "error",
            "message": error_msg,
            "error": str(e),
            "file_path": local_path,
        }

    # Read and validate notebook content
    try:
        with open(local_path, "r", encoding="utf-8") as f:
            notebook_content = json.load(f)
    except json.JSONDecodeError as e:
        return {
            "status": "error",
            "message": f"Invalid JSON in notebook file: {str(e)}",
            "error_code": "INVALID_JSON",
            "error_details": {"json_error": str(e)},
        }

    # Validate notebook schema
    schema_validated, schema_error = _validate_notebook_schema(notebook_content)
    if schema_error:
        return schema_error

    # Elicit upload name from user if not provided
    if upload_name is None:
        original_filename = os.path.basename(local_path)

        elicitation_result, _ = await try_elicitation(
            ctx,
            f"What would you like to name the uploaded file? (Original filename: {original_filename})",
            UploadName,
        )

        if elicitation_result.status == "success":
            upload_name = elicitation_result.data.name
        elif elicitation_result.status == "cancelled":
            return {
                "status": "cancelled",
                "message": "Upload cancelled by user",
            }
        else:
            # Fallback to original filename if elicitation not supported
            upload_name = original_filename
            logger.info(
                "Elicitation not supported, using original filename"
            )  # Handle upload location - elicit only if not provided
    final_location = upload_location

    if final_location is None:
        # Try to elicit upload location from user
        elicitation_result, _ = await try_elicitation(
            ctx,
            "Where would you like to upload the notebook? Choose 'shared' for shared space or 'personal' for personal space.",
            UploadLocation,
        )

        if elicitation_result.status == "success":
            if elicitation_result.data.location in ["shared", "personal"]:
                final_location = elicitation_result.data.location
            else:
                return {
                    "status": "error",
                    "message": "Invalid upload location. Must be 'shared' or 'personal'",
                    "error_code": "INVALID_UPLOAD_LOCATION",
                }
        elif elicitation_result.status == "cancelled":
            return {
                "status": "cancelled",
                "message": "Upload cancelled by user",
            }
        else:
            # Fallback to shared if elicitation not supported
            final_location = "shared"
            logger.info("Elicitation not supported, defaulting to shared space")

    # Validate location
    if final_location not in ["shared", "personal"]:
        return {
            "status": "error",
            "message": "Invalid upload location. Must be 'shared' or 'personal'",
            "error_code": "INVALID_UPLOAD_LOCATION",
        }

    # Derive remote path from elicited upload_name
    if upload_name:
        # Ensure the upload name has .ipynb extension
        if not upload_name.endswith(".ipynb"):
            remote_path = f"{upload_name}.ipynb"
        else:
            remote_path = upload_name
    else:
        # Use just the filename from the local path (fallback)
        remote_path = os.path.basename(local_path)

    # Check if file already exists and throw error if it does
    file_exists = _check_if_file_exists(remote_path, final_location)

    if file_exists:
        return {
            "status": "error",
            "message": f"File '{remote_path}' already exists in {final_location} space. Please choose a different name or delete the existing file first.",
            "error_code": "FILE_ALREADY_EXISTS",
            "error_details": {
                "existing_file": remote_path,
                "location": final_location,
            },
        }

    access_token = get_access_token()

    org_id = get_org_id()
    file_manager = s2.manage_files(
        access_token=access_token,
        base_url=settings.s2_api_base_url,
        organization_id=org_id,
    )

    file_manager_location = None

    if final_location == "shared":
        file_manager_location = file_manager.shared_space
    elif final_location == "personal":
        file_manager_location = file_manager.personal_space
    else:
        return {
            "status": "error",
            "message": "Invalid upload location. Must be 'shared' or 'personal'",
            "error_code": "INVALID_UPLOAD_LOCATION",
            "error_details": {
                "upload_location": final_location,
            },
        }

    file_info = None
    try:
        file_info = file_manager_location.upload_file(
            local_path=local_path, path=remote_path
        )
    except Exception as upload_error:
        logger.error(upload_error)
        return {
            "status": "error",
            "message": f"Failed to upload notebook: {str(upload_error)}",
            "error_code": "UPLOAD_FAILED",
            "error_details": {
                "filename": upload_name,
                "upload_location": final_location,
                "exception_type": type(upload_error).__name__,
            },
        }

    execution_time = (time.time() - start_time) * 1000

    user_id = config.get_user_id()
    settings.analytics_manager.track_event(
        user_id,
        "tool_calling",
        {
            "name": "upload_notebook_file",
            "local_path": local_path,
            "upload_name": upload_name,
            "upload_location": upload_location,
        },
    )

    return {
        "status": "success",
        "message": f"Notebook uploaded successfully to {final_location} space",
        "data": {
            "local_path": local_path,
            "remote_path": file_info.path,
            "upload_name": upload_name,
            "upload_location": final_location,
            "file_type": file_info.type,
            "file_format": file_info.format,
            "schema_validated": schema_validated,
        },
        "metadata": {
            "execution_time_ms": round(execution_time, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "file_size": os.path.getsize(local_path),
        },
    }
