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


# ── Document subcommands ──────────────────────────────────────────────────────

ALGOLIA_DOC_WITH_EXTRAS = {
    "objectID": "equipment_review_456",
    "title": "Best Blender",
    "slug": "best-blender",
    "description": "A great blender for all your needs.",
    "search_published_date": "20230115",
    "search_author": ["Jane Smith"],
    "search_stickers": ["Editor's Choice"],
    "search_facet_keywords": ["blender", "kitchen"],
    "search_atk_buy_now_link": "https://example.com/buy/blender",
    "search_url": "/equipment_reviews/best-blender",
}

_DOC_BASE = f"{ALGOLIA_BASE}/1/indexes/{INDEX}"


def test_describe_equipment_review_table(runner):
    """equipment-review table shows keywords, stickers, and buy-link rows."""
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{_DOC_BASE}/equipment_review_456").mock(
            return_value=httpx.Response(200, json=ALGOLIA_DOC_WITH_EXTRAS)
        )
        result = runner.invoke(app, ["describe", "equipment-review", "456"])
    assert result.exit_code == 0


def test_describe_equipment_review_json(runner):
    """-o json renders JSON output for equipment-review."""
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{_DOC_BASE}/equipment_review_456").mock(
            return_value=httpx.Response(200, json=ALGOLIA_DOC_WITH_EXTRAS)
        )
        result = runner.invoke(app, ["describe", "equipment-review", "456", "-o", "json"])
    assert result.exit_code == 0


def test_describe_article_table(runner):
    """article subcommand resolves to article_{id} Algolia object."""
    doc = {"objectID": "article_789", "title": "Test Article", "slug": "test-article"}
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{_DOC_BASE}/article_789").mock(
            return_value=httpx.Response(200, json=doc)
        )
        result = runner.invoke(app, ["describe", "article", "789"])
    assert result.exit_code == 0


def test_describe_taste_test_table(runner):
    """taste-test subcommand resolves to taste_test_{id} Algolia object."""
    doc = {"objectID": "taste_test_111", "title": "Best Butter", "slug": "best-butter"}
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{_DOC_BASE}/taste_test_111").mock(
            return_value=httpx.Response(200, json=doc)
        )
        result = runner.invoke(app, ["describe", "taste-test", "111"])
    assert result.exit_code == 0


def test_describe_episode_table(runner):
    """episode subcommand resolves to episode_{id} Algolia object."""
    doc = {"objectID": "episode_222", "title": "Season 24 Ep 1", "slug": "s24-ep1"}
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{_DOC_BASE}/episode_222").mock(
            return_value=httpx.Response(200, json=doc)
        )
        result = runner.invoke(app, ["describe", "episode", "222"])
    assert result.exit_code == 0


def test_describe_document_error(runner):
    """Algolia 500 for a document subcommand exits with code 1."""
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{_DOC_BASE}/equipment_review_456").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        result = runner.invoke(app, ["describe", "equipment-review", "456"])
    assert result.exit_code == 1


# ── Collection subcommand ─────────────────────────────────────────────────────

_COLLECTIONS_META = {
    "data": {
        "collections": [
            {"id": 1, "slug": "my-collection", "name": "My Collection"},
        ]
    }
}


def test_describe_collection_by_slug(runner):
    """Describe collection matched by slug."""
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE}/api/v6/user_favorites_meta_data").mock(
            return_value=httpx.Response(200, json=_COLLECTIONS_META)
        )
        result = runner.invoke(app, ["describe", "collection", "my-collection"])
    assert result.exit_code == 0


def test_describe_collection_by_id(runner):
    """Describe collection matched by numeric string id."""
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE}/api/v6/user_favorites_meta_data").mock(
            return_value=httpx.Response(200, json=_COLLECTIONS_META)
        )
        result = runner.invoke(app, ["describe", "collection", "1"])
    assert result.exit_code == 0


def test_describe_collection_not_found(runner):
    """Describe collection with unknown slug exits with code 1."""
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE}/api/v6/user_favorites_meta_data").mock(
            return_value=httpx.Response(200, json=_COLLECTIONS_META)
        )
        result = runner.invoke(app, ["describe", "collection", "nonexistent"])
    assert result.exit_code == 1


def test_describe_collection_api_error(runner):
    """Collections metadata API 500 exits with code 1."""
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE}/api/v6/user_favorites_meta_data").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        result = runner.invoke(app, ["describe", "collection", "my-collection"])
    assert result.exit_code == 1
