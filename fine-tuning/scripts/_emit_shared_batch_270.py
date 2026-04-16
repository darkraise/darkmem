"""One-off emitter for shared-base batch-270 — technical domain (software supply-chain security: SBOM formats, SLSA, Sigstore, in-toto, signed package registries, lockfiles, dependency scanners, landmark CVEs).

Writes 50 rows to data/v2/shared/batch_270.tmp.jsonl with ids shared-13451..13500.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_270.tmp.jsonl"
ID_OFFSET = 13450

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1. decision ---
    ("Standardised the release SBOM on CycloneDX 1.6 instead of SPDX 3.0 for the Go services; the VEX attachments and the BOM-Link cross-references map cleaner to our vulnerability feed than SPDX's relationship blocks.", "decision", "technical", False,
     [("CycloneDX", "tool"), ("SPDX 3.0", "tool"), ("VEX", "concept"), ("BOM-Link", "concept")],
     [("CycloneDX", "SPDX 3.0", "PREFERS")],
     "which SBOM format won the release pipeline over SPDX and what cross-reference feature sealed the pick",
     "cyclonedx spdx vex bom link sbom release go service"),
    # --- 2. architecture ---
    ("The build farm emits a CycloneDX JSON SBOM per artifact, a SPDX tag-value SBOM for the downstream enterprise pipeline, and a SWID tag for the Windows installer; all three land in the same artifact bucket keyed by commit hash.", "architecture", "technical", False,
     [("CycloneDX", "tool"), ("SPDX", "tool"), ("SWID", "tool"), ("build farm", "infrastructure"), ("commit hash", "concept")],
     [("build farm", "CycloneDX", "PRODUCES"), ("build farm", "SPDX", "PRODUCES"), ("build farm", "SWID", "PRODUCES")],
     "which three SBOM-style artifacts does the build farm emit per commit and where do they land",
     "cyclonedx spdx swid build farm artifact bucket commit hash"),
    # --- 3. milestone ---
    ("Reached SLSA level 3 on the payments monorepo this quarter: hermetic builds run on isolated runners, provenance is signed end-to-end, and the in-toto attestation chain gets verified before any image hits production.", "milestone", "technical", False,
     [("SLSA", "framework"), ("in-toto", "framework"), ("hermetic builds", "concept"), ("provenance", "concept"), ("payments monorepo", "project")],
     [("SLSA", "in-toto", "USES"), ("payments monorepo", "SLSA", "IMPLEMENTS")],
     "what supply-chain level did the payments repo hit this quarter and which attestation chain gates production",
     "slsa level 3 payments monorepo hermetic provenance in toto attestation"),
    # --- 4. fact ---
    ("Every container image is signed by cosign, and Rekor stores the signature transparency record; Fulcio issues the short-lived signing certificate keyed to the GitHub Actions OIDC identity, so no long-lived keys ever sit on a runner.", "fact", "technical", False,
     [("cosign", "tool"), ("Rekor", "service"), ("Fulcio", "service"), ("GitHub Actions", "platform"), ("OIDC", "protocol")],
     [("cosign", "Rekor", "COMMUNICATES_WITH"), ("cosign", "Fulcio", "USES"), ("Fulcio", "GitHub Actions", "COMMUNICATES_WITH")],
     "how does Sigstore's keyless signing flow tie container image signatures to GitHub Actions identity",
     "cosign rekor fulcio github actions oidc keyless container image"),
    # --- 5. decision ---
    ("Switched the Go release tooling from the upstream cosign CLI to the SigStore client-go library embedded in the releaser binary; one-shot sign-and-upload calls stopped shelling out and the runner image lost half a gigabyte.", "decision", "technical", False,
     [("SigStore client-go", "library"), ("cosign", "tool"), ("releaser binary", "project"), ("runner image", "infrastructure")],
     [("SigStore client-go", "cosign", "REPLACES"), ("releaser binary", "SigStore client-go", "USES")],
     "which Sigstore integration did the Go releaser adopt in place of shelling out to the cosign binary",
     "sigstore client go cosign cli release binary runner image shrink"),
    # --- 6. architecture ---
    ("Commits are signed with gitsign and verified by a server-side hook against Rekor transparency; developers never manage a PGP key, and the CODEOWNERS reviewer check only trusts signatures whose Fulcio identity matches an org allowlist.", "architecture", "technical", False,
     [("gitsign", "tool"), ("Rekor", "service"), ("Fulcio", "service"), ("CODEOWNERS", "concept"), ("org allowlist", "config")],
     [("gitsign", "Rekor", "COMMUNICATES_WITH"), ("gitsign", "Fulcio", "USES")],
     "how does the commit-signing flow trade PGP keys for gitsign and what gates an identity into the CODEOWNERS check",
     "gitsign rekor fulcio codeowners allowlist pgp commit signature"),
    # --- 7. reference ---
    ("The in-toto attestation spec and SLSA provenance v1 schema are vendored under docs/security/attestations/ with the Sigstore bundle format reference kept alongside; any new attestation predicate must link its spec URL next to the example payload.", "reference", "technical", False,
     [("in-toto", "framework"), ("SLSA provenance", "concept"), ("Sigstore bundle", "concept"), ("docs/security/attestations/", "file")],
     [("SLSA provenance", "in-toto", "EXTENDS")],
     "where do the in-toto attestation and SLSA provenance specs live in the repo and what does a new predicate need alongside it",
     "in toto attestation slsa provenance sigstore bundle docs security predicate"),
    # --- 8. problem ---
    ("A dependency-confusion attack slipped past the npm install step: an internal scoped package got shadowed by a public registry upload with a higher semver, and the build pulled the attacker's tarball before the proxy allowlist kicked in.", "problem", "technical", False,
     [("dependency-confusion", "concept"), ("npm", "platform"), ("scoped package", "concept"), ("proxy allowlist", "config"), ("semver", "concept")],
     [("dependency-confusion", "npm", "APPLIES_TO")],
     "which supply-chain attack pattern got past the npm install step and what registry behaviour made the shadow version win",
     "dependency confusion npm scoped package proxy allowlist semver shadow"),
    # --- 9. milestone ---
    ("Cleaned up the Log4Shell CVE-2021-44228 exposure across the Java fleet in a single week: every log4j-core below 2.17.1 got patched, JNDI lookup was disabled with formatMsgNoLookups on the stragglers, and the WAF rule held the line until rollouts finished.", "milestone", "technical", False,
     [("Log4Shell", "concept"), ("CVE-2021-44228", "concept"), ("log4j-core", "library"), ("JNDI", "protocol"), ("formatMsgNoLookups", "config"), ("WAF", "infrastructure")],
     [("formatMsgNoLookups", "JNDI", "FIXES"), ("WAF", "Log4Shell", "FIXES")],
     "how did the Java fleet remediate CVE-2021-44228 and what short-term control covered the stragglers",
     "log4shell cve 2021 44228 log4j jndi formatmsgnolookups waf java"),
    # --- 10. noise ---
    ("The office coffee roaster switched suppliers this month and half the morning standup is spent arguing about whether the new blend is fruitier.", "fact", "noise", True, [], [], None, None),
    # --- 11. fact ---
    ("The xz-utils backdoor landed as CVE-2024-3094 when Jia Tan's multi-year commit trail seeded a sshd bypass through liblzma; distros pulled the 5.6.0 and 5.6.1 releases within hours of Andres Freund's disclosure.", "fact", "technical", False,
     [("xz-utils", "library"), ("CVE-2024-3094", "concept"), ("Jia Tan", "person"), ("liblzma", "library"), ("sshd", "service"), ("Andres Freund", "person")],
     [("Jia Tan", "xz-utils", "AUTHORED_BY"), ("xz-utils", "liblzma", "HAS_PART"), ("CVE-2024-3094", "sshd", "APPLIES_TO")],
     "which maintainer compromised xz-utils and how did the backdoor route into sshd on affected distros",
     "xz utils cve 2024 3094 jia tan liblzma sshd andres freund backdoor"),
    # --- 12. decision ---
    ("After the Codecov bash uploader compromise, the CI pipeline stopped curl-piping any uploader into sh; every coverage and scanner tool now ships as a signed container and a pinned digest is verified before invocation.", "decision", "technical", False,
     [("Codecov", "service"), ("bash uploader", "tool"), ("CI pipeline", "infrastructure"), ("pinned digest", "concept")],
     [("pinned digest", "bash uploader", "REPLACES")],
     "which CI practice did the Codecov incident retire and what replaced the curl-pipe uploader pattern",
     "codecov bash uploader ci pipeline pinned digest signed container curl pipe"),
    # --- 13. reference ---
    ("The SolarWinds Sunburst postmortem sits in docs/security/incidents/solarwinds.md and grounds our build-integrity requirements: hermetic builds, two-person review for release branches, and provenance that the product team can verify without vendor cooperation.", "reference", "technical", False,
     [("SolarWinds", "organization"), ("Sunburst", "concept"), ("docs/security/incidents/solarwinds.md", "file"), ("hermetic builds", "concept"), ("provenance", "concept")],
     [("Sunburst", "SolarWinds", "APPLIES_TO")],
     "where does the SolarWinds Sunburst writeup live and which build-integrity requirements did it crystallise",
     "solarwinds sunburst incident postmortem hermetic build provenance two person"),
    # --- 14. architecture ---
    ("The 3CX incident reshaped our vendor-signed binary policy: every third-party signed desktop binary now runs through an in-house cosign verification step against a pinned Fulcio identity before deployment, regardless of the vendor's own Authenticode chain.", "architecture", "technical", False,
     [("3CX", "organization"), ("cosign", "tool"), ("Fulcio", "service"), ("Authenticode", "protocol"), ("desktop binary", "concept")],
     [("cosign", "Authenticode", "IMPROVES_ON")],
     "which vendor incident drove the extra cosign verification layer on top of Authenticode for desktop binaries",
     "3cx cosign fulcio authenticode desktop binary vendor signed verify"),
    # --- 15. milestone ---
    ("Enabled PyPI Trusted Publishing for the darkmem Python wheels; long-lived API tokens got revoked, and every release pushes via the GitHub Actions OIDC exchange so the registry sees a short-lived credential bound to the workflow run.", "milestone", "technical", False,
     [("PyPI", "platform"), ("Trusted Publishing", "concept"), ("darkmem", "project"), ("GitHub Actions", "platform"), ("OIDC", "protocol")],
     [("darkmem", "Trusted Publishing", "USES"), ("Trusted Publishing", "OIDC", "USES")],
     "how does the darkmem wheel release pipeline authenticate to PyPI after the Trusted Publishing rollout",
     "pypi trusted publishing darkmem github actions oidc wheel api token"),
    # --- 16. decision ---
    ("Picked Sigstore's npm signed attestations over the classic GPG-signed tarball workflow for the internal JS packages; the Rekor-backed transparency is auditable without shipping keyrings to every consumer.", "decision", "technical", False,
     [("Sigstore", "framework"), ("npm signed attestations", "concept"), ("GPG", "protocol"), ("Rekor", "service")],
     [("Sigstore", "GPG", "PREFERS"), ("npm signed attestations", "Rekor", "USES")],
     "which npm signing strategy did Sigstore's attestations replace for the internal JS packages and why",
     "sigstore npm signed attestation gpg tarball rekor transparency keyring"),
    # --- 17. decision ---
    ("Wired the Rust release job to publish crates.io with Sigstore attestations attached rather than the old plain cargo publish; cargo install can now verify a publisher's identity end-to-end against Rekor without trusting an intermediary mirror.", "decision", "technical", False,
     [("crates.io", "platform"), ("Sigstore", "framework"), ("cargo", "tool"), ("Rekor", "service")],
     [("crates.io", "Sigstore", "USES"), ("cargo", "Rekor", "COMMUNICATES_WITH")],
     "how does crates.io let cargo install verify a publisher's identity without relying on a mirror",
     "crates io sigstore cargo install rekor attestation publisher verify"),
    # --- 18. architecture ---
    ("Maven Central's publication flow requires a GPG-signed bundle plus namespace verification against the group id; our release job signs with an in-house key escrowed at the HSM and emits the Sigstore bundle as a parallel attestation.", "architecture", "technical", False,
     [("Maven Central", "platform"), ("GPG", "protocol"), ("HSM", "infrastructure"), ("Sigstore bundle", "concept"), ("namespace verification", "concept")],
     [("Maven Central", "GPG", "USES"), ("Maven Central", "namespace verification", "USES")],
     "how does the Maven Central release path combine the classic GPG signature with a Sigstore bundle",
     "maven central gpg hsm sigstore bundle namespace verification release"),
    # --- 19. preference ---
    ("Prefer pnpm lockfile over package-lock.json for new JavaScript services: the integrity field is keyed by SRI hash per resolved registry URL and the strict default stops a rogue transitive from silently resolving to a different tarball.", "preference", "technical", False,
     [("pnpm", "tool"), ("package-lock.json", "file"), ("SRI", "concept"), ("lockfile", "concept")],
     [("pnpm", "package-lock.json", "PREFERS")],
     "which JavaScript lockfile does the team prefer for new services and which integrity feature drives that pick",
     "pnpm package lock json sri integrity transitive rogue tarball resolve"),
    # --- 20. preference ---
    ("The Rust services commit Cargo.lock even for libraries now; the old convention of skipping it in library crates bit us when a downstream CI picked an unexpected minor bump during an active CVE advisory window.", "preference", "technical", False,
     [("Cargo.lock", "file"), ("Rust", "language"), ("CVE advisory", "concept")],
     [("Cargo.lock", "Rust", "APPLIES_TO")],
     "which Rust lockfile convention changed after a minor-bump incident during an active CVE window",
     "cargo lock rust library crate cve advisory minor bump downstream ci"),
    # --- 21. fact ---
    ("Go projects rely on go.sum for module checksums verified at build time; mismatches fail the build outright and the GOSUMDB default points at sum.golang.org so a rewritten upstream tag gets caught before it lands in the module cache.", "fact", "technical", False,
     [("go.sum", "file"), ("Go", "language"), ("GOSUMDB", "config"), ("sum.golang.org", "service"), ("module cache", "concept")],
     [("go.sum", "Go", "APPLIES_TO"), ("GOSUMDB", "sum.golang.org", "COMMUNICATES_WITH")],
     "which mechanism does Go use to detect a rewritten upstream tag before the module cache accepts it",
     "go sum gosumdb sum golang org module checksum rewritten tag cache"),
    # --- 22. decision ---
    ("Gradle lock files are now required on every JVM service; reproducible resolution lets the SCA job diff the resolved graph between PR and main and flag a new transitive without re-running the full dependency resolution.", "decision", "technical", False,
     [("Gradle lock files", "file"), ("JVM", "platform"), ("SCA", "tool"), ("reproducible resolution", "concept")],
     [("Gradle lock files", "JVM", "APPLIES_TO"), ("SCA", "Gradle lock files", "USES")],
     "which Gradle feature became mandatory and how does it let the SCA job diff transitive changes between PRs",
     "gradle lock file jvm sca reproducible resolution transitive diff"),
    # --- 23. architecture ---
    ("Dependency scanning runs in three layers: pip-audit against the resolved lockfile, Socket.dev on the PR for install-time behaviour heuristics, and Snyk for policy reporting to the security team's dashboard.", "architecture", "technical", False,
     [("pip-audit", "tool"), ("Socket.dev", "service"), ("Snyk", "service"), ("lockfile", "concept")],
     [("pip-audit", "lockfile", "APPLIES_TO")],
     "which three tools make up the layered dependency scanning stack and what does each one cover",
     "pip audit socket dev snyk lockfile dependency scan layered policy"),
    # --- 24. reference ---
    ("The OSV database feeds the in-cluster alerting pipeline: advisories are pulled from osv.dev, normalised against the Go, PyPI, and npm ecosystems, and matched to the SBOMs collected per deployment.", "reference", "technical", False,
     [("OSV", "service"), ("osv.dev", "service"), ("Go", "language"), ("PyPI", "platform"), ("npm", "platform"), ("SBOMs", "concept")],
     [("OSV", "osv.dev", "DEPLOYED_ON"), ("OSV", "SBOMs", "APPLIES_TO")],
     "which vulnerability feed drives the alerting pipeline and which ecosystems does it normalise across",
     "osv osv dev pypi npm go sbom deployment alert advisory"),
    # --- 25. fact ---
    ("GitHub Dependabot opens security update PRs for every repo in the org and groups patches by ecosystem per week; the policy file pins the merge-queue labels so a passing Dependabot PR auto-rolls into main without a human click.", "fact", "technical", False,
     [("GitHub Dependabot", "service"), ("merge-queue", "concept"), ("policy file", "file"), ("ecosystem", "concept")],
     [("GitHub Dependabot", "merge-queue", "USES")],
     "how does the org's Dependabot policy group patches and what enables auto-merge on a passing security PR",
     "github dependabot security update pr merge queue ecosystem group policy"),
    # --- 26. preference ---
    ("Prefer Renovate over Dependabot on the polyglot monorepo because its single config handles npm, pip, Gradle, and Terraform with shared version groups; Dependabot's per-ecosystem config file split was getting unwieldy.", "preference", "technical", False,
     [("Renovate", "tool"), ("Dependabot", "service"), ("npm", "platform"), ("pip", "tool"), ("Gradle", "tool"), ("Terraform", "tool")],
     [("Renovate", "Dependabot", "PREFERS")],
     "which dependency update bot does the monorepo prefer over Dependabot and which capability drives the choice",
     "renovate dependabot monorepo npm pip gradle terraform version group"),
    # --- 27. milestone ---
    ("All critical repos hit an OpenSSF Scorecard score above 8 this quarter; the branch-protection, signed-releases, and pinned-dependencies checks were the last three to flip green after the release workflow refactor.", "milestone", "technical", False,
     [("OpenSSF Scorecard", "tool"), ("branch-protection", "concept"), ("signed-releases", "concept"), ("pinned-dependencies", "concept")],
     [("OpenSSF Scorecard", "branch-protection", "USES"), ("OpenSSF Scorecard", "signed-releases", "USES")],
     "which OpenSSF Scorecard checks were the last to flip green and what threshold did the critical repos clear",
     "openssf scorecard branch protection signed release pinned dependency critical"),
    # --- 28. reference ---
    ("CNCF TAG Security's supply-chain paper anchors the internal policy doc: the four categories of source, materials, build, and artifact map directly onto the SLSA levels we gate production on.", "reference", "technical", False,
     [("CNCF TAG Security", "organization"), ("SLSA", "framework"), ("source", "concept"), ("materials", "concept"), ("build", "concept"), ("artifact", "concept")],
     [("CNCF TAG Security", "SLSA", "SUPPORTS")],
     "which CNCF TAG Security paper grounds the internal supply-chain policy and how do its categories map to SLSA levels",
     "cncf tag security supply chain paper source materials build artifact slsa"),
    # --- 29. fact ---
    ("The 2017 Equifax breach traced to an unpatched Apache Struts instance exploited through CVE-2017-5638; the postmortem anchors our quarterly framework-inventory audit and the ninety-six hour SLA on critical framework CVEs.", "fact", "technical", False,
     [("Equifax", "organization"), ("Apache Struts", "framework"), ("CVE-2017-5638", "concept"), ("2017", "date")],
     [("CVE-2017-5638", "Apache Struts", "APPLIES_TO")],
     "which 2017 breach anchors the framework-inventory audit and which Struts CVE drove the ninety-six hour SLA",
     "equifax apache struts cve 2017 5638 breach framework inventory audit sla"),
    # --- 30. architecture ---
    ("The release pipeline produces an in-toto attestation per stage — source, build, test, package — chained so the cosign verifier rejects an artifact whose predicate chain doesn't cover all four, not just the final package step.", "architecture", "technical", False,
     [("in-toto", "framework"), ("cosign", "tool"), ("predicate chain", "concept"), ("release pipeline", "infrastructure")],
     [("in-toto", "release pipeline", "APPLIES_TO"), ("cosign", "in-toto", "USES")],
     "how does the release pipeline use in-toto attestations per stage and what does cosign reject at verification",
     "in toto attestation source build test package cosign predicate chain"),
    # --- 31. decision ---
    ("Chose Sigstore bundles as the canonical envelope for attestations flowing between services; the self-contained bundle carries the signature, the certificate, and the Rekor inclusion proof so verifiers never need an online round-trip mid-request.", "decision", "technical", False,
     [("Sigstore bundle", "concept"), ("Rekor", "service"), ("inclusion proof", "concept"), ("certificate", "concept")],
     [("Sigstore bundle", "Rekor", "USES")],
     "which attestation envelope did the team standardise on and which property removed the online verification round-trip",
     "sigstore bundle rekor inclusion proof certificate envelope offline verify"),
    # --- 32. problem ---
    ("A typosquat package named reqeusts slipped into a developer's local pip install; the cached wheel made it into a demo image before the Socket.dev alert fired, and a private registry mirror is now mandatory for the same reason.", "problem", "technical", False,
     [("typosquat", "concept"), ("reqeusts", "library"), ("pip", "tool"), ("Socket.dev", "service"), ("private registry mirror", "infrastructure")],
     [("Socket.dev", "typosquat", "APPLIES_TO"), ("private registry mirror", "typosquat", "FIXES")],
     "which typosquat package made it into a demo image and what control got mandated afterwards",
     "typosquat reqeusts pip socket dev private registry mirror demo wheel"),
    # --- 33. milestone ---
    ("Rolled out SLSA provenance v1 across every container produced by the platform team; the provenance blob records the build config digest, the materials list, and the runner identity, and the admission controller enforces a non-empty materials list.", "milestone", "technical", False,
     [("SLSA provenance", "concept"), ("container", "concept"), ("admission controller", "service"), ("materials list", "concept"), ("runner identity", "concept")],
     [("admission controller", "SLSA provenance", "USES")],
     "which provenance schema did the platform team roll out and what does the admission controller check on entry",
     "slsa provenance v1 container admission controller materials runner identity"),
    # --- 34. decision ---
    ("Selected cosign over notation for container image signing because the Sigstore ecosystem gave us Rekor transparency without running a dedicated trust store; notation's OCI-native model was cleaner but the operational burden wasn't justified at our scale.", "decision", "technical", False,
     [("cosign", "tool"), ("notation", "tool"), ("Sigstore", "framework"), ("Rekor", "service"), ("OCI", "protocol")],
     [("cosign", "notation", "PREFERS"), ("cosign", "Sigstore", "USES")],
     "which image-signing tool won over notation and which Sigstore component removed an operational burden",
     "cosign notation sigstore rekor oci container image signing trust store"),
    # --- 35. architecture ---
    ("Attestation verification is split across a Kyverno policy at admission time and an offline batch audit job; the admission path enforces the cosign signature and the audit job cross-references Rekor entries against the SBOM inventory nightly.", "architecture", "technical", False,
     [("Kyverno", "tool"), ("cosign", "tool"), ("Rekor", "service"), ("SBOM inventory", "concept"), ("admission", "concept")],
     [("Kyverno", "cosign", "USES"), ("Kyverno", "admission", "IMPLEMENTS")],
     "how is attestation verification split between admission-time enforcement and offline audit in the cluster",
     "kyverno cosign rekor sbom inventory admission offline audit signature"),
    # --- 36. fact ---
    ("The SigStore client-go library exposes a Verifier type that checks both the certificate chain against Fulcio roots and the Rekor inclusion proof in one call, which is what the admission webhook uses per incoming image.", "fact", "technical", False,
     [("SigStore client-go", "library"), ("Verifier", "api"), ("Fulcio", "service"), ("Rekor", "service"), ("admission webhook", "service")],
     [("admission webhook", "SigStore client-go", "USES"), ("Verifier", "Fulcio", "USES"), ("Verifier", "Rekor", "USES")],
     "which Sigstore library call does the admission webhook use to verify certificate chain and transparency proof together",
     "sigstore client go verifier fulcio rekor admission webhook inclusion"),
    # --- 37. decision ---
    ("Banned curl-pipe installs from every Dockerfile in the org; base images now copy pinned binaries from a verified internal mirror, and the Dockerfile linter rejects a RUN curl … | sh pattern outright during CI.", "decision", "technical", False,
     [("Dockerfile", "file"), ("curl-pipe", "concept"), ("Dockerfile linter", "tool"), ("internal mirror", "infrastructure")],
     [("Dockerfile linter", "curl-pipe", "FIXES")],
     "which install pattern did the Dockerfile linter ban and what replaces it for base-image binaries",
     "dockerfile curl pipe linter internal mirror pinned binary base image"),
    # --- 38. decision ---
    ("Swapped safety for pip-audit across the Python CI because the OSV backend catches advisories across PyPI and GitHub Security Advisory sources, and the exit-code-based gating plugs straight into the existing test stage.", "decision", "technical", False,
     [("pip-audit", "tool"), ("safety", "tool"), ("OSV", "service"), ("PyPI", "platform"), ("GitHub Security Advisory", "service")],
     [("pip-audit", "safety", "REPLACES"), ("pip-audit", "OSV", "USES")],
     "which Python scanner replaced safety on CI and which advisory sources does its backend cover",
     "pip audit safety osv pypi github security advisory ci exit code"),
    # --- 39. architecture ---
    ("The signed-artifact path is keyless end-to-end: gitsign on the commit, Sigstore on the build, cosign on the image, and a final in-toto attestation binding the release tag to the commit SHA and the Fulcio identity that produced it.", "architecture", "technical", False,
     [("gitsign", "tool"), ("Sigstore", "framework"), ("cosign", "tool"), ("in-toto", "framework"), ("Fulcio", "service"), ("release tag", "concept")],
     [("in-toto", "Fulcio", "USES"), ("in-toto", "release tag", "APPLIES_TO"), ("cosign", "Sigstore", "USES")],
     "how does the keyless signing chain flow from commit to release tag across gitsign, Sigstore, cosign, and in-toto",
     "gitsign sigstore cosign in toto fulcio release tag keyless commit sha"),
    # --- 40. reference ---
    ("The dependency-policy reference under docs/security/dependency-policy.md enumerates the lockfile-per-language matrix: package-lock.json or pnpm lockfile for npm, Cargo.lock for Rust, go.sum for Go, Gradle lock files for JVM, and poetry.lock for Python.", "reference", "technical", False,
     [("docs/security/dependency-policy.md", "file"), ("package-lock.json", "file"), ("pnpm", "tool"), ("Cargo.lock", "file"), ("go.sum", "file"), ("Gradle lock files", "file"), ("poetry.lock", "file")],
     [],
     "where does the lockfile-per-language matrix live in the repo and which files cover each ecosystem",
     "dependency policy lockfile matrix package lock pnpm cargo go sum gradle poetry"),
    # --- 41. milestone ---
    ("Hit 100 percent SBOM coverage for production images this quarter; every container pushed to the registry carries an attached CycloneDX document indexed by digest, and the inventory service can answer which deployments ship a given CVE within minutes.", "milestone", "technical", False,
     [("SBOM", "concept"), ("CycloneDX", "tool"), ("registry", "service"), ("inventory service", "service"), ("CVE", "concept")],
     [("registry", "CycloneDX", "PRODUCES"), ("inventory service", "CVE", "APPLIES_TO")],
     "which SBOM coverage milestone did production hit and how fast can the inventory service answer a CVE exposure query",
     "sbom coverage production cyclonedx registry inventory cve deployment digest"),
    # --- 42. problem ---
    ("The Log4Shell aftermath exposed a gap in our log4j-core version inventory; an internal fork buried in a legacy WAR file wasn't tracked until someone grepped the artifact server, so the SBOM generator now unpacks JARs recursively.", "problem", "technical", False,
     [("Log4Shell", "concept"), ("log4j-core", "library"), ("SBOM generator", "tool"), ("WAR file", "file"), ("JAR", "file")],
     [("SBOM generator", "JAR", "APPLIES_TO"), ("SBOM generator", "Log4Shell", "FIXES")],
     "which gap did the Log4Shell cleanup expose in the SBOM generator and what does it do now with nested archives",
     "log4shell log4j core sbom generator war jar recursive unpack inventory"),
    # --- 43. noise ---
    ("The stand-up retro this week voted to retire the word synergy from any recorded meeting note on pain of buying the team coffee for a week.", "fact", "noise", True, [], [], None, None),
    # --- 44. decision ---
    ("Made SBOM emission part of the build contract, not a post-build scan; the build tool writes the CycloneDX document from the resolved dependency graph at compile time, which beats re-scanning the shipped artifact and missing build-only dependencies.", "decision", "technical", False,
     [("CycloneDX", "tool"), ("build contract", "concept"), ("post-build scan", "concept"), ("dependency graph", "concept")],
     [("build contract", "post-build scan", "REPLACES")],
     "which stage of the build does SBOM emission happen at now and what class of dependency would a post-build scan miss",
     "sbom cyclonedx build contract post build scan dependency graph compile"),
    # --- 45. architecture ---
    ("The release attestations graph stores every in-toto predicate the pipeline emits and links them with HAS_PART edges to the release tag node; a single Cypher query returns the full provenance chain for any shipped artifact.", "architecture", "technical", False,
     [("in-toto", "framework"), ("release tag", "concept"), ("Cypher", "language"), ("provenance chain", "concept"), ("attestations graph", "database")],
     [("attestations graph", "in-toto", "USES")],
     "which graph query returns the full provenance chain for a shipped artifact and how are predicates linked to the release tag",
     "attestations graph in toto release tag cypher provenance chain has part"),
    # --- 46. fact ---
    ("Sigstore's Fulcio instance issues certificates with a ten-minute validity window tied to the OIDC identity it receives, which is why the runner must sign and upload to Rekor in the same job rather than deferring to a later pipeline stage.", "fact", "technical", False,
     [("Fulcio", "service"), ("OIDC", "protocol"), ("Rekor", "service"), ("ten-minute validity", "config"), ("runner", "infrastructure")],
     [("Fulcio", "OIDC", "USES"), ("runner", "Rekor", "COMMUNICATES_WITH")],
     "why does the runner need to sign and upload to Rekor within the same job given Fulcio's certificate lifetime",
     "fulcio oidc rekor ten minute validity certificate runner job same"),
    # --- 47. preference ---
    ("Prefer the OSV schema over vendor-specific advisory JSON when piping scan results into the SIEM; the ecosystem-plus-package-plus-range tuple normalises across pip-audit, Trivy, and Grype without per-tool adapters.", "preference", "technical", False,
     [("OSV", "service"), ("SIEM", "infrastructure"), ("pip-audit", "tool"), ("Trivy", "tool"), ("Grype", "tool")],
     [("SIEM", "OSV", "USES")],
     "which advisory schema does the SIEM ingest prefer and which scanners does it normalise without adapters",
     "osv siem pip audit trivy grype advisory schema vendor ecosystem package"),
    # --- 48. reference ---
    ("CNCF TAG Security's catalog of supply-chain attack patterns — from typosquats to dependency confusion to build-system compromise — gets cited as the shared vocabulary when the incident-response team triages a new supplier-side alert.", "reference", "technical", False,
     [("CNCF TAG Security", "organization"), ("typosquat", "concept"), ("dependency confusion", "concept"), ("build-system compromise", "concept"), ("incident-response team", "organization")],
     [("incident-response team", "CNCF TAG Security", "USES")],
     "which CNCF TAG Security catalog grounds the incident-response team's vocabulary for supplier-side alerts",
     "cncf tag security attack pattern typosquat dependency confusion build system"),
    # --- 49. decision ---
    ("Decided the xz-utils backdoor postmortem would not result in banning all single-maintainer upstreams; instead we scored maintainer activity with OpenSSF Scorecard and invested in a build-reproducibility pilot so a malicious commit would surface as a binary diff.", "decision", "technical", False,
     [("xz-utils", "library"), ("OpenSSF Scorecard", "tool"), ("build-reproducibility", "concept"), ("binary diff", "concept")],
     [("OpenSSF Scorecard", "xz-utils", "APPLIES_TO"), ("build-reproducibility", "xz-utils", "FIXES")],
     "which two controls replaced a blanket single-maintainer ban after the xz-utils postmortem",
     "xz utils openssf scorecard build reproducibility binary diff maintainer ban"),
    # --- 50. milestone ---
    ("Closed the signed-provenance loop for the darkmem release: the GitHub Actions workflow produces an SLSA provenance attestation, cosign signs it against Fulcio, Rekor stores it, and the install script verifies the bundle offline before extracting the wheel.", "milestone", "technical", False,
     [("darkmem", "project"), ("GitHub Actions", "platform"), ("SLSA provenance", "concept"), ("cosign", "tool"), ("Fulcio", "service"), ("Rekor", "service"), ("install script", "tool")],
     [("cosign", "SLSA provenance", "PRODUCES"), ("install script", "cosign", "USES"), ("darkmem", "GitHub Actions", "DEPLOYED_ON")],
     "how does the darkmem release close the signed-provenance loop from build through local install verification",
     "darkmem github actions slsa provenance cosign fulcio rekor install script"),
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
