"""USDA FoodData Central lookup, used to enrich foods_that_may_help.

FDC_API_KEY is required to run the app at all (main.lifespan fails fast at
startup if it's missing) — that's a config error, loud and immediate. A
per-food lookup failure at request time (timeout, rate limit, 5xx,
malformed response) is a different failure mode: it must degrade quietly,
falling back to that food's plain name, and must never raise out of this
module or block /fill-event from responding.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"
REQUEST_TIMEOUT_SECONDS = 5.0
MAX_NUTRIENTS_PER_FOOD = 5
# Foundation/SR Legacy are generic whole-food entries. Without this filter,
# USDA's relevance search also matches branded products by name (e.g. a
# "Milky Way EGGS" candy bar outranks actual eggs for the query "eggs"),
# which makes the nutrient summary useless.
WHOLE_FOOD_DATA_TYPES = "Foundation,SR Legacy"


def lookup_food_nutrients(food_name: str, api_key: str) -> dict[str, Any] | None:
    try:
        response = httpx.get(
            f"{USDA_BASE_URL}/foods/search",
            params={
                "query": food_name,
                "pageSize": 1,
                "dataType": WHOLE_FOOD_DATA_TYPES,
                "api_key": api_key,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        foods = payload.get("foods") or []
        if not foods:
            return None
        food = foods[0]
        nutrients = [
            {
                "name": nutrient.get("nutrientName"),
                "amount": nutrient.get("value"),
                "unit": nutrient.get("unitName"),
            }
            for nutrient in (food.get("foodNutrients") or [])[:MAX_NUTRIENTS_PER_FOOD]
        ]
        return {
            "fdc_id": food.get("fdcId"),
            "description": food.get("description"),
            "nutrients": nutrients,
        }
    except Exception:
        logger.warning(
            "USDA lookup failed for food %r; falling back to plain name",
            food_name,
            exc_info=True,
        )
        return None


def enrich_foods(foods: list[str] | None, api_key: str) -> list[dict[str, Any]] | None:
    """Attach a USDA nutrient summary to each food.

    Every food is always kept (its plain name never disappears); `nutrients`
    is `None` for any single food whose USDA lookup failed, rather than
    dropping that food or failing the whole call.
    """
    if not foods:
        return None
    return [
        {"food": food, "nutrients": lookup_food_nutrients(food, api_key)}
        for food in foods
    ]
