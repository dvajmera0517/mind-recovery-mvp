from __future__ import annotations

from unittest.mock import Mock, patch

import httpx

from mind_recovery_mvp.rxclass import classify_medication_class


def _mock_response(class_items: list[tuple[str, str]]) -> Mock:
    """class_items: list of (classType, className) pairs."""
    response = Mock(spec=httpx.Response)
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "rxclassDrugInfoList": {
            "rxclassDrugInfo": [
                {
                    "minConcept": {"rxcui": "1", "name": "x", "tty": "IN"},
                    "rxclassMinConceptItem": {
                        "classId": "X",
                        "className": class_name,
                        "classType": class_type,
                    },
                    "rela": "",
                    "relaSource": "",
                }
                for class_type, class_name in class_items
            ]
        }
    }
    return response


def test_classify_medication_class_metformin() -> None:
    payload = [
        ("ATC1-4", "Biguanides"),
        ("EPC", "Biguanide"),
        ("DISEASE", "Diabetes Mellitus, Type 2"),
    ]
    with patch(
        "mind_recovery_mvp.rxclass.httpx.get", return_value=_mock_response(payload)
    ) as mock_get:
        result = classify_medication_class("metformin")

    mock_get.assert_called_once()
    assert mock_get.call_args.kwargs["params"]["drugName"] == "metformin"
    assert result == "metformin"


def test_classify_medication_class_statin() -> None:
    # Real RxClass output for atorvastatin: EPC/ATC never literally say
    # "statin", only "HMG-CoA Reductase Inhibitor" / "HMG CoA reductase
    # inhibitors" — confirming the keyword list needs that exact phrase.
    payload = [
        ("ATC1-4", "HMG CoA reductase inhibitors"),
        ("EPC", "HMG-CoA Reductase Inhibitor"),
        ("VA", "ANTILIPEMIC AGENTS"),
    ]
    with patch(
        "mind_recovery_mvp.rxclass.httpx.get", return_value=_mock_response(payload)
    ):
        result = classify_medication_class("atorvastatin")

    assert result == "statins"


def test_classify_medication_class_diuretic_via_non_epc_class() -> None:
    # Real RxClass output for spironolactone: EPC says "Aldosterone
    # Antagonist" (no "diuretic" in it at all) — only VA/ATC say
    # "diuretic". Confirms scanning all classification systems, not just
    # EPC, is necessary.
    payload = [
        ("EPC", "Aldosterone Antagonist"),
        ("VA", "POTASSIUM SPARING/COMBINATIONS DIURETICS"),
        ("ATC1-4", "Low-ceiling diuretics and potassium-sparing agents"),
    ]
    with patch(
        "mind_recovery_mvp.rxclass.httpx.get", return_value=_mock_response(payload)
    ):
        result = classify_medication_class("spironolactone")

    assert result == "diuretics"


def test_classify_medication_class_ppi() -> None:
    payload = [
        ("MOA", "Proton Pump Inhibitors"),
        ("EPC", "Proton Pump Inhibitor"),
        ("ATC1-4", "Proton pump inhibitors"),
    ]
    with patch(
        "mind_recovery_mvp.rxclass.httpx.get", return_value=_mock_response(payload)
    ):
        result = classify_medication_class("omeprazole")

    assert result == "ppi"


def test_classify_medication_class_unmapped_drug_returns_none() -> None:
    payload = [
        ("EPC", "Nonsteroidal Anti-inflammatory Drug"),
        ("VA", "ANALGESICS,NONNARCOTIC"),
    ]
    with patch(
        "mind_recovery_mvp.rxclass.httpx.get", return_value=_mock_response(payload)
    ):
        result = classify_medication_class("ibuprofen")

    assert result is None


def test_classify_medication_class_network_error_returns_none() -> None:
    with patch(
        "mind_recovery_mvp.rxclass.httpx.get",
        side_effect=httpx.ConnectError("connection failed"),
    ):
        result = classify_medication_class("metformin")

    assert result is None


def test_classify_medication_class_no_results_returns_none() -> None:
    response = Mock(spec=httpx.Response)
    response.raise_for_status.return_value = None
    response.json.return_value = {"rxclassDrugInfoList": {}}
    with patch("mind_recovery_mvp.rxclass.httpx.get", return_value=response):
        result = classify_medication_class("not-a-real-drug")

    assert result is None
