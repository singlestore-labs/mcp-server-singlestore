import os
import json
import sys
from pathlib import Path
from typing import Optional

from ..logger import get_logger
from .constants import CLIENT_CLAUDE, CLIENT_CURSOR, CLIENT_CHOICES

# Get logger for this module
logger = get_logger()

# Client config file paths (platform-dependent)
CLIENT_CONFIG_PATHS = {
    CLIENT_CLAUDE: {
        "darwin": ("~/Library/Application Support/Claude/claude_desktop_config.json"),
        "win32": "%APPDATA%\\Claude\\claude_desktop_config.json",
        "linux": "~/.config/Claude/claude_desktop_config.json",
    },
    CLIENT_CURSOR: {
        "darwin": "~/.cursor/mcp.json",
        "win32": "~/.cursor/mcp.json",
        "linux": "~/.cursor/mcp.json",
    },
}

# Client-specific config templates
CLIENT_CONFIG_TEMPLATES = {
    CLIENT_CLAUDE: {
        "mcpServers": {
            "singlestore-mcp-server": {
                "command": "uvx",
                "args": [
                    "singlestore-mcp-server",
                    "start",
                ],
            }
        }
    },
    CLIENT_CURSOR: {
        "mcpServers": {
            "singlestore-mcp-server": {
                "command": "uvx",
                "args": ["singlestore-mcp-server", "start"],
            }
        }
    },
}


def get_config_path(client: str) -> Optional[Path]:
    """
    Get the platform-specific config path for the client.

    Args:
        client: The LLM client name

    Returns:
        Path to the config file or None if unsupported platform
    """
    platform = sys.platform
    if platform not in CLIENT_CONFIG_PATHS[client]:
        logger.error(f"Unsupported platform: {platform} for client: {client}")
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
        logger.error(f"Error creating config directory: {e}")
        return False


def update_client_config(client: str) -> tuple[bool, Optional[dict]]:
    """
    Update the client configuration file to use the SingleStore MCP server with JWT authentication.

    Args:
        client: The LLM client name

    Returns:
        Tuple of (success: bool, config_data: Optional[dict])
    """
    config_path = get_config_path(client)
    if not config_path:
        return False, None

    # Create directory if it doesn't exist
    if not create_config_directory(config_path):
        return False, None

    # Prepare the config data
    template = CLIENT_CONFIG_TEMPLATES[client]
    config_data = template

    try:
        # Read existing config if available
        if config_path.exists():
            with open(config_path, "r") as f:
                try:
                    existing_config = json.load(f)
                    # Merge the configs based on client type
                    if client in [CLIENT_CLAUDE, CLIENT_CURSOR]:
                        if "mcpServers" not in existing_config:
                            existing_config["mcpServers"] = {}
                        existing_config["mcpServers"]["singlestore-mcp-server"] = (
                            config_data["mcpServers"]["singlestore-mcp-server"]
                        )

                    config_data = existing_config
                except json.JSONDecodeError:
                    # If the file exists but is invalid JSON, use our template
                    logger.warning(
                        f"Existing config file at {config_path} is not valid JSON. Creating a new file."
                    )

        # Write the updated config
        with open(config_path, "w") as f:
            json.dump(config_data, indent=2, fp=f)

        logger.info(
            f"Successfully configured {client.capitalize()} to use SingleStore MCP server."
        )
        logger.info(f"Config updated at: {config_path}")
        logger.info(
            "The server will handle authentication automatically via browser OAuth."
        )
        return True, config_data

    except Exception as e:
        logger.error(f"Error updating client config: {e}")
        return False, None


def init_command(client: str) -> int:
    """
    Initialize the SingleStore MCP server for a specific client with JWT authentication.

    Args:
        client: Name of the LLM client (claude, cursor)

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    client = client.lower()
    valid_clients = CLIENT_CHOICES

    if client not in valid_clients:
        logger.error(f"Unsupported client '{client}'")
        logger.error(f"Supported clients: {', '.join(valid_clients)}")
        return 1

    logger.info(f"Initializing SingleStore MCP server for {client.capitalize()}...")
    # Update the client configuration
    success, config_data = update_client_config(client)
    if success and config_data:
        logger.info(
            "\nSetup complete! You can now use the MCP server with your LLM client."
        )
        logger.info(
            "The server will handle authentication automatically via browser OAuth."
        )

        # Show the generated config
        logger.info("\nGenerated configuration:")
        mcp_server_config = config_data.get("mcpServers", {}).get(
            "singlestore-mcp-server", {}
        )
        config_display = {
            "mcpServers": {"...": "...", "singlestore-mcp-server": mcp_server_config}
        }
        logger.info(json.dumps(config_display, indent=4))

        logger.info("Restart your LLM client to apply the changes.")
        return 0
    else:
        logger.error("\nSetup failed. Please check the error messages above.")
        return 1
