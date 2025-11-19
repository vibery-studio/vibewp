"""Database management utilities for VibeWP"""

import secrets
import string
from typing import Optional
from cli.utils.ssh import SSHManager


class DatabaseManager:
    """Manages database operations for both dedicated and shared modes"""

    def __init__(self, ssh_manager: SSHManager):
        self.ssh = ssh_manager

    def ensure_shared_db_exists(self, root_password: str) -> bool:
        """
        Ensure shared database container exists and is running

        Args:
            root_password: MySQL root password for shared DB

        Returns:
            True if shared DB is ready, False otherwise
        """
        # Check if shared DB container exists
        exit_code, stdout, stderr = self.ssh.run_command(
            "docker ps -a --filter name=vibewp_shared_db --format '{{.Names}}'"
        )

        if exit_code != 0:
            return False

        container_exists = "vibewp_shared_db" in stdout

        if not container_exists:
            # Deploy shared DB
            return self._deploy_shared_db(root_password)

        # Check if container is running
        exit_code, stdout, stderr = self.ssh.run_command(
            "docker ps --filter name=vibewp_shared_db --format '{{.Status}}'"
        )

        if "Up" not in stdout:
            # Start the container
            exit_code, _, _ = self.ssh.run_command(
                "cd /opt/vibewp/shared-db && docker compose up -d"
            )
            return exit_code == 0

        return True

    def _deploy_shared_db(self, root_password: str) -> bool:
        """
        Deploy shared database container

        Args:
            root_password: MySQL root password

        Returns:
            True if deployment successful
        """
        # Create directory
        exit_code, _, _ = self.ssh.run_command("mkdir -p /opt/vibewp/shared-db")
        if exit_code != 0:
            return False

        # Upload docker-compose file
        compose_content = self._get_shared_db_compose(root_password)

        # Write to temp file and upload
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yml') as f:
            f.write(compose_content)
            temp_path = f.name

        try:
            self.ssh.upload_file(temp_path, "/opt/vibewp/shared-db/docker-compose.yml")
        finally:
            os.unlink(temp_path)

        # Deploy
        exit_code, _, _ = self.ssh.run_command(
            "cd /opt/vibewp/shared-db && docker compose up -d",
            timeout=120
        )

        return exit_code == 0

    def _get_shared_db_compose(self, root_password: str) -> str:
        """Get shared DB docker-compose content"""
        return f"""version: '3.8'

services:
  shared_db:
    image: mariadb:10.11
    container_name: vibewp_shared_db
    environment:
      MYSQL_ROOT_PASSWORD: "{root_password}"
      MYSQL_INITDB_SKIP_TZINFO: '1'
    volumes:
      - db_data:/var/lib/mysql
    networks:
      - proxy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    command: >
      --default-authentication-plugin=mysql_native_password
      --max_connections=500
      --innodb_buffer_pool_size=1G
      --innodb_log_file_size=256M
      --innodb_flush_log_at_trx_commit=2
      --innodb_flush_method=O_DIRECT

volumes:
  db_data:
    name: vibewp_shared_db_data

networks:
  proxy:
    external: true
"""

    def create_database_and_user(
        self,
        db_name: str,
        db_user: str,
        db_password: str,
        root_password: str
    ) -> bool:
        """
        Create database and user in shared DB container

        Args:
            db_name: Database name
            db_user: Database username
            db_password: Database password
            root_password: MySQL root password

        Returns:
            True if successful
        """
        # SQL commands to create database and user
        sql_commands = f"""
CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '{db_user}'@'%' IDENTIFIED BY '{db_password}';
GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{db_user}'@'%';
FLUSH PRIVILEGES;
"""

        # Execute SQL via docker exec
        escaped_sql = sql_commands.replace("'", "\\'").replace('"', '\\"')

        exit_code, stdout, stderr = self.ssh.run_command(
            f"docker exec vibewp_shared_db mysql -uroot -p'{root_password}' -e \"{escaped_sql}\"",
            timeout=30
        )

        return exit_code == 0

    def delete_database_and_user(
        self,
        db_name: str,
        db_user: str,
        root_password: str
    ) -> bool:
        """
        Delete database and user from shared DB

        Args:
            db_name: Database name
            db_user: Database username
            root_password: MySQL root password

        Returns:
            True if successful
        """
        sql_commands = f"""
DROP DATABASE IF EXISTS `{db_name}`;
DROP USER IF EXISTS '{db_user}'@'%';
FLUSH PRIVILEGES;
"""

        escaped_sql = sql_commands.replace("'", "\\'").replace('"', '\\"')

        exit_code, _, _ = self.ssh.run_command(
            f"docker exec vibewp_shared_db mysql -uroot -p'{root_password}' -e \"{escaped_sql}\"",
            timeout=30
        )

        return exit_code == 0

    @staticmethod
    def generate_root_password(length: int = 32) -> str:
        """Generate secure MySQL root password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def get_shared_db_root_password(self) -> Optional[str]:
        """
        Get shared DB root password from environment file

        Returns:
            Root password or None if not found
        """
        exit_code, stdout, stderr = self.ssh.run_command(
            "cat /opt/vibewp/shared-db/.env 2>/dev/null || echo ''"
        )

        if exit_code != 0 or not stdout:
            return None

        for line in stdout.split('\n'):
            if line.startswith('MYSQL_ROOT_PASSWORD='):
                return line.split('=', 1)[1].strip()

        return None

    def save_shared_db_root_password(self, password: str) -> bool:
        """
        Save shared DB root password to environment file

        Args:
            password: Root password to save

        Returns:
            True if successful
        """
        env_content = f"MYSQL_ROOT_PASSWORD={password}\n"

        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(env_content)
            temp_path = f.name

        try:
            # Ensure directory exists
            self.ssh.run_command("mkdir -p /opt/vibewp/shared-db")

            # Upload .env file
            self.ssh.upload_file(temp_path, "/opt/vibewp/shared-db/.env")

            # Set permissions
            self.ssh.run_command("chmod 600 /opt/vibewp/shared-db/.env")

            return True
        except Exception:
            return False
        finally:
            os.unlink(temp_path)
