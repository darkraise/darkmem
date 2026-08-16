# E4 epic-completion review — honest security posture, both directions

**Reviewer:** darkmem-reviewer-branch (Fable 5), 2026-08-16.
**Package:** `docs/planning/briefs/2026-08-16-e4-epic-review.md`. Scope: the union of the
19 named E4 commits on `feat/m1-measurement` (= `master`), reviewed through the named
lens. The interleaved TH1/EH1 work in the same range is out of scope per the package.
**Verification ran on `darkmem_test_3`** (targeted suites only, per the controller's
routing note): `test_api_keys.py` + `test_exposed_deployment_posture.py` +
`test_events_actor.py` — **132 passed**; plus one live mutation drill (below). No
measurement attempt spent, no gold touched, no bar moved, nothing pushed.

## Verdict

E4's engineering quality is high — T4.01's credential core, T4.06/T4.07's gating, and
T4.09→T4.10's decision chain are among the most careful work on this branch, and the
underclaim T4.04 closed (the "dormant" settings card) was real and correctly reversed.
But the lens finds one Critical and four Important defects, and the Critical is the
lens's own shape: **the branch ships three surfaces that describe keyed-call
observability the tree does not have.** Every one is a cross-task seam — each task's
own Done-when held in isolation; the drift is only visible across the four Lane-A
tasks at once.

Per the package's rule, these are follow-up tasks to mint, not merge blocks (E4 is
merged per task). **E4.F1 and E4.F2 below should land before v1.0 is called cut**;
the rest are ownable after.

---

## Findings

### Critical

**C1 — The keyed path journals nothing, while three shipped surfaces claim it does.**
Doc 18 §5's convention 8 (line 135) is explicit: *"Every keyed call stamps
`events.api_key_id` and `events.actor` … doc 13's settings surface lists keys with
`last_used_at` so a stale key is visible before it is a liability."* The tree, at HEAD:

- `backend/app/api/routes/repos.py:279` — the **only keyed route in the tree**
  (`repo_push_webhook`) receives its `Principal` and discards it
  (`_principal=Depends(_require_repo_admin)`, never read). The run it spawns journals
  `repo_indexed` through `backend/app/services/index_debt.py:217` with **no `actor`
  and no `api_key_id` parameter at all**.
- `backend/app/services/api_keys.py:31-35` — the module docstring assigns the
  `last_used_at` bump to "T4.02's per-call stamping". T4.02 closed without it;
  `rg last_used_at app/` shows **zero writers** of `api_keys.last_used_at` anywhere.
- Grep across `backend/app`: **no call site ever passes a non-None `api_key_id`** to
  any event write. T4.02 stamped the capture doors — which no key can reach (no
  capture-scope route exists) — and proved the keyed case only against a throwaway
  test app (`tests/test_events_actor.py:13-16` says so honestly).

Three surfaces assert the opposite:

- `frontend/src/features/settings/components/security-tab.tsx:562-564` renders
  `last_used_at ? "last used …" : "never used"` — **a key authenticating the webhook
  daily reads "never used", forever.** The card's own idiom for an unwired field
  (`UnavailableRow`, "never approximated — ruling 4") exists twenty lines up and was
  not used; an unwired column renders as a fabricated verdict instead.
- `docs/runbook-exposed-deployment.md:56-57` — "the key's history in the timeline
  survives its revocation": no keyed call ever enters any timeline, so the history
  being preserved is empty by construction.
- `frontend/src/features/memories/components/memory-event-timeline.tsx` — T4.04's
  attribution renderer (key badge, revoked note, unresolved marker) can never display
  a real keyed row: keys cannot reach memory routes, and the one keyed route stamps
  nothing. The whole path was verified against synthetic events only.

**Concrete failure:** on the exposed deployment this epic exists for, an operator
cannot detect the use of a leaked credential from any surface the product gives them —
the key list says "never used" for a key in active use, and the journal carries no row
naming it. Doc 18 §5 designed this exact observability; the activation shipped without
it while the surfaces shipped as if with it. This is the dishonest-security-surface
failure in the overclaim direction, on the audit surfaces themselves.

**Fix shape (E4.F1):** stamp `actor`/`api_key_id` from the webhook's `Principal` into
its journal write (thread through `_spawn_repo_index` → `index_debt.journal`), and bump
`last_used_at` beside it, per the api_keys.py docstring's own plan. Until the bump
lands, render the settings card's last-used cell as the honest gap the card already
knows how to render. Fold in T4.02's found-not-fixed `analytics.py`
`reprocess_all`/`reprocess_all_stream` `actor=NULL` — same mechanical shape.

### Important

**I1 — `capture` and `read` scopes are grantable, advertised, and gate nothing
(dropped handoff T4.01 → T4.03).**
`app/api/auth.py:160-168`'s docstring says scope assignment to the existing surface
"is still T4.03's". The E4 amendment log (2026-08-16, T4.01, Tier 2) assigned it there
too. T4.03 shipped posture only; the epic closed 13/13; the work is now assigned to a
closed task, i.e. to nobody. At HEAD, `require_scope` has exactly one consumer
(`repos.py:31`, `admin`, webhook only — pinned by
`tests/test_api_keys.py::TestRuntimeScopeGatedRoutes`). Meanwhile:

- `docs/runbook-exposed-deployment.md:50-54` (§3) tells the exposed-deployment
  operator "Non-human callers use an API key … with a closed scope set (`capture`,
  `read`, `admin`)" — but a `capture` or `read` key authenticates against **zero
  routes**; `POST /memories` is JWT-session-only.
- `security-tab.tsx:475` tags the card "live", defaults the scope input to `read`
  (:460), and offers "capture / read / admin" placeholders — minting credentials that
  cannot authenticate anything.

**Concrete failure:** an operator designs their exposure around programmatic capture
keys the runbook promises, mints one, and every call 401s. The overclaim direction,
in the two surfaces an operator reads first. **Fix shape (E4.F2):** either assign
scopes to their route groups (the deferred work — a real design task) or, minimally,
state on the card and in runbook §3 that keys reach only the push webhook today and
`capture`/`read` are forward-declared. The second is one honest paragraph; the first
is the feature.

**I2 — Webhook/polling double-index: T4.05's "the two never double-index" is proven
only against a second webhook delivery, not against polling.**
`app/services/job_runners.py:39` — `make_repo_sync_runner` selects on `auto_sync`
alone and never reads `repo.status`; `app/services/code_pipeline.py:210` — `run()`
sets `status='indexing'` with no compare-and-swap. So a poll tick landing inside a
webhook-triggered run enters `CodePipeline.run` concurrently for the same repo: two
`git pull`s on one working tree, two index passes writing the same rows. The window
recurs on exactly the event the webhook exists for (HEAD moved). Pre-existing against
`reindex_repo` (polling ignored its status claim too), so not a regression E4
introduced — but T4.05's Done-when asserts the property and its tests count
invocations only across deliveries. T4.10's record already surfaced this
(the `make_repo_sync_runner` post-audit finding) with the suggested close — a CAS
status claim inside `run()` — explicitly "not this record's to implement". It is
currently unowned. **Fix shape (E4.F3):** the CAS claim T4.10's record names, plus a
status read in the poll loop; worth taking on single-process grounds alone, and must
land before webhooks are armed against a real deployment.

**I3 — `/mcp` under exposure: the named gap is one allowlist entry from armed, and
the corpus's standing advice points at that entry** (package claim 3).
The runbook (§2 bullet 4) is honest and nothing enforces it. Two facts sharpen the
weight question the package asks: (a) by default the Host allowlist *accidentally*
blocks proxied `/mcp` — a proxied request carries the public hostname, which is not
allowlisted, so it 421s; (b) the corpus's standing rule for a 421 — "fix it by
extending the allowlist, never by disabling the check" (CLAUDE.md, the settings card,
invariant 20/21) — is precisely the move that converts that accidental defence into
full public unauthenticated MCP. An operator whose remote MCP client 421s through the
proxy and follows the standing advice has published every MCP tool. **A runbook
sentence is not the right weight here.** Cheap enforcement exists: with
`trust_proxy_headers` on, a `/mcp` request carrying proxy-forwarded headers is by
definition not the LAN-direct traffic the trust model admits — refuse it, or at
minimum journal/warn so the posture surface can show "proxied /mcp traffic seen".
**Fix shape (E4.F4):** that guard (Opus-tier — it touches the trust model), or an
owner ruling explicitly accepting the runbook-only weight, recorded.

**I4 — Doc 18 still declares the credential path dormant, three times.**
`docs/design/18-security-auth-and-trust.md` §1 (line 17: "exists and is unwired —
every write passes `api_key_id=None`"), §5 (line 128: "nothing claims this path is
shipped"), §10 (line 248: "`api_keys` is dormant and unwired"). All false since
`7ec957ba`. Correctly escalated Tier-3 per runbook §5 (the corpus is the owner's to
edit) — but this is the *underclaim* direction in the trust-model document an
operator reads before exposing the box, i.e. the exact defect class T4.04 was minted
to close on the UI. It should be an owner action attached to v1.0, not archival
staleness. Bundle with T4.09's three doc 02 divergences as one owner docs pass.

### Minor

**M1 — The timeline's fifth attribution state collapses into "session"** (package
claim 4's answer). `memory-event-timeline.tsx:38-47`: when `useApiKeys` **errors**,
`keys` stays `undefined` forever, so `keyUnresolved` is `false` and a keyed row
renders with no key indication at all — the exact collapse the component's own
docstring (:14-17) forbids. The loading case is handled deliberately; the persistent-
error case is not distinguished from it. Thread `isError` and render "key:
unresolvable — key list unreadable".

**M2 — The clamp's diagnosability, and the topology it silently forecloses** (claim 1
residue). A plain-HTTP reverse proxy has no valid configuration: trust on → the
clamped Secure cookie is dropped by the browser over http and login silently loops;
trust off → every client shares the proxy's one limiter bucket and one attacker locks
out every user. And when the clamp does break login, every clamp report except the
boot log (`security-posture`, the settings card) sits behind the login it broke. The
runbook should name the unsupported topology in §1, and a login-time warning when
`trust_proxy_headers` is on and `X-Forwarded-Proto: http` arrives would put the
diagnosis at the symptom.

**M3 — The limiter's fallback arm is unit-tested only.** Both route-level lockout
tests in `test_exposed_deployment_posture.py` always send `X-Real-IP`; the
rightmost-XFF fallback path is pinned in `test_client_ip_attribution.py` as a unit
but never driven through the limiter. The composition is plausible but unproven.

**M4 — T4.05's "signature verification" Done-when was satisfied by bearer-credential
verification with no amendment-log record.** The substitution is defensible — docs
10 §5 / 15 §9 gate the webhook on "doc 18's exposed-endpoint auth", and an HMAC over
a payload nothing parses authenticates bytes nothing reads — but the task file's
checkbox and the brief's "signature verification is the guard this task most needs
drilled" now diverge from the tree with no recorded reasoning. Also worth one line in
the runbook: the bearer shape forecloses GitHub.com-native webhook delivery (GitHub
cannot set an `Authorization` header); self-hosted senders (Gitea, post-receive
scripts) can.

**M5 — Stale docstring:** `tests/test_events_actor.py:15-16` "since no shipped route
assigns a scope yet (T4.03)" — false since T4.05 wired the webhook.

**M6 — `vitest.config.ts:13`'s "half the host" has a floor of 2**, so on a 2-core
host the pool is the whole host; the pool-bounded test's title ("never takes more
than half the host") overstates what its own assertion checks. Cosmetic.

**M7 — `progress.md`'s T4.09 row cites fix-round sha `8426407e`**, which is not on
the branch (a lane worktree sha; the merged commits are `dcb74c2e`/`3eaa482a`).

---

## The package's six claims, attacked

1. **`trust_proxy_headers` as a TLS proxy** — the inference holds *in this tree
   today*: the only sanctioned reason to enable it is the operator TLS proxy, the
   nginx-in-image fallback is recorded-not-taken, and the coupling risk is stated at
   the property (config docstring, CLAUDE.md, progress row). Clamp-over-refuse is
   defensible given the three-way reporting (boot warning, posture field, settings
   copy — all verified live in the 132-test run), and clamping errs in the safe
   direction where the cited verification-bar precedent needed a licence escape
   because its unsafe direction was reachable. Residue in M2: the foreclosed
   plain-HTTP-proxy topology is undocumented, and the clamp's failure symptom is far
   from its only unauthenticated report.
2. **The limiter pair** — not vacuous. Test 1 rotates the leftmost XFF per attempt
   and asserts the 429 *arrives*; test 2 is the anti-lumping counterpart and would
   catch a one-bucket limiter. Both drive the real login route with a real
   `LoginRateLimiter`. Ran green on `darkmem_test_3`. The bucket-rotation route
   neither covers is a proxy that passes through client `X-Real-IP` or replaces XFF —
   operator misconfiguration, which runbook §2 names with its consequence and §4
   gives a live detection drill for. Residual: M3 (fallback arm unit-only).
3. **`/mcp` runbook sentence** — not the right weight; see I3, including the
   allowlist-advice interaction the runbook does not mention.
4. **Attribution's states** — the fourth (list loading) is handled deliberately and
   correctly; a fifth exists and is mishandled (persistent list-read failure, M1).
   Note also that all keyed states are presently unreachable with real data (C1).
5. **T4.09's enumeration** — re-checked rather than taken. The third round's diff
   matches its message; both census greps re-run at the pin `78e9566a`: exactly 7
   `*_STATE_CONFIG_KEY` definition sites, 18 `session.add(Config(` sites, 2
   `pg_insert(Config` + 1 split constructor = the honest 21. The config-writer set is
   **unchanged between the pin and HEAD** (diff empty), so E4's own later landings
   did not silently extend the census. Inventory table: 38 rows, last-column tally
   17 BREAKS / 13 DEGRADES / 8 ALREADY SAFE, matching the Counts line. One nit: M7.
6. **T4.12's extrapolation** — carries, because the conclusion no longer rests on it:
   the discriminating evidence is the measured cgroup differential (capped pool green
   at a 2000 M ceiling; unbounded pool OOM-killed rc 137 in 4 s; 3200 M control
   passes unbounded), with the ceiling picked before the runs. The 16-core ~4.3 GB
   figure is labelled arithmetic on measured per-worker RSS at 4 and 7 workers, and
   the timeouts were left alone against a measured 24× headroom. Sound. Nit: M6.

**Guard drill run by this review:** repointed `delete_repo` at the module-level
`_require_repo_admin` binding (the exact mutant T4.05's Important 3 was about) —
`TestRuntimeScopeGatedRoutes` went **2 failed**, reverted, **2 passed**. The runtime
closure pin bites; that finding's closure is real.

---

## Deferred minors and parked rulings — triage

| Item | Where recorded | Triage |
|---|---|---|
| T4.10 rec 1: replica-knob tripwire test (`--workers`, `WEB_CONCURRENCY`, `deploy.replicas` absent from all launch paths) | T4.10 record §"Recommended, deliberately not armed" | **Mint now** (E4.F5, Haiku, S). Arming was rightly outside T4.10's sanction, but the invariant is now called load-bearing in CLAUDE.md, the drift class is named as silent, and the corpus's own pattern for prose-that-must-not-rot is a scan. Cheap, mechanical, before v1.0. |
| T4.10 rec 2: process-state review rule | same | **Correctly parked** — adoption is the owner's; a review-process rule is not a tree change. |
| T4.09's three doc 02 divergences (§7 false cache inventory, §11's 1-of-38 menu, §10's missing invariant) | E4 amendment log 2026-08-15 | **Correctly parked** per runbook §5 Tier 3; bundle into the E4.F6 owner docs pass with I4. Not merge-blocking — doc 02 is architecture reference, not operator procedure. |
| Doc 18's three dormancy sentences | E4 amendment log 2026-08-16 (T4.01, Tier 3) | **Parked correctly on process, wrongly on urgency** — see I4. Owner action attached to v1.0 (E4.F6), because doc 18 is what an operator reads before exposing the box, and it currently understates the shipped attack/credential surface. |
| T4.02 found-not-fixed: `analytics.py` reprocess routes journal `actor=NULL` | T4.02 progress row | **Fold into E4.F1** — same mechanical shape as the stamping fix; not worth its own task. |
| T4.05 round-2 deferred minors: `del app.dependency_overrides[get_session]` latent coupling; 409 coverage by hand-set status | fix-round-2 brief | **Correctly parked** — the first is test-internal coupling with no current defect; the second is acceptable because the in-route commit is order-pinned. |
| `make_repo_sync_runner` never reads `repo.status` | T4.10 record §"post-audit finding" | **Must be owned** — this is I2 / E4.F3. Recorded twice now with a named close and no owner; a third recording without a task is how it becomes a 40th-class finding. |
| `wiki_generator` render-cache race | T4.09 audit closure note | **Correctly parked** — needs concurrent generation of one repo's wiki; narrow under single-worker, inventoried for any future T4.10 flip. |

The **gate ledger** carries no E4-scope deferred minors or parked rulings — E4 feeds
no gate claim (checked: zero `T4.`/`E4` references in `gate-ledger.md`; its four
deferred/parked entries all belong to the measurement track this review is
chartered not to touch).

---

## Must-fix tasks, at task granularity

| # | Task | Tier | Blocks |
|---|---|---|---|
| E4.F1 | Stamp the webhook's `Principal` (actor + `api_key_id`) into its journal write; bump `last_used_at` beside it; render the settings card's last-used cell honestly until then; fold in the analytics `actor=NULL` fix | Sonnet, S | **v1.0 cut** (C1) |
| E4.F2 | Scope honesty: state on the settings card and runbook §3 that keys reach only the push webhook today, or assign `capture`/`read` to their route groups (the latter is the deferred T4.03 work and needs its own brief) | Sonnet, S (copy) / Opus, M (assignment) | **v1.0 cut** (I1 — the copy half at minimum) |
| E4.F3 | CAS status claim inside `CodePipeline.run` + status read in the `repo_sync` poll loop (T4.10's own suggested close) | Sonnet, S | Arming webhooks on a real deployment (I2) |
| E4.F4 | Refuse or journal proxy-forwarded `/mcp` requests under `trust_proxy_headers`, or an owner ruling accepting runbook-only weight | Opus, S–M | The first actual exposure (I3) |
| E4.F5 | Replica-knob tripwire test | Haiku, S | — (before v1.0, cheap) |
| E4.F6 | Owner docs pass: doc 18 §1/§5/§10 tense (I4), doc 02's three divergences, plus M4's decision record and M5/M7 staleness | Owner + Haiku sweep | v1.0 docs freeze |
| E4.F7 | Minors sweep: M1 (timeline isError state), M2 (runbook unsupported-topology paragraph + login-time proto warning), M3 (fallback-arm route test), M6 | Sonnet, S | — (may ride any wave) |

**Bottom line:** E4's mechanisms are sound and its tests mostly bite — I broke one
guard on purpose and it caught the exact sanctioned-binding-reuse mutant it was built
for. What fails the lens is the seam no single task owned: the activation's
*observability* story (doc 18 §5 convention 8) fell through the T4.01→T4.02→T4.03
handoffs while the surfaces describing it shipped, leaving the branch overclaiming
keyed-call visibility in three places and underclaiming nothing. One small fix wave
(E4.F1 + E4.F2's copy half) makes the posture honest; the rest is ownable on the
timeline above.
