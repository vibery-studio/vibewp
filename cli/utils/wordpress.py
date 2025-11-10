"""WordPress management utilities for VibeWP CLI"""

from typing import Dict, Optional


class WordPressManager:
    """Manages WordPress installations via WP-CLI"""

    def __init__(self, ssh_manager):
        """
        Initialize WordPress manager

        Args:
            ssh_manager: SSHManager instance for remote operations
        """
        self.ssh = ssh_manager

    def install_wpcli(self) -> bool:
        """
        Install WP-CLI on VPS if not already installed

        Returns:
            True if installation successful or already installed
        """
        try:
            # Check if WP-CLI is already installed
            exit_code, stdout, stderr = self.ssh.run_command("which wp")
            if exit_code == 0:
                return True

            # Install WP-CLI
            commands = [
                "curl -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar",
                "chmod +x wp-cli.phar",
                "sudo mv wp-cli.phar /usr/local/bin/wp"
            ]

            for cmd in commands:
                exit_code, stdout, stderr = self.ssh.run_command(cmd, timeout=60)
                if exit_code != 0:
                    raise RuntimeError(f"WP-CLI installation failed: {stderr}")

            # Verify installation
            exit_code, stdout, stderr = self.ssh.run_command("wp --info")
            return exit_code == 0

        except Exception as e:
            raise RuntimeError(f"Failed to install WP-CLI: {e}")

    def core_install(
        self,
        container_name: str,
        site_config: Dict[str, str],
        wp_type: str = "frankenwp"
    ) -> bool:
        """
        Install WordPress via WP-CLI

        Args:
            container_name: WordPress container name
            site_config: Site configuration dictionary
            wp_type: WordPress type (frankenwp or ols)

        Returns:
            True if installation successful
        """
        try:
            # Determine WordPress path based on type
            wp_path = "/var/www/html" if wp_type == "frankenwp" else f"/var/www/vhosts/{site_config['domain']}"

            # Build WP-CLI command
            cmd = f"""docker exec {container_name} wp core install \\
                --path={wp_path} \\
                --url=https://{site_config['domain']} \\
                --title='{site_config.get('site_title', site_config['domain'])}' \\
                --admin_user={site_config['wp_admin_user']} \\
                --admin_password='{site_config['wp_admin_password']}' \\
                --admin_email={site_config['wp_admin_email']} \\
                --skip-email \\
                --allow-root"""

            exit_code, stdout, stderr = self.ssh.run_command(cmd, timeout=120)

            if exit_code != 0:
                # Check if already installed
                if "already installed" in stderr.lower() or "already installed" in stdout.lower():
                    return True
                raise RuntimeError(f"WordPress installation failed: {stderr}")

            return True

        except Exception as e:
            raise RuntimeError(f"Failed to install WordPress: {e}")

    def update_site_url(
        self,
        container_name: str,
        url: str,
        wp_type: str = "frankenwp",
        domain: Optional[str] = None
    ) -> bool:
        """
        Update WordPress site URL

        Args:
            container_name: WordPress container name
            url: New site URL
            wp_type: WordPress type (frankenwp or ols)
            domain: Domain name (required for ols)

        Returns:
            True if update successful
        """
        try:
            # Determine WordPress path based on type
            if wp_type == "frankenwp":
                wp_path = "/var/www/html"
            else:  # ols
                if not domain:
                    raise ValueError("Domain is required for OLS WordPress type")
                wp_path = f"/var/www/vhosts/{domain}"

            commands = [
                f"docker exec {container_name} wp option update siteurl '{url}' --path={wp_path} --allow-root",
                f"docker exec {container_name} wp option update home '{url}' --path={wp_path} --allow-root"
            ]

            for cmd in commands:
                exit_code, stdout, stderr = self.ssh.run_command(cmd, timeout=30)
                if exit_code != 0:
                    raise RuntimeError(f"URL update failed: {stderr}")

            return True

        except Exception as e:
            raise RuntimeError(f"Failed to update site URL: {e}")

    def plugin_install(
        self,
        container_name: str,
        plugin_slug: str,
        activate: bool = True,
        wp_type: str = "frankenwp"
    ) -> bool:
        """
        Install WordPress plugin

        Args:
            container_name: WordPress container name
            plugin_slug: Plugin slug
            activate: Activate after installation
            wp_type: WordPress type (frankenwp or ols)

        Returns:
            True if installation successful
        """
        try:
            wp_path = "/var/www/html" if wp_type == "frankenwp" else "/var/www/vhosts"

            cmd = f"docker exec {container_name} wp plugin install {plugin_slug} --path={wp_path} --allow-root"
            if activate:
                cmd += " --activate"

            exit_code, stdout, stderr = self.ssh.run_command(cmd, timeout=120)

            if exit_code != 0 and "already installed" not in stderr.lower():
                raise RuntimeError(f"Plugin installation failed: {stderr}")

            return True

        except Exception as e:
            raise RuntimeError(f"Failed to install plugin: {e}")

    def get_wp_version(
        self,
        container_name: str,
        wp_type: str = "frankenwp"
    ) -> Optional[str]:
        """
        Get WordPress version

        Args:
            container_name: WordPress container name
            wp_type: WordPress type (frankenwp or ols)

        Returns:
            WordPress version string or None if error
        """
        try:
            wp_path = "/var/www/html" if wp_type == "frankenwp" else "/var/www/vhosts"

            exit_code, stdout, stderr = self.ssh.run_command(
                f"docker exec {container_name} wp core version --path={wp_path} --allow-root",
                timeout=30
            )

            if exit_code == 0:
                return stdout.strip()

        except Exception:
            pass

        return None

    def create_user(
        self,
        container_name: str,
        username: str,
        email: str,
        role: str = "administrator",
        wp_type: str = "frankenwp"
    ) -> Optional[str]:
        """
        Create WordPress user

        Args:
            container_name: WordPress container name
            username: Username
            email: User email
            role: User role (default: administrator)
            wp_type: WordPress type (frankenwp or ols)

        Returns:
            Generated password or None if error
        """
        try:
            from cli.utils.credentials import CredentialGenerator

            password = CredentialGenerator.generate_password(16, False)
            wp_path = "/var/www/html" if wp_type == "frankenwp" else "/var/www/vhosts"

            cmd = f"""docker exec {container_name} wp user create {username} {email} \\
                --role={role} \\
                --user_pass='{password}' \\
                --path={wp_path} \\
                --allow-root"""

            exit_code, stdout, stderr = self.ssh.run_command(cmd, timeout=60)

            if exit_code == 0:
                return password

        except Exception:
            pass

        return None

    def update_option(
        self,
        container_name: str,
        option_name: str,
        option_value: str,
        wp_type: str = "frankenwp"
    ) -> bool:
        """
        Update WordPress option

        Args:
            container_name: WordPress container name
            option_name: Option name
            option_value: Option value
            wp_type: WordPress type (frankenwp or ols)

        Returns:
            True if update successful
        """
        try:
            wp_path = "/var/www/html" if wp_type == "frankenwp" else "/var/www/vhosts"

            cmd = f"docker exec {container_name} wp option update {option_name} '{option_value}' --path={wp_path} --allow-root"

            exit_code, stdout, stderr = self.ssh.run_command(cmd, timeout=30)
            return exit_code == 0

        except Exception:
            return False
