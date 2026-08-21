# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project scope

This is a **local MVP prototype** of a pharmacy-triggered nutrient-depletion recommendation engine. It covers exactly **four medication classes**: metformin, statins, diuretics, and PPIs (proton pump inhibitors). It is **not connected to any real pharmacy system or patient data** — do not add integrations, network calls to external health/pharmacy APIs, or real patient data handling without explicit direction. Keep changes scoped to these four medication classes unless asked to expand scope.

## Tech stack

- Python 3.11+
- FastAPI (API layer)
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

- `src/mind_recovery_mvp/main.py` — FastAPI app instance and route definitions. Currently just a health-check endpoint; this is the entry point for `uvicorn`.
- `tests/` — pytest suite, uses FastAPI's `TestClient` against the `app` object directly (no live server needed to run tests).

The project is at skeleton stage: no domain logic (medication classes, nutrient-depletion rules, recommendation engine) has been implemented yet.
