from __future__ import annotations

from fastapi.testclient import TestClient

DISCLAIMER = (
    "This is educational information, not medical advice. Talk to your "
    "pharmacist or provider before starting any supplement."
)


def test_companion_page_html_metformin_shows_all_populated_fields(
    client: TestClient,
) -> None:
    response = client.get("/companion-page/metformin")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    body = response.text

    assert "Metformin" in body
    assert "Vitamin B12 depletion" in body
    assert (
        "Long-term use of metformin may be associated with reduced "
        "Vitamin B12 levels in some patients." in body
    )
    assert "eggs" in body
    assert "Vitamin B12 supplements" in body
    assert "you experience unusual fatigue, tingling, or numbness" in body
    assert "TRC Healthcare Natural Medicines" in body
    assert DISCLAIMER in body
    assert "Pending pharmacist review" not in body
    # Human-authored from the start, never drafted/reviewed through the
    # pipeline — distinct wording from the sample/LLM provenance lines
    # (no "pharmacist-reviewed" claim tacked on, since nothing was
    # reviewed here — it was written correctly the first time).
    assert "Content origin: pharmacist-authored" in body


def test_companion_page_html_ppi_shows_pending_for_null_fields(
    client: TestClient,
) -> None:
    response = client.get("/companion-page/ppi")
    assert response.status_code == 200
    body = response.text

    assert "PPI" in body
    assert "Magnesium, Calcium, and Vitamin B12 concerns" in body
    assert DISCLAIMER in body
    # why_it_matters, foods_that_may_help, supplements_to_discuss,
    # talk_to_pharmacist_if, and clinical_source are all null for ppi.
    assert body.count("Pending pharmacist review") == 5


def test_companion_page_html_statins_placeholder_hides_all_fields(
    client: TestClient,
) -> None:
    # statins is still content_status PLACEHOLDER, so even though
    # supplements_to_discuss is populated in the seed data, the render
    # gate hides it along with everything else — a placeholder record
    # never shows real content, regardless of which individual fields
    # happen to be filled in.
    response = client.get("/companion-page/statins")
    assert response.status_code == 200
    body = response.text

    assert "CoQ10 association" in body
    assert "CoQ10 supplements — confirm appropriateness with pharmacist" not in body
    assert body.count("Pending pharmacist review") == 5


def test_companion_page_html_unknown_class_returns_404(client: TestClient) -> None:
    response = client.get("/companion-page/opioids")
    assert response.status_code == 404
    assert "opioids" in response.json()["detail"]


def test_companion_page_pdf_metformin_returns_valid_pdf(client: TestClient) -> None:
    response = client.get("/companion-page/metformin.pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 500


def test_companion_page_pdf_renders_placeholder_heavy_record(
    client: TestClient,
) -> None:
    # ppi has nulls on 5 of the 7 rendered fields; confirm the pending-text
    # branch doesn't break PDF rendering.
    response = client.get("/companion-page/ppi.pdf")
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_companion_page_pdf_unknown_class_returns_404(client: TestClient) -> None:
    response = client.get("/companion-page/opioids.pdf")
    assert response.status_code == 404
    assert "opioids" in response.json()["detail"]
