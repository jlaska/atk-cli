"""Tests for atk_cli.config — profile management, deep-merge, and persistence."""

import json

import pytest

# Save real function at import time, before the autouse fixture patches it.
from atk_cli.config import get_active_profile_name as _real_get_active_profile_name
from atk_cli.config import (
    create_or_update_profile,
    get_profile,
    list_profiles,
    load,
    save,
    set_active_profile,
)
from atk_cli.exceptions import ConfigError


@pytest.fixture
def tmp_config(tmp_path, monkeypatch):
    """Redirect CONFIG_FILE and ATK_DIR to tmp_path for each test."""
    config_file = tmp_path / "config.json"
    monkeypatch.setattr("atk_cli.config.CONFIG_FILE", config_file)
    monkeypatch.setattr("atk_cli.config.ATK_DIR", tmp_path)
    return config_file


# ── load ──────────────────────────────────────────────────────────────────────

def test_load_missing_file_returns_defaults(tmp_config):
    """First-run: missing file returns default config with 'default' profile."""
    cfg = load()
    assert cfg["active_profile"] == "default"
    assert "default" in cfg["profiles"]
    assert cfg["profiles"]["default"]["site_key"] == "atk"


def test_load_preserves_user_data(tmp_config):
    """Deep-merge does not clobber user-added profiles."""
    raw = {
        "active_profile": "work",
        "profiles": {
            "default": {"email": "home@example.com", "site_key": "atk"},
            "work": {"email": "work@corp.com", "site_key": "cio"},
        },
    }
    tmp_config.write_text(json.dumps(raw))
    cfg = load()
    assert "work" in cfg["profiles"]
    assert cfg["profiles"]["work"]["email"] == "work@corp.com"
    assert cfg["profiles"]["default"]["email"] == "home@example.com"


def test_load_corrupt_json_raises(tmp_config):
    """Malformed JSON raises ConfigError."""
    tmp_config.write_text("{bad json!!!")
    from atk_cli.exceptions import ConfigError
    with pytest.raises(ConfigError, match="Malformed"):
        load()


# ── save ──────────────────────────────────────────────────────────────────────

def test_save_creates_directory(tmp_path, monkeypatch):
    """save() creates the parent directory if it doesn't exist."""
    new_dir = tmp_path / "nested"
    config_file = new_dir / "config.json"
    monkeypatch.setattr("atk_cli.config.CONFIG_FILE", config_file)
    monkeypatch.setattr("atk_cli.config.ATK_DIR", new_dir)
    cfg = load()
    save(cfg)
    assert config_file.exists()


# ── get_active_profile_name ───────────────────────────────────────────────────

def test_get_active_profile_name_reads_cfg():
    """Returns active_profile from provided cfg dict."""
    cfg = {"active_profile": "myprofile", "profiles": {}}
    result = _real_get_active_profile_name(cfg)
    assert result == "myprofile"


def test_get_active_profile_name_defaults():
    """Returns 'default' when active_profile key is missing."""
    result = _real_get_active_profile_name({})
    assert result == "default"


# ── get_profile ───────────────────────────────────────────────────────────────

def test_get_profile_active(tmp_config):
    """get_profile with name=None uses get_active_profile_name (mocked → 'default')."""
    cfg = load()
    profile = get_profile(cfg=cfg)  # name=None, autouse makes it resolve to 'default'
    assert "site_key" in profile


def test_get_profile_by_name(tmp_config):
    """get_profile with explicit name returns correct profile."""
    raw = {
        "active_profile": "default",
        "profiles": {
            "default": {"email": "", "site_key": "atk"},
            "work": {"email": "w@corp.com", "site_key": "cio"},
        },
    }
    tmp_config.write_text(json.dumps(raw))
    cfg = load()
    profile = get_profile(name="work", cfg=cfg)
    assert profile["email"] == "w@corp.com"


def test_get_profile_nonexistent_raises(tmp_config):
    """get_profile for a missing name raises ConfigError with help text."""
    cfg = load()
    with pytest.raises(ConfigError, match="not found"):
        get_profile(name="ghost", cfg=cfg)


# ── set_active_profile ────────────────────────────────────────────────────────

def test_set_active_profile_success(tmp_config):
    """set_active_profile persists the new active profile name."""
    # Create the 'work' profile first so set can succeed
    create_or_update_profile("work", email="w@example.com")
    set_active_profile("work")
    cfg = load()
    assert cfg["active_profile"] == "work"


def test_set_active_profile_nonexistent_raises(tmp_config):
    """set_active_profile for a missing profile name raises ConfigError."""
    with pytest.raises(ConfigError, match="does not exist"):
        set_active_profile("ghost")


# ── create_or_update_profile ──────────────────────────────────────────────────

def test_create_or_update_new(tmp_config):
    """create_or_update_profile creates a brand-new profile."""
    create_or_update_profile("work", email="w@corp.com", site_key="cio")
    cfg = load()
    assert "work" in cfg["profiles"]
    assert cfg["profiles"]["work"]["email"] == "w@corp.com"
    assert cfg["profiles"]["work"]["site_key"] == "cio"


def test_create_or_update_preserves_existing(tmp_config):
    """Passing empty string for email preserves the existing email value."""
    create_or_update_profile("work", email="first@corp.com", site_key="cio")
    # Passing email="" should keep the existing email (falsy → uses existing)
    create_or_update_profile("work", email="", site_key="cio")
    cfg = load()
    assert cfg["profiles"]["work"]["email"] == "first@corp.com"
    assert cfg["profiles"]["work"]["site_key"] == "cio"


# ── list_profiles ─────────────────────────────────────────────────────────────

def test_list_profiles(tmp_config):
    """list_profiles returns all profile names from the config."""
    create_or_update_profile("work", email="w@corp.com")
    create_or_update_profile("personal")
    names = list_profiles()
    assert "default" in names
    assert "work" in names
    assert "personal" in names
