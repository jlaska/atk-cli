"""Pydantic models for ATK API responses."""

from typing import Any
from pydantic import BaseModel, Field

from .constants import build_atk_url


class Pagination(BaseModel):
    total_count: int = 0
    page: int = 1
    last_page: bool = True
    per_page: int = 16


class FavoriteResult(BaseModel):
    object_id: str = ""
    document_title: str = ""
    document_avg_score: float | None = None
    slug: str = ""
    document_type: str = ""
    site_key: str = ""

    @property
    def recipe_id(self) -> str:
        return self.object_id.replace("recipe_", "")

    @property
    def url(self) -> str:
        if self.slug:
            numeric_id = self.object_id.split("_")[-1] if "_" in self.object_id else ""
            if numeric_id and self.document_type != "recipe":
                return build_atk_url(f"{numeric_id}-{self.slug}", self.document_type)
            return build_atk_url(self.slug, self.document_type)
        return ""


class FavoritesPage(BaseModel):
    results: list[FavoriteResult] = Field(default_factory=list)
    pagination: Pagination = Field(default_factory=Pagination)


class RecentFavorite(BaseModel):
    id: int | None = None
    title: str = ""
    slug: str = ""
    avgScore: float | None = None
    userRating: int | None = None

    @property
    def url(self) -> str:
        if self.slug:
            return build_atk_url(self.slug, "recipe")
        return ""


class Collection(BaseModel):
    id: int | None = None
    name: str = ""
    slug: str = ""
    items_count: int = 0
    site_key: str = ""


class RatingAttributes(BaseModel):
    avgScore: float | None = None
    userRatingsCount: int | None = None
    userRating: int | None = None


class Rating(BaseModel):
    attributes: RatingAttributes = Field(default_factory=RatingAttributes)


class SearchHit(BaseModel):
    objectID: str = ""
    title: str = ""
    description: str = ""
    search_document_klass: str = ""
    slug: str = ""
    search_url: str = ""
    avgScore: float | None = None

    @property
    def url(self) -> str:
        if self.search_url:
            return f"https://www.americastestkitchen.com{self.search_url}"
        if self.slug:
            return build_atk_url(self.slug, self.search_document_klass)
        return ""


class TrendingRecipe(BaseModel):
    id: int | None = None
    title: str = ""
    slug: str = ""
    avgScore: float | None = None

    @property
    def url(self) -> str:
        if self.slug:
            return build_atk_url(self.slug, "recipe")
        return ""


class CustomerSummary(BaseModel):
    email: str = ""
    firstName: str = ""
    lastName: str = ""
    subscriptionStatus: str = ""
    subscriptionType: str = ""
    expirationDate: str = ""
