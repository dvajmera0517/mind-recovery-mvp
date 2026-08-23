"""RxClass (NLM) drug classification lookup.

Real, live call against https://rxnav.nlm.nih.gov/REST/rxclass — no API key
or license required. Maps a drug name to one of our target medication
classes via its therapeutic classification.
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

RXCLASS_BASE_URL = "https://rxnav.nlm.nih.gov/REST/rxclass"
REQUEST_TIMEOUT_SECONDS = 5.0

# Substrings (lowercase) checked against every therapeutic class name
# RxClass returns for the drug, across all its classification systems
# (EPC, ATC, VA, MOA, ...) — not just EPC (FDA's Established Pharmacologic
# Class). EPC alone isn't enough: e.g. the potassium-sparing diuretic
# spironolactone is classified under EPC as "Aldosterone Antagonist" (no
# "diuretic" in the name at all), but does say "DIURETICS" under its VA
# and ATC classifications.
CLASS_KEYWORDS: dict[str, tuple[str, ...]] = {
    "metformin": ("biguanide",),
    "statins": ("statin", "hmg-coa reductase inhibitor"),
    "diuretics": ("diuretic",),
    "ppi": ("proton pump inhibitor",),
    "glp1": ("glp-1 receptor agonist",),
}


def classify_medication_class(drug_name: str) -> str | None:
    """Look up drug_name's therapeutic class via RxClass's
    getClassByRxNormDrugName operation and map it to one of
    metformin/statins/diuretics/ppi/glp1.

    Returns None if the live lookup fails, or if the drug doesn't map to
    any of the target classes.
    """
    try:
        response = httpx.get(
            f"{RXCLASS_BASE_URL}/class/byDrugName.json",
            params={"drugName": drug_name},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get("rxclassDrugInfoList", {}).get("rxclassDrugInfo") or []
        class_names = {
            item["rxclassMinConceptItem"]["className"].lower() for item in items
        }
    except Exception:
        logger.warning("RxClass lookup failed for drug %r", drug_name, exc_info=True)
        return None

    for target_class, keywords in CLASS_KEYWORDS.items():
        for class_name in class_names:
            if any(keyword in class_name for keyword in keywords):
                return target_class
    return None
