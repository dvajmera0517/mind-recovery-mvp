from __future__ import annotations

from unittest.mock import Mock, patch

import httpx

from mind_recovery_mvp.usda import enrich_foods, lookup_food_nutrients


def _mock_response(payload: dict, status_code: int = 200) -> Mock:
    response = Mock(spec=httpx.Response)
    response.status_code = status_code
    response.json.return_value = payload
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=Mock(), response=response
        )
    else:
        response.raise_for_status.return_value = None
    return response


def test_lookup_food_nutrients_success() -> None:
    payload = {
        "foods": [
            {
                "fdcId": 123456,
                "description": "Egg, whole, raw, fresh",
                "foodNutrients": [
                    {"nutrientName": "Protein", "value": 12.6, "unitName": "G"},
                    {"nutrientName": "Vitamin B-12", "value": 0.89, "unitName": "UG"},
                ],
            }
        ]
    }
    with patch(
        "mind_recovery_mvp.usda.httpx.get", return_value=_mock_response(payload)
    ) as mock_get:
        result = lookup_food_nutrients("eggs", "test-key")

    mock_get.assert_called_once()
    call_kwargs = mock_get.call_args.kwargs
    assert call_kwargs["params"]["query"] == "eggs"
    assert call_kwargs["params"]["api_key"] == "test-key"
    # Restricts to whole-food entries so a branded product with a matching
    # name (e.g. a candy bar called "Eggs") can't outrank actual eggs.
    assert call_kwargs["params"]["dataType"] == "Foundation,SR Legacy"
    assert result == {
        "fdc_id": 123456,
        "description": "Egg, whole, raw, fresh",
        "nutrients": [
            {"name": "Protein", "amount": 12.6, "unit": "G"},
            {"name": "Vitamin B-12", "amount": 0.89, "unit": "UG"},
        ],
    }


def test_lookup_food_nutrients_no_results_returns_none() -> None:
    with patch(
        "mind_recovery_mvp.usda.httpx.get",
        return_value=_mock_response({"foods": []}),
    ):
        result = lookup_food_nutrients("not-a-real-food", "test-key")
    assert result is None


def test_lookup_food_nutrients_http_error_returns_none() -> None:
    with patch(
        "mind_recovery_mvp.usda.httpx.get",
        return_value=_mock_response({}, status_code=500),
    ):
        result = lookup_food_nutrients("eggs", "test-key")
    assert result is None


def test_lookup_food_nutrients_network_error_returns_none() -> None:
    with patch(
        "mind_recovery_mvp.usda.httpx.get",
        side_effect=httpx.ConnectError("connection failed"),
    ):
        result = lookup_food_nutrients("eggs", "test-key")
    assert result is None


def test_enrich_foods_without_foods_returns_none() -> None:
    assert enrich_foods(None, "test-key") is None
    assert enrich_foods([], "test-key") is None


def test_enrich_foods_looks_up_each_food() -> None:
    with patch(
        "mind_recovery_mvp.usda.lookup_food_nutrients",
        side_effect=lambda food, key: {"fdc_id": 1, "description": food, "nutrients": []},
    ):
        result = enrich_foods(["eggs", "dairy"], "test-key")

    assert result == [
        {"food": "eggs", "nutrients": {"fdc_id": 1, "description": "eggs", "nutrients": []}},
        {"food": "dairy", "nutrients": {"fdc_id": 1, "description": "dairy", "nutrients": []}},
    ]


def test_enrich_foods_falls_back_to_plain_name_on_failed_lookup() -> None:
    # A single failed USDA lookup (timeout, rate limit, 5xx, ...) must not
    # drop the food or fail the whole call — it falls back to the plain
    # food name with nutrients=None.
    with patch(
        "mind_recovery_mvp.usda.lookup_food_nutrients",
        side_effect=lambda food, key: None if food == "dairy" else {
            "fdc_id": 1, "description": food, "nutrients": []
        },
    ):
        result = enrich_foods(["eggs", "dairy"], "test-key")

    assert result == [
        {"food": "eggs", "nutrients": {"fdc_id": 1, "description": "eggs", "nutrients": []}},
        {"food": "dairy", "nutrients": None},
    ]
