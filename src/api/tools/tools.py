from enum import Enum
import json
import logging
import os
import re
import uuid
import datetime
import singlestoredb as s2
import nbformat as nbf
import nbformat.v4 as nbfv4

from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import Context

from src.config import config
from src.api.tools.s2_manager import S2Manager
from src.api.common import (
    __get_user_id,
    build_request,
    get_access_token,
    get_org_id,
    query_graphql_organizations,
    get_current_organization,
)
from src.api.tools.types import Tool
from src.api.tools.types import WorkspaceTarget

# Set up logger for this module
logger = logging.getLogger(__name__)

SAMPLE_NOTEBOOK_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "sample_notebook.ipynb"
)


def __execute_sql_unified(
    ctx: Context,
    target: WorkspaceTarget,
    sql_query: str,
    username: str,
    password: str,
    database: str | None = None,
) -> dict:
    """
    Execute SQL operations on a connected workspace or virtual workspace.
    Returns results and column names in a dictionary format.
    """

    if target.endpoint is None:
        raise ValueError("Workspace or virtual workspace does not have an endpoint. ")
    endpoint = target.endpoint
    database_name = database

    # Parse host and port from endpoint
    if ":" in endpoint:
        host, port = endpoint.split(":", 1)
    else:
        host = endpoint
        port = None

    s2_manager = S2Manager(
        host=host,
        port=port,
        user=username,
        password=password,
        database=database_name,
    )

    workspace_type = "shared/virtual" if target.is_shared else "dedicated"
    ctx.report_progress(
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


def __get_virtual_workspace(virtual_workspace_id: str):
    """
    Get information about a specific virtual workspace.
    """
    settings = config.get_settings()
    user_id = config.get_user_id()
    settings.analytics_manager.track_event(
        user_id,
        "tool_calling",
        {
            "name": "__get_virtual_workspace",
            "virtual_workspace_id": virtual_workspace_id,
        },
    )
    return build_request("GET", f"sharedtier/virtualWorkspaces/{virtual_workspace_id}")


def __create_virtual_workspace(name: str, database_name: str, workspace_group=None):
    """
    Create a new virtual workspace with the specified name and database name.

    workspace_group should be a dictionary containing 'name' and 'cellID'.
    """
    settings = config.get_settings()
    user_id = config.get_user_id()
    settings.analytics_manager.track_event(
        user_id,
        "tool_calling",
        {
            "name": "__create_virtual_workspace",
            "workspace_name": name,
            "database_name": database_name,
        },
    )

    # Ensure workspace_group is properly formatted as a dictionary
    if not workspace_group:
        workspace_group = {"name": "DEFAULT"}

    # If workspace_group is provided as a string, try to convert it to a dict
    if isinstance(workspace_group, str):
        try:
            workspace_group = json.loads(workspace_group)
        except json.JSONDecodeError:
            # If it can't be parsed as JSON, assume it's meant to be a name
            workspace_group = {"name": workspace_group}

    # Ensure workspace_group is a dictionary
    if not isinstance(workspace_group, dict):
        raise ValueError(
            "workspace_group must be a dictionary with 'name' and 'cellID' keys"
        )

    # Create the payload with proper structure
    payload = {
        "name": name,
        "databaseName": database_name,
        "workspaceGroup": workspace_group,
    }

    return build_request("POST", "sharedtier/virtualWorkspaces", data=payload)


def __create_virtual_workspace_user(
    virtual_workspace_id: str, username: str, password: str
):
    """
    Create a new user for a virtual workspace.
    """
    settings = config.get_settings()
    user_id = config.get_user_id()
    settings.analytics_manager.track_event(
        user_id,
        "tool_calling",
        {
            "name": "__create_virtual_workspace_user",
            "virtual_workspace_id": virtual_workspace_id,
            "username": username,
        },
    )
    payload = {"userName": username, "password": password}
    return build_request(
        "POST",
        f"sharedtier/virtualWorkspaces/{virtual_workspace_id}/users",
        data=payload,
    )


def camel_to_snake(s: Optional[str]) -> Optional[str]:
    """Convert camel-case to snake-case."""
    if s is None:
        return None
    out = re.sub(r"([A-Z]+)", r"_\1", s).lower()
    if out and out[0] == "_":
        return out[1:]
    return out


# Migration state management (in-memory store)
_migration_store: Dict[str, Dict[str, Any]] = {}


def _store_migration(migration_id: str, migration_data: Dict[str, Any]) -> None:
    """Store migration data in memory."""
    _migration_store[migration_id] = migration_data


def _get_migration(migration_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve migration data from memory."""
    return _migration_store.get(migration_id)


def _remove_migration(migration_id: str) -> None:
    """Remove migration data from memory."""
    _migration_store.pop(migration_id, None)


def _split_sql_statements(sql: str) -> List[str]:
    """Split SQL into individual statements."""
    # Remove comments and split by semicolon
    statements = []
    for stmt in sql.split(";"):
        stmt = stmt.strip()
        if stmt and not stmt.startswith("--"):
            statements.append(stmt)
    return statements


class Mode(Enum):
    ONCE = "Once"
    RECURRING = "Recurring"

    @classmethod
    def from_str(cls, s: str) -> "Mode":
        try:
            return cls[str(camel_to_snake(s)).upper()]
        except KeyError:
            raise ValueError(f"Unknown Mode: {s}")

    def __str__(self) -> str:
        """Return string representation."""
        return self.value

    def __repr__(self) -> str:
        """Return string representation."""
        return str(self)


def __create_scheduled_job(
    notebook_path: str, mode: str, create_snapshot: bool, access_token: str = None
):
    """
    Create a new scheduled job for running a notebook periodically.

    Args:
        name: Name of the job
        notebook_path: Path to the notebook to be executed
        schedule_mode: Mode of the schedule (Once or Recurring)
        execution_interval_minutes: Minutes between executions (for Recurring mode)
        start_at: When to start the job (ISO 8601 format)
        description: Optional description of the job
        create_snapshot: Whether to create a snapshot of the notebook before execution
        runtime_name: Name of the runtime to use for the job execution
        parameters: List of parameter objects to pass to the notebook
        target_config: Optional target configuration for the job
    """

    mode_enum = Mode.from_str(mode)

    settings = config.get_settings()

    try:
        jobs_manager = s2.manage_workspaces(
            access_token=access_token,
            base_url=settings.s2_api_base_url,
        ).organizations.current.jobs
        job = jobs_manager.schedule(
            notebook_path=notebook_path,
            mode=mode_enum,
            create_snapshot=create_snapshot,
        )
        return job
    except Exception as e:
        return {"status": "error", "message": str(e)}


def __prepare_database_migration(
    ctx: Context,
    migration_sql: str,
    workspace_id: str,
    database: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Prepare a database migration by creating a temporary database branch for testing.

    Args:
        migration_sql: The SQL statements to execute for the migration
        workspace_id: The target workspace ID where migration will eventually be applied
        database: Optional database name to use
        description: Optional description of the migration

    Returns:
        Dictionary with migration details including temporary branch info
    """
    settings = config.get_settings()
    user_id = config.get_user_id()

    # Generate unique IDs
    migration_id = str(uuid.uuid4())
    branch_database_name = f"migration_test_{migration_id[:8]}"

    # Get the source workspace and database info
    target = __get_workspace_by_id(workspace_id)

    # Check if target is a shared workspace - migrations not supported
    if target.is_shared:
        raise ValueError(
            "Database migrations are not supported on shared/virtual workspaces. "
            "Please use the 'run_sql' tool to execute your SQL statements directly on the shared workspace instead."
        )

    try:
        source_database = database

        if not source_database:
            raise ValueError("Database name is required for migration")

        # Create database branch for testing
        branch_sql = f"ATTACH DATABASE {source_database} AS {branch_database_name};"

        username = __get_user_id()
        password = get_access_token()

        # Execute branch creation
        branch_result = __execute_sql_unified(
            ctx=ctx,
            target=target,
            sql_query=branch_sql,
            username=username,
            password=password,
            database=source_database,
        )

        if branch_result["status"] != "Success":
            raise Exception(f"Failed to create database branch: {branch_result}")

        # Execute migration SQL on the branch
        statements = _split_sql_statements(migration_sql)
        migration_results = []

        for stmt in statements:
            if stmt.strip():
                try:
                    # Execute each statement on the branch database
                    result = __execute_sql_unified(
                        ctx=ctx,
                        target=target,
                        sql_query=stmt,
                        username=username,
                        password=password,
                        database=branch_database_name,
                    )
                    migration_results.append(
                        {"statement": stmt, "status": "success", "result": result}
                    )
                except Exception as stmt_error:
                    migration_results.append(
                        {"statement": stmt, "status": "error", "error": str(stmt_error)}
                    )
                    # Stop on first error
                    raise Exception(
                        f"Migration failed on statement: {stmt}. Error: {str(stmt_error)}"
                    )

        # Store migration information
        migration_data = {
            "migration_id": migration_id,
            "migration_sql": migration_sql,
            "description": description,
            "source_workspace_id": workspace_id,
            "source_database": source_database,
            "branch_database_name": branch_database_name,
            "migration_results": migration_results,
            "created_at": datetime.datetime.now().isoformat(),
            "status": "prepared",
        }

        _store_migration(migration_id, migration_data)

        # Track the event
        settings.analytics_manager.track_event(
            user_id,
            "tool_calling",
            {
                "name": "__prepare_database_migration",
                "migration_id": migration_id,
                "source_workspace_id": workspace_id,
                "branch_database_name": branch_database_name,
            },
        )

        return {
            "migration_id": migration_id,
            "status": "success",
            "message": "Migration prepared successfully using database branch",
            "branch_info": {
                "workspace_id": workspace_id,
                "workspace_name": target.name,
                "workspace_type": "shared" if target.is_shared else "dedicated",
                "source_database": source_database,
                "branch_database_name": branch_database_name,
            },
            "migration_results": migration_results,
            "statements_executed": len(
                [r for r in migration_results if r["status"] == "success"]
            ),
            "total_statements": len(statements),
        }

    except Exception as e:
        # Cleanup on error - try to drop the branch database if it was created
        if "branch_database_name" in locals() and branch_database_name:
            try:
                cleanup_sql = f"DROP DATABASE IF EXISTS {branch_database_name};"
                __execute_sql_unified(
                    ctx=ctx,
                    target=target,
                    sql_query=cleanup_sql,
                    username=__get_user_id(),
                    password=get_access_token(),
                    database=source_database,
                )
            except Exception:
                pass

        return {
            "migration_id": migration_id,
            "status": "error",
            "message": f"Failed to prepare migration: {str(e)}",
            "error": str(e),
        }


def __complete_database_migration(
    ctx: Context,
    migration_id: str,
    apply_to_production: bool = True,
) -> Dict[str, Any]:
    """
    Complete a database migration by applying it to the production database or cleaning up the branch.

    Args:
        migration_id: The migration ID from prepare_database_migration
        apply_to_production: Whether to apply changes to production (True) or just cleanup (False)

    Returns:
        Dictionary with completion results
    """
    settings = config.get_settings()
    user_id = config.get_user_id()

    # Retrieve migration data
    migration_data = _get_migration(migration_id)
    if not migration_data:
        return {"status": "error", "message": f"Migration {migration_id} not found"}

    results = []
    source_workspace_id = migration_data["source_workspace_id"]
    source_database = migration_data["source_database"]
    branch_database_name = migration_data["branch_database_name"]

    # Get workspace target
    target = __get_workspace_by_id(source_workspace_id)

    # Check if target is a shared workspace - migrations not supported
    if target.is_shared:
        raise ValueError(
            "Database migrations are not supported on shared/virtual workspaces. "
            "Please use the 'run_sql' tool to execute your SQL statements directly on the shared workspace instead."
        )

    try:
        username = __get_user_id()
        password = get_access_token()

        if apply_to_production:
            # Apply migration to production database
            migration_sql = migration_data["migration_sql"]
            statements = _split_sql_statements(migration_sql)

            for stmt in statements:
                if stmt.strip():
                    result = __execute_sql_unified(
                        ctx=ctx,
                        target=target,
                        sql_query=stmt,
                        username=username,
                        password=password,
                        database=source_database,
                    )
                    results.append(
                        {"statement": stmt, "status": "success", "result": result}
                    )

        # Cleanup: Drop the branch database
        cleanup_sql = f"DROP DATABASE IF EXISTS {branch_database_name};"
        cleanup_result = __execute_sql_unified(
            ctx=ctx,
            target=target,
            sql_query=cleanup_sql,
            username=username,
            password=password,
            database=source_database,
        )

        cleanup_message = (
            f"Branch database '{branch_database_name}' successfully cleaned up"
            if cleanup_result["status"] == "Success"
            else f"Warning: Failed to cleanup branch database '{branch_database_name}'"
        )

        # Remove migration from memory
        _remove_migration(migration_id)

        # Track the event
        settings.analytics_manager.track_event(
            user_id,
            "tool_calling",
            {
                "name": "__complete_database_migration",
                "migration_id": migration_id,
                "applied_to_production": apply_to_production,
                "branch_database_name": branch_database_name,
            },
        )

        return {
            "migration_id": migration_id,
            "status": "success",
            "message": (
                "Migration completed successfully"
                if apply_to_production
                else "Migration discarded"
            ),
            "applied_to_production": apply_to_production,
            "production_results": results if apply_to_production else [],
            "cleanup_message": cleanup_message,
            "statements_applied": len(results) if apply_to_production else 0,
            "branch_database_name": branch_database_name,
        }

    except Exception as e:
        return {
            "migration_id": migration_id,
            "status": "error",
            "message": f"Failed to complete migration: {str(e)}",
            "error": str(e),
        }


def get_user_id(ctx: Context) -> str:
    """
    Retrieve the current user's unique identifier.

    Returns:
        str: UUID format identifier for the current user

    Required for:
    - Constructing paths or references to personal resources

    Performance Tip:
    Cache the returned ID when making multiple API calls.
    """
    settings = config.get_settings()
    user_id = config.get_user_id()
    # Track tool call event
    settings.analytics_manager.track_event(
        user_id, "tool_calling", {"name": "get_user_id"}
    )
    return __get_user_id()


def prepare_database_migration(
    ctx: Context,
    migration_sql: str,
    workspace_id: str,
    database: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Prepare a database migration by creating a temporary database branch for safe testing.

    This tool performs database schema migrations by automatically generating and executing DDL statements
    in a safe testing environment using SingleStore's database branching feature before applying to production.

    ⚠️  IMPORTANT: This tool only works with dedicated workspaces. For shared/virtual workspaces,
    use the 'run_sql' tool to execute your SQL statements directly instead.

    Database branching creates an exact copy of your production database that shares the same history but
    diverges once created, allowing you to test migrations without impacting production performance or stability.

    Supported operations:
    CREATE operations:
    - Add new columns (e.g., "ALTER TABLE users ADD COLUMN email VARCHAR(255)")
    - Create new tables (e.g., "CREATE TABLE posts (id INT PRIMARY KEY, title VARCHAR(255))")
    - Add constraints (e.g., "ALTER TABLE users ADD CONSTRAINT unique_email UNIQUE (email)")

    ALTER operations:
    - Modify column types (e.g., "ALTER TABLE posts MODIFY COLUMN views BIGINT")
    - Rename columns (e.g., "ALTER TABLE users CHANGE user_name username VARCHAR(255)")
    - Add/modify indexes (e.g., "CREATE INDEX idx_posts_title ON posts(title)")

    DROP operations:
    - Remove columns (e.g., "ALTER TABLE users DROP COLUMN temporary_field")
    - Drop tables (e.g., "DROP TABLE old_logs")
    - Remove constraints (e.g., "ALTER TABLE posts DROP INDEX idx_old_constraint")

    The tool will:
    1. Create a temporary database branch using ATTACH DATABASE command
    2. Execute the migration SQL in the branch database
    3. Return migration details for verification
    4. Allow you to test the changes before applying to production

    Args:
        migration_sql: The SQL statements to execute for the migration
        workspace_id: The target workspace ID where migration will eventually be applied
        database: Optional database name to use (required for branching)
        description: Optional description of the migration

    Returns:
        Dictionary with migration ID, branch database details, and execution results

    Workflow:
    1. Creates a temporary database branch of the source database
    2. Applies the migration SQL in that branch
    3. Returns migration details for verification

    Important Notes:
    After executing this tool, you MUST:
    1. Test the migration in the branch database using the 'run_sql' tool
    2. Ask for confirmation before proceeding
    3. Use 'complete_database_migration' tool to apply changes to production database

    Example:
    For a migration like:
    ALTER TABLE users ADD COLUMN last_login TIMESTAMP;

    You should test it with:
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'last_login';

    You can use 'run_sql' with the workspace ID and branch database name to test the migration.

    Error Handling:
    On error, the tool will:
    1. Automatically attempt to clean up the branch database
    2. Return detailed error information
    3. Ensure no partial changes are left in an inconsistent state

    Benefits of Database Branching:
    - Cost-effective: No additional infrastructure needed
    - Fast: Instant creation with no data duplication in object store
    - Isolated: Changes don't impact production performance
    - Exact replica: Contains all production data and structure
    """
    ctx.info(
        "Preparing database migration with the following parameters: "
        f"workspace_id={workspace_id}, database={database}, description={description}"
        "This operation can take some time depending on the size of the database."
    )
    return __prepare_database_migration(
        ctx=ctx,
        migration_sql=migration_sql,
        workspace_id=workspace_id,
        database=database,
        description=description,
    )


def complete_database_migration(
    ctx: Context,
    migration_id: str,
    apply_to_production: bool = True,
) -> Dict[str, Any]:
    """
    Complete a database migration by applying it to the production database or discarding it.

    This tool finalizes a database migration that was prepared using 'prepare_database_migration'.
    It can either apply the tested changes to the production database or discard them entirely.

    ⚠️  IMPORTANT: This tool only works with dedicated workspaces. For shared/virtual workspaces,
    use the 'run_sql' tool to execute your SQL statements directly instead.

    Args:
        migration_id: The migration ID returned from 'prepare_database_migration'
        apply_to_production: Whether to apply changes to production (True) or just cleanup (False)

    Returns:
        Dictionary with completion results including applied statements and cleanup status

    Use Cases:
    1. Apply Migration: Set apply_to_production=True to execute the migration on the production database
    2. Discard Migration: Set apply_to_production=False to cleanup without applying changes

    Important Notes:
    - This tool must be called after 'prepare_database_migration' to properly cleanup the branch database
    - If apply_to_production=True, the migration SQL will be executed on the original database
    - If apply_to_production=False, only cleanup will be performed
    - The branch database will be automatically dropped using DROP DATABASE command

    Safety Features:
    - Validates migration exists before proceeding
    - Executes statements in the same order as tested
    - Provides detailed results for each statement
    - Automatically cleans up branch database regardless of success/failure

    Database Branching Benefits:
    - Clean cleanup: Branch databases are automatically dropped
    - No orphaned resources: No temporary workspaces to manage
    - Cost effective: Only pay for new data added to the branch

    Example Usage:
    # Apply the migration to production
    complete_database_migration(migration_id="abc-123", apply_to_production=True)

    # Discard the migration without applying
    complete_database_migration(migration_id="abc-123", apply_to_production=False)
    """
    return __complete_database_migration(
        ctx=ctx, migration_id=migration_id, apply_to_production=apply_to_production
    )


def run_sql(
    ctx: Context, sql_query: str, id: str, database: Optional[str] = None
) -> Dict[str, Any]:
    """
    Use this tool to execute a single SQL statement against a SingleStore database.

    Returns:
    - Query results with column names and typed values
    - Row count and metadata
    - Execution status
    - Workspace type ("shared" for virtual workspaces, "dedicated" for regular workspaces)
    - Workspace name

    Args:
        id: Workspace or virtual workspace ID
        sql_query: The SQL query to execute
        database: (optional) Database name to use

    Returns:
        Dictionary with query results, metadata, and workspace information
    """

    ctx.info(
        f"Running SQL query on workspace ID '{id}' with database '{database}': {sql_query}"
    )

    settings = config.get_settings()

    # Target can either be a workspace or a virtual workspace
    target = __get_workspace_by_id(id)
    database_name = database

    # For virtual workspaces, use their database name if not specified
    if target.is_shared and target.database_name and not database_name:
        database_name = target.database_name

    username = __get_user_id()
    password = get_access_token()

    result = __execute_sql_unified(
        ctx=ctx,
        target=target,
        sql_query=sql_query,
        username=username,
        password=password,
        database=database_name,
    )

    # Add workspace type information to the result
    result["workspace_type"] = "shared" if target.is_shared else "dedicated"
    result["workspace_name"] = target.name

    settings.analytics_manager.track_event(
        username,
        "tool_calling",
        {
            "name": "run_sql",
            "virtual_workspace_id": id,
            "workspace_type": result["workspace_type"],
        },
    )
    return result


def create_virtual_workspace(
    name: str,
    database_name: str,
    username: str,
    password: str,
    workspace_group: Dict[str, str] = {
        "cellID": "452cc4b1-df20-4130-9e2f-e72ba79e3d46"
    },
) -> Dict[str, Any]:
    """
    Create a new starter (virtual) workspace in SingleStore and set up user access.

    Process:
    1. Creates a virtual workspace with specified name and database
    2. Creates a user account for accessing the workspace
    3. Returns both workspace details and access credentials

    Args:
        name: Unique name for the new starter workspace
        database_name: Name of the database to create in the starter workspace
        username: Username for accessing the new starter workspace
        password: Password for accessing the new starter workspace
        workspace_group: Optional workspace group configuration

    Returns:
        Dictionary with workspace and user creation details
    """
    settings = config.get_settings()
    user_id = config.get_user_id()
    settings.analytics_manager.track_event(
        user_id,
        "tool_calling",
        {
            "name": "create_virtual_workspace",
            "workspace_name": name,
            "database_name": database_name,
            "username": username,
        },
    )
    workspace_data = __create_virtual_workspace(name, database_name, workspace_group)
    return {
        "workspace": workspace_data,
        "user": __create_virtual_workspace_user(
            workspace_data.get("virtualWorkspaceID"),
            username,
            password,
        ),
    }


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


def check_if_file_exists(file_name: str, access_token: str = None) -> Dict[str, Any]:
    """
    Check if a file (notebook) exists in the user's shared space.

    Args:
        file_name: Name of the file to check (with or without .ipynb extension)

    Returns:
        JSON object with the file existence status
        {
            "exists": True/False,
            "message": "File exists" or "File does not exist"
        }
    """
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
    return {
        "exists": exists,
        "message": (f"File {file_name} {'exists' if exists else 'does not exist'}"),
    }


def create_notebook(
    notebook_name: str, content: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a new Jupyter notebook in your personal space. Only supports python and markdown.

    Parameters:
    - notebook_name (required): Name for the new notebook
      - Can include or omit .ipynb extension
      - Must be unique in your personal space

    - content (optional): JSON object with the following structure:
        {
            "cells": [
                {"type": "markdown", "content": "Markdown content here"},
                {"type": "code", "content": "Python code here"}
            ]
        }
        - 'type' must be either 'markdown' or 'code'
        - 'content' is the text content of the cell
        IMPORTANT: The content must be valid JSON.

    How to use:
        - Before creating the notebook, call check_if_file_exists tool to verify if the notebook already exists.
        - Always install the dependencies on the first cell. Example:
            {
                "cells": [
                    {"type": "code", "content": "!pip install singlestoredb --quiet"},
                    // other cells...
                ]
            }
        - To connect to the database, use the variable "connection_url" that already exists in the notebook platform. Example:
            {
                "cells": [
                    {"type": "code", "content": "conn = s2.connect(connection_url)"},
                    // other cells...
                ]
            }
    """
    settings = config.get_settings()
    user_id = config.get_user_id()
    settings.analytics_manager.track_event(
        user_id,
        "tool_calling",
        {"name": "create_notebook", "notebook_name": notebook_name},
    )
    path = (
        notebook_name if notebook_name.endswith(".ipynb") else f"{notebook_name}.ipynb"
    )
    return __create_file_in_shared_space(path, content)


def create_scheduled_job(
    notebook_path: str, mode: str, create_snapshot: bool = True
) -> Dict[str, Any]:
    """
    Create an automated job to execute a SingleStore notebook on a schedule.

    Parameters:
    - notebook_path: Complete path to the notebook
    - mode: 'Once' for single execution or 'Recurring' for repeated runs
    - create_snapshot: Enable notebook backup before execution (default: True)

    Returns Job info with:
    - jobID: UUID of created job
    - status: Current state (SUCCESS, RUNNING, etc.)
    - createdAt: Creation timestamp
    - startedAt: Execution start time
    - schedule: Configured schedule details
    - error: Any execution errors

    Common Use Cases:
    1. Automated Data Processing:
       - ETL workflows
       - Data aggregation
       - Database maintenance

    2. Scheduled Reporting:
       - Performance metrics
       - Business analytics
       - Usage statistics

    3. Maintenance Tasks:
       - Health checks
       - Backup operations
       - Clean-up routines

    Related Operations:
    - get_job_details: Monitor job
    - list_job_executions: View job execution history
    """
    settings = config.get_settings()
    user_id = config.get_user_id()
    settings.analytics_manager.track_event(
        user_id,
        "tool_calling",
        {
            "name": "create_scheduled_job",
            "notebook_path": notebook_path,
            "mode": mode,
            "create_snapshot": create_snapshot,
        },
    )
    return __create_scheduled_job(notebook_path, mode, create_snapshot)


def __get_notebook_path_by_name(notebook_name: str, location: str = "personal") -> str:
    """
    Find a notebook by its name and return its full path.

    Args:
        notebook_name: The name of the notebook to find (with or without .ipynb extension)
        location: Where to look for the notebook - 'personal' or 'shared'

    Returns:
        The full path of the notebook if found

    Raises:
        ValueError: If no notebook with the given name is found
    """
    # Make sure we look for the right extension
    if not notebook_name.endswith(".ipynb"):
        search_name = f"{notebook_name}.ipynb"
    else:
        search_name = notebook_name

    # Get all files from the specified location
    if location.lower() == "personal":
        files_response = build_request("GET", "files/fs/personal")
    elif location.lower() == "shared":
        files_response = build_request("GET", "files/fs/shared")
    else:
        raise ValueError(
            f"Invalid location: {location}. Must be 'personal' or 'shared'"
        )

    # The API might return different structures
    # Handle both array of files or object with content property
    if isinstance(files_response, dict) and "content" in files_response:
        files = files_response["content"]
    elif isinstance(files_response, list):
        files = files_response
    else:
        raise ValueError(
            f"Unexpected response format from file listing API: {type(files_response)}"
        )

    # Filter to find notebooks matching the name (case insensitive)
    matching_notebooks = []
    for file in files:
        # Verify file is a dictionary with the expected fields
        if not isinstance(file, dict):
            continue

        # Skip if not a notebook or missing path
        if (
            "path" not in file
            or not isinstance(file["path"], str)
            or not file["path"].endswith(".ipynb")
        ):
            continue

        # Check if the name matches
        file_name = file["path"].split("/")[-1]  # Get just the filename portion
        if file_name.lower() == search_name.lower():
            matching_notebooks.append(file)

    if not matching_notebooks:
        raise ValueError(
            f"No notebook with name '{notebook_name}' found in {location} space"
        )

    # If we found multiple matches (unlikely with exact name match), return first one
    notebook_path = matching_notebooks[0]["path"]

    if location.lower() == "personal":
        user_id = __get_user_id()

        # Format for personal space: {projectID}/_internal-s2-personal/{userID}/{path}
        return f"_internal-s2-personal/{user_id}/{notebook_path}"

    # If we couldn't get the IDs or format correctly, return the raw path
    return notebook_path


def workspace_groups_info() -> List[Dict[str, Any]]:
    """
    List all workspace groups accessible to the user in SingleStore.

    Returns detailed information for each group:
    - name: Display name of the workspace group
    - deploymentType: Type of deployment (e.g., 'PRODUCTION')
    - state: Current status (e.g., 'ACTIVE', 'PAUSED')
    - workspaceGroupID: Unique identifier for the group
    - firewallRanges: Array of allowed IP ranges for access control
    - createdAt: Timestamp of group creation
    - regionID: Identifier for deployment region
    - updateWindow: Maintenance window configuration

    Use this tool to:
    1. Get workspace group IDs for other operations
    2. Plan maintenance windows

    Related operations:
    - Use workspaces_info to list workspaces within a group
    - Use execute_sql to run queries on workspaces in a group
    """
    settings = config.get_settings()
    user_id = config.get_user_id()
    settings.analytics_manager.track_event(
        user_id, "tool_calling", {"name": "workspace_groups_info"}
    )
    return [
        {
            "name": group["name"],
            "deploymentType": group["deploymentType"],
            "state": group["state"],
            "workspaceGroupID": group["workspaceGroupID"],
            "firewallRanges": group.get("firewallRanges", []),
            "createdAt": group["createdAt"],
            "regionID": group["regionID"],
            "updateWindow": group["updateWindow"],
        }
        for group in build_request("GET", "workspaceGroups")
    ]


def workspaces_info(workspace_group_id: str) -> List[Dict[str, Any]]:
    """
    List all workspaces within a specified workspace group in SingleStore.

    Returns detailed information for each workspace:
    - createdAt: Timestamp of workspace creation
    - deploymentType: Type of deployment (e.g., 'PRODUCTION')
    - endpoint: Connection URL for database access
    - name: Display name of the workspace
    - size: Compute and storage configuration
    - state: Current status (e.g., 'ACTIVE', 'PAUSED')
    - terminatedAt: End timestamp if applicable
    - workspaceGroupID: Workspacegroup identifier
    - workspaceID: Unique workspace identifier

    Args:
        workspace_group_id: Unique identifier of the workspace group

    Returns:
        List of workspace information dictionaries
    """
    settings = config.get_settings()
    user_id = config.get_user_id()
    settings.analytics_manager.track_event(
        user_id,
        "tool_calling",
        {"name": "workspaces_info", "workspace_group_id": workspace_group_id},
    )
    return [
        {
            "createdAt": workspace["createdAt"],
            "deploymentType": workspace.get("deploymentType", ""),
            "endpoint": workspace.get("endpoint", ""),
            "name": workspace["name"],
            "size": workspace["size"],
            "state": workspace["state"],
            "terminatedAt": workspace.get("terminatedAt", False),
            "workspaceGroupID": workspace["workspaceGroupID"],
            "workspaceID": workspace["workspaceID"],
        }
        for workspace in build_request(
            "GET",
            "workspaces",
            {"workspaceGroupID": workspace_group_id},
        )
    ]


def organization_info() -> Dict[str, Any]:
    """
    Retrieve information about the current user's organization in SingleStore.

    Returns organization details including:
    - orgID: Unique identifier for the organization
    - name: Organization display name
    """
    settings = config.get_settings()
    user_id = config.get_user_id()
    settings.analytics_manager.track_event(
        user_id, "tool_calling", {"name": "organization_info"}
    )
    return build_request("GET", "organizations/current")


def list_of_regions() -> List[Dict[str, Any]]:
    """
    List all available deployment regions where SingleStore workspaces can be deployed for the user.

    Returns region information including:
    - regionID: Unique identifier for the region
    - provider: Cloud provider (AWS, GCP, or Azure)
    - name: Human-readable region name (e.g., Europe West 2 (London), US West 2 (Oregon))

    Use this tool to:
    1. Select optimal deployment regions based on:
       - Geographic proximity to users
       - Compliance requirements
       - Cost considerations
       - Available cloud providers
    2. Plan multi-region deployments
    """
    return build_request("GET", "regions")


def list_virtual_workspaces() -> List[Dict[str, Any]]:
    """
    List all starter (virtual) workspaces available to the user in SingleStore.

    Returns detailed information about each starter workspace:
    - virtualWorkspaceID: Unique identifier for the workspace
    - name: Display name of the workspace
    - endpoint: Connection endpoint URL
    - databaseName: Name of the primary database
    - mysqlDmlPort: Port for MySQL protocol connections
    - webSocketPort: Port for WebSocket connections
    - state: Current status of the workspace

    Use this tool to:
    1. Get virtual workspace IDs for other operations
    2. Check starter workspace availability and status
    3. Obtain connection details for database access
    """
    return build_request("GET", "sharedtier/virtualWorkspaces")


def organization_billing_usage(
    start_time: str, end_time: str, aggregate_type: str
) -> Dict[str, Any]:
    """
    Retrieve detailed billing and usage metrics for your organization over a specified time period.

    Returns compute and storage usage data, aggregated by your chosen time interval
    (hourly, daily, or monthly). This tool is essential for:
    1. Monitoring resource consumption patterns
    2. Analyzing cost trends

    Args:
        start_time: Beginning of the usage period (UTC ISO 8601 format, e.g., '2023-07-30T18:30:00Z')
        end_time: End of the usage period (UTC ISO 8601 format)
        aggregate_type: Time interval for data grouping ('hour', 'day', or 'month')

    Returns:
        Usage metrics and billing information
    """
    return build_request(
        "GET",
        "billing/usage",
        {
            "startTime": start_time,
            "endTime": end_time,
            "aggregateBy": aggregate_type,
        },
    )


def list_notebook_samples() -> List[Dict[str, Any]]:
    """
    Retrieve a catalog of pre-built notebook templates available in SingleStore Spaces.

    Returns for each notebook:
    - name: Template name and title
    - description: Detailed explanation of the notebook's purpose
    - contentURL: Direct download link for the notebook
    - likes: Number of user endorsements
    - views: Number of times viewed
    - downloads: Number of times downloaded
    - tags: List of Notebook tags

    Common template categories include:
    1. Getting Started guides
    2. Data loading and ETL patterns
    3. Query optimization examples
    4. Machine learning integrations
    5. Performance monitoring
    6. Best practices demonstrations
    """
    return build_request("GET", "spaces/notebooks")


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
    return build_request("GET", "files/fs/shared")


def get_job_details(job_id: str) -> Dict[str, Any]:
    """
    Retrieve comprehensive information about a scheduled notebook job.

    Returns:
    - jobID: Unique identifier (UUID format)
    - name: Display name of the job
    - description: Human-readable job description
    - createdAt: Creation timestamp
    - terminatedAt: End timestamp if completed
    - completedExecutionsCount: Number of successful runs
    - enqueuedBy: User ID who created the job
    - executionConfig: Notebook path and runtime settings
    - schedule: Mode, interval, and start time
    - targetConfig: Database and workspace settings
    - jobMetadata: Execution statistics and status

    Args:
        job_id: UUID of the scheduled job to retrieve details for

    Returns:
        Dictionary with job details
    """
    return build_request("GET", f"jobs/{job_id}")


def list_job_executions(job_id: str, start: int = 1, end: int = 10) -> Dict[str, Any]:
    """
    Retrieve execution history and performance metrics for a scheduled notebook job.

    Returns:
    - executions: Array of execution records containing:
      - executionID: Unique identifier for the execution
      - executionNumber: Sequential number of the run
      - jobID: Parent job identifier
      - status: Current state (Scheduled, Running, Completed, Failed)
      - startedAt: Execution start time (ISO 8601)
      - finishedAt: Execution end time (ISO 8601)
      - scheduledStartTime: Planned start time
      - snapshotNotebookPath: Backup notebook path if enabled

    Args:
        job_id: UUID of the scheduled job
        start: First execution number to retrieve (default: 1)
        end: Last execution number to retrieve (default: 10)

    Returns:
        Dictionary with execution records
    """
    return build_request(
        "GET",
        f"jobs/{job_id}/executions",
        params={"start": start, "end": end},
    )


def get_notebook_path(notebook_name: str, location: str = "personal") -> str:
    """
    Find the complete path of a notebook by its name and generate the properly formatted path for API operations.

    Args:
        notebook_name: The name of the notebook to find (with or without .ipynb extension)
        location: Where to look for the notebook - 'personal' or 'shared'

    Returns:
        Properly formatted path including project ID and user ID where needed

    Required for:
    - Creating scheduled jobs (use returned path as notebook_path parameter)
    """
    return __get_notebook_path_by_name(notebook_name, location)


async def get_organizations(ctx: Context) -> str:
    """
    List all available SingleStore organizations your account has access to.

    After logging in, this tool must be called first to identify which organization
    your queries should run against. Returns a list of organizations with:

    - orgID: Unique identifier for the organization
    - name: Display name of the organization

    Use this tool when:
    1. Starting a new session to see available organizations
    2. To verify permissions across multiple organizations
    3. Before switching context to a different organization

    After viewing the list, the tool will prompt you to select an organization:
    - If only one organization is available, it will be selected automatically
    - If multiple organizations are available, you'll be prompted to select one by name or ID
    - You can change your organization selection anytime using the `set_organization` tool
    - If no organizations are available, an error will be returned
    """

    settings = config.get_settings()
    user_id = config.get_user_id()
    # Track tool call event
    settings.analytics_manager.track_event(
        user_id, "tool_calling", {"name": "get_organizations"}
    )

    logger.debug("get_organizations called")
    logger.debug(f"Auth method: {settings.auth_method}")
    logger.debug(f"Is remote: {settings.is_remote}")

    # Only show organization selection for OAuth token authentication
    if settings.auth_method != "oauth_token":
        logger.debug("Skipping org selection - not OAuth token auth")
        return "✅ Organization selection is only required for OAuth token authentication. Your current authentication method doesn't require this step."

    try:
        logger.debug("Calling query_graphql_organizations...")
        # Get the list of organizations via GraphQL
        organizations = query_graphql_organizations()
        logger.debug(f"Retrieved {len(organizations)} organizations")

        if not organizations:
            logger.warning("No organizations available")
            return "❌ No organizations available for your account. Please check your access permissions."

        # Always return the list for user to choose from
        org_list = "\n".join(
            [f"- {org['name']} (ID: {org['orgID']})" for org in organizations]
        )

        logger.info(f"Found {len(organizations)} available organizations")

        return f"""📋 **Available SingleStore Organizations:**

{org_list}

✅ To select an organization, please use the `set_organization` tool with either the organization name or ID.

**Example:**
- `set_organization("your-org-name")`
- `set_organization("org-id-12345")`

Once you select an organization, all subsequent API calls will use that organization."""

    except Exception as e:
        logger.error(f"Error retrieving organizations: {str(e)}")
        return f"Error retrieving organizations: {e.with_traceback(None)}\n{str(e)}"


async def set_organization(orgID: str, ctx: Context) -> str:
    """
    Select which SingleStore organization to use for all subsequent API calls.

    This tool must be called after logging in and before making other API requests.
    Once set, all API calls will target the selected organization until changed.

    Args:
        orgID: Name or ID of the organization to select (use get_organizations to see available options)

    Returns:
        Success message with the selected organization details

    Usage:
    - Call get_organizations first to see available options
    - Then call this tool with either the organization's name or ID
    - All subsequent API calls will use the selected organization
    - You can call this tool anytime to switch to a different organization
    """

    settings = config.get_settings()
    user_id = config.get_user_id()
    # Track tool call event
    settings.analytics_manager.track_event(
        user_id, "tool_calling", {"name": "set_organization", "orgID": orgID}
    )

    try:
        # For OAuth token authentication, get the list of available organizations
        # and validate that the provided orgID is one the user has access to
        if settings.auth_method == "oauth_token":
            logger.debug("Getting available organizations for validation...")
            available_orgs = query_graphql_organizations()

            # Find the organization by ID or name
            selected_org = None
            for org in available_orgs:
                if orgID == org["orgID"] or orgID.lower() == org["name"].lower():
                    selected_org = org
                    break

            if not selected_org:
                available_names = [
                    f"{org['name']} (ID: {org['orgID']})" for org in available_orgs
                ]
                return (
                    f"Organization '{orgID}' not found. Available organizations:\n"
                    + "\n".join(available_names)
                )

            # Update the settings with the organization ID
            logger.debug(f"Setting org_id to: {selected_org['orgID']}")
            if hasattr(settings, "org_id"):
                settings.org_id = selected_org["orgID"]
            else:
                # For LocalSettings, we need to add the org_id attribute
                setattr(settings, "org_id", selected_org["orgID"])

            logger.info(f"Settings updated with org_id: {selected_org['orgID']}")
            return f"Successfully selected organization: {selected_org['name']} (ID: {selected_org['orgID']})"

        else:
            # For other authentication methods, try to get current organization
            logger.debug("Getting current organization...")
            current_org = get_current_organization()

            if not current_org:
                logger.error("Unable to get current organization")
                return "Unable to get current organization information."

            current_org_id = current_org.get("orgID") or current_org.get("id")
            current_org_name = current_org.get("name")

            logger.debug(f"Current org: {current_org_name} (ID: {current_org_id})")

            # Check if the provided orgID matches the current organization
            if orgID != current_org_id and orgID.lower() != current_org_name.lower():
                logger.warning(
                    f"Org mismatch: provided '{orgID}' vs current '{current_org_id}'"
                )
                return f"Organization '{orgID}' does not match your current organization '{current_org_name}' (ID: {current_org_id})"

            logger.debug("Organization match confirmed, updating settings...")
            # Update the settings with the organization ID
            if hasattr(settings, "org_id"):
                settings.org_id = current_org_id
            else:
                # For LocalSettings, we need to add the org_id attribute
                setattr(settings, "org_id", current_org_id)

            logger.info(f"Settings updated with org_id: {current_org_id}")
            return f"Successfully selected organization: {current_org_name} (ID: {current_org_id})"

    except Exception as e:
        logger.error(f"Error in set_organization: {str(e)}")
        return f"Error setting organization: {str(e)}"


def __get_workspace_by_id(workspace_id: str) -> WorkspaceTarget:
    """
    Get a workspace or virtual workspace by ID.

    Args:
        workspace_id: The workspace ID to look up

    Returns:
        WorkspaceTarget object with is_shared flag indicating if it's a virtual workspace

    Raises:
        ValueError: If workspace cannot be found
    """
    workspace_manager = s2.manage_workspaces(
        access_token=get_access_token(), organization_id=get_org_id()
    )

    target = None
    is_shared = False

    try:
        target = workspace_manager.get_workspace(workspace_id)
        is_shared = False  # Dedicated workspace
    except Exception as e:
        if "404" in str(e):
            # Try as virtual workspace
            target = workspace_manager.get_starter_workspace(workspace_id)
            is_shared = True  # Shared/virtual workspace
        else:
            raise e

    if not target:
        raise ValueError(f"Cannot find workspace {workspace_id}")

    return WorkspaceTarget(target, is_shared)


def create_starter_workspace(
    ctx: Context, name: str, database_name: str
) -> Dict[str, Any]:
    """
    Create a new starter workspace using the SingleStore SDK.

    This tool provides a modern SDK-based approach to creating starter workspaces,
    offering improved reliability and better error handling compared to direct API calls.

    Args:
        name: Unique name for the new starter workspace
        database_name: Name of the database to create in the starter workspace

    Returns:
        Dictionary with starter workspace creation details including:
        - workspace_id: Unique identifier for the created workspace
        - name: Display name of the workspace
        - endpoint: Connection endpoint URL
        - database_name: Name of the primary database

    Example Usage:
    ```python
    result = create_starter_workspace(
        ctx=ctx,
        name="my-test-workspace",
        database_name="analytics_db"
    )
    workspace_id = result["workspace_id"]
    endpoint = result["endpoint"]
    ```
    """
    ctx.info(f"Creating starter workspace '{name}' with database '{database_name}'")

    settings = config.get_settings()
    user_id = config.get_user_id()

    # Track analytics event
    settings.analytics_manager.track_event(
        user_id,
        "tool_calling",
        {
            "name": "create_starter_workspace",
            "workspace_name": name,
            "database_name": database_name,
        },
    )

    try:
        # Initialize workspace manager using the SDK
        workspace_manager = s2.manage_workspaces(
            access_token=get_access_token(),
            base_url=settings.s2_api_base_url,
            organization_id=get_org_id(),
        )

        # Create the starter workspace
        starter_workspace = workspace_manager.create_starter_workspace(
            name=name,
            database_name=database_name,
            # TODO: Dinamically set region_id if needed
            workspace_group={"cell_id": "3482219c-a389-4079-b18b-d50662524e8a"},
        )

        ctx.info(
            f"Starter workspace '{name}' created successfully with ID: {starter_workspace.workspace_id}"
        )

        return {
            "status": "success",
            "message": f"Starter workspace '{name}' created successfully",
            "name": starter_workspace.name,
            "endpoint": starter_workspace.endpoint,
            "database_name": starter_workspace.database_name,
        }

    except Exception as e:
        error_msg = f"Failed to create starter workspace '{name}': {str(e)}"
        ctx.error(error_msg)

        return {
            "status": "error",
            "message": error_msg,
            "error": str(e),
            "workspace_name": name,
            "database_name": database_name,
        }


def terminate_virtual_workspace(
    ctx: Context,
    workspace_id: str,
) -> Dict[str, Any]:
    """
    Terminate a virtual (starter) workspace using the SingleStore SDK.

    This tool provides a safe and reliable way to terminate virtual workspaces,
    with proper error handling and confirmation of the termination status.

    ⚠️  WARNING: This action is permanent and cannot be undone. All data in the
    workspace will be lost. Make sure to backup any important data before terminating.

    Args:
        workspace_id: Unique identifier of the virtual workspace to terminate

    Returns:
        Dictionary with termination status and details including:
        - status: "success" or "error"
        - message: Human-readable description of the result
        - workspace_id: ID of the terminated workspace
        - workspace_name: Name of the terminated workspace (if available)
        - termination_time: Timestamp when termination was initiated

    Benefits over direct API calls:
    - Automatic retry logic and error handling
    - Proper validation of workspace existence
    - Detailed error messages and status reporting
    - Built-in authentication handling

    Example Usage:
    ```python
    result = terminate_virtual_workspace(
        ctx=ctx,
        workspace_id="ws-abc123def456"
    )
    if result["status"] == "success":
        print(f"Workspace {result['workspace_name']} terminated successfully")
    else:
        print(f"Failed to terminate workspace: {result['message']}")
    ```
    """
    ctx.info(f"Terminating virtual workspace with ID: {workspace_id}")

    settings = config.get_settings()
    user_id = config.get_user_id()

    # Track analytics event
    settings.analytics_manager.track_event(
        user_id,
        "tool_calling",
        {
            "name": "terminate_virtual_workspace",
            "workspace_id": workspace_id,
        },
    )

    try:
        # Initialize workspace manager using the SDK
        workspace_manager = s2.manage_workspaces(
            access_token=get_access_token(),
            base_url=settings.s2_api_base_url,
            organization_id=get_org_id(),
        )

        # First, try to get the workspace details before termination
        workspace_name = None
        try:
            starter_workspace = workspace_manager.get_starter_workspace(workspace_id)
            workspace_name = starter_workspace.name
            ctx.info(f"Found virtual workspace '{workspace_name}' (ID: {workspace_id})")
        except Exception as e:
            # If we can't get the workspace, it might not exist or already be terminated
            ctx.warning(f"Could not retrieve workspace details: {str(e)}")
            raise ValueError(
                f"Virtual workspace '{workspace_id}' does not exist or has already been terminated."
            )

        # Terminate the virtual workspace
        workspace_manager.terminate_starter_workspace(workspace_id)

        termination_time = datetime.datetime.now().isoformat()

        success_message = f"Virtual workspace '{workspace_name or workspace_id}' terminated successfully"
        ctx.info(success_message)

        return {
            "status": "success",
            "message": success_message,
            "workspace_id": workspace_id,
            "workspace_name": workspace_name,
            "termination_time": termination_time,
        }

    except Exception as e:
        error_msg = f"Failed to terminate virtual workspace '{workspace_id}': {str(e)}"
        ctx.error(error_msg)

        return {
            "status": "error",
            "message": error_msg,
            "error": str(e),
            "workspace_id": workspace_id,
        }


tools_definition = [
    {"func": get_user_id},
    {"func": workspace_groups_info},
    {"func": workspaces_info},
    {"func": run_sql},
    {"func": organization_info},
    {"func": list_of_regions},
    {"func": list_virtual_workspaces},
    {"func": organization_billing_usage, "internal": True},
    {"func": list_notebook_samples, "internal": True},
    {"func": list_shared_files, "internal": True},
    {"func": create_notebook, "internal": True},
    {"func": check_if_file_exists, "internal": True},
    {"func": create_scheduled_job, "internal": True},
    {"func": get_job_details, "internal": True},
    {"func": list_job_executions, "internal": True},
    {"func": get_notebook_path, "internal": True},
    {"func": get_organizations},
    {"func": set_organization},
    # These tools are under development and not yet available for public use
    {"func": prepare_database_migration, "internal": True},
    {"func": complete_database_migration, "internal": True},
    # This tool is under development and not yet available for public use
    {"func": create_starter_workspace, "internal": True},
    {"func": terminate_virtual_workspace},
]

# Export the tools
tools = [Tool.create_from_dict(tool) for tool in tools_definition]
