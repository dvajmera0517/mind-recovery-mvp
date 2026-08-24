"""Shared content_status vocabulary and the approve/render-gate logic that
depends on it. Used by scripts/draft_content.py, scripts/review_content.py,
and companion_page.py.
"""

from __future__ import annotations

from datetime import datetime

from mind_recovery_mvp.models import NutrientContent

STATUS_LLM_DRAFTED_PENDING_REVIEW = "llm_drafted_pending_pharmacist_review"
STATUS_SAMPLE_CONTENT_PENDING_REVIEW = "sample_content_pending_pharmacist_review"
STATUS_APPROVED = "approved"
STATUS_APPROVED_WITH_EDITS = "approved_with_edits"

APPROVED_STATUSES = {STATUS_APPROVED, STATUS_APPROVED_WITH_EDITS}
# Every status representing content that a human hasn't reviewed yet.
# review_content.py lists exactly these; is_customer_visible hides exactly
# these (alongside the original PLACEHOLDER state, checked separately
# since it isn't one fixed string).
PENDING_REVIEW_STATUSES = {
    STATUS_LLM_DRAFTED_PENDING_REVIEW,
    STATUS_SAMPLE_CONTENT_PENDING_REVIEW,
}

# Tags NutrientContent.content_origin, so provenance survives past
# approval (content_status alone no longer distinguishes sample vs. LLM
# once it's "approved"/"approved_with_edits").
CONTENT_ORIGIN_LLM = "llm"
CONTENT_ORIGIN_SAMPLE = "sample"

CONTENT_ORIGIN_LABELS: dict[str, str] = {
    CONTENT_ORIGIN_SAMPLE: "Sample content (hand-written for demo)",
    CONTENT_ORIGIN_LLM: "LLM-drafted (Claude)",
}

REVIEWABLE_FIELDS = [
    "why_it_matters",
    "foods_that_may_help",
    "supplements_to_discuss",
    "talk_to_pharmacist_if",
    "clinical_source",
]


def is_customer_visible(content_status: str) -> bool:
    """Whether a record's content fields are safe to show on the
    companion page, as opposed to "Pending pharmacist review".

    Only "approved"/"approved_with_edits" are explicitly safe. The
    original PLACEHOLDER state and both pending-review states
    (LLM-drafted, sample-content) are explicitly hidden, even if some of
    their fields happen to be populated (e.g. diuretics' PLACEHOLDER
    record already has a non-null foods_that_may_help) — drafting,
    loading sample content, or partial seeding doesn't change what's
    safe to show a customer.

    Everything else (in practice, just metformin's pre-existing
    "drafted — needs final pharmacist/legal sign-off" status) falls
    through as visible: that record predates and sits outside this
    draft/review pipeline entirely — review_content.py never touches it
    either, since it only lists PENDING_REVIEW_STATUSES records. This
    gate protects the new pipeline; it isn't a blanket "only formally
    approved content is ever shown" rule.
    """
    if content_status in APPROVED_STATUSES:
        return True
    if content_status in PENDING_REVIEW_STATUSES:
        return False
    if content_status.startswith("PLACEHOLDER"):
        return False
    return True


def approve_record(
    record: NutrientContent,
    *,
    edits: dict[str, object] | None,
    reviewer_name: str,
    reviewed_at: datetime,
) -> None:
    """Apply a reviewer's approval decision to record.

    `edits` maps a subset of REVIEWABLE_FIELDS to their new value; pass
    None or {} for an as-is approval. content_status becomes "approved"
    if nothing actually changed, "approved_with_edits" if anything did
    (comparing the new value, so re-submitting the same value doesn't
    count as an edit).
    """
    changed = False
    for field, value in (edits or {}).items():
        if getattr(record, field) != value:
            setattr(record, field, value)
            changed = True

    record.content_status = STATUS_APPROVED_WITH_EDITS if changed else STATUS_APPROVED
    record.reviewed_by = reviewer_name
    record.reviewed_at = reviewed_at
