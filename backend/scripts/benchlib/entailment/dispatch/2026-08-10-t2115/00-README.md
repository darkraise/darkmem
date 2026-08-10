# T2.115 dispatch record — the firewall as executed

The branch review's I-6: T2.54 committed 17 dispatch artifacts and T2.110
committed 4, while T2.115 committed **zero** — leaving the firewall and the
agreement rates as prose with no evidence behind them. Its exact words: this is
what would convert *"no path was found by which the failure attribution reached
an authored pair"* into *"no path existed"*.

These files are that evidence, recovered from the executing session's scratchpad
before it was lost. They were **not** written for publication, so read them as
what they are: the actual briefs and outputs, unedited.

| File | What it is |
|---|---|
| `01-authoring-brief-nontemporal.md` | The allowlist brief for the 57 non-temporal pairs |
| `02-authoring-brief-temporal.md` | The 9 temporal pairs; carries the fixed 2C/3E/4U mix |
| `03-authored-nontemporal.json` | Returned pairs + the ten logged skips |
| `04-authored-temporal.json` | Returned temporal pairs |
| `05-blind-export.json` | `strip_for_blind` output: id, premise, hypothesis only |
| `06-blind-pass-A.json` | Pass A verdicts + rule cited per pair (Opus) |
| `07-blind-pass-B.json` | Pass B verdicts + rule cited per pair (Sonnet) |
| `08-escalations.json` | The two the merge rule escalated (eg-0405, eg-0416) |

**Blindness attestations, transcribed from the dispatch results** — the agents
reported these; the transcripts themselves are not artifacts this repo keeps:

- *Non-temporal author*: read only the brief, `LABELLING.md` lines 1–558
  (bounded by a `grep -n` for `## History` so nothing below it was opened), the
  assignment file, and four `gold.json` pairs sampled for schema and register.
  No forbidden path read; `git` never run.
- *Temporal author*: same allowlist; no forbidden path read; `git` never run.
- *Pass A*: read `LABELLING.md` lines 1–572 only (same `grep` bound) and the
  adjudication input. Did not open `gold.json`, `docs/planning/`, `docs/eval/`,
  `resample_runs/`; no `git`.
- *Pass B*: same; flagged eg-0416 as a rulebook gap independently of pass A.

**What this record cannot show** (M-11): there is no per-slot skip log for round
3. The ten skips are in `03-`'s `skips` list with slot, triple_key and reason,
and the branch review re-derived all ten grounds from the committed assignment
and found they check out — but the round did not write the log the protocol
describes.

**Two defects this evidence does not exonerate**, both recorded in the gate
ledger and both awaiting owner adjudication: C-1 (the replacement broke ratified
clause 5's slice-composition requirement) and C-2 (`eg-0367` is a reworded
near-duplicate of `eg-0093`, which the byte-uniqueness check could not catch).
