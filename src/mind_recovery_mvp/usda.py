"""USDA FoodData Central lookup, used to enrich foods_that_may_help.

Enrichment is optional: any failure (missing key, network error, timeout,
unexpected response shape) must fall back to `None` rather than raise, so a
USDA outage can never block /fill-event from responding.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"
REQUEST_TIMEOUT_SECONDS = 5.0
MAX_NUTRIENTS_PER_FOOD = 5


def lookup_food_nutrients(food_name: str, api_key: str) -> dict[str, Any] | None:
    try:
        response = httpx.get(
            f"{USDA_BASE_URL}/foods/search",
            params={"query": food_name, "pageSize": 1, "api_key": api_key},
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
        logger.warning("USDA lookup failed for food %r", food_name, exc_info=True)
        return None


def enrich_foods(
    foods: list[str] | None, api_key: str | None
) -> dict[str, Any] | None:
    if not api_key or not foods:
        return None

    enriched = {
        food: result
        for food in foods
        if (result := lookup_food_nutrients(food, api_key)) is not None
    }
    return enriched or None
