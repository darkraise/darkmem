# Pages: a Notion-model note tree beside documents

**Status:** draft, revised after adversarial review. Awaiting owner approval.
**Date:** 2026-09-08
**Supersedes nothing.** Amends the personal-notes epic
(`2026-09-07-personal-notes-workspace-design.md`) §2, which decided nesting is
the `uri` path. That decision stands **for documents** and is reversed only for
the new object this spec introduces.

## 1. The decision, and why the epic spec's §2 does not cover it

The epic spec §2 argued that nesting is the `uri` path: `uri` is required on
both doors, so every document already carries a path, and `documents.parent_id`
would duplicate what the path encodes while creating a second hierarchy that
can contradict `blocks.parent_id`. That reasoning is sound and is not overturned.

What it did not anticipate is that **the personal note surface and the
project-artifact surface want different invariants**, not different vocabulary
over one invariant:

| | Project document | Personal page |
|---|---|---|
| Address | full `uri` path | `parent_id` |
| Filing a child | succeeds at any depth, unconditionally | requires the parent row to exist |
| Creates ancestors | nothing | nothing — refuses instead |
| Order among siblings | none; alphabetical at render | explicit `order_index` |
| Author | an agent, over MCP or REST | a human, in the SPA |
| Source of truth | the file or agent that filed it | this row — there is no other copy |

Forcing one model to serve both produces ghost rows: a document filed at
`meetings/2026/q3.md` would have to mint `meetings` and `meetings/2026` as pages
nobody authored, appearing in listings, counts and search where today they are
derived client-side and exist nowhere.

**So: two objects, two tables, two doors.** `documents` is unchanged in
behaviour by this spec. `pages` is new.

This also settles the personal/project separation the epic left at the project
level: `projects.kind IN ('project', 'personal')` with `ux_projects_one_personal`
stays exactly as it is, and the object split now carries the distinction that
matters.

**The last row of that table is why §9 is a soft delete and not a cascade.**

## 2. What `pages` is

```sql
CREATE TABLE pages (
    id           UUID NOT NULL,
    project      TEXT NOT NULL,
    parent_id    UUID,
    order_index  INTEGER NOT NULL,
    title        TEXT,
    content      TEXT NOT NULL DEFAULT '',
    content_hash TEXT NOT NULL,
    properties   JSONB,
    deleted_at   TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pages_pkey PRIMARY KEY (id),
    -- A child's parent must be in the same project. Composite rather than a
    -- plain self-FK: a cross-project reparent is then impossible in the
    -- schema, not merely refused at the door.
    CONSTRAINT ux_pages_id_project UNIQUE (id, project),
    CONSTRAINT fk_pages_parent FOREIGN KEY (parent_id, project)
        REFERENCES pages (id, project) ON DELETE CASCADE
);
CREATE INDEX ix_pages_project_parent_order ON pages (project, parent_id, order_index);
CREATE TRIGGER pages_touch_updated_at BEFORE UPDATE
    ON pages FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
```

- **The composite parent FK gives "the parent must exist first" and "in the same
  project" together.** NULL `parent_id` is a root page. A plain self-FK would
  have left every project's roots sharing one `parent_id IS NULL` ordering
  bucket and permitted a cross-project reparent; the composite form closes both.
- **`ON DELETE CASCADE` is the *purge* path only** — §9's ordinary delete is a
  `deleted_at` stamp and never removes a row.
- **`order_index NOT NULL`**, dense and 0-based per `(project, parent_id)`,
  server-assigned. See §7.
- **`content` and `content_hash` are NOT NULL.** `content` defaults to `''` in
  the DDL; `content_hash` takes no default and the create route writes
  `compute_content_hash('')`, since a hash default would have to hard-code a
  digest the hashing function owns. Nullable columns would mean the first
  `expected_hash` a client sends has nothing to compare against, and an emptied
  page would be indistinguishable from an unwritten one. `blocks.char_span` indexes into
  `content`, and `content_hash` is what the block verbs' compare-and-set reads
  off the owner row (`block_verbs.py:163-174`).
- **No `uri`, and no `ingest_direction`.** A page has no path — that is the
  point of the split. And a page is block-first by construction; see §5 and §6
  for how content nonetheless gets *in*.
- **`updated_at` moves by the `touch_updated_at` trigger**, matching `memories`
  and `documents`, so a raw-SQL UPDATE bumps it too. Note a block edit bumps the
  page's `updated_at` through the page variant of `_WRITE_DOC`, but an edit to a
  child page does **not** bump its parent: a "recently edited" tree means
  per-page recency, not subtree recency.

## 3. How `blocks` gains a second owner

**Approach:** best-of-3 — two nullable FKs vs a polymorphic owner pair vs a
`content_owners` supertype. Ring pass (A vs B, B vs C, C vs A) at judge-fable.
Wins: A 2, B 1, C 0; A won both its comparisons 3-0 on every criterion.

```sql
CREATE TABLE blocks (
    id            UUID NOT NULL,
    document_id   UUID REFERENCES documents(id) ON DELETE CASCADE,
    page_id       UUID REFERENCES pages(id)     ON DELETE CASCADE,
    parent_id     UUID REFERENCES blocks(id)    ON DELETE CASCADE,
    order_index   INTEGER,
    type          TEXT,
    text          TEXT,
    properties    JSONB,
    char_span     INT4RANGE,
    search_vector TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('english',
            CASE WHEN type IN ('code', 'html') THEN '' ELSE coalesce(text, '') END)
    ) STORED,
    CONSTRAINT blocks_pkey PRIMARY KEY (id),
    CONSTRAINT blocks_exactly_one_owner CHECK (num_nonnulls(document_id, page_id) = 1)
);
CREATE INDEX ix_blocks_document_order ON blocks (document_id, order_index)
    WHERE document_id IS NOT NULL;
CREATE INDEX ix_blocks_page_order ON blocks (page_id, order_index)
    WHERE page_id IS NOT NULL;
-- RETAINED UNCHANGED from the current baseline. Restated because an earlier
-- draft of this spec showed the CREATE TABLE without them, which would have
-- seq-scanned every subtree delete and dropped keyword search's index.
CREATE INDEX ix_blocks_parent ON blocks (parent_id);
CREATE INDEX ix_blocks_search_vector ON blocks USING GIN (search_vector);
```

`document_id` drops `NOT NULL`; that is the only column-level change to an
existing table in this spec.

**Why this shape.** It is the codebase's own idiom applied once more — every
child table in `0001_baseline.py` carries a real FK with `ON DELETE CASCADE`,
and CHECK constraints already express conditional invariants
(`chk_superseded_has_pointer`). Both cascades stay real. The rejected
alternatives each gave something up; see the appendix.

**No cross-owner `parent_id` guard is added, and that is deliberate.** Nothing
in DDL stops a page block's `parent_id` pointing at a document block, but
neither writer can produce that state: `insert_block` and `move_block` accept a
parent only if it is in the tree `_LOAD_TREE` loaded for that owner
(`block_verbs.py:341, 387`), `_PLACE` writes parentage from that same in-memory
tree (`:249-261`), and ingest builds parentage from one parse
(`document_ingest.py:472-487`). A `BEFORE INSERT OR UPDATE` trigger would fire
once per row on every `_PLACE` — which rewrites every block of a document on
every edit — making it a per-row tax on the document path this spec promises not
to slow. The property is pinned by a test instead, the same posture
`blocks.parent_id` cycles already take (`document_door.py:268-278` records that
there is no cycle constraint either).

## 4. Page vectors get their own partition family

**This is the correction that makes §5's isolation guarantee true.** An earlier
draft had page blocks sharing `block_embeddings__<slug>`. They must not.

That partition carries one HNSW index per child (`embedder_registry.py:318-319`)
and **every document ANN read filters the owner after the index scan** —
`search_blocks` calls its own predicate "a post-scan filter over the HNSW
candidate stream" (`block_embeddings.py:275`), and `document_connections`' LATERAL
takes the ten nearest and only then applies `tb.document_id <> :id`
(`document_connections.py:177-187`). Its docstring at `:76-91` already documents
the failure mode: foreign rows "consume all ten slots … at the cost of returning
nothing for a real same-project match". Pages would be a new foreign
population — and §3 predicts the densest and most-edited one — so sharing the
partition would degrade document search recall and latency in proportion to how
much the operator writes.

So `embedder_registry` gains a `page_embeddings` template beside
`block_embeddings` in `_TEMPLATES` and `_AUX_INDEXES`: same `(block_id,
fingerprint)` key, same `REFERENCES blocks(id) ON DELETE CASCADE`, its own HNSW
index, its own `page_embeddings__<slug>` children. The existing template is
untouched.

`block_embedding_refresh` is scoped to documents by adding `WHERE b.document_id
IS NOT NULL` to `_MISSING_SQL` (`block_embedding_refresh.py:120-129`), which
today has **no owner predicate at all** — so without this, page blocks would
enter the hourly job's 500-per-tick budget and its `ORDER BY b.id` full scan,
delaying document embedding by N/500 hours on a large notes corpus. Pages get
their own repair arm on the same job, budgeted separately, so a page block whose
inline embed failed is still repaired.

## 5. The isolation guarantee: project documents are not affected

A requirement of the work, not a hope, so it is stated as an accounting — and
the accounting now covers the things that are not SQL predicates, which is where
the first draft of this spec was wrong.

**Dropping `NOT NULL` does not weaken documents.** `num_nonnulls(...) = 1` still
rejects a block with no owner at all. A bug that dropped `document_id` on a
document write is refused exactly as `NOT NULL` refused it. The only new state
the schema permits is a block owned by a page.

**No document SQL changes.** Every statement in `backend/app` naming
`blocks.document_id` filters `document_id = :id` or joins `documents` on it —
verified exhaustively at `repositories/documents.py:137,148`;
`routes/documents.py:450,995`; `document_related.py:137`;
`document_similarity.py:103,126`; `document_connections.py:171,184`;
`document_summary.py:74`; `block_embeddings.py:326`;
`document_door.py:257,469,1029,1111-1112`; `block_verbs.py:78,90,114`. No `IN`,
no `NOT EXISTS`, no unfiltered aggregate. A page block's `document_id` is NULL,
so none of them changes.

**Four sites where NULL semantics are load-bearing, not merely harmless:**

- `document_connections.py:184` filters `tb.document_id <> :document_id`;
  `NULL <> x` is never true, so page blocks are excluded automatically.
- `block_embeddings.py:326` and `document_door.py:1111` inner-join `documents`,
  dropping page rows.
- `routes/documents.py:993-1002` (`_assert_block_is_in`) 404s a page block
  addressed by id.

**Three statements read `blocks` with no owner predicate.** Two are id-keyed
from hits already scoped elsewhere and are harmless (`document_door.py:280-294`
`_ANCESTORS`; `block_embeddings.py:73-78` `_BLOCK_TEXTS`). The third —
`block_embedding_refresh._MISSING_SQL` — is not, and §4 scopes it.

**Two costs that remain, stated rather than closed:**

- **Shared heap and shared `ix_blocks_parent` / GIN index.** A heavily edited
  page rewrites every one of its rows per edit through `_PLACE`, in the same
  table as document blocks, on a host where autovacuum does not run. The partial
  owner indexes isolate one index; they do not isolate the table. Accepted:
  the alternative is a separate `page_blocks` table, which duplicates the
  parser, the four verbs and the serialiser round-trip guard.
- **`block_verbs.py` forks** (§6). It is shared code documents use. The fork is
  additive — the document path stays byte-identical — but it is not zero, and
  this spec does not claim otherwise.

**There is no ORM model for `blocks` or `documents`** — both surfaces are raw
SQL throughout, so there is no model layer to change.

**The isolation test is part of this spec**, because the correctness above rests
on NULL semantics rather than on written filters. File one page with blocks,
then assert: it is absent from document search, document connections, the
document outline and `_assert_block_is_in`; its blocks are absent from
`_MISSING_SQL`'s result set; and its vectors are in `page_embeddings__<slug>`,
not `block_embeddings__<slug>`.

## 6. The verb-layer fork

`_mutate` in `block_verbs.py` is the read-modify-write behind all four block
verbs. `_PLACE`, `_UPDATE_BLOCK` and `_DELETE_BLOCK` key on `blocks.id` and are
already owner-agnostic. Six constants touch `documents`:

| Constant | Document version | Page version |
|---|---|---|
| `_LOCK_DOCUMENT` | `SELECT id FROM documents … FOR UPDATE` | same against `pages` |
| `_DOC_META` | project, content, content_hash, direction, frontmatter | project, content, content_hash |
| `_LOAD_TREE` | `WHERE document_id = :id` | `WHERE page_id = :id` |
| `_INSERT_BLOCK` | names `document_id` | names `page_id` |
| `_WRITE_DOC` | content, hash, `ingest_direction` | content, hash |
| `_RESOLVE_BLOCK` | `SELECT document_id …` | selects both, returns the pair |

**And a seventh document-shaped thing that is not a constant:**
`object_type="document"` is hardcoded at `block_verbs.py:271`, so without a fix
a page edit would journal as a document carrying a page id and
`GET /events/timeline` would misfile it. `object_type` rides on `BlockOwner`.

`_mutate` takes a `BlockOwner` descriptor carrying the kind, the id, the
`object_type` and those statements. The document instance carries today's SQL
verbatim, so every existing document call path is byte-identical.

**Pages skip the conversion pass.** `_mutate`'s largest branch handles
`ingest_direction`: a content-first document converting to block-first, guarded
by `reproduces_source`, refusing with `DocumentNotConvertible` when the
serialiser cannot reproduce the stored source. A page is block-first by
construction — §7's create route is the only way content enters, and it parses
to blocks before the row is answered — so a page has no direction flag, no
frontmatter, and cannot raise that error.

`BlockWriteResult` keeps its `document_id` field for the document instance —
renaming it would change the document door's wire shape through
`BlockWriteResponse(**vars(result))` (`routes/documents.py:1028`) — and gains
`owner_kind` and `owner_id`.

## 7. Doors — REST only

No MCP tools, no scope vocabulary change. Agents cannot see pages in this
increment; widening later is additive.

```
POST   /api/v1/pages                          create                        201
GET    /api/v1/pages?project=…                the tree                      200
GET    /api/v1/pages/{id}                     one page + blocks             200
PATCH  /api/v1/pages/{id}                     title, or a move              200
DELETE /api/v1/pages/{id}                     soft delete, subtree          204
POST   /api/v1/pages/{id}/restore             undelete, subtree             200
POST   /api/v1/pages/trash/empty              purge, real cascade           200
POST   /api/v1/pages/{id}/blocks              insert a block                201
PATCH  /api/v1/pages/{id}/blocks/{block_id}   update a block                200
POST   /api/v1/pages/{id}/blocks/{block_id}/move                            200
DELETE /api/v1/pages/{id}/blocks/{block_id}   delete a block                204
```

**The four page block routes are not optional and their absence was a defect in
the first draft**, which claimed block editing "reuses the four existing block
verbs, addressed by block id". It does not: the only block routes are
`/documents/{id}/blocks…` (`routes/documents.py:1005-1076`), each running
`_assert_block_is_in`, which 404s a page block by construction; and
`insert_block` takes an owner id, not a block id (`block_verbs.py:331-333`).
Without page block routes, Increment A ends with a page that is a titled empty
row. The page routes get a page-flavoured `_assert_block_is_in` reading
`page_id`.

**Creating a page with content.** `POST /pages` takes an optional `content`
string, parsed to blocks atomically inside the create transaction, with
`content` then **regenerated by the serialiser** so the stored source is always
the serialiser's own output and no conversion is ever owed. This is what keeps
"block-first by construction" true of the product and not only of the schema:
without it, the first implementer writes `content` straight onto the row and
recreates content-first state on an object with no conversion path.
`MAX_BLOCKS` applies, checked inside the same savepoint as `put_document` does.

**Moves take `after_id`, never a raw index.** `PATCH` accepts `parent_id` plus
`after_id` (null = first), mirroring `move_block`'s existing `after_block_id`.
The server renumbers the old and new sibling sets in one
`UPDATE … FROM unnest(…)`. Taking a raw `order_index` would ship a contract
Increment B has to break the moment it implements drag-to-reorder.

**`order_index` semantics:** dense, 0-based, per `(project, parent_id)`,
server-assigned, **no UNIQUE constraint** — renumbering under one would need a
two-pass. `POST` appends at `max+1` under a row lock on the parent (or an
advisory lock on `(project, parent_id)` for roots), or two browser tabs mint the
same index. Sibling counts for personal notes are small enough that dense
renumbering costs nothing; fractional indexes are a later optimisation, as the
epic already says of blocks.

**`GET /pages` returns flat rows** — `SELECT … WHERE project = :p AND deleted_at
IS NULL ORDER BY parent_id, order_index`, **excluding `content`** — and the
client nests them. O(pages in project), no pagination: a personal tree does not
need it.

**Cycles are prevented under a lock, not a bare walk.** Two concurrent PATCHes
(A under B, B under A) would each walk ancestors against the committed tree,
both pass, both commit, and the subtree is orphaned from every root. Invariant
13's single worker does not help — the requests interleave across awaits. The
move takes `SELECT … FOR UPDATE` on the moved page and the new parent's
ancestor chain before walking.

**Title edits are last-writer-wins.** Block edits are covered by
`expected_hash`; `PATCH` on title is not, and for a single operator that is
accepted rather than overlooked.

**Permissions: none beyond ordinary auth.** Single operator, no MCP reach. Stated
so it is a decision rather than an omission.

**Three enumeration guards must move with these routes**, and the first draft
wrongly said none would. `tests/test_door_parity.py:1559-1573` fails on any REST
route lacking a `PARITY_TABLE` row, so **eleven `REST_ONLY` rows with their
≥80-character reasons are required** — "no two-door-parity row" was impossible.
Each route also needs an entry in `content_surfaces.ROUTES_WITHOUT_MEMORY_CONTENT`
(`content_surfaces.py:603`, guarded by `test_content_surface_scoping.py:116`) and
in `EXPECTED_STATUS` (`test_api/test_rest_conformance.py:317-339`). CLAUDE.md
names this exact shape as what left the 2026-09-07 branch red for eight tasks.

## 8. Journalling

Taxonomy-first: the values land in the vocabulary before their emitters ship.

- `OBJECT_TYPES` gains `"page"` (it holds ten values today, `"document"` among
  them).
- `EVENT_TYPES` gains `page_created`, `page_updated`, `page_moved`,
  `page_deleted`, `page_restored`, `page_purged`.
- **`blocks_edited` is reused**, once `object_type` moves onto `BlockOwner`
  (§6). Its payload names the verb, the block id and the resulting
  `content_hash`, and carries no block text.

Page events carry no page text, matching the write-time minimization rule the
events section states.

**A subtree delete journals one row per page, before the write, and refuses when
a row does not land** — the strict-journal contract `delete_documents` already
holds (`document_door.py:955-979`). So the delete enumerates the subtree first
rather than relying on a cascade to imply it.

## 9. Delete is a soft delete

`deleted_at` is stamped over the page and its whole subtree in one recursive
`UPDATE`. Deleted pages are filtered from `GET /pages`, from the keyed read, and
from every block route. `POST /pages/{id}/restore` clears the stamp over the same
subtree. `POST /pages/trash/empty` runs the real `DELETE`, which cascades through
`fk_pages_parent` and takes the blocks and their vectors with it.

**This reverses the first draft's cascade, on the argument in §1's last table
row.** A document's source of truth is the file or the agent that filed it, so an
erased document can be re-filed. A page's only copy is the row. The analogy to
`document_delete_subtree` fails on exactly that point. The cost is one column, a
filter on the read paths, and two routes; there is no new job — the 24-job roster
is unchanged — and blocks and vectors simply persist until purge.

Worth stating beside it: `document_revisions` exists in the baseline
(`0001_baseline.py:1397`) and nothing writes it. A page therefore has trash but
no undo and no version history.

**The confirm carries a count.** `DELETE` answers 204 with no body, so the count
comes from the subtree the client already holds — the tree is a single loaded
structure, so no pre-count round trip is needed.

## 10. Out of scope, and why

- **MCP tools for pages.** Deliberate: notes are a human surface first. Additive
  later.
- **Wiki-links from pages.** `document_links` keeps pointing at `documents(id)`.
  Noted rather than assumed: that table's own comment reads "`[[a-page]]`
  pointing at a note that does not exist yet is a first-class stub", so the
  schema anticipates page links. Scoped out as YAGNI, not rejected; when wanted,
  `target_page_id` beside `target_document_id` is the same nullable-owner shape
  §3 chose.
- **Tags on pages.** `page_tags` would mirror `document_tags` in four lines.
  Nothing in the core model needs it.
- **Page search and retrieval ranking.** Pages are not fused into
  `HybridSearchService` or `LayerCompositionService`. The block channel's
  firewall from the fact vault is unchanged and verified: a page module joining
  `BLOCK_CHANNEL_MODULES` is bound by the same four-method read allowlist
  (`test_block_retrieval.py:524-536`), `VAULT_WRITERS` closures gain no import,
  and `LAYER_BY_ID_KIND` gains no `page` kind.
- **Version history / undo.** See §9.

**One catalogue gap, closed by adding `pages` to the union.**
`GET /api/v1/projects` unions `memories`, `documents` and `session_checkpoints`
(`routes/projects.py:42-58`), so a project holding only pages would be invisible
to it. The alternative — declaring pages personal-only — was rejected because
`pages.project` is already a general column that nothing constrains to the
personal space, so that reading would be a rule enforced nowhere, and a project
that vanishes from its own catalogue is a bug under either reading.
`ProjectSummary` gains `page_count` beside `document_count`, which the
`/notes` project picker in Increment B then has a real field to sort on.

## 11. Increments

**Increment A — backend, no UI.** The `pages` table; the `blocks` ownership
change and its CHECK, with both existing indexes retained; the `page_embeddings`
partition family and the scoped `block_embedding_refresh`; the `BlockOwner` fork
including `object_type`; all eleven REST routes with their parity, content-surface
and conformance rows; `page` in `OBJECT_TYPES` and the six page events; the
locked cycle guard; §5's isolation test. Ends with the backend suite green and
`/documents` provably unchanged.

**Increment B — the workspace.** Repoint `/notes` to pages, split
`project-workspace.tsx`, retire `treeManagement`, and build the one genuinely new
interaction: drag to reorder siblings, which is what `order_index` exists for and
which the current drag layer does not do — it only reparents.

A carries the risk and the isolation requirement; B is UI over a settled
contract. Splitting there means the guarantee is proven and merged before any UI
depends on it. A is exercisable end to end in pytest **because** the page block
routes are in it — without them it would not be a shippable unit.

### What increment 2's merged work costs

`/notes` was built on `documents` and merged on 2026-09-08 as `c0f39b26`. Its
data layer repoints:

| File | Lines | Fate |
|---|---|---|
| `document-tree.tsx` | 560 | Survives; its tree-building moves out, since the page API returns a real tree |
| `note-tree-actions.tsx` | 96 | Survives — already generic over a node |
| `project-workspace.tsx` | 1005 | Splits: the document half stays for `/documents`, the notes half becomes its own component |
| `move-target.ts` | 52 | Rewritten and simplified — a page move is `(parent_id, after_id)`, so the string-prefix descendant checks and `NO_PATH` orphan guards go |
| `uri-tree.ts` | 91 | Mostly retired |
| `notes.tsx` | 56 | Survives, repointed |

**The `treeManagement` prop retires.** It exists to make one component serve two
purposes; with two objects there are honestly two components, and the flag was
the seam between them. The interaction design it proved carries over; the flag
and its guard do not.

## 12. Schema freeze

`pages`, the `blocks` change and the `page_embeddings` template regenerate
`0001_baseline.py` in place — greenfield, the freeze has not happened, so no
migration and no data preservation is owed. Every deployed database drops and
recreates, and `admin_password_hash` plus the eight `llm_purpose_configs` rows
are re-seeded per `docs/runbook-deployment.md`. `schema_guard` refuses to start
on a stamp mismatch, so the recreate is enforced rather than trusted.

## Appendix: rejected approaches, kept for the record

**B — polymorphic `owner_kind` / `owner_id` with delete triggers.** Follows the
`events.object_type` precedent, but that precedent is weak on its own terms:
events rows are disposable, append-only audit entries with no cascade
obligation, where a wrong value degrades a timeline query. `blocks` rows are
live, embedded and cascaded. B loses insert-time referential integrity
permanently, rewrites every block SQL statement, and its silent failure is a
query returning zero rows rather than erroring — nothing type-checks a raw SQL
string's WHERE clause.

**C — a `content_owners` supertype.** Buys the cleanest `blocks` table: one
column, one FK, one cascade. Rejected on three counts. Its atomicity story is
false — it describes create and update branches of the document filing, but
`repositories/documents.py:97-114` is a single
`INSERT ... ON CONFLICT (project, uri) WHERE uri IS NOT NULL DO UPDATE ...
RETURNING id`, so the supertype row orphans on the conflict branch unless the
upsert is restructured into the check-then-act shape a previous review removed.
It alters `documents`, which this work must not. And its delete root moves to a
table nothing calls directly, making the wrong-direction delete silent.

**On a hypothetical third owner kind: near-zero weight.** Two kinds exist and no
third is planned; the greenfield rule makes the schema half of any future
addition a regenerated baseline rather than a migration; and the part that
actually costs — the verb fork, a new door, new `OBJECT_TYPES` values, new
`BLOCK_CHANNEL_MODULES` entries — is identical under all three designs.

## Appendix: what the adversarial review changed

The first draft was reviewed at Fable and returned **not sound**. Recorded
because several of these are defects a reader would otherwise re-derive:

1. **Pages could not hold a block** — §7's four page block routes did not exist,
   and the claim that the document block routes could serve them was false.
2. **The isolation accounting counted SQL statements**, missing the shared HNSW
   partition (§4), the owner-less `block_embedding_refresh` sweep (§4), and the
   per-row cost of the cross-owner trigger (§3).
3. **The cross-owner trigger guarded a state no writer can produce**, at a
   measurable cost to the document path it promised not to slow.
4. **`object_type="document"` is hardcoded** in `_mutate` and was not among the
   six constants the fork enumerated.
5. **The `blocks` DDL silently dropped `ix_blocks_parent` and the GIN index.**
6. **Three enumeration guards were said not to apply**; all three do.
7. **The cycle walk was check-then-act**, racing two concurrent moves into an
   orphaned subtree.
8. **`content`/`content_hash` were prose-required and DDL-nullable.**
9. **No path existed for content to enter a page**, so "block-first from birth"
   was true of the schema and false of the product.
10. **Root ordering was unscoped by project** and a cross-project reparent was
    permitted.
11. **Cascade delete was wrong for hand-authored notes** — replaced by §9's soft
    delete.
