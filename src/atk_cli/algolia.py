"""Algolia index discovery and caching.

The Algolia index name used by ATK's search changes periodically.
This module auto-discovers the app ID, API key, and index name from ATK's
search page and caches them locally so discovery only happens once per week.
"""

import json
import re
from datetime import datetime, timedelta, timezone

import httpx

from .constants import ALGOLIA_INDEX, ATK_DIR, BASE_URL, BROWSER_HEADERS

ALGOLIA_CACHE_FILE = ATK_DIR / "algolia_index.json"
DEFAULT_TTL_DAYS = 7

_INDEX_PATTERN = re.compile(r"everest_search_[a-z_]+_production")
_APP_ID_PATTERN = re.compile(r'"applicationId"\s*:\s*"([A-Z0-9]{8,12})"')
_API_KEY_PATTERN = re.compile(r'"apiKey"\s*:\s*"([a-f0-9]{32})"')


def discover_algolia_config() -> dict:
    """Fetch the ATK search page and extract Algolia app_id, api_key, and index_name."""
    resp = httpx.get(
        f"{BASE_URL}/search",
        headers=BROWSER_HEADERS,
        follow_redirects=True,
        timeout=15.0,
    )
    resp.raise_for_status()
    text = resp.text

    index_matches = _INDEX_PATTERN.findall(text)
    if not index_matches:
        raise ValueError("Could not find Algolia index name in ATK search page.")

    app_id_matches = _APP_ID_PATTERN.findall(text)
    api_key_matches = _API_KEY_PATTERN.findall(text)

    return {
        "index_name": index_matches[0],
        "app_id": app_id_matches[0] if app_id_matches else None,
        "api_key": api_key_matches[0] if api_key_matches else None,
    }


def load_cached_config(max_age_days: int = DEFAULT_TTL_DAYS) -> dict | None:
    """Return cached Algolia config if present and not expired, else None."""
    if not ALGOLIA_CACHE_FILE.exists():
        return None
    try:
        data = json.loads(ALGOLIA_CACHE_FILE.read_text())
        index_name = data.get("index_name", "")
        discovered_at_str = data.get("discovered_at", "")
        if not index_name or not discovered_at_str:
            return None
        discovered_at = datetime.fromisoformat(discovered_at_str)
        if datetime.now(tz=timezone.utc) - discovered_at > timedelta(days=max_age_days):
            return None
        return data
    except Exception:
        return None


def save_cached_config(config: dict) -> None:
    """Write Algolia config + timestamp to cache file."""
    ATK_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        **config,
        "discovered_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    ALGOLIA_CACHE_FILE.write_text(json.dumps(data, indent=2))


def get_algolia_config(force_refresh: bool = False, verbose: bool = False) -> dict:
    """Return Algolia config dict with keys: app_id, api_key, index_name.

    Resolution order:
    1. Cache file (if present, not expired, and has app_id + api_key)
    2. Auto-discover from ATK search page → write cache
    3. Fallback to ALGOLIA_INDEX constant for index name; raise if keys missing
    """
    if not force_refresh:
        cached = load_cached_config()
        if cached and cached.get("app_id") and cached.get("api_key"):
            return cached

    if verbose:
        from rich import print as rprint
        rprint("[dim]Refreshing Algolia config...[/dim]")

    try:
        config = discover_algolia_config()
        if not config.get("app_id") or not config.get("api_key"):
            raise ValueError("Could not extract Algolia credentials from ATK search page.")
        save_cached_config(config)
        return config
    except Exception as exc:
        # Fall back to cache even if expired
        cached = load_cached_config(max_age_days=365)
        if cached and cached.get("app_id") and cached.get("api_key"):
            return cached
        raise ValueError(
            f"Algolia config discovery failed and no cache available: {exc}\n"
            "Run 'atk config refresh-algolia' to retry."
        ) from exc


def get_index(force_refresh: bool = False, verbose: bool = False) -> str:
    """Return the Algolia index name."""
    if not force_refresh:
        cached = load_cached_config()
        if cached and cached.get("index_name"):
            return cached["index_name"]

    if verbose:
        from rich import print as rprint
        rprint("[dim]Refreshing Algolia index...[/dim]")

    try:
        config = get_algolia_config(force_refresh=force_refresh, verbose=False)
        return config["index_name"]
    except Exception:
        return ALGOLIA_INDEX
