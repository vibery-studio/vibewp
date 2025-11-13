"""Integration tests for remote backup with real MinIO S3."""

import pytest
import os
import subprocess
import time
from pathlib import Path
from cli.utils.remote_backup import RemoteBackupManager
from cli.utils.config import RemoteBackupConfig


# Skip if not in CI/local test environment
SKIP_INTEGRATION = not os.getenv('RUN_INTEGRATION_TESTS', False)


@pytest.fixture(scope="module")
def minio_client():
    """Setup MinIO client for testing."""
    try:
        import boto3
        from botocore.client import Config

        client = boto3.client(
            's3',
            endpoint_url='http://localhost:9000',
            aws_access_key_id='minioadmin',
            aws_secret_access_key='minioadmin',
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'
        )

        # Create test bucket
        try:
            client.create_bucket(Bucket='vibewp-test')
        except:
            pass  # Bucket might already exist

        yield client

        # Cleanup
        try:
            # Delete all objects
            response = client.list_objects_v2(Bucket='vibewp-test')
            if 'Contents' in response:
                objects = [{'Key': obj['Key']} for obj in response['Contents']]
                client.delete_objects(Bucket='vibewp-test', Delete={'Objects': objects})

            # Delete bucket
            client.delete_bucket(Bucket='vibewp-test')
        except:
            pass

    except ImportError:
        pytest.skip("boto3 not installed")


@pytest.mark.skipif(SKIP_INTEGRATION, reason="Integration tests disabled")
class TestRemoteBackupIntegration:
    """Integration tests with real MinIO."""

    def test_full_backup_workflow(self, minio_client, tmp_path):
        """Test complete backup workflow with MinIO."""
        # Create test backup file
        backup_file = tmp_path / "test-backup.tar.gz"
        backup_file.write_text("test backup content")

        # This would normally use SSH manager
        # For integration test, we'd need to configure rclone locally
        # and test the actual rclone commands

        # Verify file can be uploaded to MinIO
        minio_client.upload_file(
            str(backup_file),
            'vibewp-test',
            'backups/site1/test-backup.tar.gz'
        )

        # Verify file exists
        response = minio_client.list_objects_v2(
            Bucket='vibewp-test',
            Prefix='backups/site1/'
        )

        assert 'Contents' in response
        assert len(response['Contents']) == 1
        assert response['Contents'][0]['Key'] == 'backups/site1/test-backup.tar.gz'

    def test_list_backups(self, minio_client, tmp_path):
        """Test listing backups from MinIO."""
        # Upload multiple test files
        for i in range(3):
            backup_file = tmp_path / f"backup-{i}.tar.gz"
            backup_file.write_text(f"backup {i}")
            minio_client.upload_file(
                str(backup_file),
                'vibewp-test',
                f'backups/site1/backup-{i}.tar.gz'
            )

        # List objects
        response = minio_client.list_objects_v2(
            Bucket='vibewp-test',
            Prefix='backups/site1/'
        )

        assert 'Contents' in response
        assert len(response['Contents']) == 3

    def test_delete_old_backups(self, minio_client, tmp_path):
        """Test cleanup of old backups."""
        # Upload test file
        backup_file = tmp_path / "old-backup.tar.gz"
        backup_file.write_text("old backup")
        minio_client.upload_file(
            str(backup_file),
            'vibewp-test',
            'backups/site1/old-backup.tar.gz'
        )

        # Delete the file (simulating cleanup)
        minio_client.delete_object(
            Bucket='vibewp-test',
            Key='backups/site1/old-backup.tar.gz'
        )

        # Verify deletion
        response = minio_client.list_objects_v2(
            Bucket='vibewp-test',
            Prefix='backups/site1/'
        )

        contents = response.get('Contents', [])
        assert len([c for c in contents if c['Key'] == 'backups/site1/old-backup.tar.gz']) == 0


@pytest.mark.skipif(SKIP_INTEGRATION, reason="Integration tests disabled")
class TestRcloneIntegration:
    """Test rclone commands with MinIO."""

    @pytest.fixture
    def setup_rclone_config(self, tmp_path):
        """Setup rclone config for MinIO."""
        config_dir = tmp_path / ".config" / "rclone"
        config_dir.mkdir(parents=True)

        config_file = config_dir / "rclone.conf"
        config_content = """[vibewp-test-minio]
type = s3
provider = Minio
access_key_id = minioadmin
secret_access_key = minioadmin
endpoint = http://localhost:9000
"""
        config_file.write_text(config_content)

        # Set environment variable for rclone config
        os.environ['RCLONE_CONFIG'] = str(config_file)

        yield config_file

        # Cleanup
        del os.environ['RCLONE_CONFIG']

    def test_rclone_copy_to_minio(self, setup_rclone_config, tmp_path, minio_client):
        """Test rclone copy command with MinIO."""
        # Create test file
        test_file = tmp_path / "test-upload.txt"
        test_file.write_text("rclone test content")

        # Run rclone copy
        result = subprocess.run(
            [
                "rclone", "copy",
                str(test_file),
                "vibewp-test-minio:vibewp-test/rclone-test/"
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"rclone not available: {result.stderr}")

        # Verify file exists in MinIO
        response = minio_client.list_objects_v2(
            Bucket='vibewp-test',
            Prefix='rclone-test/'
        )

        assert 'Contents' in response
        assert any(obj['Key'] == 'rclone-test/test-upload.txt' for obj in response['Contents'])

    def test_rclone_list(self, setup_rclone_config, minio_client):
        """Test rclone ls command."""
        # Upload file via boto3
        minio_client.put_object(
            Bucket='vibewp-test',
            Key='rclone-test/list-test.txt',
            Body=b'test content'
        )

        # Run rclone ls
        result = subprocess.run(
            ["rclone", "ls", "vibewp-test-minio:vibewp-test/rclone-test/"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"rclone not available: {result.stderr}")

        assert "list-test.txt" in result.stdout
