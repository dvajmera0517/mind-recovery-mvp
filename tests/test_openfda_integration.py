"""Real, live openFDA drug label call.

Excluded from the default `pytest` run (see the `-m "not integration"` in
pyproject.toml's addopts). Run just this test with:

    pytest -m integration

No API key needed (OPENFDA_API_KEY, if set, just raises the rate limit —
this test doesn't require one).
"""

from __future__ import annotations

import pytest

from mind_recovery_mvp.openfda import get_fda_label_reference


@pytest.mark.integration
def test_get_fda_label_reference_hits_real_openfda_api() -> None:
    result = get_fda_label_reference("metformin")

    assert result is not None, "Expected a real result from the live openFDA API."
    assert result["label"] == "FDA label reference"
    assert result["source_drug"]
    # drug_interactions/warnings_and_cautions can legitimately be None for
    # a given label (older-format labels use different section names) —
    # only assert the lookup itself succeeded.
