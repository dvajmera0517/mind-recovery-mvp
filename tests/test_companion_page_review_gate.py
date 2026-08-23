"""Companion-page rendering must gate on content_status, not on whether
individual fields happen to be populated — see content_review.is_customer_visible
and its use in companion_page.render_companion_page_html.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from mind_recovery_mvp.content_review import (
    STATUS_APPROVED,
    STATUS_APPROVED_WITH_EDITS,
    STATUS_LLM_DRAFTED_PENDING_REVIEW,
)
from mind_recovery_mvp.models import NutrientContent

FULLY_POPULATED_FIELDS = {
    "why_it_matters": "Some why-it-matters text.",
    "foods_that_may_help": ["food a", "food b"],
    "supplements_to_discuss": ["supplement a"],
    "talk_to_pharmacist_if": "Some discussion prompt.",
    "clinical_source": "Some citation.",
}


def _set_diuretics_status_and_fields(client: TestClient, content_status: str) -> None:
    with client.db_session_factory() as session:
        record = (
            session.query(NutrientContent)
            .filter_by(medication_class="diuretics")
            .one()
        )
        for field, value in FULLY_POPULATED_FIELDS.items():
            setattr(record, field, value)
        record.content_status = content_status
        session.commit()


def test_llm_drafted_pending_review_hides_all_fields_even_when_populated(
    client: TestClient,
) -> None:
    _set_diuretics_status_and_fields(client, STATUS_LLM_DRAFTED_PENDING_REVIEW)

    response = client.get("/companion-page/diuretics")
    assert response.status_code == 200
    body = response.text

    for value in FULLY_POPULATED_FIELDS.values():
        text = value if isinstance(value, str) else value[0]
        assert text not in body
    assert body.count("Pending pharmacist review") == 5


def test_approved_shows_real_content(client: TestClient) -> None:
    _set_diuretics_status_and_fields(client, STATUS_APPROVED)

    response = client.get("/companion-page/diuretics")
    assert response.status_code == 200
    body = response.text

    assert "Some why-it-matters text." in body
    assert "food a" in body
    assert "supplement a" in body
    assert "Some discussion prompt." in body
    assert "Some citation." in body
    assert "Pending pharmacist review" not in body


def test_approved_with_edits_shows_real_content(client: TestClient) -> None:
    _set_diuretics_status_and_fields(client, STATUS_APPROVED_WITH_EDITS)

    response = client.get("/companion-page/diuretics")
    assert response.status_code == 200
    assert "Some why-it-matters text." in response.text
    assert "Pending pharmacist review" not in response.text


def test_llm_drafted_pending_review_pdf_also_hides_content(
    client: TestClient,
) -> None:
    _set_diuretics_status_and_fields(client, STATUS_LLM_DRAFTED_PENDING_REVIEW)

    response = client.get("/companion-page/diuretics.pdf")
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
    # Can't grep text out of PDF bytes directly here; the HTML-path test
    # above covers the actual gating logic, this just confirms the PDF
    # route renders without error for a gated, fully-populated record.
