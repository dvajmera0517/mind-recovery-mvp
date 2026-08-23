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

# Sentinel used as FDC_API_KEY for every test except ones marked
# @pytest.mark.integration. Not a real key — tests/test_usda_integration.py
# checks for this exact value to know no real key is configured and falls
# back to USDA's public DEMO_KEY.
PYTEST_PLACEHOLDER_API_KEY = "pytest-placeholder-not-a-real-fdc-key"

FAKE_USDA_LOOKUP_RESULT = {
    "fdc_id": 999999,
    "description": "Test Food, generic",
    "nutrients": [{"name": "Protein", "amount": 1.0, "unit": "G"}],
}

FAKE_FDA_LABEL_REFERENCE = {
    "label": "FDA label reference",
    "source_drug": "Test Drug",
    "drug_interactions": "Test drug interactions text.",
    "warnings_and_cautions": "Test warnings and cautions text.",
}


@pytest.fixture(autouse=True)
def _isolate_external_dependencies(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    """Keep the default test run fast and offline.

    Every test gets a placeholder FDC_API_KEY and mocked USDA/openFDA
    lookups, so nothing in the default run touches the real network.
    Tests marked @pytest.mark.integration are left untouched on purpose,
    so they can exercise the real keys/APIs.
    """
    if "integration" in request.keywords:
        yield
        return

    monkeypatch.setenv("FDC_API_KEY", PYTEST_PLACEHOLDER_API_KEY)
    with (
        patch(
            "mind_recovery_mvp.usda.lookup_food_nutrients",
            return_value=FAKE_USDA_LOOKUP_RESULT,
        ),
        patch(
            "mind_recovery_mvp.openfda.get_fda_label_reference",
            return_value=FAKE_FDA_LABEL_REFERENCE,
        ),
    ):
        yield


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
