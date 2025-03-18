# SingleStore MCP Server

[![smithery badge](https://smithery.ai/badge/@singlestore-labs/mcp-server-singlestore)](https://smithery.ai/server/@singlestore-labs/mcp-server-singlestore)

Model Context Protocol (MCP) is a standardized protocol designed to manage context between large language models (LLMs) and external systems. This repository provides an installer and an MCP Server for Singlestore, enabling seamless integration.

With MCP, you can use Claude Desktop or any compatible MCP client to interact with SingleStore using natural language, making it easier to perform complex operations effortlessly.

## Installation

### Installing via Smithery

To install mcp-server-singlestore for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@singlestore-labs/mcp-server-singlestore):

```bash
npx -y @smithery/cli install @singlestore-labs/mcp-server-singlestore --client claude
```

### Clone the Repository

To clone the repository and set up the server locally:

```bash
git clone https://github.com/singlestore-labs/mcp-server-singlestore.git
cd singlestore-mcp-server
npm install
```

### Install via pip

Alternatively, you can install the package using pip:

```bash
pip install singlestore-mcp-server
```
Use command ```singlestore-mcp-client` to run the server with the mcp clients or mcp inspector.

## Components

### Resources

The server implements a simple note storage system with:
- Custom note:// URI scheme for accessing individual notes
- Each note resource has a name, description, and text/plain mimetype

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
- **connect_to_virtual_workspace**: Connect to an existing starter workspace
  - Arguments: `virtual_workspace_id`, `username`, `password`
  - Returns connection status and workspace details
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
    - `max_duration_minutes`: Maximum allowed runtime (optional)
    - `create_snapshot`: Whether to create notebook snapshots (optional)
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
SIGNLESTORE_DB_PASSWORD=your_db_password_here
```

### Configuration Methods

1. Using a .env file:
  - Copy `.env.example` to `.env`
  - Fill in your values

2. Export variables in shell:
  ```bash
  export SINGLESTORE_API_KEY=your_api_key
  export SINGLESTORE_DB_USERNAME=your_db_username #optional
  export SIGNLESTORE_DB_PASSWORD=your_db_password #optional
  ```

**Note:** Database username and password are optional and can be provided as input parameters when needed.

## Quickstart

### Claude Desktop Configuration

Configure the SingleStore MCP Server in Claude Desktop's configuration file:

**MacOS**:
```bash
~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Windows**:
```bash
%APPDATA%/Claude/claude_desktop_config.json
```

<details>
  <summary>Development Configuration</summary>
  
```json
{
  "mcpServers": {
    "SingleStore MCP Server": {
      "command": "uv",
      "args": [
        "--directory",
        "{path_to_server}/mcp-server-singlestore/server",
        "run",
        "server"
      ]
    }
  }
}
```
</details>

<details>
  <summary>Production Configuration</summary>
  
```json
{
  "mcpServers": {
    "SingleStore MCP Server": {
      "command": "uvx",
      "args": [
        "server"
      ]
    }
  }
}
```
</details>

## Development

### Running Locally with MCP Inspector

Start the development server using the MCP inspector:

```bash
npx @modelcontextprotocol/inspector uv --directory ./src/server run server.py
```

### Running With Claude Desktop App

To connect the SingleStore MCP Server with Claude Desktop:

1. Install and launch Claude Desktop
2. Configure the MCP server in Claude Desktop's config file (see Configuration section)
3. Add your SingleStore environment variables either:
    - In the `.env` file, or
    - Directly in Claude Desktop's MCP server configuration
4. Restart Claude Desktop
5. In the Claude interface:
    - Click the MCP server dropdown
    - Select "SingleStore MCP Server"
6. You should now be able to try a simple command such as `List all my workspace groups`

**Troubleshooting**:
- Ensure all environment variables are set correctly
- Check Claude Desktop logs if connection fails
- Make sure you have valid SingleStore API credentials.

### Building and Publishing

1. Update dependencies:
```bash
uv sync
```

2. Create distribution packages:
```bash
uv build
```
This generates source and wheel distributions in `dist/`.

3. Publish to PyPI:
```bash
uv publish
```

**Note**: Set your PyPI token via environment variable:
```bash
export PYPI_TOKEN=your_token_here
```
