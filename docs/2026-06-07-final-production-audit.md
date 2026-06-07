# Darkmem — Final Production-Release Audit (2026-06-07)

A definitive pre-release audit across **12 dimensions** covering every aspect, not
just deployment: security (auth, injection/SSRF, secrets/config), correctness
(domain invariants, code-graph/extraction), reliability/concurrency, performance/
scale, data/migrations, API contract, frontend, observability/ops, and testing.

Its purpose was twofold: (1) **verify** that the fixes from the prior audits — the
code-correctness audit (`2026-06-06-comprehensive-audit.md`, themes T1–T5), the
production-readiness audit (`2026-06-06-production-readiness.md`, 9 launch-blockers),
and the concurrency/leak/perf remediation (`2026-06-07-leak-perf-stuck-review.md`,
commit `c16adb0`) — actually hold in current code; and (2) **sweep fresh** for
anything still open, regressed, or newly introduced.

## Method

Twelve independent dimension auditors read the current code (not just prior docs),
each followed by an independent adversarial verifier that re-read the cited code
and confirmed, refuted, or re-rated every BLOCKER/HIGH/MED finding (29 agents
total). Every finding below was verified against current source. Severities are
rated for the target topology: **LAN / single-operator, Apache-2.0, loopback-bound
behind an operator-supplied TLS proxy.** One first-pass finding (the "reranker
still broken" claim) was **refuted on direct inspection** — see below.

## Verdict: GO (after the two release-blockers below, now fixed)

The system is **functionally and operationally sound**. The vast majority of prior
high-severity fixes verified as holding: the closed taxonomy and supersession
invariants (T4), the `chk_superseded` delete/PUT guards (T3), the hollowed-OO
code-graph fix (T5 — decorated functions, class methods, interface-default
self-calls now extracted), the frontend/backend taxonomy parity (T1), all nine ops
launch-blockers, and the entire `c16adb0` concurrency/leak set. The injection/SSRF
surface (clone-URL scheme allowlist, git arg-injection guard, no-rmtree-local_path,
SQL identifier sanitization), auth (algorithm-pinned JWT, token blocklist + refresh
rotation, password-change revocation, complete `require_auth` coverage), and data
integrity (FK cascades, fingerprint partitioning, idempotent re-extraction) are all
verified solid.

The audit surfaced **two genuine release-blockers**, both small, both now fixed and
covered by new regression tests:

### B1 — Login rate-limit bypass via spoofed X-Forwarded-For (HIGH, fixed)
`backend/app/api/routes/auth.py` `_client_ip` trusted the **leftmost** XFF entry
when `TRUST_PROXY_HEADERS=true`, but the bundled nginx **appends** to XFF
(`$proxy_add_x_forwarded_for`), so a client could send `X-Forwarded-For: <random>`
and land every guess in a fresh rate-limit bucket — defeating the only attempt-rate
boundary on the single shared admin password and enabling unlimited online
brute-force. This was a regression of the production-hardening change that set
`TRUST_PROXY_HEADERS=true`.
**Fix:** `_client_ip` now keys on `X-Real-IP` (nginx **overwrites** it with the
connecting address, so it can't be forged through nginx), falling back to the
**rightmost** XFF hop, never the spoofable leftmost. README env note corrected.
Regression test: `tests/test_client_ip_attribution.py`.

### B2 — Expired-memory sweep aborts on `chk_superseded_has_pointer` (HIGH, fixed)
`backend/app/services/job_runners.py` swept expired memories with a bare
`DELETE … WHERE expires_at < NOW()`. `fk_memories_superseded_by` is
`ON DELETE SET NULL`, so deleting an expired **superseding** memory nulled a
dependent's `superseded_by` while its `status` stayed `'superseded'` — violating
the CHECK and aborting the whole batch. Net effect: once any TTL'd memory
supersedes another, **zero** expired memories are ever reclaimed and the job errors
hourly. (Same constraint class the T3 interactive-delete fix already handled; the
sweep was the un-fixed path.)
**Fix:** the sweep now demotes dependents (`status='deprecated', superseded_by=NULL`)
before deleting, in one transaction — mirroring `MemoryService.delete_memory`.
Regression test: `tests/test_expired_memory_cleanup.py`.

### Correction: the "reranker is still a no-op" finding was a false positive
One auditor reported T2 (reranker truncates before reranking) as still open, citing
`pipeline.semantic_search` calling `hybrid.search(limit=limit)`. Following the full
call chain refutes this: `MemoryService.search_memories` over-fetches
`fetch_n = limit + offset + 50` and passes **that** widened value into
`semantic_search`, so the reranker scores all `fetch_n` candidates and the page is
sliced **after** reranking (`memory.py:247-258`). The reranker genuinely rescues
below-cut docs. **T2 is fixed.** (Verified directly, not via agent.)

## Per-dimension readiness

| Dimension | Readiness | Verified fixes | Open findings |
|-----------|-----------|----------------|---------------|
| security-auth | needs-work → **ready** (B1 fixed) | 13 | B1 (fixed) |
| security-injection-ssrf | ready | 9 | 0 |
| security-secrets-config | ready | 12 | 1 LOW |
| correctness-invariants | ready | 15 | 0 |
| correctness-codegraph | ready | 11 | 0 |
| reliability-concurrency | ready | 15 | 2 LOW |
| performance-scale | ready | 8 | 3 LOW |
| data-migrations | needs-work → **ready** (B2 fixed) | 8 | B2 (fixed) |
| api-contract | ready | 10 | 0 |
| frontend | ready | 19 | 1 LOW |
| observability-ops | ready | 14 | 2 LOW |
| testing-quality | needs-work | 10 | test-gaps (below) |

## Remaining backlog (none release-blocking)

Recommended follow-ups, in rough priority. All are LOW/MED for this topology;
several are regression-test gaps on code that is already correct.

**Hardening (LOW)**
- `frontend`: memories and graph data views render the empty state ("No memories
  yet") on a failed fetch instead of an error+retry — mirror the error branch
  `index.tsx` already has. (`memories.tsx`, `unified-graph.tsx`, `code-graph.tsx`)
- `observability`: nginx `add_header` doesn't merge — the `/assets/` and
  `= /index.html` blocks lose the four server-level security headers. Re-assert them
  (or use an `include` snippet). Narrow impact (immutable hashed assets; `/` retains
  CSP). (`frontend/nginx.conf:48-54`)
- `security-secrets`: three of four git-failure surfacing paths skip `_sanitize_url`
  on `status_message`/stderr. Modern git (≥2.34) already redacts the token from
  stderr, so nothing leaks in practice, but the intent is inconsistent — sanitize
  uniformly. (`repo_manager.py:203,354,356,438`)
- `reliability`: `utils/background.spawn` tasks aren't cancelled on SIGTERM (the
  lifespan cancels `JobRegistry`/`TaskRegistry`/ML but not `_background_tasks`). A
  reembed/retry batch is torn down abruptly rather than cleanly; it self-heals on
  restart (incremental commit + resumable). Add a bounded `cancel_all()`.
- `observability`: CI builds + Trivy-scans images but never publishes; the only
  publish path (`scripts/build-push.sh`) runs no gate and Trivy is advisory
  (exit-code 0). Maintainer-only blast radius, but add a tag-gated release workflow.
- `reliability`: no app-level retry/backoff on LLM 429/5xx (only connection-level).
  Moot for the Ollama target; matters for a rate-limited cloud provider. Failures
  are visible + recoverable via `pipeline_failures`.

**Performance (LOW, deferred from the 2026-06-07 review)**
- `P1`: code-graph structure write is per-symbol/edge N+1 (`code_pipeline._store_graph`).
- `P2`: memory-graph Phase-5 write is per-entity/relation sequential.
- `_parsed` holds the whole repo's text+ASTs during a full reindex (OOM risk on a
  large monorepo vs the 1g container — already documented + mitigated by the limit).
  All three are background-job paths; bulk-INSERT rewrites are templated by existing
  code but warrant their own tested change.

**Test-gaps (MED/LOW — protect already-correct prior fixes from silent regression)**
- T3 interactive paths (delete-a-superseder demotion; PUT `status:superseded` → 400)
  have no API regression test — the audit's #1 prior remediation is unprotected.
- T4 equal-`created_at` tie-break, T5 decorated-function extraction, and the
  end-to-end `process_batch` flow each lack a direct test (the last is partly
  covered by `test_pipeline_savepoint_decouple.py`).
- T1 taxonomy enums are hand-mirrored with no drift-detection test (graceful
  degradation on drift, so low risk).

## Accepted trade-offs (confirmed appropriate for LAN/single-operator)

Re-confirmed, not escalated: secrets at rest plaintext (git tokens, provider keys —
documented; API masks on read), orphan embedding partitions on embedder rotation,
no WebSocket reconnect-resync, basic non-structured logging, single-replica
migration model (0003 rebuilds the derived code graph), `/docs` unauthenticated.

## Bottom line

With B1 and B2 fixed (committed alongside this report), darkmem is **clear to ship**
for the LAN / single-operator topology. The backlog above is post-launch hardening
and regression-test debt, none of it gating.

---

### Remediation status (2026-06-07)
- **B1 fixed** — `_client_ip` keys on X-Real-IP / rightmost XFF; README corrected; test added.
- **B2 fixed** — expired-memory sweep demotes dependents before delete; test added.
- **T2** — verified already fixed (false-positive finding refuted).
- Backend suite: **575 passed, 2 skipped** after the fixes.
