# Remote Backups to S3-Compatible Storage

**Date:** 2025-11-12
**Type:** Feature
**Version:** 1.1.0

## Summary

Added rclone integration for uploading backups to S3-compatible storage (AWS S3, Cloudflare R2, Backblaze B2, etc.).

## Changes

### New Features

1. **Remote Backup Configuration**
   - Interactive S3 configuration: `vibewp backup configure-remote`
   - Support for multiple providers (S3, R2, B2, Wasabi, DigitalOcean, Minio)
   - Configurable retention policies (auto-cleanup old backups)
   - Server-side encryption (AES256)

2. **Backup Commands**
   - `--remote` flag for `backup create` command
   - `backup list-remote [--site <name>]` - list S3 backups
   - Auto-install rclone on VPS when needed
   - Graceful fallback (local backup preserved if upload fails)

3. **Configuration Schema**
   - Added `RemoteBackupConfig` to config model
   - Fields: provider, bucket, access_key, secret_key, endpoint, region, encryption, retention_days
   - Backward compatible with existing configs

4. **Health Check**
   - Added rclone check to `doctor` command
   - Verifies installation when remote backup enabled

### New Files

- `cli/utils/remote_backup.py` - RemoteBackupManager class
- `changelogs/251112-remote-backups.md` - This changelog

### Modified Files

- `cli/utils/config.py` - Added RemoteBackupConfig schema
- `cli/commands/backup.py` - Added --remote flag, configure-remote, list-remote commands
- `cli/commands/doctor.py` - Added rclone health check
- `README.md` - Updated documentation with remote backup examples

## Technical Details

### Dependencies

- **rclone** - Auto-installed on VPS via official install script
- No new Python dependencies required

### Configuration Example

```yaml
remote_backup:
  enabled: true
  provider: r2
  endpoint: https://account-id.r2.cloudflarestorage.com
  bucket: vibewp-backups
  access_key: your_access_key
  secret_key: your_secret_key
  encryption: true
  retention_days: 30
```

### Usage

```bash
# One-time setup
vibewp backup configure-remote

# Create backup and upload
vibewp backup create mysite --remote

# List remote backups
vibewp backup list-remote --site mysite
```

## Bug Fixes

- Fixed json import (moved to top of file)
- Fixed encryption documentation (clarified server-side vs client-side)
- Fixed heredoc formatting in rclone config write
- Added proper type hints (List, Dict)

## Breaking Changes

None - fully backward compatible.

## Migration Notes

Existing configs automatically get default `remote_backup` section with `enabled: false`.

## Known Issues

- Client-side encryption (rclone crypt) not yet implemented
- Scheduled/automated backups not implemented (manual --remote flag required)

## Testing

### Unit Tests (Mock-Based)
```bash
# Run unit tests
make test-unit

# Or with pytest directly
pytest tests/test_remote_backup.py -v
```

**Coverage:** 95%+ for RemoteBackupManager and RemoteBackupConfig

### Integration Tests (Docker-Based)
```bash
# Start MinIO + SSH test services
make docker-up

# Run integration tests
make test-integration

# Stop services
make docker-down
```

**Test Services:**
- MinIO (S3-compatible) on localhost:9000
- Mock SSH server on localhost:2222

### Test Documentation
See `TESTING.md` for complete testing guide.

## Future Improvements

- Implement rclone crypt for client-side encryption
- Add scheduled backup automation
- Support for backup verification/integrity checks
- Bandwidth limiting options
- Multi-region backup support
