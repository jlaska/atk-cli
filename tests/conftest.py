"""Shared fixtures: auth/algolia/config bypass, fake JWT, CliRunner."""

import base64
import json
import time

import pytest
from typer.testing import CliRunner

from atk_cli.client import ATKClient


# ── Fake JWT ──────────────────────────────────────────────────────────────────

def _make_fake_jwt(exp_offset: int = 86400 * 365) -> str:
    """Return a valid 3-part base64-encoded JWT with exp set in the future."""
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": "test_user", "exp": int(time.time()) + exp_offset}).encode()
    ).rstrip(b"=").decode()
    return f"{header}.{payload}.fakesignature"


FAKE_JWT = _make_fake_jwt()
FAKE_REFRESH = "fake-refresh-token"

FAKE_TOKENS = {
    "access_token": FAKE_JWT,
    "refresh_token": FAKE_REFRESH,
}

FAKE_ALGOLIA_CONFIG = {
    "app_id": "TESTAPPID00",
    "api_key": "a" * 32,
    "index_name": "test_index",
}


# ── Autouse fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_auth(monkeypatch):
    """Bypass real token storage and expiry checking in all tests."""
    monkeypatch.setattr("atk_cli.auth.get_tokens", lambda *a, **kw: FAKE_TOKENS)
    monkeypatch.setattr("atk_cli.auth.is_token_expired", lambda *a, **kw: False)


@pytest.fixture(autouse=True)
def mock_algolia_config(monkeypatch):
    """Return static Algolia config in all tests (no network/cache)."""
    monkeypatch.setattr(
        "atk_cli.algolia.get_algolia_config",
        lambda *a, **kw: FAKE_ALGOLIA_CONFIG,
    )


@pytest.fixture(autouse=True)
def mock_config(monkeypatch):
    """Return a static active profile name in all tests."""
    monkeypatch.setattr(
        "atk_cli.config.get_active_profile_name",
        lambda *a, **kw: "default",
    )


# ── Non-autouse fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def client():
    """Return an ATKClient bound to the default profile."""
    c = ATKClient(profile="default")
    yield c
    c.close()


@pytest.fixture
def runner():
    """Return a CliRunner for invoking the CLI app."""
    return CliRunner()
