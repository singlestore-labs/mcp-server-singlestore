# Scripts

This directory contains utility scripts for development and maintenance.

## check.sh

Runs code quality checks only (no tests):

- Ruff linting
- Ruff formatting
- Pre-commit hooks

Usage:

```bash
./scripts/check.sh
```

This is useful for quick code quality verification before committing.

## test.sh

Runs tests with coverage:

- Pytest with coverage reporting

Usage:

```bash
./scripts/test.sh
```

This is useful for running tests independently of code quality checks.

## check-all.sh

Runs both code quality checks AND tests:

- All checks from check.sh
- All tests from test.sh

Usage:

```bash
./scripts/check-all.sh
```

This is useful for comprehensive validation before creating a pull request.
