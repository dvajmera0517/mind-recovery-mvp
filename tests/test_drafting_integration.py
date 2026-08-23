"""Real, live Claude API call to draft the statins record.

Excluded from the default `pytest` run (see the `-m "not integration"` in
pyproject.toml's addopts). Run just this test with:

    ANTHROPIC_API_KEY=<your-key> pytest -m integration
"""

from __future__ import annotations

import os

import pytest

from mind_recovery_mvp.content_review import STATUS_LLM_DRAFTED_PENDING_REVIEW
from mind_recovery_mvp.drafting import apply_draft_to_record, draft_content_fields
from mind_recovery_mvp.evidence_excerpts import EVIDENCE_EXCERPTS
from mind_recovery_mvp.models import NutrientContent


@pytest.mark.integration
def test_draft_content_fields_hits_real_claude_api_for_statins() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip(
            "ANTHROPIC_API_KEY not set — this test needs a real key, unlike "
            "the USDA/RxClass/openFDA integration tests, since Claude has "
            "no public no-signup testing key equivalent to DEMO_KEY."
        )

    excerpt_record = next(
        e for e in EVIDENCE_EXCERPTS if e["medication_class"] == "statins"
    )

    drafted = draft_content_fields(
        medication_class="statins",
        nutrient_concern="CoQ10 association",
        evidence_excerpt=excerpt_record["evidence_excerpt"],
        citation_label=excerpt_record["citation_label"],
        api_key=api_key,
    )

    assert set(drafted.keys()) == {
        "why_it_matters",
        "foods_that_may_help",
        "supplements_to_discuss",
        "talk_to_pharmacist_if",
        "clinical_source",
    }
    # clinical_source must be exactly the citation_label, carried forward
    # verbatim rather than invented.
    assert drafted["clinical_source"] == excerpt_record["citation_label"]
    # The excerpt does support why_it_matters and foods_that_may_help —
    # a real draft should not have gone null on either.
    assert drafted["why_it_matters"]
    assert drafted["foods_that_may_help"]

    record = NutrientContent(
        medication_class="statins",
        content_status="PLACEHOLDER — foods, why-it-matters, and discussion "
        "prompt not specified in source; pharmacist/dietitian must draft "
        "and cite before use",
        nutrient_concern="CoQ10 association",
    )
    apply_draft_to_record(record, drafted, excerpt_record["evidence_excerpt"])

    assert record.content_status == STATUS_LLM_DRAFTED_PENDING_REVIEW
    assert record.evidence_excerpt == excerpt_record["evidence_excerpt"]
