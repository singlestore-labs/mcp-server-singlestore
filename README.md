# SingleStore MCP Server

[![MIT Licence](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/singlestore-labs/mcp-server-singlestore/blob/main/LICENSE) [![PyPI](https://img.shields.io/pypi/v/singlestore-mcp-server)](https://pypi.org/project/singlestore-mcp-server/) [![Downloads](https://static.pepy.tech/badge/singlestore-mcp-server)](https://pepy.tech/project/singlestore-mcp-server)

[Model Context Protocol]((https://modelcontextprotocol.io/introduction)) (MCP) is a standardized protocol designed to manage context between large language models (LLMs) and external systems. This repository provides an installer and an MCP Server for Singlestore, enabling seamless integration.

With MCP, you can use Claude Desktop, Claude Code, Cursor, or any compatible MCP client to interact with SingleStore using natural language, making it easier to perform complex operations effortlessly.

💡 **Pro Tip**: Not sure what the MCP server can do? Just call the `/help` prompt in your chat!

## Requirements

- Python >= v3.10.0
- [uvx](https://docs.astral.sh/uv/guides/tools/) installed on your python environment
- VS Code, Cursor, Windsurf, Claude Desktop, Claude Code, Goose or any other MCP client

## Getting started

## Getting started

First, install the SingleStore MCP server with your client.

**Standard config** works in most of the tools:

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

<details>
<summary>Claude Desktop</summary>

**Automatic setup:**
```bash
uvx singlestore-mcp-server init --client=claude-desktop
```

**Manual setup:**
Follow the MCP install [guide](https://modelcontextprotocol.io/quickstart/user), use the standard config above.

</details>

<details>
<summary>Claude Code</summary>

**Automatic setup:**
```bash
uvx singlestore-mcp-server init --client=claude-code
```
This will automatically run the Claude CLI command for you.

**Manual setup:**
```bash
claude mcp add singlestore-mcp-server uvx singlestore-mcp-server start
```

</details>

<details>
<summary>Cursor</summary>

**Automatic setup:**
```bash
uvx singlestore-mcp-server init --client=cursor
```

**Manual setup:**
Go to `Cursor Settings` -> `MCP` -> `Add new MCP Server`. Name to your liking, use `command` type with the command `uvx singlestore-mcp-server start`. You can also verify config or add command line arguments via clicking `Edit`.

</details>

<details>
<summary>VS Code</summary>

**Automatic setup:**
```bash
uvx singlestore-mcp-server init --client=vscode
```

**Manual setup:**
Follow the MCP install [guide](https://code.visualstudio.com/docs/copilot/chat/mcp-servers#_add-an-mcp-server), use the standard config above. You can also install using the VS Code CLI:

```bash
code --add-mcp '{"name":"singlestore-mcp-server","command":"uvx","args":["singlestore-mcp-server","start"]}'
```

After installation, the SingleStore MCP server will be available for use with your GitHub Copilot agent in VS Code.

</details>

<details>
<summary>Windsurf</summary>

**Automatic setup:**
```bash
uvx singlestore-mcp-server init --client=windsurf
```

**Manual setup:**
Follow Windsurf MCP [documentation](https://docs.windsurf.com/windsurf/cascade/mcp). Use the standard config above.

</details>

<details>
<summary>Gemini CLI</summary>

**Automatic setup:**
```bash
uvx singlestore-mcp-server init --client=gemini
```

**Manual setup:**
Follow the MCP install [guide](https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/mcp-server.md#configure-the-mcp-server-in-settingsjson), use the standard config above.

</details>

<details>
<summary>LM Studio</summary>

**Automatic setup:**
```bash
uvx singlestore-mcp-server init --client=lm-studio
```

**Manual setup:**
Go to `Program` in the right sidebar -> `Install` -> `Edit mcp.json`. Use the standard config above.

</details>

<details>
<summary>Goose</summary>

**Manual setup only:**
Go to `Advanced settings` -> `Extensions` -> `Add custom extension`. Name to your liking, use type `STDIO`, and set the `command` to `uvx singlestore-mcp-server start`. Click "Add Extension".

</details>

<details>
<summary>Qodo Gen</summary>

**Manual setup only:**
Open [Qodo Gen](https://docs.qodo.ai/qodo-documentation/qodo-gen) chat panel in VSCode or IntelliJ → Connect more tools → + Add new MCP → Paste the standard config above.

Click <code>Save</code>.

</details>

### Using Docker

**NOTE:** An API key is required when using Docker because the OAuth flow isn't supported for servers running in Docker containers.

```json
{
  "mcpServers": {
    "singlestore-mcp-server": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm", "--init", "--pull=always",
        "-e", "MCP_API_KEY=your_api_key_here",
        "singlestore/mcp-server-singlestore"
      ]
    }
  }
}
```

You can build the Docker image yourself:

```bash
docker build -t singlestore/mcp-server-singlestore .
```

For better security, we recommend using Docker Desktop to configure the SingleStore MCP server—see [this blog post](https://www.docker.com/blog/docker-mcp-catalog-secure-way-to-discover-and-run-mcp-servers/) for details on Docker's new MCP Catalog.

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
