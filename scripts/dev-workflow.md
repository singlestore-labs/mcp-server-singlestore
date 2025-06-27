# Development & Release Workflow

This document outlines the development and release process for the SingleStore MCP Server.

## 🚀 Quick Start

### Daily Development
```bash
# Create feature branch
git checkout -b feature/your-feature

# Make changes and validate
./scripts/check.sh  # Fast quality checks
git commit -m "feat: your feature"

# Before creating PR
./scripts/check-all.sh  # Comprehensive validation
git push origin feature/your-feature
```

### Creating a Release
```bash
# Ensure you're on main and everything is clean
git checkout main
git pull origin main
./scripts/check-all.sh

# Run interactive release tool
./scripts/release.sh

# 🚀 Automatic PyPI publication will be triggered!
```

## 📋 Development Process

### 1. Feature Development

**Branch Naming Convention:**
- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `chore/description` - Maintenance tasks

**Development Flow:**
```bash
# Start feature
git checkout main
git pull origin main
git checkout -b feature/add-new-tool

# Develop with fast feedback
# ... make changes ...
./scripts/check.sh  # Quick quality validation
git add . && git commit -m "feat: add new tool"

# Pre-PR validation
./scripts/check-all.sh  # Run everything
git push origin feature/add-new-tool
```

### 2. Pull Request Process

**Before Creating PR:**
1. ✅ Run `./scripts/check-all.sh`
2. ✅ Update documentation if needed
3. ✅ Add/update tests for new features
4. ✅ Ensure CI passes

**PR Requirements:**
- Descriptive title and description
- All CI checks passing
- Code review approval
- Up-to-date with main branch

### 3. Merging Strategy

**Types of Merges to Main:**
- ✅ **Safe merges**: Features, fixes, docs, CI improvements
- ✅ **No automatic publication** - Fast development cycle
- ✅ **Manual release control** - Publish only when ready

## 🏷️ Release Management

### Release Types

| Type | When to Use | Version Bump | Example |
|------|-------------|--------------|---------|
| **Patch** | Bug fixes, docs, CI | `0.2.23` → `0.2.24` | Security fixes, typos |
| **Minor** | New features, tools | `0.2.23` → `0.3.0` | New MCP tools, features |
| **Major** | Breaking changes | `0.2.23` → `1.0.0` | API changes, removals |

### Release Process

#### Option 1: Interactive Release (Recommended)
```bash
./scripts/release.sh
```
- ✅ Interactive version selection
- ✅ Quality checks before release
- ✅ Automatic tagging and publication
- ✅ Safety confirmations

#### Option 2: Manual Release
```bash
# Update version manually
echo '__version__ = "0.2.24"' > src/version.py

# Commit and tag
git add src/version.py
git commit -m "chore: bump version to 0.2.24"
git tag "v0.2.24"

# Push (triggers publication)
git push origin main --tags
```

### What Happens During Release

1. **Version Validation** - Tag must match `src/version.py`
2. **Quality Checks** - Ruff linting, formatting, tests
3. **Package Building** - Create wheel and source distribution
4. **PyPI Publication** - Automatic upload to PyPI
5. **GitHub Release** - Create release notes and assets

## 🛠️ Scripts Overview

### Quality Assurance
- **`./scripts/check.sh`** - Fast pre-commit checks (~1 second)
  - Ruff linting and formatting
  - Pre-commit hooks
  - No tests (for speed)

- **`./scripts/test.sh`** - Test suite only (~0.8 seconds)
  - Full test suite with coverage
  - Independent of quality checks

- **`./scripts/check-all.sh`** - Comprehensive validation (~2 seconds)
  - All quality checks + tests
  - Use before creating PRs

### Release Management
- **`./scripts/release.sh`** - Interactive release tool
  - Version bumping with semantic versioning
  - Safety checks and confirmations
  - Automatic publication trigger

## 🔄 Git Workflow

### Branch Protection Rules
- **Main branch** is protected
- **Pull requests** required for changes
- **Status checks** must pass (CI)
- **Reviews** required from maintainers

### Commit Message Convention
While not strictly enforced, we recommend:
```
feat: add new virtual workspace management
fix: resolve authentication timeout issue
docs: update installation instructions
chore: update dependencies
test: add integration tests for SQL execution
ci: improve build performance
```

## 🎯 Best Practices

### Development
1. **Small, focused commits** - Easier to review and debug
2. **Fast feedback loop** - Use `./scripts/check.sh` frequently
3. **Test-driven development** - Write tests with new features
4. **Documentation updates** - Keep README and docs current

### Releases
1. **Meaningful versions** - Don't publish for every small change
2. **Test thoroughly** - Use `./scripts/check-all.sh` before release
3. **Clear release notes** - Describe what changed for users
4. **Monitor publication** - Check PyPI and GitHub releases

### Code Quality
1. **Pre-commit hooks** - Automatic quality enforcement
2. **Separate concerns** - Quality checks vs. tests vs. releases
3. **CI validation** - All checks run in continuous integration
4. **Manual safety nets** - Interactive confirmations for releases

## 🚨 Troubleshooting

### Release Issues

**Version mismatch error:**
```bash
# Fix version in src/version.py to match your intended tag
echo '__version__ = "1.2.3"' > src/version.py
git add src/version.py && git commit --amend
git tag -f v1.2.3  # Force update tag
```

**Failed publication:**
- Check GitHub Actions logs
- Verify PyPI credentials
- Ensure version doesn't already exist

**Rollback release:**
```bash
# Delete local tag
git tag -d v1.2.3

# Delete remote tag (if pushed)
git push origin :refs/tags/v1.2.3
```

### Development Issues

**Pre-commit hooks failing:**
```bash
# Fix issues automatically
./scripts/check.sh

# Or run individual tools
uv run ruff format src/ tests/
uv run ruff check --fix src/ tests/
```

**Tests failing:**
```bash
# Run tests with verbose output
./scripts/test.sh -v

# Run specific test
uv run pytest tests/test_server.py::TestName -v
```

## 📞 Getting Help

- **GitHub Issues**: Report bugs and request features
- **GitHub Discussions**: Ask questions and share ideas
- **Documentation**: Check README.md and CONTRIBUTING.md
- **Code Review**: Ask maintainers during PR process

---

**Happy coding! 🚀**
