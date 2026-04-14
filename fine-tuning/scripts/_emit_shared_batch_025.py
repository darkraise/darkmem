"""One-off emitter for shared-base batch-025 — ai_coding domain (testing / CI-CD / code quality / release engineering slice).

Writes 50 rows to data/v2/shared/batch_025.tmp.jsonl with ids shared-01201..01250.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_025.tmp.jsonl"
ID_OFFSET = 1200

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Pact provider verification caught a breaking payload rename before the consumer team even pulled the new build.", "fact", "ai_coding", False,
     [("Pact", "tool"), ("provider verification", "method")],
     [],
     "which contract test technique surfaced the breaking schema rename pre-release",
     "consumer driven contract provider side verify schema change catch"),
    # --- 2 ---
    ("Stood up a Pact broker on 2026-02-15 so mobile and web consumers could publish contracts against the same billing provider.", "milestone", "ai_coding", False,
     [("Pact broker", "service"), ("2026-02-15", "date"), ("billing provider", "service")],
     [],
     "when did the contract sharing hub for mobile and web consumers come online",
     "broker deployment date shared contracts cross client provider"),
    # --- 3 ---
    ("Pact pending state let a new consumer publish failing contracts without tripping the provider build while the spec stabilised.", "fact", "ai_coding", False,
     [("Pact", "tool"), ("pending state", "pattern")],
     [],
     "what feature lets draft contracts exist without breaking the provider pipeline",
     "pending contract quarantine provider build stability draft"),
    # --- 4 ---
    ("fast-check properties surfaced a sort stability bug in the leaderboard that three targeted unit tests had stepped right past.", "problem", "ai_coding", False,
     [("fast-check", "library"), ("leaderboard", "concept")],
     [],
     "which property-based tool exposed the ranking stability defect",
     "property generator sort stability leaderboard bug reveal"),
    # --- 5 ---
    ("Haskell QuickCheck shrinkers pinned a Unicode edge case in the slug generator that the Python port had drifted past.", "problem", "ai_coding", False,
     [("QuickCheck", "library"), ("Haskell", "language"), ("slug generator", "concept")],
     [],
     "which property test shrinker localised the Unicode edge in the slug code",
     "quickcheck shrink Unicode slug edge case ported drift"),
    # --- 6 ---
    ("Stryker mutation score on the billing service crept from 62 to 84 after we deleted three assertion-free smoke tests.", "milestone", "ai_coding", False,
     [("Stryker", "tool"), ("billing service", "service")],
     [],
     "how did the mutation score climb twenty points on the billing module",
     "mutation score jump delete weak tests billing improvement"),
    # --- 7 ---
    ("mutmut surfaced equivalent mutants the team kept re-triaging; we added a skip annotation convention so the queue stopped repeating itself.", "problem", "ai_coding", False,
     [("mutmut", "tool")],
     [],
     "why did the same mutation survivors keep showing up in review",
     "equivalent mutant triage skip annotation convention queue"),
    # --- 8 ---
    ("PITest on the Java service runs nightly only; developer loops stay fast and the long mutation pass lands in the morning report.", "decision", "ai_coding", False,
     [("PITest", "tool"), ("Java", "language")],
     [],
     "how did the team keep mutation testing without slowing the inner loop",
     "nightly mutation schedule developer loop speed morning report"),
    # --- 9 ---
    ("libFuzzer corpus pruning with -merge=1 shrank the parser seed bank from 12 k to 3 k inputs without losing coverage frontiers.", "fact", "ai_coding", False,
     [("libFuzzer", "tool"), ("-merge=1", "command"), ("parser", "concept")],
     [],
     "which fuzz corpus operation trimmed redundant seeds without losing coverage",
     "fuzz corpus merge prune minimisation coverage preserve"),
    # --- 10. noise ---
    ("Anyway the new chair finally arrived and the lumbar support is a revelation.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("AFL++ caught a stack-based buffer overflow in the TLV reader that had survived three rounds of manual review.", "problem", "ai_coding", False,
     [("AFL++", "tool"), ("TLV reader", "concept")],
     [],
     "which coverage-guided fuzzer found the overflow the code review missed",
     "afl++ coverage fuzz tlv parser overflow manual miss"),
    # --- 12 ---
    ("go-fuzz corpus seeded from existing unit tests found an integer-overflow panic in the tariff calculator on its first weekend run.", "fact", "ai_coding", False,
     [("go-fuzz", "tool"), ("tariff calculator", "concept")],
     [],
     "how did the Go fuzzer find the pricing panic so quickly",
     "go fuzz seed unit test overflow panic tariff finding"),
    # --- 13 ---
    ("Golden files for SVG outputs kept drifting as Inkscape rounded coordinates differently per version; we pinned the renderer in the dev image.", "problem", "ai_coding", False,
     [("Golden files", "pattern"), ("SVG", "technology"), ("Inkscape", "tool")],
     [],
     "why did graphic golden fixtures thrash between contributor machines",
     "golden drift renderer version coordinate rounding pin image"),
    # --- 14 ---
    ("Policy: golden-file updates require a reviewer approval label; a drive-by diff regenerate is no longer enough to land the patch.", "decision", "ai_coding", False,
     [("golden-file", "pattern")],
     [],
     "what change keeps fixture regenerations from slipping in without oversight",
     "golden update review label gate regenerate policy enforce"),
    # --- 15 ---
    ("jest-image-snapshot diff tolerance went from 0.1% to 0.02% on 2026-01-30; CI caught a text anti-aliasing regression the same week.", "milestone", "ai_coding", False,
     [("jest-image-snapshot", "library"), ("2026-01-30", "date")],
     [],
     "when did the stricter pixel tolerance start catching real rendering regressions",
     "image snapshot tolerance tighten antialias regression catch date"),
    # --- 16 ---
    ("Insta review workflow (cargo insta review) makes snapshot updates feel like a staged diff instead of a blind regenerate.", "preference", "ai_coding", False,
     [("cargo insta review", "command"), ("Insta", "library")],
     [],
     "which Rust snapshot workflow earns the team's trust over blind regenerates",
     "insta review staged diff snapshot update workflow pick"),
    # --- 17 ---
    ("Codecov patch coverage gate at 80% on new lines caught an unchecked branch in the refund path during review.", "decision", "ai_coding", False,
     [("Codecov", "service"), ("refund path", "concept")],
     [],
     "what coverage rule trapped the uncovered refund branch in review",
     "codecov patch coverage gate new line threshold catch"),
    # --- 18 ---
    ("Coveralls total coverage ratchet-only policy kept the percentage from sliding quarter after quarter.", "decision", "ai_coding", False,
     [("Coveralls", "service")],
     [],
     "which policy stopped aggregate coverage from drifting downward over quarters",
     "coverage ratchet only decrease prevent quarterly drift"),
    # --- 19 ---
    ("Jacoco line coverage threshold at 70% plus branch at 60% reflected our reality better than a single blanket number.", "decision", "ai_coding", False,
     [("Jacoco", "tool")],
     [],
     "why did the Java coverage gate use two axes instead of one combined number",
     "jacoco split line branch threshold realism gate"),
    # --- 20 ---
    ("Flake quarantine label auto-demotes a test to the nightly-only lane after three flaps in seven days; the green rate stabilised quickly.", "decision", "ai_coding", False,
     [("Flake quarantine", "pattern")],
     [],
     "what automation moves repeatedly-flapping tests out of the blocking run",
     "flake quarantine auto demote nightly lane green rate stable"),
    # --- 21 ---
    ("Flake dashboard groups tests by shared failure fingerprint; one root cause in the seeded RNG explained half of last month's flaps.", "fact", "ai_coding", False,
     [("Flake dashboard", "tool"), ("seeded RNG", "concept")],
     [],
     "how did the flake tracker surface a single shared root cause across many tests",
     "flake dashboard fingerprint cluster shared root cause rng"),
    # --- 22 ---
    ("Jenkins matrix axes for OS and JDK explode multiplicatively; we dropped the Windows+JDK8 cell because nobody shipped to that combo.", "decision", "ai_coding", False,
     [("Jenkins matrix", "pattern"), ("Windows", "platform"), ("JDK8", "platform")],
     [],
     "which matrix cell did the team retire to keep the grid manageable",
     "jenkins matrix prune legacy combination cell drop rationale"),
    # --- 23 ---
    ("GitHub Actions matrix sharding by test file hash cut wall time from 18 min to 6 min on the integration suite.", "milestone", "ai_coding", False,
     [("GitHub Actions", "platform"), ("matrix sharding", "pattern")],
     [],
     "which sharding strategy cut the integration suite to a third of the wall time",
     "gha matrix shard hash bucket integration wall time win"),
    # --- 24 ---
    ("CircleCI workflow fan-out split frontend and contract tests into parallel jobs gated on a shared build artifact.", "architecture", "ai_coding", False,
     [("CircleCI", "platform"), ("fan-out", "pattern"), ("contract tests", "method")],
     [],
     "how did the CircleCI pipeline split frontend and contract stages",
     "circleci workflow fanout parallel job shared artifact gate"),
    # --- 25 ---
    ("BuildKit cache invalidation surprises came from COPY ordering; we put package manifests before source to lock the install layer.", "problem", "ai_coding", False,
     [("BuildKit", "tool"), ("COPY", "command")],
     [],
     "why did the Docker cache keep busting on unrelated source edits",
     "buildkit cache invalidation copy order manifest source split"),
    # --- 26 ---
    ("Remote Gradle cache behind an S3 backend turned a cold cross-machine build from 9 min to 2 min.", "milestone", "ai_coding", False,
     [("Gradle", "tool"), ("S3", "service")],
     [],
     "which cache backend gave the cross-machine Gradle build the big speedup",
     "gradle remote cache object store build speed cold hit"),
    # --- 27 ---
    ("Turbo remote cache auth uses a short-lived token per CI job; stale team-wide tokens no longer linger in forked PR runners.", "fact", "ai_coding", False,
     [("Turbo", "tool")],
     [],
     "how did the monorepo cache avoid leaking long-lived auth to forks",
     "turbo remote cache short lived token fork runner safety"),
    # --- 28 ---
    ("Nx Cloud distributed task execution pulled CI time below the pre-merge SLA; the decision was to keep it on for protected branches only.", "decision", "ai_coding", False,
     [("Nx Cloud", "service")],
     [],
     "where did distributed task execution earn its keep in the pipeline",
     "nx cloud dte protected branch sla enable scope"),
    # --- 29 ---
    ("Release train: a cut every other Thursday, feature freeze Monday prior, hotfix branch permitted only for severity-one issues.", "decision", "ai_coding", False,
     [("Release train", "pattern"), ("hotfix branch", "concept")],
     [],
     "what is the cadence and freeze discipline of the release process",
     "release train cadence freeze hotfix severity rule"),
    # --- 30 ---
    ("Flagger canary analysis keyed on error-rate and p99 latency rollbacks one bad deploy inside four minutes without a human in the loop.", "fact", "ai_coding", False,
     [("Flagger", "tool"), ("canary analysis", "method")],
     [],
     "which progressive delivery tool reverted a bad push without human intervention",
     "automated revert SLI guard progressive delivery hands off"),
    # --- 31 ---
    ("Argo Rollouts analysis template pulls from Prometheus; SLO burn rate beats raw error count for canary decisions.", "architecture", "ai_coding", False,
     [("Argo Rollouts", "tool"), ("Prometheus", "service"), ("SLO", "concept")],
     [],
     "how do canary decisions in Argo Rollouts consult the observability stack",
     "progressive delivery metric source error budget signal canary gate"),
    # --- 32 ---
    ("Chose blue/green for the stateful payments service; a half-baked canary on a sharded DB caused more rollback pain than it avoided.", "decision", "ai_coding", False,
     [("blue/green", "pattern"), ("payments service", "service"), ("canary", "pattern")],
     [("blue/green", "canary", "PREFERS")],
     "why did the payments team pick blue/green deployment over canary",
     "stateful deploy strategy blue green canary rollback sharded db"),
    # --- 33 ---
    ("semantic-release automates version bumps and tag creation from conventional commits; the release notes write themselves now.", "decision", "ai_coding", False,
     [("semantic-release", "tool"), ("conventional commits", "pattern")],
     [],
     "which tool turns commit conventions into version tags automatically",
     "semantic release version bump tag changelog automation"),
    # --- 34 ---
    ("Renovate shared preset auto-merges patch and minor dev dependencies on green CI; majors still need a reviewer on the hook.", "decision", "ai_coding", False,
     [("Renovate", "tool")],
     [],
     "what dependency update rule lets patches land alone but flags majors",
     "renovate preset auto merge patch minor major review split"),
    # --- 35 ---
    ("Dependabot grouped updates bundle ecosystem peers (eslint plus plugins) so the PR count dropped from 40 a week to 9.", "milestone", "ai_coding", False,
     [("Dependabot", "tool"), ("eslint", "tool")],
     [],
     "how did grouping options cut the volume of dependency update PRs",
     "dependabot group peer ecosystem pr volume reduction"),
    # --- 36 ---
    ("Required checks list is now codified in a CODEOWNERS-adjacent yaml instead of being clicked into the repo settings by hand.", "architecture", "ai_coding", False,
     [("CODEOWNERS", "file")],
     [],
     "how is the required-check list tracked in version control now",
     "required check config yaml repo setting drift code review"),
    # --- 37 ---
    ("Bors queue serialised merges on the main branch and finally killed the green-then-red-on-merge race we kept hitting.", "decision", "ai_coding", False,
     [("Bors", "tool")],
     [],
     "what tool stopped merge-after-green races on the main branch",
     "bors merge queue serialise race condition main branch"),
    # --- 38 ---
    ("Mergify queue with a batch size of three let us land stacked PRs without re-running CI on each one from scratch.", "decision", "ai_coding", False,
     [("Mergify", "tool")],
     [],
     "which merge queue batches stacked PRs to reuse CI runs",
     "mergify queue batch size stacked pr ci reuse"),
    # --- 39 ---
    ("GitHub merge queue behaved well once we dropped the redundant branch-protection status-check duplication that broke its re-run logic.", "problem", "ai_coding", False,
     [("GitHub merge queue", "tool"), ("branch-protection", "pattern")],
     [],
     "why did the native merge queue misbehave until the status-check list was trimmed",
     "github merge queue branch protection duplicate status rerun bug"),
    # --- 40 ---
    ("commitlint in CI rejects non-conventional subjects; the fast-feedback hook on lefthook warns locally so the block is rare.", "architecture", "ai_coding", False,
     [("commitlint", "tool"), ("lefthook", "tool")],
     [],
     "how is commit message style enforced both locally and in CI",
     "commitlint local warn ci reject conventional style enforcement"),
    # --- 41 ---
    ("Signed commits via sigstore gitsign replaced our GPG-key ritual; no more lost keys blocking releases.", "decision", "ai_coding", False,
     [("sigstore", "tool"), ("gitsign", "tool"), ("GPG", "technology")],
     [("gitsign", "GPG", "REPLACES")],
     "which commit-signing approach retired the GPG key ceremony",
     "gitsign sigstore gpg replace signed commit release unblock"),
    # --- 42 ---
    ("Conventional-commits enforcement was loosened to warn-only on docs-only PRs; the friction there was not earning its keep.", "decision", "ai_coding", False,
     [("Conventional-commits", "pattern")],
     [],
     "where did the team dial back commit-style enforcement and why",
     "conventional commits docs only warn loosen friction tradeoff"),
    # --- 43 ---
    ("git-cliff renders the changelog from conventional commits grouped by scope; release notes land with zero manual editing.", "fact", "ai_coding", False,
     [("git-cliff", "tool"), ("conventional commits", "pattern")],
     [],
     "which generator builds changelog sections from scoped commits automatically",
     "git cliff changelog scope group conventional commit release notes"),
    # --- 44 ---
    ("Switched changelog tooling to Changesets for the packages repo; per-package versioning plays nicer with the publish pipeline.", "decision", "ai_coding", False,
     [("Changesets", "tool")],
     [],
     "why did the packages repo move to a different changelog tool",
     "changesets per package version publish pipeline fit"),
    # --- 45 ---
    ("SLSA level 3 provenance is generated per release artifact; downstream consumers can verify with a single cosign command.", "architecture", "ai_coding", False,
     [("SLSA", "framework"), ("cosign", "tool")],
     [],
     "how can consumers verify our release artifacts end-to-end",
     "slsa level 3 provenance cosign verify consumer artifact"),
    # --- 46 ---
    ("Attested artifact provenance through the GitHub OIDC token cut our signing key management to zero; keys never touch a runner.", "fact", "ai_coding", False,
     [("GitHub OIDC", "protocol")],
     [],
     "which signing mechanism removed long-lived keys from the runners",
     "oidc attestation signing keyless runner provenance github"),
    # --- 47 ---
    ("Semgrep autofix hooked into required checks; missing null-guards get a suggested commit instead of a blocking failure.", "decision", "ai_coding", False,
     [("Semgrep", "tool")],
     [],
     "which static analysis change offers fixes instead of just failing the build",
     "semgrep autofix required check suggestion null guard workflow"),
    # --- 48 ---
    ("SonarQube quality gate blocked the PR over duplicated-code ratio; extracting the currency helper dropped the figure under threshold.", "problem", "ai_coding", False,
     [("SonarQube", "tool"), ("currency helper", "concept")],
     [],
     "which quality-gate metric failed the PR until a helper got extracted",
     "sonarqube duplication ratio quality gate extract helper unblock"),
    # --- 49 ---
    ("Release smoke suite runs post-deploy against the canary namespace and ships status to the release channel webhook.", "architecture", "ai_coding", False,
     [("canary namespace", "infrastructure"), ("webhook", "technology")],
     [],
     "how does the team get post-deploy smoke test status back to chat",
     "post deploy smoke canary namespace status webhook channel"),
    # --- 50 ---
    ("Adopted reproducible builds for the CLI release on 2026-03-11; byte-identical tarballs across runners unblocked third-party packaging.", "milestone", "ai_coding", False,
     [("CLI", "concept"), ("2026-03-11", "date")],
     [],
     "when did the CLI releases become byte-identical across runners",
     "reproducible build bit identical tarball runner date release"),
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
