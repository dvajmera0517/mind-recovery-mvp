"""Evidence excerpts used as source material for LLM-assisted drafting.

Short, paraphrased, non-verbatim source material — not a clinical
database, and not citation-ready as-is. This is the ONLY source material
scripts/draft_content.py is allowed to draw on when drafting content for
statins, diuretics, ppi, and glp1; the model is explicitly instructed not
to add clinical claims beyond what's here. citation_label is not a real
citation either — it's carried forward as-is into clinical_source, and a
pharmacist must replace it with a specific verified reference before use.
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
    {
        "medication_class": "glp1",
        "evidence_excerpt": (
            "GLP-1 receptor agonists (semaglutide, liraglutide, "
            "tirzepatide) slow gastric emptying and suppress appetite, "
            "often reducing food intake by 20-39%. This is associated "
            "with reduced protein intake and, in some patients, "
            "measurable loss of lean body mass. A large retrospective "
            "study found that over 22% of GLP-1 users developed at "
            "least one nutritional deficiency within 12 months, most "
            "commonly vitamin D, followed by thiamine, other B "
            "vitamins, and anemia. Reduced stomach acid and delayed "
            "gastric emptying can also impair vitamin B12 absorption, "
            "a similar mechanism to long-term PPI or metformin use. "
            "Protein-rich, easy-to-tolerate foods (eggs, Greek yogurt, "
            "lean meats, fish, protein shakes) and B12-rich foods "
            "(eggs, dairy, fish, fortified cereals) are commonly "
            "recommended. A discussion prompt worth considering: "
            "unusual weakness, numbness, tingling, vision changes, or "
            "difficulty maintaining adequate food and fluid intake."
        ),
        "citation_label": (
            "Retrospective cohort literature on GLP-1RA-associated "
            "nutritional deficiencies (observational studies, "
            "2025–2026) — pharmacist must supply a specific verified "
            "citation before use. This nutrient_concern spans several "
            "nutrients rather than one mechanism; the drafted "
            "foods_that_may_help and supplements_to_discuss should "
            "reflect that breadth rather than collapsing it to a "
            "single nutrient."
        ),
    },
]
