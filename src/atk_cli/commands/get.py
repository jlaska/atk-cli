"""atk get favorites/collections/trending/subscription commands."""

from typing import Annotated, Optional

import typer
from rich.console import Console

from ..client import ATKClient
from ..exceptions import ATKError
from ..output import render

console = Console()
app = typer.Typer(help="Fetch ATK resources.", context_settings={"help_option_names": ["-h", "--help"]})


def _client(ctx: typer.Context) -> ATKClient:
    state = ctx.obj
    return ATKClient(
        profile=state.profile if state else None,
        verbose=state.verbose if state else False,
        site_key=state.site if state else "atk",
    )


@app.command()
def favorites(
    ctx: typer.Context,
    recent: Annotated[bool, typer.Option("--recent", help="Most recently favorited")] = False,
    top_rated: Annotated[bool, typer.Option("--top-rated", help="Top-rated favorites")] = False,
    all_pages: Annotated[bool, typer.Option("--all", help="Fetch all pages")] = False,
    page: Annotated[int, typer.Option("--page", "-p", help="Page number")] = 1,
    limit: Annotated[int, typer.Option("--limit", "-l", help="Limit (for --recent)")] = 16,
    output: Annotated[str, typer.Option("--output", "-o", help="Output format: table|json|yaml|wide|jsonpath=...")] = "table",
    no_headers: Annotated[bool, typer.Option("--no-headers", help="Omit table headers")] = False,
) -> None:
    """Fetch user favorites."""
    state = ctx.obj
    site = state.site if state else "atk"

    try:
        with _client(ctx) as client:
            if recent:
                data = client.get_recent_favorites(limit=limit)
                rows = data.get("data", {}).get("results", [])
                render(rows, fmt=output, resource_type="recent", no_headers=no_headers)
            elif top_rated:
                data = client.get_top_rated_favorites()
                rows = data.get("data", {}).get("results", [])
                render(rows, fmt=output, resource_type="top_rated", no_headers=no_headers)
            elif all_pages:
                rows = client.get_all_favorites(site_key=site)
                render(rows, fmt=output, resource_type="favorites", no_headers=no_headers)
            else:
                data = client.get_favorites_page(page=page, site_key=site)
                rows = data.get("results", [])
                pagination = data.get("pagination", {})
                render(rows, fmt=output, resource_type="favorites", no_headers=no_headers)
                if output in ("table", "wide"):
                    total = pagination.get("total_count", 0)
                    current_page = pagination.get("page", page)
                    console.print(
                        f"\n[dim]Page {current_page} · {len(rows)} shown · {total} total[/dim]"
                    )
    except ATKError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)


@app.command()
def collections(
    ctx: typer.Context,
    output: Annotated[str, typer.Option("--output", "-o")] = "table",
    no_headers: Annotated[bool, typer.Option("--no-headers")] = False,
) -> None:
    """Fetch user collections (favorites folders)."""
    state = ctx.obj
    site = state.site if state else "atk"

    try:
        with _client(ctx) as client:
            data = client.get_favorites_metadata(site_key=site)
            # Metadata contains collections list
            rows = data.get("data", data) if isinstance(data, dict) else data
            if isinstance(rows, dict):
                # Try common keys
                rows = rows.get("collections", rows.get("userFavoritesCollections", [rows]))
            if not isinstance(rows, list):
                rows = [rows]
            render(rows, fmt=output, resource_type="collections", no_headers=no_headers)
    except ATKError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)


@app.command()
def trending(
    ctx: typer.Context,
    output: Annotated[str, typer.Option("--output", "-o")] = "table",
    no_headers: Annotated[bool, typer.Option("--no-headers")] = False,
) -> None:
    """Fetch trending recipes (no auth required)."""
    try:
        with _client(ctx) as client:
            data = client.get_trending_recipes()
            # Response: {"hits": [...]}
            if isinstance(data, dict):
                rows = data.get("hits", data.get("results", [data]))
            elif isinstance(data, list):
                rows = data
            else:
                rows = [data]
            render(rows, fmt=output, resource_type="trending", no_headers=no_headers)
    except ATKError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)


@app.command()
def subscription(
    ctx: typer.Context,
    output: Annotated[str, typer.Option("--output", "-o")] = "table",
) -> None:
    """Fetch subscription/account summary."""
    try:
        with _client(ctx) as client:
            data = client.get_customer_summary()
            render(data, fmt=output, resource_type="subscription")
    except ATKError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)
