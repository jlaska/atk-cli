"""atk-cli: kubectl-inspired CLI for America's Test Kitchen API."""

from dataclasses import dataclass
from typing import Annotated, Optional

import typer
from rich.console import Console

from .commands import auth_cmd, config_cmd, create, delete, describe, get, version
from .commands.search import search_command
from .auth import clear_tokens, resolve_credentials, save_tokens
from .client import ATKClient
from .exceptions import ATKError

console = Console()


@dataclass
class State:
    profile: str | None = None
    verbose: bool = False
    site: str = "atk"
    output: str = "table"
    no_headers: bool = False


app = typer.Typer(
    name="atk",
    help="America's Test Kitchen CLI — kubectl-style access to ATK APIs.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)


@app.callback()
def global_callback(
    ctx: typer.Context,
    profile: Annotated[
        Optional[str],
        typer.Option("--profile", "-p", help="Override active profile", envvar="ATK_PROFILE"),
    ] = None,
    site: Annotated[
        str,
        typer.Option("--site", "-s", help="Site key: atk|cio|cco", envvar="ATK_SITE"),
    ] = "atk",
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show HTTP details")] = False,
    output: Annotated[
        str,
        typer.Option("--output", "-o", help="Output format: table|json|yaml|wide|jsonpath=..."),
    ] = "table",
    no_headers: Annotated[bool, typer.Option("--no-headers", help="Omit table headers")] = False,
) -> None:
    ctx.ensure_object(State)
    ctx.obj = State(profile=profile, verbose=verbose, site=site, output=output, no_headers=no_headers)


# ── Top-level commands ─────────────────────────────────────────────────────────

@app.command("login")
def login(
    ctx: typer.Context,
    email: Annotated[Optional[str], typer.Option("--email", "-e", help="ATK account email")] = None,
    password: Annotated[
        Optional[str], typer.Option("--password", hide_input=True, help="ATK password")
    ] = None,
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
        # Persist email into the profile so 'auth status' can display it
        from . import config as cfg_mod
        profile_name = profile or cfg_mod.get_active_profile_name()
        cfg_mod.create_or_update_profile(profile_name, email=email)
        console.print("[green]Logged in successfully.[/green]")
    except ATKError as exc:
        console.print(f"[red]Login failed:[/red] {exc}")
        raise typer.Exit(1)


@app.command("logout")
def logout(ctx: typer.Context) -> None:
    """Clear stored authentication tokens for the active profile."""
    state = ctx.obj
    clear_tokens(state.profile if state else None)
    console.print("[green]Logged out.[/green]")


# ── Sub-app wiring ─────────────────────────────────────────────────────────────

app.command("search")(search_command)

app.add_typer(get.app, name="get")
app.add_typer(describe.app, name="describe")
app.add_typer(create.app, name="create")
app.add_typer(delete.app, name="delete")
app.add_typer(auth_cmd.app, name="auth")
app.add_typer(config_cmd.app, name="config")
app.add_typer(version.app, name="version")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
