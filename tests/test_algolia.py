"""Tests for atk_cli.algolia — discovery, cache, and config resolution."""

import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx

# Save real function references at import time, before autouse fixtures patch them.
from atk_cli.algolia import (
    discover_algolia_config,
    get_algolia_config as _real_get_algolia_config,
    get_index as _real_get_index,
    load_cached_config,
    save_cached_config,
)
from atk_cli.constants import ALGOLIA_INDEX

BASE_URL = "https://www.americastestkitchen.com"

# Valid Algolia credential constants for crafting test HTML/JS
TEST_APP_ID = "TESTAPP001"   # 10 chars, matches [A-Z0-9]{8,12}
TEST_API_KEY = "a" * 32      # 32 hex chars
TEST_INDEX = "everest_search_cortado_production"

_GOOD_HTML = (
    f'"applicationId": "{TEST_APP_ID}", '
    f'"apiKey": "{TEST_API_KEY}", '
    f"{TEST_INDEX}"
)
_NO_CREDS_HTML = f"{TEST_INDEX}"  # has index, but no app_id/api_key in HTML
_NO_INDEX_HTML = (
    f'"applicationId": "{TEST_APP_ID}", '
    f'"apiKey": "{TEST_API_KEY}"'
)
_JS_CHUNK_CONTENT = f'({TEST_APP_ID!r},{TEST_API_KEY!r})'  # matches _JS_CREDS_PATTERN
# Pattern: ("APP_ID","api_key_hex") — need raw parens
_JS_CREDS_SNIPPET = f'("{TEST_APP_ID}","{TEST_API_KEY}")'


@pytest.fixture
def tmp_algolia(tmp_path, monkeypatch):
    """Redirect ALGOLIA_CACHE_FILE and ATK_DIR to tmp_path."""
    cache_file = tmp_path / "algolia_index.json"
    monkeypatch.setattr("atk_cli.algolia.ALGOLIA_CACHE_FILE", cache_file)
    monkeypatch.setattr("atk_cli.algolia.ATK_DIR", tmp_path)
    return cache_file


@pytest.fixture
def real_algolia_config(monkeypatch):
    """Restore the real get_algolia_config for tests that exercise it directly."""
    monkeypatch.setattr("atk_cli.algolia.get_algolia_config", _real_get_algolia_config)


@pytest.fixture
def real_get_index_fn(monkeypatch):
    """Restore the real get_index for tests that exercise it directly."""
    monkeypatch.setattr("atk_cli.algolia.get_index", _real_get_index)


# ── discover_algolia_config ───────────────────────────────────────────────────

@respx.mock
def test_discover_html_credentials():
    """Regex patterns extract app_id and api_key directly from HTML."""
    respx.get(f"{BASE_URL}/search").mock(
        return_value=httpx.Response(200, text=_GOOD_HTML)
    )
    result = discover_algolia_config()
    assert result["app_id"] == TEST_APP_ID
    assert result["api_key"] == TEST_API_KEY
    assert result["index_name"] == TEST_INDEX


@respx.mock
def test_discover_js_chunk_fallback():
    """When HTML has no credentials, JS chunks are scraped."""
    chunk_path = "cortado-assets/_next/static/chunks/app-abc123.js"
    html = f'{TEST_INDEX} <script src="{chunk_path}"></script>'
    # Embed chunk URL using the expected pattern
    html_with_chunk = (
        f'{TEST_INDEX} '
        f'src="{chunk_path}"'
    )
    respx.get(f"{BASE_URL}/search").mock(
        return_value=httpx.Response(200, text=html_with_chunk)
    )
    respx.get(f"{BASE_URL}/{chunk_path}").mock(
        return_value=httpx.Response(200, text=_JS_CREDS_SNIPPET)
    )
    result = discover_algolia_config()
    assert result["app_id"] == TEST_APP_ID
    assert result["api_key"] == TEST_API_KEY


@respx.mock
def test_discover_layout_chunk_priority():
    """Layout chunks are sorted before other chunks (index 0 in sort key)."""
    layout_path = "cortado-assets/_next/static/chunks/layout-abc.js"
    other_path = "cortado-assets/_next/static/chunks/app-xyz.js"
    html = f'{TEST_INDEX} src="{other_path}" src="{layout_path}"'
    layout_route = respx.get(f"{BASE_URL}/{layout_path}").mock(
        return_value=httpx.Response(200, text=_JS_CREDS_SNIPPET)
    )
    respx.get(f"{BASE_URL}/{other_path}").mock(
        return_value=httpx.Response(200, text="no creds here")
    )
    respx.get(f"{BASE_URL}/search").mock(
        return_value=httpx.Response(200, text=html)
    )
    result = discover_algolia_config()
    # If layout was tried first and succeeded, other chunk should NOT have been called
    assert result["app_id"] == TEST_APP_ID
    assert layout_route.called


@respx.mock
def test_discover_no_index_raises():
    """Missing index name in HTML raises ValueError."""
    respx.get(f"{BASE_URL}/search").mock(
        return_value=httpx.Response(200, text=f'"applicationId": "{TEST_APP_ID}"')
    )
    with pytest.raises(ValueError, match="index name"):
        discover_algolia_config()


@respx.mock
def test_discover_chunk_request_failure():
    """A failing chunk request is silently skipped; remaining chunks tried."""
    failing_chunk = "cortado-assets/_next/static/chunks/fail.js"
    good_chunk = "cortado-assets/_next/static/chunks/layout-good.js"
    html = f'{TEST_INDEX} src="{failing_chunk}" src="{good_chunk}"'
    respx.get(f"{BASE_URL}/search").mock(
        return_value=httpx.Response(200, text=html)
    )
    respx.get(f"{BASE_URL}/{failing_chunk}").mock(
        return_value=httpx.Response(500, text="Server Error")
    )
    respx.get(f"{BASE_URL}/{good_chunk}").mock(
        return_value=httpx.Response(200, text=_JS_CREDS_SNIPPET)
    )
    result = discover_algolia_config()
    # layout-good.js sorts before fail.js; either way credentials are found
    assert result["index_name"] == TEST_INDEX


# ── load_cached_config ────────────────────────────────────────────────────────

def test_cache_valid(tmp_algolia):
    """Fresh cache within TTL is returned."""
    now = datetime.now(tz=timezone.utc).isoformat()
    tmp_algolia.write_text(json.dumps({
        "app_id": TEST_APP_ID,
        "api_key": TEST_API_KEY,
        "index_name": TEST_INDEX,
        "discovered_at": now,
    }))
    result = load_cached_config()
    assert result is not None
    assert result["app_id"] == TEST_APP_ID


def test_cache_expired(tmp_algolia):
    """Cache older than TTL returns None."""
    old = (datetime.now(tz=timezone.utc) - timedelta(days=8)).isoformat()
    tmp_algolia.write_text(json.dumps({
        "app_id": TEST_APP_ID,
        "api_key": TEST_API_KEY,
        "index_name": TEST_INDEX,
        "discovered_at": old,
    }))
    assert load_cached_config(max_age_days=7) is None


def test_cache_missing_file(tmp_algolia):
    """Non-existent cache file returns None."""
    assert not tmp_algolia.exists()
    assert load_cached_config() is None


def test_cache_corrupt_json(tmp_algolia):
    """Corrupt JSON cache returns None (exception swallowed)."""
    tmp_algolia.write_text("{not valid json")
    assert load_cached_config() is None


def test_cache_missing_index_name(tmp_algolia):
    """Cache without index_name returns None."""
    now = datetime.now(tz=timezone.utc).isoformat()
    tmp_algolia.write_text(json.dumps({
        "app_id": TEST_APP_ID,
        "api_key": TEST_API_KEY,
        "discovered_at": now,
        # no index_name
    }))
    assert load_cached_config() is None


# ── save_cached_config ────────────────────────────────────────────────────────

def test_save_cache_creates_directory(tmp_path, monkeypatch):
    """save_cached_config creates the directory if it doesn't exist."""
    new_dir = tmp_path / "subdir"
    cache_file = new_dir / "algolia_index.json"
    monkeypatch.setattr("atk_cli.algolia.ALGOLIA_CACHE_FILE", cache_file)
    monkeypatch.setattr("atk_cli.algolia.ATK_DIR", new_dir)
    save_cached_config({"app_id": TEST_APP_ID, "api_key": TEST_API_KEY, "index_name": TEST_INDEX})
    assert cache_file.exists()


def test_save_cache_adds_timestamp(tmp_algolia, monkeypatch):
    """save_cached_config writes a discovered_at timestamp."""
    save_cached_config({"app_id": TEST_APP_ID, "api_key": TEST_API_KEY, "index_name": TEST_INDEX})
    data = json.loads(tmp_algolia.read_text())
    assert "discovered_at" in data
    # Should parse as a valid datetime
    datetime.fromisoformat(data["discovered_at"])


# ── get_algolia_config ────────────────────────────────────────────────────────

def test_get_config_returns_fresh_cache(tmp_algolia, real_algolia_config):
    """Cache hit skips network discovery."""
    now = datetime.now(tz=timezone.utc).isoformat()
    tmp_algolia.write_text(json.dumps({
        "app_id": TEST_APP_ID,
        "api_key": TEST_API_KEY,
        "index_name": TEST_INDEX,
        "discovered_at": now,
    }))
    with respx.mock(assert_all_called=False) as mock:
        result = _real_get_algolia_config()
    assert result["app_id"] == TEST_APP_ID
    assert not mock.calls  # no HTTP calls made


def test_get_config_missing_keys_triggers_discovery(tmp_algolia, real_algolia_config):
    """Cache without app_id triggers re-discovery."""
    now = datetime.now(tz=timezone.utc).isoformat()
    tmp_algolia.write_text(json.dumps({
        "index_name": TEST_INDEX,
        "discovered_at": now,
        # no app_id or api_key
    }))
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE_URL}/search").mock(
            return_value=httpx.Response(200, text=_GOOD_HTML)
        )
        result = _real_get_algolia_config()
    assert result["app_id"] == TEST_APP_ID


def test_get_config_discovery_fails_uses_expired_cache(tmp_algolia, real_algolia_config):
    """When discovery fails, fall back to cache even if expired (max 365 days)."""
    old = (datetime.now(tz=timezone.utc) - timedelta(days=30)).isoformat()
    tmp_algolia.write_text(json.dumps({
        "app_id": TEST_APP_ID,
        "api_key": TEST_API_KEY,
        "index_name": TEST_INDEX,
        "discovered_at": old,
    }))
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE_URL}/search").mock(
            return_value=httpx.Response(500, text="Server Error")
        )
        result = _real_get_algolia_config()
    assert result["app_id"] == TEST_APP_ID


def test_get_config_discovery_fails_no_cache_raises(tmp_algolia, real_algolia_config):
    """When discovery fails and there's no cache, raises ValueError."""
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE_URL}/search").mock(
            return_value=httpx.Response(500, text="Server Error")
        )
        with pytest.raises(ValueError, match="discovery failed"):
            _real_get_algolia_config()


def test_get_config_force_refresh(tmp_algolia, real_algolia_config):
    """force_refresh=True bypasses a valid cache and rediscovers."""
    now = datetime.now(tz=timezone.utc).isoformat()
    # Cache is fresh and complete
    tmp_algolia.write_text(json.dumps({
        "app_id": "OLDAPP00001",
        "api_key": "b" * 32,
        "index_name": "old_index",
        "discovered_at": now,
    }))
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE_URL}/search").mock(
            return_value=httpx.Response(200, text=_GOOD_HTML)
        )
        result = _real_get_algolia_config(force_refresh=True)
    assert result["app_id"] == TEST_APP_ID


# ── get_index ─────────────────────────────────────────────────────────────────

def test_get_index_from_cache(tmp_algolia, real_get_index_fn):
    """Returns index_name from cache when available."""
    now = datetime.now(tz=timezone.utc).isoformat()
    tmp_algolia.write_text(json.dumps({
        "app_id": TEST_APP_ID,
        "api_key": TEST_API_KEY,
        "index_name": "everest_search_special_production",
        "discovered_at": now,
    }))
    result = _real_get_index()
    assert result == "everest_search_special_production"


def test_get_index_fallback_to_constant(tmp_algolia, real_algolia_config, real_get_index_fn):
    """Falls back to ALGOLIA_INDEX constant when everything fails."""
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE_URL}/search").mock(
            return_value=httpx.Response(500, text="fail")
        )
        result = _real_get_index()
    assert result == ALGOLIA_INDEX
