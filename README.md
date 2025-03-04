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
- Token: `--token` or `UV_PUBLISH_TOKEN`
- Or username/password: `--username`/`UV_PUBLISH_USERNAME` and `--password`/`UV_PUBLISH_PASSWORD`

### Debugging

Since MCP servers run over stdio, debugging can be challenging. For the best debugging
experience, we strongly recommend using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector).

You can launch the MCP Inspector via [`npm`](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) with this command:

```bash
npx @modelcontextprotocol/inspector uv --directory /home/prodrigues/Desktop/mcp-server-singlestore/src/my_server run server.py
```

Upon launching, the Inspector will display a URL that you can access in your browser to begin debugging.