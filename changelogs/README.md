# VibeWP Changelogs

This directory contains detailed changelogs for each feature, fix, or release.

## Format

Each changelog follows this structure:

```markdown
# Feature/Fix Title

**Date:** YYYY-MM-DD
**Type:** Feature|Fix|Enhancement|Breaking
**Version:** X.Y.Z

## Summary
Brief description

## Changes
Detailed changes

## Technical Details
Implementation details

## Bug Fixes
Fixes included

## Breaking Changes
Migration notes if any

## Known Issues
Current limitations

## Future Improvements
Planned enhancements
```

## Naming Convention

Files are named: `YYMMDD-short-description.md`

Examples:
- `251112-remote-backups.md`
- `251201-security-hardening.md`
- `260115-multi-vps-support.md`

## Viewing

```bash
# List all changelogs
ls -lt changelogs/*.md

# View specific changelog
cat changelogs/251112-remote-backups.md

# Search changelogs
grep -r "backup" changelogs/
```

## Maintenance

- Keep changelogs concise but complete
- Focus on user-facing changes
- Include migration steps for breaking changes
- Reference related issues/PRs when applicable
