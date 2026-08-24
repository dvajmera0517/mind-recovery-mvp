#!/usr/bin/env python3
"""Draft placeholder clinical content for one medication class using
Claude, from the fixed evidence excerpt in
src/mind_recovery_mvp/evidence_excerpts.py.

Output is stored with content_status =
"llm_drafted_pending_pharmacist_review" — never "approved". Review it
with scripts/review_content.py before it's safe to show a customer (see
companion_page.py's render gate).

Usage:
    python scripts/draft_content.py <statins|diuretics|ppi|glp1>

Requires ANTHROPIC_API_KEY — only for running this script, not for the
main API server. Get a key at https://console.anthropic.com/settings/keys
and set it in .env or as an environment variable.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
load_dotenv(REPO_ROOT / ".env")

from mind_recovery_mvp.evidence_excerpts import EVIDENCE_EXCERPTS  # noqa: E402

# Derived from evidence_excerpts.py rather than hardcoded: a class is
# draftable exactly when real source material exists for it, not based on
# membership in the full medication-class list (seed_data.py) — glp1
# wasn't draftable until an evidence excerpt existed for it.
DRAFTABLE_CLASSES = {e["medication_class"] for e in EVIDENCE_EXCERPTS}


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in DRAFTABLE_CLASSES:
        choices = "|".join(sorted(DRAFTABLE_CLASSES))
        print(f"Usage: python scripts/draft_content.py <{choices}>", file=sys.stderr)
        return 1
    medication_class = argv[0]

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "ANTHROPIC_API_KEY is not set. This is only needed to run "
            "scripts/draft_content.py — the main API server doesn't need "
            "it. Get a key at "
            "https://console.anthropic.com/settings/keys and set "
            "ANTHROPIC_API_KEY=<your-key> in .env or as an environment "
            "variable.",
            file=sys.stderr,
        )
        return 1

    from mind_recovery_mvp.content_review import STATUS_LLM_DRAFTED_PENDING_REVIEW
    from mind_recovery_mvp.db import SessionLocal, init_db
    from mind_recovery_mvp.drafting import apply_draft_to_record, draft_content_fields
    from mind_recovery_mvp.loader import load_seed_data
    from mind_recovery_mvp.models import NutrientContent

    excerpt_record = next(
        (e for e in EVIDENCE_EXCERPTS if e["medication_class"] == medication_class),
        None,
    )
    if excerpt_record is None:
        print(f"No evidence excerpt found for {medication_class!r}.", file=sys.stderr)
        return 1

    init_db()
    with SessionLocal() as session:
        load_seed_data(session)
        record = (
            session.query(NutrientContent)
            .filter_by(medication_class=medication_class)
            .one()
        )

        print(f"Drafting content for {medication_class!r} via Claude...")
        drafted = draft_content_fields(
            medication_class=medication_class,
            nutrient_concern=record.nutrient_concern,
            evidence_excerpt=excerpt_record["evidence_excerpt"],
            citation_label=excerpt_record["citation_label"],
            api_key=api_key,
        )
        apply_draft_to_record(record, drafted, excerpt_record["evidence_excerpt"])
        session.commit()

        print(f"Drafted fields for {medication_class!r}:")
        for field in (
            "why_it_matters",
            "foods_that_may_help",
            "supplements_to_discuss",
            "talk_to_pharmacist_if",
            "clinical_source",
        ):
            print(f"  {field}: {getattr(record, field)!r}")
        print(f"content_status = {STATUS_LLM_DRAFTED_PENDING_REVIEW!r}")
        print("Run `python scripts/review_content.py` to review before approval.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
