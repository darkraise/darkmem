# Document door and section search — design

Date: 2026-08-23
Status: proposed
Horizon: EH1 (documents/blocks), doc 16

## Problem

Coding agents (Claude Code and friends, under the superpowers plugin) hold
their durable artefacts as markdown files: requirements, designs, specs,
plans, and an execution ledger. Two costs follow.

Reading a spec costs the whole file. An agent that needs one paragraph of a
four-file corpus pays for four files, every session, forever.

The execution ledger has no durable home at all. `superpowers` writes it to
`<repo-root>/.superpowers/sdd/<plan-basename>/progress.md`, which is
git-ignored scratch its own skill notes is destroyed by `git clean -fdx`. It
is machine-local, uncommitted, and the only record of task completions,
fix rounds, parked findings and rulings.

darkmem already holds the machinery to answer both — `documents` and `blocks`
tables, a markdown parser that builds a real heading tree, a per-fingerprint
block embedding partition, and a semantic block search channel — and exposes
none of it to a writer. There is no ingest door on either transport;
`block_pipeline.ingest_document`'s only caller in the tree is a benchmark
harness under `backend/scripts/benchlib/`.

## Decisions taken before this design

Recorded because each one closes a branch this spec no longer argues:

1. **Files stay authoritative; darkmem mirrors them.** No versioning, no
   concurrent-edit resolution, no export path. A document in darkmem is a
   queryable copy, and the file on disk remains the thing you edit.
2. **The mirror is refreshed by an explicit push, not a watcher.** An agent
   calls the door after writing a file. An automatic trigger (a repo indexer
   pass, a save hook) stays a later decision, taken once the door has been
   used.
3. **This slice is the door plus section search.** The progress-ledger parser
   and task model, the inject-block wiring, and any automatic sync are queued
   behind it, each as its own spec.

## Governance: the MCP door placement — RULED 2026-08-23

`docs/two-door-parity.md` classifies the whole documents surface **REST
single-door**, and states the reason on the row: "EH1 is a horizon lane behind
its own eval gate (doc 16 §1's firewall), and an MCP twin would put an
unshipped surface in front of every agent before the gate that governs it has
run. Single-door until G-F clears, then re-decided on its merits rather than
inherited."

**G-F has not cleared.** The gate ledger records it *open — measured and
MISSED* (2026-08-17, TH1.10): entailed precision 0.888 against a 0.95 bar, a
false-accept problem concentrated in `overreach`. No bar moved, nothing was
re-run, no second vendor was tried, and three of its four probes are untouched.

This is not a formality. `tests/test_door_parity.py` drives its enumeration off
the router and the tool registry, so a new REST route or MCP tool that nobody
classified fails the suite. Every verb in this spec needs a parity row, and any
row granting an MCP twin is a re-decision of a recorded ruling — an owner act,
which this design must obtain and record rather than inherit by silence.

The argument each way, stated so the ruling is made on the merits:

**For an MCP write and search door now.** What G-F measures is the
*faithfulness gate* — whether a claim is entailed by the span it cites, which
governs `POST /documents/qa`, an answer that is generated, labelled and
served. `document_search` generates nothing and labels nothing: it returns the
document's own text with a cosine score, the way `code_search` returns source.
The firewall doc 16 §1 draws is against document content reaching the *verified
vault* unlifted, and this channel is already structurally barred from that by a
test. On that reading the gate governs a different surface than the one this
spec opens.

**Against.** The recorded ruling says "until G-F clears", not "until G-F
clears for the surfaces it measures", and the ledger's own note on the miss —
agent-authored gold, CLAUDE.md contamination reported by every participant —
is a reason to be more cautious about EH1 reaching agents, not less. An owner
who wrote "re-decided on its merits" after a *pass* is being asked to
re-decide after a *miss*.

**Owner ruling, 2026-08-23: the MCP tools ship.** The reason ruled on is the
first argument above — G-F measures the faithfulness gate, which governs
`POST /documents/qa`, an answer that is generated, labelled and served. Block
search generates nothing and labels nothing; it returns the document's own
text with a cosine score, as `code_search` returns source. The firewall doc 16
§1 draws is against document content reaching the verified vault unlifted, and
`tests/test_block_retrieval.py` already bars that structurally. The
`documents.grounded_qa` row is untouched by this ruling and stays REST
single-door: that surface is what G-F actually gates, and its answers are
withheld today.

This supersedes the "single-door until G-F clears" clause for the reads and
for the verbs this spec adds — it does not clear G-F, and no bar moved.

**Mechanically**, the parity table in `docs/two-door-parity.md` is generated:
`PARITY_TABLE` in `backend/tests/test_door_parity.py` is the source of truth,
`test_the_committed_table_is_the_enforced_table` fails on hand edits, and
`test_the_committed_table_reports_its_own_counts` fails unless the doc's
headline counts match. So the change is a `Surface` entry per verb carrying
this ruling as its reason, then a regenerate, then the headline count. The
prose paragraph above the table that states the old ruling is hand-written and
moves in the same commit.

## Scope

In: a write verb and three read verbs over the existing document/block
services, on both transports, plus the embedding wiring those verbs need to
be truthful.

Out, each already queued: the ledger parser and task model; wiring
`inject_fill` to any door; a repo-indexer or save-hook sync trigger; LLM
document summaries (`document_summary` stays on-demand where it is); a
keyword arm alongside the semantic one.

## Architecture

The door adds no retrieval semantics. Every verb is a call into a service
that already exists and already carries its own honesty rule:
`block_pipeline.ingest_document` for the write, `BlockQueryService.search`
for section search, the document repository for outline and fetch. The one
new behaviour is embedding blocks at ingest time.

Three boundaries the existing code enforces, inherited rather than restated:

**The server never reads the client's filesystem.** The agent reads the file
and sends its content; `uri` is an identity string, never a path the server
opens. Same boundary `inject_adapters` records for the block writer.

**Blocks stay firewalled from memory retrieval.** `block_query` is a separate
channel, deliberately not fused into the four-layer composition, with a
structural test asserting no fusion module imports it and that `block` is not
a member of `layer_composition.ID_KINDS`. Document content reaches the vault
only as lifted facts, never as raw block rows. This slice must not perturb
memory search ranking, and the structural test is what proves it did not.

**Ingest neither summarises nor classifies.** No model call on the write path
beyond the embedding. Filing a plan costs one embed batch, not the five-phase
capture pipeline.

## The write door

`POST /api/v1/documents` (REST) and `document_put` (MCP), over one shared
service function, in the
single-writer shape `checkpoints.py` established for two-door parity.

The MCP door lands on the unauthenticated `/mcp` surface whose
only network defence is the Host allowlist. That is the same posture
`memory_add` already has, and a document write is not more privileged than a
memory write — but it is a whole-file write door on a LAN-trust surface, and
that is worth one sentence in the ruling rather than an assumption.

| Field | Meaning |
|---|---|
| `project` | Scope, memories' convention (`default` when unset) |
| `uri` | Identity: repo-relative path, e.g. `docs/superpowers/plans/x.md` |
| `content` | The file's text, sent by the caller |
| `title` | Optional; falls back to the first heading (new door logic, not inherited) |
| `source_type` | Optional; inferred from the `.md` suffix by `resolve_source_type` |

Re-filing the same `(project, uri)` updates in place — `ux_documents_project_uri`
already enforces that identity — and `file_document`'s content hash
short-circuits the whole filing when the text is byte-identical.

**The re-file cost model, stated correctly because an earlier draft of this
spec got it wrong.** There is no per-block identity across an edit:
`document_ingest.py`'s module docstring records that blocks are replaced,
never merged, and **block ids are minted fresh each time**. So the short-circuit
is all-or-nothing at the document level. A one-character edit to a large plan
re-parses and re-embeds *every* block in it — one full embed batch per file per
edit. There is no partial path and this spec does not build one; per-block
delta embedding would need a stable block identity the substrate does not have,
and scoping that is a separate piece of work.

What this costs in practice is bounded by how agents actually write: plans and
ledgers are appended to a handful of times per session, against a LAN embedder.
If it turns out to hurt, the repair is delta identity, not a cheaper door.

**Text only, narrowing doc 16's recorded stance.** Doc 16 §235/§252 puts file
*upload* on REST multipart, because binary does not fit MCP's text-JSON, with
an MCP text-filing tool beside it. A JSON `content` string serves markdown and
plain text and drops the PDF path, which `resolve_source_type` and `parse_pdf`
already support on the service below. That narrowing is deliberate for this
slice — every artefact in scope (requirements, designs, specs, plans, the SDD
ledger) is markdown — and is recorded here rather than omitted, so a later
multipart route reads as the resumption of a deferred path and not a new idea.

**Repo-relative rather than absolute paths** is deliberate: it makes a
document portable across machines. The cost is that one project spanning two
repositories could collide on a path like `README.md`. Accepted, because the
project scope here is effectively one repository.

**Content is bounded, unlike `MemoryCreate.content`.** That field is
`min_length=1` with no maximum, and repeating the omission here would be worse
than it is there: an unbounded document drives a synchronous parse and embed
loop before the call returns, with no analogue of
`buffer_wait_timeout_seconds` to degrade against. The bound is **1,000,000
characters and 5,000 blocks per document**, refused at the schema with a 422
naming which limit was hit. Both numbers are an order of magnitude above any
plan or ledger and exist to stop a pathological input, not to shape usage.

**This door is synchronous, diverging from every capture door, and the
divergence is argued rather than assumed.** REST `POST /memories`, its batch
twin and both MCP capture tools return 202 and enqueue a `memory_buffer` row.
The buffer exists to decouple a caller from the five-phase pipeline — an
embed, an LLM extraction, a classification, an ANN dedup fan-out and a graph
write. Document filing runs none of those: it parses, writes blocks, and
embeds. It mints no memory, resolves no `origin_key`, counts toward no
corroboration and enters no verification ladder, so none of the machinery the
buffer protects is on this path. A 202 here would buy latency the caller does
not need and cost it the one thing it does need — knowing whether its document
is searchable yet. The bound above is what keeps that defensible.

Response: document id, blocks filed, blocks embedded, and the filing outcome
(`created` / `updated` / `unchanged`). The two block counts are separate
numbers for the reason under "Failure behaviour" below.

**`unchanged` still embeds what is missing.** `file_document` returns
`UNCHANGED` before touching any block, so a re-push of an identical file
files nothing — and that is exactly the state a caller is in after an embed
failed post-commit. If the door stopped there, the agent's one natural repair
(push it again) would be a no-op and the document would stay invisible until
the backstop job fired. So `document_put` on the `unchanged` path queries the
document's blocks lacking a vector in the active fingerprint and embeds those.
An already-embedded document costs one indexed query and no model call.

## The read door

Three verbs with deliberately different token costs, so a caller can choose
how much to pay. Each names its REST route explicitly, because this slice
lands on a surface that already exists: `routes/documents.py` serves
`GET /api/v1/documents`, `GET /{id}/summary`, `GET /{id}/connections` and
`POST /qa`, and its own docstring calls itself "the EH1 horizon's one door".
These verbs extend that door rather than opening a second one, and the
existing `documents.reads` and `documents.grounded_qa` parity rows are
untouched by them.

| Verb | REST route |
|---|---|
| `document_search` | `POST /api/v1/documents/search` |
| `document_outline` | `GET /api/v1/documents/{document_id}/outline` |
| `document_get` | `GET /api/v1/documents/{document_id}` |
| `document_delete` | `DELETE /api/v1/documents/{document_id}` |

`POST` for search follows the REST contract's rule that complex queries are
posted, not encoded in a query string. `DELETE` answers 204. Every route that
takes a `{document_id}` also accepts `?uri=` resolution against the same
project, since a caller that pushed by path has a path and not an id.

**`document_search(query, project, limit, document_id?)`** — the token-cheap
primitive, and the point of the slice. Returns matching blocks only: block
text, its document's title and `uri`, the heading path, the character span,
and the cosine score. Never the document. `project` has no default, matching
`BlockQueryService.search`, which refuses an omittable retrieval scope.

The heading path is resolved **in the door**, not in `block_query`. `BlockHit`
carries `block_id`, `document_id`, `project`, `uri`, `type`, `text`,
`order_index`, `char_span` and `score`, and no ancestry. The markdown parser
does build the tree — a heading owns its following content down to the next
heading of equal or shallower level, with the level in the block's properties
— so the path is a parent walk over `blocks.parent_id`. Resolving it in the
door keeps `block_query` untouched, which matters because that module is
under the firewall test above.

**`document_outline(project, uri | document_id)`** — the heading tree: block
ids, levels, heading text, no body. Cheap enough to fetch reflexively, and it
gives an agent the map before it decides what to pull. A query over the block
tree the parser already built; no model call, and specifically not
`document_summary`, which stays on-demand and unbadged where it is.

**`document_get(project, uri | document_id, block_ids?)`** — the whole
document, or only the blocks named. The `block_ids` form is the drill-down
after an outline.

**`document_delete` and the staleness it answers.** Under files-are-
authoritative, a deleted or renamed file leaves a mirror that `document_search`
keeps serving forever — sections of a plan that no longer exists, ranked
alongside live ones, with nothing in the result saying so. There is no
`DELETE` route on the existing documents surface today, so this slice adds
one. The work is small: `blocks.document_id` cascades, and the
`block_embeddings__<slug>` foreign key cascades from there, so removing the
document row takes its subtree and its vectors in every partition.

Detecting that a file was deleted is a different problem and stays out of
scope — it belongs to whatever sync trigger lands later. What this slice owes
is that an agent which *notices* has a verb to call.

**Metadata is clobbered on re-file, and that is inherited, not chosen.**
`update_document` and the upsert overwrite `title`, `source_type` and
`properties` wholesale, NULLs included. Two consequences: a re-file that omits
`title` nulls a stored one — so the door sends its resolved title on every
call rather than only when the caller supplied it — and a re-file wipes any
stored summary, which `document_summary` documents as intended, since a
summary that outlived its document's text would be a claim about a document
nobody wrote.

## Embedding wiring

`block_embeddings.embed_blocks` exists and has no caller anywhere; its own
docstring records that hooking it into the ingest path is downstream work.
Without that hook a filed document parses into blocks with no vectors and
`document_search` returns nothing — indistinguishable from an empty corpus.
Closing it is part of this slice.

**Inline, after the filing commits.** `document_put` files, commits, then
embeds, then returns; the document is searchable when the call returns, which
is the pattern an agent actually uses — write the plan, then immediately ask
about it. Embed-after-commit is forced rather than chosen: first contact with
an unknown fingerprint runs child-table DDL through `embedder_registry.register`,
which commits on the session, so embedding inside the filing transaction
would make the filing non-rollback-able.

Two mechanics the door owns because the services do not:
`file_document` returns `DocumentIngest(document_id, outcome, content_hash,
blocks_written, blocks_stripped)` — counts, not ids — so the door re-queries
the document's block ids before embedding. `embed_blocks` takes those ids and
returns `WriteResult(fingerprint, written)`, or `None` when nothing was
embedded; `written` is the "blocks embedded" number in the response, and
`None` is reported as zero rather than as success.

**A `block_embedding_refresh` job as backstop**, on the `JobRegistry`,
modelled on the existing `relation_embedding_refresh`. It sweeps blocks with
no vector in the active fingerprint's partition, bounded by a configurable
batch, and journals to `events`. It covers three cases inline embedding
cannot: an embed that failed after its filing committed, an embedder rotation
that strands every existing block in a dead partition, and documents filed
before this ships.

This makes the roster twenty-four jobs. `tests/test_code_deriver.py` compares
`app/main.py`'s registrations against a hardcoded expected set in the test, so
the build fails until that set is updated; CLAUDE.md's count is prose the test
documents rather than machine-reads, and both move in the same change — a
count that has gone stale four times already. The job registers through a
`BLOCK_EMBEDDING_JOB_KEY` constant, matching how the other nine key-constant
jobs register, so the scan reads a binding rather than a quoted literal.

Journalling needs a vocabulary entry first: `EVENT_TYPES` carries
`document_filed` and nothing for this sweep. Per the events rule — widening is
taxonomy-first, land the value before its emitter ships — the job's event type
is added to `EVENT_TYPES` in the same change, not discovered at runtime as an
unknown value that logs a warning.

## Failure behaviour

An unparseable or unroutable source raises after `file_document`'s SAVEPOINT
has rolled the filing back: the caller sees the document exactly as it was
and a session it can keep using. The error names the known source types
rather than guessing one.

`block_query` has a single retrieval arm, so a failure raises rather than
returning `[]`. Empty means "your corpus has no match" and must never mean
"the embedder was unreachable" — invariant 14, and the reason that module
catches nothing.

**The one new failure this design introduces:** because the embed runs after
the filing commits, an embed failure leaves a document that exists and cannot
be found. `document_put` therefore reports blocks filed and blocks embedded
as two numbers, and a partial embed is visible in the response rather than
inferred later from a search that returns nothing.

## Tests

- A parity row for every new route and tool, since `tests/test_door_parity.py`
  fails on any surface nobody classified, plus the regenerated doc and its
  headline counts.
- Two-door parity for all four verbs: the same call answers the same way on
  both transports.
- The content and block-count bounds refuse with a 422 naming the limit hit.
- `unchanged` re-push embeds blocks that lack a vector, and costs no model
  call when none do.
- `document_delete` removes the document, its block subtree and its vectors in
  every partition.
- Re-filing the same `(project, uri)` updates in place and mints no duplicate.
- Byte-identical content short-circuits the filing (the only short-circuit
  there is — block ids are minted fresh, so an edited document re-embeds
  whole).
- Heading-path resolution against a nested markdown fixture, including a
  heading level that pops the stack.
- Embed-after-commit ordering: a failing embed leaves the filed document
  intact and the response reporting the shortfall.
- The refresh job sweeps blocks lacking a vector in the active fingerprint.
- The existing firewall test still passes: no fusion module imports
  `block_query`, `block` stays out of `layer_composition.ID_KINDS`.

## Open questions

None blocking; the door placement was ruled 2026-08-23 and is recorded above.

Non-blocking judgements recorded above and open to reversal: the repo-relative
`uri` convention, whose cost is a cross-repository path collision inside one
project; the 1,000,000-character and 5,000-block bounds; and text-only filing,
which defers doc 16's multipart PDF path.

## Review

Adversarially reviewed 2026-08-23 (Fable). Two findings were confirmed against
the source and corrected here: the door placement conflicts with a recorded
ruling (now the Governance section), and the re-file cost model was wrong —
block ids are minted fresh, so nothing survives an edit unembedded. The
`UNCHANGED`-after-failed-embed repair path, the REST route names, the deletion
position, the size bounds, the buffered-capture argument, the event-vocabulary
entry and the roster-test mechanism were all gaps the review surfaced.
