from __future__ import annotations

from pydantic import BaseModel, ConfigDict


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
