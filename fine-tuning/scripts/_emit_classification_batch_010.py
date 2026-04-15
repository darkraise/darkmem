"""One-off emitter for classification top-up batch-010 — contrastive decision/architecture, security slice.

Same pattern as _emit_shared_batch_006.py, but targets the classification top-up schema
({id, domain, text, memory_type, pair_id}) and emits 50 pairs (100 rows).

Each pair contrasts:
  - one `decision` row about a security/auth choice made (why we switched/adopted),
  - one `architecture` row describing the ongoing security structure on the same topic.

Ids: class-00901..class-01000 (ID_OFFSET = 900).
Pair ids: cls-pair-00451..cls-pair-00500 (PAIR_OFFSET = 450).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_010.tmp.jsonl"
ID_OFFSET = 900
PAIR_OFFSET = 450

# Each pair: (topic_label, domain, decision_text, architecture_text)
# Distinct security topics covered (>=20):
#   auth protocols, key management, certificate lifecycle, secrets storage,
#   network policy, WAF rules, IDS/IPS, audit logging, access control, zero-trust,
#   device attestation, code signing, supply chain, vulnerability scanning,
#   incident response, data-protection at rest, data-protection in transit,
#   session management, identity federation, password hashing, DDoS mitigation,
#   container image security, DNS security, API gateway auth, service-to-service auth,
#   database access control, email security, backup encryption, mobile app hardening,
#   firewall policy.
PAIRS: list[tuple[str, str, str, str]] = [
    # 1. auth protocols — long-lived API keys → short-lived JWTs
    (
        "auth_protocols", "technical",
        "Moved from long-lived API keys to short-lived JWTs after the 2026-01 key leak forced a fleet-wide rotation.",
        "Every service accepts only RS256-signed JWTs with a 10-minute TTL; signing keys rotate nightly from the step-ca issuer.",
    ),
    # 2. key management — hand-rolled KMS → HashiCorp Vault Transit
    (
        "key_management", "technical",
        "Retired the hand-rolled KMS wrapper in favour of Vault Transit; custody and audit requirements outgrew the in-house code.",
        "Vault Transit holds every application data key behind AppRole auth; services call encrypt/decrypt endpoints and never see raw key material.",
    ),
    # 3. certificate lifecycle — manual Let's Encrypt → cert-manager
    (
        "certificate_lifecycle", "technical",
        "Switched from manual Let's Encrypt renewals to cert-manager after a missed renewal caused a 40-minute outage in February.",
        "cert-manager reconciles Certificate CRs in every namespace, renews 30 days before expiry, and mounts the result as a TLS secret on each pod.",
    ),
    # 4. secrets storage — env vars in CI → Vault dynamic credentials
    (
        "secrets_storage", "technical",
        "Dropped plaintext secrets in CI environment variables and adopted Vault dynamic database credentials after a log leak exposed a static password.",
        "CI jobs pull ephemeral database roles from Vault at runtime with a 15-minute TTL; static credentials are banned by a repo-level policy check.",
    ),
    # 5. network policy — flat VPC → Cilium network policies
    (
        "network_policy", "technical",
        "Abandoned the flat production VPC and rolled out Cilium network policies after a compromised pod reached the billing subnet laterally.",
        "Cilium enforces default-deny egress in every namespace; allowed flows are declared per service via CiliumNetworkPolicy and tested in CI.",
    ),
    # 6. WAF rules — AWS managed ruleset → Coraza with OWASP CRS
    (
        "waf_rules", "technical",
        "Replaced the AWS managed WAF ruleset with Coraza running the OWASP Core Rule Set; we needed tunable anomaly thresholds the managed one did not expose.",
        "Coraza sits in front of the ingress gateway with CRS 4.0 in blocking mode above an anomaly score of 10; matched requests are tagged and streamed to Loki.",
    ),
    # 7. IDS/IPS — Snort → Suricata
    (
        "ids_ips", "technical",
        "Migrated the perimeter IDS from Snort to Suricata after the Snort rule feed stopped covering our TLS 1.3 traffic patterns.",
        "Suricata runs inline on the north-south edge, consumes the ET Pro ruleset, and drops traffic that matches the `dropable` tag; events go to Elastic.",
    ),
    # 8. audit logging — application logs → dedicated immutable store
    (
        "audit_logging", "technical",
        "Split security audit events out of the generic log pipeline after auditors flagged that we could mutate them post-hoc.",
        "Security audit events ship to an append-only Loki tenant with object-lock retention of 7 years; the write role cannot delete or overwrite.",
    ),
    # 9. access control — role hierarchies → attribute-based policies
    (
        "access_control", "ai_coding",
        "Dropped the nested role hierarchy we had in the admin app and moved to OPA-based attribute checks; the role tree had become impossible to reason about.",
        "The admin backend calls an OPA sidecar on every request; policies are rego files in git, tested with opa test, and evaluated against user attributes plus resource tags.",
    ),
    # 10. zero-trust — VPN-only → identity-aware proxy
    (
        "zero_trust", "technical",
        "Retired the corporate VPN for internal tooling after a stolen laptop exposed the shared CIDR; went with an identity-aware proxy instead.",
        "All internal web tools sit behind Pomerium; device posture and SSO identity are evaluated per request and the underlying services only accept traffic from the proxy's mTLS cert.",
    ),
    # 11. device attestation — manual device allowlist → TPM attestation
    (
        "device_attestation", "technical",
        "Replaced the manual device allowlist with TPM-based attestation; operators were sharing device certificates and we could not tell which laptop signed what.",
        "Every workstation enrolls its TPM EK into smallstep; access tokens are only minted after a fresh attestation quote signs a recent nonce from the issuer.",
    ),
    # 12. code signing — unsigned internal binaries → Sigstore cosign
    (
        "code_signing", "technical",
        "Started signing every internal binary with cosign after a build-server compromise shipped a backdoored CLI to staging.",
        "Release pipelines sign artifacts with keyless cosign using the OIDC token of the GitHub Actions job; verification runs as an admission controller on every cluster.",
    ),
    # 13. supply chain — pinned versions only → SLSA level 3 provenance
    (
        "supply_chain", "technical",
        "Version pinning was not enough after the event-stream incident, so we adopted SLSA level 3 provenance for every first-party and vendored dependency.",
        "Build provenance is emitted by the Tekton chain, stored in Rekor, and verified at deploy time; images without a matching in-toto attestation are rejected by the admission webhook.",
    ),
    # 14. vulnerability scanning — nightly Trivy → inline + nightly
    (
        "vulnerability_scanning", "technical",
        "Nightly-only Trivy scans let a critical CVE sit in production for 14 hours, so we added inline scanning on every push.",
        "Trivy runs in the PR pipeline against the built image and again as a nightly sweep against every running workload; criticals block the merge and page the on-call.",
    ),
    # 15. incident response — ad-hoc chat threads → formal runbooks in PagerDuty
    (
        "incident_response", "technical",
        "Adopted PagerDuty incident workflows after the December outage ran for two hours with nobody declaring commander.",
        "Every severity-1 page opens a PagerDuty incident channel, assigns a commander from the on-call rotation, and links the standard security-incident runbook automatically.",
    ),
    # 16. data-protection at rest — LUKS on hosts → envelope encryption at app layer
    (
        "data_at_rest", "technical",
        "Host-level LUKS was not enough to satisfy the new PII contract, so we moved to application-layer envelope encryption for customer records.",
        "Each customer record is encrypted with a per-tenant data key; data keys are wrapped by a Vault Transit master key and stored alongside the ciphertext in Postgres.",
    ),
    # 17. data-protection in transit — opportunistic TLS → mandatory mTLS everywhere
    (
        "data_in_transit", "technical",
        "Moved from opportunistic TLS to mandatory mTLS on every east-west hop after packet captures showed a test service still speaking plaintext in prod.",
        "Istio sidecars enforce strict mTLS on every pod-to-pod connection; the mesh refuses plaintext and certificates come from a short-lived SPIFFE issuer.",
    ),
    # 18. session management — server-side sessions with long TTL → short-TTL refresh rotation
    (
        "session_management", "technical",
        "Long-lived server sessions were causing replay problems after stolen cookies, so we moved to short access tokens with rotating refresh.",
        "Web clients hold a 10-minute access token and a 24-hour refresh token; the refresh endpoint rotates both on every call and revokes the family on reuse detection.",
    ),
    # 19. identity federation — local accounts → Okta SSO
    (
        "identity_federation", "technical",
        "Killed the local admin account table in favour of Okta SSO after we found three shared logins still in use six months after onboarding Okta.",
        "All internal tools authenticate against Okta via OIDC; group claims drive role mapping and the local account path is disabled at the application level.",
    ),
    # 20. password hashing — bcrypt cost 10 → argon2id
    (
        "password_hashing", "technical",
        "Upgraded the password hash from bcrypt at cost 10 to argon2id after the 2026-Q1 GPU cracking benchmark showed bcrypt falling behind.",
        "Argon2id runs with m=64MB, t=3, p=4 inside the auth service; hashes are versioned and re-computed on successful login for users still on the old bcrypt scheme.",
    ),
    # 21. DDoS mitigation — in-house rate limiter → Cloudflare Magic Transit
    (
        "ddos_mitigation", "technical",
        "The in-house rate limiter collapsed under a 300 Gbps SYN flood in November, so we moved edge DDoS defence to Cloudflare Magic Transit.",
        "Cloudflare Magic Transit announces our /24 and scrubs traffic before forwarding over GRE to the origin routers; the in-house limiter now only handles layer 7 quotas.",
    ),
    # 22. container image security — distroless + no root → distroless + read-only rootfs + seccomp
    (
        "container_hardening", "technical",
        "Distroless images alone were not enough after a container escape attempt via /tmp, so we tightened the runtime profile as well.",
        "Production pods run as non-root with a read-only root filesystem, drop every Linux capability, and use the `runtime/default` seccomp profile enforced by Kyverno.",
    ),
    # 23. DNS security — plain DNS → DNS over TLS + DNSSEC validation
    (
        "dns_security", "technical",
        "Plain UDP DNS inside the VPC exposed us to cache poisoning scenarios, so we switched to DoT with DNSSEC validation on the resolver tier.",
        "Unbound resolvers in every region do DNSSEC validation and forward upstream over DoT to 1.1.1.1; workloads hit the resolvers over an internal Anycast VIP.",
    ),
    # 24. API gateway auth — shared bearer tokens → OAuth 2.1 with audience binding
    (
        "api_gateway_auth", "technical",
        "The shared-bearer pattern at the API gateway let one partner's leaked token hit other tenants, so we moved to OAuth 2.1 with audience binding.",
        "Kong at the edge validates the JWT signature, checks the `aud` claim against the matched route, and injects a per-tenant identity header that downstream services trust only from the gateway's mTLS peer.",
    ),
    # 25. service-to-service auth — static service tokens → SPIFFE/SPIRE identities
    (
        "service_identity", "technical",
        "Dropped static service account tokens after one leaked in a core dump; SPIFFE gave us short-lived, workload-bound identities instead.",
        "SPIRE agents attest each workload via the Kubernetes PSAT selector and issue SVIDs with a 1-hour TTL; gRPC servers authenticate peers by SPIFFE ID, not token.",
    ),
    # 26. database access control — shared app user → per-request dynamic roles
    (
        "db_access_control", "technical",
        "The shared `app` Postgres role made postmortems impossible, so we moved to Vault-issued per-request database roles.",
        "Every request path opens a Postgres connection with a Vault-issued role scoped to the tenant and lifecycle; role grants are generated from the OPA policy bundle at deploy time.",
    ),
    # 27. email security — SPF only → SPF + DKIM + DMARC reject
    (
        "email_security", "technical",
        "SPF alone kept letting lookalike domains through, so we added DKIM signing and pushed DMARC to p=reject after a full quarter on quarantine.",
        "Outbound mail is signed with a rotating 2048-bit DKIM key per brand domain; DMARC is published at p=reject with aggregate reports piped into a weekly review dashboard.",
    ),
    # 28. backup encryption — cleartext restic repos → age-encrypted restic with offline key
    (
        "backup_encryption", "technical",
        "Cleartext restic repositories on S3 scared the new CISO, so we wrapped every backup with age and kept the key offline.",
        "Backups are written to an S3 bucket with object-lock; restic chunks are encrypted with age using a recipient key whose private half lives only on two offline YubiKeys in the safe.",
    ),
    # 29. mobile app hardening — debuggable builds in prod stores → certificate pinning + attestation
    (
        "mobile_hardening", "ai_coding",
        "The iOS team stopped shipping debuggable builds and added Play Integrity / App Attest checks after a reverse-engineered APK hit a test forum.",
        "Release builds pin the API certificate, require a valid App Attest or Play Integrity token on every sensitive call, and refuse to run under a debugger in production flavour.",
    ),
    # 30. firewall policy — allow-by-default egress → default-deny egress with allow-list
    (
        "firewall_egress", "technical",
        "The 2025 crypto-miner incident got in through an allow-by-default egress rule, so we flipped production to default-deny with an explicit allow-list.",
        "Calico GlobalNetworkPolicies deny all egress in production by default; required destinations are declared per workload and reviewed quarterly against traffic logs.",
    ),
    # 31. passwordless — TOTP 2FA → WebAuthn-only for admins
    (
        "passwordless_auth", "technical",
        "Admin TOTP was phished twice in six months, so we went passwordless with WebAuthn for anyone with production access.",
        "Admin logins require a WebAuthn assertion from a resident key on a FIDO2 authenticator; password and TOTP paths are disabled for users in the `admins` group at the IdP.",
    ),
    # 32. container registry — public Docker Hub pulls → internal proxy with signature verification
    (
        "registry_policy", "technical",
        "Pulling base images directly from Docker Hub bit us during a rate-limit outage and again with a typosquatted tag, so we routed everything through an internal Harbor proxy.",
        "Harbor proxies Docker Hub and GHCR with on-pull Trivy scanning and cosign signature verification; the cluster's containerd only trusts `registry.corp/*` and refuses other registries.",
    ),
    # 33. web app CSP — unsafe-inline everywhere → nonce-based CSP level 3
    (
        "content_security_policy", "ai_coding",
        "The legacy `unsafe-inline` CSP let a reflected XSS reach session cookies, so we moved the web app to a strict nonce-based policy.",
        "Every HTML response sets a CSP with `script-src 'self' 'nonce-<per-request>'` and `strict-dynamic`; violations stream to a report-uri endpoint that alerts on novel hashes.",
    ),
    # 34. SSH — long-lived SSH keys → short-lived SSH certificates
    (
        "ssh_access", "technical",
        "Long-lived SSH keys kept showing up on ex-employee laptops, so we cut over to short-lived SSH certificates signed by Teleport.",
        "Teleport's CA signs SSH certificates valid for 8 hours after SSO + MFA; servers trust only the Teleport CA and the `authorized_keys` path is disabled in sshd_config.",
    ),
    # 35. log redaction — manual grep sweeps → structured redaction at the logger
    (
        "log_redaction", "ai_coding",
        "Post-hoc grep sweeps kept missing leaked PII, so we moved redaction up to the logger itself before anything hits disk.",
        "The shared logging wrapper runs a redaction pass on every record using typed field tags; fields marked `sensitive` are hashed with a rotating salt before the log line is serialised.",
    ),
    # 36. admin plane isolation — shared cluster → dedicated management cluster
    (
        "admin_plane_isolation", "technical",
        "Running the admin plane next to workloads meant one compromised node could reach the CI controller, so we split it onto a dedicated management cluster.",
        "Admin tools (ArgoCD, Vault, Teleport) run on a separate hardened cluster reachable only via the identity-aware proxy; workload clusters pull from the admin cluster and never push.",
    ),
    # 37. third-party access — permanent vendor VPN → just-in-time brokered access
    (
        "third_party_access", "technical",
        "Permanent vendor VPN accounts kept outliving their support engagements, so we moved third-party access to a just-in-time broker.",
        "Vendors request time-boxed access through the access broker; on approval, Teleport issues a 4-hour certificate scoped to the specific host and role, and the session is recorded.",
    ),
    # 38. dependency review — manual pull request reading → automated license + vuln gating
    (
        "dependency_review", "ai_coding",
        "Manual PR review for new dependencies missed a GPL library and a known-vulnerable transitive, so we gated it on automated checks.",
        "Every PR that changes a lockfile runs a dependency-review job that fails on GPL/AGPL imports and on advisories above High severity; overrides require a `security-approved` label from the platform team.",
    ),
    # 39. secrets scanning — pre-commit only → pre-commit + server-side + history sweep
    (
        "secrets_scanning", "technical",
        "Pre-commit secret scanning missed commits from contractors without the hook installed, so we added server-side scanning and a weekly history sweep.",
        "gitleaks runs as a pre-receive hook on the Gitea server and as a nightly full-history sweep; detected secrets auto-open a revocation ticket and block the push.",
    ),
    # 40. cloud IAM — long-lived IAM user keys → OIDC federation from GitHub Actions
    (
        "cloud_iam", "technical",
        "Rotated out the last long-lived AWS IAM user keys after one leaked via a screenshare; switched CI to OIDC federation instead.",
        "GitHub Actions assumes an AWS role via OIDC with a trust policy bound to the specific repo, branch and environment; the role's session is 1 hour and scoped to a single account.",
    ),
    # 41. service account permissions — wildcard IAM → permissions boundaries per service
    (
        "least_privilege_iam", "technical",
        "Wildcard `*:*` policies on legacy services kept surviving reviews, so we enforced permissions boundaries on every role.",
        "Every IAM role in production is attached to a permissions boundary generated from the service's declared needs; Terraform refuses to plan a role without a matching boundary file.",
    ),
    # 42. build environment — shared runners → ephemeral per-job runners
    (
        "ci_isolation", "technical",
        "Shared self-hosted runners leaked caches between jobs; a poisoned cache hit the auth service build, so we moved to ephemeral per-job runners.",
        "Each GitHub Actions job spawns a fresh Firecracker microVM via the runner controller; the VM is destroyed at job end and secrets are mounted via short-lived Vault tokens.",
    ),
    # 43. webhook verification — shared secret check in handler → signature verification middleware
    (
        "webhook_verification", "ai_coding",
        "An engineer forgot the shared-secret check in a new webhook handler, so we moved verification into a middleware that every handler must pass through.",
        "Inbound webhooks hit a single router that validates the HMAC signature and timestamp window before dispatching to the typed handler; handlers cannot be registered without declaring an allowed signer.",
    ),
    # 44. OS patching — monthly manual window → continuous automated patching with canary
    (
        "os_patching", "technical",
        "A 30-day manual patch cycle left hosts exposed to a kernel CVE for three weeks, so we moved to continuous automated patching with a canary ring.",
        "Kured drains and reboots nodes within 24 hours of a new kernel package; patches roll through canary, staging and production rings with health gates between each step.",
    ),
    # 45. privileged session — always-on root access → brokered break-glass sessions
    (
        "break_glass", "technical",
        "Always-on root access for SRE made SOC 2 reviewers unhappy and caused one real incident, so we introduced a brokered break-glass flow.",
        "Break-glass elevation is requested via the access broker, requires a peer approval in Slack, issues a 60-minute certificate tied to a ticket, and streams the session to an immutable recording bucket.",
    ),
    # 46. cookie security — Lax cookies with long life → Strict + short life + __Host- prefix
    (
        "cookie_security", "ai_coding",
        "SameSite=Lax plus a two-week session cookie let a CSRF variant through in staging, so we tightened the cookie policy for the main app.",
        "Session cookies use the `__Host-` prefix with `Secure`, `HttpOnly`, `SameSite=Strict` and a 12-hour expiry; the auth service rejects any request whose cookie fails the prefix invariants.",
    ),
    # 47. pentest cadence — annual external pentest → quarterly + continuous attack surface monitoring
    (
        "pentest_cadence", "technical",
        "An annual external pentest missed a staging leak that lived for eight months, so we moved to a quarterly cadence plus continuous attack surface monitoring.",
        "Pentests run quarterly with a rotating vendor; between engagements, an external attack-surface tool scans all known domains daily and files findings directly into the security tracker.",
    ),
    # 48. phishing defence — generic training → simulated phishing with just-in-time coaching
    (
        "phishing_defence", "technical",
        "Generic annual training did not move the click rate, so we replaced it with a simulated phishing program tied to just-in-time coaching.",
        "Monthly phishing simulations target all staff; clicks trigger a 10-minute training module immediately and feed a dashboard that drives targeted follow-ups for repeat clickers.",
    ),
    # 49. data classification — implicit classification → tag-driven policy enforcement
    (
        "data_classification", "ai_coding",
        "Implicit data classification led to PII ending up in analytics datasets, so we made classification explicit and enforced it through tags.",
        "Every column in the warehouse carries a `classification` tag (public, internal, confidential, restricted); access policies, masking and retention are generated from those tags at deploy time.",
    ),
    # 50. software bill of materials — on-request SBOM → SBOM on every build with diffing
    (
        "sbom_policy", "technical",
        "Producing SBOMs only for compliance requests meant we could not answer the log4shell question quickly, so we started generating them on every build.",
        "Every build writes a CycloneDX SBOM to the artifact store; a nightly job diffs each SBOM against the previous tag and opens a ticket for any dependency whose advisories changed.",
    ),
]

assert len(PAIRS) == 50, f"expected 50 pairs, got {len(PAIRS)}"

_ALLOWED_DOMAINS = {"technical", "ai_coding"}


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (topic, domain, decision_text, arch_text) in enumerate(PAIRS, start=1):
            if domain not in _ALLOWED_DOMAINS:
                raise ValueError(f"pair {i} ({topic}): bad domain {domain!r}")
            pair_id = f"cls-pair-{PAIR_OFFSET + i:05d}"
            decision_id = f"class-{ID_OFFSET + 2 * i - 1:05d}"
            arch_id = f"class-{ID_OFFSET + 2 * i:05d}"
            f.write(
                json.dumps(
                    {
                        "id": decision_id,
                        "domain": domain,
                        "text": decision_text,
                        "memory_type": "decision",
                        "pair_id": pair_id,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            f.write(
                json.dumps(
                    {
                        "id": arch_id,
                        "domain": domain,
                        "text": arch_text,
                        "memory_type": "architecture",
                        "pair_id": pair_id,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            written += 2
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
