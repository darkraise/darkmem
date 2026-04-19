# Plan v2 — 5-type relation schema + memory metadata upgrade

Last updated: 2026-04-19 (v2, self-review fixes applied)
Scope: replace the current 10-type relation schema with a 5-type coding-native set, retrain rebel-large on the new schema, add five metadata fields to the memory table, wire them into retrieval, and backfill historical rows so the graph stays consistent.

Success criteria: rebel-large-v2 pair-wise F1 beats rebel-large-v1-rescored-on-5-type by ≥ 0.05 F1 with a floor of 0.70 AND the retrieval pipeline returns status-filtered, project-scoped, tech-tagged memories end-to-end.

Out of scope: rebel-base distillation, flan-t5-large teacher, pair-wise classifier sweep. Those become easier targets after the schema migration and are deferred.

## Changes vs v1 (self-review fixes)

- REL_MAP_5 is explicit about both the 30-type historical source and the 10-type synth-row source so the merged canonical builds cleanly.
- Phase 4 migration spells out `CREATE TYPE`, the CHECK constraint SQL, and the downgrade path for the Postgres enum.
- Rank fusion math switched from additive (wrong units) to multiplicative normalised-confidence weighting.
- REPLACES supersession detector is gated on `technologies` containment, same-project, a 90-day staleness window, and an extraction-confidence threshold.
- Historical relationships are backfilled via a dedicated Phase 6.5 so old 10-type edges get mapped into the new 5-type space or deleted.
- Row-count projections in Phase 1 are grounded in the actual 10-type distribution rather than guessed.
- Promotion gate in Phase 3 is relative-plus-floor, not an absolute 0.75 target.
- Confidence rules are flagged as a v1 placeholder with an explicit path to an ML classifier follow-up.
- API versioning section removed; replaced with single-point documentation.
- `rebel_pair_rescore.py` gets a `--schema` flag to pick REL_MAP vs REL_MAP_5.

## The new schemas

### Relation types (5)

| type | semantics | collapses from |
|---|---|---|
| `USES` | source invokes, calls, imports, or contains target | 30-type: USES, CONFIGURES, APPLIES_TO, COMMUNICATES_WITH, IMPLEMENTS, DEPENDS_ON, HAS_PART, EXTENDS. 10-type: USES, DEPENDS_ON, HAS_PART |
| `REPLACES` | source is the successor; target is being phased out | 30-type: REPLACES, IMPROVES_ON, BUILDS_ON. 10-type: REPLACES |
| `IS_A` | source is a kind/implementation of target (taxonomy) | 30-type: IS_A. 10-type: IS_A |
| `DEPLOYED_ON` | source runs on target (host, cluster, IP, device) | 30-type: DEPLOYED_ON, LOCATED_IN. 10-type: DEPLOYED_ON |
| `CAUSES` | source triggers, produces, or fixes target | 30-type: CAUSES, PRODUCES, FIXES. 10-type: CAUSES |

**Dropped entirely.** Rows whose ONLY relation collapses to a dropped class become empty-relation rows (entities are kept). Dropped sources: 30-type `RELATED_TO, KNOWS, SUPPORTS, CONTRADICTS, PREFERS, FEELS_ABOUT, PLANS_TO, VISITED, LIVES_IN, HAPPENED_ON, AUTHORED_BY, PUBLISHED_IN, WORKS_AT`; 10-type `RELATED_TO, HAPPENED_ON, AUTHORED_BY`.

### REL_MAP_5 implementation

```python
REL_MAP_5 = {
    # USES cluster — 30-type
    "USES": "USES", "CONFIGURES": "USES", "APPLIES_TO": "USES",
    "COMMUNICATES_WITH": "USES", "IMPLEMENTS": "USES",
    "DEPENDS_ON": "USES", "HAS_PART": "USES", "EXTENDS": "USES",
    # REPLACES cluster — 30-type
    "REPLACES": "REPLACES", "IMPROVES_ON": "REPLACES", "BUILDS_ON": "REPLACES",
    # IS_A
    "IS_A": "IS_A",
    # DEPLOYED_ON cluster — 30-type
    "DEPLOYED_ON": "DEPLOYED_ON", "LOCATED_IN": "DEPLOYED_ON",
    # CAUSES cluster — 30-type
    "CAUSES": "CAUSES", "PRODUCES": "CAUSES", "FIXES": "CAUSES",
    # dropped 30-type — explicit None (anything not in this dict also maps to None)
    "RELATED_TO": None, "KNOWS": None, "SUPPORTS": None,
    "CONTRADICTS": None, "PREFERS": None, "FEELS_ABOUT": None,
    "PLANS_TO": None, "VISITED": None, "LIVES_IN": None,
    "HAPPENED_ON": None, "AUTHORED_BY": None,
    "PUBLISHED_IN": None, "WORKS_AT": None,
}
# Note: 10-type identity entries are already covered by the same keys above,
# since USES/DEPENDS_ON/HAS_PART/REPLACES/IS_A/DEPLOYED_ON/CAUSES all appear
# as keys with correct 5-type targets. 10-type RELATED_TO/HAPPENED_ON/
# AUTHORED_BY also resolve to None via the same dict.
```

The single dict handles both historical 30-type relationships and Phase-2 synth 10-type relationships because the shared key names collapse correctly in both cases.

### Memory metadata columns (5)

| column | type | nullable | default | source | used by |
|---|---|---|---|---|---|
| `project` | `text` | no | `'default'` | caller/session | retrieval filter |
| `status` | postgres enum `memory_status` (`active`, `deprecated`, `superseded`) | no | `'active'` | rule-based + REPLACES detector | retrieval filter |
| `superseded_by` | `uuid` | yes | NULL | REPLACES relation detector | supersession chains |
| `technologies` | `text[]` | no | `{}` | entities of type tool/service/database/language/protocol | retrieval filter |
| `confidence` | `real` | no | `0.75` | phrasing rules + memory_type prior (v1 placeholder) | rank fusion weight |

`importance` deferred to a follow-up iteration after measuring retrieval lift.

## Phase 0 — tooling (half day)

Deliverables:

1. `fine-tuning/scripts/_build_coding5_splits.py` — same shape as the coding10 builder. Emits `coding5clean_{train,val,test}_canon.jsonl`. Entity taxonomy unchanged (same 10-type entities). Only relations are remapped. Drops rows where **all** relations collapse to None.
2. `fine-tuning/scripts/_build_rebel_coding5_splits.py` — REL_MAP_5 applied at build time. Output: `rebel_coding5_{train,val,test}.jsonl` (seq2seq) + `_gold.jsonl` (pair-wise eval source).
3. `fine-tuning/scripts/_build_relclass5_splits.py` — pair-wise builder for future classifier work; produces `relclass5_{train,val,test}.jsonl`.
4. `fine-tuning/scripts/_validate_schema5.py` — schema validator with the 5-type relation set.
5. Add `--schema {10type|5type}` flag to `rebel_pair_rescore.py`; default stays 10type for backward compatibility.

Acceptance: all four builders run on the current canonical and emit counts consistent with the Phase 1 projections below.

## Phase 1 — remap the gold and rebuild data tables (half day)

### Projected counts (from the actual post-Phase-3 10-type distribution)

Seq2seq training (`rebel_coding5_train.jsonl`), relation-row counts:

| class | projected count |
|---|---:|
| USES | ~7,800 (3,772 + 1,268 + 2,758) |
| REPLACES | ~2,655 |
| CAUSES | ~1,460 |
| DEPLOYED_ON | ~1,312 |
| IS_A | ~1,191 |
| **kept total** | ~14,400 |
| dropped (RELATED_TO, HAPPENED_ON, AUTHORED_BY) | ~3,826 |

Rel-carrying row count (unique rows with ≥ 1 kept relation): ~9,500 (down from 11,243 in 10-type). Still above the 8,052-row 30-type corpus rebel-large-v1 trained on.

Pair-wise test (`rebel_coding5_test_gold.jsonl` after recast), positive pairs:

| class | projected count |
|---|---:|
| USES | ~339 (309 + 17 + 13) |
| REPLACES | ~214 |
| DEPLOYED_ON | ~32 |
| CAUSES | ~29 |
| IS_A | ~6 |
| **kept total** | ~620 |
| dropped | ~91 |

### Steps

1. Run `_build_coding5_splits.py` on `coding10clean_*_canon.jsonl` and the pre-relaug val/test copies.
2. Run `_build_rebel_coding5_splits.py` to produce the seq2seq and gold files.
3. Run `rebel_pair_rescore.py --schema 5type` against the existing rebel-large-v1 predictions on the new 5-type gold. This establishes the v1-on-5-type baseline. Hypothesis: rebel-large-v1 rescored on 5-type gold scores higher than its 10-type 0.639 because the class-merger removes annotator-disagreement noise; expected range 0.68–0.73, but do not tune plans on the hypothesis.

Acceptance: counts within ±5 percent of the projection; v1-on-5-type baseline number recorded in the progress log.

## Phase 2 — train rebel-large-v2 on 5-type (2 hours on LXC)

Recipe — same backbone and hyperparameters as rebel-large-v1 with the new corpus:

```bash
ssh -i ~/.ssh/finetune_lxc_key root@192.168.0.250 \
    "cd /root/darkmem-ft && tmux new-session -d -s rebel-v2 \
     'python3 -m scripts.train_rebel \
        --base-model Babelscape/rebel-large \
        --output-dir models/darkmem-relation-v2 \
        --train-path data/splits/rebel_coding5_train.jsonl \
        --val-path data/splits/rebel_coding5_val.jsonl \
        --epochs 5 --batch-size 2 --lr 3e-5 \
        --max-source-length 256 --max-target-length 128 \
        2>&1 | tee runs/darkmem-relation-v2/train.log'"
```

Notes:
- Five epochs instead of three; the 5-type task should tolerate more training before overfitting.
- If time permits, run a sub-experiment: train the same backbone on the 30-type `rebel_train.jsonl` and apply REL_MAP_5 post-hoc at inference. Compare against native-5-type training to see which wins.

Acceptance: training completes without OOM; checkpoint at `models/darkmem-relation-v2/best`; eval loss meaningfully lower than rebel-large-v1's ~0.165 (no hard threshold; compare vs the relative improvement expected from fewer classes).

## Phase 3 — evaluate and promote (1 hour)

```bash
python -m scripts._infer_relation \
    --model models/darkmem-relation-v2/best \
    --gold data/splits/rebel_coding5_test_gold.jsonl \
    --pred runs/darkmem-relation-v2/pred.jsonl

python -m scripts.rebel_pair_rescore --schema 5type \
    --pred runs/darkmem-relation-v2/pred.jsonl \
    --gold data/splits/rebel_coding5_test_gold.jsonl \
    --out runs/darkmem-relation-v2/metrics_pairwise.json
```

### Promotion gate (relative + absolute floor)

Promote rebel-large-v2 only when BOTH:

- **Relative**: v2 F1 ≥ v1-on-5-type F1 + 0.05.
- **Absolute floor**: v2 F1 ≥ 0.70.

Both checks protect against two failure modes: a tiny relative gain that does not justify the schema change, and a "trivially better than v1" outcome that still falls short of the 0.70 threshold needed for production retrieval quality.

If both gates pass:
1. Rename checkpoint to `models/darkmem-relation-v2/best`.
2. Update `fine-tuning/models/PRODUCTION.md` to swap the relation row. Note: 5-type native output, no post-hoc map required at inference time (REL_MAP_5 was applied at training).
3. Amend `fine-tuning/INTEGRATION_PLAN_v3.md` Section 3 (ExtractionMLService): switch relation head to v2, remove REL_MAP post-hoc step, update the 10-type → 5-type relation set documentation.

If either gate fails: investigate remap script for type-cluster bugs, audit 20 recast gold rows by hand, rerun. Do not ship until the relative gate at minimum passes.

## Phase 4 — backend schema migration (half day)

### Alembic migration (new file under `backend/migrations/versions/`)

```python
"""add memory metadata v2 (status, project, technologies, confidence, superseded_by)

Revision ID: <generated>
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg


def upgrade() -> None:
    # Create the enum type first (before column use).
    op.execute("CREATE TYPE memory_status AS ENUM ('active', 'deprecated', 'superseded')")

    op.add_column("memories", sa.Column(
        "project", sa.Text(), nullable=False, server_default="default"))
    op.add_column("memories", sa.Column(
        "status", pg.ENUM("active", "deprecated", "superseded",
                           name="memory_status", create_type=False),
        nullable=False, server_default="active"))
    op.add_column("memories", sa.Column(
        "superseded_by", pg.UUID(as_uuid=True), nullable=True))
    op.add_column("memories", sa.Column(
        "technologies", pg.ARRAY(sa.Text()), nullable=False, server_default="{}"))
    op.add_column("memories", sa.Column(
        "confidence", sa.REAL(), nullable=False, server_default="0.75"))

    op.create_foreign_key(
        "fk_memories_superseded_by", "memories", "memories",
        ["superseded_by"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_memories_project", "memories", ["project"])
    op.create_index("ix_memories_status", "memories", ["status"])
    op.create_index(
        "ix_memories_technologies", "memories", ["technologies"],
        postgresql_using="gin",
    )

    # Integrity: a superseded memory must point to its successor.
    op.execute(
        "ALTER TABLE memories ADD CONSTRAINT chk_superseded_has_pointer "
        "CHECK (status != 'superseded' OR superseded_by IS NOT NULL)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE memories DROP CONSTRAINT chk_superseded_has_pointer")
    op.drop_index("ix_memories_technologies", table_name="memories")
    op.drop_index("ix_memories_status", table_name="memories")
    op.drop_index("ix_memories_project", table_name="memories")
    op.drop_constraint("fk_memories_superseded_by", "memories", type_="foreignkey")
    op.drop_column("memories", "confidence")
    op.drop_column("memories", "technologies")
    op.drop_column("memories", "superseded_by")
    op.drop_column("memories", "status")
    op.drop_column("memories", "project")
    op.execute("DROP TYPE memory_status")
```

Acceptance: `alembic upgrade head` and `alembic downgrade -1` both succeed against a fresh test database; existing `pytest backend/tests/` stays green; CHECK constraint raises on an intentionally bad INSERT of status='superseded' with NULL superseded_by.

## Phase 5 — pipeline changes (2 days)

### 5.1 `project`

Requirement: caller must pass `project` at memory creation. If missing, derive from the active session/conversation context. Fall back to `"default"` so existing clients keep working.

### 5.2 `technologies`

In `backend/app/services/pipeline.py` after entity extraction, before commit:

```python
TECH_TYPES = {"tool", "service", "database", "language", "protocol"}
memory.technologies = sorted({
    e.normalized_name
    for e in entities
    if e.entity_type in TECH_TYPES and e.normalized_name
})
```

Denormalised so `WHERE 'pgvector' = ANY(technologies)` is a cheap GIN-indexed lookup without joining the entities table.

### 5.3 `status` and `superseded_by` — REPLACES supersession detector

After extraction commits, a post-processor runs per new memory:

```python
def detect_supersessions(new_memory: Memory, new_relations: list[Relation]) -> list[tuple[UUID, UUID]]:
    """
    Mark memories as superseded when the new memory carries a high-confidence
    REPLACES relation referencing a technology that appears in a recent,
    same-project, active memory.

    Returns a list of (old_memory_id, new_memory_id) pairs to apply.
    """
    supersessions = []
    for rel in new_relations:
        if rel.type != "REPLACES":
            continue
        if rel.confidence < REPLACES_CONFIDENCE_THRESHOLD:  # e.g. 0.7
            continue
        # rel.source = the new thing; rel.target = the deprecated thing.
        candidates = (
            Memory.query
            .filter(Memory.project == new_memory.project)
            .filter(Memory.status == "active")
            .filter(Memory.technologies.any(rel.target))
            .filter(Memory.created_at >= datetime.utcnow() - timedelta(days=90))
            .filter(Memory.id != new_memory.id)
            .order_by(Memory.created_at.desc())
            .all()
        )
        for old in candidates:
            supersessions.append((old.id, new_memory.id))
    return supersessions
```

Rules applied:
- **Same project only** — no cross-project supersession.
- **90-day staleness window** — memories older than that are left alone; schemas evolve, old context may still be valid.
- **Active-only targets** — already-superseded or deprecated memories are skipped.
- **Confidence gate on the REPLACES relation itself** — if the extractor reports low confidence (hypothetical, speculative, "might replace"), the supersession does not fire. This depends on the relation extractor emitting per-relation confidence; initial rollout can use a rule on the source text ("would", "might", "could" → skip) instead.
- **Tech-array containment** — the old memory must actually list the deprecated tech, not just mention it in text; prevents false positives from incidental mentions.

Supersessions are applied in a single transaction with the new memory insert so there is no partial state.

### 5.4 `confidence` — v1 placeholder rule

Explicitly placeholder. Intended to be replaced by an ML classifier in a follow-up once we can measure whether confidence-weighted ranking actually lifts retrieval.

```python
HIGH_CONFIDENCE_MARKERS = {"definitely", "confirmed", "always", "verified", "proven"}
LOW_CONFIDENCE_MARKERS = {"maybe", "perhaps", "not sure", "probably", "might", "would consider"}

def estimate_confidence(text: str, memory_type: str) -> float:
    t = text.lower()
    low = any(m in t for m in LOW_CONFIDENCE_MARKERS)
    high = any(m in t for m in HIGH_CONFIDENCE_MARKERS)
    if low and not high:
        return 0.5
    if high and not low:
        return 0.9
    if memory_type in ("fact", "decision", "reference"):
        return 0.85
    return 0.75  # default
```

Known failure mode: "I think X is definitely correct" triggers both markers and falls through to the default; acceptable for v1. If the ranking benefit proves too small to measure, leave the rule as-is and raise an issue for the ML replacement.

Acceptance: integration tests green; `memory.technologies` populated from entities on a 50-memory smoke test; REPLACES-supersession detector fires on a constructed "we switched from X to Y" memory and correctly skips a "we might switch…" memory; `estimate_confidence` produces non-default values for ≥ 10 percent of a random 100-memory sample.

## Phase 6 — backfill historical memory metadata (half day)

One-shot script `backend/scripts/backfill_metadata_v2.py` with dry-run default:

```bash
python -m scripts.backfill_metadata_v2             # dry-run: report counts
python -m scripts.backfill_metadata_v2 --commit    # apply
```

For each existing memory:
1. `technologies` — query entities table, filter by tech entity types, set the array.
2. `project` — already defaults to `'default'` server-side; no update needed.
3. `status` — defaults to `'active'`; no update needed.
4. `superseded_by` — NULL for historical rows. We do not retroactively chain old supersessions. (Phase 6.5 handles historical REPLACES relations separately.)
5. `confidence` — compute via `estimate_confidence(text, memory_type)` and UPDATE.

Acceptance: dry-run reports expected counts; after commit, every memory has non-NULL `technologies` and `confidence`; existing retrieval path returns identical results for queries that do not use the new filters.

## Phase 6.5 — backfill historical relationships to 5-type (half day, NEW)

Historical `memory_relations` rows are in 10-type (or legacy 30-type) form. Map them into the new 5-type space so the graph is internally consistent.

One-shot script `backend/scripts/backfill_relations_v2.py` with dry-run default:

```bash
python -m scripts.backfill_relations_v2             # dry-run: report 10->5 mapping counts
python -m scripts.backfill_relations_v2 --commit    # apply: UPDATE or DELETE rows
```

Logic per relation row:
- Look up `relation_type` in REL_MAP_5.
- If it maps to a 5-type label → `UPDATE memory_relations SET relation_type = <new>`.
- If it maps to None (`RELATED_TO`, `HAPPENED_ON`, `AUTHORED_BY`, and the 30-type droppables) → `DELETE`.
- Log counts per transition.

Run once after Phase 4 migration, before Phase 7 retrieval integration. Any retrieval path that enumerates relations per-memory then sees a uniform 5-type label space.

Acceptance: dry-run shows ~30 percent of historical relations deleted (matching the observed drop share from test data); after commit, `SELECT DISTINCT relation_type FROM memory_relations` returns only the 5 valid types; no orphan references.

## Phase 7 — retrieval integration (2 days)

### 7.1 Search filters

```python
class SearchRequest(BaseModel):
    query: str
    project: str | None = None
    status: list[MemoryStatus] = [MemoryStatus.ACTIVE]
    technologies_any: list[str] | None = None
    memory_type: list[MemoryType] | None = None
    top_k: int = 10
```

Filter applied as SQL WHERE conditions before the semantic / lexical search step. Default `status=[active]` hides superseded and deprecated memories from normal queries.

**UX tension note.** Hiding superseded memories is right for "what is the current state" queries but wrong for "what have we tried historically" queries. Recommended UI/UX handling: add a "show history" toggle in the memory browser that flips the request to `status=['active', 'superseded']`. Agent-facing tools should default to active-only unless the agent is asking an exploration-style question.

### 7.2 Rank fusion (multiplicative confidence weighting)

Replace the previous additive form. Confidence boosts or dampens a combined base score:

```python
base = alpha * semantic_score + beta * lexical_score
final_score = base * (1 + gamma * (confidence - 0.75))
```

With `gamma` in [0, 1]. Tune via grid search against the retrieval test set; if MRR@10 does not improve at any gamma > 0 the rule is too noisy and `gamma=0` disables the weighting cleanly.

### 7.3 Measurement

Run the existing retrieval benchmark before and after the metadata rollout:

```bash
python -m scripts.retrieval_benchmark \
    --pairs runs/retrieval-contrastive/test_pairs.jsonl \
    --model models/darkmem-retriever-v1
```

Expected MRR@10 lift: +0.01 to +0.03 from filtered search removing stale/off-project candidates before sort. Not a headline number, but hand-audit of a 20-query sample should show meaningfully fewer stale memories in results. Record both the automated MRR and the qualitative sample in the progress log.

Acceptance: `/api/search` accepts all four new filters with sensible defaults; retrieval MRR@10 does not regress; qualitative audit flags ≤ 3 stale memories per 20-query sample (vs a typical ~7-9 before the metadata change, based on anecdotal reports).

## Progress log

One file: `fine-tuning/runs/2026-04-19-schema-v2/progress.md`. Per-phase rows with counts, metrics, decisions, mirrors the Phase-2-relaug logbook pattern.

## Risks and mitigations

- **v1-on-5-type baseline surprises.** If rebel-large-v1 rescored on 5-type is already above our v2 absolute floor (0.70), promotion becomes harder because we need the 0.05 relative gate too. That is the intended behaviour — do not ship a v2 that does not beat v1-rescored.
- **REPLACES detector over-fires.** Staleness window, project scope, tech-containment check, and relation-confidence gate all exist to contain this. If we see > 5 percent of active memories flipped to superseded in the first backfill run, pause and audit before commit.
- **Confidence rule is too coarse.** Likely. Mitigation is the gamma dial in rank fusion: we can zero it out if the signal is not helpful, keep the column populated for future ML upgrade.
- **Historical relation backfill is lossy.** Dropping ~30 percent of existing relation rows is permanent once committed. Always run the dry-run first; keep a pre-migration pg_dump snapshot on the backend host.
- **Backward compat for the relation set.** The repo is pre-1.0 and internal. Document the 5-type set in `backend/app/services/relations.py` and in `darkraise-ui`. No API versioning wrapper; direct replacement. Any external consumer that needs the old types can pull from the pre-migration pg_dump.

## Follow-ups after this plan lands

- Reference-update sweep: `INTEGRATION_PLAN_v3.md`, any README that mentions the 10-type relation set, the frontend type definitions in `darkraise-ui`, and `PRODUCTION.md` relation row.
- rebel-base distillation targeting the new v2 teacher (easier on 5-type → expected F1 ≥ 0.70 at 606 MB VRAM).
- Confidence-classifier ML upgrade once retrieval metrics reveal whether the rule-based placeholder is worth upgrading.
- `importance` column as a follow-on metadata addition if retrieval needs finer ranking than `confidence` alone.

## Total effort

| phase | effort | dependencies |
|---|---:|---|
| 0 — tooling | 0.5 day | — |
| 1 — remap + rebuild | 0.5 day | Phase 0 |
| 2 — train rebel-large-v2 | 2 hours LXC | Phase 1 |
| 3 — evaluate + promote | 1 hour | Phase 2 |
| 4 — schema migration | 0.5 day | — (parallel with 0–3) |
| 5 — pipeline changes | 2 days | Phase 4 |
| 6 — backfill metadata | 0.5 day | Phase 5 |
| 6.5 — backfill historical relations | 0.5 day | Phase 4 |
| 7 — retrieval integration | 2 days | Phases 6 + 6.5 |

Total elapsed: roughly one week with the LXC-side work running alongside the backend work.
