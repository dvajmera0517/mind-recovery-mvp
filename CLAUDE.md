# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project scope

This is a **local MVP prototype** of a pharmacy-triggered nutrient-depletion recommendation engine. It covers exactly **four medication classes**: metformin, statins, diuretics, and PPIs (proton pump inhibitors). It is **not connected to any real pharmacy system or patient data** — do not add integrations, network calls to external health/pharmacy APIs, or real patient data handling without explicit direction. Keep changes scoped to these four medication classes unless asked to expand scope.

## Tech stack

- Python 3.11+
- FastAPI (API layer)
- SQLAlchemy + SQLite (clinical content storage)
- Jinja2 + xhtml2pdf (printable companion page — HTML and PDF; xhtml2pdf was chosen over WeasyPrint because WeasyPrint needs native Pango/GObject libraries that aren't available in this dev environment)
- httpx (live outbound calls to USDA FoodData Central, RxClass, and openFDA) + python-dotenv (loads `FDC_API_KEY` from a repo-root `.env`)
- pytest + httpx (`TestClient`) for tests
- `src/` layout, packaged as `mind_recovery_mvp`, built with setuptools via `pyproject.toml`

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # then fill in a real FDC_API_KEY — see below
```

`FDC_API_KEY` is **required**: the server fails fast at startup (not silently) if it's missing. Get a free key at https://fdc.nal.usda.gov/api-key-signup, or use USDA's public `DEMO_KEY` (rate-limited, no signup) to try things out.

## Run

```bash
uvicorn mind_recovery_mvp.main:app --reload
```

Health check: `GET http://127.0.0.1:8000/health`

## Test

```bash
pytest
```

Run a single test file: `pytest tests/test_health.py`
Run a single test: `pytest tests/test_health.py::test_health`

The default `pytest` run is fully offline — every USDA/RxClass/openFDA call is mocked (see `tests/conftest.py`'s autouse fixture), and `-m "not integration"` (set in `pyproject.toml`) excludes the three tests that hit real APIs. Run just those explicitly:

```bash
FDC_API_KEY=<your-key> pytest -m integration
```
(omit `FDC_API_KEY=` to fall back to USDA's `DEMO_KEY`. RxClass and openFDA don't need a key at all — `OPENFDA_API_KEY` is optional and only raises openFDA's rate limit.)

## Architecture

- `src/mind_recovery_mvp/main.py` — FastAPI app instance, lifespan hook (fail-fast `FDC_API_KEY` check, then DB init + seed load), and all routes. Entry point for `uvicorn`. Calls `load_dotenv()` at import time.
- `src/mind_recovery_mvp/models.py` — `NutrientContent` SQLAlchemy model (one row per medication class).
- `src/mind_recovery_mvp/seed_data.py` — the verbatim clinical content for the four seeded medication classes (metformin, statins, diuretics, ppi). This is the single source of truth for clinical content; null fields there are intentional (content not yet drafted/cited by a pharmacist) and must stay null, never filled in with invented text.
- `src/mind_recovery_mvp/loader.py` — idempotent seeding of `seed_data.py` into the DB, run on startup.
- `src/mind_recovery_mvp/db.py` — SQLAlchemy engine/session setup and the `get_db` FastAPI dependency.
- `src/mind_recovery_mvp/schemas.py` — Pydantic request/response models.
- `src/mind_recovery_mvp/usda.py` — real, live USDA FoodData Central enrichment for every food in `foods_that_may_help`, on every `/fill-event` call. Two distinct failure modes, handled differently on purpose: a **missing `FDC_API_KEY`** is a startup-time config error (loud — see `main.lifespan`); a **single food's lookup failing** at request time (timeout, rate limit, 5xx, malformed response) is caught per-food and degrades to `nutrients: None` for that one food (quiet — falls back to the plain food name, never raises, never blocks the response). Search results are restricted to `dataType=Foundation,SR Legacy` (generic whole-food entries) — without that filter, USDA's relevance search also matches branded products by name (e.g. a candy bar literally named "EGGS" outranked actual eggs for the query "eggs"). Category terms like "dairy" or "fish" still won't necessarily map to an intuitive specific food — that's a real limitation of a single-query lookup against a food database, not a bug to silently paper over.
- `src/mind_recovery_mvp/rxclass.py` — `classify_medication_class(drug_name)`, a standalone helper (not wired into an endpoint) that looks up a drug's therapeutic class via NLM's RxClass API (`getClassByRxNormDrugName`, no key needed) and maps it to one of the four target classes. Scans every classification system RxClass returns (EPC, ATC, VA, MOA, ...), not just EPC — e.g. the potassium-sparing diuretic spironolactone is EPC-classified as "Aldosterone Antagonist" (no "diuretic" in that name at all), and only shows up as a diuretic under VA/ATC.
- `src/mind_recovery_mvp/openfda.py` — `get_fda_label_reference(medication_class)`, called unconditionally on every `/fill-event`. Pulls `drug_interactions` and `warnings_and_cautions` from a representative FDA drug label via openFDA and attaches them as `fda_label_reference` — a **separate top-level field**, not nested under `recommendation`, since it's raw FDA label text, not pharmacist-curated content. `OPENFDA_API_KEY` is optional (raises the rate limit if set; unlike `FDC_API_KEY` it's not required to start). Same fail-soft contract as `usda.py`: any failure degrades the whole thing to `None` rather than raising. Two real-world quirks worth knowing: (1) `statins`/`diuretics`/`ppi` are class names, not queryable ingredient names in openFDA, so those three query by a representative drug's `pharm_class_epc` instead (the same EPC vocabulary `rxclass.py` uses) — metformin queries directly by name, but as an *exact* match on the bare ingredient (`openfda.generic_name.exact:"METFORMIN"`), because a plain substring search also matches combination products like "SITAGLIPTIN AND METFORMIN HYDROCHLORIDE" and those can outrank plain metformin's own label; (2) some FDA labels use the older `warnings` section instead of the newer `warnings_and_cautions` split — falls back to it rather than reporting no warnings when they're just filed under the other name.
- `src/mind_recovery_mvp/companion_page.py` + `src/mind_recovery_mvp/templates/companion_page.html` — renders the printable companion page (single Jinja2 template drives both the HTML and PDF endpoints, so there's one source of truth for the markup). Any null clinical field renders as a visible "Pending pharmacist review" callout, never blank.
- `src/mind_recovery_mvp/event_log.py` + `FillEventLog` model (`models.py`) — records one row per `/fill-event` call (timestamp, medication_class); `companion_page_requested` is flipped `True` on the most recent log row for that class when a companion page is subsequently requested. There's no session/request correlation in this MVP, so "subsequent" means "most recent fill-event for that medication_class," not a specific caller. `GET /metrics` aggregates this into per-class counts — an explicit stand-in for the real purchase-lift/engagement measurement described in the MVP plan, not the real thing (the response's `note` field says so too).
- `tests/conftest.py` — shared `client` fixture: a `TestClient` wired to an isolated temp-file SQLite DB (via `app.dependency_overrides[get_db]`), pre-loaded with the seed data. Also has an autouse fixture that sets a placeholder `FDC_API_KEY` and mocks `usda.lookup_food_nutrients` and `openfda.get_fda_label_reference` for every test *except* ones marked `@pytest.mark.integration` — that's what keeps the default `pytest` run offline without every test file needing to mock these itself. Note `main.py` imports the `openfda` module (`from mind_recovery_mvp import openfda`) and calls `openfda.get_fda_label_reference(...)` qualified, rather than importing the function directly — a direct `from ... import get_fda_label_reference` would bind main's own reference at import time, and patching `mind_recovery_mvp.openfda.get_fda_label_reference` afterward wouldn't affect what main.py actually calls.
- `tests/test_usda_integration.py`, `tests/test_rxclass_integration.py`, `tests/test_openfda_integration.py` — the three tests that hit real APIs; excluded by default, see Test section above.
- `tests/test_startup.py` — tests the fail-fast `FDC_API_KEY` check. Note: a bare `TestClient(app)` (what the shared `client` fixture yields) never runs FastAPI's lifespan hook — only `with TestClient(app):` does — so this is the one place in the suite that uses the context-manager form deliberately.
- `tests/` — pytest suite, uses FastAPI's `TestClient` against the `app` object directly (no live server needed to run tests).

## Known dev-environment quirk

In some sandboxed shells, `pip install -e .` editable installs are not picked up by fresh Python processes (the `.pth` file exists and is correct, but isn't processed) — `pytest`/`uvicorn` then fail with `ModuleNotFoundError: No module named 'mind_recovery_mvp'` even though `pip show` confirms the install. If this happens, run with `PYTHONPATH=src` prefixed (e.g. `PYTHONPATH=src pytest`, `PYTHONPATH=src uvicorn mind_recovery_mvp.main:app --reload`). This is specific to that shell environment, not a project misconfiguration — a normal terminal does not need this workaround.
