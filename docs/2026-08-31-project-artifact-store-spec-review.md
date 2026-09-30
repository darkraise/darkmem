# Adversarial review — project-artifact-store spec

Date: 2026-08-31
Subject: `docs/superpowers/specs/2026-08-31-project-artifact-store-design.md`
Status: acted on. The spec was revised the same day (§5 and §8 rewritten, §9's
worker redesigned, §2 and §9.7 amended) and cites these finding ids (B1, B2,
M1-M6, m1-m5) throughout, which is why this record is committed rather than
left in a scratchpad.

Charter was to find the reasons the spec should NOT be implemented as written.
Three of its most consequential findings were independently confirmed against
the code before the spec was revised.

---

# Adversarial review — 2026-08-31 project-artifact-store spec

Reviewed: `docs/superpowers/specs/2026-08-31-project-artifact-store-design.md` (spec).
All paths repo-relative to `/root/repositories/darkmem`. Line numbers verified against
the working tree at `6aac816b`.

---

## BLOCKER

### B1 — §9's `READ_ONLY` posture cannot hold at the door layer; the biggest writers never pass a door

**Claim under attack**: §9.5 — the worker "runs the same darkmem image in a read-only
posture" needing only "a `READ_ONLY` posture that refuses writes at the door layer …
so the guarantee holds for anything reaching the API" (spec:531-543).

**Evidence the guarantee leaks, none of it door-reachable:**

- **Boot writes before the first request.** `entrypoint.sh:3-17` runs
  `alembic upgrade head` then `app.schema_guard`, which *stamps a hash into the
  database it migrated* (CLAUDE.md, Migrations). A "read-only" worker mutates the
  restored snapshot at every container start. Worse: if the snapshot predates the
  worker image's baseline, `schema_guard` "refuses to start … fails closed with no
  override flag" — the viewer goes down for exactly the older snapshots one most
  wants to inspect.
- **The job scheduler starts unconditionally.** `backend/app/main.py:581`
  (`await job_registry.start_all()`) arms all 23 jobs. On a restored snapshot:
  `buffer_flush` drains any pending `memory_buffer` rows through the full pipeline —
  **making live LLM/embed calls with the real credentials sitting in the snapshot's
  `llm_providers` rows**; `expired_memory_cleanup` DELETEs; `repo_sync` runs git;
  the dream family runs; and the proposed `backup_ship` job itself would run on the
  worker, shipping snapshots of snapshots. A door-layer refusal touches none of this.
- **Boot embedder registration writes** (`main.py:92-139`): `embedder_registry.register`
  INSERTs into `embedders` and runs `CREATE TABLE IF NOT EXISTS` for partitions.
- **Reads that write.** `mark_key_used` bumps `api_keys.last_used_at` on every MCP
  scope check in its own committed session (`backend/app/services/api_keys.py:284-305`);
  fact reads batch-bump `fact_access_stats` (`backend/app/services/fact_access_stats.py:69-75`);
  auth journals `auth_*` events through `record_event` — and login itself must be
  allowed or the SPA viewer is unusable, yet login writes (journal rows, token
  rotation → blocklist rows).
- **Verb shape does not classify routes.** `POST /api/v1/documents/search` and
  `POST /api/v1/usage/subject-totals` are read-shaped POSTs (the REST conventions
  doc's own pattern); a method-based refusal breaks search, so the posture needs a
  maintained per-route allowlist the spec never mentions.
- **§9.2 contradicts §9.5.** The destinations table (spec:494-499) has the worker
  *receive* snapshots over https — a write door on the instance whose defining
  property is refusing writes. Unaddressed.
- **Scheduled restore vs the running worker.** `scripts/restore.sh:82-99` swaps via
  `ALTER DATABASE … RENAME`, which requires no live connections (it offers
  `RESTORE_FORCE=1` to terminate them). A worker app holding a pool blocks its own
  scheduled restore; if connections are killed and the swap lands, the app reconnects
  to a database `schema_guard` never re-checked (the guard runs only at boot). The
  spec does not say where the restore loop even runs (a JobRegistry job inside the
  app would be dropping its own database out from under itself).

**Why it matters**: a posture that silently fails to hold is worse than none — the
owner reads "read-only viewer" and trusts it while the worker mutates the snapshot,
spends real LLM money, and ships derivative backups.

**Recommendation**: amend §9.5 before increment 7 is planned. The posture must be
process-level, not door-level: scheduler disarmed (no `start_all`), LLM orchestrator
disarmed, boot writers gated or accepted-and-documented (alembic/schema_guard/embedder
registration), an explicit route allowlist for the door half (login + reads +
read-shaped POSTs), and the restore loop placed outside the app (host timer) with the
schema-mismatch outcome stated. The `/auth/security-posture` reporting idea is good
and survives the redesign.

### B2 — §8 claims a baseline regen without naming one schema change, and is mutually incoherent with §5

**Claim under attack**: §8.4 "Cost: **Baseline regeneration**" (spec:462-467) and
§8.2's "repays the cost model" (spec:439-451).

**The regen has no referent.** §8.1's three forced changes — diff-and-update ingest,
granular block verbs, per-block re-embed — are all code-level: `blocks.id` is already
the PK, `blocks.parent_id`/`order_index`/`properties` already exist
(`backend/migrations/versions/0001_baseline.py:1307-1316`), and
`block_embeddings__<slug>` already keys `(block_id, fingerprint)`
(`backend/app/services/embedder_registry.py:87-95`). Nowhere does §8 name a column,
constraint, or table that forces the regen it prices. Either the actual schema delta
is missing from the spec (my guess: a per-block content hash or client-stable block
key for diff matching, and whatever "nested pages" needs — see below), or the cost
row is wrong. A plan cannot be written against an unspecified schema change that is
also the plan's single largest cost.

**"Nested pages" is undesigned.** The opening sentence promises "nested pages"
(spec:410-411); documents have no hierarchy (`0001_baseline.py:1276-1287` — no parent
column) and a Notion page-block that opens a child document exists in no table. This
is plausibly *the* regen item, and it is never mentioned again.

**§5 and §8 collide, and the spec's only acknowledgment is one soft sentence.** After
a granular block edit:

- What is `documents.content_hash` — hash of what content? The raw source in
  `properties["$content"]` no longer matches the blocks. §5's `expected_hash`
  precondition (spec:327-333) preconditions on a value the block verbs either must
  recompute (from a re-serialization of the whole tree — i.e. a full re-file per
  keystroke-ish save, which recreates exactly the cost model §8.2 claims to repay)
  or leave stale (silently breaking the optimistic concurrency §5 just built).
- Every block's `char_span` indexes into the original source
  (`0001_baseline.py:1316`); editing one block invalidates the spans of every
  subsequent block. Recomputing them is again a whole-tree write; not recomputing
  them breaks the citation anchor and the `$content` round-trip.
- §8's ordering note (spec:448-451) concedes only that §3's *cost* argument
  "weakens" — it does not notice that §5's *artifacts* (`$content`, `content_hash`
  semantics, `char_span`) become undefined under block-verb writes.

**Doc 16's anchor doctrine inverts and only §7 is amended.** Doc 16 builds the lift
and citation provenance on "block ids are freshly minted on each re-ingest, nothing
durable may FK a block id … the durable anchor is `(document_id, char_span)`"
(`docs/design/16-documents-and-pkm.md:97`, restated §5 :182 and §8 :229, §9 :246).
§8 makes ids durable and spans unstable — the exact inversion — yet amends only
doc 16 §7 (spec:415-417). The lift is horizon (unshipped), so nothing breaks in code
today, but a spec that flips a doctrine three sections of a design doc state, while
amending a fourth, will mislead the next reader of doc 16.

**Recommendation**: §8 is not plannable as written. Before any plan: (a) name the
schema delta or drop the regen claim; (b) design the write-direction reconciliation
with §5 (proposal to evaluate: under §8, `$content`/`content_hash` become derived
from blocks via a canonical serializer, `char_span` becomes nullable-and-editor-owned
or is recomputed on serialize, and `expected_hash` preconditions on a document
version counter instead); (c) design or cut "nested pages"; (d) amend doc 16 §2/§5/§9
alongside §7. See also M5 on "weeks".

---

## MAJOR

### M1 — §5's `expected_hash` is check-then-act as written; the race it exists to close stays open

The justification is 4-5 concurrent lanes over an LWW upsert (spec:207-214, 327-333).
But resolve and write are separate awaited statements
(`backend/app/repositories/documents.py:65-88`), and `put_document` runs its body
across many awaits before `session.commit()` (`backend/app/services/document_door.py:441-459`).
Two lanes both read hash H at their resolve, both pass a door-level comparison, and
the last writer still wins — the same silent loss, now behind a feature named after
preventing it. The single worker does not save this: asyncio interleaves at every
await. **Recommendation**: the spec must mandate the precondition *in the SQL* —
`ON CONFLICT … DO UPDATE … WHERE documents.content_hash = :expected` with a rowcount
check distinguishing "inserted" / "updated" / "precondition failed" (or
`SELECT … FOR UPDATE`). One sentence in §5 fixes it; a plan written from the current
text will likely implement the racy version.

### M2 — §2's project index is backed by memories only; a document-only project is invisible, and the cited pairing misleads

`GET /api/v1/projects` is `SELECT project, count(*) FROM memories GROUP BY project`
(`backend/app/api/routes/projects.py:38-49`); its own docstring says "derived, never
a registry" (`projects.py:15-20`). Document filing never calls
`project_registry.register` (its callers: `backend/app/services/memory.py`, capture
paths — not `document_ingest`/`document_door`). Consequences:

- The increment-5 corpus import into project `darkmem` (documents, zero memories)
  produces a project the workspace's entry-point cards never show.
- The card data §2 promises — "document count, latest checkpoint age, latest event
  age" (spec:98-102) — is not in the response (`{name, memory_count}` only), so
  increment 4 needs a new or widened backend endpoint, contradicting its "low —
  composition over shipped routes" risk row (spec:353).
- The citation `backend/app/api/routes/projects.py:10; registry model
  backend/app/models/project.py:23` (spec:99-100) is *technically* line-accurate and
  substantively wrong: the route never touches the `projects` table. This is the
  kind of citation that propagates — a planner will assume the registry backs the
  route.

**Recommendation**: amend §2 to scope the backend work (widen the route to UNION
`documents.project` + aggregates, or register projects on document filing) and
re-rate increment 4.

### M3 — The §5 bridge dodges a regen the same spec schedules, and §9.7's "restore the content" is unsupported by the shipped restore

The bridge's stated justification is avoiding "a drop/recreate + three-pass restore
of production for one column" (spec:322-326). But: the greenfield ruling the spec
itself quotes (`CLAUDE.md:8-23`) prices data as disposable — the three-pass-restore
cost is the cost of preserving data nobody is owed; prod `documents` holds 0 rows
(measured); and increment 8 of *this same spec* commits a regen that D1 explicitly
rides (spec:358, 465-467). So the bridge's whole lifetime is the inc-3→inc-8 gap,
and no increment scopes its unbuild (door merge removal, `include_content`
re-pointing, `$content` strip).

Sharper: §9.7 claims the greenfield ruling stays survivable because you can "drop and
recreate the database freely, then restore the content" (spec:554-561). The shipped
restore replays a **full pg_dump into a side database and swaps it in**
(`scripts/restore.sh:31,99`) — that restores the *old schema wholesale*, undoing the
regen. Carrying content across a schema change needs a transform-restore (the
`backend/scripts/cutover/llm_providers_transition.py` shape), which no increment
scopes. As written, §8's own regen destroys every personal note filed in increments
4-7 with no restore path that survives the regen. **Recommendation**: either take
the `content` column now (cheapest under the ruling, zero rows at stake) and shrink
§5 to `expected_hash` + `include_content`; or keep the bridge and add (a) its unbuild
to D1's scope and (b) a per-regen transform-restore increment that makes §9.7 true.

### M4 — Increment 6's `backup_ship` "over the existing scripts" crosses a process boundary the spec doesn't see

`scripts/backup.sh` runs `docker compose exec -T postgres pg_dump …`
(`backup.sh:11,27`) — host-side, via the compose CLI and the docker socket, neither
of which the app container has; the image carries no `pg_dump` (no postgres client
in `Dockerfile`); and the host backup directory (`/root/darkmem-backups`) is not
mounted into the app container. A JobRegistry job can therefore neither run the
script nor, today, see its output. The workable shape — systemd keeps dumping (the
spec's own "floor", spec:505-507), and `backup_ship` is *ship-only* over a newly
mounted volume — requires a compose change and a "job reads files it did not
produce" contract (partial-file exclusion: the `.part` convention helps) that the
spec should state instead of "the scripts already carry the hard parts" (spec:355).
**Recommendation**: amend §9.3 to fix the division of labor (dump = host, ship =
job) and add the volume mount to increment 6's scope.

### M5 — §8's "weeks" hides an unmade editor-technology decision

darkraise-ui ships no block-editor primitive — the closest are `editable` (inline
single-value) and `textarea` (enumerated `frontend/node_modules/darkraise-ui/dist/components/`).
A Notion-style editor (nested blocks, drag-reorder, slash commands, save-as-you-type)
is therefore either a from-scratch build or a new third-party dependency
(ProseMirror/TipTap/BlockNote-class) — an ADR-shaped choice with licensing, bundle
and data-model consequences (those libraries carry their *own* block JSON model,
which must round-trip with `blocks` rows). CLAUDE.md's darkraise-ui-first rule
requires a local component to record the library gap it works around. The spec makes
no choice and prices the whole of §8 at "weeks" (spec:357). Adjacent finding, same
family: "no CRDT keeps it weeks rather than months" (spec:456-458) is asserted, not
derived. **Recommendation**: the §8 plan must open with the editor ADR; until then
"weeks" should be treated as unestimated.

### M6 — §5's reserved key is forgeable by the caller

"merged server-side with whatever `properties` the caller passed" (spec:314-317)
never states what happens when the caller's `properties` *contains* `$content`. The
upsert and update both write properties wholesale
(`backend/app/repositories/documents.py:85,96`), so an unstripped caller key would
let a filing desync the stored "raw source" from `content_hash`, the blocks, and
every `char_span` — corrupting exactly the round-trip and `expected_hash` semantics
§5 exists to provide. **Recommendation**: one added rule — the door strips or 422s
any caller-supplied reserved key, tested on both doors.

---

## MINOR

### m1 — §2's Artifacts tree caps at 200 rows against a 446-file corpus, in the same sentence that calls it fine

"grouping is client-side over the ≤200-row page, which is fine at this corpus size —
446 files" (spec:107-109) is self-refuting: the list route clamps `limit` to 200
(`backend/app/api/routes/documents.py:279`), so one page holds fewer than half the
imported corpus and the tree silently truncates — the invariant-14 shape the spec
polices elsewhere. Fix in planning: paginate-and-stitch in the hook, or raise the
clamp.

### m2 — Checkpoint step history is write-only; a late-joining viewer cannot read past notes

Rows are append-only by design (`backend/app/services/checkpoints.py:189-193`), but
the only reads are `POST` and `GET /latest` (`backend/app/api/routes/checkpoints.py:30,68`),
and the `checkpoint_saved` payload deliberately excludes the summary
(`checkpoints.py:216-222` — write-time minimization). So increment 1's live watch
works (poll latest + events timeline), but the timeline entries carry no content and
no verb serves a run's past summaries. If the Progress tab is ever expected to show
step *content* history, that is a new read verb — backend work the spec's framing
("no backend change", spec:124-126) excludes. State the limit in §3 or scope the verb.

### m3 — Old rows never acquire `$content`: the unchanged gate skips properties

"An unchanged hash does *nothing*" — no property write
(`backend/app/services/document_ingest.py:15-29`). A document filed between
increments 2 and 3 and re-pushed byte-identical hits `UNCHANGED` and never gains
`$content` — while the door's unchanged branch *does* already do embed-repair
(`document_door.py:461-469`), proving the branch is the right place for a `$content`
backfill too. One sentence in §5; small blast radius (greenfield, 0 prod rows), but
an implementer following the ingest docstring will get it wrong.

### m4 — §9's per-job lock does not serialize `backup_ship` against the systemd timer

§9.3 keeps both schedulers on purpose (spec:503-507), but the JobRegistry lock is
per-job and in-process; nothing coordinates a 03:30 timer dump with a job-cron dump
or ship. The `.part` rename discipline makes collisions mostly benign, but "mostly"
should be stated (e.g. ship only files older than N minutes). Also: encrypting and
uploading multi-hundred-MB dumps from inside the app must be executor-offloaded or
it stalls the single worker's event loop (invariant 13 context).

### m5 — Citation nits (sampled verification, full list below)

- `document_door.py:290` cited for `SectionHit.heading_path` (spec:113): line 290 is
  `search_sections`; `SectionHit` is at `document_door.py:212-230`. Concept holds,
  line off.
- `checkpoints.py:88,212` (spec:160): `CHECKPOINT_SAVED_EVENT` at 88 exact;
  `record_event` at 210, not 212.
- The §4 warning constant "8,000 chars — the nomic budget" (spec:255-257):
  nomic's budget is 2048 *tokens*; 8,000 chars assumes ~4 chars/token. Fine as a
  stated floor, but the spec should say token-vs-char basis so the constant isn't
  later "corrected" to 2048.

---

## Citation verification (sample across §§1-7)

Verified exact: `0001_baseline.py:1282` (content_hash), `:1283` (properties),
`:1293-1296` (partial unique index), `:1313` (`type TEXT`, no CHECK);
`block_query.py:110-113` (project-no-default rule; spec says 113-115, close);
`taxonomy.py:383-389` (`BLOCK_TYPES`), `:416` (`normalize_block_type`);
`embedder_registry.py:87-95` (PK `(block_id, fingerprint)`); `llm.py:499`
(count-chunking); `job_registry.py:89-98` (`default: int`); `server.py:503`
(`checkpoint_save`); `repo_manager.py:330` (`git_token_<repo_id>`);
`document_parsers.py:33-52` (SOURCE_TYPE convention), `:211-213` (hr/html_block/table
skip); `document_ingest.py:246` (`strip_blocks`); `repositories/documents.py:75-88`
(upsert), `:81-85` (properties wholesale); `document_door.py:60` (MAX_CONTENT_CHARS),
`:61` (MAX_BLOCKS), `:601` (`BlockRow`); `routes/documents.py:276` (list route);
`docs/two-door-parity.md:55` (documents.reads quote), `:59` (checkpoint rows);
`documents-view.tsx:30` (`project = "default"`); `events.py` docstring predicate
claim + `checkpoint_saved`/`resumed`/`document`/`checkpoint` vocabulary;
`list_events` builds project into SQL (`events.py:378-416`); `checkpoints.py:106`
(4000), `NEXT_STEPS_MAX_BYTES` 16384.

Wrong or misleading: `projects.py:10` + `models/project.py:23` pairing (M2 — route
never reads the registry); `document_door.py:290` (m5); `checkpoints.py:212` (m5,
trivial).

---

## Verdict

**Safe to plan as written**: Increment 0 (config-only), Increment 1 (with m2's limit
stated), Increment 2 (parser fixes — the strongest section of the spec; measured,
taxonomy-first, correctly scoped), Increment 5 (import — re-runnable; note it lands
into a project the index cannot show until M2 is fixed).

**Spec must be amended before planning**: Increment 3 (M1 SQL compare-and-set, M6
reserved-key rule, m3 backfill), Increment 4 (M2 backend scope + risk re-rate),
Increment 6 (M4 process boundary + volume mount), the D1/bridge decision itself (M3
— either take the column now or scope the unbuild and the transform-restore that
makes §9.7 true).

**Cut or redesign before any plan exists**: Increment 7 (B1 — the door-layer posture
demonstrably cannot hold; redesign process-level, restore loop outside the app),
Increment 8 (B2 + M5 — a regen with no named schema delta, an unreconciled collision
with §5's artifacts, an undesigned "nested pages", and an unmade editor ADR priced
at "weeks"; §8.2's "repays the cost model" is unearned until the char_span/content_hash
question is answered, because the naive answer re-creates the whole-document cost per
edit).

D2 and D3 are correctly deferred; D3's framing (ruling amendment, owner's call) is
exactly right.
