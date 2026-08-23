"""Verbatim clinical content seed data.

Do not add, expand, or infer content beyond what is listed here. Null
fields indicate content that has not been specified in source and must be
drafted and cited by a pharmacist/dietitian before use.
"""

from __future__ import annotations

from typing import Any

NUTRIENT_CONTENT_SEED: list[dict[str, Any]] = [
    {
        "medication_class": "metformin",
        "content_status": "drafted — needs final pharmacist/legal sign-off",
        "nutrient_concern": "Vitamin B12 depletion",
        "why_it_matters": (
            "Long-term use of metformin may be associated with reduced "
            "Vitamin B12 levels in some patients."
        ),
        "foods_that_may_help": ["eggs", "dairy", "fish", "fortified cereals"],
        "supplements_to_discuss": ["Vitamin B12 supplements"],
        "talk_to_pharmacist_if": "you experience unusual fatigue, tingling, or numbness",
        "clinical_source": "TRC Healthcare Natural Medicines / [approved clinical reference]",
    },
    {
        "medication_class": "statins",
        "content_status": (
            "PLACEHOLDER — foods, why-it-matters, and discussion prompt not "
            "specified in source; pharmacist/dietitian must draft and cite "
            "before use"
        ),
        "nutrient_concern": "CoQ10 association",
        "why_it_matters": None,
        "foods_that_may_help": None,
        "supplements_to_discuss": ["CoQ10 supplements — confirm appropriateness with pharmacist"],
        "talk_to_pharmacist_if": None,
        "clinical_source": None,
    },
    {
        "medication_class": "diuretics",
        "content_status": (
            "PLACEHOLDER — why-it-matters and discussion prompt not "
            "specified in source; pharmacist/dietitian must draft and cite "
            "before use"
        ),
        "nutrient_concern": "Potassium or magnesium depletion risk",
        "why_it_matters": None,
        "foods_that_may_help": ["bananas", "leafy greens", "beans", "avocados", "nuts"],
        "supplements_to_discuss": None,
        "talk_to_pharmacist_if": None,
        "clinical_source": None,
    },
    {
        "medication_class": "ppi",
        "content_status": (
            "PLACEHOLDER — only the nutrient concern is specified in "
            "source; everything else must be pharmacist/dietitian-drafted "
            "and cited before use"
        ),
        "nutrient_concern": "Magnesium, Calcium, and Vitamin B12 concerns",
        "why_it_matters": None,
        "foods_that_may_help": None,
        "supplements_to_discuss": None,
        "talk_to_pharmacist_if": None,
        "clinical_source": None,
    },
    {
        "medication_class": "glp1",
        "content_status": "PLACEHOLDER — added as a 5th target class; nothing drafted or reviewed yet",
        "nutrient_concern": (
            "Reduced overall nutrient intake — protein, Vitamin B12, iron, "
            "Vitamin D, and thiamine — due to appetite suppression and "
            "delayed gastric emptying"
        ),
        "why_it_matters": None,
        "foods_that_may_help": None,
        "supplements_to_discuss": None,
        "talk_to_pharmacist_if": None,
        "clinical_source": None,
    },
]
