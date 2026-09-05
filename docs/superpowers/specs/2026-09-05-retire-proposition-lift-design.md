# Retiring proposition lifting — documents are embedded, never extracted

**Owner ruling, 2026-09-05.** Documents stay out of the extraction pipeline.
Filing parses a document into blocks and embeds them; that is the whole
pipeline. Doc 16 §5's vault bridge — block → proposition memory → L1 graph →
L2 fact — is **retired, not deferred**, and the block firewall becomes
absolute: after this change there is no route from a block to a fact.

Revision 2, after an adversarial review (Fable, xhigh) that verdicted revision 1
*do not execute as written*. The findings that survived are folded in and named
where they changed a decision, because three of them changed the design rather
than the prose.

## 1. What the measurement found

The lift shipped behind a pricing script (§6.3 of the artifacts spec) that
refuses a full corpus run until a sample has been read. The sample ran on
**2026-09-04** and was killed by `earlyoom` after 7 of 20 documents — not a
failure, and the state was what the script promised: a smaller corpus, not a
broken one. Seven documents were enough to settle the question.

| | Measured (7 documents) |
|---|---|
| Propositions minted | 2,058 |
| Non-empty blocks consumed | 949 |
| Propositions per block | 2.17 |
| Extraction calls | 3,097 (949 lift + ~2,058 pipeline) |
| Spend | $0.720 |
| Entities | 149 → 1,483 |

The spend was never the problem. **The corpus was.** darkmem held 50 memories;
seven documents added 2,058. Recomputed on the real cost driver — 47,811
non-empty blocks corpus-wide, not 475 documents — the full run lands at
**~104,000 memories and ~152,000 calls**, a two-thousand-fold expansion in
which every hand-captured memory is outnumbered by machine-extracted
propositions from the project's own documentation.

§6.3 framed this as "the largest single LLM expenditure this project has
proposed" and priced it in calls and tokens. That framing was wrong in a way
only the sample could expose: the spend is trivial and the product consequence
is enormous, and a cost number was never going to surface it.

### 1.1 The granularity defect

The LLM call unit is one block, and most blocks are too small to hold a
proposition. Corpus-wide: 6,556 headings averaging 42 characters, 824 table
stubs at 37, 15,414 list items at 174. Each gets its own extraction call with
no surrounding document context, and the prompt still demands "one standalone
assertion". Real rows the sample minted:

- `The lower-effort path is to drop it.` — drop *what*?
- `It contains pipeline-maintenance panels: Reprocess-All, …` — *what* contains?
- `Low | validate_local_path home-subpath check has a Windows gap | repo_manager.py:39-71` — a table row echoed verbatim.

101 of the sample's propositions came from *heading* blocks: headings restated
as claims. At 2.17 propositions per 300-character paragraph the lift is
transcription rather than distillation — one memory per 67 characters of
source.

This is not a prompt-tuning problem. A block-scoped extractor cannot resolve a
referent that lives in a sibling block, and widening the window to the document
makes it an ordinary summariser, which doc 09 already owns properly with
grounding and a ladder.

**One inference drawn from this finding turned out not to generalise, and it is
corrected in §3.3** — "short blocks carry no claim" holds for the audit
documents measured here and is false for the planning documents, where terse
checklist items are the claim statements.

### 1.2 The bridge was half-built anyway

`block_fact_sources.record_block_source` — the function that stamps
`origin_key = document_id`, which is doc 16 §5's entire "one document is one
origin" corroboration rule — **has never had a production caller**. Only the
withdrawal halves are wired, into `block_verbs` and `document_door`. Prod
`fact_sources` holds 100 rows, every one `source_kind='memory'`, so no
block-kind row has ever existed.

Every one of the 2,058 lifted rows carried `origin_key = NULL`, folding into
the anonymous bucket that counts once and fires no gate. That was safe — the
lift could not fabricate corroboration — but it means the rows were pure
retrieval noise, and the capability doc 16 §5 designed the lift *for* was never
reachable. Retiring the lift gives up nothing that worked.

## 2. Rulings this spec reverses

Stated under its own heading, because a reversal buried in a rationale is how a
recorded decision gets lost.

**The artifacts spec §8 lists "A similarity score" under *What NOT to build*,
pointing at §6.2. This spec reverses that, on the owner's ruling of
2026-09-05.** §6.2's argument was that shared-entity *count* is evidence and
must not be normalised into a similarity number, "the rule
`document_connections.py` already states for itself". That argument was right
about what it addressed: manufacturing a pseudo-metric out of count evidence
asserts a precision nobody measured.

It does not reach a cosine between two stored vectors. That is the same number
`document_search` already returns and that `docs/two-door-parity.md` already
describes as returning "its own text with a cosine score". The prohibition was
against inventing a score, not against serving one the system already computes.

**What the reversal genuinely costs, stated rather than argued away.** The
review measured the score distribution across all 475 documents and it is
continuous — p50 0.503, p90 0.612, p95 0.662, p99 0.750, with no seam anywhere.
A cosine on this surface is therefore an **ordering key and not a calibrated
relevance measurement**, and a UI that renders it as a percentage or a
confidence badge would commit exactly the error §6.2 was protecting against, one
layer further down. §3.4 binds the presentation accordingly.

`test_document_related.py:184-213` pins the no-score rule in two tests. They are
rewritten deliberately as part of this change, never deleted quietly.

## 3. What replaces relatedness

`GET /api/v1/documents/{id}/related-memories` survives and changes its basis.
Today it walks document → lifted propositions → shared entities → other
memories, which has no basis once nothing is lifted.

**New basis: cosine between the document's block vectors and the project's
memory vectors.** Both sides already live under one fingerprint, so this is a
same-fingerprint join across two child tables — no cross-fingerprint
comparison, no new table, and **zero LLM calls**, at query time or ever.

### 3.1 Aggregation: max, not mean

One row per candidate memory, scored by the **maximum** cosine across the
document's blocks. A large document is heterogeneous; a mean dilutes every real
match into noise, and the memory that matches one paragraph perfectly ranks
below one that is vaguely near everything.

Max also yields the matching block for free. The response returns that block's
id, text and `char_span` alongside the memory. That passage — not the number —
is the evidence, which is what §2's reversal obliges.

### 3.2 Query shape: one scan, and the cost model is stated honestly

**Scope note, post-implementation (2026-09-05): this section is `document_related`'s
(blocks vs. the project's memory vectors) and its exact-scan conclusion held.
This section's own measurement, below, is the pre-implementation figure: 78 ms
on the same 1,132-block-vs-50-memory case this design specced. The shipped
statement's own docstring (`document_related.py:32`) re-measured the identical
case at 89 ms — the two are the same query at the same size, just measured at
different points (design-time estimate vs. shipped, three-run measurement);
neither supersedes the other, and no correction to this section's exact-scan
conclusion is needed. `document_connections` (blocks vs. other documents'
blocks) is a different, quadratic case and does *not* share this section's
exact-scan shape; §4's own correction covers what shipped there and the
mismeasurement that preceded it.**

Revision 1 specified a `LATERAL` ANN probe per block and claimed it "uses the
HNSW index once per block rather than computing a full cross product". **The
review refuted that.** Built at 20,000 vectors, the planner with the project
join picks `Seq Scan` + hash join, not the index; forced onto the index it
becomes a nested loop with the project predicate applied *after* the scan — the
post-scan filter `block_embeddings.py:275-283` warns about and compensates for
with `SEMANTIC_FETCH_MULTIPLIER`, which revision 1's shape had no equivalent of.

So the shape is the one the planner was going to choose anyway: **a single
statement joining the document's block vectors against the project's memory
vectors, max-aggregated per memory, ordered, limited.** No `LATERAL`, no
per-block `k`, no probe cap. Measured on prod against the corpus's largest
document (`E2-truth-core.md`, 1,132 non-empty blocks × 50 memories = 56,600
distance computations): **78 ms**, plan is a hash join over two sequential
scans.

**The honest cost model: this is O(document blocks × project memories) and uses
no index.** It is correct at any size and fast at this one. The threshold at
which it needs restructuring is the project's memory count, not its document
count — at ~50 memories a 1,132-block document costs 78 ms; at 10,000 memories
the same document would cost roughly 200× that and the surface would need an
over-fetching ANN probe with the `SEMANTIC_FETCH_MULTIPLIER` discipline.

Worth stating because it is load-bearing rather than lucky: **the owner's
ruling is what keeps this shape viable.** A corpus that does not absorb 104,000
machine-extracted propositions is a corpus small enough to scan. The retirement
in §1 and the query shape here are the same decision seen twice.

Scoping stays in SQL, for the reason `search_blocks` and
`connections_for_document` both state. Candidate memories are filtered to the
document's own project inside the statement, never on the returned page: a
Python-side filter lets another project's rows consume the `LIMIT` and then be
discarded, silently under-filling a surface whose purpose is to show rows the
reader had not thought of — and a cross-project result breaches the isolation
boundary doc 18 §8 calls a security one.

### 3.3 No floor: top-N, with the score and the passage shown

Revision 1 set `MIN_SCORE = 0.70` and called it "measured, not chosen". **The
review established that it was a fit to one document.** The exact cross product
over all 475 documents × 20 in-project memories shows a continuous distribution
with no gap near 0.70. At that floor:

- 325 of 475 documents (68%) would render "nothing relates to this";
- the median document would get zero rows;
- **both error types straddle the floor.** Above it, 0.724 pairs the
  supersession memory with the 28-character list item "No dangling
  `superseded_by`." — noise. Below it, 0.673 and 0.683 pair the events-table
  memory with two blocks making *the same claim* — true positives excluded.

There is also a structural bias a floor cannot fix: a max over N blocks is an
**order statistic**, so the share of documents with any hit rises monotonically
with document size (11% under 25 blocks, 62% over 200; mean best score 0.610 →
0.741). A fixed floor therefore encodes "long documents are more related",
which is not a claim anyone wants to make.

**So there is no floor.** The surface returns the top N matches with the score
and the matching passage shown, and the reader judges. This makes no precision
claim the data cannot support, which is the only honest option under a
continuous distribution. The cost is that the surface can no longer say
"nothing relates to this" — it says "here are the nearest, and here is how near"
— and §3.5's envelope carries the states it still can distinguish.

Establishing a real floor later is a measurement task, not a tuning one: a
stratified labelled sample of roughly 60 argmax pairs across 0.55–0.85 from 20+
documents, **labelled by someone other than the design's author**, with the
floor chosen to a stated precision target and re-measured once the memory
corpus exceeds 20 rows per project. Until that exists, no number goes in.

**The probe cap is dropped with the floor.** Revision 1 capped at 200 blocks
ordered by text length descending, reasoning from §1.1 that short blocks carry
no claim. The review showed that inference does not transfer: over the 63
over-cap documents the cap loses 14 of 276 clearing pairs, and they are the
*best* matches on the largest documents — `E1-engine-core.md` drops 0.843 → 0.505
because its argmax was a 131-character checklist item ranked 464th of 1,083 by
length. On planning documents the terse checklist items and headings are the
claim statements, and they have exactly the shape a memory row has. With the
scan shape measured at 78 ms on the 1,132-block worst case, the cap bought
nothing and cost the best rows on the documents that most needed them.

### 3.4 Presentation is constrained by the reversal

Because §2 lifts a prohibition rather than sidestepping it, the constraint moves
into the UI and is specified here rather than left to taste:

- The **passage is the evidence**; the score is an ordering key. The matching
  block's text is rendered, not summarised.
- The score is shown as a raw cosine to three decimals, **never as a
  percentage, a bar, a badge or a word like "strong"**. The distribution in
  §3.3 does not license any of those.
- No prose is generated about what the document and the memory share. That
  remains unbadged synthesis and remains doc 09's, with grounding and a ladder —
  `test_document_related.py`'s no-model-call scan survives this change unchanged.

### 3.5 The envelope's states, and the fingerprint

Revision 1 renamed `lifted: bool` to `embedded: bool`. The review found that
insufficient: after an embedder rotation, a document's blocks can be embedded
under fingerprint F while the project's memories are not yet — blocks re-embed
through the hourly `block_embedding_refresh`, memories through the `reembed`
POST. `embedded=True, items=[]` would then render "nothing relates" when the
truth is "no memory is comparable yet", the exact confusion the field exists to
prevent.

**The fingerprint is derived from the data, never resolved through the
embedder.** `resolve_active_fingerprint` is a real embed call per request —
a network call the existing `test_document_related.py:176-182` pin forbids by
name, and one that would oblige `refuse_when_read_only` on the route, which is
why document search is refused on the backup worker. `resolve_read_fingerprint`
is a data probe biased toward a stale populated partition after a rotation, so
the panel would serve old-embedder rows while search serves the active one.

Instead: pick the **newest fingerprint in which both this document's blocks and
this project's memories have vectors**. Zero calls, no staleness bias in the
harmful direction, and it degrades correctly — during a rotation the panel
serves the old fingerprint's comparison until both sides finish re-embedding,
which is right, because a cosine across fingerprints has no defined value.

The envelope therefore carries `comparable_memories: int` beside the items, and
the surface distinguishes:

| State | Meaning |
|---|---|
| document has no blocks | nothing to compare from |
| no shared fingerprint | blocks or memories not embedded yet; self-resolving |
| `comparable_memories = 0` | the project holds no comparable memory |
| `comparable_memories > 0`, items returned | the nearest N, with scores |

### 3.6 Firewall classification

`document_related` starts reading block rows and block vectors, so it **joins
`BLOCK_CHANNEL_MODULES` in this same change**. That set's own comment states the
rule: a module is classified in the task that creates it, because an
unclassified module is a hole in the scan and that is this codebase's named
characteristic defect.

The review verified the classification mechanically rather than accepting the
prose: it walked all nine `VAULT_WRITERS` closures with the test's own
`import_closure` and none reaches `document_related`, `document_connections`,
`routes.documents`, `block_embeddings` or `block_query`. The promoting-method
scan forbids the repository's 11 public methods minus 5 allowlisted, none of
which a cosine read names. The fusion scan inspects only the four fusion
modules' imports. The classification holds.

**Stated without softening:** this is blocks ranking memories, on a surface
outside the composition, with a similarity score. It is not blocks entering
ranking (the composition still refuses a block candidate outright, and `block`
is still absent from its channel and id-kind registries) and it is not blocks
reaching the vault (nothing here mints a fact or names a ladder method). The
firewall's two real concerns are untouched; a third thing that merely resembles
them is now permitted, on §2's ruling.

**The pin must be structural, not behavioural** — a test asserting today's
results contain no block cannot pin "cannot". So: nothing under `app/services`
imports `document_related`, and no fusion module does, asserted over the import
graph.

## 4. `document_connections` moves to the same basis

The review found that `document_connections.py:33` imports `PROVENANCE_KEY`
from `proposition_lift`, so deleting that module fails the app at import — and
that patching the import is not enough, because the feature walks document →
lifted propositions → entities → documents and is permanently empty with
nothing lifted. It is committed by doc 16 §6 and rendered in two frontend
places, captioned "Emergent from shared entities after lifting".

**Owner ruling 2026-09-05: re-base it on cosine, alongside related-memories.**
Document-to-document over `block_embeddings` alone — a **same-table** join,
which is both simpler and better-indexed than §3.2's cross-table one, since a
single ANN probe per block against the same partition is the shape
`search_blocks` already serves.

Everything §3 decides applies here for the same reasons: max-aggregation, no
floor, top-N with the matching passage pair shown, the fingerprint derived from
data, and scoping to the document's own project in SQL. The caption changes —
"emergent from shared entities after lifting" describes a mechanism that will
not exist.

**Correction, post-implementation (2026-09-05): the shape above is not what
shipped.** "A same-table join... the shape `search_blocks` already serves"
described an **exact** self-join — both sides scanned in full, the same shape
§3.2 uses for `document_related`, which is safe there only because one side
(the project's memory vectors) is small. Here *both* sides are the same
`block_embeddings__<slug>` partition, so both scale with block count, and the
join is quadratic rather than linear. Implemented as written, it measured
**166,526 ms** (166.5 s) on the live database for the corpus's largest filed
document (`E2-truth-core.md`, 1,132 non-empty blocks) — three orders of
magnitude past `document_related`'s cost on the same document. The exact
self-join **was committed to the branch and measured live** (`document_connections.py`'s
own docstring says so: "was shipped first and measured on the live corpus at
166.5s"), then replaced before the branch merged to master — "shipping" there
means landing on the implementation branch this measurement forced a
correction on, not reaching production. `backend/app/services/document_connections.py`
was rewritten to probe instead of join: a `LATERAL` **ANN probe per block**
(`ORDER BY t.embedding <=> m.embedding LIMIT 10`, using the HNSW index rather
than defeating it by ordering on the derived `score`), excluding the queried
document's own blocks, max-aggregated by document exactly as §3.1 specifies,
and with **no block cap** for the same reason §3.3 drops the cap on
`document_related` — an earlier per-document probe cap ordered by block count
was measured to drop the *best* cross-document match on the documents that
most needed it (one case moved 0.843 → 0.505). This surface is therefore
approximate (an ANN probe can miss the true nearest block) where
`document_related` stays exact, the same trade `search_blocks` already made
for the block channel.

**A second correction belongs beside the first: the numbers this section
implies for that probe were themselves mismeasured at first, on a basis
error rather than a code error.** An initial pass measured this replacement
statement at 494 ms typical / 3,436 ms (3.4 s) worst case, and the gap
between that and a wider `ef_search` was read as evidence the tuning was not
helping. That reading was wrong: those numbers were taken in a plain `psql`
session, where `SHOW hnsw.ef_search` **errors** rather than reporting a
value, because pgvector 0.8.2 registers its HNSW GUCs lazily — a session that
never issues the app's `SET`s silently runs at pgvector's own defaults
(`ef_search=40`, `iterative_scan` off) rather than the tuned ones, and a bare
`psql` session issues no such `SET`. `app/database.py:23-24` sets
`hnsw.ef_search = 100` and `hnsw.iterative_scan = 'relaxed_order'` on every
*application* connection, so 494 ms / 3,436 ms was never this surface's
number — it measured the untuned default, not the shipped configuration.
Re-measured under the app's real settings, two different queries produced two
different pairs of numbers, and both belong in the record because a later
docstring correction (`document_connections.py`) conflated them: a **narrower
query** projecting only ids and score (not the full block-pair evidence the
shipped statement returns) measured **785 ms typical / 2,085 ms worst**; the
**statement actually shipped**, which does return the full evidence, measures
**320–623 ms typical / 2,739–3,964 ms worst**. The narrower projection is not
a second measurement of the shipped surface's own cost — it is a comparison
of what a lighter projection would cost, and it measures faster than the
shipped statement only on the large (1,132-block) document; on the small
(282-block) one it is in fact *slower* (785 ms vs. 320–623 ms), a difference
within noise at that size rather than a real saving. Neither pair is the
494 ms / 3,436 ms figure, and neither should be read as superseding the
other — they are different queries under the same, correctly-tuned settings.

## 5. What is removed

The review found revision 1's inventory incomplete in three directions, and an
incomplete inventory here is the implementer's defect rather than the gate's.

**Backend:**

| Removed | Note |
|---|---|
| `app/services/proposition_lift.py` | The lift |
| `POST /api/v1/documents/{id}/lift` | Its only door — no MCP twin |
| `scripts/bulk_lift_documents.py` | Prices a run that will never happen |
| `app/services/block_fact_sources.py` | No production caller; prod has zero block-kind `fact_sources` rows |
| Withdrawal call sites in `block_verbs.py`, `document_door.py` | Nothing attaches, so nothing withdraws |
| `tests/test_proposition_lift.py`, `test_document_lift_door.py`, `test_lift_idempotence.py`, `test_block_fact_sources.py` | Subjects gone |

**Backend references that must be updated, not just deleted:**

- `app/services/document_connections.py:33` — the import that breaks the boot (§4).
- `app/services/content_surfaces.py:647` — the lift route in
  `ROUTES_WITHOUT_MEMORY_CONTENT`; `test_content_surface_scoping.py:116-125`
  asserts `classified - live == set()`.
- `app/services/content_surfaces.py:164-181` — `document_related_memories`'
  reason cites "spec 2026-09-03 §6.2" and the `_PROJECT_SQL` argument; both
  change.
- `app/services/document_door.py:642` — `expire_facts_left_bare` loses its only
  callers.
- `app/repositories/fact_sources.py:124-141` — `BLOCK_SOURCE_KIND` stays in
  `SOURCE_KINDS` under a comment saying its producer shipped. **Decide
  explicitly: reserved or dropped.**
- `tests/test_document_door.py:8,455-520`, `tests/test_document_routes.py:748-750`
  — call `record_block_source`.
- `tests/test_prompt_hardening.py:117-123` — imports `proposition_lift`.
- `tests/test_door_parity.py:304-322` (`documents.lift`) and `:285-302`.
- `tests/test_api/test_rest_conformance.py:66`.
- `docs/two-door-parity.md:13` — **"78 surfaces: 24 two-door, 54 single-door
  (47 REST-only, 7 MCP-only)" becomes 77 / 24 / 53 / 46 / 7**, asserted verbatim
  at `test_door_parity.py:1985-2005`. `documents.related_memories` also needs a
  rewritten single-door reason; whether a cosine-scored read stays REST-only is
  an owner decision by that document's own rule.

**Benchlib — the gate's harness leg, which plain `pytest -q` does not collect:**

- `scripts/benchlib/isolation_probe.py:470` imports `PROVENANCE_KEY` inside
  `_seed`, so every probe run fails at seeding; `:541-570` seeds a "lifted"
  memory sharing `redis` across projects; `:1223-1257` drives the surface on
  that fixture.
- `scripts/benchlib/tests/test_isolation_probe.py:600-636` monkeypatches
  `document_related._RELATED_SQL` by string-replacing the literal
  `"WHERE m.project = :project"`.
- **The fixture must be redesigned, not ported.** The probe seeds zero block
  embeddings and its stub embedder is `_hash_vector(text)`, so proving the
  cross-project leak needs a designed block in the observer project whose vector
  ranks a foreign memory — otherwise the predicate-mutation test passes
  vacuously, which is worse than deleting it.

**Frontend — absent from revision 1 entirely, and it would have shipped broken:**

- `hooks/api/use-documents-api.ts:275-297` — `useRelatedMemories` typed
  `{items, lifted}`, `useDocumentLift` POSTing to the deleted route.
- `hooks/api/use-documents-api.ts:259-266` — the `RelatedMemory` interface.
- `document-actions.tsx:220-262` — `!related.data?.lifted` renders "not been
  lifted" forever once the field is gone, with a Lift button that 404s, and maps
  `shared_entities`.
- `document-actions.tsx:172-187` and `documents-view.tsx:233-247` — the
  connections panel and its "after lifting" caption (§4).
- `lib/query-keys.ts:114-130`.

`fact_lift.py` and `test_deriver_lift.py` **stay** — different lifts
(graph → vault, and doc 10 §6's repository assertions), unrelated to documents.

Deleting `block_fact_sources` also removes the special-case entry in
`test_block_retrieval.py`'s vault scan, which costs three paragraphs of
justification today. The forbidden set becomes the complement with no exception:
strictly stronger, and shorter to read. Two shapes go stale with it and must be
corrected rather than left: `document_door.delete_document` keeps its "withdraws
provenance before removing the row" shape with nothing to withdraw, and
CLAUDE.md's paragraph of that name plus `content_surfaces.py:654-660` both
describe a delete that expires facts.

### 5.1 Production state

Rolled back on 2026-09-05 **before any code change**, so the tool that performs
the rollback still existed when it was needed. `strip_document_lift` across the
7 lifted documents removed all 2,058 rows through the ordinary `delete_memory`
path; `prune_orphan_entities` then reclaimed 1,334 entities and 357 relations.

Verified after: **50 memories, 149 entities, 98 relations**, zero rows carrying
`document_provenance` — the pre-lift state exactly.

## 6. Documents to amend

Amended rather than deleted — the reasoning in each is still why the resulting
shape is what it is. Revision 1 listed only doc 16 §4 and §5; the review found
four more.

- **doc 16 §5** — retired. Its "on demand, never automatic" argument survives as
  the reason documents are not extracted *at all*.
- **doc 16 §4** and **`block_query.py:9-14`** — both say document content reaches
  the composition "only as lifted facts (§5)". It now reaches it not at all.
- **doc 16 §6** — commits to connections as an entity-derived surface (§4).
- **doc 01 §159** — "the differentiator is proposition ingestion… why the horizon
  is designed in from the start".
- **doc 05 line 29** and **doc 20 H1** — both state the lift.
- **CHANGELOG.md:911**.
- **CLAUDE.md, Documents section** — "doc 16 §5's lift is left as the only route
  from a block to a fact", the `block_fact_sources` exception it justifies, and
  the delete-withdraws-provenance paragraph.
- **`docs/two-door-parity.md`** — the `documents.lift` row, the corrected
  headline counts, and the `documents.write` / `documents.retrieval` rows, which
  quote the lift as the sole block-to-fact route.
- **The artifacts spec §6.1–6.3, §8, §9** — the lift door, both surfaces' basis,
  the pricing script, the *What NOT to build* entry (§2), and §9's testing list.

## 7. Testing

- `test_document_related.py` rewritten: max-aggregation ordering, project
  scoping in SQL, the four-state envelope, the returned block provenance, the
  no-model-call scan retained, and the two no-score pins rewritten per §2.
- `test_document_connections.py` rewritten to the cosine basis (§4).
- `test_block_retrieval.py` gains `document_related` and `document_connections`
  in `BLOCK_CHANNEL_MODULES`, plus §3.6's structural pin.
- The benchlib isolation-probe fixture redesigned per §5, with an assertion that
  the cross-project case is non-vacuous.
- `test_door_parity.py`'s headline counts to 77 / 24 / 53 / 46 / 7.
- Frontend: the four-state panel per artifacts §9 — a failed read must never
  render as an empty one.
- **The full gate is required.** Dropping a route trips the enumeration guards
  and the benchlib leg, neither of which plain `pytest -q` collects.
- Redeploy after merge, per the standing ruling: this alters `backend/` and
  `frontend/`, so the image is rebuilt and the change confirmed in it.

## 8. Adjacent defect, not fixed here

`MemoryService.delete_memory` journals `event_type="delete"`
(`app/services/memory.py:393`, through `AuditRepository.log` at
`app/repositories/relational.py:285`), which is absent from `EVENT_TYPES`. Every
memory deletion — the UI, the TTL sweep, MCP `memory_delete` — logs `outside the
doc 04 §8.1 closed vocabulary`. The rows do land (2,058 arrived during the
rollback), so nothing is lost; it is a vocabulary-completeness gap against
CLAUDE.md's own taxonomy-first rule, which says the value lands in the
vocabulary before its emitter ships. This emitter shipped without it.

Recorded here because it was found here. It is not part of this change.
