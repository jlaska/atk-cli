"""Tests for atk_cli.auth — token persistence, security, and credential resolution."""

import json
import os

import pytest

# Save real function references at import time, before autouse patches them.
from atk_cli.auth import get_tokens as _real_get_tokens
from atk_cli.auth import (
    _load_tokens,
    _save_tokens,
    clear_tokens,
    resolve_credentials,
    save_tokens,
)
from atk_cli.exceptions import AuthenticationError, ConfigError


@pytest.fixture
def tmp_tokens(tmp_path, monkeypatch):
    """Redirect TOKENS_FILE + ATK_DIR to tmp_path and restore real get_tokens."""
    tokens_file = tmp_path / "tokens.json"
    monkeypatch.setattr("atk_cli.auth.TOKENS_FILE", tokens_file)
    monkeypatch.setattr("atk_cli.auth.ATK_DIR", tmp_path)
    # Restore the real get_tokens (autouse fixture patches it to a lambda)
    monkeypatch.setattr("atk_cli.auth.get_tokens", _real_get_tokens)
    return tokens_file


# ── save_tokens / get_tokens round-trip ───────────────────────────────────────

def test_save_and_get_roundtrip(tmp_tokens):
    """Tokens saved for a profile can be retrieved for the same profile."""
    save_tokens("access123", "refresh456", profile="default")
    result = _real_get_tokens(profile="default")
    assert result["access_token"] == "access123"
    assert result["refresh_token"] == "refresh456"


def test_get_missing_profile_raises(tmp_tokens):
    """get_tokens for an unknown profile raises AuthenticationError."""
    with pytest.raises(AuthenticationError, match="atk login"):
        _real_get_tokens(profile="ghost")


def test_get_empty_file(tmp_tokens):
    """Empty tokens dict (file with {}) raises AuthenticationError."""
    tmp_tokens.write_text("{}")
    with pytest.raises(AuthenticationError):
        _real_get_tokens(profile="default")


# ── clear_tokens ──────────────────────────────────────────────────────────────

def test_clear_tokens(tmp_tokens):
    """clear_tokens removes the profile entry from the file."""
    save_tokens("access", "refresh", profile="default")
    clear_tokens(profile="default")
    data = json.loads(tmp_tokens.read_text())
    assert "default" not in data


def test_clear_nonexistent_noop(tmp_tokens):
    """clear_tokens on a non-existent profile does not raise."""
    tmp_tokens.write_text("{}")
    clear_tokens(profile="ghost")  # should not raise


# ── security: file permissions ────────────────────────────────────────────────

def test_file_permissions_0600(tmp_tokens):
    """Tokens file is created with mode 0o600 (owner read/write only)."""
    save_tokens("access", "refresh", profile="default")
    mode = oct(tmp_tokens.stat().st_mode)[-4:]
    assert mode == "0600", f"Expected 0600, got {mode}"


# ── directory creation ────────────────────────────────────────────────────────

def test_save_creates_directory(tmp_path, monkeypatch):
    """save_tokens creates the parent directory when it doesn't exist."""
    new_dir = tmp_path / "nested" / "atk"
    tokens_file = new_dir / "tokens.json"
    monkeypatch.setattr("atk_cli.auth.TOKENS_FILE", tokens_file)
    monkeypatch.setattr("atk_cli.auth.ATK_DIR", new_dir)
    monkeypatch.setattr("atk_cli.auth.get_tokens", _real_get_tokens)
    save_tokens("access", "refresh", profile="default")
    assert tokens_file.exists()


# ── multi-profile isolation ───────────────────────────────────────────────────

def test_multiple_profiles(tmp_tokens):
    """Multiple profiles are stored and retrieved independently."""
    save_tokens("access_a", "refresh_a", profile="profileA")
    save_tokens("access_b", "refresh_b", profile="profileB")
    a = _real_get_tokens(profile="profileA")
    b = _real_get_tokens(profile="profileB")
    assert a["access_token"] == "access_a"
    assert b["access_token"] == "access_b"


# ── corrupt JSON ──────────────────────────────────────────────────────────────

def test_corrupt_json(tmp_tokens):
    """Corrupt tokens file causes get_tokens to raise AuthenticationError."""
    tmp_tokens.write_text("{not valid json")
    # _load_tokens swallows JSONDecodeError → returns {} → get_tokens raises
    with pytest.raises(AuthenticationError):
        _real_get_tokens(profile="default")


# ── resolve_credentials ───────────────────────────────────────────────────────

def test_resolve_credentials_env_vars(monkeypatch):
    """env vars ATK_EMAIL and ATK_PASSWORD are returned directly."""
    monkeypatch.setenv("ATK_EMAIL", "env@example.com")
    monkeypatch.setenv("ATK_PASSWORD", "envpass")
    email, password = resolve_credentials()
    assert email == "env@example.com"
    assert password == "envpass"


def test_resolve_credentials_config_fallback(monkeypatch):
    """When env vars absent, email falls back to profile config."""
    monkeypatch.delenv("ATK_EMAIL", raising=False)
    monkeypatch.delenv("ATK_PASSWORD", raising=False)
    monkeypatch.setattr(
        "atk_cli.config.get_profile",
        lambda *a, **kw: {"email": "config@example.com", "site_key": "atk"},
    )
    email, password = resolve_credentials()
    assert email == "config@example.com"
    assert password == ""


def test_resolve_credentials_nothing(monkeypatch):
    """When no env vars and config raises, returns ('', '')."""
    monkeypatch.delenv("ATK_EMAIL", raising=False)
    monkeypatch.delenv("ATK_PASSWORD", raising=False)
    monkeypatch.setattr(
        "atk_cli.config.get_profile",
        lambda *a, **kw: (_ for _ in ()).throw(ConfigError("no profile")),
    )
    email, password = resolve_credentials()
    assert email == ""
    assert password == ""
