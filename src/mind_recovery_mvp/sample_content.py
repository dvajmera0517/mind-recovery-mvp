"""Hand-written sample content — the default content-drafting path.

No LLM call, no ANTHROPIC_API_KEY needed. Distinct from
evidence_excerpts.py (the --use-llm path's source material) and from
seed_data.py (the live clinical content store): this is finished,
demo-ready copy written by hand for statins/diuretics/ppi/glp1, loaded
verbatim from sample_content.json (data, not prose in code).

Like the LLM path, this is still just a draft: content_status becomes
STATUS_SAMPLE_CONTENT_PENDING_REVIEW, never "approved", until a human
reviews it via scripts/review_content.py — being hand-written doesn't
make it pharmacist-reviewed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mind_recovery_mvp.content_review import (
    CONTENT_ORIGIN_SAMPLE,
    STATUS_SAMPLE_CONTENT_PENDING_REVIEW,
)
from mind_recovery_mvp.models import NutrientContent

_SAMPLE_CONTENT_PATH = Path(__file__).parent / "sample_content.json"
SAMPLE_CONTENT: list[dict[str, Any]] = json.loads(_SAMPLE_CONTENT_PATH.read_text())


def apply_sample_content_to_record(
    record: NutrientContent, sample_record: dict[str, Any]
) -> None:
    """Write a sample_content.json entry onto record, in place.

    Mirrors drafting.apply_draft_to_record's contract: never sets
    content_status to "approved". evidence_excerpt is left untouched
    (null unless a previous --use-llm draft set it) — sample content
    isn't drafted from an excerpt, so there's nothing to attach.
    """
    record.why_it_matters = sample_record["why_it_matters"]
    record.foods_that_may_help = sample_record["foods_that_may_help"]
    record.supplements_to_discuss = sample_record["supplements_to_discuss"]
    record.talk_to_pharmacist_if = sample_record["talk_to_pharmacist_if"]
    record.clinical_source = sample_record["clinical_source"]
    record.content_status = STATUS_SAMPLE_CONTENT_PENDING_REVIEW
    record.content_origin = CONTENT_ORIGIN_SAMPLE
