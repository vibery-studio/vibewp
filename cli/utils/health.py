"""Health check utilities for VibeWP CLI"""

import time
import requests
from typing import Optional
from requests.exceptions import RequestException


class HealthChecker:
    """Health check utilities for containers and services"""

    def __init__(self, ssh_manager=None):
        """
        Initialize health checker

        Args:
            ssh_manager: Optional SSHManager instance for remote checks
        """
        self.ssh = ssh_manager

    def wait_for_database(
        self,
        container_name: str,
        timeout: int = 60,
        interval: int = 2
    ) -> bool:
        """
        Wait for database container to be ready

        Args:
            container_name: Database container name
            timeout: Maximum wait time in seconds
            interval: Check interval in seconds

        Returns:
            True if database is ready, False if timeout
        """
        if not self.ssh:
            raise RuntimeError("SSH manager required for remote health checks")

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Check if container is running
                exit_code, stdout, stderr = self.ssh.run_command(
                    f"docker inspect -f '{{{{.State.Health.Status}}}}' {container_name}"
                )

                if exit_code == 0:
                    health_status = stdout.strip()

                    # If no healthcheck defined, check if container is running
                    if health_status == "<no value>":
                        exit_code, stdout, stderr = self.ssh.run_command(
                            f"docker inspect -f '{{{{.State.Status}}}}' {container_name}"
                        )
                        if stdout.strip() == "running":
                            # Try to ping database
                            exit_code, _, _ = self.ssh.run_command(
                                f"docker exec {container_name} mysqladmin ping -h localhost --silent"
                            )
                            if exit_code == 0:
                                return True
                    elif health_status == "healthy":
                        return True

            except Exception:
                pass

            time.sleep(interval)

        return False

    def wait_for_container(
        self,
        container_name: str,
        timeout: int = 30,
        interval: int = 2
    ) -> bool:
        """
        Wait for container to be running

        Args:
            container_name: Container name
            timeout: Maximum wait time in seconds
            interval: Check interval in seconds

        Returns:
            True if container is running, False if timeout
        """
        if not self.ssh:
            raise RuntimeError("SSH manager required for remote health checks")

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                exit_code, stdout, stderr = self.ssh.run_command(
                    f"docker inspect -f '{{{{.State.Status}}}}' {container_name}"
                )

                if exit_code == 0 and stdout.strip() == "running":
                    return True

            except Exception:
                pass

            time.sleep(interval)

        return False

    def check_http_response(
        self,
        url: str,
        timeout: int = 30,
        expected_status: int = 200,
        verify_ssl: bool = False
    ) -> bool:
        """
        Check if URL returns expected HTTP status

        Args:
            url: URL to check
            timeout: Request timeout in seconds
            expected_status: Expected HTTP status code
            verify_ssl: Verify SSL certificates

        Returns:
            True if URL returns expected status, False otherwise
        """
        try:
            response = requests.get(
                url,
                timeout=timeout,
                verify=verify_ssl,
                allow_redirects=True
            )
            return response.status_code == expected_status

        except RequestException:
            return False

    def wait_for_http(
        self,
        url: str,
        timeout: int = 60,
        interval: int = 5,
        verify_ssl: bool = False
    ) -> bool:
        """
        Wait for URL to become accessible

        Args:
            url: URL to check
            timeout: Maximum wait time in seconds
            interval: Check interval in seconds
            verify_ssl: Verify SSL certificates

        Returns:
            True if URL becomes accessible, False if timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            if self.check_http_response(url, timeout=10, verify_ssl=verify_ssl):
                return True

            time.sleep(interval)

        return False

    def check_container_health(
        self,
        container_name: str
    ) -> Optional[str]:
        """
        Get container health status

        Args:
            container_name: Container name

        Returns:
            Health status string or None if error
        """
        if not self.ssh:
            raise RuntimeError("SSH manager required for remote health checks")

        try:
            exit_code, stdout, stderr = self.ssh.run_command(
                f"docker inspect -f '{{{{.State.Health.Status}}}}' {container_name}"
            )

            if exit_code == 0:
                health_status = stdout.strip()
                if health_status != "<no value>":
                    return health_status

                # If no health check, return running status
                exit_code, stdout, stderr = self.ssh.run_command(
                    f"docker inspect -f '{{{{.State.Status}}}}' {container_name}"
                )
                return stdout.strip()

        except Exception:
            pass

        return None
