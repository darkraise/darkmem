# Plan v2 — relation-corpus augmentation and pair-wise relation-classifier sweep

Last updated: 2026-04-18 (v2, self-review fixes applied)
Scope: augment the 10-type relation corpus to at least 1,000 positive examples per class, reuse the generated rows to retrain `darkmem-span-v1` and `darkmem-typer-v1`, then train five small backbones (all well under 1 GB VRAM) as pair-wise relation classifiers and pick a winner to replace `darkmem-relation-v1`.

Out of scope: `darkmem-classifier-v1` retrain (current 0.975 accuracy leaves marginal headroom), `darkmem-retriever-v1` expansion (MRR@10 0.884 is near the bge-base ceiling without hard-negative mining).

## Changes vs v1 (self-review fixes)

- **Held-out test and val are frozen.** Synth rows merge into `coding10clean_train_canon.jsonl` only; the pre-aug `coding10clean_val_canon.jsonl` and `coding10clean_test_canon.jsonl` are preserved as `*.pre-relaug.jsonl` and continue to serve as the eval set. Every F1 in phases 4 and 5 is reported on clean real data.
- **NONE cap applies only to train.** Validator and benchmark splits enumerate every directional pair so metrics reflect realistic inference.
- **Gold test-set recasting is explicit.** `_build_relclass_splits.py` accepts an arbitrary canonical JSONL path, so we can build the pair-wise eval table from `rebel_coding10_test_gold.jsonl` or any frozen gold file.
- **Learning rate is 3e-5 uniformly** across the five-backbone sweep (matches typer-v1 recipe). LR sweep is a follow-up, not part of the initial run.
- **Class-balancing method is specified**: `CrossEntropyLoss(weight=inverse_class_freq)` computed on train only. No downsampling, no weighted sampler.
- **Phase 5 promotion rule is explicit**: auto-promote only if the candidate dominates the incumbent on both axes. Trade-offs escalate to the user with a full per-class F1 table.
- **Phase 6 covers all promoted heads**, not just the relation classifier. If span-v2 or typer-v2 promote, the integration plan and `MLModels.load_all()` update alongside the relation swap, including pair-wise batching in the relation inference path.
- **Validator uniqueness rule is `(normalized_name, start_offset)`** rather than bare name, so the same entity can legitimately appear at different offsets.
- **Phase 0 includes an audit** of `fine-tuning/data/v2/noisy/noisy_batch_01-10.jsonl` to confirm whether those 487 rows are already in `coding10clean_*_canon.jsonl`.

## Current state snapshot

Positive-pair counts after REL_MAP 30→10 on `coding10clean_*_canon.jsonl`:

| class | count | deficit vs 1,000 | raw-row target (70% survival) |
|---|---:|---:|---:|
| USES | 2,971 | — | — |
| REPLACES | 2,281 | — | — |
| RELATED_TO | 802 | 198 | 280 |
| DEPLOYED_ON | 271 | 729 | 1,040 |
| CAUSES | 225 | 775 | 1,100 |
| HAS_PART | 170 | 830 | 1,180 |
| DEPENDS_ON | 145 | 855 | 1,220 |
| AUTHORED_BY | 86 | 914 | 1,300 |
| IS_A | 31 | 969 | 1,380 |
| HAPPENED_ON | 16 | 984 | 1,400 |
| **total** | — | **6,254** | **~8,900 raw rows** |

Shipping head today: `darkmem-relation-v1` (rebel-large + post-hoc REL_MAP), F1 0.638 on `rebel_coding10_test_gold.jsonl`, 1,625 MB VRAM. Target: sub-1 GB head with F1 ≥ 0.638 and lower VRAM (hard auto-promote); any Pareto trade-off is a user-decision.

## Phase 0 — tooling, briefs, and audits

Deliverables before any generation runs.

1. **Audit existing synth assets.** Confirm whether `fine-tuning/data/v2/noisy/noisy_batch_01-10.jsonl` (487 rows from prior augmentation) is already merged into `coding10clean_*_canon.jsonl`. One-liner: `python -c "import json; s={json.loads(l)['id'] for l in open('fine-tuning/data/splits/coding10clean_train_canon.jsonl')}; print(sum(1 for l in open('fine-tuning/data/v2/noisy/noisy_batch_01.jsonl') if json.loads(l)['id'] in s))"`. If merged, skip. If not, decide in this phase whether to include it now or keep scope narrow to relation-targeted synth.

2. **Per-class generation briefs.** One per deficient class at `fine-tuning/data/v2/relaug/brief_{relation}.md` (eight files). Each brief specifies:
   - Relation semantics in one sentence plus directionality rule (`source → target`).
   - Allowed subject entity types and object entity types from the 10-type taxonomy.
   - Five authentic exemplars pulled from existing `coding10clean_*_canon.jsonl` rows that already carry this relation. Agents anchor voice on these.
   - Generation rules: one target relation per row is enough; prioritise developer-note voice over relation density; entity types must be drawn from the 10-type set; char offsets must be exact; include a `memory_type` field from the seven-class set for schema parity even though the classifier will not be retrained.
   - Required output schema matching `coding10clean` exactly, plus `source: "synth-relaug"` and `id: "synth-relaug-{class}-{uuid}"`.

3. **`scripts/_validate_relaug.py`** — row validator. Checks:
   - JSONL schema conformance.
   - Char-offset correctness against `text`.
   - Entity types all in the 10-type set.
   - At least one relation of the target class.
   - Entity `(normalized_name, start_offset)` uniqueness inside a row (same name at different offsets is allowed).
   - Text length 40 to 400 characters.

   Emits `data/v2/relaug/survivors/{class}.jsonl` and `data/v2/relaug/rejected/{class}.jsonl` with rejection reasons.

4. **`scripts/_merge_relaug.py`** — train-only merge. Copies the pre-aug `coding10clean_val_canon.jsonl` and `coding10clean_test_canon.jsonl` to `*.pre-relaug.jsonl` (first run only; idempotent). Appends survivors into `coding10clean_train_canon.jsonl` with `source: "synth-relaug"`. Val and test are never touched.

5. **`scripts/_build_relclass_splits.py`** — pair-wise builder. Reads any canonical JSONL path supplied via CLI (default: all three coding10clean splits). For each row, enumerates directional entity pairs and emits `{text, e1_name, e1_type, e1_start, e1_end, e2_name, e2_type, e2_start, e2_end, label}`. Label is the REL_MAP 10-type if the pair appears in `relationships`, otherwise `NONE`. NONE cap at 3× the most common positive class **applies to train only**; val, test, and any recast gold file enumerate all pairs.

Acceptance: all four scripts run clean on the pre-aug corpus with expected counts. Pre-aug relclass counts should be approximately: train 18,800 pairs (capped), val 6,300 pairs (uncapped), test 6,300 pairs (uncapped); record actual numbers in the progress log and lock them as the pre-aug baseline.

## Phase 1 — pilot generation (400 rows)

Spawn eight parallel subagents in a single message, one per deficient class, each producing 50 JSONL rows that conform to its brief. Output path per agent: `data/v2/relaug/raw/pilot_{class}.jsonl`.

After the round:

1. Run `_validate_relaug.py` on all eight files; record survival rate per class.
2. Hand-audit a 40-row stratified sample (5 per class) for authenticity, directionality, and entity-type coherence.
3. Decision gate: if survival is ≥ 0.65 and audit flags < 5 of 40 rows, proceed to Phase 2. Otherwise revise the briefs (wrong directionality, unrealistic voice, overly templated phrasing are the common failure modes) and repeat the pilot.

Acceptance: pilot rows committed to `survivors/pilot_{class}.jsonl`; survival-rate table appended to `fine-tuning/runs/2026-04-18-relaug/progress.md`.

## Phase 2 — scale generation

Per-class raw-row target from the deficit table above, plus a 15 percent overshoot for validator losses.

- Each subagent run produces 150 rows.
- Up to 10 parallel agents per round, distributing across classes proportional to remaining deficit.
- Phase 1 survival rate sets the stopping rule per class.
- Between rounds, run `_validate_relaug.py` and append survivors to `data/v2/relaug/survivors/{class}.jsonl`.

Estimate: roughly 60 agent invocations, six rounds of 10. Expected wall-clock is two to three hours.

Acceptance: each of the eight deficient classes has at least 1,000 survivors.

## Phase 3 — merge into train, rebuild derived splits

Steps, in order:

1. Back up val and test once: `cp coding10clean_val_canon.jsonl coding10clean_val_canon.pre-relaug.jsonl` (same for test). These are the frozen gold for every benchmark downstream.
2. `python -m fine-tuning.scripts._merge_relaug --survivors fine-tuning/data/v2/relaug/survivors --train fine-tuning/data/splits/coding10clean_train_canon.jsonl`. Appends to train only; val and test are untouched.
3. `python -m fine-tuning.scripts._build_coding10_splits` → rebuilds `span_{train,val,test}.jsonl` and `typer_{train,val,test}.jsonl`. Train gains the synth rows; val and test do not.
4. `python -m fine-tuning.scripts._build_rebel_coding10_splits` → rebuilds the seq2seq relation tables for the rebel-large-coding10 comparison run.
5. `python -m fine-tuning.scripts._build_relclass_splits` → writes `relclass_{train,val,test}.jsonl` for the pair-wise sweep. Train NONE-capped, val and test uncapped.
6. `python -m fine-tuning.scripts._build_relclass_splits --input fine-tuning/data/splits/rebel_coding10_test_gold.jsonl --output fine-tuning/data/splits/relclass_rebelgold_test.jsonl` → produces the recast pair-wise eval table used for direct comparison against rebel-large-v1's 0.638 baseline.

Sanity-check counts in `progress.md`: expected span train +~8,900 rows, typer train +~31,000 rows, relclass positive pairs in train +~6,254. Val and test counts unchanged vs the pre-aug baseline.

Acceptance: all rebuilt splits pass `validate_data.py --strict`; pre-aug val and test counts match the Phase 0 baseline exactly.

## Phase 4 — retrain span and typer on the enriched corpus

Two training runs on the LXC (RTX 2060 12 GB, fp16).

1. **`darkmem-span-v2`** — gliner_small-v2.1 base, same recipe as span-v1 (5 epochs, batch 16, lr 1e-5, max_length 256, single "entity" label). Output `fine-tuning/models/darkmem-span-v2/`.
2. **`darkmem-typer-v2`** — ModernBERT-base, same recipe as typer-v1 (5 epochs, batch 16, lr 3e-5, max_length 256, fp16, `[ENT]` / `[/ENT]` special tokens). Output `fine-tuning/models/darkmem-typer-v2/`.

Benchmark both on the two frozen eval sets:

- `docs/e2e/scripts/extraction_eval/corpus/gold.jsonl` (90-example hand-labeled gold; never changes).
- `coding10clean_test_canon.pre-relaug.jsonl` (the 791-row in-domain held-out slice).

Promotion rule for v2 heads:
- No regression greater than 2 F1 points on the 90-gold, AND
- At least +3 F1 points on the pre-relaug 2k-ish split.

If either gate fails, keep the v1 head and proceed with the v1 artifact in downstream phases.

## Phase 5 — pair-wise relation classifier sweep

Train five backbones on `relclass_train.jsonl` with a single shared recipe: 5 epochs, batch 16, lr 3e-5, max_length 256, AdamW + cosine LR, `CrossEntropyLoss(weight=inverse_class_freq)` where the weight vector is computed on the final train split, fp16 on LXC or bf16 on the RTX 5060.

| run | backbone | params | expected VRAM |
|---|---|---:|---:|
| relclass-modernbert-base | `answerdotai/ModernBERT-base` | 150M | ~620 MB |
| relclass-deberta-v3-base | `microsoft/deberta-v3-base` | 86M | ~400 MB |
| relclass-deberta-v3-small | `microsoft/deberta-v3-small` | 44M | ~200 MB |
| relclass-distilbert-base | `distilbert/distilbert-base-uncased` | 66M | ~250 MB |
| relclass-minilm-l12 | `microsoft/MiniLM-L12-H384-uncased` | 33M | ~130 MB |

Dependency pre-flight: `_train_relclass.py` must assert `sentencepiece` importable before the first DeBERTa run and fail fast if not (DeBERTa-v3 tokenizer hard-requires it).

Evaluation, three slices per model:

1. **Gold-entity upper bound** — pair rows from `relclass_test.jsonl` (pre-aug coding10 gold entities). Isolates relation F1 from any extraction error.
2. **Rebel-gold recast** — pair rows from `relclass_rebelgold_test.jsonl` (recast from `rebel_coding10_test_gold.jsonl`, 567 rows). Direct apples-to-apples comparison against rebel-large-v1's 0.638.
3. **End-to-end** — span + typer extract entities on the 791-row pre-relaug test text, then the classifier runs over all predicted pairs. Uses `darkmem-span-v2` + `darkmem-typer-v2` if both promoted in Phase 4, otherwise falls back to v1. Clearly label which span/typer pair was used.

Report per model: micro F1, macro F1, per-class F1, NONE precision, direction accuracy, VRAM peak, mean latency per pair. Write all numbers to `fine-tuning/runs/2026-04-18-relaug/relclass_summary.md`.

Phase 5 acceptance / promotion rule:
- **Auto-promote** if the candidate dominates rebel-large-v1 on both axes — F1 ≥ 0.638 on slice 2 AND peak VRAM < 1,625 MB.
- **User-decision** if the candidate wins one axis and loses the other. Present the full per-class F1 table plus VRAM and latency, then wait for the call.
- **Reject** if no candidate beats either axis.

## Phase 6 — ship

Steps:

1. Rename the chosen checkpoint to `fine-tuning/models/darkmem-relation-v2/best`.
2. If Phase 4 promoted them, rename span / typer outputs to `darkmem-span-v2/best` and `darkmem-typer-v2/best`. Otherwise keep v1 artifacts in place.
3. Update `fine-tuning/models/PRODUCTION.md`: swap the relation row, update the co-load budget (relation line goes from 1,625 MB to the new number), update the final pipeline-metrics table. If span or typer promoted, update their rows too.
4. Amend `fine-tuning/INTEGRATION_PLAN_v3.md`:
   - `ExtractionMLService.relation_head` switches from seq2seq decode to pair-wise classifier loop. Add a note that inference batches up to 64 pairs per forward pass to amortise tokenizer cost.
   - Remove any REL_MAP post-hoc step in the relation path — the classifier is native 10-type.
   - If span or typer promoted, bump their version strings in `MLModels.load_all()` and the `/api/health/ml_models` response. If they did not promote, leave those paths untouched.
5. Commit on `feat/architecture-overhaul` with a clear message listing every head whose version changed; do not merge. The downstream integration plan owns that merge.

## Progress log

Every phase appends a timestamped row to `fine-tuning/runs/2026-04-18-relaug/progress.md` with: what was done, counts delta, eval metrics delta, decision taken. Single source of truth.

## Risks and guard-rails

- Templated phrasing from generators helps relation F1 but hurts span and typer realism. Phase 1 audit is the checkpoint; if we see it, revise the briefs to demand voice variation before Phase 2 scale.
- The held-out val and test are the pre-aug files. Any code path that rebuilds them automatically during Phase 3 is a bug — `_merge_relaug.py` must log every file it writes and never touch val/test.
- Pair-wise inference at runtime enumerates up to 10×9 = 90 pairs per memory. The Phase 6 integration update must batch these forward passes (≤64 per batch is a reasonable default) or tail latency suffers.
- VRAM co-load ceiling leaves ~640 MB headroom today. The new relation head must land at or below that when loaded alongside classifier + retriever + span + typer.
- HAPPENED_ON (16) and IS_A (31) may remain weak even after augmentation because synth will be the majority of their training data. Report per-class F1 honestly; if either lands below 0.40, label it a known weakness in `PRODUCTION.md`.
