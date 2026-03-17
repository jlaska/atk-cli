"""Tests for `atk auth status` command."""

import base64
import json
import time

import pytest

from atk_cli.main import app
from atk_cli.exceptions import AuthenticationError, ConfigError


def _make_jwt(payload: dict) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=").decode()
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"{header}.{encoded}.fakesig"


@pytest.fixture
def fake_cfg():
    return {
        "active_profile": "default",
        "profiles": {
            "default": {"email": "user@example.com", "site_key": "atk"},
        },
    }


@pytest.fixture
def fake_profile(fake_cfg):
    return fake_cfg["profiles"]["default"]


def test_status_valid_token(runner, fake_cfg, fake_profile, monkeypatch):
    """Happy path: shows profile, email, and VALID status."""
    monkeypatch.setattr("atk_cli.config.load", lambda: fake_cfg)
    monkeypatch.setattr("atk_cli.config.get_profile", lambda name=None, cfg=None: fake_profile)

    result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 0
    assert "VALID" in result.output
    assert "default" in result.output
    assert "user@example.com" in result.output


def test_status_expired_token(runner, fake_cfg, fake_profile, monkeypatch):
    """Expired token shows EXPIRED status."""
    monkeypatch.setattr("atk_cli.config.load", lambda: fake_cfg)
    monkeypatch.setattr("atk_cli.config.get_profile", lambda name=None, cfg=None: fake_profile)
    monkeypatch.setattr("atk_cli.commands.auth_cmd.is_token_expired", lambda *a, **kw: True)

    result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 0
    assert "EXPIRED" in result.output


def test_status_email_from_jwt(runner, monkeypatch):
    """Email fallback: when config has no email, use JWT email claim."""
    jwt = _make_jwt({"sub": "fallback_user", "email": "user@jwt.com", "exp": int(time.time()) + 86400})
    monkeypatch.setattr("atk_cli.auth.get_tokens", lambda *a, **kw: {"access_token": jwt, "refresh_token": "x"})
    cfg = {
        "active_profile": "default",
        "profiles": {"default": {"email": "", "site_key": "atk"}},
    }
    monkeypatch.setattr("atk_cli.config.load", lambda: cfg)
    monkeypatch.setattr("atk_cli.config.get_profile", lambda name=None, cfg=None: cfg["profiles"]["default"])

    result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 0
    assert "user@jwt.com" in result.output


def test_status_no_tokens(runner, fake_cfg, fake_profile, monkeypatch):
    """When not logged in, shows help message to run atk login."""
    monkeypatch.setattr("atk_cli.config.load", lambda: fake_cfg)
    monkeypatch.setattr("atk_cli.config.get_profile", lambda name=None, cfg=None: fake_profile)

    def _raise(*a, **kw):
        raise AuthenticationError("No tokens found")

    monkeypatch.setattr("atk_cli.auth.get_tokens", _raise)

    result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 0
    assert "atk login" in result.output


def test_status_profile_not_found(runner, fake_cfg, monkeypatch):
    """Unknown profile shows warning about profile not found in config."""
    monkeypatch.setattr("atk_cli.config.load", lambda: fake_cfg)

    def _raise(*a, **kw):
        raise ConfigError("not found")

    monkeypatch.setattr("atk_cli.config.get_profile", _raise)

    result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 0
    assert "not found" in result.output.lower()


def test_status_token_preview(runner, fake_cfg, fake_profile, monkeypatch):
    """Token preview shows beginning of token with trailing ellipsis."""
    monkeypatch.setattr("atk_cli.config.load", lambda: fake_cfg)
    monkeypatch.setattr("atk_cli.config.get_profile", lambda name=None, cfg=None: fake_profile)

    result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 0
    assert "..." in result.output
