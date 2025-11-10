"""SSH configuration and management commands"""

import typer
from rich.syntax import Syntax
from rich.panel import Panel
import time
from cli.ui.console import console, print_success, print_error, print_warning, print_info, confirm
from cli.utils.ssh import SSHManager
from cli.utils.firewall import FirewallManager

app = typer.Typer(help="SSH configuration and key management")


@app.command("change-port")
def change_port(new_port: int = typer.Argument(..., help="New SSH port number")):
    """Change SSH port with safety checks and rollback capability"""
    try:
        # Validate port (use high ports to avoid conflicts)
        if not 1024 <= new_port <= 65535:
            print_error("Port must be between 1024-65535 (non-privileged ports)")
            raise typer.Exit(1)

        ssh = SSHManager.from_config()
        ssh.connect()

        current_port = ssh.get_current_port()

        if new_port == current_port:
            print_warning(f"SSH is already using port {new_port}")
            ssh.disconnect()
            return

        # Preview changes
        console.print("\n[bold cyan]SSH Port Change Plan[/bold cyan]\n")
        console.print(f"  [bold]Current port:[/bold] {current_port}")
        console.print(f"  [bold]New port:[/bold] {new_port}\n")

        console.print("[bold]Safety Steps:[/bold]")
        console.print("  1. Add UFW rule for new port (LIMIT for brute force protection)")
        console.print("  2. Update /etc/ssh/sshd_config")
        console.print("  3. Restart SSH service")
        console.print("  4. Test new port connection")
        console.print("  5. Remove old UFW rule (only if test succeeds)")
        console.print("  6. Update local config\n")

        print_warning("IMPORTANT: Keep this terminal window open during the process!")
        console.print("[dim]If something goes wrong, we'll rollback automatically[/dim]\n")

        if not confirm("Proceed with SSH port change?", default=False):
            ssh.disconnect()
            raise typer.Exit()

        try:
            fw = FirewallManager(ssh)

            # Step 1: Add new UFW rule
            console.print("\n[cyan]Step 1/6: Adding UFW rule for new port...[/cyan]")
            fw.open_port(new_port, "tcp", limit=True)
            print_success(f"UFW rule added for port {new_port}")
            time.sleep(1)

            # Step 2: Update sshd_config
            console.print("[cyan]Step 2/6: Updating SSH configuration...[/cyan]")
            ssh.update_ssh_config("Port", str(new_port))
            print_success("SSH config updated")
            time.sleep(1)

            # Step 3: Restart sshd
            console.print("[cyan]Step 3/6: Restarting SSH service...[/cyan]")
            print_warning("Current connection will remain active")
            ssh.restart_ssh_service()
            print_success("SSH service restarted")
            time.sleep(2)

            # Step 4: Test connection
            console.print(f"[cyan]Step 4/6: Testing connection on port {new_port}...[/cyan]")

            test_success = False
            for attempt in range(1, 4):
                console.print(f"  Attempt {attempt}/3...", end=" ")

                if ssh.test_ssh_connection(new_port, timeout=5):
                    console.print("[green]OK[/green]")
                    test_success = True
                    break
                else:
                    console.print("[yellow]WAIT[/yellow]")
                    time.sleep(2)

            if test_success:
                print_success(f"New port {new_port} is accessible")

                # Step 5: Remove old rule
                console.print("[cyan]Step 5/6: Removing old UFW rule...[/cyan]")
                fw.close_port(current_port, "tcp")
                print_success(f"Old port {current_port} rule removed")

                # Step 6: Update local config
                console.print("[cyan]Step 6/6: Updating local configuration...[/cyan]")
                ssh.save_new_port(new_port)
                print_success("Local config updated")

                console.print(f"\n[bold green]SSH port successfully changed to {new_port}[/bold green]")
                console.print(f"\n[yellow]Next SSH connection:[/yellow] ssh -p {new_port} {ssh.user}@{ssh.host}")

            else:
                # Test failed - rollback
                print_error("Connection test FAILED")
                console.print("[yellow]Rolling back changes...[/yellow]\n")

                # Restore old port
                console.print("  Restoring SSH config...")
                ssh.update_ssh_config("Port", str(current_port))
                ssh.restart_ssh_service()

                # Remove new UFW rule
                console.print("  Removing new firewall rule...")
                fw.close_port(new_port, "tcp")

                print_warning("Rollback complete - SSH remains on port " + str(current_port))

        except Exception as e:
            print_error(f"Error during port change: {e}")
            print_warning("Attempting rollback...")

            try:
                ssh.update_ssh_config("Port", str(current_port))
                ssh.restart_ssh_service()
                print_warning(f"SSH port restored to {current_port}")
            except Exception:
                print_error("Rollback failed - manual intervention may be required")

            raise typer.Exit(1)

        finally:
            ssh.disconnect()

    except Exception as e:
        print_error(f"Failed to change SSH port: {e}")
        raise typer.Exit(1)


@app.command("show-config")
def show_config():
    """Display current SSH daemon configuration"""
    try:
        with console.status("[cyan]Fetching SSH configuration...", spinner="dots"):
            ssh = SSHManager.from_config()
            ssh.connect()

            config_content = ssh.get_ssh_config()
            current_port = ssh.get_current_port()

        # Display with syntax highlighting
        syntax = Syntax(
            config_content,
            "sshd_config",
            theme="monokai",
            line_numbers=True,
            word_wrap=True
        )

        panel = Panel(
            syntax,
            title=f"[bold]SSH Configuration[/bold] (Port: {current_port})",
            border_style="cyan"
        )

        console.print(panel)
        ssh.disconnect()

    except Exception as e:
        print_error(f"Failed to show SSH config: {e}")
        raise typer.Exit(1)


@app.command("add-key")
def add_key(key_path: str = typer.Argument(..., help="Path to public key file")):
    """Add SSH public key to authorized_keys"""
    import os

    try:
        # Validate key file exists
        if not os.path.exists(key_path):
            print_error(f"File not found: {key_path}")
            raise typer.Exit(1)

        # Read public key
        with open(key_path, 'r') as f:
            public_key = f.read().strip()

        # Validate key format
        valid_types = ['ssh-rsa', 'ssh-ed25519', 'ecdsa-sha2-nistp256', 'ecdsa-sha2-nistp384', 'ecdsa-sha2-nistp521']

        if not any(public_key.startswith(key_type) for key_type in valid_types):
            print_error("Invalid SSH public key format")
            print_info(f"Expected one of: {', '.join(valid_types)}")
            raise typer.Exit(1)

        # Preview key
        key_parts = public_key.split()
        key_type = key_parts[0] if key_parts else "unknown"
        key_comment = key_parts[2] if len(key_parts) > 2 else "no comment"

        console.print(f"\n[bold]Key Type:[/bold] {key_type}")
        console.print(f"[bold]Comment:[/bold] {key_comment}\n")

        if not confirm("Add this key to authorized_keys?", default=True):
            raise typer.Exit()

        # Add key
        ssh = SSHManager.from_config()
        ssh.connect()

        with console.status("[cyan]Adding SSH key...", spinner="dots"):
            ssh.add_authorized_key(public_key)

        print_success("SSH key added successfully")
        ssh.disconnect()

    except Exception as e:
        print_error(f"Failed to add SSH key: {e}")
        raise typer.Exit(1)


@app.command("remove-key")
def remove_key(pattern: str = typer.Argument(..., help="Pattern to match (comment, fingerprint, or part of key)")):
    """Remove SSH key from authorized_keys by pattern"""
    try:
        print_warning(f"This will remove keys matching: {pattern}")

        if not confirm("Continue?", default=False):
            raise typer.Exit()

        ssh = SSHManager.from_config()
        ssh.connect()

        with console.status("[cyan]Removing SSH key...", spinner="dots"):
            ssh.remove_authorized_key(pattern)

        print_success("SSH key removed")
        print_warning("Verify you can still connect with another key!")
        ssh.disconnect()

    except Exception as e:
        print_error(f"Failed to remove SSH key: {e}")
        raise typer.Exit(1)


@app.command("test")
def test_connection():
    """Test SSH connection to VPS"""
    try:
        ssh = SSHManager.from_config()

        console.print(f"\n[bold]Testing SSH Connection[/bold]")
        console.print(f"Host: {ssh.host}")
        console.print(f"Port: {ssh.port}")
        console.print(f"User: {ssh.user}\n")

        with console.status("[cyan]Connecting...", spinner="dots"):
            ssh.connect()

        print_success("SSH connection successful!")

        # Test command execution
        with console.status("[cyan]Running test command...", spinner="dots"):
            exit_code, hostname, _ = ssh.run_command("hostname")

        if exit_code == 0:
            console.print(f"[bold]Remote hostname:[/bold] {hostname}")

        ssh.disconnect()

    except Exception as e:
        print_error(f"SSH connection failed: {e}")
        raise typer.Exit(1)
