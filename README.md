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

`/fill-event` also makes a real, live call to
[openFDA](https://api.fda.gov/drug/label.json) on every request, attaching
`drug_interactions` and `warnings_and_cautions` from the official FDA label
as `fda_label_reference` — separate from the pharmacist-curated
`recommendation`. No key needed; optionally set `OPENFDA_API_KEY` in `.env`
to raise its rate limit.

Separately, `src/mind_recovery_mvp/rxclass.py` provides
`classify_medication_class(drug_name)`, a helper that looks up a drug's
therapeutic class via [RxClass](https://rxnav.nlm.nih.gov/REST/rxclass) (NLM
— no key needed) and maps it to one of the four target classes. It's not
wired into an endpoint yet.

None of RxClass/openFDA/`OPENFDA_API_KEY` are required to start the server —
only `FDC_API_KEY` is.

## LLM-assisted content drafting (statins, diuretics, PPIs)

Three of the four medication classes are still placeholders (see the table
below). `scripts/draft_content.py` uses Claude to draft their missing fields
from a fixed, short evidence excerpt (`src/mind_recovery_mvp/evidence_excerpts.py`)
— never from general model knowledge. It never marks anything "approved":
output is stored as `content_status = "llm_drafted_pending_pharmacist_review"`,
and the companion page keeps showing "Pending pharmacist review" for that
record regardless of what's now in the database, until a human reviews it.

```bash
python scripts/draft_content.py statins    # or diuretics / ppi
python scripts/review_content.py           # approve, edit, or skip each draft
```

Set `ANTHROPIC_API_KEY` in `.env` (get one at
https://console.anthropic.com/settings/keys) — only `draft_content.py` needs
it; the main server doesn't. `review_content.py` needs no API key, just a
`REVIEWER_NAME` env var (or it'll prompt you).

## Run

```bash
uvicorn mind_recovery_mvp.main:app --reload
```

Health check: `GET http://127.0.0.1:8000/health`

## Test

```bash
pytest
```

This is fully offline (USDA/RxClass/openFDA/Claude calls are mocked). To run
the four tests that hit the real APIs:

```bash
FDC_API_KEY=<your-key> ANTHROPIC_API_KEY=<your-key> pytest -m integration
```

(the Claude one skips itself with a message if `ANTHROPIC_API_KEY` isn't set
— there's no free/no-signup key for it the way USDA has `DEMO_KEY`)

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

This table reflects the data as originally seeded. Running
`scripts/draft_content.py` + `scripts/review_content.py` (see above) moves a
class from `PLACEHOLDER` to `llm_drafted_pending_pharmacist_review` and then
to `approved`/`approved_with_edits` — but the companion page still shows
"Pending pharmacist review" for everything up through the drafted state,
regardless of what's actually in the database by then.
