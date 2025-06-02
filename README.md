# SingleStore MCP Server

[![MIT Licence](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/singlestore-labs/mcp-server-singlestore/blob/main/LICENSE) [![PyPI](https://img.shields.io/pypi/v/singlestore-mcp-server)](https://pypi.org/project/singlestore-mcp-server/) [![Downloads](https://static.pepy.tech/badge/singlestore-mcp-server)](https://pepy.tech/project/singlestore-mcp-server) [![Smithery](https://smithery.ai/badge/@singlestore-labs/mcp-server-singlestore)](https://smithery.ai/server/@singlestore-labs/mcp-server-singlestore)

[Model Context Protocol]((https://modelcontextprotocol.io/introduction)) (MCP) is a standardized protocol designed to manage context between large language models (LLMs) and external systems. This repository provides an installer and an MCP Server for Singlestore, enabling seamless integration.

With MCP, you can use Claude Desktop, Cursor, or any compatible MCP client to interact with SingleStore using natural language, making it easier to perform complex operations effortlessly.

## Requirements

- Python >= v3.11.0
- [uvx](https://docs.astral.sh/uv/guides/tools/) installed on your python environment
- Claude Desktop, Cursor, or another supported LLM client

## Client Setup

### 1. Init Command

The simplest way to set up the MCP server is to use the initialization command:

```bash
uvx singlestore-mcp-server init --api-key <SINGLESTORE_API_KEY>
```

This command will:

1. Authenticate the user
2. Automatically locate the configuration file for your platform
3. Create or update the configuration to include the SingleStore MCP server
4. Provide instructions for starting the server

To specify a client (e.g., `claude` or `cursor`), use the `--client` flag:

```bash
uvx singlestore-mcp-server init --api-key <SINGLESTORE_API_KEY> --client=<client>
```

### 2. Installing via Smithery

To install `mcp-server-singlestore` automatically via [Smithery](https://smithery.ai/server/@singlestore-labs/mcp-server-singlestore):

```bash
npx -y @smithery/cli install @singlestore-labs/mcp-server-singlestore --client=<client>
```

Replace `<client>` with `claude` or `cursor` as needed.

### 3. Manual Configuration

#### Claude Desktop and Cursor

1. Add the following configuration to your client configuration file. Check the client's configuration file here:

- [Claude Desktop](https://modelcontextprotocol.io/quickstart/user)
- [Cursor](https://docs.cursor.com/context/model-context-protocol#configuration-locations)

  ```json
  {
    "mcpServers": {
     "singlestore-mcp-server": {
      "command": "uvx",
      "args": [
        "singlestore-mcp-server",
        "start",
        "--api-key",
        "<SINGLESTORE_API_KEY>"
      ]
     }
    }
  }
  ```

2. Restart your client after making changes to the configuration.

## Components

### Tools

The server implements the following tools:

- **workspace_groups_info**: Retrieve details about the workspace groups accessible to the user
  - No arguments required
  - Returns details of the workspace groups
- **workspaces_info**: Retrieve details about the workspaces in a specific workspace group
  - Arguments: `workspaceGroupID` (string)
  - Returns details of the workspaces
- **organization_info**: Retrieve details about the user's current organization
  - No arguments required
  - Returns details of the organization
- **list_of_regions**: Retrieve a list of all regions that support workspaces for the user
  - No arguments required
  - Returns a list of regions
- **execute_sql**: Execute SQL operations on a connected workspace
  - Arguments: `workspace_group_identifier`, `workspace_identifier`, `username`, `password`, `database`, `sql_query`
  - Returns the results of the SQL query in a structured format
- **list_virtual_workspaces**: List all starter workspaces accessible to the user
  - No arguments required
  - Returns details of available starter workspaces
- **create_virtual_workspace**: Create a new starter workspace with a user
  - Arguments:
    - `name`: Name of the starter workspace
    - `database_name`: Name of the database to create
    - `username`: Username for accessing the workspace
    - `password`: Password for the user
    - `workspace_group`: Object containing `name` (optional) and `cellID` (mandatory)
  - Returns details of the created workspace and user
- **execute_sql_on_virtual_workspace**: Execute SQL operations on a virtual workspace
  - Arguments: `virtual_workspace_id`, `username`, `password`, `sql_query`
  - Returns the results of the SQL query in a structured format including data, row count, columns, and status
- **list_notebook_samples**: List all notebook samples available in SingleStore Spaces
  - No arguments required
  - Returns details of available notebook samples
- **create_notebook**: Create a new notebook in the user's personal space
  - Arguments: `notebook_name`, `content` (optional)
  - Returns details of the created notebook
- **list_personal_files**: List all files in the user's personal space
  - No arguments required
  - Returns details of all files in the user's personal space
- **create_scheduled_job**: Create a new scheduled job to run a notebook
  - Arguments:
    - `name`: Name for the job
    - `notebook_path`: Path to the notebook to execute
    - `schedule_mode`: Once or Recurring
    - `execution_interval_minutes`: Minutes between executions (optional)
    - `start_at`: When to start the job (optional)
    - `description`: Description of the job (optional)
    - `create_snapshot`: Whether to create notebook snapshots (optional)
    - `runtime_name`: Name of the runtime environment
    - `parameters`: Parameters for the job (optional)
    - `target_config`: Target configuration for the job (optional)
  - Returns details of the created job
- **get_job_details**: Get details about a specific job
  - Arguments: `job_id`
  - Returns detailed information about the specified job
- **list_job_executions**: List execution history for a specific job
  - Arguments: `job_id`, `start` (optional), `end` (optional)
  - Returns execution history for the specified job

## Dockerization

### Building the Docker Image

To build the Docker image for the MCP server, run the following command in the project root:

```bash
docker build -t mcp-server-singlestore .
```

### Running the Docker Container

To run the Docker container, use the following command:

```bash
docker run -d \
  -p 8000:8000 \
  --name mcp-server \
  mcp-server-singlestore
```
