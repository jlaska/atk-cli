"""atk login / atk logout commands."""

from typing import Annotated, Optional

import typer
from rich.console import Console

from ..auth import clear_tokens, resolve_credentials, save_tokens
from ..client import ATKClient
from ..exceptions import ATKError

console = Console()
app = typer.Typer(help="Authentication commands.")


@app.command()
def login(
    ctx: typer.Context,
    email: Annotated[Optional[str], typer.Option("--email", "-e", help="ATK account email")] = None,
    password: Annotated[Optional[str], typer.Option("--password", "-p", help="ATK password", hide_input=True)] = None,
) -> None:
    """Authenticate with America's Test Kitchen and save tokens."""
    state = ctx.obj

    resolved_email, resolved_password = resolve_credentials(state.profile if state else None)
    email = email or resolved_email
    password = password or resolved_password

    if not email:
        email = typer.prompt("Email")
    if not password:
        password = typer.prompt("Password", hide_input=True)

    profile = state.profile if state else None

    console.print(f"[dim]Logging in as {email}...[/dim]")
    try:
        with ATKClient(profile=profile, verbose=state.verbose if state else False) as client:
            data = client.login(email, password)

        access_token = data.get("accessToken", "")
        refresh_token = data.get("refreshToken", "")
        if not access_token:
            console.print("[red]Login failed: no access token in response.[/red]")
            raise typer.Exit(1)

        save_tokens(access_token, refresh_token, profile)
        console.print("[green]Logged in successfully.[/green]")
    except ATKError as exc:
        console.print(f"[red]Login failed:[/red] {exc}")
        raise typer.Exit(1)


@app.command()
def logout(ctx: typer.Context) -> None:
    """Clear stored tokens for the active profile."""
    state = ctx.obj
    profile = state.profile if state else None
    clear_tokens(profile)
    console.print("[green]Logged out.[/green]")
