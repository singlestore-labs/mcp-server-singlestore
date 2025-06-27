#!/bin/bash

# Interactive release script for SingleStore MCP Server
# Handles version bumping, tagging, and automated PyPI publication

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 SingleStore MCP Server Release Tool${NC}"
echo "========================================"

# Check if we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
  echo -e "${RED}❌ Error: You must be on the main branch to create a release${NC}"
  echo "Current branch: $CURRENT_BRANCH"
  exit 1
fi

# Check if working directory is clean
if [ -n "$(git status --porcelain)" ]; then
  echo -e "${RED}❌ Error: Working directory is not clean${NC}"
  echo "Please commit or stash your changes before creating a release."
  git status --short
  exit 1
fi

# Get current version
if [ ! -f "src/version.py" ]; then
  echo -e "${RED}❌ Error: src/version.py not found${NC}"
  exit 1
fi

CURRENT_VERSION=$(python -c "exec(open('src/version.py').read()); print(__version__)")
echo -e "📦 Current version: ${YELLOW}$CURRENT_VERSION${NC}"

# Parse version components
IFS='.' read -ra VERSION_PARTS <<< "$CURRENT_VERSION"
MAJOR=${VERSION_PARTS[0]}
MINOR=${VERSION_PARTS[1]}
PATCH=${VERSION_PARTS[2]}

echo ""
echo -e "${BLUE}Choose version bump type:${NC}"
echo "1) 🐛 Patch (bug fixes): $MAJOR.$MINOR.$((PATCH + 1))"
echo "2) ✨ Minor (new features): $MAJOR.$((MINOR + 1)).0"
echo "3) 💥 Major (breaking changes): $((MAJOR + 1)).0.0"
echo "4) 🎯 Custom version"
echo "5) ❌ Cancel"

read -p "Enter choice (1-5): " choice

case $choice in
  1)
    NEW_VERSION="$MAJOR.$MINOR.$((PATCH + 1))"
    RELEASE_TYPE="patch"
    ;;
  2)
    NEW_VERSION="$MAJOR.$((MINOR + 1)).0"
    RELEASE_TYPE="minor"
    ;;
  3)
    NEW_VERSION="$((MAJOR + 1)).0.0"
    RELEASE_TYPE="major"
    ;;
  4)
    read -p "Enter new version (e.g., 1.2.3): " NEW_VERSION
    RELEASE_TYPE="custom"
    # Validate version format
    if ! [[ $NEW_VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
      echo -e "${RED}❌ Error: Invalid version format. Use semantic versioning (e.g., 1.2.3)${NC}"
      exit 1
    fi
    ;;
  5)
    echo -e "${YELLOW}Release cancelled.${NC}"
    exit 0
    ;;
  *)
    echo -e "${RED}❌ Invalid choice. Exiting.${NC}"
    exit 1
    ;;
esac

echo ""
echo -e "${GREEN}📋 Release Summary:${NC}"
echo "  Current version: $CURRENT_VERSION"
echo "  New version:     $NEW_VERSION"
echo "  Release type:    $RELEASE_TYPE"
echo ""

read -p "Continue with release? (y/N): " confirm

if [[ $confirm != [yY] ]]; then
  echo -e "${YELLOW}Release cancelled.${NC}"
  exit 0
fi

echo ""
echo -e "${BLUE}🔄 Preparing release...${NC}"

# Run quality checks
echo "1/6 Running quality checks..."
if ! ./scripts/check-all.sh > /dev/null 2>&1; then
  echo -e "${RED}❌ Quality checks failed. Please fix issues before releasing.${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Quality checks passed${NC}"

# Update version file
echo "2/6 Updating version file..."
echo "__version__ = \"$NEW_VERSION\"" > src/version.py
echo -e "${GREEN}✅ Version updated to $NEW_VERSION${NC}"

# Create commit
echo "3/6 Creating release commit..."
git add src/version.py
git commit -m "chore: bump version to $NEW_VERSION"
echo -e "${GREEN}✅ Release commit created${NC}"

# Create tag
echo "4/6 Creating release tag..."
git tag "v$NEW_VERSION"
echo -e "${GREEN}✅ Tag v$NEW_VERSION created${NC}"

# Final confirmation
echo ""
echo -e "${YELLOW}⚠️  Ready to publish release v$NEW_VERSION${NC}"
echo "This will:"
echo "  1. Push commit to main branch"
echo "  2. Push tag v$NEW_VERSION"
echo "  3. Trigger automatic PyPI publication"
echo "  4. Create GitHub release"
echo ""

read -p "Push release? (y/N): " push_confirm

if [[ $push_confirm != [yY] ]]; then
  echo -e "${YELLOW}Release prepared but not pushed.${NC}"
  echo "To push later, run:"
  echo "  git push origin main --tags"
  exit 0
fi

# Push to remote
echo "5/6 Pushing to remote..."
git push origin main --tags
echo -e "${GREEN}✅ Pushed to remote${NC}"

echo "6/6 Monitoring publication..."
echo ""
echo -e "${GREEN}🎉 Release v$NEW_VERSION initiated successfully!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  📦 PyPI publication: https://github.com/singlestore-labs/mcp-server-singlestore/actions"
echo "  📋 GitHub release: https://github.com/singlestore-labs/mcp-server-singlestore/releases"
echo "  🔍 PyPI package: https://pypi.org/project/singlestore-mcp-server/"
echo ""
echo -e "${YELLOW}⏱️  Publication typically takes 2-5 minutes${NC}"
