#!/bin/bash

# Create changelog file for next release version
# Does NOT bump package version - only creates changelog

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📝 Create Changelog File${NC}"
echo "==============================="

# Get current version
if [ ! -f "src/version.py" ]; then
    echo -e "${RED}❌ src/version.py not found${NC}"
    exit 1
fi

CURRENT_VERSION=$(python -c "exec(open('src/version.py').read()); print(__version__)")
echo -e "${BLUE}Current version:${NC} $CURRENT_VERSION"

# Parse version components
IFS='.' read -ra VERSION_PARTS <<< "$CURRENT_VERSION"
MAJOR=${VERSION_PARTS[0]}
MINOR=${VERSION_PARTS[1]}
PATCH=${VERSION_PARTS[2]}

echo ""
echo -e "${YELLOW}Choose release type for changelog:${NC}"
echo "1) 🔧 Patch (bug fixes, docs, CI): $MAJOR.$MINOR.$((PATCH + 1))"
echo "2) ✨ Minor (new features): $MAJOR.$((MINOR + 1)).0"
echo "3) 💥 Major (breaking changes): $((MAJOR + 1)).0.0"
echo "4) ❌ Cancel"

read -p "Enter choice (1-4): " choice

case $choice in
  1)
    RELEASE_TYPE="patch"
    NEW_VERSION="$MAJOR.$MINOR.$((PATCH + 1))"
    ;;
  2)
    RELEASE_TYPE="minor"
    NEW_VERSION="$MAJOR.$((MINOR + 1)).0"
    ;;
  3)
    RELEASE_TYPE="major"
    NEW_VERSION="$((MAJOR + 1)).0.0"
    ;;
  4)
    echo -e "${YELLOW}Cancelled${NC}"
    exit 0
    ;;
  *)
    echo -e "${RED}Invalid choice. Exiting.${NC}"
    exit 1
    ;;
esac

# Create changelog directory if it doesn't exist
mkdir -p changelog

# Create changelog file
CHANGELOG_FILE="changelog/$NEW_VERSION.md"
if [ -f "$CHANGELOG_FILE" ]; then
    echo -e "${YELLOW}⚠️  Changelog file already exists: $CHANGELOG_FILE${NC}"
    read -p "Overwrite? (y/N): " overwrite
    if [[ $overwrite != [yY] ]]; then
        echo -e "${YELLOW}Cancelled${NC}"
        exit 0
    fi
fi

CURRENT_DATE=$(date +%Y-%m-%d)
echo "# [$NEW_VERSION] - $CURRENT_DATE

## Added

-
-

## Fixed

-
-" > "$CHANGELOG_FILE"

echo ""
echo -e "${GREEN}✅ Changelog file created!${NC}"
echo -e "${BLUE}File:${NC} $CHANGELOG_FILE"
echo -e "${BLUE}Version:${NC} $NEW_VERSION ($RELEASE_TYPE)"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Edit the changelog file to add your changes"
echo "2. Commit the changelog: ${YELLOW}git add $CHANGELOG_FILE && git commit -m 'docs: add changelog for $NEW_VERSION'${NC}"
