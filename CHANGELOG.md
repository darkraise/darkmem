# Changelog

What changed, per release. One user, one dev environment — this is a "what got
better" log, not release notes for strangers. The ladder is
`docs/planning/RELEASES.md`.

## v0.5 — 2026-08-15

**An agent can now research a subject and file what it found as ordinary
memories, with one origin per source it actually read.** That last clause is the
whole feature: corroboration counts distinct origins, so a loop that refetches
the same page twice would manufacture its own agreement. The loop is **built and
not armed** — `research_run` refuses while the `auto_research` config row is
disabled, which is the default, and pointing it at real subjects is a separate
decision.

### Added
- The research loop, filing through the ordinary capture door (`T3.07`). One
  batch call per run, so a run either lands whole or does not land: an
  over-budget run refuses rather than filing a truncated version of what it
  found. It ships with **no `JobRegistry` job on purpose** — a cron'd research
  pass would refetch the same sources every tick, which is exactly the
  manufactured-corroboration hazard the origin rule exists to prevent.
- Its one door is MCP, and that is an argument rather than a convenience
  (`T3.27`). `research_run` files evidence *the caller* gathered:
  `ResearchGatherer` has no in-tree implementation by design, because a model
  without web access would invent sources. On MCP the caller is a gatherer; on
  REST neither caller is, so an honest REST shape would need the gatherer the
  design refuses. The tool takes no `source`, no `origin_key` and no `ctx`, so
  the header ladder that steers every other capture's identity has no route in,
  and a finding naming either field is a loud error rather than a dropped key.
- Distinct-origin stamping for researched sources (`T3.08`). One origin per
  evidence **source** — the identity is the source's, never the run's and never
  the finding's — and the canonicalisation aims to collapse the variation a
  fetcher produces mechanically, so that a refetch, a re-run or a paraphrase of
  one page adds no origin. That is a tested property held by generated-spelling
  tests and named pins, not a structural guarantee: three earlier restatements
  of it as a closure did not survive their reviews, and every falsification so
  far is pinned. Researched
  origins stay machine-distinguishable from observed ones, so a measurement that
  pools them does it on purpose.

### Changed
- The census's independence disclosure counts by connected component rather than
  by row (`T2.123`). A component of k mutually-duplicate rows yields k(k−1)/2
  findings and collapses k−1 rows, so the old arithmetic was right only while
  every component was exactly two wide. Entailed corrected 166 → 167;
  contradicted unchanged at 80/78.
- `SINGLE_VALUED_RELATIONS` stays empty, and now says why (`T2.120`). All
  sixteen relations fail the at-most-one-object-per-subject test, and every
  exclusive slot in the misses that motivated it is an **attribute** — port,
  version, TTL, scrape interval — which this taxonomy does not store as a
  relation at all. The hoped-for capacity cannot be added at any membership,
  so the argument lives beside the frozenset rather than being quietly dropped.

### Fixed
- **The origin canonicaliser split one page into two origins**, found by review
  before the loop was armed (`T3.08`). Six spellings did it —
  percent-encoded paths, percent-encoded unreserved characters, dot-segments,
  punycode versus unicode, NFC versus NFD, a duplicated identical parameter —
  and each is a
  spelling this repo's own `httpx` produces. Two variants seven days apart met
  the two-origin bar, which is a promotion off a single page. Repaired
  merge-only, with all seven failing shapes proven red first and three
  over-merge controls guarding the other direction.
- **And the same claim was falsified a second time, before this release was
  cut.** v0.5's version review attacked the repaired canonicaliser with 26
  same-source pairs and found **nine more splits**. The one that matters: this
  module normalised hosts through Python's IDNA**2003** codec while `httpx`
  emits IDNA**2008**, so `straße.example` and the `xn--strae-oqa.example` the
  client produces for it were two attributable origins — one page, and at seven
  days' spacing a promotion. The host pass now uses the `idna` package with
  `httpx`'s own parameters, which also stopped IDNA2003 conflating
  `strasse.example` with `straße.example`, two genuinely different hosts. The
  other eight: a trailing-dot FQDN keeping its dot once a default port came
  off, `:0443` not recognised as `:443`, IPv6 zero-compression, a
  scheme-relative href written without its slashes, an embedded tab or newline
  the URL spec strips, dot-segments popping past the root and gluing the path
  onto the host, and an unparseable id falling back to its pre-normalisation
  spelling.
- **And that repair needed a repair, which is the part worth reading.** It
  reattached a non-default port to the host *before* the trailing-dot, IPv6 and
  IDNA passes ran — so it relocated the ordering bug rather than removing it,
  and every one of those passes stopped working whenever a port was present.
  Worse, strict `idna.encode` raises on the embedded colon where the old
  IDNA2003 codec had tolerated it, so the fix for "one page must not become two
  origins" *created* exactly that failure for an IDN host carrying a port. The
  port is now split off before any canonicalisation and reattached at the end.
  Found by the review of the fix, not by the fix's own tests.
- **And the repair of the repair did it again, which settled the approach.**
  Widening the slash fold to one slash made `tmp` the host of
  `file:/tmp/a.pdf` — the spelling `httpx` itself emits for
  `file:///tmp/a.pdf` — so the third consecutive hand-written repair
  introduced the split class it was closing, again found by the review rather
  than by the fix's own tests. The fold is now scheme-aware (no single slash
  rule is correct for both `https:` and `file:`), and the suite carries the
  reviewers' own instrument instead of relying on hand-written pairs: a
  deterministic generator produces URL spellings mechanically and asserts
  every one agrees with the spelling `httpx` emits for it. On its first run
  that property found three splits no review round had seen — percent-encoded
  hosts, percent-encoded NFD bytes in paths and query values, a leading-zero
  non-default port — each repaired red-first.
- Two fail-open defects in the research loop, also found by review (`T3.07`).
  `bool("false")` is `True`, so a malformed `enabled` value armed the master
  switch — the one field where failing closed matters most was the one without a
  strict guard. And the run committed twice, so a raise in the journal window
  reported a durable filing as failed and would have double-filed on retry.
- The judge-verdicts directory leaked synthetic files under real judge
  identities (`T2.122`). It held 96 files rather than the 80 first measured — a
  stray `verdicts/verdicts/` subdirectory carried 16 more, left by an earlier
  unfinished manual quarantine. 95 removed, the 1 genuine artifact kept with its
  sha recorded outside the gitignored directory.

### Known limits
- **"Merge-only by construction" is retired as a phrase.** It has been stated
  as a structural guarantee twice and falsified twice, by the only two parties
  who attacked it on purpose. It is a tested property with named pins, and the
  next person to extend the canonicaliser should assume there are more splits
  nobody has looked for. Two are deliberate: `;` versus `&` in a query is not
  variation a fetcher produces, and two punycode labels decoding to different
  strings are different hosts.
- **Built is not armed, and armed is not measured.** The loop refuses by
  default. When it is armed, the origins it mints are weaker corroboration than
  independent capture produces: two same-day research origins carry the same
  source kind, so there is no kind diversity between them and they hold at three
  rather than promoting at two.
- **The entailment census is not clean, and the disclosure stands even though
  the verdict does not move** (`T2.118`). Five duplicated entailed propositions
  across seven findings, one component three rows wide, and five of Rule B's 72
  entailed rows restate propositions from the contacted population. The minimum
  pass is 156/173 rows against a measured 0.9827, so the verdict is
  unthreatened — that is a reason to report the duplication, not to stop
  counting it.
- G-C and G-D are still open, so a promoted fact still serves as `candidate`
  with `verification_unmeasured`. Nothing in this release changes what a badge
  means.

### Also in this tag
Gate-track work that landed after v0.5's scope closed. It ships here without
being part of the headline, because the gate track is not a version
(`docs/planning/RELEASES.md`):
- The homelab instance is provisioned fresh on the baseline, with nightly
  backups that actually prune — the dump script had no retention, and an
  unpruned nightly cadence on the host that also runs the database is a slow
  disk-fill that takes production down with it (`T1.54`).
- Qualification records are per consumer **role** over one judge identity, so
  the article consumer stops being gated on a discrimination it never makes
  (`T2.117`).
- G-C's and the judge's bars are floors at runtime, not only in source: a
  `config` row below a floor clamps back unless a licence names the parameter
  and cites its argument, the direction is carried **per bar** because G-C's six
  do not share one, and a clamped run now says so in the artifact rather than
  only in a log nobody configured (`T2.126`, `T2.127`, `T2.128`).
- The promotion corpus grew past the decidable band and the deterministic
  contradiction detector was armed, giving the false-promotion audit a
  numerator for the first time (`T2.129`). Measuring what that verdict was
  worth showed the rule itself was a coin flip at the bar at every sample
  size, so it is now scored on the exact Clopper-Pearson upper bound rather
  than the observed
  rate — a strict tightening that moved no bar and flipped the audit axis from
  a pass to a fail (`T2.130`, `T2.132`).

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
- G-E's two bars are stated and pinned, and the runner that reads production
  coverage now exists — but nothing has measured them. Its first run against
  production reports 0 live articles and *not evaluable*, which is the honest
  standing state while G-D is open rather than a fault.
- Synthesis needs corroborated facts, and no fact has ever left `candidate` on
  this machine. A fresh install will correctly show no articles at all.

### Also in this tag
Gate-track hardening landed after v0.4's own scope closed. It ships in this
tag without being part of the release's headline, because the gate track is
not a version (`docs/planning/RELEASES.md`):
- The entailment gold's resample certification is now bound to the pairs it
  certified, so a verdict flipped after a sitting turns eligibility red
  instead of leaving it green on a certification of a different file.
- G-D's anti-tuning disclosure now counts contacts with the gold's *pairs*
  rather than its file bytes. Editing a rationale — or writing the
  certification into the file — used to reset that counter silently.
- The coverage-distribution runner behind G-E, read-only against production.

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
