# Retrieval gold — the seven slices (doc 17 §4)

This file is the authority for what each slice *means*. Add pairs against
these decision procedures, not from memory of what the slice name suggests —
two contributors drawing the boundary differently is how a slice silently
becomes a mixture and the 2026-04 weak-slice finding stops meaning anything.

Files: `corpus.json` (94 memories, fixed `memory_id` UUIDs + declared
`created_at`), `gold.json` (118 pairs, 102 live). Loader and seeding:
`benchlib/retrieval_gold.py`. Validation: `benchlib/tests/test_retrieval_gold.py`.

## File discipline (doc 17 §11)

- **Append-only.** New pairs go at the end with the next `rg-` id. A wrong
  pair is retired in place (`"retired": true` + reason in `notes`) — never
  deleted, rewritten, or reordered. `declared_slice_counts` counts
  non-retired pairs and is updated with every append; the validation test
  pins the documented numbers, so both move together, visibly.
- **One slice tag per pair** (v1 discipline). A query that seems to belong
  to two slices is a badly chosen query — sharpen it until it belongs to one.
- **Group-anchored pairs are machine-guarded.** Temporal and update corpus
  entries carry a `group`; speculative members carry `"speculative": true`.
  A pair whose gold depends on group state declares an `anchor`:
  `"current"` — every grouped relevant memory must be the newest
  non-speculative member of its group — or `"whole-group"` — the relevant
  set must equal the group's full membership. `validate_gold_against_corpus`
  enforces both, so appending a newer sibling (a `t2d` snapshot, a
  definitive `u6c` replacement) fails the suite instead of silently making a
  latest-anchored or present-state pair point at stale gold. That failure is
  the signal to re-adjudicate the affected pairs under retire-and-replace.
  Any new pair whose gold means "the current truth" or "the whole story"
  must carry the matching anchor.
- **Live multi-hop pairs are machine-guarded.** Each records
  `consequence_memory_id` and its measured `baseline_consequence_rank`;
  the loader rejects a live pair whose recorded rank is not worse than
  `MULTI_HOP_BASELINE_K` (see the multi-hop section for the measurement
  protocol). The 2026-07-26 retirements predate the fields and carry
  neither. Since gold v4 each live pair also records `bridge_entity` and
  `bridge_status` (graph-side verification, same section); `name-only`
  status is lawful only for the closed pre-v4 exception list pinned in
  the loader (`MULTI_HOP_NAME_ONLY_BRIDGES`) — a new pair must be
  `shared-entity`.
- **Fixed ids.** `memory_id` is uuid5 of the entry `key` under
  `retrieval_gold.MEMORY_ID_NAMESPACE` — mint new ids with
  `retrieval_gold.memory_id_for_key(key)`; the loader rejects an id that
  does not derive from its key. Ids never change across reseeds, which is
  the whole reason `relevant_memory_ids` can live in a versioned file.

## Corpus authoring rules the slices depend on

- **Distractors are load-bearing.** Every literal domain (ports, versions,
  times, buckets) has ≥ 2 same-shaped competitor memories; a query over a
  corpus with no near-misses cannot fail, so it measures nothing.
- **Temporal-group contents are calendar-date-free.** The temporal anchor
  must resolve through `created_at` alone; a month name in the content lets
  full-text search answer a time question lexically.
- **Update pairs keep pair-internal spacing ≤ 90 days, but that does NOT
  make them eligible for supersession at ingest.** The real detector
  computes its window from wall-clock now, not from the pair's spacing
  (`detect_supersessions`, `app/services/supersession.py`:
  `cutoff = now - SUPERSESSION_WINDOW_DAYS`, and the pipeline call site
  never passes `now=`), so whether a stale member falls inside the window
  depends on the calendar day of the run — and as the corpus dates age, none
  do. These pairs therefore test a retriever's handling of
  **stale-but-present** candidates; whether ingest flipped the stale row to
  `superseded` is wall-clock-dependent and is *not* a property this corpus
  can guarantee. Anyone measuring a supersession-aware arm (T0.10's
  comparisons) must either control the detector's clock — pass `now=` at
  the call site under test — or re-date the update-pair members and
  re-adjudicate every affected pair under retire-and-replace. Never re-date
  on a rolling basis or silently: that trades a documentation error for a
  determinism break.
- **Temporal siblings are snapshots, never corrections** — each is true of
  its own time. Corrections belong to the knowledge-update group.
- Roles are per-query, not per-memory: a memory is a "distractor" only
  relative to a query, and any corpus memory may be a target.
- **Growing the corpus re-opens the gold.** Every appended memory must be
  adjudicated against every live pair's query — a new memory that
  genuinely answers an existing query makes that pair's `relevant` set
  incomplete and the pair scores a false miss forever. And because new
  memories shift every ranked list, every live multi-hop pair's
  `baseline_consequence_rank` must be re-measured over the grown corpus
  and re-recorded (warm-cache re-measurement costs zero live calls for
  unchanged content).

## Query-type slices

### exact (12 pairs)

**Decision procedure.** The query copies a distinctive span from the target
memory: at least three consecutive content tokens, or at least two
distinctive tokens beyond the subject-entity name, verbatim and correctly
spelled. Exactly one target memory.

**Negative example.** "Which port serves the metrics dashboard UI?" for the
Grafana memory — no verbatim distinctive span survives; that is a
paraphrase-or-fact query, not exact.

**What it catches.** The control slice: if exact fails, the harness itself
is broken (an ingest failure, or the memory-id string/UUID drift dropping
matches at the boundary) — both retrieval channels should trivially win it.

### paraphrase (18 pairs)

**Decision procedure.** The query restates the target's assertion in
different words. After stopword removal, the query shares no content lemma
with the target except (a) lemmas occurring in ≥ 3 corpus memories
(domain-common), and (b) at most one proper noun, kept only when the
assertion is inexpressible without it — and then only if at least one other
corpus memory also contains it, so it alone cannot single out the target.
Exactly one target memory, which must not be part of a temporal or update
group (siblings would make "the" restated assertion ambiguous).

**Negative example.** "Where does Grafana run and on which port?" — it keeps
"Grafana" + "port", a token pair that uniquely keys the target through the
keyword channel; not a paraphrase however much the rest is reworded.

**What it catches.** The keyword channel scores ~zero by construction, so
the slice isolates the semantic channel: an embedder regression, or a fusion
change that over-weights the FTS side, shows up here first. Historically a
weak slice (2026-04).

### typo (14 pairs)

**Decision procedure.** Start from an exact-style query (verbatim spans),
then corrupt one to three of its most discriminating content tokens with
edit-distance-≤2 errors (transposition, omission, insertion, doubling). The
corrupted tokens must include at least one token that keys the target;
`plainto_tsquery` is a conjunction, so one corrupted content word already
zeroes the keyword channel, and corrupting the discriminating token also
stresses any future partial-match retriever (trigram, OR-fusion). The
misspelling must not spell another corpus term. Note the corruption in
`notes` (`token->tyop`).

**Negative example.** "grafana listens on prot 3000" — only the generic
token is corrupted while "grafana" and "3000" stay intact; the
discriminating tokens still key the target, so the query does not test
robustness to misspelled *content*.

**What it catches.** Robustness of the semantic channel to misspelled input
(agents forward user typos verbatim), and any keyword-side crutch: a
retriever that only wins via intact lexemes collapses here. Historically a
weak slice (2026-04).

### fact (18 pairs)

**Decision procedure.** An interrogative query that names the subject
entity verbatim and asks for a specific attribute stated in exactly one
corpus memory — a number, name, version, path, time, or stated reason. The
query must not contain the answer value. The target must be a
single-version subject (not in a temporal or update group).

**Negative example.** "What is our database setup like?" — open-ended, no
single literal answer, several plausible memories; that is not a fact query.
Likewise "Is Grafana on port 3000?" — it contains the answer.

**What it catches.** Question-form-to-declarative-form bridging plus
value-level precision: the corpus places same-shaped literals in competing
memories (staging 15.6 vs production 16.2; backups at 02:30 vs 04:00 vs
03:15; bucket artifacts-prod vs tf-state), so a retriever that matches the
topic but not the *attribute holder* ranks the wrong sibling first.
Historically a weak slice (2026-04).

## Capability slices

These are the slices the Phase-2 arm activations must move to earn their
flags (doc 00 §8): each is built so a hybrid-only baseline plausibly fails
it, and each catches a wrong behaviour the other six cannot.

### multi-hop (14 pairs)

**Decision procedure.** `relevant_memory_ids` has ≥ 2 members (enforced by
the loader) forming a chain: memory A links the query's anchor to a bridge
term; memory B carries the queried consequence, contains the bridge, and
does **not** contain the anchor. The query shares no distinctive content
lemma with B — distinctive meaning a lemma occurring in fewer than three
corpus memories, as in the paraphrase rule; check every content word of the
query against B. Neither A nor B alone answers the query.

**Mechanical isolation check (mandatory since gold v3).** Lexical
isolation is not enough: the 2026-07-26 re-adjudication measured 13 of the
original 14 pairs saturated — the query named B's consequence *domain*
(power, latency, rate limits, websockets...) and the semantic channel
reached B at ranks 1–9 with no hop at all. Every live multi-hop pair must
therefore record in `gold.json`:

- `consequence_memory_id` — which relevant memory is B, and
- `baseline_consequence_rank` — B's measured rank for this pair's query
  under the hybrid-only baseline (doc 17 §4 current configuration:
  `GateConfig()` defaults — hybrid on, reranker off,
  `confidence_rank_gamma` 0, `relation_rescue` on — via
  `retrieval_runner.run_retrieval` at `limit` = the full corpus size),
  or `null` if B was not retrieved at all.

`load_retrieval_gold` **rejects** a live multi-hop pair whose recorded
rank is missing or not worse than `MULTI_HOP_BASELINE_K` (10, the k the
baseline is scored at). Authoring a multi-hop pair therefore requires
running the baseline measurement — a domain-naming query measures ≤ 10
and cannot enter the file; "the consequence memory is not semantically
proximal to the query" is decided by the retriever, never by argument.
Recorded ranks are as-of the corpus at adjudication time; any corpus
growth requires re-measuring and re-recording them (see the corpus
authoring rules). Bridge tokens must be semantically opaque — the
saturated pairs that survived a first replacement round leaked through
bridge names that encoded the anchor's domain (`acct-03` for invoices,
`signage-config` for displays, `cast-media` for podcasts, `lang-cdn-1`
for translations); host-number-style names (`acs-01`, `sftp-02`,
`gpu-01`, `hv-27`) do not leak.

**Graph-side check (mandatory since gold v4).** The rank guard proves
the baseline *cannot* reach B; it says nothing about whether a graph
arm *can*. The 2026-07-27 review replayed the ingested graph and found
two v3 pairs whose bridge existed only in the corpus text — the
extractor produced **zero entities** for one memory of each chain, so
no entity-graph arm could ever traverse to B: dead weight no arm can
fix, silently capping the slice's achievable hit@10. Every live pair
must therefore also record:

- `bridge_entity` — the bridge's entity name as extraction stores it
  (lowercased), and
- `bridge_status` — `shared-entity` when one `(name, entity_type)` row
  in the ingested `entities` table carries **both** memories in its
  `memory_ids`, or `name-only` when the two memories hold same-named
  nodes of *different* entity types (disjoint under the domain model's
  `(name, entity_type)` identity; Phase-4 dedup is deliberately
  type-constrained, so they never merge).

Verify against the real graph, not the corpus text: ingest the corpus
(cache replay), then check the `entities` rows' `memory_ids` for both
memories. Extraction is deterministic here (content-seeded, cached), so
the status is stable across reseeds. Phrasing note: the extractor keys
on the bridge's noun phrase — using the **identical** phrase in both
memories ("the fleet-cfg repository", "the hook-runner service") is
what reliably yields one shared `(name, entity_type)` node; bare
prepositional mentions ("through the ops-oauth app registration",
"on the arc-store bucket") can extract as zero entities.

**A new pair must be `shared-entity`** — the strictest plausible arm
design must be able to win it. `name-only` is grandfathered for exactly
the eight pre-v4 pairs pinned in `MULTI_HOP_NAME_ONLY_BRIDGES`
(rg-0072 `search-01` artifact/service, rg-0104/0105 `hv-27`
place/entity, rg-0107/0108 `acs-01` service/artifact, rg-0112/0113
`iot-gw-1` service/artifact, rg-0114 `gpu-01` place/service) — the
same property rg-0072, the slice's only originally-blessed pair,
already had, i.e. the slice's pre-existing standard, recorded rather
than re-authored. Whether a name-only bridge is traversable depends on
whether the Phase-2 arm links entities by node identity or by name /
name-embedding — **deliberately not decided here**; that decision
belongs to the arm-activation task (Tier-2 amendment logged
2026-07-27). Until it is made, the slice's ceiling reads off the
recorded statuses: 6/14 under strict node identity, 14/14 under
name-linking — visible, not implicit.

**Negative example.** A chain where the consequence memory also names the
anchor ("The svc-bot token used by the chat-ops bot expires every 90
days") — B is reachable lexically from the query, the hop collapses to
single-hop, and the pair tests nothing the exact slice doesn't.

**What it catches.** The retriever returns only the lexically anchored
memory and never surfaces the bridge-linked consequence, so hit@K over the
full relevant set fails. Both isolation properties are now established
per pair: lexical (B shares no distinctive query lemma) and semantic (the
recorded `baseline_consequence_rank` proves the hybrid-only baseline does
not reach B inside k). History: T0.07 measured the original slice
saturated — 13 of 14 pairs solved by the semantic channel alone because
the query named B's domain outright, exactly as this file's earlier
caveat suspected — and the 2026-07-26 re-adjudication retired-and-replaced
all 13 under the mechanical check above (gold v2 → v3); only rg-0072
survived. The 2026-07-27 review round then retired two v3 replacements
whose bridges never reached the extracted graph and added the
graph-side check (v3 → v4). The re-measured slice sits at
hit@10 = 0.0000 with every anchor still found at rank 1. Graph-aware
arms (PPR over shared entities, dual-level) are the designed path to B;
no other slice requires composing two memories.

### temporal (12 pairs)

**Decision procedure.** The corpus holds ≥ 2 memories about the same
subject with different declared `created_at`, each a snapshot true of its
own time — a **snapshot group**, never an update pair (slice membership
follows the target group's kind, not the qualifier wording; see
knowledge-update). The query carries an explicit temporal qualifier — a
named month/quarter/year, "current/latest/most recent/right now/today", or
"before/after <corpus event>". Gold is exactly the sibling(s) whose
`created_at` satisfies the qualifier; latest-anchored pairs carry
`"anchor": "current"` so a newly appended sibling fails validation instead
of silently staling them. Sibling contents must not state the calendar date
the qualifier names: the anchor must resolve through `created_at`, never
through text match.

**Negative example.** "What did the February incident review cover?" over a
memory whose content says "February" — the anchor resolves lexically, so
the pair does not test time-awareness (it is an exact/fact query). Also
negative: "current X" where the corpus has only one memory about X —
nothing to discriminate.

**What it catches.** Time-blindness. By construction the siblings' contents
give no date signal, so a content-only retriever cannot know which sibling
is from March — it returns an arbitrary or newest one for as-of-past
queries. Only `created_at`-aware ranking answers both directions; note the
as-of-past half also fails a *pure recency boost*, which is exactly what
separates this slice from knowledge-update.

### knowledge-update (14 pairs)

**Decision procedure.** The corpus holds an update pair in the same
project: an older memory asserting a state, and a newer memory (within the
90-day supersession window) that either **definitively** asserts its
replacement/retirement or only **speculates** about one (a
`SPECULATIVE_REPLACES_MARKERS` phrasing: "considering", "might switch",
...). Speculative members are marked `"speculative": true` in the corpus.
The query asks for the *present* state — present tense, optionally
"now/today" — with no calendar anchor. A present-anchor ("now", "today",
"these days") does **not** move a pair to temporal: the disambiguator is
the target group's kind — update pair → knowledge-update, snapshot group →
temporal. Only a calendar or corpus-event anchor over an update pair moves
the query to temporal. Gold: definitive pair → the newer memory only;
speculative pair → the older memory only; a query asking whether the
announced change has happened → both members. Present-state pairs carry
`"anchor": "current"` and change-status pairs `"anchor": "whole-group"`
(see File discipline), so appending a newer group member forces
re-adjudication instead of silently staling the gold.

**Negative example.** "What did we use for session storage before the Redis
migration?" — anchored to a past event, so it belongs to temporal, not
knowledge-update. Also negative: a present-state query over a subject with
only one memory — there is no stale competitor, so nothing can fail.

**What it catches.** Two failure modes no other slice separates: serving
stale truth (the retired assertion often matches the query lexically at
least as well as its replacement — definitive pairs), and naive recency
(the speculative traps, where the *newest* memory is the wrong answer, so a
crude prefer-newer boost fails exactly where supersession-aware handling
succeeds). Whether ingest's supersession fired or not, the gold stays
valid: it names the memory that states the current truth.
