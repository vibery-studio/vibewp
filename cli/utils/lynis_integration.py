"""Lynis security audit tool integration"""

from typing import Dict, Optional
import re


class LynisIntegration:
    """Integration with Lynis security audit tool"""

    def __init__(self, ssh_manager):
        """
        Initialize Lynis integration

        Args:
            ssh_manager: SSHManager instance
        """
        self.ssh = ssh_manager

    def is_installed(self) -> bool:
        """
        Check if Lynis is installed

        Returns:
            True if Lynis is installed
        """
        exit_code, _, _ = self.ssh.run_command("which lynis")
        return exit_code == 0

    def get_version(self) -> Optional[str]:
        """
        Get installed Lynis version

        Returns:
            Version string or None
        """
        if not self.is_installed():
            return None

        exit_code, output, _ = self.ssh.run_command("lynis show version 2>/dev/null")
        if exit_code == 0:
            # Parse version from output
            match = re.search(r'(\d+\.\d+\.\d+)', output)
            if match:
                return match.group(1)

        return None

    def run_audit(self, quick: bool = True) -> Dict:
        """
        Run Lynis system audit

        Args:
            quick: Run quick scan (default: True)

        Returns:
            Dictionary with Lynis audit results
        """
        if not self.is_installed():
            return {
                'installed': False,
                'hardening_index': 0,
                'findings': [],
                'suggestions': [],
                'warnings': []
            }

        # Run Lynis audit
        cmd = "sudo lynis audit system"
        if quick:
            cmd += " --quick"
        cmd += " --quiet --no-colors"

        exit_code, output, _ = self.ssh.run_command(cmd, timeout=300)

        if exit_code != 0:
            return {
                'installed': True,
                'error': 'Lynis audit failed',
                'hardening_index': 0,
                'findings': [],
                'suggestions': [],
                'warnings': []
            }

        # Parse Lynis output
        results = self._parse_lynis_output(output)
        results['installed'] = True

        return results

    def get_hardening_index(self) -> Optional[int]:
        """
        Get system hardening index (0-100)

        Returns:
            Hardening index or None if unavailable
        """
        if not self.is_installed():
            return None

        # Check for last audit report
        exit_code, output, _ = self.ssh.run_command(
            "sudo grep 'Hardening index' /var/log/lynis.log 2>/dev/null | tail -1"
        )

        if exit_code == 0 and output.strip():
            # Extract index from log
            match = re.search(r'(\d+)', output)
            if match:
                return int(match.group(1))

        return None

    def _parse_lynis_output(self, output: str) -> Dict:
        """
        Parse Lynis audit output

        Args:
            output: Lynis command output

        Returns:
            Parsed results dictionary
        """
        results = {
            'hardening_index': 0,
            'tests_performed': 0,
            'findings': [],
            'suggestions': [],
            'warnings': []
        }

        current_section = None

        for line in output.split('\n'):
            line = line.strip()

            if not line:
                continue

            # Extract hardening index
            if 'Hardening index' in line or 'hardening_index' in line.lower():
                match = re.search(r'(\d+)', line)
                if match:
                    results['hardening_index'] = int(match.group(1))

            # Extract tests performed
            if 'Tests performed' in line:
                match = re.search(r'(\d+)', line)
                if match:
                    results['tests_performed'] = int(match.group(1))

            # Identify sections
            if '[WARNING]' in line or 'Warning:' in line:
                current_section = 'warnings'
                warning_text = line.replace('[WARNING]', '').replace('Warning:', '').strip()
                if warning_text:
                    results['warnings'].append(warning_text)

            elif '[SUGGESTION]' in line or 'Suggestion:' in line:
                current_section = 'suggestions'
                suggestion_text = line.replace('[SUGGESTION]', '').replace('Suggestion:', '').strip()
                if suggestion_text:
                    results['suggestions'].append(suggestion_text)

            elif current_section == 'warnings' and line and not line.startswith('['):
                results['warnings'].append(line)

            elif current_section == 'suggestions' and line and not line.startswith('['):
                results['suggestions'].append(line)

        return results

    def convert_to_findings(self, lynis_results: Dict) -> list:
        """
        Convert Lynis results to standard finding format

        Args:
            lynis_results: Parsed Lynis results

        Returns:
            List of findings in standard format
        """
        findings = []

        # Convert warnings to high severity findings
        for idx, warning in enumerate(lynis_results.get('warnings', [])):
            findings.append({
                'id': f'LYN-W-{idx+1:03d}',
                'severity': 'high',
                'title': 'Lynis Warning',
                'description': warning,
                'impact': 'Security configuration issue detected by Lynis',
                'remediation': 'Review Lynis documentation for details',
                'auto_fix': None
            })

        # Convert suggestions to medium severity findings
        for idx, suggestion in enumerate(lynis_results.get('suggestions', [])):
            findings.append({
                'id': f'LYN-S-{idx+1:03d}',
                'severity': 'medium',
                'title': 'Lynis Suggestion',
                'description': suggestion,
                'impact': 'Recommended security improvement',
                'remediation': 'Review Lynis documentation for implementation',
                'auto_fix': None
            })

        # Add hardening index as finding if low
        hardening_index = lynis_results.get('hardening_index', 0)
        if hardening_index < 60:
            findings.append({
                'id': 'LYN-INDEX',
                'severity': 'high',
                'title': f'Low system hardening index: {hardening_index}',
                'description': f'Lynis hardening index is {hardening_index}/100',
                'impact': 'System may have multiple security weaknesses',
                'remediation': 'Address Lynis warnings and suggestions to improve score',
                'auto_fix': None
            })
        elif hardening_index < 80:
            findings.append({
                'id': 'LYN-INDEX',
                'severity': 'medium',
                'title': f'Moderate system hardening index: {hardening_index}',
                'description': f'Lynis hardening index is {hardening_index}/100',
                'impact': 'System security could be improved',
                'remediation': 'Address Lynis suggestions to improve score',
                'auto_fix': None
            })

        return findings

    def get_install_instructions(self) -> str:
        """
        Get installation instructions for Lynis

        Returns:
            Installation command string
        """
        return """
# Install Lynis on Ubuntu/Debian
sudo apt-get update
sudo apt-get install lynis

# Or install latest version from GitHub
cd /tmp
git clone https://github.com/CISOfy/lynis
cd lynis
sudo ./lynis audit system --quick
"""
