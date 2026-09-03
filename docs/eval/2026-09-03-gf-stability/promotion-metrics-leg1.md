# Promotion metrics — 2026-06-05 to 2026-09-03

- database: `localhost:5433/darkmem` (read-only)
- window: `2026-06-05T05:01:38.286987+00:00` .. `2026-09-03T05:01:38.286987+00:00`
- schema present: False
- `verified` payloads validated (T2.60 / unknown-vocabulary guard): 0
- under-powered threshold: < 5 observations

This is a measurement, not a verdict: no bar is stated or judged here (T2.40's role). Every rate below carries its denominator; a slice below the under-powered threshold is labelled, never read as a plain percentage.

**Units: every promotion-rate figure below is per-transition (per journaled `verified` event), not per-fact.** Doc 17 §5.1 states the metric as `(facts promoted) / (eligible candidate facts)`; a fact that exits `candidate` more than once inside the window (e.g. promote, later demote, later re-promote) contributes one row per transition to both promoted and eligible here, not one row per fact. The false-promotion audit below is the one number in this report that IS de-duplicated to distinct facts (`COUNT(DISTINCT object_id)`), matching doc 17's own wording for that metric — do not read the two counting conventions as consistent with each other.

## Promotion rate — by which N-fired gate (`gate_fired`)

| gate_fired | promoted | blocked | eligible | rate |
|---|---|---|---|---|
| (no eligible transitions in window) | - | - | - | n/a **UNDER-POWERED** |

## Promotion rate — by source-kind diversity

**Caveat: the `diverse` bucket is not equivalent to "the diversity gate fired".** It buckets on whether the payload's `source_kinds` list (the union of kinds across every origin that ever asserted the fact, including a single origin whose own rows span two kinds) contains more than one distinct value. The ladder's actual diversity gate (`OriginProfile.kinds_are_diverse`) is stricter: it requires **two distinct, attributable origins** that differ in kind, and returns `False` outright for a lone origin regardless of how many kinds that one origin spans. So a fact asserted by exactly one origin under two kinds slices as `diverse` here without ever having lowered N — this is a deliberately independent cut (per doc 17 §5.1's two-slice-axes instruction), not a proxy for `gate_fired = 'diversity'`; use the gate_fired table above for that question.

| bucket | promoted | blocked | eligible | rate |
|---|---|---|---|---|
| (no eligible transitions in window) | - | - | - | n/a **UNDER-POWERED** |

## False-promotion audit

Count of DISTINCT corroborated facts later disputed or human-rejected (doc 17 §5.1). Sources: `events` self-join for the disputed half (T2.06's exact SQL, tuple-compared).

**The human-rejected half is live as of T2.63.** It reads the `human_verdict` journal, not `review_state` -- that column is pure queue-membership (T2.62: only `open` is writable, cleared to NULL on resolution), so it could never carry a verdict and this count read 0 forever while its own tripwire could not fire. A 0 here is now a measurement, not an absence -- but note the only human verb reachable today is rejection; ratify is T2.05's and re-ground/edit have no owner, so this counts rejections rather than all adjudication.

- corroborations in window: 0
- later disputed: 0
- later human-rejected: 0
- DISTINCT facts in either arm: 0
- false-promotion rate (point estimate): n/a **UNDER-POWERED**
- corroborated facts later expired (R2 companion): 0

**The last line is `promotion_bars` ruling R2's companion, and the rate above must not be quoted without it.** An entity-merge fact fold keeps one row's id and retires the other, so a corroboration and a later dispute can land on two ids that the audit's join can never bring together — the audit then undercounts, the one direction it may not err in silently. A non-zero count here caps what a zero rate claims. It is an upper bound on folds by construction: human adjudication and provenance withdrawal expire facts too, and the journal carries no discriminator, so this counts every expiry after an in-window corroboration rather than narrowing the cap on a guess.

The three counts above do not sum: a fact the human rejects is usually one the queue served them *because* it was disputed, so it appears in both arms. doc 17 §5.1 counts facts, so the rate divides the DISTINCT union — summing the arms reported 200% off a single fact.

## Notes

- the target database has no `events` table (never migrated) -- treated as 0 observations by construction, under-powered, not a pass

