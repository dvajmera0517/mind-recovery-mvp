from __future__ import annotations

from mind_recovery_mvp.content_review import (
    CONTENT_ORIGIN_SAMPLE,
    STATUS_SAMPLE_CONTENT_PENDING_REVIEW,
)
from mind_recovery_mvp.models import NutrientContent
from mind_recovery_mvp.sample_content import (
    SAMPLE_CONTENT,
    apply_sample_content_to_record,
)


def test_sample_content_covers_all_four_placeholder_classes() -> None:
    classes = {r["medication_class"] for r in SAMPLE_CONTENT}
    assert classes == {"statins", "diuretics", "ppi", "glp1"}


def test_sample_content_status_matches_pending_review_constant() -> None:
    for record in SAMPLE_CONTENT:
        assert record["content_status"] == STATUS_SAMPLE_CONTENT_PENDING_REVIEW


def test_sample_content_no_field_is_missing() -> None:
    required_keys = {
        "medication_class",
        "content_status",
        "nutrient_concern",
        "why_it_matters",
        "foods_that_may_help",
        "supplements_to_discuss",
        "talk_to_pharmacist_if",
        "clinical_source",
    }
    for record in SAMPLE_CONTENT:
        assert required_keys <= set(record.keys())


def test_apply_sample_content_to_record_sets_fields_status_and_origin() -> None:
    record = NutrientContent(
        medication_class="statins",
        content_status="PLACEHOLDER — foods, why-it-matters, and discussion "
        "prompt not specified in source; pharmacist/dietitian must draft "
        "and cite before use",
        nutrient_concern="CoQ10 association",
    )
    sample_record = next(
        r for r in SAMPLE_CONTENT if r["medication_class"] == "statins"
    )

    apply_sample_content_to_record(record, sample_record)

    assert record.why_it_matters == sample_record["why_it_matters"]
    assert record.foods_that_may_help == sample_record["foods_that_may_help"]
    assert record.supplements_to_discuss == sample_record["supplements_to_discuss"]
    assert record.talk_to_pharmacist_if == sample_record["talk_to_pharmacist_if"]
    assert record.clinical_source == sample_record["clinical_source"]
    assert record.content_status == STATUS_SAMPLE_CONTENT_PENDING_REVIEW
    assert record.content_origin == CONTENT_ORIGIN_SAMPLE
    # Sample content isn't drafted from an excerpt — nothing to attach.
    assert record.evidence_excerpt is None
