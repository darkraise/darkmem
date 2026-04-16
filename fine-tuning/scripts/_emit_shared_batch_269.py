"""One-off emitter for shared-base batch-269 — technical domain (static analysis, linting, and code quality tooling).

Writes 50 rows to data/v2/shared/batch_269.tmp.jsonl with ids shared-13401..13450.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_269.tmp.jsonl"
ID_OFFSET = 13400

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Adopted semgrep as the primary SAST layer after the Snyk Code trial; the custom rule DSL let platform security ship an internal taint pack that CodeQL couldn't express without a compiled pack.", "decision", "technical", False,
     [("semgrep", "tool"), ("Snyk Code", "tool"), ("CodeQL", "tool"), ("SAST", "concept"), ("taint pack", "pattern")],
     [("semgrep", "Snyk Code", "REPLACES"), ("semgrep", "CodeQL", "PREFERS")],
     "which SAST engine won the internal bake-off and what extensibility feature sealed the choice",
     "semgrep snyk codeql sast taint rule dsl custom pack platform"),
    # --- 2 fact ---
    ("CodeQL runs as a scheduled GitHub Actions workflow on the default branch weekly; pull-request scans use the same database but scope to changed files so developer feedback stays under four minutes.", "fact", "technical", False,
     [("CodeQL", "tool"), ("GitHub Actions", "service"), ("default branch", "concept"), ("pull-request", "concept")],
     [("CodeQL", "GitHub Actions", "USES")],
     "how is CodeQL scheduled across branch and pull-request contexts to keep developer feedback fast",
     "codeql github actions workflow schedule weekly pull request scope"),
    # --- 3 milestone ---
    ("SonarQube 10.4 rollout finished on the Java monorepo; the migration from SonarQube 9.9 LTS pulled in the new clean-code taxonomy and retired the old technical-debt rating on every dashboard.", "milestone", "technical", False,
     [("SonarQube", "tool"), ("10.4", "config"), ("9.9 LTS", "config"), ("Java monorepo", "project"), ("clean-code taxonomy", "concept")],
     [("SonarQube", "Java monorepo", "APPLIES_TO")],
     "which SonarQube upgrade landed on the Java monorepo and what rating did it retire",
     "sonarqube 10 4 9 9 lts java monorepo clean code taxonomy debt"),
    # --- 4 decision ---
    ("Dropped Veracode for application scanning and standardised on Snyk Code plus semgrep; Veracode's daily queue made merge blockers unpredictable and doubled the median PR-to-merge time.", "decision", "technical", False,
     [("Veracode", "tool"), ("Snyk Code", "tool"), ("semgrep", "tool"), ("PR", "concept")],
     [("Snyk Code", "Veracode", "REPLACES"), ("semgrep", "Veracode", "REPLACES")],
     "which SAST vendor got replaced after queue latency doubled the merge time",
     "veracode snyk semgrep sast queue latency merge block pr time"),
    # --- 5 fact ---
    ("SonarCloud ingests the coverage XML from jacoco and surfaces the quality-gate failure inline on the GitHub pull-request status check; the gate fails on any new-code coverage below eighty percent.", "fact", "technical", False,
     [("SonarCloud", "service"), ("jacoco", "tool"), ("GitHub", "service"), ("quality-gate", "concept")],
     [("SonarCloud", "GitHub", "USES"), ("SonarCloud", "jacoco", "USES")],
     "how does SonarCloud surface a coverage-based quality gate on GitHub pull requests",
     "sonarcloud jacoco github quality gate coverage xml new code eighty"),
    # --- 6 reference ---
    ("PMD rule catalog for the legacy Java service is pinned in tools/pmd/ruleset.xml; the file lists category/best-practices, category/design, and a suppressed category/errorprone.AvoidCatchingGenericException.", "reference", "technical", False,
     [("PMD", "tool"), ("tools/pmd/ruleset.xml", "file"), ("Java", "language"), ("AvoidCatchingGenericException", "concept")],
     [("PMD", "Java", "APPLIES_TO")],
     "where does the legacy Java service keep its PMD ruleset and which rule is suppressed",
     "pmd ruleset java legacy xml best practice design errorprone suppress"),
    # --- 7 architecture ---
    ("SpotBugs runs under the gradle spotbugsMain task with the fb-contrib plugin and findsecbugs; the three finding streams merge into a single SARIF artefact uploaded to GitHub code scanning.", "architecture", "technical", False,
     [("SpotBugs", "tool"), ("fb-contrib", "library"), ("findsecbugs", "library"), ("SARIF", "pattern"), ("gradle", "tool")],
     [("SpotBugs", "gradle", "USES"), ("SpotBugs", "fb-contrib", "USES"), ("SpotBugs", "findsecbugs", "USES")],
     "how is SpotBugs wired with gradle and which plugins feed its SARIF output",
     "spotbugs fb contrib findsecbugs gradle sarif github code scan"),
    # --- 8 decision ---
    ("Error Prone is now the compile-time nag layer on every Java module; the FindBugs ant target got retired because javac-integrated checks gave the same signal without a separate build step.", "decision", "technical", False,
     [("Error Prone", "tool"), ("FindBugs", "tool"), ("javac", "tool"), ("Java", "language")],
     [("Error Prone", "FindBugs", "REPLACES"), ("Error Prone", "javac", "USES")],
     "which javac-integrated checker replaced the FindBugs ant target across Java modules",
     "error prone findbugs javac ant java compile time nag retire"),
    # --- 9 architecture ---
    ("Meta's Infer runs in the nightly pipeline over the Objective-C and Java source tree; the incremental mode caches the summaries per translation unit so re-runs on a topic branch skip unchanged files.", "architecture", "technical", False,
     [("Infer", "tool"), ("Objective-C", "language"), ("Java", "language"), ("translation unit", "concept")],
     [("Infer", "Objective-C", "APPLIES_TO"), ("Infer", "Java", "APPLIES_TO")],
     "how does Infer stay fast in the nightly pipeline across branches without full re-analysis",
     "infer objective c java nightly incremental summary translation unit"),
    # --- 10 noise ---
    ("The office plant on the fourth-floor window sill lost its name tag and three people now claim to have picked it.", "fact", "noise", True, [], [], None, None),
    # --- 11 decision ---
    ("CBMC was chosen over Frama-C for the firmware bounded-model-checking gate; the SMT backend integration with yices matched the existing proof workflow and Frama-C's WP plugin needed a separate Coq install.", "decision", "technical", False,
     [("CBMC", "tool"), ("Frama-C", "tool"), ("yices", "tool"), ("WP plugin", "library"), ("Coq", "tool")],
     [("CBMC", "Frama-C", "PREFERS"), ("CBMC", "yices", "USES")],
     "which bounded-model-checker won the firmware gate evaluation and what integration drove the choice",
     "cbmc frama c yices smt bounded model check firmware wp coq"),
    # --- 12 milestone ---
    ("Coverity Scan cleared the legacy driver codebase after the 2026-Q1 sweep; the final count landed at zero high-impact defects across 412 kLOC of C, down from 87 a year earlier.", "milestone", "technical", False,
     [("Coverity Scan", "service"), ("2026-Q1", "date"), ("C", "language"), ("legacy driver", "project")],
     [("Coverity Scan", "legacy driver", "APPLIES_TO")],
     "which quarter did the legacy driver Coverity sweep close out and what defect count did it hit",
     "coverity scan legacy driver c kloc high impact defect q1 2026"),
    # --- 13 architecture ---
    ("Facebook Pyre runs as the Python type checker for the services monorepo; it uses a Watchman-backed daemon so incremental recheck on file save stays sub-second on ten-million-line trees.", "architecture", "technical", False,
     [("Facebook Pyre", "tool"), ("Python", "language"), ("Watchman", "tool"), ("daemon", "pattern")],
     [("Facebook Pyre", "Python", "APPLIES_TO"), ("Facebook Pyre", "Watchman", "USES")],
     "how does Facebook Pyre keep incremental type checking fast on very large Python trees",
     "pyre facebook python watchman daemon incremental type check save"),
    # --- 14 decision ---
    ("Pyright strict replaces mypy daemon on the new Python service skeleton; the stricter inference catches Optional unwraps that mypy's relaxed defaults let slip and the editor latency matches the daemon.", "decision", "technical", False,
     [("Pyright strict", "tool"), ("mypy daemon", "tool"), ("Optional", "concept"), ("Python", "language")],
     [("Pyright strict", "mypy daemon", "REPLACES"), ("Pyright strict", "Python", "APPLIES_TO")],
     "which Python type checker replaced mypy daemon on new services and which inference gap drove the swap",
     "pyright strict mypy daemon python optional unwrap editor latency"),
    # --- 15 reference ---
    ("Ruff ruleset for the data-platform lives in pyproject.toml under [tool.ruff.lint.select]; the active families are E, W, F, I, N, B, A, C4, SIM, UP, and PL with PLR0913 raised to sixteen arguments.", "reference", "technical", False,
     [("Ruff", "tool"), ("pyproject.toml", "file"), ("PLR0913", "concept"), ("data-platform", "project")],
     [("Ruff", "data-platform", "APPLIES_TO")],
     "which Ruff rule families run on the data platform and what threshold override applies",
     "ruff pyproject ruleset e w f i n b a c4 sim up pl plr0913"),
    # --- 16 decision ---
    ("ESLint 9 flat config is the standard for every TypeScript repo; the old .eslintrc hierarchical config made shared presets brittle and the flat config maps cleanly onto the workspace graph.", "decision", "technical", False,
     [("ESLint 9", "tool"), ("flat config", "pattern"), (".eslintrc", "file"), ("TypeScript", "language")],
     [("flat config", ".eslintrc", "REPLACES"), ("ESLint 9", "TypeScript", "APPLIES_TO")],
     "which ESLint configuration model replaced hierarchical rc files on TypeScript repos and why",
     "eslint 9 flat config eslintrc typescript workspace preset hierarchical"),
    # --- 17 decision ---
    ("Biome now handles format and lint on the frontend monorepo, retiring the prettier plus ESLint combo; a single pass on the pre-commit hook cut wall-clock time from 14 seconds to under two.", "decision", "technical", False,
     [("Biome", "tool"), ("prettier", "tool"), ("ESLint", "tool"), ("pre-commit hook", "pattern"), ("frontend monorepo", "project")],
     [("Biome", "prettier", "REPLACES"), ("Biome", "ESLint", "REPLACES")],
     "which combined lint-and-format tool replaced prettier plus ESLint on the frontend monorepo",
     "biome prettier eslint frontend monorepo pre commit format lint"),
    # --- 18 fact ---
    ("Oxlint is the fastest linter we've measured on the vendor tree; a full pass on 430 kLOC of JavaScript completes in 1.1 seconds on the M2 Pro where ESLint with the same subset takes 38 seconds.", "fact", "technical", False,
     [("Oxlint", "tool"), ("ESLint", "tool"), ("JavaScript", "language"), ("M2 Pro", "platform")],
     [],
     "which linter ran fastest on the vendor JavaScript tree and what was the ESLint comparison",
     "oxlint eslint javascript vendor kloc m2 pro fast linter bench"),
    # --- 19 reference ---
    ("rust-clippy runs as a required check on the CI matrix with -D warnings on stable and nightly; the pedantic group is opt-in per crate so experimental Rust crates can trial rules without blocking merges.", "reference", "technical", False,
     [("rust-clippy", "tool"), ("Rust", "language"), ("pedantic", "concept"), ("CI matrix", "pattern")],
     [("rust-clippy", "Rust", "APPLIES_TO")],
     "how is rust-clippy gated in CI and which rule group stays opt-in per crate",
     "rust clippy ci matrix stable nightly pedantic opt in crate warnings"),
    # --- 20 decision ---
    ("Go vet runs in the same test binary, but staticcheck and golangci-lint own the sharper checks; the config pins staticcheck to 2025.1.1 because a later dev release changed SA5011 semantics mid-cycle.", "decision", "technical", False,
     [("Go vet", "tool"), ("staticcheck", "tool"), ("golangci-lint", "tool"), ("SA5011", "concept"), ("2025.1.1", "config")],
     [("staticcheck", "Go vet", "IMPROVES_ON"), ("golangci-lint", "staticcheck", "USES")],
     "which Go linters share responsibility and why did staticcheck get pinned to a specific release",
     "go vet staticcheck golangci lint sa5011 2025 1 1 pin go language"),
    # --- 21 reference ---
    ("shellcheck is pinned at 0.10.0 in the shared tools image and invoked via .githooks/pre-push; the shared config suppresses SC2086 on the single ops wrapper that intentionally word-splits a variable.", "reference", "technical", False,
     [("shellcheck", "tool"), ("0.10.0", "config"), (".githooks/pre-push", "file"), ("SC2086", "concept")],
     [],
     "which shellcheck version runs in pre-push hooks and which rule is suppressed on the ops wrapper",
     "shellcheck 0 10 0 pre push githooks sc2086 word split wrapper"),
    # --- 22 architecture ---
    ("hadolint runs in the Dockerfile lint stage of every image pipeline; a repo-wide .hadolint.yaml ignores DL3008 on base images that intentionally pin apt packages via an upstream digest pin.", "architecture", "technical", False,
     [("hadolint", "tool"), ("Dockerfile", "file"), (".hadolint.yaml", "file"), ("DL3008", "concept")],
     [("hadolint", "Dockerfile", "APPLIES_TO")],
     "how does the Dockerfile pipeline use hadolint and which rule is ignored for digest-pinned bases",
     "hadolint dockerfile hadolint yaml dl3008 apt pin digest image"),
    # --- 23 fact ---
    ("yamllint is wired into pre-commit for every GitOps repo; the config allows document-start markers to stay off so the Flux Kustomization files match the Flux generator output byte-for-byte.", "fact", "technical", False,
     [("yamllint", "tool"), ("pre-commit", "tool"), ("Flux", "tool"), ("Kustomization", "concept"), ("GitOps", "concept")],
     [("yamllint", "pre-commit", "USES"), ("yamllint", "Flux", "APPLIES_TO")],
     "which GitOps repos run yamllint and which marker rule stays relaxed to match Flux output",
     "yamllint pre commit flux kustomization gitops document start marker"),
    # --- 24 preference ---
    ("The team prefers dotenv-linter over write-env-files-manually; every service ships a .env.example that dotenv-linter validates in CI and the check blocks drift between example and actual runtime keys.", "preference", "technical", False,
     [("dotenv-linter", "tool"), (".env.example", "file"), ("CI", "concept")],
     [("dotenv-linter", ".env.example", "APPLIES_TO")],
     "which dotenv tool does the team prefer and what drift does the CI check prevent",
     "dotenv linter env example ci drift runtime key validate service"),
    # --- 25 preference ---
    ("ansible-lint runs on the platform playbook collection with the production profile; role-specific skips live in .ansible-lint-ignore and the nightly pipeline fails the build on any new no_changed_when warning.", "preference", "technical", False,
     [("ansible-lint", "tool"), ("playbook", "concept"), (".ansible-lint-ignore", "file"), ("no_changed_when", "concept")],
     [("ansible-lint", "playbook", "APPLIES_TO")],
     "how is ansible-lint wired on the platform playbooks and where do role-specific skips live",
     "ansible lint production playbook ignore no changed when nightly skip"),
    # --- 26 decision ---
    ("tflint replaced the home-grown terraform fmt wrapper after the AWS provider ruleset caught three deprecated instance types during the eu-central migration review; the wrapper had none of those checks.", "decision", "technical", False,
     [("tflint", "tool"), ("terraform fmt", "tool"), ("AWS", "service"), ("eu-central", "concept")],
     [("tflint", "terraform fmt", "REPLACES"), ("tflint", "AWS", "APPLIES_TO")],
     "which Terraform linter replaced the home-grown fmt wrapper and what provider check clinched it",
     "tflint terraform fmt aws provider eu central deprecated instance"),
    # --- 27 architecture ---
    ("checkov scans the Terraform plan JSON rather than source HCL so dynamic modules resolve before policy evaluation; findings flow to the GitHub checks tab via the SARIF uploader action.", "architecture", "technical", False,
     [("checkov", "tool"), ("Terraform", "tool"), ("SARIF", "pattern"), ("GitHub", "service"), ("HCL", "language")],
     [("checkov", "Terraform", "APPLIES_TO"), ("checkov", "GitHub", "USES")],
     "why does checkov scan the Terraform plan JSON instead of raw HCL source",
     "checkov terraform plan json hcl sarif github dynamic module policy"),
    # --- 28 decision ---
    ("trivy is the default container image scanner across all services; grype stays in the nightly comparison job because its Syft SBOM pairing still finds the occasional PHP dependency trivy misses.", "decision", "technical", False,
     [("trivy", "tool"), ("grype", "tool"), ("Syft", "tool"), ("SBOM", "concept"), ("PHP", "language")],
     [("trivy", "grype", "PREFERS"), ("grype", "Syft", "USES")],
     "which container scanner is the default and why does grype still run in the nightly job",
     "trivy grype syft sbom container image scan php nightly default"),
    # --- 29 milestone ---
    ("kubesec runs at admission via a ValidatingWebhookConfiguration that rejects any Pod manifest scoring below seven; the webhook is deployed as two replicas in the security namespace with a mutual-TLS bundle.", "milestone", "technical", False,
     [("kubesec", "tool"), ("ValidatingWebhookConfiguration", "api"), ("Pod", "concept"), ("security namespace", "concept")],
     [("kubesec", "Pod", "APPLIES_TO")],
     "how is kubesec enforced at admission time and what Pod score threshold blocks a deploy",
     "kubesec admission validating webhook pod score security namespace"),
    # --- 30 decision ---
    ("Falco stays as the primary runtime-detection engine on the production clusters; Tracee's eBPF approach looked promising but the rule language gap against the Falco rules we already maintain was too big to bridge this quarter.", "decision", "technical", False,
     [("Falco", "tool"), ("Tracee", "tool"), ("eBPF", "technology"), ("production clusters", "concept")],
     [("Falco", "Tracee", "PREFERS"), ("Falco", "eBPF", "USES")],
     "which eBPF runtime detector stayed primary and what blocked the Tracee migration this quarter",
     "falco tracee ebpf runtime detect rule production cluster quarter"),
    # --- 31 problem ---
    ("eBPF-based runtime detection started dropping events on kernel 6.8 once the BPF ring buffer size hit default limits during deploy storms; bumping the per-program ringbuf to 16 MiB cleared the gap.", "problem", "technical", False,
     [("eBPF", "technology"), ("kernel 6.8", "config"), ("BPF ring buffer", "concept"), ("16 MiB", "config")],
     [],
     "which kernel version exposed the eBPF ringbuf drop during deploy storms and what config fixed it",
     "ebpf kernel 6 8 ring buffer drop deploy storm 16 mib ringbuf"),
    # --- 32 architecture ---
    ("Snyk IaC is the policy gate for the landing-zone Terraform; custom rules in Rego extend the built-in bundle and the plan-JSON feed avoids re-evaluating unchanged modules between runs.", "architecture", "technical", False,
     [("Snyk IaC", "tool"), ("Terraform", "tool"), ("Rego", "language"), ("landing-zone", "project")],
     [("Snyk IaC", "Terraform", "APPLIES_TO"), ("Snyk IaC", "Rego", "USES")],
     "how does Snyk IaC gate the landing-zone Terraform and which policy language extends the bundle",
     "snyk iac terraform landing zone rego policy plan json module"),
    # --- 33 milestone ---
    ("OpenRewrite recipe run finished the JUnit 4 to JUnit 5 migration across 217 repos on 2026-03-12; Moderne's hosted mass-refactor applied 8,914 commits and the CI bill came in at 610 dollars for the batch.", "milestone", "technical", False,
     [("OpenRewrite", "tool"), ("Moderne", "service"), ("JUnit 4", "framework"), ("JUnit 5", "framework"), ("2026-03-12", "date")],
     [("OpenRewrite", "JUnit 4", "REPLACES"), ("OpenRewrite", "Moderne", "USES")],
     "which mass refactor finished on 2026-03-12 and how many repos did the OpenRewrite recipe touch",
     "openrewrite moderne junit 4 5 migration recipe mass refactor repos"),
    # --- 34 architecture ---
    ("Spoon powers the internal Java AST tooling for the custom deprecation sweeper; the processor visits CtMethod nodes and rewrites call sites in parallel with a fork-join pool sized to core count.", "architecture", "technical", False,
     [("Spoon", "tool"), ("Java", "language"), ("CtMethod", "concept"), ("fork-join pool", "pattern")],
     [("Spoon", "Java", "APPLIES_TO")],
     "how does the deprecation sweeper use Spoon to visit Java AST nodes in parallel",
     "spoon java ast ctmethod fork join pool deprecation sweeper rewrite"),
    # --- 35 decision ---
    ("jscodeshift remains the go-to codemod runner for the React monorepo; even with ast-grep on the radar, the Babel-compatible transformer format the team already maintains made the switch not worth the tooling churn.", "decision", "technical", False,
     [("jscodeshift", "tool"), ("React monorepo", "project"), ("Babel", "tool"), ("ast-grep", "tool")],
     [("jscodeshift", "ast-grep", "PREFERS"), ("jscodeshift", "Babel", "USES")],
     "which codemod runner stays on the React monorepo and why wasn't ast-grep adopted yet",
     "jscodeshift react monorepo babel ast grep codemod transformer"),
    # --- 36 fact ---
    ("semgrep-rules taint config for the services repo declares flask.request.args as a source and subprocess.run as a sink; a pass-through sanitiser is registered so html.escape clears taint on string arguments.", "fact", "technical", False,
     [("semgrep", "tool"), ("flask", "framework"), ("subprocess.run", "api"), ("html.escape", "api")],
     [("semgrep", "flask", "APPLIES_TO")],
     "how does the semgrep taint config declare source, sink, and sanitiser for the services repo",
     "semgrep flask request args subprocess run html escape taint source"),
    # --- 37 preference ---
    ("The security team prefers custom CodeQL queries over semgrep rules for cross-function data-flow; the database query model catches indirect flows that single-file semgrep patterns miss on the ingestion service.", "preference", "technical", False,
     [("CodeQL", "tool"), ("semgrep", "tool"), ("ingestion service", "project"), ("data-flow", "concept")],
     [("CodeQL", "semgrep", "PREFERS")],
     "which engine does the security team prefer for cross-function flows and why",
     "codeql semgrep data flow cross function ingestion service indirect"),
    # --- 38 problem ---
    ("SonarQube false-positive wave on the Java monorepo traced to the java:S2259 NullPointerException rule firing on Optional.get; a sonar-project.properties suppression by path pattern cleared the queue without disabling the rule elsewhere.", "problem", "technical", False,
     [("SonarQube", "tool"), ("java:S2259", "concept"), ("Optional.get", "api"), ("sonar-project.properties", "file")],
     [],
     "which SonarQube rule produced the false-positive wave and how was the suppression scoped",
     "sonarqube s2259 java null pointer optional get properties suppress"),
    # --- 39 fact ---
    ("Coverity Scan integrates with the nightly build via the cov-build wrapper that captures the gcc invocations, uploads the intermediate representation, and polls the defect stream until the cov-commit-defects call returns clean.", "fact", "technical", False,
     [("Coverity Scan", "service"), ("cov-build", "tool"), ("gcc", "tool"), ("cov-commit-defects", "tool")],
     [("Coverity Scan", "gcc", "APPLIES_TO")],
     "how does Coverity Scan capture build invocations and feed the defect stream each night",
     "coverity scan cov build gcc commit defect stream nightly wrapper"),
    # --- 40 reference ---
    ("Biome config lives in biome.json at the repo root; the linter extends recommended and the formatter sets indent-style to space with width two to match the legacy prettier baseline.", "reference", "technical", False,
     [("Biome", "tool"), ("biome.json", "file"), ("prettier", "tool"), ("formatter", "concept")],
     [],
     "where does the Biome config sit and which settings keep it compatible with the legacy prettier baseline",
     "biome json repo root linter formatter indent space width prettier"),
    # --- 41 preference ---
    ("Developers prefer ruff over flake8 and isort combined; the single binary and unified cache dropped CI lint duration to 11 seconds on a 180 kLOC Python repo and the reformat pass is lossless on the existing tree.", "preference", "technical", False,
     [("ruff", "tool"), ("flake8", "tool"), ("isort", "tool"), ("Python", "language")],
     [("ruff", "flake8", "REPLACES"), ("ruff", "isort", "REPLACES")],
     "which Python linter replaced flake8 plus isort and what wall-clock win did developers see",
     "ruff flake8 isort python ci lint 180 kloc cache binary fast"),
    # --- 42 architecture ---
    ("golangci-lint runs the curated linter bundle gated by a version file in tools/golangci-version; renovate bumps the version through a pinned PR and the matrix CI re-runs the full suite against the tag before merge.", "architecture", "technical", False,
     [("golangci-lint", "tool"), ("tools/golangci-version", "file"), ("renovate", "tool"), ("matrix CI", "pattern")],
     [("golangci-lint", "renovate", "USES")],
     "how is the golangci-lint version pinned and gated when renovate proposes a bump",
     "golangci lint tools golangci version renovate matrix ci pin bump"),
    # --- 43 noise ---
    ("The communal coffee machine is on its third descaling of the month and the HR notice about rotation duty has been up since March.", "fact", "noise", True, [], [], None, None),
    # --- 44 milestone ---
    ("Frama-C WP plugin cleared the safety-critical kernel module last week; 312 annotations, 9 lemmas, and 47 VCs all discharged under the Alt-Ergo solver inside the six-hour CI window.", "milestone", "technical", False,
     [("Frama-C", "tool"), ("WP plugin", "library"), ("Alt-Ergo", "tool"), ("safety-critical kernel", "project")],
     [("Frama-C", "Alt-Ergo", "USES"), ("Frama-C", "safety-critical kernel", "APPLIES_TO")],
     "which verification run cleared the safety-critical kernel module and which solver discharged the VCs",
     "frama c wp alt ergo kernel safety vc lemma annotation ci six"),
    # --- 45 architecture ---
    ("CodeQL custom pack for internal authentication sinks ships from the security org; every application repo references the pack through the codeql-config.yml extends field so rule updates roll out without repo edits.", "architecture", "technical", False,
     [("CodeQL", "tool"), ("codeql-config.yml", "file"), ("security org", "concept"), ("custom pack", "concept")],
     [("CodeQL", "security org", "APPLIES_TO")],
     "how do application repos pick up CodeQL rule updates from the central security pack",
     "codeql custom pack codeql config yml extends security org rule"),
    # --- 46 fact ---
    ("Infer's pulse mode caught a classic use-after-free across two translation units in the graphics driver that cppcheck and clang-tidy both missed; the offending pointer crossed a void* cast at the module boundary.", "fact", "technical", False,
     [("Infer", "tool"), ("cppcheck", "tool"), ("clang-tidy", "tool"), ("use-after-free", "concept"), ("graphics driver", "project")],
     [("Infer", "graphics driver", "APPLIES_TO")],
     "which Infer mode caught the cross-translation-unit UAF that cppcheck and clang-tidy missed",
     "infer pulse use after free translation unit cppcheck clang tidy"),
    # --- 47 milestone ---
    ("The Moderne hosted run on 2026-02-28 finished the org-wide log4j 1.x to 2.x migration with OpenRewrite; 403 services now carry the reload-guard annotation and the deprecated bridge is gone from every pom.xml.", "milestone", "technical", False,
     [("Moderne", "service"), ("OpenRewrite", "tool"), ("log4j", "library"), ("2026-02-28", "date"), ("pom.xml", "file")],
     [("OpenRewrite", "log4j", "REPLACES")],
     "which org-wide log4j migration finished via Moderne on 2026-02-28 and how many services did it touch",
     "moderne openrewrite log4j 1 2 migration pom xml service bridge"),
    # --- 48 milestone ---
    ("Pyright strict passed clean on the payments service on 2026-04-02; the six-month type-tightening project closed with zero reveal_type lies and a one-point-four-second incremental recheck baseline.", "milestone", "technical", False,
     [("Pyright strict", "tool"), ("payments service", "project"), ("reveal_type", "api"), ("2026-04-02", "date")],
     [("Pyright strict", "payments service", "APPLIES_TO")],
     "when did Pyright strict close on the payments service and what incremental recheck baseline landed",
     "pyright strict payments service reveal type 2026 04 02 recheck"),
    # --- 49 problem ---
    ("Oxlint integration broke on the design-system package because a JSX fragment short-hand parsed differently than ESLint's espree; pinning oxlint to 0.9.5 with the jsx-compat flag restored parity until the upstream fix lands.", "problem", "technical", False,
     [("Oxlint", "tool"), ("JSX", "language"), ("design-system", "project"), ("ESLint", "tool"), ("espree", "library")],
     [],
     "which parser mismatch broke Oxlint on the design system and what pin kept things working",
     "oxlint jsx fragment eslint espree design system 0 9 5 compat"),
    # --- 50 reference ---
    ("The shared-services linter manifest in tools/linters.yaml lists ruff, mypy daemon, Biome, hadolint, shellcheck, yamllint, ansible-lint, tflint, checkov, trivy, and semgrep with version pins and invocation commands per tool.", "reference", "technical", False,
     [("tools/linters.yaml", "file"), ("ruff", "tool"), ("mypy daemon", "tool"), ("Biome", "tool"), ("hadolint", "tool"), ("shellcheck", "tool"), ("yamllint", "tool"), ("ansible-lint", "tool"), ("tflint", "tool"), ("checkov", "tool"), ("trivy", "tool"), ("semgrep", "tool")],
     [],
     "where does the shared-services linter manifest live and which tools does it pin",
     "tools linters yaml ruff mypy biome hadolint shellcheck yaml ansible"),
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
