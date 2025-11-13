# VibeWP v1.4.0 - Remote Backups Release

**Release Date:** November 12, 2025

## 🎉 What's New

### Remote Backups to S3-Compatible Storage

Upload your WordPress backups to cloud storage automatically!

```bash
# Configure S3 storage (one-time setup)
vibewp backup configure-remote

# Create backup and upload to S3
vibewp backup create mysite --remote

# List remote backups
vibewp backup list-remote --site mysite
```

## ✨ Key Features

### Supported Providers
- ✅ **AWS S3** - Standard S3 storage
- ✅ **Cloudflare R2** - Zero egress fees
- ✅ **Backblaze B2** - Affordable storage
- ✅ **Wasabi** - Hot cloud storage
- ✅ **DigitalOcean Spaces** - Simple object storage
- ✅ **MinIO** - Self-hosted S3
- ✅ Any S3-compatible storage

### Automated Features
- 🔧 **Auto-install rclone** - Installs automatically when needed
- 🔐 **Server-side encryption** - AES256 encryption at rest
- 🗑️ **Auto-cleanup** - Configurable retention policies
- 🛡️ **Graceful fallback** - Local backup preserved if upload fails
- ⚡ **Parallel transfers** - Fast multi-threaded uploads
- 🔄 **Automatic retries** - Handles network failures

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

## 📦 Installation

### New Installation
```bash
curl -fsSL https://raw.githubusercontent.com/vibery-studio/vibewp/main/install.sh | sudo bash
```

### Update Existing Installation
```bash
vibewp update install
```

## 🚀 Getting Started

### 1. Configure Remote Storage

```bash
vibewp backup configure-remote
```

You'll be prompted for:
- Provider (s3/r2/b2/etc.)
- Bucket name
- Access key ID
- Secret access key
- Endpoint URL (for R2, B2, etc.)
- Region (for S3)
- Encryption (yes/no)
- Retention period (days)

### 2. Create Remote Backup

```bash
# Create local backup + upload to S3
vibewp backup create mysite --remote
```

### 3. List Remote Backups

```bash
# List all remote backups
vibewp backup list-remote

# List for specific site
vibewp backup list-remote --site mysite
```

## 🧪 Testing (No VPS Required!)

We've built a comprehensive testing system so you can test without real VPS:

### Unit Tests (Fast)
```bash
make test-unit
# 28 tests pass in 0.21 seconds
```

### Integration Tests (Docker)
```bash
make docker-up        # Start local MinIO
make test-integration # Test with real S3
make docker-down      # Cleanup
```

See `TESTING.md` for complete guide.

## 🔧 Technical Details

### New Commands
- `backup create --remote` - Upload backup to S3
- `backup configure-remote` - Configure S3 settings
- `backup list-remote` - List S3 backups

### New Files
- `cli/utils/remote_backup.py` - Remote backup manager
- `docker-compose.test.yml` - Test infrastructure
- `tests/test_remote_backup.py` - Unit tests
- `Makefile` - Test automation

### New Documentation
- `TESTING.md` - Testing guide
- `CHANGELOG.md` - Version history
- `changelogs/251112-remote-backups.md` - Detailed changelog

## 🐛 Bug Fixes

- Fixed SSH connection cleanup in health checks
- Fixed progress flag for non-interactive SSH
- Added proper type hints for IDE support
- Improved error messages

## ⚠️ Known Limitations

- Client-side encryption (rclone crypt) not yet implemented
- Scheduled backups not yet automated (manual --remote flag required)
- No backup verification/integrity checks yet

## 📊 Statistics

- **New Code:** 327 lines (RemoteBackupManager)
- **Tests:** 28 unit tests, 95%+ coverage
- **Test Speed:** 0.21 seconds
- **Documentation:** 6 new docs files
- **Providers Supported:** 6+ S3-compatible services

## 🔒 Security

- Credentials stored securely (600 permissions)
- Server-side encryption (AES256)
- No credentials in logs
- SSH-only communication with VPS

## 🆙 Upgrade Notes

### From v1.3.x

**No breaking changes!** This is a backward-compatible release.

Your existing configs will work. New `remote_backup` section added automatically with `enabled: false`.

To start using remote backups:
```bash
vibewp backup configure-remote
```

## 📚 Resources

- **Main Docs:** `README.md`
- **Testing Guide:** `TESTING.md`
- **Changelog:** `CHANGELOG.md`
- **Feature Changelog:** `changelogs/251112-remote-backups.md`
- **Code Review:** `TRIPLE_CHECK_REPORT.md`

## 🙏 Credits

Built with:
- [rclone](https://rclone.org/) - For S3 operations
- [MinIO](https://min.io/) - For local testing
- [pytest](https://pytest.org/) - For testing

## 🔮 What's Next

- Client-side encryption (rclone crypt)
- Scheduled backup automation
- Backup verification
- Multi-region support
- Bandwidth limiting options

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/vibery-studio/vibewp/issues)
- **Docs:** [GitHub Wiki](https://github.com/vibery-studio/vibewp/wiki)

---

**Enjoy secure, automated backups to the cloud! 🎉**
