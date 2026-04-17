# GLiNER + REBEL training and benchmark — 2026-04-16 session

## Summary

Expanded the shared v2 corpus from 7,000 to 14,000 rows, re-stratified into GLiNER and REBEL splits, fine-tuned three heads (GLiNER-small, GLiNER-large, REBEL-large), and ran head-level plus pipeline benchmarks on a 2,000-row held-out test split. **Production pick: `gliner-small-v2corpus` paired with `rebel-large-v2corpus`.** Head-level F1 is 0.465 (GLiNER-small) / 0.491 (GLiNER-large) / 0.435 (REBEL); the 2.6-point gap between GLiNER sizes falls below the 5-point threshold the plan set for preferring the larger model, and the large variant plus the warm qwen3.5:4b would exceed the 8.15 GB VRAM budget of the RTX 5060.

## Corpus expansion

| metric | value |
|---|---|
| shared rows before | 7,000 |
| shared rows after | 14,000 |
| rows added | 7,000 (140 batches × 50 rows) |
| validator pass rate after append | 14,000 / 14,000 |

Memory-type distribution after expansion:

| memory_type | count | share |
|---|---:|---:|
| decision | 3,200 | 22.9% |
| architecture | 2,636 | 18.8% |
| fact | 2,234 | 16.0% |
| milestone | 1,963 | 14.0% |
| reference | 1,733 | 12.4% |
| preference | 1,209 | 8.6% |
| problem | 1,025 | 7.3% |

Non-noise rows with entities: 13,446. Rows with non-empty relationships: 10,065 (used as the REBEL pool).

Phase 1.1 (open-corpus top-up to ~50k rows using NuNER and the REBEL dataset) was considered and skipped — the open corpora are Wikipedia-biased and would require a lossy remap onto the 35 entity and 30 relation types, pulling training distribution away from the conversational/technical memories darkmem serves. Recommendation preserved for future sessions if Phase 3 numbers need lifting on specific weak classes.

## Split sizes

GLiNER (all shared rows eligible, stratified by memory_type, seed 42):

| split | rows |
|---|---:|
| gliner_train | 10,000 |
| gliner_val | 2,000 |
| gliner_test | 2,000 |

REBEL (non-empty-rel subset only, 80/10/10 stratified by memory_type, seed 42):

| split | rows |
|---|---:|
| rebel_train | 8,052 |
| rebel_val | 1,006 |
| rebel_test | 1,007 |

REBEL val and test come in below the plan's ≥1,800 aspiration because Phase 1.1 was skipped and the darkmem-only rel-carrying pool is 10,065 rows. The 80/10/10 allocation is the only split that still clears the ≥8,000 train floor.

Gold-entity preservation through tokenization after the span-bug fix: 50,371 / 50,371 (100%). Relationship preservation: 13,405 / 13,405 (100%).

## Head-level metrics

| model | base | params | train time | batch loss (final / aggregate) | test micro F1 | type acc | mean IoU | ms / row | peak VRAM (MB) | worst 3 types (≥50 sup) | best 3 types |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---|---|
| gliner-small-v2corpus | urchade/gliner_small-v2.1 | ~50M | 349 s | 82.4 / 98.1 | 0.465 | 0.685 | 1.00 | 12.0 | 647 | library 0.03, project 0.07, activity 0.13 | publication 0.76, date 0.82, person 0.87 |
| gliner-large-v2corpus | urchade/gliner_large-v2.1 | ~210M | 12,720 s | 17.4 / 30.3 | 0.491 | 0.722 | 1.00 | 30.6 | 1,825 | pattern 0.21, project 0.22, config 0.28 | database 0.76, date 0.81, person 0.86 |
| rebel-large-v2corpus | Babelscape/rebel-large | ~407M | 1,420 s | 0.12 / 0.22 (eval 0.31) | 0.435 | n/a | n/a | 229 | 1,720 | DEPENDS_ON 0.00, PRODUCES 0.09, RELATED_TO 0.12 | REPLACES 0.64, AUTHORED_BY 0.70, PREFERS 0.73 |

Mean IoU of 1.00 on GLiNER splits confirms the span-end convention fix landed cleanly — every predicted span that matches a gold name matches the gold character offsets exactly. Before the fix every span was shifted by one token and F1 collapsed to 0.007 (see _What got cut_ below).

## Extraction pipeline metrics (Phase 4)

2-head pipeline (fine-tuned GLiNER → fine-tuned REBEL) on the 2,000-row canonical test split. Gold entities are not fed into REBEL — the pipeline uses GLiNER's predictions as the entity hint, so entity errors propagate to relation extraction.

| pairing | entity F1 | rel F1 | direction rate | latency (ms/row) | peak VRAM (MB, nvidia-smi) |
|---|---:|---:|---:|---:|---:|
| gliner-small + rebel-large | 0.727 | 0.349 | 0.995 | 213 | 2,973 |
| gliner-large + rebel-large | 0.739 | 0.363 | 0.996 | 264 | 4,164 |

Entity F1 in the pipeline is higher than the head-level F1 because `scripts.evaluate` matches entities by (name, type) rather than by exact character offsets — more forgiving than the strict head-level scorer in `eval_entity.py`. Direction rate approaches 1.0 because REBEL consistently emits source and target in the same order as the gold.

## 4-head VRAM co-load audit (Phase 5)

Idle allocation with classifier (modernbert-base v3aug2), retriever (bge-base-7500clean), a GLiNER variant, and REBEL-large all loaded on CUDA at once. The ollama container was not running during the audit so the warm qwen3.5:4b footprint (~3 GB per PRODUCTION.md) is not included — add it to the totals for the production picture.

| variant | classifier | retriever | GLiNER | REBEL | torch total | nvidia-smi | with qwen3.5:4b (est.) |
|---|---:|---:|---:|---:|---:|---:|---:|
| with gliner-small | 619 | 439 | 613 | 1,625 | 3,297 | 3,932 | ~6,932 MB |
| with gliner-large | 619 | 439 | 1,782 | 1,625 | 4,905 | 5,486 | ~8,486 MB |

Numbers in MB. GPU total 8,151 MB. Threshold for recommending the large variant: ≤ 7,200 MB including qwen3.5:4b.

## Production recommendation

Pick **`gliner-small-v2corpus` + `rebel-large-v2corpus`**.

Two independent criteria point the same way:

1. **F1 gap rule.** Plan: recommend GLiNER-large only if (head-level test F1 large − F1 small) ≥ 5 points. Observed gap is 0.491 − 0.465 = 0.026 points, which is 2.6 points. Below threshold.
2. **VRAM rule.** Plan: recommend GLiNER-large only if the 4-head sum with qwen3.5:4b ≤ 7.2 GB. Observed estimate is ~8.5 GB, which also exceeds the 8.15 GB card capacity. Above threshold.

GLiNER-small additionally runs at 12 ms/row vs 31 ms/row, leaving more headroom for REBEL and qwen3.5:4b latency inside a single extraction request.

## What got cut

- **Cross-encoder reranker training or benchmarking** — explicitly out of scope.
- **Phase 1.1 open-corpus top-up (NuNER + REBEL dataset)** — documented in the plan, gated on user confirmation, decided against to keep training distribution on-domain. If Phase 3 per-type weaknesses (library, project, activity for GLiNER; DEPENDS_ON, PRODUCES, RELATED_TO for REBEL) matter for production, a targeted Phase 1.1 aimed only at those classes is the cheapest next lever.
- **First GLiNER training pass (~3.7 h wall-clock wasted)** — landed with a labelling bug. `_char_spans_to_token_spans` in `scripts/validate_data.py` produced exclusive end-token indices while GLiNER treats `ner = [[start, end, label]]` as inclusive. The resulting model confidently predicted every entity extended by one trailing word (for example `CodeQL runs` instead of `CodeQL`), collapsing head-level F1 to 0.007. Fixed in commit `7ccbf32` by changing `end_tok = ti + 1` to `end_tok = ti`; both GLiNER models were retrained. REBEL and the canonical splits were unaffected.

## Follow-ups

- **Per-type class imbalance.** Several high-support entity types (library, project, activity, pattern, config) and relation types (DEPENDS_ON, PRODUCES, RELATED_TO) sit below F1 0.3. Two reasonable levers: tighter entity-pool diversity in the synthetic minting prompts, or a targeted Phase 1.1 using the subset of NuNER/REBEL-dataset that maps cleanly onto those classes.
- **Hugging Face token rotation.** `fine-tuning/scripts/train_gliner.py` and `train_rebel.py` still embed `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` as a fallback default. Pre-existing, flagged by the plan as out-of-scope; rotate and move to env-only before any broader sharing.
- **Backend wiring.** The extraction pipeline for the backend service still needs to consume `models/gliner-small-v2corpus/best` and `models/rebel-large-v2corpus/best`. `scripts/evaluate.py` already demonstrates the two-head contract end-to-end; wire the same loader into `backend/app/services/extraction.py` when the production roll-forward lands.
- **Ollama restart.** Phase 5 measurement was done with ollama offline (docker daemon down). A follow-up run with qwen3.5:4b actually resident would replace the `~3 GB` estimate with a measured figure, tightening the decision.
- **REBEL val/test sample size.** val 1,006 and test 1,007 produce wider CIs than a 1,800-row split would. If REBEL metrics become decision-critical, run a second REBEL test pass once Phase 1.1 has expanded the rel pool.
