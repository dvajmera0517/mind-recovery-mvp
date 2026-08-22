# mind-recovery-mvp

This is a local MVP prototype of a pharmacy-triggered nutrient-depletion recommendation engine, covering four medication classes (metformin, statins, diuretics, PPIs). It is not connected to any real pharmacy system or patient data.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Edit `.env` and set `FDC_API_KEY` — a free USDA FoodData Central key from
https://fdc.nal.usda.gov/api-key-signup, or the public `DEMO_KEY` (rate-limited,
no signup) to try things out. The server enriches `foods_that_may_help` with a
real, live USDA lookup on every `/fill-event` call, so it **fails fast at
startup** if this isn't set.

## Run

```bash
uvicorn mind_recovery_mvp.main:app --reload
```

Health check: `GET http://127.0.0.1:8000/health`

## Test

```bash
pytest
```

This is fully offline (USDA calls are mocked). To run the one test that hits
the real USDA API:

```bash
FDC_API_KEY=<your-key> pytest -m integration
```

## Demo

Single command to see the whole MVP flow end to end — fires `/fill-event` for
all four medication classes, downloads each companion-page PDF into
`./output/`, and prints a summary table:

```bash
python scripts/demo.py
```

It starts its own throwaway server on a free port with a scratch database, so
there's no need to have `uvicorn` already running. If `FDC_API_KEY` isn't set,
it falls back to USDA's public `DEMO_KEY` automatically.

## What's real vs. placeholder

The clinical content in `src/mind_recovery_mvp/seed_data.py` is **not**
uniformly complete. Only one of the four medication classes has drafted
content for every field — and even that one isn't signed off yet. None of
this is ready for a real pilot store without pharmacist/dietitian review.

| Medication class | Status | What's filled in | What's missing |
|---|---|---|---|
| **metformin** | Drafted — needs final pharmacist/legal sign-off | All 6 content fields | Sign-off itself; `clinical_source` is a placeholder (`"TRC Healthcare Natural Medicines / [approved clinical reference]"` — names a plausible source family but isn't a specific, verifiable citation) |
| **statins** | PLACEHOLDER | `nutrient_concern` (CoQ10 association), `supplements_to_discuss` | `why_it_matters`, `foods_that_may_help`, `talk_to_pharmacist_if`, `clinical_source` |
| **diuretics** | PLACEHOLDER | `nutrient_concern` (potassium/magnesium risk), `foods_that_may_help` | `why_it_matters`, `supplements_to_discuss`, `talk_to_pharmacist_if`, `clinical_source` |
| **PPIs** | PLACEHOLDER | `nutrient_concern` only (magnesium, calcium, B12) | `why_it_matters`, `foods_that_may_help`, `supplements_to_discuss`, `talk_to_pharmacist_if`, `clinical_source` |

Every missing field renders as a visibly highlighted **"Pending pharmacist
review"** callout on the companion page (`GET /companion-page/{class}` or
`.pdf`) — never blank, never filled in with invented text. Before any of this
goes near a real pilot store, statins, diuretics, and PPIs need a
pharmacist/dietitian to draft and cite the missing fields, and metformin
needs its citation replaced with a real, verifiable reference and formal
sign-off.
