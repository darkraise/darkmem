# Promotion metrics — 2026-05-02 to 2026-07-31

- database: `localhost:5433/darkmem` (read-only)
- window: `2026-05-02T16:57:06.076301+00:00` .. `2026-07-31T16:57:06.076301+00:00`
- schema present: False
- `verified` payloads validated (T2.60 / unknown-vocabulary guard): 0
- under-powered threshold: < 5 observations

This is a measurement, not a verdict: no bar is stated or judged here (T2.40's role). Every rate below carries its denominator; a slice below the under-powered threshold is labelled, never read as a plain percentage.

**Units: every promotion-rate figure below is per-transition (per journaled `verified` event), not per-fact.** Doc 17 §5.1 states the metric as `(facts promoted) / (eligible candidate facts)`; a fact that exits `candidate` more than once inside the window (e.g. promote, later demote, later re-promote) contributes one row per transition to both promoted and eligible here, not one row per fact. The false-promotion audit below is the one number in this report that IS de-duplicated to distinct facts (`COUNT(DISTINCT object_id)`), matching doc 17's own wording for that metric — do not read the two counting conventions as consistent with each other.

## Promotion rate — by which N-fired gate (`gate_fired`)

| gate_fired | promoted | eligible | rate |
|---|---|---|---|
| (no eligible transitions in window) | - | - | n/a **UNDER-POWERED** |

## Promotion rate — by source-kind diversity

**Caveat: the `diverse` bucket is not equivalent to "the diversity gate fired".** It buckets on whether the payload's `source_kinds` list (the union of kinds across every origin that ever asserted the fact, including a single origin whose own rows span two kinds) contains more than one distinct value. The ladder's actual diversity gate (`OriginProfile.kinds_are_diverse`) is stricter: it requires **two distinct, attributable origins** that differ in kind, and returns `False` outright for a lone origin regardless of how many kinds that one origin spans. So a fact asserted by exactly one origin under two kinds slices as `diverse` here without ever having lowered N — this is a deliberately independent cut (per doc 17 §5.1's two-slice-axes instruction), not a proxy for `gate_fired = 'diversity'`; use the gate_fired table above for that question.

| bucket | promoted | eligible | rate |
|---|---|---|---|
| (no eligible transitions in window) | - | - | n/a **UNDER-POWERED** |

## False-promotion audit

Count of DISTINCT corroborated facts later disputed or human-rejected (doc 17 §5.1). Sources: `events` self-join for the disputed half (T2.06's exact SQL, tuple-compared).

**The human-rejected half is structurally blind, not merely quiet.** T2.62 defines `knowledge_triples.review_state` as pure queue-membership: the only writable value is `'open'`, and human resolution clears it to `NULL` — no value in that design ever means "rejected". This runner's guard (`KNOWN_REVIEW_STATES = {'open'}`) will therefore never trip and `human-rejected` below will read 0 forever under that design, **including once humans actually start rejecting facts** — the 0 is not evidence of zero rejections. Doc 17 §5.1's audit has no source for this half until a rejection verdict is journalled somewhere this runner can read (most naturally `events`, matching the disputed half's own shape); until then, treat `human-rejected` as absent, not measured.

- corroborated facts in window: 0
- later disputed: 0
- human-rejected: 0
- false-promotion rate: n/a **UNDER-POWERED**

## Notes

- the target database has no `events` table (never migrated) -- treated as 0 observations by construction, under-powered, not a pass

