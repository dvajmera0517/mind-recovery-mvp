from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from mind_recovery_mvp.main import app


def test_missing_fdc_api_key_fails_fast_on_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The regular `client` fixture never triggers FastAPI's lifespan hook
    # (a bare TestClient(app) doesn't; only `with TestClient(app):` does),
    # so this test deliberately uses the context-manager form to exercise
    # startup directly, with no FDC_API_KEY in the environment.
    monkeypatch.delenv("FDC_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="FDC_API_KEY"):
        with TestClient(app):
            pass
