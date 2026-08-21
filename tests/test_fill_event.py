from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator

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
    client: TestClient, seed_record: dict
) -> None:
    response = client.post(
        "/fill-event", json={"medication_class": seed_record["medication_class"]}
    )
    assert response.status_code == 200
    assert response.json() == seed_record


def test_fill_event_unknown_class_returns_404(client: TestClient) -> None:
    response = client.post("/fill-event", json={"medication_class": "opioids"})
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "opioids" in detail
    assert "metformin" in detail
