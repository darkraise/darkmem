"""One-off emitter for shared-base batch-007 — ai_coding domain (round 2).

Same pattern as _emit_shared_batch_006.py; only ENTRIES changes.
Appends 50 rows to data/v2/shared/shared.jsonl with ids shared-00301..00350.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
ID_OFFSET = 300  # batches 001..006 consumed shared-00001..00300

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The npm install finished but failed to run scripts because the shell on the CI image was sh, not bash.", "problem", "ai_coding", False,
     [("npm install", "command"), ("sh", "tool"), ("bash", "tool")],
     [],
     "why did the JavaScript dependency scripts fail inside the CI container",
     "package post-install shell mismatch continuous integration"),
    # --- 2 ---
    ("Picked Playwright over Cypress for end-to-end tests; parallelism across browsers was cleaner to wire up.", "decision", "ai_coding", False,
     [("Playwright", "library"), ("Cypress", "library")],
     [("Playwright", "Cypress", "REPLACES")],
     "which e2e runner did we end up choosing and why",
     "browser automation pick parallel cross-engine setup"),
    # --- 3 ---
    ("Completed the ESLint v9 flat config migration across the monorepo on 2026-02-18.", "milestone", "ai_coding", False,
     [("ESLint v9", "tool"), ("monorepo", "project"), ("2026-02-18", "date")],
     [],
     "when did the linter rule-set overhaul wrap up across the repo",
     "flat config rollout lint version bump date"),
    # --- 4 ---
    ("The Rust Book chapter on ownership is what I point new teammates at during the first week.", "reference", "ai_coding", False,
     [("Rust Book", "publication"), ("ownership", "concept")],
     [],
     "what do new hires read in week one to learn the memory model",
     "onboarding text chapter lifetime concept intro"),
    # --- 5 ---
    ("Each PR gets a preview URL via Vercel; the bot comments with the link once the build is green.", "architecture", "ai_coding", False,
     [("Vercel", "service")],
     [],
     "how do reviewers reach a live preview of a change before merge",
     "deploy bot automatic link pull request green status"),
    # --- 6 ---
    ("Flutter hot reload stopped working after the riverpod upgrade because the provider scope lived outside the app widget.", "problem", "ai_coding", False,
     [("Flutter", "framework"), ("riverpod", "library")],
     [],
     "why did the mobile framework's fast refresh break after the state package bump",
     "reactive scope outside tree hot reload breakage"),
    # --- 7 ---
    ("pytest's --pdb flag drops into the debugger on the first failure, not on collection errors.", "fact", "ai_coding", False,
     [("pytest", "library"), ("--pdb", "command")]
     ,
     [],
     "when does the debugger flag actually kick in during a test run",
     "test runner debugger entry timing rule"),
    # --- 8 ---
    ("Prefer dataclasses over attrs for simple records; frozen=True plus type hints covers our invariants.", "preference", "ai_coding", False,
     [("dataclasses", "library"), ("attrs", "library")],
     [("dataclasses", "attrs", "PREFERS")],
     "which Python record helper wins for our small value types",
     "immutable simple record library pick typed"),
    # --- 9 ---
    ("Stopped using Sentry's breadcrumb auto-capture; the volume overwhelmed the error quota in one bad deploy.", "decision", "ai_coding", False,
     [("Sentry", "service"), ("breadcrumb", "concept")],
     [],
     "why did we disable automatic trace crumbs in error reporting",
     "error tracker trail volume quota incident"),
    # --- 10. noise ---
    ("I'll just give that one more look before we move on.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("mypy passed locally but failed on CI because the cache loaded with a stale dependency signature.", "problem", "ai_coding", False,
     [("mypy", "tool")],
     [],
     "why did static type checks disagree between the laptop and CI",
     "type checker cache mismatch dependency signature"),
    # --- 12 ---
    ("Fine-tuned the reranker and passed the 0.85 nDCG threshold on 2026-03-29.", "milestone", "ai_coding", False,
     [("reranker", "service"), ("nDCG", "concept"), ("2026-03-29", "date")],
     [],
     "when did the tuned ranker cross the quality bar",
     "ranking model metric achievement date fine-tune"),
    # --- 13 ---
    ("Frontend uses TanStack Router with file-based routes; server state goes through TanStack Query.", "architecture", "ai_coding", False,
     [("TanStack Router", "library"), ("TanStack Query", "library")],
     [],
     "how is routing and server data state organised in the UI code",
     "SPA file-based routes async cache layer"),
    # --- 14 ---
    ("Migrated API contract checks from Pact to OpenAPI-based request validators; fewer moving parts.", "decision", "ai_coding", False,
     [("Pact", "tool"), ("OpenAPI", "protocol")],
     [("OpenAPI", "Pact", "REPLACES")],
     "which contract testing approach took over from the old consumer-driven one",
     "API schema validation replacement simpler stack"),
    # --- 15 ---
    ("The Playwright test hung forever when a modal's close animation took longer than the default timeout.", "problem", "ai_coding", False,
     [("Playwright", "library"), ("modal", "concept")],
     [],
     "why did the browser test hang on a dialog interaction",
     "animation duration timeout default UI test"),
    # --- 16 ---
    ("golangci-lint runs tests through the test linter only when you enable the testifylint checker explicitly.", "fact", "ai_coding", False,
     [("golangci-lint", "tool"), ("testifylint", "tool")],
     [],
     "how do you opt into test-specific lints in the Go meta-linter",
     "aggregate linter plugin enable test ruleset"),
    # --- 17 ---
    ("For debugging reach for a bisect commit first, then a print statement; the debugger comes last.", "preference", "ai_coding", False,
     [("bisect", "command"), ("debugger", "tool")],
     [],
     "what order do we walk through debugging techniques by default",
     "root-cause search sequence git-first print fallback"),
    # --- 18 ---
    ("Services log structured JSON to stdout and let the container runtime ship logs to the collector.", "architecture", "ai_coding", False,
     [("JSON", "language"), ("stdout", "api")],
     [],
     "how do services hand off logs to the observability pipeline",
     "structured log stream runtime shipper collector"),
    # --- 19 ---
    ("SWR cached the stale cursor after pagination, so fast back-clicks showed the wrong page boundary.", "problem", "ai_coding", False,
     [("SWR", "library")],
     [],
     "why did pagination go sideways when users clicked back quickly",
     "data fetcher cache cursor pagination stale bug"),
    # --- 20 ---
    ("Wrote a small codemod with jscodeshift to move from React.FC to explicit prop types everywhere.", "decision", "ai_coding", False,
     [("jscodeshift", "tool"), ("React.FC", "pattern"), ("explicit prop types", "pattern")],
     [("explicit prop types", "React.FC", "REPLACES")],
     "what automated refactor changed the component type declarations",
     "codemod migration functional component annotation swap"),
    # --- 21 ---
    ("Prefer feature branches named by ticket-id over descriptive slugs; the link to the tracker is automatic.", "preference", "ai_coding", False,
     [("feature branches", "pattern"), ("ticket-id", "pattern")],
     [],
     "what branch naming convention does the team use for traceability",
     "branch naming policy tracker link convention"),
    # --- 22 ---
    ("Reduced the monorepo's cold build time from 14 min to 3 min 40 s using Nx's affected graph on 2026-04-02.", "milestone", "ai_coding", False,
     [("monorepo", "project"), ("Nx", "framework"), ("2026-04-02", "date")],
     [],
     "when did the cold build time drop by three quarters and using what tool",
     "cold build speedup affected graph build system date"),
    # --- 23 ---
    ("Kent Beck's TDD book still sets the vocabulary we use in code review for fake it till you make it.", "reference", "ai_coding", False,
     [("Kent Beck", "person"), ("TDD", "method"), ("code review", "activity")],
     [],
     "whose book still anchors how we talk about test-driven style",
     "test-first author vocabulary review shared"),
    # --- 24 ---
    ("Database migration on staging timed out because the ALTER TABLE rewrite ran serially behind the default lock.", "problem", "ai_coding", False,
     [("ALTER TABLE", "command")],
     [],
     "why did a staging schema change blow past its timeout window",
     "schema rewrite table lock serial migration stall"),
    # --- 25 ---
    ("Monorepo uses pnpm workspaces, Turborepo for caching, and changesets for versioning internal packages.", "architecture", "ai_coding", False,
     [("pnpm workspaces", "tool"), ("Turborepo", "tool"), ("changesets", "tool")],
     [],
     "what tooling stack holds the many-package JavaScript repo together",
     "multi-package JS repo build cache release tool trio"),
    # --- 26 ---
    ("Adopted trunk-based development with feature flags; long-lived branches had stopped merging cleanly.", "decision", "ai_coding", False,
     [("trunk-based development", "pattern"), ("feature flags", "pattern")],
     [],
     "what branching model took over after merges kept breaking",
     "short-lived branches flag gating integration cadence"),
    # --- 27 ---
    ("In Python prefer match statements over elif chains when shape-matching JSON; the patterns read as specs.", "preference", "ai_coding", False,
     [("Python", "language"), ("match statements", "pattern"), ("elif chains", "pattern"), ("JSON", "language")],
     [("match statements", "elif chains", "PREFERS")],
     "what control-flow construct wins for structural checks on dictionaries",
     "pattern matching replace condition ladder readability"),
    # --- 28 ---
    ("GraphQL codegen generated optional types everywhere because the Apollo schema lacked non-null annotations.", "problem", "ai_coding", False,
     [("GraphQL", "language"), ("Apollo", "library")],
     [],
     "why did the generated TypeScript types end up optional on every field",
     "schema nullability downstream optional codegen"),
    # --- 29 ---
    ("Node.js worker threads share memory via SharedArrayBuffer, not via structured clone for normal objects.", "fact", "ai_coding", False,
     [("Node.js", "platform"), ("worker threads", "pattern"), ("SharedArrayBuffer", "api")],
     [],
     "how do worker threads actually share memory between them in Node",
     "concurrency primitive shared buffer clone boundary"),
    # --- 30 ---
    ("Switched the whole frontend to React 19 on 2026-01-20 without any runtime regressions.", "milestone", "ai_coding", False,
     [("React 19", "library"), ("2026-01-20", "date")],
     [],
     "when did the UI codebase land on the latest major framework version",
     "major library upgrade clean migration date"),
    # --- 31 ---
    ("Tests live next to source files; a pre-commit hook rewrites imports when files move.", "architecture", "ai_coding", False,
     [("pre-commit hook", "tool")],
     [],
     "where do tests sit relative to source and how do paths stay in sync",
     "co-located test layout import rewrite automation"),
    # --- 32 ---
    ("Picked Vitest over Jest for the new Vite-based packages; same test API, faster startup.", "decision", "ai_coding", False,
     [("Vitest", "library"), ("Jest", "library"), ("Vite", "tool")],
     [("Vitest", "Jest", "REPLACES")],
     "which test runner replaced the old one in the bundler-native packages",
     "test runner swap bundler alignment startup speed"),
    # --- 33 ---
    ("Django migration squashing dropped a backwards-compatibility shim that staging still depended on; rolled back.", "problem", "ai_coding", False,
     [("Django", "framework")],
     [],
     "why did the compaction of old migrations have to be reverted",
     "migration squash legacy shim dependency rollback"),
    # --- 34 ---
    ("The Zen of Python still gets cited in code review comments when someone adds an unneeded abstraction.", "reference", "ai_coding", False,
     [("Zen of Python", "publication"), ("code review", "activity")],
     [],
     "which Python cultural touchstone keeps showing up in reviewer notes",
     "language ethos quotable principle design pushback"),
    # --- 35 ---
    ("For complex state machines reach for XState rather than bespoke reducers; the visualiser pays for itself.", "preference", "ai_coding", False,
     [("XState", "library"), ("bespoke reducers", "pattern")],
     [("XState", "bespoke reducers", "PREFERS")],
     "which library wins over hand-rolled reducers for intricate flows",
     "state machine library visualiser worth adoption"),
    # --- 36 ---
    ("pytest-asyncio's strict mode forces explicit event_loop_policy fixtures and catches accidental loop leakage.", "fact", "ai_coding", False,
     [("pytest-asyncio", "library"), ("event_loop_policy", "api")],
     [],
     "what does the strict setting do in the async test plugin",
     "asyncio test plugin explicit policy fixture leak"),
    # --- 37 ---
    ("git worktrees let you check out multiple branches simultaneously, sharing a single repository object store.", "fact", "ai_coding", False,
     [("git worktrees", "tool")],
     [],
     "how can two branches be worked on at once without cloning the repo twice",
     "multiple checkout shared repo object store feature"),
    # --- 38 ---
    ("A Dependabot upgrade of jsonwebtoken flipped the default algorithm; token verification failed silently in staging.", "problem", "ai_coding", False,
     [("Dependabot", "tool"), ("jsonwebtoken", "library")],
     [],
     "what library bump caused silent JWT verification failures",
     "dependency upgrade default algorithm regression token"),
    # --- 39 ---
    ("The API gateway uses OpenAPI-first: contracts live in Git, and server stubs are generated on merge.", "architecture", "ai_coding", False,
     [("API gateway", "service"), ("OpenAPI", "protocol"), ("Git", "tool")],
     [],
     "where do the API contracts live and when do the server stubs regenerate",
     "specification-first workflow stub generation merge"),
    # --- 40 ---
    ("Replaced Husky pre-commit hooks with lefthook; parallel hook execution and a friendlier config language won.", "decision", "ai_coding", False,
     [("Husky", "tool"), ("lefthook", "tool")],
     [("lefthook", "Husky", "REPLACES")],
     "which commit-hook runner replaced the older one and why",
     "hook runner swap parallel execution config format"),
    # --- 41 ---
    ("Got the CI matrix down to 8 minutes median on 2026-03-14 after moving flaky tests into a nightly job.", "milestone", "ai_coding", False,
     [("CI matrix", "config"), ("2026-03-14", "date")],
     [],
     "when did the build pipeline settle under ten minutes median",
     "CI wall-clock reduction flaky quarantine date"),
    # --- 42 ---
    ("An unbounded asyncio.Queue blew the worker's heap because producers never awaited when consumers fell behind.", "problem", "ai_coding", False,
     [("asyncio.Queue", "api")],
     [],
     "why did the worker OOM when consumers could not keep up",
     "backpressure missing queue unbounded producer drain"),
    # --- 43 ---
    ("TypeScript's noUncheckedIndexedAccess only checks index signatures, not tuple element access.", "fact", "ai_coding", False,
     [("TypeScript", "language"), ("noUncheckedIndexedAccess", "config")],
     [],
     "what does the strict index-access flag actually cover and miss",
     "strict TS option index signature tuple coverage gap"),
    # --- 44 ---
    ("For new CLIs reach for Typer over argparse; decorators beat manual parser wiring for small scripts.", "preference", "ai_coding", False,
     [("Typer", "library"), ("argparse", "library")],
     [("Typer", "argparse", "PREFERS")],
     "which library wins for writing small Python command-line tools",
     "CLI decorator author preference manual wiring"),
    # --- 45 ---
    ("The Clean Architecture dependency rule informs how services import from their own domain modules.", "reference", "ai_coding", False,
     [("Clean Architecture", "publication")],
     [],
     "which architectural principle governs import direction inside services",
     "layered design inward dependency rule convention"),
    # --- 46 ---
    ("The SQLAlchemy selectinload made the N+1 worse because each batch fetched the full child rows; joined loading fixed it.", "problem", "ai_coding", False,
     [("SQLAlchemy", "library"), ("selectinload", "api"), ("N+1", "concept"), ("joined loading", "method")],
     [("joined loading", "selectinload", "REPLACES")],
     "which ORM loading strategy actually fixed the child-row blow-up",
     "eager loader swap batch query child rows fix"),
    # --- 47 ---
    ("CI publishes preview Storybook builds per PR; design review happens in Chromatic before merge.", "architecture", "ai_coding", False,
     [("Storybook", "tool"), ("Chromatic", "service")],
     [],
     "where does UI design review happen before a change lands",
     "component catalog preview visual review merge gate"),
    # --- 48 ---
    ("Switched linting from Pylint to Ruff in the Python repo; startup went from 11 s to 300 ms on the largest package.", "decision", "ai_coding", False,
     [("Pylint", "tool"), ("Ruff", "tool"), ("Python", "language")],
     [("Ruff", "Pylint", "REPLACES")],
     "which linter took over and how much did startup time drop",
     "static check swap startup speed improvement"),
    # --- 49 ---
    ("Shipped tree-sitter-based code search across the repo on 2026-04-05; reviews quote snippets by ranges now.", "milestone", "ai_coding", False,
     [("tree-sitter", "library"), ("2026-04-05", "date")],
     [],
     "when did structural code search replace plain text across the repo",
     "parser-based search adoption review quoting date"),
    # --- 50 ---
    ("Docker multi-stage builds cached a stale node_modules layer because the package.json copy skipped the lockfile.", "problem", "ai_coding", False,
     [("Docker", "tool"), ("node_modules", "file"), ("package.json", "file")],
     [],
     "why did the container build use an outdated dependency layer",
     "multi-stage cache invalidation lockfile copy bug"),
]


def _find_span(text: str, needle: str, used: list[tuple[int, int]]) -> tuple[int, int]:
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx < 0:
            raise ValueError(f"entity name {needle!r} not found in text {text!r}")
        end = idx + len(needle)
        overlap = any(not (end <= s or idx >= e) for s, e in used)
        if not overlap:
            return idx, end
        start = idx + 1


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("a", encoding="utf-8") as f:
        for i, entry in enumerate(ENTRIES, start=1):
            text, mt, domain, noise, ents, rels, qq, qk = entry
            used: list[tuple[int, int]] = []
            entities = []
            for name, typ in ents:
                s, e = _find_span(text, name, used)
                used.append((s, e))
                entities.append({"name": name, "type": typ, "start": s, "end": e})
            row: dict = {
                "id": f"shared-{ID_OFFSET + i:05d}",
                "domain": domain,
                "text": text,
                "memory_type": mt,
                "noise": noise,
                "entities": entities,
                "relationships": [{"source": s, "target": t, "type": r} for s, t, r in rels],
            }
            if qq is not None and qk is not None:
                row["queries"] = [
                    {"form": "question", "text": qq},
                    {"form": "keyword", "text": qk},
                ]
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
