"""Domain management commands for VibeWP CLI"""

import time
import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from simple_term_menu import TerminalMenu

from cli.utils.config import ConfigManager
from cli.utils.ssh import SSHManager
from cli.utils.dns import DNSValidator
from cli.utils.caddy import CaddyManager
from cli.utils.wordpress import WordPressManager
from cli.ui.console import print_success, print_error, print_info, print_warning

console = Console()
app = typer.Typer(help="Domain management commands")


def manage_domains():
    """Domain management menu - select site and manage domains"""
    try:
        config = ConfigManager()
        sites = config.get_sites()

        if not sites:
            print_warning("No sites found. Create a site first.")
            console.input("\n[dim]Press Enter to continue...[/dim]")
            return

        # Select site
        site_names = [f"{site.name} ({site.domain})" for site in sites]
        menu = TerminalMenu(
            site_names,
            title="Select site to manage domains:",
            menu_cursor="→ ",
            menu_cursor_style=("fg_cyan", "bold"),
            menu_highlight_style=("bg_cyan", "fg_black")
        )
        choice = menu.show()

        if choice is None:
            return

        selected_site = sites[choice]
        domain_menu(selected_site)

    except Exception as e:
        print_error(f"Error: {e}")
        console.input("\n[dim]Press Enter to continue...[/dim]")


def domain_menu(site):
    """Domain operations menu for selected site"""
    try:
        config = ConfigManager()

        # Connect to SSH
        ssh = SSHManager(
            host=config.vps.host,
            port=config.vps.port,
            user=config.vps.user,
            key_path=config.vps.key_path
        )
        ssh.connect()

        try:
            caddy = CaddyManager(ssh, config.docker.base_path)

            while True:
                # Get current domains from Caddy labels
                try:
                    domains = caddy.get_site_domains(site.name)
                except Exception as e:
                    print_error(f"Failed to get domains: {e}")
                    console.input("\n[dim]Press Enter to continue...[/dim]")
                    break

                # Display header
                console.print(f"\n[bold cyan]Site:[/bold cyan] {site.name}")
                console.print(f"[bold cyan]Primary Domain:[/bold cyan] {site.domain}")
                console.print(f"[bold cyan]All Domains:[/bold cyan] {', '.join(domains)}\n")

                # Menu options
                options = [
                    "➕ Add Domain",
                    "➖ Remove Domain",
                    "🏠 Set Primary Domain",
                    "🔒 View SSL Status",
                    "🔙 Back"
                ]

                menu = TerminalMenu(
                    options,
                    title="Domain Operations:",
                    menu_cursor="→ ",
                    menu_cursor_style=("fg_cyan", "bold"),
                    menu_highlight_style=("bg_cyan", "fg_black")
                )
                choice = menu.show()

                if choice == 0:
                    add_domain(site, caddy, ssh, config)
                elif choice == 1:
                    remove_domain(site, caddy, ssh, config)
                elif choice == 2:
                    set_primary_domain(site, caddy, ssh, config)
                elif choice == 3:
                    show_ssl_status(caddy, site)
                elif choice == 4 or choice is None:
                    break

        finally:
            ssh.disconnect()

    except Exception as e:
        print_error(f"Error: {e}")
        console.input("\n[dim]Press Enter to continue...[/dim]")


def add_domain(site, caddy: CaddyManager, ssh: SSHManager, config: ConfigManager):
    """Add domain to site"""
    try:
        console.print("\n[bold cyan]Add Domain[/bold cyan]")
        domain = typer.prompt("Enter domain to add")

        # Verify DNS
        print_info(f"Verifying DNS configuration for {domain}...")
        vps_ip = config.get_vps_ip()
        validator = DNSValidator(vps_ip)

        success, resolved_ip = validator.verify_dns(domain, timeout=10)

        if not success:
            if resolved_ip:
                print_warning(f"DNS points to {resolved_ip}, but VPS is at {vps_ip}")
            else:
                print_warning(f"DNS not configured for {domain}")

            if not typer.confirm("Continue anyway?", default=False):
                return

        # Add domain to Caddy labels
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        ) as progress:
            task = progress.add_task(description="Adding domain to Caddy...", total=None)

            try:
                caddy.add_domain(site.name, domain)
            except ValueError as e:
                print_error(str(e))
                console.input("\n[dim]Press Enter to continue...[/dim]")
                return

            # Reload Caddy
            progress.update(task, description="Reloading Caddy configuration...")
            caddy.reload_caddy(site.name)

            # Wait for SSL certificate
            progress.update(task, description="Waiting for SSL certificate...")
            time.sleep(5)  # Give Caddy time to request certificate

            # Check SSL status (with timeout)
            ssl_ready = False
            for i in range(12):  # Try for 60 seconds
                cert_status = caddy.get_cert_status(domain)
                if cert_status.get('status') == 'valid':
                    ssl_ready = True
                    break
                time.sleep(5)

        # Update config registry
        config.add_domain_to_site(site.name, domain)

        if ssl_ready:
            print_success(f"Domain {domain} added successfully with SSL certificate")
        else:
            print_warning(f"Domain {domain} added, but SSL certificate not yet ready")

    except Exception as e:
        print_error(f"Failed to add domain: {e}")

    console.input("\n[dim]Press Enter to continue...[/dim]")


def remove_domain(site, caddy: CaddyManager, ssh: SSHManager, config: ConfigManager):
    """Remove domain from site"""
    try:
        console.print("\n[bold cyan]Remove Domain[/bold cyan]")

        # Get current domains
        domains = caddy.get_site_domains(site.name)

        if len(domains) == 1:
            print_error("Cannot remove the last domain")
            console.input("\n[dim]Press Enter to continue...[/dim]")
            return

        # Select domain to remove
        menu = TerminalMenu(
            domains,
            title="Select domain to remove:",
            menu_cursor="→ ",
            menu_cursor_style=("fg_cyan", "bold"),
            menu_highlight_style=("bg_cyan", "fg_black")
        )
        choice = menu.show()

        if choice is None:
            return

        domain_to_remove = domains[choice]

        # Confirm removal
        console.print(f"\n[bold red]Warning:[/bold red] This will remove domain: {domain_to_remove}")
        if not typer.confirm("Are you sure?", default=False):
            return

        # Remove domain
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        ) as progress:
            task = progress.add_task(description="Removing domain from Caddy...", total=None)

            try:
                caddy.remove_domain(site.name, domain_to_remove)
            except ValueError as e:
                print_error(str(e))
                console.input("\n[dim]Press Enter to continue...[/dim]")
                return

            # Reload Caddy
            progress.update(task, description="Reloading Caddy configuration...")
            caddy.reload_caddy(site.name)

        # Update config registry
        config.remove_domain_from_site(site.name, domain_to_remove)

        print_success(f"Domain {domain_to_remove} removed successfully")

    except Exception as e:
        print_error(f"Failed to remove domain: {e}")

    console.input("\n[dim]Press Enter to continue...[/dim]")


def set_primary_domain(site, caddy: CaddyManager, ssh: SSHManager, config: ConfigManager):
    """Change WordPress primary domain"""
    try:
        console.print("\n[bold cyan]Set Primary Domain[/bold cyan]")

        # Get current domains
        domains = caddy.get_site_domains(site.name)

        # Select new primary domain
        menu = TerminalMenu(
            domains,
            title="Select new primary domain:",
            menu_cursor="→ ",
            menu_cursor_style=("fg_cyan", "bold"),
            menu_highlight_style=("bg_cyan", "fg_black")
        )
        choice = menu.show()

        if choice is None:
            return

        new_primary = domains[choice]

        # Check if already primary
        if new_primary == site.domain:
            print_info(f"{new_primary} is already the primary domain")
            console.input("\n[dim]Press Enter to continue...[/dim]")
            return

        # Confirm change
        console.print(f"\n[bold cyan]Current primary:[/bold cyan] {site.domain}")
        console.print(f"[bold cyan]New primary:[/bold cyan] {new_primary}")
        if not typer.confirm("Update WordPress siteurl and home?", default=True):
            return

        # Update WordPress URLs
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        ) as progress:
            task = progress.add_task(description="Updating WordPress URLs...", total=None)

            wp_manager = WordPressManager(ssh)
            wp_container = f"{site.name}_wp" if site.type == "frankenwp" else f"{site.name}_ols"

            try:
                wp_manager.update_site_url(
                    wp_container,
                    f"https://{new_primary}",
                    wp_type=site.type,
                    domain=new_primary if site.type == "ols" else None
                )
            except Exception as e:
                print_error(f"Failed to update WordPress URLs: {e}")
                console.input("\n[dim]Press Enter to continue...[/dim]")
                return

        # Update config registry
        config.update_site_primary_domain(site.name, new_primary)

        print_success(f"Primary domain changed to {new_primary}")

    except Exception as e:
        print_error(f"Failed to set primary domain: {e}")

    console.input("\n[dim]Press Enter to continue...[/dim]")


def show_ssl_status(caddy: CaddyManager, site):
    """Display SSL certificate status for all domains"""
    try:
        console.print("\n[bold cyan]SSL Certificate Status[/bold cyan]\n")

        # Get domains
        domains = caddy.get_site_domains(site.name)

        # Create table
        table = Table(title=f"SSL Certificates - {site.name}")
        table.add_column("Domain", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Issuer", style="yellow")
        table.add_column("Expires", style="magenta")
        table.add_column("Days Left", style="blue")

        # Check each domain
        for domain in domains:
            cert_status = caddy.get_cert_status(domain)

            if cert_status.get('status') == 'valid':
                status = "✓ Valid"
                issuer = cert_status.get('issuer_org', 'Unknown')
                expires = cert_status.get('not_after', '-')
                days_left = cert_status.get('days_until_expiry', 0)

                if days_left < 0:
                    status = "✗ Expired"
                elif days_left < 30:
                    status = "⚠ Expiring Soon"

                table.add_row(
                    domain,
                    status,
                    issuer,
                    expires,
                    str(days_left)
                )
            else:
                error_msg = cert_status.get('error', 'Unknown error')
                table.add_row(
                    domain,
                    f"✗ {cert_status.get('status', 'Error')}",
                    "-",
                    "-",
                    error_msg[:30]
                )

        console.print(table)

    except Exception as e:
        print_error(f"Failed to get SSL status: {e}")

    console.input("\n[dim]Press Enter to continue...[/dim]")


if __name__ == "__main__":
    app()
