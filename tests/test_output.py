"""Tests for _get and _parse_jsonpath_expr in atk_cli.output."""

import pytest

from atk_cli.output import _get, _parse_jsonpath_expr


# ── _get ──────────────────────────────────────────────────────────────────────

def test_get_simple_key():
    assert _get({"title": "Roast Chicken"}, "title") == "Roast Chicken"


def test_get_nested_key():
    assert _get({"a": {"b": "c"}}, "a.b") == "c"


def test_get_missing_key():
    assert _get({}, "x") == ""


def test_get_missing_nested_key():
    assert _get({"a": {}}, "a.b") == ""


def test_get_float():
    result = _get({"score": 4.7}, "score")
    assert result == "4.70"


def test_get_int():
    result = _get({"count": 42}, "count")
    assert result == "42"


def test_get_slug_with_search_url():
    obj = {
        "slug": "roast-chicken",
        "search_url": "/recipes/roast-chicken",
        "search_document_klass": "recipe",
    }
    result = _get(obj, "slug")
    assert result == "https://www.americastestkitchen.com/recipes/roast-chicken"


def test_get_slug_recipe():
    obj = {
        "slug": "roast-chicken",
        "search_document_klass": "recipe",
    }
    result = _get(obj, "slug")
    assert "roast-chicken" in result
    assert "americastestkitchen.com" in result


def test_get_none_value():
    assert _get({"key": None}, "key") == ""


# ── _parse_jsonpath_expr ──────────────────────────────────────────────────────

def test_parse_jsonpath_expr_valid():
    result = _parse_jsonpath_expr("jsonpath=hits[*]")
    assert result == "hits[*]"


def test_parse_jsonpath_expr_none():
    assert _parse_jsonpath_expr("table") is None


def test_parse_jsonpath_expr_json():
    assert _parse_jsonpath_expr("json") is None


def test_parse_jsonpath_expr_nested():
    result = _parse_jsonpath_expr("jsonpath=results[0].hits[*].title")
    assert result == "results[0].hits[*].title"
