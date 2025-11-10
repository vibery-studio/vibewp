"""SFTP user management with site-specific chroot restrictions"""

import os
import re
from typing import List, Dict, Optional
from pathlib import Path


class SFTPManager:
    """Manages SFTP users with site-specific chroot jails"""

    def __init__(self, ssh_manager, base_path: str = "/opt/vibewp"):
        """
        Initialize SFTP manager

        Args:
            ssh_manager: SSHManager instance
            base_path: Base path for sites on VPS
        """
        self.ssh = ssh_manager
        self.base_path = base_path
        self.sftp_group = "sftpusers"

    def _get_site_wp_content_path(self, site_name: str) -> str:
        """
        Get wp-content path for site (from Docker volume)

        Args:
            site_name: Site name

        Returns:
            Path to wp-content directory
        """
        # Get Docker volume mount point
        container_name = f"{site_name}_wp"
        exit_code, output, stderr = self.ssh.run_command(
            f"docker inspect {container_name} --format '{{{{range .Mounts}}}}{{{{.Source}}}}{{{{end}}}}'"
        )

        if exit_code != 0:
            raise RuntimeError(f"Failed to get volume path: {stderr}")

        volume_path = output.strip()
        if not volume_path:
            raise RuntimeError(f"No volume found for site '{site_name}'")

        # wp-content is in /var/www/html/wp-content inside container
        # which maps to volume_path on host
        return f"{volume_path}/wp-content"

    def _ensure_sftp_group(self) -> None:
        """Ensure sftpusers group exists"""
        exit_code, _, _ = self.ssh.run_command(f"getent group {self.sftp_group}")

        if exit_code != 0:
            # Create group
            exit_code, _, stderr = self.ssh.run_command(
                f"groupadd {self.sftp_group}"
            )
            if exit_code != 0:
                raise RuntimeError(f"Failed to create SFTP group: {stderr}")

    def _get_sftp_username(self, site_name: str, key_identifier: str) -> str:
        """
        Generate SFTP username

        Args:
            site_name: Site name
            key_identifier: Short identifier for the key (e.g., 'john', 'deploy')

        Returns:
            Username in format: sftp_<site>_<identifier>
        """
        # Sanitize identifier (alphanumeric + underscore only)
        safe_identifier = re.sub(r'[^a-z0-9_]', '', key_identifier.lower())
        if not safe_identifier:
            safe_identifier = "user"

        return f"sftp_{site_name}_{safe_identifier}"

    def add_ssh_key(
        self,
        site_name: str,
        public_key: str,
        key_identifier: str = "user"
    ) -> Dict[str, str]:
        """
        Add SFTP user with SSH key for site-specific access

        Args:
            site_name: Site name
            public_key: SSH public key content
            key_identifier: Short identifier for this key

        Returns:
            Dictionary with username, site_name, chroot_path
        """
        # Validate public key format
        if not public_key.strip().startswith(('ssh-rsa', 'ssh-ed25519', 'ecdsa-')):
            raise ValueError("Invalid SSH public key format")

        # Ensure SFTP group exists
        self._ensure_sftp_group()

        # Get site wp-content path
        wp_content_path = self._get_site_wp_content_path(site_name)

        # Generate username
        username = self._get_sftp_username(site_name, key_identifier)

        # Check if user already exists
        exit_code, _, _ = self.ssh.run_command(f"id {username}")
        if exit_code == 0:
            raise ValueError(f"SFTP user '{username}' already exists")

        # Create chroot directory structure
        chroot_base = f"{self.base_path}/sftp/{username}"
        chroot_wp_content = f"{chroot_base}/wp-content"

        commands = [
            # Create user with no shell, home in chroot
            f"useradd -m -d /{username} -s /usr/sbin/nologin -g {self.sftp_group} {username}",

            # Create chroot directory structure (must be owned by root)
            f"mkdir -p {chroot_base}",
            f"chown root:root {chroot_base}",
            f"chmod 755 {chroot_base}",

            # Create user home directory inside chroot
            f"mkdir -p {chroot_base}/{username}",
            f"chown {username}:{self.sftp_group} {chroot_base}/{username}",
            f"chmod 700 {chroot_base}/{username}",

            # Create .ssh directory
            f"mkdir -p {chroot_base}/{username}/.ssh",
            f"chmod 700 {chroot_base}/{username}/.ssh",

            # Add public key
            f"echo '{public_key}' > {chroot_base}/{username}/.ssh/authorized_keys",
            f"chmod 600 {chroot_base}/{username}/.ssh/authorized_keys",
            f"chown -R {username}:{self.sftp_group} {chroot_base}/{username}/.ssh",

            # Create symlink to wp-content (bind mount would be better but complex)
            f"ln -s {wp_content_path} {chroot_wp_content}",

            # Ensure www-data group access for file editing
            f"usermod -aG www-data {username}",

            # Set ACLs on wp-content for write access
            f"setfacl -R -m u:{username}:rwX {wp_content_path}",
            f"setfacl -R -d -m u:{username}:rwX {wp_content_path}",
        ]

        for cmd in commands:
            exit_code, _, stderr = self.ssh.run_command(cmd)
            if exit_code != 0:
                # Cleanup on failure
                self.ssh.run_command(f"userdel -r {username} 2>/dev/null")
                self.ssh.run_command(f"rm -rf {chroot_base} 2>/dev/null")
                raise RuntimeError(f"Failed to setup SFTP user: {stderr}")

        # Update sshd_config
        self._update_sshd_config(username, chroot_base)

        # Reload SSH service
        exit_code, _, stderr = self.ssh.run_command("systemctl reload sshd")
        if exit_code != 0:
            raise RuntimeError(f"Failed to reload SSH service: {stderr}")

        return {
            'username': username,
            'site_name': site_name,
            'chroot_path': chroot_base,
            'wp_content_path': wp_content_path
        }

    def remove_ssh_key(self, site_name: str, key_identifier: str) -> None:
        """
        Remove SFTP user

        Args:
            site_name: Site name
            key_identifier: Key identifier
        """
        username = self._get_sftp_username(site_name, key_identifier)

        # Check if user exists
        exit_code, _, _ = self.ssh.run_command(f"id {username}")
        if exit_code != 0:
            raise ValueError(f"SFTP user '{username}' does not exist")

        # Remove user
        chroot_base = f"{self.base_path}/sftp/{username}"

        commands = [
            f"userdel {username}",
            f"rm -rf {chroot_base}"
        ]

        for cmd in commands:
            exit_code, _, stderr = self.ssh.run_command(cmd)
            if exit_code != 0:
                raise RuntimeError(f"Failed to remove SFTP user: {stderr}")

        # Remove from sshd_config
        self._remove_from_sshd_config(username)

        # Reload SSH service
        exit_code, _, stderr = self.ssh.run_command("systemctl reload sshd")
        if exit_code != 0:
            raise RuntimeError(f"Failed to reload SSH service: {stderr}")

    def list_ssh_keys(self, site_name: Optional[str] = None) -> List[Dict[str, str]]:
        """
        List SFTP users

        Args:
            site_name: Optional site name to filter by

        Returns:
            List of SFTP user dictionaries
        """
        # Get all users in sftpusers group
        exit_code, output, _ = self.ssh.run_command(
            f"getent group {self.sftp_group}"
        )

        if exit_code != 0:
            return []

        # Parse group members
        # Format: sftpusers:x:1001:user1,user2,user3
        parts = output.strip().split(':')
        if len(parts) < 4 or not parts[3]:
            return []

        usernames = parts[3].split(',')

        # Filter by site if specified
        if site_name:
            prefix = f"sftp_{site_name}_"
            usernames = [u for u in usernames if u.startswith(prefix)]

        users = []
        for username in usernames:
            # Parse username: sftp_<site>_<identifier>
            match = re.match(r'sftp_([^_]+)_(.+)', username)
            if not match:
                continue

            site, identifier = match.groups()

            # Get user info
            exit_code, user_info, _ = self.ssh.run_command(
                f"getent passwd {username}"
            )

            if exit_code == 0:
                # Format: username:x:uid:gid:comment:home:shell
                user_parts = user_info.strip().split(':')
                if len(user_parts) >= 6:
                    users.append({
                        'username': username,
                        'site_name': site,
                        'key_identifier': identifier,
                        'uid': user_parts[2],
                        'home': user_parts[5]
                    })

        return users

    def _update_sshd_config(self, username: str, chroot_path: str) -> None:
        """
        Update sshd_config with Match User directive

        Args:
            username: SFTP username
            chroot_path: Chroot directory path
        """
        # Read current sshd_config
        exit_code, config_content, stderr = self.ssh.run_command(
            "cat /etc/ssh/sshd_config"
        )

        if exit_code != 0:
            raise RuntimeError(f"Failed to read sshd_config: {stderr}")

        # Check if Match directive already exists
        if f"Match User {username}" in config_content:
            return  # Already configured

        # Add Match User block at the end
        match_block = f"""
# SFTP chroot for {username}
Match User {username}
    ChrootDirectory {chroot_path}
    ForceCommand internal-sftp
    AllowTcpForwarding no
    X11Forwarding no
"""

        # Write updated config
        updated_config = config_content + match_block

        # Create temp file and upload
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.conf') as tmp:
            tmp.write(updated_config)
            local_temp = tmp.name

        try:
            remote_temp = f"/tmp/sshd_config.{username}"
            self.ssh.upload_file(local_temp, remote_temp)

            # Validate config before applying
            exit_code, _, stderr = self.ssh.run_command(
                f"sshd -t -f {remote_temp}"
            )

            if exit_code != 0:
                raise RuntimeError(f"Invalid sshd_config: {stderr}")

            # Apply config
            exit_code, _, stderr = self.ssh.run_command(
                f"mv {remote_temp} /etc/ssh/sshd_config && chmod 644 /etc/ssh/sshd_config"
            )

            if exit_code != 0:
                raise RuntimeError(f"Failed to update sshd_config: {stderr}")

        finally:
            if os.path.exists(local_temp):
                os.remove(local_temp)

    def _remove_from_sshd_config(self, username: str) -> None:
        """
        Remove Match User directive from sshd_config

        Args:
            username: SFTP username
        """
        # Read current sshd_config
        exit_code, config_content, stderr = self.ssh.run_command(
            "cat /etc/ssh/sshd_config"
        )

        if exit_code != 0:
            raise RuntimeError(f"Failed to read sshd_config: {stderr}")

        # Remove Match User block
        lines = config_content.split('\n')
        filtered_lines = []
        skip_until_next_match = False

        for line in lines:
            if line.strip().startswith(f"Match User {username}"):
                skip_until_next_match = True
                continue
            elif skip_until_next_match:
                # Skip until we find next Match or EOF
                if line.strip().startswith('Match ') or not line.strip().startswith((' ', '\t')):
                    skip_until_next_match = False
                    if line.strip():
                        filtered_lines.append(line)
                continue
            else:
                filtered_lines.append(line)

        updated_config = '\n'.join(filtered_lines)

        # Write updated config
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.conf') as tmp:
            tmp.write(updated_config)
            local_temp = tmp.name

        try:
            remote_temp = f"/tmp/sshd_config.{username}"
            self.ssh.upload_file(local_temp, remote_temp)

            # Apply config
            exit_code, _, stderr = self.ssh.run_command(
                f"mv {remote_temp} /etc/ssh/sshd_config && chmod 644 /etc/ssh/sshd_config"
            )

            if exit_code != 0:
                raise RuntimeError(f"Failed to update sshd_config: {stderr}")

        finally:
            if os.path.exists(local_temp):
                os.remove(local_temp)

    def test_sftp_access(self, username: str) -> Dict[str, any]:
        """
        Test SFTP access for user

        Args:
            username: SFTP username

        Returns:
            Test results dictionary
        """
        # Check if user can authenticate (we can't test this without the private key)
        # Instead, check if the setup is correct

        chroot_base = f"{self.base_path}/sftp/{username}"

        checks = {
            'user_exists': False,
            'chroot_dir_exists': False,
            'authorized_keys_exists': False,
            'sshd_config_match': False
        }

        # Check user exists
        exit_code, _, _ = self.ssh.run_command(f"id {username}")
        checks['user_exists'] = exit_code == 0

        # Check chroot directory
        exit_code, _, _ = self.ssh.run_command(f"test -d {chroot_base}")
        checks['chroot_dir_exists'] = exit_code == 0

        # Check authorized_keys
        exit_code, _, _ = self.ssh.run_command(
            f"test -f {chroot_base}/{username}/.ssh/authorized_keys"
        )
        checks['authorized_keys_exists'] = exit_code == 0

        # Check sshd_config
        exit_code, config, _ = self.ssh.run_command("cat /etc/ssh/sshd_config")
        checks['sshd_config_match'] = f"Match User {username}" in config

        checks['all_passed'] = all(checks.values())

        return checks
