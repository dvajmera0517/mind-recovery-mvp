#!/usr/bin/env python3
"""Interactive CLI to review LLM-drafted clinical content before approval.

Lists every record with content_status ==
"llm_drafted_pending_pharmacist_review", shows the draft next to its
source evidence excerpt, and lets the reviewer approve as-is or edit any
field before approving. On approval, content_status becomes "approved"
(nothing changed) or "approved_with_edits" (something did), and
reviewed_by/reviewed_at are recorded.

Usage:
    python scripts/review_content.py

Reviewer name comes from the REVIEWER_NAME env var if set, otherwise
you'll be prompted for it.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

from mind_recovery_mvp.content_review import (  # noqa: E402
    REVIEWABLE_FIELDS,
    STATUS_LLM_DRAFTED_PENDING_REVIEW,
    approve_record,
)
from mind_recovery_mvp.db import SessionLocal, init_db  # noqa: E402
from mind_recovery_mvp.models import NutrientContent  # noqa: E402

LIST_FIELDS = {"foods_that_may_help", "supplements_to_discuss"}


def _format_value(value: object) -> str:
    if value is None:
        return "(null)"
    if isinstance(value, list):
        return ", ".join(value) if value else "(empty list)"
    return str(value)


def _prompt_reviewer_name() -> str:
    name = os.environ.get("REVIEWER_NAME")
    if name:
        return name
    while True:
        name = input("Reviewer name: ").strip()
        if name:
            return name
        print("Reviewer name is required.")


def _prompt_field_edit(field: str, current: object) -> object:
    print(f"  Current {field}: {_format_value(current)}")
    prompt = (
        f"  New value for {field} (comma-separated list, blank to keep, "
        f"'null' to clear): "
        if field in LIST_FIELDS
        else f"  New value for {field} (blank to keep, 'null' to clear): "
    )
    raw = input(prompt).strip()

    if raw == "":
        return current
    if raw.lower() == "null":
        return None
    if field in LIST_FIELDS:
        return [item.strip() for item in raw.split(",") if item.strip()]
    return raw


def review_record(session, record: NutrientContent) -> None:
    print("\n" + "=" * 70)
    print(f"Medication class: {record.medication_class}")
    print(f"Nutrient concern: {record.nutrient_concern}")
    print("-" * 70)
    print("Source evidence excerpt:")
    print(record.evidence_excerpt or "(none attached)")
    print("-" * 70)
    print("LLM draft:")
    for field in REVIEWABLE_FIELDS:
        print(f"  {field}: {_format_value(getattr(record, field))}")
    print("=" * 70)

    while True:
        choice = input("[a]pprove as-is, [e]dit before approving, [s]kip: ").strip().lower()
        if choice in {"a", "e", "s"}:
            break
        print("Please enter a, e, or s.")

    if choice == "s":
        print("Skipped.")
        return

    edits: dict[str, object] = {}
    if choice == "e":
        for field in REVIEWABLE_FIELDS:
            edits[field] = _prompt_field_edit(field, getattr(record, field))

    reviewer_name = _prompt_reviewer_name()
    approve_record(
        record,
        edits=edits,
        reviewer_name=reviewer_name,
        reviewed_at=datetime.now(timezone.utc),
    )
    session.commit()
    print(f"Saved as {record.content_status!r}, reviewed by {reviewer_name!r}.")


def main() -> int:
    init_db()
    with SessionLocal() as session:
        pending = (
            session.query(NutrientContent)
            .filter_by(content_status=STATUS_LLM_DRAFTED_PENDING_REVIEW)
            .all()
        )
        if not pending:
            print("No records pending review.")
            return 0

        print(f"{len(pending)} record(s) pending review.")
        for record in pending:
            review_record(session, record)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
