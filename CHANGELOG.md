# Changelog

All notable changes to VibeWP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.1] - 2025-11-13

### Added
- **Remote Backups to S3-Compatible Storage** - Upload backups to AWS S3, Cloudflare R2, Backblaze B2, or any S3-compatible storage
  - `vibewp backup create <site> --remote` - Create and upload backup to S3
  - `vibewp backup configure-remote` - Interactive S3 configuration wizard
  - `vibewp backup list-remote [--site <name>]` - List backups in remote storage
  - Auto-install rclone on VPS when needed
  - Configurable retention policies (auto-cleanup old backups)
  - Server-side encryption (AES256) support
  - Multiple provider support (S3, R2, B2, Wasabi, DigitalOcean, Minio)

- **Remote Backup Configuration**
  - New `remote_backup` section in config with validation
  - Fields: enabled, provider, bucket, access_key, secret_key, endpoint, region, encryption, retention_days
  - Pydantic validators for required fields and retention limits

- **Health Checks**
  - Added rclone installation check to `vibewp doctor`
  - Verifies rclone when remote backup is enabled

- **Testing Infrastructure**
  - Comprehensive unit test suite (28 tests, 95%+ coverage)
  - Mock SSH manager for VPS-free testing
  - Docker-based integration tests with MinIO and SSH server
  - `docker-compose.test.yml` for local S3 testing
  - `Makefile` with test automation commands
  - Complete testing documentation (`TESTING.md`, `TESTING_SUMMARY.md`)

### Changed
- Updated README with remote backup usage examples
- Enhanced backup commands with remote sync capability
- Improved error handling for remote operations (local backup preserved on upload failure)

### Fixed
- **Site creation error**: removed redundant `import time` causing "cannot access local variable 'time'" error (cli/commands/site.py:177)
- Proper SSH connection cleanup in doctor health checks (added finally block)
- rclone configuration check added (separate from installation check)
- Progress flag replaced with stats for non-interactive SSH usage
- Import organization (json moved to top-level)
- Type hints added for better IDE support

### Documentation
- `changelogs/251112-remote-backups.md` - Detailed feature changelog
- `changelogs/README.md` - Changelog system documentation
- `TESTING.md` - Comprehensive testing guide
- `TESTING_SUMMARY.md` - Quick testing reference
- `tests/README.md` - Test suite quick start
- `TRIPLE_CHECK_REPORT.md` - Code review and bug fixes
- `REVIEW.md` - Edge case analysis

### Developer Experience
- Mock-based testing (no VPS required)
- Local MinIO for S3 testing (no cloud costs)
- Fast unit tests (0.21s for 28 tests)
- CI/CD ready test suite

## [1.3.2] - Previous Release

See git history for previous releases.

---

## Types of Changes

- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** in case of vulnerabilities

## Version Numbering

- **Major** (X.0.0) - Breaking changes
- **Minor** (1.X.0) - New features, backward compatible
- **Patch** (1.0.X) - Bug fixes, backward compatible
