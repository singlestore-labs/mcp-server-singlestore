# Structured Tool Responses

This document describes the structured response format used in the SingleStore MCP server tools.

## Overview

All tools in the SingleStore MCP server return responses in a consistent, structured format that follows the Model Context Protocol (MCP) specifications for structured output. This enables:

- Consistent client-side handling of tool responses
- Automatic schema generation and validation
- Better type safety and IDE autocompletion
- Clearer API documentation

## Response Structure

All tool responses follow this general structure:

```python
{
    "status": str,         # "success", "error", or "warning"
    "message": str,        # Human-readable message about the result
    "data": {...},         # Tool-specific structured data payload
    "metadata": {          # Additional contextual information
        "execution_time_ms": float,
        "timestamp": str,  # ISO 8601 format
        "user_id": str
    },
    # Optional error fields
    "error_code": str,     # Present only for status="error"
    "error_details": {...}, # Present only for status="error"
    "warning_details": str  # Present only for status="warning"
}
```

## Implementation

The structured response format is implemented using Pydantic models, which provide automatic validation and schema generation. The base models are:

- `ToolResponseBase`: Common fields for all responses
- `ToolResponse[T]`: Generic response container with a tool-specific data payload
- `ToolMetadata`: Common metadata fields

Each tool has its own specific data model that defines the structure of its response data payload.

## Example Usage

### Tool Implementation Example

Here's how a tool implementation looks using the structured response format:

```python
def run_sql(
    ctx: Context, sql_query: str, id: str, database: Optional[str] = None
) -> SqlResponse:
    """Execute a SQL query against a SingleStore database."""
    start_time = time.time()
    user_id = get_user_id_from_context(ctx)

    try:
        # Execute the query...

        return SqlResponse(
            status="success",
            message=f"Query executed successfully, returned {len(rows)} rows",
            data=SqlResult(
                columns=columns,
                rows=rows,
                row_count=len(rows),
                workspace_type="shared" if is_shared else "dedicated",
                workspace_name=workspace_name
            ),
            metadata=ToolMetadata(
                execution_time_ms=round((time.time() - start_time) * 1000, 2),
                timestamp=datetime.now(timezone.utc).isoformat(),
                user_id=user_id
            )
        )

    except Exception as e:
        return SqlResponse(
            status="error",
            message=f"SQL query failed: {str(e)}",
            error_code="SQL_EXECUTION_ERROR",
            error_details={
                "exception": type(e).__name__,
                "workspace_id": id,
                "database": database
            },
            metadata=ToolMetadata(
                execution_time_ms=round((time.time() - start_time) * 1000, 2),
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        )
```

### Calling Tool Functions and Handling Responses

Here's how to call a tool function and handle its response:

```python
# Import the tools
from src.api.tools.tools import get_organizations, run_sql, get_virtual_workspaces

# Call a tool to get organizations
org_response = get_organizations(ctx)

# Check for success and process the response
if org_response.status == "success":
    # Access the data in a type-safe way
    organizations = org_response.data.organizations

    for org in organizations:
        print(f"Organization: {org.name} (ID: {org.org_id})")

    # Select the first organization
    if organizations:
        selected_org = organizations[0]

        # Use another tool with the selected organization
        set_org_response = set_organization(ctx, orgID=selected_org.org_id)

        if set_org_response.status == "success":
            print(f"Successfully set organization to: {set_org_response.data.name}")
        else:
            print(f"Error setting organization: {set_org_response.message}")
            if set_org_response.error_code:
                print(f"Error code: {set_org_response.error_code}")
else:
    print(f"Error getting organizations: {org_response.message}")
```

### Working with Different Tool Response Types

Different tools return different response types with specialized data models:

```python
# Running SQL queries
sql_response = run_sql(
    ctx,
    id="my-workspace-id",
    sql_query="SELECT * FROM customers WHERE region='US' LIMIT 10"
)

if sql_response.status == "success":
    # Process SQL results
    print(f"Column names: {', '.join(sql_response.data.columns)}")
    print(f"Number of rows: {sql_response.data.row_count}")

    # Print each row
    for row in sql_response.data.rows:
        print(row)

    # Access metadata
    print(f"Query execution time: {sql_response.metadata.execution_time_ms} ms")
    print(f"Workspace name: {sql_response.data.workspace_name}")
else:
    print(f"SQL error: {sql_response.message}")

# List virtual workspaces
vw_response = get_virtual_workspaces(ctx)

if vw_response.status == "success":
    workspaces = vw_response.data.workspaces

    if workspaces:
        print(f"Found {len(workspaces)} virtual workspaces:")
        for workspace in workspaces:
            print(f"- {workspace.name} ({workspace.virtual_workspace_id})")
            print(f"  Status: {workspace.state}")
            print(f"  Endpoint: {workspace.endpoint}")
            print(f"  Database: {workspace.database_name}")
    else:
        print("No virtual workspaces found")
```

### Error Handling

Proper error handling is important when working with tool responses:

```python
def handle_tool_response(response):
    """Generic response handler that works with any tool response"""
    if response.status == "success":
        print(f"Operation successful: {response.message}")
        return response.data
    elif response.status == "warning":
        print(f"Warning: {response.message}")
        if hasattr(response, "warning_details"):
            print(f"Warning details: {response.warning_details}")
        return response.data
    else:  # error
        print(f"Error: {response.message}")
        if hasattr(response, "error_code") and response.error_code:
            print(f"Error code: {response.error_code}")
        if hasattr(response, "error_details") and response.error_details:
            print(f"Error details: {response.error_details}")
        return None
```

## Benefits

1. **Consistency**: All tools return responses in the same format
2. **Type Safety**: Response types are checked at compile time
3. **Self-documenting**: The schema describes the response structure
4. **Validation**: Ensures responses match the expected structure
5. **IDE Support**: Better autocomplete and documentation in code editors

## Response Types

Here are some of the response types defined:

- `SqlResponse`: For SQL query execution results
- `OrganizationsResponse`: For listing organizations
- `SetOrganizationResponse`: For setting the active organization
- `RegionsResponse`: For listing regions
- `VirtualWorkspacesResponse`: For listing virtual workspaces
- `WorkspaceGroupsResponse`: For workspace group operations
- `WorkspacesResponse`: For workspace operations

Each response type is a specialization of the `ToolResponse[T]` generic class, where `T` is the specific data model for that tool.
