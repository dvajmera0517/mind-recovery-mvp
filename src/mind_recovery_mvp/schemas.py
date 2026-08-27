from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FillEventRequest(BaseModel):
    medication_class: str


class NutrientContentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    medication_class: str
    content_status: str
    nutrient_concern: str
    why_it_matters: str | None
    foods_that_may_help: list[str] | None
    supplements_to_discuss: list[str] | None
    talk_to_pharmacist_if: str | None
    clinical_source: str | None


class FoodNutrient(BaseModel):
    name: str | None
    amount: float | None
    unit: str | None


class FoodNutrientLookup(BaseModel):
    fdc_id: int | None
    description: str | None
    nutrients: list[FoodNutrient]


class EnrichedFood(BaseModel):
    food: str
    nutrients: FoodNutrientLookup | None = None


class Recommendation(BaseModel):
    foods_that_may_help: list[EnrichedFood] | None
    supplements_to_discuss: list[str] | None


class FdaLabelReference(BaseModel):
    label: str = "FDA label reference"
    source_drug: str | None
    drug_interactions: str | None
    warnings_and_cautions: str | None


class FillEventResponse(NutrientContentResponse):
    recommendation: Recommendation
    fda_label_reference: FdaLabelReference | None


class SimulatePrescriptionRequest(BaseModel):
    drug_name: str


class ClassificationResult(BaseModel):
    matched: bool
    medication_class: str | None
    message: str | None = None


class TimingBreakdownMs(BaseModel):
    rxclass: float | None
    usda: float | None
    openfda: float | None


class SimulatePrescriptionResponse(BaseModel):
    drug_name: str
    classification: ClassificationResult
    clinical_content: NutrientContentResponse | None
    recommendation: Recommendation | None
    fda_label_reference: FdaLabelReference | None
    timing_ms: TimingBreakdownMs


class ReviewQueueItem(NutrientContentResponse):
    evidence_excerpt: str | None
    content_origin: str | None
    reviewed_by: str | None
    reviewed_at: datetime | None


class ReviewQueueResponse(BaseModel):
    items: list[ReviewQueueItem]


class ReviewApprovalRequest(BaseModel):
    reviewer_name: str = Field(min_length=1)
    # Only fields the reviewer actually changed — omit a field entirely
    # to keep its current value, same "blank to keep" contract
    # scripts/review_content.py uses. None clears a field to null.
    edits: dict[str, str | list[str] | None] | None = None


class MedicationClassMetrics(BaseModel):
    medication_class: str
    fill_event_count: int
    companion_page_count: int
    companion_page_rate: float | None


class MetricsResponse(BaseModel):
    generated_at: datetime
    note: str = (
        "Stand-in for engagement/purchase-lift measurement. Counts "
        "/fill-event calls and subsequent companion-page requests only "
        "— not real purchases or clinical outcomes."
    )
    medication_classes: list[MedicationClassMetrics]
