# Changelog

What changed, per release. One user, one dev environment — this is a "what got
better" log, not release notes for strangers. The ladder is
`docs/planning/RELEASES.md`.

## v0.4 — 2026-08-12

**The vault writes articles about your subjects, and every sentence has to earn
its place.** A subject with enough corroborated facts gets a synthesised
write-up whose claims each link to the fact that entails them. Nothing about
those articles is badged as verified yet — the groundedness gate is still open,
so they ship labelled `candidate`, which is what the label means rather than a
placeholder for it.

### Added
- Article synthesis runs for real (`T3.02`). A daily Tier-C pass picks eligible
  subjects, gathers only their non-disputed corroborated/confirmed facts, and
  stores one article per subject with the fact ids it was built from
  journalled, so a bad article is traceable to its inputs. Disputed and
  candidate facts are excluded at the query, never filtered out of a draft the
  model already saw.
- Claim-level entailment and coverage routing (`T3.03`). Every sentence is
  checked against the facts it cites, and an article below the coverage
  threshold routes to review instead of shipping. Coverage is served as
  "claim-support coverage" — the fraction of sentences a verified fact entails
  — because that is what the number is.
- The one hard foreign key (`T3.04`). A citation can never dangle, which is
  safe only because facts are invalidate-not-delete; both halves are now
  pinned by test, including two scans proving nothing in the tree deletes a
  fact.
- Staleness and debounced re-synthesis (`T3.05`). An article whose supporting
  facts moved is *labelled* stale and stays readable; re-synthesis waits for a
  quiet period so a burst of corroborations produces one rewrite rather than
  one per tick, then supersedes the old article and keeps the lineage.
- The Articles tab and article detail on live data (`T3.06`), with a read door
  the API contract named and nothing had built (`GET /knowledge/articles`,
  `/articles/{id}`, and MCP's `article_get`). Every claim's citation is one
  click away, and the coverage number shows in Simple as well as Advanced,
  because it is an honesty signal rather than technical detail.
- Articles joined retrieval as their own channel (`T3.23`), stale label
  included — a stale article is returned labelled, never withheld.
- A held re-synthesis now reaches a human. When a rewrite cannot be grounded,
  the *subject* is routed to review while the standing article keeps its badge
  and its place in retrieval; before this, a subject whose knowledge could no
  longer be grounded was visible only as a counter on a job tick.

### Changed
- An invalidated fact now makes its article stale. The staleness gate reads the
  verified **and still believed** set, so a fact whose belief window closed
  stops propping up an article that cites it (doc 09 §4.4, ruled and amended).
- A chronically ungroundable subject is no longer re-attempted every tick. It
  costs one attempt per change to its facts instead of one per day, and the
  attempts it skips are counted rather than silently not happening.

### Fixed
- The Playwright leg of the merge gate collided with any darkmem already
  running on `:8000` — and did not fail cleanly: it health-checked the other
  instance and aimed its admin-setup at it.
- A `subject_key` written without its type half took down the whole articles
  listing with a 500, and stopped the staleness sweep at its first odd row.

### Known limits
- **Articles ship unlabelled, deliberately.** Coverage cannot be measured until
  a verification judge qualifies (G-D), so every article reads `candidate` with
  its coverage shown as "not measured" — a measured absence, not a zero.
- G-E's two bars are stated and pinned but nothing has measured them: the
  runner that reads production coverage is still to come.
- Synthesis needs corroborated facts, and no fact has ever left `candidate` on
  this machine. A fresh install will correctly show no articles at all.

## v0.3 — 2026-08-11

**Context stays live, and visible.** Push can follow your working context
instead of only firing at session start — and everything it pushes is on
screen, per day and per target.

### Added
- Inject records render in the day timeline and the calendar (`T3.20`). A push
  names its target, its item count and its budget, and opens to show exactly
  what was pushed, per layer. The used-against-budget pair is the diagnostic
  half: a push that spent 40 of 4000 tokens and one that hit its ceiling look
  identical from the id list alone and mean different things about what the
  agent was *not* told. `/events/calendar` gained an `event_type` filter so the
  days holding an inject can be marked without counting rows client-side.
- Watch mode (`T4.06`): re-inject as the project, the open file or the declared
  context shifts. Off by default, and the opt-in is a config flag read at two
  doors. Every refresh journals what shifted — without that, a re-inject is
  indistinguishable from a session start and "you can see the swap" reduces to
  seeing that something was pushed twice.
- Auto-capture in the browser extension (`T4.07`), strictly opt-in. The chat
  surfaces are optional permissions the browser withholds until you grant them,
  so an install that never opted in cannot read those pages at all. Opting in
  captures from that point on; it does not send the conversation you already
  had. A `REC` badge shows while it is running.
- The Distribution tab now shows watch state per target, the curb, and a live
  inject log read from the journal (`T4.08`).

### Changed
- The curb is enforced server-side. A watch refresh re-reads it every time and
  refuses while it is on, so curbing stops the next swap rather than the next
  session — the client is the thing being curbed, which is why the client does
  not decide. The tab's copy said the flag had no enforcer; that stopped being
  true with watch mode and now says so.

### Fixed
- The demo resume block and the demo inject record were prose where the real
  branch reads a payload, so the mockups could not be expanded and could
  disagree with the live surfaces without any test noticing.

### Known limits
- Nothing drives watch mode yet: the client-side loop that would call it is the
  Claude Code plugin, outside this repo. The session-start inject still has no
  HTTP door, so the curb governs the watch cadence today and will govern that
  one the moment it has a caller.
- Verification, groundedness and coverage labels remain withheld pending G-C,
  G-D and G-E.

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
