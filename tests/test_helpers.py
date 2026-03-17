"""Tests for pure helper functions in atk_cli.commands.describe."""

import pytest

from atk_cli.commands.describe import _format_ingredient, _parse_iso_duration, _strip_html


# ── _strip_html ───────────────────────────────────────────────────────────────

def test_strip_html_tags():
    assert _strip_html("<b>hello</b> world") == "hello world"


def test_strip_html_empty():
    assert _strip_html("") == ""


def test_strip_html_none():
    assert _strip_html(None) == ""


def test_strip_html_nested():
    assert _strip_html("<p><em>italic</em> and <strong>bold</strong></p>") == "italic and bold"


# ── _parse_iso_duration ───────────────────────────────────────────────────────

def test_parse_iso_duration_full():
    assert _parse_iso_duration("PT1H30M") == "1 hr 30 mins"


def test_parse_iso_duration_hours_plural():
    assert _parse_iso_duration("PT2H") == "2 hrs"


def test_parse_iso_duration_hour_singular():
    assert _parse_iso_duration("PT1H") == "1 hr"


def test_parse_iso_duration_minutes():
    assert _parse_iso_duration("PT45M") == "45 mins"


def test_parse_iso_duration_seconds():
    assert _parse_iso_duration("PT30S") == "30 secs"


def test_parse_iso_duration_empty():
    assert _parse_iso_duration("") == ""


def test_parse_iso_duration_invalid():
    assert _parse_iso_duration("PLACEHOLDER") == ""


def test_parse_iso_duration_hms():
    assert _parse_iso_duration("PT1H30M15S") == "1 hr 30 mins 15 secs"


# ── _format_ingredient ────────────────────────────────────────────────────────

def test_format_ingredient_full():
    item = {
        "fields": {
            "qty": "2",
            "preText": "large",
            "postText": "peeled",
            "ingredient": {"fields": {"title": "carrots"}},
        }
    }
    result = _format_ingredient(item)
    assert "2" in result
    assert "large" in result
    assert "carrots" in result
    assert "peeled" in result


def test_format_ingredient_string_ingredient():
    item = {
        "fields": {
            "qty": "1",
            "preText": "",
            "postText": "",
            "ingredient": "plain string ingredient",
        }
    }
    result = _format_ingredient(item)
    assert "plain string ingredient" in result


def test_format_ingredient_empty():
    item = {
        "fields": {
            "qty": "",
            "preText": "",
            "postText": "",
            "ingredient": {},
        }
    }
    assert _format_ingredient(item) == ""
