"""atk describe recipe/collection commands."""

from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..client import ATKClient
from ..exceptions import ATKError
from ..output import render

console = Console()
app = typer.Typer(help="Show detailed information about a resource.")


def _client(ctx: typer.Context) -> ATKClient:
    state = ctx.obj
    return ATKClient(
        profile=state.profile if state else None,
        verbose=state.verbose if state else False,
    )


@app.command()
def recipe(
    ctx: typer.Context,
    recipe_id: Annotated[str, typer.Argument(help="Recipe ID (numeric or recipe_NNNNN)")],
    output: Annotated[str, typer.Option("--output", "-o")] = "table",
) -> None:
    """Show rating, collections, and favorite status for a recipe."""
    # Normalise — strip leading 'recipe_' if provided
    numeric_id = recipe_id.replace("recipe_", "")
    object_id = f"recipe_{numeric_id}"

    try:
        with _client(ctx) as client:
            # Rating
            rating_resp = client.get_recipe_rating(numeric_id)
            rating_data = (
                rating_resp.get("data", {}).get("rating", {}).get("attributes", {})
            )

            # Collections containing this recipe
            try:
                coll_resp = client.get_recipe_collections(object_id)
                collections = coll_resp.get("data", [])
            except ATKError:
                collections = []

            # Favorite status
            try:
                inter = client.check_favorites_intersection([object_id])
                is_fav = bool(inter.get("data", {}).get(object_id, False))
            except ATKError:
                is_fav = None

        if output == "json":
            import json
            render(
                {"id": numeric_id, "rating": rating_data, "collections": collections, "favorited": is_fav},
                fmt="json",
            )
            return

        # Rich panel display
        avg = rating_data.get("avgScore")
        count = rating_data.get("userRatingsCount")
        user_r = rating_data.get("userRating")
        fav_str = "Yes" if is_fav else ("No" if is_fav is False else "Unknown")

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Field", style="bold cyan")
        table.add_column("Value")
        table.add_row("Recipe ID", numeric_id)
        table.add_row("Avg Rating", f"{avg:.2f}" if avg else "N/A")
        table.add_row("# Ratings", str(count) if count is not None else "N/A")
        table.add_row("Your Rating", str(user_r) if user_r is not None else "N/A")
        table.add_row("Favorited", fav_str)
        table.add_row(
            "URL", f"https://www.americastestkitchen.com/recipes/{numeric_id}"
        )

        console.print(Panel(table, title=f"Recipe {numeric_id}", border_style="cyan"))

        if collections:
            console.print("\n[bold]Collections containing this recipe:[/bold]")
            render(collections, fmt="table", resource_type="collections")

    except ATKError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)


@app.command()
def collection(
    ctx: typer.Context,
    slug: Annotated[str, typer.Argument(help="Collection slug or ID")],
    output: Annotated[str, typer.Option("--output", "-o")] = "table",
) -> None:
    """Show details for a collection."""
    state = ctx.obj
    site = state.site if state else "atk"

    try:
        with _client(ctx) as client:
            data = client.get_favorites_metadata(site_key=site)
            # Find the matching collection
            all_colls = data.get("data", {})
            if isinstance(all_colls, dict):
                all_colls = all_colls.get(
                    "collections", all_colls.get("userFavoritesCollections", [])
                )
            match = next(
                (c for c in all_colls if str(c.get("id")) == slug or c.get("slug") == slug),
                None,
            )
            if match is None:
                console.print(f"[yellow]Collection '{slug}' not found.[/yellow]")
                raise typer.Exit(1)
            render(match, fmt=output, resource_type="collections")
    except ATKError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)
