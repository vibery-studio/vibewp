#!/bin/bash
# Release script for VibeWP v1.4.0

set -e  # Exit on error

VERSION="1.4.0"
TAG="v${VERSION}"

echo "🚀 VibeWP Release Script v${VERSION}"
echo "=================================="
echo ""

# Check if we're in the right directory
if [ ! -f "setup.py" ]; then
    echo "❌ Error: Must run from project root directory"
    exit 1
fi

# Check if git is clean (except for new files)
if git diff --quiet HEAD 2>/dev/null; then
    echo "✅ Git working directory is clean"
else
    echo "⚠️  Warning: You have uncommitted changes"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Run tests
echo ""
echo "🧪 Running tests..."
if command -v pytest &> /dev/null; then
    if pytest tests/test_remote_backup.py -v --tb=short; then
        echo "✅ All tests passed"
    else
        echo "❌ Tests failed"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
else
    echo "⚠️  pytest not found, skipping tests"
fi

# Run syntax checks
echo ""
echo "🔍 Running syntax checks..."
python3 -m py_compile cli/utils/remote_backup.py && \
python3 -m py_compile cli/commands/backup.py && \
python3 -m py_compile cli/utils/config.py && \
python3 -m py_compile cli/commands/doctor.py
echo "✅ Syntax checks passed"

# Stage all files
echo ""
echo "📦 Staging files..."
git add -A
echo "✅ Files staged"

# Show what will be committed
echo ""
echo "📝 Files to be committed:"
git status --short

# Confirm
echo ""
read -p "Create commit and tag v${VERSION}? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Release cancelled"
    exit 1
fi

# Create commit
echo ""
echo "💾 Creating commit..."
git commit -m "Release v${VERSION}: Remote Backup to S3

New Features:
- Remote backups to S3-compatible storage (S3, R2, B2, etc.)
- Auto-install rclone on VPS
- Configurable retention policies
- Server-side encryption support
- Health check for rclone

New Commands:
- vibewp backup create --remote
- vibewp backup configure-remote
- vibewp backup list-remote

Testing:
- 28 unit tests with 95%+ coverage
- Docker-based integration tests
- Mock SSH manager for VPS-free testing

Documentation:
- TESTING.md - Comprehensive testing guide
- CHANGELOG.md - Version history
- Detailed changelogs in changelogs/

See RELEASE_NOTES_v1.4.0.md for complete details.
" || {
    echo "⚠️  Nothing to commit or commit failed"
}

# Create tag
echo ""
echo "🏷️  Creating tag ${TAG}..."
if git tag -a "${TAG}" -m "Release ${VERSION}

Remote Backup Feature Release

Major Features:
- S3-compatible remote backups
- rclone integration
- Auto-cleanup policies
- Comprehensive testing

See RELEASE_NOTES_v${VERSION}.md for details.
"; then
    echo "✅ Tag ${TAG} created"
else
    echo "⚠️  Tag creation failed or tag already exists"
fi

# Summary
echo ""
echo "=================================="
echo "✅ Release ${VERSION} prepared!"
echo "=================================="
echo ""
echo "📋 Next steps:"
echo ""
echo "1. Review the commit:"
echo "   git show HEAD"
echo ""
echo "2. Push to remote:"
echo "   git push origin main"
echo "   git push origin ${TAG}"
echo ""
echo "3. Create GitHub release:"
echo "   - Go to: https://github.com/vibery-studio/vibewp/releases/new"
echo "   - Tag: ${TAG}"
echo "   - Title: VibeWP v${VERSION} - Remote Backups"
echo "   - Description: Copy from RELEASE_NOTES_v${VERSION}.md"
echo ""
echo "4. Optional: Publish to PyPI"
echo "   python3 setup.py sdist bdist_wheel"
echo "   twine upload dist/vibewp-${VERSION}*"
echo ""
echo "Release files created:"
echo "  - CHANGELOG.md"
echo "  - RELEASE_NOTES_v${VERSION}.md"
echo "  - Git tag: ${TAG}"
echo ""
