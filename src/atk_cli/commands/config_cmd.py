"""atk config commands."""

from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from .. import config as cfg_mod
from ..constants import DEFAULT_SITE_KEY, SITE_KEYS
from ..exceptions import ConfigError

console = Console()
app = typer.Typer(help="Manage atk-cli configuration and profiles.")


@app.command("view")
def view() -> None:
    """Show current configuration (tokens redacted)."""
    cfg = cfg_mod.load()
    active = cfg.get("active_profile", "default")

    console.print(f"[bold]Config file:[/bold] {cfg_mod.CONFIG_FILE}")
    console.print(f"[bold]Active profile:[/bold] {active}\n")

    profiles = cfg.get("profiles", {})
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Profile")
    table.add_column("Email")
    table.add_column("Site Key")
    table.add_column("Active")

    for name, profile in profiles.items():
        is_active = "✓" if name == active else ""
        table.add_row(
            name,
            profile.get("email", ""),
            profile.get("site_key", DEFAULT_SITE_KEY),
            is_active,
        )
    console.print(table)


@app.command("get-profiles")
def get_profiles() -> None:
    """List all configured profiles."""
    cfg = cfg_mod.load()
    active = cfg.get("active_profile", "default")
    for name in cfg_mod.list_profiles(cfg):
        marker = " (active)" if name == active else ""
        console.print(f"  {name}{marker}")


@app.command("use-profile")
def use_profile(
    name: Annotated[str, typer.Argument(help="Profile name to activate")],
) -> None:
    """Switch the active profile."""
    try:
        cfg_mod.set_active_profile(name)
        console.print(f"[green]Switched to profile '{name}'.[/green]")
    except ConfigError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)


@app.command("set-profile")
def set_profile(
    name: Annotated[str, typer.Argument(help="Profile name to create or update")],
    email: Annotated[Optional[str], typer.Option("--email", "-e")] = None,
    site_key: Annotated[str, typer.Option("--site", "-s", help=f"Site key: {', '.join(SITE_KEYS)}")] = DEFAULT_SITE_KEY,
) -> None:
    """Create or update a profile."""
    if not email:
        email = typer.prompt(f"Email for profile '{name}'", default="")
    try:
        cfg_mod.create_or_update_profile(name, email=email or "", site_key=site_key)
        console.print(f"[green]Profile '{name}' saved.[/green]")
    except ConfigError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)
