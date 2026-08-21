# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project scope

This is a **local MVP prototype** of a pharmacy-triggered nutrient-depletion recommendation engine. It covers exactly **four medication classes**: metformin, statins, diuretics, and PPIs (proton pump inhibitors). It is **not connected to any real pharmacy system or patient data** — do not add integrations, network calls to external health/pharmacy APIs, or real patient data handling without explicit direction. Keep changes scoped to these four medication classes unless asked to expand scope.

## Tech stack

- Python 3.11+
- FastAPI (API layer)
- SQLAlchemy + SQLite (clinical content storage)
- Jinja2 + xhtml2pdf (printable companion page — HTML and PDF; xhtml2pdf was chosen over WeasyPrint because WeasyPrint needs native Pango/GObject libraries that aren't available in this dev environment)
- httpx (outbound calls to USDA FoodData Central)
- pytest + httpx (`TestClient`) for tests
- `src/` layout, packaged as `mind_recovery_mvp`, built with setuptools via `pyproject.toml`

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

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

## Architecture

- `src/mind_recovery_mvp/main.py` — FastAPI app instance, lifespan hook (DB init + seed load), and all routes. Entry point for `uvicorn`.
- `src/mind_recovery_mvp/models.py` — `NutrientContent` SQLAlchemy model (one row per medication class).
- `src/mind_recovery_mvp/seed_data.py` — the verbatim clinical content for the four seeded medication classes (metformin, statins, diuretics, ppi). This is the single source of truth for clinical content; null fields there are intentional (content not yet drafted/cited by a pharmacist) and must stay null, never filled in with invented text.
- `src/mind_recovery_mvp/loader.py` — idempotent seeding of `seed_data.py` into the DB, run on startup.
- `src/mind_recovery_mvp/db.py` — SQLAlchemy engine/session setup and the `get_db` FastAPI dependency.
- `src/mind_recovery_mvp/schemas.py` — Pydantic request/response models.
- `src/mind_recovery_mvp/usda.py` — optional USDA FoodData Central enrichment for `foods_that_may_help`, gated on the `FDC_API_KEY` env var. Every failure mode (missing key, timeout, HTTP error, malformed response) is caught per-food and degrades to `None` rather than raising — this must never block `/fill-event` from responding.
- `src/mind_recovery_mvp/companion_page.py` + `src/mind_recovery_mvp/templates/companion_page.html` — renders the printable companion page (single Jinja2 template drives both the HTML and PDF endpoints, so there's one source of truth for the markup). Any null clinical field renders as a visible "Pending pharmacist review" callout, never blank.
- `src/mind_recovery_mvp/event_log.py` + `FillEventLog` model (`models.py`) — records one row per `/fill-event` call (timestamp, medication_class); `companion_page_requested` is flipped `True` on the most recent log row for that class when a companion page is subsequently requested. There's no session/request correlation in this MVP, so "subsequent" means "most recent fill-event for that medication_class," not a specific caller. `GET /metrics` aggregates this into per-class counts — an explicit stand-in for the real purchase-lift/engagement measurement described in the MVP plan, not the real thing (the response's `note` field says so too).
- `tests/conftest.py` — shared `client` fixture: a `TestClient` wired to an isolated temp-file SQLite DB (via `app.dependency_overrides[get_db]`), pre-loaded with the seed data. Used by most test modules instead of hitting the real app DB file.
- `tests/` — pytest suite, uses FastAPI's `TestClient` against the `app` object directly (no live server needed to run tests). External calls (USDA) are mocked in tests — never hit the real API in the test suite.

## Known dev-environment quirk

In some sandboxed shells, `pip install -e .` editable installs are not picked up by fresh Python processes (the `.pth` file exists and is correct, but isn't processed) — `pytest`/`uvicorn` then fail with `ModuleNotFoundError: No module named 'mind_recovery_mvp'` even though `pip show` confirms the install. If this happens, run with `PYTHONPATH=src` prefixed (e.g. `PYTHONPATH=src pytest`, `PYTHONPATH=src uvicorn mind_recovery_mvp.main:app --reload`). This is specific to that shell environment, not a project misconfiguration — a normal terminal does not need this workaround.
