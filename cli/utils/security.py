"""Security scanning and auditing utilities"""

from typing import Dict, List, Optional


class SecurityScanner:
    """Comprehensive security scanner for VPS"""

    def __init__(self, ssh_manager):
        """
        Initialize security scanner

        Args:
            ssh_manager: SSHManager instance for remote command execution
        """
        self.ssh = ssh_manager

    def run_audit(self) -> Dict:
        """
        Run comprehensive security audit

        Returns:
            Dictionary with audit results and security score
        """
        results = {
            'ssh': self._check_ssh_security(),
            'firewall': self._check_firewall(),
            'updates': self._check_updates(),
            'docker': self._check_docker_security(),
            'score': 0
        }

        # Calculate overall security score
        results['score'] = self._calculate_score(results)

        return results

    def _check_ssh_security(self) -> Dict:
        """
        Check SSH configuration security

        Returns:
            Dictionary of SSH security checks
        """
        checks = {}

        # Read SSH config
        exit_code, config, _ = self.ssh.run_command("sudo cat /etc/ssh/sshd_config")
        if exit_code != 0:
            return {'error': {'passed': False, 'message': 'Cannot read SSH config'}}

        # Check root login disabled
        root_login_disabled = False
        for line in config.split('\n'):
            line = line.strip()
            if line.startswith('PermitRootLogin') and not line.startswith('#'):
                if 'no' in line.lower():
                    root_login_disabled = True

        checks['root_login_disabled'] = {
            'passed': root_login_disabled,
            'message': 'Root login disabled' if root_login_disabled else 'Root login enabled (HIGH RISK)'
        }

        # Check password authentication
        password_auth_disabled = False
        for line in config.split('\n'):
            line = line.strip()
            if line.startswith('PasswordAuthentication') and not line.startswith('#'):
                if 'no' in line.lower():
                    password_auth_disabled = True

        checks['password_auth_disabled'] = {
            'passed': password_auth_disabled,
            'message': 'Password auth disabled' if password_auth_disabled else 'Password auth enabled (RISK)'
        }

        # Check custom SSH port
        custom_port = False
        port = '22'
        for line in config.split('\n'):
            line = line.strip()
            if line.startswith('Port') and not line.startswith('#'):
                port = line.split()[1] if len(line.split()) > 1 else '22'
                custom_port = port != '22'

        checks['custom_ssh_port'] = {
            'passed': custom_port,
            'message': f'Using custom port {port}' if custom_port else 'Using default port 22 (RISK)'
        }

        return checks

    def _check_firewall(self) -> Dict:
        """
        Check firewall configuration

        Returns:
            Dictionary of firewall security checks
        """
        checks = {}

        # Check UFW status
        exit_code, status, _ = self.ssh.run_command("sudo ufw status")

        firewall_active = 'Status: active' in status
        checks['firewall_active'] = {
            'passed': firewall_active,
            'message': 'Firewall is active' if firewall_active else 'Firewall INACTIVE (CRITICAL RISK)'
        }

        # Check fail2ban
        exit_code, fail2ban_status, _ = self.ssh.run_command(
            "sudo systemctl is-active fail2ban 2>/dev/null || echo inactive"
        )

        fail2ban_active = 'active' in fail2ban_status.lower() and 'inactive' not in fail2ban_status.lower()
        checks['fail2ban_active'] = {
            'passed': fail2ban_active,
            'message': 'fail2ban is active' if fail2ban_active else 'fail2ban not running (RISK)'
        }

        return checks

    def _check_updates(self) -> Dict:
        """
        Check for available security updates

        Returns:
            Dictionary with update counts
        """
        # Update package cache (suppress output)
        self.ssh.run_command("sudo apt-get update -qq 2>/dev/null")

        # Count upgradable packages
        exit_code, upgradable, _ = self.ssh.run_command(
            "apt list --upgradable 2>/dev/null | grep -c '^' || echo 0"
        )
        total_updates = int(upgradable.strip()) - 1  # Subtract header line
        total_updates = max(0, total_updates)

        # Count security updates
        exit_code, security, _ = self.ssh.run_command(
            "apt list --upgradable 2>/dev/null | grep -i security | wc -l || echo 0"
        )
        security_updates = int(security.strip())

        return {
            'total': total_updates,
            'security': security_updates
        }

    def _check_docker_security(self) -> Dict:
        """
        Check Docker security configuration

        Returns:
            Dictionary of Docker security checks
        """
        checks = {}

        # Check if Docker socket is exposed to network
        exit_code, netstat, _ = self.ssh.run_command(
            "sudo netstat -tlnp 2>/dev/null | grep docker || echo 'not exposed'"
        )

        # Docker socket should only listen on localhost or unix socket
        socket_safe = (
            'not exposed' in netstat or
            '127.0.0.1' in netstat or
            'unix' in netstat.lower()
        )

        checks['docker_socket_not_exposed'] = {
            'passed': socket_safe,
            'message': 'Docker socket not exposed' if socket_safe else 'Docker socket may be exposed (CHECK)'
        }

        # Check if Docker is running in rootless mode (optional check)
        exit_code, docker_info, _ = self.ssh.run_command(
            "docker info 2>/dev/null | grep -i rootless || echo 'standard'"
        )

        rootless = 'rootless' in docker_info.lower()
        checks['docker_rootless'] = {
            'passed': rootless,
            'message': 'Docker running rootless' if rootless else 'Docker running as root (STANDARD)'
        }

        return checks

    def _calculate_score(self, results: Dict) -> int:
        """
        Calculate overall security score (0-100)

        Args:
            results: Audit results dictionary

        Returns:
            Security score from 0 to 100
        """
        total_checks = 0
        passed_checks = 0

        # Count checks from each category
        for category in ['ssh', 'firewall', 'docker']:
            if category not in results:
                continue

            for check, result in results[category].items():
                if isinstance(result, dict) and 'passed' in result:
                    total_checks += 1
                    if result['passed']:
                        passed_checks += 1

        # Calculate base score
        if total_checks == 0:
            base_score = 0
        else:
            base_score = int((passed_checks / total_checks) * 100)

        # Penalty for security updates
        security_updates = results.get('updates', {}).get('security', 0)
        update_penalty = min(security_updates * 5, 20)  # Max 20 point penalty

        # Critical penalties
        critical_penalty = 0

        # Critical: Firewall not active
        if not results.get('firewall', {}).get('firewall_active', {}).get('passed', True):
            critical_penalty += 30

        # Critical: Root login enabled
        if not results.get('ssh', {}).get('root_login_disabled', {}).get('passed', True):
            critical_penalty += 15

        # Calculate final score
        final_score = base_score - update_penalty - critical_penalty
        return max(0, min(100, final_score))  # Clamp between 0-100


class Fail2BanManager:
    """Manages fail2ban jail monitoring and IP unbanning"""

    def __init__(self, ssh_manager):
        """
        Initialize fail2ban manager

        Args:
            ssh_manager: SSHManager instance
        """
        self.ssh = ssh_manager

    def get_jails(self) -> List[str]:
        """
        Get list of active fail2ban jails

        Returns:
            List of jail names
        """
        exit_code, output, _ = self.ssh.run_command("sudo fail2ban-client status")

        if exit_code != 0:
            return []

        # Parse jail list
        for line in output.split('\n'):
            if 'Jail list:' in line:
                jails_str = line.split('Jail list:')[1].strip()
                return [j.strip() for j in jails_str.split(',') if j.strip()]

        return []

    def get_jail_status(self, jail: str) -> Dict:
        """
        Get status of specific jail

        Args:
            jail: Jail name

        Returns:
            Dictionary with jail statistics
        """
        exit_code, output, _ = self.ssh.run_command(f"sudo fail2ban-client status {jail}")

        if exit_code != 0:
            return {'currently_banned': 0, 'total_banned': 0, 'banned_ips': []}

        stats = {
            'currently_banned': 0,
            'total_banned': 0,
            'banned_ips': []
        }

        for line in output.split('\n'):
            if 'Currently banned:' in line:
                try:
                    stats['currently_banned'] = int(line.split(':')[1].strip())
                except (ValueError, IndexError):
                    pass
            elif 'Total banned:' in line:
                try:
                    stats['total_banned'] = int(line.split(':')[1].strip())
                except (ValueError, IndexError):
                    pass
            elif 'Banned IP list:' in line:
                ips_str = line.split(':')[1].strip()
                if ips_str:
                    stats['banned_ips'] = [ip.strip() for ip in ips_str.split()]

        return stats

    def unban_ip(self, ip: str, jail: Optional[str] = None) -> None:
        """
        Unban an IP address from jail(s)

        Args:
            ip: IP address to unban
            jail: Specific jail name, or None to unban from all jails
        """
        if jail:
            # Unban from specific jail
            exit_code, _, stderr = self.ssh.run_command(
                f"sudo fail2ban-client set {jail} unbanip {ip}"
            )
            if exit_code != 0:
                raise RuntimeError(f"Failed to unban IP from {jail}: {stderr}")
        else:
            # Unban from all jails
            jails = self.get_jails()
            for jail_name in jails:
                try:
                    self.ssh.run_command(f"sudo fail2ban-client set {jail_name} unbanip {ip}")
                except Exception:
                    # Continue even if one jail fails
                    pass
