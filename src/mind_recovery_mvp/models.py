from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from mind_recovery_mvp.db import Base


class NutrientContent(Base):
    __tablename__ = "nutrient_content"

    id: Mapped[int] = mapped_column(primary_key=True)
    medication_class: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    content_status: Mapped[str] = mapped_column(String, nullable=False)
    nutrient_concern: Mapped[str] = mapped_column(String, nullable=False)
    why_it_matters: Mapped[str | None] = mapped_column(String, nullable=True)
    foods_that_may_help: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    supplements_to_discuss: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    talk_to_pharmacist_if: Mapped[str | None] = mapped_column(String, nullable=True)
    clinical_source: Mapped[str | None] = mapped_column(String, nullable=True)

    # Set by scripts/draft_content.py: the source excerpt the LLM draft was
    # generated from, so a reviewer can see what it was drafted from.
    evidence_excerpt: Mapped[str | None] = mapped_column(String, nullable=True)
    # Set by scripts/review_content.py on approval.
    reviewed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class FillEventLog(Base):
    """One row per /fill-event call.

    companion_page_requested is set after the fact, on the most recent log
    row for that medication_class, when the companion page is subsequently
    requested. There's no session/request correlation in this MVP, so
    "subsequently requested" is approximated as "the most recent fill-event
    for this medication_class" rather than tied to a specific caller.
    """

    __tablename__ = "fill_event_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    medication_class: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    companion_page_requested: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
