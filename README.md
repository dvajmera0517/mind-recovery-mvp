# mind-recovery-mvp

This is a local MVP prototype of a pharmacy-triggered nutrient-depletion recommendation engine, covering four medication classes (metformin, statins, diuretics, PPIs). It is not connected to any real pharmacy system or patient data.

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

## Demo

Single command to see the whole MVP flow end to end — fires `/fill-event` for
all four medication classes, downloads each companion-page PDF into
`./output/`, and prints a summary table:

```bash
python scripts/demo.py
```

It starts its own throwaway server on a free port with a scratch database, so
there's no need to have `uvicorn` already running.
