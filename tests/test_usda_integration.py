"""Real, live USDA FoodData Central call.

Excluded from the default `pytest` run (see the `-m "not integration"` in
pyproject.toml's addopts). Run just this test with:

    pytest -m integration
"""

from __future__ import annotations

import os

import pytest

from mind_recovery_mvp.usda import lookup_food_nutrients
from tests.conftest import PYTEST_PLACEHOLDER_API_KEY

# USDA's public, rate-limited testing key — used only if no real
# FDC_API_KEY is configured, so this test can run against the real API
# out of the box. Get your own free key: https://fdc.nal.usda.gov/api-key-signup
USDA_DEMO_KEY = "DEMO_KEY"


def _resolve_real_api_key() -> str:
    api_key = os.environ.get("FDC_API_KEY")
    if not api_key or api_key == PYTEST_PLACEHOLDER_API_KEY:
        return USDA_DEMO_KEY
    return api_key


@pytest.mark.integration
def test_lookup_food_nutrients_hits_real_usda_api() -> None:
    api_key = _resolve_real_api_key()

    result = lookup_food_nutrients("eggs", api_key)

    assert result is not None, (
        "Expected a real result from the live USDA API. If this fails with "
        "the public DEMO_KEY, USDA's demo rate limit may be exhausted — "
        "set a real FDC_API_KEY and retry."
    )
    assert isinstance(result["fdc_id"], int)
    assert isinstance(result["description"], str) and result["description"]
    assert len(result["nutrients"]) > 0
    for nutrient in result["nutrients"]:
        assert nutrient["name"]
        assert nutrient["unit"]
