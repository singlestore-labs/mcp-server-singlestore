"""Stage tools for SingleStore MCP server."""

import os
import time

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from mcp.server.fastmcp import Context

from src.api.common import build_request
from src.config import config
from src.logger import get_logger
from src.utils.uuid_validation import validate_uuid_string

logger = get_logger()


async def stage_list_files(
    ctx: Context, deployment_id: str, path: str = ""
) -> Dict[str, Any]:
    """
    List files and folders in a Stage deployment's file system.

    Lists the contents of the root folder or a specific subfolder in the Stage
    file system attached to a SingleStore deployment (workspace group or starter
    workspace).

    Args:
        deployment_id: The workspace group ID or starter workspace ID.
        path: Optional folder path to list. Defaults to root. Must refer to a
              folder.

    Returns:
        Dictionary with folder contents including files and subfolders.
    """
    validated_id = validate_uuid_string(deployment_id)
    start_time = time.time()
    settings = config.get_settings()
    user_id = config.get_user_id()
    settings.analytics_manager.track_event(
        user_id, "tool_calling", {"name": "stage_list_files"}
    )

    try:
        if path:
            # Ensure trailing slash for folder listing
            if not path.endswith("/"):
                path = path + "/"
            endpoint = f"stage/{validated_id}/fs/{path}"
        else:
            endpoint = f"stage/{validated_id}/fs"

        result = build_request("GET", endpoint)
        execution_time = (time.time() - start_time) * 1000

        return {
            "status": "success",
            "message": f"Listed contents of '{path or '/'}'",
            "data": result,
            "metadata": {
                "execution_time_ms": round(execution_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Failed to list stage files: {e}")
        return {
            "status": "error",
            "message": f"Failed to list stage files: {str(e)}",
            "errorCode": "STAGE_LIST_FAILED",
        }


async def stage_get_file(
    ctx: Context,
    deployment_id: str,
    path: str,
    return_type: str = "metadata",
) -> Dict[str, Any]:
    """
    Get a file from Stage by path. Returns metadata, a download URL, or text content.

    Recommended workflow: first call with return_type='metadata' to check file size
    and type, then decide whether to fetch the full content or just the URL.

    Args:
        deployment_id: The workspace group ID or starter workspace ID.
        path: Path to the file in Stage.
        return_type: What to return. One of:
            - 'metadata': File metadata as JSON (default).
            - 'url': A pre-signed download URL (does not download the file).
            - 'content': The file's text content (follows redirect and reads body).

    Returns:
        Dictionary with file metadata, download URL, or text content.
    """
    if return_type not in ("metadata", "url", "content"):
        return {
            "status": "error",
            "message": "Invalid return_type. Must be 'metadata', 'url', or 'content'.",
            "errorCode": "INVALID_RETURN_TYPE",
        }

    validated_id = validate_uuid_string(deployment_id)
    start_time = time.time()
    settings = config.get_settings()
    user_id = config.get_user_id()
    settings.analytics_manager.track_event(
        user_id, "tool_calling", {"name": "stage_get_file"}
    )

    # Strip trailing slash for file paths
    path = path.rstrip("/")

    try:
        endpoint = f"stage/{validated_id}/fs/{path}"

        if return_type == "metadata":
            result = build_request("GET", endpoint, params={"metadata": "true"})
            execution_time = (time.time() - start_time) * 1000
            return {
                "status": "success",
                "message": f"Retrieved metadata for '{path}'",
                "data": result,
                "metadata": {
                    "execution_time_ms": round(execution_time, 2),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }

        if return_type == "url":
            response = build_request(
                "GET", endpoint, raw_response=True, allow_redirects=False
            )
            if response.status_code == 307:
                download_url = response.headers.get("Location", "")
                execution_time = (time.time() - start_time) * 1000
                return {
                    "status": "success",
                    "message": f"Retrieved download URL for '{path}'",
                    "data": {"url": download_url},
                    "metadata": {
                        "execution_time_ms": round(execution_time, 2),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                }
            else:
                return {
                    "status": "error",
                    "message": f"Expected 307 redirect but got {response.status_code}: {response.text}",
                    "errorCode": "UNEXPECTED_RESPONSE",
                }

        # return_type == "content"
        response = build_request("GET", endpoint, raw_response=True)
        if response.status_code == 200:
            execution_time = (time.time() - start_time) * 1000
            return {
                "status": "success",
                "message": f"Retrieved content of '{path}'",
                "data": {"content": response.text},
                "metadata": {
                    "execution_time_ms": round(execution_time, 2),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to get file content: {response.status_code} {response.text}",
                "errorCode": "CONTENT_FETCH_FAILED",
            }

    except Exception as e:
        logger.error(f"Failed to get stage file: {e}")
        return {
            "status": "error",
            "message": f"Failed to get stage file: {str(e)}",
            "errorCode": "STAGE_GET_FILE_FAILED",
        }


async def stage_create_folder(
    ctx: Context, deployment_id: str, path: str
) -> Dict[str, Any]:
    """
    Create a folder in Stage.

    Args:
        deployment_id: The workspace group ID or starter workspace ID.
        path: Folder path to create.

    Returns:
        Dictionary with creation status.
    """
    validated_id = validate_uuid_string(deployment_id)
    start_time = time.time()
    settings = config.get_settings()
    user_id = config.get_user_id()
    settings.analytics_manager.track_event(
        user_id, "tool_calling", {"name": "stage_create_folder"}
    )

    # Ensure trailing slash for folder creation
    if not path.endswith("/"):
        path = path + "/"

    try:
        endpoint = f"stage/{validated_id}/fs/{path}"
        build_request("PUT", endpoint, data=None)
        execution_time = (time.time() - start_time) * 1000

        return {
            "status": "success",
            "message": f"Folder '{path}' created successfully",
            "data": {"path": path},
            "metadata": {
                "execution_time_ms": round(execution_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Failed to create stage folder: {e}")
        return {
            "status": "error",
            "message": f"Failed to create folder: {str(e)}",
            "errorCode": "STAGE_CREATE_FOLDER_FAILED",
        }


async def stage_upload_file_local(
    ctx: Context,
    deployment_id: str,
    path: str,
    content: Optional[str] = None,
    local_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Upload a file to Stage from text content or a local file path.

    Provide exactly one of `content` or `local_path`:
    - content: Text content to upload as the file body.
    - local_path: Absolute path to a local file to upload.

    Args:
        deployment_id: The workspace group ID or starter workspace ID.
        path: Destination file path in Stage.
        content: Text content to upload as the file body.
        local_path: Absolute path to a local file to upload.

    Returns:
        Dictionary with upload status.
    """
    if content is not None and local_path is not None:
        return {
            "status": "error",
            "message": "Provide exactly one of 'content' or 'local_path', not both.",
            "errorCode": "INVALID_ARGUMENTS",
        }
    if content is None and local_path is None:
        return {
            "status": "error",
            "message": "Provide exactly one of 'content' or 'local_path'.",
            "errorCode": "INVALID_ARGUMENTS",
        }

    validated_id = validate_uuid_string(deployment_id)
    start_time = time.time()
    settings = config.get_settings()
    user_id = config.get_user_id()
    settings.analytics_manager.track_event(
        user_id, "tool_calling", {"name": "stage_upload_file"}
    )

    # Ensure path does NOT end with slash (it's a file, not a folder)
    path = path.rstrip("/")

    # Extract filename from path for the multipart field
    filename = path.rsplit("/", 1)[-1]

    try:
        if local_path is not None:
            if not os.path.isfile(local_path):
                return {
                    "status": "error",
                    "message": f"Local file not found: {local_path}",
                    "errorCode": "FILE_NOT_FOUND",
                }
            with open(local_path, "rb") as f:
                file_bytes = f.read()
        else:
            file_bytes = content.encode("utf-8")  # type: ignore[union-attr]

        endpoint = f"stage/{validated_id}/fs/{path}"
        build_request(
            "PUT",
            endpoint,
            files={"file": (filename, file_bytes)},
        )
        execution_time = (time.time() - start_time) * 1000

        return {
            "status": "success",
            "message": f"File '{path}' uploaded successfully",
            "data": {"path": path, "filename": filename},
            "metadata": {
                "execution_time_ms": round(execution_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Failed to upload stage file: {e}")
        return {
            "status": "error",
            "message": f"Failed to upload file: {str(e)}",
            "errorCode": "STAGE_UPLOAD_FAILED",
        }


async def stage_upload_file_remote(
    ctx: Context, deployment_id: str, path: str, content: str
) -> Dict[str, Any]:
    """
    Upload a file to Stage with the given text content.

    Args:
        deployment_id: The workspace group ID or starter workspace ID.
        path: Destination file path in Stage.
        content: Text content to upload as the file body.

    Returns:
        Dictionary with upload status.
    """
    validated_id = validate_uuid_string(deployment_id)
    start_time = time.time()
    settings = config.get_settings()
    user_id = config.get_user_id()
    settings.analytics_manager.track_event(
        user_id, "tool_calling", {"name": "stage_upload_file"}
    )

    # Ensure path does NOT end with slash (it's a file, not a folder)
    path = path.rstrip("/")

    # Extract filename from path for the multipart field
    filename = path.rsplit("/", 1)[-1]

    try:
        endpoint = f"stage/{validated_id}/fs/{path}"
        build_request(
            "PUT",
            endpoint,
            files={"file": (filename, content.encode("utf-8"))},
        )
        execution_time = (time.time() - start_time) * 1000

        return {
            "status": "success",
            "message": f"File '{path}' uploaded successfully",
            "data": {"path": path, "filename": filename},
            "metadata": {
                "execution_time_ms": round(execution_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Failed to upload stage file: {e}")
        return {
            "status": "error",
            "message": f"Failed to upload file: {str(e)}",
            "errorCode": "STAGE_UPLOAD_FAILED",
        }


async def stage_move(
    ctx: Context, deployment_id: str, source_path: str, destination_path: str
) -> Dict[str, Any]:
    """
    Move or rename a file or folder in Stage.
    For folders, ensure the path ends with '/'.
    For files, the path must not end with '/'.

    Works like the `mv` command - can rename and/or move into a different folder.

    Args:
        deployment_id: The workspace group ID or starter workspace ID.
        source_path: Current path of the file or folder.
        destination_path: New path for the file or folder.

    Returns:
        Dictionary with move status.
    """
    validated_id = validate_uuid_string(deployment_id)
    start_time = time.time()
    settings = config.get_settings()
    user_id = config.get_user_id()
    settings.analytics_manager.track_event(
        user_id, "tool_calling", {"name": "stage_move"}
    )

    try:
        endpoint = f"stage/{validated_id}/fs/{source_path}"
        build_request("PATCH", endpoint, data={"newPath": destination_path})
        execution_time = (time.time() - start_time) * 1000

        return {
            "status": "success",
            "message": f"Moved '{source_path}' to '{destination_path}'",
            "data": {
                "source_path": source_path,
                "destination_path": destination_path,
            },
            "metadata": {
                "execution_time_ms": round(execution_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Failed to move stage path: {e}")
        return {
            "status": "error",
            "message": f"Failed to move: {str(e)}",
            "errorCode": "STAGE_MOVE_FAILED",
        }


async def stage_delete(ctx: Context, deployment_id: str, path: str) -> Dict[str, Any]:
    """
    Delete a file or folder from Stage.

    For folders, ensure the path ends with '/'.
    For files, the path must not end with '/'.

    Args:
        deployment_id: The workspace group ID or starter workspace ID.
        path: Path of the file or folder to delete.

    Returns:
        Dictionary with deletion status.
    """
    validated_id = validate_uuid_string(deployment_id)
    start_time = time.time()
    settings = config.get_settings()
    user_id = config.get_user_id()
    settings.analytics_manager.track_event(
        user_id, "tool_calling", {"name": "stage_delete"}
    )

    try:
        endpoint = f"stage/{validated_id}/fs/{path}"
        build_request("DELETE", endpoint)
        execution_time = (time.time() - start_time) * 1000

        return {
            "status": "success",
            "message": f"Deleted '{path}' successfully",
            "metadata": {
                "execution_time_ms": round(execution_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Failed to delete stage path: {e}")
        return {
            "status": "error",
            "message": f"Failed to delete: {str(e)}",
            "errorCode": "STAGE_DELETE_FAILED",
        }
