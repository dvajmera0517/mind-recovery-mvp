"""Live prescription-fill simulator — a UI on top of the running FastAPI
server, nothing more.

Every result on screen comes from a real HTTP call to the backend's
POST /simulate-prescription and GET /companion-page/{class} endpoints.
This file never calls RxClass, USDA FoodData Central, or openFDA
directly, and never reimplements any of that pipeline logic — the
backend already does all of it (see src/mind_recovery_mvp/
simulate_prescription.py). This is deliberate: it's the whole reason the
"Live API calls" panel below is trustworthy as proof of real network
calls, rather than something this file could fake.

Run standalone:
    streamlit run streamlit_app.py

Or use ./run_demo.sh (or run_demo.ps1 on Windows), which starts the
FastAPI server and this app together.

Configure the backend URL via the SIMULATOR_API_BASE_URL env var
(defaults to http://localhost:8000).
"""

from __future__ import annotations

import os

import httpx
import streamlit as st

API_BASE_URL = os.environ.get("SIMULATOR_API_BASE_URL", "http://localhost:8000").rstrip("/")
REQUEST_TIMEOUT_SECONDS = 30.0

# The text the backend's companion-page renderer uses for any field that
# isn't safe to show yet (see content_review.is_customer_visible /
# companion_page.PENDING_TEXT). Checking for this in the fetched HTML,
# rather than trying to infer "is this approved" from content_status
# ourselves, is deliberate: content_status alone doesn't distinguish
# metformin's pre-pipeline "drafted — needs final pharmacist/legal
# sign-off" status (fully populated, correctly shown as finished) from
# statins/diuretics/ppi/glp1's placeholder/pending states (correctly
# hidden) — that distinction is a judgment call the backend already
# made (see content_review.is_customer_visible's docstring), and
# duplicating it here as a status-string check would risk drifting out
# of sync with it. Reading the backend's actual rendered output instead
# can't drift.
PENDING_REVIEW_TEXT = "Pending pharmacist review"

PRESET_SCENARIOS = [
    ("Metformin", "metformin"),
    ("Atorvastatin (statin)", "atorvastatin"),
    ("Furosemide (diuretic)", "furosemide"),
    ("Omeprazole (PPI)", "omeprazole"),
    ("Semaglutide (GLP-1)", "semaglutide"),
    ("Amoxicillin (unsupported)", "amoxicillin"),
]


def call_simulate_prescription(drug_name: str) -> dict:
    response = httpx.post(
        f"{API_BASE_URL}/simulate-prescription",
        json={"drug_name": drug_name},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def fetch_companion_page_html(medication_class: str) -> str:
    response = httpx.get(
        f"{API_BASE_URL}/companion-page/{medication_class}",
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.text


def run_for_drug(drug_name: str) -> None:
    drug_name = drug_name.strip()
    if not drug_name:
        st.warning("Enter a drug name first.")
        return

    with st.spinner(f"Calling the live pipeline for “{drug_name}”…"):
        try:
            result = call_simulate_prescription(drug_name)
        except httpx.HTTPError as exc:
            st.session_state["last_error"] = (
                f"Could not reach the API at {API_BASE_URL}: {exc}\n\n"
                "Is the FastAPI server running? Try `./run_demo.sh`, or "
                "`uvicorn mind_recovery_mvp.main:app --reload` in another "
                "terminal."
            )
            st.session_state["last_result"] = None
            return

        companion_html = None
        medication_class = result["classification"].get("medication_class")
        if medication_class:
            try:
                companion_html = fetch_companion_page_html(medication_class)
            except httpx.HTTPError as exc:
                st.session_state["companion_page_error"] = str(exc)

        st.session_state["last_error"] = None
        st.session_state["last_result"] = result
        st.session_state["last_companion_html"] = companion_html
        st.session_state["last_drug_name"] = drug_name


st.set_page_config(
    page_title="Prescription Fill Simulator",
    layout="wide",
)

with st.sidebar:
    st.title("Prescription Fill Simulator")
    st.caption("mind-recovery-mvp demo")
    st.info("This is a local demo. No real patient or pharmacy data is used.")
    st.divider()
    st.caption(f"Backend API: `{API_BASE_URL}`")
    st.caption(
        "Set `SIMULATOR_API_BASE_URL` to point this UI at a different "
        "running server."
    )

st.title("Prescription Fill Simulator")
st.write(
    "Simulates a pharmacy fill event for a drug name: classifies it via "
    "RxClass, looks up the matching nutrient-depletion content, enriches "
    "it via USDA, and pulls an openFDA label reference — all in one real "
    "call to the backend."
)

st.subheader("Preset scenarios")
preset_cols = st.columns(len(PRESET_SCENARIOS))
for col, (label, drug_name) in zip(preset_cols, PRESET_SCENARIOS):
    with col:
        if st.button(label, use_container_width=True, key=f"preset_{drug_name}"):
            run_for_drug(drug_name)

st.subheader("Try any drug name")
with st.form("free_text_form", clear_on_submit=False):
    free_text_col, button_col = st.columns([4, 1])
    with free_text_col:
        drug_name_input = st.text_input(
            "Drug name",
            placeholder="e.g. lisinopril",
            label_visibility="collapsed",
        )
    with button_col:
        submitted = st.form_submit_button("Run simulation", use_container_width=True)
if submitted:
    run_for_drug(drug_name_input)

st.divider()

if st.session_state.get("last_error"):
    st.error(st.session_state["last_error"])
elif st.session_state.get("last_result"):
    result = st.session_state["last_result"]
    companion_html = st.session_state.get("last_companion_html")
    drug_name = st.session_state["last_drug_name"]

    st.subheader(f"Results for “{drug_name}”")

    classification = result["classification"]

    if not classification["matched"]:
        st.warning(
            f"**Not a supported medication class.**\n\n{classification['message']}"
        )
    else:
        medication_class = classification["medication_class"]
        st.success(
            f"RxClass classified **{drug_name}** as **{medication_class}**"
        )

        clinical_content = result.get("clinical_content")
        content_status = clinical_content["content_status"] if clinical_content else None
        # See PENDING_REVIEW_TEXT above for why this checks the actual
        # rendered page rather than content_status directly.
        is_approved = bool(companion_html) and PENDING_REVIEW_TEXT not in companion_html

        page_col, fda_col = st.columns([3, 2])

        with page_col:
            st.markdown("#### Companion page preview")
            if content_status:
                st.caption(f"content_status: `{content_status}`")

            if not is_approved:
                st.markdown(
                    """
                    <div style="
                        background-color:#fff3cd;
                        border:2px solid #f5a623;
                        border-radius:6px;
                        padding:10px 14px;
                        margin-bottom:10px;
                        font-weight:600;
                        color:#7a4a00;
                    ">
                        ⚠️ PENDING PHARMACIST REVIEW &mdash; this
                        preview is NOT approved for customer display.
                        Individual fields below still read
                        &ldquo;Pending pharmacist review&rdquo; even where
                        the database has draft content, by design.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            if companion_html:
                border_color = "#2e7d32" if is_approved else "#f5a623"
                st.markdown(
                    f'<div style="border:3px solid {border_color}; '
                    'border-radius:8px; overflow:hidden;">',
                    unsafe_allow_html=True,
                )
                st.iframe(companion_html, height=850)
                st.markdown("</div>", unsafe_allow_html=True)
            elif st.session_state.get("companion_page_error"):
                st.error(
                    "Could not load the companion page preview: "
                    f"{st.session_state['companion_page_error']}"
                )
            else:
                st.info("No companion page preview available.")

        with fda_col:
            st.markdown(
                "#### FDA label reference — informational only, "
                "not the pharmacist-curated content"
            )
            fda_ref = result.get("fda_label_reference")
            if fda_ref:
                with st.container(border=True):
                    if fda_ref.get("source_drug"):
                        st.markdown(f"**Source drug:** {fda_ref['source_drug']}")
                    st.markdown("**Drug interactions**")
                    st.write(fda_ref.get("drug_interactions") or "_Not available._")
                    st.markdown("**Warnings & cautions**")
                    st.write(fda_ref.get("warnings_and_cautions") or "_Not available._")
            else:
                st.info("No openFDA reference available for this drug.")

    st.divider()
    st.markdown("#### Live API calls")
    st.caption(
        "Real response times from the backend's own timing measurements "
        "— proof these are live network calls, not mocked data."
    )
    timing = result["timing_ms"]

    def _format_timing(value: float | None, attempted: bool = True) -> str:
        if value is None:
            return "not attempted" if attempted else "—"
        return f"{value:.1f} ms"

    t1, t2, t3 = st.columns(3)
    t1.metric("RxClass", _format_timing(timing["rxclass"]))
    t2.metric("USDA FoodData Central", _format_timing(timing["usda"]))
    t3.metric("openFDA", _format_timing(timing["openfda"]))
else:
    st.caption("Pick a preset scenario or enter a drug name to run the live pipeline.")
