#!/bin/bash

# Script to run all code quality checks AND tests
set -e

echo "🔍 Running code quality checks..."
./scripts/check.sh

echo ""
echo "🧪 Running tests..."
./scripts/test.sh

echo ""
echo "🎉 All checks and tests passed!"
