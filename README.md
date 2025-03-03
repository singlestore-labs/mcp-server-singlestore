# SingleStore MCP Server

A SingleStore MCP server

## Components

### Resources

The server implements a simple note storage system with:
- Custom note:// URI scheme for accessing individual notes
- Each note resource has a name, description and text/plain mimetype

### Prompts

The server provides three prompts:
- get-workspace-details: Get details of a specific workspace
  - Takes "workspace_id" as a required string argument
- get-workspace-group-details: Get details of a specific workspace group
  - Takes "workspace_group_id" as a required string argument
- get-starter-workspace-details: Get details of a specific starter workspace
  - Takes "starter_workspace_id" as a required string argument

### Tools

The server implements twelve tools:
- list-workspace-groups: Lists all workspace groups in SingleStore
  - No arguments required
  - Returns a list of workspace group details including name, creation date, region ID, state, and workspace group ID
- get-workspace-details: Get details of a specific workspace
  - Takes "workspace_id" as a required string argument
  - Returns details of the specified workspace
- terminate-workspace: Terminate a specific workspace
  - Takes "workspace_id" as a required string argument
  - Takes "force" as an optional boolean argument to force termination
- get-workspace-group-details: Get details of a specific workspace group
  - Takes "workspace_group_id" as a required string argument
  - Returns details of the specified workspace group
- terminate-workspace-group: Terminate a specific workspace group
  - Takes "workspace_group_id" as a required string argument
  - Takes "force" as an optional boolean argument to force termination
- list-starter-workspaces: Lists all starter workspaces in SingleStore
  - No arguments required
  - Returns a list of starter workspace details including name and ID
- create-starter-workspace: Create a new starter workspace
  - Takes "name" as a required string argument
  - Returns details of the created starter workspace
- get-starter-workspace-details: Get details of a specific starter workspace
  - Takes "starter_workspace_id" as a required string argument
  - Returns details of the specified starter workspace
- terminate-starter-workspace: Terminate a specific starter workspace
  - Takes "starter_workspace_id" as a required string argument
- workspace_groups_info: Retrieve details about the workspace groups accessible to the user
  - No arguments required
  - Returns details of the workspace groups
- organization_info: Retrieve details about the user's current organization
  - No arguments required
  - Returns details of the organization
- list_of_regions: Retrieve a list of all regions that support workspaces for the user
  - No arguments required
  - Returns a list of regions

## Configuration

The server requires a SingleStore API key to access the SingleStore Management API. You can provide the API key via environment variables.

```bash
export SINGLESTORE_API_KEY="your_api_key_here"
```

## Quickstart

### Install

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
- Token: `--token` or `UV_PUBLISH_TOKEN`
- Or username/password: `--username`/`UV_PUBLISH_USERNAME` and `--password`/`UV_PUBLISH_PASSWORD`

### Debugging

Since MCP servers run over stdio, debugging can be challenging. For the best debugging
experience, we strongly recommend using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector).


You can launch the MCP Inspector via [`npm`](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) with this command:

```bash
npx @modelcontextprotocol/inspector uv --directory /home/prodrigues/Desktop/mcp-server/my-server run my-server
```


Upon launching, the Inspector will display a URL that you can access in your browser to begin debugging.