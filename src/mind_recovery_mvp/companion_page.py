from __future__ import annotations

from io import BytesIO
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from xhtml2pdf import pisa

from mind_recovery_mvp.content_review import CONTENT_ORIGIN_LABELS, is_customer_visible
from mind_recovery_mvp.models import NutrientContent

TEMPLATES_DIR = Path(__file__).parent / "templates"

PENDING_TEXT = "Pending pharmacist review"

MEDICATION_DISPLAY_NAMES: dict[str, str] = {
    "metformin": "Metformin",
    "statins": "Statins",
    "diuretics": "Diuretics",
    "ppi": "PPI",
    "glp1": "GLP-1",
}

_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html"]),
)


def render_companion_page_html(record: NutrientContent) -> str:
    template = _env.get_template("companion_page.html")
    # Gate on content_status, not on whether fields happen to be
    # populated: an LLM draft, sample content, or a partially-seeded
    # placeholder must never render as real content until a pharmacist
    # has approved it.
    show_content = is_customer_visible(record.content_status)

    # Provenance is only meaningful (and only shown) once the content is
    # actually visible — content_origin survives past approval so this
    # still works for "approved"/"approved_with_edits", not just the
    # moment right after drafting.
    content_origin_label = None
    if show_content and record.content_origin in CONTENT_ORIGIN_LABELS:
        content_origin_label = (
            f"Content origin: {CONTENT_ORIGIN_LABELS[record.content_origin]}"
        )

    return template.render(
        medication=MEDICATION_DISPLAY_NAMES.get(
            record.medication_class, record.medication_class
        ),
        nutrient_concern=record.nutrient_concern,
        why_it_matters=record.why_it_matters if show_content else None,
        foods_that_may_help=record.foods_that_may_help if show_content else None,
        supplements_to_discuss=(
            record.supplements_to_discuss if show_content else None
        ),
        talk_to_pharmacist_if=(
            record.talk_to_pharmacist_if if show_content else None
        ),
        clinical_source=record.clinical_source if show_content else None,
        content_origin_label=content_origin_label,
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
