"""Tests for JWT functions in atk_cli.auth."""

import base64
import json
import time

import pytest

from atk_cli.auth import _decode_jwt_payload, is_token_expired


def _make_jwt(payload: dict) -> str:
    """Build a minimal 3-part JWT with the given payload (no real signature)."""
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=").decode()
    encoded_payload = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).rstrip(b"=").decode()
    return f"{header}.{encoded_payload}.fakesig"


# ── _decode_jwt_payload ───────────────────────────────────────────────────────

def test_decode_jwt_payload_valid():
    token = _make_jwt({"sub": "user123", "exp": 9999999999})
    result = _decode_jwt_payload(token)
    assert result["sub"] == "user123"
    assert result["exp"] == 9999999999


def test_decode_jwt_payload_invalid():
    assert _decode_jwt_payload("not-a-jwt") == {}


def test_decode_jwt_payload_two_parts():
    assert _decode_jwt_payload("a.b") == {}


def test_decode_jwt_payload_bad_base64():
    assert _decode_jwt_payload("header.!!!.sig") == {}


# ── is_token_expired ──────────────────────────────────────────────────────────

def test_is_token_expired_future():
    token = _make_jwt({"exp": int(time.time()) + 86400})
    assert is_token_expired(token) is False


def test_is_token_expired_past():
    token = _make_jwt({"exp": int(time.time()) - 3600})
    assert is_token_expired(token) is True


def test_is_token_expired_within_buffer():
    # exp 30 seconds from now, default buffer is 60 → should be expired
    token = _make_jwt({"exp": int(time.time()) + 30})
    assert is_token_expired(token, buffer_seconds=60) is True


def test_is_token_expired_garbage():
    assert is_token_expired("garbage-string") is True


def test_is_token_expired_no_exp_claim():
    token = _make_jwt({"sub": "user"})  # no exp field
    assert is_token_expired(token) is True
