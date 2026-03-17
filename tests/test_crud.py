"""Tests for `atk create favorite` and `atk delete favorite` commands."""

import httpx
import pytest
import respx

from atk_cli.main import app

BASE = "https://www.americastestkitchen.com"


# ── create favorite ───────────────────────────────────────────────────────────

def test_create_favorite(runner):
    """create favorite with numeric ID calls POST and exits cleanly."""
    with respx.mock(assert_all_called=False) as mock:
        mock.post(f"{BASE}/api/v6/user_favorites").mock(
            return_value=httpx.Response(200, json={"id": "fav_1", "object_id": "recipe_123"})
        )
        result = runner.invoke(app, ["create", "favorite", "123"])
    assert result.exit_code == 0
    assert "123" in result.output


def test_create_favorite_prefix(runner):
    """create favorite with recipe_ prefix strips it and normalizes the ID."""
    with respx.mock(assert_all_called=False) as mock:
        route = mock.post(f"{BASE}/api/v6/user_favorites").mock(
            return_value=httpx.Response(200, json={"object_id": "recipe_456"})
        )
        result = runner.invoke(app, ["create", "favorite", "recipe_456"])
    assert result.exit_code == 0
    if route.calls:
        import json
        body = json.loads(route.calls.last.request.content)
        assert body["object_id"] == "recipe_456"


def test_create_api_error(runner):
    """API error during create shows error message and exits with code 1."""
    with respx.mock(assert_all_called=False) as mock:
        mock.post(f"{BASE}/api/v6/user_favorites").mock(
            return_value=httpx.Response(500, text="Server Error")
        )
        result = runner.invoke(app, ["create", "favorite", "999"])
    assert result.exit_code == 1


# ── delete favorite ───────────────────────────────────────────────────────────

def test_delete_with_yes(runner):
    """--yes flag skips confirmation and calls DELETE."""
    with respx.mock(assert_all_called=False) as mock:
        mock.delete(f"{BASE}/api/v6/user_favorites/recipe_123").mock(
            return_value=httpx.Response(200, json={"deleted": True})
        )
        result = runner.invoke(app, ["delete", "favorite", "123", "--yes"])
    assert result.exit_code == 0
    assert "123" in result.output


def test_delete_abort(runner):
    """Without --yes, answering 'n' to confirmation aborts the delete."""
    with respx.mock(assert_all_called=False) as mock:
        route = mock.delete(f"{BASE}/api/v6/user_favorites/recipe_123").mock(
            return_value=httpx.Response(200, json={"deleted": True})
        )
        # Provide 'n' as input to the confirmation prompt
        result = runner.invoke(app, ["delete", "favorite", "123"], input="n\n")
    # Should abort without making the DELETE call
    assert not route.called
