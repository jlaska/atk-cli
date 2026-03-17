"""Tests for `atk login` and `atk logout` commands."""

import httpx
import pytest
import respx

from atk_cli.main import app

BASE = "https://www.americastestkitchen.com"
LOGIN_RESPONSE = {"accessToken": "test-access-token", "refreshToken": "test-refresh-token"}


def test_login_with_flags(runner, monkeypatch):
    """Login with --email and --password flags succeeds."""
    monkeypatch.setattr("atk_cli.commands.login.save_tokens", lambda *a, **kw: None)
    monkeypatch.setattr("atk_cli.config.create_or_update_profile", lambda *a, **kw: None)

    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE}/sign_in").mock(return_value=httpx.Response(200, text="ok"))
        mock.post(f"{BASE}/api/v6/sessions/login").mock(
            return_value=httpx.Response(200, json=LOGIN_RESPONSE)
        )
        result = runner.invoke(
            app, ["login", "--email", "test@example.com", "--password", "secret"]
        )

    assert result.exit_code == 0
    assert "Logged in successfully" in result.output


def test_login_saves_tokens(runner, monkeypatch):
    """Verifies save_tokens is called with the access token from the response."""
    saved = {}

    def capture_save(access, refresh, profile=None):
        saved["access"] = access
        saved["refresh"] = refresh

    monkeypatch.setattr("atk_cli.commands.login.save_tokens", capture_save)
    monkeypatch.setattr("atk_cli.config.create_or_update_profile", lambda *a, **kw: None)

    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE}/sign_in").mock(return_value=httpx.Response(200, text="ok"))
        mock.post(f"{BASE}/api/v6/sessions/login").mock(
            return_value=httpx.Response(200, json=LOGIN_RESPONSE)
        )
        result = runner.invoke(
            app, ["login", "--email", "test@example.com", "--password", "secret"]
        )

    assert result.exit_code == 0
    assert saved["access"] == "test-access-token"
    assert saved["refresh"] == "test-refresh-token"


def test_login_no_access_token(runner, monkeypatch):
    """Empty accessToken in response → exit 1."""
    monkeypatch.setattr("atk_cli.commands.login.save_tokens", lambda *a, **kw: None)

    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE}/sign_in").mock(return_value=httpx.Response(200, text="ok"))
        mock.post(f"{BASE}/api/v6/sessions/login").mock(
            return_value=httpx.Response(200, json={"accessToken": "", "refreshToken": ""})
        )
        result = runner.invoke(
            app, ["login", "--email", "test@example.com", "--password", "secret"]
        )

    assert result.exit_code == 1
    assert "no access token" in result.output.lower()


def test_login_api_error(runner, monkeypatch):
    """ATKError from client.login() → exit 1 with failure message."""
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE}/sign_in").mock(return_value=httpx.Response(200, text="ok"))
        mock.post(f"{BASE}/api/v6/sessions/login").mock(
            return_value=httpx.Response(401, json={"error": "Invalid credentials"})
        )
        result = runner.invoke(
            app, ["login", "--email", "test@example.com", "--password", "wrongpass"]
        )

    assert result.exit_code == 1
    assert "Login failed" in result.output


def test_login_persists_email(runner, monkeypatch):
    """Email is saved to profile config after successful login."""
    created = {}

    def capture_create(name, email="", site_key="atk"):
        created["name"] = name
        created["email"] = email

    monkeypatch.setattr("atk_cli.commands.login.save_tokens", lambda *a, **kw: None)
    monkeypatch.setattr("atk_cli.config.create_or_update_profile", capture_create)

    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE}/sign_in").mock(return_value=httpx.Response(200, text="ok"))
        mock.post(f"{BASE}/api/v6/sessions/login").mock(
            return_value=httpx.Response(200, json=LOGIN_RESPONSE)
        )
        result = runner.invoke(
            app, ["login", "--email", "persist@example.com", "--password", "secret"]
        )

    assert result.exit_code == 0
    assert created.get("email") == "persist@example.com"


def test_logout(runner, monkeypatch):
    """Logout calls clear_tokens and shows success message."""
    cleared = {}

    def capture_clear(profile=None):
        cleared["profile"] = profile

    monkeypatch.setattr("atk_cli.commands.login.clear_tokens", capture_clear)

    result = runner.invoke(app, ["logout"])

    assert result.exit_code == 0
    assert "Logged out" in result.output
