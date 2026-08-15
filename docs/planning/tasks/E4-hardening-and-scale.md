# E4 — Phase 4: Hardening & scale

**Goal:** `ApiKey` activation + exposed-deployment posture, the repo push webhook, inject
`watch` mode, auto-scrape opt-in, and the multi-replica decision if ever taken.

**Advance gate:** **demand-gated.** An actual exposed deployment — or a concrete second
consumer — opens this phase. Nothing in Phases 0–3 depends on it (doc 20 §10).

**Epic branch:** `feat/e4-hardening-and-scale`

**Contract:** [`../agent-runbook.md`](../agent-runbook.md). Amendments log at the bottom.

**Do not start this epic speculatively.** Every task here is a response to a real
deployment fact. Building it early means maintaining an exposed-deployment posture for a
system that is not exposed — cost with no corresponding risk reduction. The trigger is an
event, not a score.

**Trust posture is additive here, never replaced.** Every LAN rule stays unchanged
underneath: the MCP Host allowlist, trust-on-first-use setup then 403, single-door
ratification, and the rule that a LAN `421` is fixed by extending the allowlist rather
than disabling the check (invariants 20, 21).

---

## Lane A — `ApiKey` activation

#### T4.01 — Bearer credential shape + closed scope set

`Model: Opus 5` · `Effort: high` · `Size: M` · `Trigger: first exposed deployment` · `Depends: T1.62` · `Doc: 18 §5` · `Tag: activation` · `Gate: demand-gated`

**What.** The `api_keys` table exists today and is unwired — every write passes
`api_key_id=None`. Wire it to `dmk_<key_id>_<secret>` with a closed scope set:
`capture` / `read` / `admin`, plus an optional MCP bearer. **`ratify` is deliberately
never a scope** — machine ratification would collapse the human ceiling the whole
verification ladder rests on.

**Activation bar:** first exposed deployment, or a push-webhook receiver needing a
non-LAN credential. An event trigger, not a scored metric.

**Done when:**
- [ ] Key format parsed and verified in constant time
- [ ] Scope set is closed; an unknown scope is rejected at issue time
- [ ] No code path can grant or check a `ratify` scope, proven by test
- [ ] Secrets stored hashed; the plaintext is shown once at issue and never again

**Verify.** `cd backend && python -m pytest tests/test_api_keys.py -q`

#### T4.02 — Stamp `events.api_key_id` / `events.actor`

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T4.01, T1.06` · `Doc: 18 §5` · `Tag: activation` · `Gate: demand-gated`

**What.** First writer to the columns landed inert in T1.06. Every keyed call stamps its
key and actor.

**Done when:** every keyed call stamps both; unkeyed LAN calls still journal with a null
key rather than being dropped; the columns lose their inert label.
**Verify.** `cd backend && python -m pytest tests/test_events_actor.py -q`

#### T4.03 — Exposed-deployment posture

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T4.01` · `Doc: 18 §4, §9` · `Tag: activation` · `Gate: demand-gated`

**What.** Under exposure an operator TLS proxy sits in front, so the IP-source strategy
flips **back** to the header path and `cookie_secure` is enforced.

**The base posture is app-as-edge, not nginx.** T1.62 ships one image with the app as
the edge, `trust_proxy_headers` **off**, and the limiter reading the transport peer
(docs 19 §5, 18 §4). This task is the exposed-deployment case where a trusted proxy
exists again — it re-enables the header strategy T1.62 kept live and tested; it does
not restore nginx as the default.

**Done when:**
- [ ] With a trusted proxy in front, `trust_proxy_headers` on and the limiter reads the
      proxy's own header (`X-Real-IP`) — **never** the spoofable leftmost
      `X-Forwarded-For`, which is trusted in no posture
- [ ] `cookie_secure` enforced when exposed; the tri-state LAN behaviour is unchanged
- [ ] Login rate limiting and lockout verified against the proxied IP
- [ ] A deployment checklist documents the operator's TLS responsibility

**Verify.** `cd backend && python -m pytest tests/test_auth_security.py tests/test_client_ip_attribution.py -q`

#### T4.04 — `ApiKey` use surfaced in the per-object timeline

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T4.02` · `Doc: 13 §6.4` · `Tag: activation` · `Gate: demand-gated`

**What.** Keyed calls become visible in the timeline — who did what, with which key.

**Done when:** timeline shows key label and actor; key management UI can revoke; a revoked
key's history survives.
**Verify.** `cd frontend && npm test -- timeline`

---

## Lane B — repo push webhook

**Entry condition: T4.01 shipped** — the webhook needs an externally reachable
authenticated receiver.

#### T4.05 — Push webhook receiver

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T4.01, T1.40` · `Doc: 10 §5, 15 §9` · `Tag: target-new` · `Gate: demand-gated`

**What.** Replaces periodic change-gated `repo_sync` polling **for the pushed repo only**,
reusing the identical change-gated `CodePipeline.run`. **Never a second indexing path.**

**Done when:**
- [ ] The webhook calls the same pipeline entry point as polling, proven by test
- [ ] Signature verification before any work
- [ ] Polling remains for repos without a webhook; the two never double-index
- [ ] An unchanged HEAD short-circuits exactly as polling does

**Verify.** `cd backend && python -m pytest tests/test_push_webhook.py -q`

---

## Lane C — inject `watch` and auto-scrape

#### T4.06 — Inject `watch` mode

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T3.11` · `Doc: 15 §3.5` · `Tag: target-new` · `Gate: demand-gated`

**What.** Re-inject the managed block as the project, open file, or declared context
shifts, instead of only at session start. Config-gated, deferred behind measured need.

**Done when:** off by default; every re-inject journals so the human can see the swap; the
curb control (T3.19) stops it immediately.
**Verify.** `cd backend && python -m pytest tests/test_inject_watch.py -q`

#### T4.07 — Auto-scrape opt-in

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T3.15` · `Doc: 15 §4` · `Tag: target-new` · `Gate: demand-gated`

**What.** Widens v1's human-triggered-selection-only scope to automatic full-conversation
capture — strictly opt-in.

**Done when:** off by default and per-install opt-in; the `origin_key` still collapses one
install to one origin; a clear indicator shows when it is active.
**Verify.** Extension integration test with auto-capture enabled.

#### T4.08 — Watch + curb surfaces on the Distribution tab

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T4.06` · `Doc: 13 §6.5` · `Tag: target-new` · `Gate: demand-gated`

**What.** The human can see and curb push — never a silent context swap.

**Done when:** watch state visible per target; curb is one control and takes effect
immediately; recent injects listed inline.
**Verify.** `cd frontend && npm test -- distribution`

---

## Lane D — the multi-replica decision

#### T4.09 — In-process assumption audit

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: —` · `Doc: 02 §11` · `Tag: target-new` · `Gate: demand-gated`

**What.** Before any replica decision, enumerate every in-process assumption that a second
worker breaks: the cached PPR/igraph snapshot (T2.32), the feature-flag TTL cache, the
entity-embedding LRU, and every per-job `asyncio.Lock`.

**Done when:** every assumption listed with its owning code path and the concrete failure
a second worker causes; written up as a decision input, not a plan.
**Verify.** Audit reviewed at Fable tier against doc 02 §11 and invariant 13.

#### T4.10 — Multi-replica decision record

`Model: Fable 5` · `Effort: high` · `Size: M` · `Depends: T4.09` · `Doc: 02 §11, 20 §9` · `Tag: target-new` · `Gate: demand-gated`

**What.** Decide: sticky routing, a serialised snapshot table, or stay single-worker.
**This stays a flagged decision, never a side effect of a deployment task** — a replica
count changed during an unrelated ops change is how invariant 13 gets broken silently.

**Done when:** the decision and its rationale recorded; if taken, each T4.09 assumption
has a named mitigation; if not taken, the single-worker constraint is re-asserted in
`CLAUDE.md`.
**Verify.** Decision record committed under `docs/design/` or `docs/planning/`.

---

## Lane E — floor hazards

#### T4.11 — `seed_partition` leaves a half-registered fingerprint

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: —` · `Doc: 04 §5.3` · `Tag: target-new` · `Gate: —`

**Minted 2026-08-16**, found by T4.05 while its own new test crashed on it. T4.05
worked around it locally (`vector_repo=None`, the `test_code_fail_stale.py` idiom)
rather than reaching into pipeline internals, which was right for its tier.

**What.** `tests/test_memory_dream.py`'s `seed_partition` helper (`:92`) inserts an
`embedders` row and creates **only** the `memory_embeddings__<slug>` child table.
`embedder_registry.register` creates the **full** partition set for a fingerprint;
this helper bypasses it. The result is a registered fingerprint whose other
partitions — `code_chunk_embeddings__t212_embedder_4` among them — do not exist.

The reported symptom: any later test in the same suite that runs a real first-index
`CodePipeline.run` with a live `vector_repo` crashes, plus a secondary
`MissingGreenlet` out of `code_pipeline.py`'s exception-cleanup path. **The floor is
green today** — this bites only tests of that shape, which is why it has survived.
TH1.06 is the next task likely to write one.

**The mechanism is established** — traced end to end by T4.05's Fable review
(2026-08-16), so this task implements rather than investigates:

1. `build_pair` (`test_memory_dream.py:758`) calls `seed_partition` on the
   **`committing`** factory, so the `embedders` row is durable rather than rolled
   back — that is how a helper documented as living "inside the rollback-isolated
   session" leaves residue.
2. The `committing` fixture's teardown (`:728-743`) cleans memories, tags and
   config — **not** the `embedders` row and not the partition.
3. `delete_code_chunks_by_repo` / `delete_code_chunks_by_file`
   (`repositories/vector.py:735-757`) iterate **every** `embedders` fingerprint and
   DELETE against `code_chunk_embeddings__<slug>`. A fingerprint with no such child
   table raises `UndefinedTable`.

**It is wider than first reported:** `test_the_canary_beats_a_configured_sentinel`
(`:996`) durably seeds `t212-embedder|0` the same way.

**The production invariant is intact.** `embedder_registry.register` always creates
the full partition set; this is purely a test fixture violating that invariant. So
**hardening `delete_code_chunks_by_repo` would be treating the symptom** — do not.
The fix belongs to `test_memory_dream.py` (T2.12's suite).

**Done when:**
- [ ] No half-registered fingerprint survives a test — either the committing
      teardown removes the `embedders` rows and their partitions, or
      `seed_partition` seeds all four child tables
- [ ] Both durable seeds are covered (`t212-embedder|4` and `t212-embedder|0`)
- [ ] The helper's offline property is preserved (the suite must not need a live
      embedder)
- [ ] A regression test fails without the fix — a real first-index
      `CodePipeline.run` with a live `vector_repo` after `test_memory_dream`
- [ ] `delete_code_chunks_by_repo` is **not** modified
- [ ] The secondary `MissingGreenlet` in `code_pipeline.py`'s exception-cleanup path
      is either fixed or recorded with its own reason

**Verify.** `cd backend && python -m pytest tests/test_memory_dream.py tests/test_push_webhook.py -q`, then the full floor.

#### T4.12 — The `frontend test` gate step must degrade in duration, not in verdict

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: —` · `Doc: —` · `Tag: target-new` · `Gate: —`

**Minted 2026-08-16.** `progress.md` has characterised this failure twice and both
times recorded that the real fix is **unowned**. This owns it.

**What.** `gate.sh`'s `frontend test` step reds on a loaded host for a reason no
diff caused, and the loop's stop condition 7 then halts a lane over the weather.
The 2026-08-15 characterisation is one-sided and conclusive: **14 failed / 789
passed under the gate at load 57 on 16 cores with ~4 GB in swap, against 811
passed in 20.16 s standalone on an idle host.** Every failure was a clock, never an
assertion, scattered across unrelated files; one worker could not even be killed.

**The cause is config, and it is absent rather than wrong.**
`frontend/vitest.config.ts` sets `environment`, `globals`, `setupFiles` and
`exclude` — and **nothing else**. There is no `poolOptions`, no `maxForks`, no
`hookTimeout` and no `testTimeout`, so vitest sizes its fork pool to the host's CPU
count and uses the default 10 s hook timeout. That default is the exact string in
the failure record (`Hook timed out in 10000ms`).

**Bounding the pool and raising a timeout are not equally safe, and the task is
mostly the first.** Capping `maxForks` cannot mask a failure — it only serialises
work, so an assertion that would fail still fails. Raising `hookTimeout` **can**
mask a genuinely slow hook, which is a real regression this step exists to catch.
So: bound the pool, and raise a timeout only as far as evidence supports, with the
number justified rather than picked.

**Done when:**
- [ ] The fork pool is bounded so the step cannot saturate the host it runs on
- [ ] Any timeout change is justified against measured hook durations on an idle
      host, not chosen to make a red run pass
- [ ] The standalone suite is still green and **not materially slower** on an idle
      host — record both durations
- [ ] Evidence that the step now degrades in duration under load: run it under
      deliberate load and show it passing slower rather than failing
- [ ] `progress.md`'s two characterisation notes are updated to point here

**Note this is not the `activity.spec.ts` flake**, which is Playwright e2e in a
different gate step and fails on a missing element rather than on time. Do not
conflate them; that flake is separately open with four refuted hypotheses.

**Verify.** `cd frontend && npm test`, then `./scripts/gate.sh` on a host whose
`uptime` is recorded alongside the result.

#### T4.13 — The same fixture residue in T2.16's suite

`Model: Opus 5` · `Effort: high` · `Size: S` · `Depends: T4.11` · `Doc: 04 §5.3` · `Tag: target-new` · `Gate: —`

**Minted 2026-08-16.** T4.11 fixed the residue in `test_memory_dream.py` and its
new regression test — correctly, being general rather than special-cased —
immediately caught **a second instance of the identical defect** in
`tests/test_memory_relation_derivation.py` (T2.16's suite). T4.11 attempted the
same fix there, **broke 11 of that file's own tests, and reverted rather than
guessing at a suite it was not briefed on.** That was the right call and this task
is the consequence.

**What.** `test_memory_relation_derivation.py` carries the same shape as the one
T4.11 closed: `FP = "t216-embedder|4"` (`:35`), its own `committing` fixture
(`:52`) whose teardown (`:63-69`) deletes `memory_relations`, `entities` and
`memories` but **not** the `embedders` row or its partitions, and its own
`seed_partition` (`:151`). The durable half-registered fingerprint then makes
`delete_code_chunks_by_repo` raise `UndefinedTable` for any later test that drives
a real first-index with a live `vector_repo`.

**Why it is Opus-tier and not a copy-paste of T4.11.** The naive port fails, and
the reason is a real difference in the suite: **several of its tests rely on an
earlier test's partition surviving across test boundaries within the file**,
rather than reseeding it themselves. `test_memory_dream.py` does not share that
assumption. So a teardown that drops the partitions per test breaks them. The task
is to make the residue not escape the *file* while preserving whatever
within-file sharing its tests actually depend on — or to remove that dependency
deliberately, if the sharing turns out to be incidental rather than load-bearing.
Establish which it is before choosing.

**Done when:**
- [ ] No `t216-` embedder row or partition survives the file
- [ ] T4.11's regression test passes with this file in the same run
- [ ] Every test in `test_memory_relation_derivation.py` still passes, and any
      within-file partition sharing you removed is shown to have been incidental
- [ ] `delete_code_chunks_by_repo` is **not** modified — the production invariant
      is intact and this remains a fixture defect
- [ ] The full floor is green

**A third instance may exist.** Two suites had this independently, so sweep for the
pattern — a `committing` fixture plus a local `seed_partition` — rather than
assuming these are the only two. Report what the sweep found either way.

**Verify.** `cd backend && python -m pytest tests/test_memory_relation_derivation.py tests/test_memory_dream.py tests/test_push_webhook.py -q`, then the full floor.

---

## Amendment log

| Date | Task | Tier | Change | Why |
|---|---|---|---|---|
| 2026-08-15 | T4.09 | 3 (surfaced, **not** corrected) | **The audit landed** at `docs/planning/analyses/2026-08-15-t4.09-in-process-assumption-audit.md`: 35 assumptions, 16 BREAKS / 11 DEGRADES / 8 ALREADY SAFE. Two of the four assumptions T4.09's own text names do **not** break — the entity-embedding LRU is fingerprint-keyed at both tiers and correctness-safe, and the PPR snapshot is inert at `w_ppr = 0.0` so it costs nothing until the arm is activated. The one that does break (the per-job `asyncio.Lock`) breaks in five ways, only one of which is about a lock. Three divergences against **doc 02** are surfaced for the owner and deliberately left uncorrected under runbook §5's Tier-3 rule: §7's *"the only app-side caches are…"* sentence is false against the tree (at least eight more in `backend/app`); §11's remedy pair addresses 1 of 35 findings; and §10's invariant list omits the single-worker invariant that §8 and §11 both call load-bearing | T4.09's scope is unchanged — it was chartered to enumerate, and reporting a design doc's staleness is inside that charter while editing doc 02 is not. **What this changes for T4.10:** its option set as written ("sticky routing, a serialised snapshot table, or stay single-worker") is a remedy for the snapshot only; the three findings that would bite first — WebSocket fan-out, the job scheduler's absent lease, and the per-IP login limiter multiplying by N — need three different mitigation classes and none of them is sticky routing |
| 2026-08-16 | T4.01 | 2 | **Two honesty statements about `api_keys` are now false and were corrected in the same change**: doc 18 §5's parenthetical *"exists today, unwired — every write passes `api_key_id=None`"* (repeated at §1 line 17 and §10's invariant-23 bullet) and the comment at `0001_baseline.py:1028` saying *"Exists, unwired … the schema carries over unchanged"*. The baseline comment is corrected here; **doc 18's three are surfaced, not edited** — see the row below. Separately, **T4.03's `Done when` now inherits a shipped mechanism rather than a blank**: `require_scope` exists and is opt-in, so T4.03's work is assigning scopes to the existing surface, not designing the dependency. And **T4.05's entry condition is met**: the webhook's *"externally reachable authenticated receiver"* now has a credential to authenticate against | The activation is exactly what invariant 23's *named gap* language was holding open, so leaving those sentences would present a shipped path as dormant — the mirror of the failure that language exists to prevent. Recorded at Tier 2 rather than Tier 1 because it changes what T4.02–T4.05 inherit |
| 2026-08-16 | T4.01 | 3 (surfaced, **not** corrected) | **Doc 18 §5, §1 and §10 describe `api_keys` as dormant and unwired, which stopped being true with this commit.** §5's *"nothing claims this path is shipped"*, §1's honesty table entry, and §10's invariant-23 bullet each need the tense moved. The design itself needed no amendment — §5 was written to be a wiring task and it was one — so this is a staleness correction, not a design divergence. Also surfaced: **§11's stance that the first activation ships the REST bearer and leaves the MCP bearer to a second independent flip is what this task followed**, so T4.01's own `What` field (*"plus an optional MCP bearer"*) reads as if both ship together and should be re-scoped to T4.03 | Runbook §5 Tier 3: a design doc's text is the corpus, and the corpus wins until a human decides otherwise. Editing doc 18 to describe the tree is the right correction but it is the owner's, not an implementer's — and the divergence is one of tense, so nothing downstream is blocked on it |
| 2026-08-16 | T4.09 | 2 | **The 2026-08-15 T4.09 row above is superseded on its numbers: the inventory is 38 assumptions — 17 BREAKS / 13 DEGRADES / 8 ALREADY SAFE — and §11's remedy pair therefore addresses 1 of 38, not 1 of 35.** Two review rounds added three rows the original sweep missed: `reembed_locks`' 409-busy contract (item 36, BREAKS), the pipeline's 30-second classifier-resolution cache (item 37, DEGRADES — named in the audit's own §7 divergence list and then left out of its own census), and `entrypoint.sh`'s unserialised `alembic upgrade head` at container start (item 38, DEGRADES today and BREAKS after the schema freeze). Separately, **item 6's cursor census was short by four and is now seven**: `memory_dream_state`, `verification_recompute_state`, `contradiction_scan_state` and `article_synthesis_state` join the three it named, so a T4.10 mitigation scoped to "the three cursors item 6 names" would have left four unserialised. The seven are now derived by two committed greps rather than by eye, and the derivation is written into the analysis so the closure can be re-run. Item 33's *"the ladder needs nothing from T4.10"* is qualified in the same edit — true of the rung transition, false of the subsystem, since `verification_recompute`'s watermark is one of the four that were missing | Recorded as its own row rather than by editing the 2026-08-15 one, per this log's append-only rule (E1's 2026-07-28 T1.51 row states it). The number matters because doc 02 §11's option set is judged against it: "1 of 35" and "1 of 38" argue the same way, but a corpus stating one task's headline three different ways is the staleness shape invariant 23 exists for — and this was the **third** consecutive undercount of an enumeration whose completeness was the point, inside the document that convicts doc 02 §7 of exactly that. Which is why the fix is a mechanical derivation rather than a fourth careful reading. **No grade moved and no reasoning was revised**; the audit's verdicts and both ALREADY-SAFE exonerations survived review intact |
