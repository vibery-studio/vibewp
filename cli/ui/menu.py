"""Interactive menu system for VibeWP CLI"""

from simple_term_menu import TerminalMenu
from cli.ui.console import (
    console,
    print_banner,
    print_success,
    print_error,
    print_info,
    confirm
)
from typing import Optional, Callable, List


class MenuOption:
    """Represents a menu option"""

    def __init__(
        self,
        label: str,
        action: Optional[Callable] = None,
        icon: str = "",
        submenu: Optional['Menu'] = None
    ):
        self.label = label
        self.action = action
        self.icon = icon
        self.submenu = submenu

    @property
    def display_label(self) -> str:
        """Get display label with icon"""
        if self.icon:
            return f"{self.icon}  {self.label}"
        return self.label


class Menu:
    """Interactive menu"""

    def __init__(
        self,
        title: str,
        options: List[MenuOption],
        show_back: bool = False
    ):
        self.title = title
        self.options = options
        self.show_back = show_back

    def show(self) -> Optional[int]:
        """
        Display menu and get user selection

        Returns:
            Index of selected option or None if cancelled
        """
        # Build menu items
        menu_items = [opt.display_label for opt in self.options]

        if self.show_back:
            menu_items.append("← Back")

        # Create terminal menu
        terminal_menu = TerminalMenu(
            menu_items,
            title=self.title,
            menu_cursor="→ ",
            menu_cursor_style=("fg_cyan", "bold"),
            menu_highlight_style=("bg_cyan", "fg_black"),
            cycle_cursor=True,
            clear_screen=False
        )

        # Show menu
        selection = terminal_menu.show()

        # Handle back option
        if self.show_back and selection == len(self.options):
            return None

        return selection

    def run(self) -> None:
        """Run menu loop"""
        while True:
            selection = self.show()

            if selection is None:
                break

            option = self.options[selection]

            # Handle submenu
            if option.submenu:
                option.submenu.run()
                continue

            # Handle action
            if option.action:
                try:
                    result = option.action()
                    # If action returns False, exit menu
                    if result is False:
                        break
                except KeyboardInterrupt:
                    print_info("\nOperation cancelled")
                    continue
                except Exception as e:
                    print_error(f"Error: {e}")
                    console.input("\n[dim]Press Enter to continue...[/dim]")
            else:
                break


def show_main_menu() -> None:
    """Show main VibeWP menu"""
    from cli.utils.config import ConfigManager

    # Print banner
    print_banner()

    # Initialize config
    try:
        config_mgr = ConfigManager()
        config_mgr.init_config()
    except Exception as e:
        print_error(f"Failed to initialize config: {e}")
        return

    # Define menu options
    options = [
        MenuOption(
            label="Create New Site",
            icon="🌍",
            action=lambda: create_site_action()
        ),
        MenuOption(
            label="Delete Site",
            icon="🗑️",
            action=lambda: delete_site_action()
        ),
        MenuOption(
            label="List All Sites",
            icon="📋",
            action=lambda: list_sites_action()
        ),
        MenuOption(
            label="Manage Domains",
            icon="🌐",
            action=lambda: manage_domains_action()
        ),
        MenuOption(
            label="Firewall Control",
            icon="🔒",
            action=lambda: firewall_menu()
        ),
        MenuOption(
            label="SSH Configuration",
            icon="🔑",
            action=lambda: ssh_menu()
        ),
        MenuOption(
            label="Security Audit",
            icon="🛡️",
            action=lambda: security_menu()
        ),
        MenuOption(
            label="System Monitoring",
            icon="📊",
            action=lambda: system_menu()
        ),
        MenuOption(
            label="Backup & Restore",
            icon="💾",
            action=lambda: backup_menu()
        ),
        MenuOption(
            label="Settings",
            icon="⚙️",
            action=lambda: settings_action()
        ),
        MenuOption(
            label="Exit",
            icon="🚪",
            action=lambda: exit_action()
        )
    ]

    # Create and run menu
    menu = Menu("VPS WordPress Manager", options)
    menu.run()


def create_site_action():
    """Action for creating a new site"""
    from cli.commands.site import create_site

    try:
        create_site()
    except Exception as e:
        print_error(f"Failed to create site: {e}")


def delete_site_action():
    """Action for deleting a site"""
    from cli.commands.site import delete_site
    from cli.utils.config import ConfigManager
    from simple_term_menu import TerminalMenu

    try:
        config_mgr = ConfigManager()
        sites = config_mgr.get_sites()

        if not sites:
            print_info("No sites found")
            console.input("\n[dim]Press Enter to continue...[/dim]")
            return

        # Select site to delete
        site_names = [f"{site.name} ({site.domain})" for site in sites]
        menu = TerminalMenu(
            site_names,
            title="Select site to delete:",
            menu_cursor="→ ",
            menu_cursor_style=("fg_cyan", "bold"),
            menu_highlight_style=("bg_cyan", "fg_black")
        )
        choice = menu.show()

        if choice is None:
            return

        selected_site = sites[choice]
        delete_site(site_name=selected_site.name, force=False)

    except Exception as e:
        print_error(f"Failed to delete site: {e}")
        console.input("\n[dim]Press Enter to continue...[/dim]")


def list_sites_action():
    """Action for listing sites"""
    from cli.utils.config import ConfigManager
    from cli.ui.console import print_sites_table

    try:
        config_mgr = ConfigManager()
        sites = config_mgr.get_sites()

        # Convert to dict format for table
        sites_data = [
            {
                'name': site.name,
                'domain': site.domain,
                'type': site.type,
                'status': site.status,
                'created': site.created
            }
            for site in sites
        ]

        print_sites_table(sites_data)

    except Exception as e:
        print_error(f"Failed to list sites: {e}")

    console.input("\n[dim]Press Enter to continue...[/dim]")


def manage_domains_action():
    """Action for managing domains"""
    from cli.commands.domain import manage_domains

    try:
        manage_domains()
    except Exception as e:
        print_error(f"Failed to manage domains: {e}")


def settings_action():
    """Action for settings management"""
    from cli.commands.config import show_config

    try:
        show_config()
    except Exception as e:
        print_error(f"Failed to show settings: {e}")

    console.input("\n[dim]Press Enter to continue...[/dim]")


def exit_action():
    """Action for exiting the application"""
    if confirm("Are you sure you want to exit?", default=False):
        print_success("Goodbye!")
        return False  # Signal to exit menu
    return True  # Continue showing menu


def select_from_list(
    title: str,
    items: List[str],
    allow_cancel: bool = True
) -> Optional[int]:
    """
    Show selection menu from list of items

    Args:
        title: Menu title
        items: List of items to select from
        allow_cancel: Whether to show cancel option

    Returns:
        Index of selected item or None if cancelled
    """
    if not items:
        print_info("No items available")
        return None

    menu_items = items.copy()
    if allow_cancel:
        menu_items.append("← Cancel")

    terminal_menu = TerminalMenu(
        menu_items,
        title=title,
        menu_cursor="→ ",
        menu_cursor_style=("fg_cyan", "bold"),
        menu_highlight_style=("bg_cyan", "fg_black"),
        cycle_cursor=True
    )

    selection = terminal_menu.show()

    # Handle cancel
    if allow_cancel and selection == len(items):
        return None

    return selection


# VPS Control Submenus

def firewall_menu():
    """Firewall management submenu"""
    from cli.commands import firewall

    options = [
        MenuOption(label="List Rules", icon="📋", action=lambda: run_command(firewall.list_rules)),
        MenuOption(label="Open Port", icon="🔓", action=lambda: open_port_interactive()),
        MenuOption(label="Close Port", icon="🔒", action=lambda: close_port_interactive()),
        MenuOption(label="Status", icon="📊", action=lambda: run_command(firewall.status))
    ]

    menu = Menu("Firewall Control", options, show_back=True)
    menu.run()


def ssh_menu():
    """SSH configuration submenu"""
    from cli.commands import ssh_cmd

    options = [
        MenuOption(label="Show Config", icon="📄", action=lambda: run_command(ssh_cmd.show_config)),
        MenuOption(label="Change Port", icon="🔧", action=lambda: change_ssh_port_interactive()),
        MenuOption(label="Add Key", icon="➕", action=lambda: add_ssh_key_interactive()),
        MenuOption(label="Test Connection", icon="🔌", action=lambda: run_command(ssh_cmd.test_connection))
    ]

    menu = Menu("SSH Configuration", options, show_back=True)
    menu.run()


def security_menu():
    """Security audit submenu"""
    from cli.commands import security

    options = [
        MenuOption(label="Security Scan", icon="🔍", action=lambda: run_command(security.security_scan)),
        MenuOption(label="Fail2Ban Status", icon="🚫", action=lambda: run_command(security.fail2ban_status)),
        MenuOption(label="Unban IP", icon="✅", action=lambda: unban_ip_interactive()),
        MenuOption(label="Check Updates", icon="📦", action=lambda: run_command(security.check_updates))
    ]

    menu = Menu("Security Audit", options, show_back=True)
    menu.run()


def system_menu():
    """System monitoring submenu"""
    from cli.commands import system

    options = [
        MenuOption(label="System Status", icon="📊", action=lambda: run_command(system.system_status)),
        MenuOption(label="Docker Stats", icon="🐳", action=lambda: run_command(system.docker_stats)),
        MenuOption(label="View Logs", icon="📄", action=lambda: view_logs_interactive()),
        MenuOption(label="List Processes", icon="⚙️", action=lambda: run_command(system.list_processes)),
        MenuOption(label="Disk Usage", icon="💾", action=lambda: run_command(system.disk_usage)),
        MenuOption(label="Cleanup", icon="🧹", action=lambda: run_command(system.cleanup))
    ]

    menu = Menu("System Monitoring", options, show_back=True)
    menu.run()


def backup_menu():
    """Backup & restore submenu"""
    from cli.commands import backup

    options = [
        MenuOption(label="List Backups", icon="📋", action=lambda: run_command(backup.list_backups)),
        MenuOption(label="Create Backup", icon="➕", action=lambda: create_backup_interactive()),
        MenuOption(label="Restore Backup", icon="♻️", action=lambda: restore_backup_interactive()),
        MenuOption(label="Delete Backup", icon="🗑️", action=lambda: delete_backup_interactive())
    ]

    menu = Menu("Backup & Restore", options, show_back=True)
    menu.run()


# Interactive helper functions

def run_command(func):
    """Run command and wait for user"""
    try:
        func()
    except Exception as e:
        print_error(f"Command failed: {e}")

    console.input("\n[dim]Press Enter to continue...[/dim]")


def open_port_interactive():
    """Interactive port opening"""
    from cli.commands import firewall

    try:
        port_str = console.input("\n[cyan]Port number:[/cyan] ").strip()
        protocol = console.input("[cyan]Protocol (tcp/udp) [tcp]:[/cyan] ").strip() or "tcp"

        port = int(port_str)
        firewall.open_port(port, protocol)

    except ValueError:
        print_error("Invalid port number")
    except Exception as e:
        print_error(f"Failed to open port: {e}")

    console.input("\n[dim]Press Enter to continue...[/dim]")


def close_port_interactive():
    """Interactive port closing"""
    from cli.commands import firewall

    try:
        port_str = console.input("\n[cyan]Port number:[/cyan] ").strip()
        protocol = console.input("[cyan]Protocol (tcp/udp) [tcp]:[/cyan] ").strip() or "tcp"

        port = int(port_str)
        firewall.close_port(port, protocol)

    except ValueError:
        print_error("Invalid port number")
    except Exception as e:
        print_error(f"Failed to close port: {e}")

    console.input("\n[dim]Press Enter to continue...[/dim]")


def change_ssh_port_interactive():
    """Interactive SSH port change"""
    from cli.commands import ssh_cmd

    try:
        port_str = console.input("\n[cyan]New SSH port (1024-65535):[/cyan] ").strip()
        port = int(port_str)
        ssh_cmd.change_port(port)

    except ValueError:
        print_error("Invalid port number")
    except Exception as e:
        print_error(f"Failed to change port: {e}")

    console.input("\n[dim]Press Enter to continue...[/dim]")


def add_ssh_key_interactive():
    """Interactive SSH key addition"""
    from cli.commands import ssh_cmd

    try:
        key_path = console.input("\n[cyan]Path to public key file:[/cyan] ").strip()
        ssh_cmd.add_key(key_path)

    except Exception as e:
        print_error(f"Failed to add key: {e}")

    console.input("\n[dim]Press Enter to continue...[/dim]")


def unban_ip_interactive():
    """Interactive IP unbanning"""
    from cli.commands import security

    try:
        ip = console.input("\n[cyan]IP address to unban:[/cyan] ").strip()
        security.unban_ip(ip)

    except Exception as e:
        print_error(f"Failed to unban IP: {e}")

    console.input("\n[dim]Press Enter to continue...[/dim]")


def view_logs_interactive():
    """Interactive log viewing"""
    from cli.commands import system

    try:
        services = ["syslog", "docker", "fail2ban", "auth"]
        service_menu = TerminalMenu(
            services,
            title="Select log to view:",
            menu_cursor="→ "
        )
        choice = service_menu.show()

        if choice is not None:
            system.view_logs(service=services[choice])

    except Exception as e:
        print_error(f"Failed to view logs: {e}")

    console.input("\n[dim]Press Enter to continue...[/dim]")


def create_backup_interactive():
    """Interactive backup creation"""
    from cli.commands import backup
    from cli.utils.config import ConfigManager

    try:
        config_mgr = ConfigManager()
        sites = config_mgr.get_sites()

        if not sites:
            print_info("No sites found")
            console.input("\n[dim]Press Enter to continue...[/dim]")
            return

        site_names = [site.name for site in sites]
        site_menu = TerminalMenu(
            site_names,
            title="Select site to backup:",
            menu_cursor="→ "
        )
        choice = site_menu.show()

        if choice is not None:
            backup.create_backup(site_names[choice])

    except Exception as e:
        print_error(f"Failed to create backup: {e}")

    console.input("\n[dim]Press Enter to continue...[/dim]")


def restore_backup_interactive():
    """Interactive backup restoration"""
    from cli.commands import backup
    from cli.utils.ssh import SSHManager
    from cli.utils.backup import BackupManager

    try:
        ssh = SSHManager.from_config()
        ssh.connect()

        backup_mgr = BackupManager(ssh)
        backups = backup_mgr.list_backups()

        ssh.disconnect()

        if not backups:
            print_info("No backups found")
            console.input("\n[dim]Press Enter to continue...[/dim]")
            return

        backup_labels = [f"{b['site']} - {b['id']} ({b['date']})" for b in backups]
        backup_menu = TerminalMenu(
            backup_labels,
            title="Select backup to restore:",
            menu_cursor="→ "
        )
        choice = backup_menu.show()

        if choice is not None:
            selected = backups[choice]
            backup.restore_backup(selected['site'], selected['id'])

    except Exception as e:
        print_error(f"Failed to restore backup: {e}")

    console.input("\n[dim]Press Enter to continue...[/dim]")


def delete_backup_interactive():
    """Interactive backup deletion"""
    from cli.commands import backup
    from cli.utils.ssh import SSHManager
    from cli.utils.backup import BackupManager

    try:
        ssh = SSHManager.from_config()
        ssh.connect()

        backup_mgr = BackupManager(ssh)
        backups = backup_mgr.list_backups()

        ssh.disconnect()

        if not backups:
            print_info("No backups found")
            console.input("\n[dim]Press Enter to continue...[/dim]")
            return

        backup_labels = [f"{b['site']} - {b['id']} ({b['date']}) - {b['size']}" for b in backups]
        backup_menu = TerminalMenu(
            backup_labels,
            title="Select backup to delete:",
            menu_cursor="→ "
        )
        choice = backup_menu.show()

        if choice is not None:
            selected = backups[choice]
            backup.delete_backup(selected['site'], selected['id'])

    except Exception as e:
        print_error(f"Failed to delete backup: {e}")

    console.input("\n[dim]Press Enter to continue...[/dim]")
