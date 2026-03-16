"""atk create favorite command."""

from typing import Annotated

import typer
from rich.console import Console

from ..client import ATKClient
from ..exceptions import ATKError

console = Console()
app = typer.Typer(help="Create ATK resources.")


@app.command()
def favorite(
    ctx: typer.Context,
    recipe_id: Annotated[str, typer.Argument(help="Recipe ID (numeric or recipe_NNNNN)")],
) -> None:
    """Add a recipe to your favorites."""
    numeric_id = recipe_id.replace("recipe_", "")
    object_id = f"recipe_{numeric_id}"
    state = ctx.obj
    site = state.site if state else "atk"

    try:
        with ATKClient(
            profile=state.profile if state else None,
            verbose=state.verbose if state else False,
        ) as client:
            client.create_favorite(object_id, site_key=site)
        console.print(f"[green]Favorited recipe {numeric_id}.[/green]")
    except ATKError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)
