"""Orchestrates RxClass -> clinical content -> USDA -> openFDA for a raw
drug name, in one real-time call. This is the /simulate-prescription
endpoint's logic (see main.py), pulled out into its own module so it's
testable without going through FastAPI.

Reuses the exact same functions main.fill_event uses for the clinical
content lookup and the USDA/openFDA enrichment — no logic is duplicated
here, only orchestrated. Every external call (RxClass, USDA, openFDA) is
invoked via a module-qualified reference (`rxclass.classify_medication_class`,
not a direct `from ... import`), the same pattern openfda.py's caller in
main.py already uses — it's what lets tests patch
`mind_recovery_mvp.rxclass.classify_medication_class` (etc.) and have it
actually take effect here, regardless of how this module itself gets
imported elsewhere.
"""

from __future__ import annotations

import time
from typing import Any, Callable, TypeVar

from sqlalchemy.orm import Session

from mind_recovery_mvp import openfda, rxclass, usda
from mind_recovery_mvp.models import NutrientContent
from mind_recovery_mvp.schemas import NutrientContentResponse

T = TypeVar("T")


def _timed_call(fn: Callable[..., T], *args: Any, **kwargs: Any) -> tuple[T, float]:
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return result, round(elapsed_ms, 2)


def _unmatched_response(drug_name: str, rxclass_ms: float) -> dict[str, Any]:
    return {
        "drug_name": drug_name,
        "classification": {
            "matched": False,
            "medication_class": None,
            "message": (
                f"{drug_name!r} did not map to any supported medication "
                "class (metformin, statins, diuretics, ppi, glp1). This "
                "is a normal outcome, not an error."
            ),
        },
        "clinical_content": None,
        "recommendation": None,
        "fda_label_reference": None,
        "timing_ms": {"rxclass": rxclass_ms, "usda": None, "openfda": None},
    }


def run_simulation(drug_name: str, db: Session, fdc_api_key: str) -> dict[str, Any]:
    medication_class, rxclass_ms = _timed_call(
        rxclass.classify_medication_class, drug_name
    )

    if medication_class is None:
        return _unmatched_response(drug_name, rxclass_ms)

    record = (
        db.query(NutrientContent)
        .filter_by(medication_class=medication_class)
        .one_or_none()
    )
    if record is None:
        # Classified into one of the five target classes, but that class
        # isn't seeded — a genuine data-integrity bug (rxclass.CLASS_KEYWORDS
        # and seed_data.py are meant to stay in sync), not a normal
        # "unsupported drug" outcome. Raising here (surfaced as a 500) is
        # more honest than silently reporting matched=False, which would
        # misrepresent that classification actually succeeded.
        raise RuntimeError(
            f"{drug_name!r} classified as {medication_class!r}, but no "
            f"seeded NutrientContent record exists for that class."
        )

    enriched_foods, usda_ms = _timed_call(
        usda.enrich_foods, record.foods_that_may_help, fdc_api_key
    )
    fda_label_reference, openfda_ms = _timed_call(
        openfda.get_fda_label_reference, medication_class
    )

    return {
        "drug_name": drug_name,
        "classification": {"matched": True, "medication_class": medication_class},
        "clinical_content": NutrientContentResponse.model_validate(record).model_dump(),
        "recommendation": {
            "foods_that_may_help": enriched_foods,
            "supplements_to_discuss": record.supplements_to_discuss,
        },
        "fda_label_reference": fda_label_reference,
        "timing_ms": {"rxclass": rxclass_ms, "usda": usda_ms, "openfda": openfda_ms},
    }
