"""Backup and restore management utilities"""

import os
from datetime import datetime
from typing import List, Dict, Optional


class BackupManager:
    """Manages site backups and restores"""

    def __init__(self, ssh_manager, base_path: str = "/opt/vibewp"):
        """
        Initialize backup manager

        Args:
            ssh_manager: SSHManager instance
            base_path: Base path for site containers
        """
        self.ssh = ssh_manager
        self.base_path = base_path
        self.backup_dir = f"{base_path}/backups"

        # Ensure backup directory exists
        self._ensure_backup_dir()

    def _ensure_backup_dir(self) -> None:
        """Create backup directory if it doesn't exist"""
        self.ssh.run_command(f"sudo mkdir -p {self.backup_dir}")
        self.ssh.run_command(f"sudo chmod 700 {self.backup_dir}")

    def site_exists(self, site_name: str) -> bool:
        """
        Check if site exists

        Args:
            site_name: Site name

        Returns:
            True if site exists, False otherwise
        """
        site_path = f"{self.base_path}/{site_name}"
        exit_code, _, _ = self.ssh.run_command(f"test -d {site_path}")
        return exit_code == 0

    def create_backup(self, site_name: str, compress: bool = True) -> str:
        """
        Create backup of a site (database + files)

        Args:
            site_name: Site name to backup
            compress: Whether to compress the backup

        Returns:
            Backup ID (timestamp-based)
        """
        if not self.site_exists(site_name):
            raise ValueError(f"Site '{site_name}' does not exist")

        # Generate backup ID
        backup_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_name = f"{site_name}_{backup_id}"
        backup_path = f"{self.backup_dir}/{backup_name}"

        # Create backup directory
        self.ssh.run_command(f"sudo mkdir -p {backup_path}")

        # Backup database
        self._backup_database(site_name, backup_path)

        # Backup WordPress files
        self._backup_files(site_name, backup_path)

        # Compress if requested
        if compress:
            self._compress_backup(backup_path)

        return backup_id

    def _backup_database(self, site_name: str, backup_path: str) -> None:
        """
        Backup MySQL database

        Args:
            site_name: Site name
            backup_path: Backup destination path
        """
        # Export database from MySQL container
        cmd = (
            f"sudo docker exec {site_name}-mysql "
            f"mysqldump -u wordpress -pwordpress wordpress "
            f"> {backup_path}/database.sql"
        )

        exit_code, _, stderr = self.ssh.run_command(cmd)

        if exit_code != 0:
            raise RuntimeError(f"Database backup failed: {stderr}")

    def _backup_files(self, site_name: str, backup_path: str) -> None:
        """
        Backup WordPress files

        Args:
            site_name: Site name
            backup_path: Backup destination path
        """
        site_path = f"{self.base_path}/{site_name}"
        wp_content = f"{site_path}/wordpress"

        # Copy wp-content directory (contains themes, plugins, uploads)
        cmd = f"sudo cp -r {wp_content} {backup_path}/wordpress"
        exit_code, _, stderr = self.ssh.run_command(cmd)

        if exit_code != 0:
            raise RuntimeError(f"File backup failed: {stderr}")

    def _compress_backup(self, backup_path: str) -> None:
        """
        Compress backup directory

        Args:
            backup_path: Path to backup directory
        """
        backup_dir = os.path.dirname(backup_path)
        backup_name = os.path.basename(backup_path)

        # Create tar.gz archive
        cmd = (
            f"cd {backup_dir} && "
            f"sudo tar -czf {backup_name}.tar.gz {backup_name} && "
            f"sudo rm -rf {backup_name}"
        )

        exit_code, _, stderr = self.ssh.run_command(cmd)

        if exit_code != 0:
            raise RuntimeError(f"Backup compression failed: {stderr}")

    def list_backups(self) -> List[Dict[str, str]]:
        """
        List all available backups

        Returns:
            List of backup dictionaries with id, site, date, size
        """
        # List backup files and directories
        exit_code, output, _ = self.ssh.run_command(
            f"sudo ls -lh {self.backup_dir} 2>/dev/null || echo ''"
        )

        if exit_code != 0 or not output.strip():
            return []

        backups = []

        for line in output.split('\n')[1:]:  # Skip 'total' line
            if not line.strip():
                continue

            parts = line.split()
            if len(parts) < 9:
                continue

            # Parse file info
            size = parts[4]
            date = f"{parts[5]} {parts[6]} {parts[7]}"
            name = parts[8]

            # Extract site name and backup ID
            # Format: sitename_YYYYMMDD-HHMMSS or sitename_YYYYMMDD-HHMMSS.tar.gz
            name_clean = name.replace('.tar.gz', '')

            if '_' in name_clean:
                site_name, backup_id = name_clean.rsplit('_', 1)

                backups.append({
                    'id': backup_id,
                    'site': site_name,
                    'date': date,
                    'size': size,
                    'filename': name
                })

        return backups

    def restore_backup(self, site_name: str, backup_id: str) -> None:
        """
        Restore site from backup

        Args:
            site_name: Site name to restore to
            backup_id: Backup ID to restore from
        """
        # Find backup
        backups = self.list_backups()
        backup = None

        for b in backups:
            if b['site'] == site_name and b['id'] == backup_id:
                backup = b
                break

        if not backup:
            raise ValueError(f"Backup not found: {site_name}_{backup_id}")

        backup_filename = backup['filename']
        backup_path = f"{self.backup_dir}/{backup_filename}"

        # Extract if compressed
        if backup_filename.endswith('.tar.gz'):
            backup_path = self._extract_backup(backup_path)

        # Stop site containers
        self._stop_site(site_name)

        # Restore database
        self._restore_database(site_name, backup_path)

        # Restore files
        self._restore_files(site_name, backup_path)

        # Start site containers
        self._start_site(site_name)

    def _extract_backup(self, backup_file: str) -> str:
        """
        Extract compressed backup

        Args:
            backup_file: Path to .tar.gz backup file

        Returns:
            Path to extracted directory
        """
        backup_dir = os.path.dirname(backup_file)

        cmd = f"cd {backup_dir} && sudo tar -xzf {os.path.basename(backup_file)}"
        exit_code, _, stderr = self.ssh.run_command(cmd)

        if exit_code != 0:
            raise RuntimeError(f"Backup extraction failed: {stderr}")

        # Return extracted directory path
        return backup_file.replace('.tar.gz', '')

    def _stop_site(self, site_name: str) -> None:
        """Stop site containers"""
        site_path = f"{self.base_path}/{site_name}"
        self.ssh.run_command(f"cd {site_path} && sudo docker-compose down")

    def _start_site(self, site_name: str) -> None:
        """Start site containers"""
        site_path = f"{self.base_path}/{site_name}"
        self.ssh.run_command(f"cd {site_path} && sudo docker-compose up -d")

    def _restore_database(self, site_name: str, backup_path: str) -> None:
        """
        Restore database from backup

        Args:
            site_name: Site name
            backup_path: Path to backup directory
        """
        db_file = f"{backup_path}/database.sql"

        # Import database into MySQL container
        cmd = (
            f"sudo docker exec -i {site_name}-mysql "
            f"mysql -u wordpress -pwordpress wordpress "
            f"< {db_file}"
        )

        exit_code, _, stderr = self.ssh.run_command(cmd)

        if exit_code != 0:
            raise RuntimeError(f"Database restore failed: {stderr}")

    def _restore_files(self, site_name: str, backup_path: str) -> None:
        """
        Restore WordPress files from backup

        Args:
            site_name: Site name
            backup_path: Path to backup directory
        """
        site_path = f"{self.base_path}/{site_name}"
        wp_backup = f"{backup_path}/wordpress"

        # Remove current files
        self.ssh.run_command(f"sudo rm -rf {site_path}/wordpress")

        # Restore from backup
        cmd = f"sudo cp -r {wp_backup} {site_path}/wordpress"
        exit_code, _, stderr = self.ssh.run_command(cmd)

        if exit_code != 0:
            raise RuntimeError(f"File restore failed: {stderr}")

        # Fix permissions
        self.ssh.run_command(f"sudo chown -R www-data:www-data {site_path}/wordpress")

    def download_backup(self, backup_id: str, site_name: str, local_path: str) -> None:
        """
        Download backup to local machine

        Args:
            backup_id: Backup ID
            site_name: Site name
            local_path: Local destination path
        """
        # Find backup
        backups = self.list_backups()
        backup = None

        for b in backups:
            if b['site'] == site_name and b['id'] == backup_id:
                backup = b
                break

        if not backup:
            raise ValueError(f"Backup not found: {site_name}_{backup_id}")

        remote_file = f"{self.backup_dir}/{backup['filename']}"

        # Download via SFTP
        self.ssh.download_file(remote_file, local_path)

    def get_backup_size(self, site_name: str) -> str:
        """
        Estimate backup size for a site

        Args:
            site_name: Site name

        Returns:
            Human-readable size estimate
        """
        site_path = f"{self.base_path}/{site_name}"

        exit_code, size, _ = self.ssh.run_command(f"sudo du -sh {site_path} | awk '{{print $1}}'")

        if exit_code != 0:
            return "Unknown"

        return size.strip()
