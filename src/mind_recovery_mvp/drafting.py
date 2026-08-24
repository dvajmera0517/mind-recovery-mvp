"""LLM-assisted content drafting for the placeholder medication classes
that have an evidence excerpt (statins, diuretics, ppi, glp1 — see
evidence_excerpts.py), from the fixed excerpt for that class — a real,
live Claude API call, not a stub.

Output is always stored with content_status =
STATUS_LLM_DRAFTED_PENDING_REVIEW, never "approved" — see
content_review.py and scripts/review_content.py. A human must review it
before companion_page.py will render it to a customer.

ANTHROPIC_API_KEY is only required to actually call draft_content_fields
(i.e. to run scripts/draft_content.py) — the main API server never
imports this module and never needs the key.
"""

from __future__ import annotations

from typing import Any

import anthropic
from pydantic import BaseModel

from mind_recovery_mvp.content_review import (
    CONTENT_ORIGIN_LLM,
    STATUS_LLM_DRAFTED_PENDING_REVIEW,
)
from mind_recovery_mvp.models import NutrientContent

DRAFTING_MODEL = "claude-opus-5"
MAX_TOKENS = 2048

SYSTEM_PROMPT = (
    "You are drafting patient-education content for a nutrient-depletion "
    "companion page. You will be given ONE evidence excerpt as your only "
    "source material. Rules, no exceptions:\n"
    "1. Use ONLY the evidence excerpt provided. Do not add clinical "
    "claims, foods, supplements, or discussion prompts that are not "
    "directly supported by the excerpt — even if they are true, common "
    "knowledge, or something you're confident about from general medical "
    "training. This excerpt is the entire source of truth for this task.\n"
    "2. If the excerpt does not clearly support a field, output null for "
    "that field rather than inventing something plausible-sounding.\n"
    "3. For clinical_source, output exactly the citation label you are "
    "given, verbatim, word for word. Do not invent a more specific "
    "citation, a page number, a URL, or a publication you believe might "
    "be the real source — even if you think you know it.\n"
    "4. Keep language plain and patient-facing."
)


class DraftedFields(BaseModel):
    why_it_matters: str | None
    foods_that_may_help: list[str] | None
    supplements_to_discuss: list[str] | None
    talk_to_pharmacist_if: str | None
    clinical_source: str | None


def _build_user_prompt(
    medication_class: str, nutrient_concern: str, evidence_excerpt: str, citation_label: str
) -> str:
    return (
        f"Medication class: {medication_class}\n"
        f"Nutrient concern (already known — do not redraft this): "
        f"{nutrient_concern}\n\n"
        f"Evidence excerpt (your ONLY source material):\n{evidence_excerpt}\n\n"
        f"Citation label to carry forward verbatim as clinical_source:\n"
        f"{citation_label}\n\n"
        "Draft:\n"
        "- why_it_matters: 1-2 plain-language sentences explaining the "
        "mechanism, grounded only in the excerpt.\n"
        "- foods_that_may_help: the specific foods named in the excerpt, "
        "as a list — or null if none are named.\n"
        "- supplements_to_discuss: any supplements named in the excerpt, "
        "as a list — or null if none are named.\n"
        "- talk_to_pharmacist_if: the discussion prompt from the excerpt "
        "— or null if the excerpt doesn't suggest one.\n"
        "- clinical_source: the citation label above, copied verbatim."
    )


def draft_content_fields(
    *,
    medication_class: str,
    nutrient_concern: str,
    evidence_excerpt: str,
    citation_label: str,
    api_key: str,
) -> dict[str, Any]:
    """Call Claude to draft the four content fields from evidence_excerpt.

    clinical_source in the returned dict is always citation_label,
    regardless of what the model output — enforced here rather than
    trusted, since an invented citation must never reach the content
    store even if the model imperfectly follows the system prompt.
    """
    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.parse(
        model=DRAFTING_MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": _build_user_prompt(
                    medication_class, nutrient_concern, evidence_excerpt, citation_label
                ),
            }
        ],
        output_format=DraftedFields,
    )

    drafted = response.parsed_output
    if drafted is None:
        raise RuntimeError(
            f"Claude did not return a parsed draft for {medication_class!r} "
            f"(stop_reason={response.stop_reason!r})."
        )

    return {
        "why_it_matters": drafted.why_it_matters,
        "foods_that_may_help": drafted.foods_that_may_help,
        "supplements_to_discuss": drafted.supplements_to_discuss,
        "talk_to_pharmacist_if": drafted.talk_to_pharmacist_if,
        "clinical_source": citation_label,
    }


def apply_draft_to_record(
    record: NutrientContent, drafted: dict[str, Any], evidence_excerpt: str
) -> None:
    """Write a draft_content_fields() result onto record, in place.

    Never sets content_status to "approved" — always the pending-review
    status, and always keeps evidence_excerpt attached so a reviewer can
    see what the draft came from.
    """
    record.why_it_matters = drafted["why_it_matters"]
    record.foods_that_may_help = drafted["foods_that_may_help"]
    record.supplements_to_discuss = drafted["supplements_to_discuss"]
    record.talk_to_pharmacist_if = drafted["talk_to_pharmacist_if"]
    record.clinical_source = drafted["clinical_source"]
    record.evidence_excerpt = evidence_excerpt
    record.content_status = STATUS_LLM_DRAFTED_PENDING_REVIEW
    record.content_origin = CONTENT_ORIGIN_LLM
