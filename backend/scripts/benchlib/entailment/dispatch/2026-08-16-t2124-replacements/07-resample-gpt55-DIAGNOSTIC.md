# gpt-5.5 second sitting — DIAGNOSTIC, not a certifying sitting (2026-08-16)

Owner-directed after the v4-pro miss. n = 93, same gold sha `cac8c974`, so the
seeded draw is the **identical 93 pairs**. Raw replies:
`resample_runs/2026-08-16-gpt-5-5-cac8c974.json`.

**Result: 1 disagreement, which numerically clears the `<= 1` bar.**
**It is deliberately NOT written into `gold.json` and must not be banked.** Two
reasons, the second decisive.

## 1. It is a model swap without the rule fix the protocol requires

Step 11's failure path is classify -> **rule-then-pairs** -> redraw. The rule
gap the first sitting exposed is still open, and the gold is byte-identical, so
this is a second model on the same pairs under the same unresolved rule.
Certifying on it would mean the gold passed by finding a model that agrees with
it. The two-consecutive-failure stop exists to bound exactly that move.

## 2. The two vendors CONVERGE on the pair that matters

| pair | gold | deepseek-v4-pro | gpt-5.5 |
|---|---|---|---|
| eg-0486 | entailed | **unsupported** | **unsupported** |
| eg-0546 | entailed | unsupported | entailed |
| eg-0650 | entailed | entailed | entailed |

Model-vs-model agreement across all 93 is **92/93 = 0.9892**.

**Two independent non-Claude models, different vendors, both read `eg-0486` as
unsupported.** The `<= 1` bar tolerates a single disagreement because one model
can be wrong; it was not designed for a single disagreement that a second
independent instrument corroborates. Banking this pass would certify a gold
containing a pair both instruments flagged.

`eg-0486`: premise "clickhouse depends on ledger-02", hypothesis "ledger-02 has
at least one **component** that depends on it". The hypothesis asserts
clickhouse is a *component* — content the premise never supplies.

## 3. What the disagreement between the two models sharpens

`eg-0486` and `eg-0546` share the unearned-sortal defect but differ on one axis:

- `eg-0486` generalises the **subject** (clickhouse -> "at least one component"),
- `eg-0546` generalises the **object** (etcd -> "at least one other component").

v4-pro rejected both; gpt-5.5 rejected only the subject-side one. So the open
rule question is not merely *"must the sortal be earned?"* but possibly
*"must it be earned on the subject side only?"* — the object-side reading being
that "one of the things Consul uses" is already licensed by the relation.

Both readings are defensible and the gold currently states neither. That is the
ruling owed, and this second sitting bought the axis it turns on rather than a
certification.

## Cost incurred, recorded

gpt-5.5 has now been run over 93 of this gold's pairs, so it carries the
resample-circularity objection as a T2.125 judge exactly as v4-pro does. Both
known candidates are now spent in that sense. The owner accepted this before the
run.
