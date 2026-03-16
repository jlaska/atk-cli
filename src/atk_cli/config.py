"""Profile management backed by ~/.atk/config.json."""

import json
from typing import Any

from .constants import ATK_DIR, CONFIG_FILE, DEFAULT_SITE_KEY
from .exceptions import ConfigError

DEFAULT_CONFIG: dict[str, Any] = {
    "active_profile": "default",
    "profiles": {
        "default": {
            "email": "",
            "site_key": DEFAULT_SITE_KEY,
        }
    },
}


def _load_raw() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text())
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Malformed config file {CONFIG_FILE}: {exc}") from exc


def _save_raw(data: dict[str, Any]) -> None:
    ATK_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2))


def load() -> dict[str, Any]:
    raw = _load_raw()
    # Deep-merge defaults
    cfg = {**DEFAULT_CONFIG, **raw}
    cfg.setdefault("profiles", {})
    if "default" not in cfg["profiles"]:
        cfg["profiles"]["default"] = DEFAULT_CONFIG["profiles"]["default"].copy()
    return cfg


def save(cfg: dict[str, Any]) -> None:
    _save_raw(cfg)


def get_active_profile_name(cfg: dict[str, Any] | None = None) -> str:
    if cfg is None:
        cfg = load()
    return cfg.get("active_profile", "default")


def get_profile(name: str | None = None, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    if cfg is None:
        cfg = load()
    if name is None:
        name = get_active_profile_name(cfg)
    profiles = cfg.get("profiles", {})
    if name not in profiles:
        raise ConfigError(f"Profile '{name}' not found. Use 'atk config get-profiles' to list profiles.")
    return profiles[name]


def set_active_profile(name: str) -> None:
    cfg = load()
    if name not in cfg.get("profiles", {}):
        raise ConfigError(f"Profile '{name}' does not exist.")
    cfg["active_profile"] = name
    save(cfg)


def create_or_update_profile(name: str, email: str = "", site_key: str = DEFAULT_SITE_KEY) -> None:
    cfg = load()
    cfg.setdefault("profiles", {})
    existing = cfg["profiles"].get(name, {})
    cfg["profiles"][name] = {
        **existing,
        "email": email or existing.get("email", ""),
        "site_key": site_key or existing.get("site_key", DEFAULT_SITE_KEY),
    }
    save(cfg)


def list_profiles(cfg: dict[str, Any] | None = None) -> list[str]:
    if cfg is None:
        cfg = load()
    return list(cfg.get("profiles", {}).keys())
