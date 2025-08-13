"""Stage tools for SingleStore MCP server."""

import os
import time
import singlestoredb as s2
from datetime import datetime, timezone
from typing import Any, Dict

from mcp.server.fastmcp import Context

from src.config import config
from src.api.common import get_access_token, get_org_id
from src.logger import get_logger

# Set up logger for this module
logger = get_logger()


async def upload_file_to_stage(
    ctx: Context,
    local_path: str,
    workspace_group_id: str,
) -> Dict[str, Any]:
    """
    Upload a file to SingleStore Stage and return the stage URL.

    Stage is SingleStore's file storage driver that allows users to upload files
    and get a URL where the file is stored, which can then be used in SQL operations
    like creating pipelines.

    Note: Files are limited to a maximum size of 1GB.

    Args:
        ctx: MCP context for user interaction
        local_path: Local file system path to the file to upload
        workspace_group_id: ID of the workspace group to use for Stage access

    Returns:
        Dictionary with upload status and stage URL

    Example:
        local_path = "/path/to/data.csv"
        workspace_group_id = "wg-123abc456def"
    """
    settings = config.get_settings()
    user_id = config.get_user_id()
    settings.analytics_manager.track_event(
        user_id,
        "tool_calling",
        {"name": "upload_file_to_stage"},
    )

    start_time = time.time()

    try:
        # Validate local file exists
        if not os.path.exists(local_path):
            return {
                "status": "error",
                "message": f"Local file not found: {local_path}",
                "errorCode": "FILE_NOT_FOUND",
            }

        # Use the original filename as the stage path
        stage_path = os.path.basename(local_path)

        # Get file size for metadata and validation
        file_size = os.path.getsize(local_path)

        # Check file size limit (1GB = 1,073,741,824 bytes)
        max_file_size = 1024 * 1024 * 1024  # 1GB in bytes
        if file_size > max_file_size:
            file_size_mb = file_size / (1024 * 1024)
            max_size_mb = max_file_size / (1024 * 1024)
            return {
                "status": "error",
                "message": f"File size ({file_size_mb:.2f} MB) exceeds the maximum allowed size of {max_size_mb:.0f} MB (1GB)",
                "errorCode": "FILE_TOO_LARGE",
                "errorDetails": {
                    "fileSizeBytes": file_size,
                    "fileSizeMB": round(file_size_mb, 2),
                    "maxSizeBytes": max_file_size,
                    "maxSizeMB": max_size_mb,
                },
            }

        await ctx.info(
            f"Uploading file '{local_path}' to Stage at '{stage_path}' in workspace group '{workspace_group_id}'..."
        )

        # Get authentication details
        access_token = get_access_token()
        org_id = get_org_id()

        # Create workspace manager to access workspaces
        workspace_manager = s2.manage_workspaces(
            access_token=access_token,
            base_url=settings.s2_api_base_url,
            organization_id=org_id,
        )

        # Find workspace group by ID
        workspace_group = workspace_manager.get_workspace_group(id=workspace_group_id)
        stage = workspace_group.stage

        # Upload file to Stage
        try:
            stage_info = stage.upload_file(local_path=local_path, stage_path=stage_path)

            stage_url = stage_info.abspath()

            await ctx.info(
                f"File '{local_path}' uploaded to Stage at '{stage_url}' in workspace group '{workspace_group.name}'"
            )
            logger.info(
                f"File '{local_path}' uploaded to Stage at '{stage_url}' in workspace group '{workspace_group.name}'"
            )

        except Exception as upload_error:
            logger.error(f"Stage upload error: {upload_error}")
            return {
                "status": "error",
                "message": f"Failed to upload file to Stage: {str(upload_error)}",
                "errorCode": "STAGE_UPLOAD_FAILED",
                "errorDetails": {
                    "localPath": local_path,
                    "stagePath": stage_path,
                    "exceptionType": type(upload_error).__name__,
                },
            }

        execution_time = (time.time() - start_time) * 1000

        return {
            "status": "success",
            "message": f"File uploaded successfully to Stage at '{stage_path}'",
            "data": {
                "localPath": local_path,
                "stagePath": stage_path,
                "stageUrl": stage_url,
                "fileSize": file_size,
                "fileName": os.path.basename(local_path),
                "workspaceGroupName": workspace_group.name,
                "workspaceGroupId": workspace_group.id,
                "stageInfo": stage_info.path if hasattr(stage_info, "path") else None,
            },
            "metadata": {
                "executionTimeMs": round(execution_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "uploadedFileSize": file_size,
            },
        }

    except Exception as e:
        logger.error(f"Error uploading file to Stage: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to upload file to Stage: {str(e)}",
            "errorCode": "STAGE_OPERATION_FAILED",
            "errorDetails": {
                "exceptionType": type(e).__name__,
                "localPath": local_path,
            },
        }
