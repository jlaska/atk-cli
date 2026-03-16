"""Credential resolution, token persistence, and JWT expiry checking."""

import base64
import json
import os
import time
from typing import Any

from .constants import ATK_DIR, TOKENS_FILE
from .exceptions import AuthenticationError, ConfigError
from . import config as cfg_mod


def _load_tokens() -> dict[str, Any]:
    if not TOKENS_FILE.exists():
        return {}
    try:
        return json.loads(TOKENS_FILE.read_text())
    except json.JSONDecodeError:
        return {}


def _save_tokens(tokens: dict[str, Any]) -> None:
    ATK_DIR.mkdir(parents=True, exist_ok=True)
    TOKENS_FILE.write_text(json.dumps(tokens, indent=2))
    TOKENS_FILE.chmod(0o600)


def get_tokens(profile: str | None = None) -> dict[str, str]:
    """Return stored tokens for profile. Raises AuthenticationError if missing."""
    if profile is None:
        profile = cfg_mod.get_active_profile_name()
    tokens = _load_tokens()
    profile_tokens = tokens.get(profile)
    if not profile_tokens:
        raise AuthenticationError(
            f"No tokens for profile '{profile}'. Run 'atk login' first."
        )
    return profile_tokens


def save_tokens(access_token: str, refresh_token: str, profile: str | None = None) -> None:
    if profile is None:
        profile = cfg_mod.get_active_profile_name()
    tokens = _load_tokens()
    tokens[profile] = {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }
    _save_tokens(tokens)


def clear_tokens(profile: str | None = None) -> None:
    if profile is None:
        profile = cfg_mod.get_active_profile_name()
    tokens = _load_tokens()
    tokens.pop(profile, None)
    _save_tokens(tokens)


def _decode_jwt_exp(token: str) -> int | None:
    """Decode JWT payload (no verification) and return exp claim or None."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        # Add padding
        payload_b64 = parts[1] + "=="
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return payload.get("exp")
    except Exception:
        return None


def is_token_expired(token: str, buffer_seconds: int = 60) -> bool:
    """Return True if token is expired or expiry unknown."""
    exp = _decode_jwt_exp(token)
    if exp is None:
        return True
    return time.time() >= (exp - buffer_seconds)


def resolve_credentials(profile_name: str | None = None) -> tuple[str, str]:
    """Return (email, password) from env vars or config profile."""
    email = os.environ.get("ATK_EMAIL", "")
    password = os.environ.get("ATK_PASSWORD", "")
    if email and password:
        return email, password

    try:
        profile = cfg_mod.get_profile(profile_name)
        email = email or profile.get("email", "")
    except ConfigError:
        pass

    return email, password
