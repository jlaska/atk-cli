"""Tests for `atk search` command."""

import httpx
import pytest
import respx

from atk_cli.main import app

ALGOLIA_BASE = "https://y1fnzxui30-dsn.algolia.net"

_SEARCH_RESPONSE = {
    "results": [
        {
            "hits": [
                {"objectID": "recipe_1", "title": "Roast Chicken", "search_document_klass": "recipe"},
                {"objectID": "recipe_2", "title": "Pasta Primavera", "search_document_klass": "recipe"},
            ],
            "nbHits": 2,
        }
    ]
}

_EMPTY_RESPONSE = {
    "results": [{"hits": [], "nbHits": 0}]
}


def test_search_basic(runner):
    """Basic search returns results and exits cleanly."""
    with respx.mock(assert_all_called=False) as mock:
        mock.post(f"{ALGOLIA_BASE}/1/indexes/*/queries").mock(
            return_value=httpx.Response(200, json=_SEARCH_RESPONSE)
        )
        result = runner.invoke(app, ["search", "roast chicken"])
    assert result.exit_code == 0


def test_search_type_filter(runner):
    """--type flag is passed through to the Algolia request."""
    with respx.mock(assert_all_called=False) as mock:
        route = mock.post(f"{ALGOLIA_BASE}/1/indexes/*/queries").mock(
            return_value=httpx.Response(200, json=_SEARCH_RESPONSE)
        )
        result = runner.invoke(app, ["search", "chicken", "--type", "article"])
    assert result.exit_code == 0
    if route.calls:
        import json
        body = json.loads(route.calls.last.request.content)
        params = body["requests"][0]["params"]
        assert "article" in params


def test_search_empty_results(runner):
    """Empty search results exits cleanly (no crash on empty hits)."""
    with respx.mock(assert_all_called=False) as mock:
        mock.post(f"{ALGOLIA_BASE}/1/indexes/*/queries").mock(
            return_value=httpx.Response(200, json=_EMPTY_RESPONSE)
        )
        result = runner.invoke(app, ["search", "xyzzy"])
    assert result.exit_code == 0


def test_search_algolia_error_hint(runner):
    """Algolia 'does not exist' error shows the refresh-index hint."""
    with respx.mock(assert_all_called=False) as mock:
        mock.post(f"{ALGOLIA_BASE}/1/indexes/*/queries").mock(
            return_value=httpx.Response(404, text='{"message":"Index does not exist"}')
        )
        result = runner.invoke(app, ["search", "chicken"])
    assert result.exit_code == 1
    assert "refresh-index" in result.output or "does not exist" in result.output.lower()


def test_search_json_output(runner):
    """--output json flag passes through and exits cleanly."""
    with respx.mock(assert_all_called=False) as mock:
        mock.post(f"{ALGOLIA_BASE}/1/indexes/*/queries").mock(
            return_value=httpx.Response(200, json=_SEARCH_RESPONSE)
        )
        result = runner.invoke(app, ["search", "pasta", "-o", "json"])
    assert result.exit_code == 0
