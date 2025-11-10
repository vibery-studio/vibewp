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
):
    """Create a new WordPress site"""

    try:
        # Load config
        config_mgr = ConfigManager()
        config_mgr.load_config()

        # Interactive prompts if not provided
        if not site_name:
            site_name = typer.prompt("Site name (alphanumeric, underscores)")

        # Validate site name
        if not site_name.replace('_', '').replace('-', '').isalnum():
            print_error("Site name must be alphanumeric with underscores/hyphens")
            raise typer.Exit(code=1)

        # Check if site already exists
        if config_mgr.get_site(site_name):
            print_error(f"Site '{site_name}' already exists")
            raise typer.Exit(code=1)

        if not domain:
            domain = typer.prompt("Domain name")

        if not wp_type:
            console.print("\n[bold cyan]Choose WordPress Engine:[/bold cyan]")
            console.print("  [green]1. frankenwp[/green] - FrankenPHP (high performance, Go-based)")
            console.print("  [green]2. ols[/green] - OpenLiteSpeed (proven stability, LiteSpeed Cache)")
            wp_choice = typer.prompt("Select engine", type=int, default=1)
            wp_type = "frankenwp" if wp_choice == 1 else "ols"

        if wp_type not in ["frankenwp", "ols"]:
            print_error("Invalid WordPress type. Choose 'frankenwp' or 'ols'")
            raise typer.Exit(code=1)

        if not admin_email:
            admin_email = typer.prompt("Admin email", default=config_mgr.wordpress.default_admin_email)

        if not site_title:
            site_title = typer.prompt("Site title", default=domain)

        # Display summary
        console.print("\n[bold cyan]Site Configuration:[/bold cyan]")
        console.print(f"  Site Name: {site_name}")
        console.print(f"  Domain: {domain}")
        console.print(f"  Engine: {wp_type}")
        console.print(f"  Admin Email: {admin_email}")
        console.print(f"  Site Title: {site_title}\n")

        # Confirm
        if not typer.confirm("Proceed with site creation?", default=True):
            print_info("Site creation cancelled")
            raise typer.Exit(code=0)

        # Generate credentials
        print_info("Generating secure credentials...")
        creds = CredentialGenerator.generate_site_credentials(site_name, admin_email)

        # Add site config details
        creds['site_name'] = site_name
        creds['domain'] = domain
        creds['site_title'] = site_title

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

                # Wait for database
                progress.update(task, description="Waiting for database initialization...")
                health_checker = HealthChecker(ssh_manager=ssh)
                db_container = f"{site_name}_db"

                if not health_checker.wait_for_database(db_container, timeout=90):
                    raise RuntimeError("Database initialization timeout")

                # Wait for WordPress container
                wp_container = f"{site_name}_wp" if wp_type == "frankenwp" else f"{site_name}_ols"
                if not health_checker.wait_for_container(wp_container, timeout=60):
                    raise RuntimeError("WordPress container failed to start")

                # Install WordPress
                progress.update(task, description="Installing WordPress...")
                wp_manager = WordPressManager(ssh_manager=ssh)

                try:
                    wp_manager.core_install(
                        container_name=wp_container,
                        site_config=creds,
                        wp_type=wp_type
                    )
                except Exception as e:
                    raise RuntimeError(f"WordPress installation failed: {e}")

                # Verify site accessibility
                progress.update(task, description="Verifying site accessibility...")
                site_url = f"https://{domain}"

                # Wait a bit for WordPress to initialize
                time.sleep(5)

                if not health_checker.wait_for_http(site_url, timeout=30, verify_ssl=False):
                    print_warning("Site may not be accessible yet (this is normal for new sites)")

            # Add site to registry
            site_config = SiteConfig(
                name=site_name,
                domain=domain,
                type=wp_type,
                status="running"
            )
            config_mgr.add_site(site_config)

            # Display success summary
            console.print()
            console.print(Panel.fit(
                f"[bold green]Site Created Successfully![/bold green]\n\n"
                f"[bold]Site Name:[/bold] {site_name}\n"
                f"[bold]Domain:[/bold] {domain}\n"
                f"[bold]Engine:[/bold] {wp_type}\n\n"
                f"[bold cyan]Access URLs:[/bold cyan]\n"
                f"  Site: {site_url}\n"
                f"  Admin: {site_url}/wp-admin\n\n"
                f"[bold cyan]Admin Credentials:[/bold cyan]\n"
                f"  Username: {creds['wp_admin_user']}\n"
                f"  Password: {creds['wp_admin_password']}\n\n"
                f"[yellow]⚠ Save these credentials securely![/yellow]",
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
        table.add_column("Status", style="magenta")
        table.add_column("Created", style="blue")

        for site in sites:
            table.add_row(
                site.name,
                site.domain,
                site.type,
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
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation")
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
    service: Optional[str] = typer.Option(None, "--service", "-s", help="Service name (wp, db, redis)"),
    tail: int = typer.Option(100, "--tail", "-n", help="Number of lines to show"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output")
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


if __name__ == "__main__":
    app()
