"""Pydantic models for ATK API responses."""

from typing import Any
from pydantic import BaseModel, Field


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
            return f"https://www.americastestkitchen.com/{self.slug}"
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
            return f"https://www.americastestkitchen.com/{self.slug}"
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
    avgScore: float | None = None

    @property
    def url(self) -> str:
        if self.slug:
            return f"https://www.americastestkitchen.com/{self.slug}"
        return ""


class TrendingRecipe(BaseModel):
    id: int | None = None
    title: str = ""
    slug: str = ""
    avgScore: float | None = None

    @property
    def url(self) -> str:
        if self.slug:
            return f"https://www.americastestkitchen.com/{self.slug}"
        return ""


class CustomerSummary(BaseModel):
    email: str = ""
    firstName: str = ""
    lastName: str = ""
    subscriptionStatus: str = ""
    subscriptionType: str = ""
    expirationDate: str = ""
