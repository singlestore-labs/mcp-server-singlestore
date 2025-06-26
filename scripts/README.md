# Scripts

This directory contains utility scripts for development and maintenance.

## check.sh

Runs all code quality checks in sequence:

- Ruff linting
- Ruff formatting
- Pre-commit hooks
- Tests

Usage:

```bash
./scripts/check.sh
```

This is useful for checking your code before committing or creating a pull request.
