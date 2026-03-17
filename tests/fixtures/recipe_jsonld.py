"""JSON-LD fixture dicts and HTML wrapper helper."""

import json

JSONLD_RECIPE = {
    "@context": "https://schema.org",
    "@type": "Recipe",
    "name": "Classic Roast Chicken",
    "description": "The best roast chicken recipe ever.",
    "author": {"@type": "Person", "name": "Julia Collin Davison"},
    "datePublished": "2023-06-15",
    "prepTime": "PT15M",
    "cookTime": "PT1H15M",
    "totalTime": "PT1H30M",
    "recipeYield": ["4 servings", "4"],
    "recipeIngredient": [
        "1 whole chicken (3½ to 4 pounds)",
        "2 tablespoons unsalted butter",
        "1 teaspoon kosher salt",
    ],
    "recipeInstructions": [
        {"@type": "HowToStep", "text": "Preheat oven to 450°F."},
        {"@type": "HowToStep", "text": "Pat chicken dry and season with salt and pepper."},
        {"@type": "HowToStep", "text": "Roast until thigh registers 175°F, about 75 minutes."},
    ],
    "aggregateRating": {
        "@type": "AggregateRating",
        "ratingValue": "4.7",
        "reviewCount": "312",
    },
    "keywords": "chicken, roasting, dinner, easy",
    "nutrition": {
        "@type": "NutritionInformation",
        "calories": "420 calories",
    },
    "suitableForDiet": "https://schema.org/GlutenFreeDiet",
}

JSONLD_MULTI_DIET = {
    **JSONLD_RECIPE,
    "suitableForDiet": [
        "https://schema.org/VegetarianDiet",
        "https://schema.org/GlutenFreeDiet",
    ],
}

JSONLD_LIST_AUTHOR = {
    **JSONLD_RECIPE,
    "author": [
        {"@type": "Person", "name": "Julia Collin Davison"},
        {"@type": "Person", "name": "Bridget Lancaster"},
    ],
}

JSONLD_PLACEHOLDER_TIME = {
    **JSONLD_RECIPE,
    "totalTime": "PLACEHOLDER",
    "prepTime": "PT15M",
    "cookTime": "PT1H15M",
}


def wrap_jsonld_in_html(data: dict) -> str:
    """Wrap a JSON-LD dict in minimal HTML with a script tag."""
    return (
        "<!DOCTYPE html><html><head>"
        f'<script type="application/ld+json">{json.dumps(data)}</script>'
        "</head><body><h1>Recipe</h1></body></html>"
    )


HTML_NO_JSONLD = "<!DOCTYPE html><html><head><title>Recipe</title></head><body><h1>Recipe</h1></body></html>"

HTML_JSONLD_LIST = (
    "<!DOCTYPE html><html><head>"
    '<script type="application/ld+json">'
    + json.dumps(
        [
            {"@type": "WebPage", "name": "Recipe Page"},
            JSONLD_RECIPE,
        ]
    )
    + "</script></head><body></body></html>"
)
