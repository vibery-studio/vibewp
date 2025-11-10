"""System-level security auditing for VPS infrastructure"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import re


class SystemAuditor:
    """Comprehensive system-level security auditor"""

    def __init__(self, ssh_manager):
        """
        Initialize system auditor

        Args:
            ssh_manager: SSHManager instance for remote command execution
        """
        self.ssh = ssh_manager

    def audit_all(self) -> Dict:
        """
        Run all system-level security audits

        Returns:
            Dictionary with all audit results
        """
        return {
            'ssh': self.audit_ssh_config(),
            'firewall': self.audit_firewall(),
            'fail2ban': self.audit_fail2ban(),
            'ports': self.audit_open_ports(),
            'services': self.audit_services(),
            'users': self.audit_users(),
            'updates': self.audit_updates(),
            'logs': self.audit_logs(),
            'filesystem': self.audit_filesystem_permissions(),
            'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }

    def audit_ssh_config(self) -> Dict:
        """
        Audit SSH configuration for security issues

        Returns:
            Dictionary of SSH security findings
        """
        findings = []

        # Read SSH config
        exit_code, config, _ = self.ssh.run_command("sudo cat /etc/ssh/sshd_config")
        if exit_code != 0:
            return {'error': 'Cannot read SSH config', 'findings': []}

        # Parse config
        config_dict = self._parse_ssh_config(config)

        # Check root login
        permit_root = config_dict.get('permitrootlogin', 'yes').lower()
        if permit_root not in ['no', 'prohibit-password']:
            findings.append({
                'id': 'SSH-001',
                'severity': 'high',
                'title': 'Root login enabled',
                'description': 'SSH allows direct root login',
                'impact': 'Increases brute-force attack surface',
                'remediation': 'Edit /etc/ssh/sshd_config: PermitRootLogin no',
                'auto_fix': None
            })

        # Check password authentication
        password_auth = config_dict.get('passwordauthentication', 'yes').lower()
        if password_auth == 'yes':
            findings.append({
                'id': 'SSH-002',
                'severity': 'high',
                'title': 'Password authentication enabled',
                'description': 'SSH allows password-based login',
                'impact': 'Vulnerable to brute-force and credential stuffing attacks',
                'remediation': 'Edit /etc/ssh/sshd_config: PasswordAuthentication no',
                'auto_fix': None
            })

        # Check SSH port
        port = config_dict.get('port', '22')
        if port == '22':
            findings.append({
                'id': 'SSH-003',
                'severity': 'medium',
                'title': 'Default SSH port in use',
                'description': 'SSH running on default port 22',
                'impact': 'Easier target for automated attacks',
                'remediation': 'Change SSH port to non-standard value',
                'auto_fix': 'vibewp ssh change-port <port>'
            })

        # Check key-based authentication
        pubkey_auth = config_dict.get('pubkeyauthentication', 'yes').lower()
        if pubkey_auth != 'yes':
            findings.append({
                'id': 'SSH-004',
                'severity': 'high',
                'title': 'Public key authentication disabled',
                'description': 'SSH public key authentication is not enabled',
                'impact': 'Cannot use key-based authentication',
                'remediation': 'Edit /etc/ssh/sshd_config: PubkeyAuthentication yes',
                'auto_fix': None
            })

        # Check protocol version
        protocol = config_dict.get('protocol', '2')
        if '1' in protocol:
            findings.append({
                'id': 'SSH-005',
                'severity': 'critical',
                'title': 'SSH Protocol 1 enabled',
                'description': 'Insecure SSH Protocol 1 is enabled',
                'impact': 'Vulnerable to known protocol attacks',
                'remediation': 'Edit /etc/ssh/sshd_config: Protocol 2',
                'auto_fix': None
            })

        return {'findings': findings, 'config': config_dict}

    def audit_firewall(self) -> Dict:
        """
        Audit firewall configuration and status

        Returns:
            Dictionary of firewall findings
        """
        findings = []

        # Check UFW status
        exit_code, status, _ = self.ssh.run_command("sudo ufw status verbose")

        if exit_code != 0:
            findings.append({
                'id': 'FW-001',
                'severity': 'critical',
                'title': 'UFW not installed',
                'description': 'Uncomplicated Firewall (UFW) is not installed',
                'impact': 'No firewall protection',
                'remediation': 'Install UFW: sudo apt-get install ufw',
                'auto_fix': None
            })
            return {'findings': findings, 'active': False, 'rules': []}

        firewall_active = 'Status: active' in status
        if not firewall_active:
            findings.append({
                'id': 'FW-002',
                'severity': 'critical',
                'title': 'Firewall inactive',
                'description': 'UFW firewall is installed but not active',
                'impact': 'All ports exposed to internet',
                'remediation': 'Enable firewall: sudo ufw enable',
                'auto_fix': 'vibewp firewall enable'
            })

        # Parse firewall rules
        rules = self._parse_ufw_rules(status)

        # Check for overly permissive rules
        for rule in rules:
            if rule.get('from') == 'Anywhere' and rule.get('to').startswith('Anywhere'):
                findings.append({
                    'id': 'FW-003',
                    'severity': 'medium',
                    'title': f"Unrestricted access on port {rule.get('to_port', 'unknown')}",
                    'description': f"Port {rule.get('to_port')} allows connections from any IP",
                    'impact': 'Increased attack surface',
                    'remediation': f"Restrict access to specific IPs if possible",
                    'auto_fix': None
                })

        # Check default policy
        default_incoming = 'Default: deny (incoming)' in status
        if not default_incoming:
            findings.append({
                'id': 'FW-004',
                'severity': 'high',
                'title': 'Permissive default incoming policy',
                'description': 'Default incoming policy is not deny',
                'impact': 'Ports not explicitly denied are accessible',
                'remediation': 'Set default deny: sudo ufw default deny incoming',
                'auto_fix': None
            })

        return {
            'findings': findings,
            'active': firewall_active,
            'rules': rules,
            'status': status
        }

    def audit_fail2ban(self) -> Dict:
        """
        Audit fail2ban configuration and status

        Returns:
            Dictionary of fail2ban findings
        """
        findings = []

        # Check if fail2ban is installed
        exit_code, _, _ = self.ssh.run_command("which fail2ban-client")
        if exit_code != 0:
            findings.append({
                'id': 'F2B-001',
                'severity': 'medium',
                'title': 'fail2ban not installed',
                'description': 'fail2ban intrusion prevention not installed',
                'impact': 'No automatic IP banning for brute-force attacks',
                'remediation': 'Install fail2ban: sudo apt-get install fail2ban',
                'auto_fix': None
            })
            return {'findings': findings, 'active': False, 'jails': []}

        # Check if fail2ban is running
        exit_code, status, _ = self.ssh.run_command(
            "sudo systemctl is-active fail2ban 2>/dev/null || echo inactive"
        )

        fail2ban_active = 'active' in status.lower() and 'inactive' not in status.lower()
        if not fail2ban_active:
            findings.append({
                'id': 'F2B-002',
                'severity': 'medium',
                'title': 'fail2ban not running',
                'description': 'fail2ban service is not active',
                'impact': 'No protection against brute-force attacks',
                'remediation': 'Start fail2ban: sudo systemctl start fail2ban',
                'auto_fix': None
            })
            return {'findings': findings, 'active': False, 'jails': []}

        # Get jail list
        exit_code, jail_output, _ = self.ssh.run_command("sudo fail2ban-client status")
        jails = []
        if exit_code == 0:
            for line in jail_output.split('\n'):
                if 'Jail list:' in line:
                    jails_str = line.split('Jail list:')[1].strip()
                    jails = [j.strip() for j in jails_str.split(',') if j.strip()]

        # Check for sshd jail
        if 'sshd' not in jails:
            findings.append({
                'id': 'F2B-003',
                'severity': 'medium',
                'title': 'SSH jail not configured',
                'description': 'fail2ban sshd jail is not active',
                'impact': 'SSH not protected by fail2ban',
                'remediation': 'Enable sshd jail in /etc/fail2ban/jail.local',
                'auto_fix': None
            })

        return {
            'findings': findings,
            'active': fail2ban_active,
            'jails': jails
        }

    def audit_open_ports(self) -> Dict:
        """
        Scan for open ports and listening services

        Returns:
            Dictionary of open ports and findings
        """
        findings = []

        # Use ss (socket statistics) to get listening ports
        exit_code, output, _ = self.ssh.run_command(
            "sudo ss -tulnp | grep LISTEN"
        )

        if exit_code != 0:
            return {'findings': [], 'ports': []}

        ports = self._parse_ss_output(output)

        # Flag potentially risky open ports
        risky_ports = {
            '3306': 'MySQL',
            '5432': 'PostgreSQL',
            '6379': 'Redis',
            '27017': 'MongoDB',
            '9200': 'Elasticsearch',
            '8080': 'HTTP Proxy',
            '2375': 'Docker API (unencrypted)',
            '2376': 'Docker API'
        }

        for port_info in ports:
            port = port_info.get('port')
            address = port_info.get('address')

            # Check if database/service is exposed to public
            if port in risky_ports and address != '127.0.0.1':
                findings.append({
                    'id': f'PORT-{port}',
                    'severity': 'high',
                    'title': f'{risky_ports[port]} exposed',
                    'description': f'{risky_ports[port]} (port {port}) is listening on {address}',
                    'impact': 'Service accessible from network',
                    'remediation': f'Bind {risky_ports[port]} to localhost only',
                    'auto_fix': None
                })

        return {
            'findings': findings,
            'ports': ports
        }

    def audit_services(self) -> Dict:
        """
        Audit running services for security issues

        Returns:
            Dictionary of service findings
        """
        findings = []

        # List running services
        exit_code, output, _ = self.ssh.run_command(
            "sudo systemctl list-units --type=service --state=running --no-pager"
        )

        if exit_code != 0:
            return {'findings': [], 'services': []}

        services = self._parse_systemctl_output(output)

        # Flag unnecessary services
        unnecessary_services = ['telnet', 'rsh', 'rlogin', 'vsftpd', 'xinetd']
        for service_name in unnecessary_services:
            if any(service_name in s.lower() for s in services):
                findings.append({
                    'id': f'SVC-{service_name.upper()}',
                    'severity': 'high',
                    'title': f'Insecure service running: {service_name}',
                    'description': f'{service_name} service is running',
                    'impact': 'Potential security vulnerability',
                    'remediation': f'Disable service: sudo systemctl disable {service_name}',
                    'auto_fix': None
                })

        return {
            'findings': findings,
            'services': services
        }

    def audit_users(self) -> Dict:
        """
        Audit user accounts and permissions

        Returns:
            Dictionary of user permission findings
        """
        findings = []

        # Get users with sudo access
        exit_code, sudo_users, _ = self.ssh.run_command(
            "grep -Po '^sudo.+:\\K.*$' /etc/group"
        )

        users_with_sudo = []
        if exit_code == 0 and sudo_users.strip():
            users_with_sudo = [u.strip() for u in sudo_users.split(',')]

        # Get users with login shells
        exit_code, passwd, _ = self.ssh.run_command(
            "getent passwd | grep -v '/nologin\\|/false'"
        )

        login_users = []
        if exit_code == 0:
            for line in passwd.split('\n'):
                if line.strip():
                    parts = line.split(':')
                    if len(parts) >= 1:
                        username = parts[0]
                        # Exclude system users
                        if username not in ['root', 'sync', 'shutdown', 'halt']:
                            login_users.append(username)

        # Check for users without password
        exit_code, shadow_check, _ = self.ssh.run_command(
            "sudo awk -F: '($2 == \"\" ) {print $1}' /etc/shadow"
        )

        users_no_password = []
        if exit_code == 0 and shadow_check.strip():
            users_no_password = [u.strip() for u in shadow_check.split('\n') if u.strip()]

        for user in users_no_password:
            if user != 'root':  # Root typically checked separately
                findings.append({
                    'id': f'USER-{user}',
                    'severity': 'high',
                    'title': f'User without password: {user}',
                    'description': f'User account {user} has no password set',
                    'impact': 'Potential unauthorized access',
                    'remediation': f'Set password: sudo passwd {user}',
                    'auto_fix': None
                })

        return {
            'findings': findings,
            'sudo_users': users_with_sudo,
            'login_users': login_users
        }

    def audit_updates(self) -> Dict:
        """
        Check for available security and system updates

        Returns:
            Dictionary with update information
        """
        findings = []

        # Update package cache quietly
        self.ssh.run_command("sudo apt-get update -qq 2>/dev/null", timeout=120)

        # Count upgradable packages
        exit_code, upgradable, _ = self.ssh.run_command(
            "apt list --upgradable 2>/dev/null | tail -n +2 | wc -l"
        )
        total_updates = int(upgradable.strip()) if upgradable.strip().isdigit() else 0

        # Count security updates
        exit_code, security, _ = self.ssh.run_command(
            "apt list --upgradable 2>/dev/null | grep -i security | wc -l"
        )
        security_updates = int(security.strip()) if security.strip().isdigit() else 0

        if security_updates > 0:
            findings.append({
                'id': 'UPD-001',
                'severity': 'high',
                'title': f'{security_updates} security updates available',
                'description': f'System has {security_updates} pending security updates',
                'impact': 'Known vulnerabilities may be exploitable',
                'remediation': 'Install updates: sudo apt-get upgrade',
                'auto_fix': 'vibewp security install-updates --security-only'
            })

        if total_updates > 10:
            findings.append({
                'id': 'UPD-002',
                'severity': 'medium',
                'title': f'{total_updates} total updates available',
                'description': f'System has {total_updates} pending updates',
                'impact': 'System may be missing important patches',
                'remediation': 'Install updates: sudo apt-get upgrade',
                'auto_fix': 'vibewp security install-updates'
            })

        return {
            'findings': findings,
            'total_updates': total_updates,
            'security_updates': security_updates
        }

    def audit_logs(self) -> Dict:
        """
        Analyze system logs for suspicious activity

        Returns:
            Dictionary of log analysis findings
        """
        findings = []

        # Check for failed SSH login attempts
        exit_code, failed_ssh, _ = self.ssh.run_command(
            "sudo grep 'Failed password' /var/log/auth.log 2>/dev/null | wc -l"
        )

        failed_attempts = int(failed_ssh.strip()) if failed_ssh.strip().isdigit() else 0

        if failed_attempts > 100:
            findings.append({
                'id': 'LOG-001',
                'severity': 'medium',
                'title': f'{failed_attempts} failed SSH login attempts',
                'description': f'Detected {failed_attempts} failed SSH authentication attempts',
                'impact': 'Possible brute-force attack in progress',
                'remediation': 'Review /var/log/auth.log and consider fail2ban',
                'auto_fix': None
            })

        # Check for sudo usage
        exit_code, sudo_usage, _ = self.ssh.run_command(
            "sudo grep 'sudo:' /var/log/auth.log 2>/dev/null | tail -20"
        )

        recent_sudo = []
        if exit_code == 0:
            recent_sudo = sudo_usage.split('\n')[:10]  # Last 10 entries

        return {
            'findings': findings,
            'failed_ssh_attempts': failed_attempts,
            'recent_sudo': recent_sudo
        }

    def audit_filesystem_permissions(self) -> Dict:
        """
        Check sensitive file permissions

        Returns:
            Dictionary of filesystem permission findings
        """
        findings = []

        sensitive_files = {
            '/etc/passwd': '644',
            '/etc/shadow': '640',
            '/etc/group': '644',
            '/etc/gshadow': '640',
            '/etc/ssh/sshd_config': '600'
        }

        for filepath, expected_perms in sensitive_files.items():
            exit_code, perms, _ = self.ssh.run_command(
                f"stat -c '%a' {filepath} 2>/dev/null"
            )

            if exit_code != 0:
                continue

            actual_perms = perms.strip()
            if actual_perms != expected_perms:
                findings.append({
                    'id': f'FS-{filepath.replace("/", "-")}',
                    'severity': 'medium',
                    'title': f'Incorrect permissions on {filepath}',
                    'description': f'{filepath} has permissions {actual_perms}, expected {expected_perms}',
                    'impact': 'Sensitive file may be accessible to unauthorized users',
                    'remediation': f'Fix permissions: sudo chmod {expected_perms} {filepath}',
                    'auto_fix': None
                })

        return {
            'findings': findings
        }

    # Helper methods
    def _parse_ssh_config(self, config: str) -> Dict[str, str]:
        """Parse SSH config into dictionary"""
        config_dict = {}
        for line in config.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                parts = line.split(None, 1)
                if len(parts) == 2:
                    key = parts[0].lower()
                    value = parts[1]
                    config_dict[key] = value
        return config_dict

    def _parse_ufw_rules(self, status: str) -> List[Dict]:
        """Parse UFW status output into rule list"""
        rules = []
        in_rules_section = False

        for line in status.split('\n'):
            line = line.strip()

            if 'To' in line and 'Action' in line and 'From' in line:
                in_rules_section = True
                continue

            if in_rules_section and line:
                parts = line.split()
                # Skip header separator lines and ensure valid rule format
                if len(parts) >= 3 and not line.startswith('-'):
                    # Additional validation: check if first part contains port/service info
                    if '/' in parts[0] or parts[0].isdigit() or parts[0].lower() in ['anywhere', 'any']:
                        rules.append({
                            'to': parts[0],
                            'action': parts[1],
                            'from': ' '.join(parts[2:])
                        })

        return rules

    def _parse_ss_output(self, output: str) -> List[Dict]:
        """Parse ss command output"""
        ports = []
        for line in output.split('\n'):
            if not line.strip():
                continue

            parts = line.split()
            if len(parts) >= 5:
                # Extract address and port from local address
                local_addr = parts[4]
                if ':' in local_addr:
                    addr_parts = local_addr.rsplit(':', 1)
                    address = addr_parts[0].replace('[', '').replace(']', '')
                    port = addr_parts[1]

                    # Extract process name if available
                    process = parts[6] if len(parts) > 6 else 'unknown'

                    ports.append({
                        'protocol': parts[0],
                        'address': address,
                        'port': port,
                        'process': process
                    })

        return ports

    def _parse_systemctl_output(self, output: str) -> List[str]:
        """Parse systemctl list output"""
        services = []
        for line in output.split('\n'):
            if '.service' in line:
                parts = line.split()
                if parts:
                    service_name = parts[0].replace('.service', '')
                    services.append(service_name)
        return services
