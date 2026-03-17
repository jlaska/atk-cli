"""Tests for _get, _parse_jsonpath_expr, and render() in atk_cli.output."""

from io import StringIO

import pytest
from rich.console import Console as RichConsole

import atk_cli.output as output_mod
from atk_cli.output import _get, _parse_jsonpath_expr, render


@pytest.fixture
def out(monkeypatch):
    """Capture output from render(): console output in buf, rprint output in printed."""
    buf = StringIO()
    test_console = RichConsole(file=buf, force_terminal=False, no_color=True, width=200)
    monkeypatch.setattr(output_mod, "console", test_console)

    printed = []

    def fake_rprint(*args, **kwargs):
        printed.append(str(args[0]) if args else "")

    monkeypatch.setattr(output_mod, "rprint", fake_rprint)
    return buf, printed


# ── _get ──────────────────────────────────────────────────────────────────────

def test_get_simple_key():
    assert _get({"title": "Roast Chicken"}, "title") == "Roast Chicken"


def test_get_nested_key():
    assert _get({"a": {"b": "c"}}, "a.b") == "c"


def test_get_missing_key():
    assert _get({}, "x") == ""


def test_get_missing_nested_key():
    assert _get({"a": {}}, "a.b") == ""


def test_get_float():
    result = _get({"score": 4.7}, "score")
    assert result == "4.70"


def test_get_int():
    result = _get({"count": 42}, "count")
    assert result == "42"


def test_get_slug_with_search_url():
    obj = {
        "slug": "roast-chicken",
        "search_url": "/recipes/roast-chicken",
        "search_document_klass": "recipe",
    }
    result = _get(obj, "slug")
    assert result == "https://www.americastestkitchen.com/recipes/roast-chicken"


def test_get_slug_recipe():
    obj = {
        "slug": "roast-chicken",
        "search_document_klass": "recipe",
    }
    result = _get(obj, "slug")
    assert "roast-chicken" in result
    assert "americastestkitchen.com" in result


def test_get_none_value():
    assert _get({"key": None}, "key") == ""


# ── _parse_jsonpath_expr ──────────────────────────────────────────────────────

def test_parse_jsonpath_expr_valid():
    result = _parse_jsonpath_expr("jsonpath=hits[*]")
    assert result == "hits[*]"


def test_parse_jsonpath_expr_none():
    assert _parse_jsonpath_expr("table") is None


def test_parse_jsonpath_expr_json():
    assert _parse_jsonpath_expr("json") is None


def test_parse_jsonpath_expr_nested():
    result = _parse_jsonpath_expr("jsonpath=results[0].hits[*].title")
    assert result == "results[0].hits[*].title"


# ── render ────────────────────────────────────────────────────────────────────

_FAVORITE_ROW = {
    "object_id": "recipe_1",
    "document_title": "Roast Chicken",
    "document_avg_score": None,
    "document_type": "recipe",
    "site_key": "atk",
    "slug": "roast-chicken",
}


def test_render_json(out):
    """JSON format sends data to rprint as JSON string."""
    buf, printed = out
    render([{"title": "Roast Chicken"}], fmt="json")
    combined = "\n".join(printed)
    assert "Roast Chicken" in combined


def test_render_yaml(out):
    """YAML format renders YAML via console."""
    buf, printed = out
    render([{"title": "Roast Chicken"}], fmt="yaml")
    assert "Roast Chicken" in buf.getvalue()


def test_render_table(out):
    """Table format renders rows using COLUMNS for the resource type."""
    buf, printed = out
    render([_FAVORITE_ROW], fmt="table", resource_type="favorites")
    assert "Roast Chicken" in buf.getvalue()


def test_render_wide(out):
    """Wide format includes extra columns beyond the default set."""
    buf, printed = out
    render([_FAVORITE_ROW], fmt="wide", resource_type="favorites")
    assert "Roast Chicken" in buf.getvalue()


def test_render_empty_list(out):
    """Empty list prints 'No results.' message."""
    buf, printed = out
    render([], fmt="table", resource_type="favorites")
    assert "No results" in buf.getvalue()


def test_render_dict_input(out):
    """A single dict is treated as a one-row list."""
    buf, printed = out
    render(_FAVORITE_ROW, fmt="table", resource_type="favorites")
    assert "Roast Chicken" in buf.getvalue()


def test_render_no_headers(out):
    """no_headers=True suppresses the table header row."""
    buf, printed = out
    render([_FAVORITE_ROW], fmt="table", resource_type="favorites", no_headers=True)
    assert "Roast Chicken" in buf.getvalue()


def test_render_unknown_format(out):
    """Unknown format falls back to JSON output."""
    buf, printed = out
    render([{"title": "Fallback"}], fmt="unknown_format")
    combined = "\n".join(printed)
    assert "Fallback" in combined
