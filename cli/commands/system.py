"""System monitoring and management commands"""

import typer
import time
from rich.table import Table
from rich.panel import Panel
from cli.ui.console import console, print_success, print_error, print_warning, print_info, confirm
from cli.utils.ssh import SSHManager

app = typer.Typer(help="System monitoring and resource management")


@app.command("status")
def system_status():
    """Display system resource usage (CPU, RAM, disk, load)"""
    try:
        ssh = SSHManager.from_config()
        ssh.connect()

        with console.status("[cyan]Gathering system metrics...", spinner="dots"):
            # CPU usage
            exit_code, cpu_output, _ = ssh.run_command(
                "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | sed 's/%us,//'"
            )
            cpu_usage = cpu_output.strip() if exit_code == 0 else "N/A"

            # Memory usage
            exit_code, mem_output, _ = ssh.run_command(
                "free -h | awk '/^Mem:/ {print $3\"/\"$2}'"
            )
            mem_usage = mem_output.strip() if exit_code == 0 else "N/A"

            # Memory percentage
            exit_code, mem_pct, _ = ssh.run_command(
                "free | awk '/^Mem:/ {printf \"%.1f\", $3/$2*100}'"
            )
            mem_percent = mem_pct.strip() if exit_code == 0 else "0"

            # Disk usage
            exit_code, disk_output, _ = ssh.run_command(
                "df -h / | awk 'NR==2 {print $3\"/\"$2\" (\"$5\")\"}'"
            )
            disk_usage = disk_output.strip() if exit_code == 0 else "N/A"

            # Load average
            exit_code, load_output, _ = ssh.run_command(
                "uptime | awk -F'load average:' '{print $2}' | sed 's/^ //'"
            )
            load_avg = load_output.strip() if exit_code == 0 else "N/A"

            # Uptime
            exit_code, uptime_output, _ = ssh.run_command(
                "uptime -p"
            )
            uptime_str = uptime_output.strip().replace('up ', '') if exit_code == 0 else "N/A"

        # Create status panel
        status_text = f"""
[bold]CPU Usage:[/bold] {cpu_usage}%
[bold]Memory:[/bold] {mem_usage} ({mem_percent}%)
[bold]Disk:[/bold] {disk_usage}
[bold]Load Average:[/bold] {load_avg}
[bold]Uptime:[/bold] {uptime_str}
        """

        panel = Panel(
            status_text.strip(),
            title="[bold cyan]System Status[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        )

        console.print(panel)

        # Color-coded warnings
        try:
            cpu_val = float(cpu_usage)
            if cpu_val > 80:
                print_warning("High CPU usage detected")
        except ValueError:
            pass

        try:
            mem_val = float(mem_percent)
            if mem_val > 85:
                print_warning("High memory usage detected")
        except ValueError:
            pass

        ssh.disconnect()

    except Exception as e:
        print_error(f"Failed to get system status: {e}")
        raise typer.Exit(1)


@app.command("docker-stats")
def docker_stats():
    """Show Docker container resource statistics"""
    try:
        ssh = SSHManager.from_config()
        ssh.connect()

        with console.status("[cyan]Fetching Docker stats...", spinner="dots"):
            exit_code, output, stderr = ssh.run_command(
                "docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}'"
            )

        if exit_code != 0:
            print_error(f"Failed to get Docker stats: {stderr}")
            ssh.disconnect()
            raise typer.Exit(1)

        if not output.strip():
            print_info("No Docker containers running")
            ssh.disconnect()
            return

        # Display raw output (already formatted as table)
        console.print("\n[bold cyan]Docker Container Statistics[/bold cyan]\n")
        console.print(output)

        ssh.disconnect()

    except Exception as e:
        print_error(f"Failed to get Docker stats: {e}")
        raise typer.Exit(1)


@app.command("logs")
def view_logs(
    lines: int = typer.Option(50, "--lines", "-n", help="Number of lines to show"),
    filter_text: str = typer.Option(None, "--filter", "-f", help="Filter logs by text"),
    service: str = typer.Option("syslog", "--service", "-s", help="Service to view logs for (syslog, docker, fail2ban)")
):
    """View and filter system logs"""
    try:
        ssh = SSHManager.from_config()
        ssh.connect()

        # Determine log file
        log_files = {
            'syslog': '/var/log/syslog',
            'docker': '/var/log/docker.log',
            'fail2ban': '/var/log/fail2ban.log',
            'auth': '/var/log/auth.log'
        }

        log_file = log_files.get(service, service)

        # Build command
        if filter_text:
            cmd = f"sudo tail -n {lines} {log_file} | grep -i '{filter_text}'"
        else:
            cmd = f"sudo tail -n {lines} {log_file}"

        with console.status(f"[cyan]Fetching logs from {service}...", spinner="dots"):
            exit_code, output, stderr = ssh.run_command(cmd)

        if exit_code != 0 and "grep" not in cmd:
            print_error(f"Failed to read logs: {stderr}")
            ssh.disconnect()
            raise typer.Exit(1)

        if not output.strip():
            print_info(f"No logs found matching filter: {filter_text}" if filter_text else "No logs available")
            ssh.disconnect()
            return

        # Display logs
        title = f"{service.capitalize()} Logs"
        if filter_text:
            title += f" (filtered: {filter_text})"

        panel = Panel(
            output,
            title=f"[bold]{title}[/bold]",
            border_style="cyan",
            padding=(1, 2)
        )

        console.print(panel)
        ssh.disconnect()

    except Exception as e:
        print_error(f"Failed to view logs: {e}")
        raise typer.Exit(1)


@app.command("cleanup")
def cleanup():
    """Clean up Docker resources (stopped containers, dangling images, unused volumes)"""
    try:
        ssh = SSHManager.from_config()
        ssh.connect()

        console.print("\n[bold]Docker Cleanup[/bold]\n")
        console.print("This will remove:")
        console.print("  - Stopped containers")
        console.print("  - Dangling images")
        console.print("  - Unused volumes")
        console.print("  - Build cache\n")

        if not confirm("Continue with cleanup?", default=False):
            ssh.disconnect()
            raise typer.Exit()

        results = {}

        # Remove stopped containers
        console.print("[cyan]Removing stopped containers...[/cyan]")
        exit_code, output, _ = ssh.run_command("docker container prune -f")
        results['containers'] = output

        # Remove dangling images
        console.print("[cyan]Removing dangling images...[/cyan]")
        exit_code, output, _ = ssh.run_command("docker image prune -f")
        results['images'] = output

        # Remove unused volumes
        console.print("[cyan]Removing unused volumes...[/cyan]")
        exit_code, output, _ = ssh.run_command("docker volume prune -f")
        results['volumes'] = output

        # Clean build cache
        console.print("[cyan]Cleaning build cache...[/cyan]")
        exit_code, output, _ = ssh.run_command("docker builder prune -f")
        results['cache'] = output

        print_success("\nCleanup complete!")

        # Show space reclaimed
        for key, value in results.items():
            if 'Total reclaimed space' in value:
                space = value.split('Total reclaimed space:')[1].strip()
                console.print(f"  {key.capitalize()}: {space}")

        ssh.disconnect()

    except Exception as e:
        print_error(f"Cleanup failed: {e}")
        raise typer.Exit(1)


@app.command("reboot")
def reboot():
    """Reboot the VPS (with countdown confirmation)"""
    try:
        console.print("\n[bold red]VPS Reboot[/bold red]\n")
        console.print("[yellow]This will restart the entire VPS server![/yellow]")
        console.print("[yellow]All services will be temporarily unavailable (1-2 minutes)[/yellow]\n")

        if not confirm("Are you absolutely sure?", default=False):
            raise typer.Exit()

        console.print("\n[yellow]Type 'REBOOT' to confirm:[/yellow] ", end="")
        confirmation = input().strip()

        if confirmation != "REBOOT":
            print_error("Reboot cancelled")
            raise typer.Exit()

        ssh = SSHManager.from_config()
        ssh.connect()

        # Countdown
        console.print("\n[bold]Rebooting in:[/bold]")
        for i in range(5, 0, -1):
            console.print(f"  {i}...", end="\r")
            time.sleep(1)

        console.print("\n[cyan]Initiating reboot...[/cyan]")

        # Send reboot command (connection will drop)
        try:
            ssh.run_command("sudo reboot", timeout=5)
        except Exception:
            # Expected to fail as connection drops
            pass

        console.print("\n[yellow]VPS is rebooting. This will take 1-2 minutes.[/yellow]")
        console.print("[dim]You can test reconnection with: vibewp ssh test[/dim]\n")

    except KeyboardInterrupt:
        print_error("\nReboot cancelled")
        raise typer.Exit()
    except Exception as e:
        print_error(f"Reboot command failed: {e}")
        raise typer.Exit(1)


@app.command("processes")
def list_processes(
    sort_by: str = typer.Option("cpu", help="Sort by: cpu, mem, pid, time"),
    limit: int = typer.Option(15, help="Number of processes to show")
):
    """List top processes by resource usage"""
    try:
        ssh = SSHManager.from_config()
        ssh.connect()

        # Map sort options to ps flags
        sort_map = {
            'cpu': '--sort=-pcpu',
            'mem': '--sort=-pmem',
            'pid': '--sort=pid',
            'time': '--sort=-time'
        }

        sort_flag = sort_map.get(sort_by, '--sort=-pcpu')

        cmd = f"ps aux {sort_flag} | head -n {limit + 1}"

        with console.status("[cyan]Fetching process list...", spinner="dots"):
            exit_code, output, _ = ssh.run_command(cmd)

        if exit_code != 0:
            print_error("Failed to get process list")
            ssh.disconnect()
            raise typer.Exit(1)

        console.print(f"\n[bold cyan]Top {limit} Processes (sorted by {sort_by})[/bold cyan]\n")
        console.print(output)

        ssh.disconnect()

    except Exception as e:
        print_error(f"Failed to list processes: {e}")
        raise typer.Exit(1)


@app.command("disk")
def disk_usage(
    all_filesystems: bool = typer.Option(False, "--all", "-a", help="Show all filesystems")
):
    """Show disk usage for all mounted filesystems"""
    try:
        ssh = SSHManager.from_config()
        ssh.connect()

        cmd = "df -h" if all_filesystems else "df -h -x tmpfs -x devtmpfs"

        with console.status("[cyan]Checking disk usage...", spinner="dots"):
            exit_code, output, _ = ssh.run_command(cmd)

        if exit_code != 0:
            print_error("Failed to get disk usage")
            ssh.disconnect()
            raise typer.Exit(1)

        console.print("\n[bold cyan]Disk Usage[/bold cyan]\n")
        console.print(output)

        # Parse and warn on high usage
        for line in output.split('\n')[1:]:
            if line.strip() and '%' in line:
                parts = line.split()
                if len(parts) >= 5:
                    usage_pct = parts[4].replace('%', '')
                    mount_point = parts[5]
                    try:
                        if int(usage_pct) > 85:
                            print_warning(f"High disk usage on {mount_point}: {usage_pct}%")
                    except ValueError:
                        pass

        ssh.disconnect()

    except Exception as e:
        print_error(f"Failed to check disk usage: {e}")
        raise typer.Exit(1)
