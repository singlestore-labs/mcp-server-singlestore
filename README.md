# SingleStore MCP Server

[![MIT Licence](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/singlestore-labs/mcp-server-singlestore/blob/main/LICENSE) [![PyPI](https://img.shields.io/pypi/v/singlestore-mcp-server)](https://pypi.org/project/singlestore-mcp-server/) [![Downloads](https://static.pepy.tech/badge/singlestore-mcp-server)](https://pepy.tech/project/singlestore-mcp-server) [![Smithery](https://smithery.ai/badge/@singlestore-labs/mcp-server-singlestore)](https://smithery.ai/server/@singlestore-labs/mcp-server-singlestore)

[Model Context Protocol]((https://modelcontextprotocol.io/introduction)) (MCP) is a standardized protocol designed to manage context between large language models (LLMs) and external systems. This repository provides an installer and an MCP Server for Singlestore, enabling seamless integration.

With MCP, you can use Claude Desktop or any compatible MCP client to interact with SingleStore using natural language, making it easier to perform complex operations effortlessly.

## Claude Setup

### Installing via Smithery

To install mcp-server-singlestore for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@singlestore-labs/mcp-server-singlestore):

```bash
npx -y @smithery/cli install @singlestore-labs/mcp-server-singlestore --client claude
```

## Requirements

- Python >= v3.11.0
- [Pipx](https://pipx.pypa.io/stable/) installed on your python environment
- Claude Desktop

## How to use locally

1. Add the following config to your Claude Desktop [config file](https://modelcontextprotocol.io/quickstart/user)
2. Restart Claude Desktop after making changes to the configuration

```json
{
  "mcpServers": {
    "singlestore-mcp-server": {
      "command": "pipx",
        "args": [
          "run",
          "singlestore-mcp-server"
      ],
      "env": {
        "SINGLESTORE_DB_USERNAME": "your-database-username",
        "SINGLESTORE_DB_PASSWORD": "your-database-password",
        "SINGLESTORE_API_KEY": "your-api-key"
      }
    }
  }
}
```

Note:

You can get your API key and DB credentials on SingleStore's [Helios Portal](https://portal.singlestore.com/intention/cloud)

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

## Configuration

The server requires the following environment variables:

```bash
# SingleStore's management API key (required)
SINGLESTORE_API_KEY=your_api_key_here

# Database credentials (optional - can be provided as input parameters)
SINGLESTORE_DB_USERNAME=your_db_username_here
SINGLESTORE_DB_PASSWORD=your_db_password_here
```
