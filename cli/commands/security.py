"""Security auditing and monitoring commands"""

import typer
from pathlib import Path
from rich.table import Table
from rich.panel import Panel
from cli.ui.console import console, print_success, print_error, print_warning, print_info, confirm
from cli.utils.ssh import SSHManager
from cli.utils.config import ConfigManager
from cli.utils.security import SecurityScanner, Fail2BanManager
from cli.utils.server_audit import ServerAuditManager

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


@app.command("audit-server")
def audit_server(
    format: str = typer.Option("console", "--format", help="Output format: console, json, html, pdf"),
    output: str = typer.Option(None, "--output", help="Output file path"),
    wp_api_token: str = typer.Option(None, "--wp-api-token", help="WPScan API token (overrides config)"),
    skip_wordpress: bool = typer.Option(False, "--skip-wordpress", help="Skip WordPress audits"),
    skip_lynis: bool = typer.Option(False, "--skip-lynis", help="Skip Lynis integration"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed progress")
):
    """Run comprehensive server security audit"""
    try:
        # Load configuration
        config = ConfigManager()
        config.load_config()

        # Connect to VPS
        ssh = SSHManager.from_config()

        with console.status("[cyan]Connecting to VPS...", spinner="dots"):
            ssh.connect()

        print_success("Connected to VPS")

        # Initialize audit manager
        audit_manager = ServerAuditManager(ssh, config)

        # Get WPScan API token (from parameter or config)
        api_token = wp_api_token
        if not api_token and not skip_wordpress:
            api_token = config.get_wpscan_token() if hasattr(config, 'get_wpscan_token') else None
            if not api_token and verbose:
                print_info("No WPScan API token configured - vulnerability scanning will be skipped")

        # Run audit with progress indicator
        print_info("Starting comprehensive security audit...")
        console.print("[dim]This may take several minutes depending on system size[/dim]\n")

        try:
            with console.status("[cyan]Running security audit...", spinner="dots") as status:
                if verbose:
                    status.stop()
                    console.print("[cyan]Running system-level security checks...[/cyan]")

                audit_results = audit_manager.run_full_audit(
                    skip_wordpress=skip_wordpress,
                    skip_lynis=skip_lynis,
                    wpscan_api_token=api_token,
                    verbose=verbose
                )

                if verbose:
                    console.print("[green]✓[/green] Audit completed")
        except KeyboardInterrupt:
            print_warning("\nAudit interrupted by user")
            ssh.disconnect()
            raise typer.Exit(130)

        # Check for errors
        if audit_results.get('errors'):
            print_warning(f"Audit completed with {len(audit_results['errors'])} error(s)")
            if verbose:
                for error in audit_results['errors']:
                    print_error(f"  {error['component']}: {error['error']}")

        # Generate report
        if verbose:
            console.print("\n[cyan]Generating report...[/cyan]")

        report_content = audit_manager.generate_report(audit_results, format)

        # Display or save report
        if output:
            # Save to file
            output_path = Path(output).expanduser()
            audit_manager.save_report(report_content, str(output_path), format)
            print_success(f"Report saved to: {output_path}")

            # Also show summary in console
            if format != 'console':
                console.print("\n[bold]Audit Summary:[/bold]")
                console.print(f"Overall Score: [{_get_score_color_name(audit_results['overall_score'])}]{audit_results['overall_score']}/100[/]")
                console.print(f"Timestamp: {audit_results['timestamp']}")

                # Count findings by severity
                all_findings = _collect_findings(audit_results)
                critical = len([f for f in all_findings if f['severity'] == 'critical'])
                high = len([f for f in all_findings if f['severity'] == 'high'])
                medium = len([f for f in all_findings if f['severity'] == 'medium'])
                low = len([f for f in all_findings if f['severity'] == 'low'])

                console.print(f"\nFindings:")
                if critical > 0:
                    console.print(f"  [red]Critical: {critical}[/red]")
                if high > 0:
                    console.print(f"  [orange1]High: {high}[/orange1]")
                if medium > 0:
                    console.print(f"  [yellow]Medium: {medium}[/yellow]")
                if low > 0:
                    console.print(f"  [green]Low: {low}[/green]")

        else:
            # Display in console
            if format == 'console':
                console.print("\n")
                console.print(report_content)
            else:
                # Non-console format without output path - print to stdout
                print(report_content)

        ssh.disconnect()

    except Exception as e:
        print_error(f"Security audit failed: {e}")
        if verbose:
            import traceback
            console.print(f"[red]{traceback.format_exc()}[/red]")
        raise typer.Exit(1)


def _get_score_color_name(score: int) -> str:
    """Get color name for score"""
    if score >= 80:
        return "green"
    elif score >= 60:
        return "yellow"
    elif score >= 40:
        return "orange1"
    else:
        return "red"


def _collect_findings(audit_data: dict) -> list:
    """Collect all findings from audit data"""
    findings = []

    # System findings
    if 'system' in audit_data:
        for category_data in audit_data['system'].values():
            if isinstance(category_data, dict) and 'findings' in category_data:
                findings.extend(category_data['findings'])

    # WordPress findings
    if 'wordpress' in audit_data:
        if 'findings' in audit_data['wordpress']:
            findings.extend(audit_data['wordpress']['findings'])
        if 'sites' in audit_data['wordpress']:
            for site_data in audit_data['wordpress']['sites'].values():
                if 'findings' in site_data:
                    findings.extend(site_data['findings'])

    # Vulnerability findings
    if 'vulnerabilities' in audit_data:
        if 'findings' in audit_data['vulnerabilities']:
            findings.extend(audit_data['vulnerabilities']['findings'])
        if 'sites' in audit_data['vulnerabilities']:
            for site_data in audit_data['vulnerabilities']['sites'].values():
                if 'findings' in site_data:
                    findings.extend(site_data['findings'])

    return findings


@app.command("set-wpscan-token")
def set_wpscan_token(
    token: str = typer.Argument(..., help="WPScan API token")
):
    """Configure WPScan API token for vulnerability scanning"""
    try:
        config = ConfigManager()
        config.load_config()
        config.set_wpscan_token(token)
        print_success("WPScan API token saved to configuration")
        print_info("Token will be used for vulnerability scanning in audit-server command")
        console.print("[dim]Note: Get your free API token from https://wpscan.com/api[/dim]")

    except Exception as e:
        print_error(f"Failed to save token: {e}")
        raise typer.Exit(1)


@app.command("clear-wpscan-token")
def clear_wpscan_token():
    """Remove WPScan API token from configuration"""
    try:
        config = ConfigManager()
        config.load_config()
        config.clear_wpscan_token()
        print_success("WPScan API token removed from configuration")

    except Exception as e:
        print_error(f"Failed to clear token: {e}")
        raise typer.Exit(1)
