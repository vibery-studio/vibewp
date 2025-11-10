"""Docker management for VibeWP CLI"""

import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
import docker
from docker.errors import DockerException, NotFound, APIError


class DockerManager:
    """Manages Docker operations for VibeWP"""

    def __init__(self):
        """Initialize Docker client"""
        try:
            self.client = docker.from_env()
            # Test connection
            self.client.ping()
        except DockerException as e:
            raise RuntimeError(
                f"Docker daemon not accessible. Is Docker running? Error: {e}"
            )

    def compose_up(
        self,
        compose_file: str,
        project_name: str,
        detach: bool = True,
        build: bool = False
    ) -> subprocess.CompletedProcess:
        """
        Execute docker compose up

        Args:
            compose_file: Path to docker-compose.yml
            project_name: Docker Compose project name
            detach: Run in detached mode
            build: Build images before starting

        Returns:
            CompletedProcess with stdout/stderr
        """
        cmd = [
            "docker", "compose",
            "-f", compose_file,
            "-p", project_name,
            "up"
        ]

        if detach:
            cmd.append("-d")
        if build:
            cmd.append("--build")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            return result
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Docker Compose up failed: {e.stderr}"
            )

    def compose_down(
        self,
        compose_file: str,
        project_name: str,
        remove_volumes: bool = False
    ) -> subprocess.CompletedProcess:
        """
        Execute docker compose down

        Args:
            compose_file: Path to docker-compose.yml
            project_name: Docker Compose project name
            remove_volumes: Remove named volumes

        Returns:
            CompletedProcess with stdout/stderr
        """
        cmd = [
            "docker", "compose",
            "-f", compose_file,
            "-p", project_name,
            "down"
        ]

        if remove_volumes:
            cmd.append("-v")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            return result
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Docker Compose down failed: {e.stderr}"
            )

    def compose_ps(
        self,
        compose_file: str,
        project_name: str
    ) -> List[Dict[str, Any]]:
        """
        Get status of compose project containers

        Args:
            compose_file: Path to docker-compose.yml
            project_name: Docker Compose project name

        Returns:
            List of container info dictionaries
        """
        cmd = [
            "docker", "compose",
            "-f", compose_file,
            "-p", project_name,
            "ps", "--format", "json"
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            # Parse JSON output (one JSON object per line)
            import json
            containers = []
            if result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    if line:
                        containers.append(json.loads(line))
            return containers

        except subprocess.CalledProcessError as e:
            # Empty result if project doesn't exist
            return []

    def list_containers(
        self,
        label: Optional[str] = None,
        all: bool = False
    ) -> List[Any]:
        """
        List Docker containers

        Args:
            label: Filter by label (e.g., "vibewp=true")
            all: Include stopped containers

        Returns:
            List of Container objects
        """
        try:
            filters = {}
            if label:
                filters['label'] = label

            return self.client.containers.list(filters=filters, all=all)

        except APIError as e:
            raise RuntimeError(f"Failed to list containers: {e}")

    def get_container(self, name_or_id: str) -> Optional[Any]:
        """
        Get container by name or ID

        Args:
            name_or_id: Container name or ID

        Returns:
            Container object or None if not found
        """
        try:
            return self.client.containers.get(name_or_id)
        except NotFound:
            return None
        except APIError as e:
            raise RuntimeError(f"Failed to get container: {e}")

    def container_status(self, name_or_id: str) -> str:
        """
        Get container status

        Args:
            name_or_id: Container name or ID

        Returns:
            Status string (running, exited, etc.) or "not_found"
        """
        container = self.get_container(name_or_id)
        if container:
            return container.status
        return "not_found"

    def container_logs(
        self,
        name_or_id: str,
        tail: int = 100,
        follow: bool = False
    ) -> str:
        """
        Get container logs

        Args:
            name_or_id: Container name or ID
            tail: Number of lines to show
            follow: Stream logs

        Returns:
            Log output as string
        """
        container = self.get_container(name_or_id)
        if not container:
            raise ValueError(f"Container not found: {name_or_id}")

        try:
            logs = container.logs(tail=tail, follow=follow)
            if isinstance(logs, bytes):
                return logs.decode('utf-8')
            return logs
        except APIError as e:
            raise RuntimeError(f"Failed to get logs: {e}")

    def network_exists(self, name: str) -> bool:
        """
        Check if Docker network exists

        Args:
            name: Network name

        Returns:
            True if network exists, False otherwise
        """
        try:
            self.client.networks.get(name)
            return True
        except NotFound:
            return False
        except APIError as e:
            raise RuntimeError(f"Failed to check network: {e}")

    def create_network(self, name: str, driver: str = "bridge") -> None:
        """
        Create Docker network

        Args:
            name: Network name
            driver: Network driver (bridge, overlay, etc.)
        """
        try:
            if not self.network_exists(name):
                self.client.networks.create(name, driver=driver)
        except APIError as e:
            raise RuntimeError(f"Failed to create network: {e}")

    def volume_exists(self, name: str) -> bool:
        """
        Check if Docker volume exists

        Args:
            name: Volume name

        Returns:
            True if volume exists, False otherwise
        """
        try:
            self.client.volumes.get(name)
            return True
        except NotFound:
            return False
        except APIError as e:
            raise RuntimeError(f"Failed to check volume: {e}")

    def is_running(self) -> bool:
        """
        Check if Docker daemon is running

        Returns:
            True if Docker is accessible, False otherwise
        """
        try:
            self.client.ping()
            return True
        except:
            return False

    def container_exec(
        self,
        name_or_id: str,
        command: str,
        workdir: Optional[str] = None
    ) -> tuple[int, str]:
        """
        Execute command in running container

        Args:
            name_or_id: Container name or ID
            command: Command to execute
            workdir: Working directory for command

        Returns:
            Tuple of (exit_code, output)
        """
        container = self.get_container(name_or_id)
        if not container:
            raise ValueError(f"Container not found: {name_or_id}")

        try:
            exec_result = container.exec_run(
                command,
                workdir=workdir,
                demux=False
            )
            exit_code = exec_result.exit_code
            output = exec_result.output.decode('utf-8') if isinstance(exec_result.output, bytes) else exec_result.output

            return exit_code, output

        except APIError as e:
            raise RuntimeError(f"Failed to execute command: {e}")

    def container_health(self, name_or_id: str) -> str:
        """
        Get container health status

        Args:
            name_or_id: Container name or ID

        Returns:
            Health status string (healthy, unhealthy, starting, or none)
        """
        container = self.get_container(name_or_id)
        if not container:
            return "not_found"

        try:
            container.reload()
            health = container.attrs.get('State', {}).get('Health', {})

            if not health:
                # No health check defined
                return "none"

            return health.get('Status', 'unknown').lower()

        except APIError as e:
            raise RuntimeError(f"Failed to get container health: {e}")
