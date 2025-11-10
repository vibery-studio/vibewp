"""Integration tests for server security audit workflow."""

import pytest
from unittest.mock import Mock, MagicMock, patch
import json
import tempfile
from pathlib import Path
from cli.utils.server_audit import ServerAuditManager
from cli.utils.system_auditor import SystemAuditor
from cli.utils.wordpress_auditor import WordPressAuditor
from cli.utils.vulnerability_scanner import VulnerabilityScanner
from cli.utils.audit_report import ReportGenerator


class TestAuditIntegration:
    """Integration tests for full audit workflow."""

    @pytest.fixture
    def mock_ssh_comprehensive(self):
        """Create comprehensive mock SSH with realistic responses."""
        ssh = Mock()

        def command_handler(cmd, *args, **kwargs):
            """Handle different SSH commands with realistic responses."""
            # SSH config
            if 'sshd_config' in cmd:
                return (0, """Port 2222
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
Protocol 2
""", "")

            # UFW status
            if 'ufw status' in cmd:
                return (0, """Status: active
Default: deny (incoming), allow (outgoing), deny (routed)

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
""", "")

            # fail2ban check
            if 'which fail2ban-client' in cmd:
                return (0, "/usr/bin/fail2ban-client", "")
            if 'is-active fail2ban' in cmd:
                return (0, "active", "")
            if 'fail2ban-client status' in cmd:
                return (0, "Jail list: sshd, apache-auth", "")

            # Open ports
            if 'ss -tulnp' in cmd:
                return (0, """tcp   LISTEN 0      128        0.0.0.0:22        0.0.0.0:*    users:(("sshd",pid=1234))
tcp   LISTEN 0      128        0.0.0.0:80        0.0.0.0:*    users:(("nginx",pid=5678))
tcp   LISTEN 0      128      127.0.0.1:3306      0.0.0.0:*    users:(("mysqld",pid=9012))
""", "")

            # Services
            if 'systemctl list-units' in cmd:
                return (0, """sshd.service    loaded active running OpenSSH server
nginx.service   loaded active running Nginx web server
docker.service  loaded active running Docker daemon
""", "")

            # Users
            if 'grep -Po' in cmd and '/etc/group' in cmd:
                return (0, "user1,user2", "")
            if 'getent passwd' in cmd:
                return (0, "user1:x:1000:1000::/home/user1:/bin/bash", "")
            if '/etc/shadow' in cmd and 'awk' in cmd:
                return (0, "", "")  # No users without password

            # Updates
            if 'apt-get update' in cmd:
                return (0, "", "")
            if 'apt list --upgradable' in cmd and 'wc -l' in cmd:
                return (0, "5", "")
            if 'apt list --upgradable' in cmd and 'grep -i security' in cmd:
                return (0, "2", "")

            # Logs
            if 'Failed password' in cmd:
                return (0, "15", "")
            if 'grep sudo' in cmd:
                return (0, "Jan 10 user1 sudo command", "")

            # File permissions
            if 'stat -c' in cmd:
                if '/etc/shadow' in cmd:
                    return (0, "640", "")
                return (0, "644", "")

            # Docker container check
            if 'docker ps --filter' in cmd:
                return (0, "testsite-wp", "")

            # WordPress checks
            if 'wp core version' in cmd:
                return (0, "6.4.0", "")
            if 'wp core check-update' in cmd:
                return (0, "[]", "")  # No updates
            if 'wp-config.php' in cmd and 'stat' in cmd:
                return (0, "600", "")
            if 'uploads' in cmd and 'stat' in cmd:
                return (0, "755", "")
            if 'cat' in cmd and 'wp-config.php' in cmd:
                return (0, """define('DB_NAME', 'wordpress');
define('AUTH_KEY', 'unique-key-here');
define('WP_DEBUG', false);
""", "")
            if 'wp plugin list' in cmd:
                if '--format=json' in cmd:
                    return (0, '[{"name":"akismet","version":"5.0","status":"active"}]', "")
                if '--format=count' in cmd:
                    return (0, "0", "")  # No updates
                if '--format=csv' in cmd:
                    return (0, "name,version,status\nakismet,5.0,active", "")
            if 'wp theme list' in cmd:
                if '--format=count' in cmd:
                    return (0, "0", "")
                if '--format=json' in cmd:
                    return (0, '[{"name":"twentytwentyfour","status":"active"}]', "")
                if '--format=csv' in cmd:
                    return (0, "name,version,status\ntwentytwentyfour,1.0,active", "")
            if 'wp user list' in cmd:
                if '--role=administrator' in cmd:
                    return (0, "2", "")
            if 'wp user get admin' in cmd:
                return (1, "", "")  # admin user doesn't exist

            # Lynis
            if 'which lynis' in cmd:
                return (1, "", "")  # Not installed

            # Default
            return (0, "", "")

        ssh.run_command.side_effect = command_handler
        return ssh

    @pytest.fixture
    def mock_config_with_sites(self):
        """Create mock config with test sites."""
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
        config.get_wpscan_token.return_value = None

        return config

    def test_full_audit_workflow_end_to_end(self, mock_ssh_comprehensive, mock_config_with_sites):
        """Test complete audit workflow from start to finish."""
        # Initialize manager
        manager = ServerAuditManager(mock_ssh_comprehensive, mock_config_with_sites)

        # Run full audit
        results = manager.run_full_audit(
            skip_wordpress=False,
            skip_lynis=True,
            wpscan_api_token=None,
            verbose=False
        )

        # Verify structure
        assert 'timestamp' in results
        assert 'overall_score' in results
        assert 'system' in results
        assert 'wordpress' in results
        assert 'vulnerabilities' in results
        assert 'lynis' in results

        # Verify system audit ran
        assert 'ssh' in results['system']
        assert 'firewall' in results['system']
        assert 'fail2ban' in results['system']

        # Verify WordPress audit ran
        assert results['wordpress']['sites_audited'] == 2
        assert 'testsite1' in results['wordpress']['sites']
        assert 'testsite2' in results['wordpress']['sites']

        # Verify vulnerability scan was skipped (no token)
        assert results['vulnerabilities']['skipped'] is True

        # Verify score is valid
        assert 0 <= results['overall_score'] <= 100

    def test_full_audit_with_vulnerability_scanning(self, mock_ssh_comprehensive, mock_config_with_sites):
        """Test audit workflow with vulnerability scanning enabled."""
        manager = ServerAuditManager(mock_ssh_comprehensive, mock_config_with_sites)

        # Mock WPScan API responses
        with patch('cli.utils.vulnerability_scanner.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'akismet': {
                    'latest_version': '5.0',
                    'vulnerabilities': []
                }
            }
            mock_get.return_value = mock_response

            results = manager.run_full_audit(
                skip_wordpress=False,
                wpscan_api_token='test_token_123',
                verbose=False
            )

            # Verify vulnerability scan ran
            assert 'vulnerabilities' in results
            assert not results['vulnerabilities'].get('skipped', False)
            assert 'sites' in results['vulnerabilities']

    def test_audit_error_handling_ssh_failure(self, mock_config_with_sites):
        """Test audit handles SSH connection failures gracefully."""
        mock_ssh = Mock()
        mock_ssh.run_command.side_effect = Exception("Connection refused")

        manager = ServerAuditManager(mock_ssh, mock_config_with_sites)

        results = manager.run_full_audit(verbose=False)

        # Should have errors but not crash
        assert len(results['errors']) > 0
        assert 'overall_score' in results

    def test_audit_error_handling_partial_failure(self, mock_ssh_comprehensive, mock_config_with_sites):
        """Test audit continues when one component fails."""
        # Make WordPress audit fail
        def selective_failure(cmd, *args, **kwargs):
            if 'docker ps' in cmd:
                raise Exception("Docker connection failed")
            # Default SSH responses for system audit
            if 'sshd_config' in cmd:
                return (0, "PermitRootLogin no", "")
            return (0, "", "")

        mock_ssh_comprehensive.run_command.side_effect = selective_failure

        manager = ServerAuditManager(mock_ssh_comprehensive, mock_config_with_sites)
        results = manager.run_full_audit(verbose=False)

        # System audit should complete
        assert 'system' in results
        # WordPress audit should have error
        assert len(results['errors']) > 0 or 'wordpress' in results

    def test_audit_with_skip_options(self, mock_ssh_comprehensive, mock_config_with_sites):
        """Test audit respects skip flags."""
        manager = ServerAuditManager(mock_ssh_comprehensive, mock_config_with_sites)

        results = manager.run_full_audit(
            skip_wordpress=True,
            skip_lynis=True,
            verbose=False
        )

        assert results['wordpress']['skipped'] is True
        assert results['lynis']['skipped'] is True
        assert 'system' in results  # System should still run

    def test_report_generation_all_formats(self, mock_ssh_comprehensive, mock_config_with_sites):
        """Test report generation in all supported formats."""
        manager = ServerAuditManager(mock_ssh_comprehensive, mock_config_with_sites)

        # Run audit
        results = manager.run_full_audit(verbose=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Test JSON format
            json_path = Path(tmpdir) / "audit.json"
            json_report = manager.generate_report(results, 'json')
            manager.save_report(json_report, str(json_path), 'json')
            assert json_path.exists()

            # Verify JSON is valid
            with open(json_path, 'r') as f:
                json_data = json.load(f)
                assert 'security_score' in json_data
                assert 'timestamp' in json_data

            # Test console format (doesn't save to file)
            console_report = manager.generate_report(results, 'console')
            assert console_report is not None or console_report == ""  # Console may print directly

    def test_audit_performance_under_5_minutes(self, mock_ssh_comprehensive, mock_config_with_sites):
        """Test audit completes in reasonable time (simulated)."""
        import time

        manager = ServerAuditManager(mock_ssh_comprehensive, mock_config_with_sites)

        start_time = time.time()
        results = manager.run_full_audit(verbose=False)
        elapsed = time.time() - start_time

        # With mocks, should complete very quickly
        assert elapsed < 5.0  # Should be much faster with mocks
        assert 'overall_score' in results

    def test_audit_data_consistency(self, mock_ssh_comprehensive, mock_config_with_sites):
        """Test audit results are consistent across multiple runs."""
        manager = ServerAuditManager(mock_ssh_comprehensive, mock_config_with_sites)

        # Run audit twice
        results1 = manager.run_full_audit(verbose=False)
        results2 = manager.run_full_audit(verbose=False)

        # Scores should be consistent (same mock data)
        assert results1['overall_score'] == results2['overall_score']

        # Structure should be identical
        assert results1.keys() == results2.keys()

    def test_audit_findings_categorization(self, mock_ssh_comprehensive, mock_config_with_sites):
        """Test findings are properly categorized by severity."""
        manager = ServerAuditManager(mock_ssh_comprehensive, mock_config_with_sites)
        results = manager.run_full_audit(verbose=False)

        # Collect all findings
        all_findings = []

        # System findings
        for category_data in results['system'].values():
            if isinstance(category_data, dict) and 'findings' in category_data:
                all_findings.extend(category_data['findings'])

        # WordPress findings
        if 'sites' in results.get('wordpress', {}):
            for site_data in results['wordpress']['sites'].values():
                if 'findings' in site_data:
                    all_findings.extend(site_data['findings'])

        # Verify all findings have required fields
        for finding in all_findings:
            assert 'id' in finding
            assert 'severity' in finding
            assert finding['severity'] in ['critical', 'high', 'medium', 'low']
            assert 'title' in finding
            assert 'description' in finding
            assert 'impact' in finding
            assert 'remediation' in finding

    def test_audit_with_insecure_system(self, mock_config_with_sites):
        """Test audit on intentionally insecure system configuration."""
        # Create mock SSH with insecure responses
        mock_ssh = Mock()

        def insecure_command_handler(cmd, *args, **kwargs):
            if 'sshd_config' in cmd:
                return (0, """Port 22
PermitRootLogin yes
PasswordAuthentication yes
Protocol 1,2
""", "")
            if 'ufw status' in cmd:
                return (0, "Status: inactive", "")
            if 'which fail2ban' in cmd:
                return (1, "", "not found")
            if 'apt list --upgradable' in cmd and 'wc -l' in cmd:
                return (0, "50", "")  # Many updates
            if 'apt list --upgradable' in cmd and 'grep -i security' in cmd:
                return (0, "15", "")  # Many security updates
            if 'Failed password' in cmd:
                return (0, "500", "")  # Many failed attempts
            if '/etc/shadow' in cmd and 'stat' in cmd:
                return (0, "644", "")  # Wrong permissions
            if 'docker ps' in cmd:
                return (0, "", "")  # No containers
            return (0, "", "")

        mock_ssh.run_command.side_effect = insecure_command_handler

        manager = ServerAuditManager(mock_ssh, mock_config_with_sites)
        results = manager.run_full_audit(skip_wordpress=True, verbose=False)

        # Should have many findings
        total_findings = sum(
            len(data.get('findings', []))
            for data in results['system'].values()
            if isinstance(data, dict)
        )

        assert total_findings > 5  # Expect multiple security issues

        # Score should be low
        assert results['overall_score'] < 50

    def test_audit_export_format_validation(self, mock_ssh_comprehensive, mock_config_with_sites):
        """Test exported reports are valid in their respective formats."""
        manager = ServerAuditManager(mock_ssh_comprehensive, mock_config_with_sites)
        results = manager.run_full_audit(verbose=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            # JSON validation
            json_path = Path(tmpdir) / "audit.json"
            json_report = manager.generate_report(results, 'json')
            manager.save_report(json_report, str(json_path), 'json')

            with open(json_path, 'r') as f:
                data = json.load(f)
                # Validate required fields
                assert 'timestamp' in data
                assert 'security_score' in data
                assert 'severity_counts' in data
                assert isinstance(data['security_score'], int)
                assert 0 <= data['security_score'] <= 100

    def test_graceful_degradation_no_wordpress_sites(self, mock_ssh_comprehensive):
        """Test audit works gracefully with no WordPress sites configured."""
        mock_config = Mock()
        mock_config.get_sites.return_value = []
        mock_config.get_wpscan_token.return_value = None

        manager = ServerAuditManager(mock_ssh_comprehensive, mock_config)
        results = manager.run_full_audit(verbose=False)

        # System audit should still work
        assert 'system' in results
        assert results['wordpress']['sites_audited'] == 0
        # Score should still be calculated
        assert 'overall_score' in results

    def test_vulnerability_scan_rate_limiting(self, mock_ssh_comprehensive, mock_config_with_sites):
        """Test vulnerability scanner respects rate limiting."""
        # Create site with many plugins
        mock_config = Mock()
        site = Mock()
        site.name = "testsite"
        site.domain = "test.com"
        site.type = "frankenwp"
        mock_config.get_sites.return_value = [site]

        # Mock WP-CLI to return many plugins
        def plugin_command_handler(cmd, *args, **kwargs):
            if 'docker ps' in cmd:
                return (0, "testsite-wp", "")
            if 'wp plugin list' in cmd and '--format=csv' in cmd:
                # Return 20 plugins
                plugins = ["name,version,status\n"]
                for i in range(20):
                    plugins.append(f"plugin{i},1.0.0,active\n")
                return (0, "".join(plugins), "")
            # Other commands
            if 'wp core version' in cmd:
                return (0, "6.4.0", "")
            if 'wp theme list' in cmd and '--format=csv' in cmd:
                return (0, "name,version,status\ntwentyfour,1.0,active", "")
            return (0, "", "")

        ssh = Mock()
        ssh.run_command.side_effect = plugin_command_handler

        manager = ServerAuditManager(ssh, mock_config)

        with patch('cli.utils.vulnerability_scanner.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'plugin0': {'vulnerabilities': []}}
            mock_get.return_value = mock_response

            results = manager.run_full_audit(
                wpscan_api_token='test_token',
                verbose=False
            )

            # Should limit scan to first 10 plugins (check implementation)
            # Verify rate limiting happened (check call count)
            assert mock_get.call_count <= 12  # 1 core + 10 plugins + 1 theme = max 12

    def test_concurrent_site_audits(self, mock_ssh_comprehensive):
        """Test auditing multiple sites doesn't cause conflicts."""
        # Create config with many sites
        mock_config = Mock()
        sites = []
        for i in range(5):
            site = Mock()
            site.name = f"site{i}"
            site.domain = f"site{i}.com"
            site.type = "frankenwp"
            sites.append(site)
        mock_config.get_sites.return_value = sites

        manager = ServerAuditManager(mock_ssh_comprehensive, mock_config)
        results = manager.run_full_audit(verbose=False)

        # All sites should be audited
        assert results['wordpress']['sites_audited'] == 5
        assert len(results['wordpress']['sites']) == 5

    def test_error_recovery_and_reporting(self, mock_config_with_sites):
        """Test system recovers from errors and reports them properly."""
        mock_ssh = Mock()
        call_count = [0]

        def intermittent_failure(cmd, *args, **kwargs):
            call_count[0] += 1
            # Fail every 3rd call
            if call_count[0] % 3 == 0:
                raise Exception("Intermittent error")
            return (0, "", "")

        mock_ssh.run_command.side_effect = intermittent_failure

        manager = ServerAuditManager(mock_ssh, mock_config_with_sites)
        results = manager.run_full_audit(verbose=False)

        # Should have errors but complete
        assert 'errors' in results
        assert 'overall_score' in results

    def test_audit_timestamp_consistency(self, mock_ssh_comprehensive, mock_config_with_sites):
        """Test timestamps are consistent and properly formatted."""
        manager = ServerAuditManager(mock_ssh_comprehensive, mock_config_with_sites)
        results = manager.run_full_audit(verbose=False)

        # Main timestamp
        assert 'timestamp' in results
        assert results['timestamp'].endswith('Z')  # UTC format

        # Component timestamps
        if 'timestamp' in results.get('system', {}):
            assert results['system']['timestamp'].endswith('Z')

        if 'timestamp' in results.get('wordpress', {}):
            assert results['wordpress']['timestamp'].endswith('Z')


class TestAuditEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_ssh_responses(self):
        """Test handling of empty SSH command responses."""
        mock_ssh = Mock()
        mock_ssh.run_command.return_value = (0, "", "")

        mock_config = Mock()
        mock_config.get_sites.return_value = []

        manager = ServerAuditManager(mock_ssh, mock_config)
        results = manager.run_full_audit(verbose=False)

        # Should complete without crashing
        assert 'overall_score' in results

    def test_malformed_ssh_responses(self):
        """Test handling of malformed SSH responses."""
        mock_ssh = Mock()
        mock_ssh.run_command.return_value = (0, "malformed data !@#$%", "")

        mock_config = Mock()
        mock_config.get_sites.return_value = []

        manager = ServerAuditManager(mock_ssh, mock_config)
        results = manager.run_full_audit(verbose=False)

        # Should complete without crashing
        assert 'overall_score' in results

    def test_unicode_in_responses(self):
        """Test handling of unicode characters in responses."""
        mock_ssh = Mock()
        mock_ssh.run_command.return_value = (0, "Ñoño ユーザー 用户", "")

        mock_config = Mock()
        mock_config.get_sites.return_value = []

        manager = ServerAuditManager(mock_ssh, mock_config)
        results = manager.run_full_audit(verbose=False)

        assert 'overall_score' in results

    def test_very_long_responses(self):
        """Test handling of very long SSH responses."""
        mock_ssh = Mock()
        # Simulate very long output
        long_output = "line\n" * 10000
        mock_ssh.run_command.return_value = (0, long_output, "")

        mock_config = Mock()
        mock_config.get_sites.return_value = []

        manager = ServerAuditManager(mock_ssh, mock_config)
        results = manager.run_full_audit(verbose=False)

        assert 'overall_score' in results

    def test_null_bytes_in_responses(self):
        """Test handling of null bytes in SSH responses."""
        mock_ssh = Mock()
        mock_ssh.run_command.return_value = (0, "data\x00with\x00nulls", "")

        mock_config = Mock()
        mock_config.get_sites.return_value = []

        manager = ServerAuditManager(mock_ssh, mock_config)
        results = manager.run_full_audit(verbose=False)

        assert 'overall_score' in results
