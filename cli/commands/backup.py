"""Backup and restore management commands"""

import typer
from rich.table import Table
from cli.ui.console import console, print_success, print_error, print_warning, print_info, confirm
from cli.utils.ssh import SSHManager
from cli.utils.backup import BackupManager
from cli.utils.remote_backup import RemoteBackupManager
from cli.utils.config import ConfigManager

app = typer.Typer(help="Backup and restore operations")


@app.command("create")
def create_backup(
    site_name: str = typer.Argument(..., help="Site name to backup"),
    compress: bool = typer.Option(True, help="Compress backup (tar.gz)"),
    remote: bool = typer.Option(False, "--remote", help="Upload backup to remote S3 storage"),
    exclude_uploads: bool = typer.Option(False, "--exclude-uploads", help="Skip uploads directory for faster backup")
):
    """Create a backup of a WordPress site (database + files)"""
    try:
        ssh = SSHManager.from_config()
        ssh.connect()

        backup_mgr = BackupManager(ssh)

        # Verify site exists
        if not backup_mgr.site_exists(site_name):
            print_error(f"Site '{site_name}' not found")
            ssh.disconnect()
            raise typer.Exit(1)

        # Check remote backup configuration if --remote flag used
        config_mgr = ConfigManager()
        remote_config = config_mgr.load_config().remote_backup

        if remote and not remote_config.enabled:
            print_error("Remote backup not configured. Run 'vibewp backup configure-remote' first")
            ssh.disconnect()
            raise typer.Exit(1)

        # Show estimated size
        estimated_size = backup_mgr.get_backup_size(site_name)
        console.print(f"\n[bold]Site:[/bold] {site_name}")
        console.print(f"[bold]Estimated size:[/bold] {estimated_size}")
        console.print(f"[bold]Compression:[/bold] {'Enabled' if compress else 'Disabled'}")
        if remote:
            console.print(f"[bold]Remote sync:[/bold] Enabled (→ {remote_config.provider}:{remote_config.bucket})\n")
        else:
            console.print()

        if not confirm("Create backup?", default=True):
            ssh.disconnect()
            raise typer.Exit()

        # Create backup
        if exclude_uploads:
            print_info(f"Creating backup of {site_name} (excluding uploads)...")
        else:
            print_info(f"Creating backup of {site_name}...")

        with console.status("[cyan]Backing up database and files...", spinner="dots"):
            backup_id = backup_mgr.create_backup(site_name, compress=compress, exclude_uploads=exclude_uploads)

        print_success(f"Backup created: {backup_id}")
        console.print(f"\n[dim]Backup ID: {site_name}_{backup_id}[/dim]")

        # Upload to remote if requested
        if remote:
            try:
                remote_mgr = RemoteBackupManager(ssh)

                # Check rclone installation
                if not remote_mgr.check_rclone_installed():
                    print_warning("rclone not installed on VPS, installing...")
                    remote_mgr.install_rclone()
                    print_success("rclone installed")

                # Configure rclone if not already configured
                if not remote_mgr.check_rclone_configured():
                    print_info("Configuring rclone...")
                    remote_mgr.configure_rclone(
                        provider=remote_config.provider,
                        bucket=remote_config.bucket,
                        access_key=remote_config.access_key,
                        secret_key=remote_config.secret_key,
                        endpoint=remote_config.endpoint,
                        region=remote_config.region
                    )

                # Sync to remote
                print_info("Uploading backup to remote storage...")

                backup_filename = f"{site_name}_{backup_id}.tar.gz" if compress else f"{site_name}_{backup_id}"
                local_backup = f"{backup_mgr.backup_dir}/{backup_filename}"
                remote_path = f"backups/{site_name}"

                with console.status("[cyan]Syncing to S3...", spinner="dots"):
                    remote_mgr.sync_backup_to_remote(
                        local_backup_path=local_backup,
                        remote_path=remote_path,
                        bucket=remote_config.bucket,
                        encryption=remote_config.encryption
                    )

                print_success(f"Backup uploaded to {remote_config.provider}:{remote_config.bucket}/{remote_path}")

                # Cleanup old remote backups if retention configured
                if remote_config.retention_days > 0:
                    remote_mgr.cleanup_old_backups(
                        bucket=remote_config.bucket,
                        remote_path=f"backups/{site_name}",
                        retention_days=remote_config.retention_days
                    )

            except Exception as e:
                print_error(f"Remote upload failed: {e}")
                print_warning("Local backup still available")

        ssh.disconnect()

    except Exception as e:
        print_error(f"Backup creation failed: {e}")
        raise typer.Exit(1)


@app.command("list")
def list_backups(
    site: str = typer.Option(None, "--site", help="Filter by site name")
):
    """List all available backups"""
    try:
        ssh = SSHManager.from_config()
        ssh.connect()

        backup_mgr = BackupManager(ssh)

        with console.status("[cyan]Fetching backup list...", spinner="dots"):
            backups = backup_mgr.list_backups()

        if not backups:
            print_info("No backups found")
            ssh.disconnect()
            return

        # Filter by site if specified
        if site:
            backups = [b for b in backups if b['site'] == site]

            if not backups:
                print_info(f"No backups found for site: {site}")
                ssh.disconnect()
                return

        # Sort by date (newest first)
        backups.sort(key=lambda x: x['id'], reverse=True)

        # Create table
        table = Table(title="Available Backups", show_header=True)
        table.add_column("Backup ID", style="cyan")
        table.add_column("Site", style="green")
        table.add_column("Date", style="yellow")
        table.add_column("Size", style="blue")

        for backup in backups:
            table.add_row(
                backup['id'],
                backup['site'],
                backup['date'],
                backup['size']
            )

        console.print(table)
        console.print(f"\n[dim]Total backups: {len(backups)}[/dim]")

        ssh.disconnect()

    except Exception as e:
        print_error(f"Failed to list backups: {e}")
        raise typer.Exit(1)


@app.command("restore")
def restore_backup(
    site_name: str = typer.Argument(..., help="Site name to restore to"),
    backup_id: str = typer.Argument(..., help="Backup ID to restore from")
):
    """Restore a site from backup"""
    try:
        ssh = SSHManager.from_config()
        ssh.connect()

        backup_mgr = BackupManager(ssh)

        # Verify backup exists
        backups = backup_mgr.list_backups()
        backup_found = False

        for b in backups:
            if b['site'] == site_name and b['id'] == backup_id:
                backup_found = True
                backup_info = b
                break

        if not backup_found:
            print_error(f"Backup not found: {site_name}_{backup_id}")
            ssh.disconnect()
            raise typer.Exit(1)

        # Warning and confirmation
        console.print("\n[bold red]Site Restore Warning[/bold red]\n")
        console.print(f"[bold]Site:[/bold] {site_name}")
        console.print(f"[bold]Backup ID:[/bold] {backup_id}")
        console.print(f"[bold]Backup Date:[/bold] {backup_info['date']}")
        console.print(f"[bold]Size:[/bold] {backup_info['size']}\n")

        print_warning("This will OVERWRITE the current site data!")
        console.print("[yellow]Current database and files will be LOST[/yellow]\n")

        if not confirm("Continue with restore?", default=False):
            ssh.disconnect()
            raise typer.Exit()

        # Double confirmation
        console.print("\n[yellow]Type the site name to confirm:[/yellow] ", end="")
        confirmation = input().strip()

        if confirmation != site_name:
            print_error("Site name mismatch - restore cancelled")
            ssh.disconnect()
            raise typer.Exit()

        # Perform restore
        print_info(f"Restoring {site_name} from backup {backup_id}...")

        with console.status("[cyan]Restoring database and files...", spinner="dots"):
            backup_mgr.restore_backup(site_name, backup_id)

        print_success(f"Site {site_name} restored successfully")
        console.print("\n[dim]Site containers have been restarted[/dim]")

        ssh.disconnect()

    except Exception as e:
        print_error(f"Restore failed: {e}")
        raise typer.Exit(1)


@app.command("download")
def download_backup(
    site_name: str = typer.Argument(..., help="Site name"),
    backup_id: str = typer.Argument(..., help="Backup ID"),
    output_path: str = typer.Option("./", "--output", help="Local download path")
):
    """Download a backup to local machine"""
    import os

    try:
        # Validate output path
        if not os.path.exists(output_path):
            print_error(f"Output path does not exist: {output_path}")
            raise typer.Exit(1)

        ssh = SSHManager.from_config()
        ssh.connect()

        backup_mgr = BackupManager(ssh)

        # Verify backup exists
        backups = backup_mgr.list_backups()
        backup_found = False
        backup_filename = None

        for b in backups:
            if b['site'] == site_name and b['id'] == backup_id:
                backup_found = True
                backup_filename = b['filename']
                break

        if not backup_found:
            print_error(f"Backup not found: {site_name}_{backup_id}")
            ssh.disconnect()
            raise typer.Exit(1)

        # Download
        local_file = os.path.join(output_path, backup_filename)

        print_info(f"Downloading backup to {local_file}...")

        with console.status("[cyan]Downloading...", spinner="dots"):
            backup_mgr.download_backup(backup_id, site_name, local_file)

        print_success(f"Backup downloaded: {local_file}")

        ssh.disconnect()

    except Exception as e:
        print_error(f"Download failed: {e}")
        raise typer.Exit(1)


@app.command("delete")
def delete_backup(
    site_name: str = typer.Argument(..., help="Site name"),
    backup_id: str = typer.Argument(..., help="Backup ID to delete")
):
    """Delete a backup"""
    try:
        ssh = SSHManager.from_config()
        ssh.connect()

        backup_mgr = BackupManager(ssh)

        # Verify backup exists
        backups = backup_mgr.list_backups()
        backup_found = False
        backup_filename = None

        for b in backups:
            if b['site'] == site_name and b['id'] == backup_id:
                backup_found = True
                backup_filename = b['filename']
                backup_info = b
                break

        if not backup_found:
            print_error(f"Backup not found: {site_name}_{backup_id}")
            ssh.disconnect()
            raise typer.Exit(1)

        # Confirmation
        console.print(f"\n[bold]Delete Backup[/bold]")
        console.print(f"  Site: {site_name}")
        console.print(f"  Backup ID: {backup_id}")
        console.print(f"  Date: {backup_info['date']}")
        console.print(f"  Size: {backup_info['size']}\n")

        if not confirm("Delete this backup?", default=False):
            ssh.disconnect()
            raise typer.Exit()

        # Delete
        print_info("Deleting backup...")

        remote_path = f"{backup_mgr.backup_dir}/{backup_filename}"
        exit_code, _, stderr = ssh.run_command(f"sudo rm -f {remote_path}")

        if exit_code != 0:
            print_error(f"Failed to delete backup: {stderr}")
            ssh.disconnect()
            raise typer.Exit(1)

        print_success("Backup deleted")

        ssh.disconnect()

    except Exception as e:
        print_error(f"Failed to delete backup: {e}")
        raise typer.Exit(1)


@app.command("info")
def backup_info(
    site_name: str = typer.Argument(..., help="Site name"),
    backup_id: str = typer.Argument(..., help="Backup ID")
):
    """Show detailed backup information"""
    try:
        ssh = SSHManager.from_config()
        ssh.connect()

        backup_mgr = BackupManager(ssh)

        # Find backup
        backups = backup_mgr.list_backups()
        backup = None

        for b in backups:
            if b['site'] == site_name and b['id'] == backup_id:
                backup = b
                break

        if not backup:
            print_error(f"Backup not found: {site_name}_{backup_id}")
            ssh.disconnect()
            raise typer.Exit(1)

        # Get detailed info
        backup_path = f"{backup_mgr.backup_dir}/{backup['filename']}"

        # Check if compressed
        is_compressed = backup['filename'].endswith('.tar.gz')

        # Display info
        console.print(f"\n[bold cyan]Backup Information[/bold cyan]\n")
        console.print(f"[bold]Site:[/bold] {backup['site']}")
        console.print(f"[bold]Backup ID:[/bold] {backup['id']}")
        console.print(f"[bold]Date:[/bold] {backup['date']}")
        console.print(f"[bold]Size:[/bold] {backup['size']}")
        console.print(f"[bold]Compressed:[/bold] {'Yes' if is_compressed else 'No'}")
        console.print(f"[bold]Filename:[/bold] {backup['filename']}")
        console.print(f"[bold]Remote Path:[/bold] {backup_path}\n")

        ssh.disconnect()

    except Exception as e:
        print_error(f"Failed to get backup info: {e}")
        raise typer.Exit(1)


@app.command("configure-remote")
def configure_remote_backup():
    """Configure remote S3-compatible backup storage"""
    try:
        console.print("\n[bold cyan]Configure Remote Backup Storage[/bold cyan]\n")

        # Get configuration inputs
        console.print("[yellow]Provider types: s3 (AWS S3), r2 (Cloudflare R2), b2 (Backblaze B2)[/yellow]\n")

        provider = typer.prompt("Provider (s3/r2/b2)", default="s3")
        bucket = typer.prompt("Bucket name")
        access_key = typer.prompt("Access key ID")
        secret_key = typer.prompt("Secret access key", hide_input=True)

        endpoint = None
        region = None

        if provider in ['r2', 'b2']:
            endpoint = typer.prompt("S3 endpoint URL")

        if provider == 's3':
            region = typer.prompt("AWS region", default="us-east-1")

        encryption = confirm("Enable encryption?", default=True)
        retention_days = typer.prompt("Retention period (days)", default=30, type=int)

        # Load and update config
        config_mgr = ConfigManager()
        config = config_mgr.load_config()

        config.remote_backup.enabled = True
        config.remote_backup.provider = provider
        config.remote_backup.bucket = bucket
        config.remote_backup.access_key = access_key
        config.remote_backup.secret_key = secret_key
        config.remote_backup.endpoint = endpoint
        config.remote_backup.region = region
        config.remote_backup.encryption = encryption
        config.remote_backup.retention_days = retention_days

        config_mgr.save_config(config)

        print_success("Remote backup configuration saved")

        # Test configuration
        console.print("\n[yellow]Testing configuration...[/yellow]\n")

        ssh = SSHManager.from_config()
        ssh.connect()

        remote_mgr = RemoteBackupManager(ssh)

        # Check/install rclone
        if not remote_mgr.check_rclone_installed():
            print_info("Installing rclone on VPS...")
            remote_mgr.install_rclone()

        # Configure rclone
        print_info("Configuring rclone...")
        remote_mgr.configure_rclone(
            provider=provider,
            bucket=bucket,
            access_key=access_key,
            secret_key=secret_key,
            endpoint=endpoint,
            region=region
        )

        print_success("Remote backup configured and tested successfully!")
        console.print(f"\n[dim]Use --remote flag with 'vibewp backup create' to upload backups[/dim]\n")

        ssh.disconnect()

    except Exception as e:
        print_error(f"Configuration failed: {e}")
        raise typer.Exit(1)


@app.command("list-remote")
def list_remote_backups(
    site: str = typer.Option(None, "--site", help="Filter by site name")
):
    """List backups in remote S3 storage"""
    try:
        config_mgr = ConfigManager()
        remote_config = config_mgr.load_config().remote_backup

        if not remote_config.enabled:
            print_error("Remote backup not configured")
            raise typer.Exit(1)

        ssh = SSHManager.from_config()
        ssh.connect()

        remote_mgr = RemoteBackupManager(ssh)

        # Determine remote path
        remote_path = f"backups/{site}" if site else "backups"

        with console.status("[cyan]Fetching remote backup list...", spinner="dots"):
            backups = remote_mgr.list_remote_backups(
                bucket=remote_config.bucket,
                remote_path=remote_path
            )

        if not backups:
            print_info("No remote backups found")
            ssh.disconnect()
            return

        # Create table
        table = Table(title=f"Remote Backups ({remote_config.provider}:{remote_config.bucket})", show_header=True)
        table.add_column("Filename", style="cyan")
        table.add_column("Size", style="blue")

        for backup in backups:
            table.add_row(backup['filename'], backup['size'])

        console.print(table)
        console.print(f"\n[dim]Total: {len(backups)} backups[/dim]")

        # Show total size
        total_size = remote_mgr.get_remote_size(remote_config.bucket, remote_path)
        console.print(f"[dim]Total size: {total_size}[/dim]\n")

        ssh.disconnect()

    except Exception as e:
        print_error(f"Failed to list remote backups: {e}")
        raise typer.Exit(1)
