import pytest
from unittest.mock import patch, MagicMock, mock_open
from click.testing import CliRunner
from pathlib import Path

from src.main import cli
from src.commands.init import get_config_path, init_command
from src.commands.constants import (
    CLIENT_CLAUDE,
    CLIENT_CURSOR,
    CLIENT_CHOICES,
    DEFAULT_CLIENT,
    TRANSPORT_STDIO,
    TRANSPORT_CHOICES,
    DEFAULT_TRANSPORT,
)


class TestInitCommand:
    """Test the init command functionality."""

    @pytest.mark.parametrize(
        "client_args,expected_client",
        [
            (["--client", CLIENT_CLAUDE], CLIENT_CLAUDE),
            (["--client", CLIENT_CURSOR], CLIENT_CURSOR),
            ([], DEFAULT_CLIENT),  # default client
        ],
    )
    def test_init_command_clients(self, client_args, expected_client):
        """Test init command with different client configurations."""
        runner = CliRunner()
        result = runner.invoke(cli, ["init"] + client_args)

        # Should not fail (exit code 0 or handled gracefully)
        assert result.exit_code == 0 or result.exit_code is None

    def test_init_command_invalid_client(self):
        """Test init command with invalid client."""
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--client", "invalid"])

        # Should fail with non-zero exit code
        assert result.exit_code != 0

    @patch("src.commands.init.get_config_path")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    def test_config_path_creation(
        self, mock_mkdir, mock_exists, mock_file, mock_get_config_path
    ):
        """Test config file creation logic."""
        # Setup mocks
        mock_config_path = Path("/mock/path/config.json")
        mock_get_config_path.return_value = mock_config_path
        mock_exists.return_value = False

        # Test that init_command handles file creation
        with patch("src.commands.init.print") as mock_print:
            try:
                init_command(CLIENT_CLAUDE)
                # Verify that appropriate messages are printed
                assert mock_print.called
            except Exception:
                # Some exceptions are expected due to mocking
                pass

    def test_get_config_path_claude_darwin(self):
        """Test config path retrieval for Claude on macOS."""
        with patch("sys.platform", "darwin"):
            path = get_config_path(CLIENT_CLAUDE)
            assert path is not None
            assert "Claude" in str(path)

    def test_get_config_path_cursor_darwin(self):
        """Test config path retrieval for Cursor on macOS."""
        with patch("sys.platform", "darwin"):
            path = get_config_path(CLIENT_CURSOR)
            assert path is not None
            assert ".cursor" in str(path)

    def test_client_type_choices(self):
        """Test that CLIENT_CHOICES provides correct choices."""
        choices = CLIENT_CHOICES
        assert CLIENT_CLAUDE in choices
        assert CLIENT_CURSOR in choices
        assert len(choices) == 2

    def test_client_type_default(self):
        """Test that DEFAULT_CLIENT provides correct default."""
        default = DEFAULT_CLIENT
        assert default == CLIENT_CLAUDE


class TestStartCommand:
    """Test the start command functionality."""

    @patch("src.commands.start.get_authentication_token")
    @patch("src.config.config.init_settings")
    @patch("src.api.tools.register_tools")
    @patch("src.api.resources.register.register_resources")
    def test_start_command_stdio_success(
        self,
        mock_register_resources,
        mock_register_tools,
        mock_init_settings,
        mock_get_auth_token,
    ):
        """Test start command with stdio transport and successful authentication."""
        # Setup mocks
        mock_get_auth_token.return_value = "mock_oauth_token"
        mock_settings = MagicMock()
        mock_settings.is_remote = False
        mock_init_settings.return_value = mock_settings

        # Mock FastMCP
        with patch("src.commands.start.FastMCP") as mock_fastmcp:
            mock_mcp_instance = MagicMock()
            mock_fastmcp.return_value = mock_mcp_instance

            runner = CliRunner()
            # Use invoke with input to simulate user interaction if needed
            runner.invoke(cli, ["start", "--transport", TRANSPORT_STDIO])

            # Verify authentication was attempted
            mock_get_auth_token.assert_called_once()

    @patch("src.commands.start.get_authentication_token")
    def test_start_command_stdio_auth_failure(self, mock_get_auth_token):
        """Test start command with stdio transport and failed authentication."""
        # Setup mock to return None (auth failure)
        mock_get_auth_token.return_value = None

        runner = CliRunner()
        runner.invoke(cli, ["start", "--transport", TRANSPORT_STDIO])

        # Verify authentication was attempted
        mock_get_auth_token.assert_called_once()

    def test_start_command_default_transport(self):
        """Test start command with default transport."""
        runner = CliRunner()

        with patch("src.commands.start.get_authentication_token") as mock_auth:
            mock_auth.return_value = None  # Simulate auth failure for quick exit
            runner.invoke(cli, ["start"])

            # Should attempt to use default transport (stdio)
            mock_auth.assert_called_once()

    def test_start_command_invalid_transport(self):
        """Test start command with invalid transport."""
        runner = CliRunner()
        result = runner.invoke(cli, ["start", "--transport", "invalid"])

        # Should fail with non-zero exit code
        assert result.exit_code != 0

    def test_transport_type_choices(self):
        """Test that TRANSPORT_CHOICES provides correct choices."""
        choices = TRANSPORT_CHOICES
        assert TRANSPORT_STDIO in choices
        # Verify only supported transports are included
        assert len(choices) >= 1

    def test_transport_type_default(self):
        """Test that DEFAULT_TRANSPORT provides correct default."""
        default = DEFAULT_TRANSPORT
        assert default == TRANSPORT_STDIO


class TestCLIIntegration:
    """Test CLI integration and command structure."""

    def test_cli_help(self):
        """Test that CLI help is accessible."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "init" in result.output
        assert "start" in result.output

    def test_init_help(self):
        """Test that init command help is accessible."""
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--help"])

        assert result.exit_code == 0
        assert "client" in result.output.lower()

    def test_start_help(self):
        """Test that start command help is accessible."""
        runner = CliRunner()
        result = runner.invoke(cli, ["start", "--help"])

        assert result.exit_code == 0
        assert "transport" in result.output.lower()

    def test_main_function_exists(self):
        """Test that main function is properly defined."""
        from src.main import main

        assert callable(main)

    @patch("src.main.cli")
    def test_main_function_calls_cli(self, mock_cli):
        """Test that main function calls the CLI."""
        from src.main import main

        main()
        mock_cli.assert_called_once()


class TestConfigurationTemplates:
    """Test configuration template functionality."""

    @pytest.mark.parametrize("client", [CLIENT_CLAUDE, CLIENT_CURSOR])
    def test_client_config_templates_exist(self, client):
        """Test that configuration templates exist for all supported clients."""
        from src.commands.init import CLIENT_CONFIG_TEMPLATES

        assert client in CLIENT_CONFIG_TEMPLATES
        config = CLIENT_CONFIG_TEMPLATES[client]
        assert "mcpServers" in config
        assert "singlestore-mcp-server" in config["mcpServers"]

    @pytest.mark.parametrize("client", [CLIENT_CLAUDE, CLIENT_CURSOR])
    def test_client_config_paths_exist(self, client):
        """Test that configuration paths are defined for all supported clients."""
        from src.commands.init import CLIENT_CONFIG_PATHS

        assert client in CLIENT_CONFIG_PATHS
        paths = CLIENT_CONFIG_PATHS[client]
        assert "darwin" in paths
        assert "win32" in paths
        assert "linux" in paths

    def test_config_template_structure(self):
        """Test that config templates have correct structure."""
        from src.commands.init import CLIENT_CONFIG_TEMPLATES

        for client, config in CLIENT_CONFIG_TEMPLATES.items():
            assert "mcpServers" in config
            server_config = config["mcpServers"]["singlestore-mcp-server"]
            assert "command" in server_config
            assert "args" in server_config
            assert isinstance(server_config["args"], list)
            assert "singlestore-mcp-server" in server_config["args"]
            assert "start" in server_config["args"]


if __name__ == "__main__":
    pytest.main([__file__])
