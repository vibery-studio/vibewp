"""Tests for update manager."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from cli.utils.update import (
    UpdateManager,
    UpdateInfo,
    UpdateError,
    InstallMethod
)


class TestInstallMethod:
    """Test InstallMethod enum."""

    def test_enum_values(self):
        """Test enum values."""
        assert InstallMethod.PIP_EDITABLE.value == "pip_editable"
        assert InstallMethod.PIP_PACKAGE.value == "pip_package"
        assert InstallMethod.SCRIPT_INSTALL.value == "script"


class TestUpdateManager:
    """Test UpdateManager class."""

    @patch('cli.utils.update.Path.exists')
    def test_detect_script_install(self, mock_exists):
        """Test detecting script installation."""
        mock_exists.return_value = True

        manager = UpdateManager()
        # When /opt/vibewp/.git exists
        assert manager.install_method == InstallMethod.SCRIPT_INSTALL

    @patch('cli.utils.update.Path.exists')
    @patch('cli.utils.update.subprocess.run')
    def test_detect_pip_editable(self, mock_run, mock_exists):
        """Test detecting pip editable installation."""
        mock_exists.return_value = False  # /opt/vibewp/.git doesn't exist

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Editable project location: /some/path"
        mock_run.return_value = mock_result

        manager = UpdateManager()
        assert manager.install_method == InstallMethod.PIP_EDITABLE

    @patch('cli.utils.update.Path.exists')
    @patch('cli.utils.update.subprocess.run')
    def test_detect_pip_package(self, mock_run, mock_exists):
        """Test detecting pip package installation."""
        mock_exists.return_value = False

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Location: /usr/local/lib/python3.9/site-packages"
        mock_run.return_value = mock_result

        manager = UpdateManager()
        assert manager.install_method == InstallMethod.PIP_PACKAGE

    @patch('cli.utils.update.GitHubClient')
    def test_check_for_updates_available(self, mock_github_class):
        """Test checking for updates when update is available."""
        mock_client = Mock()
        mock_release = Mock()
        mock_release.version = "1.1.0"
        mock_client.get_latest_release.return_value = mock_release
        mock_github_class.return_value = mock_client

        manager = UpdateManager()
        manager.current_version = "1.0.0"

        update_info = manager.check_for_updates()

        assert update_info.update_available is True
        assert update_info.current_version == "1.0.0"
        assert update_info.latest_version == "1.1.0"

    @patch('cli.utils.update.GitHubClient')
    def test_check_for_updates_not_available(self, mock_github_class):
        """Test checking for updates when no update available."""
        mock_client = Mock()
        mock_release = Mock()
        mock_release.version = "1.0.0"
        mock_client.get_latest_release.return_value = mock_release
        mock_github_class.return_value = mock_client

        manager = UpdateManager()
        manager.current_version = "1.0.0"

        update_info = manager.check_for_updates()

        assert update_info.update_available is False

    @patch('cli.utils.update.GitHubClient')
    def test_check_for_updates_github_failure(self, mock_github_class):
        """Test handling GitHub API failure."""
        mock_client = Mock()
        mock_client.get_latest_release.return_value = None
        mock_github_class.return_value = mock_client

        manager = UpdateManager()

        with pytest.raises(UpdateError):
            manager.check_for_updates()

    @patch('cli.utils.update.Path')
    @patch('cli.utils.update.subprocess.run')
    def test_update_script_install_success(self, mock_run, mock_path_class):
        """Test successful script installation update."""
        # Mock Path for __init__ detection
        mock_git_path = Mock()
        mock_git_path.exists.return_value = False

        # Mock Path for _update_script_install
        mock_install_path = Mock()
        mock_install_path.exists.return_value = True

        mock_path_class.return_value = mock_install_path
        mock_path_class.side_effect = [mock_git_path, mock_install_path]

        # Mock for __init__ detection
        init_result = Mock()
        init_result.returncode = 0
        init_result.stdout = "Location: /usr/local/lib/python3.9/site-packages"

        # Mock for actual update
        update_result = Mock()
        update_result.returncode = 0
        update_result.stderr = ""

        mock_run.side_effect = [init_result, update_result, update_result]

        manager = UpdateManager()
        manager.install_method = InstallMethod.SCRIPT_INSTALL

        # Mock path exists for update
        with patch('cli.utils.update.Path') as mock_update_path:
            mock_update_path.return_value.exists.return_value = True
            success = manager._update_script_install()
            assert success is True

    @patch('cli.utils.update.subprocess.run')
    def test_update_script_install_git_failure(self, mock_run):
        """Test script installation update with git pull failure."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Git pull failed"
        mock_run.return_value = mock_result

        manager = UpdateManager()
        manager.install_method = InstallMethod.SCRIPT_INSTALL

        with pytest.raises(UpdateError):
            manager._update_script_install()

    @patch('cli.utils.update.Path.exists')
    @patch('cli.utils.update.subprocess.run')
    def test_update_pip_package_success(self, mock_run, mock_exists):
        """Test successful pip package update."""
        mock_exists.return_value = False  # Mock for __init__

        # Mock for __init__ detection
        init_result = Mock()
        init_result.returncode = 0
        init_result.stdout = "Location: /usr/local/lib/python3.9/site-packages"

        # Mock for actual update
        update_result = Mock()
        update_result.returncode = 0
        update_result.stderr = ""

        mock_run.side_effect = [init_result, update_result]

        manager = UpdateManager()
        manager.install_method = InstallMethod.PIP_PACKAGE

        success = manager._update_pip_package()
        assert success is True

    @patch('cli.utils.update.Path.exists')
    @patch('cli.utils.update.subprocess.run')
    def test_update_pip_package_with_version(self, mock_run, mock_exists):
        """Test pip package update to specific version."""
        mock_exists.return_value = False  # Mock for __init__

        # Mock for __init__ detection
        init_result = Mock()
        init_result.returncode = 0
        init_result.stdout = "Location: /usr/local/lib/python3.9/site-packages"

        # Mock for actual update
        update_result = Mock()
        update_result.returncode = 0
        update_result.stderr = ""

        mock_run.side_effect = [init_result, update_result]

        manager = UpdateManager()
        manager.install_method = InstallMethod.PIP_PACKAGE

        success = manager._update_pip_package(target_version="1.2.0")
        assert success is True

        # Verify correct command was called
        call_args = mock_run.call_args[0][0]
        assert "vibewp==1.2.0" in call_args

    @patch('cli.utils.update.Path.exists')
    @patch('cli.utils.update.subprocess.run')
    def test_update_pip_package_force_reinstall(self, mock_run, mock_exists):
        """Test pip package force reinstall."""
        mock_exists.return_value = False  # Mock for __init__

        # Mock for __init__ detection
        init_result = Mock()
        init_result.returncode = 0
        init_result.stdout = "Location: /usr/local/lib/python3.9/site-packages"

        # Mock for actual update
        update_result = Mock()
        update_result.returncode = 0
        update_result.stderr = ""

        mock_run.side_effect = [init_result, update_result]

        manager = UpdateManager()
        manager.install_method = InstallMethod.PIP_PACKAGE

        success = manager._update_pip_package(force=True)
        assert success is True

        # Verify --force-reinstall flag was used
        call_args = mock_run.call_args[0][0]
        assert "--force-reinstall" in call_args

    def test_verify_installation_success(self):
        """Test installation verification success."""
        manager = UpdateManager()
        # cli.main should be importable in test environment
        verified = manager.verify_installation()
        assert verified is True

    @patch('cli.utils.update.subprocess.run')
    def test_get_installation_info(self, mock_run):
        """Test getting installation information."""
        manager = UpdateManager()
        manager.install_method = InstallMethod.PIP_PACKAGE

        info = manager.get_installation_info()

        assert 'version' in info
        assert 'install_method' in info
        assert 'python_version' in info
        assert info['install_method'] == 'pip_package'


class TestUpdateInfo:
    """Test UpdateInfo data class."""

    def test_update_info_creation(self):
        """Test creating UpdateInfo."""
        info = UpdateInfo(
            current_version="1.0.0",
            latest_version="1.1.0",
            update_available=True,
            release=None,
            install_method=InstallMethod.PIP_PACKAGE
        )

        assert info.current_version == "1.0.0"
        assert info.latest_version == "1.1.0"
        assert info.update_available is True
        assert info.install_method == InstallMethod.PIP_PACKAGE
