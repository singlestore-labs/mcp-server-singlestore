"""Database tools for SingleStore MCP server."""

import time
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from mcp.server.fastmcp import Context

from src.config import config
from src.api.common import fetch_user, get_access_token
from src.api.tools.s2_manager import S2Manager
from src.api.tools.types import WorkspaceTarget
from src.auth.session_credentials_manager import (
    get_session_credentials_manager,
    invalidate_credentials,
)
from src.utils.uuid_validation import validate_workspace_id
from src.utils.elicitation import try_elicitation, ElicitationError
from src.logger import get_logger

# Set up logger for this module
logger = get_logger()


class DatabaseCredentials(BaseModel):
    """Schema for database authentication credentials when using API key."""

    username: str = Field(..., description="Database username for authentication")
    password: str = Field(..., description="Database password for authentication")


async def _get_database_credentials(
    ctx: Context,
    target: WorkspaceTarget,
    database_name: str | None = None,
    provided_username: str | None = None,
    provided_password: str | None = None,
) -> tuple[str, str]:
    """
    Get database credentials based on the authentication method.

    Args:
        ctx: The MCP context
        target: The workspace target
        database_name: The database name to use for key generation
        provided_username: Optional username provided by the caller
        provided_password: Optional password provided by the caller

    Returns:
        Tuple of (username, password)

    Raises:
        Exception: If credentials cannot be obtained
    """
    settings = config.get_settings()

    # Check if we're using API key authentication
    is_using_api_key = (
        not settings.is_remote
        and isinstance(settings, config.LocalSettings)
        and settings.api_key is not None
    )

    if is_using_api_key:
        # If credentials are provided directly, use them
        if provided_username and provided_password:
            logger.debug(f"Using provided credentials for workspace: {target.name}")
            return (provided_username, provided_password)

        # For API key authentication, we need database credentials
        # Generate database key using credentials manager
        credentials_manager = get_session_credentials_manager()
        database_key = credentials_manager.generate_database_key(
            workspace_name=target.name, database_name=database_name
        )

        # Check if we have cached credentials for this database
        if credentials_manager.has_credentials(database_key):
            cached_creds = credentials_manager.get_credentials(database_key)
            if cached_creds:
                logger.debug(f"Using cached credentials for workspace: {target.name}")
                return cached_creds

        # Dedicated workspaces: need to request database credentials from user
        elicitation_message = (
            f"API key authentication detected. To connect to the dedicated workspace '{target.name}', "
            f"please provide your database username and password for this workspace."
        )

        try:
            elicitation_result, error = await try_elicitation(
                ctx=ctx, message=elicitation_message, schema=DatabaseCredentials
            )

            if error == ElicitationError.NOT_SUPPORTED:
                # Fallback: raise exception with clear message
                raise Exception(
                    "Database credentials required for API key authentication on dedicated workspaces. "
                    f"Please provide your database username and password for workspace '{target.name}'. "
                    "You can obtain these credentials from your SingleStore portal. "
                    "Note: This is different from your SingleStore account credentials - these are "
                    "database-specific credentials for connecting to the workspace."
                )
            elif elicitation_result.status == "success" and elicitation_result.data:
                username = elicitation_result.data.username
                password = elicitation_result.data.password

                # Store credentials in session cache for future use
                try:
                    credentials_manager.store_credentials(
                        database_key, username, password
                    )
                    logger.debug(f"Cached credentials for workspace: {target.name}")
                except Exception as e:
                    logger.warning(f"Failed to cache credentials: {e}")

                return (username, password)
            else:
                raise Exception(
                    "Database credentials are required but were not provided. Please ask the user to provide the database credentials"
                )
        except Exception as e:
            if "Database credentials required" in str(e):
                raise  # Re-raise our specific credential error
            logger.error(f"Error during credential elicitation: {e}")
            raise Exception(f"Failed to obtain database credentials: {str(e)}")
    else:
        # JWT authentication: use user_id and access_token as before
        user = fetch_user()
        return user.get("userID"), get_access_token()


async def __execute_sql_unified(
    ctx: Context,
    target: WorkspaceTarget,
    sql_query: str,
    username: str,
    password: str,
    database: str | None = None,
) -> dict:
    """
    Execute SQL operations on a connected workspace or starter workspace.
    Returns results and column names in a dictionary format.
    """

    if target.endpoint is None:
        raise ValueError("Workspace or starter workspace does not have an endpoint. ")
    endpoint = target.endpoint
    database_name = database

    # Parse host and port from endpoint
    if ":" in endpoint:
        host, port = endpoint.split(":", 1)
    else:
        host = endpoint
        port = None

    # Generate database key for credential management
    credentials_manager = get_session_credentials_manager()
    database_key = credentials_manager.generate_database_key(
        workspace_name=target.name, database_name=database_name
    )

    try:
        s2_manager = S2Manager(
            host=host,
            port=port,
            user=username,
            password=password,
            database=database_name,
        )

        workspace_type = "shared/virtual" if target.is_shared else "dedicated"
        await ctx.info(
            f"Executing SQL query on {workspace_type} workspace '{target.name}' with database '{database_name}': {sql_query}"
            "This query may take some time depending on the complexity and size of the data."
        )
        s2_manager.execute(sql_query)
        columns = (
            [desc[0] for desc in s2_manager.cursor.description]
            if s2_manager.cursor.description
            else []
        )
        rows = s2_manager.fetchmany()
        results = []
        for row in rows:
            result_dict = {}
            for i, column in enumerate(columns):
                result_dict[column] = row[i]
            results.append(result_dict)
        s2_manager.close()
        return {
            "data": results,
            "row_count": len(rows),
            "columns": columns,
            "status": "Success",
        }
    except Exception as e:
        # Check if this is an authentication error
        error_msg = str(e).lower()
        is_auth_error = any(
            auth_keyword in error_msg
            for auth_keyword in [
                "access denied",
                "authentication failed",
                "invalid credentials",
                "login failed",
                "permission denied",
                "unauthorized",
                "auth",
            ]
        )

        if is_auth_error:
            logger.warning(
                f"Authentication failed for database {database_key}, invalidating cached credentials"
            )
            invalidate_credentials(database_key)
            raise Exception(f"Authentication failed: {str(e)}")
        else:
            # Non-authentication error, re-raise as-is
            raise


def get_workspace_by_id(workspace_id: str) -> WorkspaceTarget:
    """
    Get a workspace or starter workspace by ID.

    Args:
        workspace_id: The workspace ID to look up

    Returns:
        WorkspaceTarget object with is_shared flag indicating if it's a starter workspace

    Raises:
        ValueError: If workspace cannot be found
    """
    from src.api.common import build_request

    target = None
    is_shared = False

    try:
        # Try as dedicated workspace first
        workspace_data = build_request("GET", f"workspaces/{workspace_id}")

        # Create a simple object to match the SDK interface
        class SimpleWorkspace:
            def __init__(self, data):
                self.name = data.get("name", "")
                self.id = data.get("workspaceID", workspace_id)
                self.endpoint = data.get("endpoint")

        target = SimpleWorkspace(workspace_data)
        is_shared = False  # Dedicated workspace
    except Exception as e:
        if "404" in str(e):
            # Try as starter workspace
            try:
                starter_workspace_data = build_request(
                    "GET", f"sharedtier/virtualWorkspaces/{workspace_id}"
                )

                # Create a simple object to match the SDK interface
                class SimpleVirtualWorkspace:
                    def __init__(self, data):
                        self.name = data.get("name", "")
                        self.id = data.get("virtualWorkspaceID", workspace_id)
                        self.endpoint = data.get("endpoint")
                        self.database_name = data.get("databaseName", "")

                target = SimpleVirtualWorkspace(starter_workspace_data)
                is_shared = True  # Shared/starter workspace
            except Exception:
                raise ValueError(f"Cannot find workspace {workspace_id}")
        else:
            raise e

    if not target:
        raise ValueError(f"Cannot find workspace {workspace_id}")

    return WorkspaceTarget(target, is_shared)


async def create_pipeline(
    ctx: Context,
    pipeline_name: str,
    data_source: str,
    target_table_or_procedure: str,
    workspace_id: str,
    database: Optional[str] = None,
    credentials: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a SQL pipeline for streaming CSV data from an S3 data source to a database table or stored procedure.

    This tool is restricted to S3 data sources only and automatically configures the pipeline with:
    - CSV format only
    - Comma delimiter (,)
    - MAX_PARTITIONS_PER_BATCH = 2
    - Auto-start enabled
    - No config options

    Args:
        pipeline_name: Name for the pipeline (will be used in CREATE PIPELINE statement)
        data_source: S3 URL (must start with 's3://')
        target_table_or_procedure: Target table name or procedure name (use "PROCEDURE procedure_name" for procedures)
        workspace_id: Workspace ID where the pipeline should be created
        database: Optional database name to use
        credentials: Optional AWS credentials in JSON format for private S3 buckets:
                    '{"aws_access_key_id": "key", "aws_secret_access_key": "secret", "aws_session_token": "token"}'
                    Use '{}' for public S3 buckets
        username: Optional database username for API key authentication
        password: Optional database password for API key authentication

    Returns:
        Dictionary with pipeline creation status and details

    Example:
        # Create pipeline from public S3 bucket
        pipeline_name = "uk_price_paid"
        data_source = "s3://singlestore-docs-example-datasets/pp-monthly/pp-monthly-update-new-version.csv"
        target_table_or_procedure = "process_uk_price_paid"
        credentials = "{}"

        # Create pipeline from private S3 bucket
        credentials = '{"aws_access_key_id": "AKIAIOSFODNN7EXAMPLE", "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"}'
    """
    # Validate workspace ID format
    validated_id = validate_workspace_id(workspace_id)

    # Validate that data source is S3
    if not data_source.lower().startswith("s3://"):
        return {
            "status": "error",
            "message": "Only S3 data sources are supported. Data source must start with 's3://'",
            "errorCode": "INVALID_DATA_SOURCE",
        }

    await ctx.info(
        f"Creating S3 pipeline '{pipeline_name}' from '{data_source}' to '{target_table_or_procedure}' in workspace '{validated_id}'"
    )

    start_time = time.time()

    # Fixed parameters for restrictions
    file_format = "CSV"
    max_partitions_per_batch = 2
    field_terminator = ","
    field_enclosure = '"'
    field_escape = "\\\\"
    line_terminator = "\\n"
    line_starting = ""

    # Build the CREATE PIPELINE SQL statement
    sql_parts = [
        f"CREATE OR REPLACE PIPELINE {pipeline_name} AS",
        f"     LOAD DATA S3 '{data_source}'",
    ]

    # Add credentials if provided
    if credentials:
        sql_parts.append(f"     CREDENTIALS '{credentials}'")

    # Add fixed max partitions per batch
    sql_parts.append(f"     MAX_PARTITIONS_PER_BATCH {max_partitions_per_batch}")

    # Determine if target is a table or procedure and format accordingly
    is_procedure = (
        target_table_or_procedure.upper().startswith("PROCEDURE ")
        or "process_" in target_table_or_procedure.lower()
    )

    if is_procedure:
        # Remove "PROCEDURE " prefix if present
        procedure_name = target_table_or_procedure
        if procedure_name.upper().startswith("PROCEDURE "):
            procedure_name = procedure_name[10:]  # Remove "PROCEDURE " prefix
        sql_parts.append(f"     INTO PROCEDURE {procedure_name}")
    else:
        sql_parts.append(f"     INTO TABLE {target_table_or_procedure}")

    # Add fixed format and CSV-specific options
    sql_parts.append(f"     FORMAT {file_format.upper()}")
    sql_parts.append(
        f"     FIELDS TERMINATED BY '{field_terminator}' ENCLOSED BY '{field_enclosure}' ESCAPED BY '{field_escape}'"
    )
    sql_parts.append(
        f"     LINES TERMINATED BY '{line_terminator}' STARTING BY '{line_starting}'"
    )

    # Combine all parts into final SQL
    create_pipeline_sql = "\n".join(sql_parts) + ";"

    logger.info(create_pipeline_sql)

    try:
        # Execute the CREATE PIPELINE statement
        create_result = await run_sql(
            ctx=ctx,
            sql_query=create_pipeline_sql,
            id=validated_id,
            database=database,
            username=username,
            password=password,
        )

        if create_result.get("status") != "success":
            return {
                "status": "error",
                "message": f"Failed to create pipeline: {create_result.get('message', 'Unknown error')}",
                "errorCode": "PIPELINE_CREATION_FAILED",
                "errorDetails": create_result,
            }

        # If auto_start is True, also start the pipeline (always true in restricted mode)
        start_result = None
        start_pipeline_sql = f"START PIPELINE IF NOT RUNNING {pipeline_name};"
        start_result = await run_sql(
            ctx=ctx,
            sql_query=start_pipeline_sql,
            id=validated_id,
            database=database,
            username=username,
            password=password,
        )

        execution_time = (time.time() - start_time) * 1000

        # Track analytics
        settings = config.get_settings()
        user_id = config.get_user_id()
        settings.analytics_manager.track_event(
            user_id,
            "tool_calling",
            {
                "name": "create_pipeline",
                "pipeline_name": pipeline_name,
                "workspace_id": validated_id,
                "auto_start": True,
            },
        )

        # Build success message
        success_message = f"Pipeline '{pipeline_name}' created successfully"
        if start_result and start_result.get("status") == "success":
            success_message += " and started"

        return {
            "status": "success",
            "message": success_message,
            "data": {
                "pipelineName": pipeline_name,
                "dataSource": data_source,
                "targetTableOrProcedure": target_table_or_procedure,
                "workspaceId": validated_id,
                "database": database,
                "autoStarted": start_result and start_result.get("status") == "success",
                "createSql": create_pipeline_sql,
                "startSql": f"START PIPELINE IF NOT RUNNING {pipeline_name};",
            },
            "metadata": {
                "executionTimeMs": round(execution_time, 2),
                "timestamp": datetime.now().isoformat(),
                "fileFormat": "CSV",
                "maxPartitionsPerBatch": 2,
                "creationResult": create_result,
                "startResult": start_result,
            },
        }

    except Exception as e:
        logger.error(f"Error creating pipeline: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to create pipeline: {str(e)}",
            "errorCode": "PIPELINE_CREATION_ERROR",
            "errorDetails": {
                "exception_type": type(e).__name__,
                "pipelineName": pipeline_name,
                "workspaceId": validated_id,
            },
        }


async def run_sql(
    ctx: Context,
    sql_query: str,
    id: str,
    database: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Use this tool to execute a single SQL statement against a SingleStore database.

    Returns:
    - Query results with column names and typed values
    - Row count and metadata
    - Execution status
    - Workspace type ("shared" for starter workspaces, "dedicated" for regular workspaces)
    - Workspace name

    Args:
        id: Workspace or starter workspace ID
        sql_query: The SQL query to execute
        database: (optional) Database name to use
        username: (optional) Database username for authentication. If not provided, will be requested via elicitation for API key auth
        password: (optional) Database password for authentication. If not provided, will be requested via elicitation for API key auth

    Returns:
        Standardized response with query results and metadata
    """
    # Validate workspace ID format
    validated_id = validate_workspace_id(id)

    await ctx.info(
        f"Running SQL query on workspace ID '{validated_id}' with database '{database}': {sql_query}"
    )

    settings = config.get_settings()

    # Target can either be a workspace or a starter workspace
    target = get_workspace_by_id(validated_id)
    database_name = database

    # For starter workspaces, use their database name if not specified
    if target.is_shared and target.database_name and not database_name:
        database_name = target.database_name

    # Get database credentials based on authentication method
    try:
        db_username, db_password = await _get_database_credentials(
            ctx, target, database_name, username, password
        )
    except Exception as e:
        if "Database credentials required" in str(e):
            # Handle the specific case where elicitation is not supported
            return {
                "status": "error",
                "message": str(e),
                "errorCode": "CREDENTIALS_REQUIRED",
                "workspace_id": validated_id,
                "workspace_name": target.name,
                "workspace_type": "shared" if target.is_shared else "dedicated",
                "instruction": (
                    "Please call this function again with the same parameters once you have "
                    "the database credentials available, or ask the user to provide their "
                    "database username and password for this workspace."
                ),
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to obtain database credentials: {str(e)}",
                "errorCode": "AUTHENTICATION_ERROR",
            }

    # Execute the SQL query
    start_time = time.time()
    try:
        result = await __execute_sql_unified(
            ctx=ctx,
            target=target,
            sql_query=sql_query,
            username=db_username,
            password=db_password,
            database=database_name,
        )
    except Exception as e:
        # Check if this is an authentication error from __execute_sql_unified
        if "Authentication failed:" in str(e):
            # Authentication error already handled by __execute_sql_unified (credentials invalidated)
            return {
                "status": "error",
                "message": str(e),
                "errorCode": "AUTHENTICATION_ERROR",
                "workspace_id": validated_id,
                "workspace_name": target.name,
                "workspace_type": "shared" if target.is_shared else "dedicated",
                "instruction": (
                    "Authentication failed. Please provide valid database credentials "
                    "for this workspace and try again."
                ),
            }
        else:
            # Non-authentication error, re-raise
            raise

    results_data = result.get("data", [])

    logger.debug(
        f"result: {results_data}, type: {type(results_data)}, id: {id}, database_name: {database_name}"
    )

    execution_time_ms = int((time.time() - start_time) * 1000)

    # Track analytics
    settings.analytics_manager.track_event(
        db_username,
        "tool_calling",
        {
            "name": "run_sql",
            "starter_workspace_id": id,
            "workspace_type": "shared" if target.is_shared else "dedicated",
        },
    )

    # Build standardized response
    workspace_type = "shared" if target.is_shared else "dedicated"
    row_count = len(results_data)

    return {
        "status": "success",
        "message": f"Query executed successfully. {row_count} rows returned.",
        "data": {
            "result": results_data,
            "row_count": row_count,
            "workspace_id": id,
            "workspace_name": target.name,
            "database": database_name,
            "status": result.get("status", "Success"),
        },
        "metadata": {
            "query_length": len(sql_query),
            "execution_time_ms": execution_time_ms,
            "workspace_type": workspace_type,
            "database_used": database_name,
            "executed_at": datetime.now().isoformat(),
        },
    }
