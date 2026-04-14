# Fine-Tuning v2 — Multi-Session HANDOFF

This document coordinates the v2 corpus generation across many Claude Code sessions.

## Current state

| Corpus | File | Target | Completed | Next batch |
|---|---|---:|---:|---|
| Shared base | shared/shared.jsonl | 7,000 | 600 | batch-013 |
| Extraction top-up | extraction/topup.jsonl | 3,000 | 5,368 (absorbed) | batch-001 |
| Classification top-up | classification/topup.jsonl | 3,000 | 0 | batch-001 |
| Retrieval top-up | retrieval/topup.jsonl | 3,000 | 0 | batch-001 |
| Document stub | documents/seed.jsonl | 200 | 0 | batch-001 |

## Rules for every session

1. Read this file first; find `Next batch` for the corpus you're generating.
2. Write 1 batch per tool call, ≤50 items (shared) or ≤100 items (top-up), in one `Write` append.
3. Run the validator:
   ```
   cd fine-tuning
   python -m scripts.validate_v2 data/v2/<corpus>/<file>.jsonl --kind <kind> --failed-dir data/v2/failed/
   ```
4. If any rows fail validation, remove them from the file and note them in the "pending rewrites" section below.
5. Update the "Current state" table and "Next batch" row.
6. Commit with `data(fine-tune): <corpus> <batch-id> (+N rows, -M failed)`.

## Schema — shared row

Every shared row has exactly these fields:

- `id` (str, unique, pattern: `shared-NNNNN`)
- `domain` (one of `technical`, `ai_coding`, `personal`, `knowledge`, `cross`, `noise`)
- `text` (1–3 sentence memory, natural, plausible)
- `memory_type` (one of the 7 types below)
- `noise` (bool)
- `entities` (list, each with `name`, `type`, `start`, `end`)
- `relationships` (list, each with `source`, `target`, `type`)
- `queries` (list of exactly 2; one `form: question`, one `form: keyword`) — omit for noise rows

Noise rows set `noise: true`, `entities: []`, `relationships: []`, omit `queries`, use `memory_type: fact`.

## Taxonomy — memory types

`fact`, `decision`, `preference`, `problem`, `reference`, `architecture`, `milestone`.

`reference` requires a citable source (URL, named publication, documented standard, or explicit citation). Otherwise use `fact`.

## Taxonomy — entity types

Technical: technology, service, library, database, framework, protocol, algorithm, project, language, platform, infrastructure
AI-coding: file, command, error, config, pattern, api
Personal: person, place, organization, event, date, food, activity, goal, emotion, hobby
Knowledge: concept, theory, publication, method, finding, claim, field, tool

## Taxonomy — relation types

Core 12: USES, DEPENDS_ON, REPLACES, IMPROVES_ON, IS_A, HAS_PART, COMMUNICATES_WITH, KNOWS, LOCATED_IN, HAPPENED_ON, CAUSES, RELATED_TO
Extended: DEPLOYED_ON, PRODUCES, IMPLEMENTS, FIXES, CONFIGURES, EXTENDS, LIVES_IN, WORKS_AT, VISITED, FEELS_ABOUT, PLANS_TO, PREFERS, SUPPORTS, CONTRADICTS, BUILDS_ON, AUTHORED_BY, PUBLISHED_IN, APPLIES_TO

Direction rules:
- REPLACES: source = new, target = old
- IMPROVES_ON: source = improvement, target = baseline
- BUILDS_ON: source = derivative, target = foundation
- DEPENDS_ON: source = dependent, target = dependency

## Prompts

### Shared base (50 rows per batch)

> Write 50 memory entries in the `{domain}` domain. Each entry is one JSON object on its own line, matching the shared-row schema above. Include ~5% noise rows (noise=true, empty entities/relationships, omit queries). Include at least 5 rows with REPLACES or IMPROVES_ON to exercise direction-sensitive relations. Vary entity count per row (1 to ~6). Use ≥15 distinct entity types across the batch. Verify every `text[start:end]` equals the corresponding entity name before writing. Append all 50 rows to `data/v2/shared/shared.jsonl` in one Write call.

### Extraction top-up (100 rows per batch)

> Write 100 extraction-only memory entries that stress `{failure_mode}` (one of: direction_sensitive, multi_entity_architecture, long_tail_types, hard_noise, cross_paragraph). Schema: `{id, domain, text, memory_type, entities, relationships}`. Do NOT include queries. Append to `data/v2/extraction/topup.jsonl`.

### Classification top-up (100 rows per batch)

> Write 100 classification-only memory entries targeting `{mode}` (one of: contrastive_reference_fact, contrastive_decision_architecture, short_ambiguous, multi_type). For contrastive modes, emit items in paired topic clusters with `pair_id` linking them. Schema: `{id, domain, text, memory_type, pair_id?}`. Append to `data/v2/classification/topup.jsonl`.

### Retrieval top-up (100 rows per batch)

> Read shared rows {offset}–{offset+99} from `data/v2/shared/shared.jsonl`. For each row, write 1 hard retrieval row using kind `{query_kind}` (one of: paraphrase, acronym, typo, code-switch, multi-sentence, hard-negative). Schema: `{id, source_id, query, positive, query_kind}` (for hard-negative: `{id, source_id, query, negative, query_kind}`). Append to `data/v2/retrieval/topup.jsonl`.

## Batch log

| Batch ID | Corpus | Domain/mode | Rows written | Rows failed | Commit |
|---|---|---|---:|---:|---|
| absorb-ext | extraction/topup | absorbed from data/validated/all.jsonl | 5,368 | 2,632 | `61c5eca` |
| batch-001 | shared | technical | 50 | 0 | `5175850` |
| batch-002 | shared | ai_coding | 50 | 0 | `5b648de` |
| batch-003 | shared | personal | 50 | 0 | `5720818` |
| batch-004 | shared | knowledge | 50 | 0 | `3cb04a4` |
| batch-005 | shared | cross | 50 | 0 | `77ecbdb` |
| batch-006 | shared | technical | 50 | 0 | `d44cda7` |
| batch-007 | shared | ai_coding | 50 | 0 | `4bdff91` |
| batch-008 | shared | personal | 50 | 0 | `81fe18d` |
| batch-009 | shared | knowledge | 50 | 0 | `17cbcd5` |
| batch-010 | shared | cross | 50 | 0 | pending |
| batch-011 | shared | technical | 50 | 0 | pending |
| batch-012 | shared | ai_coding | 50 | 0 | pending |

## Generation pattern

Batches are emitted by one-off scripts `scripts/_emit_shared_batch_NNN.py` that embed the entries as Python data (text + entity names + types + relationships + queries) and compute character offsets programmatically via `str.find()` so the offsets cannot drift. Pattern for future batches: copy the previous batch's emit script, swap `ENTRIES`, and re-run. The scripts are versioned alongside the data so the audit trail stays intact.

## Pending rewrites

Failed rows that need to be regenerated in a future session go here.

## Do not modify

- `docs/e2e/scripts/retrieval_eval/queries.jsonl` — 270-query fixed test set
- `docs/e2e/scripts/retrieval_eval/gold.jsonl` — 195-memory passage pool for the test set
- `docs/e2e/scripts/classification_eval/corpus/gold.jsonl` — 60-example classification gold set
