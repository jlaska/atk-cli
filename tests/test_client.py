"""Tests for ATKClient methods with respx-mocked HTTP responses."""

import json

import httpx
import pytest
import respx

from atk_cli.client import ATKClient
from atk_cli.exceptions import APIError, AuthenticationError
from tests.fixtures.recipe_algolia import ALGOLIA_DOCUMENT, ALGOLIA_SEARCH_RESPONSE
from tests.fixtures.recipe_rest import RECIPE_COLLECTIONS, RECIPE_DETAIL, RECIPE_RATING

BASE = "https://www.americastestkitchen.com"
ALGOLIA_BASE = "https://y1fnzxui30-dsn.algolia.net"
INDEX = "test_index"  # matches FAKE_ALGOLIA_CONFIG in conftest


# ── REST API tests ────────────────────────────────────────────────────────────

@respx.mock
def test_get_recipe_detail_success(client):
    respx.get(f"{BASE}/api/v6/recipes/123").mock(
        return_value=httpx.Response(200, json=RECIPE_DETAIL)
    )
    result = client.get_recipe_detail(123)
    assert result["title"] == "Classic Roast Chicken"
    assert result["slug"] == "classic-roast-chicken"


@respx.mock
def test_get_recipe_detail_404(client):
    respx.get(f"{BASE}/api/v6/recipes/999").mock(
        return_value=httpx.Response(404, text="Not Found")
    )
    with pytest.raises(APIError) as exc_info:
        client.get_recipe_detail(999)
    assert exc_info.value.status_code == 404


@respx.mock
def test_get_recipe_detail_401(client):
    respx.get(f"{BASE}/api/v6/recipes/123").mock(
        return_value=httpx.Response(401, text="Unauthorized")
    )
    with pytest.raises(AuthenticationError):
        client.get_recipe_detail(123)


@respx.mock
def test_get_recipe_rating(client):
    respx.get(f"{BASE}/api/v6/ratings/recipe/123").mock(
        return_value=httpx.Response(200, json=RECIPE_RATING)
    )
    result = client.get_recipe_rating(123)
    avg = result["data"]["rating"]["attributes"]["avgScore"]
    assert avg == 4.7


@respx.mock
def test_get_favorites_page(client):
    payload = {"results": [{"object_id": "recipe_1", "document_title": "Chicken"}], "pagination": {"last_page": True}}
    respx.get(f"{BASE}/api/v6/user_favorites/results").mock(
        return_value=httpx.Response(200, json=payload)
    )
    result = client.get_favorites_page()
    assert len(result["results"]) == 1


@respx.mock
def test_get_trending_recipes(client):
    payload = {"results": [{"objectID": "recipe_1", "title": "Trending Chicken"}]}
    respx.get(f"{BASE}/api/cortado/trending-recipes").mock(
        return_value=httpx.Response(200, json=payload)
    )
    result = client.get_trending_recipes()
    assert result["results"][0]["title"] == "Trending Chicken"


@respx.mock
def test_create_favorite(client):
    payload = {"id": "fav_1", "object_id": "recipe_123"}
    respx.post(f"{BASE}/api/v6/user_favorites").mock(
        return_value=httpx.Response(200, json=payload)
    )
    result = client.create_favorite("recipe_123")
    assert result["object_id"] == "recipe_123"


@respx.mock
def test_delete_favorite(client):
    respx.delete(f"{BASE}/api/v6/user_favorites/recipe_123").mock(
        return_value=httpx.Response(200, json={"deleted": True})
    )
    result = client.delete_favorite("recipe_123")
    assert result.get("deleted") is True


# ── Algolia tests ─────────────────────────────────────────────────────────────

@respx.mock
def test_get_document_by_object_id(client):
    url = f"{ALGOLIA_BASE}/1/indexes/{INDEX}/recipe_123"
    respx.get(url).mock(return_value=httpx.Response(200, json=ALGOLIA_DOCUMENT))
    result = client.get_document_by_object_id("recipe_123")
    assert result["objectID"] == "recipe_123"
    assert result["title"] == "Classic Roast Chicken"


@respx.mock
def test_get_document_by_object_id_sends_algolia_headers(client):
    url = f"{ALGOLIA_BASE}/1/indexes/{INDEX}/recipe_123"
    route = respx.get(url).mock(return_value=httpx.Response(200, json=ALGOLIA_DOCUMENT))
    client.get_document_by_object_id("recipe_123")
    request = route.calls.last.request
    assert "X-Algolia-Application-Id" in request.headers
    assert "X-Algolia-API-Key" in request.headers


@respx.mock
def test_search(client):
    url = f"{ALGOLIA_BASE}/1/indexes/*/queries"
    route = respx.post(url).mock(
        return_value=httpx.Response(200, json=ALGOLIA_SEARCH_RESPONSE)
    )
    result = client.search("roast chicken")
    assert "results" in result
    hits = result["results"][0]["hits"]
    assert len(hits) == 2

    # Verify request body structure
    request = route.calls.last.request
    body = json.loads(request.content)
    assert "requests" in body
    assert body["requests"][0]["indexName"] == INDEX


# ── JSON-LD scraping tests ────────────────────────────────────────────────────

@respx.mock
def test_get_recipe_jsonld_found(client):
    from tests.fixtures.recipe_jsonld import JSONLD_RECIPE, wrap_jsonld_in_html
    html = wrap_jsonld_in_html(JSONLD_RECIPE)
    respx.get(f"{BASE}/recipes/classic-roast-chicken").mock(
        return_value=httpx.Response(200, text=html)
    )
    result = client.get_recipe_jsonld("/recipes/classic-roast-chicken")
    assert result["@type"] == "Recipe"
    assert result["name"] == "Classic Roast Chicken"


@respx.mock
def test_get_recipe_jsonld_not_found(client):
    respx.get(f"{BASE}/recipes/missing").mock(
        return_value=httpx.Response(200, text="<html><body>No JSON-LD here</body></html>")
    )
    result = client.get_recipe_jsonld("/recipes/missing")
    assert result == {}


@respx.mock
def test_get_recipe_jsonld_list_format(client):
    from tests.fixtures.recipe_jsonld import HTML_JSONLD_LIST
    respx.get(f"{BASE}/recipes/classic-roast-chicken").mock(
        return_value=httpx.Response(200, text=HTML_JSONLD_LIST)
    )
    result = client.get_recipe_jsonld("/recipes/classic-roast-chicken")
    assert result["@type"] == "Recipe"
    assert result["name"] == "Classic Roast Chicken"
