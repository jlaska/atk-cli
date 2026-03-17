"""REST API fixture dicts matching the ATK API shape."""

RECIPE_DETAIL = {
    "id": 123,
    "title": "Classic Roast Chicken",
    "slug": "classic-roast-chicken",
    "description": "<p>The <b>best</b> roast chicken recipe.</p>",
    "headnote": "Use a good quality bird for best results.",
    "yields": "Serves 4",
    "recipeTimeNote": "1 hour 30 minutes",
    "publishDate": "2023-06-15T00:00:00.000Z",
    "contentAccess": "full_access",
    "ingredientGroups": [
        {
            "fields": {
                "title": "Chicken",
                "recipeIngredientItems": [
                    {
                        "fields": {
                            "qty": "1",
                            "preText": "whole",
                            "postText": "(3½ to 4 pounds)",
                            "ingredient": {
                                "fields": {
                                    "title": "chicken",
                                }
                            },
                        }
                    },
                    {
                        "fields": {
                            "qty": "2",
                            "preText": "",
                            "postText": "",
                            "ingredient": {
                                "fields": {
                                    "title": "tablespoons unsalted butter",
                                }
                            },
                        }
                    },
                ],
            }
        }
    ],
    "instructions": [
        {
            "fields": {
                "content": "<p>Preheat oven to 450°F.</p>",
            }
        },
        {
            "fields": {
                "content": "<p>Pat chicken dry and season with salt and pepper.</p>",
            }
        },
    ],
    "nutritionSummary": {
        "calories": 420,
        "protein": 45,
        "fat": 25,
    },
    "tags": [
        {"fields": {"tagTitle": "chicken"}},
        {"fields": {"tagTitle": "roasting"}},
        {"fields": {"tagTitle": "dinner"}},
    ],
}

RECIPE_RATING = {
    "data": {
        "rating": {
            "attributes": {
                "avgScore": 4.7,
                "userRatingsCount": 312,
            }
        },
        "userRating": {
            "attributes": {
                "score": 5,
            }
        },
    }
}

RECIPE_COLLECTIONS = [
    {
        "id": 1,
        "name": "Weeknight Dinners",
        "items_count": 12,
        "site_key": "atk",
    },
    {
        "id": 2,
        "name": "Favorites",
        "items_count": 48,
        "site_key": "atk",
    },
]
