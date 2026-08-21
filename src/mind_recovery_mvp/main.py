from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from mind_recovery_mvp.db import SessionLocal, get_db, init_db
from mind_recovery_mvp.loader import load_seed_data
from mind_recovery_mvp.models import NutrientContent
from mind_recovery_mvp.schemas import FillEventRequest, NutrientContentResponse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    with SessionLocal() as session:
        load_seed_data(session)
    yield


app = FastAPI(title="Mind Recovery MVP", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/fill-event", response_model=NutrientContentResponse)
def fill_event(
    payload: FillEventRequest, db: Session = Depends(get_db)
) -> NutrientContent:
    record = (
        db.query(NutrientContent)
        .filter_by(medication_class=payload.medication_class)
        .one_or_none()
    )
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Unknown medication_class: {payload.medication_class!r}. "
                "Supported classes: metformin, statins, diuretics, ppi."
            ),
        )
    return record
