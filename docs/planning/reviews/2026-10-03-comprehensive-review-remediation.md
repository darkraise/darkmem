# Comprehensive review remediation — 2026-10-03

## Outcome

All **26 independently validated findings (6 P1, 20 P2)** have accepted code resolutions on `fix/comprehensive-review`. All nine implementation tasks are complete, with fresh full-suite verification recorded below. The initial verification checkpoint was uncommitted against reviewed base `b5a25e6bc0a3e70afdc3cb888416114704e0ca56`. The owner subsequently authorizes local commit, merge into `master` and redeployment; remote pushes/releases remain out of scope.

The [original review](2026-10-02-comprehensive-code-review.md) describes the pre-fix snapshot. The execution plan is `docs/superpowers/plans/2026-10-03-comprehensive-review-fixes.md`; its register records acceptance separately from deployment. Existing single-worker architecture, schemas, fingerprint partitions, feature defaults and recurring HEAD-only indexing policy remain unchanged.

## Resolutions

Every row is accepted by independent source/caller/test review and covered by behavioral regressions. The qualifications below remain part of acceptance, rather than promises of broader behavior.

| Finding | Task | Accepted resolution |
|---|---|---|
| 1 | 1 | Containment at the actual parser read and explicit-file classification boundaries; safe internal symlinks remain supported. |
| 2 | 1 | Forge-independent URL userinfo redaction across Git diagnostics, exceptions and timeouts. |
| 3 | 3 | Retention counts journal-verified snapshots and freshly verifies prospective survivors before deleting older known-good artifacts. |
| 4 | 2 | Dirty/refused note drafts survive navigation and reopening; application-lifetime unload protection and explicit discard remain active. |
| 5 | 4 | Owner locking and text revalidation prevent stale embedding responses from replacing current vectors; refresh accurately reports remaining gaps. |
| 6 | 5 | Fact locks precede provenance withdrawal/counting, preserving concurrently added witnesses and fact identity. |
| 7 | 4 | Shared-writer/exclusive-collector lifecycle locking, post-lock reference validation and coordinated filesystem phases cover both race orders. |
| 8 | 5 | Semantic retrieval applies all-tag filters consistently before final result assembly. |
| 9 | 5 | Ordinary and traced retrieval share feature selection, ranking, reranking and fallback behavior. |
| 10 | 5 | Project graphs admit relationships only through selected-memory assertion provenance. |
| 11 | 5 | Same-batch supersession reconciles committed memories chronologically instead of depending on concurrent write completion. |
| 12 | 6 | Incremental indexing resolves against the surviving symbol/binding universe without expanding parse/embed work; wildcard bridges re-expand current exports. |
| 13 | 6 | HEAD-only recurring trigger policy is retained and documented; explicit manual/later pipeline runs drain deferred indexing work. |
| 14 | 6 | Code-search fusion identifies results by repository, path and line rather than merging unrelated repositories. |
| 15 | 7 | WebSockets share session validation and recheck connected sessions on idle intervals and before broadcasts. |
| 16 | 7 | Creation/change validates bcrypt's 72-byte UTF-8 limit; oversized login input fails safely without truncation or hash migration. |
| 17 | 8 | The actual classic content-script artifact executes; opt-in registration, badge/options feedback and opt-out ordering remain truthful. |
| 18 | 7 | Acquisition-time leases cover request streams, pinned pipelines, job runners and detached consumers; failed fanout cancels and joins children before retirement. |
| 19 | 7 | Read-only provider/credential/setup/notification probes refuse egress; graph naming/health are local; hybrid-disabled memory search uses filtered keyword fallback before provider access. |
| 20 | 9 | Multiline source editing preserves structural quote/list ancestry, including compact imported markers, while retaining literal code content. |
| 21 | 9 | Nested insertion resolves the structural parent and surfaces mutation failures. |
| 22 | 9 | Graph placeholders are scoped to the current project rather than retaining another project's graph. |
| 23 | 9 | Terminal pipeline/repository events and reconnects invalidate exposed graph/code data. |
| 24 | 9 | Live chat responses and completion callbacks remain owned by their originating conversation across navigation. |
| 25 | 9 | Chat errors are visible and accessible; definite failures permit draft retry, ambiguous sends avoid blind replay, and unauthorized responses use shared handling. |
| 26 | 4 | Upload/import cleanup preserves bytes after uncertain commit outcomes or failed rollback; proven precommit failures retain safe cleanup. |

## Independent review

- Nine implementation tasks ran through assigned subagents, followed by four independent `gpt-6-astra/high` task judges reviewing settled source snapshots.
- Initial task reviews found four additional P2 gaps: unchanged wildcard export bridges, failed fanout draining, read-only empty configuration updates, and compact imported quote ancestry. Each received regressions, corrections and independent acceptance.
- A fresh `gpt-6-astra/high` fix-wave judge accepted those corrections and the related fixture/role-inventory updates. Exact assertions and database privileges were not weakened.
- The user-requested **`gpt-6.1-sol/xhigh`** reviewer inspected all 26 findings, source, callers and tests across the entire remediation branch. It identified one remaining read-only/vector-mode egress path, subsequently fixed with six failing-then-passing service/API regressions.
- That dedicated reviewer and a separate fresh `gpt-6-astra/high` judge both accepted the final correction. All 26 findings have accepted resolutions; neither reviewer reported another confirmed defect. Affected task scores are 19/19/19/18 and 19/19/19/19 respectively for requirements/correctness/tests/maintainability.
- Covered repository snapshots matched before/after each read-only review. The final code-review snapshot is `c5556f0a44fe89478ea35aeb2c2ccee30b7fd0b4283b91f0641842ff29faa7c2`; subsequent controller documentation is not part of that code snapshot.

## Verification

| Check | Result |
|---|---|
| Final whole backend after the last correction | 7,947 passed, 26 skipped; exit 0, 407.33 seconds. Merge-gate rerun also passes, 395.95 seconds. |
| Whole backend before the last six-case correction | 7,941 passed, 26 skipped; exit 0. |
| Last correction and adjacent retrieval/read-only/API/lifetime tests | Six RED, six GREEN; 246 adjacent passed. |
| Whole frontend | 1,981 passed across 264 files; exit 0. |
| Frontend production build, including TypeScript | Passed; dynamic-import and large-chunk warnings remain. |
| Python SDK | 36 passed. |
| TypeScript SDK | 20 passed. |
| Extension, individual Node tests | 61 passed. |
| CI sharding unit tests | Four passed. |
| Documented merge-gate floor | GREEN: backend, frontend/typecheck/build, extension, SDK tests/build, single Alembic head, benchlib and cached F1. |
| Benchlib harness | 1,062 passed, 45 warnings; 72.40 seconds. Disposable development bench database only. |
| Cached extraction F1 | All four recorded floors pass; entity name/type F1 0.956, name-only 0.985, relation F1 0.935. No live model calls. |
| Plan lint and diff whitespace checks | Zero errors/warnings and clean diff check. |
| Whole frontend lint | 59 errors, 192 warnings; not clean. Errors in changed files match reviewed HEAD baselines; the newly introduced effect error was fixed. |

Backend commands run from `backend/` using `.venv/bin/python -m pytest`, with explicit `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@127.0.0.1:5433/darkmem_test_4` for the final full run. The full command is `pytest -q --durations=15 -o faulthandler_timeout=90 --basetemp=/home/dm-final-1003`. Other workers use exclusively assigned disposable development lanes 2–5; no concurrent process shares a lane. Existing cutover fixtures create their guarded private development `_bfill` database, never the production database. Temporary directories outside the normal workspace require explicit reviewed escalation and are allocated only at previously absent private paths.

Frontend checks use `npm test -- --maxWorkers=1`, `npm run build` and `npm run lint`. SDK checks use the backend Python virtualenv and frontend Vitest installation. Extension counts come from `node --test --test-isolation=none extension/test/*.test.js`; CI checks use `backend/.venv/bin/python -m unittest discover -s scripts/tests -p 'test_ci_pytest.py'`.

The first full-backend attempt exposed nine development-PostgreSQL disk-full failures and five fixture/inventory mismatches. Disposable storage/connectivity was verified and retried without production cleanup. Fixture corrections follow pinned classifier behavior and scoped relationship provenance while preserving exact behavioral assertions; the role inventory adds two verified writer-only modules without broadening read privileges. The subsequent whole-backend run passed. After the last code correction, another full attempt recorded 7,942 passed, 26 skipped and five `OSError: ENOSPC` failures writing cutover snapshots on shared `/tmp` tmpfs. The entire unchanged cutover module passed 41 tests on immediate retry. A controller-selected workspace temp directory then caused 97 failures because real path guards reject `/root` descendants and Unix socket fixtures exceeded their path-length limit. Final validation instead uses an explicitly approved short disk-backed private temp path. No application guard or test assertion is changed to bypass these environment incompatibilities.

The short-path smoke passed 137 tests. The final complete backend run then passed 7,947 tests with 26 skips and 1,662 warnings. Log: `/tmp/darkmem-review-backend-short-storage-tests.log`. Frontend logs: `/tmp/darkmem-review-frontend-postreview-tests.log`, `/tmp/darkmem-review-frontend-verified-build.log` and `/tmp/darkmem-review-frontend-final-lint.log`. Skips and existing dependency/test-fixture warnings remain visible; no claim of clean lint or warning-free validation is made.

## Execution rulings

- Continue all nine authorized tasks without another planning approval or count-based session stop; preserve the uncommitted branch and prohibit production/provider/integration side effects.
- Implement disjoint write sets concurrently, then stop writers for independent review waves with matching before/after snapshots.
- Expand Task 7's audited lease coverage to direct REST/MCP/retry/dream consumers and detached repository/re-embedding jobs; acquire before pre-dispatch awaits and release through terminal cleanup. Task 5/6 remain owners of pipeline/job captures.
- Permit Task 9 to reuse/export existing unauthorized handling and test mounted mutation payloads through local production serialization; update only the verified writer-module inventory for the two new locks, without widening database privileges.
- Amend attachment work to include cleanup-first post-lock reference validation. Preserve the accepted HEAD-only recurring indexing policy and all dormant feature defaults.
- Retry infrastructure failures using isolated development lanes and a fresh short, disk-backed temporary directory after correcting an unsuitable workspace path; do not delete unrelated data, weaken path guards or modify production to make tests pass.

## Limits and operational follow-up

- Initial review/fix verification used no production endpoint, real provider, deployment, migration, merge, push, staging or commit. The subsequent owner request authorizes local integration and redeployment with backup and health checks; deployment evidence is recorded separately. The development PostgreSQL service was started alone for isolated tests.
- No browser end-to-end/accessibility audit, production load/performance benchmark or live retrieval-quality gate was run. The merge-gate floor does run the isolated benchlib suite and cached-only F1 benchmark, without activating dormant arms. Source and mounted component tests do not establish pixel-level UX or throughput guarantees. Existing frontend lint debt and bundle-size warnings remain outside these scoped fixes.
- Historical stale vectors or missing attachment bytes are not reconstructed by these guards; operators may need explicit re-embedding or restoration. Rotate any real credentials previously exposed by the old diagnostic path; this work does not inspect or rotate secrets.
- Attachment safety covers participating application writers, not raw SQL/admin bypasses. Commit ambiguity tests inject acknowledgement-boundary faults around real commits, not every possible asyncpg transport schedule.
- Notes and chat recovery are in-memory session/tab behavior, not crash-proof browser storage or idempotent server replay. Same-batch reconciliation is not a new crash-recovery journal.
- Backup verification deliberately favors over-retention on uncertainty and adds survivor readback I/O. Failed or unknown artifacts are not counted as verified survivors; producer/systemd behavior is unchanged.
- Dormant retrieval arms and default ranking gates remain unchanged. Finding 13 is resolved under the accepted HEAD-only policy, not by introducing an automatic unchanged-HEAD timer. The review is not proof that unreported functionality is defect-free.
