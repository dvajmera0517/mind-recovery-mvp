from __future__ import annotations

from io import BytesIO
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from xhtml2pdf import pisa

from mind_recovery_mvp.models import NutrientContent

TEMPLATES_DIR = Path(__file__).parent / "templates"

PENDING_TEXT = "Pending pharmacist review"

MEDICATION_DISPLAY_NAMES: dict[str, str] = {
    "metformin": "Metformin",
    "statins": "Statins",
    "diuretics": "Diuretics",
    "ppi": "PPI",
}

_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html"]),
)


def render_companion_page_html(record: NutrientContent) -> str:
    template = _env.get_template("companion_page.html")
    return template.render(
        medication=MEDICATION_DISPLAY_NAMES.get(
            record.medication_class, record.medication_class
        ),
        nutrient_concern=record.nutrient_concern,
        why_it_matters=record.why_it_matters,
        foods_that_may_help=record.foods_that_may_help,
        supplements_to_discuss=record.supplements_to_discuss,
        talk_to_pharmacist_if=record.talk_to_pharmacist_if,
        clinical_source=record.clinical_source,
        pending_text=PENDING_TEXT,
    )


def render_companion_page_pdf(record: NutrientContent) -> bytes:
    html = render_companion_page_html(record)
    buffer = BytesIO()
    result = pisa.CreatePDF(html, dest=buffer)
    if result.err:
        raise RuntimeError(
            f"Failed to render companion page PDF for {record.medication_class!r}"
        )
    return buffer.getvalue()
