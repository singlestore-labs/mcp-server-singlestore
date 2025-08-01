import time
import singlestoredb as s2

from datetime import datetime, timezone
from typing import Optional

from mcp.server.fastmcp import Context

from src.api.tools.jobs import utils
from src.config import config
from src.logger import get_logger

# Set up logger for this module
logger = get_logger()


async def create_job_from_notebook(
    ctx: Context,
    name: str,
    notebook_path: str,
    mode: str = "Once",
    execution_interval_in_minutes: Optional[int] = None,
) -> dict:
    """
    Create a scheduled job to run a notebook (uploaded to shared space).

    Args:
        ctx: Context object
        name: Name of the job
        notebook_path: Remote path to the shared notebook file
        mode: Job mode (options: "Once", "Recurring")
        execution_interval_in_minutes: Optional interval in minutes for recurring jobs

    Returns:
        Dict with job creation result
    """

    logger.info("Creating job from notebook")

    settings = config.get_settings()
    start_time = time.time()
    user_id = config.get_user_id()
    try:
        jobs_manager = utils.get_org_jobs_manager()

        job_obj = jobs_manager.schedule(
            notebook_path=notebook_path,
            name=name,
            mode=s2.management.job.Mode(mode),
            create_snapshot=True,
            execution_interval_in_minutes=execution_interval_in_minutes,
        )

        settings.analytics_manager.track_event(
            user_id,
            "tool_calling",
            {
                "name": "create_job_from_notebook",
                "job_name": name,
                "notebook_path": notebook_path,
            },
        )
        execution_time = (time.time() - start_time) * 1000
        return {
            "status": "success",
            "message": f"Job '{name}' created successfully.",
            "data": {
                "jobID": job_obj.job_id,
                "name": job_obj.name,
                "description": job_obj.description,
                "completedExecutionsCount": job_obj.completed_executions_count,
                "schedule": {
                    "mode": job_obj.schedule.mode.value,
                    "executionIntervalInMinutes": job_obj.schedule.execution_interval_in_minutes,
                },
                "createdAt": job_obj.created_at,
                "terminatedAt": job_obj.terminated_at,
            },
            "metadata": {
                "executionTimeMs": round(execution_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to create job: {str(e)}",
            "errorCode": "JOB_CREATION_FAILED",
            "errorDetails": {"exception_type": type(e).__name__},
        }


async def get_job(
    ctx: Context,
    job_id: str,
) -> dict:
    """
    Retrieve details of a scheduled job by its ID.

    Args:
        ctx: Context object
        job_id: ID of the job to retrieve

    Returns:
        Dict with job details or error info
    """
    settings = config.get_settings()
    start_time = time.time()
    user_id = config.get_user_id()
    try:
        jobs_manager = utils.get_org_jobs_manager()
        job_obj = jobs_manager.get(job_id)
        if not job_obj:
            return {
                "status": "error",
                "message": f"Job with ID '{job_id}' not found.",
                "errorCode": "JOB_NOT_FOUND",
            }
        settings.analytics_manager.track_event(
            user_id,
            "tool_calling",
            {
                "name": "get_job",
                "job_id": job_id,
            },
        )
        execution_time = (time.time() - start_time) * 1000
        return {
            "status": "success",
            "message": f"Job '{job_obj.name}' retrieved successfully.",
            "data": {
                "jobID": job_obj.job_id,
                "name": job_obj.name,
                "description": job_obj.description,
                "completedExecutionsCount": job_obj.completed_executions_count,
                "schedule": {
                    "mode": job_obj.schedule.mode.value,
                    "executionIntervalInMinutes": job_obj.schedule.execution_interval_in_minutes,
                },
                "createdAt": job_obj.created_at,
                "terminatedAt": job_obj.terminated_at,
            },
            "metadata": {
                "executionTimeMs": round(execution_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Error retrieving job: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to retrieve job: {str(e)}",
            "errorCode": "JOB_GET_FAILED",
            "errorDetails": {"exception_type": type(e).__name__},
        }


async def delete_job(
    ctx: Context,
    job_id: str,
) -> dict:
    """
    Delete a scheduled job by its ID.

    Args:
        ctx: Context object
        job_id: ID of the job to delete

    Returns:
        Dict with deletion result
    """
    settings = config.get_settings()
    start_time = time.time()
    user_id = config.get_user_id()

    try:
        jobs_manager = utils.get_org_jobs_manager()

        success = jobs_manager.delete(job_id)
        if not success:
            return {
                "status": "error",
                "message": f"Failed to delete job with ID '{job_id}'.",
                "errorCode": "JOB_DELETION_FAILED",
            }

        settings.analytics_manager.track_event(
            user_id,
            "tool_calling",
            {
                "name": "delete_job",
                "job_id": job_id,
            },
        )
        execution_time = (time.time() - start_time) * 1000
        return {
            "status": "success",
            "message": f"Job '{job_id}' deleted successfully.",
            "metadata": {
                "executionTimeMs": round(execution_time, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Error deleting job: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to delete job: {str(e)}",
            "errorCode": "JOB_DELETION_FAILED",
            "errorDetails": {"exception_type": type(e).__name__},
        }
