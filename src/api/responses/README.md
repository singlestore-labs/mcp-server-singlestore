# Response Standardization System

## Overview

The SingleStore MCP Server response standardization system provides a unified, type-safe approach to handling tool responses. It ensures consistency, improves error handling, and enhances observability across all tool functions.

## Key Features

- **🔧 Consistent Structure**: All tools return the same response format
- **⚡ Type Safety**: Pydantic validation prevents response format errors
- **🚨 Automatic Error Handling**: Decorators catch and standardize exceptions
- **🔄 Backward Compatibility**: Legacy responses are automatically converted
- **📊 Enhanced Observability**: Rich metadata and error details for monitoring
- **🛠️ Developer Friendly**: Simple builder patterns and decorators

## Quick Start

### Basic Usage

```python
from src.api.responses import ToolResponseBuilder, ensure_dict_response

@ensure_dict_response
def my_tool(ctx: Context, param: str) -> Dict[str, Any]:
    """Example tool with standardized responses."""

    # Your tool logic
    result = perform_operation(param)

    # Return standardized response
    return ToolResponseBuilder.success(
        message="Operation completed successfully",
        data={"result": result},
        metadata={"execution_time_ms": 150}
    )
```

### Response Structure

All responses follow this standardized format:

```json
{
  "status": "success|error|warning|partial",
  "message": "Human-readable description",
  "data": {
    "tool": "specific",
    "response": "data"
  },
  "metadata": {
    "timestamp": "2024-01-01T12:00:00Z",
    "execution_time_ms": 150
  },
  "error_code": "ERROR_TYPE",
  "error_details": {
    "exception": "Detailed error info"
  }
}
```

## Components

### Core Types

- **`ToolResponse`**: Pydantic model defining the response structure
- **`ResponseStatus`**: Enum for status values (SUCCESS, ERROR, WARNING, PARTIAL)
- **`ToolResponseBuilder`**: Builder class for creating responses

### Decorators

- **`@ensure_dict_response`**: Converts ToolResponse to dict for MCP compatibility
- **`@standardize_response`**: Standardizes responses and handles exceptions

### Utilities

- **`convert_to_dict()`**: Manual conversion from ToolResponse to dict
- **`from_legacy()`**: Converts legacy response formats to standardized format

## Response Types

### Success Response

```python
ToolResponseBuilder.success(
    message="Query executed successfully. 5 rows returned.",
    data={"results": [...], "row_count": 5},
    metadata={"execution_time_ms": 150, "workspace_type": "shared"}
)
```

### Error Response

```python
ToolResponseBuilder.error(
    message="SQL execution failed",
    error_code="SQL_ERROR",
    error_details={"sql_error": "Table not found", "query": "SELECT * FROM ..."}
)
```

### Warning Response

```python
ToolResponseBuilder.warning(
    message="Operation completed with warnings",
    data={"results": [...], "warnings": ["deprecated_field"]},
    metadata={"warning_count": 1}
)
```

### Partial Response

```python
ToolResponseBuilder.partial(
    message="8 of 10 operations completed",
    data={"successful": 8, "failed": 2, "results": [...]},
    metadata={"success_rate": 0.8}
)
```

## Migration Guide

See [Migration Guide](../docs/response-standardization-migration.md) for detailed instructions on converting existing tools.

### Quick Migration Example

#### Before
```python
def list_workspaces(group_id: str):
    workspaces = get_workspaces(group_id)
    return [{"name": w.name, "id": w.id} for w in workspaces]
```

#### After
```python
@ensure_dict_response
def list_workspaces(group_id: str):
    workspaces = get_workspaces(group_id)
    workspace_data = [{"name": w.name, "id": w.id} for w in workspaces]

    return ToolResponseBuilder.success(
        message=f"Retrieved {len(workspaces)} workspaces",
        data={"workspaces": workspace_data, "group_id": group_id},
        metadata={"count": len(workspaces)}
    )
```

## Benefits

### For Developers
- **Reduced Boilerplate**: Decorator handles common patterns
- **Better Debugging**: Detailed error information with stack traces
- **Type Safety**: Compile-time validation of response structure
- **Consistent Patterns**: Same approach across all tools

### For Users
- **Predictable Responses**: All tools use the same format
- **Better Error Messages**: Rich error context and details
- **Enhanced Metadata**: Additional context like execution time
- **Improved Reliability**: Automatic exception handling

### For Operations
- **Better Observability**: Standardized logging and metrics
- **Easier Monitoring**: Consistent response structure
- **Enhanced Debugging**: Detailed error tracking
- **Performance Insights**: Execution time and metadata

## Testing

The system includes comprehensive tests covering:

- Response model validation
- Builder pattern functionality
- Decorator behavior
- Legacy conversion
- Error handling
- Type safety

Run tests with:

```bash
uv run pytest tests/test_responses.py -v
```

## File Structure

```
src/api/responses/
├── __init__.py          # Main exports
├── types.py             # Response models and builders
└── decorators.py        # Response standardization decorators

docs/
└── response-standardization-migration.md  # Detailed migration guide

tests/
└── test_responses.py    # Comprehensive test suite
```

## Current Status

- ✅ **Core System**: Response types, builders, and decorators implemented
- ✅ **Testing**: Comprehensive test suite with 100% coverage
- ✅ **Documentation**: Migration guide and examples
- ✅ **Example Migration**: `check_if_file_exists` tool converted
- 🔄 **In Progress**: Tool-by-tool migration
- ⏳ **Planned**: Full validation and legacy cleanup

## Next Steps

1. **Phase 1**: Migrate high-usage tools (SQL execution, workspace listing)
2. **Phase 2**: Convert error-prone tools with complex operations
3. **Phase 3**: Apply to all remaining tools and new tools
4. **Phase 4**: Remove legacy response patterns and validate

## Examples

### SQL Execution Tool
```python
@ensure_dict_response
def run_sql(ctx: Context, sql_query: str, workspace_id: str) -> Dict[str, Any]:
    try:
        results = execute_query(sql_query, workspace_id)

        return ToolResponseBuilder.success(
            message=f"Query executed successfully. {len(results)} rows returned.",
            data={
                "results": results,
                "row_count": len(results),
                "workspace_id": workspace_id
            },
            metadata={
                "query_length": len(sql_query),
                "execution_time_ms": get_execution_time(),
                "workspace_type": get_workspace_type(workspace_id)
            }
        )
    except SQLError as e:
        return ToolResponseBuilder.error(
            message="SQL execution failed",
            error_code="SQL_ERROR",
            error_details={
                "sql_error": str(e),
                "query": sql_query[:100] + "..." if len(sql_query) > 100 else sql_query
            }
        )
```

### File Operations Tool
```python
@ensure_dict_response
def check_file_exists(file_name: str) -> Dict[str, Any]:
    exists = file_manager.shared_space.exists(file_name)
    message = f"File {file_name} {'exists' if exists else 'does not exist'}"

    return ToolResponseBuilder.success(
        message=message,
        data={"exists": exists, "file_name": file_name},
        metadata={"checked_at": datetime.datetime.now().isoformat()}
    )
```

## Contributing

When adding new tools or modifying existing ones:

1. Use `@ensure_dict_response` decorator
2. Return `ToolResponseBuilder` responses
3. Include meaningful metadata
4. Add appropriate error handling
5. Update tests and documentation

For questions or contributions, see the main [CONTRIBUTING.md](../CONTRIBUTING.md) guide.
