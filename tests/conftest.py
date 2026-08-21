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
