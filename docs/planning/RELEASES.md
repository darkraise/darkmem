# Releases

The ladder. One version per shipped feature-group; a version is cut when its
tasks are `done` and `./scripts/gate.sh --full` is green. Design:
`docs/superpowers/specs/2026-08-10-release-milestones-and-autonomous-loop-design.md`.

**`v0.1` is not the schema freeze.** Dev environment, disposable data by the
owner's decision (2026-08-10). CLAUDE.md's trigger — the first deploy whose data
must survive — remains in the future.

## Where these files live

Two classes, and the split is what keeps either from drifting:

- **Planning state is canonical on `master`** — this file, `progress.md`,
  `gate-ledger.md`. `scripts/gen_progress.py` derives `progress.md`'s `Version`
  column from the sections below and hard-refuses to run off `master`, so the
  ladder has to be here for the column to exist at all. Read it with
  `git show master:docs/planning/RELEASES.md` from an epic branch.
- **Product artifacts travel with the code** — `CHANGELOG.md`, `scripts/release.sh`
  and the three version fields live on the branch being released, because
  `release.sh` asserts a clean tree and commits the version sync *into* the tree
  it tags.

## Format, because two parsers read it

A `### ` section labelled `v0.N` or `Gate track` owns the `` - `Tid` `` list items
beneath it; every other heading owns prose. `gen_progress.py` and
`backend/tests/test_planning_docs.py` both apply exactly that rule, so a task id
mentioned in a sentence — as the parked ids below are — is assigned nothing.

### v0.1 — It runs

Everything already `done`: capture, retrieval, the code graph, 21 jobs, MCP, the
SPA, both SDKs, the browser extension. No new tasks, so no list items — the 232
done rows carry no version, deliberately. The column answers "which release?"
for *open* work, which is the visibility problem it was added to fix. Cut by
demonstration, not by assertion.

> ## ✅ RESOLVED 2026-08-11 — owner ratified; both edits applied
>
> The owner's instruction was "start next two versions", which ships v0.2 **and**
> v0.3. That settles the partition question by making it moot — `T3.10` is built
> either way — leaving only the dependency amendment, applied below. `T3.10`
> moved into v0.2 and its `T3.23` edge is dropped. The escalation is kept for
> the record; the ladder sections themselves are now correct.
>
> ## The blockage, as escalated (2026-08-11)
>
> **The ladder could not be executed in the order it stated.** Two
> version-inverting dependency edges existed, and they composed:
>
> | Edge | From | To |
> |---|---|---|
> | `T3.17` → `T3.10` | v0.2 | v0.3 |
> | `T3.10` → `T3.23` | v0.3 | v0.4 |
>
> The full chain is `T3.17 → T3.10 → T3.23 → T3.02`, so **v0.2's headline
> feature is transitively downstream of v0.4's**. Only `T3.18` is startable
> today. Every other edge across v0.2/v0.3/v0.4 was checked and is clean.
>
> This is a Tier-3 amendment: the correction changes the owner-approved ladder
> table in design spec §3, and which release delivers what is the owner's scope
> authority, not the loop's. Fable-tier ruling; both edges verified against the
> tree.
>
> **Proposed fix — two edits, either alone insufficient:**
>
> 1. **Amend `T3.10`'s `Depends` from `T3.09, T2.43, T3.23` to `T3.09, T2.43`**,
>    adding a Done-when: *an absent or empty L3 channel yields an empty tier,
>    never an error.* The edge is over-tight. `T3.10` must handle an empty L3
>    tier **forever anyway** — every fresh install has zero articles even after
>    `T3.23` ships — so the degradation is permanent required behaviour, not
>    scaffolding for a missing dependency. `T3.10` reads L3 through the doc 07 §5
>    composition (`T2.43`, done); `T3.23` registers a channel *into* that
>    composition rather than defining an interface `T3.10` would have to invent,
>    so no parallel path is created. What genuinely waits on `T3.23` is G-E's
>    "L3 shipped" evidence — and `T3.10`'s gate is `G-E (label)`. Moving the edge
>    from build to evidence is this epic's own ratified 2026-08-06 pattern:
>    *a gate blocks what it certifies, not what merely precedes it.*
> 2. **Move `T3.10` into v0.2** (shown below), leaving v0.3 as `T3.20`, `T4.06`,
>    `T4.07`, `T4.08`. Spec §3's counts become v0.2: 3→4, v0.3: 5→4; the 14 / 24
>    / 6 bucket arithmetic is unchanged.
>
> **Why this grouping and not the alternative** (move `T3.17` and `T3.21` down
> to v0.3): v0.2's headline is only honest with `T3.10` inside it — resume as
> specified *is* a budgeted digest through the fill path, so without `T3.10`
> there is no resume, and v0.2 would ship an isolation guard under a feature
> headline. The per-version user story stays true at each rung: v0.2 "your agent
> can resume", v0.3 "context stays live and visible", v0.4 "synthesised articles
> join the fill".
>
> **Note `T3.10` is `Size: L`**, so runbook §3 forbids executing it directly — it
> needs a step-level plan reviewed at Fable tier first. That is a real cost of
> moving it into v0.2 and is stated here rather than discovered later.
>
> **`T3.18` is startable under every candidate resolution** and is the correct
> first task once this is ratified.

### v0.2 — Resume and checkpoints

- `T3.10` — Truth-first content fill under a token budget
- `T3.17` — Resume as a specialised inject
- `T3.18` — Checkpoints are operational, not vault knowledge
- `T3.21` — Session checkpoints / resume view

### v0.3 — Auto-context into agent tools

- `T3.20` — Inject records in timeline and calendar
- `T4.06` — Inject `watch` mode
- `T4.07` — Auto-scrape opt-in
- `T4.08` — Watch + curb surfaces on the Distribution tab

### v0.4 — Synthesised articles, unlabelled

- `T3.02` — `article_synthesis` productive runs
- `T3.03` — Claim-level entailment pass + coverage routing
- `T3.04` — `article_citations` — the one hard FK
- `T3.05` — Staleness gate + debounced re-synthesis
- `T3.06` — Articles tab
- `T3.23` — Articles retrieval channel + `article_embeddings` writer

### v0.5 — The corpus can begin

Design:
`docs/superpowers/specs/2026-08-12-v0.5-per-role-qualification-and-corpus-design.md`.
Two halves. Half A splits the qualification record by consumer role, so the article
consumer stops being gated on a discrimination it never makes; **it clears G-D as
redefined** if `T2.118` reports clean and the owner's holdings land. Half B is the corpus
— production holds one distinct `origin_key`, so no machine path can promote a fact off
`candidate`, and that, not the judge, is what holds G-C shut. `T1.54` is owner-gated and
is the version's true critical path: the 7-day origin-spacing clause cannot start
counting until capture does.

**Re-scoped 2026-08-12, on an independent review's fourth option, adopted by the owner.**
Nothing in v0.5's shipped substance needs a G-D decision, and holding the version open on
one applies exactly the pressure that turns a defensible amendment into a rushed one. So
**`T2.117` moves to the gate track** beside the qualification work, and v0.5 is
re-headlined as what it honestly is: the research loop, its origin discipline and its
door, plus a hardened census — the machinery by which a corpus can start existing. The
judge's redefinition and its qualification ship where every other gate verdict ships.

**Half B is the corpus, and the research agent joined it on the owner's instruction
(2026-08-12)** — `T3.07` and `T3.08` were parked and are now v0.5. The evidence cost is
stated where it will be read: origins a loop mints for itself are weaker corroboration than
origins independent capture produces, so `T3.08`'s stamping must make the two
machine-distinguishable and G-C's eventual verdict owes the slice. **Building them is not
running them** — pointing the loop at production is a separate decision and remains the
owner's.

- `T2.118` — Duplicate/independence pass over the non-contradicted census
- `T2.120` — `SINGLE_VALUED_RELATIONS`: the per-relation argument
- `T2.123` — The independence disclosure counts findings, not propositions
- `T3.07` — Research-agent loop through the ordinary capture door
- `T3.08` — Distinct-origin stamping for researched sources
- `T3.27` — The research loop has no door
- `T2.121` — Correct the contradiction-recall derivation in the ledger
- `T2.122` — The verdicts directory leaks synthetic files under real identities

### Gate track

Not parked and not a version: these produce gates, which unlock labels. Clearing
G-C and G-D ships as its own version whose headline is "badges go live".

- `T2.117` — Per-role qualification records (R1, ratified 2026-08-12)
- `T2.124` — A fresh entailment gold, justified without citing a result
- `T2.125` — Qualify the entailment role on the fresh gold
- `T2.129` — Grow the promotion corpus past the band, and arm the machine arm
- `T2.131` — Grow the promotion corpus to a window that settles the audit
- `T2.114` — G-D third-vendor attempt
- `T2.116` — Bind the resample certification to the pairs it certified
- `T3.22` — G-E evidence run
- `T3.24` — Coverage-distribution runner
- `TH1.10` — Faithfulness ship gate (G-F evidence)
- `TH1.17` — Faithfulness-gate runner

### v1.0 — Everything, and the gates carry verdicts

**Minted 2026-08-15 on the owner's instruction that everything remaining ships in
v1.0.** The ladder had no rung above v0.5; this is it, and it unparks what was
parked. Nothing below is horizon work any more.

**The gate rule, ruled the same day: _both_.** Each of G-C, G-D, G-E and G-F must
carry a verdict — M1's own done-when has always accepted a measured miss as an
outcome — **and** the target is that each one clears. The distinction is kept
because one half is not fully in our control: G-D needs a judge to pass bars two
models have already missed, and no amount of work guarantees a model clears 0.95.
A miss, measured and recorded, is a shipped outcome; an *unmeasured* gate is not.

Scope, all of it:

- **EH1 — documents / PKM**, all fifteen (`TH1.01`–`TH1.16`), unparked. The
  largest unstarted block; `TH1.01` no longer gates `TH1.02`–`TH1.08`, so the
  parsers and block writers can run beside the metric definition.
- **E4 — hardening**, all seven: API keys and webhooks (`T4.01`–`T4.05`) and the
  two audit records (`T4.09`, `T4.10`). Unparked; "demand-gated" is satisfied.
- **M1 — measurement**, the remainder: `T2.124` → `T2.125` (G-D), `T2.131` (G-C),
  `T2.129`'s owed review, `T3.22` (G-E), `TH1.17` → `TH1.10` (G-F).
- **The research loop becomes operable, not just built** — a new task for the
  configuration and trigger surface on the web UI, because today `auto_research`
  has no writer anywhere in the tree and arming it means a manual database write.

**The scope above is prose, and prose assigns nothing.** The four bullets name
their tasks inside sentences, and both parsers own only `` - `Tid` `` list items
— so from this section's minting on 2026-08-15 until 2026-08-16, **every one of
the nineteen open tasks v1.0 carries showed `—` in `progress.md`'s Version
column**, the exact question that column was added to answer. The list below is
the same scope in the form the parsers read; it adds no task and moves none.

This is the h3-hole failure in a second dress, and `gen_progress.py`'s own
comment predicted the shape: *every test still passed on the misparse, because
the column and the ladder agreed with each other.* They agreed here too — the
prose was right, the column was empty, and nothing compared them.

**Done rows are deliberately absent**, on v0.1's stated precedent: the column
answers "which release?" for *open* work, so the EH1 and E4 tasks already `done`
carry no version and are not listed. The **gate-track** tasks are also absent
and stay `gate` — that section says it is "not a version", and listing them here
would silently overwrite the label, since this section is parsed after it.

- `T3.28` — Arm the research loop from the UI: configure, enable, trigger
- `T4.02` — Stamp `events.api_key_id` / `events.actor`
- `T4.03` — Exposed-deployment posture
- `T4.04` — `ApiKey` use surfaced in the per-object timeline
- `T4.05` — Push webhook receiver
- `T4.09` — In-process assumption audit
- `T4.10` — Multi-replica decision record
- `TH1.05` — `block_embeddings__<slug>` writer
- `TH1.06` — Semantic-only block channel
- `TH1.07` — Trace addendum: `block` id-kind, `document` layer
- `TH1.08` — Grounded Q&A flow
- `TH1.09` — Span-support faithfulness check before serving
- `TH1.11` — On-demand Tier-C lift
- `TH1.12` — Block-sourced facts, one document = one origin
- `TH1.13` — Idempotent lifting, keyed on `document_id`
- `TH1.14` — Single-document summary (unbadged)
- `TH1.15` — Emergent cross-document connections
- `TH1.16` — Documents UI, horizon-labelled
- `TH1.18` — Make `file_document` atomic by default

**The schema freeze is *not* in this version and must not be inferred from it.**
It happens after v1.0 ships and after the owner's review of the visual web UI
passes (owner ruling 2026-08-15, recorded in `CLAUDE.md`).

## Parked — kept, not dropped, no version assigned

**Nothing is parked any more.** EH1 documents/PKM (15 tasks), API keys and
webhooks (`T4.01`–`T4.05`) and the two audit records (`T4.09`, `T4.10`) were
parked here and were **unparked into v1.0 on 2026-08-15** by the owner's
instruction that everything remaining ships in that version. This section is kept
for the rule it states rather than for its contents.
**`T1.54` was on this list and is not parked — it shipped `done` and rides in
v0.5's tag** (corrected 2026-08-15, found by that version's review: a "here is
the full list" sentence naming a task that had already landed).
Parked work stops implying imminent effort; it is not dropped, and a
drop is a different status with a different obligation (`progress.md`'s status
vocabulary).
