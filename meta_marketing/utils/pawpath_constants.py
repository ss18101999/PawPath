"""PawPath brand constants for Meta advertising."""

from __future__ import annotations

PAWPATH_PAGE_ID = "1176239588903352"
PAWPATH_PIXEL_ID = "2450255575122418"
PAWPATH_STORE_URL = "https://pawpathsupply.com"
# Set when IG is assigned to ad account in Business Manager; None = Facebook Page only
PAWPATH_INSTAGRAM_USER_ID: str | None = None

AI_CAMPAIGN_NAMES = ("PawPath_AI_Test_1", "PawPath_AI_Test_2", "PawPath_AI_Test_3")
CAMPAIGN_DAILY_BUDGET_INR = 10000  # ₹100/day per campaign

US_DOG_TARGETING: dict = {
    "geo_locations": {"countries": ["US"]},
    "age_min": 25,
    "age_max": 65,
    "flexible_spec": [
        {
            "interests": [
                {"id": "6003332344237", "name": "Dogs (animals)"},
                {"id": "6003341040796", "name": "Puppy (dogs)"},
                {"id": "6003545396227", "name": "Dog training (pets)"},
                {"id": "6003121856334", "name": "Pet store (pet supplies)"},
                {"id": "6003293626330", "name": "Dog walking (dogs)"},
                {"id": "6003381100005", "name": "Dog food (pet supplies)"},
            ]
        }
    ],
    "targeting_automation": {"advantage_audience": 1},
}
