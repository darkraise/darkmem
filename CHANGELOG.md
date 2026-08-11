# Changelog

What changed, per release. One user, one dev environment — this is a "what got
better" log, not release notes for strangers. The ladder is
`docs/planning/RELEASES.md`.

## v0.2 — 2026-08-11

**Your agent can resume.** A run saves a compact digest, and the next session
loads it instead of reloading the context window it burned.

### Added
- Truth-first content fill for the managed block (`T3.10`): items are chosen
  under one token budget, verified rows first, with a cold-start pass that
  admits candidates only when nothing verified landed — under the *same*
  budget, so a cold-start block is never an over-budget one. An empty L3 tier
  yields an empty tier, never an error; every fresh install has zero articles.
- Resume as a specialised inject (`T3.17`): the latest checkpoint leads that
  same fill as its `lead`, charged against the same budget rather than
  computing a second one. A run with no checkpoint degrades to the ordinary
  inject — a first session has nothing to resume from, which is the common
  case, not a fault. A resume is journalled only when the digest actually
  survived the fill, so the stream counts resumes rather than session starts.
- The Session-checkpoints view is live (`T3.21`): per-run history grouped from
  the journal, the latest digest one click away, and copy-resume. Both doors
  now serve `resume_line` and `token_estimate` — derived from the resume path's
  own functions, so what you copy is what your session receives rather than a
  second rendering of it.

### Changed
- Checkpoints are pinned out of the vault by test, not by convention (`T3.18`):
  no fact-ladder reach, no verification column, no badge on the wire, no
  embedding partition. A checkpoint is what an agent said about its own run.
- `resumed` takes its recorded place in the activity taxonomy.

### Fixed
- The demo resume block spelled `darkmem:resume:begin` markers that no shipped
  code writes. Copied into a `CLAUDE.md`, the real writer would not have
  recognised them and would have appended a second, live marker pair beneath.

### Known limits
- Nothing writes a checkpoint automatically yet. The client half — the hook
  that authors a digest at session end and the one that loads it at session
  start — is the Claude Code plugin, which lives outside this repo.
- Verification, groundedness and coverage labels remain withheld pending G-C,
  G-D and G-E, exactly as in v0.1.

## v0.1 — 2026-08-10

First release. Everything below already existed and had never been tagged or
deployed.

### Added
- Buffered capture on four doors (REST + MCP, single and batch) with
  `origin_key` identity resolution.
- Hybrid retrieval — semantic + keyword under RRF, with an optional reranker.
- The entity/relationship graph, closed taxonomy, supersession, and
  fingerprint-partitioned embeddings.
- Code indexing: symbol graph, code search, blast radius, wiki.
- 21 scheduled jobs under one registry, including the Tier-C dream family —
  20 with real bodies; `article_synthesis` is still a registered placeholder,
  and its productive run is v0.4's.
- The verified-fact vault and its ladder — **badges serve as `candidate` until
  G-C and G-D clear**, which is deliberate, not a defect.
- Session checkpoints on both doors.
- The SPA: memories, knowledge, activity, code, settings.
- Minimal TypeScript and Python SDKs, generated from the live contract.
- A browser capture extension.

### Known limits
- Verification, groundedness and coverage labels are withheld pending G-C, G-D
  and G-E. The system ships **unlabelled** by design (`T2.95`).
- Data is disposable: the schema is not frozen and a schema change drops and
  recreates the database.
- The product version fields read `0.2.0` before this release and had never
  been managed or shipped under it. They reset to `0.1.0`, where the ladder
  starts.
