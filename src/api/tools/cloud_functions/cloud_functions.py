"""Cloud function tools for SingleStore MCP server."""

import time

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from mcp.server.fastmcp import Context

from src.api.common import build_request
from src.config import config
from src.logger import get_logger
from src.utils.uuid_validation import validate_uuid_string

logger = get_logger()

VALID_TARGET_TYPES = ("Workspace", "Cluster", "VirtualWorkspace")

FIELD_MAP = {
    "name": "name",
    "notebook_path": "notebookPath",
    "target_id": "targetID",
    "target_type": "targetType",
    "database_name": "databaseName",
    "description": "description",
    "idle_timeout_seconds": "idleTimeoutSeconds",
}


def _build_cloud_function_body(**kwargs: Any) -> Dict[str, Any]:
    body: Dict[str, Any] = {}
    for py_key, api_key in FIELD_MAP.items():
        value = kwargs.get(py_key)
        if value is None:
            continue
        if py_key == "target_id":
            value = validate_uuid_string(value)
        body[api_key] = value
    return body


async def list_cloud_functions(
    ctx: Context,
    limit: Optional[int] = None,
    offset_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    List all cloud functions in the current organization.

    Returns name, status, endpoint, and description for each cloud function.

    Args:
        limit: Optional maximum number of cloud functions to return.
        offset_id: ID of the last cloud function from the previous page, used to
            continue pagination. Pass the serviceID of the last item returned when
            fetching the next page.
    """
    start_time = time.time()
    settings = config.get_settings()
    user_id = config.get_user_id()
    settings.analytics_manager.track_event(
        user_id, "tool_calling", {"name": "list_cloud_functions"}
    )

    try:
        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset_id is not None:
            params["offsetID"] = validate_uuid_string(offset_id)

        result = build_request("GET", "cloudfunctions", params=params)
        cloud_functions = result.get("cloudFunctions", [])
        pagination = result.get("metadata") or {}
        execution_time = (time.time() - start_time) * 1000

        return {
            "status": "success",
            "message": f"Found {len(cloud_functions)} cloud function(s)",
            "data": cloud_functions,
            "metadata": {
                "execution_time_ms": round(execution_time, 2),
                "count": len(cloud_functions),
                "total_count": pagination.get("totalCount"),
                "has_next_page": pagination.get("hasNextPage"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Failed to list cloud functions: {e}")
        return {
            "status": "error",
            "message": f"Failed to list cloud functions: {str(e)}",
            "errorCode": "LIST_CLOUD_FUNCTIONS_ERROR",
        }


async def get_cloud_function(ctx: Context, cloud_function_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific cloud function including its
    status, endpoint, and configuration.

    Args:
        cloud_function_id: The unique identifier (UUID) of the cloud function.
    """
    start_time = time.time()
    settings = config.get_settings()
    user_id = config.get_user_id()

    try:
        validated_id = validate_uuid_string(cloud_function_id)
        settings.analytics_manager.track_event(
            user_id,
            "tool_calling",
            {"name": "get_cloud_function", "cloud_function_id": validated_id},
        )

        result = build_request("GET", f"cloudfunctions/{validated_id}")
        execution_time = (time.time() - start_time) * 1000

        return {
            "status": "success",
            "message": f"Cloud function '{result.get('name', validated_id)}' is {result.get('status', 'unknown')}",
            "data": result,
            "metadata": {
                "execution_time_ms": round(execution_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Failed to get cloud function: {e}")
        return {
            "status": "error",
            "message": f"Failed to get cloud function: {str(e)}",
            "errorCode": "GET_CLOUD_FUNCTION_ERROR",
        }


async def create_cloud_function(
    ctx: Context,
    name: str,
    notebook_path: str,
    target_id: str,
    target_type: str = "Workspace",
    database_name: Optional[str] = None,
    description: Optional[str] = None,
    idle_timeout_seconds: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Deploy a notebook as a cloud function.

    The notebook must already exist in the Stage file system shared space. Use
    stage_upload_file to upload a notebook first, then deploy it as a cloud function.

    The notebook must define a FastAPI app, and initialize it using a singlestore tool.
    Base example:
        from fastapi import FastAPI
        import singlestoredb.apps as apps
        app = FastAPI()
        @app.get("/")
        async def root():
            return {"message": "hello world"}
        await apps.run_function_app(app)

    Target_type is optional, but if it specifies a virtual workspace, it must also specify a database_name.

    Args:
        name: Name for the cloud function.
        notebook_path: Path to the notebook in Stage (e.g. "my_notebook.ipynb").
        target_id: ID of the workspace, cluster, or virtual workspace to deploy to.
        target_type: Type of target - "Workspace", "Cluster", or "VirtualWorkspace".
        database_name: Optional database name to attach to the function.
        description: Optional description of the cloud function.
        idle_timeout_seconds: Optional idle timeout in seconds before scaling down.
    """
    if target_type not in VALID_TARGET_TYPES:
        return {
            "status": "error",
            "message": f"Invalid target_type '{target_type}'. Must be one of: {', '.join(VALID_TARGET_TYPES)}",
            "errorCode": "INVALID_TARGET_TYPE",
        }

    if target_type == "VirtualWorkspace" and not database_name:
        return {
            "status": "error",
            "message": "database_name is required when target_type is 'VirtualWorkspace'",
            "errorCode": "MISSING_DATABASE_NAME",
        }

    start_time = time.time()
    settings = config.get_settings()
    user_id = config.get_user_id()

    try:
        settings.analytics_manager.track_event(
            user_id,
            "tool_calling",
            {"name": "create_cloud_function", "name_param": name},
        )

        body = _build_cloud_function_body(
            name=name,
            notebook_path=notebook_path,
            target_id=target_id,
            target_type=target_type,
            database_name=database_name,
            description=description,
            idle_timeout_seconds=idle_timeout_seconds,
        )

        result = build_request("POST", "cloudfunctions", data=body)
        execution_time = (time.time() - start_time) * 1000

        return {
            "status": "success",
            "message": f"Cloud function '{name}' created successfully",
            "data": result,
            "metadata": {
                "execution_time_ms": round(execution_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Failed to create cloud function '{name}': {e}")
        return {
            "status": "error",
            "message": f"Failed to create cloud function: {str(e)}",
            "errorCode": "CREATE_CLOUD_FUNCTION_ERROR",
        }


async def delete_cloud_function(ctx: Context, cloud_function_id: str) -> Dict[str, Any]:
    """
    Delete a cloud function by its ID.

    Args:
        cloud_function_id: The unique identifier (UUID) of the cloud function to delete.
    """
    start_time = time.time()
    settings = config.get_settings()
    user_id = config.get_user_id()

    try:
        validated_id = validate_uuid_string(cloud_function_id)
        settings.analytics_manager.track_event(
            user_id,
            "tool_calling",
            {"name": "delete_cloud_function", "cloud_function_id": validated_id},
        )

        result = build_request("DELETE", f"cloudfunctions/{validated_id}")
        execution_time = (time.time() - start_time) * 1000

        return {
            "status": "success",
            "message": f"Cloud function '{validated_id}' deleted successfully",
            "data": result,
            "metadata": {
                "execution_time_ms": round(execution_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Failed to delete cloud function: {e}")
        return {
            "status": "error",
            "message": f"Failed to delete cloud function: {str(e)}",
            "errorCode": "DELETE_CLOUD_FUNCTION_ERROR",
        }


async def update_cloud_function(
    ctx: Context,
    cloud_function_id: str,
    name: Optional[str] = None,
    notebook_path: Optional[str] = None,
    target_id: Optional[str] = None,
    target_type: Optional[str] = None,
    database_name: Optional[str] = None,
    description: Optional[str] = None,
    idle_timeout_seconds: Optional[int] = None,
    update_notebook_snapshot: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Update a cloud function's configuration. Only provided fields are updated.

    Args:
        cloud_function_id: The unique identifier (UUID) of the cloud function.
        name: New name for the cloud function.
        notebook_path: New notebook path in Stage.
        target_id: New target workspace/cluster/virtual workspace ID.
        target_type: New target type - "Workspace", "Cluster", or "VirtualWorkspace".
        database_name: New database name to attach.
        description: New description.
        idle_timeout_seconds: New idle timeout in seconds.
        update_notebook_snapshot: Whether to update the notebook snapshot after updating.
    """
    if target_type is not None and target_type not in VALID_TARGET_TYPES:
        return {
            "status": "error",
            "message": f"Invalid target_type '{target_type}'. Must be one of: {', '.join(VALID_TARGET_TYPES)}",
            "errorCode": "INVALID_TARGET_TYPE",
        }

    if not any(
        value is not None
        for value in (
            name,
            notebook_path,
            target_id,
            target_type,
            database_name,
            description,
            idle_timeout_seconds,
            update_notebook_snapshot,
        )
    ):
        return {
            "status": "error",
            "message": "No fields provided to update",
            "errorCode": "NO_FIELDS_TO_UPDATE",
        }

    start_time = time.time()
    settings = config.get_settings()
    user_id = config.get_user_id()

    try:
        validated_id = validate_uuid_string(cloud_function_id)
        settings.analytics_manager.track_event(
            user_id,
            "tool_calling",
            {"name": "update_cloud_function", "cloud_function_id": validated_id},
        )

        body = _build_cloud_function_body(
            name=name,
            notebook_path=notebook_path,
            target_id=target_id,
            target_type=target_type,
            database_name=database_name,
            description=description,
            idle_timeout_seconds=idle_timeout_seconds,
        )

        params: Dict[str, Any] = {}
        if update_notebook_snapshot is not None:
            params["updateNotebookSnapshot"] = str(update_notebook_snapshot).lower()

        result = build_request(
            "PATCH",
            f"cloudfunctions/{validated_id}",
            data=body,
            params=params,
        )
        execution_time = (time.time() - start_time) * 1000

        return {
            "status": "success",
            "message": f"Cloud function '{validated_id}' updated successfully",
            "data": result,
            "metadata": {
                "execution_time_ms": round(execution_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Failed to update cloud function: {e}")
        return {
            "status": "error",
            "message": f"Failed to update cloud function: {str(e)}",
            "errorCode": "UPDATE_CLOUD_FUNCTION_ERROR",
        }


async def get_cloud_function_token(
    ctx: Context, cloud_function_id: str
) -> Dict[str, Any]:
    """
    Get an authentication token for invoking a cloud function.

    Returns a JWT token and its expiration time. Use this token in the
    Authorization header when making HTTP requests to the cloud function's
    endpoint.

    Args:
        cloud_function_id: The unique identifier (UUID) of the cloud function.
    """
    start_time = time.time()
    settings = config.get_settings()
    user_id = config.get_user_id()

    try:
        validated_id = validate_uuid_string(cloud_function_id)
        settings.analytics_manager.track_event(
            user_id,
            "tool_calling",
            {"name": "get_cloud_function_token", "cloud_function_id": validated_id},
        )

        token_result = build_request("GET", f"cloudfunctions/{validated_id}/token")

        # Also fetch the function details to include the endpoint URL
        function_info = build_request("GET", f"cloudfunctions/{validated_id}")
        endpoint = function_info.get("endpoint")

        execution_time = (time.time() - start_time) * 1000

        return {
            "status": "success",
            "message": "Token retrieved successfully",
            "data": {
                "jwt": token_result.get("jwt"),
                "expiresAt": token_result.get("expiresAt"),
                "endpoint": endpoint,
            },
            "metadata": {
                "execution_time_ms": round(execution_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Failed to get token for cloud function: {e}")
        return {
            "status": "error",
            "message": f"Failed to get cloud function token: {str(e)}",
            "errorCode": "GET_CLOUD_FUNCTION_TOKEN_ERROR",
        }
