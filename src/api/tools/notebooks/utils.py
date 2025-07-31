import json
import jsonschema
import os
import uuid
import singlestoredb as s2

from typing import Any, Dict, Optional

import nbformat as nbf
import nbformat.v4 as nbfv4

from src.config import config
from src.api.common import get_access_token, get_org_id
from src.logger import get_logger


# Set up logger for this module
logger = get_logger()


SAMPLE_NOTEBOOK_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "sample_notebook.ipynb"
)


def get_notebook_schema() -> dict:
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


def create_file_in_shared_space(
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


def validate_content_structure(content: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validate the basic structure of the content dictionary.

    Returns:
        None if validation passes, error dict if validation fails
    """
    if not isinstance(content, dict):
        return {
            "status": "error",
            "message": "Content must be a dictionary",
            "errorCode": "INVALID_CONTENT_TYPE",
        }

    if "cells" not in content:
        return {
            "status": "error",
            "message": "Content must contain a 'cells' field",
            "errorCode": "MISSING_CELLS_FIELD",
        }

    if not isinstance(content["cells"], list):
        return {
            "status": "error",
            "message": "Cells field must be an array",
            "errorCode": "INVALID_CELLS_TYPE",
        }

    return None


def convert_to_notebook_cells(cells: list) -> tuple[list, Optional[Dict[str, Any]]]:
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
                "errorCode": "INVALID_CELL_TYPE",
            }

        if "type" not in cell or "content" not in cell:
            return [], {
                "status": "error",
                "message": f"Cell {i} must have 'type' and 'content' fields",
                "errorCode": "MISSING_CELL_FIELDS",
            }

        cell_type = cell["type"]
        cell_content = cell["content"]

        if cell_type not in ["markdown", "code"]:
            return [], {
                "status": "error",
                "message": f"Cell {i} type must be 'markdown' or 'code', got '{cell_type}'",
                "errorCode": "INVALID_CELL_TYPE_VALUE",
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


def create_notebook_structure(notebook_cells: list) -> Dict[str, Any]:
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


def validate_notebook_schema(
    notebook_content: Dict[str, Any],
) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    Validate notebook content against Jupyter notebook schema.

    Returns:
        Tuple of (schema_validated, error_dict). error_dict is None if successful or skipped.
    """
    try:
        # Load schema from external file
        schema = get_notebook_schema()

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
            "errorCode": "INVALID_SCHEMA_FILE",
            "errorDetails": {"json_error": str(e)},
        }
    except jsonschema.ValidationError as e:
        return False, {
            "status": "error",
            "message": f"Notebook content validation failed: {e.message}",
            "errorCode": "SCHEMA_VALIDATION_FAILED",
            "errorDetails": {"validation_error": str(e)},
        }
    except Exception as e:
        logger.warning(f"Schema validation failed: {str(e)}")
        # Continue without validation if schema can't be loaded
        return False, None


def transform_to_valid_notebook_format(notebook_content: dict) -> dict:
    """
    Transform a Jupyter notebook dict into the correct format for schema validation and upload.

    Args:
        notebook_content: The original notebook dict (may be malformed or missing fields)

    Returns:
        A dict in the correct Jupyter notebook format (v4, minor 5)
    """
    # Ensure top-level keys
    nbformat = notebook_content.get("nbformat", 4)
    nbformat_minor = notebook_content.get("nbformat_minor", 5)
    metadata = notebook_content.get("metadata", {})
    cells = notebook_content.get("cells", [])

    # Fix metadata
    if "kernelspec" not in metadata:
        metadata["kernelspec"] = {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        }
    if "language_info" not in metadata:
        metadata["language_info"] = {
            "name": "python",
            "version": "3.8.0",
            "mimetype": "text/x-python",
            "codemirror_mode": {"name": "ipython", "version": 3},
            "pygments_lexer": "ipython3",
            "file_extension": ".py",
        }

    # Normalize cells
    normalized_cells = []
    import uuid

    for i, cell in enumerate(cells):
        # If cell is not a dict, skip
        if not isinstance(cell, dict):
            continue
        cell_type = cell.get("cell_type") or cell.get("type")
        source = cell.get("source") if "source" in cell else cell.get("content")
        # Skip cell if missing type or content
        if cell_type not in ["markdown", "code"] or source is None:
            continue
        # Ensure source is a list
        if isinstance(source, str):
            source = [source]
        elif not isinstance(source, list):
            source = [str(source)]
        cell_id = cell.get("id") or str(uuid.uuid4())[:8]
        metadata_cell = cell.get("metadata", {})
        if cell_type == "markdown":
            normalized_cells.append(
                {
                    "id": cell_id,
                    "cell_type": "markdown",
                    "metadata": metadata_cell,
                    "source": source,
                }
            )
        elif cell_type == "code":
            outputs = cell.get("outputs", [])
            execution_count = cell.get("execution_count", None)
            normalized_cells.append(
                {
                    "id": cell_id,
                    "cell_type": "code",
                    "metadata": metadata_cell,
                    "source": source,
                    "outputs": outputs,
                    "execution_count": execution_count,
                }
            )

    # Compose notebook dict
    valid_notebook = {
        "nbformat": nbformat,
        "nbformat_minor": nbformat_minor,
        "metadata": metadata,
        "cells": normalized_cells,
    }
    return valid_notebook


def check_if_file_exists(file_name: str, location: str = "shared") -> bool:
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
