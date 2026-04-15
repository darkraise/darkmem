"""One-off emitter for classification top-up batch-030 — multi_type mode, ai_coding slice.

Writes 100 rows to data/v2/classification/batch_030.tmp.jsonl with ids class-02901..03000.

Distribution (exact):
  fact         : 15
  decision     : 15
  preference   : 15
  problem      : 15
  architecture : 15
  milestone    : 15
  reference    : 10 (each with a citable source)

All rows use domain = ai_coding. No pair_id. Schema: {id, domain, text, memory_type}.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_030.tmp.jsonl"
ID_OFFSET = 2900

# Each row: (text, domain, memory_type). Text length 15–45 words.
ROWS: list[tuple[str, str, str]] = [
    # ---------------- fact (15) ----------------
    (
        "Mutation testing tools like Stryker and mutmut deliberately introduce small code changes and rerun the test suite to measure how many mutants survive, producing a sharper coverage signal than line coverage alone.",
        "ai_coding",
        "fact",
    ),
    (
        "GitHub Actions schedules each workflow run on an ephemeral runner with a clean filesystem, so any state that must persist between jobs has to be explicitly uploaded as an artifact or written to a cache key.",
        "ai_coding",
        "fact",
    ),
    (
        "The py-spy sampling profiler attaches to a running Python process without modifying its code and reads stack frames directly from memory, which makes it safe to use against long-lived production workloads.",
        "ai_coding",
        "fact",
    ),
    (
        "Vite performs on-demand transformation of source modules during development by serving native ES modules to the browser, which avoids the upfront bundling cost that traditional webpack dev servers pay.",
        "ai_coding",
        "fact",
    ),
    (
        "An Architecture Decision Record is a short markdown document that captures the context, decision, and consequences of a single choice, and the convention was first popularized by Michael Nygard in a 2011 blog post.",
        "ai_coding",
        "fact",
    ),
    (
        "Feature flag systems typically evaluate rules through a client-side SDK that fetches a ruleset from a central service, allowing per-request targeting without a network round trip on every evaluation path.",
        "ai_coding",
        "fact",
    ),
    (
        "OpenTelemetry traces propagate context across process boundaries through W3C traceparent and tracestate headers, and every span records a start timestamp, duration, kind, status, and optional attribute bag.",
        "ai_coding",
        "fact",
    ),
    (
        "In Rust, the Send and Sync marker traits are automatically implemented for types whose fields are all Send and Sync, which lets the compiler reject data races at compile time without runtime instrumentation.",
        "ai_coding",
        "fact",
    ),
    (
        "The React reconciler uses a virtual DOM diffing algorithm that runs in linear time by comparing elements of the same type at the same position and discarding the subtree when types differ.",
        "ai_coding",
        "fact",
    ),
    (
        "Domain-driven design distinguishes between entities, which have a stable identity across their lifecycle, and value objects, which are defined entirely by their attributes and are compared structurally.",
        "ai_coding",
        "fact",
    ),
    (
        "ESLint applies rules by walking an AST produced by Espree or a custom parser, and each rule subscribes to specific node types through a visitor pattern rather than reparsing the file itself.",
        "ai_coding",
        "fact",
    ),
    (
        "The Web Content Accessibility Guidelines define success criteria at levels A, AA, and AAA, and most regulated procurement contracts require at minimum WCAG 2.1 level AA conformance for public-facing interfaces.",
        "ai_coding",
        "fact",
    ),
    (
        "Unity's entity component system stores components in contiguous chunks keyed by archetype, which gives cache-friendly iteration over entities that share the same set of components during a frame update.",
        "ai_coding",
        "fact",
    ),
    (
        "The OWASP Top 10 for 2021 lists broken access control as the highest-ranked web application risk category, having moved up from fifth place in the 2017 edition of the same document.",
        "ai_coding",
        "fact",
    ),
    (
        "React Native's new architecture replaces the asynchronous bridge with JSI, a C++ interface that lets JavaScript hold direct references to native objects and call their methods synchronously when needed.",
        "ai_coding",
        "fact",
    ),

    # ---------------- decision (15) ----------------
    (
        "We decided to adopt Playwright over Cypress for end-to-end testing because Playwright's multi-browser support and built-in trace viewer made debugging flaky tests measurably faster during the last hardening sprint.",
        "ai_coding",
        "decision",
    ),
    (
        "The team chose to standardize on pnpm workspaces rather than Yarn or npm for the monorepo because its content-addressable store cuts disk usage dramatically and its strict linking catches phantom dependencies early.",
        "ai_coding",
        "decision",
    ),
    (
        "We settled on conventional commits enforced by commitlint in a Husky pre-push hook so that changelogs and semantic versioning can be fully automated without relying on human discipline every pull request.",
        "ai_coding",
        "decision",
    ),
    (
        "After weighing options, we chose Zustand over Redux Toolkit for the new dashboard because its minimal API and absence of boilerplate reducers fit a small team that values fast iteration over strict formalism.",
        "ai_coding",
        "decision",
    ),
    (
        "The architecture group decided to require an ADR for any new external dependency exceeding one megabyte unpacked, because dependency drift had become the dominant source of unplanned work in the prior quarter.",
        "ai_coding",
        "decision",
    ),
    (
        "We chose Storybook plus Chromatic for visual regression testing of the design system rather than rolling our own screenshot diffing, because the cost of maintaining that pipeline far exceeded the subscription.",
        "ai_coding",
        "decision",
    ),
    (
        "The mobile guild decided to standardize on Kotlin Multiplatform for new shared modules instead of maintaining parallel Swift and Kotlin implementations, because business logic drift between platforms was causing subtle defects.",
        "ai_coding",
        "decision",
    ),
    (
        "We decided to adopt Tailwind CSS across all product surfaces rather than continue maintaining our bespoke SCSS design tokens, because token drift and specificity bugs consumed roughly two engineer-days per sprint.",
        "ai_coding",
        "decision",
    ),
    (
        "After a spike, we chose Sentry for error tracking over Bugsnag because its richer release tracking and source map upload tooling integrate more cleanly with our existing Vite build pipeline.",
        "ai_coding",
        "decision",
    ),
    (
        "The team decided to require type hints on all new Python code and to enforce this through mypy in CI, because runtime errors from implicit Any types were leaking into production at an unacceptable rate.",
        "ai_coding",
        "decision",
    ),
    (
        "We are adopting trunk-based development with pull-request queues rather than GitFlow because long-lived release branches were accumulating merge conflicts and delaying security patches by nearly two weeks on average.",
        "ai_coding",
        "decision",
    ),
    (
        "The frontend team decided to adopt TanStack Query for server state instead of continuing to hand-roll fetch wrappers, because cache invalidation bugs were the single largest source of user-reported defects last quarter.",
        "ai_coding",
        "decision",
    ),
    (
        "We chose GitHub Copilot over Tabnine for the engineering organization because per-seat cost, enterprise audit support, and measured acceptance rate on an internal benchmark all favored the GitHub offering.",
        "ai_coding",
        "decision",
    ),
    (
        "The infrastructure group decided to generate API clients from OpenAPI specifications rather than hand-write them, because drift between the server contract and client code caused three customer-visible incidents in six months.",
        "ai_coding",
        "decision",
    ),
    (
        "We decided to keep feature flag evaluations server-side for privacy-sensitive rules rather than ship them to the client SDK, because leaking targeting criteria to browsers would expose customer segmentation to competitors.",
        "ai_coding",
        "decision",
    ),

    # ---------------- preference (15) ----------------
    (
        "I prefer writing unit tests in an arrange-act-assert block layout separated by blank lines, because the visual structure makes failure diagnosis faster than one-line assertions crammed against their setup.",
        "ai_coding",
        "preference",
    ),
    (
        "When debugging I lean on conditional breakpoints and logpoints in VS Code rather than editing the source with print statements, because I hate accidentally committing debug noise into pull requests.",
        "ai_coding",
        "preference",
    ),
    (
        "My default profiling workflow starts with py-spy for a flame graph, moves to cProfile for precise call counts, and only drops to line_profiler when I already suspect a specific hot function.",
        "ai_coding",
        "preference",
    ),
    (
        "I prefer small focused pull requests under four hundred lines of diff, because reviewer feedback quality degrades sharply above that threshold and merge conflicts compound faster on larger branches.",
        "ai_coding",
        "preference",
    ),
    (
        "For frontend styling I favor utility-first CSS with Tailwind over component-scoped styles because the markup carries its own design language and refactoring does not require hunting through separate style files.",
        "ai_coding",
        "preference",
    ),
    (
        "I prefer REST APIs that use plural resource nouns with hyphenated paths and reserve verbs for the HTTP method itself, because that convention maps cleanly onto client generators and routing tables.",
        "ai_coding",
        "preference",
    ),
    (
        "When refactoring I like to land the behavior-preserving move as one commit and the behavior change as a separate commit afterward, because it makes reverting targeted problems much simpler during incident response.",
        "ai_coding",
        "preference",
    ),
    (
        "I prefer authoring docs as markdown checked into the same repository as the code, because docs that live in a separate wiki or CMS drift out of date within about a quarter in my experience.",
        "ai_coding",
        "preference",
    ),
    (
        "For state management in React I reach for useReducer with immer before Redux, because most component trees never grow complex enough to justify the extra ceremony that a global store brings.",
        "ai_coding",
        "preference",
    ),
    (
        "I prefer feature flags that default to off and require an explicit expiry date in the flag metadata, because stale flags accumulate dead branches that make the codebase harder to reason about over time.",
        "ai_coding",
        "preference",
    ),
    (
        "My accessibility workflow starts with semantic HTML elements, layers ARIA only where native semantics cannot express intent, and ends with a screen reader pass before merging any user-facing component.",
        "ai_coding",
        "preference",
    ),
    (
        "I prefer running Lighthouse CI on every pull request with a strict performance budget rather than manual audits, because regressions otherwise slip in as accidental bundle size increases on routine feature work.",
        "ai_coding",
        "preference",
    ),
    (
        "For code review I prefer leaving comments framed as questions rather than demands, because it keeps the reviewer-author relationship collaborative and often surfaces context I did not have before writing the note.",
        "ai_coding",
        "preference",
    ),
    (
        "I prefer writing new game logic with pure functions over component methods, because pure functions are trivially unit-testable without spinning up the engine's scene graph or entity lifecycle hooks.",
        "ai_coding",
        "preference",
    ),
    (
        "When writing concurrent code I prefer channels and structured concurrency over shared mutable state guarded by locks, because data races are far harder to reason about than ownership transfer at well-defined boundaries.",
        "ai_coding",
        "preference",
    ),

    # ---------------- problem (15) ----------------
    (
        "Our test suite has a flaky failure in the order reconciliation test because the assertion depends on current wall-clock time, and runners that straddle a second boundary produce non-deterministic results.",
        "ai_coding",
        "problem",
    ),
    (
        "The CI pipeline takes fifty-two minutes end to end because the integration stage reinstalls node_modules from scratch on every run, defeating the cache key that was set up for the unit test stage.",
        "ai_coding",
        "problem",
    ),
    (
        "The mobile app's cold start has regressed from 1.1 seconds to 2.4 seconds on mid-tier Android hardware, and the flamegraph shows a new synchronous JSON parse of the feature flag payload on the main thread.",
        "ai_coding",
        "problem",
    ),
    (
        "Our TypeScript build is emitting stale type declarations because tsc incremental mode is reading a cache from a previous branch, and the incremental marker file is not included in the CI cache key.",
        "ai_coding",
        "problem",
    ),
    (
        "The code review bot is posting duplicate comments on every push because it does not deduplicate against prior runs, and reviewers are starting to ignore its output entirely as a result.",
        "ai_coding",
        "problem",
    ),
    (
        "Profiling reveals that 40 percent of our API latency is spent in N+1 queries from a newly added serializer, because the select_related call was dropped during a refactor and no integration test caught the regression.",
        "ai_coding",
        "problem",
    ),
    (
        "Our game's frame time spikes every few seconds on lower-end GPUs because the shader compiler is hitting the driver cache synchronously on the render thread instead of being warmed during the loading screen.",
        "ai_coding",
        "problem",
    ),
    (
        "Internationalized strings are rendering with visible placeholder tokens in the Japanese locale because the extraction script missed interpolations that use template literals instead of the format helper the team standardized on.",
        "ai_coding",
        "problem",
    ),
    (
        "The feature flag SDK is returning the default value during the first 300 milliseconds after page load because the client bundle loads the evaluation payload after the initial render cycle has already completed.",
        "ai_coding",
        "problem",
    ),
    (
        "Our dependency updates are blocked because Dependabot keeps opening pull requests that fail the peer-dependency check, and no one on the team has the context to resolve the conflicting semver ranges manually.",
        "ai_coding",
        "problem",
    ),
    (
        "The screen reader announces the submit button twice on the checkout page because an outer div carries a redundant aria-label while the inner button already has accessible text from its visible label.",
        "ai_coding",
        "problem",
    ),
    (
        "Our LLM integration occasionally returns malformed JSON even with strict schema prompting, because rare tokens in user input are triggering completions that omit the closing brace before hitting the max token limit.",
        "ai_coding",
        "problem",
    ),
    (
        "The observability dashboard is missing traces for the payment service because the OpenTelemetry instrumentation library was silently disabled when a transitive dependency pinned an incompatible protobuf version last week.",
        "ai_coding",
        "problem",
    ),
    (
        "Hot module replacement stopped working locally for the design system package after the workspace migration because pnpm now hoists shared dependencies to a path that Vite's file watcher does not monitor.",
        "ai_coding",
        "problem",
    ),
    (
        "Our concurrency tests are deadlocking intermittently because two background workers acquire the same pair of locks in opposite orders, and the issue only surfaces when the scheduler happens to interleave them precisely.",
        "ai_coding",
        "problem",
    ),

    # ---------------- architecture (15) ----------------
    (
        "The frontend is structured as a TanStack Router single-page application backed by TanStack Query for server state, with shadcn components layered on Radix primitives and Tailwind utilities handling the visual system.",
        "ai_coding",
        "architecture",
    ),
    (
        "Our CI/CD pipeline is a directed graph of reusable GitHub Actions workflows, where build and test run on pull requests, and a separate deployment workflow triggered by release tags performs canary rollout to production.",
        "ai_coding",
        "architecture",
    ),
    (
        "The refactoring toolkit is organized as a plugin host with typed extension points, where individual codemods register against AST node types and the host orchestrates parsing, traversal, and printing once per file.",
        "ai_coding",
        "architecture",
    ),
    (
        "Our documentation site is built with Docusaurus from markdown alongside the source, and a custom remark plugin inlines code examples from the test suite so that examples cannot drift out of sync with behavior.",
        "ai_coding",
        "architecture",
    ),
    (
        "The feature flag system is split into a control plane that stores rules, an edge worker that evaluates them close to the user, and an event sink that records every evaluation for downstream analytics.",
        "ai_coding",
        "architecture",
    ),
    (
        "The observability subsystem uses the OpenTelemetry collector as a gateway, fanning metrics to Prometheus, traces to Tempo, and logs to Loki, with Grafana providing a unified view through correlated exemplars.",
        "ai_coding",
        "architecture",
    ),
    (
        "The mobile app follows a clean architecture layering with a Kotlin Multiplatform domain module free of framework dependencies, platform-specific presentation layers, and a shared repository layer that mediates local and remote data sources.",
        "ai_coding",
        "architecture",
    ),
    (
        "The domain-driven checkout service is split into bounded contexts for pricing, payments, and fulfillment, each owning its database and communicating through a thin set of integration events published to a shared bus.",
        "ai_coding",
        "architecture",
    ),
    (
        "Our a11y architecture centralizes focus management and live region announcements in a small library consumed by every route, so that screen reader users receive consistent navigation cues without per-page re-implementation.",
        "ai_coding",
        "architecture",
    ),
    (
        "The i18n pipeline extracts strings at build time into an ICU-compatible catalog, pushes them to Crowdin for translation, and syncs translated bundles back through a scheduled workflow that opens automated pull requests.",
        "ai_coding",
        "architecture",
    ),
    (
        "The LLM integration architecture places a thin prompt-templating layer over a provider-agnostic client, with a retry-and-fallback policy that can swap between Claude, GPT, and a locally hosted model based on rule evaluation.",
        "ai_coding",
        "architecture",
    ),
    (
        "Our game engine is organized around an entity component system with archetype-based storage, a job system that schedules system ticks across worker threads, and a render graph that resolves per-frame resource lifetimes declaratively.",
        "ai_coding",
        "architecture",
    ),
    (
        "The code review automation runs as a GitHub App that receives pull request webhooks, fetches the diff, invokes a set of reviewer agents in parallel, and consolidates their findings into a single summary comment.",
        "ai_coding",
        "architecture",
    ),
    (
        "The type-driven validation layer derives runtime schemas from TypeScript types through a compile-time codegen step, so that the same shape enforces both static checking at the boundary and runtime rejection of malformed payloads.",
        "ai_coding",
        "architecture",
    ),
    (
        "Our security-focused coding pipeline wires Semgrep, CodeQL, and gitleaks into a single GitHub Actions workflow that annotates pull requests and fails the build whenever a new high-severity finding is introduced in changed files.",
        "ai_coding",
        "architecture",
    ),

    # ---------------- milestone (15) ----------------
    (
        "We cut CI runtime from 52 minutes to 14 minutes last sprint by parallelizing the integration stage, caching node_modules across jobs, and sharding the Playwright suite across four runners by test manifest.",
        "ai_coding",
        "milestone",
    ),
    (
        "The refactor to extract the billing domain into its own module landed this week, concluding an eight-month effort and shrinking the core service binary by roughly thirty percent of its prior disk footprint.",
        "ai_coding",
        "milestone",
    ),
    (
        "The developer experience team shipped the one-command local dev environment yesterday, so new hires can now run the full stack after cloning the repo and executing a single bootstrap script without manual steps.",
        "ai_coding",
        "milestone",
    ),
    (
        "We completed the migration from REST to GraphQL for the account service this afternoon, deprecated the old endpoints with a six-month sunset header, and published client migration notes to the internal docs portal.",
        "ai_coding",
        "milestone",
    ),
    (
        "The ADR catalog hit one hundred published records last week, giving the engineering organization a searchable historical index of every significant architectural choice made since the program began two years ago.",
        "ai_coding",
        "milestone",
    ),
    (
        "We rolled out the new security-focused linting profile to every repository this sprint, closing the final compliance action item from the third-party penetration test conducted at the end of last quarter.",
        "ai_coding",
        "milestone",
    ),
    (
        "The observability coverage milestone landed yesterday, with every production service now emitting OpenTelemetry traces and the on-call rotation able to trace any customer-reported issue end to end through a single dashboard.",
        "ai_coding",
        "milestone",
    ),
    (
        "We finished the error-handling rewrite across the payments path last week, converting implicit exceptions into typed result objects and eliminating the last unhandled rejection that had caused sporadic alerts for months.",
        "ai_coding",
        "milestone",
    ),
    (
        "The concurrency refactor of the ingestion worker shipped this morning, replacing ad-hoc mutex juggling with structured channels and cutting the ninety-ninth percentile processing latency from 2.3 seconds down to 410 milliseconds.",
        "ai_coding",
        "milestone",
    ),
    (
        "We completed the rollout of AI pair programming across the engineering organization this quarter, issuing seats, measuring acceptance rate, and publishing an internal playbook describing safe and productive usage patterns.",
        "ai_coding",
        "milestone",
    ),
    (
        "The code review automation reached steady state last Friday, now handling roughly thirty percent of nit-level comments that previously consumed human reviewer time on every non-trivial pull request across the organization.",
        "ai_coding",
        "milestone",
    ),
    (
        "We finalized the migration of the entire Python monorepo to strict mypy mode this week, closing out a two-quarter effort that touched every module and caught roughly four hundred latent type issues along the way.",
        "ai_coding",
        "milestone",
    ),
    (
        "The design system reached 1.0 yesterday with a frozen public API, full Storybook coverage, and automated Chromatic visual regression running on every pull request, clearing the blocker for consumer teams to adopt it.",
        "ai_coding",
        "milestone",
    ),
    (
        "The i18n program completed coverage of the top five locales this afternoon, pushing the translated string coverage above ninety-eight percent and unblocking the planned product launch in two new European markets.",
        "ai_coding",
        "milestone",
    ),
    (
        "The accessibility audit remediation wrapped up this week, bringing the checkout flow into WCAG 2.1 AA conformance, closing the last blocker for the enterprise procurement contract that was pending on accessibility proof.",
        "ai_coding",
        "milestone",
    ),

    # ---------------- reference (10) — each has a real citable source ----------------
    (
        "According to the Google Engineering Practices documentation on code review, the primary goal of every review is to ensure that the overall code health of the codebase improves over time with each change landed.",
        "ai_coding",
        "reference",
    ),
    (
        "As described in Martin Fowler's Refactoring second edition, the Extract Function refactoring is the single most common move and is motivated primarily by reducing the cognitive load required to understand a block of code.",
        "ai_coding",
        "reference",
    ),
    (
        "The TypeScript Handbook's section on narrowing defines a type guard as a function whose return type is a type predicate of the form parameterName is Type, which allows the compiler to refine unions at call sites.",
        "ai_coding",
        "reference",
    ),
    (
        "Per the OWASP Top 10 2021 document, broken access control moved up to the first position, and the recommended mitigation is to deny by default and enforce access control decisions server-side on every request.",
        "ai_coding",
        "reference",
    ),
    (
        "According to the WCAG 2.1 specification published by the W3C, success criterion 1.4.3 requires a minimum contrast ratio of 4.5 to 1 for normal body text and 3 to 1 for large text at conformance level AA.",
        "ai_coding",
        "reference",
    ),
    (
        "As established in Eric Evans's Domain-Driven Design book from 2003, a bounded context is the explicit boundary within which a particular domain model applies, and integration between contexts should happen through context maps.",
        "ai_coding",
        "reference",
    ),
    (
        "The OpenTelemetry specification at opentelemetry.io defines a span as the primary building block of a distributed trace, carrying a name, start and end timestamps, status, kind, and an attribute bag of key-value pairs.",
        "ai_coding",
        "reference",
    ),
    (
        "According to the Conventional Commits 1.0.0 specification, a commit message structured as type(scope): description enables automated semantic versioning and changelog generation tools to classify changes without human intervention.",
        "ai_coding",
        "reference",
    ),
    (
        "As documented in the React documentation chapter on rules of hooks, hooks must be called at the top level of a component or another hook, and the plugin eslint-plugin-react-hooks enforces this statically.",
        "ai_coding",
        "reference",
    ),
    (
        "Per the Web Content Accessibility Guidelines 2.1 guideline 2.1.1, all functionality of the content must be operable through a keyboard interface without requiring specific timings for individual keystrokes except where the underlying function requires it.",
        "ai_coding",
        "reference",
    ),
]


def emit() -> int:
    assert len(ROWS) == 100, f"expected 100 rows, got {len(ROWS)}"
    counts: dict[str, int] = {}
    for _, _, mt in ROWS:
        counts[mt] = counts.get(mt, 0) + 1
    expected = {
        "fact": 15,
        "decision": 15,
        "preference": 15,
        "problem": 15,
        "architecture": 15,
        "milestone": 15,
        "reference": 10,
    }
    assert counts == expected, f"distribution mismatch: {counts} != {expected}"
    for _, domain, _ in ROWS:
        assert domain == "ai_coding", f"all rows must be ai_coding, got {domain}"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (text, domain, mt) in enumerate(ROWS, start=1):
            row_id = f"class-{ID_OFFSET + i:05d}"
            f.write(
                json.dumps(
                    {"id": row_id, "domain": domain, "text": text, "memory_type": mt},
                    ensure_ascii=False,
                )
                + "\n"
            )
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
