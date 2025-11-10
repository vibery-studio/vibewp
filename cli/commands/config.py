"""Configuration management commands for VibeWP CLI"""

import yaml
from cli.utils.config import ConfigManager
from cli.ui.console import (
    console,
    print_success,
    print_error,
    print_info,
    print_header
)


def show_config() -> None:
    """Display current configuration"""
    try:
        config_mgr = ConfigManager()
        config = config_mgr.load_config()

        # Print header
        print_header("VibeWP Configuration", f"Location: {config_mgr.config_path}")

        # VPS Configuration
        console.print("\n[bold]VPS Connection:[/bold]")
        console.print(f"  Host:     [highlight]{config.vps.host}[/highlight]")
        console.print(f"  Port:     {config.vps.port}")
        console.print(f"  User:     {config.vps.user}")
        console.print(f"  SSH Key:  [muted]{config.vps.key_path}[/muted]")

        # WordPress Configuration
        console.print("\n[bold]WordPress Defaults:[/bold]")
        console.print(f"  Admin Email:  {config.wordpress.default_admin_email}")
        console.print(f"  Timezone:     {config.wordpress.default_timezone}")
        console.print(f"  Locale:       {config.wordpress.default_locale}")

        # Docker Configuration
        console.print("\n[bold]Docker Settings:[/bold]")
        console.print(f"  Base Path:     {config.docker.base_path}")
        console.print(f"  Network Name:  {config.docker.network_name}")

        # Sites
        console.print(f"\n[bold]Deployed Sites:[/bold] {len(config.sites)}")
        if config.sites:
            for site in config.sites:
                console.print(f"  • {site.name} ({site.domain}) - {site.status}")
        else:
            console.print("  [muted]No sites deployed yet[/muted]")

    except Exception as e:
        print_error(f"Failed to load config: {e}")
        raise


def edit_config() -> None:
    """Edit configuration file"""
    import subprocess
    import os

    try:
        config_mgr = ConfigManager()

        # Get editor from environment or use default
        editor = os.environ.get('EDITOR', 'vim')

        print_info(f"Opening config in {editor}...")
        subprocess.run([editor, str(config_mgr.config_path)])

        # Validate config after edit
        try:
            config_mgr.load_config()
            print_success("Configuration is valid")
        except Exception as e:
            print_error(f"Configuration validation failed: {e}")

    except Exception as e:
        print_error(f"Failed to edit config: {e}")
        raise


def reset_config() -> None:
    """Reset configuration to defaults"""
    from cli.ui.console import confirm

    try:
        config_mgr = ConfigManager()

        if not confirm("This will reset all configuration. Continue?", default=False):
            print_info("Reset cancelled")
            return

        # Backup existing config
        if config_mgr.config_path.exists():
            backup_path = config_mgr.config_path.with_suffix('.backup')
            config_mgr.config_path.rename(backup_path)
            print_info(f"Backup saved to {backup_path}")

        # Initialize new config
        config_mgr.init_config()
        print_success("Configuration reset to defaults")

    except Exception as e:
        print_error(f"Failed to reset config: {e}")
        raise


def export_config(output_path: str) -> None:
    """
    Export configuration to file

    Args:
        output_path: Path to export config to
    """
    try:
        config_mgr = ConfigManager()
        config = config_mgr.load_config()

        with open(output_path, 'w') as f:
            yaml.safe_dump(
                config.model_dump(),
                f,
                default_flow_style=False,
                sort_keys=False
            )

        print_success(f"Configuration exported to {output_path}")

    except Exception as e:
        print_error(f"Failed to export config: {e}")
        raise


def import_config(input_path: str) -> None:
    """
    Import configuration from file

    Args:
        input_path: Path to import config from
    """
    from cli.ui.console import confirm

    try:
        config_mgr = ConfigManager()

        # Load and validate new config
        with open(input_path, 'r') as f:
            data = yaml.safe_load(f)

        from cli.utils.config import VibeWPConfig
        new_config = VibeWPConfig(**data)

        # Confirm import
        if not confirm(f"Import configuration from {input_path}?", default=False):
            print_info("Import cancelled")
            return

        # Save config
        config_mgr.save_config(new_config)
        print_success("Configuration imported successfully")

    except Exception as e:
        print_error(f"Failed to import config: {e}")
        raise
