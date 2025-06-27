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

### 4. Set Up Pre-commit Hooks (Recommended)

```bash
# Install pre-commit hooks
uv run pre-commit install

# Test that pre-commit works
uv run pre-commit run --all-files
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
# Format and lint with Ruff
uv run ruff format src/ tests/
uv run ruff check src/ tests/

# Fix linting issues automatically
uv run ruff check --fix src/ tests/

# Type checking with Pyright
uv run pyright src/

# Run all quality checks
uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run pyright src/
```

### 5. Pre-commit Hooks (Recommended)

Set up pre-commit hooks to automatically run code quality checks:

```bash
# Install pre-commit hooks
uv run pre-commit install

# Run pre-commit on all files
uv run pre-commit run --all-files

# Run pre-commit on staged files
uv run pre-commit run
```

### 6. Quick Quality Checks

Use the provided scripts for different scenarios:

```bash
# Run only code quality checks (fast - good for pre-commit)
./scripts/check.sh

# Run only tests
./scripts/test.sh

# Run everything (comprehensive - good for pre-PR)
./scripts/check-all.sh
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

### Code Formatting and Linting

We use **Ruff** for both code formatting and linting. Ruff is a fast, modern Python linter and formatter that replaces Black and Flake8:

```bash
# Format all files
uv run ruff format src/ tests/

# Check if files need formatting
uv run ruff format --check src/ tests/

# Lint source code
uv run ruff check src/ tests/

# Lint and fix issues automatically
uv run ruff check --fix src/ tests/
```

### Type Checking

We use **Pyright** for type checking:

```bash
# Type check source code
uv run pyright src/

# Run Pyright via pre-commit (manual stage)
uv run pre-commit run --hook-stage manual pyright
```

### Pre-commit Hooks

We use pre-commit hooks to automatically run code quality checks on every commit:

```bash
# Install pre-commit hooks (one-time setup)
uv run pre-commit install

# Run all pre-commit hooks manually
uv run pre-commit run --all-files

# Run pre-commit on staged files only
uv run pre-commit run
```

**What runs automatically on commit:**

- Trailing whitespace removal
- End-of-file fixing
- YAML validation
- Large file detection
- Merge conflict detection
- Ruff linting (with auto-fix)
- Ruff formatting

**What runs manually/in CI:**

- Full test suite (use `./scripts/test.sh` or CI)
- Type checking with Pyright (use `uv run pyright src/`)

**Note:** Tests are kept separate from pre-commit hooks to keep commits fast. Run tests manually or let CI handle them.

### Pre-commit Checks

We recommend using pre-commit hooks, but if you need to run checks manually before committing:

```bash
# Run only quality checks (fast - what pre-commit does)
./scripts/check.sh

# Or run individual commands
uv run ruff format src/ tests/
uv run ruff check --fix src/ tests/
uv run pre-commit run --all-files

# Run tests separately when needed
./scripts/test.sh
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
- Use Ruff for code formatting and linting (replaces Black and Flake8)
- Use descriptive variable and function names
- Add type hints to function signatures
- Write docstrings for public functions and classes
- Set up pre-commit hooks for automatic code quality checks

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

### For Regular Development (PR-based Workflow)

When your feature/fix is ready and you want it to trigger a release:

```bash
# 1. On your feature branch
./scripts/mark-release.sh

# Choose release type:
# - Patch: Bug fixes, documentation, CI improvements
# - Minor: New features, backwards-compatible changes
# - Major: Breaking changes, API modifications

# 2. Push and create PR
git push origin your-branch-name

# 3. When PR is merged to main:
# → Automatic version bump
# → Automatic PyPI publication
# → Automatic GitHub release
```

### For Emergency Releases (Direct to main)

For hotfixes or emergency releases that can't wait for PR review:

```bash
git checkout main
git pull origin main
./scripts/release.sh  # Interactive release
git push origin main --tags
```

### Release Types Guide

- **🔧 Patch (X.Y.Z+1)**: Bug fixes, docs, tests, CI changes
- **✨ Minor (X.Y+1.0)**: New tools, features, backwards-compatible changes
- **💥 Major (X+1.0.0)**: Breaking changes, removed features, API changes

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
2. **Set up pre-commit hooks**: Run `uv run pre-commit install` after cloning
3. **Fast pre-commit checks**: Use `./scripts/check.sh` for quick quality validation
4. **Separate test runs**: Use `./scripts/test.sh` to run tests independently
5. **Comprehensive validation**: Use `./scripts/check-all.sh` before creating PRs
6. **Smart releases**: Use `./scripts/release.sh` for controlled PyPI publication
7. **Test edge cases**: Test with invalid inputs, network failures, etc.
8. **Mock external dependencies**: Use `unittest.mock` for database connections, API calls
9. **Keep changes focused**: One feature or fix per pull request
10. **Update tests**: Add or modify tests for any code changes
11. **Check CI status**: Ensure all GitHub Actions pass before requesting review

## Release Management

This project uses **tag-based publishing** for smart release control:

- ✅ **Fast development**: Commits to main don't trigger publications
- ✅ **Controlled releases**: Only publish when you create version tags
- ✅ **Automated pipeline**: PyPI publication happens automatically on tags

### Quick Release Process

```bash
# Ensure everything is ready
git checkout main && git pull
./scripts/check-all.sh

# Create and publish release
./scripts/release.sh  # Interactive tool
# 🚀 Automatic PyPI publication triggered!
```

See [`scripts/dev-workflow.md`](scripts/dev-workflow.md) for complete workflow documentation.

Thank you for contributing to SingleStore MCP Server! 🚀
