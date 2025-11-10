"""SFTP key management commands"""

import typer
from typing import Optional
from pathlib import Path

from ..utils.ssh import SSHManager
from ..utils.config import get_config
from ..utils.sftp import SFTPManager
from ..ui.console import (
    console, print_success, print_error, print_info,
    print_warning, create_table
)

app = typer.Typer(help="Manage SFTP access with site-specific restrictions")


def get_sftp_manager() -> SFTPManager:
    """Get configured SFTP manager instance"""
    config = get_config()
    ssh_manager = SSHManager(
        host=config['vps']['host'],
        port=config['vps'].get('port', 22),
        username=config['vps']['user'],
        key_path=config['vps'].get('key_path')
    )
    return SFTPManager(ssh_manager)


@app.command("add-key")
def add_key(
    site_name: str = typer.Argument(..., help="Site name"),
    public_key_file: str = typer.Argument(..., help="Path to SSH public key file (e.g., ~/.ssh/id_rsa.pub)"),
    identifier: str = typer.Option("user", "--id", help="Short identifier for this key (e.g., 'john', 'deploy')")
):
    """
    Add SFTP access for a site with SSH key authentication

    The user will only have access to the site's wp-content directory
    via SFTP (no shell access, no other directories).

    Example:
        vibewp sftp add-key mysite ~/.ssh/id_rsa.pub --id john
    """
    try:
        # Read public key file
        key_path = Path(public_key_file).expanduser()
        if not key_path.exists():
            print_error(f"Public key file not found: {public_key_file}")
            raise typer.Exit(1)

        with open(key_path, 'r') as f:
            public_key = f.read().strip()

        print_info(f"Adding SFTP access for site '{site_name}'...")

        # Add SSH key
        sftp_manager = get_sftp_manager()
        result = sftp_manager.add_ssh_key(site_name, public_key, identifier)

        print_success(f"SFTP access created successfully!")
        console.print()
        console.print(f"[bold]Connection Details:[/bold]")
        console.print(f"  Username: [cyan]{result['username']}[/cyan]")
        console.print(f"  Host: [cyan]{sftp_manager.ssh.host}[/cyan]")
        console.print(f"  Port: [cyan]22[/cyan]")
        console.print(f"  Accessible Path: [cyan]/wp-content[/cyan]")
        console.print()
        console.print(f"[dim]Connect with:[/dim]")
        console.print(f"  [bold]sftp {result['username']}@{sftp_manager.ssh.host}[/bold]")
        console.print()

    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(1)
    except RuntimeError as e:
        print_error(f"Failed to add SFTP access: {e}")
        raise typer.Exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        raise typer.Exit(1)


@app.command("remove-key")
def remove_key(
    site_name: str = typer.Argument(..., help="Site name"),
    identifier: str = typer.Argument(..., help="Key identifier")
):
    """
    Remove SFTP access for a site

    Example:
        vibewp sftp remove-key mysite john
    """
    try:
        sftp_manager = get_sftp_manager()

        # Confirm removal
        username = sftp_manager._get_sftp_username(site_name, identifier)
        from ..ui.console import confirm

        if not confirm(f"Remove SFTP user '{username}'?", default=False):
            print_info("Cancelled")
            raise typer.Exit(0)

        print_info(f"Removing SFTP access...")

        # Remove SSH key
        sftp_manager.remove_ssh_key(site_name, identifier)

        print_success(f"SFTP access removed successfully!")

    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(1)
    except RuntimeError as e:
        print_error(f"Failed to remove SFTP access: {e}")
        raise typer.Exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        raise typer.Exit(1)


@app.command("list")
def list_keys(
    site_name: Optional[str] = typer.Argument(None, help="Optional site name to filter by")
):
    """
    List all SFTP users

    Example:
        vibewp sftp list
        vibewp sftp list mysite
    """
    try:
        sftp_manager = get_sftp_manager()

        users = sftp_manager.list_ssh_keys(site_name)

        if not users:
            if site_name:
                print_info(f"No SFTP users found for site '{site_name}'")
            else:
                print_info("No SFTP users found")
            raise typer.Exit(0)

        # Create table
        columns = [
            ("Username", "cyan"),
            ("Site", "info"),
            ("Identifier", ""),
            ("UID", "muted"),
            ("Home", "muted")
        ]

        rows = []
        for user in users:
            rows.append([
                user['username'],
                user['site_name'],
                user['key_identifier'],
                user['uid'],
                user['home']
            ])

        title = f"SFTP Users (Site: {site_name})" if site_name else "SFTP Users"
        table = create_table(
            title,
            columns,
            rows
        )

        console.print()
        console.print(table)
        console.print()

    except Exception as e:
        print_error(f"Failed to list SFTP users: {e}")
        raise typer.Exit(1)


@app.command("test")
def test_access(
    site_name: str = typer.Argument(..., help="Site name"),
    identifier: str = typer.Argument(..., help="Key identifier")
):
    """
    Test SFTP access configuration

    Verifies that the SFTP user is properly configured (does not test actual connection)

    Example:
        vibewp sftp test mysite john
    """
    try:
        sftp_manager = get_sftp_manager()
        username = sftp_manager._get_sftp_username(site_name, identifier)

        print_info(f"Testing SFTP configuration for '{username}'...")

        results = sftp_manager.test_sftp_access(username)

        console.print()
        console.print("[bold]Configuration Checks:[/bold]")
        console.print()

        for check_name, passed in results.items():
            if check_name == 'all_passed':
                continue

            status = "[green]✓[/green]" if passed else "[red]✗[/red]"
            check_label = check_name.replace('_', ' ').title()
            console.print(f"  {status} {check_label}")

        console.print()

        if results['all_passed']:
            print_success("All checks passed! SFTP access is properly configured.")
        else:
            print_error("Some checks failed. SFTP access may not work correctly.")
            raise typer.Exit(1)

    except Exception as e:
        print_error(f"Failed to test SFTP access: {e}")
        raise typer.Exit(1)


@app.command("info")
def show_info():
    """
    Show information about SFTP access and usage

    Example:
        vibewp sftp info
    """
    from ..ui.console import Panel

    info_text = """
[bold cyan]SFTP Access Overview[/bold cyan]

VibeWP provides secure SFTP access with site-specific restrictions:

[bold]Features:[/bold]
  • SSH key authentication (no passwords)
  • Chroot jail - users can only access their site's wp-content
  • No shell access - SFTP only
  • Automatic file permissions for WordPress

[bold]Common Commands:[/bold]
  • Add access:    [cyan]vibewp sftp add-key <site> ~/.ssh/id_rsa.pub --id <name>[/cyan]
  • Remove access: [cyan]vibewp sftp remove-key <site> <name>[/cyan]
  • List users:    [cyan]vibewp sftp list[/cyan]
  • Test config:   [cyan]vibewp sftp test <site> <name>[/cyan]

[bold]Client Connection:[/bold]
  After adding a key, users connect with:
  [cyan]sftp sftp_<site>_<name>@your-server.com[/cyan]

  They will only see /wp-content directory with full read/write access.

[bold]Security:[/bold]
  • Users cannot navigate outside wp-content
  • Users cannot execute shell commands
  • Users cannot access other sites
  • All changes are logged in system auth logs
"""

    panel = Panel(
        info_text,
        title="[bold]SFTP Access Information[/bold]",
        border_style="cyan"
    )

    console.print()
    console.print(panel)
    console.print()


if __name__ == "__main__":
    app()
