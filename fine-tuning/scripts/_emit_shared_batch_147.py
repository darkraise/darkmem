"""One-off emitter for shared-base batch-147 — CI/CD pipelines (GitHub Actions, GitLab CI, Jenkins, ArgoCD, Flux, Tekton, caching, matrix builds, OIDC, ephemeral runners, release automation).

Writes 50 rows to data/v2/shared/batch_147.tmp.jsonl with ids shared-07301..07350.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_147.tmp.jsonl"
ID_OFFSET = 7300

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Migrated the monorepo CI from Jenkins Freestyle jobs to GitHub Actions reusable workflows; the declarative workflow_call surface replaced a thousand lines of Groovy glue.", "decision", "technical", False,
     [("Jenkins", "tool"), ("GitHub Actions", "platform"), ("reusable workflows", "pattern"), ("workflow_call", "api"), ("Groovy", "language")],
     [("GitHub Actions", "Jenkins", "REPLACES"), ("reusable workflows", "workflow_call", "USES")],
     "which CI platform and reusable pattern replaced Jenkins Freestyle and Groovy glue in the monorepo",
     "github actions jenkins freestyle reusable workflow call groovy migrate"),
    # --- 2 architecture ---
    ("ArgoCD watches the env/prod overlay in a Kustomize repo and syncs every three minutes; the app-of-apps root manifest fans out into twenty-eight child Applications grouped by team.", "architecture", "technical", False,
     [("ArgoCD", "tool"), ("Kustomize", "tool"), ("app-of-apps", "pattern"), ("Applications", "api")],
     [("ArgoCD", "Kustomize", "USES"), ("app-of-apps", "Applications", "HAS_PART")],
     "how does the GitOps controller fan out environment manifests across twenty-eight team-owned apps",
     "argocd kustomize app of apps sync overlay prod application team"),
    # --- 3 milestone ---
    ("Cutover to Buildkite elastic agents landed on 2026-03-14; the pinned Jenkins master instance is now read-only and scheduled for deletion at the end of the quarter.", "milestone", "technical", False,
     [("Buildkite", "platform"), ("elastic agents", "pattern"), ("Jenkins master", "infrastructure"), ("2026-03-14", "date")],
     [("Buildkite", "Jenkins master", "REPLACES"), ("Buildkite", "2026-03-14", "HAPPENED_ON")],
     "when did the cutover from Jenkins master to Buildkite elastic agents land for the org",
     "buildkite elastic agent jenkins master cutover march read only decommission"),
    # --- 4 fact ---
    ("The GitHub Actions cache key for pnpm is keyed on hashFiles('**/pnpm-lock.yaml'); a stale lock from a bad merge poisoned restores until we added the os and node-version prefix.", "fact", "technical", False,
     [("GitHub Actions", "platform"), ("pnpm", "tool"), ("hashFiles", "api"), ("pnpm-lock.yaml", "file")],
     [("GitHub Actions", "hashFiles", "USES"), ("hashFiles", "pnpm-lock.yaml", "APPLIES_TO")],
     "how is the pnpm dependency cache keyed in Actions and which fields did we add to avoid stale restores",
     "github actions cache key pnpm lock hashfiles os node version prefix"),
    # --- 5 decision ---
    ("Picked CircleCI dynamic config over static workflows for the polyglot monorepo; the setup job inspects changed paths and emits a filtered config that skips untouched services.", "decision", "technical", False,
     [("CircleCI", "platform"), ("dynamic config", "pattern"), ("setup job", "pattern"), ("monorepo", "pattern")],
     [("CircleCI", "dynamic config", "USES"), ("dynamic config", "setup job", "DEPENDS_ON")],
     "which CircleCI feature routes the monorepo to affected-only builds and what job emits the filtered plan",
     "circleci dynamic config setup job monorepo affected path filter skip"),
    # --- 6 architecture ---
    ("Tekton pipelines back the internal platform: a PipelineRun is triggered by an EventListener watching GitHub webhooks, and Tasks run as ephemeral Pods on the in-cluster runner node pool.", "architecture", "technical", False,
     [("Tekton", "framework"), ("PipelineRun", "api"), ("EventListener", "api"), ("GitHub", "platform"), ("Pods", "infrastructure")],
     [("Tekton", "PipelineRun", "HAS_PART"), ("EventListener", "GitHub", "COMMUNICATES_WITH"), ("PipelineRun", "Pods", "DEPLOYED_ON")],
     "how does the internal platform wire GitHub webhooks to ephemeral Kubernetes-backed pipeline runs",
     "tekton pipelinerun eventlistener github webhook pod ephemeral runner"),
    # --- 7 milestone ---
    ("GitLab CI pipeline stalls traced to a shared runner concurrency cap of eight against a 40-stage fan-out; bumping concurrent = 32 in config.toml drained the queue inside an hour.", "milestone", "technical", False,
     [("GitLab CI", "platform"), ("shared runner", "infrastructure"), ("config.toml", "file"), ("concurrent", "config")],
     [("GitLab CI", "shared runner", "USES"), ("concurrent", "config.toml", "CONFIGURES")],
     "which runner concurrency knob unblocked the 40-stage fan-out and where does it live in config",
     "gitlab ci runner concurrent config toml stall fan out queue drain"),
    # --- 8 decision ---
    ("Adopted release-please for automated changelogs on the SDK repos; the previous semantic-release setup kept fighting our conventional-commit guard and double-bumping minors on rebases.", "decision", "technical", False,
     [("release-please", "tool"), ("semantic-release", "tool"), ("changelogs", "pattern"), ("conventional-commit", "pattern")],
     [("release-please", "semantic-release", "REPLACES"), ("release-please", "conventional-commit", "USES")],
     "which release-automation tool replaced semantic-release on the SDK repos and why",
     "release please semantic release changelog conventional commit minor bump rebase"),
    # --- 9 reference ---
    ("Runner pool sizing is documented in docs/ci/runners.md: four m7i.large for the baseline queue, eight c7i.2xlarge for integration, and a spot-only bucket for nightly perf runs.", "reference", "technical", False,
     [("docs/ci/runners.md", "file"), ("m7i.large", "infrastructure"), ("c7i.2xlarge", "infrastructure"), ("spot", "infrastructure")],
     [],
     "where are the CI runner instance sizes and queue tiers documented for the platform team",
     "runner pool docs m7i c7i spot bucket instance size nightly perf"),
    # --- 10 noise ---
    ("The office espresso machine grinds too coarse on Mondays because the maintenance intern forgets to reset the burr after cleaning on Friday.", "fact", "noise", True, [], [], None, None),
    # --- 11 architecture ---
    ("Secrets flow from HashiCorp Vault into GitHub Actions via OIDC: the workflow mints a short-lived JWT, Vault validates the iss claim against the repo, and hands back a 15-minute token.", "architecture", "technical", False,
     [("HashiCorp Vault", "tool"), ("GitHub Actions", "platform"), ("OIDC", "protocol"), ("JWT", "protocol"), ("iss", "config")],
     [("GitHub Actions", "OIDC", "USES"), ("HashiCorp Vault", "JWT", "USES"), ("HashiCorp Vault", "iss", "CONFIGURES")],
     "how does the OIDC handshake between Actions and Vault scope secrets without storing long-lived creds",
     "github actions oidc vault jwt short lived token iss claim repo mint"),
    # --- 12 decision ---
    ("Flux replaced ArgoCD on the platform clusters; the Kustomization controller's multi-tenancy story with impersonation under serviceAccountName was cleaner for our per-team namespace model.", "decision", "technical", False,
     [("Flux", "tool"), ("ArgoCD", "tool"), ("Kustomization", "api"), ("serviceAccountName", "config")],
     [("Flux", "ArgoCD", "REPLACES"), ("Kustomization", "serviceAccountName", "USES")],
     "which GitOps controller replaced ArgoCD on platform clusters and which multi-tenancy feature sealed it",
     "flux argocd kustomization service account impersonation tenant platform"),
    # --- 13 architecture ---
    ("Ephemeral self-hosted runners spin up as EC2 spot instances via actions-runner-controller on EKS; a job-received webhook scales the ScaleSet and the pod self-destructs on job completion.", "architecture", "technical", False,
     [("actions-runner-controller", "tool"), ("EC2", "platform"), ("EKS", "platform"), ("ScaleSet", "api"), ("spot", "infrastructure")],
     [("actions-runner-controller", "EKS", "DEPLOYED_ON"), ("ScaleSet", "EC2", "USES")],
     "how do ephemeral Actions runners spin up on EKS and which scaling object drives the pod lifecycle",
     "ephemeral runner eks actions runner controller scaleset ec2 spot webhook"),
    # --- 14 milestone ---
    ("A Jenkins shared-library cache poisoned PR builds across the org; pointing @Library to a sha-pinned ref and disabling the implicit master fallback stopped the cross-branch contamination.", "milestone", "technical", False,
     [("Jenkins", "tool"), ("shared-library", "pattern"), ("@Library", "api"), ("sha-pinned", "pattern")],
     [("@Library", "sha-pinned", "USES"), ("sha-pinned", "shared-library", "FIXES")],
     "which Jenkins shared-library pinning change stopped PR builds from leaking master library code",
     "jenkins shared library sha pinned master fallback poison pr build"),
    # --- 15 fact ---
    ("Matrix builds in GitHub Actions expand fromJSON(needs.setup.outputs.matrix); our setup step returns a dynamic list of changed packages so untouched libs in the monorepo never queue.", "fact", "technical", False,
     [("GitHub Actions", "platform"), ("matrix", "pattern"), ("fromJSON", "api"), ("setup", "pattern")],
     [("matrix", "fromJSON", "USES")],
     "how does the monorepo dynamic matrix feed changed packages into the Actions job fan-out",
     "github actions matrix fromjson setup output dynamic package changed"),
    # --- 16 decision ---
    ("Went with changesets over semantic-release for the packages/ monorepo; per-package version intents land as .changeset/*.md files and the release PR bundles them into a single coordinated bump.", "decision", "technical", False,
     [("changesets", "tool"), ("semantic-release", "tool"), (".changeset/*.md", "file"), ("release PR", "pattern")],
     [("changesets", "semantic-release", "REPLACES"), ("changesets", ".changeset/*.md", "USES")],
     "which release tool won for the packages monorepo and what artifact captures per-package version intents",
     "changesets semantic release monorepo package version intent markdown pr"),
    # --- 17 decision ---
    ("Preview deploys run on Vercel for the Next.js app and on fly.io for the API; a GitHub Actions job posts both URLs into the PR body so reviewers can click through before approval.", "decision", "technical", False,
     [("Vercel", "service"), ("fly.io", "service"), ("Next.js", "framework"), ("GitHub Actions", "platform"), ("PR", "pattern")],
     [("Next.js", "Vercel", "DEPLOYED_ON"), ("GitHub Actions", "Vercel", "COMMUNICATES_WITH"), ("GitHub Actions", "fly.io", "COMMUNICATES_WITH")],
     "how are per-PR preview environments provisioned across the Next.js app and the API service",
     "vercel fly io preview deploy next js github actions pr url comment"),
    # --- 18 milestone ---
    ("Docker layer cache on Buildkite was blowing past 80 GB on the build hosts; switching to registry-backed cache with type=registry,mode=max in buildx kept the hot path warm without local bloat.", "milestone", "technical", False,
     [("Docker", "tool"), ("Buildkite", "platform"), ("buildx", "tool"), ("type=registry,mode=max", "config")],
     [("buildx", "type=registry,mode=max", "USES"), ("buildx", "Docker", "CONFIGURES")],
     "which buildx cache mode replaced local layer storage on Buildkite and what bloat did it retire",
     "docker buildkite buildx registry cache mode max layer bloat 80gb"),
    # --- 19 architecture ---
    ("Drone CI runs on a three-node k3s cluster behind Cloudflare Tunnel; the kubernetes runner backend schedules step pods and the autoscaler drains nodes during the 03:00 UTC quiet window.", "architecture", "technical", False,
     [("Drone", "platform"), ("k3s", "tool"), ("Cloudflare Tunnel", "service"), ("kubernetes runner", "infrastructure")],
     [("Drone", "k3s", "DEPLOYED_ON"), ("Drone", "Cloudflare Tunnel", "COMMUNICATES_WITH"), ("Drone", "kubernetes runner", "USES")],
     "how is the Drone CI runtime deployed and which runner backend schedules pipeline steps",
     "drone k3s cloudflare tunnel kubernetes runner autoscale quiet window"),
    # --- 20 decision ---
    ("Promotion gates between staging and prod are manual environment reviewers in GitHub Actions; the earlier branch-protection-only model let a merge skip the smoke-test approval chain.", "decision", "technical", False,
     [("GitHub Actions", "platform"), ("environment reviewers", "pattern"), ("branch-protection", "pattern"), ("smoke-test", "pattern")],
     [("environment reviewers", "branch-protection", "REPLACES"), ("GitHub Actions", "environment reviewers", "USES")],
     "which Actions feature replaced branch protection as the prod promotion gate after a bypass incident",
     "environment reviewer branch protection promotion gate staging prod smoke"),
    # --- 21 reference ---
    ("The Jenkinsfile shared-library API lives under vars/ as Groovy scripts; the style guide in CONTRIBUTING.md requires @NonCPS on any helper that iterates a Map to avoid serialization crashes.", "reference", "technical", False,
     [("Jenkinsfile", "file"), ("vars/", "file"), ("Groovy", "language"), ("@NonCPS", "api"), ("CONTRIBUTING.md", "file")],
     [("Jenkinsfile", "vars/", "USES"), ("vars/", "Groovy", "IMPLEMENTS")],
     "where do Jenkins shared-library helpers live and what annotation keeps Map iteration crash-free",
     "jenkinsfile vars groovy shared library noncps map iterate serialize"),
    # --- 22 fact ---
    ("GitLab CI rules:changes paths land in the rules: block with a compare_to of the default branch; the earlier only:changes syntax was deprecated in 15.0 and quietly no-ops on newer runners.", "fact", "technical", False,
     [("GitLab CI", "platform"), ("rules:changes", "api"), ("compare_to", "config"), ("only:changes", "api")],
     [("rules:changes", "only:changes", "REPLACES"), ("rules:changes", "compare_to", "USES")],
     "which GitLab CI keyword replaced only:changes for path-based job filtering and what comparison ref does it use",
     "gitlab ci rules changes compare to only deprecated 15 0 path filter"),
    # --- 23 reference ---
    ("The internal Python wheel build runs in parallel shards on TeamCity; a master job seeds a build chain and dependency matrix across x86_64 and aarch64 agents with artifact pass-through.", "reference", "technical", False,
     [("TeamCity", "platform"), ("Python", "language"), ("build chain", "pattern"), ("x86_64", "platform"), ("aarch64", "platform")],
     [("TeamCity", "build chain", "USES"), ("build chain", "x86_64", "APPLIES_TO"), ("build chain", "aarch64", "APPLIES_TO")],
     "how are cross-arch Python wheel builds parallelised on TeamCity and which feature passes artifacts between jobs",
     "teamcity python wheel shard build chain x86 aarch64 artifact matrix"),
    # --- 24 milestone ---
    ("On 2026-02-28 we finished migrating all secrets out of Travis env vars into AWS Secrets Manager pulled via OIDC; the last repo to flip was the legacy billing-gateway service.", "milestone", "technical", False,
     [("Travis", "platform"), ("AWS Secrets Manager", "service"), ("OIDC", "protocol"), ("billing-gateway", "service"), ("2026-02-28", "date")],
     [("AWS Secrets Manager", "Travis", "REPLACES"), ("AWS Secrets Manager", "OIDC", "USES"), ("billing-gateway", "2026-02-28", "HAPPENED_ON")],
     "when did we retire the last Travis env-var secret and which service was the final holdout",
     "travis aws secrets manager oidc billing gateway migration last repo"),
    # --- 25 decision ---
    ("Chose Woodpecker CI over Gitea Actions for the self-hosted code mirror; the pipeline DSL is closer to Drone's and we already had Drone-shaped plugins from the old setup.", "decision", "technical", False,
     [("Woodpecker", "platform"), ("Gitea Actions", "platform"), ("Drone", "platform"), ("plugins", "pattern")],
     [("Woodpecker", "Gitea Actions", "PREFERS"), ("Woodpecker", "Drone", "BUILDS_ON")],
     "which self-hosted CI won over Gitea Actions for the mirror and what prior investment pushed the decision",
     "woodpecker gitea actions drone plugin self hosted mirror dsl"),
    # --- 26 problem ---
    ("Nightly matrix builds were silently green because a missing fail-fast: false with continue-on-error: true swallowed individual shard failures; the top-level job passed while three OSes actually broke.", "problem", "technical", False,
     [("matrix", "pattern"), ("fail-fast", "config"), ("continue-on-error", "config")],
     [("fail-fast", "matrix", "CONFIGURES"), ("continue-on-error", "matrix", "CONFIGURES")],
     "which matrix knobs combined to hide broken-OS shard failures in the nightly builds",
     "matrix fail fast continue on error nightly green silent shard os"),
    # --- 27 architecture ---
    ("Jenkins agents run inside Kubernetes via the jenkins-kubernetes-plugin with a PodTemplate per language; the inbound TCP 50000 port is closed in favour of WebSocket agents through the ingress.", "architecture", "technical", False,
     [("Jenkins", "tool"), ("Kubernetes", "platform"), ("jenkins-kubernetes-plugin", "tool"), ("PodTemplate", "api"), ("WebSocket", "protocol")],
     [("Jenkins", "Kubernetes", "DEPLOYED_ON"), ("Jenkins", "jenkins-kubernetes-plugin", "USES"), ("Jenkins", "WebSocket", "COMMUNICATES_WITH")],
     "how do Jenkins agents attach over Kubernetes without opening the classic inbound TCP port",
     "jenkins kubernetes plugin pod template websocket ingress inbound 50000"),
    # --- 28 preference ---
    ("Team convention: every workflow file pins actions to a 40-character SHA, never a floating tag; Dependabot version-update rewrites the SHAs weekly so the signal-to-noise stays manageable.", "preference", "technical", False,
     [("workflow", "file"), ("SHA", "pattern"), ("Dependabot", "tool"), ("tag", "pattern")],
     [("workflow", "SHA", "PREFERS"), ("Dependabot", "workflow", "CONFIGURES")],
     "what pin style do workflows require for third-party actions and what keeps those pins fresh",
     "workflow sha pin dependabot rewrite tag floating version update weekly"),
    # --- 29 fact ---
    ("Buildkite's dynamic pipeline uploads call pipeline.yml via a buildkite-agent pipeline upload step; our generator emits a JSON schema-validated payload before the upload to catch typos early.", "fact", "technical", False,
     [("Buildkite", "platform"), ("pipeline.yml", "file"), ("buildkite-agent", "tool"), ("JSON schema", "technology")],
     [("Buildkite", "pipeline.yml", "USES"), ("buildkite-agent", "pipeline.yml", "CONFIGURES"), ("JSON schema", "pipeline.yml", "APPLIES_TO")],
     "how does dynamic pipeline upload work in Buildkite and what guardrail catches typos before the upload",
     "buildkite pipeline yml buildkite agent upload dynamic json schema validate"),
    # --- 30 architecture ---
    ("Bazel remote cache runs on an in-VPC BuildBuddy with mTLS; CI jobs authenticate via short-lived tokens from the GitHub OIDC provider, and cache hits regularly push remote-exec savings past 70%.", "architecture", "technical", False,
     [("Bazel", "tool"), ("BuildBuddy", "service"), ("mTLS", "protocol"), ("OIDC", "protocol"), ("remote-exec", "pattern")],
     [("Bazel", "BuildBuddy", "USES"), ("BuildBuddy", "mTLS", "USES"), ("BuildBuddy", "OIDC", "USES")],
     "which remote-cache backend does Bazel talk to and how are CI jobs authenticated to it",
     "bazel buildbuddy mtls oidc remote cache exec hit rate github vpc"),
    # --- 31 decision ---
    ("Picked GitHub merge queue over Bors-ng for the main monorepo; the native integration with required checks and speculative batching was enough to retire the homegrown queue-bot.", "decision", "technical", False,
     [("GitHub", "platform"), ("merge queue", "pattern"), ("Bors-ng", "tool"), ("queue-bot", "service")],
     [("merge queue", "Bors-ng", "REPLACES"), ("merge queue", "queue-bot", "REPLACES")],
     "which merge-automation tool replaced Bors-ng and the homegrown queue-bot on the main monorepo",
     "github merge queue bors ng queue bot speculative batch required check retire"),
    # --- 32 milestone ---
    ("Flaky integration tests re-ran three times automatically via retry: in GitLab CI and hid a real race; we cut retry to zero on main and the underlying flake surfaced within two days.", "milestone", "technical", False,
     [("integration tests", "pattern"), ("retry:", "config"), ("GitLab CI", "platform"), ("flake", "error")],
     [("retry:", "GitLab CI", "CONFIGURES"), ("retry:", "flake", "CAUSES")],
     "which GitLab CI retry setting was masking a real race and how did disabling it help surface the bug",
     "gitlab ci retry flake integration test main race hidden auto rerun"),
    # --- 33 decision ---
    ("Image signing uses cosign with keyless OIDC-based signatures; the GitHub Actions identity is embedded in the Rekor transparency log and policy-controller verifies before admission on the cluster.", "decision", "technical", False,
     [("cosign", "tool"), ("OIDC", "protocol"), ("GitHub Actions", "platform"), ("Rekor", "service"), ("policy-controller", "tool")],
     [("cosign", "OIDC", "USES"), ("cosign", "Rekor", "USES"), ("policy-controller", "cosign", "USES")],
     "how do container images get signed keylessly in CI and what admits or rejects them on the cluster",
     "cosign keyless oidc rekor transparency log policy controller admission github"),
    # --- 34 preference ---
    ("Prefer GitHub Actions composite actions over Docker container actions for the shared setup steps; composite runs reuse the host toolchain cache and start five seconds faster per job.", "preference", "technical", False,
     [("GitHub Actions", "platform"), ("composite actions", "pattern"), ("Docker container actions", "pattern"), ("toolchain cache", "pattern")],
     [("composite actions", "Docker container actions", "PREFERS"), ("composite actions", "toolchain cache", "USES")],
     "which Actions action flavour does the team prefer for shared setup and what startup win does it unlock",
     "github actions composite docker container toolchain cache startup second"),
    # --- 35 reference ---
    ("The canonical CI runbook at docs/ops/ci-runbook.md covers runner cycling, cache bust procedure, and the emergency disable-workflow endpoint for stuck jobs on release day.", "reference", "technical", False,
     [("docs/ops/ci-runbook.md", "file"), ("runner", "infrastructure"), ("cache bust", "pattern"), ("disable-workflow", "api")],
     [],
     "where does on-call find the playbook for stuck release-day jobs and agent recycling",
     "ci runbook docs ops runner cycle cache bust disable workflow release"),
    # --- 36 fact ---
    ("Affected-only builds in the Turborepo monorepo use turbo run build --filter=...[origin/main]; the base ref flips to the merge-base SHA on PR events so refactors don't trigger the whole graph.", "fact", "technical", False,
     [("Turborepo", "tool"), ("monorepo", "pattern"), ("--filter", "command"), ("merge-base", "pattern")],
     [("Turborepo", "--filter", "USES"), ("Turborepo", "merge-base", "USES")],
     "how does Turborepo scope builds to affected packages and which ref does the filter compare against on PRs",
     "turborepo affected filter monorepo merge base sha pr event package graph"),
    # --- 37 fact ---
    ("actions/cache v4 removed the per-repo 10 GB cap in favour of a sliding 10 GB LRU per key prefix; misreading the docs cost us two days of mysterious cache evictions on the big C++ repo.", "fact", "technical", False,
     [("actions/cache", "tool"), ("LRU", "algorithm"), ("C++", "language"), ("10 GB", "config")],
     [("actions/cache", "LRU", "USES"), ("actions/cache", "10 GB", "CONFIGURES")],
     "how did quota semantics shift in the v4 action and which repo ate the mysterious eviction bill",
     "actions cache v4 10gb lru sliding key prefix eviction c plus plus"),
    # --- 38 decision ---
    ("Switched the release pipeline to goreleaser for the Go CLIs; the prior hand-rolled matrix across darwin-arm64, linux-amd64, and windows-amd64 drifted on checksums every second release.", "decision", "technical", False,
     [("goreleaser", "tool"), ("Go", "language"), ("darwin-arm64", "platform"), ("linux-amd64", "platform"), ("windows-amd64", "platform")],
     [("goreleaser", "Go", "APPLIES_TO"), ("goreleaser", "darwin-arm64", "SUPPORTS"), ("goreleaser", "linux-amd64", "SUPPORTS"), ("goreleaser", "windows-amd64", "SUPPORTS")],
     "which release tool replaced the hand-rolled Go cross-compile matrix after checksum drift became routine",
     "goreleaser go cli darwin arm64 linux amd64 windows checksum drift matrix"),
    # --- 39 architecture ---
    ("ArgoCD image updater reconciles a write-back commit to the env repo on new image tags; the Application is set to automated sync with selfHeal true so manual drift is reverted within a cycle.", "architecture", "technical", False,
     [("ArgoCD", "tool"), ("image updater", "tool"), ("Application", "api"), ("selfHeal", "config"), ("automated sync", "pattern")],
     [("image updater", "ArgoCD", "EXTENDS"), ("Application", "selfHeal", "USES"), ("Application", "automated sync", "USES")],
     "how does the image-updater loop close with ArgoCD and which Application settings keep drift out of prod",
     "argocd image updater application self heal automated sync write back env"),
    # --- 40 problem ---
    ("OIDC trust-policy drift broke deploys: the aud claim was hardcoded to sts.amazonaws.com but our federated role expected a custom audience; realigning the audience in the Actions workflow fixed it.", "problem", "technical", False,
     [("OIDC", "protocol"), ("aud", "config"), ("sts.amazonaws.com", "service"), ("federated role", "pattern"), ("Actions", "platform")],
     [("OIDC", "aud", "USES"), ("aud", "sts.amazonaws.com", "CONFIGURES"), ("aud", "federated role", "APPLIES_TO")],
     "which OIDC claim mismatch broke deploys and where did the fix land in the Actions workflow",
     "oidc aud sts amazonaws federated role audience hardcode workflow fix"),
    # --- 41 architecture ---
    ("Secrets rotation is driven by External Secrets Operator pulling from AWS Secrets Manager; ESO syncs into Kubernetes Secret objects every 30 minutes and the deployment reloader restarts pods on change.", "architecture", "technical", False,
     [("External Secrets Operator", "tool"), ("AWS Secrets Manager", "service"), ("Kubernetes Secret", "api"), ("reloader", "tool")],
     [("External Secrets Operator", "AWS Secrets Manager", "COMMUNICATES_WITH"), ("External Secrets Operator", "Kubernetes Secret", "PRODUCES"), ("reloader", "Kubernetes Secret", "USES")],
     "how does the cluster pull rotated secrets from AWS and which controller restarts pods on the change",
     "external secrets operator aws secrets manager kubernetes reloader sync rotate"),
    # --- 42 milestone ---
    ("Achieved sub-four-minute median CI on the platform monorepo on 2026-01-22 after sharding Jest across eight runners and moving the Docker buildx cache to a regional R2 bucket.", "milestone", "technical", False,
     [("Jest", "tool"), ("buildx", "tool"), ("R2", "service"), ("platform monorepo", "project"), ("2026-01-22", "date")],
     [("Jest", "platform monorepo", "APPLIES_TO"), ("buildx", "R2", "USES"), ("platform monorepo", "2026-01-22", "HAPPENED_ON")],
     "when did the platform monorepo hit sub-four-minute median CI and what two changes got us there",
     "platform monorepo ci four minute jest shard buildx r2 january 22"),
    # --- 43 noise ---
    ("The ficus by reception dropped half its leaves after someone overwatered it during the long weekend and the replacement pot is still back-ordered.", "fact", "noise", True, [], [], None, None),
    # --- 44 decision ---
    ("Adopted skaffold dev for local-to-cluster inner loop in place of tilt; skaffold's file-sync and hot-deploy profiles matched the team's existing Helm charts with less YAML surgery.", "decision", "technical", False,
     [("skaffold", "tool"), ("tilt", "tool"), ("Helm", "tool"), ("file-sync", "pattern"), ("hot-deploy", "pattern")],
     [("skaffold", "tilt", "REPLACES"), ("skaffold", "Helm", "USES"), ("skaffold", "file-sync", "USES")],
     "which local inner-loop tool replaced tilt and which feature aligned better with the team's Helm charts",
     "skaffold tilt helm file sync hot deploy local inner loop yaml chart"),
    # --- 45 reference ---
    ("The reusable workflow .github/workflows/ci-node.yml takes inputs node-version, pnpm-version, and run-e2e; the contract is documented in docs/ci/reusable.md with semver policy for breaking changes.", "reference", "technical", False,
     [(".github/workflows/ci-node.yml", "file"), ("node-version", "config"), ("pnpm-version", "config"), ("run-e2e", "config"), ("docs/ci/reusable.md", "file")],
     [(".github/workflows/ci-node.yml", "node-version", "USES"), (".github/workflows/ci-node.yml", "pnpm-version", "USES"), (".github/workflows/ci-node.yml", "run-e2e", "USES")],
     "which file holds the shared node CI workflow and which inputs does it accept",
     "reusable workflow ci node yml inputs pnpm version run e2e semver doc"),
    # --- 46 reference ---
    ("Nightly perf suite runs on bare-metal Hetzner runners registered as self-hosted GitHub runners; the job uses runs-on: [self-hosted, perf, amd-zen4] to pin to the reserved fleet.", "reference", "technical", False,
     [("Hetzner", "platform"), ("GitHub", "platform"), ("self-hosted", "infrastructure"), ("runs-on", "config"), ("amd-zen4", "platform")],
     [("GitHub", "Hetzner", "DEPLOYED_ON"), ("runs-on", "self-hosted", "USES"), ("runs-on", "amd-zen4", "APPLIES_TO")],
     "how is the nightly perf suite pinned to reserved bare-metal runners in GitHub Actions",
     "hetzner self hosted github runner runs on perf amd zen4 nightly"),
    # --- 47 problem ---
    ("A flaky flake-y Tekton Task failed with ExitCode 137 mid-run; the step pod was OOMKilled because the default memory limit of 512Mi wasn't lifted for the webpack bundler shard.", "problem", "technical", False,
     [("Tekton", "framework"), ("Task", "api"), ("OOMKilled", "error"), ("webpack", "tool"), ("512Mi", "config")],
     [("Task", "OOMKilled", "CAUSES"), ("512Mi", "Task", "CONFIGURES"), ("webpack", "Task", "APPLIES_TO")],
     "which Tekton Task resource limit caused the ExitCode 137 failure on the webpack bundler shard",
     "tekton task oomkilled exitcode 137 webpack 512mi memory limit shard"),
    # --- 48 fact ---
    ("GitHub Actions concurrency: group uses ${{ github.workflow }}-${{ github.ref }} with cancel-in-progress: true so pushing to a PR branch mid-run cancels the stale run instead of queueing.", "fact", "technical", False,
     [("GitHub Actions", "platform"), ("concurrency", "config"), ("cancel-in-progress", "config"), ("github.workflow", "api"), ("github.ref", "api")],
     [("concurrency", "cancel-in-progress", "USES"), ("concurrency", "github.workflow", "USES"), ("concurrency", "github.ref", "USES")],
     "how does the Actions concurrency group cancel stale PR runs when a new push lands",
     "github actions concurrency group cancel in progress workflow ref push pr"),
    # --- 49 preference ---
    ("We favour declarative Jenkinsfile pipelines over scripted ones for new services; the structured stages block keeps the Blue Ocean view readable and cuts review time on pipeline PRs.", "preference", "technical", False,
     [("Jenkinsfile", "file"), ("declarative", "pattern"), ("scripted", "pattern"), ("Blue Ocean", "tool")],
     [("declarative", "scripted", "PREFERS"), ("Jenkinsfile", "declarative", "USES"), ("Blue Ocean", "Jenkinsfile", "APPLIES_TO")],
     "which Jenkinsfile flavour does the team prefer for new services and what review win does it offer",
     "jenkinsfile declarative scripted blue ocean stage view readable review"),
    # --- 50 preference ---
    ("Keep workflow job timeouts explicit via timeout-minutes: 20 on every job; unbounded runs on self-hosted runners used to wedge an agent for hours when a test deadlocked overnight.", "preference", "technical", False,
     [("timeout-minutes", "config"), ("self-hosted", "infrastructure"), ("agent", "infrastructure"), ("deadlock", "error")],
     [("timeout-minutes", "agent", "APPLIES_TO"), ("deadlock", "agent", "CAUSES")],
     "which workflow setting does the team require on every job and what runner incident drove the rule",
     "timeout minutes job self hosted agent wedge deadlock overnight bound"),
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
