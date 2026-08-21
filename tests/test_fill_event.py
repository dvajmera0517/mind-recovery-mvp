from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from mind_recovery_mvp.seed_data import NUTRIENT_CONTENT_SEED
from tests.conftest import FAKE_USDA_LOOKUP_RESULT


@pytest.mark.parametrize(
    "seed_record", NUTRIENT_CONTENT_SEED, ids=lambda r: r["medication_class"]
)
def test_fill_event_returns_seeded_record(
    client: TestClient, seed_record: dict
) -> None:
    response = client.post(
        "/fill-event", json={"medication_class": seed_record["medication_class"]}
    )
    assert response.status_code == 200
    body = response.json()

    for field in seed_record:
        assert body[field] == seed_record[field]

    expected_foods = None
    if seed_record["foods_that_may_help"] is not None:
        expected_foods = [
            {"food": food, "nutrients": FAKE_USDA_LOOKUP_RESULT}
            for food in seed_record["foods_that_may_help"]
        ]
    assert body["recommendation"] == {
        "foods_that_may_help": expected_foods,
        "supplements_to_discuss": seed_record["supplements_to_discuss"],
    }


def test_fill_event_unknown_class_returns_404(client: TestClient) -> None:
    response = client.post("/fill-event", json={"medication_class": "opioids"})
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "opioids" in detail
    assert "metformin" in detail


def test_fill_event_enriches_each_food_via_usda(client: TestClient) -> None:
    fake_lookup = {
        "fdc_id": 1,
        "description": "fake food",
        "nutrients": [{"name": "Protein", "amount": 1.0, "unit": "G"}],
    }

    with patch(
        "mind_recovery_mvp.usda.lookup_food_nutrients", return_value=fake_lookup
    ) as mock_lookup:
        response = client.post("/fill-event", json={"medication_class": "metformin"})

    assert response.status_code == 200
    foods = response.json()["recommendation"]["foods_that_may_help"]
    assert {entry["food"] for entry in foods} == {
        "eggs",
        "dairy",
        "fish",
        "fortified cereals",
    }
    assert all(entry["nutrients"] == fake_lookup for entry in foods)
    assert mock_lookup.call_count == 4


def test_fill_event_falls_back_to_plain_name_when_one_usda_lookup_fails(
    client: TestClient,
) -> None:
    def fake_lookup(food: str, api_key: str) -> dict | None:
        if food == "dairy":
            return None
        return {"fdc_id": 1, "description": food, "nutrients": []}

    with patch(
        "mind_recovery_mvp.usda.lookup_food_nutrients", side_effect=fake_lookup
    ):
        response = client.post("/fill-event", json={"medication_class": "metformin"})

    assert response.status_code == 200
    foods = {
        entry["food"]: entry["nutrients"]
        for entry in response.json()["recommendation"]["foods_that_may_help"]
    }
    assert foods["dairy"] is None
    assert foods["eggs"] == {"fdc_id": 1, "description": "eggs", "nutrients": []}
