"""Update command for VibeWP CLI self-update functionality."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
from pathlib import Path
import shutil
import logging

from cli.utils.update import UpdateManager, UpdateError, InstallMethod
from cli.utils.backup import BackupManager
from cli.utils.config import ConfigManager

console = Console()
logger = logging.getLogger(__name__)

app = typer.Typer(help="Update VibeWP CLI")


@app.command("check")
def check_updates(
    pre: bool = typer.Option(False, "--pre", help="Include pre-release versions"),
):
    """Check for available updates without installing."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(description="Checking for updates...", total=None)

            manager = UpdateManager()
            update_info = manager.check_for_updates(include_prerelease=pre)

        # Display version information
        table = Table(title="Version Information")
        table.add_column("Item", style="cyan")
        table.add_column("Value", style="yellow")

        table.add_row("Current Version", update_info.current_version)
        table.add_row("Latest Version", update_info.latest_version)
        table.add_row("Install Method", update_info.install_method.value)

        console.print(table)

        # Display update status
        if update_info.update_available:
            console.print(
                Panel(
                    f"✨ Update available: {update_info.current_version} → {update_info.latest_version}\n\n"
                    f"Run [bold cyan]vibewp update[/bold cyan] to install the latest version.",
                    title="Update Available",
                    border_style="green",
                )
            )

            # Show release notes if available
            if update_info.release and update_info.release.body:
                console.print(
                    Panel(
                        update_info.release.body[:500] + ("..." if len(update_info.release.body) > 500 else ""),
                        title="Release Notes",
                        border_style="blue",
                    )
                )
        else:
            console.print(
                Panel(
                    f"✅ You are running the latest version: {update_info.current_version}",
                    title="Up to Date",
                    border_style="green",
                )
            )

    except UpdateError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command("install")
def install_update(
    pre: bool = typer.Option(False, "--pre", help="Include pre-release versions"),
    force: bool = typer.Option(False, "--force", help="Force reinstall current version"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    skip_backup: bool = typer.Option(False, "--skip-backup", help="Skip backup creation (not recommended)"),
):
    """Install the latest VibeWP update."""
    try:
        manager = UpdateManager()

        # Check for updates
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(description="Checking for updates...", total=None)
            update_info = manager.check_for_updates(include_prerelease=pre)

        # Check if update needed
        if not update_info.update_available and not force:
            console.print(
                Panel(
                    f"✅ Already on latest version: {update_info.current_version}",
                    title="Up to Date",
                    border_style="green",
                )
            )
            return

        # Display update information
        console.print(
            Panel(
                f"Current Version: [yellow]{update_info.current_version}[/yellow]\n"
                f"New Version: [green]{update_info.latest_version}[/green]\n"
                f"Install Method: [cyan]{update_info.install_method.value}[/cyan]",
                title="Update Information",
                border_style="blue",
            )
        )

        # Confirmation prompt
        if not yes:
            confirm = typer.confirm(
                "Do you want to proceed with the update?",
                default=True
            )
            if not confirm:
                console.print("[yellow]Update cancelled.[/yellow]")
                return

        backup_path = None

        try:
            # Create backup (only for script installations)
            if update_info.install_method == InstallMethod.SCRIPT_INSTALL and not skip_backup:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task = progress.add_task(description="Creating backup...", total=None)
                    backup_path = BackupManager.create_installation_backup()
                    progress.update(task, completed=True)

                console.print(f"[green]✓[/green] Backup created: {backup_path}")

            # Backup config files
            config_backup = _backup_config_files()

            # Perform update
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(description="Installing update...", total=None)
                success = manager.perform_update(force=force)
                progress.update(task, completed=True)

            if success:
                # Restore config files
                _restore_config_files(config_backup)

                # Verify installation
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task = progress.add_task(description="Verifying installation...", total=None)
                    verified = manager.verify_installation()
                    progress.update(task, completed=True)

                if verified:
                    console.print(
                        Panel(
                            f"✅ Successfully updated to version {update_info.latest_version}!",
                            title="Update Complete",
                            border_style="green",
                        )
                    )

                    # Cleanup old backups
                    if backup_path:
                        BackupManager.cleanup_old_backups(keep_count=3)
                else:
                    raise UpdateError("Installation verification failed")

        except Exception as e:
            logger.error(f"Update failed: {e}")
            console.print(f"[bold red]Update failed:[/bold red] {e}")

            # Attempt rollback if backup exists
            if backup_path and backup_path.exists():
                console.print("\n[yellow]Attempting to rollback...[/yellow]")

                try:
                    BackupManager.restore_installation_backup(backup_path)
                    console.print("[green]✓[/green] Rollback successful. Installation restored.")
                except Exception as rollback_error:
                    console.print(
                        f"[bold red]Rollback failed:[/bold red] {rollback_error}\n"
                        f"[yellow]Manual restore required from:[/yellow] {backup_path}"
                    )

            raise typer.Exit(1)

    except UpdateError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command("cleanup")
def cleanup_backups(
    keep: int = typer.Option(3, "--keep", help="Number of backups to keep"),
):
    """Cleanup old installation backups."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(description="Cleaning up old backups...", total=None)
            BackupManager.cleanup_old_backups(keep_count=keep)

        console.print(f"[green]✓[/green] Cleanup complete. Kept {keep} most recent backups.")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command("info")
def installation_info():
    """Display detailed installation information."""
    try:
        manager = UpdateManager()
        info = manager.get_installation_info()

        table = Table(title="Installation Information")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="yellow")

        for key, value in info.items():
            table.add_row(key.replace('_', ' ').title(), str(value))

        console.print(table)

        # Check rate limit
        rate_limit = manager.github_client.check_rate_limit()
        console.print(
            Panel(
                f"Limit: [yellow]{rate_limit.get('limit', 'unknown')}[/yellow]\n"
                f"Remaining: [cyan]{rate_limit.get('remaining', 'unknown')}[/cyan]\n"
                f"Reset: [blue]{rate_limit.get('reset', 'unknown')}[/blue]",
                title="GitHub API Rate Limit",
                border_style="blue",
            )
        )

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


def _backup_config_files() -> dict:
    """
    Backup configuration files before update.

    Returns:
        Dict with backed up config data
    """
    config_manager = ConfigManager()
    config_path = Path.home() / ".vibewp" / "sites.yaml"

    backup = {}

    if config_path.exists():
        backup['sites_yaml'] = config_path.read_text()

    return backup


def _restore_config_files(backup: dict) -> None:
    """
    Restore configuration files after update.

    Args:
        backup: Dict with backed up config data
    """
    config_path = Path.home() / ".vibewp" / "sites.yaml"

    if 'sites_yaml' in backup:
        config_path.write_text(backup['sites_yaml'])


if __name__ == "__main__":
    app()
