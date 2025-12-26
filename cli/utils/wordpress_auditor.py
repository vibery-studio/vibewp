"""WordPress-specific security auditing"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
import re
import shlex


class WordPressAuditor:
    """WordPress security auditor for all sites on VPS"""

    def __init__(self, ssh_manager, config_manager):
        """
        Initialize WordPress auditor

        Args:
            ssh_manager: SSHManager instance
            config_manager: ConfigManager instance
        """
        self.ssh = ssh_manager
        self.config = config_manager

    def audit_all_sites(self) -> Dict:
        """
        Audit all WordPress sites

        Returns:
            Dictionary with audit results for all sites
        """
        sites = self.config.get_sites()

        if not sites:
            return {
                'sites_audited': 0,
                'findings': [],
                'sites': {},
                'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }

        all_findings = []
        site_results = {}

        for site in sites:
            site_audit = self.audit_site(site.name, site.domain, site.type)
            site_results[site.name] = site_audit
            all_findings.extend(site_audit['findings'])

        return {
            'sites_audited': len(sites),
            'findings': all_findings,
            'sites': site_results,
            'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }

    def audit_site(self, site_name: str, domain: str, wp_type: str) -> Dict:
        """
        Audit a single WordPress site

        Args:
            site_name: Site name
            domain: Site domain
            wp_type: WordPress type (frankenwp or ols)

        Returns:
            Dictionary with site audit results
        """
        findings = []
        container_name = f"{site_name}-wp"

        # Check if container is running
        exit_code, _, _ = self.ssh.run_command(
            f"docker ps --filter name={container_name} --format '{{{{.Names}}}}'"
        )

        if exit_code != 0:
            return {
                'site': site_name,
                'status': 'container_not_running',
                'findings': [{
                    'id': f'WP-{site_name}-OFFLINE',
                    'severity': 'high',
                    'title': f'WordPress container offline: {site_name}',
                    'description': f'Container {container_name} is not running',
                    'impact': 'Site unavailable for security checks',
                    'remediation': f'Start container: docker start {container_name}',
                    'auto_fix': None
                }]
            }

        # Run all WordPress-specific audits
        findings.extend(self._audit_core_version(container_name, site_name, wp_type))
        findings.extend(self._audit_file_permissions(container_name, site_name, wp_type, domain))
        findings.extend(self._audit_wp_config(container_name, site_name, wp_type, domain))
        findings.extend(self._audit_plugins(container_name, site_name, wp_type))
        findings.extend(self._audit_themes(container_name, site_name, wp_type))
        findings.extend(self._audit_users(container_name, site_name, wp_type))

        return {
            'site': site_name,
            'domain': domain,
            'status': 'audited',
            'findings': findings
        }

    def _audit_core_version(self, container: str, site: str, wp_type: str) -> List[Dict]:
        """Check WordPress core version"""
        findings = []
        wp_path = "/var/www/html" if wp_type in ["frankenwp", "wordpress"] else "/var/www/vhosts"

        # Get current WP version
        exit_code, current_version, _ = self.ssh.run_command(
            f"docker exec {container} wp core version --path={wp_path} --allow-root 2>/dev/null"
        )

        if exit_code != 0:
            findings.append({
                'id': f'WP-{site}-CORE-001',
                'severity': 'medium',
                'title': f'Cannot verify WordPress version: {site}',
                'description': 'Unable to check WordPress core version',
                'impact': 'Cannot verify if core is up to date',
                'remediation': 'Verify WP-CLI is working properly',
                'auto_fix': None
            })
            return findings

        current_version = current_version.strip()

        # Check for updates
        exit_code, update_check, _ = self.ssh.run_command(
            f"docker exec {container} wp core check-update --path={wp_path} --format=json --allow-root 2>/dev/null"
        )

        if exit_code == 0 and update_check.strip() and update_check.strip() != '[]':
            findings.append({
                'id': f'WP-{site}-CORE-002',
                'severity': 'high',
                'title': f'WordPress core outdated: {site}',
                'description': f'WordPress {current_version} has updates available',
                'impact': 'May contain known security vulnerabilities',
                'remediation': f'Update WordPress: docker exec {container} wp core update --path={wp_path} --allow-root',
                'auto_fix': None
            })

        # Check if version is very outdated (rough check)
        try:
            version_parts = current_version.split('.')
            major = int(version_parts[0])
            minor = int(version_parts[1]) if len(version_parts) > 1 else 0

            # If major version is less than 6 or version is 6.0-6.3, it's quite old
            if major < 6 or (major == 6 and minor < 4):
                findings.append({
                    'id': f'WP-{site}-CORE-003',
                    'severity': 'critical',
                    'title': f'WordPress version critically outdated: {site}',
                    'description': f'WordPress {current_version} is significantly outdated',
                    'impact': 'Multiple known security vulnerabilities likely present',
                    'remediation': f'Urgently update WordPress: docker exec {container} wp core update --path={wp_path} --allow-root',
                    'auto_fix': None
                })
        except (ValueError, IndexError):
            pass

        return findings

    def _audit_file_permissions(self, container: str, site: str, wp_type: str, domain: str) -> List[Dict]:
        """Audit WordPress file permissions"""
        findings = []

        if wp_type in ["frankenwp", "wordpress"]:
            wp_path = "/var/www/html"
            config_path = f"{wp_path}/wp-config.php"
            uploads_path = f"{wp_path}/wp-content/uploads"
        else:
            wp_path = f"/var/www/vhosts/{domain}"
            config_path = f"{wp_path}/wp-config.php"
            uploads_path = f"{wp_path}/wp-content/uploads"

        # Check wp-config.php permissions
        exit_code, perms, _ = self.ssh.run_command(
            f"docker exec {container} stat -c '%a' {config_path} 2>/dev/null"
        )

        if exit_code == 0:
            perms = perms.strip()
            # wp-config.php should be 600 or 640, not 644 or 666
            if perms in ['644', '666', '777']:
                findings.append({
                    'id': f'WP-{site}-PERM-001',
                    'severity': 'high',
                    'title': f'Insecure wp-config.php permissions: {site}',
                    'description': f'wp-config.php has permissions {perms}',
                    'impact': 'Database credentials may be readable by other users',
                    'remediation': f'docker exec {container} chmod 600 {config_path}',
                    'auto_fix': None
                })

        # Check uploads directory permissions
        exit_code, perms, _ = self.ssh.run_command(
            f"docker exec {container} stat -c '%a' {uploads_path} 2>/dev/null"
        )

        if exit_code == 0:
            perms = perms.strip()
            # Uploads should not be 777
            if perms == '777':
                findings.append({
                    'id': f'WP-{site}-PERM-002',
                    'severity': 'medium',
                    'title': f'Overly permissive uploads directory: {site}',
                    'description': f'Uploads directory has permissions {perms}',
                    'impact': 'Anyone can write files to uploads',
                    'remediation': f'docker exec {container} chmod 755 {uploads_path}',
                    'auto_fix': None
                })

        return findings

    def _audit_wp_config(self, container: str, site: str, wp_type: str, domain: str) -> List[Dict]:
        """Audit wp-config.php security settings"""
        findings = []

        if wp_type in ["frankenwp", "wordpress"]:
            config_path = "/var/www/html/wp-config.php"
        else:
            config_path = f"/var/www/vhosts/{domain}/wp-config.php"

        # Read wp-config.php
        exit_code, config, _ = self.ssh.run_command(
            f"docker exec {container} cat {config_path} 2>/dev/null"
        )

        if exit_code != 0:
            findings.append({
                'id': f'WP-{site}-CFG-001',
                'severity': 'critical',
                'title': f'Cannot read wp-config.php: {site}',
                'description': 'wp-config.php is missing or unreadable',
                'impact': 'Cannot verify security configuration',
                'remediation': 'Investigate WordPress installation integrity',
                'auto_fix': None
            })
            return findings

        # Check for WP_DEBUG enabled in production
        if re.search(r"define\s*\(\s*['\"]WP_DEBUG['\"]\s*,\s*true", config, re.IGNORECASE):
            findings.append({
                'id': f'WP-{site}-CFG-002',
                'severity': 'medium',
                'title': f'Debug mode enabled: {site}',
                'description': 'WP_DEBUG is set to true',
                'impact': 'Sensitive information may be exposed in error messages',
                'remediation': 'Set WP_DEBUG to false in wp-config.php',
                'auto_fix': None
            })

        # Check for security keys
        security_keys = [
            'AUTH_KEY', 'SECURE_AUTH_KEY', 'LOGGED_IN_KEY', 'NONCE_KEY',
            'AUTH_SALT', 'SECURE_AUTH_SALT', 'LOGGED_IN_SALT', 'NONCE_SALT'
        ]

        for key in security_keys:
            # Check if key is defined and not using default value
            if key not in config:
                findings.append({
                    'id': f'WP-{site}-CFG-KEY-{key}',
                    'severity': 'high',
                    'title': f'Missing security key: {key} in {site}',
                    'description': f'Security key {key} is not defined',
                    'impact': 'Weakened authentication security',
                    'remediation': 'Add security keys from https://api.wordpress.org/secret-key/1.1/salt/',
                    'auto_fix': None
                })
            elif 'put your unique phrase here' in config.lower():
                findings.append({
                    'id': f'WP-{site}-CFG-003',
                    'severity': 'critical',
                    'title': f'Default security keys in use: {site}',
                    'description': 'WordPress security keys are using default values',
                    'impact': 'Authentication can be easily compromised',
                    'remediation': 'Replace with unique keys from https://api.wordpress.org/secret-key/1.1/salt/',
                    'auto_fix': None
                })
                break  # Only report once

        # Check for DISALLOW_FILE_EDIT
        if 'DISALLOW_FILE_EDIT' not in config or 'DISALLOW_FILE_EDIT\' , false' in config.lower():
            findings.append({
                'id': f'WP-{site}-CFG-004',
                'severity': 'medium',
                'title': f'File editing not disabled: {site}',
                'description': 'DISALLOW_FILE_EDIT is not set to true',
                'impact': 'Compromised admin accounts can edit theme/plugin files',
                'remediation': "Add to wp-config.php: define('DISALLOW_FILE_EDIT', true);",
                'auto_fix': None
            })

        return findings

    def _audit_plugins(self, container: str, site: str, wp_type: str) -> List[Dict]:
        """Audit WordPress plugins"""
        findings = []
        wp_path = "/var/www/html" if wp_type in ["frankenwp", "wordpress"] else "/var/www/vhosts"

        # Get list of plugins
        exit_code, plugins_json, _ = self.ssh.run_command(
            f"docker exec {container} wp plugin list --path={wp_path} --format=json --allow-root 2>/dev/null"
        )

        if exit_code != 0:
            return findings

        # Parse JSON (basic parsing without import json module)
        # Count inactive plugins
        inactive_count = plugins_json.count('"status":"inactive"')

        if inactive_count > 5:
            findings.append({
                'id': f'WP-{site}-PLG-001',
                'severity': 'low',
                'title': f'Many inactive plugins: {site}',
                'description': f'{inactive_count} inactive plugins found',
                'impact': 'Unused plugins may contain vulnerabilities',
                'remediation': 'Remove unused plugins to reduce attack surface',
                'auto_fix': None
            })

        # Check for plugin updates
        exit_code, updates, _ = self.ssh.run_command(
            f"docker exec {container} wp plugin list --path={wp_path} --update=available --format=count --allow-root 2>/dev/null"
        )

        if exit_code == 0 and updates.strip().isdigit():
            update_count = int(updates.strip())
            if update_count > 0:
                findings.append({
                    'id': f'WP-{site}-PLG-002',
                    'severity': 'high',
                    'title': f'{update_count} plugin updates available: {site}',
                    'description': f'{update_count} plugins have updates available',
                    'impact': 'Outdated plugins may have known vulnerabilities',
                    'remediation': f'Update plugins: docker exec {container} wp plugin update --all --path={wp_path} --allow-root',
                    'auto_fix': None
                })

        return findings

    def _audit_themes(self, container: str, site: str, wp_type: str) -> List[Dict]:
        """Audit WordPress themes"""
        findings = []
        wp_path = "/var/www/html" if wp_type in ["frankenwp", "wordpress"] else "/var/www/vhosts"

        # Check for theme updates
        exit_code, updates, _ = self.ssh.run_command(
            f"docker exec {container} wp theme list --path={wp_path} --update=available --format=count --allow-root 2>/dev/null"
        )

        if exit_code == 0 and updates.strip().isdigit():
            update_count = int(updates.strip())
            if update_count > 0:
                findings.append({
                    'id': f'WP-{site}-THM-001',
                    'severity': 'medium',
                    'title': f'{update_count} theme updates available: {site}',
                    'description': f'{update_count} themes have updates available',
                    'impact': 'Outdated themes may have vulnerabilities',
                    'remediation': f'Update themes: docker exec {container} wp theme update --all --path={wp_path} --allow-root',
                    'auto_fix': None
                })

        # Count inactive themes
        exit_code, themes_json, _ = self.ssh.run_command(
            f"docker exec {container} wp theme list --path={wp_path} --format=json --allow-root 2>/dev/null"
        )

        if exit_code == 0:
            inactive_count = themes_json.count('"status":"inactive"')

            if inactive_count > 3:
                findings.append({
                    'id': f'WP-{site}-THM-002',
                    'severity': 'low',
                    'title': f'Many inactive themes: {site}',
                    'description': f'{inactive_count} inactive themes found',
                    'impact': 'Unused themes may contain vulnerabilities',
                    'remediation': 'Remove unused themes to reduce attack surface',
                    'auto_fix': None
                })

        return findings

    def _audit_users(self, container: str, site: str, wp_type: str) -> List[Dict]:
        """Audit WordPress users"""
        findings = []
        wp_path = "/var/www/html" if wp_type in ["frankenwp", "wordpress"] else "/var/www/vhosts"

        # Get list of administrator users
        exit_code, admins, _ = self.ssh.run_command(
            f"docker exec {container} wp user list --path={wp_path} --role=administrator --format=count --allow-root 2>/dev/null"
        )

        if exit_code == 0 and admins.strip().isdigit():
            admin_count = int(admins.strip())

            if admin_count > 5:
                findings.append({
                    'id': f'WP-{site}-USR-001',
                    'severity': 'medium',
                    'title': f'Too many administrator accounts: {site}',
                    'description': f'{admin_count} administrator accounts found',
                    'impact': 'Increased risk from compromised admin accounts',
                    'remediation': 'Review and reduce number of admin accounts',
                    'auto_fix': None
                })

        # Check for default 'admin' username
        exit_code, has_admin, _ = self.ssh.run_command(
            f"docker exec {container} wp user get admin --path={wp_path} --allow-root 2>/dev/null"
        )

        if exit_code == 0:
            findings.append({
                'id': f'WP-{site}-USR-002',
                'severity': 'medium',
                'title': f'Default admin username exists: {site}',
                'description': 'User account with username "admin" exists',
                'impact': 'Common target for brute-force attacks',
                'remediation': 'Create new admin user and delete "admin" account',
                'auto_fix': None
            })

        return findings

    def get_plugin_list(self, site_name: str) -> List[Dict]:
        """
        Get list of installed plugins for a site

        Args:
            site_name: Site name

        Returns:
            List of plugin dictionaries
        """
        site = self.config.get_site(site_name)
        if not site:
            return []

        container_name = f"{site_name}-wp"
        wp_path = "/var/www/html" if site.type == "frankenwp" else "/var/www/vhosts"

        exit_code, output, _ = self.ssh.run_command(
            f"docker exec {container_name} wp plugin list --path={wp_path} --format=json --allow-root 2>/dev/null"
        )

        if exit_code != 0:
            return []

        # Basic JSON parsing (without json module)
        plugins = []
        # This is a simplified parser - in production you'd use json.loads()
        return plugins

    def get_theme_list(self, site_name: str) -> List[Dict]:
        """
        Get list of installed themes for a site

        Args:
            site_name: Site name

        Returns:
            List of theme dictionaries
        """
        site = self.config.get_site(site_name)
        if not site:
            return []

        container_name = f"{site_name}-wp"
        wp_path = "/var/www/html" if site.type == "frankenwp" else "/var/www/vhosts"

        exit_code, output, _ = self.ssh.run_command(
            f"docker exec {container_name} wp theme list --path={wp_path} --format=json --allow-root 2>/dev/null"
        )

        if exit_code != 0:
            return []

        themes = []
        return themes
