#!/bin/bash

# Script to run code quality checks (without tests)
set -e

echo "🔍 Running Ruff linter..."
uv run ruff check src/ tests/

echo "🎨 Checking Ruff formatting..."
uv run ruff format --check src/ tests/

echo "📋 Running pre-commit hooks..."
uv run pre-commit run --all-files

echo "✅ All quality checks passed!"
