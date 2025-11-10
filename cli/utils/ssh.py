"""SSH management for VibeWP CLI"""

import os
from pathlib import Path
from typing import Optional, Tuple
import paramiko
from paramiko import SSHClient, AutoAddPolicy
from paramiko.ssh_exception import SSHException, AuthenticationException


class SSHManager:
    """Manages SSH connections to VPS"""

    def __init__(self, host: str, port: int, user: str, key_path: str):
        """
        Initialize SSH manager

        Args:
            host: VPS hostname or IP
            port: SSH port
            user: SSH username
            key_path: Path to SSH private key
        """
        self.host = host
        self.port = port
        self.user = user
        self.key_path = Path(key_path).expanduser()
        self.client: Optional[SSHClient] = None

    def connect(self) -> bool:
        """
        Establish SSH connection

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Validate key file exists
            if not self.key_path.exists():
                raise FileNotFoundError(f"SSH key not found: {self.key_path}")

            # Check key file permissions (should be 600)
            key_perms = self.key_path.stat().st_mode & 0o777
            if key_perms not in (0o600, 0o400):
                raise PermissionError(
                    f"SSH key has incorrect permissions: {oct(key_perms)}. "
                    f"Should be 600 or 400"
                )

            # Create SSH client
            self.client = SSHClient()
            self.client.set_missing_host_key_policy(AutoAddPolicy())

            # Connect
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.user,
                key_filename=str(self.key_path),
                timeout=10,
                banner_timeout=10,
                auth_timeout=10
            )

            return True

        except FileNotFoundError as e:
            raise FileNotFoundError(f"SSH connection failed: {e}")
        except AuthenticationException as e:
            raise AuthenticationException(f"SSH authentication failed: {e}")
        except SSHException as e:
            raise SSHException(f"SSH connection error: {e}")
        except Exception as e:
            raise Exception(f"Unexpected SSH error: {e}")

    def disconnect(self) -> None:
        """Close SSH connection"""
        if self.client:
            self.client.close()
            self.client = None

    def run_command(self, command: str, timeout: int = 30) -> Tuple[int, str, str]:
        """
        Execute command on remote VPS

        Args:
            command: Shell command to execute
            timeout: Command timeout in seconds

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        if not self.client:
            raise RuntimeError("SSH not connected. Call connect() first.")

        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
            exit_code = stdout.channel.recv_exit_status()
            stdout_text = stdout.read().decode('utf-8').strip()
            stderr_text = stderr.read().decode('utf-8').strip()

            return exit_code, stdout_text, stderr_text

        except Exception as e:
            raise RuntimeError(f"Command execution failed: {e}")

    def upload_file(self, local_path: str, remote_path: str) -> None:
        """
        Upload file to VPS via SFTP

        Args:
            local_path: Local file path
            remote_path: Remote destination path
        """
        if not self.client:
            raise RuntimeError("SSH not connected. Call connect() first.")

        try:
            sftp = self.client.open_sftp()
            sftp.put(local_path, remote_path)
            sftp.close()

        except Exception as e:
            raise RuntimeError(f"File upload failed: {e}")

    def download_file(self, remote_path: str, local_path: str) -> None:
        """
        Download file from VPS via SFTP

        Args:
            remote_path: Remote file path
            local_path: Local destination path
        """
        if not self.client:
            raise RuntimeError("SSH not connected. Call connect() first.")

        try:
            sftp = self.client.open_sftp()
            sftp.get(remote_path, local_path)
            sftp.close()

        except Exception as e:
            raise RuntimeError(f"File download failed: {e}")

    def file_exists(self, remote_path: str) -> bool:
        """
        Check if file exists on VPS

        Args:
            remote_path: Remote file path

        Returns:
            True if file exists, False otherwise
        """
        if not self.client:
            raise RuntimeError("SSH not connected. Call connect() first.")

        try:
            sftp = self.client.open_sftp()
            try:
                sftp.stat(remote_path)
                return True
            except FileNotFoundError:
                return False
            finally:
                sftp.close()

        except Exception as e:
            raise RuntimeError(f"File check failed: {e}")

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def read_file(self, remote_path: str) -> str:
        """
        Read file content from VPS

        Args:
            remote_path: Remote file path

        Returns:
            File content as string
        """
        if not self.client:
            raise RuntimeError("SSH not connected. Call connect() first.")

        try:
            sftp = self.client.open_sftp()
            try:
                with sftp.open(remote_path, 'r') as f:
                    content = f.read().decode('utf-8')
                return content
            finally:
                sftp.close()

        except Exception as e:
            raise RuntimeError(f"Failed to read file: {e}")

    def write_file(self, remote_path: str, content: str) -> None:
        """
        Write content to file on VPS

        Args:
            remote_path: Remote file path
            content: Content to write
        """
        if not self.client:
            raise RuntimeError("SSH not connected. Call connect() first.")

        try:
            sftp = self.client.open_sftp()
            try:
                with sftp.open(remote_path, 'w') as f:
                    f.write(content.encode('utf-8'))
            finally:
                sftp.close()

        except Exception as e:
            raise RuntimeError(f"Failed to write file: {e}")

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

    @classmethod
    def from_config(cls):
        """
        Create SSHManager instance from VibeWP config

        Returns:
            SSHManager instance
        """
        from cli.utils.config import ConfigManager

        config_mgr = ConfigManager()
        vps_config = config_mgr.vps

        return cls(
            host=vps_config.host,
            port=vps_config.port,
            user=vps_config.user,
            key_path=vps_config.key_path
        )

    def get_current_port(self) -> int:
        """
        Get current SSH port from sshd_config

        Returns:
            Current SSH port number
        """
        exit_code, config, _ = self.run_command("sudo cat /etc/ssh/sshd_config")

        if exit_code != 0:
            return 22  # Default fallback

        for line in config.split('\n'):
            line = line.strip()
            if line.startswith('Port') and not line.startswith('#'):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        return int(parts[1])
                    except ValueError:
                        pass

        return 22  # Default if not found

    def get_ssh_config(self) -> str:
        """
        Get SSH daemon configuration

        Returns:
            Contents of /etc/ssh/sshd_config
        """
        exit_code, config, stderr = self.run_command("sudo cat /etc/ssh/sshd_config")

        if exit_code != 0:
            raise RuntimeError(f"Failed to read SSH config: {stderr}")

        return config

    def update_ssh_config(self, key: str, value: str) -> None:
        """
        Update SSH configuration directive

        Args:
            key: Configuration key (e.g., 'Port', 'PermitRootLogin')
            value: New value
        """
        # Read current config
        config = self.get_ssh_config()

        # Update or add the directive
        lines = config.split('\n')
        found = False
        new_lines = []

        for line in lines:
            stripped = line.strip()

            # Skip commented lines with this key
            if stripped.startswith('#') and stripped[1:].strip().startswith(key):
                new_lines.append(line)
                continue

            # Update existing directive
            if stripped.startswith(key) and not stripped.startswith('#'):
                new_lines.append(f"{key} {value}")
                found = True
            else:
                new_lines.append(line)

        # Add directive if not found
        if not found:
            new_lines.append(f"\n{key} {value}")

        new_config = '\n'.join(new_lines)

        # Write to temporary file
        temp_file = "/tmp/sshd_config.tmp"
        self.run_command(f"cat > {temp_file} << 'EOF'\n{new_config}\nEOF")

        # Backup current config
        self.run_command("sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup")

        # Move temp file to actual config
        self.run_command(f"sudo mv {temp_file} /etc/ssh/sshd_config")

        # Set proper permissions
        self.run_command("sudo chmod 644 /etc/ssh/sshd_config")

    def restart_ssh_service(self) -> None:
        """Restart SSH daemon service"""
        exit_code, _, stderr = self.run_command("sudo systemctl restart sshd")

        if exit_code != 0:
            raise RuntimeError(f"Failed to restart SSH service: {stderr}")

    def test_ssh_connection(self, port: int, timeout: int = 10) -> bool:
        """
        Test SSH connection on specific port

        Args:
            port: Port to test
            timeout: Connection timeout in seconds

        Returns:
            True if connection successful, False otherwise
        """
        import socket

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((self.host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def add_authorized_key(self, public_key: str) -> None:
        """
        Add SSH public key to authorized_keys

        Args:
            public_key: Public key content (full line including type and comment)
        """
        # Ensure .ssh directory exists
        self.run_command("mkdir -p ~/.ssh && chmod 700 ~/.ssh")

        # Check if key already exists
        exit_code, current_keys, _ = self.run_command("cat ~/.ssh/authorized_keys 2>/dev/null || echo ''")

        if public_key in current_keys:
            return  # Key already exists

        # Append key
        cmd = f"echo '{public_key}' >> ~/.ssh/authorized_keys"
        exit_code, _, stderr = self.run_command(cmd)

        if exit_code != 0:
            raise RuntimeError(f"Failed to add SSH key: {stderr}")

        # Set proper permissions
        self.run_command("chmod 600 ~/.ssh/authorized_keys")

    def remove_authorized_key(self, key_pattern: str) -> None:
        """
        Remove SSH key from authorized_keys by pattern

        Args:
            key_pattern: Pattern to match (fingerprint or part of key/comment)
        """
        cmd = f"sed -i '/{key_pattern}/d' ~/.ssh/authorized_keys"
        exit_code, _, stderr = self.run_command(cmd)

        if exit_code != 0:
            raise RuntimeError(f"Failed to remove SSH key: {stderr}")

    def save_new_port(self, port: int) -> None:
        """
        Update local VibeWP config with new SSH port

        Args:
            port: New SSH port number
        """
        from cli.utils.config import ConfigManager
        import yaml

        config_mgr = ConfigManager()

        # Read current config
        with open(config_mgr.config_path, 'r') as f:
            config_data = yaml.safe_load(f)

        # Update port
        if 'vps' not in config_data:
            config_data['vps'] = {}

        config_data['vps']['port'] = port

        # Write back
        with open(config_mgr.config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False)

        # Update instance port
        self.port = port
