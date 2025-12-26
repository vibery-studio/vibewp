"""Credential generation utilities for VibeWP CLI"""

import secrets
import string
from typing import Dict


class CredentialGenerator:
    """Generate secure credentials for WordPress sites"""

    @staticmethod
    def generate_password(length: int = 32, special_chars: bool = True) -> str:
        """
        Generate cryptographically secure random password

        Args:
            length: Password length (default 32)
            special_chars: Include special characters (default True)

        Returns:
            Secure random password string
        """
        alphabet = string.ascii_letters + string.digits
        if special_chars:
            # Use shell-safe special characters
            alphabet += "!@#^*-_=+"

        return ''.join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def generate_site_credentials(site_name: str, admin_email: str) -> Dict[str, str]:
        """
        Generate all credentials for a WordPress site

        Args:
            site_name: Unique site identifier
            admin_email: Admin email address

        Returns:
            Dictionary containing all site credentials
        """
        # Generate secure passwords
        db_password = CredentialGenerator.generate_password(32, True)
        # Sanitize site_name for database (replace hyphens with underscores)
        # MariaDB has issues with hyphens in database names in GRANT statements
        db_safe_name = site_name.replace('-', '_')
        db_root_password = CredentialGenerator.generate_password(32, True)
        wp_admin_password = CredentialGenerator.generate_password(16, False)

        # For OLS, generate admin password
        lsws_admin_pass = CredentialGenerator.generate_password(16, False)

        return {
            # Database credentials
            'db_name': f'wp_{db_safe_name}',
            'db_user': f'wp_{db_safe_name}_user',
            'db_password': db_password,
            'db_root_password': db_root_password,

            # WordPress admin credentials
            'wp_admin_user': 'admin',
            'wp_admin_password': wp_admin_password,
            'wp_admin_email': admin_email,

            # OLS admin credentials
            'lsws_admin_user': 'admin',
            'lsws_admin_pass': lsws_admin_pass,
        }

    @staticmethod
    def generate_wp_salts() -> Dict[str, str]:
        """
        Generate WordPress security salts

        Returns:
            Dictionary of WordPress salt keys
        """
        salt_keys = [
            'AUTH_KEY',
            'SECURE_AUTH_KEY',
            'LOGGED_IN_KEY',
            'NONCE_KEY',
            'AUTH_SALT',
            'SECURE_AUTH_SALT',
            'LOGGED_IN_SALT',
            'NONCE_SALT',
        ]

        return {
            key: CredentialGenerator.generate_password(64, True)
            for key in salt_keys
        }
