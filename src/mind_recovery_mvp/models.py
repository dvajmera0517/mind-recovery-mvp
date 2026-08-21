from __future__ import annotations

from sqlalchemy import JSON, String
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
