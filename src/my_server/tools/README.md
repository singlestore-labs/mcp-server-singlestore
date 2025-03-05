# Tools Package

This package contains tools for interacting with the SingleStore API.

## Setup

1. Set up environment variables using one of these methods:

    a. Using a .env file: Copy .env.example to .env and fill in your values 

    b. Export variables in shell:
    ```bash
    export SINGLESTORE_API_KEY=your_api_key
    export SINGLESTORE_DB_USERNAME=your_db_username
    export SIGNLESTORE_DB_PASSWORD=your_db_password
    ```

Note: Database username and password are optional and can be provided as input parameters when needed.

## Usage

The tools package provides various tools for interacting with the SingleStore API. The tools are defined in the `definitions.py` file and can be executed by name.

### Available Tools

- `workspace_groups_info`: Retrieve details about the workspace groups accessible to the user.
- `workspaces_info`: Retrieve details about the workspaces in a specific workspace group.
- `organization_info`: Retrieve details about the user's current organization.
- `list_of_regions`: Retrieve a list of all regions that support workspaces for the user.
- `execute_sql`: Execute SQL operations on a connected workspace.
- `list_virtual_workspaces`: List all starter workspaces (virtual workspaces) accessible to the user.
- `create_virtual_workspace`: Create a new starter workspace (virtual workspace) with a specified name and database name.
- `execute_sql_on_virtual_workspace`: Execute SQL operations on a connected virtual workspace (starter workspace).
- `organization_billing_usage`: Retrieves the compute usage and storage usage of an organization.

## License

This project is licensed under the MIT License.
