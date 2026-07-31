# Promotion metrics — 2026-05-02 to 2026-07-31

- database: `localhost:5433/darkmem` (read-only)
- window: `2026-05-02T16:30:29.167947+00:00` .. `2026-07-31T16:30:29.167947+00:00`
- schema present: False
- `verified` payloads validated (T2.60 / unknown-vocabulary guard): 0
- under-powered threshold: < 5 observations

This is a measurement, not a verdict: no bar is stated or judged here (T2.40's role). Every rate below carries its denominator; a slice below the under-powered threshold is labelled, never read as a plain percentage.

## Promotion rate — by which N-fired gate (`gate_fired`)

| gate_fired | promoted | eligible | rate |
|---|---|---|---|
| (no eligible transitions in window) | - | - | n/a **UNDER-POWERED** |

## Promotion rate — by source-kind diversity

| bucket | promoted | eligible | rate |
|---|---|---|---|
| (no eligible transitions in window) | - | - | n/a **UNDER-POWERED** |

## False-promotion audit

Count of corroborated facts later disputed or human-rejected (doc 17 §5.1). Sources: `events` self-join for the disputed half (T2.06's exact SQL, tuple-compared); `knowledge_triples.review_state` for the human-rejected half, which is 0 today by construction -- no writer for a rejection verdict exists yet (T2.62 not landed).

- corroborated facts in window: 0
- later disputed: 0
- human-rejected: 0
- false-promotion rate: n/a **UNDER-POWERED**

## Notes

- the target database has no `events` table (never migrated) -- treated as 0 observations by construction, under-powered, not a pass

