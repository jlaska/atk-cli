"""atk describe recipe/collection commands."""

import re
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from ..client import ATKClient
from ..constants import build_atk_url
from ..exceptions import ATKError
from ..output import render

console = Console()
app = typer.Typer(help="Show detailed information about a resource.", context_settings={"help_option_names": ["-h", "--help"]})


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _parse_iso_duration(iso: str) -> str:
    """Convert ISO 8601 duration like 'PT1H30M' to '1 hr 30 mins'."""
    if not iso:
        return ""
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not m:
        return ""
    parts = []
    if m.group(1):
        parts.append(f"{m.group(1)} hr" + ("s" if int(m.group(1)) > 1 else ""))
    if m.group(2):
        parts.append(f"{m.group(2)} mins")
    if m.group(3):
        parts.append(f"{m.group(3)} secs")
    return " ".join(parts)


def _format_ingredient(item: dict) -> str:
    f = item.get("fields", {})
    qty = f.get("qty", "")
    pre = f.get("preText", "")
    post = f.get("postText", "")
    ing = f.get("ingredient") or {}
    if isinstance(ing, dict):
        ing_name = ing.get("fields", {}).get("title", "")
    else:
        ing_name = str(ing)
    parts = [qty, pre, ing_name, post]
    return " ".join(p for p in parts if p).strip()


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
    """Show full details for a recipe: title, description, rating, ingredients, and steps."""
    numeric_id = recipe_id.replace("recipe_", "")
    object_id = f"recipe_{numeric_id}"

    try:
        with _client(ctx) as client:
            try:
                detail = client.get_recipe_detail(numeric_id)
            except ATKError as exc:
                if getattr(exc, "status_code", None) == 404:
                    _describe_recipe_fallback(ctx, object_id, output)
                    return
                raise

            try:
                rating_resp = client.get_recipe_rating(numeric_id)
                rating_attrs = rating_resp.get("data", {}).get("rating", {}).get("attributes", {})
                user_rating_score = (
                    rating_resp.get("data", {}).get("userRating", {}).get("attributes", {}).get("score", 0)
                )
            except ATKError:
                rating_attrs = {}
                user_rating_score = 0

            try:
                coll_resp = client.get_recipe_collections(object_id)
                collections = coll_resp if isinstance(coll_resp, list) else coll_resp.get("data", [])
            except ATKError:
                collections = []

        # ── Build structured data ─────────────────────────────────────────────
        title = detail.get("title", "")
        slug = detail.get("slug", "")
        description = _strip_html(detail.get("description", ""))
        headnote = _strip_html(detail.get("headnote", ""))
        yields = detail.get("yields", "")
        time_note = detail.get("recipeTimeNote", "")
        publish_date = (detail.get("publishDate") or "")[:10]
        content_access = detail.get("contentAccess", "")

        avg_score = rating_attrs.get("avgScore")
        ratings_count = rating_attrs.get("userRatingsCount")
        your_rating = user_rating_score if user_rating_score else None

        # Ingredients
        ingredients: list[str] = []
        for group in detail.get("ingredientGroups", []):
            group_title = group.get("fields", {}).get("title", "")
            items = group.get("fields", {}).get("recipeIngredientItems", [])
            if group_title:
                ingredients.append(f"[{group_title}]")
            for item in items:
                line = _format_ingredient(item)
                if line:
                    ingredients.append(line)

        # Instructions
        steps: list[str] = []
        for step in detail.get("instructions", []):
            fields = step.get("fields", {})
            text = _strip_html(fields.get("content") or fields.get("text") or "")
            if text:
                steps.append(text)

        # Nutrition
        nutrition = detail.get("nutritionSummary", {})
        calories = nutrition.get("calories") if isinstance(nutrition, dict) else None

        # Tags
        tags = [
            t.get("fields", {}).get("tagTitle", "")
            for t in detail.get("tags", [])
            if t.get("fields", {}).get("tagTitle")
        ]

        url = build_atk_url(slug, "recipe") if slug else f"https://www.americastestkitchen.com/recipes/{numeric_id}"

        if output == "pdf":
            if not slug:
                console.print("[red]Error:[/red] Recipe slug not available; cannot build print URL.")
                raise typer.Exit(1)
            output_path = Path(f"{slug}.pdf").resolve()
            console.print(f"Exporting recipe to [cyan]{output_path}[/cyan] ...")
            try:
                with _client(ctx) as pdf_client:
                    pdf_client.export_recipe_pdf(slug, output_path)
            except ATKError as exc:
                console.print(f"[red]Error:[/red] {exc}")
                raise typer.Exit(1)
            console.print(f"[green]Saved:[/green] {output_path}")
            return

        if output == "json":
            render(
                {
                    "id": numeric_id,
                    "title": title,
                    "description": description,
                    "url": url,
                    "yields": yields,
                    "time": time_note,
                    "publish_date": publish_date,
                    "content_access": content_access,
                    "avg_score": avg_score,
                    "ratings_count": ratings_count,
                    "your_rating": your_rating,
                    "tags": tags,
                    "ingredients": ingredients,
                    "steps": steps,
                    "calories": calories,
                    "collections": collections,
                },
                fmt="json",
            )
            return

        # ── Rich display ──────────────────────────────────────────────────────
        meta = Table(show_header=False, box=None, padding=(0, 1))
        meta.add_column("Field", style="bold cyan", no_wrap=True)
        meta.add_column("Value")
        meta.add_row("ID", numeric_id)
        meta.add_row("URL", url)
        if yields:
            meta.add_row("Yields", yields)
        if time_note:
            meta.add_row("Time", time_note)
        if publish_date:
            meta.add_row("Published", publish_date)
        if content_access:
            meta.add_row("Access", content_access)
        meta.add_row("Avg Rating", f"{avg_score:.2f} ({ratings_count} ratings)" if avg_score else "N/A")
        meta.add_row("Your Rating", f"{your_rating}/5" if your_rating else "Not rated")
        if tags:
            meta.add_row("Tags", ", ".join(tags))
        if calories:
            meta.add_row("Calories", f"{int(calories)} per serving")

        title_text = Text(title, style="bold")
        console.print(Panel(title_text, border_style="cyan"))
        console.print(meta)

        if description:
            console.print(f"\n[italic]{description}[/italic]")

        if headnote:
            console.print(f"\n[dim]{headnote}[/dim]")

        if ingredients:
            console.print()
            console.print(Rule("[bold]Ingredients[/bold]", style="cyan"))
            for line in ingredients:
                prefix = "  " if not line.startswith("[") else ""
                console.print(f"{prefix}{line}")

        if steps:
            console.print()
            console.print(Rule("[bold]Instructions[/bold]", style="cyan"))
            for i, step in enumerate(steps, 1):
                console.print(f"  [bold cyan]{i}.[/bold cyan] {step}")
                console.print()

        if collections:
            console.print(Rule("[bold]Collections[/bold]", style="cyan"))
            render(collections, fmt="table", resource_type="collections")

    except ATKError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)


def _describe_recipe_fallback(
    ctx: typer.Context,
    object_id: str,
    output: str,
) -> None:
    """404 fallback: fetch Algolia metadata + JSON-LD from the recipe page."""
    try:
        with _client(ctx) as client:
            algolia_data = client.get_document_by_object_id(object_id)
            search_url = algolia_data.get("search_url", "")
            jsonld: dict = {}
            if search_url:
                try:
                    jsonld = client.get_recipe_jsonld(search_url)
                except Exception:
                    pass

        if jsonld:
            _describe_recipe_from_jsonld(object_id, search_url, jsonld, algolia_data, output)
        else:
            # Fall back to basic Algolia display
            _describe_document(ctx, "recipe", object_id, output)
    except ATKError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)


def _describe_recipe_from_jsonld(
    object_id: str,
    search_url: str,
    jsonld: dict,
    algolia_data: dict,
    output: str,
) -> None:
    """Render a recipe sourced from JSON-LD structured data."""
    from ..constants import BASE_URL

    numeric_id = object_id.replace("recipe_", "")
    title = jsonld.get("name", algolia_data.get("title", ""))
    description = _strip_html(jsonld.get("description", algolia_data.get("description", "") or ""))
    url = f"{BASE_URL}{search_url}" if search_url else f"{BASE_URL}/recipes/{numeric_id}"

    # Yields
    recipe_yield = jsonld.get("recipeYield", "")
    if isinstance(recipe_yield, list):
        yields = next((s for s in recipe_yield if isinstance(s, str) and not s.isdigit()), str(recipe_yield[0]))
    else:
        yields = str(recipe_yield) if recipe_yield else ""

    # Published date — prefer JSON-LD, fall back to Algolia
    publish_date = (jsonld.get("datePublished") or "")[:10]
    if not publish_date:
        raw_date = str(algolia_data.get("search_published_date", ""))
        publish_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}" if len(raw_date) == 8 else ""

    # Cook / prep / total time
    prep_time = _parse_iso_duration(jsonld.get("prepTime", ""))
    cook_time = _parse_iso_duration(jsonld.get("cookTime", ""))
    total_time = _parse_iso_duration(jsonld.get("totalTime", ""))

    # Rating
    agg = jsonld.get("aggregateRating", {})
    avg_score = agg.get("ratingValue")
    ratings_count = agg.get("reviewCount")

    # Keywords / tags
    keywords_raw = jsonld.get("keywords", "")
    keywords = [k.strip() for k in keywords_raw.split(",")] if isinstance(keywords_raw, str) and keywords_raw else []

    # Nutrition
    nutrition = jsonld.get("nutrition", {})
    calories_str = nutrition.get("calories", "") if isinstance(nutrition, dict) else ""
    calories = None
    if calories_str:
        # May be "350 calories" or just "350"
        cal_parts = str(calories_str).split()
        try:
            calories = int(cal_parts[0])
        except (ValueError, IndexError):
            pass

    # Diet — can be a list
    diet_raw = jsonld.get("suitableForDiet", "")
    if isinstance(diet_raw, list):
        diet_labels = [d.replace("https://schema.org/", "").replace("Diet", "") for d in diet_raw if d]
    else:
        diet_labels = [diet_raw.replace("https://schema.org/", "").replace("Diet", "")] if diet_raw else []
    diet_label = ", ".join(diet_labels)

    # Author
    author_raw = jsonld.get("author", {})
    if isinstance(author_raw, dict):
        author = author_raw.get("name", "")
    elif isinstance(author_raw, list):
        author = ", ".join(a.get("name", "") if isinstance(a, dict) else str(a) for a in author_raw)
    else:
        author = str(author_raw) if author_raw else ""
    if not author:
        author = algolia_data.get("search_author", "")

    # Ingredients
    ingredients: list[str] = jsonld.get("recipeIngredient", [])

    # Instructions
    steps: list[str] = []
    for step in jsonld.get("recipeInstructions", []):
        if isinstance(step, dict):
            text = _strip_html(step.get("text", ""))
        else:
            text = _strip_html(str(step))
        if text:
            steps.append(text)

    if output == "json":
        render(
            {
                "id": numeric_id,
                "title": title,
                "description": description,
                "url": url,
                "yields": yields,
                "total_time": total_time or None,
                "prep_time": prep_time or None,
                "cook_time": cook_time or None,
                "publish_date": publish_date,
                "author": author or None,
                "avg_score": avg_score,
                "ratings_count": ratings_count,
                "keywords": keywords,
                "ingredients": ingredients,
                "steps": steps,
                "calories": calories,
                "diet": diet_label or None,
            },
            fmt="json",
        )
        return

    meta = Table(show_header=False, box=None, padding=(0, 1))
    meta.add_column("Field", style="bold cyan", no_wrap=True)
    meta.add_column("Value")
    meta.add_row("ID", numeric_id)
    meta.add_row("URL", url)
    if yields:
        meta.add_row("Yields", yields)
    if total_time:
        meta.add_row("Total Time", total_time)
    elif prep_time or cook_time:
        if prep_time:
            meta.add_row("Prep Time", prep_time)
        if cook_time:
            meta.add_row("Cook Time", cook_time)
    if publish_date:
        meta.add_row("Published", publish_date)
    if author:
        meta.add_row("Author", author)
    if avg_score:
        rating_str = f"{avg_score}"
        if ratings_count:
            rating_str += f" ({ratings_count} ratings)"
        meta.add_row("Avg Rating", rating_str)
    if keywords:
        meta.add_row("Keywords", ", ".join(keywords[:8]))
    if calories:
        meta.add_row("Calories", f"{calories} per serving")
    if diet_label:
        meta.add_row("Diet", diet_label)

    console.print(Panel(Text(title, style="bold"), border_style="cyan"))
    console.print(meta)

    if description:
        console.print(f"\n[italic]{description}[/italic]")

    if ingredients:
        console.print()
        console.print(Rule("[bold]Ingredients[/bold]", style="cyan"))
        for line in ingredients:
            console.print(f"  {line}")

    if steps:
        console.print()
        console.print(Rule("[bold]Instructions[/bold]", style="cyan"))
        for i, step in enumerate(steps, 1):
            console.print(f"  [bold cyan]{i}.[/bold cyan] {step}")
            console.print()


def _describe_document(
    ctx: typer.Context,
    content_type: str,
    document_id: str,
    output: str,
) -> None:
    """Generic renderer for any non-recipe content type (fetched from Algolia)."""
    # Strip type prefix if present (e.g. "equipment_review_2338" → "2338")
    prefix = f"{content_type}_"
    if document_id.startswith(prefix):
        document_id = document_id[len(prefix):]

    object_id = f"{content_type}_{document_id}"

    try:
        with _client(ctx) as client:
            data = client.get_document_by_object_id(object_id)

        if output == "json":
            render(data, fmt="json")
            return

        title = data.get("title", "")
        slug = data.get("slug", "")
        description = _strip_html(data.get("description", "") or "")
        raw_date = str(data.get("search_published_date", ""))
        publish_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}" if len(raw_date) == 8 else ""
        authors = data.get("search_author", [])
        stickers = data.get("search_stickers", [])
        keywords = data.get("search_facet_keywords", [])
        buy_link = data.get("search_atk_buy_now_link", "")
        search_url = data.get("search_url", "")
        url = f"https://www.americastestkitchen.com{search_url}" if search_url else (
            build_atk_url(slug, content_type) if slug else ""
        )

        meta = Table(show_header=False, box=None, padding=(0, 1))
        meta.add_column("Field", style="bold cyan", no_wrap=True)
        meta.add_column("Value")
        meta.add_row("ID", document_id)
        if url:
            meta.add_row("URL", url)
        if publish_date:
            meta.add_row("Published", publish_date)
        if authors:
            meta.add_row("Author", ", ".join(authors))
        if keywords:
            meta.add_row("Keywords", ", ".join(keywords))
        if stickers:
            meta.add_row("Info", ", ".join(stickers))
        if buy_link:
            meta.add_row("Buy Now", buy_link)

        console.print(Panel(Text(title, style="bold"), border_style="cyan"))
        console.print(meta)
        if description:
            console.print(f"\n[italic]{description}[/italic]")

    except ATKError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)


@app.command()
def equipment_review(
    ctx: typer.Context,
    review_id: Annotated[str, typer.Argument(help="Equipment review ID (numeric or equipment_review_NNNNN)")],
    output: Annotated[str, typer.Option("--output", "-o")] = "table",
) -> None:
    """Show details for an equipment review."""
    _describe_document(ctx, "equipment_review", review_id, output)


@app.command()
def article(
    ctx: typer.Context,
    article_id: Annotated[str, typer.Argument(help="Article ID (numeric or article_NNNNN)")],
    output: Annotated[str, typer.Option("--output", "-o")] = "table",
) -> None:
    """Show details for an article."""
    _describe_document(ctx, "article", article_id, output)


@app.command()
def taste_test(
    ctx: typer.Context,
    taste_test_id: Annotated[str, typer.Argument(help="Taste test ID (numeric or taste_test_NNNNN)")],
    output: Annotated[str, typer.Option("--output", "-o")] = "table",
) -> None:
    """Show details for a taste test."""
    _describe_document(ctx, "taste_test", taste_test_id, output)


@app.command()
def episode(
    ctx: typer.Context,
    episode_id: Annotated[str, typer.Argument(help="Episode ID (numeric or episode_NNNNN)")],
    output: Annotated[str, typer.Option("--output", "-o")] = "table",
) -> None:
    """Show details for an episode."""
    _describe_document(ctx, "episode", episode_id, output)


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
