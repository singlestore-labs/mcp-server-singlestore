#!/bin/bash

# Mark current branch for release when merged to main
# Works with PR-based workflow

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📝 Mark Branch for Release${NC}"
echo "==============================="

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" = "main" ]; then
    echo -e "${RED}❌ Cannot mark main branch for release${NC}"
    echo "This command is for feature/PR branches only"
    echo "Use ./scripts/release.sh on main branch instead"
    exit 1
fi

echo -e "${BLUE}Current branch:${NC} $CURRENT_BRANCH"

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
echo -e "${YELLOW}Choose release type for this PR:${NC}"
echo "1) 🔧 Patch (bug fixes, docs, CI): $MAJOR.$MINOR.$((PATCH + 1))"
echo "2) ✨ Minor (new features): $MAJOR.$((MINOR + 1)).0"
echo "3) 💥 Major (breaking changes): $((MAJOR + 1)).0.0"
echo "4) ❌ Cancel (no release)"

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
    echo -e "${YELLOW}Release cancelled${NC}"
    exit 0
    ;;
  *)
    echo -e "${RED}Invalid choice. Exiting.${NC}"
    exit 1
    ;;
esac

echo ""
echo -e "${GREEN}Release Plan:${NC}"
echo -e "  Branch: ${BLUE}$CURRENT_BRANCH${NC}"
echo -e "  Type: ${YELLOW}$RELEASE_TYPE${NC}"
echo -e "  Version: ${GREEN}$CURRENT_VERSION → $NEW_VERSION${NC}"
echo ""

read -p "Mark this branch for release? (y/N): " confirm
if [[ $confirm != [yY] ]]; then
  echo -e "${YELLOW}Release marking cancelled${NC}"
  exit 0
fi

# Update version file directly
echo "__version__ = \"$NEW_VERSION\"" > src/version.py

# Add to git
git add src/version.py
git commit -m "release: bump version to $NEW_VERSION ($RELEASE_TYPE release)"

git push origin "$CURRENT_BRANCH"

echo ""
echo -e "${GREEN}✅ Branch marked for release!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Push your branch: ${YELLOW}git push origin $CURRENT_BRANCH${NC}"
echo "2. Create PR to main"
echo "3. When PR is merged, automatic PyPI publication will be triggered"
echo "4. Optionally create git tag manually: ${YELLOW}git tag v$NEW_VERSION && git push origin v$NEW_VERSION${NC}"
echo ""
echo -e "${BLUE}Release details:${NC}"
echo "  🏷️  Release type: $RELEASE_TYPE"
echo "  📦 New version: $NEW_VERSION"
echo "  📝 Version file updated and committed"
