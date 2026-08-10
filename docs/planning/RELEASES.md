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

### v0.2 — Resume and checkpoints

- `T3.17` — Resume as a specialised inject
- `T3.18` — Checkpoints are operational, not vault knowledge
- `T3.21` — Session checkpoints / resume view

### v0.3 — Auto-context into agent tools

- `T3.10` — Truth-first content fill under a token budget
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

### Gate track

Not parked and not a version: these produce gates, which unlock labels. Clearing
G-C and G-D ships as its own version whose headline is "badges go live".

- `T2.114` — G-D third-vendor attempt
- `T2.116` — Bind the resample certification to the pairs it certified
- `T3.22` — G-E evidence run
- `T3.24` — Coverage-distribution runner
- `TH1.10` — Faithfulness ship gate (G-F evidence)
- `TH1.17` — Faithfulness-gate runner

## Parked — kept, not dropped, no version assigned

EH1 documents/PKM (15 tasks), the research agent (`T3.07`, `T3.08`), API keys
and webhooks (`T4.01`–`T4.05`), the two audit records (`T4.09`, `T4.10`), and
`T1.54`. Parked work stops implying imminent effort; it is not dropped, and a
drop is a different status with a different obligation (`progress.md`'s status
vocabulary).
