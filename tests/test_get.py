"""Tests for `atk get` subcommands: favorites, collections, trending, subscription."""

import httpx
import pytest
import respx

from atk_cli.main import app

BASE = "https://www.americastestkitchen.com"

_FAVORITES_PAGE = {
    "results": [
        {"object_id": "recipe_1", "document_title": "Roast Chicken", "document_type": "recipe"},
        {"object_id": "recipe_2", "document_title": "Pasta", "document_type": "recipe"},
    ],
    "pagination": {"last_page": True, "total_count": 2, "page": 1},
}

_RECENT_DATA = {
    "data": {
        "results": [
            {"object_id": "recipe_3", "document_title": "Recent Recipe", "document_type": "recipe"},
        ]
    }
}

_TOP_RATED_DATA = {
    "data": {
        "results": [
            {"object_id": "recipe_4", "document_title": "Top Recipe", "document_type": "recipe"},
        ]
    }
}


# ── favorites (default page) ──────────────────────────────────────────────────

def test_favorites_default(runner):
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE}/api/v6/user_favorites/results").mock(
            return_value=httpx.Response(200, json=_FAVORITES_PAGE)
        )
        result = runner.invoke(app, ["get", "favorites"])
    assert result.exit_code == 0


def test_favorites_json(runner):
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE}/api/v6/user_favorites/results").mock(
            return_value=httpx.Response(200, json=_FAVORITES_PAGE)
        )
        result = runner.invoke(app, ["get", "favorites", "-o", "json"])
    assert result.exit_code == 0


# ── favorites --recent ────────────────────────────────────────────────────────

def test_favorites_recent(runner):
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE}/api/v6/user_favorites/most_recent").mock(
            return_value=httpx.Response(200, json=_RECENT_DATA)
        )
        result = runner.invoke(app, ["get", "favorites", "--recent"])
    assert result.exit_code == 0


# ── favorites --top-rated ─────────────────────────────────────────────────────

def test_favorites_top_rated(runner):
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE}/api/v6/user_favorites/top_rated").mock(
            return_value=httpx.Response(200, json=_TOP_RATED_DATA)
        )
        result = runner.invoke(app, ["get", "favorites", "--top-rated"])
    assert result.exit_code == 0


# ── favorites --all (pagination) ──────────────────────────────────────────────

def test_favorites_all(runner):
    all_page = {
        "results": [{"object_id": "recipe_1", "document_title": "Chicken"}],
        "pagination": {"last_page": True, "total_count": 1, "page": 1},
    }
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE}/api/v6/user_favorites/results").mock(
            return_value=httpx.Response(200, json=all_page)
        )
        result = runner.invoke(app, ["get", "favorites", "--all"])
    assert result.exit_code == 0


# ── trending ──────────────────────────────────────────────────────────────────

def test_trending_no_auth(runner):
    """Trending uses unauthenticated endpoint — should not send auth header."""
    with respx.mock(assert_all_called=False) as mock:
        route = mock.get(f"{BASE}/api/cortado/trending-recipes").mock(
            return_value=httpx.Response(200, json={"hits": [{"title": "Trending"}]})
        )
        result = runner.invoke(app, ["get", "trending"])
    assert result.exit_code == 0
    if route.calls:
        assert "x-access-token" not in route.calls.last.request.headers


# ── collections ───────────────────────────────────────────────────────────────

def test_collections(runner):
    meta = {"collections": [{"id": 1, "name": "My Collection"}]}
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE}/api/v6/user_favorites_meta_data").mock(
            return_value=httpx.Response(200, json=meta)
        )
        result = runner.invoke(app, ["get", "collections"])
    assert result.exit_code == 0


# ── subscription ──────────────────────────────────────────────────────────────

def test_subscription(runner):
    summary = {"plan": "premium", "status": "active"}
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE}/api/v8/cds_core/customer_summaries").mock(
            return_value=httpx.Response(200, json=summary)
        )
        result = runner.invoke(app, ["get", "subscription"])
    assert result.exit_code == 0


# ── error handling ────────────────────────────────────────────────────────────

def test_favorites_api_error(runner):
    """API error is displayed and exits with code 1."""
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE}/api/v6/user_favorites/results").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        result = runner.invoke(app, ["get", "favorites"])
    assert result.exit_code == 1


def test_collections_api_error(runner):
    """Collections API 500 exits with code 1."""
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE}/api/v6/user_favorites_meta_data").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        result = runner.invoke(app, ["get", "collections"])
    assert result.exit_code == 1


def test_trending_list_response(runner):
    """Trending returns bare list — should render as rows."""
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE}/api/cortado/trending-recipes").mock(
            return_value=httpx.Response(200, json=[{"title": "Trending Recipe"}])
        )
        result = runner.invoke(app, ["get", "trending"])
    assert result.exit_code == 0


def test_trending_scalar_response(runner):
    """Trending returns a non-dict, non-list value — wrapped in list."""
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE}/api/cortado/trending-recipes").mock(
            return_value=httpx.Response(200, json="unexpected-scalar")
        )
        result = runner.invoke(app, ["get", "trending"])
    assert result.exit_code == 0


def test_trending_api_error(runner):
    """Trending API 500 exits with code 1."""
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE}/api/cortado/trending-recipes").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        result = runner.invoke(app, ["get", "trending"])
    assert result.exit_code == 1


def test_subscription_api_error(runner):
    """Subscription API 500 exits with code 1."""
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE}/api/v8/cds_core/customer_summaries").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        result = runner.invoke(app, ["get", "subscription"])
    assert result.exit_code == 1
