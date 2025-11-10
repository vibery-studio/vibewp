"""UFW firewall management utilities"""

from typing import List, Dict, Optional


class FirewallManager:
    """Manages UFW firewall operations"""

    def __init__(self, ssh_manager):
        """
        Initialize firewall manager

        Args:
            ssh_manager: SSHManager instance for remote command execution
        """
        self.ssh = ssh_manager

    def get_rules(self) -> List[Dict[str, str]]:
        """
        Get all UFW firewall rules

        Returns:
            List of rule dictionaries with num, port, protocol, action, from fields
        """
        exit_code, output, _ = self.ssh.run_command("sudo ufw status numbered")
        if exit_code != 0:
            return []

        return self._parse_rules(output)

    def is_port_open(self, port: int, protocol: str = "tcp") -> bool:
        """
        Check if port is already open in firewall

        Args:
            port: Port number
            protocol: Protocol (tcp/udp)

        Returns:
            True if port is open, False otherwise
        """
        rules = self.get_rules()
        for rule in rules:
            if rule['port'] == str(port) and rule['protocol'] == protocol:
                return True
        return False

    def open_port(self, port: int, protocol: str = "tcp", limit: bool = False) -> None:
        """
        Open a port in the firewall

        Args:
            port: Port number to open
            protocol: Protocol (tcp/udp)
            limit: Use LIMIT instead of ALLOW (rate limiting for brute force protection)
        """
        action = "limit" if limit else "allow"
        cmd = f"sudo ufw {action} {port}/{protocol}"
        exit_code, _, stderr = self.ssh.run_command(cmd)

        if exit_code != 0:
            raise RuntimeError(f"Failed to open port: {stderr}")

        # Reload firewall to apply changes
        self.ssh.run_command("sudo ufw reload")

    def close_port(self, port: int, protocol: str = "tcp") -> None:
        """
        Close a port in the firewall

        Args:
            port: Port number to close
            protocol: Protocol (tcp/udp)
        """
        # Find rule number first
        rules = self.get_rules()
        rule_num = None

        for rule in rules:
            if rule['port'] == str(port) and rule['protocol'] == protocol:
                rule_num = rule['num']
                break

        if not rule_num:
            raise ValueError(f"Port {port}/{protocol} not found in firewall rules")

        # Delete by rule number (more reliable)
        cmd = f"echo 'y' | sudo ufw delete {rule_num}"
        exit_code, _, stderr = self.ssh.run_command(cmd)

        if exit_code != 0:
            raise RuntimeError(f"Failed to close port: {stderr}")

        # Reload firewall
        self.ssh.run_command("sudo ufw reload")

    def get_status(self) -> Dict[str, any]:
        """
        Get firewall status and statistics

        Returns:
            Dictionary with active status, default policies, and rule count
        """
        exit_code, output, _ = self.ssh.run_command("sudo ufw status verbose")
        if exit_code != 0:
            return {
                'active': 'unknown',
                'default_incoming': 'unknown',
                'default_outgoing': 'unknown',
                'total_rules': 0
            }

        status = self._parse_status(output)

        # Get rule count
        rules = self.get_rules()
        status['total_rules'] = len(rules)

        return status

    def _parse_rules(self, output: str) -> List[Dict[str, str]]:
        """
        Parse UFW rules from command output

        Args:
            output: Output from 'ufw status numbered'

        Returns:
            List of parsed rules
        """
        rules = []

        for line in output.split('\n'):
            # Look for lines with brackets indicating rule numbers
            # Example: [ 1] 2222/tcp                   LIMIT IN    Anywhere
            if '[' not in line or ']' not in line:
                continue

            try:
                # Extract rule number
                num_part = line.split(']')[0].strip('[').strip()

                # Split the rest of the line
                rest = line.split(']')[1].strip()
                parts = rest.split()

                if len(parts) >= 4:
                    # Parse port/protocol
                    port_proto = parts[0].split('/')
                    port = port_proto[0]
                    protocol = port_proto[1] if len(port_proto) > 1 else 'tcp'

                    # Parse action and direction
                    action = parts[1]
                    direction = parts[2] if len(parts) > 2 else ''

                    # Parse source
                    from_addr = ' '.join(parts[3:]) if len(parts) > 3 else 'Anywhere'

                    rules.append({
                        'num': num_part,
                        'port': port,
                        'protocol': protocol,
                        'action': f"{action} {direction}".strip(),
                        'from': from_addr
                    })

            except (IndexError, ValueError):
                # Skip malformed lines
                continue

        return rules

    def _parse_status(self, output: str) -> Dict[str, str]:
        """
        Parse UFW status output

        Args:
            output: Output from 'ufw status verbose'

        Returns:
            Dictionary with status information
        """
        status = {
            'active': 'inactive',
            'default_incoming': 'deny',
            'default_outgoing': 'allow'
        }

        for line in output.split('\n'):
            line_lower = line.lower()

            if 'status:' in line_lower:
                status['active'] = line.split(':')[1].strip()
            elif 'default:' in line_lower:
                # Parse default policies
                # Example: "Default: deny (incoming), allow (outgoing), disabled (routed)"
                if 'incoming' in line_lower:
                    parts = line.lower().split('incoming')
                    if len(parts) > 0:
                        # Extract the policy before 'incoming'
                        policy_part = parts[0].split()[-1] if parts[0].split() else 'deny'
                        status['default_incoming'] = policy_part.strip('(),')

                if 'outgoing' in line_lower:
                    parts = line.lower().split('outgoing')
                    if len(parts) > 0:
                        # Extract the policy before 'outgoing'
                        policy_part = parts[0].split()[-1] if parts[0].split() else 'allow'
                        status['default_outgoing'] = policy_part.strip('(),')

        return status
