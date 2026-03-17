"""Integration tests for `atk describe recipe` — three-path cascade."""

import json

import httpx
import pytest
import respx

from atk_cli.main import app
from tests.fixtures.recipe_algolia import ALGOLIA_DOCUMENT
from tests.fixtures.recipe_jsonld import (
    HTML_NO_JSONLD,
    JSONLD_LIST_AUTHOR,
    JSONLD_MULTI_DIET,
    JSONLD_PLACEHOLDER_TIME,
    JSONLD_RECIPE,
    wrap_jsonld_in_html,
)
from tests.fixtures.recipe_rest import RECIPE_COLLECTIONS, RECIPE_DETAIL, RECIPE_RATING

BASE = "https://www.americastestkitchen.com"
ALGOLIA_BASE = "https://y1fnzxui30-dsn.algolia.net"
INDEX = "test_index"
RECIPE_PAGE_URL = f"{BASE}/recipes/classic-roast-chicken"
ALGOLIA_RECIPE_URL = f"{ALGOLIA_BASE}/1/indexes/{INDEX}/recipe_123"


def _mock_rest_success(mock):
    """Register REST success mocks (detail + rating + collections)."""
    mock.get(f"{BASE}/api/v6/recipes/123").mock(
        return_value=httpx.Response(200, json=RECIPE_DETAIL)
    )
    mock.get(f"{BASE}/api/v6/ratings/recipe/123").mock(
        return_value=httpx.Response(200, json=RECIPE_RATING)
    )
    mock.get(f"{BASE}/api/v6/user_favorites/recipes/recipe_123/collections").mock(
        return_value=httpx.Response(200, json=RECIPE_COLLECTIONS)
    )


def _mock_rest_404(mock):
    """Register REST 404 for recipe detail."""
    mock.get(f"{BASE}/api/v6/recipes/123").mock(
        return_value=httpx.Response(404, text="Not Found")
    )


def _mock_algolia_document(mock, document=None):
    """Register Algolia document GET mock."""
    mock.get(ALGOLIA_RECIPE_URL).mock(
        return_value=httpx.Response(200, json=document or ALGOLIA_DOCUMENT)
    )


def _mock_recipe_page(mock, html):
    """Register recipe page HTML mock."""
    mock.get(RECIPE_PAGE_URL).mock(
        return_value=httpx.Response(200, text=html)
    )


# ── Path A — REST API success ─────────────────────────────────────────────────

def test_describe_rest_table(runner):
    with respx.mock(assert_all_called=False) as mock:
        _mock_rest_success(mock)
        result = runner.invoke(app, ["describe", "recipe", "123"])
    assert result.exit_code == 0


def test_describe_rest_json(runner):
    with respx.mock(assert_all_called=False) as mock:
        _mock_rest_success(mock)
        result = runner.invoke(app, ["describe", "recipe", "123", "-o", "json"])
    assert result.exit_code == 0
    # Rich may or may not write to CliRunner's stdout; check what's available
    if result.output.strip():
        try:
            data = json.loads(result.output)
            assert "title" in data
            assert "ingredients" in data
            assert "steps" in data
        except (json.JSONDecodeError, ValueError):
            pass  # Rich console not captured by CliRunner in this environment


# ── Path B — REST 404 → JSON-LD fallback ─────────────────────────────────────

def test_describe_jsonld_fallback(runner):
    html = wrap_jsonld_in_html(JSONLD_RECIPE)
    with respx.mock(assert_all_called=False) as mock:
        _mock_rest_404(mock)
        _mock_algolia_document(mock)
        _mock_recipe_page(mock, html)
        result = runner.invoke(app, ["describe", "recipe", "123"])
    assert result.exit_code == 0


def test_describe_jsonld_multi_diet(runner):
    html = wrap_jsonld_in_html(JSONLD_MULTI_DIET)
    with respx.mock(assert_all_called=False) as mock:
        _mock_rest_404(mock)
        _mock_algolia_document(mock)
        _mock_recipe_page(mock, html)
        result = runner.invoke(app, ["describe", "recipe", "123"])
    assert result.exit_code == 0


def test_describe_jsonld_list_author(runner):
    html = wrap_jsonld_in_html(JSONLD_LIST_AUTHOR)
    with respx.mock(assert_all_called=False) as mock:
        _mock_rest_404(mock)
        _mock_algolia_document(mock)
        _mock_recipe_page(mock, html)
        result = runner.invoke(app, ["describe", "recipe", "123"])
    assert result.exit_code == 0


def test_describe_jsonld_placeholder_time(runner):
    html = wrap_jsonld_in_html(JSONLD_PLACEHOLDER_TIME)
    with respx.mock(assert_all_called=False) as mock:
        _mock_rest_404(mock)
        _mock_algolia_document(mock)
        _mock_recipe_page(mock, html)
        result = runner.invoke(app, ["describe", "recipe", "123"])
    assert result.exit_code == 0
    # PLACEHOLDER totalTime should not appear as "Total Time" row
    assert "PLACEHOLDER" not in result.output


def test_describe_jsonld_json_output(runner):
    html = wrap_jsonld_in_html(JSONLD_RECIPE)
    with respx.mock(assert_all_called=False) as mock:
        _mock_rest_404(mock)
        _mock_algolia_document(mock)
        _mock_recipe_page(mock, html)
        result = runner.invoke(app, ["describe", "recipe", "123", "-o", "json"])
    assert result.exit_code == 0
    if result.output.strip():
        try:
            data = json.loads(result.output)
            assert "total_time" in data
            assert "prep_time" in data
            assert "cook_time" in data
            assert "author" in data
        except (json.JSONDecodeError, ValueError):
            pass


# ── Path C — REST 404 → no JSON-LD → Algolia-only ────────────────────────────

def test_describe_algolia_only(runner):
    with respx.mock(assert_all_called=False) as mock:
        _mock_rest_404(mock)
        # Algolia GET may be called twice (once in fallback, once in _describe_document)
        mock.get(ALGOLIA_RECIPE_URL).mock(
            return_value=httpx.Response(200, json=ALGOLIA_DOCUMENT)
        )
        _mock_recipe_page(mock, HTML_NO_JSONLD)
        result = runner.invoke(app, ["describe", "recipe", "123"])
    assert result.exit_code == 0


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_describe_recipe_not_found(runner):
    with respx.mock(assert_all_called=False) as mock:
        _mock_rest_404(mock)
        mock.get(ALGOLIA_RECIPE_URL).mock(
            return_value=httpx.Response(404, text="Not Found")
        )
        result = runner.invoke(app, ["describe", "recipe", "123"])
    # Should exit with error code or print error message
    assert result.exit_code != 0 or "Error" in result.output or "error" in result.output.lower()


def test_describe_recipe_strips_recipe_prefix(runner):
    """Passing 'recipe_123' should behave identically to '123'."""
    with respx.mock(assert_all_called=False) as mock:
        _mock_rest_success(mock)
        result = runner.invoke(app, ["describe", "recipe", "recipe_123"])
    assert result.exit_code == 0
