# Tools Package

This package contains tools for interacting with the SingleStore API.

## Setup

1. Set up environment variables:
    Create a `config` folder with a `__init__.py` file with the following content:
    ```properties
    api_key=your_api_key_here
    api_base_url="https://api.singlestore.com"
    ```

## Usage

The tools package provides various tools for interacting with the SingleStore API. The tools are defined in the `definitions.py` file and can be executed by name.

### Available Tools

- `workspace_groups_info`: Retrieve details about the workspace groups accessible to the user.
- `organization_info`: Retrieve details about the user's current organization.
- `list_of_regions`: Retrieve a list of all regions that support workspaces for the user.

## License

This project is licensed under the MIT License.