import json
import os
import tempfile
import time
import singlestoredb as s2

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel

from mcp.server.fastmcp import Context

from src.api.tools.notebooks import utils
from src.config import config
from src.api.common import get_access_token, get_org_id
from src.logger import get_logger
from src.utils.elicitation import try_elicitation

# Set up logger for this module
logger = get_logger()


async def create_notebook_file(ctx: Context, content: Dict[str, Any]) -> Dict[str, Any]:
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
        content_error = utils.validate_content_structure(content)
        if content_error:
            return content_error

        # Convert simplified format to full Jupyter notebook format
        notebook_cells, cells_error = utils.convert_to_notebook_cells(content["cells"])
        if cells_error:
            return cells_error

        # Create full notebook structure
        notebook_content = utils.create_notebook_structure(notebook_cells)

        # Validate against Jupyter notebook schema
        schema_validated, schema_error = utils.validate_notebook_schema(
            notebook_content
        )
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
                "tempFilePath": temp_file_path,
                "cellCount": len(notebook_cells),
                "schemaValidated": schema_validated,
                "notebookFormat": {"nbformat": 4, "nbformat_minor": 5},
            },
            "metadata": {
                "executionTimeMs": round(execution_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tempFileSize": os.path.getsize(temp_file_path),
            },
        }

    except Exception as e:
        logger.error(f"Error creating notebook file: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to create notebook file: {str(e)}",
            "errorCode": "NOTEBOOK_CREATION_FAILED",
            "errorDetails": {"exception_type": type(e).__name__},
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
                "errorCode": "FILE_NOT_FOUND",
            }

        if not local_path.endswith(".ipynb"):
            return {
                "status": "error",
                "message": "File must be a Jupyter notebook (.ipynb)",
                "errorCode": "INVALID_FILE_TYPE",
            }
    except Exception as e:
        error_msg = f"Failed to validate local file '{local_path}': {str(e)}"
        ctx.error(error_msg)

        return {
            "status": "error",
            "message": error_msg,
            "error": str(e),
            "filePath": local_path,
        }

    # Read notebook content and normalize to valid format
    try:
        with open(local_path, "r", encoding="utf-8") as f:
            raw_content = json.load(f)
    except json.JSONDecodeError as e:
        return {
            "status": "error",
            "message": f"Invalid JSON in notebook file: {str(e)}",
            "errorCode": "INVALID_JSON",
            "errorDetails": {"json_error": str(e)},
        }

    # Transform to valid notebook format before validation and upload
    notebook_content = utils.transform_to_valid_notebook_format(raw_content)

    # Validate notebook schema
    schema_validated, schema_error = utils.validate_notebook_schema(notebook_content)
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
                    "errorCode": "INVALID_UPLOAD_LOCATION",
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
            "errorCode": "INVALID_UPLOAD_LOCATION",
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
    file_exists = utils.check_if_file_exists(remote_path, final_location)

    if file_exists:
        return {
            "status": "error",
            "message": f"File '{remote_path}' already exists in {final_location} space. Please choose a different name or delete the existing file first.",
            "errorCode": "FILE_ALREADY_EXISTS",
            "errorDetails": {
                "existingFile": remote_path,
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
            "errorCode": "INVALID_UPLOAD_LOCATION",
            "errorDetails": {
                "uploadLocation": final_location,
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
            "errorCode": "UPLOAD_FAILED",
            "errorDetails": {
                "filename": upload_name,
                "uploadLocation": final_location,
                "exceptionType": type(upload_error).__name__,
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
            "localPath": local_path,
            "remotePath": file_info.path,
            "uploadName": upload_name,
            "uploadLocation": final_location,
            "fileType": file_info.type,
            "fileFormat": file_info.format,
            "schemaValidated": schema_validated,
        },
        "metadata": {
            "executionTimeMs": round(execution_time, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fileSize": os.path.getsize(local_path),
        },
    }
