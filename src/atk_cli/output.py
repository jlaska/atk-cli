"""Output rendering: table / json / yaml / wide / jsonpath."""

from typing import Any

import json
import yaml
from rich import print as rprint
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from .constants import build_atk_url

console = Console()

# Column definitions per resource type
# Format: (header, key_path) where key_path is dot-separated
COLUMNS: dict[str, list[tuple[str, str]]] = {
    "favorites": [
        ("ID", "object_id"),
        ("Title", "document_title"),
        ("Rating", "document_avg_score"),
        ("Type", "document_type"),
        ("Site", "site_key"),
    ],
    "recent": [
        ("ID", "id"),
        ("Title", "title"),
        ("Avg Score", "avgScore"),
        ("Your Rating", "userRating"),
    ],
    "top_rated": [
        ("ID", "id"),
        ("Title", "title"),
        ("Avg Score", "avgScore"),
        ("Your Rating", "userRating"),
    ],
    "collections": [
        ("ID", "id"),
        ("Name", "name"),
        ("Items", "items_count"),
        ("Site", "site_key"),
    ],
    "search": [
        ("ID", "objectID"),
        ("Title", "title"),
        ("Type", "search_document_klass"),
        ("Rating", "avgScore"),
    ],
    "trending": [
        ("ID", "objectID"),
        ("Title", "title"),
        ("Type", "search_document_klass"),
        ("Ratings", "search_user_ratings_count"),
    ],
}

WIDE_EXTRA: dict[str, list[tuple[str, str]]] = {
    "favorites": [("URL", "slug")],
    "recent": [("URL", "slug")],
    "search": [("URL", "slug"), ("Description", "description")],
}


def _get(obj: dict[str, Any], key_path: str) -> str:
    val = obj
    for part in key_path.split("."):
        if isinstance(val, dict):
            val = val.get(part)
        else:
            val = None
        if val is None:
            break
    if val is None:
        return ""
    if isinstance(val, float):
        return f"{val:.2f}"
    if key_path == "slug" and val:
        if search_url := obj.get("search_url"):
            return f"https://www.americastestkitchen.com{search_url}"
        doc_type = obj.get("document_type") or obj.get("search_document_klass") or "recipe"
        object_id = obj.get("object_id", "")
        numeric_id = object_id.split("_")[-1] if "_" in object_id else ""
        if numeric_id and doc_type != "recipe":
            return build_atk_url(f"{numeric_id}-{val}", doc_type)
        return build_atk_url(val, doc_type)
    return str(val)


def _parse_jsonpath_expr(fmt: str) -> str | None:
    if fmt.startswith("jsonpath="):
        return fmt[len("jsonpath="):]
    return None


def render(
    data: Any,
    fmt: str = "table",
    resource_type: str = "favorites",
    no_headers: bool = False,
) -> None:
    jsonpath_expr = _parse_jsonpath_expr(fmt)

    if jsonpath_expr:
        _render_jsonpath(data, jsonpath_expr)
    elif fmt == "json":
        rprint(json.dumps(data, indent=2))
    elif fmt == "yaml":
        console.print(Syntax(yaml.dump(data, allow_unicode=True), "yaml", theme="monokai"))
    elif fmt in ("table", "wide"):
        _render_table(data, resource_type=resource_type, wide=(fmt == "wide"), no_headers=no_headers)
    else:
        # Fallback
        rprint(json.dumps(data, indent=2))


def _render_table(
    rows: list[dict[str, Any]] | dict[str, Any],
    resource_type: str,
    wide: bool,
    no_headers: bool,
) -> None:
    if isinstance(rows, dict):
        rows = [rows]
    if not rows:
        console.print("[dim]No results.[/dim]")
        return

    columns = list(COLUMNS.get(resource_type, [("Key", "key"), ("Value", "value")]))
    if wide:
        columns = columns + list(WIDE_EXTRA.get(resource_type, []))

    table = Table(show_header=not no_headers, header_style="bold cyan", box=None, padding=(0, 1))
    for header, _ in columns:
        table.add_column(header)

    for row in rows:
        table.add_row(*[_get(row, key) for _, key in columns])

    console.print(table)


def _render_jsonpath(data: Any, expr: str) -> None:
    try:
        from jsonpath_ng.ext import parse as jp_parse
        jp = jp_parse(expr)
        matches = [m.value for m in jp.find(data)]
        if len(matches) == 1:
            rprint(matches[0])
        else:
            rprint(matches)
    except ImportError:
        console.print("[red]jsonpath-ng not installed. Run: pip install jsonpath-ng[/red]")
    except Exception as exc:
        console.print(f"[red]JSONPath error: {exc}[/red]")
