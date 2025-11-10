"""Update manager for VibeWP CLI self-update functionality."""

import os
import sys
import subprocess
import shutil
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
import logging

from cli.utils.github import GitHubClient, GitHubRelease
from cli.utils.version import parse_version, compare_versions
from cli import __version__

logger = logging.getLogger(__name__)


class InstallMethod(Enum):
    """Installation method types."""
    PIP_EDITABLE = "pip_editable"  # pip install -e .
    PIP_PACKAGE = "pip_package"    # pip install vibewp
    SCRIPT_INSTALL = "script"       # install.sh


@dataclass
class UpdateInfo:
    """Update information."""
    current_version: str
    latest_version: str
    update_available: bool
    release: Optional[GitHubRelease]
    install_method: InstallMethod


class UpdateError(Exception):
    """Update operation errors."""
    pass


class UpdateManager:
    """Manages VibeWP CLI updates."""

    def __init__(self):
        """Initialize update manager."""
        self.current_version = __version__
        self.github_client = GitHubClient()
        self.install_method = self._detect_install_method()

    def _detect_install_method(self) -> InstallMethod:
        """
        Detect how VibeWP was installed.

        Returns:
            InstallMethod enum value

        Detection logic:
        1. Check if /opt/vibewp/.git exists (script install)
        2. Check if installed via pip editable mode
        3. Default to pip package install
        """
        # Check for script install (git repo in /opt/vibewp)
        script_install_path = Path("/opt/vibewp/.git")
        if script_install_path.exists():
            logger.debug("Detected script installation method")
            return InstallMethod.SCRIPT_INSTALL

        # Check pip installation method
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", "-f", "vibewp"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                output = result.stdout

                # Check for editable install
                if "Editable project location:" in output or "editable" in output.lower():
                    logger.debug("Detected pip editable installation method")
                    return InstallMethod.PIP_EDITABLE

                logger.debug("Detected pip package installation method")
                return InstallMethod.PIP_PACKAGE

        except (subprocess.SubprocessError, subprocess.TimeoutExpired) as e:
            logger.warning(f"Failed to detect installation method via pip: {e}")

        # Default to pip package
        logger.debug("Defaulting to pip package installation method")
        return InstallMethod.PIP_PACKAGE

    def _get_install_path(self) -> Optional[Path]:
        """
        Get installation path based on install method.

        Returns:
            Path to installation directory or None
        """
        if self.install_method == InstallMethod.SCRIPT_INSTALL:
            return Path("/opt/vibewp")

        # For pip installs, try to get the location
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", "vibewp"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('Location:'):
                        location = line.split(':', 1)[1].strip()
                        return Path(location) / "vibewp"

        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
            pass

        return None

    def check_for_updates(self, include_prerelease: bool = False) -> UpdateInfo:
        """
        Check if updates are available.

        Args:
            include_prerelease: Include pre-release versions

        Returns:
            UpdateInfo object with version comparison

        Raises:
            UpdateError: If update check fails
        """
        try:
            # Get latest release from GitHub
            latest_release = self.github_client.get_latest_release(
                include_prerelease=include_prerelease
            )

            if latest_release is None:
                raise UpdateError("Failed to fetch latest release from GitHub")

            latest_version = latest_release.version

            # Compare versions
            update_available = False
            try:
                comparison = compare_versions(self.current_version, latest_version)
                update_available = comparison < 0  # current < latest
            except ValueError as e:
                logger.error(f"Version comparison failed: {e}")
                raise UpdateError(f"Invalid version format: {e}")

            return UpdateInfo(
                current_version=self.current_version,
                latest_version=latest_version,
                update_available=update_available,
                release=latest_release,
                install_method=self.install_method
            )

        except Exception as e:
            logger.error(f"Update check failed: {e}")
            raise UpdateError(f"Failed to check for updates: {e}")

    def perform_update(self, target_version: Optional[str] = None, force: bool = False) -> bool:
        """
        Perform update based on installation method.

        Args:
            target_version: Specific version to update to (None for latest)
            force: Force reinstall even if same version

        Returns:
            True if update successful, False otherwise

        Raises:
            UpdateError: If update fails
        """
        try:
            if self.install_method == InstallMethod.SCRIPT_INSTALL:
                return self._update_script_install()
            elif self.install_method == InstallMethod.PIP_EDITABLE:
                return self._update_pip_editable()
            else:
                return self._update_pip_package(target_version, force)

        except Exception as e:
            logger.error(f"Update failed: {e}")
            raise UpdateError(f"Update operation failed: {e}")

    def _update_script_install(self) -> bool:
        """
        Update script installation via git pull.

        Returns:
            True if successful
        """
        install_path = Path("/opt/vibewp")

        if not install_path.exists():
            raise UpdateError(f"Installation path not found: {install_path}")

        logger.info("Updating via git pull...")

        # Git pull
        result = subprocess.run(
            ["git", "pull"],
            cwd=install_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            raise UpdateError(f"Git pull failed: {result.stderr}")

        # Reinstall to update dependencies
        logger.info("Reinstalling package...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", "."],
            cwd=install_path,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            raise UpdateError(f"Package reinstall failed: {result.stderr}")

        logger.info("Update completed successfully")
        return True

    def _update_pip_editable(self) -> bool:
        """
        Update pip editable installation.

        Returns:
            True if successful
        """
        install_path = self._get_install_path()

        if install_path is None or not install_path.exists():
            raise UpdateError("Could not determine installation path")

        logger.info("Updating pip editable installation...")

        # If it's a git repo, pull latest
        git_path = install_path.parent / ".git"
        if git_path.exists():
            result = subprocess.run(
                ["git", "pull"],
                cwd=install_path.parent,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.warning(f"Git pull failed: {result.stderr}")

        # Reinstall
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", str(install_path.parent)],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            raise UpdateError(f"Pip reinstall failed: {result.stderr}")

        logger.info("Update completed successfully")
        return True

    def _update_pip_package(self, target_version: Optional[str] = None, force: bool = False) -> bool:
        """
        Update pip package installation.

        Args:
            target_version: Specific version to install
            force: Force reinstall

        Returns:
            True if successful
        """
        logger.info("Updating via pip...")

        cmd = [sys.executable, "-m", "pip", "install", "--upgrade"]

        if force:
            cmd.append("--force-reinstall")

        if target_version:
            cmd.append(f"vibewp=={target_version}")
        else:
            cmd.append("vibewp")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            raise UpdateError(f"Pip upgrade failed: {result.stderr}")

        logger.info("Update completed successfully")
        return True

    def verify_installation(self) -> bool:
        """
        Verify VibeWP installation is working.

        Returns:
            True if installation is valid
        """
        try:
            # Try importing CLI
            import cli.main
            return True
        except ImportError as e:
            logger.error(f"Installation verification failed: {e}")
            return False

    def get_installation_info(self) -> Dict[str, Any]:
        """
        Get detailed installation information.

        Returns:
            Dict with installation details
        """
        return {
            "version": self.current_version,
            "install_method": self.install_method.value,
            "install_path": str(self._get_install_path()) if self._get_install_path() else "unknown",
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "python_executable": sys.executable
        }
