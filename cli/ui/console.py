"""Rich console configuration for VibeWP CLI"""

from rich.console import Console
from rich.theme import Theme
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from typing import Optional


# Define custom theme
vibewp_theme = Theme({
    "info": "cyan",
    "success": "bold green",
    "warning": "bold yellow",
    "error": "bold red",
    "header": "bold magenta",
    "highlight": "bold blue",
    "muted": "dim",
})

# Create global console instance
console = Console(theme=vibewp_theme)


def print_success(message: str) -> None:
    """Print success message"""
    console.print(f"[success]✓[/success] {message}")


def print_error(message: str) -> None:
    """Print error message"""
    console.print(f"[error]✗[/error] {message}")


def print_warning(message: str) -> None:
    """Print warning message"""
    console.print(f"[warning]⚠[/warning] {message}")


def print_info(message: str) -> None:
    """Print info message"""
    console.print(f"[info]ℹ[/info] {message}")


def print_header(title: str, subtitle: Optional[str] = None) -> None:
    """Print styled header"""
    if subtitle:
        text = f"[header]{title}[/header]\n[muted]{subtitle}[/muted]"
    else:
        text = f"[header]{title}[/header]"

    panel = Panel(text, border_style="header", padding=(1, 2))
    console.print(panel)


def create_table(
    title: str,
    columns: list[tuple[str, str]],
    rows: list[list[str]],
    show_header: bool = True
) -> Table:
    """
    Create styled table

    Args:
        title: Table title
        columns: List of (column_name, style) tuples
        rows: List of row data
        show_header: Whether to show header row

    Returns:
        Rich Table object
    """
    table = Table(title=title, show_header=show_header, header_style="header")

    # Add columns
    for col_name, col_style in columns:
        table.add_column(col_name, style=col_style)

    # Add rows
    for row in rows:
        table.add_row(*row)

    return table


def create_progress() -> Progress:
    """
    Create styled progress bar

    Returns:
        Rich Progress object
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    )


def confirm(message: str, default: bool = False) -> bool:
    """
    Prompt user for confirmation

    Args:
        message: Confirmation message
        default: Default value if user just presses Enter

    Returns:
        True if confirmed, False otherwise
    """
    default_str = "Y/n" if default else "y/N"
    hint = "[dim](Type Y or N)[/dim] "
    response = console.input(f"[warning]{message}[/warning] {hint}[{default_str}]: ").strip().lower()

    if not response:
        return default

    return response in ('y', 'yes')


def prompt(message: str, default: Optional[str] = None) -> str:
    """
    Prompt user for input

    Args:
        message: Prompt message
        default: Default value if user just presses Enter

    Returns:
        User input
    """
    if default:
        message = f"{message} [dim](default: {default})[/dim]"

    response = console.input(f"[info]{message}:[/info] ").strip()

    return response if response else (default or "")


def print_sites_table(sites: list[dict]) -> None:
    """
    Print formatted sites table

    Args:
        sites: List of site dictionaries
    """
    if not sites:
        print_info("No sites found")
        return

    columns = [
        ("Name", "highlight"),
        ("Domain", "info"),
        ("Type", ""),
        ("Status", "success"),
        ("Created", "muted")
    ]

    rows = []
    for site in sites:
        status_style = "success" if site.get('status') == 'running' else "error"
        rows.append([
            site.get('name', 'N/A'),
            site.get('domain', 'N/A'),
            site.get('type', 'N/A'),
            f"[{status_style}]{site.get('status', 'unknown')}[/{status_style}]",
            site.get('created', 'N/A')[:10]  # Show date only
        ])

    table = create_table("Deployed Sites", columns, rows)
    console.print(table)


def print_banner() -> None:
    """Print VibeWP CLI banner"""
    banner = """
    ╦  ╦╦╔╗ ╔═╗╦ ╦╔═╗
    ╚╗╔╝║╠╩╗║╣ ║║║╠═╝
     ╚╝ ╩╚═╝╚═╝╚╩╝╩
    WordPress Manager
    """
    panel = Panel(
        banner,
        border_style="header",
        padding=(1, 2),
        subtitle="[muted]VPS WordPress Management Tool[/muted]"
    )
    console.print(panel)
