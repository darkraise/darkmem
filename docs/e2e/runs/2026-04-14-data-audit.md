# Data Audit — v2 fine-tuning corpus revamp (2026-04-14)

## Sources audited

- `fine-tuning/data/validated/all.jsonl` (8,000 rows, existing extraction schema) — audited as `extraction` kind
- `fine-tuning/data/classification/train.jsonl` (2,579 rows, existing classification schema) — audited as `classification` kind
- `docs/e2e/scripts/retrieval_eval/train_pairs_5k.jsonl` (200 rows, existing retrieval pair schema) — audited as `retrieval` kind

## Method

200-row random sample (seed=42) per source, scored by `fine-tuning/scripts/audit_existing.py` against the v2 schema defined in `fine-tuning/config/taxonomy_v2.yaml`. Absorb threshold: 60% sample pass rate.

## Results

| Source | Total sampled | Passed | Pass rate | Decision |
|---|---:|---:|---:|---|
| extraction | 200 | 136 | 68.00% | absorb |
| classification | 200 | 0 | 0.00% | discard |
| retrieval | 200 | 0 | 0.00% | discard |

(Retrieval source has exactly 200 rows — full file used, not a subsample.)

## Absorb procedure

**extraction** — append passing rows to `fine-tuning/data/v2/shared/` in Task 9:

```bash
cd fine-tuning
python -m scripts.validate_v2 data/validated/all.jsonl --kind extraction \
  --failed-dir data/v2/failed
# Then copy passing rows (those not in failed/) into data/v2/shared/absorbed_extraction.jsonl
```

**classification** — discard; regenerate from scratch in the classification top-up generation task.

**retrieval** — discard; regenerate from scratch in the retrieval top-up generation task.

## Top failure patterns

### extraction

```
(11) unknown memory_type: debug
 (9) unknown memory_type: workflow
```

All 64 failures stem from exactly two old memory types (`debug`, `workflow`) that were removed from the v2 7-type taxonomy (`fact`, `decision`, `preference`, `problem`, `reference`, `architecture`, `milestone`). The underlying text and entity/relationship annotations are otherwise schema-valid, so these rows are candidates for manual relabelling rather than outright discard.

### classification

```
(20) foreign field on top-up row: label
(20) missing required fields: ['domain', 'id', 'memory_type']
```

Every row fails on two independent issues: the old `label` field is foreign to the v2 classification top-up schema, and the rows lack `id`, `domain`, and `memory_type` entirely. The schema is incompatible; regeneration is required.

### retrieval

```
(20) missing required fields: ['id', 'query_kind', 'source_id']
```

Every row in the old `{query, positive}` format is missing `id`, `source_id`, and `query_kind`. No remediation is feasible without re-running generation; discard and regenerate.

## Implications

At 68% pass rate the extraction corpus yields approximately 5,440 absorbable rows out of 8,000. These cover the `fact`, `decision`, `preference`, `problem`, `reference`, `architecture`, and `milestone` types with real entity and relationship annotations, giving the shared-base corpus a substantial head start. The 32% failure rate (rows tagged `debug` or `workflow`) should be reviewed for potential relabelling into the closest v2 type before the top-up generation budget is finalised. Classification and retrieval will be generated entirely from scratch, so their session budgets remain at the full planned allocation. The net effect is that shared-base generation sessions can be reduced proportionally to the absorbed count — approximately 27 sessions needed instead of the planned 35 (absorbing roughly 5,440 of the 7,000 shared target).
