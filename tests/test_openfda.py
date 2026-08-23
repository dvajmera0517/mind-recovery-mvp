from __future__ import annotations

from unittest.mock import Mock, patch

import httpx
import pytest

from mind_recovery_mvp.openfda import get_fda_label_reference


def _mock_response(results: list[dict]) -> Mock:
    response = Mock(spec=httpx.Response)
    response.raise_for_status.return_value = None
    response.json.return_value = {"results": results}
    return response


def test_get_fda_label_reference_success() -> None:
    results = [
        {
            "openfda": {
                "brand_name": ["Metformin Hydrochloride"],
                "generic_name": ["METFORMIN HYDROCHLORIDE"],
            },
            "drug_interactions": ["7 DRUG INTERACTIONS Table 3 presents..."],
            "warnings_and_cautions": ["5 WARNINGS AND PRECAUTIONS Lactic Acidosis..."],
        }
    ]
    with patch(
        "mind_recovery_mvp.openfda.httpx.get", return_value=_mock_response(results)
    ) as mock_get:
        result = get_fda_label_reference("metformin")

    mock_get.assert_called_once()
    assert (
        mock_get.call_args.kwargs["params"]["search"]
        == 'openfda.generic_name.exact:"METFORMIN"'
    )
    assert result == {
        "label": "FDA label reference",
        "source_drug": "Metformin Hydrochloride",
        "drug_interactions": "7 DRUG INTERACTIONS Table 3 presents...",
        "warnings_and_cautions": "5 WARNINGS AND PRECAUTIONS Lactic Acidosis...",
    }


def test_get_fda_label_reference_uses_epc_query_for_class_names() -> None:
    with patch(
        "mind_recovery_mvp.openfda.httpx.get",
        return_value=_mock_response([{"openfda": {}, "drug_interactions": [], "warnings_and_cautions": []}]),
    ) as mock_get:
        get_fda_label_reference("statins")

    assert (
        mock_get.call_args.kwargs["params"]["search"]
        == 'openfda.pharm_class_epc:"HMG-CoA Reductase Inhibitor [EPC]"'
    )


def test_get_fda_label_reference_uses_epc_query_for_glp1() -> None:
    # Verified live: openfda.pharm_class_epc:"GLP-1 Receptor Agonist [EPC]"
    # matches liraglutide's real FDA label.
    with patch(
        "mind_recovery_mvp.openfda.httpx.get",
        return_value=_mock_response(
            [{"openfda": {}, "drug_interactions": [], "warnings_and_cautions": []}]
        ),
    ) as mock_get:
        get_fda_label_reference("glp1")

    assert (
        mock_get.call_args.kwargs["params"]["search"]
        == 'openfda.pharm_class_epc:"GLP-1 Receptor Agonist [EPC]"'
    )


def test_get_fda_label_reference_falls_back_to_warnings_field() -> None:
    # Real-world case (furosemide): some labels use the older "warnings"
    # section instead of "warnings_and_cautions".
    results = [
        {
            "openfda": {"brand_name": ["Furosemide"]},
            "drug_interactions": ["Some interaction text."],
            "warnings": ["Some warnings text under the old section name."],
        }
    ]
    with patch(
        "mind_recovery_mvp.openfda.httpx.get", return_value=_mock_response(results)
    ):
        result = get_fda_label_reference("diuretics")

    assert result["warnings_and_cautions"] == "Some warnings text under the old section name."


def test_get_fda_label_reference_truncates_long_text() -> None:
    long_text = "x" * 5000
    results = [
        {
            "openfda": {"brand_name": ["Test Drug"]},
            "drug_interactions": [long_text],
            "warnings_and_cautions": [],
        }
    ]
    with patch(
        "mind_recovery_mvp.openfda.httpx.get", return_value=_mock_response(results)
    ):
        result = get_fda_label_reference("metformin")

    assert len(result["drug_interactions"]) == 1500
    assert result["drug_interactions"].endswith("…")


def test_get_fda_label_reference_unmapped_medication_class_returns_none_without_network_call() -> None:
    with patch("mind_recovery_mvp.openfda.httpx.get") as mock_get:
        result = get_fda_label_reference("opioids")

    mock_get.assert_not_called()
    assert result is None


def test_get_fda_label_reference_no_results_returns_none() -> None:
    with patch(
        "mind_recovery_mvp.openfda.httpx.get", return_value=_mock_response([])
    ):
        result = get_fda_label_reference("metformin")

    assert result is None


def test_get_fda_label_reference_network_error_returns_none() -> None:
    with patch(
        "mind_recovery_mvp.openfda.httpx.get",
        side_effect=httpx.ConnectError("connection failed"),
    ):
        result = get_fda_label_reference("metformin")

    assert result is None


def test_get_fda_label_reference_sends_api_key_when_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENFDA_API_KEY", "real-key")
    with patch(
        "mind_recovery_mvp.openfda.httpx.get", return_value=_mock_response([{"openfda": {}}])
    ) as mock_get:
        get_fda_label_reference("metformin")

    assert mock_get.call_args.kwargs["params"]["api_key"] == "real-key"


def test_get_fda_label_reference_omits_api_key_when_not_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENFDA_API_KEY", raising=False)
    with patch(
        "mind_recovery_mvp.openfda.httpx.get", return_value=_mock_response([{"openfda": {}}])
    ) as mock_get:
        get_fda_label_reference("metformin")

    assert "api_key" not in mock_get.call_args.kwargs["params"]
