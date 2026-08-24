from __future__ import annotations

from datetime import datetime, timezone

from mind_recovery_mvp.content_review import (
    PENDING_REVIEW_STATUSES,
    STATUS_APPROVED,
    STATUS_APPROVED_WITH_EDITS,
    STATUS_LLM_DRAFTED_PENDING_REVIEW,
    STATUS_SAMPLE_CONTENT_PENDING_REVIEW,
    approve_record,
    is_customer_visible,
)
from mind_recovery_mvp.models import NutrientContent


def test_is_customer_visible_approved() -> None:
    assert is_customer_visible(STATUS_APPROVED) is True
    assert is_customer_visible(STATUS_APPROVED_WITH_EDITS) is True


def test_is_customer_visible_llm_drafted_pending_review() -> None:
    assert is_customer_visible(STATUS_LLM_DRAFTED_PENDING_REVIEW) is False


def test_is_customer_visible_sample_content_pending_review() -> None:
    assert is_customer_visible(STATUS_SAMPLE_CONTENT_PENDING_REVIEW) is False


def test_pending_review_statuses_covers_both_draft_paths() -> None:
    # review_content.py lists exactly this set — regression check for the
    # "confirm it handles the new status, don't assume" ask: it did NOT,
    # until PENDING_REVIEW_STATUSES replaced the old single-status filter.
    assert PENDING_REVIEW_STATUSES == {
        STATUS_LLM_DRAFTED_PENDING_REVIEW,
        STATUS_SAMPLE_CONTENT_PENDING_REVIEW,
    }


def test_is_customer_visible_placeholder() -> None:
    assert (
        is_customer_visible(
            "PLACEHOLDER — foods, why-it-matters, and discussion prompt not "
            "specified in source; pharmacist/dietitian must draft and cite "
            "before use"
        )
        is False
    )


def test_is_customer_visible_metformin_status_falls_through_as_visible() -> None:
    # metformin's pre-existing status predates and sits outside the
    # LLM-draft/review pipeline entirely (review_content.py never lists
    # it either, since it only queries STATUS_LLM_DRAFTED_PENDING_REVIEW)
    # — it should keep rendering normally, not get swept into the new gate.
    assert is_customer_visible("drafted — needs final pharmacist/legal sign-off") is True


def _make_record(**overrides: object) -> NutrientContent:
    defaults = dict(
        medication_class="diuretics",
        content_status=STATUS_LLM_DRAFTED_PENDING_REVIEW,
        nutrient_concern="Potassium or magnesium depletion risk",
        why_it_matters="draft text",
        foods_that_may_help=["bananas"],
        supplements_to_discuss=None,
        talk_to_pharmacist_if="draft prompt",
        clinical_source="draft citation",
    )
    defaults.update(overrides)
    return NutrientContent(**defaults)


def test_approve_record_as_is_sets_approved_status() -> None:
    record = _make_record()
    reviewed_at = datetime.now(timezone.utc)

    approve_record(record, edits=None, reviewer_name="Alex P.", reviewed_at=reviewed_at)

    assert record.content_status == STATUS_APPROVED
    assert record.reviewed_by == "Alex P."
    assert record.reviewed_at == reviewed_at
    assert record.why_it_matters == "draft text"


def test_approve_record_with_actual_edit_sets_approved_with_edits() -> None:
    record = _make_record()

    approve_record(
        record,
        edits={"why_it_matters": "edited text"},
        reviewer_name="Alex P.",
        reviewed_at=datetime.now(timezone.utc),
    )

    assert record.content_status == STATUS_APPROVED_WITH_EDITS
    assert record.why_it_matters == "edited text"


def test_approve_record_resubmitting_same_value_is_not_an_edit() -> None:
    record = _make_record()

    approve_record(
        record,
        edits={"why_it_matters": "draft text"},  # same as current value
        reviewer_name="Alex P.",
        reviewed_at=datetime.now(timezone.utc),
    )

    assert record.content_status == STATUS_APPROVED


def test_approve_record_edit_to_null_counts_as_edit() -> None:
    record = _make_record()

    approve_record(
        record,
        edits={"talk_to_pharmacist_if": None},
        reviewer_name="Alex P.",
        reviewed_at=datetime.now(timezone.utc),
    )

    assert record.content_status == STATUS_APPROVED_WITH_EDITS
    assert record.talk_to_pharmacist_if is None
