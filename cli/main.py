"""Main entry point for VibeWP CLI"""

import typer
from typing import Optional
from cli import __version__
from cli.ui.menu import show_main_menu
from cli.ui.console import print_success, print_error, print_info
from cli.utils.config import ConfigManager

# Create Typer app
app = typer.Typer(
    name="vibewp",
    help="VPS WordPress Manager - CLI for managing WordPress sites on VPS",
    add_completion=True
)

# Create subcommands
config_app = typer.Typer(help="Configuration management")
app.add_typer(config_app, name="config")

# Import all command groups
from cli.commands.site import app as site_app
from cli.commands import firewall, ssh_cmd, security, system, backup, domain, update, sftp, doctor, proxy, php

# Register command groups
app.add_typer(site_app, name="site")
app.add_typer(domain.app, name="domain")
app.add_typer(firewall.app, name="firewall")
app.add_typer(ssh_cmd.app, name="ssh")
app.add_typer(security.app, name="security")
app.add_typer(system.app, name="system")
app.add_typer(backup.app, name="backup")
app.add_typer(update.app, name="update")
app.add_typer(sftp.app, name="sftp")
app.add_typer(doctor.app, name="doctor")
app.add_typer(proxy.app, name="proxy")
app.add_typer(php.app, name="php")


def version_callback(value: bool):
    """Show version and exit"""
    if value:
        from cli.utils.update import UpdateManager
        try:
            manager = UpdateManager()
            install_method = manager.install_method.value
            typer.echo(f"VibeWP CLI v{__version__} ({install_method})")
        except Exception:
            typer.echo(f"VibeWP CLI v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "-v",
        "--version",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True
    )
):
    """
    VibeWP - VPS WordPress Manager

    Manage WordPress sites on your VPS with ease.
    """
    pass


@app.command()
def menu():
    """Launch interactive menu"""
    try:
        show_main_menu()
    except KeyboardInterrupt:
        print_info("\nExiting...")
    except Exception as e:
        print_error(f"Error: {e}")
        raise typer.Exit(code=1)


@config_app.command("init")
def config_init():
    """Initialize configuration file"""
    try:
        config_mgr = ConfigManager()
        config_mgr.init_config()
        print_success(f"Configuration initialized at {config_mgr.config_path}")
    except Exception as e:
        print_error(f"Failed to initialize config: {e}")
        raise typer.Exit(code=1)


@config_app.command("show")
def config_show():
    """Show current configuration"""
    from cli.commands.config import show_config

    try:
        show_config()
    except Exception as e:
        print_error(f"Failed to show config: {e}")
        raise typer.Exit(code=1)


@config_app.command("path")
def config_path():
    """Show configuration file path"""
    try:
        config_mgr = ConfigManager()
        print_info(f"Configuration file: {config_mgr.config_path}")
    except Exception as e:
        print_error(f"Error: {e}")
        raise typer.Exit(code=1)


@app.command()
def test_ssh():
    """Test SSH connection to VPS"""
    from cli.utils.config import ConfigManager
    from cli.utils.ssh import SSHManager

    try:
        # Load config
        config_mgr = ConfigManager()
        vps_config = config_mgr.vps

        print_info(f"Testing SSH connection to {vps_config.host}:{vps_config.port}...")

        # Test connection
        ssh = SSHManager(
            host=vps_config.host,
            port=vps_config.port,
            user=vps_config.user,
            key_path=vps_config.key_path
        )

        ssh.connect()
        print_success("SSH connection successful!")

        # Run test command
        exit_code, stdout, stderr = ssh.run_command("hostname")
        if exit_code == 0:
            print_success(f"Remote hostname: {stdout}")
        else:
            print_error(f"Command failed: {stderr}")

        ssh.disconnect()

    except Exception as e:
        print_error(f"SSH connection failed: {e}")
        raise typer.Exit(code=1)


@app.command()
def test_docker():
    """Test Docker connection"""
    from cli.utils.docker import DockerManager

    try:
        print_info("Testing Docker connection...")

        docker_mgr = DockerManager()

        if docker_mgr.is_running():
            print_success("Docker daemon is running!")

            # Show Docker info
            containers = docker_mgr.list_containers(all=True)
            print_info(f"Total containers: {len(containers)}")

        else:
            print_error("Docker daemon is not running")
            raise typer.Exit(code=1)

    except Exception as e:
        print_error(f"Docker connection failed: {e}")
        raise typer.Exit(code=1)


@app.command()
def test_templates():
    """Test template rendering"""
    from cli.utils.template import TemplateRenderer

    try:
        print_info("Testing template rendering...")

        renderer = TemplateRenderer()

        # List templates
        templates = renderer.list_templates("*.yml")
        print_info(f"Found {len(templates)} templates:")
        for template in templates:
            print_info(f"  - {template}")

        print_success("Template system working!")

    except Exception as e:
        print_error(f"Template test failed: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
