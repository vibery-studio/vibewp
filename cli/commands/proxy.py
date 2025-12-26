"""Caddy proxy management commands"""

import typer
from pathlib import Path
from cli.ui.console import print_success, print_error, print_info, print_warning
from cli.utils.config import ConfigManager
from cli.utils.docker import DockerManager

app = typer.Typer(help="Caddy reverse proxy management")


@app.command("deploy")
def deploy_proxy():
    """Deploy Caddy reverse proxy"""
    try:
        print_info("Deploying Caddy reverse proxy...")

        # Check if Docker is running
        docker_mgr = DockerManager()
        if not docker_mgr.is_running():
            print_error("Docker daemon is not running")
            print_info("Start Docker: systemctl start docker")
            raise typer.Exit(code=1)

        # Load config
        config_mgr = ConfigManager()
        network_name = config_mgr.docker.network_name

        # Ensure proxy network exists
        if not docker_mgr.network_exists(network_name):
            print_info(f"Creating proxy network '{network_name}'...")
            docker_mgr.create_network(network_name)
            print_success(f"✓ Network '{network_name}' created")
        else:
            print_info(f"✓ Network '{network_name}' already exists")

        # Check if Caddy is already running
        if docker_mgr.get_container("caddy_proxy"):
            print_warning("Caddy proxy is already running")
            if not typer.confirm("Redeploy Caddy proxy?", default=False):
                print_info("Deployment cancelled")
                raise typer.Exit(code=0)

            # Stop existing Caddy
            print_info("Stopping existing Caddy proxy...")
            import subprocess
            result = subprocess.run(
                ["docker", "compose", "-f", "/opt/vibewp/templates/caddy/docker-compose.yml", "down"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                print_error(f"Failed to stop Caddy: {result.stderr}")
                raise typer.Exit(code=1)

        # Deploy Caddy
        print_info("Starting Caddy proxy...")
        import subprocess
        result = subprocess.run(
            ["docker", "compose", "-f", "/opt/vibewp/templates/caddy/docker-compose.yml", "up", "-d"],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            print_error(f"Failed to deploy Caddy: {result.stderr}")
            raise typer.Exit(code=1)

        # Verify deployment
        import time
        time.sleep(2)

        container = docker_mgr.get_container("caddy_proxy")
        if container and container.status == "running":
            print_success("✓ Caddy proxy deployed successfully!")
            print_info("\nCaddy is now listening on:")
            print_info("  HTTP:  port 80")
            print_info("  HTTPS: port 443")
        else:
            print_error("Caddy container failed to start")
            print_info("Check logs: docker logs caddy_proxy")
            raise typer.Exit(code=1)

    except Exception as e:
        print_error(f"Failed to deploy Caddy proxy: {e}")
        raise typer.Exit(code=1)


@app.command("status")
def proxy_status():
    """Check Caddy proxy status"""
    try:
        docker_mgr = DockerManager()

        container = docker_mgr.get_container("caddy_proxy")
        if not container:
            print_warning("Caddy proxy is not running")
            print_info("\nTo deploy: vibewp proxy deploy")
            raise typer.Exit(code=1)

        # Get container details
        container.reload()
        status = container.status
        created = container.attrs['Created']

        print_info("=== Caddy Proxy Status ===\n")
        print_info(f"Container: caddy_proxy")
        print_info(f"Status: {status}")
        print_info(f"Image: {container.image.tags[0] if container.image.tags else 'unknown'}")
        print_info(f"Created: {created}")

        # Show ports
        ports = container.attrs['NetworkSettings']['Ports']
        if ports:
            print_info("\nPorts:")
            for port, bindings in ports.items():
                if bindings:
                    for binding in bindings:
                        print_info(f"  {binding['HostPort']} → {port}")

        # Show networks
        networks = container.attrs['NetworkSettings']['Networks']
        if networks:
            print_info("\nNetworks:")
            for network_name in networks.keys():
                print_info(f"  - {network_name}")

        if status == "running":
            print_success("\n✓ Caddy proxy is healthy")
        else:
            print_warning(f"\n⚠ Caddy proxy status: {status}")

    except Exception as e:
        print_error(f"Error checking proxy status: {e}")
        raise typer.Exit(code=1)


@app.command("logs")
def proxy_logs(
    tail: int = typer.Option(100, "--tail", help="Number of lines to show"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output")
):
    """Show Caddy proxy logs"""
    try:
        docker_mgr = DockerManager()

        container = docker_mgr.get_container("caddy_proxy")
        if not container:
            print_error("Caddy proxy is not running")
            raise typer.Exit(code=1)

        if follow:
            print_info("Following Caddy logs (Ctrl+C to stop)...\n")
            import subprocess
            subprocess.run(["docker", "logs", "-f", "--tail", str(tail), "caddy_proxy"])
        else:
            logs = docker_mgr.container_logs("caddy_proxy", tail=tail)
            print(logs)

    except KeyboardInterrupt:
        print_info("\nStopped following logs")
    except Exception as e:
        print_error(f"Error getting logs: {e}")
        raise typer.Exit(code=1)


@app.command("restart")
def proxy_restart():
    """Restart Caddy proxy"""
    try:
        docker_mgr = DockerManager()

        container = docker_mgr.get_container("caddy_proxy")
        if not container:
            print_error("Caddy proxy is not running")
            print_info("Deploy first: vibewp proxy deploy")
            raise typer.Exit(code=1)

        print_info("Restarting Caddy proxy...")
        container.restart(timeout=10)

        import time
        time.sleep(2)

        container.reload()
        if container.status == "running":
            print_success("✓ Caddy proxy restarted successfully")
        else:
            print_error("Failed to restart Caddy proxy")
            raise typer.Exit(code=1)

    except Exception as e:
        print_error(f"Error restarting proxy: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
