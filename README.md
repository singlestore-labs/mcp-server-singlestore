# SingleStore MCP Server

A SingleStore MCP server

## Components

### Resources

The server implements a simple note storage system with:
- Custom note:// URI scheme for accessing individual notes
- Each note resource has a name, description and text/plain mimetype

### Tools

The server implements the following tools:
- workspace_groups_info: Retrieve details about the workspace groups accessible to the user
  - No arguments required
  - Returns details of the workspace groups
- workspaces_info: Retrieve details about the workspaces in a specific workspace group
  - Arguments: workspaceGroupID (string)
  - Returns details of the workspaces
- organization_info: Retrieve details about the user's current organization
  - No arguments required
  - Returns details of the organization
- list_of_regions: Retrieve a list of all regions that support workspaces for the user
  - No arguments required
  - Returns a list of regions
- execute_sql: Execute SQL operations on a connected workspace
  - Arguments: workspace_group_identifier, workspace_identifier, username, password, database, sql_query
  - Returns the results of the SQL query in a structured format
- list_virtual_workspaces: List all starter workspaces accessible to the user
  - No arguments required
  - Returns details of available starter workspaces
- create_virtual_workspace: Create a new starter workspace with a user
  - Arguments: 
    - name: Name of the starter workspace
    - database_name: Name of the database to create
    - username: Username for accessing the workspace
    - password: Password for the user
    - workspace_group: Object containing name (optional) and cellID (mandatory)
  - Returns details of the created workspace and user
- connect_to_virtual_workspace: Connect to an existing starter workspace
  - Arguments: virtual_workspace_id, username, password
  - Returns connection status and workspace details
- execute_sql_on_virtual_workspace: Execute SQL operations on a virtual workspace
  - Arguments: virtual_workspace_id, username, password, sql_query
  - Returns the results of the SQL query in a structured format including data, row count, columns, and status

## Configuration

The server requires a SingleStore API key to access the SingleStore Management API. You can provide the API key via environment variables.

```bash
export SINGLESTORE_API_KEY="your_api_key_here"
```

## Quickstart

### Install

1. Set up environment variables:
    Create a `config` folder with a `__init__.py` file with the following content:
    ```properties
    singlestore_api_key=your_api_key_here

#### Claude Desktop

On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`
On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

<details>
  <summary>Development/Unpublished Servers Configuration</summary>
  ```
  "mcpServers": {
    "SingleStore MCP Server": {
      "command": "uv",
      "args": [
        "--directory",
        "/home/prodrigues/Desktop/mcp-server/my-server",
        "run",
        "my-server"
      ]
    }
  }
  ```
</details>

<details>
  <summary>Published Servers Configuration</summary>
  ```
  "mcpServers": {
    "SingleStore MCP Server": {
      "command": "uvx",
      "args": [
        "my-server"
      ]
    }
  }
  ```
</details>

## Development

To run the project:
```bash
px @modelcontextprotocol/inspector uv --directory /home/prodrigues/Desktop/mcp-server-singlestore/src/my_server run server.py
```

### Building and Publishing

To prepare the package for distribution:

1. Sync dependencies and update lockfile:
```bash
uv sync
```

2. Build package distributions:
```bash
uv build
```

This will create source and wheel distributions in the `dist/` directory.

3. Publish to PyPI:
```bash
uv publish
```

Note: You'll need to set PyPI credentials via environment variables or command flags:
- Token