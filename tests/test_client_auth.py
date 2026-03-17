"""Tests for ATKClient auth flow, refresh, request error handling, and pagination."""

import httpx
import pytest
import respx

from atk_cli.client import ATKClient
from atk_cli.exceptions import APIError, AuthenticationError, ATKError

BASE = "https://www.americastestkitchen.com"

# Tokens returned by the autouse mock_auth fixture (defined in conftest.py)
from tests.conftest import FAKE_JWT, FAKE_REFRESH, FAKE_TOKENS


# ── _ensure_auth ──────────────────────────────────────────────────────────────

@respx.mock
def test_ensure_auth_valid_token(client):
    """When token is not expired, _ensure_auth returns it without refresh."""
    # autouse mock_auth: is_token_expired returns False
    token = client._ensure_auth()
    assert token == FAKE_JWT


@respx.mock
def test_ensure_auth_refreshes_expired(client, monkeypatch):
    """When token is expired, _ensure_auth calls _refresh."""
    monkeypatch.setattr("atk_cli.auth.is_token_expired", lambda *a, **kw: True)
    monkeypatch.setattr("atk_cli.auth.save_tokens", lambda *a, **kw: None)
    respx.patch(f"{BASE}/v6/sessions/refresh_token").mock(
        return_value=httpx.Response(200, json={"accessToken": "new_access", "refreshToken": "new_refresh"})
    )
    token = client._ensure_auth()
    assert token == "new_access"


# ── _refresh ──────────────────────────────────────────────────────────────────

@respx.mock
def test_refresh_saves_tokens(client, monkeypatch):
    """After a successful refresh, save_tokens is called with new tokens."""
    saved = {}

    def capture_save(access, refresh, profile=None):
        saved["access"] = access
        saved["refresh"] = refresh

    monkeypatch.setattr("atk_cli.auth.save_tokens", capture_save)
    respx.patch(f"{BASE}/v6/sessions/refresh_token").mock(
        return_value=httpx.Response(200, json={"accessToken": "fresh_access", "refreshToken": "fresh_refresh"})
    )
    client._refresh(FAKE_REFRESH)
    assert saved["access"] == "fresh_access"
    assert saved["refresh"] == "fresh_refresh"


@respx.mock
def test_refresh_failure_raises(client):
    """Non-200 refresh response raises AuthenticationError."""
    respx.patch(f"{BASE}/v6/sessions/refresh_token").mock(
        return_value=httpx.Response(401, text="Unauthorized")
    )
    with pytest.raises(AuthenticationError, match="atk login"):
        client._refresh(FAKE_REFRESH)


@respx.mock
def test_refresh_empty_token_raises(client):
    """200 response with empty accessToken raises AuthenticationError."""
    respx.patch(f"{BASE}/v6/sessions/refresh_token").mock(
        return_value=httpx.Response(200, json={"accessToken": "", "refreshToken": "r"})
    )
    with pytest.raises(AuthenticationError, match="no access token"):
        client._refresh(FAKE_REFRESH)


# ── _request error handling ───────────────────────────────────────────────────

@respx.mock
def test_request_401_raises_auth_error(client):
    """401 response raises AuthenticationError."""
    respx.get(f"{BASE}/api/v6/recipes/1").mock(
        return_value=httpx.Response(401, text="Unauthorized")
    )
    with pytest.raises(AuthenticationError, match="atk login"):
        client._request("GET", "/api/v6/recipes/1")


@respx.mock
def test_request_500_raises_api_error(client):
    """Non-success (500) response raises APIError with status code."""
    respx.get(f"{BASE}/api/v6/recipes/1").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )
    with pytest.raises(APIError) as exc_info:
        client._request("GET", "/api/v6/recipes/1")
    assert exc_info.value.status_code == 500


@respx.mock
def test_request_non_json_response(client):
    """200 response with non-JSON body returns raw text instead of crashing."""
    respx.get(f"{BASE}/api/v6/recipes/1").mock(
        return_value=httpx.Response(200, text="plain text response")
    )
    result = client._request("GET", "/api/v6/recipes/1")
    assert result == "plain text response"


@respx.mock
def test_request_unauthenticated(client):
    """authenticated=False requests do not include x-access-token header."""
    route = respx.get(f"{BASE}/api/cortado/trending-recipes").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    client._request("GET", "/api/cortado/trending-recipes", authenticated=False)
    request = route.calls.last.request
    assert "x-access-token" not in request.headers


# ── get_all_favorites pagination ──────────────────────────────────────────────

@respx.mock
def test_get_all_favorites_pagination(client):
    """get_all_favorites fetches all pages until last_page=True."""
    page1 = {
        "results": [{"object_id": "recipe_1"}],
        "pagination": {"last_page": False},
    }
    page2 = {
        "results": [{"object_id": "recipe_2"}],
        "pagination": {"last_page": True},
    }
    call_count = 0

    def side_effect(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json=page1 if call_count == 1 else page2)

    respx.get(f"{BASE}/api/v6/user_favorites/results").mock(side_effect=side_effect)
    results = client.get_all_favorites()
    assert len(results) == 2
    assert call_count == 2


@respx.mock
def test_get_all_favorites_single_page(client):
    """get_all_favorites stops after a single page when last_page=True."""
    payload = {
        "results": [{"object_id": "recipe_1"}, {"object_id": "recipe_2"}],
        "pagination": {"last_page": True},
    }
    respx.get(f"{BASE}/api/v6/user_favorites/results").mock(
        return_value=httpx.Response(200, json=payload)
    )
    results = client.get_all_favorites()
    assert len(results) == 2


# ── export_recipe_pdf ──────────────────────────────────────────────────────────

def test_export_pdf_no_playwright(client, tmp_path, monkeypatch):
    """export_recipe_pdf raises ATKError with install hint when playwright is missing."""
    import sys
    # Simulate playwright not being installed
    monkeypatch.setitem(sys.modules, "playwright", None)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)

    output_path = tmp_path / "recipe.pdf"
    with pytest.raises(ATKError, match="playwright"):
        client.export_recipe_pdf("classic-roast-chicken", output_path)
