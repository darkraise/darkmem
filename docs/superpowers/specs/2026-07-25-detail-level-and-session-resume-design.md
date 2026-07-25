# darkmem — Detail-level preference & session-resume checkpoints (design)

**Status:** design spec, dated 2026-07-25. Two post-corpus feature additions
requested after the design phase closed (docs/design/00–20). This spec is the
owning doc the corresponding `docs/planning/feature-epics.md` rows trace to; it
extends docs 13/14 (Feature 1) and docs 04/12/13/15 (Feature 2) without
re-opening a closed decision. Where it touches an existing mechanism it follows
that doc's pointer and never re-designs it.

## Why this spec exists

The design corpus is closed and Fable-reviewed; the feature-epics bridge promises
every row traces to an owning design doc. These two features are new decisions
with no corpus home, so they are recorded here rather than smuggled into a closed
doc, and the feature rows cite this spec.

---

## Feature 1 — Detail-level preference (Simple / Advanced view)

### Problem

The read surfaces render honest but technical detail — per-modality scores, the
fused `rrf_score`, the rerank score, the `rank_fusion_factor` arm breakdown,
embedder fingerprints, raw `config` keys, and doc-section references. For a
non-technical reader this is noise that makes the data hard to read. A display
preference should let such a reader hide the jargon without darkmem ever hiding
what it is honest about.

### Decision

A per-viewer **detail-level preference** with two values, `advanced` (default)
and `simple`. It is a client-side display preference (localStorage, per browser),
not runtime config and not a `config` row — it changes nothing the backend
computes or returns, only what the UI chooses to render. Default is `advanced`,
preserving today's honesty-first behaviour; `simple` is opt-in.

### The hard line — Simple hides jargon, never honesty (invariant 14)

`simple` may hide only **technical / numeric** detail:

- the per-row score breakdown (semantic / keyword / ppr / dual_level / rerank bars),
- the `rank_fusion_factor` arm breakdown (confidence / importance / heat / recency),
- the fused `rrf_score` value and the envelope `weights` line,
- raw ids, embedder fingerprints / slugs, `config` keys shown as jargon,
- doc-section references and other internal identifiers.

`simple` may **never** hide an honesty signal. These always render, in both modes
(invariant 14, doc 13 §8/§5.4):

- the verification badge (verbatim honest claim — `corroborated` / `confirmed` /
  `disputed` / `candidate`), never softened to "true"/"verified",
- the layer label, the superseded amber badge + lineage, the stale-article label,
- the exclusion counts (`by_project` / `by_status` / `by_context_conflict`),
  rendered as the plain human copy they already are ("3 facts excluded by context
  conflict") — surfaced, never buried,
- honest empty / error / degraded states.

In `simple`, the numeric breakdown collapses to one plain-language "why it ranked"
line (e.g. "Top match — strong text and keyword overlap, boosted for your
context") so the row still explains itself; it is a *rephrase*, not a drop.

### Scope of effect

The read / data surfaces: the Memories why-retrieved trace (the heaviest case),
and the numeric internals on memory / fact / article detail. The admin Settings
tabs (Flags, LLM, Jobs, …) are **unaffected** — an admin tuning `w_*` needs the
numbers regardless of this preference; a non-technical reader simply does not open
those tabs.

### Where it lives (IA)

The natural home is the **global chrome**, a segmented control next to the theme
switcher — detail-level is the same category of per-viewer display preference as
theme, so it belongs where theme lives (doc 13 §3 chrome, doc 14 §9), not inside
the flattened six-tab `/settings` runtime-config surface (doc 13 §7). The chrome
control *is* the setting.

### Owning docs & sequencing

Doc 13 (what each surface shows in simple vs advanced) + doc 14 (how simple
looks). Ships in **Phase 1** with the first advanced surface (the why-retrieved
trace, E1). Every later advanced surface (vault detail, flags) honours the same
flag through its own F9 callout — it is a UI-wide preference that grows with the
surfaces, not a per-phase feature.

### Mockups

- S03 (memories-trace): add a `simple` render state — the same panel with the
  score bars, arm breakdown, `rrf_score`, weights line, and id-tags removed, the
  badges / layer chips / claims / exclusion strip kept, and the numeric breakdown
  replaced by the plain "why it ranked" line.
- C03 (global chrome): add the detail-level segmented control to the topbar, with
  an annotation stating the localStorage/per-viewer persistence and the
  never-hide-honesty rule.

---

## Feature 2 — Session progress checkpoints + resume

### Problem

An agent runs a task overnight and fills a large context window. When a fresh
session resumes in the morning the prompt cache has expired, so reloading the
full context burns session and weekly limits before any work happens. darkmem
should let a run resume from a compact, durable digest — the progress, the
necessary items, and a summarised context — instead of reloading raw history.

### Decision — a server-side checkpoint surface in darkmem

darkmem grows a first-class **session-checkpoint** store, keyed on `origin_key`
(which already *is* the capture-session / agent-run identity, doc 05 §2.1). A
checkpoint is a compact, durable record of a run's progress. Checkpoints are
**operational**, not verified knowledge: they never enter the vault, carry no
verification badge, and are labelled as session digests.

### Data model (extends doc 04)

New table `session_checkpoints`:

- `id` uuidv7 PK; `project` text; `origin_key` text (the run identity, doc 05 §2.1);
- `title` text (short run label); `summary` text (the compact resumable digest prose);
- `state` jsonb — structured `{done[], next_steps[], decisions[], open_questions[],
  touched_files[], artifacts[]}`;
- `token_estimate` int (size of the resume block); `source` text (writing client,
  e.g. `claude-code-plugin`); `created_at` timestamptz default `now()`.
- Append-only history; the resume path reads the latest per `(project, origin_key)`.
  Partial/btree index `(project, origin_key, created_at DESC)` for the latest-lookup.
- A checkpoint write journals a `checkpoint_saved` `events` row; a resume journals
  `resumed` (doc 04 §8.1) so the run's timeline shows both.

The digest is authored by the **client** (the in-session model already holds the
context, so summarising there is the cheap place to do it) and stored server-side;
darkmem stores and serves, it does not re-summarise raw transcripts in v1. A
`summarization`-purpose (doc 11) server-side compaction endpoint is a possible
later addition, not v1.

### Contract (extends doc 12)

- REST: `POST /api/v1/checkpoints` (201), `GET /api/v1/checkpoints?project=&origin_key=&latest=true`,
  `GET /api/v1/checkpoints/{id}`, following the doc-12 REST conventions.
- MCP tools: `checkpoint_save`, `checkpoint_latest`, `checkpoint_list` — the
  LAN-trusted door the plugin calls. These are operational writes, never a
  ratification surface (doc 12's no-ratify-over-MCP stance is unaffected).

### Resume is a specialised inject (extends doc 15)

At session start the client fetches the latest checkpoint for `(project,
origin_key)` and writes its `summary` + `next_steps` into a marker-bounded
managed block in the tool's context file (Claude Code `CLAUDE.md`), reusing the
inject writer's strip-before-rewrite discipline (doc 15 §3.2) under the
`inject_token_budget`. This is the token-cost win: the fresh session loads a
~budgeted digest, not the full history. It is a *delivery*, not a second ranking
path (invariant 17).

### UI (extends doc 13)

A "Session checkpoints / Resume" view in the **Activity** shell (operational,
run-scoped): per-run checkpoint history, the latest resumable digest with
`next_steps`, the token estimate, and a copy-resume affordance; `checkpoint_saved`
and `resumed` markers surface in the run timeline. Rendered as operational
session digests — explicitly not vault knowledge, no verification badge.

### Sequencing (doc 20)

Committed home is **Phase 3** (distribution, E3), F-flow **F10** (the resume is a
push/inject) with an F1-style write for the checkpoint itself, gate **G-D**
(entry). The auto-inject-at-session-start half rides inject v1 (Phase 3). One
note: the store + a manual `/resume` command needs only `origin_key`, so that
half is **Phase-1-capable** and can be pulled forward without re-sequencing the
roadmap.

### Mockups

New Activity screen (S33): session-checkpoints / resume — populated (both themes),
empty, and the "resume block written to CLAUDE.md" state.

### The Claude Code plugin (planned this session, built later)

The client carrier lives in the marketplace repo `D:\Repositories\Personal\claude-code-plugins`:

- a `Stop` hook / `/darkmem-checkpoint` command that authors a compact progress
  digest in-session and `POST`s it (or MCP `checkpoint_save`), keyed on a stable
  `origin_key` per project/run;
- a `SessionStart` hook / `/darkmem-resume` command that fetches the latest
  checkpoint and writes the resume block into `CLAUDE.md`;
- MCP config written by `darkmem connect claude-code` (doc 15 §5).

**Scope this session is plan-only:** the marketplace repo is initialised with a
README + this plan; the actual plugin build is a separate brainstorm → plan →
build cycle. The darkmem-side subsystem (table, endpoints, MCP tools, UI) is the
Phase-3 roadmap item recorded in feature-epics.

---

## Deliverables (this session)

1. This spec (owning doc for the two feature rows).
2. `docs/planning/feature-epics.md`: an E1 row (detail-level preference) and an E3
   row (session checkpoints + resume), F9-callout mentions, and matrix rows.
3. Mockups: S03 simple state, C03 detail toggle, new S33 checkpoints screen;
   rebuild `index.html`.
4. `D:\Repositories\Personal\claude-code-plugins`: README + the plugin plan.

Non-goals this session: building the plugin; implementing the backend table /
endpoints (that is the Phase-3 implementation-planning phase, downstream of these
feature rows).
