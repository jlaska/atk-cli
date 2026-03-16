"""atk search command (Algolia) — imported by main.py as a top-level command."""

from typing import Annotated, Optional

import typer
from rich.console import Console

from ..client import ATKClient
from ..exceptions import ATKError
from ..output import render

console = Console()


def search_command(
    ctx: typer.Context,
    query: Annotated[str, typer.Argument(help="Search query")],
    search_type: Annotated[
        Optional[str],
        typer.Option("--type", "-t", help="Content type: recipe|article|equipment|taste_test"),
    ] = "recipe",
    page: Annotated[int, typer.Option("--page", "-p", help="Page number (0-indexed)")] = 0,
    limit: Annotated[int, typer.Option("--limit", "-l", help="Results per page")] = 20,
    output: Annotated[str, typer.Option("--output", "-o")] = "table",
    no_headers: Annotated[bool, typer.Option("--no-headers")] = False,
) -> None:
    """Search America's Test Kitchen content via Algolia."""
    state = ctx.obj
    try:
        with ATKClient(
            profile=state.profile if state else None,
            verbose=state.verbose if state else False,
        ) as client:
            data = client.search(
                query=query,
                search_type=search_type or "",
                page=page,
                hits_per_page=limit,
            )
        results = data.get("results", [{}])
        hits = results[0].get("hits", []) if results else []
        nb_hits = results[0].get("nbHits", 0) if results else 0

        render(hits, fmt=output, resource_type="search", no_headers=no_headers)

        if output in ("table", "wide"):
            console.print(f"\n[dim]{len(hits)} results shown · {nb_hits} total[/dim]")
    except ATKError as exc:
        msg = str(exc)
        console.print(f"[red]Error:[/red] {msg}")
        if "does not exist" in msg:
            console.print(
                "[yellow]Hint:[/yellow] The Algolia index name may have changed. "
                "Run [bold]atk config refresh-index[/bold] to auto-discover the new index."
            )
        raise typer.Exit(1)
