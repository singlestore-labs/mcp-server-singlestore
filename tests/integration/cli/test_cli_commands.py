"""Test that verifies all CLI commands are accessible.
Extracts commands from --help and tests them."""

import subprocess
import pytest


def get_commands():
    """Get all commands by parsing --help output."""
    result = subprocess.run(
        "uvx --from . singlestore-mcp-server --help",
        shell=True,
        capture_output=True,
        text=True,
        check=True,
    )
    # Extract commands from help output (looking for "Commands:" section)
    commands = []
    in_commands = False
    for line in result.stdout.split("\n"):
        if line.strip() == "Commands:":
            in_commands = True
            continue
        if in_commands and line.strip():
            # Extract command name (first word)
            command = line.strip().split()[0]
            commands.append(command)
        elif in_commands and not line.strip():
            # Empty line after commands section
            break
    return commands


@pytest.fixture(scope="session", autouse=True)
def build_package():
    """Build the package before running tests."""
    subprocess.run("uvx --from build pyproject-build", shell=True, check=True)


@pytest.mark.parametrize("command", get_commands())
def test_command_help(command):
    """Test that each command's --help works."""
    result = subprocess.run(
        f"uvx --from . singlestore-mcp-server {command} --help",
        shell=True,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Command '{command} --help' failed:\n{result.stderr}"
    )
