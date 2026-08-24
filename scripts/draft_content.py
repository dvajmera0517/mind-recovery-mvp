#!/usr/bin/env python3
"""Draft placeholder clinical content for one medication class.

Two modes:
  - Default (no flags): loads hand-written sample content from
    sample_content.json. No API call, no ANTHROPIC_API_KEY needed.
    content_status becomes "sample_content_pending_pharmacist_review".
  - --use-llm: calls Claude to draft from the fixed evidence excerpt in
    evidence_excerpts.py. Requires ANTHROPIC_API_KEY.
    content_status becomes "llm_drafted_pending_pharmacist_review".

Either way, this is still just a draft: review it with
scripts/review_content.py before it's safe to show a customer (see
companion_page.py's render gate) — neither mode ever marks anything
"approved".

Usage:
    python scripts/draft_content.py <statins|diuretics|ppi|glp1>
    python scripts/draft_content.py <statins|diuretics|ppi|glp1> --use-llm

--use-llm requires ANTHROPIC_API_KEY — only for that mode, not for the
main API server and not for the default sample-content mode. Get a key
at https://console.anthropic.com/settings/keys and set it in .env or as
an environment variable.
"""

from __future__ import annotations

import argparse
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
from mind_recovery_mvp.sample_content import SAMPLE_CONTENT  # noqa: E402

LLM_DRAFTABLE_CLASSES = {e["medication_class"] for e in EVIDENCE_EXCERPTS}
SAMPLE_DRAFTABLE_CLASSES = {s["medication_class"] for s in SAMPLE_CONTENT}


def _print_drafted_fields(record, status_label: str) -> None:
    print(f"Drafted fields for {record.medication_class!r}:")
    for field in (
        "why_it_matters",
        "foods_that_may_help",
        "supplements_to_discuss",
        "talk_to_pharmacist_if",
        "clinical_source",
    ):
        print(f"  {field}: {getattr(record, field)!r}")
    print(f"content_status = {status_label!r}")
    print("Run `python scripts/review_content.py` to review before approval.")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Draft placeholder clinical content for one medication class."
    )
    parser.add_argument(
        "medication_class",
        choices=sorted(SAMPLE_DRAFTABLE_CLASSES | LLM_DRAFTABLE_CLASSES),
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help=(
            "Call the real Claude API to draft from evidence_excerpts.py "
            "instead of loading sample_content.json. Requires "
            "ANTHROPIC_API_KEY."
        ),
    )
    args = parser.parse_args(argv)
    medication_class = args.medication_class

    from mind_recovery_mvp.content_review import (
        STATUS_LLM_DRAFTED_PENDING_REVIEW,
        STATUS_SAMPLE_CONTENT_PENDING_REVIEW,
    )
    from mind_recovery_mvp.db import SessionLocal, init_db
    from mind_recovery_mvp.loader import load_seed_data
    from mind_recovery_mvp.models import NutrientContent

    if args.use_llm:
        if medication_class not in LLM_DRAFTABLE_CLASSES:
            print(
                f"{medication_class!r} has no evidence excerpt in "
                "evidence_excerpts.py — can't use --use-llm for it.",
                file=sys.stderr,
            )
            return 1

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print(
                "ANTHROPIC_API_KEY is not set. This is only needed for "
                "--use-llm — the main API server and the default "
                "sample-content mode don't need it. Get a key at "
                "https://console.anthropic.com/settings/keys and set "
                "ANTHROPIC_API_KEY=<your-key> in .env or as an "
                "environment variable.",
                file=sys.stderr,
            )
            return 1

        from mind_recovery_mvp.drafting import (
            apply_draft_to_record,
            draft_content_fields,
        )

        excerpt_record = next(
            e for e in EVIDENCE_EXCERPTS if e["medication_class"] == medication_class
        )

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
            _print_drafted_fields(record, STATUS_LLM_DRAFTED_PENDING_REVIEW)
        return 0

    # Default: sample content, no API call, no key required.
    if medication_class not in SAMPLE_DRAFTABLE_CLASSES:
        print(
            f"{medication_class!r} has no entry in sample_content.json.",
            file=sys.stderr,
        )
        return 1

    from mind_recovery_mvp.sample_content import apply_sample_content_to_record

    sample_record = next(
        s for s in SAMPLE_CONTENT if s["medication_class"] == medication_class
    )

    init_db()
    with SessionLocal() as session:
        load_seed_data(session)
        record = (
            session.query(NutrientContent)
            .filter_by(medication_class=medication_class)
            .one()
        )
        print(f"Loading sample content for {medication_class!r} (no API call)...")
        apply_sample_content_to_record(record, sample_record)
        session.commit()
        _print_drafted_fields(record, STATUS_SAMPLE_CONTENT_PENDING_REVIEW)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
