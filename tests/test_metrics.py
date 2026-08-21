from __future__ import annotations

from fastapi.testclient import TestClient

# NOTE: tests in this file share one module-scoped db (see tests/conftest.py)
# and each test's fill-event/companion-page calls accumulate in it, so
# ordering matters: tests that need a medication_class untouched by prior
# fill-events must run before any other test in this file logs one for that
# class. Test order below follows file/definition order (default pytest
# behavior, no randomization plugin installed).


def _metrics_for(body: dict, medication_class: str) -> dict:
    return next(
        entry
        for entry in body["medication_classes"]
        if entry["medication_class"] == medication_class
    )


def test_metrics_starts_at_zero_for_all_seeded_classes(client: TestClient) -> None:
    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.json()

    classes = {entry["medication_class"] for entry in body["medication_classes"]}
    assert classes == {"metformin", "statins", "diuretics", "ppi"}
    for entry in body["medication_classes"]:
        assert entry["fill_event_count"] == 0
        assert entry["companion_page_count"] == 0
        assert entry["companion_page_rate"] is None


def test_metrics_companion_page_without_prior_fill_event_is_a_noop(
    client: TestClient,
) -> None:
    # Must run before any other test in this file logs a fill-event for
    # "metformin" (see module note above).
    before = _metrics_for(client.get("/metrics").json(), "metformin")
    assert before["fill_event_count"] == 0

    client.get("/companion-page/metformin")

    after = _metrics_for(client.get("/metrics").json(), "metformin")
    assert after["fill_event_count"] == 0
    assert after["companion_page_count"] == 0


def test_metrics_counts_fill_event_calls(client: TestClient) -> None:
    client.post("/fill-event", json={"medication_class": "metformin"})
    client.post("/fill-event", json={"medication_class": "metformin"})
    client.post("/fill-event", json={"medication_class": "statins"})

    body = client.get("/metrics").json()

    assert _metrics_for(body, "metformin")["fill_event_count"] == 2
    assert _metrics_for(body, "statins")["fill_event_count"] == 1
    assert _metrics_for(body, "diuretics")["fill_event_count"] == 0


def test_metrics_counts_companion_page_requests_after_fill_event(
    client: TestClient,
) -> None:
    client.post("/fill-event", json={"medication_class": "diuretics"})
    client.get("/companion-page/diuretics")

    body = client.get("/metrics").json()
    diuretics = _metrics_for(body, "diuretics")

    assert diuretics["fill_event_count"] == 1
    assert diuretics["companion_page_count"] == 1
    assert diuretics["companion_page_rate"] == 1.0


def test_metrics_companion_page_pdf_request_also_counts(client: TestClient) -> None:
    client.post("/fill-event", json={"medication_class": "ppi"})
    client.get("/companion-page/ppi.pdf")

    body = client.get("/metrics").json()
    ppi = _metrics_for(body, "ppi")

    assert ppi["fill_event_count"] == 1
    assert ppi["companion_page_count"] == 1


def test_metrics_unknown_class_fill_event_is_not_logged(client: TestClient) -> None:
    before = client.get("/metrics").json()
    total_before = sum(e["fill_event_count"] for e in before["medication_classes"])

    client.post("/fill-event", json={"medication_class": "opioids"})

    after = client.get("/metrics").json()
    total_after = sum(e["fill_event_count"] for e in after["medication_classes"])

    assert total_after == total_before
    assert "opioids" not in {e["medication_class"] for e in after["medication_classes"]}


def test_metrics_includes_stand_in_disclaimer_note(client: TestClient) -> None:
    body = client.get("/metrics").json()
    assert "not real purchases" in body["note"]
