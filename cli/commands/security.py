"""Security auditing and monitoring commands"""

import typer
from rich.table import Table
from rich.panel import Panel
from cli.ui.console import console, print_success, print_error, print_warning, print_info, confirm
from cli.utils.ssh import SSHManager
from cli.utils.security import SecurityScanner, Fail2BanManager

app = typer.Typer(help="Security auditing and threat monitoring")


@app.command("scan")
def security_scan():
    """Run comprehensive security audit"""
    try:
        ssh = SSHManager.from_config()
        ssh.connect()

        scanner = SecurityScanner(ssh)

        with console.status("[cyan]Running security audit...", spinner="dots"):
            results = scanner.run_audit()

        # Display results
        console.print("\n[bold cyan]Security Audit Results[/bold cyan]\n")

        # SSH Security
        console.print("[bold]SSH Configuration:[/bold]")
        for check, status in results['ssh'].items():
            if 'error' in check:
                print_error(f"  {status['message']}")
                continue

            icon = "✓" if status['passed'] else "✗"
            color = "green" if status['passed'] else "red"
            console.print(f"  [{color}]{icon}[/{color}] {status['message']}")

        # Firewall
        console.print("\n[bold]Firewall:[/bold]")
        for check, status in results['firewall'].items():
            icon = "✓" if status['passed'] else "✗"
            color = "green" if status['passed'] else "red"
            console.print(f"  [{color}]{icon}[/{color}] {status['message']}")

        # Docker Security
        console.print("\n[bold]Docker Security:[/bold]")
        for check, status in results['docker'].items():
            icon = "✓" if status['passed'] else "✗"
            color = "green" if status['passed'] else "yellow"
            console.print(f"  [{color}]{icon}[/{color}] {status['message']}")

        # System Updates
        console.print("\n[bold]System Updates:[/bold]")
        updates = results['updates']
        if updates['security'] > 0:
            print_warning(f"  {updates['security']} security update(s) available")
        else:
            print_success("  No security updates pending")

        if updates['total'] > 0:
            print_info(f"  {updates['total']} total update(s) available")

        # Overall Score
        score = results['score']

        if score >= 80:
            score_color = "green"
            score_label = "GOOD"
        elif score >= 60:
            score_color = "yellow"
            score_label = "FAIR"
        else:
            score_color = "red"
            score_label = "POOR"

        console.print(f"\n[bold]Security Score:[/bold] [{score_color}]{score}/100 ({score_label})[/{score_color}]\n")

        # Recommendations
        if score < 80:
            console.print("[bold]Recommendations:[/bold]")

            if not results['firewall'].get('firewall_active', {}).get('passed', True):
                print_error("  CRITICAL: Enable firewall (sudo ufw enable)")

            if not results['ssh'].get('root_login_disabled', {}).get('passed', True):
                print_warning("  Disable root login in SSH config")

            if not results['ssh'].get('password_auth_disabled', {}).get('passed', True):
                print_warning("  Disable password authentication in SSH config")

            if not results['ssh'].get('custom_ssh_port', {}).get('passed', True):
                print_info("  Consider changing SSH port (vibewp ssh change-port <port>)")

            if not results['firewall'].get('fail2ban_active', {}).get('passed', True):
                print_warning("  Install and enable fail2ban")

            if updates['security'] > 0:
                print_warning(f"  Install {updates['security']} security update(s)")

        ssh.disconnect()

    except Exception as e:
        print_error(f"Security scan failed: {e}")
        raise typer.Exit(1)


@app.command("fail2ban-status")
def fail2ban_status():
    """Show fail2ban jail status and banned IPs"""
    try:
        ssh = SSHManager.from_config()
        ssh.connect()

        f2b = Fail2BanManager(ssh)

        with console.status("[cyan]Fetching fail2ban status...", spinner="dots"):
            jails = f2b.get_jails()

        if not jails:
            print_warning("No fail2ban jails found or fail2ban not installed")
            ssh.disconnect()
            return

        # Create status table
        table = Table(title="Fail2Ban Jails", show_header=True)
        table.add_column("Jail", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Currently Banned", style="red")
        table.add_column("Total Banned", style="yellow")

        for jail in jails:
            stats = f2b.get_jail_status(jail)
            table.add_row(
                jail,
                "Active",
                str(stats['currently_banned']),
                str(stats['total_banned'])
            )

        console.print(table)

        # Show banned IPs
        has_banned_ips = False
        banned_details = []

        for jail in jails:
            stats = f2b.get_jail_status(jail)
            if stats['banned_ips']:
                has_banned_ips = True
                banned_details.append((jail, stats['banned_ips']))

        if has_banned_ips:
            console.print("\n[bold]Currently Banned IPs:[/bold]\n")
            for jail, ips in banned_details:
                console.print(f"  [cyan]{jail}:[/cyan] {', '.join(ips)}")
        else:
            print_success("\nNo IPs currently banned")

        ssh.disconnect()

    except Exception as e:
        print_error(f"Failed to get fail2ban status: {e}")
        raise typer.Exit(1)


@app.command("unban")
def unban_ip(
    ip: str = typer.Argument(..., help="IP address to unban"),
    jail: str = typer.Option(None, help="Specific jail (default: all jails)")
):
    """Unban an IP address from fail2ban"""
    try:
        # Basic IP validation
        parts = ip.split('.')
        if len(parts) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
            print_error(f"Invalid IP address: {ip}")
            raise typer.Exit(1)

        ssh = SSHManager.from_config()
        ssh.connect()

        f2b = Fail2BanManager(ssh)

        if jail:
            print_info(f"Unbanning {ip} from jail '{jail}'...")
            f2b.unban_ip(ip, jail=jail)
            print_success(f"IP {ip} unbanned from {jail}")
        else:
            print_info(f"Unbanning {ip} from all jails...")
            f2b.unban_ip(ip)
            print_success(f"IP {ip} unbanned from all jails")

        ssh.disconnect()

    except Exception as e:
        print_error(f"Failed to unban IP: {e}")
        raise typer.Exit(1)


@app.command("check-updates")
def check_updates():
    """Check for available security updates"""
    try:
        ssh = SSHManager.from_config()
        ssh.connect()

        print_info("Checking for updates...")

        with console.status("[cyan]Updating package cache...", spinner="dots"):
            # Update package cache
            ssh.run_command("sudo apt-get update -qq 2>/dev/null")

        # Get upgradable packages
        exit_code, output, _ = ssh.run_command(
            "apt list --upgradable 2>/dev/null | tail -n +2"
        )

        if exit_code != 0 or not output.strip():
            print_success("All packages are up to date")
            ssh.disconnect()
            return

        packages = output.strip().split('\n')
        total_updates = len(packages)

        # Filter security updates
        security_packages = [p for p in packages if 'security' in p.lower()]
        security_updates = len(security_packages)

        # Display summary
        console.print(f"\n[bold]Update Summary:[/bold]")
        console.print(f"  Total updates: {total_updates}")

        if security_updates > 0:
            print_warning(f"  Security updates: {security_updates}")
        else:
            console.print(f"  Security updates: 0")

        # Show security updates
        if security_packages:
            console.print("\n[bold red]Security Updates Available:[/bold red]")
            for pkg in security_packages[:10]:  # Show first 10
                pkg_name = pkg.split('/')[0]
                console.print(f"  - {pkg_name}")

            if len(security_packages) > 10:
                console.print(f"  ... and {len(security_packages) - 10} more")

            console.print(f"\n[yellow]Run: sudo apt-get upgrade[/yellow]")

        ssh.disconnect()

    except Exception as e:
        print_error(f"Failed to check updates: {e}")
        raise typer.Exit(1)


@app.command("install-updates")
def install_updates(
    security_only: bool = typer.Option(False, "--security-only", help="Install only security updates")
):
    """Install available system updates"""
    try:
        ssh = SSHManager.from_config()
        ssh.connect()

        print_warning("This will update system packages")

        if not confirm("Continue with system updates?", default=False):
            ssh.disconnect()
            raise typer.Exit()

        if security_only:
            print_info("Installing security updates only...")
            cmd = "sudo apt-get upgrade -y --only-upgrade $(apt list --upgradable 2>/dev/null | grep security | cut -d'/' -f1)"
        else:
            print_info("Installing all available updates...")
            cmd = "sudo apt-get upgrade -y"

        # Update package cache first
        console.print("[cyan]Updating package cache...[/cyan]")
        ssh.run_command("sudo apt-get update")

        # Install updates
        console.print("[cyan]Installing updates (this may take several minutes)...[/cyan]")

        with console.status("[cyan]Installing...", spinner="dots"):
            exit_code, output, stderr = ssh.run_command(cmd, timeout=600)

        if exit_code == 0:
            print_success("System updates installed successfully")

            # Check if reboot required
            exit_code, reboot_check, _ = ssh.run_command("test -f /var/run/reboot-required && echo 'reboot' || echo 'ok'")

            if 'reboot' in reboot_check:
                print_warning("System reboot required to complete updates")
                console.print("[dim]Run: vibewp system reboot[/dim]")
        else:
            print_error("Update installation failed")
            console.print(f"[red]{stderr}[/red]")

        ssh.disconnect()

    except Exception as e:
        print_error(f"Failed to install updates: {e}")
        raise typer.Exit(1)
