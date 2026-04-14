"""One-off emitter for shared-base batch-040 — ai_coding domain (refactoring / legacy code / migrations / strangler-fig patterns).

Writes 50 rows to data/v2/shared/batch_040.tmp.jsonl with ids shared-01951..02000.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_040.tmp.jsonl"
ID_OFFSET = 1950

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Carved the billing surface out of the monolith behind a strangler-fig proxy in Kong; traffic shifted 10% per week with a kill switch on the header.", "architecture", "ai_coding", False,
     [("billing", "concept"), ("Kong", "tool"), ("strangler-fig", "pattern")],
     [],
     "how did the billing extraction avoid a big-bang cutover from the old monolith",
     "edge proxy gradual traffic shift kill switch header weekly ramp"),
    # --- 2 ---
    ("Ran a GitHub Scientist experiment for six weeks on the pricing calculator; the new engine matched 99.4% of outputs before we flipped the publish path.", "milestone", "ai_coding", False,
     [("GitHub Scientist", "library"), ("pricing calculator", "concept")],
     [],
     "what parallel-run technique validated the new pricing engine before switching authority",
     "scientist style dual run match rate validation publish path flip"),
    # --- 3 ---
    ("Introduced a PaymentGateway abstraction seam first, then swapped Stripe for Adyen behind it without touching the callers — branch-by-abstraction done right.", "decision", "ai_coding", False,
     [("PaymentGateway", "pattern"), ("Stripe", "service"), ("Adyen", "service"), ("branch-by-abstraction", "pattern")],
     [("Adyen", "Stripe", "REPLACES")],
     "which refactoring technique let us swap the payment processor without freezing feature work",
     "abstraction seam runtime swap caller stability processor change"),
    # --- 4 ---
    ("Dark-launched the new search service alongside Elasticsearch for a month; responses were logged but discarded until parity hit 99.9%.", "architecture", "ai_coding", False,
     [("Elasticsearch", "service"), ("search service", "concept")],
     [],
     "how did the replacement search backend prove itself before serving any user traffic",
     "shadow traffic log discard parity threshold switchover prep"),
    # --- 5 ---
    ("Expand-Contract rename on the users.email_address column took three releases: add column, dual-write, backfill, switch reads, stop writes, drop old.", "architecture", "ai_coding", False,
     [("Expand-Contract", "pattern"), ("users.email_address", "file")],
     [],
     "which column-rename pattern kept a live service running through the migration",
     "additive schema dual write backfill cutover drop legacy step sequence"),
    # --- 6 ---
    ("Parallel-write pattern during the Postgres-to-Citus migration caught three ordering bugs our unit tests had missed for years.", "problem", "ai_coding", False,
     [("Postgres", "database"), ("Citus", "database"), ("Parallel-write", "pattern")],
     [("Citus", "Postgres", "REPLACES")],
     "what surprising bugs showed up when we wrote to both databases at once during cutover",
     "dual write shadow target ordering bug surface long latent test gap"),
    # --- 7 ---
    ("Contract-first extraction paid off: generated the OpenAPI client from the new service's spec before writing a line of implementation code.", "decision", "ai_coding", False,
     [("OpenAPI", "protocol"), ("Contract-first", "pattern")],
     [],
     "which ordering of work kept callers unblocked while a new service was still being built",
     "spec first client generation implementation later unblock consumer"),
    # --- 8 ---
    ("git log -L :calculateTax:tax.py pulled the full 9-year change history of one function in seconds; we found the rationale for the odd rounding in a 2019 commit.", "fact", "ai_coding", False,
     [("git log -L", "command"), ("tax.py", "file")],
     [],
     "which git command pulled the entire history of a single function for code archaeology",
     "history slice function scope archaeology rationale ancient commit"),
    # --- 9 ---
    ("git log -S 'legacy_bonus_calc' exposed that the helper hadn't been referenced since 2021; a three-line commit removed it.", "fact", "ai_coding", False,
     [("git log -S", "command"), ("legacy_bonus_calc", "file")],
     [],
     "which pickaxe search proved the dead helper was safe to delete",
     "pickaxe search symbol gone callers none dead code delete safe"),
    # --- 10. noise ---
    ("Coffee's cold again — I keep forgetting to drink it while reading diff reviews.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Telemetry-driven dead-code removal: we logged entry-point hits for six months, then deleted any handler with zero invocations; 48 files gone.", "decision", "ai_coding", False,
     [("Telemetry", "concept"), ("dead-code removal", "activity")],
     [],
     "how did production metrics decide which handlers were safe to delete",
     "runtime usage probe zero hit threshold prune confidence data driven"),
    # --- 12 ---
    ("Shipped a Pendo in-app banner for the v1 API with a six-month sunset clock; support tickets mentioning the old endpoints dropped 80% by month four.", "milestone", "ai_coding", False,
     [("Pendo", "service"), ("v1 API", "concept")],
     [],
     "which in-app messaging approach drove adoption of the new API before the deprecation date",
     "deprecation banner countdown sunset clock support volume drop"),
    # --- 13 ---
    ("Deprecation warnings emitted via warnings.warn with DeprecationWarning and stacklevel=2 actually surfaced in callers' logs; stacklevel=1 had buried them.", "problem", "ai_coding", False,
     [("warnings.warn", "api"), ("DeprecationWarning", "api"), ("stacklevel", "config")],
     [],
     "what Python warning argument finally made deprecation notices show in the caller's output",
     "warning module stack frame argument caller visibility fix"),
    # --- 14 ---
    ("Ran a libcst codemod to replace 2,300 instances of the old logger import; CST preserved every trailing comment and trailing comma across the diff.", "milestone", "ai_coding", False,
     [("libcst", "tool"), ("codemod", "pattern"), ("logger", "library")],
     [],
     "which Python refactoring library handled the bulk logger import rewrite while keeping formatting intact",
     "concrete syntax tree bulk rewrite comment preserve whitespace safe"),
    # --- 15 ---
    ("Bowler let interns write refactor scripts without understanding Python AST visitors; the declarative query API was the selling point.", "fact", "ai_coding", False,
     [("Bowler", "tool"), ("Python", "language"), ("AST", "concept")],
     [],
     "which refactoring tool lowered the barrier for Python bulk edits without AST knowledge",
     "declarative query refactor tool barrier drop junior friendly"),
    # --- 16 ---
    ("ts-morph made the legacy React class-to-function codemod tractable; its TypeChecker integration caught three prop-type drift cases jscodeshift would have missed.", "decision", "ai_coding", False,
     [("ts-morph", "tool"), ("React", "framework"), ("TypeChecker", "api")],
     [],
     "which TypeScript refactoring library caught type-aware bugs during the class-to-function migration",
     "typed refactor codemod type checker integration drift detection"),
    # --- 17 ---
    ("Coexisted SQLAlchemy 1.4 and SQLAlchemy 2.0 style APIs in the same codebase for eight months; the future=True flag let us migrate file by file.", "architecture", "ai_coding", False,
     [("SQLAlchemy 1.4", "library"), ("SQLAlchemy 2.0", "library"), ("future=True", "config")],
     [],
     "which flag let two generations of the ORM live side by side during a gradual migration",
     "ORM dual style forward compat flag incremental file migration"),
    # --- 18 ---
    ("Replaced our custom DI container with stdlib functools.partial and explicit wiring; lost nothing and deleted 1,100 lines of reflection magic.", "decision", "ai_coding", False,
     [("DI container", "pattern"), ("functools.partial", "api")],
     [("functools.partial", "DI container", "REPLACES")],
     "what stdlib primitive let us retire the homegrown dependency-injection framework",
     "DI removal stdlib partial application explicit wiring reflection drop"),
    # --- 19 ---
    ("Scaled past the ORM and dropped to raw SQL for the reports query; six months later we moved it back into SQLAlchemy Core once the hotspot cooled.", "fact", "ai_coding", False,
     [("SQLAlchemy Core", "library"), ("reports query", "concept")],
     [],
     "why did one query round-trip from ORM to raw SQL and back within a year",
     "ORM escape hatch raw SQL hotspot performance later return oscillate"),
    # --- 20 ---
    ("Strangler migration of the legacy PHP app wrapped on 2026-03-12 after 14 months; Symfony served the last surviving admin pages behind Nginx.", "milestone", "ai_coding", False,
     [("PHP", "language"), ("Symfony", "framework"), ("Nginx", "service"), ("2026-03-12", "date")],
     [("Symfony", "PHP", "REPLACES")],
     "when did the long-running strangler rewrite of the old PHP app finally finish",
     "strangler completion legacy language framework cutover date milestone"),
    # --- 21 ---
    ("Two-phase deploy split the migration: phase one shipped the new code path off by default, phase two flipped the flag after observing the stack.", "architecture", "ai_coding", False,
     [("Two-phase deploy", "pattern")],
     [],
     "which deploy structure separated the risky switch from the code arrival",
     "deploy split code arrival flag flip decouple risk observation window"),
    # --- 22 ---
    ("Killed the legacy_checkout feature flag on 2026-03-28 after three months at 100% rollout; removing the branch deleted 2,800 lines of dead alternative code.", "milestone", "ai_coding", False,
     [("legacy_checkout", "pattern"), ("feature flag", "pattern"), ("2026-03-28", "date")],
     [],
     "when did we retire the rolled-out feature flag and how much dead code did the cleanup drop",
     "flag retirement long rollout stale branch dead code prune date"),
    # --- 23 ---
    ("Internal SDK v2 sunset plan: banner in v1 docs for 90 days, monthly email to owners, auto-open migration PRs from Renovate, then repo archive on 2026-06-30.", "architecture", "ai_coding", False,
     [("SDK v2", "concept"), ("Renovate", "tool"), ("2026-06-30", "date")],
     [],
     "what phased plan is driving the retirement of the old internal SDK",
     "sunset phased plan docs banner mail owner auto PR archive date"),
    # --- 24 ---
    ("Branch-by-abstraction around the cache layer let us swap Memcached for Redis without a long-lived branch; trunk-based flow survived the migration.", "architecture", "ai_coding", False,
     [("Memcached", "service"), ("Redis", "service")],
     [("Redis", "Memcached", "REPLACES")],
     "which technique avoided a long-lived branch during the cache backend swap",
     "abstraction layer cache backend swap trunk flow preserve migration"),
    # --- 25 ---
    ("Contract tests via Pact caught a silent response-shape drift the day we extracted the inventory service from the monolith.", "problem", "ai_coding", False,
     [("Pact", "tool"), ("inventory service", "concept")],
     [],
     "which consumer-driven testing tool caught the extracted service's shape drift",
     "consumer driven contract test drift catch extraction first day"),
    # --- 26 ---
    ("Archived six no-longer-used internal packages on 2026-02-05 after Renovate showed zero active consumers for 18 months; the monorepo CI build sped up 12%.", "milestone", "ai_coding", False,
     [("Renovate", "tool"), ("CI", "infrastructure"), ("2026-02-05", "date")],
     [],
     "when did we prune orphan packages from the monorepo based on dependency-scan evidence",
     "orphan package archive dependency scan evidence CI speed date"),
    # --- 27 ---
    ("Legacy cron jobs migrated to Temporal workflows one at a time behind a dispatcher; the cron entries became thin shims that called the workflow API.", "architecture", "ai_coding", False,
     [("cron", "tool"), ("Temporal", "service"), ("dispatcher", "pattern")],
     [("Temporal", "cron", "REPLACES")],
     "how did scheduled jobs migrate from the classic scheduler to the workflow engine gradually",
     "cron workflow migration dispatcher shim incremental swap strategy"),
    # --- 28 ---
    ("Blue-green was overkill for the database cutover; expand-contract plus a read-only window during the final flip worked with less operational risk.", "decision", "ai_coding", False,
     [("Blue-green", "pattern"), ("expand-contract", "pattern"), ("database", "concept")],
     [("expand-contract", "Blue-green", "PREFERS")],
     "why did we pick the additive column pattern over a full parallel stack for the DB migration",
     "cutover strategy pick additive parallel stack cost compare risk"),
    # --- 29 ---
    ("Spring Boot 2 to Spring Boot 3 migration leaned on OpenRewrite recipes; the javax-to-jakarta namespace sweep was 600 files but took one afternoon.", "milestone", "ai_coding", False,
     [("Spring Boot 2", "framework"), ("Spring Boot 3", "framework"), ("OpenRewrite", "tool"), ("jakarta", "concept")],
     [("Spring Boot 3", "Spring Boot 2", "REPLACES")],
     "which refactoring engine drove the bulk namespace rewrite during the Java framework upgrade",
     "framework major upgrade recipe driven mass namespace rewrite speed"),
    # --- 30 ---
    ("JUnit 4 to JUnit 5 happened incrementally thanks to the vintage engine; we turned it off a year later once the last @RunWith was gone.", "architecture", "ai_coding", False,
     [("JUnit 4", "library"), ("JUnit 5", "library"), ("vintage engine", "pattern"), ("@RunWith", "api")],
     [("JUnit 5", "JUnit 4", "REPLACES")],
     "which coexistence mechanism let both test generations run in one JVM during the gradual swap",
     "test framework coexistence vintage engine long tail cleanup window"),
    # --- 31 ---
    ("git-filter-repo cleaned 2 GB of old binary assets from the monorepo; we coordinated the force-push and mass re-clone across 40 engineers for a Monday.", "milestone", "ai_coding", False,
     [("git-filter-repo", "tool"), ("monorepo", "concept")],
     [],
     "which tool scrubbed the giant legacy binaries from the repo history and how did we land it",
     "history rewrite binary scrub coordinated re-clone team event day"),
    # --- 32 ---
    ("Django 3 to Django 4 migration on the legacy CRM kept USE_DEPRECATED_PYTZ = True for two sprints; we flipped it only after the zoneinfo tests stayed green.", "problem", "ai_coding", False,
     [("Django 3", "framework"), ("Django 4", "framework"), ("USE_DEPRECATED_PYTZ", "config"), ("zoneinfo", "library")],
     [("Django 4", "Django 3", "REPLACES")],
     "which Django setting let the timezone code limp along while we audited the zoneinfo swap",
     "framework upgrade deprecated flag limp timezone library audit swap"),
    # --- 33 ---
    ("Ruby-on-Rails 6 to Ruby-on-Rails 7 upgrade unblocked only after dual-booting with Appraisal; the app ran both Gemfile variants in CI for a month.", "architecture", "ai_coding", False,
     [("Ruby-on-Rails 6", "framework"), ("Ruby-on-Rails 7", "framework"), ("Appraisal", "tool"), ("Gemfile", "file")],
     [("Ruby-on-Rails 7", "Ruby-on-Rails 6", "REPLACES")],
     "which Ruby tooling pattern ran two framework versions in parallel CI during the upgrade",
     "dual boot gemset appraisal variant CI lane parallel upgrade prove"),
    # --- 34 ---
    ("Legacy stored-procedure logic moved to a Python worker via a shadow-table sync; the DB CPU dropped 40% once triggers replayed writes into the new path.", "milestone", "ai_coding", False,
     [("stored-procedure", "pattern"), ("Python worker", "concept"), ("shadow-table", "pattern")],
     [],
     "which sync pattern migrated logic out of the database triggers into an application worker",
     "stored procedure exit shadow table trigger replay CPU offload"),
    # --- 35 ---
    ("Prefer retiring a service over rewriting it when usage data shows two customers and a dashboard; we sunset three internal tools that way in 2025.", "preference", "ai_coding", False,
     [("service", "concept"), ("internal tools", "concept")],
     [],
     "which decision rule do we default to before investing in yet another rewrite",
     "retire preference over rewrite low usage evidence sunset rationale"),
    # --- 36 ---
    ("Hexagonal extraction of the notification domain stalled because the legacy repo still owned the User row; solved by moving ownership in an Expand-Contract pass.", "problem", "ai_coding", False,
     [("notification domain", "concept"), ("User row", "pattern"), ("Expand-Contract", "pattern")],
     [],
     "why did the notification service carve-out stall and what pattern unblocked it",
     "service extraction data ownership tangle expand contract unblock"),
    # --- 37 ---
    ("Replaced the custom workflow DSL with plain Python plus decorators; the legacy parser was 4k lines and its last contributor had left two years earlier.", "decision", "ai_coding", False,
     [("workflow DSL", "pattern"), ("Python", "language"), ("decorators", "pattern")],
     [("Python", "workflow DSL", "REPLACES")],
     "why did we swap the homegrown workflow language for native language constructs",
     "DSL retirement host language decorator owner attrition maintainability"),
    # --- 38 ---
    ("Parallel deploy of the payments service shipped traffic at 1% via a weighted Envoy split; errors at 1% meant rollback, not rollforward.", "architecture", "ai_coding", False,
     [("payments service", "concept"), ("Envoy", "service")],
     [],
     "which proxy feature enabled the cautious percentage ramp of the new payments service",
     "weighted split ramp proxy percentage rollback criterion guardrail"),
    # --- 39 ---
    ("Tidy-first commit hygiene split refactor commits from behaviour-change commits; PR reviews got 30% faster because reviewers could skim the mechanical diffs.", "preference", "ai_coding", False,
     [("Tidy-first", "pattern"), ("PR reviews", "activity")],
     [],
     "which commit discipline shortened pull-request review time on big refactors",
     "commit split refactor behaviour separate review skim speed gain"),
    # --- 40 ---
    ("Adopted preview deploys per PR so every legacy extraction could be exercised end-to-end without a shared staging queue.", "architecture", "ai_coding", False,
     [("preview deploys", "pattern"), ("staging", "infrastructure")],
     [],
     "which deploy workflow removed the staging queue bottleneck for extraction work",
     "per PR environment parallel test no shared queue migration cadence"),
    # --- 41 ---
    ("Legacy MySQL collation utf8 vs utf8mb4 surfaced during the schema migration; the Expand-Contract column copy with explicit CONVERT USING utf8mb4 was the only safe path.", "problem", "ai_coding", False,
     [("MySQL", "database"), ("utf8", "pattern"), ("utf8mb4", "pattern"), ("CONVERT USING", "api")],
     [],
     "which character-set trap forced the migration to use explicit conversion during the column copy",
     "collation legacy charset conversion explicit copy safe path pitfall"),
    # --- 42 ---
    ("Dropped the legacy SOAP endpoint on 2026-01-15 after six months at 0 RPS; monitoring proved abandonment better than any survey ever could.", "milestone", "ai_coding", False,
     [("SOAP", "protocol"), ("2026-01-15", "date")],
     [],
     "when did the last SOAP endpoint finally retire and what evidence justified it",
     "protocol retirement zero traffic evidence window decommission date"),
    # --- 43 ---
    ("Wrote a small ts-morph script to convert CommonJS require calls into ESM imports across the edge-handler package; 320 files migrated with a clean diff.", "milestone", "ai_coding", False,
     [("ts-morph", "tool"), ("CommonJS", "concept"), ("ESM", "concept")],
     [("ESM", "CommonJS", "REPLACES")],
     "which TypeScript tooling drove the require-to-import conversion across the edge package",
     "module format mass conversion script typed AST clean diff"),
    # --- 44 ---
    ("Sunset the v0 GraphQL schema by switching @deprecated reason strings to point at the exact new field; client telemetry showed which apps still queried legacy fields.", "architecture", "ai_coding", False,
     [("GraphQL", "technology"), ("@deprecated", "api")],
     [],
     "how did we drive clients off the old GraphQL fields with precise migration pointers",
     "schema deprecation reason string client telemetry migration pointer"),
    # --- 45 ---
    ("Extracted the recommendations engine via a seam-first refactor: introduced a boring interface, slid an adapter behind it, then built the replacement behind the adapter.", "architecture", "ai_coding", False,
     [("recommendations engine", "concept"), ("adapter", "pattern")],
     [],
     "which refactor sequence let the recommender swap in without freezing product work",
     "seam introduce adapter behind then replace order of operations refactor"),
    # --- 46 ---
    ("Coexisting two ORMs hurt: Prisma owned new writes while TypeORM served legacy reads, and the session-boundary bugs took three weeks to fully shake out.", "problem", "ai_coding", False,
     [("Prisma", "library"), ("TypeORM", "library"), ("ORM", "pattern")],
     [],
     "what was painful about running two ORMs in one codebase during the migration",
     "dual ORM session boundary transaction confusion debug window cost"),
    # --- 47 ---
    ("Consumer-deprecation campaigns work best when the replacement exists, the old thing has a clock, and the docs link the two in both directions.", "preference", "ai_coding", False,
     [("deprecation", "activity"), ("docs", "concept")],
     [],
     "which three ingredients make a deprecation campaign actually move consumers off the old API",
     "deprecation campaign ingredient replacement clock bidirectional link"),
    # --- 48 ---
    ("Ran a Scientist-style double-call against the legacy fraud service for four weeks before cutover; a 0.3% mismatch rate turned out to be a rounding bug in the old code.", "problem", "ai_coding", False,
     [("Scientist", "pattern"), ("fraud service", "concept")],
     [],
     "what did the parallel-call experiment reveal about the existing fraud system",
     "double call legacy bug discovery mismatch investigation root cause"),
    # --- 49 ---
    ("Big-bang ORM rewrite rejected after a one-week spike showed cross-cutting session assumptions everywhere; the incremental seam approach was adopted instead.", "decision", "ai_coding", False,
     [("Big-bang", "pattern"), ("ORM", "pattern"), ("spike", "activity"), ("incremental seam", "pattern")],
     [("incremental seam", "Big-bang", "PREFERS")],
     "why was the wholesale ORM replacement scrapped in favor of incremental work",
     "big bang rejected spike evidence incremental approach pick rationale"),
    # --- 50 ---
    ("Retired the telemetry of the old metrics client once Prometheus scraping covered the same signals; the dual-emit window lasted 45 days with a dashboard comparing the two.", "milestone", "ai_coding", False,
     [("Prometheus", "service"), ("metrics client", "concept"), ("dual-emit", "pattern")],
     [("Prometheus", "metrics client", "REPLACES")],
     "how did we prove the new monitoring covered everything before retiring the old emitter",
     "dual emit comparison dashboard coverage proof retire old emitter"),
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
    with OUT.open("w", encoding="utf-8") as f:
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
