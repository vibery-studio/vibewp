"""DNS verification utilities for VibeWP CLI"""

import socket
import time
from typing import Optional, Tuple


class DNSValidator:
    """DNS validation and verification"""

    def __init__(self, vps_ip: str):
        """
        Initialize DNS validator

        Args:
            vps_ip: Expected VPS IP address
        """
        self.vps_ip = vps_ip

    def verify_dns(self, domain: str, timeout: int = 10) -> Tuple[bool, Optional[str]]:
        """
        Verify domain DNS A record points to VPS

        Args:
            domain: Domain name to verify
            timeout: Verification timeout in seconds

        Returns:
            Tuple of (success: bool, resolved_ip: Optional[str])
        """
        try:
            # Set socket timeout
            socket.setdefaulttimeout(timeout)

            # Resolve domain to IP
            resolved_ip = socket.gethostbyname(domain)

            # Check if resolved IP matches VPS IP
            if resolved_ip == self.vps_ip:
                return True, resolved_ip
            else:
                return False, resolved_ip

        except socket.gaierror:
            # DNS resolution failed (domain not configured)
            return False, None
        except socket.timeout:
            # DNS resolution timeout
            return False, None
        except Exception as e:
            # Other errors
            return False, None
        finally:
            # Reset socket timeout
            socket.setdefaulttimeout(None)

    def wait_for_dns_propagation(
        self,
        domain: str,
        timeout: int = 300,
        check_interval: int = 5
    ) -> bool:
        """
        Wait for DNS propagation to complete

        Args:
            domain: Domain name to check
            timeout: Maximum wait time in seconds (default: 5 minutes)
            check_interval: Seconds between checks

        Returns:
            True if DNS propagated successfully, False if timeout
        """
        start_time = time.time()
        elapsed_time = 0

        while elapsed_time < timeout:
            success, resolved_ip = self.verify_dns(domain, timeout=10)

            if success:
                return True

            # Wait before next check
            time.sleep(check_interval)
            elapsed_time = time.time() - start_time

        return False

    def get_domain_ip(self, domain: str) -> Optional[str]:
        """
        Get current IP address for domain

        Args:
            domain: Domain name

        Returns:
            IP address or None if resolution fails
        """
        try:
            return socket.gethostbyname(domain)
        except:
            return None

    def is_wildcard_domain(self, domain: str) -> bool:
        """
        Check if domain is wildcard format

        Args:
            domain: Domain name

        Returns:
            True if wildcard domain (*.example.com)
        """
        return domain.startswith('*.')
