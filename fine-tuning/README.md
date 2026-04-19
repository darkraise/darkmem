# darkmem fine-tuning guide

Single source of truth for the ML pipeline that powers darkmem extraction, classification, retrieval, relation extraction, and their end-to-end benchmarks. Start here when beginning a fresh session.

## 1. The five production heads

All shipping weights are documented in `fine-tuning/models/PRODUCTION.md`. A quick map:

| head | role | base | params | VRAM idle | shipping F1 / metric |
|---|---|---|---:|---:|---:|
| `darkmem-classifier-v1` | memory-type (7 classes) | answerdotai/ModernBERT-base | 150M | ~619 MB | 0.975 accuracy |
| `darkmem-retriever-v1` | dense embedder | BAAI/bge-base-en-v1.5 | 109M | ~439 MB | MRR@10 0.884 |
| `darkmem-span-v1` | entity span detector | urchade/gliner_small-v2.1 | ~50M | ~613 MB | name recall 0.972 (90-gold) |
| `darkmem-typer-v1` | entity 10-type classifier | answerdotai/ModernBERT-base | 150M | ~618 MB | 0.692 acc / 0.678 macro F1 |
| `darkmem-relation-v1` | relation seq2seq | Babelscape/rebel-large | 407M | ~1,625 MB | pair-wise F1 0.639 |

Entity extraction is two-stage: span detector finds candidate spans with the single label `entity`, then the typer assigns one of the 10 taxonomy types with `[ENT]...[/ENT]` markers. Relation extraction is seq2seq with the `<triplet> subject <subj> target <obj> type` format, 30-type native output collapsed to 10 via `REL_MAP` post-hoc.

## 2. The 10-type coding taxonomies

Defined in `fine-tuning/scripts/_build_coding10_splits.py` (entities) and `fine-tuning/scripts/_build_rebel_coding10_splits.py` (relations).

**Entity types (10):** `tool, service, database, language, protocol, project, algorithm, artifact, concept, entity`.

**Relation types (10):** `USES, DEPENDS_ON, REPLACES, IS_A, HAS_PART, DEPLOYED_ON, CAUSES, AUTHORED_BY, HAPPENED_ON, RELATED_TO`.

`REL_MAP` collapses the original 30-type space to 10 clusters (e.g. `CONFIGURES`, `APPLIES_TO`, `COMMUNICATES_WITH`, `IMPLEMENTS` all map to `USES`). Both the rebel-seq2seq output and the pair-wise classifier labels converge on the same 10-type set.

## 3. Where training runs

| environment | GPU | precision | use for |
|---|---|---|---|
| **Proxmox LXC `192.168.0.250`** (`/root/darkmem-ft/`, flat layout — no `fine-tuning/` prefix) | RTX 2060, 12 GB | fp16 | **Primary training host.** Every shipping head was trained here. SSH via `~/.ssh/finetune_lxc_key`. |
| **Local Windows RTX 5060**, 8.5 GB | Blackwell | bf16 | **Parallel-only exception.** Requires explicit user approval. Use for the second head when both LXC and local are needed simultaneously (e.g. span-v2 on LXC while typer-v2 runs locally). Drop `--fp16` flag; Blackwell picks bf16 automatically. |

Never default to local training. The LXC is the workstation-friendly option because the Windows GPU is the user's interactive machine.

### 3.1 SSH commands

```bash
# One-shot
ssh -i ~/.ssh/finetune_lxc_key root@192.168.0.250 "<command>"

# Interactive tmux
ssh -t -i ~/.ssh/finetune_lxc_key root@192.168.0.250 "tmux attach -t <session>"

# Background train in tmux
ssh -i ~/.ssh/finetune_lxc_key root@192.168.0.250 \
    "cd /root/darkmem-ft && tmux new-session -d -s <name> '<train cmd> 2>&1 | tee runs/<name>/train.log'"
```

### 3.2 Data sync — Windows to LXC

```bash
scp -i ~/.ssh/finetune_lxc_key <local_files> root@192.168.0.250:/root/darkmem-ft/data/splits/
```

Typical sync set: `coding10clean_{train,val,test}_canon.jsonl`, `span_*.jsonl`, `typer_*.jsonl`, `rebel_*.jsonl`, `rebel_coding10_*.jsonl`, `relclass_*.jsonl`, `relclass_rebelgold_test.jsonl`.

### 3.3 Pull-back when training finishes

```bash
mkdir -p fine-tuning/models/<name>/
scp -i ~/.ssh/finetune_lxc_key -r \
    root@192.168.0.250:/root/darkmem-ft/models/<name>/best \
    fine-tuning/models/<name>/
```

Only pull `best/` unless you specifically need intermediate checkpoints. Full checkpoint dirs are ~1-2 GB each and are disposable once the best is validated.

### 3.4 Disk-space gotcha

The LXC root FS is 99 GB. Old experiment checkpoints accumulate fast. Always check before training:

```bash
ssh -i ~/.ssh/finetune_lxc_key root@192.168.0.250 "df -h / && du -sh /root/darkmem-ft/models/* 2>&1 | sort -rh"
```

Archived experiments that also exist locally under `fine-tuning/models/_experiments/` are safe to delete on the LXC after explicit user confirmation.

## 4. Repository layout (cheat sheet)

```
fine-tuning/
├── README.md                       ← this file
├── PRODUCTION.md                   ← shipping manifest (under models/)
├── INTEGRATION_PLAN_v3.md          ← latest backend-wiring plan
├── RELATION_AUG_PLAN.md            ← v2, relation-corpus augmentation + classifier sweep
├── config/
│   ├── taxonomy_v2.yaml            ← 35 entity / 30 relation types (legacy source-of-truth)
│   └── training_v2.yaml            ← hyperparameters
├── data/
│   ├── splits/                     ← every canonical and derived training JSONL
│   │   ├── coding10clean_{train,val,test}_canon.jsonl   ← 10-type canonical corpus (primary source)
│   │   ├── coding10clean_{val,test}_canon.pre-relaug.jsonl  ← frozen pre-aug gold (never modified)
│   │   ├── span_{train,val,test}.jsonl                 ← for darkmem-span
│   │   ├── typer_{train,val,test}.jsonl                ← for darkmem-typer with [ENT] markers
│   │   ├── rebel_{train,val,test}.jsonl                ← 30-type seq2seq training (v2 corpus, 8,052 rows)
│   │   ├── rebel_coding10_{train,val,test}.jsonl       ← 10-type seq2seq training (post-aug, 11,243 rows)
│   │   ├── rebel_coding10_test_gold.jsonl              ← 567-row gold for relation eval
│   │   ├── relclass_{train,val,test}.jsonl             ← pair-wise classifier training (post-aug, 26,366 rows)
│   │   └── relclass_rebelgold_test.jsonl               ← 6,470 pairs recast from rebel_coding10_test_gold
│   └── v2/
│       ├── relaug/                 ← Phase 2 synth-relation augmentation briefs + survivors
│       └── noisy/                  ← pre-Phase-3 noisy-batch augmentation (not merged)
├── models/
│   ├── PRODUCTION.md
│   ├── darkmem-classifier-v1/      ← shipping
│   ├── darkmem-retriever-v1/       ← shipping
│   ├── darkmem-span-v1/            ← shipping
│   ├── darkmem-typer-v1/           ← shipping
│   ├── darkmem-relation-v1/        ← shipping
│   └── _experiments/               ← archived, not in production
├── runs/                           ← per-training logs + eval outputs
└── scripts/
    ├── train_*.py                  ← per-head trainers
    ├── _infer_*.py                 ← inference scripts
    ├── eval_*.py                   ← strict scorers
    ├── _build_*_splits.py          ← data-pipeline builders
    ├── _validate_relaug.py         ← Phase 0 schema validator
    ├── _merge_relaug.py            ← train-only merge (preserves frozen val/test)
    └── rebel_pair_rescore.py       ← score rebel seq2seq on pair-wise metric for apples-to-apples
```

## 5. Training recipes (canonical)

Every trainer now accepts `--train-path` and `--val-path` explicitly. Default commands point at the standard split filenames; pass overrides when training a new head on a different corpus.

### HuggingFace dataset mode (no local corpus)

Every trainer also accepts `--hf-train-repo` / `--hf-val-repo` (plus `--hf-*-file` for the filename, default `train.jsonl` / `val.jsonl` / `test.jsonl`). When set, the file is pulled via `hf_hub_download` into the HF cache and the cached path is fed to the trainer — no code change inside the read loop. Requires `HF_TOKEN` (env or `--hf-token`) for private dataset repos.

Example: reproduce the shipping classifier pulling straight from the Hub:

```bash
HF_TOKEN=hf_... python3 -m scripts.train_classifier \
    --base answerdotai/ModernBERT-base \
    --epochs 10 --batch-size 16 --lr 3e-5 --max-length 256 --bf16 \
    --lr-scheduler-type cosine --label-smoothing 0.05 --trust-remote-code \
    --hf-train-repo darkraise/darkmem-classifier-dataset \
    --output-dir models/darkmem-classifier-v1
```

The data-build pipeline (`_build_*_splits.py`) pulls its canonical inputs from `darkraise/darkmem-corpus` on the Hub using the same `_hf_dataset_loader` helper. `shared/shared_coding10_clean.jsonl`, `coding10clean/`, `coding5clean/`, `relaug_survivors/`, and `noisy/` all live in that single dataset repo. Mount the corpus via `huggingface_hub.snapshot_download(repo_id="darkraise/darkmem-corpus", repo_type="dataset", token=...)` and feed the returned path as your local `data/` root.

### 5.1 darkmem-classifier (memory type, 7 classes)

Not expected to re-train often. Shipping weights at 0.975 accuracy.

```bash
cd /root/darkmem-ft
python3 -m scripts.train_classifier \
    --base answerdotai/ModernBERT-base \
    --epochs 10 --batch-size 16 --lr 3e-5 \
    --max-length 256 --bf16 --lr-scheduler-type cosine \
    --label-smoothing 0.05 --trust-remote-code \
    --data data/classification/train_v2_aug2.jsonl \
    --output-dir models/darkmem-classifier-v1
```

### 5.2 darkmem-retriever (bge-base contrastive)

```bash
cd /root/darkmem-ft
python3 -m scripts.contrastive_finetune \
    --base BAAI/bge-base-en-v1.5 \
    --train runs/retrieval-contrastive/train_pairs_7k_clean.jsonl \
    --triplets runs/retrieval-contrastive/train_triplets.jsonl \
    --out models/darkmem-retriever-v1 \
    --epochs 5 --batch-size 64 --lr 2e-5 --max-length 256
```

### 5.3 darkmem-span (gliner_small, single "entity" label)

```bash
cd /root/darkmem-ft
python3 -m scripts.train_gliner \
    --base-model urchade/gliner_small-v2.1 \
    --output-dir models/darkmem-span-v1 \
    --train-path data/splits/span_train.jsonl \
    --val-path data/splits/span_val.jsonl \
    --epochs 5 --batch-size 16 --lr 1e-5
```

Wall-clock ~14 min on LXC. The gliner Trainer does NOT evaluate per epoch; `best/` is the final epoch. Use post-hoc eval on the 90-gold and pre-relaug 2k test to promote.

### 5.4 darkmem-typer (ModernBERT-base, 10-type with [ENT] markers)

```bash
cd /root/darkmem-ft
python3 -m scripts.train_typer \
    --base answerdotai/ModernBERT-base \
    --output-dir models/darkmem-typer-v1 \
    --train-path data/splits/typer_train.jsonl \
    --val-path data/splits/typer_val.jsonl \
    --epochs 5 --batch-size 16 --lr 3e-5 \
    --max-length 256 --fp16          # drop --fp16 on Blackwell
```

Wall-clock ~16 min on LXC, 15 min on local RTX 5060 (bf16). Adds `[ENT]` / `[/ENT]` special tokens.

### 5.5 darkmem-relation (rebel-large seq2seq, 30-type + REL_MAP)

```bash
cd /root/darkmem-ft
python3 -m scripts.train_rebel \
    --base-model Babelscape/rebel-large \
    --output-dir models/darkmem-relation-v1 \
    --train-path data/splits/rebel_train.jsonl \
    --val-path data/splits/rebel_val.jsonl \
    --epochs 3 --batch-size 2 --lr 3e-5 \
    --max-source-length 256 --max-target-length 128
```

Wall-clock ~90 min on LXC. Decode with `num_beams=4, max_target=128`.

### 5.6 Pair-wise relation classifier (experimental, from Phase 5)

```bash
python3 -m scripts.train_relclass \
    --base <hf-id> \
    --output-dir models/relclass/<name> \
    --train-path data/splits/relclass_train.jsonl \
    --val-path data/splits/relclass_val.jsonl \
    --epochs 5 --batch-size 16 --lr 3e-5 \
    --max-length 256 \
    --class-weight-scheme sqrt \
    [--no-special-tokens]            # for DeBERTa SentencePiece models
```

Supports `inverse`, `sqrt`, `none` weight schemes. `inverse` over-predicts positives; `sqrt` is the usable default. DeBERTa-v3 (base and small) **collapse to always-NONE regardless of scheme** — drop from the sweep if attempting again.

## 6. Inference and evaluation

### 6.1 Entity extraction (span + typer, two-stage)

```bash
python3 -m scripts._infer_entity_twostage \
    --span-model models/darkmem-span-v1/best \
    --type-model models/darkmem-typer-v1/best \
    --gold <gold.jsonl> \
    --pred <pred.jsonl>

python3 -m scripts.eval_entity_pair \
    --gold <gold_in_10type_form.jsonl> \
    --pred <pred.jsonl> \
    --out <metrics.json>
```

`eval_entity_pair.py` reads the `entities` key, NOT `expected_entities`. The 90-gold at `docs/e2e/scripts/extraction_eval/corpus/gold.jsonl` was deleted during the 2026-04-19 cleanup and is not recoverable from git or HF. The metrics in `PRODUCTION.md` (name recall 0.972, type accuracy given name 0.83) are historical figures on that corpus; reproducing them now requires re-curating an entity-extraction gold. If you do, the format was `expected_entities` in the 35-type taxonomy; remap via `scripts._build_coding10_splits.TYPE_MAP` before scoring and drop `food`/`emotion`/`hobby`/`activity`/`goal` (map to `None`) and `standard`/`specification` (not in the 35-type map).

### 6.2 Relation extraction (rebel seq2seq)

```bash
python3 -m scripts._infer_relation \
    --model models/darkmem-relation-v1/best \
    --gold data/splits/rebel_coding10_test_gold.jsonl \
    --pred runs/<name>/pred.jsonl

python3 -m scripts.rebel_pair_rescore \
    --pred runs/<name>/pred.jsonl \
    --gold data/splits/rebel_coding10_test_gold.jsonl \
    --out runs/<name>/metrics_pairwise.json
```

`rebel_pair_rescore.py` applies REL_MAP 30→10 on both predictions and gold, enumerates every directional entity pair, and computes strict per-pair F1. This is the **apples-to-apples** metric across all relation heads (seq2seq or classifier).

### 6.3 Pair-wise relation classifier

```bash
python3 -m scripts.eval_relclass \
    --model models/relclass/<name>/best \
    --test data/splits/relclass_rebelgold_test.jsonl \
    --out runs/relclass/<name>/rebelgold_metrics.json

python3 -m scripts.relclass_threshold_sweep \
    --model models/relclass/<name>/best \
    --val data/splits/relclass_val.jsonl \
    --test data/splits/relclass_test.jsonl \
    --out runs/relclass/<name>/sweep.json
```

Threshold sweep predicts positive only when `max_pos_prob > threshold * none_prob`. Pick the val-best threshold and apply to test for fair comparison.

### 6.4 LLM relation extraction (qwen3.5:4b via Ollama)

```bash
python3 -m scripts.infer_relation_llm \
    --model qwen3.5:4b \
    --gold data/splits/rebel_coding10_test_gold.jsonl \
    --pred runs/<name>/pred.jsonl \
    --prompt-variant optimized     # or "default"
```

Uses Ollama at `http://localhost:11434`. **Important:** Qwen3 family ships with "thinking mode" enabled by default — the script passes `think: false` automatically. Without that, each row takes 5+ minutes and hits `done_reason: length`. The `--prompt-variant optimized` flag uses the stricter prompt with disambiguation rules.

Score with `rebel_pair_rescore.py` the same way as a seq2seq head.

## 7. Data pipeline — how the splits are built

Start from canonical `coding10clean_*_canon.jsonl` rows. Each row:

```json
{
  "id": "...",
  "text": "...",
  "entities": [{"name": "...", "normalized_name": "...", "type": "<10-type>", "start": <int>, "end": <int>}],
  "relationships": [{"source": "<name>", "target": "<name>", "type": "<30-type or 10-type>"}],
  "memory_type": "<one of 7>",
  "domain": "coding",
  "source": "<synth-relaug|noisy|null>"
}
```

`end` is Python-exclusive (`text[start:end] == name`). GLiNER internally uses inclusive end — the data builder handles the conversion, never pass raw inclusive-end data through GLiNER trainers.

Rebuilders:

| script | reads | writes |
|---|---|---|
| `_build_twostage_splits.py` | `coding10clean_*_canon.jsonl` | `span_*.jsonl`, `typer_*.jsonl` |
| `_build_rebel_coding10_splits.py` | `coding10clean_*_canon.jsonl` | `rebel_coding10_*.jsonl` (10-type native via REL_MAP at build time) |
| `_build_relclass_splits.py` | any canonical JSONL (CLI arg) | `relclass_*.jsonl` (pair-wise, NONE-cap on train only) |
| `_merge_relaug.py` | `survivors/*.jsonl` + `coding10clean_train_canon.jsonl` | appends to train only; val and test copied to `*.pre-relaug.jsonl` on first run and never touched again |

Every split rebuild is deterministic given the same canonical. Val and test are frozen at the pre-relaug state so all benchmarks run on clean real data.

## 8. Augmentation (Phase 2 workflow)

See `RELATION_AUG_PLAN.md` v2 for the full plan. Summary of what works:

1. Write per-class briefs at `data/v2/relaug/brief_{class}.md` with 5 authentic exemplars pulled from existing canonical rows.
2. Spawn 10 parallel subagents in a **single** assistant message (separate messages serialise). Each agent generates 150 JSONL rows.
3. Run `_validate_relaug.py` on each file. Typical survival rate ~95 percent with minor offset drift.
4. Append survivors via `_merge_relaug.py`. Val and test stay frozen.
5. Rebuild derived splits with the three builders above.

The Phase 2 run produced 6,825 surviving synth rows across eight deficient classes, lifting every minority relation class to ≥1,000 positive pairs.

## 9. Full Phase 5 leaderboard (2026-04-18)

Pair-wise F1 on `rebel_coding10_test_gold.jsonl` (567 rows, 711 positive pairs):

| head | params | F1 | precision | recall | VRAM | latency ms/row |
|---|---:|---:|---:|---:|---:|---:|
| rebel-large-v1 (shipping) | 407M | 0.639 | 0.665 | 0.616 | 1,625 MB | 493 |
| rebel-base-6-epoch (30-type + REL_MAP) | 139M | 0.602 | 0.681 | 0.540 | 606 MB | 426 |
| rebel-base-3-epoch (30-type + REL_MAP) | 139M | 0.496 | 0.560 | 0.444 | 606 MB | 341 |
| ModernBERT-base-sqrt (pair-wise, t=10) | 150M | 0.400 | 0.459 | 0.354 | 620 MB | 20 |
| rebel-base-10type (native) | 139M | 0.396 | 0.449 | 0.354 | 606 MB | 173 |
| DistilBERT-base-sqrt (pair-wise, t=30) | 66M | 0.369 | 0.400 | 0.343 | 250 MB | 10 |
| MiniLM-L12-sqrt (pair-wise, t=20) | 33M | 0.331 | 0.414 | 0.276 | 130 MB | 5 |
| qwen-claude + optimized prompt (LLM) | 4.7B | 0.315 | 0.255 | 0.414 | 6,900 MB | 1,946 |
| qwen3.5:4b zero-shot (LLM) | 4.7B | 0.291 | 0.229 | 0.399 | 6,900 MB | 1,435 |
| DeBERTa-v3 base/small | 86/44M | collapsed | — | — | — | — |

Promotion gate per `RELATION_AUG_PLAN.md`: auto-promote if candidate dominates on both axes (F1 ≥ 0.639 AND VRAM < 1,625 MB). Current best sub-1 GB candidate is rebel-base-6-epoch at −0.037 F1 vs shipping (Pareto trade-off, user decision).

Identified levers to close the last F1 gap:
- Extend rebel-base to 9 epochs (+0.02–0.04 expected).
- Rebel-large teacher distillation on rebel-base (+0.03–0.05 expected).
- 30-type corpus augmentation (+0.03–0.08 expected).

## 10. Known gotchas (save future sessions from re-learning)

- **Always train on LXC by default.** Local Windows RTX 5060 only when the user explicitly approves parallel execution for a specific session.
- **Agent parallelism requires a single assistant message.** Multiple Agent tool calls in one response run concurrently; separate responses serialise.
- **GLiNER inclusive end.** `scripts/_char_spans_to_token_spans` emits inclusive end indices to match GLiNER. Any builder that outputs exclusive-end to a GLiNER trainer silently collapses F1 to ~0.01.
- **DeBERTa-v3 collapses on this relclass task** (both with and without special-token addition), on both fp16 and bf16. Drop from any sweep; the failure is structural, not a hyperparameter issue.
- **Qwen3 thinking mode blows out inference.** Pass `think: false` to the Ollama API. Without it, each row takes 5 minutes and hits max-tokens.
- **Class-weighted relclass over-predicts.** `inverse` weighting pushes precision below 0.15 at plain argmax. Use `sqrt` or apply threshold sweep to pick the best operating point.
- **Val and test are frozen at pre-relaug.** `_merge_relaug.py` backs them up to `*.pre-relaug.jsonl` on first run and never touches them again. Every benchmark must read the pre-relaug versions (or their copies in `coding10clean_*_canon.jsonl` post-Phase-3; val/test in that file are byte-identical to the backups).
- **LXC disk fills fast.** Always check `df -h` before training; delete archived experiments after explicit confirmation.
- **Transformers 5.1 API.** `tokenizer=` keyword is removed from `Trainer.__init__`; use `processing_class=` instead (the trainers fall back automatically with try/except).
- **Ollama is local**, not on the LXC. `http://localhost:11434` on the Windows workstation.
- **The backend integration plan is `INTEGRATION_PLAN_v3.md`.** It names real call sites in `backend/app/services/pipeline.py` and uses the `entities` table with `entity_type` column. v1 and v2 are superseded.

## 11. End-to-end workflow (train a new head from scratch)

1. Confirm the canonical corpus is current (`coding10clean_*_canon.jsonl`).
2. Rebuild the head-specific split table with the appropriate `_build_*_splits.py`.
3. Sync scripts and data to the LXC (`scp -i ~/.ssh/finetune_lxc_key scripts/*.py root@192.168.0.250:/root/darkmem-ft/scripts/` and same for `data/splits/`).
4. Kick off training in a tmux session on the LXC. Use `tee runs/<name>/train.log` for the log.
5. Monitor via `ssh "tail /root/darkmem-ft/runs/<name>/train.log"`.
6. Pull `best/` back to the Windows workstation via `scp -r`.
7. Run the appropriate inference + eval pair locally or on the LXC.
8. If the new head dominates the promotion gate, update `PRODUCTION.md` and move on to backend integration via `INTEGRATION_PLAN_v3.md`. Otherwise keep the old shipping head and archive the experiment to `_experiments/`.

## 12. Contact points for the LXC

The LXC is a Proxmox VM dedicated to darkmem training. Hostname `fine-tune`, IP `192.168.0.250`, SSH key `~/.ssh/finetune_lxc_key`. Python 3.11.2, `gliner`, `transformers 5.1.0`, `torch` with CUDA for the RTX 2060. Repo lives at `/root/darkmem-ft/` (flat layout — no `fine-tuning/` wrapping directory). Do not `git clone` into the LXC; sync individual files with scp.
