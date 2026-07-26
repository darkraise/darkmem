# Retrieval gold — the seven slices (doc 17 §4)

This file is the authority for what each slice *means*. Add pairs against
these decision procedures, not from memory of what the slice name suggests —
two contributors drawing the boundary differently is how a slice silently
becomes a mixture and the 2026-04 weak-slice finding stops meaning anything.

Files: `corpus.json` (72 memories, fixed `memory_id` UUIDs + declared
`created_at`), `gold.json` (102 pairs). Loader and seeding:
`benchlib/retrieval_gold.py`. Validation: `benchlib/tests/test_retrieval_gold.py`.

## File discipline (doc 17 §11)

- **Append-only.** New pairs go at the end with the next `rg-` id. A wrong
  pair is retired in place (`"retired": true` + reason in `notes`) — never
  deleted, rewritten, or reordered. `declared_slice_counts` counts
  non-retired pairs and is updated with every append; the validation test
  pins the documented numbers, so both move together, visibly.
- **One slice tag per pair** (v1 discipline). A query that seems to belong
  to two slices is a badly chosen query — sharpen it until it belongs to one.
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
- **Update pairs sit inside the 90-day supersession window** (newer member's
  `created_at` within 90 days of the older's) so the pairs are eligible for
  the real supersession path, whichever way ingest resolves them.
- **Temporal siblings are snapshots, never corrections** — each is true of
  its own time. Corrections belong to the knowledge-update group.
- Roles are per-query, not per-memory: a memory is a "distractor" only
  relative to a query, and any corpus memory may be a target.

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

**Negative example.** A chain where the consequence memory also names the
anchor ("The svc-bot token used by the chat-ops bot expires every 90
days") — B is reachable lexically from the query, the hop collapses to
single-hop, and the pair tests nothing the exact slice doesn't.

**What it catches.** The retriever returns only the lexically anchored
memory and never surfaces the bridge-linked consequence, so hit@K over the
full relevant set fails. Hybrid-only has no path to B (no shared query
lemmas, and B embeds near the bridge's topic, not the query's); only
graph-aware arms (PPR over shared entities, dual-level) can lift it. No
other slice requires composing two memories.

### temporal (12 pairs)

**Decision procedure.** The corpus holds ≥ 2 memories about the same
subject with different declared `created_at`, each a snapshot true of its
own time. The query carries an explicit temporal qualifier — a named
month/quarter/year, "current/latest/most recent/right now/today", or
"before/after <corpus event>". Gold is exactly the sibling(s) whose
`created_at` satisfies the qualifier. Sibling contents must not state the
calendar date the qualifier names: the anchor must resolve through
`created_at`, never through text match.

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
...). The query asks for the *present* state — present tense, optionally
"now/today" — with no calendar anchor. Gold: definitive pair → the newer
memory only; speculative pair → the older memory only; a query asking
whether the announced change has happened → both members.

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
