"""One-off emitter for shared-base batch-116 — ai_coding domain (feature flag rollout patterns: LaunchDarkly, Unleash, Flagsmith, Split.io, ConfigCat, PostHog, OpenFeature, percentage/canary/kill-switch/segment rollouts, experimentation vs toggles, stale-flag cleanup, SDK patterns, multi-variate and prerequisite flags, CI preview integrations).

Writes 50 rows to data/v2/shared/batch_116.tmp.jsonl with ids shared-05751..05800.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_116.tmp.jsonl"
ID_OFFSET = 5750

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Adopted OpenFeature as the flag-evaluation abstraction so the application code stops importing LaunchDarkly client directly; swapping providers is now a bootstrap-only change.", "decision", "ai_coding", False,
     [("OpenFeature", "protocol"), ("LaunchDarkly", "service"), ("flag-evaluation", "pattern")],
     [("OpenFeature", "LaunchDarkly", "REPLACES")],
     "which abstraction replaced the direct LaunchDarkly SDK imports across the application code",
     "openfeature abstraction launchdarkly provider swap bootstrap vendor"),
    # --- 2 ---
    ("Percentage rollout on the new checkout ramps 1 -> 5 -> 25 -> 50 -> 100 with a 24-hour soak at each step; error-rate SLO breach auto-pauses the progression.", "architecture", "ai_coding", False,
     [("Percentage rollout", "pattern"), ("checkout", "service"), ("SLO", "concept")],
     [],
     "how does the checkout percentage rollout progress through its stages and what pauses it",
     "percentage rollout ramp soak slo auto pause checkout progression"),
    # --- 3 ---
    ("Killed the in-house flag service in favour of Unleash self-hosted; the SDK's graceful-degradation cache meant we could keep the same 'fail to last-known-good' semantics we already relied on.", "milestone", "ai_coding", False,
     [("Unleash", "service"), ("in-house flag service", "service"), ("graceful-degradation", "pattern")],
     [("Unleash", "in-house flag service", "REPLACES")],
     "which open-source flag platform replaced the home-grown flag service and what made the cutover safe",
     "unleash self hosted replace in house flag graceful degradation cache"),
    # --- 4 ---
    ("Kill-switch flags get a KS- prefix and a mandatory runbook link in the description; on-call can disable them without waiting for a deploy and the dashboard surfaces them first.", "preference", "ai_coding", False,
     [("KS-", "pattern"), ("Kill-switch", "pattern"), ("runbook", "pattern")],
     [],
     "which naming convention marks kill-switch flags and why does on-call care",
     "kill switch flag prefix runbook link on call dashboard disable"),
    # --- 5 ---
    ("Canary rollout of the payment engine v2 targets a 2% user-segment carved by hashed customer id mod 50; dogfooding staff always resolve to the new branch via a prerequisite flag.", "architecture", "ai_coding", False,
     [("Canary rollout", "pattern"), ("payment engine v2", "service"), ("prerequisite flag", "pattern"), ("hashed customer id", "pattern")],
     [("prerequisite flag", "Canary rollout", "APPLIES_TO")],
     "how does the payment-engine canary select its 2% segment and how do staff get forced into it",
     "canary rollout hash modulo segment prerequisite dogfood staff"),
    # --- 6 ---
    ("Switched feature flag vendor from Split.io to Flagsmith for cost reasons; the new bill sits under a tenth of the old one and the self-hosted option gives us an escape hatch.", "decision", "ai_coding", False,
     [("Split.io", "service"), ("Flagsmith", "service")],
     [("Flagsmith", "Split.io", "REPLACES")],
     "which flag vendor swap did we make to cut cost and what escape hatch did we pick up",
     "flagsmith replace split io cost self hosted escape hatch vendor"),
    # --- 7 ---
    ("Experimentation flags go through PostHog feature flags because they integrate directly with the analytics events; plain toggles stay on ConfigCat where experiment metadata would be noise.", "architecture", "ai_coding", False,
     [("PostHog", "service"), ("ConfigCat", "service"), ("Experimentation", "concept"), ("toggles", "pattern")],
     [("PostHog", "ConfigCat", "PREFERS")],
     "which tool handles experimentation flags versus plain toggles and why the split",
     "posthog experimentation analytics configcat toggle split tool"),
    # --- 8 ---
    ("The OpenFeature provider for Flagsmith ships as a thin adapter in libs/feature-flags; app code calls booleanValue(key, default, evaluationContext) and never sees vendor types.", "architecture", "ai_coding", False,
     [("OpenFeature", "protocol"), ("Flagsmith", "service"), ("booleanValue", "method"), ("evaluationContext", "pattern")],
     [("OpenFeature", "Flagsmith", "USES")],
     "how is the Flagsmith integration shaped so that application code stays provider-agnostic",
     "openfeature provider flagsmith adapter boolean value context app"),
    # --- 9 ---
    ("Stale-flag cleanup runs as a weekly job: any flag older than 90 days with 100% or 0% rollout and zero variant variance gets filed as a cleanup ticket automatically.", "architecture", "ai_coding", False,
     [("Stale-flag cleanup", "pattern"), ("cleanup ticket", "concept")],
     [],
     "how does the platform team keep stale feature flags from piling up across the codebase",
     "stale flag cleanup age rollout saturation ticket weekly job"),
    # --- 10. noise ---
    ("The espresso machine on floor two finally stopped leaving a puddle under it after someone replaced the drip tray.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("piranha-java lints the Java monorepo for stale flag references; when a flag is archived in LaunchDarkly a follow-up PR is auto-opened to delete the dead branches.", "architecture", "ai_coding", False,
     [("piranha-java", "tool"), ("LaunchDarkly", "service")],
     [("piranha-java", "LaunchDarkly", "RELATED_TO")],
     "which lint tool automates deletion of archived LaunchDarkly flag branches in the Java monorepo",
     "piranha java lint stale flag launchdarkly archive auto pr"),
    # --- 12 ---
    ("Rails flipper backs the admin-only internal toggles because its ActiveRecord adapter fits naturally; customer-facing flags live on LaunchDarkly where streaming updates matter.", "decision", "ai_coding", False,
     [("Rails flipper", "library"), ("ActiveRecord", "library"), ("LaunchDarkly", "service")],
     [("LaunchDarkly", "Rails flipper", "IMPROVES_ON")],
     "which flag layer handles internal admin toggles and which one handles customer-facing rollouts",
     "rails flipper active record internal launchdarkly customer facing split"),
    # --- 13 ---
    ("User-segment targeting uses Unleash constraints on plan tier, country, and a custom beta_cohort attribute; the SDK passes these through unleashContext on every evaluation.", "architecture", "ai_coding", False,
     [("Unleash", "service"), ("constraints", "pattern"), ("unleashContext", "pattern"), ("beta_cohort", "pattern")],
     [],
     "how does user-segment targeting express plan and cohort rules in the Unleash setup",
     "unleash constraint plan country beta cohort context segment target"),
    # --- 14 ---
    ("Multi-variate flag 'cart-layout' serves four string variants weighted 40/30/20/10; the default is pinned in code so a provider outage serves 'classic' instead of throwing.", "architecture", "ai_coding", False,
     [("Multi-variate flag", "pattern"), ("cart-layout", "config"), ("classic", "pattern")],
     [],
     "how is the cart-layout multi-variate flag weighted and what is the outage default",
     "multi variate flag variant weight default outage classic pin"),
    # --- 15 ---
    ("Preview environments wire a per-PR flag prefix so a branch under review can flip flags without leaking into staging; the CI step patches evaluationContext.environment to pr-<num>.", "architecture", "ai_coding", False,
     [("Preview environments", "pattern"), ("evaluationContext", "pattern"), ("CI", "tool")],
     [],
     "how do preview environments isolate their flag state from shared staging during CI",
     "preview environment per pr prefix evaluation context ci isolate"),
    # --- 16 ---
    ("A flag-as-circuit-breaker guards the third-party address-lookup call; when error budget burns past 2% per minute the flag auto-flips to degraded mode for an hour.", "architecture", "ai_coding", False,
     [("flag-as-circuit-breaker", "pattern"), ("address-lookup", "service"), ("error budget", "concept")],
     [("flag-as-circuit-breaker", "address-lookup", "APPLIES_TO")],
     "how does the address-lookup integration use a feature flag as a circuit breaker",
     "feature flag circuit breaker error budget burn degrade address"),
    # --- 17 ---
    ("The distinction between experiment and toggle is documented in the RFC: experiments carry a hypothesis and a stop date, toggles do not; experiments must graduate or be killed within 6 weeks.", "reference", "ai_coding", False,
     [("RFC", "publication"), ("experiment", "concept"), ("toggle", "pattern")],
     [],
     "which document spells out the difference between experiment and toggle flags and the 6-week rule",
     "experiment toggle distinction rfc hypothesis stop date six week"),
    # --- 18 ---
    ("ConfigCat's targeting rules resolved simpler than we expected for plan-tier gates; the no-code editor let product-ops run the premium-only toggle without a deploy.", "fact", "ai_coding", False,
     [("ConfigCat", "service"), ("targeting rules", "pattern"), ("product-ops", "organization")],
     [],
     "which flag platform let product-ops run plan-tier gates without a deploy",
     "configcat targeting rule plan tier premium product ops no code"),
    # --- 19 ---
    ("Go services import the openfeature-go SDK; the provider factory lives in pkg/flags and is swapped by a build tag so tests default to the in-memory provider.", "architecture", "ai_coding", False,
     [("openfeature-go", "library"), ("in-memory provider", "pattern"), ("build tag", "pattern")],
     [],
     "how do Go services wire flag evaluation so tests use an in-memory provider instead of the real one",
     "openfeature go sdk provider factory build tag in memory test"),
    # --- 20 ---
    ("Feature-flag testing strategy pins both variants in the test matrix for any flag that gates user-visible behaviour; a pytest fixture forces resolution per parametrize row.", "preference", "ai_coding", False,
     [("pytest", "tool"), ("fixture", "pattern"), ("parametrize", "pattern")],
     [],
     "how does the test suite cover both branches of a user-visible feature flag",
     "feature flag test matrix both variant pytest fixture parametrize"),
    # --- 21 ---
    ("Prerequisite flag 'new-billing-enabled' gates nine downstream flags; turning off the parent short-circuits resolution so the subsystem can be rolled back without touching every child.", "architecture", "ai_coding", False,
     [("Prerequisite flag", "pattern"), ("new-billing-enabled", "config")],
     [],
     "how does the billing subsystem use a prerequisite flag to roll back without touching every child toggle",
     "prerequisite flag parent child gate rollback billing short circuit"),
    # --- 22 ---
    ("PostHog replaced the separate analytics-plus-flags split across Amplitude and LaunchDarkly; single event id lets us tie flag exposure to downstream funnel events without a join job.", "decision", "ai_coding", False,
     [("PostHog", "service"), ("Amplitude", "service"), ("LaunchDarkly", "service"), ("funnel", "concept")],
     [("PostHog", "Amplitude", "REPLACES"), ("PostHog", "LaunchDarkly", "REPLACES")],
     "which consolidation replaced the Amplitude-plus-LaunchDarkly split and what did it simplify",
     "posthog replace amplitude launchdarkly split analytics flag funnel"),
    # --- 23 ---
    ("Flag evaluations emit an exposure event with flag key, variant, and hashed user id; the warehouse team uses this as the source of truth for experiment analysis.", "architecture", "ai_coding", False,
     [("exposure event", "pattern"), ("flag key", "pattern"), ("warehouse", "service")],
     [],
     "which event schema carries the flag-evaluation record into the warehouse for experiment analysis",
     "exposure event flag key variant hashed user id warehouse truth"),
    # --- 24 ---
    ("LaunchDarkly Relay Proxy fronts the SDKs from the edge POPs; the tail-latency at p99 dropped from 210 ms to 18 ms after we moved off the public streaming endpoint.", "milestone", "ai_coding", False,
     [("LaunchDarkly Relay Proxy", "service"), ("POP", "infrastructure"), ("p99", "concept")],
     [],
     "which component shaved tail-latency off the LaunchDarkly SDK streaming path",
     "launchdarkly relay proxy pop tail latency p99 streaming endpoint"),
    # --- 25 ---
    ("Flag hygiene lint rule forbids boolean flag defaults that match the 'on' variant; the code must default to the safe off-path so a provider outage never accidentally ships the new feature.", "preference", "ai_coding", False,
     [("lint rule", "pattern"), ("boolean flag", "pattern"), ("off-path", "pattern")],
     [],
     "which lint rule prevents flag defaults from accidentally shipping the new behaviour during a provider outage",
     "flag hygiene lint default off path outage boolean safe ship"),
    # --- 26 ---
    ("The Flagsmith Java SDK is pinned to the synchronous evaluator for server-side calls; the async flavour bit us when a cold JVM resolved flags before the first poll completed.", "problem", "ai_coding", False,
     [("Flagsmith Java SDK", "library"), ("synchronous evaluator", "pattern"), ("JVM", "platform")],
     [],
     "which Flagsmith SDK mode did we pin after a cold-JVM resolution bug and why",
     "flagsmith java sdk synchronous evaluator cold jvm poll pin"),
    # --- 27 ---
    ("Split.io's targeting trees were expressive but the traffic type concept bled vendor terminology into our domain; OpenFeature's plain evaluationContext is a cleaner fit.", "fact", "ai_coding", False,
     [("Split.io", "service"), ("traffic type", "pattern"), ("OpenFeature", "protocol"), ("evaluationContext", "pattern")],
     [("OpenFeature", "Split.io", "IMPROVES_ON")],
     "why did we feel OpenFeature's evaluationContext fit our domain better than Split.io's traffic types",
     "split io traffic type vendor terminology openfeature context clean"),
    # --- 28 ---
    ("Unleash replaced the in-house flag system mainly because we wanted to stop owning the SDK; the community SDK set covers Node, Go, Java, Python, and Ruby which matched our stack exactly.", "decision", "ai_coding", False,
     [("Unleash", "service"), ("in-house flag system", "service"), ("Ruby", "language"), ("Go", "language")],
     [("Unleash", "in-house flag system", "REPLACES")],
     "why did Unleash replace the home-grown flag system and which SDK coverage clinched it",
     "unleash replace in house community sdk node go java python ruby"),
    # --- 29 ---
    ("LaunchDarkly's percentage rollout hashing uses bucket-by key on tenant_id so an entire tenant always lands in the same bucket; random user-id bucketing used to split a tenant's screens.", "problem", "ai_coding", False,
     [("LaunchDarkly", "service"), ("bucket-by", "pattern"), ("tenant_id", "pattern")],
     [("bucket-by", "tenant_id", "APPLIES_TO")],
     "which bucket-by key did we switch to after random user-id bucketing split a tenant's experience",
     "launchdarkly bucket by tenant id rollout hash consistent tenant"),
    # --- 30 ---
    ("Feature-flag SDK initialisation is in the process bootstrap only; any code that needs a flag takes the client by constructor injection, never a module-level singleton.", "preference", "ai_coding", False,
     [("Feature-flag SDK", "library"), ("constructor injection", "pattern"), ("singleton", "pattern")],
     [],
     "how is the feature-flag client exposed to application code and why not a module-level singleton",
     "feature flag sdk bootstrap constructor injection singleton ban"),
    # --- 31 ---
    ("Switched webhooks from LaunchDarkly flag-change notifications to a poll-plus-ETag diff every 30 seconds; the webhooks' at-most-once delivery was dropping important change events.", "problem", "ai_coding", False,
     [("LaunchDarkly", "service"), ("webhook", "pattern"), ("ETag", "config")],
     [("ETag", "webhook", "REPLACES")],
     "which LaunchDarkly notification swap fixed the dropped flag-change events",
     "launchdarkly webhook drop poll etag diff at most once replace"),
    # --- 32 ---
    ("Canary flag 'search-rerank-v3' rolled out by country: NZ -> AU -> CA -> UK -> US in weekly steps; each step waited for the previous cohort's top-line metric to hold within 1% of control.", "milestone", "ai_coding", False,
     [("search-rerank-v3", "config"), ("NZ", "place"), ("US", "place"), ("Canary flag", "pattern")],
     [],
     "how did the search-rerank canary sequence its country-by-country rollout and what gate held it",
     "canary country rollout nz au ca uk us weekly metric gate"),
    # --- 33 ---
    ("LaunchDarkly improves on Rails flipper at our scale because its streaming SDK cuts the per-request Redis round-trip; flipper was fine under 50 rps but started adding milliseconds past 500.", "fact", "ai_coding", False,
     [("LaunchDarkly", "service"), ("Rails flipper", "library"), ("Redis", "database"), ("streaming SDK", "pattern")],
     [("LaunchDarkly", "Rails flipper", "IMPROVES_ON")],
     "why does LaunchDarkly outscale Rails flipper in our hot paths",
     "launchdarkly streaming redis round trip flipper scale rps cost"),
    # --- 34 ---
    ("flag_d.yaml is the local dev provider; it ships with every repo so engineers can work offline and the CI smoke job runs with a fixed snapshot for reproducibility.", "preference", "ai_coding", False,
     [("flag_d.yaml", "file"), ("local dev provider", "pattern"), ("CI", "tool")],
     [],
     "how do engineers work on flag-gated code offline and keep CI smoke runs reproducible",
     "flag local dev provider yaml offline ci snapshot reproducible"),
    # --- 35 ---
    ("Experimentation platform enforces a minimum sample size calculator before a flag can graduate; the CLI spits out the required N and stops product managers from calling a result early.", "architecture", "ai_coding", False,
     [("Experimentation platform", "service"), ("sample size calculator", "tool"), ("CLI", "tool")],
     [],
     "which tool gates experiment graduation on a computed minimum sample size",
     "experiment sample size calculator cli graduate gate product manager"),
    # --- 36 ---
    ("Flag deprecation flow needs three approvals: code owner, QA, and SRE; the SRE sign-off confirms no dashboards or runbooks still reference the retired flag key.", "preference", "ai_coding", False,
     [("Flag deprecation", "concept"), ("SRE", "organization"), ("QA", "organization")],
     [],
     "who must sign off on retiring a feature flag and what does the SRE review check for",
     "flag deprecation approval code owner qa sre dashboard runbook"),
    # --- 37 ---
    ("Boolean flag fanout on the orders-api module hit 38 flags; the team introduced a typed FlagSet wrapper so downstream callers pass a single value object instead of 38 booleans.", "problem", "ai_coding", False,
     [("orders-api", "service"), ("FlagSet", "pattern"), ("Boolean flag", "pattern")],
     [],
     "which abstraction did orders-api introduce to tame a 38-boolean flag fanout at the function boundary",
     "flag fanout typed flag set wrapper value object orders api"),
    # --- 38 ---
    ("Flag-controlled database migration uses expand-and-contract with a 'reads-from-new' flag; once 100% of reads pass without error for 48 hours the old column gets dropped.", "architecture", "ai_coding", False,
     [("expand-and-contract", "pattern"), ("reads-from-new", "config"), ("database migration", "concept")],
     [],
     "how does a flag coordinate an expand-and-contract database migration before dropping the old column",
     "expand contract migration reads from new flag 48 hour drop"),
    # --- 39 ---
    ("ConfigCat's native SDKs lacked a Rust binding we trusted, so the Rust services fetch the webhook-pushed JSON snapshot from S3 and evaluate locally with a tiny in-house resolver.", "architecture", "ai_coding", False,
     [("ConfigCat", "service"), ("Rust", "language"), ("S3", "service"), ("in-house resolver", "service")],
     [],
     "how do Rust services read ConfigCat flags without an official Rust SDK",
     "configcat rust no sdk s3 snapshot webhook local resolver"),
    # --- 40 ---
    ("Flagsmith identity overrides let us force a specific variant for a single customer during a support incident; the override auto-expires after 24 hours so nothing lingers.", "fact", "ai_coding", False,
     [("Flagsmith", "service"), ("identity override", "pattern"), ("support", "organization")],
     [],
     "which Flagsmith feature lets support force a variant for one customer with auto-expiry",
     "flagsmith identity override support incident expire 24 hour"),
    # --- 41 ---
    ("CI preview job emits a sticky flag bundle per PR that the preview URL reads; reviewers toggle variants from the PR comment via /flag slash-commands the bot handles.", "architecture", "ai_coding", False,
     [("CI", "tool"), ("preview URL", "pattern"), ("slash-command", "pattern"), ("bot", "service")],
     [],
     "how can PR reviewers flip flags on a preview deployment from the pull-request thread",
     "ci preview flag bundle pr slash command bot toggle variant"),
    # --- 42 ---
    ("When a flag key collides between two services because copy-paste, the registry rejects the second create with a 409; the mono-repo owns a single source-of-truth flags/registry.yaml.", "preference", "ai_coding", False,
     [("flags/registry.yaml", "file"), ("409", "config"), ("mono-repo", "concept")],
     [],
     "how does the flag registry keep two services from silently sharing the same flag key",
     "flag registry yaml collision 409 mono repo source truth reject"),
    # --- 43 ---
    ("OpenFeature hooks let us add an exposure-logging hook once instead of per call-site; the hook writes to the event bus and decorates spans with the resolved variant.", "architecture", "ai_coding", False,
     [("OpenFeature", "protocol"), ("hook", "pattern"), ("event bus", "service")],
     [],
     "which OpenFeature mechanism lets exposure logging live in one place rather than every call site",
     "openfeature hook exposure log span variant event bus central"),
    # --- 44 ---
    ("Unleash variant stickiness is set to sessionId on the marketing site and userId on the product; anonymous visitors must see a stable copy within a session even without a login.", "architecture", "ai_coding", False,
     [("Unleash", "service"), ("sessionId", "pattern"), ("userId", "pattern"), ("marketing site", "project")],
     [],
     "which Unleash stickiness axes apply to the marketing site versus the authenticated product",
     "unleash variant sticky session id user id marketing anonymous"),
    # --- 45 ---
    ("Flag default in code must match the pre-rollout behaviour so a rollback is always 'flip the flag off'; reviewers reject PRs whose default is the new behaviour.", "preference", "ai_coding", False,
     [("Flag default", "pattern"), ("rollback", "concept")],
     [],
     "which code-review rule makes every feature flag trivially rollback-safe",
     "flag default code match pre rollout behavior reviewer reject"),
    # --- 46 ---
    ("Ruby services wire the ldclient-rb SDK via Rails initializers; each environment uses a distinct SDK key stored in Rails credentials so a dev machine can never hit prod flags.", "architecture", "ai_coding", False,
     [("ldclient-rb", "library"), ("Rails", "framework"), ("Ruby", "language")],
     [],
     "how do Ruby services wire LaunchDarkly so dev machines can't resolve production flags",
     "ruby ldclient rb rails initializer sdk key credentials env"),
    # --- 47 ---
    ("A kill-switch flag stopped a runaway email-worker in 20 seconds during the 2026-02-09 incident; the post-mortem made kill-switches a mandatory control on any external side-effecting job.", "milestone", "ai_coding", False,
     [("kill-switch", "pattern"), ("email-worker", "service"), ("2026-02-09", "date"), ("post-mortem", "publication")],
     [],
     "which incident made kill-switch flags a mandatory control on side-effecting jobs",
     "kill switch email worker incident post mortem side effect mandatory"),
    # --- 48 ---
    ("Flag metadata carries an owner team and an auto-remind schedule; every flag older than its soft-expiry pings the owning Slack channel until it's closed or renewed.", "architecture", "ai_coding", False,
     [("owner team", "pattern"), ("soft-expiry", "pattern"), ("Slack", "service")],
     [],
     "how does the platform nag owners about flags that overstay their soft expiry",
     "flag metadata owner team soft expiry slack nag auto remind"),
    # --- 49. noise ---
    ("A stray squirrel on the roof of the data center tripped a motion sensor on Tuesday morning.", "fact", "noise", True, [], [], None, None),
    # --- 50 ---
    ("Strangler-fig migrations lean on feature flags for traffic shifting only; the domain-logic decisions live in code review and ADRs, not in the flag UI, so we don't confuse rollout with design.", "decision", "ai_coding", False,
     [("Strangler-fig", "pattern"), ("ADR", "publication"), ("flag UI", "pattern")],
     [],
     "how do strangler-fig migrations split flag responsibilities from design decisions",
     "strangler fig flag traffic shift adr design decision separation"),
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
