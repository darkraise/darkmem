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

`Model: Opus 5` · `Trigger: first exposed deployment` · `Depends: T1.62` · `Doc: 18 §5` · `Tag: activation` · `Gate: demand-gated`

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

`Model: Sonnet 5` · `Depends: T4.01, T1.06` · `Doc: 18 §5` · `Tag: activation` · `Gate: demand-gated`

**What.** First writer to the columns landed inert in T1.06. Every keyed call stamps its
key and actor.

**Done when:** every keyed call stamps both; unkeyed LAN calls still journal with a null
key rather than being dropped; the columns lose their inert label.
**Verify.** `cd backend && python -m pytest tests/test_events_actor.py -q`

#### T4.03 — Exposed-deployment posture

`Model: Opus 5` · `Depends: T4.01` · `Doc: 18 §4, §9` · `Tag: activation` · `Gate: demand-gated`

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

`Model: Sonnet 5` · `Depends: T4.02` · `Doc: 13 §6.4` · `Tag: activation` · `Gate: demand-gated`

**What.** Keyed calls become visible in the timeline — who did what, with which key.

**Done when:** timeline shows key label and actor; key management UI can revoke; a revoked
key's history survives.
**Verify.** `cd frontend && npm test -- timeline`

---

## Lane B — repo push webhook

**Entry condition: T4.01 shipped** — the webhook needs an externally reachable
authenticated receiver.

#### T4.05 — Push webhook receiver

`Model: Sonnet 5` · `Depends: T4.01, T1.40` · `Doc: 10 §5, 15 §9` · `Tag: target-new` · `Gate: demand-gated`

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

`Model: Sonnet 5` · `Depends: T3.11` · `Doc: 15 §3.5` · `Tag: target-new` · `Gate: demand-gated`

**What.** Re-inject the managed block as the project, open file, or declared context
shifts, instead of only at session start. Config-gated, deferred behind measured need.

**Done when:** off by default; every re-inject journals so the human can see the swap; the
curb control (T3.19) stops it immediately.
**Verify.** `cd backend && python -m pytest tests/test_inject_watch.py -q`

#### T4.07 — Auto-scrape opt-in

`Model: Sonnet 5` · `Depends: T3.15` · `Doc: 15 §4` · `Tag: target-new` · `Gate: demand-gated`

**What.** Widens v1's human-triggered-selection-only scope to automatic full-conversation
capture — strictly opt-in.

**Done when:** off by default and per-install opt-in; the `origin_key` still collapses one
install to one origin; a clear indicator shows when it is active.
**Verify.** Extension integration test with auto-capture enabled.

#### T4.08 — Watch + curb surfaces on the Distribution tab

`Model: Sonnet 5` · `Depends: T4.06` · `Doc: 13 §6.5` · `Tag: target-new` · `Gate: demand-gated`

**What.** The human can see and curb push — never a silent context swap.

**Done when:** watch state visible per target; curb is one control and takes effect
immediately; recent injects listed inline.
**Verify.** `cd frontend && npm test -- distribution`

---

## Lane D — the multi-replica decision

#### T4.09 — In-process assumption audit

`Model: Opus 5` · `Depends: —` · `Doc: 02 §11` · `Tag: target-new` · `Gate: demand-gated`

**What.** Before any replica decision, enumerate every in-process assumption that a second
worker breaks: the cached PPR/igraph snapshot (T2.32), the feature-flag TTL cache, the
entity-embedding LRU, and every per-job `asyncio.Lock`.

**Done when:** every assumption listed with its owning code path and the concrete failure
a second worker causes; written up as a decision input, not a plan.
**Verify.** Audit reviewed at Fable tier against doc 02 §11 and invariant 13.

#### T4.10 — Multi-replica decision record

`Model: Fable 5` · `Depends: T4.09` · `Doc: 02 §11, 20 §9` · `Tag: target-new` · `Gate: demand-gated`

**What.** Decide: sticky routing, a serialised snapshot table, or stay single-worker.
**This stays a flagged decision, never a side effect of a deployment task** — a replica
count changed during an unrelated ops change is how invariant 13 gets broken silently.

**Done when:** the decision and its rationale recorded; if taken, each T4.09 assumption
has a named mitigation; if not taken, the single-worker constraint is re-asserted in
`CLAUDE.md`.
**Verify.** Decision record committed under `docs/design/` or `docs/planning/`.

---

## Amendment log

| Date | Task | Tier | Change | Why |
|---|---|---|---|---|
| — | — | — | (none yet) | — |
