"""Evidence excerpts used as source material for LLM-assisted drafting.

Short, paraphrased, non-verbatim source material — not a clinical
database, and not citation-ready as-is. This is the ONLY source material
scripts/draft_content.py is allowed to draw on when drafting content for
statins, diuretics, and ppi; the model is explicitly instructed not to add
clinical claims beyond what's here. citation_label is not a real citation
either — it's carried forward as-is into clinical_source, and a pharmacist
must replace it with a specific verified reference before use.
"""

from __future__ import annotations

EVIDENCE_EXCERPTS: list[dict[str, str]] = [
    {
        "medication_class": "statins",
        "evidence_excerpt": (
            "Statins (HMG-CoA reductase inhibitors) block the mevalonate "
            "pathway, which the body also uses to synthesize coenzyme Q10 "
            "(CoQ10). Several clinical studies report lower circulating "
            "CoQ10 levels in patients on statin therapy. Foods with some "
            "CoQ10 content include organ meats (liver, heart), fatty fish "
            "(salmon, mackerel, sardines), whole grains, peanuts, and "
            "soybean or canola oil. A discussion prompt worth considering: "
            "muscle aches, weakness, or unusual fatigue while on a statin."
        ),
        "citation_label": (
            "General pharmacology/nutrition literature on statin-associated "
            "CoQ10 depletion — pharmacist must supply a specific verified "
            "citation before use."
        ),
    },
    {
        "medication_class": "diuretics",
        "evidence_excerpt": (
            "Loop and thiazide diuretics increase renal excretion of "
            "potassium and magnesium, which can lead to hypokalemia and "
            "hypomagnesemia with prolonged use. Potassium-sparing "
            "diuretics are a notable exception and work by a different "
            "mechanism. A discussion prompt worth considering: muscle "
            "cramps, weakness, or irregular heartbeat while on a diuretic."
        ),
        "citation_label": (
            "General pharmacology literature on diuretic-associated "
            "electrolyte depletion — pharmacist must supply a specific "
            "verified citation before use."
        ),
    },
    {
        "medication_class": "ppi",
        "evidence_excerpt": (
            "Long-term acid suppression from PPIs can reduce absorption of "
            "magnesium, calcium, and vitamin B12 — B12 requires stomach "
            "acid to be released from dietary protein before it can be "
            "absorbed. For magnesium: leafy greens, nuts, seeds, whole "
            "grains. For calcium: dairy, fortified foods, leafy greens. "
            "For B12: eggs, dairy, fish, fortified cereals. A discussion "
            "prompt worth considering: taking a PPI for longer than a "
            "year, or experiencing muscle cramps, irregular heartbeat, "
            "tingling, or unusual fatigue."
        ),
        "citation_label": (
            "FDA Drug Safety Communication (March 2011), 'Low magnesium "
            "levels can be associated with long-term use of proton pump "
            "inhibitor drugs (PPIs)' — pharmacist should confirm the "
            "current citation and add calcium/B12-specific references "
            "before use."
        ),
    },
]
