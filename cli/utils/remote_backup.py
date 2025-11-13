"""Remote backup utilities using rclone for S3-compatible storage"""

import json
import logging
from typing import Optional, List, Dict
from cli.utils.ssh import SSHManager

logger = logging.getLogger(__name__)


class RemoteBackupManager:
    """Manages remote backups to S3-compatible storage using rclone"""

    def __init__(self, ssh_manager: SSHManager):
        """
        Initialize remote backup manager

        Args:
            ssh_manager: SSHManager instance for remote operations
        """
        self.ssh = ssh_manager
        self.rclone_remote_name = "vibewp-s3"

    def check_rclone_installed(self) -> bool:
        """
        Check if rclone is installed on the VPS

        Returns:
            True if rclone is installed, False otherwise
        """
        exit_code, _, _ = self.ssh.run_command("which rclone")
        return exit_code == 0

    def check_rclone_configured(self) -> bool:
        """
        Check if rclone remote is already configured

        Returns:
            True if configured, False otherwise
        """
        exit_code, _, _ = self.ssh.run_command(
            f"rclone listremotes | grep -q '^{self.rclone_remote_name}:$'"
        )
        return exit_code == 0

    def install_rclone(self) -> bool:
        """
        Install rclone on the VPS

        Returns:
            True if installation successful

        Raises:
            RuntimeError: If installation fails
        """
        logger.info("Installing rclone on VPS...")

        # Download and install rclone
        install_cmd = "curl https://rclone.org/install.sh | sudo bash"

        exit_code, stdout, stderr = self.ssh.run_command(install_cmd)

        if exit_code != 0:
            raise RuntimeError(f"Failed to install rclone: {stderr}")

        # Verify installation
        if not self.check_rclone_installed():
            raise RuntimeError("rclone installation verification failed")

        logger.info("rclone installed successfully")
        return True

    def configure_rclone(
        self,
        provider: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        endpoint: Optional[str] = None,
        region: Optional[str] = None
    ) -> bool:
        """
        Configure rclone remote for S3-compatible storage

        Args:
            provider: Provider type (s3, r2, b2, etc.)
            bucket: S3 bucket name
            access_key: S3 access key
            secret_key: S3 secret key
            endpoint: S3 endpoint URL (for custom providers)
            region: S3 region

        Returns:
            True if configuration successful

        Raises:
            RuntimeError: If configuration fails
        """
        logger.info(f"Configuring rclone remote: {self.rclone_remote_name}")

        # Build rclone config based on provider
        config_parts = [
            f"[{self.rclone_remote_name}]",
            "type = s3",
            f"provider = {self._get_rclone_provider(provider)}",
            f"access_key_id = {access_key}",
            f"secret_access_key = {secret_key}",
        ]

        if endpoint:
            config_parts.append(f"endpoint = {endpoint}")

        if region:
            config_parts.append(f"region = {region}")

        # Additional settings for reliability
        config_parts.extend([
            "acl = private",
            "server_side_encryption = AES256",
        ])

        config_content = "\n".join(config_parts)

        # Create rclone config directory
        self.ssh.run_command("mkdir -p ~/.config/rclone")

        # Write config file (escape config_content properly for heredoc)
        write_cmd = f"""cat > ~/.config/rclone/rclone.conf << 'EOF'
{config_content}
EOF
chmod 600 ~/.config/rclone/rclone.conf"""

        exit_code, _, stderr = self.ssh.run_command(write_cmd)

        if exit_code != 0:
            raise RuntimeError(f"Failed to configure rclone: {stderr}")

        # Test configuration
        test_exit, _, test_err = self.ssh.run_command(
            f"rclone lsd {self.rclone_remote_name}:{bucket} --max-depth 1"
        )

        if test_exit != 0:
            raise RuntimeError(f"rclone configuration test failed: {test_err}")

        logger.info("rclone configured and tested successfully")
        return True

    def sync_backup_to_remote(
        self,
        local_backup_path: str,
        remote_path: str,
        bucket: str,
        encryption: bool = False
    ) -> bool:
        """
        Sync local backup to remote S3 storage

        Args:
            local_backup_path: Path to local backup file on VPS
            remote_path: Remote path within bucket
            bucket: S3 bucket name
            encryption: Enable server-side encryption (note: S3 server-side, not rclone crypt)

        Returns:
            True if sync successful

        Raises:
            RuntimeError: If sync fails
        """
        logger.info(f"Syncing backup to remote: {remote_path}")

        # Build rclone sync command
        # Note: encryption here refers to S3 server-side encryption (configured in rclone config)
        # For client-side encryption, would need to configure rclone crypt remote separately
        rclone_cmd = f"rclone copy {local_backup_path} {self.rclone_remote_name}:{bucket}/{remote_path}"

        # Add transfer options for reliability
        rclone_cmd += " --transfers 4 --checkers 8 --retries 3 --low-level-retries 10"

        # Use stats for summary instead of progress (non-interactive friendly)
        rclone_cmd += " --stats 30s --stats-one-line"

        exit_code, stdout, stderr = self.ssh.run_command(rclone_cmd)

        if exit_code != 0:
            raise RuntimeError(f"Backup sync failed: {stderr}")

        logger.info(f"Backup synced successfully to {bucket}/{remote_path}")
        return True

    def list_remote_backups(self, bucket: str, remote_path: str = "backups") -> List[Dict[str, str]]:
        """
        List backups in remote storage

        Args:
            bucket: S3 bucket name
            remote_path: Remote path to list

        Returns:
            List of remote backup files
        """
        cmd = f"rclone ls {self.rclone_remote_name}:{bucket}/{remote_path}"
        exit_code, stdout, stderr = self.ssh.run_command(cmd)

        if exit_code != 0:
            logger.warning(f"Failed to list remote backups: {stderr}")
            return []

        backups = []
        for line in stdout.strip().split('\n'):
            if line.strip():
                parts = line.strip().split(None, 1)
                if len(parts) == 2:
                    size, filename = parts
                    backups.append({
                        'filename': filename,
                        'size': size
                    })

        return backups

    def cleanup_old_backups(
        self,
        bucket: str,
        remote_path: str,
        retention_days: int
    ) -> bool:
        """
        Remove backups older than retention period

        Args:
            bucket: S3 bucket name
            remote_path: Remote path containing backups
            retention_days: Keep backups newer than this many days

        Returns:
            True if cleanup successful
        """
        logger.info(f"Cleaning up backups older than {retention_days} days")

        # Use rclone delete with --min-age filter
        cmd = f"rclone delete {self.rclone_remote_name}:{bucket}/{remote_path} --min-age {retention_days}d"

        exit_code, stdout, stderr = self.ssh.run_command(cmd)

        if exit_code != 0:
            logger.warning(f"Backup cleanup had issues: {stderr}")
            return False

        logger.info("Old backups cleaned up successfully")
        return True

    def download_from_remote(
        self,
        bucket: str,
        remote_file: str,
        local_path: str
    ) -> bool:
        """
        Download backup from remote storage

        Args:
            bucket: S3 bucket name
            remote_file: Remote file path
            local_path: Local destination path

        Returns:
            True if download successful

        Raises:
            RuntimeError: If download fails
        """
        logger.info(f"Downloading backup from remote: {remote_file}")

        cmd = f"rclone copy {self.rclone_remote_name}:{bucket}/{remote_file} {local_path}"

        exit_code, stdout, stderr = self.ssh.run_command(cmd)

        if exit_code != 0:
            raise RuntimeError(f"Download failed: {stderr}")

        logger.info("Backup downloaded successfully from remote")
        return True

    def get_remote_size(self, bucket: str, remote_path: str = "backups") -> str:
        """
        Get total size of remote backups

        Args:
            bucket: S3 bucket name
            remote_path: Remote path to check

        Returns:
            Human-readable size string
        """
        cmd = f"rclone size {self.rclone_remote_name}:{bucket}/{remote_path} --json"
        exit_code, stdout, _ = self.ssh.run_command(cmd)

        if exit_code != 0:
            return "Unknown"

        try:
            data = json.loads(stdout)
            bytes_size = data.get('bytes', 0)

            # Convert to human-readable
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_size < 1024:
                    return f"{bytes_size:.2f} {unit}"
                bytes_size /= 1024

            return f"{bytes_size:.2f} PB"

        except Exception:
            return "Unknown"

    @staticmethod
    def _get_rclone_provider(provider: str) -> str:
        """
        Map provider name to rclone provider string

        Args:
            provider: Provider type (s3, r2, b2, etc.)

        Returns:
            rclone provider string
        """
        provider_map = {
            's3': 'AWS',
            'r2': 'Cloudflare',
            'b2': 'Backblaze',
            'wasabi': 'Wasabi',
            'digitalocean': 'DigitalOcean',
            'minio': 'Minio',
        }

        return provider_map.get(provider.lower(), 'Other')
