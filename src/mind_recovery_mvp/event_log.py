from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from mind_recovery_mvp.models import FillEventLog
from mind_recovery_mvp.seed_data import NUTRIENT_CONTENT_SEED

MEDICATION_CLASSES: list[str] = [
    record["medication_class"] for record in NUTRIENT_CONTENT_SEED
]


def record_fill_event(db: Session, medication_class: str) -> FillEventLog:
    entry = FillEventLog(medication_class=medication_class)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def mark_companion_page_requested(db: Session, medication_class: str) -> None:
    """Flag the most recent fill-event log row for this class as followed
    by a companion-page request. A no-op if there's no prior fill-event."""
    entry = (
        db.query(FillEventLog)
        .filter_by(medication_class=medication_class)
        .order_by(FillEventLog.created_at.desc(), FillEventLog.id.desc())
        .first()
    )
    if entry is not None:
        entry.companion_page_requested = True
        db.commit()


def get_metrics(db: Session) -> dict:
    counts_by_class: dict[str, dict[str, int]] = {
        medication_class: {"fill_event_count": 0, "companion_page_count": 0}
        for medication_class in MEDICATION_CLASSES
    }

    rows = (
        db.query(
            FillEventLog.medication_class,
            func.count(FillEventLog.id),
            func.sum(FillEventLog.companion_page_requested),
        )
        .group_by(FillEventLog.medication_class)
        .all()
    )
    for medication_class, fill_event_count, companion_page_count in rows:
        counts_by_class[medication_class]["fill_event_count"] = fill_event_count
        counts_by_class[medication_class]["companion_page_count"] = (
            companion_page_count or 0
        )

    medication_classes = []
    for medication_class in counts_by_class:
        fill_event_count = counts_by_class[medication_class]["fill_event_count"]
        companion_page_count = counts_by_class[medication_class]["companion_page_count"]
        medication_classes.append(
            {
                "medication_class": medication_class,
                "fill_event_count": fill_event_count,
                "companion_page_count": companion_page_count,
                "companion_page_rate": (
                    companion_page_count / fill_event_count
                    if fill_event_count > 0
                    else None
                ),
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc),
        "medication_classes": medication_classes,
    }
