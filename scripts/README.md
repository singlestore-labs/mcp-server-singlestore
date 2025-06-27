# Development Scripts for SingleStore MCP Server

This directory contains utility scripts for development, testing, and release management.

## Scripts Overview

### Release Management Scripts

#### For PR/Branch Development:
- **`mark-release.sh`** - Mark current branch for release when merged to main
- **`release.sh`** - Direct release from main branch (legacy/emergency use)

#### Quality Assurance:
- **`check.sh`** - Fast linting/formatting checks (pre-commit)
- **`test.sh`** - Run test suite only
- **`check-all.sh`** - Comprehensive validation (pre-PR)

## Usage Examples

### Normal PR-based Development Flow:
```bash
# 1. Create feature branch
git checkout -b feature/awesome-feature

# 2. Make changes, commit normally
git add . && git commit -m "feat: add awesome feature"

# 3. When ready for release, mark the branch
./scripts/mark-release.sh
# Choose: patch/minor/major
# This updates version.py and commits it

# 4. Push and create PR
git push origin feature/awesome-feature
# Create PR on GitHub

# 5. When PR is merged to main:
# → Automatic PyPI publication (triggered by version.py change)
```

### Emergency Direct Release (from main):
```bash
git checkout main
./scripts/release.sh  # Legacy direct release
git push origin main --tags
```

### Quality Checks:
```bash
./scripts/check.sh     # Quick checks (1 sec)
./scripts/test.sh      # Tests only (0.8 sec)
./scripts/check-all.sh # Everything (2 sec)
```

## How It Works

1. **Version Bump**: `mark-release.sh` updates `src/version.py` and commits it
2. **PR Review**: Version change goes through normal PR review process
3. **Auto Release**: When PR merges, publish workflow detects version change
4. **Publication**: Automatic PyPI publication and GitHub release creation

## Script Details

### `mark-release.sh` - Mark Branch for Release
Mark your current PR branch for automatic release when merged:
```bash
./scripts/mark-release.sh
```

Features:
- **Branch validation**: Only works on non-main branches
- **Version calculation**: Shows patch/minor/major options
- **Direct version update**: Updates `src/version.py` directly
- **Auto commit**: Commits version change with descriptive message

**Release Types:**
- **🔧 Patch (X.Y.Z+1)**: Bug fixes, documentation, CI improvements
- **✨ Minor (X.Y+1.0)**: New features, backwards-compatible changes
- **💥 Major (X+1.0.0)**: Breaking changes, API modifications

### `release.sh` - Direct Release (Emergency Use)
Smart release tool for direct releases from main branch:
```bash
./scripts/release.sh
```

Features:
- **Safety checks**: Ensures clean working directory and main branch
- **Version detection**: Reads current version from `src/version.py`
- **Semantic versioning**: Supports patch, minor, major, and custom versions
- **Git integration**: Creates commits and tags automatically
- **PyPI trigger**: Pushes tags to trigger automated PyPI publication

### Quality Assurance Scripts

### `check.sh` - Fast Quality Checks (~1 second)
Runs linting and formatting checks without tests for quick feedback:
```bash
./scripts/check.sh
```
- Ruff linting for code quality
- Ruff formatting checks
- Pre-commit hook validation
- Perfect for development workflow and pre-commit hooks

### `test.sh` - Test Suite (~0.8 seconds)
Runs the test suite independently for fast test feedback:
```bash
./scripts/test.sh
```
- Pytest with coverage reporting
- Generates coverage.xml for CI/CD
- Can be run in parallel with quality checks

### `check-all.sh` - Comprehensive Validation (~2 seconds)
Runs both quality checks and tests for complete validation:
```bash
./scripts/check-all.sh
```
- Combines `check.sh` and `test.sh`
- Perfect for pre-PR validation
- Used in CI/CD pipelines

## Files Created

- Updated `src/version.py` - Version source of truth
- Automatic commits: `"release: bump version to X.Y.Z"`
- Automatic tags: `vX.Y.Z` (created during publication)

This system ensures all releases go through PR review while maintaining automation!

## Performance Characteristics

| Script | Duration | Use Case |
|--------|----------|----------|
| `mark-release.sh` | ~2s | PR release marking |
| `check.sh` | ~1.0s | Development, pre-commit |
| `test.sh` | ~0.8s | Test feedback |
| `check-all.sh` | ~2.0s | Pre-PR, CI/CD |
| `release.sh` | ~5s | Emergency releases |

## Dependencies

All scripts use `uv` for fast dependency management and execution:
- Faster than pip/conda
- Automatic virtual environment handling
- Consistent across development and CI

## Configuration

Scripts respect the following configuration:
- **pyproject.toml**: Ruff, pytest, and coverage settings
- **.pre-commit-config.yaml**: Pre-commit hook configuration
- **src/version.py**: Version source of truth
- **Environment variables**: LOG_LEVEL for debugging

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
