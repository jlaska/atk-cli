"""Tests for build_atk_url in atk_cli.constants."""

import pytest

from atk_cli.constants import build_atk_url


def test_build_url_recipe():
    url = build_atk_url("my-recipe", "recipe")
    assert url == "https://www.americastestkitchen.com/recipes/my-recipe"


def test_build_url_article():
    url = build_atk_url("my-article", "article")
    assert url == "https://www.americastestkitchen.com/articles/my-article"


def test_build_url_equipment_review():
    url = build_atk_url("123-review", "equipment_review")
    assert url == "https://www.americastestkitchen.com/equipment_reviews/123-review"


def test_build_url_taste_test():
    url = build_atk_url("best-ketchup", "taste_test")
    assert url == "https://www.americastestkitchen.com/taste_tests/best-ketchup"


def test_build_url_episode():
    url = build_atk_url("s24e01", "episode")
    assert url == "https://www.americastestkitchen.com/episodes/s24e01"


def test_build_url_unknown_type():
    # Falls back to <type>s/<slug>
    url = build_atk_url("my-slug", "video")
    assert url == "https://www.americastestkitchen.com/videos/my-slug"


def test_build_url_default_type():
    # Default type is recipe
    url = build_atk_url("my-recipe")
    assert url == "https://www.americastestkitchen.com/recipes/my-recipe"
