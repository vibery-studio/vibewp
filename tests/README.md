# Testing Quick Start

## TL;DR

```bash
# Unit tests (fast, no dependencies)
make test-unit

# Integration tests (requires Docker)
make docker-up
make test-integration
make docker-down

# Everything
make test-all
```

## File Structure

```
tests/
├── README.md                           # This file
├── test_remote_backup.py               # Unit tests with mocks
├── integration/
│   └── test_remote_backup_integration.py  # Integration tests with MinIO
└── fixtures/
    └── ssh/                            # SSH keys for testing
        ├── id_rsa
        ├── id_rsa.pub
        └── authorized_keys
```

## Unit Tests (Recommended)

**No setup required.** Uses mocks to simulate VPS and S3 operations.

```bash
# Run all unit tests
pytest tests/test_remote_backup.py -v

# Run specific test class
pytest tests/test_remote_backup.py::TestRemoteBackupManager -v

# Run with coverage
pytest tests/test_remote_backup.py --cov=cli.utils.remote_backup
```

**What's tested:**
- ✅ rclone installation check
- ✅ rclone configuration
- ✅ Backup sync to remote
- ✅ List remote backups
- ✅ Cleanup old backups
- ✅ Config validation
- ✅ Error handling

**Speed:** ~2 seconds for all unit tests

## Integration Tests (Optional)

**Requires Docker.** Uses real MinIO (S3) and SSH server.

```bash
# 1. Start services
docker-compose -f docker-compose.test.yml up -d

# 2. Wait for services (or check status)
docker ps | grep vibewp-test

# 3. Run tests
RUN_INTEGRATION_TESTS=1 pytest tests/integration/ -v

# 4. Cleanup
docker-compose -f docker-compose.test.yml down
```

**What's tested:**
- ✅ Real S3 uploads to MinIO
- ✅ rclone commands with real backend
- ✅ SSH operations (if SSH server configured)

**Speed:** ~10 seconds including Docker startup

## Using Makefile (Easiest)

```bash
# View all available commands
make help

# Run unit tests
make test

# Run integration tests
make test-integration

# Run all tests
make test-all

# Start test services only
make docker-up

# View service logs
make docker-logs

# Stop services
make docker-down

# Generate coverage report
make coverage
```

## Manual Testing with MinIO

```bash
# 1. Start MinIO
docker-compose -f docker-compose.test.yml up -d minio

# 2. Open MinIO console
open http://localhost:9001
# Login: minioadmin / minioadmin

# 3. Create bucket via UI or CLI
docker exec vibewp-test-minio mc mb local/vibewp-test

# 4. Configure rclone
cat > ~/.config/rclone/test-minio.conf << 'EOF'
[test-minio]
type = s3
provider = Minio
access_key_id = minioadmin
secret_access_key = minioadmin
endpoint = http://localhost:9000
EOF

# 5. Test upload
echo "test" > /tmp/test.txt
rclone copy /tmp/test.txt test-minio:vibewp-test/test/

# 6. Verify in console
open http://localhost:9001/browser/vibewp-test
```

## Troubleshooting

### Tests fail with "connection refused"
```bash
# Check if services are running
docker ps | grep vibewp-test

# Restart services
docker-compose -f docker-compose.test.yml restart

# Check logs
docker-compose -f docker-compose.test.yml logs
```

### MinIO not accessible
```bash
# Check MinIO health
curl http://localhost:9000/minio/health/live

# Should return 200 OK

# If not, restart MinIO
docker-compose -f docker-compose.test.yml restart minio
```

### Import errors
```bash
# Install test dependencies
pip install pytest pytest-cov pytest-mock boto3

# Or use Makefile
make install-dev
```

### SSH tests fail
```bash
# Generate SSH keys
make setup-test

# Or manually
mkdir -p tests/fixtures/ssh
ssh-keygen -t rsa -f tests/fixtures/ssh/id_rsa -N ""
cp tests/fixtures/ssh/id_rsa.pub tests/fixtures/ssh/authorized_keys
```

## CI/CD Integration

For GitHub Actions, see `.github/workflows/tests.yml` (to be created).

Basic example:
```yaml
- name: Run tests
  run: |
    pip install pytest pytest-cov
    pytest tests/test_remote_backup.py -v --cov
```

## See Also

- `TESTING.md` - Comprehensive testing guide
- `TRIPLE_CHECK_REPORT.md` - Code review and bug fixes
- `changelogs/251112-remote-backups.md` - Feature changelog
