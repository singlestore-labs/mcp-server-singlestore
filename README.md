# SingleStore MCP Server

[![MIT Licence](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/singlestore-labs/mcp-server-singlestore/blob/main/LICENSE) [![PyPI](https://img.shields.io/pypi/v/singlestore-mcp-server)](https://pypi.org/project/singlestore-mcp-server/) [![Downloads](https://static.pepy.tech/badge/singlestore-mcp-server)](https://pepy.tech/project/singlestore-mcp-server)

[Model Context Protocol]((https://modelcontextprotocol.io/introduction)) (MCP) is a standardized protocol designed to manage context between large language models (LLMs) and external systems. This repository provides an installer and an MCP Server for Singlestore, enabling seamless integration.

With MCP, you can use Claude Desktop, Cursor, or any compatible MCP client to interact with SingleStore using natural language, making it easier to perform complex operations effortlessly.

💡 **Pro Tip**: Not sure what the MCP server can do? Just call the `/help` prompt in your chat!

## Requirements

- Python >= v3.11.0
- [uvx](https://docs.astral.sh/uv/guides/tools/) installed on your python environment
- Claude Desktop, Cursor, or another supported LLM client

## Client Setup

### 1. Init Command

The simplest way to set up the MCP server is to use the initialization command:

```bash
uvx singlestore-mcp-server init
```

This command will:

1. Automatically locate the configuration file for your platform
2. Create or update the configuration to include the SingleStore MCP server
3. Configure browser-based OAuth authentication
4. Provide instructions for starting the server

To specify a client (e.g., `claude` or `cursor`), use the `--client` flag:

```bash
uvx singlestore-mcp-server init --client=<client>
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
        "start"
      ]
     }
    }
  }
  ```

   **No API keys, tokens, or environment variables required!** The server automatically handles authentication via browser OAuth when started.

### 4. Using Docker

#### Building the Docker Image

To build the Docker image for the MCP server, run the following command in the project root:

```bash
docker build -t mcp-server-singlestore .
```

#### Running the Docker Container

To run the Docker container, use the following command:

```bash
docker run -d \
  -p 8000:8000 \
  -e MCP_API_KEY="your_api_key_here" \
  -it \
  --name mcp-server \
  mcp-server-singlestore
```

Note: An API key is needed when using Docker because the OAuth flow isn't supported locally for servers running in a Docker container. We're working with the Docker team to enable OAuth for local servers in the future. For better security, we recommend using Docker Desktop to configure the S2 MCP server—see [this blog post](https://www.docker.com/blog/docker-mcp-catalog-secure-way-to-discover-and-run-mcp-servers/) for details on Docker's new MCP Catalog.


2. Restart your client after making changes to the configuration.

## Components

### Tools

The server implements the following tools:

- **get_user_info**: Retrieve details about the current user
  - No arguments required
  - Returns user information and details

- **organization_info**: Retrieve details about the user's current organization
  - No arguments required
  - Returns details of the organization

- **choose_organization**: Choose from available organizations (only available when API key environment variable is not set)
  - No arguments required
  - Returns a list of available organizations to choose from

- **set_organization**: Set the active organization (only available when API key environment variable is not set)
  - Arguments: `organization_id` (string)
  - Sets the specified organization as active

- **workspace_groups_info**: Retrieve details about the workspace groups accessible to the user
  - No arguments required
  - Returns details of the workspace groups

- **workspaces_info**: Retrieve details about the workspaces in a specific workspace group
  - Arguments: `workspace_group_id` (string)
  - Returns details of the workspaces

- **resume_workspace**: Resume a suspended workspace
  - Arguments: `workspace_id` (string)
  - Resumes the specified workspace

- **list_starter_workspaces**: List all starter workspaces accessible to the user
  - No arguments required
  - Returns details of available starter workspaces

- **create_starter_workspace**: Create a new starter workspace
  - Arguments: workspace configuration parameters
  - Returns details of the created starter workspace

- **terminate_starter_workspace**: Terminate an existing starter workspace
  - Arguments: `workspace_id` (string)
  - Terminates the specified starter workspace

- **list_regions**: Retrieve a list of all regions that support workspaces
  - No arguments required
  - Returns a list of available regions

- **list_sharedtier_regions**: Retrieve a list of shared tier regions
  - No arguments required
  - Returns a list of shared tier regions

- **run_sql**: Execute SQL operations on a connected workspace
  - Arguments: `workspace_id`, `database`, `sql_query`, and connection parameters
  - Returns the results of the SQL query in a structured format

- **create_notebook_file**: Create a new notebook file in SingleStore Spaces
  - Arguments: `notebook_name`, `content` (optional)
  - Returns details of the created notebook

- **upload_notebook_file**: Upload a notebook file to SingleStore Spaces
  - Arguments: `file_path`, `notebook_name`
  - Returns details of the uploaded notebook

- **create_job_from_notebook**: Create a scheduled job from a notebook
  - Arguments: job configuration including `notebook_path`, `schedule_mode`, etc.
  - Returns details of the created job

- **get_job**: Retrieve details of an existing job
  - Arguments: `job_id` (string)
  - Returns details of the specified job

- **delete_job**: Delete an existing job
  - Arguments: `job_id` (string)
  - Deletes the specified job

**Note**: Organization management tools (`choose_organization` and `set_organization`) are only available when the API key environment variable is not set, allowing for interactive organization selection during OAuth authentication.

## Development

### Prerequisites

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/) for dependency management

### Setup

1. Clone the repository:

```bash
git clone https://github.com/singlestore-labs/mcp-server-singlestore.git
cd mcp-server-singlestore
```

1. Install dependencies:

```bash
uv sync --dev
```

1. Set up pre-commit hooks (optional but recommended):

```bash
uv run pre-commit install
```

### Development Workflow

```bash
# Quick quality checks (fast feedback)
./scripts/check.sh

# Run tests independently
./scripts/test.sh

# Comprehensive validation (before PRs)
./scripts/check-all.sh

# Create and publish releases
./scripts/release.sh
```

### Running Tests

```bash
# Run test suite with coverage
./scripts/test.sh

# Or use pytest directly
uv run pytest
uv run pytest --cov=src --cov-report=html
```

### Code Quality

We use [Ruff](https://docs.astral.sh/ruff/) for both linting and formatting:

```bash
# Format code
uv run ruff format src/ tests/

# Lint code
uv run ruff check src/ tests/

# Lint and fix issues automatically
uv run ruff check --fix src/ tests/
```

### Release Process

Releases are managed through git tags and automated PyPI publication:

1. **Create release**: `./scripts/release.sh` (interactive tool)
2. **Automatic publication**: Triggered by pushing version tags
3. **No manual PyPI uploads** - fully automated pipeline

See [`scripts/dev-workflow.md`](scripts/dev-workflow.md) for detailed workflow documentation.
