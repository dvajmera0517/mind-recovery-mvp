"""Real, live RxClass (NLM) call.

Excluded from the default `pytest` run (see the `-m "not integration"` in
pyproject.toml's addopts). Run just this test with:

    pytest -m integration

No API key needed for RxClass.
"""

from __future__ import annotations

import pytest

from mind_recovery_mvp.rxclass import classify_medication_class


@pytest.mark.integration
def test_classify_medication_class_hits_real_rxclass_api() -> None:
    assert classify_medication_class("metformin") == "metformin"
    assert classify_medication_class("atorvastatin") == "statins"
    assert classify_medication_class("furosemide") == "diuretics"
    assert classify_medication_class("omeprazole") == "ppi"
