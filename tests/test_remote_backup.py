"""Tests for remote backup functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from cli.utils.remote_backup import RemoteBackupManager
from cli.utils.config import RemoteBackupConfig


class MockSSHManager:
    """Mock SSH manager for testing without VPS."""

    def __init__(self):
        self.connected = False
        self.commands_run = []
        self.mock_responses = {}

    def connect(self):
        """Mock SSH connection."""
        self.connected = True

    def disconnect(self):
        """Mock SSH disconnection."""
        self.connected = False

    def run_command(self, cmd):
        """Mock command execution."""
        self.commands_run.append(cmd)

        # Return mock responses based on command
        if cmd in self.mock_responses:
            return self.mock_responses[cmd]

        # Default responses
        if "which rclone" in cmd:
            return (0, "/usr/bin/rclone", "")
        elif "rclone listremotes" in cmd:
            return (0, "vibewp-s3:\n", "")
        elif "rclone lsd" in cmd:
            return (0, "", "")
        elif "rclone ls" in cmd:
            return (0, "1048576 backup1.tar.gz\n2097152 backup2.tar.gz\n", "")
        elif "rclone size" in cmd:
            return (0, '{"bytes": 3145728}', "")
        else:
            return (0, "", "")


class TestRemoteBackupManager:
    """Test RemoteBackupManager class."""

    @pytest.fixture
    def mock_ssh(self):
        """Create mock SSH manager."""
        return MockSSHManager()

    @pytest.fixture
    def backup_manager(self, mock_ssh):
        """Create RemoteBackupManager with mock SSH."""
        return RemoteBackupManager(mock_ssh)

    def test_init(self, backup_manager):
        """Test initialization."""
        assert backup_manager.rclone_remote_name == "vibewp-s3"
        assert backup_manager.ssh is not None

    def test_check_rclone_installed_success(self, backup_manager, mock_ssh):
        """Test checking rclone when installed."""
        mock_ssh.mock_responses["which rclone"] = (0, "/usr/bin/rclone", "")
        assert backup_manager.check_rclone_installed() is True
        assert "which rclone" in mock_ssh.commands_run

    def test_check_rclone_installed_not_found(self, backup_manager, mock_ssh):
        """Test checking rclone when not installed."""
        mock_ssh.mock_responses["which rclone"] = (1, "", "not found")
        assert backup_manager.check_rclone_installed() is False

    def test_check_rclone_configured_success(self, backup_manager, mock_ssh):
        """Test checking rclone configuration when configured."""
        assert backup_manager.check_rclone_configured() is True

    def test_check_rclone_configured_not_found(self, backup_manager, mock_ssh):
        """Test checking rclone configuration when not configured."""
        mock_ssh.mock_responses[
            "rclone listremotes | grep -q '^vibewp-s3:$'"
        ] = (1, "", "")
        assert backup_manager.check_rclone_configured() is False

    def test_install_rclone_success(self, backup_manager, mock_ssh):
        """Test installing rclone successfully."""
        install_cmd = "curl https://rclone.org/install.sh | sudo bash"
        mock_ssh.mock_responses[install_cmd] = (0, "Installation complete", "")
        mock_ssh.mock_responses["which rclone"] = (0, "/usr/bin/rclone", "")

        result = backup_manager.install_rclone()
        assert result is True
        assert install_cmd in mock_ssh.commands_run

    def test_install_rclone_failure(self, backup_manager, mock_ssh):
        """Test rclone installation failure."""
        install_cmd = "curl https://rclone.org/install.sh | sudo bash"
        mock_ssh.mock_responses[install_cmd] = (1, "", "Download failed")

        with pytest.raises(RuntimeError, match="Failed to install rclone"):
            backup_manager.install_rclone()

    def test_configure_rclone_s3(self, backup_manager, mock_ssh):
        """Test configuring rclone for S3."""
        result = backup_manager.configure_rclone(
            provider="s3",
            bucket="test-bucket",
            access_key="AKIATEST",
            secret_key="secret123",
            region="us-east-1"
        )

        assert result is True
        # Check config write command was run
        config_cmds = [cmd for cmd in mock_ssh.commands_run if "rclone.conf" in cmd]
        assert len(config_cmds) > 0

    def test_configure_rclone_r2(self, backup_manager, mock_ssh):
        """Test configuring rclone for Cloudflare R2."""
        result = backup_manager.configure_rclone(
            provider="r2",
            bucket="test-bucket",
            access_key="AKIATEST",
            secret_key="secret123",
            endpoint="https://account.r2.cloudflarestorage.com"
        )

        assert result is True

    def test_configure_rclone_test_failure(self, backup_manager, mock_ssh):
        """Test rclone configuration when test fails."""
        mock_ssh.mock_responses[
            "rclone lsd vibewp-s3:test-bucket --max-depth 1"
        ] = (1, "", "Bucket not found")

        with pytest.raises(RuntimeError, match="rclone configuration test failed"):
            backup_manager.configure_rclone(
                provider="s3",
                bucket="test-bucket",
                access_key="AKIATEST",
                secret_key="secret123"
            )

    def test_sync_backup_to_remote(self, backup_manager, mock_ssh):
        """Test syncing backup to remote."""
        sync_cmd = "rclone copy /path/to/backup.tar.gz vibewp-s3:test-bucket/backups/site1 --transfers 4 --checkers 8 --retries 3 --low-level-retries 10 --stats 30s --stats-one-line"
        mock_ssh.mock_responses[sync_cmd] = (0, "Transferred: 10MB", "")

        result = backup_manager.sync_backup_to_remote(
            local_backup_path="/path/to/backup.tar.gz",
            remote_path="backups/site1",
            bucket="test-bucket",
            encryption=True
        )

        assert result is True

    def test_sync_backup_failure(self, backup_manager, mock_ssh):
        """Test backup sync failure."""
        # Mock all rclone copy commands to fail
        for cmd in mock_ssh.commands_run:
            if cmd.startswith("rclone copy"):
                mock_ssh.mock_responses[cmd] = (1, "", "Upload failed")

        # Set default fail response for any rclone copy
        def run_command_with_fail(cmd):
            if cmd.startswith("rclone copy"):
                return (1, "", "Upload failed")
            return (0, "", "")

        mock_ssh.run_command = run_command_with_fail

        with pytest.raises(RuntimeError, match="Backup sync failed"):
            backup_manager.sync_backup_to_remote(
                local_backup_path="/path/to/backup.tar.gz",
                remote_path="backups/site1",
                bucket="test-bucket"
            )

    def test_list_remote_backups(self, backup_manager, mock_ssh):
        """Test listing remote backups."""
        backups = backup_manager.list_remote_backups(
            bucket="test-bucket",
            remote_path="backups"
        )

        assert len(backups) == 2
        assert backups[0]['filename'] == 'backup1.tar.gz'
        assert backups[0]['size'] == '1048576'
        assert backups[1]['filename'] == 'backup2.tar.gz'

    def test_list_remote_backups_empty(self, backup_manager, mock_ssh):
        """Test listing when no backups exist."""
        mock_ssh.mock_responses[
            "rclone ls vibewp-s3:test-bucket/backups"
        ] = (0, "", "")

        backups = backup_manager.list_remote_backups(
            bucket="test-bucket",
            remote_path="backups"
        )

        assert backups == []

    def test_list_remote_backups_error(self, backup_manager, mock_ssh):
        """Test listing backups with error."""
        mock_ssh.mock_responses[
            "rclone ls vibewp-s3:test-bucket/backups"
        ] = (1, "", "Access denied")

        backups = backup_manager.list_remote_backups(
            bucket="test-bucket",
            remote_path="backups"
        )

        assert backups == []

    def test_cleanup_old_backups(self, backup_manager, mock_ssh):
        """Test cleanup of old backups."""
        result = backup_manager.cleanup_old_backups(
            bucket="test-bucket",
            remote_path="backups/site1",
            retention_days=30
        )

        assert result is True
        cleanup_cmd = [cmd for cmd in mock_ssh.commands_run if "rclone delete" in cmd]
        assert len(cleanup_cmd) > 0
        assert "--min-age 30d" in cleanup_cmd[0]

    def test_cleanup_failure(self, backup_manager, mock_ssh):
        """Test cleanup failure handling."""
        def run_command_fail(cmd):
            if "rclone delete" in cmd:
                return (1, "", "Delete failed")
            return (0, "", "")

        mock_ssh.run_command = run_command_fail

        result = backup_manager.cleanup_old_backups(
            bucket="test-bucket",
            remote_path="backups/site1",
            retention_days=30
        )

        assert result is False

    def test_get_remote_size(self, backup_manager, mock_ssh):
        """Test getting remote size."""
        size = backup_manager.get_remote_size(
            bucket="test-bucket",
            remote_path="backups"
        )

        assert size == "3.00 MB"

    def test_get_remote_size_error(self, backup_manager, mock_ssh):
        """Test getting remote size with error."""
        mock_ssh.mock_responses[
            "rclone size vibewp-s3:test-bucket/backups --json"
        ] = (1, "", "Error")

        size = backup_manager.get_remote_size(
            bucket="test-bucket",
            remote_path="backups"
        )

        assert size == "Unknown"

    def test_get_rclone_provider_mapping(self):
        """Test provider name mapping."""
        from cli.utils.remote_backup import RemoteBackupManager

        assert RemoteBackupManager._get_rclone_provider("s3") == "AWS"
        assert RemoteBackupManager._get_rclone_provider("r2") == "Cloudflare"
        assert RemoteBackupManager._get_rclone_provider("b2") == "Backblaze"
        assert RemoteBackupManager._get_rclone_provider("wasabi") == "Wasabi"
        assert RemoteBackupManager._get_rclone_provider("unknown") == "Other"
        assert RemoteBackupManager._get_rclone_provider("S3") == "AWS"  # Case insensitive


class TestRemoteBackupConfig:
    """Test RemoteBackupConfig validation."""

    def test_default_config(self):
        """Test default configuration."""
        config = RemoteBackupConfig()
        assert config.enabled is False
        assert config.provider == "s3"
        assert config.bucket == ""
        assert config.encryption is True
        assert config.retention_days == 30

    def test_valid_enabled_config(self):
        """Test valid enabled configuration."""
        config = RemoteBackupConfig(
            enabled=True,
            bucket="test-bucket",
            access_key="AKIATEST",
            secret_key="secret123"
        )
        assert config.enabled is True
        assert config.bucket == "test-bucket"

    def test_invalid_enabled_without_bucket(self):
        """Test validation fails when enabled without bucket."""
        with pytest.raises(ValueError, match="required when remote backup is enabled"):
            RemoteBackupConfig(
                enabled=True,
                bucket="",  # Empty
                access_key="AKIATEST",
                secret_key="secret123"
            )

    def test_invalid_enabled_without_access_key(self):
        """Test validation fails when enabled without access_key."""
        with pytest.raises(ValueError, match="required when remote backup is enabled"):
            RemoteBackupConfig(
                enabled=True,
                bucket="test-bucket",
                access_key="",  # Empty
                secret_key="secret123"
            )

    def test_invalid_retention_negative(self):
        """Test validation fails for negative retention."""
        with pytest.raises(ValueError, match="retention_days must be >= 0"):
            RemoteBackupConfig(retention_days=-1)

    def test_invalid_retention_too_large(self):
        """Test validation fails for excessive retention."""
        with pytest.raises(ValueError, match="retention_days cannot exceed 3650"):
            RemoteBackupConfig(retention_days=5000)

    def test_retention_zero_allowed(self):
        """Test retention_days=0 is allowed (no cleanup)."""
        config = RemoteBackupConfig(retention_days=0)
        assert config.retention_days == 0

    def test_disabled_with_empty_fields(self):
        """Test disabled config allows empty fields."""
        config = RemoteBackupConfig(
            enabled=False,
            bucket="",
            access_key="",
            secret_key=""
        )
        assert config.enabled is False
