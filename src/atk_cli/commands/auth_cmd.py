"""atk auth status command."""

import time
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from .. import auth as auth_mod
from .. import config as cfg_mod
from ..auth import _decode_jwt_exp, is_token_expired
from ..exceptions import ATKError

console = Console()
app = typer.Typer(help="Auth management.")


@app.command("status")
def status(ctx: typer.Context) -> None:
    """Show current authentication status and token info."""
    state = ctx.obj
    profile_name = (state.profile if state else None) or cfg_mod.get_active_profile_name()
    cfg = cfg_mod.load()

    console.print(f"[bold]Active profile:[/bold] {profile_name}")

    try:
        profile = cfg_mod.get_profile(profile_name, cfg)
        console.print(f"[bold]Email:[/bold]          {profile.get('email', '(not set)')}")
        console.print(f"[bold]Site key:[/bold]       {profile.get('site_key', 'atk')}")
    except ATKError:
        console.print(f"[yellow]Profile '{profile_name}' not found in config.[/yellow]")

    console.print()

    try:
        tokens = auth_mod.get_tokens(profile_name)
        access = tokens.get("access_token", "")
        exp = _decode_jwt_exp(access)
        expired = is_token_expired(access)

        status_str = "[red]EXPIRED[/red]" if expired else "[green]VALID[/green]"
        exp_str = (
            time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(exp)) if exp else "unknown"
        )

        console.print(f"[bold]Token status:[/bold]   {status_str}")
        console.print(f"[bold]Expires:[/bold]        {exp_str}")
        console.print(f"[bold]Token (preview):[/bold] {access[:20]}...")
    except ATKError:
        console.print("[yellow]No tokens found. Run 'atk login' to authenticate.[/yellow]")
