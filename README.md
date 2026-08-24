# mind-recovery-mvp

This is a local MVP prototype of a pharmacy-triggered nutrient-depletion recommendation engine, covering five medication classes (metformin, statins, diuretics, PPIs, GLP-1 agonists). It is not connected to any real pharmacy system or patient data.

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

`src/mind_recovery_mvp/rxclass.py` provides `classify_medication_class(drug_name)`,
which looks up a drug's therapeutic class via
[RxClass](https://rxnav.nlm.nih.gov/REST/rxclass) (NLM — no key needed) and
maps it to one of the five target classes, or `None` if it doesn't match any
— a normal outcome for most real-world drug names, not an error.

None of RxClass/openFDA/`OPENFDA_API_KEY` are required to start the server —
only `FDC_API_KEY` is.

### `POST /simulate-prescription`

Takes a raw drug name — `{"drug_name": "atorvastatin"}` — and runs the full
pipeline live in one call: RxClass classifies it, then (if classified) looks
up the matching clinical content record, enriches its foods via USDA, and
pulls the openFDA label reference — the same functions `/fill-event` uses,
not reimplemented. Returns one consolidated response: the classification
result, the clinical content record with its real `content_status` (whatever
it currently is — `approved`, a pending-review state, or still
`PLACEHOLDER`), the USDA-enriched foods, the openFDA reference text, and a
`timing_ms` breakdown (RxClass/USDA/openFDA, each in milliseconds) so you can
see these are real network calls, not instant mocked ones.

A drug that doesn't map to any of the five classes (e.g. `amoxicillin`)
still returns `200` with `classification.matched: false` and a `message`
explaining why — not an error, since most real-world drug names aren't in
scope for this prototype. In that case `usda`/`openfda` in `timing_ms` are
`null` (not `0`) — the pipeline stops after classification and never
attempts them.

## Content drafting for statins, diuretics, PPIs, GLP-1

The four still-placeholder classes (see the table below) can each be
drafted two ways with `scripts/draft_content.py`. Neither mode ever marks
anything "approved" — a human always reviews the draft via
`scripts/review_content.py` first, and the companion page keeps showing
"Pending pharmacist review" for that record regardless of what's now in
the database, until that happens.

**Default — sample content (no API call, no key needed):**

```bash
python scripts/draft_content.py statins    # or diuretics / ppi / glp1
```

Loads hand-written demo copy from `src/mind_recovery_mvp/sample_content.json`.
`content_status` becomes `"sample_content_pending_pharmacist_review"`.

**`--use-llm` — real Claude call (requires `ANTHROPIC_API_KEY`):**

```bash
python scripts/draft_content.py statins --use-llm
```

Drafts from the fixed excerpt in `src/mind_recovery_mvp/evidence_excerpts.py`
— never from general model knowledge. `content_status` becomes
`"llm_drafted_pending_pharmacist_review"`.

Either way:

```bash
python scripts/review_content.py           # approve, edit, or skip each draft
```

Set `ANTHROPIC_API_KEY` in `.env` (get one at
https://console.anthropic.com/settings/keys) only if you'll use `--use-llm`
— the default mode, the main server, and `review_content.py` all need no
API key at all, just a `REVIEWER_NAME` env var for the reviewer's name (or
it'll prompt you). Once approved, the companion page shows a provenance
line — printed on the page itself, not just stored as data — distinguishing
all three ways content can originate, deliberately worded so they can never
read as interchangeable:

- `"Content origin: pharmacist-authored"` — metformin only; never went
  through drafting or review, so no review claim is made about it.
- `"Content origin: Sample content (hand-written for demo), pharmacist-reviewed"`
- `"Content origin: LLM-drafted, pharmacist-reviewed"`

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
the tests that hit the real APIs:

```bash
FDC_API_KEY=<your-key> ANTHROPIC_API_KEY=<your-key> pytest -m integration
```

(the Claude one skips itself with a message if `ANTHROPIC_API_KEY` isn't set
— there's no free/no-signup key for it the way USDA has `DEMO_KEY`)

## Demo

Single command to see the whole MVP flow end to end — the *before/after*
story of drafting and review, not just a snapshot:

```bash
python scripts/demo.py
```

1. Renders and saves all five companion pages exactly as originally seeded
   to `./output/before_review/` — metformin complete-but-unsigned, the
   other four all showing "Pending pharmacist review".
2. Drafts sample content (the default, no-API-key path from the section
   above) for statins, diuretics, ppi, and glp1.
3. Runs those four drafts through `scripts/review_content.py`
   non-interactively, approving each as-is, with reviewer name `"Demo
   Reviewer (not a licensed pharmacist)"` — printed inside loud `!!!!!`
   banners in the console output specifically so it can't be mistaken for
   a real review.
4. Re-renders and saves all five companion pages to `./output/after_review/`
   — statins/diuretics/ppi/glp1 now fully populated, with the sample-content
   provenance line on the page.
5. Prints a before/after `content_status` table for all five classes, and
   confirms all 10 PDFs (5 classes × before/after) generated successfully.

It starts its own throwaway server on a free port with a scratch database, so
there's no need to have `uvicorn` already running. If `FDC_API_KEY` isn't set,
it falls back to USDA's public `DEMO_KEY` automatically — the whole demo,
including the drafting/review steps, needs zero API keys by default.

## What's real vs. placeholder

The clinical content in `src/mind_recovery_mvp/seed_data.py` is **not**
uniformly complete. Only one of the five medication classes has drafted
content for every field — and even that one isn't signed off yet. None of
this is ready for a real pilot store without pharmacist/dietitian review.

| Medication class | Status | What's filled in | What's missing |
|---|---|---|---|
| **metformin** | Drafted — needs final pharmacist/legal sign-off | All 6 content fields | Sign-off itself; `clinical_source` is a placeholder (`"TRC Healthcare Natural Medicines / [approved clinical reference]"` — names a plausible source family but isn't a specific, verifiable citation) |
| **statins** | PLACEHOLDER | `nutrient_concern` (CoQ10 association), `supplements_to_discuss` | `why_it_matters`, `foods_that_may_help`, `talk_to_pharmacist_if`, `clinical_source` |
| **diuretics** | PLACEHOLDER | `nutrient_concern` (potassium/magnesium risk), `foods_that_may_help` | `why_it_matters`, `supplements_to_discuss`, `talk_to_pharmacist_if`, `clinical_source` |
| **PPIs** | PLACEHOLDER | `nutrient_concern` only (magnesium, calcium, B12) | `why_it_matters`, `foods_that_may_help`, `supplements_to_discuss`, `talk_to_pharmacist_if`, `clinical_source` |
| **glp1** | PLACEHOLDER — added as a 5th target class; nothing drafted or reviewed yet | `nutrient_concern` only (reduced overall intake — protein, B12, iron, D, thiamine) | `why_it_matters`, `foods_that_may_help`, `supplements_to_discuss`, `talk_to_pharmacist_if`, `clinical_source` |

Every missing field renders as a visibly highlighted **"Pending pharmacist
review"** callout on the companion page (`GET /companion-page/{class}` or
`.pdf`) — never blank, never filled in with invented text. Before any of this
goes near a real pilot store, statins, diuretics, PPIs, and glp1 need a
pharmacist/dietitian to draft and cite the missing fields, and metformin
needs its citation replaced with a real, verifiable reference and formal
sign-off.

This table reflects the data as originally seeded. Running
`scripts/draft_content.py` + `scripts/review_content.py` (see above) moves a
class from `PLACEHOLDER` to `sample_content_pending_pharmacist_review` (or
`llm_drafted_pending_pharmacist_review` with `--use-llm`) and then to
`approved`/`approved_with_edits` — but the companion page still shows
"Pending pharmacist review" for everything up through the drafted state,
regardless of what's actually in the database by then. `python
scripts/demo.py` (see the Demo section below) runs through this whole
progression automatically and shows both ends of it side by side.
