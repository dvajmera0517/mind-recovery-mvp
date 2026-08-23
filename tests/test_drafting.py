from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from mind_recovery_mvp.content_review import STATUS_LLM_DRAFTED_PENDING_REVIEW
from mind_recovery_mvp.drafting import (
    DraftedFields,
    apply_draft_to_record,
    draft_content_fields,
)
from mind_recovery_mvp.models import NutrientContent


def _mock_client(parsed: DraftedFields | None, stop_reason: str = "end_turn") -> MagicMock:
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.parsed_output = parsed
    fake_response.stop_reason = stop_reason
    fake_client.messages.parse.return_value = fake_response
    return fake_client


def test_draft_content_fields_returns_drafted_values() -> None:
    parsed = DraftedFields(
        why_it_matters="Statins block the mevalonate pathway.",
        foods_that_may_help=["organ meats", "fatty fish"],
        supplements_to_discuss=None,
        talk_to_pharmacist_if="muscle aches or weakness",
        clinical_source="whatever the model happened to say",
    )
    fake_client = _mock_client(parsed)

    with patch(
        "mind_recovery_mvp.drafting.anthropic.Anthropic", return_value=fake_client
    ):
        result = draft_content_fields(
            medication_class="statins",
            nutrient_concern="CoQ10 association",
            evidence_excerpt="Statins block the mevalonate pathway...",
            citation_label="General pharmacology literature — needs a real citation.",
            api_key="test-key",
        )

    assert result["why_it_matters"] == "Statins block the mevalonate pathway."
    assert result["foods_that_may_help"] == ["organ meats", "fatty fish"]
    assert result["supplements_to_discuss"] is None
    assert result["talk_to_pharmacist_if"] == "muscle aches or weakness"


def test_draft_content_fields_forces_clinical_source_to_citation_label() -> None:
    # Even if the model outputs something else for clinical_source, the
    # returned value must be exactly citation_label — never trusted from
    # the model, even when it looks plausible.
    parsed = DraftedFields(
        why_it_matters="text",
        foods_that_may_help=None,
        supplements_to_discuss=None,
        talk_to_pharmacist_if=None,
        clinical_source="Journal of Made-Up Medicine, 2019",
    )
    fake_client = _mock_client(parsed)

    with patch(
        "mind_recovery_mvp.drafting.anthropic.Anthropic", return_value=fake_client
    ):
        result = draft_content_fields(
            medication_class="statins",
            nutrient_concern="CoQ10 association",
            evidence_excerpt="excerpt text",
            citation_label="The real citation_label to carry forward.",
            api_key="test-key",
        )

    assert result["clinical_source"] == "The real citation_label to carry forward."


def test_draft_content_fields_uses_opus_5_model_and_includes_excerpt() -> None:
    parsed = DraftedFields(
        why_it_matters=None,
        foods_that_may_help=None,
        supplements_to_discuss=None,
        talk_to_pharmacist_if=None,
        clinical_source="c",
    )
    fake_client = _mock_client(parsed)

    with patch(
        "mind_recovery_mvp.drafting.anthropic.Anthropic", return_value=fake_client
    ) as mock_anthropic_cls:
        draft_content_fields(
            medication_class="ppi",
            nutrient_concern="Magnesium, Calcium, and Vitamin B12 concerns",
            evidence_excerpt="UNIQUE_EXCERPT_MARKER_XYZ",
            citation_label="citation",
            api_key="the-api-key",
        )

    mock_anthropic_cls.assert_called_once_with(api_key="the-api-key")
    call_kwargs = fake_client.messages.parse.call_args.kwargs
    assert call_kwargs["model"] == "claude-opus-5"
    assert call_kwargs["output_format"] is DraftedFields
    user_message = call_kwargs["messages"][0]["content"]
    assert "UNIQUE_EXCERPT_MARKER_XYZ" in user_message


def test_draft_content_fields_raises_if_no_parsed_output() -> None:
    fake_client = _mock_client(parsed=None, stop_reason="refusal")

    with patch(
        "mind_recovery_mvp.drafting.anthropic.Anthropic", return_value=fake_client
    ):
        with pytest.raises(RuntimeError, match="did not return a parsed draft"):
            draft_content_fields(
                medication_class="statins",
                nutrient_concern="CoQ10 association",
                evidence_excerpt="excerpt",
                citation_label="citation",
                api_key="test-key",
            )


def test_apply_draft_to_record_sets_fields_status_and_excerpt() -> None:
    record = NutrientContent(
        medication_class="statins",
        content_status="PLACEHOLDER — ...",
        nutrient_concern="CoQ10 association",
    )
    drafted = {
        "why_it_matters": "text",
        "foods_that_may_help": ["organ meats"],
        "supplements_to_discuss": ["CoQ10 supplements"],
        "talk_to_pharmacist_if": "muscle aches",
        "clinical_source": "citation label text",
    }

    apply_draft_to_record(record, drafted, "the source excerpt")

    assert record.why_it_matters == "text"
    assert record.foods_that_may_help == ["organ meats"]
    assert record.supplements_to_discuss == ["CoQ10 supplements"]
    assert record.talk_to_pharmacist_if == "muscle aches"
    assert record.clinical_source == "citation label text"
    assert record.evidence_excerpt == "the source excerpt"
    assert record.content_status == STATUS_LLM_DRAFTED_PENDING_REVIEW
