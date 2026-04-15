"""One-off emitter for shared-base batch-130 — ai_coding domain (dependency management at the code level: lockfiles, version pinning, monorepo policies, private registries, supply-chain attestations, audit tooling).

Writes 50 rows to data/v2/shared/batch_130.tmp.jsonl with ids shared-06451..06500.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_130.tmp.jsonl"
ID_OFFSET = 6450

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the Python services from pip to uv for lockfile management; uv.lock resolves the whole workspace in one pass and build times on CI halved.", "decision", "ai_coding", False,
     [("uv", "tool"), ("pip", "tool"), ("uv.lock", "file")],
     [("uv", "pip", "REPLACES")],
     "which Python lockfile tool replaced pip across the services and what did it buy on CI",
     "uv lock pip replace python resolve workspace ci build time"),
    # --- 2 ---
    ("The frontend monorepo swapped yarn classic for pnpm; the content-addressable store cut disk usage across workspace packages and the workspace protocol pins intra-repo links.", "milestone", "ai_coding", False,
     [("yarn classic", "tool"), ("pnpm", "tool"), ("workspace protocol", "pattern")],
     [("pnpm", "yarn classic", "REPLACES")],
     "which package manager took over the frontend monorepo and what changed about intra-repo linking",
     "pnpm replace yarn classic monorepo content addressable workspace"),
    # --- 3 ---
    ("package-lock.json is committed with every PR and the CI step runs npm ci rather than npm install; a drift check diffs the lockfile after install to catch silent bumps.", "architecture", "ai_coding", False,
     [("package-lock.json", "file"), ("npm ci", "command"), ("npm install", "command")],
     [("npm ci", "npm install", "PREFERS")],
     "how does the Node pipeline stop silent lockfile drift from landing on main",
     "package lock npm ci install drift check diff pipeline"),
    # --- 4 ---
    ("Version ranges in package.json shifted from caret to exact pins on production dependencies; caret still stands for devDependencies where the blast radius is local.", "decision", "ai_coding", False,
     [("package.json", "file"), ("caret", "pattern"), ("exact pins", "pattern"), ("devDependencies", "config")],
     [("exact pins", "caret", "PREFERS")],
     "which version-range policy replaced blanket carets and where do the old ranges still live",
     "caret tilde exact pin package json dev dependency production"),
    # --- 5 ---
    ("Renovate took over from Dependabot once the team needed grouped updates, dashboard issues, and custom presets for security-only vs minor bumps.", "decision", "ai_coding", False,
     [("Renovate", "tool"), ("Dependabot", "tool"), ("preset", "config")],
     [("Renovate", "Dependabot", "REPLACES")],
     "which dependency bot replaced Dependabot and what features tipped the decision",
     "renovate replace dependabot grouped update dashboard preset"),
    # --- 6 ---
    ("poetry.lock is the source of truth for the Python API; CI fails if poetry lock --check reports drift, so contributors run the fix locally before pushing.", "architecture", "ai_coding", False,
     [("poetry.lock", "file"), ("poetry lock --check", "command"), ("Python API", "service")],
     [],
     "how does the Python API repo keep poetry.lock authoritative and catch drift before merge",
     "poetry lock check ci drift python api contributor"),
    # --- 7 ---
    ("Cargo.lock is now committed for the CLI crates too; we used to skip it for libraries, but reproducible builds for the shipped binaries outweighed the purism.", "decision", "ai_coding", False,
     [("Cargo.lock", "file"), ("CLI", "project")],
     [],
     "why did we start committing Cargo.lock on the CLI crates despite the library convention",
     "cargo lock commit cli crate reproducible binary library"),
    # --- 8 ---
    ("The Turborepo pipeline replaced lerna; remote caching on Vercel fed every workspace build and the test step keyed off changed files instead of full graph rebuilds.", "milestone", "ai_coding", False,
     [("Turborepo", "tool"), ("lerna", "tool"), ("Vercel", "service")],
     [("Turborepo", "lerna", "REPLACES")],
     "which monorepo build tool replaced lerna and how did remote caching change the test loop",
     "turborepo replace lerna remote cache vercel workspace build"),
    # --- 9 ---
    ("Nx graph enforces module boundaries in the Angular monorepo; a feature lib cannot import from another feature lib, only from shared or data-access tags.", "architecture", "ai_coding", False,
     [("Nx", "tool"), ("Angular", "framework"), ("feature lib", "pattern")],
     [],
     "how does the Angular monorepo police cross-feature imports at build time",
     "nx module boundary tag feature lib shared data access angular"),
    # --- 10. noise ---
    ("The espresso machine in the kitchen leaks when the first pot of the morning comes through, every single day.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Yarn Berry with PnP and zero-installs runs the design-system repo; the .yarn/cache is committed so CI never hits the registry at all.", "architecture", "ai_coding", False,
     [("Yarn Berry", "tool"), ("PnP", "pattern"), (".yarn/cache", "file")],
     [],
     "which Yarn mode powers the design-system repo and why is the cache checked into git",
     "yarn berry pnp zero install cache commit design system ci"),
    # --- 12 ---
    ("A private Verdaccio instance proxies npm and hosts the internal scope; the .npmrc points the @acme scope at Verdaccio and public packages fall through transparently.", "architecture", "ai_coding", False,
     [("Verdaccio", "tool"), ("npm", "tool"), (".npmrc", "file"), ("@acme", "config")],
     [],
     "how does the team host internal npm packages while still pulling public ones transparently",
     "verdaccio private registry proxy npmrc scope acme fallback"),
    # --- 13 ---
    ("JFrog Artifactory replaced a homegrown Nexus setup for Java artefacts; the virtual repo layers snapshots, releases, and Maven Central behind one URL.", "decision", "ai_coding", False,
     [("JFrog Artifactory", "tool"), ("Nexus", "tool"), ("Maven Central", "service")],
     [("JFrog Artifactory", "Nexus", "REPLACES")],
     "which artefact server replaced the Nexus install and how is the virtual repo structured",
     "jfrog artifactory replace nexus virtual repo maven central java"),
    # --- 14 ---
    ("GitHub Packages hosts the signed container images and npm scopes for the platform org; the same PAT covers pull and publish so CI only needs one secret.", "architecture", "ai_coding", False,
     [("GitHub Packages", "service"), ("PAT", "config"), ("platform", "project")],
     [],
     "which registry hosts the org's container images and npm scopes and how does CI authenticate",
     "github packages pat registry container npm scope ci secret"),
    # --- 15 ---
    ("AWS CodeArtifact fronts PyPI for the data team; the domain-level upstream rule means a package newly published to PyPI shows up internally after the first install.", "architecture", "ai_coding", False,
     [("AWS CodeArtifact", "service"), ("PyPI", "service"), ("upstream", "config")],
     [],
     "how does the data team pull from PyPI without exposing build infra to the public index",
     "aws codeartifact pypi upstream proxy domain python data team"),
    # --- 16 ---
    ("Maven dependencyManagement now points to a published BOM from the platform team; service poms declare versions via import scope instead of hand-picked numbers.", "architecture", "ai_coding", False,
     [("Maven", "tool"), ("BOM", "pattern"), ("dependencyManagement", "config")],
     [],
     "which Maven pattern centralised version choices across the service poms",
     "maven bom dependency management import scope platform version"),
    # --- 17 ---
    ("Gradle version catalogs in libs.versions.toml replaced a tangle of ext properties; a single TOML file now owns every library coordinate across the multi-project build.", "decision", "ai_coding", False,
     [("Gradle", "tool"), ("libs.versions.toml", "file"), ("ext", "config")],
     [("libs.versions.toml", "ext", "REPLACES")],
     "which Gradle feature replaced ext-property version strings across the multi-project build",
     "gradle version catalog libs toml ext replace multi project"),
    # --- 18 ---
    ("Go modules go through a GOPROXY pointing at an Athens mirror; GOSUMDB stays on sum.golang.org and the mirror caches every module the builds have ever pulled.", "architecture", "ai_coding", False,
     [("Go modules", "technology"), ("GOPROXY", "config"), ("Athens", "tool"), ("GOSUMDB", "config")],
     [],
     "how does the Go build pipeline cache modules while still verifying via the public sum database",
     "goproxy athens gosumdb go modules mirror cache sum database"),
    # --- 19 ---
    ("A Rust workspace-hack crate pre-unifies feature flags across the 40-crate workspace; without it, cargo kept rebuilding serde thrice with different feature sets.", "problem", "ai_coding", False,
     [("Rust", "language"), ("workspace-hack", "pattern"), ("serde", "library")],
     [],
     "which Rust trick stopped cargo from rebuilding serde with inconsistent feature sets across the workspace",
     "rust workspace hack feature unify serde rebuild cargo crate"),
    # --- 20 ---
    ("Deno import maps live in deno.json and pin every remote URL to a specific version; the lock file covers transitive fetches so a CDN change can't quietly alter code.", "architecture", "ai_coding", False,
     [("Deno", "tool"), ("import maps", "pattern"), ("deno.json", "file")],
     [],
     "how does the Deno project pin remote modules so a CDN change cannot alter shipped code",
     "deno import map lock json pin cdn remote transitive"),
    # --- 21 ---
    ("Node started shipping with import maps in the package.json imports field; a bunch of aliasing that used to live in tsconfig paths moved there for runtime parity.", "fact", "ai_coding", False,
     [("Node", "platform"), ("package.json", "file"), ("tsconfig", "file")],
     [],
     "which Node feature took over the aliasing that used to live in tsconfig paths at runtime",
     "node import map package json imports alias tsconfig runtime"),
    # --- 22 ---
    ("Publishing releases through npm provenance attestations replaced the old unsigned tarball flow; the release workflow runs on GitHub Actions and stamps the package with an OIDC claim.", "milestone", "ai_coding", False,
     [("npm provenance", "pattern"), ("unsigned tarball", "pattern"), ("GitHub Actions", "service"), ("OIDC", "protocol")],
     [("npm provenance", "unsigned tarball", "REPLACES")],
     "which publishing mechanism replaced unsigned tarballs and where does the trust anchor come from",
     "npm provenance attest oidc github actions replace unsigned tarball"),
    # --- 23 ---
    ("PyPI trusted publishing via OIDC replaced long-lived API tokens on the release workflow; the package page now shows the GitHub repository that uploaded the distribution.", "decision", "ai_coding", False,
     [("PyPI", "service"), ("trusted publishing", "pattern"), ("API tokens", "config")],
     [("trusted publishing", "API tokens", "REPLACES")],
     "which PyPI mechanism replaced long-lived API tokens and what visible signal does it add",
     "pypi trusted publishing oidc api token replace release workflow"),
    # --- 24 ---
    ("pip-audit runs inside a pre-commit hook on requirements.txt; failing finds block the commit unless the hash is explicitly allowlisted in .pip-audit-ignore.", "architecture", "ai_coding", False,
     [("pip-audit", "tool"), ("pre-commit", "tool"), ("requirements.txt", "file")],
     [],
     "which Python audit tool gates commits on vulnerable dependencies and how are exceptions managed",
     "pip audit pre commit requirements block allowlist ignore"),
    # --- 25 ---
    ("osv-scanner scans every Go and Python lockfile in the monorepo; the JSON output is converted to SARIF and uploaded to code scanning for the triage dashboard.", "architecture", "ai_coding", False,
     [("osv-scanner", "tool"), ("SARIF", "protocol"), ("monorepo", "project")],
     [],
     "which cross-language vulnerability scanner feeds the code-scanning dashboard across the monorepo",
     "osv scanner sarif code scanning go python lockfile monorepo"),
    # --- 26 ---
    ("peerDependencies on the shared React component library are pinned to an exact minor; react and react-dom must match the host app or npm refuses to install without --legacy-peer-deps.", "architecture", "ai_coding", False,
     [("peerDependencies", "config"), ("React", "framework"), ("--legacy-peer-deps", "config")],
     [],
     "how does the shared component library keep host React versions aligned without implicit dedupe",
     "peer dependency react exact minor legacy peer deps npm host"),
    # --- 27 ---
    ("The lockfile-lint config bans unknown registries and git+ssh URLs; a 2026-02-04 incident where a dev accidentally pointed a transitive at a fork taught us to gate it.", "problem", "ai_coding", False,
     [("lockfile-lint", "tool"), ("git+ssh", "pattern"), ("2026-02-04", "date")],
     [],
     "which lockfile-lint rules stopped stray fork URLs from landing and what drove adding them",
     "lockfile lint registry git ssh fork transitive incident gate"),
    # --- 28 ---
    ("pnpm workspaces use the catalog feature to version shared dependencies once; typescript and eslint live in pnpm-workspace.yaml's catalog and every package imports the catalog alias.", "architecture", "ai_coding", False,
     [("pnpm", "tool"), ("catalog", "pattern"), ("pnpm-workspace.yaml", "file"), ("typescript", "tool"), ("eslint", "tool")],
     [],
     "which pnpm feature centralises shared dependency versions across the workspace",
     "pnpm catalog workspace yaml typescript eslint shared version"),
    # --- 29 ---
    ("Composer handles the PHP monorepo and composer.lock is committed; platform-check runs in CI so a PHP version upgrade doesn't silently ship mismatched extension constraints.", "architecture", "ai_coding", False,
     [("Composer", "tool"), ("composer.lock", "file"), ("PHP", "language"), ("platform-check", "command")],
     [],
     "how does the PHP monorepo catch platform constraint drift when someone bumps the runtime",
     "composer lock php platform check extension constraint monorepo"),
    # --- 30 ---
    ("Rust's cargo-deny config enforces license allowlist, RustSec advisory database scans, and ban rules for duplicate crates; the CI step fails the build on any of the three.", "architecture", "ai_coding", False,
     [("cargo-deny", "tool"), ("RustSec", "service"), ("license allowlist", "pattern")],
     [],
     "which Rust policy tool covers licenses, advisories, and duplicate crates in one CI step",
     "cargo deny license advisory ban duplicate rust ci policy"),
    # --- 31 ---
    ("The docs ignore-update rule in Renovate keeps major framework bumps behind a schedule; Tailwind 4 and Next 15 wait for the monthly upgrade window instead of flooding PRs.", "preference", "ai_coding", False,
     [("Renovate", "tool"), ("Tailwind", "framework"), ("Next", "framework")],
     [],
     "which Renovate policy keeps major framework bumps from flooding the PR queue",
     "renovate schedule major framework tailwind next monthly upgrade"),
    # --- 32 ---
    ("Dependabot's grouped updates cover patch releases on a weekly cadence; security alerts still open individual PRs so they can be merged without waiting for the group.", "fact", "ai_coding", False,
     [("Dependabot", "tool"), ("grouped updates", "pattern")],
     [],
     "how does Dependabot balance grouping patch updates with the urgency of security alerts",
     "dependabot group patch weekly security alert individual pr"),
    # --- 33 ---
    ("All npm installs in CI run with --ignore-scripts; a separate vetted allowlist of packages that legitimately need lifecycle scripts lives in .npmrc ignore-scripts=false blocks.", "architecture", "ai_coding", False,
     [("npm", "tool"), ("--ignore-scripts", "config"), (".npmrc", "file"), ("lifecycle scripts", "pattern")],
     [],
     "which hardening flag do CI npm installs pass and how do legitimate scripts get an exception",
     "npm ignore scripts ci allowlist lifecycle npmrc exception"),
    # --- 34 ---
    ("The Go team pinned GOFLAGS to -mod=readonly in CI so a stray go get in a script can never mutate go.mod silently during the build.", "preference", "ai_coding", False,
     [("GOFLAGS", "config"), ("-mod=readonly", "config"), ("go.mod", "file"), ("go get", "command")],
     [],
     "which Go build flag prevents accidental go.mod mutations during CI",
     "goflags mod readonly go get ci mutate go mod build"),
    # --- 35 ---
    ("The engineering handbook cites Semantic Versioning 2.0.0 for what major, minor, and patch mean; breaking changes always bump major, even for unstable 0.x packages internally.", "reference", "ai_coding", False,
     [("Semantic Versioning 2.0.0", "publication"), ("handbook", "file")],
     [],
     "which versioning spec drives the org's major-minor-patch decisions and what's the internal twist",
     "semver 2 0 0 semantic version major minor patch zero unstable"),
    # --- 36 ---
    ("Sigstore's cosign verifies every image pulled by the deploy workflow; tags with missing or untrusted signatures fail the admission step before ever hitting the cluster.", "architecture", "ai_coding", False,
     [("Sigstore", "service"), ("cosign", "tool"), ("admission", "pattern")],
     [],
     "which signing layer gates container pulls into the cluster and where does verification happen",
     "sigstore cosign image signature admission deploy verify"),
    # --- 37 ---
    ("SLSA level 3 provenance is attached to every release via GitHub's slsa-github-generator; consumers can verify the builder identity and the source repo from the attestation.", "milestone", "ai_coding", False,
     [("SLSA", "pattern"), ("slsa-github-generator", "tool"), ("GitHub", "service")],
     [],
     "which supply-chain framework and tool produces provenance attestations for the org's releases",
     "slsa provenance github generator release attest builder identity"),
    # --- 38 ---
    ("The lockfile for the Electron app lives in the root and every workspace package references it via pnpm; electron-builder refuses to ship a binary if the hash doesn't match the committed lock.", "architecture", "ai_coding", False,
     [("Electron", "framework"), ("electron-builder", "tool"), ("pnpm", "tool")],
     [],
     "how does the Electron release pipeline refuse to ship binaries built off an unknown lockfile",
     "electron builder pnpm lockfile hash match binary ship refuse"),
    # --- 39 ---
    ("requirements.in is the source file and pip-compile writes requirements.txt with --generate-hashes; every transitive dep lands with a sha256, making reruns deterministic on any machine.", "architecture", "ai_coding", False,
     [("pip-compile", "tool"), ("requirements.in", "file"), ("requirements.txt", "file"), ("--generate-hashes", "config")],
     [("pip-compile", "requirements.txt", "PRODUCES")],
     "which pip-compile flag produces the hash-pinned lockfile and where does the input live",
     "pip compile requirements in txt generate hashes sha256 transitive"),
    # --- 40 ---
    ("Our published npm tarball excludes tests, benches, and the src directory; files in package.json lists only the dist output so consumers download a fraction of the repo.", "preference", "ai_coding", False,
     [("npm", "tool"), ("package.json", "file"), ("dist", "pattern")],
     [],
     "which package.json setting keeps the published tarball tiny by excluding tests and source",
     "package json files dist exclude test bench src npm tarball"),
    # --- 41 ---
    ("A CODEOWNERS-gated file named DEPENDENCY-UPDATES.md records risky major bumps; every merge that changes a lockfile for a top-20 dependency links to an entry in the log.", "architecture", "ai_coding", False,
     [("CODEOWNERS", "file"), ("DEPENDENCY-UPDATES.md", "file"), ("lockfile", "file")],
     [],
     "which manual audit trail complements the automated lockfile diff for risky major bumps",
     "codeowners dependency updates md lockfile major bump audit log"),
    # --- 42 ---
    ("The snyk CLI is being phased out in favour of Trivy fs scans; Trivy covers both OS and language packages and its json output fits our existing SARIF converter.", "decision", "ai_coding", False,
     [("snyk", "tool"), ("Trivy", "tool"), ("SARIF", "protocol")],
     [("Trivy", "snyk", "REPLACES")],
     "which scanner is replacing snyk across the language pipelines and why the switch",
     "trivy replace snyk fs scan os package language sarif"),
    # --- 43 ---
    ("Bundled dependencies are rejected in review; a lint rule checks for bundleDependencies in package.json so no one can sneak a vendored copy of a library into the tree.", "preference", "ai_coding", False,
     [("bundleDependencies", "config"), ("package.json", "file"), ("lint rule", "pattern")],
     [],
     "which review policy and lint guard keeps vendored bundleDependencies out of the tree",
     "bundle dependencies package json lint vendored library review"),
    # --- 44 ---
    ("Our Go modules use the replace directive sparingly and every instance carries a TODO with a GitHub issue; a CI check flags a replace older than 60 days as a stale pin.", "architecture", "ai_coding", False,
     [("Go modules", "technology"), ("replace", "config"), ("TODO", "pattern")],
     [],
     "which policy keeps Go replace directives from rotting into forever-forks of upstream modules",
     "go module replace directive todo issue ci stale pin days"),
    # --- 45 ---
    ("cargo-edit's cargo upgrade with --incompatible=allow runs weekly on a scheduled branch; the branch opens PRs grouped by workspace member so reviewers can tackle them crate by crate.", "preference", "ai_coding", False,
     [("cargo-edit", "tool"), ("cargo upgrade", "command"), ("--incompatible=allow", "config")],
     [],
     "which Rust tooling automates weekly upgrade PRs and how are they grouped for review",
     "cargo edit upgrade incompatible weekly schedule workspace pr"),
    # --- 46 ---
    ("The deno.lock file got committed two weeks after release; the team had been running tests without it and a transitive dependency on deno-std had quietly bumped twice in a day.", "problem", "ai_coding", False,
     [("deno.lock", "file"), ("deno-std", "library")],
     [],
     "which Deno lockfile gap caused silent transitive drift and how was it closed",
     "deno lock commit transitive std drift test pipeline"),
    # --- 47 ---
    ("npm overrides pin a patched transitive for lodash until upstream ships; a note in README.md points to the CVE and the date we can remove the override.", "architecture", "ai_coding", False,
     [("npm overrides", "config"), ("lodash", "library"), ("README.md", "file"), ("CVE", "pattern")],
     [],
     "which npm feature pinned a patched transitive version of lodash while upstream caught up",
     "npm overrides lodash transitive patch cve readme override"),
    # --- 48 ---
    ("Maven's enforcer plugin bans duplicate classes and snapshot dependencies on release builds; a maven-enforcer-plugin rule called requireReleaseDeps runs in the release profile.", "architecture", "ai_coding", False,
     [("Maven", "tool"), ("enforcer plugin", "tool"), ("requireReleaseDeps", "config")],
     [],
     "which Maven plugin rule stops snapshot dependencies and duplicate classes from landing in releases",
     "maven enforcer plugin require release deps snapshot duplicate"),
    # --- 49. noise ---
    ("Someone swapped the office wall clock for a digital one overnight and no one has admitted to it yet.", "fact", "noise", True, [], [], None, None),
    # --- 50 ---
    ("The .tool-versions file at the repo root is read by asdf and mise alike; the lockfile-level determinism for node, python, and terraform flows out of that one manifest.", "architecture", "ai_coding", False,
     [("asdf", "tool"), ("mise", "tool"), (".tool-versions", "file"), ("terraform", "tool")],
     [],
     "which single manifest pins runtime versions across node, python, and terraform for both asdf and mise",
     "tool versions asdf mise node python terraform pin manifest"),
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
