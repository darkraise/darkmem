"""One-off emitter for shared-base batch-023 — technical domain (networking/security/identity/crypto).

Same pattern as _emit_shared_batch_011.py; only ENTRIES and ID_OFFSET change.
Writes 50 rows to data/v2/shared/batch_023.tmp.jsonl with ids shared-01101..01150.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_023.tmp.jsonl"
ID_OFFSET = 1100

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("step-ca issues short-lived SSH host certificates signed by a root anchor held in a YubiKey; bastion trust-on-first-use is gone.", "architecture", "technical", False,
     [("step-ca", "service"), ("SSH", "protocol"), ("YubiKey", "infrastructure")],
     [],
     "how does our bastion swap trust-on-first-use for proper host certs",
     "CA host certificate root anchor smallstep hardware"),
    # --- 2 ---
    ("smallstep replaced HashiCorp Boundary for operator access; the ACME-style enrolment flow clicked with the existing TLS story.", "decision", "technical", False,
     [("smallstep", "service"), ("HashiCorp Boundary", "service"), ("ACME", "protocol"), ("TLS", "protocol")],
     [("smallstep", "HashiCorp Boundary", "REPLACES")],
     "which operator-access tool pushed out the HashiCorp one and why",
     "broker swap enrolment protocol reuse choice"),
    # --- 3 ---
    ("SPIFFE IDs let cross-region workloads prove identity without shared secrets; SPIRE agents attest nodes via AWS instance metadata.", "architecture", "technical", False,
     [("SPIFFE", "framework"), ("SPIRE", "service"), ("AWS", "platform")],
     [],
     "how do workloads authenticate across regions without pre-shared keys",
     "workload identity attestation cross region metadata"),
    # --- 4 ---
    ("SPIRE is preferred over custom JWT minters for service identity; rotation and attestation come for free in the reference agent.", "preference", "technical", False,
     [("SPIRE", "service"), ("JWT", "protocol")],
     [("SPIRE", "JWT", "PREFERS")],
     "which identity source wins over hand-rolled token minters",
     "identity issuer rotation attestation builtin reference"),
    # --- 5 ---
    ("STUN alone could not punch through the symmetric NAT on one carrier; TURN relay kept the voice call quality acceptable.", "problem", "technical", False,
     [("STUN", "protocol"), ("NAT", "technology"), ("TURN", "protocol")],
     [],
     "what rescued voice calls when the binding-only method failed behind symmetric NAT",
     "relay fallback carrier symmetric punch failure"),
    # --- 6 ---
    ("ICE candidate gathering picks a host, server-reflexive, or relay pair; the priority formula is RFC 8445 verbatim.", "reference", "technical", False,
     [("ICE", "protocol"), ("RFC 8445", "publication")],
     [],
     "where does the pairing algorithm for NAT traversal candidates live formally",
     "candidate priority specification document formula"),
    # --- 7 ---
    ("BGP route flapping from a misbehaving peer triggered dampening on 2026-02-21; RPKI origin validation caught the bogus prefix.", "milestone", "technical", False,
     [("BGP", "protocol"), ("RPKI", "protocol"), ("2026-02-21", "date")],
     [],
     "when did the prefix-origin check save us from a flapping peer",
     "route dampening prefix origin check incident day"),
    # --- 8 ---
    ("Anycast deploys of the auth resolver cut P50 latency across Asia-Pacific; health withdrawal handles the unhealthy POP case cleanly.", "architecture", "technical", False,
     [("Anycast", "technology"), ("POP", "infrastructure")],
     [],
     "how did the auth resolver get faster for the APAC region specifically",
     "shared address latency regional health withdraw"),
    # --- 9 ---
    ("Let's Encrypt ACME DNS-01 flow via Cloudflare issues wildcard certs for the internal sub-domains; no public HTTP is exposed.", "architecture", "technical", False,
     [("Let's Encrypt", "service"), ("ACME", "protocol"), ("Cloudflare", "service")],
     [],
     "how do we get wildcard certificates without exposing any HTTP server publicly",
     "wildcard issuance DNS challenge internal zone closed"),
    # --- 10. noise ---
    ("Hang on, refreshing the console.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Vault dynamic database credentials replace the long-lived shared password; Postgres roles now live for fifteen minutes at most.", "decision", "technical", False,
     [("Vault", "service"), ("Postgres", "database")],
     [],
     "how did the team retire the shared database password in favour of per-request creds",
     "secret broker short lived role window lease"),
    # --- 12 ---
    ("Doppler is preferred over AWS Secrets Manager for developer-facing config; the CLI injects env vars without a sidecar.", "preference", "technical", False,
     [("Doppler", "service"), ("AWS Secrets Manager", "service")],
     [("Doppler", "AWS Secrets Manager", "PREFERS")],
     "which secret store wins for day-to-day developer workflows",
     "env injection CLI sidecar avoid dev experience"),
    # --- 13 ---
    ("OIDC authorization code flow now requires PKCE for every public client; the mobile SDK had to bump past a dusty pinned version.", "decision", "technical", False,
     [("OIDC", "protocol"), ("PKCE", "protocol")],
     [],
     "what auth tightening did we force across every public-client app",
     "code exchange proof key mandatory mobile bump"),
    # --- 14 ---
    ("SAML replay protection caught a stolen assertion being reused two seconds later; the InResponseTo check pinned the original request.", "problem", "technical", False,
     [("SAML", "protocol"), ("InResponseTo", "api")],
     [],
     "what stopped a captured SSO assertion from being replayed almost immediately",
     "assertion reuse attack detection response binding"),
    # --- 15 ---
    ("CSP headers enforce strict-dynamic plus SRI hashes on every bundle; one inline script removal took a week but bounced an XSS class.", "architecture", "technical", False,
     [("CSP", "protocol"), ("SRI", "protocol"), ("XSS", "concept")],
     [],
     "how did the front-end stop a whole class of script injections with headers alone",
     "content policy subresource integrity inline removal"),
    # --- 16 ---
    ("Cookie SameSite=Lax was not enough against a top-frame GET CSRF; tightened to SameSite=Strict on the admin console cookies.", "problem", "technical", False,
     [("SameSite", "config"), ("CSRF", "concept")],
     [],
     "why did the admin console cookie need a stricter cross-site policy than Lax",
     "cookie policy top frame request forgery tighten"),
    # --- 17 ---
    ("JWT rotation pattern keeps two active signing keys in JWKS; the jose library on verifiers still accepts the old kid during overlap.", "architecture", "technical", False,
     [("JWT", "protocol"), ("JWKS", "api"), ("jose", "library")],
     [],
     "how do we rotate signing keys without invalidating live tokens mid-flight",
     "dual key overlap verifier kid bridge window"),
    # --- 18 ---
    ("OAuth scopes now gate coarse feature access while roles stay inside the resource server; the split stopped scope explosion.", "decision", "technical", False,
     [("OAuth", "protocol")],
     [],
     "how are scopes and roles divided across the auth boundary to avoid explosion",
     "permission boundary coarse fine grained split"),
    # --- 19 ---
    ("AWS KMS customer-managed keys wrap the RDS data keys; grants are scoped per application role rather than per human identity.", "architecture", "technical", False,
     [("AWS KMS", "service"), ("RDS", "service")],
     [],
     "how are database encryption keys scoped in our cloud account model",
     "envelope encryption grant role scoped database"),
    # --- 20 ---
    ("HashiCorp Vault transit engine replaced homegrown KMS wrappers for internal services; key versioning simplified rotation audits.", "decision", "technical", False,
     [("HashiCorp Vault", "service"), ("transit engine", "api")],
     [("HashiCorp Vault", "transit engine", "REPLACES")],
     "which managed crypto path took over from the internal key-wrapping code",
     "encryption as a service rotation audit trail"),
    # --- 21 ---
    ("GCP KMS external key manager (EKM) integration lets a customer hold their own root; break-glass uses a signed sealed-envelope flow.", "architecture", "technical", False,
     [("GCP KMS", "service"), ("EKM", "api")],
     [],
     "how can a customer keep root key custody while we still use managed KMS",
     "external manager customer hold root break glass"),
    # --- 22 ---
    ("YubiKey attestation cert chains get pinned in the enrolment service; any non-genuine device is refused a production role.", "architecture", "technical", False,
     [("YubiKey", "infrastructure")],
     [],
     "how do we block counterfeit hardware tokens from getting production roles",
     "attestation cert pinning device genuine enrolment"),
    # --- 23 ---
    ("TPM-backed platform attestation gates laptop access to sensitive repos; measured boot PCRs feed a conditional-access policy.", "architecture", "technical", False,
     [("TPM", "infrastructure"), ("PCR", "concept")],
     [],
     "how do laptops prove platform integrity before reaching sensitive repos",
     "measured boot platform register conditional access"),
    # --- 24 ---
    ("Cloudflare WAF rules now include a managed ruleset for Log4Shell patterns; a rare false positive hit a templated reporting URL.", "problem", "technical", False,
     [("Cloudflare", "service"), ("WAF", "service"), ("Log4Shell", "concept")],
     [],
     "what managed ruleset slipped up on one of our internal reporting URLs",
     "firewall rule false positive template match"),
    # --- 25 ---
    ("The token-bucket rate limiter lives in the edge gateway; per-tenant buckets refill at a rate tied to the contract tier.", "architecture", "technical", False,
     [("token-bucket", "algorithm")],
     [],
     "where does the per-tenant throttling math happen and how does it scale",
     "leaky limiter tier refill contract edge gateway"),
    # --- 26 ---
    ("mTLS is now mandatory east-west inside the Istio mesh; PeerAuthentication STRICT landed on 2026-03-02 for the payments service namespace.", "milestone", "technical", False,
     [("mTLS", "protocol"), ("Istio", "service"), ("PeerAuthentication", "config"), ("2026-03-02", "date"), ("payments service", "project")],
     [],
     "when did strict mutual TLS cover the payments namespace inside the mesh",
     "east west peer auth strict namespace rollout"),
    # --- 27 ---
    ("Cilium Tetragon traces exec events in-kernel via eBPF for runtime policy; the rule engine blocks unexpected process trees on tier-0 pods.", "architecture", "technical", False,
     [("Cilium", "service"), ("Tetragon", "tool"), ("eBPF", "technology")],
     [],
     "how does the kernel-level tracer enforce runtime policy on our top tier pods",
     "exec trace kernel rule block process tree"),
    # --- 28 ---
    ("Falco is preferred over custom audit scripts for kernel rule coverage; the community ruleset catches techniques we would have missed.", "preference", "technical", False,
     [("Falco", "tool"), ("audit", "technology")],
     [("Falco", "audit", "PREFERS")],
     "which runtime detector beat the hand-rolled audit scripts and why",
     "community rule kernel sensor coverage hand rolled"),
    # --- 29 ---
    ("Syft generates SPDX and CycloneDX SBOMs per image build; the attestation gets stored next to the image in the OCI registry.", "architecture", "technical", False,
     [("Syft", "tool"), ("SPDX", "concept"), ("CycloneDX", "concept"), ("OCI", "protocol")],
     [],
     "how do we produce and store software bills of materials per container image",
     "SBOM format generator attestation registry colocate"),
    # --- 30 ---
    ("cosign replaced Notary v1 for container signing; the Go-based keyless flow against Fulcio matched our short-lived identity story.", "decision", "technical", False,
     [("cosign", "tool"), ("Notary v1", "tool"), ("Fulcio", "service"), ("Go", "language")],
     [("cosign", "Notary v1", "REPLACES")],
     "which signing stack took over from the older Docker-era tool",
     "keyless signing ephemeral identity container swap"),
    # --- 31 ---
    ("SLSA level 3 provenance builds on in-toto attestation; every release publishes a signed statement of its build parameters.", "architecture", "technical", False,
     [("SLSA", "method"), ("in-toto", "framework")],
     [("SLSA", "in-toto", "BUILDS_ON")],
     "how does the supply-chain framework derive from the underlying attestation spec",
     "provenance level framework attestation statement build"),
    # --- 32 ---
    ("DNSSEC signing rolled out across the public zones on 2026-01-18; a blown KSK rollover taught us to script the double-DS dance.", "milestone", "technical", False,
     [("DNSSEC", "protocol"), ("KSK", "concept"), ("2026-01-18", "date")],
     [],
     "when did public zone signing finally land and what lesson came with it",
     "zone signature rollover key double dance launch"),
    # --- 33 ---
    ("HSTS preload submission for the apex domain was completed after fixing three subdomains that still served mixed content.", "milestone", "technical", False,
     [("HSTS", "protocol")],
     [],
     "what did we finish for the apex domain on the transport security front",
     "preload list apex subdomain mixed content cleanup"),
    # --- 34. noise ---
    ("Let me poke the service and circle back.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Pomerium replaced a legacy VPN as the zero-trust entry point for internal apps; device posture gates every request, not the session.", "decision", "technical", False,
     [("Pomerium", "service"), ("VPN", "technology")],
     [("Pomerium", "VPN", "REPLACES")],
     "which zero-trust proxy took over from the legacy remote-access tool",
     "device posture per request gate session drop"),
    # --- 36 ---
    ("Cloudflare Access handles SSO for vendor consoles; short-lived JWT headers let each upstream enforce additional RBAC locally.", "architecture", "technical", False,
     [("Cloudflare Access", "service"), ("JWT", "protocol"), ("RBAC", "concept")],
     [],
     "how are vendor console logins fronted while upstreams keep their own permission rules",
     "edge SSO token header upstream permission enforce"),
    # --- 37 ---
    ("BeyondCorp-style access assumes the corporate network is hostile; internal DNS, mTLS, and device trust replace the perimeter.", "reference", "technical", False,
     [("BeyondCorp", "method"), ("mTLS", "protocol"), ("DNS", "protocol")],
     [],
     "what three controls the zero-trust model leans on instead of a network perimeter",
     "perimeter drop internal name resolution device trust"),
    # --- 38 ---
    ("Tailscale mesh improves on plain WireGuard configs for rapid peer churn; the coordination server removes hand-tuned peer lists.", "preference", "technical", False,
     [("Tailscale", "service"), ("WireGuard", "protocol")],
     [("Tailscale", "WireGuard", "IMPROVES_ON")],
     "how does the managed mesh beat hand-rolled configs for shifting peers",
     "coordination server peer churn managed overlay"),
    # --- 39 ---
    ("Netbird was picked over Netmaker for self-hosted mesh; the SSO-native control plane slotted into our OIDC setup cleanly.", "decision", "technical", False,
     [("Netbird", "service"), ("Netmaker", "service"), ("OIDC", "protocol")],
     [("Netbird", "Netmaker", "PREFERS")],
     "which self-hosted mesh got picked over the other open-source option",
     "self hosted overlay control plane SSO native fit"),
    # --- 40 ---
    ("Caddy handles automatic TLS for the ops dashboards; the internal ACME server issues certs without touching public infrastructure.", "architecture", "technical", False,
     [("Caddy", "service"), ("TLS", "protocol"), ("ACME", "protocol")],
     [],
     "how do internal ops dashboards get valid TLS without any public issuance",
     "internal issuer automatic cert ops dashboard path"),
    # --- 41 ---
    ("Traefik is preferred over Nginx for the dynamic ingress tier; container-label discovery beat template-regen scripts for our churn.", "preference", "technical", False,
     [("Traefik", "service"), ("Nginx", "service")],
     [("Traefik", "Nginx", "PREFERS")],
     "which ingress wins for high-churn container-label environments",
     "label discovery template regen drop dynamic ingress"),
    # --- 42 ---
    ("Nginx still fronts the static marketing site; the 30-line config beats any reason to layer in a heavier reverse proxy.", "decision", "technical", False,
     [("Nginx", "service")],
     [],
     "why does the marketing site keep the lightweight reverse proxy instead of the dynamic one",
     "static site minimal config heavier proxy reject"),
    # --- 43 ---
    ("Boundary session recording captured a misbehaving admin session for the incident review on 2026-03-09; playback was in-browser.", "milestone", "technical", False,
     [("Boundary", "service"), ("2026-03-09", "date")],
     [],
     "when did recorded admin sessions first feed a real incident review",
     "session playback admin review incident evidence"),
    # --- 44 ---
    ("SPIFFE Workload API is wired into the sidecar injector; short-lived SVIDs arrive on a Unix socket and never touch disk.", "architecture", "technical", False,
     [("SPIFFE", "framework"), ("Workload API", "api"), ("SVID", "api")],
     [],
     "how do pods get workload identity documents without ever writing a secret to disk",
     "socket delivery short lived document inject path"),
    # --- 45 ---
    ("Fulcio keyless signing issues per-build ephemeral certs bound to OIDC identities; Rekor logs make rollbacks auditable.", "architecture", "technical", False,
     [("Fulcio", "service"), ("OIDC", "protocol"), ("Rekor", "service")],
     [],
     "how do ephemeral signing certs get audit trails tied to identities per build",
     "keyless signing transparency log identity bind"),
    # --- 46 ---
    ("AES-GCM-SIV replaces AES-GCM for at-rest blobs where nonce-reuse risk is non-trivial; throughput cost was acceptable.", "decision", "technical", False,
     [("AES-GCM-SIV", "algorithm"), ("AES-GCM", "algorithm")],
     [("AES-GCM-SIV", "AES-GCM", "REPLACES")],
     "which at-rest cipher replaces the original AEAD for nonce-risk workloads",
     "nonce misuse resistant AEAD at rest trade cost"),
    # --- 47 ---
    ("Argon2id is preferred over bcrypt for new password hashes; memory-hardness tuning slotted cleanly into the login hot path.", "preference", "technical", False,
     [("Argon2id", "algorithm"), ("bcrypt", "algorithm")],
     [("Argon2id", "bcrypt", "PREFERS")],
     "which password hash wins for newly enrolled accounts and why",
     "memory hard hash GPU resistant login parameter"),
    # --- 48 ---
    ("HashiCorp Vault KV v2 stores audit metadata per secret version; a stale app hit a 404 on an undeleted but demoted version.", "problem", "technical", False,
     [("HashiCorp Vault", "service"), ("KV v2", "api")],
     [],
     "what gotcha around version metadata bit the app when a secret was demoted",
     "version metadata demote stale fetch not found"),
    # --- 49 ---
    ("eBPF socket filter on the egress gateway flagged exfil-shaped traffic to an odd ASN; the block list update closed it within the hour.", "milestone", "technical", False,
     [("eBPF", "technology"), ("ASN", "concept")],
     [],
     "what detection caught exfil-shaped traffic heading to an unusual network operator",
     "socket filter egress unusual operator quick block"),
    # --- 50 ---
    ("Ed25519 SSH keys are mandatory for new enrolments; RSA-2048 keys kept a grandfather window until the next key-rotation sweep.", "decision", "technical", False,
     [("Ed25519", "algorithm"), ("SSH", "protocol"), ("RSA-2048", "algorithm")],
     [("Ed25519", "RSA-2048", "REPLACES")],
     "which signing curve replaced the older RSA key for new SSH enrolments",
     "curve signature new enrolment legacy grandfather"),
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
