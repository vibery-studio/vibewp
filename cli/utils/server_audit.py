"""Server security audit orchestration and management"""

from typing import Dict, Optional
from datetime import datetime, timezone
from cli.utils.system_auditor import SystemAuditor
from cli.utils.wordpress_auditor import WordPressAuditor
from cli.utils.vulnerability_scanner import VulnerabilityScanner
from cli.utils.report_generator import ReportGenerator


class ServerAuditManager:
    """Orchestrates comprehensive server security audits"""

    def __init__(self, ssh_manager, config_manager):
        """
        Initialize server audit manager

        Args:
            ssh_manager: SSHManager instance
            config_manager: ConfigManager instance
        """
        self.ssh = ssh_manager
        self.config = config_manager
        self.system_auditor = SystemAuditor(ssh_manager)
        self.wp_auditor = WordPressAuditor(ssh_manager, config_manager)
        self.vuln_scanner = None  # Initialized when needed with API token
        self.report_generator = ReportGenerator()

    def run_full_audit(
        self,
        skip_wordpress: bool = False,
        skip_lynis: bool = False,
        wpscan_api_token: Optional[str] = None,
        verbose: bool = False
    ) -> Dict:
        """
        Run comprehensive security audit

        Args:
            skip_wordpress: Skip WordPress-specific audits
            skip_lynis: Skip Lynis integration
            wpscan_api_token: WPScan API token for vulnerability scanning
            verbose: Enable verbose output

        Returns:
            Complete audit results dictionary
        """
        audit_results = {
            'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'overall_score': 0,
            'system': {},
            'wordpress': {},
            'vulnerabilities': {},
            'lynis': {},
            'errors': []
        }

        # 1. System-level audit
        try:
            if verbose:
                print("Running system audit...")
            audit_results['system'] = self.system_auditor.audit_all()
        except Exception as e:
            audit_results['errors'].append({
                'component': 'system',
                'error': str(e)
            })
            audit_results['system'] = {'error': str(e)}

        # 2. WordPress audit
        if not skip_wordpress:
            try:
                if verbose:
                    print("Running WordPress audit...")
                audit_results['wordpress'] = self.wp_auditor.audit_all_sites()
            except Exception as e:
                audit_results['errors'].append({
                    'component': 'wordpress',
                    'error': str(e)
                })
                audit_results['wordpress'] = {'error': str(e)}
        else:
            audit_results['wordpress'] = {'skipped': True}

        # 3. Vulnerability scanning (if API token provided)
        if wpscan_api_token and not skip_wordpress:
            try:
                if verbose:
                    print("Running vulnerability scan...")
                audit_results['vulnerabilities'] = self._run_vulnerability_scan(
                    wpscan_api_token,
                    verbose
                )
            except Exception as e:
                audit_results['errors'].append({
                    'component': 'vulnerabilities',
                    'error': str(e)
                })
                audit_results['vulnerabilities'] = {'error': str(e)}
        else:
            if skip_wordpress:
                audit_results['vulnerabilities'] = {'skipped': True}
            else:
                audit_results['vulnerabilities'] = {
                    'skipped': True,
                    'reason': 'No WPScan API token provided'
                }

        # 4. Lynis integration (if available and not skipped)
        if not skip_lynis:
            try:
                if verbose:
                    print("Checking Lynis availability...")
                audit_results['lynis'] = self._run_lynis_audit(verbose)
            except Exception as e:
                audit_results['errors'].append({
                    'component': 'lynis',
                    'error': str(e)
                })
                audit_results['lynis'] = {'error': str(e)}
        else:
            audit_results['lynis'] = {'skipped': True}

        # 5. Calculate overall security score
        audit_results['overall_score'] = self._calculate_overall_score(audit_results)

        return audit_results

    def _run_vulnerability_scan(self, api_token: str, verbose: bool = False) -> Dict:
        """
        Run vulnerability scan on all WordPress sites

        Args:
            api_token: WPScan API token
            verbose: Enable verbose output

        Returns:
            Vulnerability scan results
        """
        # Initialize scanner with token
        self.vuln_scanner = VulnerabilityScanner(api_token)

        sites = self.config.get_sites()
        if not sites:
            return {
                'total_vulnerabilities': 0,
                'sites': {},
                'scanned': 0
            }

        vulnerability_results = {
            'total_vulnerabilities': 0,
            'sites': {},
            'scanned': len(sites),
            'api_requests': 0
        }

        for site in sites:
            if verbose:
                print(f"  Scanning {site.name}...")

            site_vulns = self._scan_site_vulnerabilities(site.name, site.type)
            vulnerability_results['sites'][site.name] = site_vulns
            vulnerability_results['total_vulnerabilities'] += len(site_vulns.get('findings', []))

        # Get API request count
        if self.vuln_scanner:
            vulnerability_results['api_requests'] = self.vuln_scanner.get_request_count()

        return vulnerability_results

    def _scan_site_vulnerabilities(self, site_name: str, wp_type: str) -> Dict:
        """
        Scan single site for vulnerabilities

        Args:
            site_name: Site name
            wp_type: WordPress type (frankenwp/ols)

        Returns:
            Site vulnerability results
        """
        if not self.vuln_scanner:
            return {'error': 'Vulnerability scanner not initialized'}

        container_name = f"{site_name}-wp"
        wp_path = "/var/www/html" if wp_type in ["frankenwp", "wordpress"] else "/var/www/vhosts"

        findings = []

        # 1. Get WordPress core version
        exit_code, wp_version, _ = self.ssh.run_command(
            f"docker exec {container_name} wp core version --path={wp_path} --allow-root 2>/dev/null"
        )

        if exit_code == 0 and wp_version.strip():
            wp_version = wp_version.strip()
            core_scan = self.vuln_scanner.scan_wordpress_core(wp_version)
            core_findings = self.vuln_scanner.convert_to_findings(
                core_scan, site_name, 'core'
            )
            findings.extend(core_findings)

        # 2. Get plugins
        exit_code, plugins_output, _ = self.ssh.run_command(
            f"docker exec {container_name} wp plugin list --path={wp_path} --format=csv --fields=name,version,status --allow-root 2>/dev/null"
        )

        if exit_code == 0 and plugins_output.strip():
            plugins = self._parse_csv_output(plugins_output)
            for plugin in plugins[:10]:  # Limit to first 10 plugins to avoid rate limits
                if plugin.get('status') == 'active':
                    plugin_scan = self.vuln_scanner.scan_plugin(
                        plugin['name'],
                        plugin.get('version')
                    )
                    plugin_findings = self.vuln_scanner.convert_to_findings(
                        plugin_scan, site_name, 'plugin'
                    )
                    findings.extend(plugin_findings)

        # 3. Get themes
        exit_code, themes_output, _ = self.ssh.run_command(
            f"docker exec {container_name} wp theme list --path={wp_path} --format=csv --fields=name,version,status --allow-root 2>/dev/null"
        )

        if exit_code == 0 and themes_output.strip():
            themes = self._parse_csv_output(themes_output)
            for theme in themes[:5]:  # Limit to first 5 themes
                if theme.get('status') == 'active':
                    theme_scan = self.vuln_scanner.scan_theme(
                        theme['name'],
                        theme.get('version')
                    )
                    theme_findings = self.vuln_scanner.convert_to_findings(
                        theme_scan, site_name, 'theme'
                    )
                    findings.extend(theme_findings)

        return {
            'site': site_name,
            'findings': findings,
            'scanned_components': {
                'core': exit_code == 0,
                'plugins': len(plugins) if exit_code == 0 else 0,
                'themes': len(themes) if exit_code == 0 else 0
            }
        }

    def _run_lynis_audit(self, verbose: bool = False) -> Dict:
        """
        Run Lynis system audit if available

        Args:
            verbose: Enable verbose output

        Returns:
            Lynis audit results
        """
        # Check if Lynis is installed
        exit_code, _, _ = self.ssh.run_command("which lynis")

        if exit_code != 0:
            return {
                'available': False,
                'reason': 'Lynis not installed'
            }

        if verbose:
            print("  Running Lynis audit (this may take a few minutes)...")

        # Run Lynis audit
        exit_code, output, _ = self.ssh.run_command(
            "sudo lynis audit system --quick --quiet --no-colors 2>/dev/null",
            timeout=300  # 5 minutes
        )

        if exit_code != 0:
            return {
                'available': True,
                'error': 'Lynis audit failed'
            }

        # Parse Lynis output
        lynis_results = self._parse_lynis_output(output)
        lynis_results['available'] = True

        return lynis_results

    def _parse_lynis_output(self, output: str) -> Dict:
        """Parse Lynis audit output"""
        results = {
            'hardening_index': 0,
            'tests_performed': 0,
            'warnings': 0,
            'suggestions': 0,
            'findings': []
        }

        for line in output.split('\n'):
            line = line.strip()

            # Extract hardening index
            if 'Hardening index' in line:
                try:
                    parts = line.split(':')
                    if len(parts) > 1:
                        index_str = parts[1].strip().split('[')[0].strip()
                        results['hardening_index'] = int(index_str)
                except (ValueError, IndexError):
                    pass

            # Count tests
            elif 'Tests performed' in line:
                try:
                    parts = line.split(':')
                    if len(parts) > 1:
                        results['tests_performed'] = int(parts[1].strip())
                except (ValueError, IndexError):
                    pass

            # Parse warnings
            elif line.startswith('Warning:') or 'WARNING' in line:
                results['warnings'] += 1
                results['findings'].append({
                    'id': f'LYNIS-WARN-{results["warnings"]}',
                    'severity': 'high',
                    'title': 'Lynis Warning',
                    'description': line,
                    'impact': 'System hardening issue detected',
                    'remediation': 'Review Lynis full report for details',
                    'auto_fix': None
                })

            # Parse suggestions
            elif line.startswith('Suggestion:') or 'SUGGESTION' in line:
                results['suggestions'] += 1

        return results

    def _parse_csv_output(self, csv_output: str) -> list:
        """Parse CSV output from WP-CLI"""
        lines = csv_output.strip().split('\n')
        if len(lines) < 2:
            return []

        # Parse header
        headers = [h.strip() for h in lines[0].split(',')]

        # Parse rows
        items = []
        for line in lines[1:]:
            if line.strip():
                values = [v.strip() for v in line.split(',')]
                item = {}
                for i, header in enumerate(headers):
                    if i < len(values):
                        item[header] = values[i]
                items.append(item)

        return items

    def _calculate_overall_score(self, audit_results: Dict) -> int:
        """
        Calculate overall security score from all audit results

        Args:
            audit_results: Complete audit results

        Returns:
            Security score (0-100)
        """
        total_score = 0
        weight_sum = 0

        # System audit score (weight: 40%)
        if 'system' in audit_results and not audit_results['system'].get('error'):
            system_score = self._calculate_system_score(audit_results['system'])
            total_score += system_score * 0.4
            weight_sum += 0.4

        # WordPress audit score (weight: 30%)
        if 'wordpress' in audit_results and not audit_results['wordpress'].get('error'):
            if not audit_results['wordpress'].get('skipped'):
                wp_score = self._calculate_wordpress_score(audit_results['wordpress'])
                total_score += wp_score * 0.3
                weight_sum += 0.3

        # Vulnerability scan score (weight: 20%)
        if 'vulnerabilities' in audit_results and not audit_results['vulnerabilities'].get('error'):
            if not audit_results['vulnerabilities'].get('skipped'):
                vuln_score = self._calculate_vulnerability_score(audit_results['vulnerabilities'])
                total_score += vuln_score * 0.2
                weight_sum += 0.2

        # Lynis score (weight: 10%)
        if 'lynis' in audit_results and audit_results['lynis'].get('available'):
            if not audit_results['lynis'].get('error'):
                lynis_score = audit_results['lynis'].get('hardening_index', 0)
                total_score += lynis_score * 0.1
                weight_sum += 0.1

        # Normalize score
        if weight_sum > 0:
            overall_score = int(total_score / weight_sum)
        else:
            overall_score = 0

        return max(0, min(100, overall_score))

    def _calculate_system_score(self, system_data: Dict) -> int:
        """Calculate score from system audit"""
        total_checks = 0
        passed_checks = 0

        for category_data in system_data.values():
            if isinstance(category_data, dict) and 'findings' in category_data:
                findings = category_data['findings']
                # Count findings - fewer is better
                for finding in findings:
                    total_checks += 1
                    # Critical/high findings count as failed checks
                    if finding['severity'] in ['low', 'medium']:
                        passed_checks += 0.5

        # Base score
        if total_checks == 0:
            return 100

        score = int((1 - (total_checks - passed_checks) / max(total_checks, 1)) * 100)
        return max(0, min(100, score))

    def _calculate_wordpress_score(self, wp_data: Dict) -> int:
        """Calculate score from WordPress audit"""
        if wp_data.get('sites_audited', 0) == 0:
            return 100

        total_findings = len(wp_data.get('findings', []))
        critical_count = 0
        high_count = 0

        for finding in wp_data.get('findings', []):
            if finding['severity'] == 'critical':
                critical_count += 1
            elif finding['severity'] == 'high':
                high_count += 1

        # Score based on severity
        penalty = (critical_count * 15) + (high_count * 10) + (total_findings * 2)
        score = 100 - penalty

        return max(0, min(100, score))

    def _calculate_vulnerability_score(self, vuln_data: Dict) -> int:
        """Calculate score from vulnerability scan"""
        total_vulns = vuln_data.get('total_vulnerabilities', 0)

        if total_vulns == 0:
            return 100

        # Penalty based on vulnerabilities
        penalty = total_vulns * 10
        score = 100 - penalty

        return max(0, min(100, score))

    def generate_report(self, audit_results: Dict, format: str = 'console') -> str:
        """
        Generate audit report

        Args:
            audit_results: Audit results
            format: Report format (console, json, html, pdf)

        Returns:
            Report content
        """
        return self.report_generator.generate(audit_results, format)

    def save_report(self, report_content: str, filepath: str, format: str = 'txt'):
        """
        Save report to file

        Args:
            report_content: Report content
            filepath: Output file path
            format: File format
        """
        self.report_generator.save_to_file(report_content, filepath, format)
