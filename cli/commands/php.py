"""PHP configuration management commands"""

import typer
from typing import Optional
from cli.ui.console import print_success, print_error, print_info, print_warning
from cli.utils.config import ConfigManager
from cli.utils.ssh import SSHManager

app = typer.Typer(help="PHP configuration management")


def get_site_type(ssh: SSHManager, site_name: str) -> Optional[str]:
    """Detect site type (frankenwp or ols) from running containers"""
    # Check for FrankenWP container
    exit_code, _, _ = ssh.run_command(f"docker ps --filter name={site_name}_wp --format '{{{{.Names}}}}'")
    if exit_code == 0:
        return "frankenwp"

    # Check for OLS container
    exit_code, _, _ = ssh.run_command(f"docker ps --filter name={site_name}_ols --format '{{{{.Names}}}}'")
    if exit_code == 0:
        return "ols"

    return None


def update_frankenwp_limits(ssh: SSHManager, site_name: str, upload_max: str, memory_limit: str, post_max: str) -> bool:
    """Update PHP limits for FrankenWP site using .htaccess"""
    container_name = f"{site_name}_wp"

    # Create PHP limits configuration in .htaccess
    htaccess_content = f"""# BEGIN WordPress PHP Limits
php_value upload_max_filesize {upload_max}
php_value post_max_size {post_max}
php_value memory_limit {memory_limit}
php_value max_execution_time 300
php_value max_input_time 300
# END WordPress PHP Limits

# BEGIN WordPress
# The directives (lines) between "BEGIN WordPress" and "END WordPress" are
# dynamically generated, and should only be modified via WordPress filters.
# Any changes to the directives between these markers will be overwritten.
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteRule .* - [E=HTTP_AUTHORIZATION:%{{HTTP:Authorization}}]
RewriteBase /
RewriteRule ^index\\.php$ - [L]
RewriteCond %{{REQUEST_FILENAME}} !-f
RewriteCond %{{REQUEST_FILENAME}} !-d
RewriteRule . /index.php [L]
</IfModule>
# END WordPress
"""

    # Write to temporary file
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.htaccess') as tmp:
        tmp.write(htaccess_content)
        tmp_path = tmp.name

    try:
        # Copy to container
        exit_code, stdout, stderr = ssh.run_command(
            f"docker cp {tmp_path} {container_name}:/var/www/html/.htaccess"
        )

        if exit_code != 0:
            print_error(f"Failed to update .htaccess: {stderr}")
            return False

        # Set proper permissions
        ssh.run_command(f"docker exec {container_name} chown www-data:www-data /var/www/html/.htaccess")
        ssh.run_command(f"docker exec {container_name} chmod 644 /var/www/html/.htaccess")

        return True
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def update_ols_limits(ssh: SSHManager, site_name: str, domain: str, upload_max: str, memory_limit: str, post_max: str) -> bool:
    """Update PHP limits for OpenLiteSpeed site"""
    container_name = f"{site_name}_ols"

    # OpenLiteSpeed uses PHP ini settings
    # We need to create/update custom PHP ini file
    php_ini_content = f"""[PHP]
upload_max_filesize = {upload_max}
post_max_size = {post_max}
memory_limit = {memory_limit}
max_execution_time = 300
max_input_time = 300
max_input_vars = 5000
"""

    # Write to temporary file
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ini') as tmp:
        tmp.write(php_ini_content)
        tmp_path = tmp.name

    try:
        # Copy to container's PHP configuration directory
        exit_code, stdout, stderr = ssh.run_command(
            f"docker exec {container_name} mkdir -p /usr/local/lsws/lsphp80/etc/php.d/"
        )

        exit_code, stdout, stderr = ssh.run_command(
            f"docker cp {tmp_path} {container_name}:/usr/local/lsws/lsphp80/etc/php.d/99-custom.ini"
        )

        if exit_code != 0:
            print_error(f"Failed to update PHP ini: {stderr}")
            return False

        # Restart OpenLiteSpeed to apply changes
        exit_code, stdout, stderr = ssh.run_command(
            f"docker exec {container_name} /usr/local/lsws/bin/lswsctrl restart",
            timeout=30
        )

        if exit_code != 0:
            print_warning(f"OLS restart warning: {stderr}")

        return True
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.command("set-limits")
def set_php_limits(
    site_name: str = typer.Argument(..., help="Site name"),
    upload_max: str = typer.Option("256M", "--upload-max", help="Max upload file size (e.g., 256M, 1G)"),
    memory_limit: str = typer.Option("512M", "--memory-limit", help="PHP memory limit (e.g., 512M, 1G)"),
    post_max: Optional[str] = typer.Option(None, "--post-max", help="Max POST size (default: same as upload-max)")
):
    """Set PHP upload and memory limits for a site"""
    try:
        # Load config
        config_mgr = ConfigManager()
        config_mgr.load_config()

        # Check if site exists
        site = config_mgr.get_site(site_name)
        if not site:
            print_error(f"Site '{site_name}' not found")
            raise typer.Exit(code=1)

        # Default post_max to upload_max if not specified
        if post_max is None:
            post_max = upload_max

        # Validate size format
        import re
        size_pattern = r'^\d+[KMG]$'
        if not re.match(size_pattern, upload_max, re.IGNORECASE):
            print_error("Invalid upload_max format. Use format like: 256M, 1G, 512M")
            raise typer.Exit(code=1)

        if not re.match(size_pattern, memory_limit, re.IGNORECASE):
            print_error("Invalid memory_limit format. Use format like: 512M, 1G, 2G")
            raise typer.Exit(code=1)

        if not re.match(size_pattern, post_max, re.IGNORECASE):
            print_error("Invalid post_max format. Use format like: 256M, 1G, 512M")
            raise typer.Exit(code=1)

        print_info(f"Configuring PHP limits for '{site_name}'...")
        print_info(f"  Upload Max:   {upload_max}")
        print_info(f"  POST Max:     {post_max}")
        print_info(f"  Memory Limit: {memory_limit}\n")

        # Connect to VPS
        ssh = SSHManager(
            host=config_mgr.vps.host,
            port=config_mgr.vps.port,
            user=config_mgr.vps.user,
            key_path=config_mgr.vps.key_path
        )

        ssh.connect()

        # Detect site type
        site_type = get_site_type(ssh, site_name)
        if not site_type:
            print_error(f"Could not detect site type for '{site_name}'. Is the site running?")
            ssh.disconnect()
            raise typer.Exit(code=1)

        print_info(f"Detected site type: {site_type}")

        # Update limits based on site type
        success = False
        if site_type == "frankenwp":
            success = update_frankenwp_limits(ssh, site_name, upload_max, memory_limit, post_max)
        elif site_type == "ols":
            domain = site.domain
            success = update_ols_limits(ssh, site_name, domain, upload_max, memory_limit, post_max)

        ssh.disconnect()

        if success:
            print_success(f"\n✓ PHP limits updated for '{site_name}'")
            print_info("\nNew limits:")
            print_info(f"  • Max upload file size: {upload_max}")
            print_info(f"  • Max POST size:        {post_max}")
            print_info(f"  • PHP memory limit:     {memory_limit}")
            print_info(f"  • Max execution time:   300s")

            if site_type == "ols":
                print_info("\n⚠ OpenLiteSpeed has been restarted to apply changes")
        else:
            print_error("Failed to update PHP limits")
            raise typer.Exit(code=1)

    except Exception as e:
        print_error(f"Error: {e}")
        raise typer.Exit(code=1)


@app.command("show-limits")
def show_php_limits(
    site_name: str = typer.Argument(..., help="Site name")
):
    """Show current PHP limits for a site"""
    try:
        # Load config
        config_mgr = ConfigManager()
        config_mgr.load_config()

        # Check if site exists
        site = config_mgr.get_site(site_name)
        if not site:
            print_error(f"Site '{site_name}' not found")
            raise typer.Exit(code=1)

        # Connect to VPS
        ssh = SSHManager(
            host=config_mgr.vps.host,
            port=config_mgr.vps.port,
            user=config_mgr.vps.user,
            key_path=config_mgr.vps.key_path
        )

        ssh.connect()

        # Detect site type
        site_type = get_site_type(ssh, site_name)
        if not site_type:
            print_error(f"Could not detect site type for '{site_name}'. Is the site running?")
            ssh.disconnect()
            raise typer.Exit(code=1)

        # Get container name
        container_name = f"{site_name}_wp" if site_type == "frankenwp" else f"{site_name}_ols"

        print_info(f"PHP Limits for '{site_name}' ({site_type}):\n")

        # Get PHP info using WP-CLI
        wpcli_container = f"{site_name}_wpcli"

        # Check key PHP settings
        settings = [
            "upload_max_filesize",
            "post_max_size",
            "memory_limit",
            "max_execution_time",
            "max_input_time"
        ]

        for setting in settings:
            exit_code, value, stderr = ssh.run_command(
                f"docker exec {wpcli_container} wp eval 'echo ini_get(\"{setting}\");' 2>/dev/null",
                timeout=10
            )
            if exit_code == 0 and value.strip():
                print_info(f"  • {setting.replace('_', ' ').title()}: {value.strip()}")
            else:
                print_warning(f"  • {setting.replace('_', ' ').title()}: Unable to retrieve")

        ssh.disconnect()

    except Exception as e:
        print_error(f"Error: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
