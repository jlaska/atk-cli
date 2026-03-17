"""Algolia fixture dicts matching the Algolia document shape."""

ALGOLIA_DOCUMENT = {
    "objectID": "recipe_123",
    "title": "Classic Roast Chicken",
    "description": "The best roast chicken recipe ever.",
    "slug": "classic-roast-chicken",
    "search_url": "/recipes/classic-roast-chicken",
    "search_document_klass": "recipe",
    "search_published_date": "20230615",
    "search_author": "Julia Collin Davison",
    "avgScore": 4.7,
    "search_user_ratings_count": 312,
}

ALGOLIA_SEARCH_RESPONSE = {
    "results": [
        {
            "hits": [
                {
                    "objectID": "recipe_123",
                    "title": "Classic Roast Chicken",
                    "search_document_klass": "recipe",
                    "avgScore": 4.7,
                    "slug": "classic-roast-chicken",
                    "search_url": "/recipes/classic-roast-chicken",
                },
                {
                    "objectID": "recipe_456",
                    "title": "Simple Roasted Chicken Thighs",
                    "search_document_klass": "recipe",
                    "avgScore": 4.5,
                    "slug": "simple-roasted-chicken-thighs",
                    "search_url": "/recipes/simple-roasted-chicken-thighs",
                },
            ],
            "nbHits": 2,
            "page": 0,
            "nbPages": 1,
            "hitsPerPage": 20,
            "query": "roast chicken",
        }
    ]
}
