#!/bin/bash

# Script to run tests with coverage
set -e

echo "🧪 Running tests with coverage..."
uv run pytest --cov=src --cov-report=term-missing

echo "✅ All tests passed!"
