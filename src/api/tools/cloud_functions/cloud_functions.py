import time

from datetime import datetime, timezone
from typing import Optional, Dict

from mcp.server.fastmcp import Context

from src.api.tools.cloud_functions import utils
from src.config import config
from src.logger import get_logger

# Set up logger for this module
logger = get_logger()


async def create_code_service(
    ctx: Context,
    name: str,
    notebook_path: str,
    description: Optional[str] = None,
) -> dict:
    """
    Create a new code service from a notebook.

    Args:
        ctx: Context object
        name: Name of the code service
        notebook_path: Remote path to the shared notebook file
        description: Optional description of the code service
        environment_variables: Optional environment variables for the service

    Returns:
        Dict with code service creation result
    """

    logger.info(f"Creating code service '{name}' from notebook '{notebook_path}'")

    settings = config.get_settings()
    start_time = time.time()
    user_id = config.get_user_id()

    try:
        code_services_manager = utils.get_org_code_services_manager()

        if not code_services_manager:
            return {
                "status": "error",
                "message": "Code services functionality not available in the current SDK version",
                "errorCode": "CODE_SERVICES_NOT_AVAILABLE",
            }

        # Create the code service
        service_obj = code_services_manager.create(
            name=name,
            notebook_path=notebook_path,
            description=description,
        )

        settings.analytics_manager.track_event(
            user_id,
            "tool_calling",
            {
                "name": "create_code_service",
                "service_name": name,
                "notebook_path": notebook_path,
            },
        )

        execution_time = (time.time() - start_time) * 1000
        return {
            "status": "success",
            "message": f"Code service '{name}' created successfully.",
            "data": {
                "codeServiceID": service_obj.code_service_id,
                "name": service_obj.name,
                "description": service_obj.description,
                "notebookPath": service_obj.notebook_path,
                "environmentVariables": service_obj.environment_variables,
                "status": service_obj.status,
                "createdAt": service_obj.created_at,
                "updatedAt": service_obj.updated_at,
            },
            "metadata": {
                "executionTimeMs": round(execution_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Error creating code service: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to create code service: {str(e)}",
            "errorCode": "CODE_SERVICE_CREATION_FAILED",
            "errorDetails": {"exception_type": type(e).__name__},
        }


async def list_code_services(ctx: Context) -> dict:
    """
    List all code services in the organization.

    Args:
        ctx: Context object

    Returns:
        Dict with list of code services
    """

    logger.info("Listing code services")

    settings = config.get_settings()
    start_time = time.time()
    user_id = config.get_user_id()

    try:
        code_services_manager = utils.get_org_code_services_manager()

        if not code_services_manager:
            return {
                "status": "error",
                "message": "Code services functionality not available in the current SDK version",
                "errorCode": "CODE_SERVICES_NOT_AVAILABLE",
            }

        services = code_services_manager.list()

        settings.analytics_manager.track_event(
            user_id,
            "tool_calling",
            {
                "name": "list_code_services",
                "services_count": len(services),
            },
        )

        execution_time = (time.time() - start_time) * 1000
        return {
            "status": "success",
            "message": f"Retrieved {len(services)} code services.",
            "data": [
                {
                    "codeServiceID": service.code_service_id,
                    "name": service.name,
                    "description": service.description,
                    "notebookPath": service.notebook_path,
                    "environmentVariables": service.environment_variables,
                    "status": service.status,
                    "createdAt": service.created_at,
                    "updatedAt": service.updated_at,
                }
                for service in services
            ],
            "metadata": {
                "executionTimeMs": round(execution_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Error listing code services: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to list code services: {str(e)}",
            "errorCode": "CODE_SERVICES_LIST_FAILED",
            "errorDetails": {"exception_type": type(e).__name__},
        }


async def get_code_service(
    ctx: Context,
    code_service_id: str,
) -> dict:
    """
    Retrieve details of a code service by its ID.

    Args:
        ctx: Context object
        code_service_id: ID of the code service to retrieve

    Returns:
        Dict with code service details or error info
    """

    logger.info(f"Getting code service '{code_service_id}'")

    settings = config.get_settings()
    start_time = time.time()
    user_id = config.get_user_id()

    try:
        code_services_manager = utils.get_org_code_services_manager()

        if not code_services_manager:
            return {
                "status": "error",
                "message": "Code services functionality not available in the current SDK version",
                "errorCode": "CODE_SERVICES_NOT_AVAILABLE",
            }

        service_obj = code_services_manager.get(code_service_id)

        if not service_obj:
            return {
                "status": "error",
                "message": f"Code service with ID '{code_service_id}' not found.",
                "errorCode": "CODE_SERVICE_NOT_FOUND",
            }

        settings.analytics_manager.track_event(
            user_id,
            "tool_calling",
            {
                "name": "get_code_service",
                "code_service_id": code_service_id,
            },
        )

        execution_time = (time.time() - start_time) * 1000
        return {
            "status": "success",
            "message": f"Code service '{service_obj.name}' retrieved successfully.",
            "data": {
                "codeServiceID": service_obj.code_service_id,
                "name": service_obj.name,
                "description": service_obj.description,
                "notebookPath": service_obj.notebook_path,
                "environmentVariables": service_obj.environment_variables,
                "status": service_obj.status,
                "createdAt": service_obj.created_at,
                "updatedAt": service_obj.updated_at,
            },
            "metadata": {
                "executionTimeMs": round(execution_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Error retrieving code service: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to retrieve code service: {str(e)}",
            "errorCode": "CODE_SERVICE_GET_FAILED",
            "errorDetails": {"exception_type": type(e).__name__},
        }


async def update_code_service(
    ctx: Context,
    code_service_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    notebook_path: Optional[str] = None,
    environment_variables: Optional[Dict[str, str]] = None,
) -> dict:
    """
    Update a code service by its ID.

    Args:
        ctx: Context object
        code_service_id: ID of the code service to update
        name: Optional new name for the service
        description: Optional new description for the service
        notebook_path: Optional new notebook path for the service
        environment_variables: Optional new environment variables for the service

    Returns:
        Dict with update result
    """

    logger.info(f"Updating code service '{code_service_id}'")

    settings = config.get_settings()
    start_time = time.time()
    user_id = config.get_user_id()

    try:
        code_services_manager = utils.get_org_code_services_manager()

        if not code_services_manager:
            return {
                "status": "error",
                "message": "Code services functionality not available in the current SDK version",
                "errorCode": "CODE_SERVICES_NOT_AVAILABLE",
            }

        # Prepare update parameters
        update_params = {}
        if name is not None:
            update_params["name"] = name
        if description is not None:
            update_params["description"] = description
        if notebook_path is not None:
            update_params["notebook_path"] = notebook_path
        if environment_variables is not None:
            update_params["environment_variables"] = environment_variables

        if not update_params:
            return {
                "status": "error",
                "message": "No update parameters provided",
                "errorCode": "NO_UPDATE_PARAMS",
            }

        service_obj = code_services_manager.update(code_service_id, **update_params)

        if not service_obj:
            return {
                "status": "error",
                "message": f"Failed to update code service with ID '{code_service_id}'.",
                "errorCode": "CODE_SERVICE_UPDATE_FAILED",
            }

        settings.analytics_manager.track_event(
            user_id,
            "tool_calling",
            {
                "name": "update_code_service",
                "code_service_id": code_service_id,
                "updated_fields": list(update_params.keys()),
            },
        )

        execution_time = (time.time() - start_time) * 1000
        return {
            "status": "success",
            "message": f"Code service '{service_obj.name}' updated successfully.",
            "data": {
                "codeServiceID": service_obj.code_service_id,
                "name": service_obj.name,
                "description": service_obj.description,
                "notebookPath": service_obj.notebook_path,
                "environmentVariables": service_obj.environment_variables,
                "status": service_obj.status,
                "createdAt": service_obj.created_at,
                "updatedAt": service_obj.updated_at,
            },
            "metadata": {
                "executionTimeMs": round(execution_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Error updating code service: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to update code service: {str(e)}",
            "errorCode": "CODE_SERVICE_UPDATE_FAILED",
            "errorDetails": {"exception_type": type(e).__name__},
        }


async def delete_code_service(
    ctx: Context,
    code_service_id: str,
) -> dict:
    """
    Delete a code service by its ID.

    Args:
        ctx: Context object
        code_service_id: ID of the code service to delete

    Returns:
        Dict with deletion result
    """

    logger.info(f"Deleting code service '{code_service_id}'")

    settings = config.get_settings()
    start_time = time.time()
    user_id = config.get_user_id()

    try:
        code_services_manager = utils.get_org_code_services_manager()

        if not code_services_manager:
            return {
                "status": "error",
                "message": "Code services functionality not available in the current SDK version",
                "errorCode": "CODE_SERVICES_NOT_AVAILABLE",
            }

        success = code_services_manager.delete(code_service_id)

        if not success:
            return {
                "status": "error",
                "message": f"Failed to delete code service with ID '{code_service_id}'.",
                "errorCode": "CODE_SERVICE_DELETION_FAILED",
            }

        settings.analytics_manager.track_event(
            user_id,
            "tool_calling",
            {
                "name": "delete_code_service",
                "code_service_id": code_service_id,
            },
        )

        execution_time = (time.time() - start_time) * 1000
        return {
            "status": "success",
            "message": f"Code service '{code_service_id}' deleted successfully.",
            "metadata": {
                "executionTimeMs": round(execution_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Error deleting code service: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to delete code service: {str(e)}",
            "errorCode": "CODE_SERVICE_DELETION_FAILED",
            "errorDetails": {"exception_type": type(e).__name__},
        }
