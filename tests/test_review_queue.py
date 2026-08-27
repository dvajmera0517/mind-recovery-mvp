"""GET /review-queue and POST /review-queue/{class}/approve — the HTTP
surface scripts/review_content.py's CLI logic is exposed through, so the
Streamlit review UI (or any other client) can review/approve without
touching the DB directly. Thin wrapper around content_review.approve_record
— see tests/test_content_review.py for that function's own unit tests.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from mind_recovery_mvp.content_review import (
    CONTENT_ORIGIN_LLM,
    STATUS_APPROVED,
    STATUS_APPROVED_WITH_EDITS,
    STATUS_LLM_DRAFTED_PENDING_REVIEW,
    STATUS_SAMPLE_CONTENT_PENDING_REVIEW,
)
from mind_recovery_mvp.models import NutrientContent


def _set_status(
    client: TestClient,
    medication_class: str,
    content_status: str,
    **field_overrides: object,
) -> None:
    with client.db_session_factory() as session:
        record = (
            session.query(NutrientContent)
            .filter_by(medication_class=medication_class)
            .one()
        )
        record.content_status = content_status
        for field, value in field_overrides.items():
            setattr(record, field, value)
        session.commit()


def test_review_queue_lists_only_pending_review_records(client: TestClient) -> None:
    _set_status(client, "diuretics", STATUS_LLM_DRAFTED_PENDING_REVIEW)
    _set_status(client, "ppi", STATUS_SAMPLE_CONTENT_PENDING_REVIEW)

    response = client.get("/review-queue")
    assert response.status_code == 200
    items = response.json()["items"]

    classes = {item["medication_class"] for item in items}
    assert {"diuretics", "ppi"} <= classes
    for item in items:
        assert item["content_status"] in {
            STATUS_LLM_DRAFTED_PENDING_REVIEW,
            STATUS_SAMPLE_CONTENT_PENDING_REVIEW,
        }


def test_review_queue_item_includes_evidence_excerpt_and_origin(
    client: TestClient,
) -> None:
    _set_status(
        client,
        "diuretics",
        STATUS_LLM_DRAFTED_PENDING_REVIEW,
        evidence_excerpt="Some excerpt.",
        content_origin=CONTENT_ORIGIN_LLM,
    )

    items = client.get("/review-queue").json()["items"]
    item = next(i for i in items if i["medication_class"] == "diuretics")
    assert item["evidence_excerpt"] == "Some excerpt."
    assert item["content_origin"] == CONTENT_ORIGIN_LLM


def test_approve_review_queue_item_as_is(client: TestClient) -> None:
    _set_status(
        client,
        "glp1",
        STATUS_SAMPLE_CONTENT_PENDING_REVIEW,
        why_it_matters="Draft text.",
    )

    response = client.post(
        "/review-queue/glp1/approve",
        json={"reviewer_name": "Alex P."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["content_status"] == STATUS_APPROVED
    assert body["why_it_matters"] == "Draft text."
    assert body["reviewed_by"] == "Alex P."
    assert body["reviewed_at"] is not None

    queue = client.get("/review-queue").json()["items"]
    assert not any(i["medication_class"] == "glp1" for i in queue)


def test_approve_review_queue_item_with_edits_marks_approved_with_edits(
    client: TestClient,
) -> None:
    _set_status(
        client,
        "statins",
        STATUS_LLM_DRAFTED_PENDING_REVIEW,
        why_it_matters="Draft text.",
    )

    response = client.post(
        "/review-queue/statins/approve",
        json={
            "reviewer_name": "Alex P.",
            "edits": {"why_it_matters": "Edited text."},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["content_status"] == STATUS_APPROVED_WITH_EDITS
    assert body["why_it_matters"] == "Edited text."


def test_approve_review_queue_item_rejects_unknown_field(client: TestClient) -> None:
    _set_status(client, "statins", STATUS_LLM_DRAFTED_PENDING_REVIEW)

    response = client.post(
        "/review-queue/statins/approve",
        json={"reviewer_name": "Alex P.", "edits": {"medication_class": "ppi"}},
    )
    assert response.status_code == 422


def test_approve_review_queue_item_rejects_when_not_pending(client: TestClient) -> None:
    _set_status(client, "statins", STATUS_APPROVED)

    response = client.post(
        "/review-queue/statins/approve",
        json={"reviewer_name": "Alex P."},
    )
    assert response.status_code == 409


def test_approve_review_queue_item_unknown_class_404s(client: TestClient) -> None:
    response = client.post(
        "/review-queue/not-a-real-class/approve",
        json={"reviewer_name": "Alex P."},
    )
    assert response.status_code == 404
