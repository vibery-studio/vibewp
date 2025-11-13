# Testing Guide for VibeWP

Complete guide for testing VibeWP without creating real VPS instances.

## Testing Approaches

### 1. Unit Tests (Mock-Based)
Fast, isolated tests using mocks. No external dependencies.

### 2. Integration Tests (Docker-Based)
Test with real services (MinIO for S3, SSH server) running in Docker.

### 3. Manual Testing (Local Development)
Interactive testing with local services.

---

## Quick Start

### Run Unit Tests (No Setup Required)

```bash
# Run all unit tests
pytest tests/test_remote_backup.py -v

# Run specific test
pytest tests/test_remote_backup.py::TestRemoteBackupManager::test_check_rclone_installed_success -v

# Run with coverage
pytest tests/test_remote_backup.py --cov=cli.utils.remote_backup --cov-report=html
```

### Run Integration Tests (Requires Docker)

```bash
# 1. Start test services
docker-compose -f docker-compose.test.yml up -d

# 2. Wait for services to be ready
sleep 10

# 3. Run integration tests
RUN_INTEGRATION_TESTS=1 pytest tests/integration/ -v

# 4. Stop services
docker-compose -f docker-compose.test.yml down
```

---

## Unit Testing (Mocking)

### Mock SSH Manager

The `MockSSHManager` class simulates VPS SSH connections:

```python
from tests.test_remote_backup import MockSSHManager

# Create mock SSH
mock_ssh = MockSSHManager()

# Configure mock responses
mock_ssh.mock_responses["which rclone"] = (0, "/usr/bin/rclone", "")

# Use with RemoteBackupManager
backup_mgr = RemoteBackupManager(mock_ssh)
backup_mgr.check_rclone_installed()  # Uses mock

# Verify commands were run
assert "which rclone" in mock_ssh.commands_run
```

### Test Examples

**Test rclone installation check:**
```python
def test_check_rclone_installed(mock_ssh):
    mock_ssh.mock_responses["which rclone"] = (0, "/usr/bin/rclone", "")
    backup_mgr = RemoteBackupManager(mock_ssh)
    assert backup_mgr.check_rclone_installed() is True
```

**Test backup sync:**
```python
def test_sync_backup(mock_ssh):
    backup_mgr = RemoteBackupManager(mock_ssh)
    result = backup_mgr.sync_backup_to_remote(
        local_backup_path="/path/to/backup.tar.gz",
        remote_path="backups/site1",
        bucket="test-bucket"
    )
    assert result is True
    # Verify rclone copy was called
    assert any("rclone copy" in cmd for cmd in mock_ssh.commands_run)
```

### Benefits
- ✅ Fast (milliseconds per test)
- ✅ No external dependencies
- ✅ Test error conditions easily
- ✅ CI/CD friendly

---

## Integration Testing (Docker)

### Local MinIO Setup

MinIO provides S3-compatible API for testing:

```bash
# Start MinIO
docker-compose -f docker-compose.test.yml up -d minio

# Access MinIO Console
open http://localhost:9001
# Login: minioadmin / minioadmin

# Create test bucket via UI or CLI
docker exec vibewp-test-minio mc mb local/vibewp-test
```

### Configure rclone for MinIO

```bash
# Create rclone config for local testing
cat > ~/.config/rclone/rclone.conf << 'EOF'
[vibewp-test-minio]
type = s3
provider = Minio
access_key_id = minioadmin
secret_access_key = minioadmin
endpoint = http://localhost:9000
EOF

# Test rclone connection
rclone lsd vibewp-test-minio:
```

### Test Real Uploads

```bash
# Create test backup
echo "test backup" > /tmp/test-backup.tar.gz

# Upload with rclone
rclone copy /tmp/test-backup.tar.gz vibewp-test-minio:vibewp-test/backups/

# List backups
rclone ls vibewp-test-minio:vibewp-test/backups/

# Verify in MinIO Console
open http://localhost:9001/browser/vibewp-test/backups
```

### Mock SSH Server

Test SSH operations without VPS:

```bash
# Start SSH server
docker-compose -f docker-compose.test.yml up -d ssh-server

# Generate SSH key for testing
mkdir -p tests/fixtures/ssh
ssh-keygen -t rsa -f tests/fixtures/ssh/id_rsa -N ""

# Copy public key to authorized_keys
cp tests/fixtures/ssh/id_rsa.pub tests/fixtures/ssh/authorized_keys

# Test SSH connection
ssh -i tests/fixtures/ssh/id_rsa -p 2222 testuser@localhost
```

### Benefits
- ✅ Test real S3 operations
- ✅ Test rclone commands
- ✅ Test SSH operations
- ✅ Reproducible environment
- ✅ No cloud costs

---

## Manual Testing Workflow

### 1. Setup Local Environment

```bash
# Start all test services
docker-compose -f docker-compose.test.yml up -d

# Verify services are running
docker ps | grep vibewp-test

# Check MinIO health
curl http://localhost:9000/minio/health/live

# Check SSH server
nc -zv localhost 2222
```

### 2. Configure VibeWP for Local Testing

Create test config:

```bash
# Create test config
mkdir -p ~/.vibewp-test
cat > ~/.vibewp-test/sites.yaml << 'EOF'
vps:
  host: localhost
  port: 2222
  user: testuser
  key_path: tests/fixtures/ssh/id_rsa

remote_backup:
  enabled: true
  provider: minio
  endpoint: http://localhost:9000
  bucket: vibewp-test
  access_key: minioadmin
  secret_key: minioadmin
  encryption: false
  retention_days: 7
EOF
```

### 3. Test Backup Commands

```bash
# Test configuration
VIBEWP_CONFIG=~/.vibewp-test/sites.yaml vibewp backup configure-remote

# Test backup creation (requires mock site)
# You'd need to create mock site structure first

# Test listing remote backups
rclone ls vibewp-test-minio:vibewp-test/backups/
```

### 4. Verify Results

```bash
# Check MinIO Console
open http://localhost:9001/browser/vibewp-test

# Check uploaded files
docker exec vibewp-test-minio mc ls local/vibewp-test/backups/

# Download and verify
rclone copy vibewp-test-minio:vibewp-test/backups/test.tar.gz /tmp/
tar -tzf /tmp/test.tar.gz
```

---

## Testing Configuration Validation

### Test Config Schema

```python
from cli.utils.config import RemoteBackupConfig
import pytest

# Test valid config
config = RemoteBackupConfig(
    enabled=True,
    bucket="test-bucket",
    access_key="AKIATEST",
    secret_key="secret"
)
assert config.enabled is True

# Test validation
with pytest.raises(ValueError):
    RemoteBackupConfig(
        enabled=True,
        bucket="",  # Empty bucket should fail
        access_key="AKIATEST",
        secret_key="secret"
    )
```

---

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run unit tests
        run: pytest tests/test_remote_backup.py -v --cov

  integration-tests:
    runs-on: ubuntu-latest
    services:
      minio:
        image: minio/minio:latest
        ports:
          - 9000:9000
        env:
          MINIO_ROOT_USER: minioadmin
          MINIO_ROOT_PASSWORD: minioadmin
        options: --health-cmd "curl -f http://localhost:9000/minio/health/live"

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install rclone
        run: curl https://rclone.org/install.sh | sudo bash
      - name: Run integration tests
        env:
          RUN_INTEGRATION_TESTS: 1
        run: pytest tests/integration/ -v
```

---

## Troubleshooting

### MinIO Connection Issues

```bash
# Check MinIO is running
docker logs vibewp-test-minio

# Restart MinIO
docker-compose -f docker-compose.test.yml restart minio

# Test connection
curl http://localhost:9000/minio/health/live
```

### SSH Server Issues

```bash
# Check SSH server logs
docker logs vibewp-test-ssh

# Verify SSH key permissions
chmod 600 tests/fixtures/ssh/id_rsa
chmod 644 tests/fixtures/ssh/id_rsa.pub

# Test SSH connection manually
ssh -i tests/fixtures/ssh/id_rsa -p 2222 testuser@localhost -v
```

### rclone Issues

```bash
# Check rclone config
rclone config show vibewp-test-minio

# Test connection
rclone lsd vibewp-test-minio: -vv

# Check MinIO credentials
docker exec vibewp-test-minio mc alias list
```

---

## Test Coverage Goals

| Component | Target Coverage | Current |
|-----------|----------------|---------|
| RemoteBackupManager | 90%+ | ✅ |
| RemoteBackupConfig | 100% | ✅ |
| Backup Commands | 80%+ | ⏳ |
| Doctor Checks | 80%+ | ⏳ |

---

## Best Practices

1. **Mock for Unit Tests**
   - Fast feedback
   - Test edge cases
   - No external dependencies

2. **Docker for Integration**
   - Test real operations
   - Reproducible environment
   - Safe sandbox

3. **Manual for Workflows**
   - End-to-end testing
   - UX validation
   - Documentation verification

4. **Always Test Error Paths**
   - Network failures
   - Invalid credentials
   - Permission errors

5. **Keep Tests Fast**
   - Unit tests < 100ms
   - Integration tests < 5s
   - Full suite < 30s

---

## Resources

- **pytest docs:** https://docs.pytest.org/
- **MinIO docs:** https://min.io/docs/
- **rclone docs:** https://rclone.org/docs/
- **unittest.mock:** https://docs.python.org/3/library/unittest.mock.html
