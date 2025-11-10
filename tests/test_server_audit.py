"""Unit tests for server security audit components."""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime
import json
from cli.utils.system_auditor import SystemAuditor
from cli.utils.wordpress_auditor import WordPressAuditor
from cli.utils.vulnerability_scanner import VulnerabilityScanner
from cli.utils.audit_report import ReportGenerator
from cli.utils.server_audit import ServerAuditManager


# ============================================================================
# SystemAuditor Tests
# ============================================================================

class TestSystemAuditor:
    """Test SystemAuditor class methods."""

    @pytest.fixture
    def mock_ssh(self):
        """Create mock SSH manager."""
        ssh = Mock()
        return ssh

    @pytest.fixture
    def auditor(self, mock_ssh):
        """Create SystemAuditor instance."""
        return SystemAuditor(mock_ssh)

    def test_audit_ssh_config_secure(self, auditor, mock_ssh):
        """Test SSH config audit with secure configuration."""
        ssh_config = """
Port 2222
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
Protocol 2
"""
        mock_ssh.run_command.return_value = (0, ssh_config, "")

        result = auditor.audit_ssh_config()

        assert 'findings' in result
        assert 'config' in result
        assert len(result['findings']) == 0  # No findings for secure config
        assert result['config']['permitrootlogin'] == 'no'
        assert result['config']['port'] == '2222'

    def test_audit_ssh_config_insecure_root_login(self, auditor, mock_ssh):
        """Test SSH config with root login enabled."""
        ssh_config = "PermitRootLogin yes\nPasswordAuthentication no"
        mock_ssh.run_command.return_value = (0, ssh_config, "")

        result = auditor.audit_ssh_config()

        findings = result['findings']
        assert any(f['id'] == 'SSH-001' for f in findings)
        assert any('Root login enabled' in f['title'] for f in findings)
        assert any(f['severity'] == 'high' for f in findings)

    def test_audit_ssh_config_password_auth_enabled(self, auditor, mock_ssh):
        """Test SSH config with password authentication enabled."""
        ssh_config = "PermitRootLogin no\nPasswordAuthentication yes"
        mock_ssh.run_command.return_value = (0, ssh_config, "")

        result = auditor.audit_ssh_config()

        findings = result['findings']
        assert any(f['id'] == 'SSH-002' for f in findings)
        assert any('Password authentication enabled' in f['title'] for f in findings)

    def test_audit_ssh_config_default_port(self, auditor, mock_ssh):
        """Test SSH config with default port 22."""
        ssh_config = "Port 22\nPermitRootLogin no"
        mock_ssh.run_command.return_value = (0, ssh_config, "")

        result = auditor.audit_ssh_config()

        findings = result['findings']
        assert any(f['id'] == 'SSH-003' for f in findings)
        assert any('Default SSH port' in f['title'] for f in findings)
        assert any(f['severity'] == 'medium' for f in findings)

    def test_audit_ssh_config_protocol_1(self, auditor, mock_ssh):
        """Test SSH config with insecure Protocol 1."""
        ssh_config = "Protocol 1,2\nPermitRootLogin no"
        mock_ssh.run_command.return_value = (0, ssh_config, "")

        result = auditor.audit_ssh_config()

        findings = result['findings']
        assert any(f['id'] == 'SSH-005' for f in findings)
        assert any(f['severity'] == 'critical' for f in findings)

    def test_audit_ssh_config_read_error(self, auditor, mock_ssh):
        """Test SSH config audit when file cannot be read."""
        mock_ssh.run_command.return_value = (1, "", "Permission denied")

        result = auditor.audit_ssh_config()

        assert 'error' in result
        assert result['error'] == 'Cannot read SSH config'

    def test_audit_firewall_active(self, auditor, mock_ssh):
        """Test firewall audit with active UFW."""
        ufw_status = """Status: active
Default: deny (incoming), allow (outgoing)

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
"""
        mock_ssh.run_command.return_value = (0, ufw_status, "")

        result = auditor.audit_firewall()

        assert result['active'] is True
        assert len(result['findings']) == 0  # Active firewall with deny default
        assert len(result['rules']) > 0

    def test_audit_firewall_inactive(self, auditor, mock_ssh):
        """Test firewall audit with inactive UFW."""
        ufw_status = "Status: inactive"
        mock_ssh.run_command.return_value = (0, ufw_status, "")

        result = auditor.audit_firewall()

        findings = result['findings']
        assert any(f['id'] == 'FW-002' for f in findings)
        assert any(f['severity'] == 'critical' for f in findings)

    def test_audit_firewall_not_installed(self, auditor, mock_ssh):
        """Test firewall audit when UFW not installed."""
        mock_ssh.run_command.return_value = (127, "", "ufw: command not found")

        result = auditor.audit_firewall()

        findings = result['findings']
        assert any(f['id'] == 'FW-001' for f in findings)
        assert any('UFW not installed' in f['title'] for f in findings)

    def test_audit_fail2ban_active(self, auditor, mock_ssh):
        """Test fail2ban audit with active service."""
        mock_ssh.run_command.side_effect = [
            (0, "/usr/bin/fail2ban-client", ""),  # which fail2ban-client
            (0, "active", ""),  # systemctl is-active
            (0, "Jail list: sshd, apache-auth", "")  # fail2ban-client status
        ]

        result = auditor.audit_fail2ban()

        assert result['active'] is True
        assert 'sshd' in result['jails']
        assert len(result['findings']) == 0  # No issues

    def test_audit_fail2ban_not_installed(self, auditor, mock_ssh):
        """Test fail2ban audit when not installed."""
        mock_ssh.run_command.return_value = (1, "", "not found")

        result = auditor.audit_fail2ban()

        findings = result['findings']
        assert any(f['id'] == 'F2B-001' for f in findings)
        assert any('fail2ban not installed' in f['title'] for f in findings)

    def test_audit_fail2ban_missing_sshd_jail(self, auditor, mock_ssh):
        """Test fail2ban without sshd jail configured."""
        mock_ssh.run_command.side_effect = [
            (0, "/usr/bin/fail2ban-client", ""),
            (0, "active", ""),
            (0, "Jail list: apache-auth", "")  # No sshd
        ]

        result = auditor.audit_fail2ban()

        findings = result['findings']
        assert any(f['id'] == 'F2B-003' for f in findings)
        assert any('SSH jail not configured' in f['title'] for f in findings)

    def test_audit_open_ports_risky_exposed(self, auditor, mock_ssh):
        """Test open ports audit with risky ports exposed."""
        ss_output = """tcp   LISTEN 0      128          0.0.0.0:22              0.0.0.0:*    users:(("sshd",pid=1234))
tcp   LISTEN 0      80           0.0.0.0:3306            0.0.0.0:*    users:(("mysqld",pid=5678))
tcp   LISTEN 0      128        127.0.0.1:6379            0.0.0.0:*    users:(("redis",pid=9012))
"""
        mock_ssh.run_command.return_value = (0, ss_output, "")

        result = auditor.audit_open_ports()

        findings = result['findings']
        assert len(findings) > 0
        assert any('MySQL' in f['title'] for f in findings)
        assert any(f['severity'] == 'high' for f in findings)

    def test_audit_services_insecure_running(self, auditor, mock_ssh):
        """Test services audit with insecure services."""
        systemctl_output = """telnet.service    loaded active running Telnet
sshd.service      loaded active running SSH Daemon
vsftpd.service    loaded active running FTP Server
"""
        mock_ssh.run_command.return_value = (0, systemctl_output, "")

        result = auditor.audit_services()

        findings = result['findings']
        assert any('telnet' in f['title'].lower() for f in findings)
        assert any('vsftpd' in f['title'].lower() for f in findings)

    def test_audit_users_no_password(self, auditor, mock_ssh):
        """Test user audit with accounts without password."""
        mock_ssh.run_command.side_effect = [
            (0, "user1,user2", ""),  # sudo users
            (0, "user1:x:1000\nuser2:x:1001", ""),  # login users
            (0, "testuser", "")  # users without password
        ]

        result = auditor.audit_users()

        findings = result['findings']
        assert any('testuser' in f['id'] for f in findings)
        assert any('without password' in f['title'] for f in findings)

    def test_audit_updates_security_available(self, auditor, mock_ssh):
        """Test updates audit with security updates available."""
        mock_ssh.run_command.side_effect = [
            (0, "", ""),  # apt-get update
            (0, "15", ""),  # total upgradable
            (0, "5", "")  # security updates
        ]

        result = auditor.audit_updates()

        findings = result['findings']
        assert result['total_updates'] == 15
        assert result['security_updates'] == 5
        assert any(f['id'] == 'UPD-001' for f in findings)
        assert any(f['severity'] == 'high' for f in findings)

    def test_audit_logs_failed_ssh_attempts(self, auditor, mock_ssh):
        """Test log analysis with many failed SSH attempts."""
        mock_ssh.run_command.side_effect = [
            (0, "150", ""),  # Failed SSH attempts
            (0, "sudo command output", "")  # Recent sudo
        ]

        result = auditor.audit_logs()

        findings = result['findings']
        assert result['failed_ssh_attempts'] == 150
        assert any(f['id'] == 'LOG-001' for f in findings)
        assert any('brute-force' in f['impact'] for f in findings)

    def test_audit_filesystem_permissions_incorrect(self, auditor, mock_ssh):
        """Test filesystem permissions with incorrect perms."""
        def mock_stat_command(cmd, *args, **kwargs):
            if '/etc/shadow' in cmd:
                return (0, "644", "")  # Wrong permissions
            return (0, "644", "")

        mock_ssh.run_command.side_effect = mock_stat_command

        result = auditor.audit_filesystem_permissions()

        findings = result['findings']
        assert len(findings) > 0
        assert any('/etc/shadow' in f['title'] for f in findings)

    def test_parse_ssh_config(self, auditor):
        """Test SSH config parsing."""
        config = """Port 2222
PermitRootLogin no
# Comment line
PasswordAuthentication no
"""
        result = auditor._parse_ssh_config(config)

        assert result['port'] == '2222'
        assert result['permitrootlogin'] == 'no'
        assert result['passwordauthentication'] == 'no'

    def test_parse_ufw_rules(self, auditor):
        """Test UFW rules parsing."""
        status = """To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
80/tcp                     DENY        192.168.1.0/24
"""
        result = auditor._parse_ufw_rules(status)

        assert len(result) == 2
        assert result[0]['to'] == '22/tcp'
        assert result[0]['action'] == 'ALLOW'

    def test_parse_ss_output(self, auditor):
        """Test ss output parsing."""
        output = """tcp   LISTEN 0      128        127.0.0.1:3306        0.0.0.0:*    users:(("mysqld",pid=1234))
tcp   LISTEN 0      128          0.0.0.0:80          0.0.0.0:*    users:(("nginx",pid=5678))
"""
        result = auditor._parse_ss_output(output)

        assert len(result) == 2
        assert result[0]['port'] == '3306'
        assert result[0]['address'] == '127.0.0.1'
        assert result[1]['port'] == '80'

    def test_audit_all_comprehensive(self, auditor, mock_ssh):
        """Test audit_all runs all checks."""
        mock_ssh.run_command.return_value = (0, "", "")

        result = auditor.audit_all()

        assert 'ssh' in result
        assert 'firewall' in result
        assert 'fail2ban' in result
        assert 'ports' in result
        assert 'services' in result
        assert 'users' in result
        assert 'updates' in result
        assert 'logs' in result
        assert 'filesystem' in result
        assert 'timestamp' in result


# ============================================================================
# WordPressAuditor Tests
# ============================================================================

class TestWordPressAuditor:
    """Test WordPressAuditor class methods."""

    @pytest.fixture
    def mock_ssh(self):
        """Create mock SSH manager."""
        return Mock()

    @pytest.fixture
    def mock_config(self):
        """Create mock config manager."""
        config = Mock()
        site1 = Mock()
        site1.name = "testsite1"
        site1.domain = "test1.com"
        site1.type = "frankenwp"

        site2 = Mock()
        site2.name = "testsite2"
        site2.domain = "test2.com"
        site2.type = "ols"

        config.get_sites.return_value = [site1, site2]
        config.get_site.return_value = site1
        return config

    @pytest.fixture
    def auditor(self, mock_ssh, mock_config):
        """Create WordPressAuditor instance."""
        return WordPressAuditor(mock_ssh, mock_config)

    def test_audit_site_container_not_running(self, auditor, mock_ssh):
        """Test audit when container is not running."""
        mock_ssh.run_command.return_value = (1, "", "")

        result = auditor.audit_site("testsite", "test.com", "frankenwp")

        assert result['status'] == 'container_not_running'
        assert len(result['findings']) == 1
        assert result['findings'][0]['severity'] == 'high'

    def test_audit_core_version_outdated(self, auditor, mock_ssh):
        """Test WordPress core version audit with outdated version."""
        mock_ssh.run_command.side_effect = [
            (0, "testsite-wp", ""),  # Container check
            (0, "6.2.0", ""),  # WP version
            (0, '[{"version":"6.5.0"}]', "")  # Updates available
        ]

        result = auditor.audit_site("testsite", "test.com", "frankenwp")

        findings = result['findings']
        assert any('outdated' in f['title'].lower() for f in findings)
        assert any(f['severity'] in ['high', 'critical'] for f in findings)

    def test_audit_core_version_critically_outdated(self, auditor, mock_ssh):
        """Test WordPress with critically outdated version."""
        mock_ssh.run_command.side_effect = [
            (0, "testsite-wp", ""),
            (0, "5.8.0", ""),  # Very old version
            (0, "[]", "")
        ]

        result = auditor.audit_site("testsite", "test.com", "frankenwp")

        findings = result['findings']
        assert any('critically outdated' in f['title'].lower() for f in findings)
        assert any(f['severity'] == 'critical' for f in findings)

    def test_audit_file_permissions_insecure_wp_config(self, auditor, mock_ssh):
        """Test file permissions with insecure wp-config.php."""
        mock_ssh.run_command.side_effect = [
            (0, "testsite-wp", ""),  # Container running
            (0, "6.5.0", ""),  # WP version
            (0, "[]", ""),  # No updates
            (0, "644", ""),  # wp-config.php perms - INSECURE
            (0, "755", ""),  # uploads perms
            (0, "define('WP_DEBUG', false);", ""),  # wp-config content
            (0, "[]", ""),  # plugins
            (0, "0", ""),  # plugin updates
            (0, "0", ""),  # theme updates
            (0, "[]", ""),  # themes
            (0, "2", ""),  # admin count
        ]

        result = auditor.audit_site("testsite", "test.com", "frankenwp")

        findings = result['findings']
        assert any('wp-config.php' in f['title'].lower() for f in findings)
        assert any(f['severity'] == 'high' for f in findings)

    def test_audit_wp_config_debug_enabled(self, auditor, mock_ssh):
        """Test wp-config audit with WP_DEBUG enabled."""
        wp_config = "define('WP_DEBUG', true);"
        mock_ssh.run_command.side_effect = [
            (0, "testsite-wp", ""),
            (0, "6.5.0", ""),
            (0, "[]", ""),
            (0, "600", ""),
            (0, "755", ""),
            (0, wp_config, ""),  # wp-config with debug
            (0, "[]", ""),
            (0, "0", ""),
            (0, "0", ""),
            (0, "[]", ""),
            (0, "2", ""),
        ]

        result = auditor.audit_site("testsite", "test.com", "frankenwp")

        findings = result['findings']
        assert any('Debug mode enabled' in f['title'] for f in findings)

    def test_audit_wp_config_default_security_keys(self, auditor, mock_ssh):
        """Test wp-config with default security keys."""
        wp_config = "define('AUTH_KEY', 'put your unique phrase here');"
        mock_ssh.run_command.side_effect = [
            (0, "testsite-wp", ""),
            (0, "6.5.0", ""),
            (0, "[]", ""),
            (0, "600", ""),
            (0, "755", ""),
            (0, wp_config, ""),
            (0, "[]", ""),
            (0, "0", ""),
            (0, "0", ""),
            (0, "[]", ""),
            (0, "2", ""),
        ]

        result = auditor.audit_site("testsite", "test.com", "frankenwp")

        findings = result['findings']
        assert any('Default security keys' in f['title'] for f in findings)
        assert any(f['severity'] == 'critical' for f in findings)

    def test_audit_plugins_many_inactive(self, auditor, mock_ssh):
        """Test plugin audit with many inactive plugins."""
        plugins_json = '[' + ','.join(['{"status":"inactive"}'] * 8) + ']'
        mock_ssh.run_command.side_effect = [
            (0, "testsite-wp", ""),
            (0, "6.5.0", ""),
            (0, "[]", ""),
            (0, "600", ""),
            (0, "755", ""),
            (0, "define('WP_DEBUG', false);", ""),
            (0, plugins_json, ""),  # 8 inactive plugins
            (0, "0", ""),
            (0, "0", ""),
            (0, "[]", ""),
            (0, "2", ""),
        ]

        result = auditor.audit_site("testsite", "test.com", "frankenwp")

        findings = result['findings']
        assert any('inactive plugins' in f['title'].lower() for f in findings)

    def test_audit_plugins_updates_available(self, auditor, mock_ssh):
        """Test plugin audit with updates available."""
        mock_ssh.run_command.side_effect = [
            (0, "testsite-wp", ""),
            (0, "6.5.0", ""),
            (0, "[]", ""),
            (0, "600", ""),
            (0, "755", ""),
            (0, "define('WP_DEBUG', false);", ""),
            (0, "[]", ""),
            (0, "3", ""),  # 3 plugin updates available
            (0, "0", ""),
            (0, "[]", ""),
            (0, "2", ""),
        ]

        result = auditor.audit_site("testsite", "test.com", "frankenwp")

        findings = result['findings']
        assert any('plugin updates' in f['title'].lower() for f in findings)
        assert any(f['severity'] == 'high' for f in findings)

    def test_audit_users_too_many_admins(self, auditor, mock_ssh):
        """Test user audit with too many administrator accounts."""
        mock_ssh.run_command.side_effect = [
            (0, "testsite-wp", ""),
            (0, "6.5.0", ""),
            (0, "[]", ""),
            (0, "600", ""),
            (0, "755", ""),
            (0, "define('WP_DEBUG', false);", ""),
            (0, "[]", ""),
            (0, "0", ""),
            (0, "0", ""),
            (0, "[]", ""),
            (0, "8", ""),  # 8 admin accounts
            (0, "", ""),  # admin user check (not exists)
        ]

        result = auditor.audit_site("testsite", "test.com", "frankenwp")

        findings = result['findings']
        assert any('Too many administrator' in f['title'] for f in findings)

    def test_audit_users_default_admin_username(self, auditor, mock_ssh):
        """Test user audit with default 'admin' username."""
        mock_ssh.run_command.side_effect = [
            (0, "testsite-wp", ""),
            (0, "6.5.0", ""),
            (0, "[]", ""),
            (0, "600", ""),
            (0, "755", ""),
            (0, "define('WP_DEBUG', false);", ""),
            (0, "[]", ""),
            (0, "0", ""),
            (0, "0", ""),
            (0, "[]", ""),
            (0, "2", ""),
            (0, "User ID: 1", ""),  # admin user exists
        ]

        result = auditor.audit_site("testsite", "test.com", "frankenwp")

        findings = result['findings']
        assert any('Default admin username' in f['title'] for f in findings)

    def test_audit_all_sites(self, auditor, mock_ssh, mock_config):
        """Test audit_all_sites runs audit for all configured sites."""
        mock_ssh.run_command.return_value = (1, "", "")  # Containers not running

        result = auditor.audit_all_sites()

        assert result['sites_audited'] == 2
        assert 'testsite1' in result['sites']
        assert 'testsite2' in result['sites']
        assert 'timestamp' in result

    def test_audit_all_sites_no_sites(self, auditor, mock_ssh, mock_config):
        """Test audit_all_sites with no sites configured."""
        mock_config.get_sites.return_value = []

        result = auditor.audit_all_sites()

        assert result['sites_audited'] == 0
        assert len(result['findings']) == 0


# ============================================================================
# VulnerabilityScanner Tests
# ============================================================================

class TestVulnerabilityScanner:
    """Test VulnerabilityScanner class."""

    @pytest.fixture
    def scanner(self):
        """Create VulnerabilityScanner instance."""
        return VulnerabilityScanner(api_token="test_token_123")

    @pytest.fixture
    def scanner_no_token(self):
        """Create VulnerabilityScanner without token."""
        return VulnerabilityScanner()

    def test_init_with_token(self):
        """Test initialization with API token."""
        scanner = VulnerabilityScanner("my_token")
        assert scanner.api_token == "my_token"
        assert scanner._request_count == 0

    def test_init_without_token(self):
        """Test initialization without API token."""
        scanner = VulnerabilityScanner()
        assert scanner.api_token is None

    def test_set_api_token(self, scanner_no_token):
        """Test setting API token after initialization."""
        scanner_no_token.set_api_token("new_token")
        assert scanner_no_token.api_token == "new_token"

    @patch('cli.utils.vulnerability_scanner.requests.get')
    def test_scan_plugin_success(self, mock_get, scanner):
        """Test successful plugin vulnerability scan."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'test-plugin': {
                'latest_version': '2.0.0',
                'popular': True,
                'vulnerabilities': [
                    {
                        'title': 'SQL Injection',
                        'vuln_type': 'sqli',
                        'fixed_in': '1.5.0',
                        'references': {'url': ['https://example.com/vuln1']},
                        'cvss': {'score': 8.5}
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        result = scanner.scan_plugin('test-plugin', '1.0.0')

        assert result['slug'] == 'test-plugin'
        assert result['version'] == '1.0.0'
        assert len(result['vulnerabilities']) == 1
        assert result['vulnerabilities'][0]['title'] == 'SQL Injection'
        assert scanner._request_count == 1

    @patch('cli.utils.vulnerability_scanner.requests.get')
    def test_scan_plugin_not_found(self, mock_get, scanner):
        """Test plugin scan when plugin not found in database."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = scanner.scan_plugin('unknown-plugin', '1.0.0')

        assert result['not_found'] is True
        assert len(result['vulnerabilities']) == 0

    @patch('cli.utils.vulnerability_scanner.requests.get')
    def test_scan_plugin_rate_limited(self, mock_get, scanner):
        """Test plugin scan when API rate limit hit."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        result = scanner.scan_plugin('test-plugin', '1.0.0')

        assert 'error' in result
        assert 'rate limit' in result['error'].lower()

    def test_scan_plugin_no_token(self, scanner_no_token):
        """Test plugin scan without API token."""
        result = scanner_no_token.scan_plugin('test-plugin', '1.0.0')

        assert 'error' in result
        assert 'No API token' in result['error']

    @patch('cli.utils.vulnerability_scanner.requests.get')
    def test_scan_plugin_request_exception(self, mock_get, scanner):
        """Test plugin scan with network error."""
        mock_get.side_effect = Exception("Connection error")

        result = scanner.scan_plugin('test-plugin', '1.0.0')

        assert 'error' in result
        assert 'Request failed' in result['error']

    @patch('cli.utils.vulnerability_scanner.requests.get')
    def test_scan_theme_success(self, mock_get, scanner):
        """Test successful theme vulnerability scan."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'test-theme': {
                'latest_version': '3.0.0',
                'vulnerabilities': [
                    {
                        'title': 'XSS Vulnerability',
                        'vuln_type': 'xss',
                        'fixed_in': '2.5.0',
                        'references': {'url': []},
                        'cvss': {'score': 6.0}
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        result = scanner.scan_theme('test-theme', '2.0.0')

        assert result['slug'] == 'test-theme'
        assert len(result['vulnerabilities']) == 1
        assert result['vulnerabilities'][0]['type'] == 'xss'

    @patch('cli.utils.vulnerability_scanner.requests.get')
    def test_scan_wordpress_core_success(self, mock_get, scanner):
        """Test WordPress core vulnerability scan."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            '6.2.0': {
                'vulnerabilities': [
                    {
                        'title': 'Core XSS',
                        'vuln_type': 'xss',
                        'fixed_in': '6.2.1',
                        'references': {'url': ['https://wpvulndb.com/vuln1']},
                        'cvss': {'score': 7.5}
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        result = scanner.scan_wordpress_core('6.2.0')

        assert result['version'] == '6.2.0'
        assert len(result['vulnerabilities']) == 1

    @patch('cli.utils.vulnerability_scanner.requests.get')
    def test_scan_with_cache(self, mock_get, scanner):
        """Test vulnerability scan uses cache."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'test-plugin': {'vulnerabilities': []}
        }
        mock_get.return_value = mock_response

        # First call
        result1 = scanner.scan_plugin('test-plugin', '1.0.0')
        # Second call should use cache
        result2 = scanner.scan_plugin('test-plugin', '1.0.0')

        assert mock_get.call_count == 1  # Only called once
        assert result1 == result2

    def test_convert_to_findings_with_cvss(self, scanner):
        """Test converting scan results to findings format."""
        scan_result = {
            'slug': 'test-plugin',
            'version': '1.0.0',
            'vulnerabilities': [
                {
                    'title': 'Critical SQL Injection',
                    'cvss': 9.5,
                    'fixed_in': '1.5.0',
                    'references': ['https://example.com']
                },
                {
                    'title': 'Medium XSS',
                    'cvss': 5.0,
                    'fixed_in': '1.3.0',
                    'references': []
                }
            ]
        }

        findings = scanner.convert_to_findings(scan_result, 'mysite', 'plugin')

        assert len(findings) == 2
        assert findings[0]['severity'] == 'critical'  # CVSS 9.5
        assert findings[1]['severity'] == 'medium'  # CVSS 5.0
        assert 'mysite' in findings[0]['id']

    def test_convert_to_findings_no_cvss(self, scanner):
        """Test converting findings without CVSS defaults to high."""
        scan_result = {
            'slug': 'test-plugin',
            'version': '1.0.0',
            'vulnerabilities': [
                {
                    'title': 'Unknown Severity',
                    'fixed_in': '1.5.0',
                    'references': []
                }
            ]
        }

        findings = scanner.convert_to_findings(scan_result, 'mysite', 'plugin')

        assert findings[0]['severity'] == 'high'  # Default

    def test_convert_to_findings_with_error(self, scanner):
        """Test converting findings with error returns empty list."""
        scan_result = {
            'slug': 'test-plugin',
            'error': 'API error'
        }

        findings = scanner.convert_to_findings(scan_result, 'mysite', 'plugin')

        assert len(findings) == 0

    def test_version_compare(self, scanner):
        """Test version comparison logic."""
        assert scanner._version_compare('1.0.0', '2.0.0') == -1
        assert scanner._version_compare('2.0.0', '1.0.0') == 1
        assert scanner._version_compare('1.0.0', '1.0.0') == 0
        assert scanner._version_compare('1.0.1', '1.0.0') == 1
        assert scanner._version_compare('1.10.0', '1.9.0') == 1

    def test_get_request_count(self, scanner):
        """Test request count tracking."""
        assert scanner.get_request_count() == 0
        scanner._request_count = 5
        assert scanner.get_request_count() == 5

    def test_clear_cache(self, scanner):
        """Test cache clearing."""
        scanner._cache = {'key1': 'value1', 'key2': 'value2'}
        scanner.clear_cache()
        assert len(scanner._cache) == 0

    def test_get_cache_stats(self, scanner):
        """Test cache statistics."""
        from datetime import datetime
        scanner._cache = {
            'key1': ('data1', datetime.utcnow()),
            'key2': ('data2', datetime.utcnow())
        }

        stats = scanner.get_cache_stats()

        assert stats['total_entries'] == 2
        assert stats['active_entries'] == 2
        assert stats['expired_entries'] == 0


# ============================================================================
# ReportGenerator Tests
# ============================================================================

class TestReportGenerator:
    """Test ReportGenerator class."""

    @pytest.fixture
    def generator(self):
        """Create ReportGenerator instance."""
        return ReportGenerator()

    @pytest.fixture
    def sample_system_results(self):
        """Sample system audit results."""
        return {
            'ssh': {
                'findings': [
                    {
                        'id': 'SSH-001',
                        'severity': 'high',
                        'title': 'Root login enabled',
                        'description': 'SSH allows root login',
                        'impact': 'Security risk',
                        'remediation': 'Disable root login',
                        'auto_fix': None
                    }
                ]
            },
            'firewall': {
                'findings': []
            },
            'timestamp': '2025-01-10T10:00:00Z'
        }

    @pytest.fixture
    def sample_wordpress_results(self):
        """Sample WordPress audit results."""
        return {
            'sites_audited': 1,
            'findings': [],
            'sites': {
                'testsite': {
                    'site': 'testsite',
                    'status': 'audited',
                    'findings': [
                        {
                            'id': 'WP-TEST-001',
                            'severity': 'medium',
                            'title': 'Debug mode enabled',
                            'description': 'WP_DEBUG is true',
                            'impact': 'Info disclosure',
                            'remediation': 'Set WP_DEBUG to false',
                            'auto_fix': None
                        }
                    ]
                }
            },
            'timestamp': '2025-01-10T10:00:00Z'
        }

    def test_aggregate_findings(self, generator, sample_system_results, sample_wordpress_results):
        """Test aggregating findings from multiple sources."""
        findings = generator._aggregate_findings(sample_system_results, sample_wordpress_results)

        assert len(findings) == 2  # 1 system + 1 wordpress
        assert any(f['id'] == 'SSH-001' for f in findings)
        assert any(f['id'] == 'WP-TEST-001' for f in findings)

    def test_calculate_security_score_perfect(self, generator):
        """Test security score calculation with no findings."""
        findings = []
        score = generator._calculate_security_score(findings)
        assert score == 100

    def test_calculate_security_score_with_findings(self, generator):
        """Test security score with various severity findings."""
        findings = [
            {'severity': 'critical'},  # -10
            {'severity': 'high'},      # -7
            {'severity': 'medium'},    # -4
            {'severity': 'low'}        # -2
        ]
        score = generator._calculate_security_score(findings)
        assert score == 77  # 100 - 23

    def test_calculate_security_score_minimum(self, generator):
        """Test security score doesn't go below 0."""
        findings = [{'severity': 'critical'}] * 20  # -200
        score = generator._calculate_security_score(findings)
        assert score == 0

    def test_group_by_severity(self, generator):
        """Test grouping findings by severity level."""
        findings = [
            {'severity': 'critical', 'id': '1'},
            {'severity': 'high', 'id': '2'},
            {'severity': 'high', 'id': '3'},
            {'severity': 'low', 'id': '4'}
        ]

        grouped = generator._group_by_severity(findings)

        assert len(grouped['critical']) == 1
        assert len(grouped['high']) == 2
        assert len(grouped['medium']) == 0
        assert len(grouped['low']) == 1

    def test_count_severities(self, generator):
        """Test counting findings by severity."""
        findings = [
            {'severity': 'critical'},
            {'severity': 'high'},
            {'severity': 'high'},
            {'severity': 'medium'},
            {'severity': 'low'}
        ]

        counts = generator._count_severities(findings)

        assert counts['critical'] == 1
        assert counts['high'] == 2
        assert counts['medium'] == 1
        assert counts['low'] == 1

    def test_get_score_color(self, generator):
        """Test score color mapping."""
        assert generator._get_score_color(95) == 'green'
        assert generator._get_score_color(80) == 'yellow'
        assert generator._get_score_color(60) == 'orange1'
        assert generator._get_score_color(30) == 'red'

    def test_generate_json_report(self, generator, sample_system_results, sample_wordpress_results, tmp_path):
        """Test JSON report generation."""
        output_path = tmp_path / "report.json"

        path = generator._generate_json_report(
            {
                'timestamp': '2025-01-10T10:00:00Z',
                'security_score': 85,
                'total_findings': 2,
                'severity_counts': {'critical': 0, 'high': 1, 'medium': 1, 'low': 0},
                'findings_by_severity': {},
                'system_results': sample_system_results,
                'wordpress_results': sample_wordpress_results
            },
            str(output_path)
        )

        assert output_path.exists()
        with open(output_path, 'r') as f:
            data = json.load(f)
            assert data['security_score'] == 85
            assert data['total_findings'] == 2


# ============================================================================
# ServerAuditManager Tests
# ============================================================================

class TestServerAuditManager:
    """Test ServerAuditManager orchestration."""

    @pytest.fixture
    def mock_ssh(self):
        """Create mock SSH manager."""
        return Mock()

    @pytest.fixture
    def mock_config(self):
        """Create mock config manager."""
        config = Mock()
        config.get_sites.return_value = []
        return config

    @pytest.fixture
    def manager(self, mock_ssh, mock_config):
        """Create ServerAuditManager instance."""
        return ServerAuditManager(mock_ssh, mock_config)

    def test_init(self, manager):
        """Test initialization of audit manager."""
        assert manager.system_auditor is not None
        assert manager.wp_auditor is not None
        assert manager.report_generator is not None
        assert manager.vuln_scanner is None  # Initialized when needed

    def test_run_full_audit_skip_all(self, manager):
        """Test full audit with all components skipped."""
        with patch.object(manager.system_auditor, 'audit_all') as mock_system:
            mock_system.return_value = {'timestamp': '2025-01-10T10:00:00Z'}

            result = manager.run_full_audit(
                skip_wordpress=True,
                skip_lynis=True
            )

            assert result['wordpress']['skipped'] is True
            assert result['lynis']['skipped'] is True
            assert 'system' in result
            assert 'overall_score' in result

    def test_run_full_audit_comprehensive(self, manager, mock_ssh, mock_config):
        """Test comprehensive full audit."""
        # Mock all audit components
        with patch.object(manager.system_auditor, 'audit_all') as mock_system, \
             patch.object(manager.wp_auditor, 'audit_all_sites') as mock_wp:

            mock_system.return_value = {
                'ssh': {'findings': []},
                'firewall': {'findings': []},
                'timestamp': '2025-01-10T10:00:00Z'
            }
            mock_wp.return_value = {
                'sites_audited': 0,
                'findings': [],
                'sites': {}
            }

            result = manager.run_full_audit(verbose=True)

            assert 'system' in result
            assert 'wordpress' in result
            assert 'overall_score' in result
            assert result['overall_score'] >= 0
            assert result['overall_score'] <= 100

    def test_run_full_audit_with_errors(self, manager):
        """Test full audit handles component errors gracefully."""
        with patch.object(manager.system_auditor, 'audit_all') as mock_system:
            mock_system.side_effect = Exception("System audit failed")

            result = manager.run_full_audit()

            assert len(result['errors']) > 0
            assert result['errors'][0]['component'] == 'system'
            assert 'overall_score' in result

    def test_calculate_overall_score(self, manager):
        """Test overall security score calculation."""
        audit_results = {
            'system': {
                'ssh': {'findings': [{'severity': 'high'}]},
                'firewall': {'findings': []}
            },
            'wordpress': {
                'sites_audited': 0,
                'findings': []
            },
            'vulnerabilities': {'skipped': True},
            'lynis': {'skipped': True}
        }

        score = manager._calculate_overall_score(audit_results)

        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_calculate_system_score(self, manager):
        """Test system score calculation."""
        system_data = {
            'ssh': {'findings': [
                {'severity': 'high'},
                {'severity': 'medium'}
            ]},
            'firewall': {'findings': []},
            'timestamp': '2025-01-10T10:00:00Z'
        }

        score = manager._calculate_system_score(system_data)

        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_calculate_wordpress_score_no_sites(self, manager):
        """Test WordPress score with no sites."""
        wp_data = {'sites_audited': 0, 'findings': []}
        score = manager._calculate_wordpress_score(wp_data)
        assert score == 100

    def test_calculate_wordpress_score_with_findings(self, manager):
        """Test WordPress score with findings."""
        wp_data = {
            'sites_audited': 1,
            'findings': [
                {'severity': 'critical'},
                {'severity': 'high'},
                {'severity': 'medium'}
            ]
        }
        score = manager._calculate_wordpress_score(wp_data)
        assert score < 100

    def test_calculate_vulnerability_score_no_vulns(self, manager):
        """Test vulnerability score with no vulnerabilities."""
        vuln_data = {'total_vulnerabilities': 0}
        score = manager._calculate_vulnerability_score(vuln_data)
        assert score == 100

    def test_calculate_vulnerability_score_with_vulns(self, manager):
        """Test vulnerability score with vulnerabilities."""
        vuln_data = {'total_vulnerabilities': 5}
        score = manager._calculate_vulnerability_score(vuln_data)
        assert score < 100

    def test_parse_csv_output(self, manager):
        """Test CSV parsing from WP-CLI output."""
        csv_output = """name,version,status
akismet,5.0,active
jetpack,12.0,inactive
hello,1.7.2,active
"""
        result = manager._parse_csv_output(csv_output)

        assert len(result) == 3
        assert result[0]['name'] == 'akismet'
        assert result[0]['version'] == '5.0'
        assert result[0]['status'] == 'active'

    def test_parse_csv_output_empty(self, manager):
        """Test CSV parsing with empty output."""
        result = manager._parse_csv_output("")
        assert len(result) == 0

    def test_generate_report(self, manager):
        """Test report generation."""
        audit_results = {
            'timestamp': '2025-01-10T10:00:00Z',
            'overall_score': 85,
            'system': {},
            'wordpress': {},
            'vulnerabilities': {},
            'lynis': {}
        }

        with patch.object(manager.report_generator, 'generate') as mock_gen:
            mock_gen.return_value = "Report content"

            result = manager.generate_report(audit_results, 'console')

            mock_gen.assert_called_once()
            assert result == "Report content"
