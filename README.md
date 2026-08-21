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
