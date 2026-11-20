# P1 — infrastructure, scripts, CI, SDKs, extension

Reviewer findings for the 2026-11-20 audit, as returned. Summary first where the reviewer gave one, then one entry per finding. Index and verification status: `docs/2026-11-20-codebase-audit.md`.

**Counts:** 2 high, 8 medium, 14 low.

**High**
1. **Auto-capture stores every partial chat reply.** In `extension/src/content-autocapture.js:26-35,91-94`, every change to the page re-reads each message's text and sends any text it hasn't seen before. A reply that streams in token by token therefore becomes dozens of near-duplicate memories, each paying for extraction. Replies over 20,000 characters are refused, so the full text is never stored while its prefixes are. The code path is confirmed; the streaming behaviour of the three sites is inferred.
2. **Pull requests run arbitrary code on the self-hosted LAN runner.** `ci.yml:6-8` triggers on `pull_request`, e2e always runs on `darkmem-linux` (`:295-297`), and fork PRs have no picker token so `pick_runner.py:67-69` sends them to self-hosted too. The README links a public GitHub repo. Settle by checking repo visibility, the fork-PR approval setting and the runner's network.

**Medium**
3. **A release can be tagged at the wrong commit.** In `release.yml:401`, a cancelled `tag` job still lets `github-release` run, and `gh release create` without `--verify-tag` (`:464`) creates the tag on master's tip.
4. **`numpy` is imported but not declared.** It is in the lock only through `pgvector` (imported by nothing) and `scikit-learn` (used only by `get_clustered_vectors`, `vector.py:353`, which only a test calls). Removing both unused packages would break boot unless `numpy` is declared first.
5. **Third-party actions are pinned to movable tags, not commit SHAs.** This includes the publish job that holds `DOCKERHUB_TOKEN`. The trivy scan job also writes the same build cache that publish reads.
6. **`CONTRIBUTING.md:84-86,189-196` describes the old release model.** It says tags publish and `release.sh` tags; in fact a push to master releases. A contributor following it can cut a release by accident.
7. **`release.sh:46` cannot finish on this host.** It runs `gate.sh --full`, which CLAUDE.md says cannot complete here.
8. **The e2e database reset bypasses the destructive-SQL guard on a false premise.** `e2e_db.py:18-37` drops the schema of whatever `TEST_DATABASE_URL` the environment names. Its guard exemption claims it never touches an ambient database.
9. **The worker's restore loop hides real failures.** `restore-cycle.sh:233-243` treats every migrate failure as an old-baseline snapshot and exits 0, so a broken migration looks like success every night.
10. **`start_dev_server.sh` can migrate production.** It calls bare `python`, which isn't on PATH here, and by default migrates `localhost:5432`, which is the production database on this host.

**Low**
11. Five seed and test scripts are broken and unreferenced (no MCP auth, or the wrong `ProcessingPipeline` arguments).
12. `publish_production_models.sh` changes into the deleted `fine-tuning/` directory; `scripts/eval_*.js` hard-code a Windows path.
13. The `cutover/` package is the one-time 0006-to-baseline loader and only its own tests use it. `llm_providers_transition.py` in the same folder is still documented and stays.
14. `entailment/cache_span/` (about 549 judge-cache files) appears to be tracked even though its sibling `cache/` is gitignored and the labelling protocol says judge output is quarantined. `harvest_l2_cache_fixture/` (about 810 files) is a deliberate committed fixture.
15. CI skips the extension suite, both SDK suites and the SDK build.
16. The Dockerfile's `chown -R` duplicates layers and leaves the code writable by the runtime user; the app package is installed twice; Node 20 is end-of-life.
17. `build-push.sh` tags the HEAD sha even from a dirty tree.
18. `backup.sh` accepts any complete dump, so a dump of the wrong database would push real dumps out of retention over 14 nights. A failed dump cannot trigger a prune.
19. `frontend/nginx.conf` is used by no build path, and under bridge networking its `proxy_pass 127.0.0.1:8000` can't reach the app.
20. Stale comments: the `ml` extra in `pyproject.toml`, `alembic.ini`'s ignored URL, and the e2e README.
21. The two GitNexus files at the repo root are unreferenced.
22. `eval_round3/` is held in place by the guard test and still waits on owner decision D5.
23. `import_docs_corpus.py` is likely superseded by the dr-forge mirror.
24. The worker compose comment says the receiver has no network, but it joins the default one.

**Checked and found sound:**
- The release order is correct: the tag is written only after the image is published.
- Every workflow passes outside values through `env:`, and nothing uses `pull_request_target`.
- `backup.sh` cannot prune after a failed dump.
- `restore-cycle.sh` verifies before it swaps.
- The image runs as non-root, with `exec` and `init` handling signals, and no secrets in layers.
- The extension asks only for narrow permissions.
- Every other dependency in `pyproject.toml` has a live importer.

**Benchlib runners:** the gate runs only `run_bench.py --algo-only`, `run_retrieval_eval.py` (with `--full`) and the benchlib tests; CI runs only the tests. Every other runner is run by hand.
