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
