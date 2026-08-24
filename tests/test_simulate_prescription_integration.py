"""Real, live end-to-end /simulate-prescription pipeline: RxClass, USDA,
and openFDA all called for real, plus the "not supported" case.

Excluded from the default `pytest` run (see the `-m "not integration"` in
pyproject.toml's addopts). Run just this test with:

    pytest -m integration
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from tests.conftest import PYTEST_PLACEHOLDER_API_KEY

# USDA's public, rate-limited testing key — used only if no real
# FDC_API_KEY is configured, matching the other integration tests.
USDA_DEMO_KEY = "DEMO_KEY"


def _resolve_real_fdc_api_key() -> str:
    api_key = os.environ.get("FDC_API_KEY")
    if not api_key or api_key == PYTEST_PLACEHOLDER_API_KEY:
        return USDA_DEMO_KEY
    return api_key


@pytest.mark.integration
def test_simulate_prescription_real_pipeline_for_matched_drug(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # "metformin" is both a specific drug name and one of our medication
    # classes, and its seed record has foods_that_may_help populated — so
    # this exercises real network calls to all three APIs (RxClass
    # classification, USDA per-food enrichment, openFDA label lookup),
    # not just the two that'd fire for a class with no foods to enrich.
    monkeypatch.setenv("FDC_API_KEY", _resolve_real_fdc_api_key())

    response = client.post("/simulate-prescription", json={"drug_name": "metformin"})

    assert response.status_code == 200
    body = response.json()

    assert body["drug_name"] == "metformin"
    assert body["classification"] == {
        "matched": True,
        "medication_class": "metformin",
        "message": None,
    }

    assert body["clinical_content"] is not None
    assert body["clinical_content"]["medication_class"] == "metformin"
    # content_status is whatever it currently is in the store — proving
    # the live pipeline works end to end, not pinning the seed data's
    # current review state.
    assert body["clinical_content"]["content_status"]

    foods = body["recommendation"]["foods_that_may_help"]
    assert foods is not None
    assert {entry["food"] for entry in foods} == {
        "eggs",
        "dairy",
        "fish",
        "fortified cereals",
    }

    assert body["fda_label_reference"] is not None
    assert body["fda_label_reference"]["label"] == "FDA label reference"
    assert body["fda_label_reference"]["source_drug"]

    # Real network calls take measurable, non-instant time — the whole
    # point of the timing breakdown is proving these aren't mocked.
    timing = body["timing_ms"]
    assert timing["rxclass"] > 0
    assert timing["usda"] > 0
    assert timing["openfda"] > 0


@pytest.mark.integration
def test_simulate_prescription_real_pipeline_for_unmatched_drug(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FDC_API_KEY", _resolve_real_fdc_api_key())

    response = client.post(
        "/simulate-prescription", json={"drug_name": "amoxicillin"}
    )

    assert response.status_code == 200
    body = response.json()

    assert body["drug_name"] == "amoxicillin"
    assert body["classification"]["matched"] is False
    assert body["classification"]["medication_class"] is None
    assert "amoxicillin" in body["classification"]["message"]

    assert body["clinical_content"] is None
    assert body["recommendation"] is None
    assert body["fda_label_reference"] is None

    timing = body["timing_ms"]
    assert timing["rxclass"] > 0
    assert timing["usda"] is None
    assert timing["openfda"] is None
