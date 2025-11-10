"""Firewall management commands"""

import typer
from rich.table import Table
from cli.ui.console import console, print_success, print_error, print_warning, print_info, confirm
from cli.utils.ssh import SSHManager
from cli.utils.firewall import FirewallManager

app = typer.Typer(help="Firewall control and port management")


@app.command("list")
def list_rules():
    """Display all active firewall rules"""
    try:
        with console.status("[cyan]Fetching firewall rules...", spinner="dots"):
            ssh = SSHManager.from_config()
            ssh.connect()

            fw = FirewallManager(ssh)
            rules = fw.get_rules()

        if not rules:
            print_info("No firewall rules found")
            return

        # Create table
        table = Table(title="UFW Firewall Rules", show_header=True)
        table.add_column("No.", style="cyan", width=6)
        table.add_column("Port", style="green")
        table.add_column("Protocol", style="blue")
        table.add_column("Action", style="yellow")
        table.add_column("From", style="magenta")

        for rule in rules:
            table.add_row(
                rule['num'],
                rule['port'],
                rule['protocol'],
                rule['action'],
                rule['from']
            )

        console.print(table)
        ssh.disconnect()

    except Exception as e:
        print_error(f"Failed to list firewall rules: {e}")
        raise typer.Exit(1)


@app.command("open")
def open_port(
    port: int = typer.Argument(..., help="Port number to open"),
    protocol: str = typer.Option("tcp", help="Protocol (tcp/udp)"),
    limit: bool = typer.Option(False, "--limit", help="Use LIMIT for rate limiting (SSH protection)")
):
    """Open a port in the firewall"""
    try:
        # Validate port range
        if not 1 <= port <= 65535:
            print_error("Port must be between 1-65535")
            raise typer.Exit(1)

        # Warn about reserved ports
        if port < 1024:
            print_warning(f"Port {port} is reserved (requires root privileges)")
            if not confirm("Continue?", default=False):
                raise typer.Exit()

        # Validate protocol
        if protocol not in ['tcp', 'udp']:
            print_error("Protocol must be 'tcp' or 'udp'")
            raise typer.Exit(1)

        ssh = SSHManager.from_config()
        ssh.connect()

        fw = FirewallManager(ssh)

        # Check if already open
        if fw.is_port_open(port, protocol):
            print_warning(f"Port {port}/{protocol} is already open")
            ssh.disconnect()
            return

        # Open port
        print_info(f"Opening port {port}/{protocol}...")
        action_type = "LIMIT" if limit else "ALLOW"

        with console.status(f"[cyan]Configuring firewall...", spinner="dots"):
            fw.open_port(port, protocol, limit=limit)

        print_success(f"Port {port}/{protocol} opened ({action_type})")
        ssh.disconnect()

    except Exception as e:
        print_error(f"Failed to open port: {e}")
        raise typer.Exit(1)


@app.command("close")
def close_port(
    port: int = typer.Argument(..., help="Port number to close"),
    protocol: str = typer.Option("tcp", help="Protocol (tcp/udp)")
):
    """Close a port in the firewall"""
    try:
        ssh = SSHManager.from_config()
        ssh.connect()

        fw = FirewallManager(ssh)

        # Get current SSH port
        current_ssh_port = ssh.get_current_port()

        # Prevent closing SSH port
        if port == current_ssh_port and protocol == "tcp":
            print_error(f"Cannot close SSH port {port}!")
            print_warning("This would lock you out of the VPS")
            ssh.disconnect()
            raise typer.Exit(1)

        # Check if port is actually open
        if not fw.is_port_open(port, protocol):
            print_warning(f"Port {port}/{protocol} is not currently open")
            ssh.disconnect()
            return

        # Confirmation
        print_warning(f"This will close port {port}/{protocol}")
        if not confirm("Continue?", default=False):
            ssh.disconnect()
            raise typer.Exit()

        # Close port
        print_info(f"Closing port {port}/{protocol}...")

        with console.status("[cyan]Updating firewall...", spinner="dots"):
            fw.close_port(port, protocol)

        print_success(f"Port {port}/{protocol} closed")
        ssh.disconnect()

    except Exception as e:
        print_error(f"Failed to close port: {e}")
        raise typer.Exit(1)


@app.command("status")
def status():
    """Show firewall status and statistics"""
    try:
        with console.status("[cyan]Checking firewall status...", spinner="dots"):
            ssh = SSHManager.from_config()
            ssh.connect()

            fw = FirewallManager(ssh)
            fw_status = fw.get_status()
            rules = fw.get_rules()

        # Display status
        console.print("\n[bold]Firewall Status[/bold]\n")

        status_color = "green" if fw_status['active'] == 'active' else "red"
        console.print(f"[bold]Status:[/bold] [{status_color}]{fw_status['active']}[/{status_color}]")

        console.print(f"[bold]Default Incoming:[/bold] {fw_status['default_incoming']}")
        console.print(f"[bold]Default Outgoing:[/bold] {fw_status['default_outgoing']}")
        console.print(f"[bold]Total Rules:[/bold] {fw_status['total_rules']}")

        # Show open ports summary
        if rules:
            console.print("\n[bold]Open Ports:[/bold]")
            for rule in rules:
                console.print(f"  {rule['port']}/{rule['protocol']} - {rule['action']}")

        ssh.disconnect()

    except Exception as e:
        print_error(f"Failed to get firewall status: {e}")
        raise typer.Exit(1)
