"""atk delete favorite command."""

from typing import Annotated

import typer
from rich.console import Console

from ..client import ATKClient
from ..exceptions import ATKError

console = Console()
app = typer.Typer(help="Delete ATK resources.", context_settings={"help_option_names": ["-h", "--help"]})


@app.command()
def favorite(
    ctx: typer.Context,
    recipe_id: Annotated[str, typer.Argument(help="Recipe ID (numeric or recipe_NNNNN)")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Remove a recipe from your favorites."""
    numeric_id = recipe_id.replace("recipe_", "")
    object_id = f"recipe_{numeric_id}"

    if not yes:
        confirmed = typer.confirm(f"Remove recipe {numeric_id} from favorites?")
        if not confirmed:
            raise typer.Abort()

    state = ctx.obj
    try:
        with ATKClient(
            profile=state.profile if state else None,
            verbose=state.verbose if state else False,
        ) as client:
            client.delete_favorite(object_id)
        console.print(f"[green]Removed recipe {numeric_id} from favorites.[/green]")
    except ATKError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)
