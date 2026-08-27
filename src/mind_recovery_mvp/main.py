import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from mind_recovery_mvp.companion_page import (
    render_companion_page_html,
    render_companion_page_pdf,
)
from mind_recovery_mvp.content_review import (
    PENDING_REVIEW_STATUSES,
    REVIEWABLE_FIELDS,
    approve_record,
)
from mind_recovery_mvp.db import SessionLocal, get_db, init_db
from mind_recovery_mvp.event_log import (
    get_metrics,
    mark_companion_page_requested,
    record_fill_event,
)
from mind_recovery_mvp.loader import load_seed_data
from mind_recovery_mvp.models import NutrientContent
from mind_recovery_mvp import openfda
from mind_recovery_mvp.schemas import (
    FillEventRequest,
    FillEventResponse,
    MetricsResponse,
    NutrientContentResponse,
    ReviewApprovalRequest,
    ReviewQueueItem,
    ReviewQueueResponse,
    SimulatePrescriptionRequest,
    SimulatePrescriptionResponse,
)
from mind_recovery_mvp.seed_data import NUTRIENT_CONTENT_SEED
from mind_recovery_mvp.simulate_prescription import run_simulation
from mind_recovery_mvp.usda import enrich_foods

# Loads a repo-root .env file (if present) into the environment. Called at
# import time so FDC_API_KEY is available before the startup check below,
# regardless of whether the process's cwd is the repo root.
load_dotenv()

# Derived from seed_data.py rather than hardcoded, so adding/removing a
# medication class there doesn't also require remembering to update this.
SUPPORTED_CLASSES_MESSAGE = "Supported classes: " + ", ".join(
    record["medication_class"] for record in NUTRIENT_CONTENT_SEED
) + "."


def _get_record_or_404(medication_class: str, db: Session) -> NutrientContent:
    record = (
        db.query(NutrientContent)
        .filter_by(medication_class=medication_class)
        .one_or_none()
    )
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Unknown medication_class: {medication_class!r}. "
                f"{SUPPORTED_CLASSES_MESSAGE}"
            ),
        )
    return record


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if not os.environ.get("FDC_API_KEY"):
        raise RuntimeError(
            "FDC_API_KEY is not set. This server enriches "
            "foods_that_may_help with real USDA FoodData Central lookups "
            "on every /fill-event call, so a key is required to start. "
            "Get a free key at https://fdc.nal.usda.gov/api-key-signup "
            "and set FDC_API_KEY=<your-key> in a .env file at the repo "
            "root (or as an environment variable) before starting the "
            "server."
        )
    init_db()
    with SessionLocal() as session:
        load_seed_data(session)
    yield


app = FastAPI(title="Mind Recovery MVP", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/fill-event", response_model=FillEventResponse)
def fill_event(payload: FillEventRequest, db: Session = Depends(get_db)) -> dict:
    record = _get_record_or_404(payload.medication_class, db)
    record_fill_event(db, record.medication_class)

    # Guaranteed present: lifespan fails fast at startup otherwise.
    api_key = os.environ["FDC_API_KEY"]
    enriched_foods = enrich_foods(record.foods_that_may_help, api_key)
    fda_label_reference = openfda.get_fda_label_reference(record.medication_class)

    return {
        **NutrientContentResponse.model_validate(record).model_dump(),
        "recommendation": {
            "foods_that_may_help": enriched_foods,
            "supplements_to_discuss": record.supplements_to_discuss,
        },
        "fda_label_reference": fda_label_reference,
    }


# Registered before the plain HTML route below: the {medication_class} path
# param would otherwise also match "<class>.pdf" and shadow this route.
@app.get("/companion-page/{medication_class}.pdf")
def companion_page_pdf(medication_class: str, db: Session = Depends(get_db)) -> Response:
    record = _get_record_or_404(medication_class, db)
    mark_companion_page_requested(db, medication_class)
    pdf_bytes = render_companion_page_pdf(record)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'inline; filename="{medication_class}-companion-page.pdf"'
            )
        },
    )


@app.get("/companion-page/{medication_class}", response_class=HTMLResponse)
def companion_page_html(medication_class: str, db: Session = Depends(get_db)) -> str:
    record = _get_record_or_404(medication_class, db)
    mark_companion_page_requested(db, medication_class)
    return render_companion_page_html(record)


@app.get("/metrics", response_model=MetricsResponse)
def metrics(db: Session = Depends(get_db)) -> dict:
    return get_metrics(db)


@app.get("/review-queue", response_model=ReviewQueueResponse)
def review_queue(db: Session = Depends(get_db)) -> dict:
    records = (
        db.query(NutrientContent)
        .filter(NutrientContent.content_status.in_(PENDING_REVIEW_STATUSES))
        .all()
    )
    return {"items": records}


@app.post("/review-queue/{medication_class}/approve", response_model=ReviewQueueItem)
def approve_review_queue_item(
    medication_class: str,
    payload: ReviewApprovalRequest,
    db: Session = Depends(get_db),
) -> NutrientContent:
    record = _get_record_or_404(medication_class, db)
    if record.content_status not in PENDING_REVIEW_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=(
                f"{medication_class!r} is not pending review "
                f"(content_status={record.content_status!r})."
            ),
        )

    if payload.edits:
        unknown_fields = set(payload.edits) - set(REVIEWABLE_FIELDS)
        if unknown_fields:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Unknown field(s) in edits: {sorted(unknown_fields)}. "
                    f"Valid fields: {REVIEWABLE_FIELDS}."
                ),
            )

    approve_record(
        record,
        edits=payload.edits,
        reviewer_name=payload.reviewer_name,
        reviewed_at=datetime.now(timezone.utc),
    )
    db.commit()
    db.refresh(record)
    return record


@app.post("/simulate-prescription", response_model=SimulatePrescriptionResponse)
def simulate_prescription(
    payload: SimulatePrescriptionRequest, db: Session = Depends(get_db)
) -> dict:
    # Guaranteed present: lifespan fails fast at startup otherwise.
    api_key = os.environ["FDC_API_KEY"]
    return run_simulation(payload.drug_name, db, api_key)
