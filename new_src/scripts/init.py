import os
import json
import sys
from pathlib import Path
from typing import Optional, Literal

# Supported client types
ClientType = Literal["claude", "cursor"]

# Client config file paths (platform-dependent)
CLIENT_CONFIG_PATHS = {
    "claude": {
        "darwin": ("~/Library/Application Support/Claude/claude_desktop_config.json"),
        "win32": "%APPDATA%\\Claude\\claude_desktop_config.json",
        "linux": "~/.config/Claude/claude_desktop_config.json",
    },
    "cursor": {
        "darwin": "~/.cursor/mcp.json",
        "win32": "~/.cursor/mcp.json",
        "linux": "~/.cursor/mcp.json",
    },
}

# Client-specific config templates
CLIENT_CONFIG_TEMPLATES = {
    "claude": {
        "mcpServers": {
            "singlestore-mcp-server": {
                "command": "uvx",
                "args": [
                    "singlestore-mcp-server",
                    "start",
                    "--api-key",
                    "{api_key}",
                ],
            }
        }
    },
    "cursor": {
        "mcpServers": {
            "singlestore-mcp-server": {
                "command": "uvx",
                "args": ["singlestore-mcp-server", "start", "--api-key", "{api_key}"],
            }
        }
    },
}


def get_config_path(client: ClientType) -> Optional[Path]:
    """
    Get the platform-specific config path for the client.

    Args:
        client: The LLM client name

    Returns:
        Path to the config file or None if unsupported platform
    """
    platform = sys.platform
    if platform not in CLIENT_CONFIG_PATHS[client]:
        print(f"Unsupported platform: {platform} for client: {client}")
        return None

    # Get the raw path and expand environment variables and user directory
    raw_path = CLIENT_CONFIG_PATHS[client][platform]
    if platform == "win32":
        # Windows-specific environment variable expansion
        for env_var in os.environ:
            placeholder = f"%{env_var}%"
            if placeholder in raw_path:
                raw_path = raw_path.replace(placeholder, os.environ[env_var])
        return Path(raw_path)
    else:
        # Unix-like systems
        return Path(os.path.expanduser(raw_path))


def create_config_directory(config_path: Path) -> bool:
    """
    Create the directory for the config file if it doesn't exist.

    Args:
        config_path: Path to the config file

    Returns:
        True if successful, False otherwise
    """
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating config directory: {e}")
        return False


def update_client_config(client: ClientType, api_key: str) -> bool:
    """
    Update the client configuration file to use the SingleStore MCP server.

    Args:
        client: The LLM client name
        api_key: SingleStore API key

    Returns:
        True if successful, False otherwise
    """
    config_path = get_config_path(client)
    if not config_path:
        return False

    # Create directory if it doesn't exist
    if not create_config_directory(config_path):
        return False

    # Prepare the config data
    template = CLIENT_CONFIG_TEMPLATES[client]

    # Fill in the API key
    config_str = json.dumps(template, indent=2)
    config_str = config_str.replace('"{api_key}"', f'"{api_key}"')
    config_data = json.loads(config_str)

    try:
        # Read existing config if available
        if config_path.exists():
            with open(config_path, "r") as f:
                try:
                    existing_config = json.load(f)
                    # Merge the configs based on client type
                    if client in ["claude", "cursor"]:
                        if "mcpServers" not in existing_config:
                            existing_config["mcpServers"] = {}
                        existing_config["mcpServers"]["singlestore-mcp-server"] = (
                            config_data["mcpServers"]["singlestore-mcp-server"]
                        )

                    config_data = existing_config
                except json.JSONDecodeError:
                    # If the file exists but is invalid JSON, use our template
                    print(
                        f"Warning: Existing config file at {config_path} is not valid JSON. Creating a new file."
                    )

        # Write the updated config
        with open(config_path, "w") as f:
            json.dump(config_data, indent=2, fp=f)

        print(
            f"Successfully configured {client.capitalize()} to use SingleStore MCP server."
        )
        print(f"Config updated at: {config_path}")
        return True

    except Exception as e:
        print(f"Error updating client config: {e}")
        return False


def init_command(
    api_key: str,
    client: str = "claude",
) -> int:
    """
    Initialize the SingleStore MCP server for a specific client.

    Args:
        api_key: SingleStore API key
        client: Name of the LLM client (claude, cursor)

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    client = client.lower()
    valid_clients = list(CLIENT_CONFIG_TEMPLATES.keys())

    if client not in valid_clients:
        print(f"Error: Unsupported client '{client}'")
        print(f"Supported clients: {', '.join(valid_clients)}")
        return 1

    print(f"Initializing SingleStore MCP server for {client.capitalize()}...")
    # Update the client configuration
    if update_client_config(client, api_key):
        print("\nSetup complete! You can now use the MCP server with your LLM client.")
        print("Restart your LLM client to apply the changes.")
        return 0
    else:
        print("\nSetup failed. Please check the error messages above.")
        return 1
