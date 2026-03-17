"""atk-cli: kubectl-inspired CLI for America's Test Kitchen API."""

from dataclasses import dataclass
from typing import Annotated, Optional

import typer

from .commands import auth_cmd, config_cmd, create, delete, describe, get, version
from .commands.login import login_command, logout_command
from .commands.search import search_command

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

app.command("login")(login_command)
app.command("logout")(logout_command)

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
