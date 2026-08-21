from __future__ import annotations

from sqlalchemy.orm import Session

from mind_recovery_mvp.models import NutrientContent
from mind_recovery_mvp.seed_data import NUTRIENT_CONTENT_SEED


def load_seed_data(session: Session) -> None:
    for record in NUTRIENT_CONTENT_SEED:
        existing = (
            session.query(NutrientContent)
            .filter_by(medication_class=record["medication_class"])
            .one_or_none()
        )
        if existing is not None:
            continue
        session.add(NutrientContent(**record))
    session.commit()
