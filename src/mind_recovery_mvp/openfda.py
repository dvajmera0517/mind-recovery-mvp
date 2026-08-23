"""openFDA drug label lookup — supporting FDA reference text.

Real, live call against https://api.fda.gov/drug/label.json on every
/fill-event call. Kept strictly separate from the pharmacist-curated
clinical content in seed_data.py — this is unedited official FDA label
text, labeled as such, not advice.

No API key required. OPENFDA_API_KEY (optional) is sent if set, raising
the rate limit — same pattern as FDC_API_KEY for USDA, but optional here
per the caller's requirement, not a startup-time hard requirement.

Same resilience contract as usda.py: any failure (network error, timeout,
HTTP error, no results, malformed response) is caught and logged, and
degrades to None rather than raising — this must never block /fill-event
from responding.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

OPENFDA_BASE_URL = "https://api.fda.gov/drug/label.json"
REQUEST_TIMEOUT_SECONDS = 5.0
MAX_REFERENCE_TEXT_LENGTH = 1500

# openFDA's generic_name field holds actual ingredient names, not class
# names — "statins"/"diuretics"/"ppi"/"glp1" aren't queryable that way.
# For those, search by a representative drug's FDA Established
# Pharmacologic Class instead (openfda.pharm_class_epc), the same EPC
# vocabulary rxclass.py classifies drugs into.
#
# metformin is itself a specific ingredient, so it's queried directly by
# name — but as an *exact* match on the bare ingredient name, not a plain
# substring search: "metformin" as a substring also matches combination
# products like "SITAGLIPTIN AND METFORMIN HYDROCHLORIDE", which then
# outranks plain metformin's own label for relevance.
SEARCH_QUERY_BY_MEDICATION_CLASS: dict[str, str] = {
    "metformin": 'openfda.generic_name.exact:"METFORMIN"',
    "statins": 'openfda.pharm_class_epc:"HMG-CoA Reductase Inhibitor [EPC]"',
    "diuretics": 'openfda.pharm_class_epc:"Loop Diuretic [EPC]"',
    "ppi": 'openfda.pharm_class_epc:"Proton Pump Inhibitor [EPC]"',
    "glp1": 'openfda.pharm_class_epc:"GLP-1 Receptor Agonist [EPC]"',
}


def _first_or_none(value: list[str] | None) -> str | None:
    if not value:
        return None
    text = value[0]
    if len(text) > MAX_REFERENCE_TEXT_LENGTH:
        text = text[: MAX_REFERENCE_TEXT_LENGTH - 1] + "…"
    return text


def get_fda_label_reference(medication_class: str) -> dict[str, Any] | None:
    query = SEARCH_QUERY_BY_MEDICATION_CLASS.get(medication_class)
    if query is None:
        return None

    params: dict[str, Any] = {"search": query, "limit": 1}
    api_key = os.environ.get("OPENFDA_API_KEY")
    if api_key:
        params["api_key"] = api_key

    try:
        response = httpx.get(
            OPENFDA_BASE_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []
        if not results:
            return None
        result = results[0]

        openfda_meta = result.get("openfda") or {}
        brand_names = openfda_meta.get("brand_name") or []
        generic_names = openfda_meta.get("generic_name") or []
        source_drug = (brand_names or generic_names or [None])[0]

        # Older-format labels use "warnings" instead of the newer
        # "warnings_and_cautions" section split — fall back to it rather
        # than reporting no warnings text at all when it's really just
        # under the other section name.
        warnings_and_cautions = _first_or_none(
            result.get("warnings_and_cautions")
        ) or _first_or_none(result.get("warnings"))

        return {
            "label": "FDA label reference",
            "source_drug": source_drug,
            "drug_interactions": _first_or_none(result.get("drug_interactions")),
            "warnings_and_cautions": warnings_and_cautions,
        }
    except Exception:
        logger.warning(
            "openFDA label lookup failed for medication_class %r",
            medication_class,
            exc_info=True,
        )
        return None
