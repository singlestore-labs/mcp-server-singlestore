# Development Scripts

This directory contains utility scripts for development and release management.

## Quality Checks

### check.sh

Runs code quality checks only (no tests):

- Ruff linting
- Ruff formatting
- Pre-commit hooks

Usage:

```bash
./scripts/check.sh
```

This is useful for quick code quality verification before committing (~1 second).

### test.sh

Runs tests with coverage:

- Pytest with coverage reporting

Usage:

```bash
./scripts/test.sh
```

This is useful for running tests independently of code quality checks (~0.8 seconds).

### check-all.sh

Runs both code quality checks AND tests:

- All checks from check.sh
- All tests from test.sh

Usage:

```bash
./scripts/check-all.sh
```

This is useful for comprehensive validation before creating a pull request (~2 seconds).

## Release Management

### release.sh

Interactive release management tool:

- Semantic version bumping (patch/minor/major)
- Automated quality checks before release
- Git tagging and commit creation
- Automated PyPI publication trigger
- Safety confirmations at each step

Usage:

```bash
./scripts/release.sh
```

This provides a guided release process with automatic PyPI publication.

### dev-workflow.md

Complete development and release workflow documentation:

- Daily development practices
- Release process guidelines
- Git workflow conventions
- Troubleshooting guides

## Usage Examples

```bash
# Daily development (fast)
./scripts/check.sh && git commit

# Run tests independently
./scripts/test.sh

# Before creating PR (comprehensive)
./scripts/check-all.sh

# Create and publish new release
./scripts/release.sh
```

## Release Workflow

1. **Development**: Use `check.sh` for fast feedback
2. **Pre-PR**: Use `check-all.sh` for comprehensive validation
3. **Release**: Use `release.sh` for controlled publication
4. **Publication**: Automatic PyPI upload triggered by git tags
