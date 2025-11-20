"""Centralized WordPress permissions management"""

from cli.utils.ssh import SSHManager


class PermissionsManager:
    """
    Manage WordPress file permissions systematically

    WordPress recommended permissions:
    - Core files: 755/644 (secure, read-only)
    - wp-content: 775/664 (group writable for plugins/uploads)
    - Owner: www-data:www-data
    """

    def __init__(self, ssh: SSHManager):
        self.ssh = ssh

    def set_wordpress_permissions(self, site_name: str, timeout: int = 120) -> bool:
        """
        Set correct WordPress permissions systematically

        This is the SINGLE SOURCE OF TRUTH for WordPress permissions.
        All other code should call this function.

        Args:
            site_name: Site name
            timeout: Command timeout in seconds

        Returns:
            True if successful
        """
        # Use wp container (has root access) not wpcli (runs as www-data)
        wp_container = f"{site_name}_wp"

        # Step 1: Set ownership to www-data:www-data
        exit_code, stdout, stderr = self.ssh.run_command(
            f"docker exec --user root {wp_container} chown -R www-data:www-data /var/www/html",
            timeout=timeout
        )
        if exit_code != 0:
            print(f"Failed to set ownership: {stderr}")
            return False

        # Step 2: Set core permissions (secure, read-only)
        # Directories: 755 (rwxr-xr-x)
        exit_code, stdout, stderr = self.ssh.run_command(
            f"docker exec --user root {wp_container} find /var/www/html -type d -exec chmod 755 {{}} \\;",
            timeout=timeout
        )
        if exit_code != 0:
            print(f"Failed to set directory permissions: {stderr}")
            return False

        # Files: 644 (rw-r--r--)
        exit_code, stdout, stderr = self.ssh.run_command(
            f"docker exec --user root {wp_container} find /var/www/html -type f -exec chmod 644 {{}} \\;",
            timeout=timeout
        )
        if exit_code != 0:
            print(f"Failed to set file permissions: {stderr}")
            return False

        # Step 3: Set wp-content permissions (group writable for WordPress operations)
        # Directories: 775 (rwxrwxr-x) - allows plugins to create folders
        exit_code, stdout, stderr = self.ssh.run_command(
            f"docker exec --user root {wp_container} find /var/www/html/wp-content -type d -exec chmod 775 {{}} \\;",
            timeout=timeout
        )
        if exit_code != 0:
            print(f"Failed to set wp-content directory permissions: {stderr}")
            return False

        # Files: 664 (rw-rw-r--) - allows plugins to write files
        exit_code, stdout, stderr = self.ssh.run_command(
            f"docker exec --user root {wp_container} find /var/www/html/wp-content -type f -exec chmod 664 {{}} \\;",
            timeout=timeout
        )
        if exit_code != 0:
            print(f"Failed to set wp-content file permissions: {stderr}")
            return False

        return True

    def verify_permissions(self, site_name: str) -> dict:
        """
        Verify WordPress permissions are correct

        Returns:
            dict with verification results
        """
        wpcli_container = f"{site_name}_wpcli"

        results = {
            "ownership": False,
            "core_dirs": False,
            "core_files": False,
            "wpcontent_dirs": False,
            "wpcontent_files": False
        }

        # Check ownership
        exit_code, stdout, _ = self.ssh.run_command(
            f"docker exec {wpcli_container} stat -c '%U:%G' /var/www/html",
            timeout=10
        )
        if exit_code == 0 and stdout.strip() == "www-data:www-data":
            results["ownership"] = True

        # Check wp-content directory permissions (should be 775)
        exit_code, stdout, _ = self.ssh.run_command(
            f"docker exec {wpcli_container} stat -c '%a' /var/www/html/wp-content",
            timeout=10
        )
        if exit_code == 0 and stdout.strip() == "775":
            results["wpcontent_dirs"] = True

        # Sample check: uploads directory (should be 775)
        exit_code, stdout, _ = self.ssh.run_command(
            f"docker exec {wpcli_container} stat -c '%a' /var/www/html/wp-content/uploads 2>/dev/null || echo 'missing'",
            timeout=10
        )
        if exit_code == 0 and stdout.strip() == "775":
            results["wpcontent_files"] = True

        return results
