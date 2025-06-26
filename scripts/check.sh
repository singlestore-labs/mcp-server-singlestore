#!/bin/bash

# Script to run all code quality checks
set -e

echo "🔍 Running Ruff linter..."
uv run ruff check src/ tests/

echo "🎨 Checking Ruff formatting..."
uv run ruff format --check src/ tests/

echo "📋 Running pre-commit hooks..."
uv run pre-commit run --all-files

echo "🧪 Running tests..."
uv run pytest

echo "✅ All checks passed!"
