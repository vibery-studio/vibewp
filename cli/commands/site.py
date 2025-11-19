"""Site management commands for VibeWP CLI"""

import os
import time
import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

from cli.utils.config import ConfigManager, SiteConfig
from cli.utils.ssh import SSHManager
from cli.utils.template import TemplateRenderer
from cli.utils.credentials import CredentialGenerator
from cli.utils.health import HealthChecker
from cli.utils.wordpress import WordPressManager
from cli.ui.console import print_success, print_error, print_info, print_warning

console = Console()
app = typer.Typer(help="Site management commands")


def rollback_site_creation(site_name: str, ssh: SSHManager, remote_dir: str):
    """
    Rollback failed site creation

    Args:
        site_name: Site name
        ssh: SSH manager
        remote_dir: Remote site directory
    """
    try:
        print_warning(f"Rolling back site creation for {site_name}...")

        # Stop and remove containers
        exit_code, stdout, stderr = ssh.run_command(
            f"cd {remote_dir} && docker compose down -v",
            timeout=60
        )

        # Remove site directory
        ssh.run_command(f"rm -rf {remote_dir}")

        print_info("Rollback completed")

    except Exception as e:
        print_error(f"Rollback failed: {e}")


@app.command("create")
def create_site(
    site_name: Optional[str] = typer.Option(None, help="Site name (alphanumeric)"),
    domain: Optional[str] = typer.Option(None, help="Domain name"),
    wp_type: Optional[str] = typer.Option(None, help="WordPress type (frankenwp/ols)"),
    admin_email: Optional[str] = typer.Option(None, help="Admin email"),
    site_title: Optional[str] = typer.Option(None, help="Site title"),
    db_mode: Optional[str] = typer.Option(None, "--db-mode", help="Database mode (shared/dedicated, defaults to config)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Create a new WordPress site"""

    try:
        # Load config
        config_mgr = ConfigManager()
        config_mgr.load_config()

        # Interactive prompts if not provided
        # Handle both None and OptionInfo objects from typer
        if not site_name or not isinstance(site_name, str):
            site_name = typer.prompt("Site name (alphanumeric, underscores)")

        # Ensure site_name is a string and validate
        site_name = str(site_name).strip()
        if not site_name or not site_name.replace('_', '').replace('-', '').isalnum():
            print_error("Site name must be alphanumeric with underscores/hyphens")
            raise typer.Exit(code=1)

        # Check if site already exists
        if config_mgr.get_site(site_name):
            print_error(f"Site '{site_name}' already exists")
            raise typer.Exit(code=1)

        if not domain or not isinstance(domain, str):
            domain = typer.prompt("Domain name")
        domain = str(domain).strip()

        if not wp_type or not isinstance(wp_type, str):
            console.print("\n[bold cyan]Choose WordPress Engine:[/bold cyan]")
            console.print("  [green]1. frankenwp[/green] - FrankenPHP (high performance, Go-based)")
            console.print("  [green]2. ols[/green] - OpenLiteSpeed (proven stability, LiteSpeed Cache)")
            wp_choice = typer.prompt("Select engine", type=int, default=1)
            wp_type = "frankenwp" if wp_choice == 1 else "ols"

        wp_type = str(wp_type).strip().lower()
        if wp_type not in ["frankenwp", "ols"]:
            print_error("Invalid WordPress type. Choose 'frankenwp' or 'ols'")
            raise typer.Exit(code=1)

        if not admin_email or not isinstance(admin_email, str):
            admin_email = typer.prompt("Admin email", default=config_mgr.wordpress.default_admin_email)
        admin_email = str(admin_email).strip()

        if not site_title or not isinstance(site_title, str):
            site_title = typer.prompt("Site title", default=domain)
        site_title = str(site_title).strip()

        # Handle db_mode: use flag if provided, otherwise use config default
        if db_mode and isinstance(db_mode, str):
            db_mode = str(db_mode).strip().lower()
            if db_mode not in ["shared", "dedicated"]:
                print_error("Invalid DB mode. Choose 'shared' or 'dedicated'")
                raise typer.Exit(code=1)
        else:
            db_mode = config_mgr.docker.db_mode

        # Display summary
        console.print("\n[bold cyan]Site Configuration:[/bold cyan]")
        console.print(f"  Site Name: {site_name}")
        console.print(f"  Domain: {domain}")
        console.print(f"  Engine: {wp_type}")
        console.print(f"  DB Mode: {db_mode}")
        console.print(f"  Admin Email: {admin_email}")
        console.print(f"  Site Title: {site_title}\n")

        # Confirm
        if not yes and not typer.confirm("Proceed with site creation?", default=True):
            print_info("Site creation cancelled")
            raise typer.Exit(code=0)

        # Generate credentials
        print_info("Generating secure credentials...")
        creds = CredentialGenerator.generate_site_credentials(site_name, admin_email)

        # Add site config details
        creds['site_name'] = site_name
        creds['domain'] = domain
        creds['site_title'] = site_title
        creds['db_mode'] = db_mode

        # Render docker-compose template
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        ) as progress:
            progress.add_task(description="Preparing deployment...", total=None)

            template_name = f"{wp_type}/docker-compose.yml.j2"
            renderer = TemplateRenderer()

            try:
                compose_content = renderer.render(template_name, **creds)
            except Exception as e:
                print_error(f"Template rendering failed: {e}")
                raise typer.Exit(code=1)

        # Ensure proxy network exists and Caddy is running
        print_info("Checking Docker proxy network...")
        from cli.utils.docker import DockerManager
        import subprocess
        try:
            docker_mgr = DockerManager()
            network_name = config_mgr.docker.network_name

            if not docker_mgr.network_exists(network_name):
                print_info(f"Creating proxy network '{network_name}'...")
                docker_mgr.create_network(network_name)
                print_success(f"✓ Network '{network_name}' created")
            else:
                print_success(f"✓ Network '{network_name}' exists")

            # Check if Caddy proxy is running
            caddy_container = docker_mgr.get_container("caddy_proxy")
            if not caddy_container or caddy_container.status != "running":
                print_info("Caddy proxy not running, deploying...")
                result = subprocess.run(
                    ["docker", "compose", "-f", "/opt/vibewp/templates/caddy/docker-compose.yml", "up", "-d"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode != 0:
                    print_error(f"Failed to deploy Caddy: {result.stderr}")
                    raise typer.Exit(code=1)

                # Wait for Caddy to start
                time.sleep(2)

                caddy_container = docker_mgr.get_container("caddy_proxy")
                if caddy_container and caddy_container.status == "running":
                    print_success("✓ Caddy proxy deployed successfully")
                else:
                    print_error("Caddy failed to start")
                    raise typer.Exit(code=1)
            else:
                print_success("✓ Caddy proxy is running")

        except Exception as e:
            print_error(f"Failed to setup proxy: {e}")
            raise typer.Exit(code=1)

        # Connect to VPS via SSH
        print_info(f"Connecting to VPS {config_mgr.vps.host}...")
        ssh = SSHManager(
            host=config_mgr.vps.host,
            port=config_mgr.vps.port,
            user=config_mgr.vps.user,
            key_path=config_mgr.vps.key_path
        )

        try:
            ssh.connect()
        except Exception as e:
            print_error(f"SSH connection failed: {e}")
            raise typer.Exit(code=1)

        # Handle shared DB mode
        shared_db_root_password = None
        if db_mode == "shared":
            print_info("Setting up shared database...")
            from cli.utils.database import DatabaseManager

            db_mgr = DatabaseManager(ssh)

            # Get or generate root password
            shared_db_root_password = db_mgr.get_shared_db_root_password()
            if not shared_db_root_password:
                shared_db_root_password = DatabaseManager.generate_root_password()
                db_mgr.save_shared_db_root_password(shared_db_root_password)

            # Ensure shared DB exists
            if not db_mgr.ensure_shared_db_exists(shared_db_root_password):
                print_error("Failed to setup shared database")
                raise typer.Exit(code=1)

            print_success("✓ Shared database ready")

        # Define remote directory
        remote_base = config_mgr.docker.base_path
        remote_dir = f"{remote_base}/sites/{site_name}"

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True
            ) as progress:
                # Create remote directory
                task = progress.add_task(description="Creating remote directory...", total=None)
                exit_code, stdout, stderr = ssh.run_command(f"mkdir -p {remote_dir}")
                if exit_code != 0:
                    raise RuntimeError(f"Failed to create directory: {stderr}")

                # Upload docker-compose file
                progress.update(task, description="Uploading docker-compose.yml...")
                local_compose_path = f"/tmp/{site_name}-compose.yml"
                with open(local_compose_path, 'w') as f:
                    f.write(compose_content)

                ssh.upload_file(local_compose_path, f"{remote_dir}/docker-compose.yml")
                os.remove(local_compose_path)

                # Deploy containers
                progress.update(task, description=f"Deploying {wp_type} containers...")
                exit_code, stdout, stderr = ssh.run_command(
                    f"cd {remote_dir} && docker compose up -d",
                    timeout=300
                )
                if exit_code != 0:
                    raise RuntimeError(f"Docker compose up failed: {stderr}")

                # Wait for containers to start
                progress.update(task, description="Waiting for containers to start...")
                time.sleep(5)

                # Handle database setup based on mode
                health_checker = HealthChecker(ssh_manager=ssh)

                if db_mode == "shared":
                    # Create database and user in shared DB
                    progress.update(task, description="Creating database in shared DB...")
                    from cli.utils.database import DatabaseManager
                    db_mgr = DatabaseManager(ssh)

                    if not db_mgr.create_database_and_user(
                        db_name=creds['db_name'],
                        db_user=creds['db_user'],
                        db_password=creds['db_password'],
                        root_password=shared_db_root_password
                    ):
                        raise RuntimeError("Failed to create database in shared DB")

                    progress.update(task, description="Database created in shared DB...")
                else:
                    # Wait for dedicated database
                    progress.update(task, description="Waiting for database initialization...")
                    db_container = f"{site_name}_db"

                    if not health_checker.wait_for_database(db_container, timeout=90):
                        raise RuntimeError("Database initialization timeout")

                # Wait for WordPress container
                wp_container = f"{site_name}_wp" if wp_type == "frankenwp" else f"{site_name}_ols"
                if not health_checker.wait_for_container(wp_container, timeout=60):
                    raise RuntimeError("WordPress container failed to start")

                # Wait for WP-CLI container
                wpcli_container = f"{site_name}_wpcli"
                if not health_checker.wait_for_container(wpcli_container, timeout=60):
                    raise RuntimeError("WP-CLI container failed to start")

                progress.update(task, description="WordPress containers ready...")

                # Wait for WordPress files to be ready
                progress.update(task, description="Waiting for WordPress files...")
                wp_path = "/var/www/html" if wp_type == "frankenwp" else f"/var/www/vhosts/{domain}"
                wp_ready = False
                for attempt in range(30):  # 30 seconds max
                    exit_code, _, _ = ssh.run_command(
                        f"docker exec {wpcli_container} test -f {wp_path}/wp-load.php",
                        timeout=5
                    )
                    if exit_code == 0:
                        wp_ready = True
                        break
                    time.sleep(1)

                if not wp_ready:
                    raise RuntimeError("WordPress files not ready after 30 seconds")

                # Auto-install WordPress using WP-CLI
                progress.update(task, description="Installing WordPress via WP-CLI...")
                wp_manager = WordPressManager(ssh_manager=ssh)

                try:
                    if not wp_manager.core_install(
                        container_name=wpcli_container,
                        site_config={
                            'domain': domain,
                            'site_title': site_title,
                            'wp_admin_user': creds['wp_admin_user'],
                            'wp_admin_password': creds['wp_admin_password'],
                            'wp_admin_email': admin_email
                        },
                        wp_type=wp_type
                    ):
                        raise RuntimeError("WordPress installation failed")

                    progress.update(task, description="WordPress installed successfully...")
                except Exception as e:
                    raise RuntimeError(f"WordPress core installation failed: {e}")

                # Verify site accessibility
                progress.update(task, description="Verifying site accessibility...")
                site_url = f"https://{domain}"

                if not health_checker.wait_for_http(site_url, timeout=30, verify_ssl=False):
                    print_warning("Site may not be accessible via HTTPS yet (checking installation status)")

            # Add site to registry
            site_config = SiteConfig(
                name=site_name,
                domain=domain,
                type=wp_type,
                status="running",
                db_mode=db_mode
            )
            config_mgr.add_site(site_config)

            # Display success summary
            console.print()
            console.print(Panel.fit(
                f"[bold green]Site Created Successfully![/bold green]\n\n"
                f"[bold]Site Name:[/bold] {site_name}\n"
                f"[bold]Domain:[/bold] {domain}\n"
                f"[bold]Engine:[/bold] {wp_type}\n"
                f"[bold]Site URL:[/bold] {site_url}\n\n"
                f"[bold cyan]WordPress Admin Credentials:[/bold cyan]\n"
                f"  URL: {site_url}/wp-admin\n"
                f"  Username: {creds['wp_admin_user']}\n"
                f"  Password: {creds['wp_admin_password']}\n"
                f"  Email: {admin_email}\n\n"
                f"[bold cyan]Database Credentials:[/bold cyan]\n"
                f"  Database: {creds['db_name']}\n"
                f"  Username: {creds['db_user']}\n"
                f"  Password: {creds['db_password']}\n"
                f"  Host: db (FrankenWP) / mysql (OLS)\n\n"
                f"[green]✓ WordPress is fully installed and ready to use![/green]",
                title="VibeWP Site Creation",
                border_style="green"
            ))

        except Exception as e:
            print_error(f"Site creation failed: {e}")
            rollback_site_creation(site_name, ssh, remote_dir)
            raise typer.Exit(code=1)

        finally:
            ssh.disconnect()

    except Exception as e:
        print_error(f"Error: {e}")
        raise typer.Exit(code=1)


@app.command("list")
def list_sites():
    """List all WordPress sites"""
    try:
        config_mgr = ConfigManager()
        sites = config_mgr.get_sites()

        if not sites:
            print_info("No sites found")
            return

        table = Table(title="WordPress Sites")
        table.add_column("Name", style="cyan")
        table.add_column("Domain", style="green")
        table.add_column("Type", style="yellow")
        table.add_column("DB Mode", style="blue")
        table.add_column("Status", style="magenta")
        table.add_column("Created", style="dim")

        for site in sites:
            table.add_row(
                site.name,
                site.domain,
                site.type,
                site.db_mode,
                site.status,
                site.created[:10]  # Show date only
            )

        console.print(table)

    except Exception as e:
        print_error(f"Error: {e}")
        raise typer.Exit(code=1)


@app.command("info")
def site_info(site_name: str = typer.Argument(..., help="Site name")):
    """Show detailed site information"""
    try:
        config_mgr = ConfigManager()
        site = config_mgr.get_site(site_name)

        if not site:
            print_error(f"Site '{site_name}' not found")
            raise typer.Exit(code=1)

        console.print(Panel.fit(
            f"[bold cyan]Site Information[/bold cyan]\n\n"
            f"[bold]Name:[/bold] {site.name}\n"
            f"[bold]Domain:[/bold] {site.domain}\n"
            f"[bold]Type:[/bold] {site.type}\n"
            f"[bold]DB Mode:[/bold] {site.db_mode}\n"
            f"[bold]Status:[/bold] {site.status}\n"
            f"[bold]Created:[/bold] {site.created}\n\n"
            f"[bold cyan]URLs:[/bold cyan]\n"
            f"  Site: https://{site.domain}\n"
            f"  Admin: https://{site.domain}/wp-admin",
            title=f"Site: {site_name}",
            border_style="cyan"
        ))

    except Exception as e:
        print_error(f"Error: {e}")
        raise typer.Exit(code=1)


@app.command("delete")
def delete_site(
    site_name: str = typer.Argument(..., help="Site name"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation")
):
    """Delete a WordPress site"""
    try:
        config_mgr = ConfigManager()
        site = config_mgr.get_site(site_name)

        if not site:
            print_error(f"Site '{site_name}' not found")
            raise typer.Exit(code=1)

        # Confirm deletion
        if not force:
            console.print(f"\n[bold red]WARNING:[/bold red] This will permanently delete:")
            console.print(f"  - Site: {site.domain}")
            console.print(f"  - All containers and volumes")
            console.print(f"  - All WordPress data\n")

            if not typer.confirm("Are you sure you want to continue?", default=False):
                print_info("Deletion cancelled")
                raise typer.Exit(code=0)

        # Connect to VPS
        print_info(f"Connecting to VPS...")
        ssh = SSHManager(
            host=config_mgr.vps.host,
            port=config_mgr.vps.port,
            user=config_mgr.vps.user,
            key_path=config_mgr.vps.key_path
        )

        try:
            ssh.connect()
        except Exception as e:
            print_error(f"SSH connection failed: {e}")
            raise typer.Exit(code=1)

        try:
            remote_dir = f"{config_mgr.docker.base_path}/sites/{site_name}"

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True
            ) as progress:
                task = progress.add_task(description="Stopping containers...", total=None)

                # Stop and remove containers with volumes
                exit_code, stdout, stderr = ssh.run_command(
                    f"cd {remote_dir} && docker compose down -v",
                    timeout=120
                )

                if exit_code != 0:
                    print_warning(f"Docker compose down warning: {stderr}")

                # If shared DB mode, cleanup database and user
                if site.db_mode == "shared":
                    progress.update(task, description="Removing database from shared DB...")
                    from cli.utils.database import DatabaseManager
                    from cli.utils.credentials import CredentialGenerator

                    db_mgr = DatabaseManager(ssh)
                    root_password = db_mgr.get_shared_db_root_password()

                    if root_password:
                        # Get site's DB credentials
                        db_name = f"{site_name}_wp"
                        db_user = f"{site_name}_user"

                        if not db_mgr.delete_database_and_user(db_name, db_user, root_password):
                            print_warning("Failed to delete database from shared DB")
                    else:
                        print_warning("Shared DB root password not found")

                # Remove site directory
                progress.update(task, description="Removing site directory...")
                exit_code, stdout, stderr = ssh.run_command(f"rm -rf {remote_dir}")

                if exit_code != 0:
                    raise RuntimeError(f"Failed to remove directory: {stderr}")

            # Remove from registry
            config_mgr.remove_site(site_name)

            print_success(f"Site '{site_name}' deleted successfully")

        finally:
            ssh.disconnect()

    except Exception as e:
        print_error(f"Error: {e}")
        raise typer.Exit(code=1)


@app.command("logs")
def site_logs(
    site_name: str = typer.Argument(..., help="Site name"),
    service: Optional[str] = typer.Option(None, "--service", help="Service name (wp, db, redis)"),
    tail: int = typer.Option(100, "--tail", help="Number of lines to show"),
    follow: bool = typer.Option(False, "--follow", help="Follow log output")
):
    """View container logs for a site"""
    try:
        config_mgr = ConfigManager()
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

        try:
            ssh.connect()
        except Exception as e:
            print_error(f"SSH connection failed: {e}")
            raise typer.Exit(code=1)

        try:
            remote_dir = f"{config_mgr.docker.base_path}/sites/{site_name}"

            # Build logs command
            cmd = f"cd {remote_dir} && docker compose logs --tail {tail}"

            if service:
                cmd += f" {service}"

            if follow:
                cmd += " -f"

            print_info(f"Fetching logs for {site_name}...")
            exit_code, stdout, stderr = ssh.run_command(cmd, timeout=30)

            if exit_code == 0:
                console.print(stdout)
            else:
                print_error(f"Failed to fetch logs: {stderr}")

        finally:
            ssh.disconnect()

    except Exception as e:
        print_error(f"Error: {e}")
        raise typer.Exit(code=1)


@app.command("reinstall-core")
def reinstall_wordpress_core(
    site_name: str = typer.Argument(..., help="Site name"),
    version: Optional[str] = typer.Option(None, "--version", help="WordPress version (default: latest)"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation")
):
    """
    Reinstall WordPress core files (useful after hack/corruption)

    This will:
    - Download fresh WordPress core files
    - Replace all WP core files (wp-admin, wp-includes, root PHP files)
    - Preserve wp-content and wp-config.php
    - Keep your database intact
    """
    from cli.ui.console import confirm

    try:
        config_mgr = ConfigManager()
        config_mgr.load_config()

        site = config_mgr.get_site(site_name)
        if not site:
            print_error(f"Site '{site_name}' not found")
            raise typer.Exit(code=1)

        # Warning
        if not force:
            print_warning("\n⚠️  This will reinstall WordPress core files")
            print_info("  • wp-admin/ and wp-includes/ will be replaced")
            print_info("  • Root PHP files will be replaced")
            print_info("  • wp-content/ and wp-config.php will be preserved")
            print_info("  • Your database will remain untouched\n")

            if not confirm("Continue with WordPress core reinstallation?", default=False):
                print_info("Reinstallation cancelled")
                return

        # Connect to VPS
        ssh = SSHManager(
            host=config_mgr.vps.host,
            port=config_mgr.vps.port,
            user=config_mgr.vps.user,
            key_path=config_mgr.vps.key_path
        )

        ssh.connect()

        try:
            wpcli_container = f"{site_name}_wpcli"
            version_str = version if version else "latest"

            print_info(f"Reinstalling WordPress core ({version_str})...")

            # Backup .htaccess before reinstall (may contain security rules or custom config)
            print_info("Backing up .htaccess...")
            ssh.run_command(
                f"docker exec --user root {wpcli_container} cp /var/www/html/.htaccess /var/www/html/.htaccess.backup 2>/dev/null || true",
                timeout=10
            )

            # Run as root to handle any permission scenarios
            # This is safe as we're only replacing core files, not touching wp-content
            version_arg = f"--version={version}" if version else ""
            exit_code, stdout, stderr = ssh.run_command(
                f"docker exec --user root {wpcli_container} wp core download --force --skip-content --allow-root {version_arg}",
                timeout=120
            )

            if exit_code != 0:
                print_error(f"Failed to reinstall WordPress core: {stderr}")
                raise typer.Exit(code=1)

            # Restore .htaccess backup if it exists
            print_info("Restoring .htaccess...")
            ssh.run_command(
                f"docker exec --user root {wpcli_container} mv /var/www/html/.htaccess.backup /var/www/html/.htaccess 2>/dev/null || true",
                timeout=10
            )

            # Ensure proper ownership after download
            ssh.run_command(f"docker exec --user root {wpcli_container} chown -R www-data:www-data /var/www/html", timeout=30)

            # Set recommended permissions: 755 for directories, 644 for files
            ssh.run_command(f"docker exec --user root {wpcli_container} find /var/www/html -type d -exec chmod 755 {{}} \\;", timeout=60)
            ssh.run_command(f"docker exec --user root {wpcli_container} find /var/www/html -type f -exec chmod 644 {{}} \\;", timeout=60)

            # Verify installation
            exit_code, wp_version, stderr = ssh.run_command(
                f"docker exec {wpcli_container} wp core version",
                timeout=10
            )

            if exit_code == 0:
                print_success(f"\n✓ WordPress core reinstalled successfully")
                print_info(f"  Version: {wp_version.strip()}")
                print_info("\n✓ Your content and database are intact")
                print_info("✓ Please test your site and clear any caches")
            else:
                print_warning("Core reinstalled but version check failed")

        finally:
            ssh.disconnect()

    except Exception as e:
        print_error(f"Error: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
