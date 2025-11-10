"""Caddy configuration management for VibeWP CLI"""

import yaml
import ssl
import socket
from typing import List, Dict, Optional
from datetime import datetime


class CaddyManager:
    """Manages Caddy labels in docker-compose files"""

    def __init__(self, ssh_manager, base_path: str = "/opt/vibewp"):
        """
        Initialize Caddy manager

        Args:
            ssh_manager: SSHManager instance
            base_path: Base path for sites on VPS
        """
        self.ssh = ssh_manager
        self.base_path = base_path

    def get_compose_path(self, site_name: str) -> str:
        """Get docker-compose.yml path for site"""
        return f"{self.base_path}/sites/{site_name}/docker-compose.yml"

    def get_site_domains(self, site_name: str) -> List[str]:
        """
        Get current domains from compose file

        Args:
            site_name: Site name

        Returns:
            List of domains configured in Caddy labels
        """
        compose_path = self.get_compose_path(site_name)

        # Read compose file
        exit_code, content, stderr = self.ssh.run_command(f"cat {compose_path}")

        # If compose file doesn't exist, try reading from Docker container labels
        if exit_code != 0:
            container_name = f"{site_name}_wp"
            exit_code2, label_content, _ = self.ssh.run_command(
                f"docker inspect {container_name} --format '{{{{index .Config.Labels \"caddy\"}}}}' 2>/dev/null"
            )
            if exit_code2 == 0 and label_content.strip():
                # Parse domains from Caddy label
                import re
                domains = re.findall(r'([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', label_content)
                if domains:
                    return list(set(domains))
            raise RuntimeError(f"Failed to read compose file: {stderr}")

        # Parse YAML
        compose_data = yaml.safe_load(content)

        # Extract Caddy label
        try:
            labels = compose_data['services']['wordpress']['labels']
            caddy_label = labels.get('caddy', '')

            if not caddy_label:
                return []

            return caddy_label.split()
        except (KeyError, TypeError) as e:
            raise RuntimeError(f"Invalid compose file structure: {e}")

    def update_labels(self, site_name: str, domains: List[str]) -> None:
        """
        Update Caddy labels with new domain list

        Args:
            site_name: Site name
            domains: List of domains to set
        """
        if not domains:
            raise ValueError("At least one domain is required")

        compose_path = self.get_compose_path(site_name)

        # Read compose file
        exit_code, content, stderr = self.ssh.run_command(f"cat {compose_path}")
        if exit_code != 0:
            raise RuntimeError(f"Failed to read compose file: {stderr}")

        # Parse YAML
        compose_data = yaml.safe_load(content)

        # Update Caddy label
        try:
            compose_data['services']['wordpress']['labels']['caddy'] = ' '.join(domains)
        except KeyError as e:
            raise RuntimeError(f"Invalid compose file structure: {e}")

        # Write updated compose file
        updated_content = yaml.dump(compose_data, default_flow_style=False, sort_keys=False)

        # Upload via temp file
        temp_path = f"/tmp/{site_name}-compose.yml"

        # Create temp file locally
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yml') as tmp:
            tmp.write(updated_content)
            local_temp = tmp.name

        try:
            # Upload temp file
            self.ssh.upload_file(local_temp, temp_path)

            # Move to final location
            exit_code, stdout, stderr = self.ssh.run_command(f"mv {temp_path} {compose_path}")
            if exit_code != 0:
                raise RuntimeError(f"Failed to update compose file: {stderr}")
        finally:
            # Clean up local temp file
            import os
            if os.path.exists(local_temp):
                os.remove(local_temp)

    def add_domain(self, site_name: str, domain: str) -> None:
        """
        Add domain to site

        Args:
            site_name: Site name
            domain: Domain to add
        """
        current_domains = self.get_site_domains(site_name)

        if domain in current_domains:
            raise ValueError(f"Domain '{domain}' already exists on site '{site_name}'")

        current_domains.append(domain)
        self.update_labels(site_name, current_domains)

    def remove_domain(self, site_name: str, domain: str) -> None:
        """
        Remove domain from site

        Args:
            site_name: Site name
            domain: Domain to remove
        """
        current_domains = self.get_site_domains(site_name)

        if domain not in current_domains:
            raise ValueError(f"Domain '{domain}' not found on site '{site_name}'")

        if len(current_domains) == 1:
            raise ValueError("Cannot remove the last domain from site")

        current_domains.remove(domain)
        self.update_labels(site_name, current_domains)

    def reload_caddy(self, site_name: str) -> None:
        """
        Reload Caddy configuration (apply changes without downtime)

        Args:
            site_name: Site name
        """
        site_dir = f"{self.base_path}/sites/{site_name}"

        # Use docker compose up -d to apply changes (zero downtime)
        exit_code, stdout, stderr = self.ssh.run_command(
            f"cd {site_dir} && docker compose up -d",
            timeout=120
        )

        if exit_code != 0:
            raise RuntimeError(f"Failed to reload Caddy: {stderr}")

    def get_cert_status(self, domain: str) -> Dict[str, str]:
        """
        Get SSL certificate status for domain

        Args:
            domain: Domain name

        Returns:
            Dictionary with certificate information
        """
        try:
            # Create SSL context
            context = ssl.create_default_context()

            # Connect and get certificate
            with socket.create_connection((domain, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()

                    # Parse certificate info
                    subject = dict(x[0] for x in cert['subject'])
                    issuer = dict(x[0] for x in cert['issuer'])

                    # Parse dates
                    not_before = cert['notBefore']
                    not_after = cert['notAfter']

                    # Calculate days until expiry
                    expiry_date = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
                    days_left = (expiry_date - datetime.now()).days

                    return {
                        'domain': domain,
                        'status': 'valid',
                        'subject_cn': subject.get('commonName', 'Unknown'),
                        'issuer_cn': issuer.get('commonName', 'Unknown'),
                        'issuer_org': issuer.get('organizationName', 'Unknown'),
                        'not_before': not_before,
                        'not_after': not_after,
                        'days_until_expiry': days_left,
                        'is_expired': days_left < 0
                    }

        except ssl.SSLError as e:
            return {
                'domain': domain,
                'status': 'ssl_error',
                'error': str(e)
            }
        except socket.timeout:
            return {
                'domain': domain,
                'status': 'timeout',
                'error': 'Connection timeout'
            }
        except socket.gaierror:
            return {
                'domain': domain,
                'status': 'dns_error',
                'error': 'DNS resolution failed'
            }
        except Exception as e:
            return {
                'domain': domain,
                'status': 'error',
                'error': str(e)
            }
