"""Tests for `atk config *` commands."""

import base64
import json

import pytest

from atk_cli.main import app
from atk_cli.exceptions import ConfigError


@pytest.fixture
def tmp_config(tmp_path, monkeypatch):
    """Redirect CONFIG_FILE and ATK_DIR to tmp_path for each test."""
    config_file = tmp_path / "config.json"
    monkeypatch.setattr("atk_cli.config.CONFIG_FILE", config_file)
    monkeypatch.setattr("atk_cli.config.ATK_DIR", tmp_path)
    return config_file


def _make_jwt_with_email(email: str) -> str:
    import time
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": email, "email": email, "exp": int(time.time()) + 86400}).encode()
    ).rstrip(b"=").decode()
    return f"{header}.{payload}.fakesig"


def test_view(runner, tmp_config):
    """Shows config path, active profile, and profile table."""
    raw = {
        "active_profile": "default",
        "profiles": {
            "default": {"email": "admin@example.com", "site_key": "atk"},
        },
    }
    tmp_config.write_text(json.dumps(raw))

    result = runner.invoke(app, ["config", "view"])

    assert result.exit_code == 0
    assert "default" in result.output
    assert "admin@example.com" in result.output


def test_view_jwt_email_backfill(runner, tmp_config, monkeypatch):
    """When profile has no email, backfills from JWT sub claim."""
    raw = {
        "active_profile": "default",
        "profiles": {
            "default": {"email": "", "site_key": "atk"},
        },
    }
    tmp_config.write_text(json.dumps(raw))
    jwt = _make_jwt_with_email("jwt@example.com")
    monkeypatch.setattr(
        "atk_cli.auth.get_tokens",
        lambda *a, **kw: {"access_token": jwt, "refresh_token": "x"},
    )

    result = runner.invoke(app, ["config", "view"])

    assert result.exit_code == 0
    assert "jwt@example.com" in result.output


def test_get_profiles(runner, tmp_config):
    """Lists profiles with (active) marker for the current active profile."""
    raw = {
        "active_profile": "default",
        "profiles": {
            "default": {"email": "", "site_key": "atk"},
            "work": {"email": "w@corp.com", "site_key": "cio"},
        },
    }
    tmp_config.write_text(json.dumps(raw))

    result = runner.invoke(app, ["config", "get-profiles"])

    assert result.exit_code == 0
    assert "(active)" in result.output
    assert "default" in result.output
    assert "work" in result.output


def test_use_profile_success(runner, tmp_config):
    """Switches active profile to an existing profile."""
    raw = {
        "active_profile": "default",
        "profiles": {
            "default": {"email": "", "site_key": "atk"},
            "work": {"email": "w@corp.com", "site_key": "cio"},
        },
    }
    tmp_config.write_text(json.dumps(raw))

    result = runner.invoke(app, ["config", "use-profile", "work"])

    assert result.exit_code == 0
    assert "work" in result.output


def test_use_profile_nonexistent(runner, tmp_config):
    """Switching to a non-existent profile exits with code 1."""
    raw = {
        "active_profile": "default",
        "profiles": {
            "default": {"email": "", "site_key": "atk"},
        },
    }
    tmp_config.write_text(json.dumps(raw))

    result = runner.invoke(app, ["config", "use-profile", "ghost"])

    assert result.exit_code == 1
    assert "Error" in result.output


def test_refresh_algolia_success(runner, tmp_config):
    """Calls get_algolia_config with force_refresh=True and shows result."""
    result = runner.invoke(app, ["config", "refresh-algolia"])

    assert result.exit_code == 0
    assert "TESTAPPID00" in result.output


def test_refresh_algolia_failure(runner, tmp_config, monkeypatch):
    """Discovery error exits with code 1."""
    def _raise(*a, **kw):
        raise RuntimeError("Discovery failed")

    monkeypatch.setattr("atk_cli.algolia.get_algolia_config", _raise)

    result = runner.invoke(app, ["config", "refresh-algolia"])

    assert result.exit_code == 1
    assert "Error" in result.output


def test_set_profile(runner, tmp_config):
    """Creates a profile with --email flag and shows success message."""
    result = runner.invoke(
        app,
        ["config", "set-profile", "newprofile", "--email", "new@example.com"],
    )

    assert result.exit_code == 0
    assert "newprofile" in result.output
