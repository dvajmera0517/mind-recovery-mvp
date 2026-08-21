from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from mind_recovery_mvp.db import Base, get_db
from mind_recovery_mvp.loader import load_seed_data
from mind_recovery_mvp.main import app
from mind_recovery_mvp.seed_data import NUTRIENT_CONTENT_SEED


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(bind=engine)

    with TestSessionLocal() as session:
        load_seed_data(session)

    def override_get_db() -> Iterator[Session]:
        with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
        os.remove(db_path)


@pytest.mark.parametrize(
    "seed_record", NUTRIENT_CONTENT_SEED, ids=lambda r: r["medication_class"]
)
def test_fill_event_returns_seeded_record(
    client: TestClient, seed_record: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("FDC_API_KEY", raising=False)

    response = client.post(
        "/fill-event", json={"medication_class": seed_record["medication_class"]}
    )
    assert response.status_code == 200
    body = response.json()

    for field in seed_record:
        assert body[field] == seed_record[field]

    assert body["recommendation"] == {
        "foods_that_may_help": seed_record["foods_that_may_help"],
        "supplements_to_discuss": seed_record["supplements_to_discuss"],
        "food_nutrients": None,
    }


def test_fill_event_unknown_class_returns_404(client: TestClient) -> None:
    response = client.post("/fill-event", json={"medication_class": "opioids"})
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "opioids" in detail
    assert "metformin" in detail


def test_fill_event_without_fdc_api_key_skips_enrichment(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("FDC_API_KEY", raising=False)

    with patch("mind_recovery_mvp.usda.httpx.get") as mock_get:
        response = client.post("/fill-event", json={"medication_class": "metformin"})

    assert response.status_code == 200
    mock_get.assert_not_called()
    assert response.json()["recommendation"]["food_nutrients"] is None


def test_fill_event_with_fdc_api_key_enriches_foods(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FDC_API_KEY", "test-key")
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
    food_nutrients = response.json()["recommendation"]["food_nutrients"]
    assert set(food_nutrients) == {"eggs", "dairy", "fish", "fortified cereals"}
    assert food_nutrients["eggs"] == fake_lookup
    assert mock_lookup.call_count == 4
