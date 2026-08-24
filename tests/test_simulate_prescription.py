from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.conftest import FAKE_FDA_LABEL_REFERENCE, FAKE_USDA_LOOKUP_RESULT


def test_simulate_prescription_matched_returns_consolidated_response(
    client: TestClient,
) -> None:
    # Autouse fixture defaults classification to "statins" for any drug
    # name, so a made-up name is fine here — this test is about the
    # response shape, not real classification behavior.
    response = client.post(
        "/simulate-prescription", json={"drug_name": "atorvastatin"}
    )
    assert response.status_code == 200
    body = response.json()

    assert body["drug_name"] == "atorvastatin"
    assert body["classification"] == {
        "matched": True,
        "medication_class": "statins",
        "message": None,
    }
    assert body["clinical_content"]["medication_class"] == "statins"
    assert body["clinical_content"]["nutrient_concern"] == "CoQ10 association"

    # statins has no foods_that_may_help in the seed data, so nothing to
    # enrich — this still exercises the "matched" path end to end without
    # depending on another class's seed content.
    assert body["recommendation"]["foods_that_may_help"] is None

    assert body["fda_label_reference"] == FAKE_FDA_LABEL_REFERENCE

    timing = body["timing_ms"]
    assert timing["rxclass"] is not None
    assert timing["usda"] is not None
    assert timing["openfda"] is not None
    assert all(isinstance(v, (int, float)) for v in timing.values())


def test_simulate_prescription_matched_with_foods_enriches_via_usda(
    client: TestClient,
) -> None:
    with patch(
        "mind_recovery_mvp.rxclass.classify_medication_class",
        return_value="metformin",
    ):
        response = client.post(
            "/simulate-prescription", json={"drug_name": "metformin"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["classification"]["medication_class"] == "metformin"

    foods = body["recommendation"]["foods_that_may_help"]
    assert {entry["food"] for entry in foods} == {
        "eggs",
        "dairy",
        "fish",
        "fortified cereals",
    }
    assert all(entry["nutrients"] == FAKE_USDA_LOOKUP_RESULT for entry in foods)


def test_simulate_prescription_unmatched_drug_returns_clear_not_supported(
    client: TestClient,
) -> None:
    with patch(
        "mind_recovery_mvp.rxclass.classify_medication_class", return_value=None
    ) as mock_classify, patch(
        "mind_recovery_mvp.usda.lookup_food_nutrients"
    ) as mock_usda, patch(
        "mind_recovery_mvp.openfda.get_fda_label_reference"
    ) as mock_openfda:
        response = client.post(
            "/simulate-prescription", json={"drug_name": "amoxicillin"}
        )

    assert response.status_code == 200
    body = response.json()

    assert body["drug_name"] == "amoxicillin"
    assert body["classification"]["matched"] is False
    assert body["classification"]["medication_class"] is None
    assert "amoxicillin" in body["classification"]["message"]
    assert "not" in body["classification"]["message"].lower()

    assert body["clinical_content"] is None
    assert body["recommendation"] is None
    assert body["fda_label_reference"] is None

    timing = body["timing_ms"]
    assert timing["rxclass"] is not None
    assert timing["usda"] is None
    assert timing["openfda"] is None

    # This is the "normal outcome, not a failure" contract from the task:
    # an unmatched drug must not even attempt USDA/openFDA calls.
    mock_classify.assert_called_once_with("amoxicillin")
    mock_usda.assert_not_called()
    mock_openfda.assert_not_called()


def test_simulate_prescription_timing_reflects_real_elapsed_time(
    client: TestClient,
) -> None:
    """Not a network test — proves the timing values come from actually
    timing the (mocked) calls, rather than being hardcoded/fake, by
    making one of the mocks artificially slow and checking it shows up."""
    import time

    def slow_lookup(*args: object, **kwargs: object) -> dict:
        time.sleep(0.05)
        return FAKE_USDA_LOOKUP_RESULT

    with patch(
        "mind_recovery_mvp.rxclass.classify_medication_class",
        return_value="metformin",
    ), patch("mind_recovery_mvp.usda.lookup_food_nutrients", side_effect=slow_lookup):
        response = client.post(
            "/simulate-prescription", json={"drug_name": "metformin"}
        )

    assert response.status_code == 200
    # 4 foods x ~50ms each, minus some slack for scheduling jitter.
    assert response.json()["timing_ms"]["usda"] >= 150
