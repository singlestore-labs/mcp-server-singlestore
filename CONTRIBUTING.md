# Contributing to SingleStore MCP Server

Thank you for your interest in contributing to the SingleStore MCP Server! This guide will help you set up your development environment and contribute effectively to the project.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Debugging](#debugging)
- [Environment Variables](#environment-variables)
- [Contributing Guidelines](#contributing-guidelines)
- [Release Process](#release-process)

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.10+** (recommended: Python 3.11)
- **[uv](https://docs.astral.sh/uv/)** - Modern Python package manager
- **Git** - Version control
- **SingleStore account** - For testing database connectivity

### Installing uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Alternative: using pip
pip install uv
```

## Development Setup

### 1. Fork and Clone the Repository

```bash
# Fork the repository on GitHub, then clone your fork
git clone git@github.com:singlestore-labs/mcp-server-singlestore.git
cd mcp-server-singlestore
```

### 2. Set Up Development Environment

```bash
# Create and activate virtual environment with dependencies
uv sync --dev

# Verify installation
uv run python --version
uv run pytest --version
```

### 3. Install the Package in Development Mode

```bash
# Install the package in editable mode
uv pip install -e .

# Verify the CLI works
uv run singlestore-mcp-server --help
```

## Development Workflow

### 1. Create a Feature Branch

```bash
# Fetch latest changes from upstream
git fetch upstream
git checkout main
git merge upstream/main

# Create a new feature branch
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Follow the existing code structure and patterns
- Add tests for new functionality
- Update documentation when necessary
- Use the centralized logger from `src.logger`

### 3. Test Your Changes

```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_server.py

# Run tests matching a pattern
uv run pytest -k "test_init"
```

### 4. Code Quality Checks

```bash
# Format code with Black
uv run black src/ tests/

# Check formatting
uv run black --check src/ tests/

# Lint with Flake8
uv run flake8 src/ --ignore=E501,W503

# Type checking with Pyright
uv run pyright src/

# Run all quality checks
uv run black --check src/ tests/ && uv run flake8 src/ --ignore=E501,W503 && uv run pyright src/
```

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test class
uv run pytest tests/test_server.py::TestInitCommand

# Run specific test method
uv run pytest tests/test_server.py::TestInitCommand::test_init_with_valid_client

# Run tests and generate coverage report
uv run pytest --cov=src --cov-report=term-missing
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files with `test_*.py` pattern
- Use descriptive test names that explain what is being tested
- Mock external dependencies (databases, API calls, file systems)
- Test both success and error cases

Example test structure:

```python
import pytest
from unittest.mock import patch, MagicMock

def test_feature_success():
    """Test that feature works correctly under normal conditions."""
    # Arrange
    # Act
    # Assert

def test_feature_error_handling():
    """Test that feature handles errors gracefully."""
    # Arrange
    # Act
    # Assert
```

## Code Quality

### Code Formatting

We use **Black** for code formatting:

```bash
# Format all files
uv run black src/ tests/

# Check if files need formatting
uv run black --check src/ tests/
```

### Linting

We use **Flake8** for linting:

```bash
# Lint source code
uv run flake8 src/ --ignore=E501,W503

# Lint tests
uv run flake8 tests/ --ignore=E501,W503
```

### Type Checking

We use **Pyright** for type checking:

```bash
# Type check source code
uv run pyright src/
```

### Pre-commit Checks

Before committing, always run:

```bash
# Format, lint, type check, and test
uv run black src/ tests/
uv run flake8 src/ --ignore=E501,W503
uv run pyright src/
uv run pytest
```

## Debugging

### Local Development

To test the MCP server locally:

```bash
# Set up environment variables (optional)
export LOG_LEVEL=DEBUG

# Run the server in stdio mode
uv run singlestore-mcp-server start

# Test authentication flow
uv run python -c "
from src.auth.browser_auth import get_authentication_token
token = get_authentication_token()
print('Token obtained:', bool(token))
"
```

### Using the CLI

```bash
# Initialize for Claude Desktop
uv run singlestore-mcp-server init --client claude

# Initialize for Cursor
uv run singlestore-mcp-server init --client cursor

# Start the server
uv run singlestore-mcp-server start --transport stdio
```

### Logging

The project uses centralized logging. Control verbosity with:

```bash
# Default (INFO level)
uv run singlestore-mcp-server start

# Debug mode - detailed output
LOG_LEVEL=DEBUG uv run singlestore-mcp-server start

# Quiet mode - warnings and errors only  
LOG_LEVEL=WARNING uv run singlestore-mcp-server start

# Errors only
LOG_LEVEL=ERROR uv run singlestore-mcp-server start
```

## Environment Variables

The following environment variables can be used for development:

```bash
# Logging level (DEBUG, INFO, WARNING, ERROR)
export LOG_LEVEL=DEBUG

# Custom OAuth settings (for testing)
export OAUTH_HOST=https://authsvc.singlestore.com
export CLIENT_ID=your-client-id

# Development mode flags
export DEVELOPMENT=true
```

## Contributing Guidelines

### Code Style

- Follow PEP 8 style guidelines
- Use Black for code formatting
- Use descriptive variable and function names
- Add type hints to function signatures
- Write docstrings for public functions and classes

### Constants and Configuration

- Add new constants to `src/commands/constants.py`
- Use the centralized logger from `src.logger`
- Update type definitions when adding new constants
- **Important**: When adding new client types, update both the constant lists AND the type definitions in the same file

Example:

```python
# In constants.py
NEW_FEATURE_OPTION = "new_option"
FEATURE_CHOICES = [NEW_FEATURE_OPTION, "other_option"]
FeatureType = Literal["new_option", "other_option"]

# In your module
from .constants import NEW_FEATURE_OPTION, FeatureType
from ..logger import get_logger

logger = get_logger()
```

### Commit Messages

Use clear, descriptive commit messages:

```bash
# Good examples
git commit -m "feat: add support for new authentication method"
git commit -m "fix: handle timeout errors in OAuth flow"
git commit -m "docs: update installation instructions"
git commit -m "test: add integration tests for database connection"

# Use prefixes: feat, fix, docs, test, refactor, chore
```

### Pull Request Process

1. **Update your branch** with the latest upstream changes
2. **Test thoroughly** - ensure all tests pass
3. **Update documentation** if needed
4. **Create a clear PR description** explaining:
   - What changes were made
   - Why they were made
   - How to test them
5. **Request review** from maintainers

### Pull Request Template

```markdown
## Description
Brief description of changes made.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added tests for new functionality
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
```

## Release Process

> **Note**: This section is for maintainers

### Version Bumping

1. Update version in `src/version.py`
2. Update CHANGELOG.md with new version details
3. Create a pull request with version changes
4. After merge, create a git tag:

```bash
git tag v1.2.3
git push upstream v1.2.3
```

### Automated Publishing

The project uses GitHub Actions for automated publishing:

- **CI Pipeline**: Runs on every PR and push to main
- **PyPI Publishing**: Triggered by version tags
- **Version Validation**: Ensures version consistency

## Getting Help

- **Issues**: Report bugs and request features on [GitHub Issues](https://github.com/singlestore-labs/mcp-server-singlestore/issues)
- **Discussions**: Join conversations in [GitHub Discussions](https://github.com/singlestore-labs/mcp-server-singlestore/discussions)
- **Documentation**: Check the [README.md](README.md) for usage instructions

## Development Tips

1. **Use descriptive branch names**: `feature/add-ssl-support`, `fix/auth-timeout-bug`
2. **Test edge cases**: Test with invalid inputs, network failures, etc.
3. **Mock external dependencies**: Use `unittest.mock` for database connections, API calls
4. **Keep changes focused**: One feature or fix per pull request
5. **Update tests**: Add or modify tests for any code changes
6. **Check CI status**: Ensure all GitHub Actions pass before requesting review

Thank you for contributing to SingleStore MCP Server! 🚀
