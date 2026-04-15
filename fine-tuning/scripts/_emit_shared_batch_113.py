"""One-off emitter for shared-base batch-113 — technical domain (secrets management and PKI infra).

Writes 50 rows to data/v2/shared/batch_113.tmp.jsonl with ids shared-05601..05650.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_113.tmp.jsonl"
ID_OFFSET = 5600

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("HashiCorp Vault replaced a scatter of .env files across the CI runners; dynamic database credentials with a 15-minute TTL cut the blast radius when a runner leaked a token.", "decision", "technical", False,
     [("HashiCorp Vault", "service"), (".env files", "pattern"), ("CI", "infrastructure")],
     [("HashiCorp Vault", ".env files", "REPLACES")],
     "which secrets engine displaced the .env sprawl on the CI runners",
     "dynamic database credential TTL blast radius token leak"),
    # --- 2 ---
    ("Vault's AppRole auth method issued the short-lived tokens; the role_id lived in the AMI and secret_id was pushed by the orchestrator at boot, so neither half was ever at rest together.", "architecture", "technical", False,
     [("Vault", "service"), ("AppRole", "concept"), ("AMI", "technology")],
     [],
     "which Vault auth split kept role_id and secret_id apart at rest",
     "AppRole role id secret id boot push split at rest"),
    # --- 3 ---
    ("Vault Transit encryption replaced application-side AES-GCM wrappers for the PII column; key rotation became a one-line rewrap instead of a code deploy.", "decision", "technical", False,
     [("Vault Transit", "service"), ("AES-GCM", "technology"), ("PII", "concept")],
     [("Vault Transit", "AES-GCM", "REPLACES")],
     "which KMS pattern retired the in-app AES wrappers on the PII column",
     "transit encrypt rewrap rotation key column application"),
    # --- 4 ---
    ("AWS Secrets Manager held the RDS master credential for the legacy monolith; the scheduled Lambda rotation every 30 days survived two audit cycles without drift.", "architecture", "technical", False,
     [("AWS Secrets Manager", "service"), ("RDS", "service"), ("Lambda", "service")],
     [],
     "which AWS service rotated the RDS master credential on the monolith",
     "scheduled rotation master credential audit cycle drift"),
    # --- 5 ---
    ("AWS Secrets Manager was preferred over SSM Parameter Store SecureString for the multi-region failover DB; cross-region replication on the secret itself avoided a bespoke sync job.", "preference", "technical", False,
     [("AWS Secrets Manager", "service"), ("SSM Parameter Store", "service")],
     [("AWS Secrets Manager", "SSM Parameter Store", "PREFERS")],
     "which AWS store won for multi-region DB failover on native replication",
     "cross region replicate secret store failover sync bespoke"),
    # --- 6 ---
    ("GCP Secret Manager replaced a homegrown KMS-wrapped GCS bucket for application secrets; versioned secrets with pinned aliases ended the tag-to-version confusion.", "decision", "technical", False,
     [("GCP Secret Manager", "service"), ("KMS", "service"), ("GCS", "service")],
     [("GCP Secret Manager", "GCS", "REPLACES")],
     "which GCP service killed the KMS-wrapped GCS bucket for app secrets",
     "version pin alias secret drift wrap bucket homegrown"),
    # --- 7 ---
    ("Azure Key Vault stored the signing certificate for the payment webhook; the HSM-backed premium tier stopped the private key from ever leaving FIPS 140-2 Level 2 boundary.", "architecture", "technical", False,
     [("Azure Key Vault", "service"), ("HSM", "technology"), ("FIPS 140-2", "concept")],
     [],
     "which Azure tier kept the webhook signing key inside a FIPS boundary",
     "premium HSM FIPS level boundary signing certificate private"),
    # --- 8 ---
    ("SOPS with age keys replaced git-crypt on the GitOps repo; per-file recipient lists let SRE rotate a laptop's key without re-encrypting every file.", "decision", "technical", False,
     [("SOPS", "tool"), ("age", "tool"), ("git-crypt", "tool"), ("SRE", "organization")],
     [("SOPS", "git-crypt", "REPLACES")],
     "which encryption tool displaced git-crypt on the GitOps repo",
     "recipient list rotate laptop key per file swap encrypt"),
    # --- 9 ---
    ("SOPS was wired to AWS KMS for production values; age keys stayed as a break-glass fallback in the offline safe, not as a primary decryption path.", "architecture", "technical", False,
     [("SOPS", "tool"), ("AWS KMS", "service"), ("age", "tool")],
     [],
     "which SOPS backend held production and which stayed as break-glass",
     "KMS production age offline break glass fallback safe"),
    # --- 10. noise ---
    ("Hold on, my YubiKey is blinking at me.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Doppler ran the secrets injection for the Vercel monorepo; the CLI's scoped tokens beat the old Heroku-style config vars per app.", "architecture", "technical", False,
     [("Doppler", "service"), ("Vercel", "service"), ("Heroku", "service")],
     [],
     "which secrets platform handled the Vercel monorepo injection",
     "CLI scope token config var per app monorepo inject"),
    # --- 12 ---
    ("Infisical replaced Doppler after the self-hosting requirement landed; the open-source control plane ran on the internal Kubernetes cluster without a vendor contract.", "decision", "technical", False,
     [("Infisical", "service"), ("Doppler", "service"), ("Kubernetes", "platform")],
     [("Infisical", "Doppler", "REPLACES")],
     "which secrets manager took over from Doppler once self-hosting was mandated",
     "self host open source control plane vendor contract swap"),
    # --- 13 ---
    ("Bitnami Sealed Secrets encrypted the per-cluster manifests; only the controller in the target cluster could decrypt, so the Git repo stayed public-safe.", "architecture", "technical", False,
     [("Bitnami Sealed Secrets", "tool"), ("Git", "tool")],
     [],
     "which Kubernetes tool kept secrets safe to store in a public Git repo",
     "controller decrypt cluster public repo sealed per cluster"),
    # --- 14 ---
    ("SOPS-flux replaced Sealed Secrets on the multi-tenant cluster; shared KMS keys with IAM role boundaries scaled better than per-cluster controller keys.", "decision", "technical", False,
     [("SOPS-flux", "tool"), ("Sealed Secrets", "tool"), ("KMS", "service"), ("IAM", "service")],
     [("SOPS-flux", "Sealed Secrets", "REPLACES")],
     "which GitOps secrets pattern scaled past Sealed Secrets for multi-tenant",
     "shared KMS IAM role boundary multi tenant scale swap"),
    # --- 15 ---
    ("External Secrets Operator pulled from Vault and synced native Kubernetes Secret objects; workloads kept using env vars without learning the Vault API.", "architecture", "technical", False,
     [("External Secrets Operator", "tool"), ("Vault", "service"), ("Kubernetes", "platform")],
     [("External Secrets Operator", "Vault", "BUILDS_ON")],
     "which operator bridged Vault into native Kubernetes Secret objects",
     "operator pull sync native secret env var bridge workload"),
    # --- 16 ---
    ("YubiHSM 2 replaced a software-only key store for the code-signing root; USB-attached HSM gave deterministic signing throughput without a rack-mounted appliance.", "decision", "technical", False,
     [("YubiHSM 2", "technology"), ("software-only key store", "pattern"), ("HSM", "technology")],
     [("YubiHSM 2", "software-only key store", "REPLACES")],
     "which HSM replaced the software key store for the code-signing root",
     "USB HSM deterministic throughput rack avoid signing root"),
    # --- 17 ---
    ("AWS CloudHSM fronted the regulated signing workload; the PKCS#11 provider in the Java signer offloaded private-key operations without changing the application code.", "architecture", "technical", False,
     [("AWS CloudHSM", "service"), ("PKCS#11", "protocol"), ("Java", "language")],
     [],
     "which HSM served the regulated Java signing workload via PKCS#11",
     "cloud HSM PKCS offload regulated signer private key"),
    # --- 18 ---
    ("KMS envelope encryption wrapped per-tenant DEKs for the multi-tenant SaaS; the KEK in KMS rotated yearly, while DEKs rotated on tenant key-event.", "architecture", "technical", False,
     [("KMS", "service"), ("DEK", "concept"), ("KEK", "concept"), ("SaaS", "concept")],
     [],
     "which envelope encryption layout separated KEK rotation from DEK rotation",
     "envelope DEK KEK rotate yearly tenant event multi tenant"),
    # --- 19 ---
    ("Let's Encrypt handled the public edge certificates; 90-day automation through ACME kept the cert ops budget near zero without sacrificing browser trust.", "architecture", "technical", False,
     [("Let's Encrypt", "service"), ("ACME", "protocol")],
     [],
     "which public CA covered the edge cert rotation at near-zero ops cost",
     "ACME 90 day automation ops budget public CA browser trust"),
    # --- 20 ---
    ("BuyPass Go SSL was added as a secondary ACME CA behind Let's Encrypt; the cert-manager multi-issuer config tolerated a Let's Encrypt outage without a scramble.", "decision", "technical", False,
     [("BuyPass Go SSL", "service"), ("Let's Encrypt", "service"), ("cert-manager", "tool"), ("ACME", "protocol")],
     [("BuyPass Go SSL", "Let's Encrypt", "SUPPORTS")],
     "which secondary ACME CA backed Let's Encrypt on the cert-manager issuer list",
     "secondary issuer multi CA outage fail tolerate cert manager"),
    # --- 21 ---
    ("Sectigo issued the EV certificates on the checkout domain; browser UI still treated the green-bar history as a trust signal for the B2B buyers.", "fact", "technical", False,
     [("Sectigo", "organization")],
     [],
     "which CA issued the EV certs on the checkout domain for B2B trust",
     "EV issuer checkout green bar trust signal B2B browser"),
    # --- 22 ---
    ("step-ca replaced a self-rolled OpenSSL CA for the internal mTLS mesh; ACME support inside the corp network let workloads renew via the same client as public certs.", "decision", "technical", False,
     [("step-ca", "tool"), ("OpenSSL", "tool"), ("ACME", "protocol"), ("mTLS", "protocol")],
     [("step-ca", "OpenSSL", "REPLACES")],
     "which internal CA retired the self-rolled OpenSSL root for the mesh",
     "step internal ACME renew self rolled CA retire mesh"),
    # --- 23 ---
    ("smallstep PKI was chosen over EJBCA for the device CA; the YAML-config and ACME-first ergonomics matched the small SRE team better than the JEE stack.", "decision", "technical", False,
     [("smallstep PKI", "tool"), ("EJBCA", "tool"), ("SRE", "organization"), ("JEE", "technology")],
     [("smallstep PKI", "EJBCA", "PREFERS")],
     "which PKI product won over EJBCA for the device CA choice",
     "YAML ACME ergonomic JEE stack SRE small team choose"),
    # --- 24 ---
    ("mTLS certificate rotation moved to a 24-hour lifetime on the internal API mesh; SPIRE workload attestation made the short windows operationally cheap.", "architecture", "technical", False,
     [("mTLS", "protocol"), ("SPIRE", "service"), ("API", "concept")],
     [],
     "which rotation window landed on the internal API mesh with SPIRE",
     "24 hour lifetime rotate attestation mesh short window"),
    # --- 25 ---
    ("SPIFFE identities replaced the long-lived service-account JWTs for service-to-service auth; SVIDs were minted per workload with sub-hour TTL.", "decision", "technical", False,
     [("SPIFFE", "protocol"), ("SVID", "concept"), ("JWT", "technology")],
     [("SPIFFE", "JWT", "REPLACES")],
     "which identity framework displaced long-lived JWTs for s2s auth",
     "SPIFFE SVID mint workload TTL JWT service account swap"),
    # --- 26 ---
    ("SPIRE server federation tied the EKS cluster to the on-prem bare-metal mesh; cross-trust-domain SVIDs kept the zero-trust story consistent.", "architecture", "technical", False,
     [("SPIRE", "service"), ("EKS", "service"), ("SVID", "concept")],
     [],
     "which SPIRE feature joined the cloud and on-prem meshes under zero-trust",
     "federation cross trust domain cloud on prem zero trust"),
    # --- 27 ---
    ("Certbot was retired on the load balancer tier in favor of Caddy's built-in ACME client; one fewer cron job and no more renewal-failure pages at 3 AM.", "decision", "technical", False,
     [("Certbot", "tool"), ("Caddy", "service"), ("ACME", "protocol")],
     [("Caddy", "Certbot", "REPLACES")],
     "which ACME client took over from Certbot on the LB tier",
     "built in ACME cron renewal fail page LB tier swap"),
    # --- 28 ---
    ("Traefik handled the ACME DNS-01 challenge against Route53; wildcard certs covered the customer-tenant subdomains without pinning a cert per tenant.", "architecture", "technical", False,
     [("Traefik", "service"), ("ACME", "protocol"), ("Route53", "service")],
     [],
     "which proxy ran DNS-01 ACME for the tenant wildcard certificates",
     "DNS 01 challenge wildcard tenant sub domain wild pin"),
    # --- 29 ---
    ("HTTP-01 was preferred over DNS-01 for the public marketing site; no DNS provider tokens on the edge server lowered the secret-management surface.", "preference", "technical", False,
     [("HTTP-01", "protocol"), ("DNS-01", "protocol"), ("DNS", "technology")],
     [("HTTP-01", "DNS-01", "PREFERS")],
     "which ACME challenge won on the marketing site for lower secret surface",
     "HTTP 01 challenge provider token edge server surface lower"),
    # --- 30 ---
    ("sigstore cosign replaced raw GPG signing on the container release pipeline; keyless OIDC-bound signatures dropped the whole key-custody problem on the floor.", "decision", "technical", False,
     [("sigstore", "service"), ("cosign", "tool"), ("GPG", "tool"), ("OIDC", "protocol")],
     [("cosign", "GPG", "REPLACES")],
     "which signing stack replaced GPG on the container release pipeline",
     "keyless OIDC bind container signature custody drop swap"),
    # --- 31 ---
    ("Rekor transparency log anchored the cosign signatures; auditors could verify inclusion proofs weeks after release without bugging the release team.", "architecture", "technical", False,
     [("Rekor", "service"), ("cosign", "tool")],
     [("cosign", "Rekor", "BUILDS_ON")],
     "which transparency log anchored the cosign signatures for audit",
     "transparency log inclusion proof audit verify release team"),
    # --- 32 ---
    ("Fulcio issued the short-lived signing certificates tied to GitHub OIDC; release provenance pointed back to the exact workflow run via the certificate subject.", "architecture", "technical", False,
     [("Fulcio", "service"), ("GitHub", "service"), ("OIDC", "protocol")],
     [],
     "which sigstore CA bound signing certs to the GitHub workflow OIDC",
     "Fulcio short lived signing workflow subject provenance"),
    # --- 33 ---
    ("SLSA level 3 provenance landed on the release pipeline; cosign attestations bound the build environment hash to the Rekor entry for the artifact.", "milestone", "technical", False,
     [("SLSA", "concept"), ("cosign", "tool"), ("Rekor", "service")],
     [],
     "which provenance level landed with cosign attestations tied to Rekor",
     "SLSA level provenance attest build env hash artifact"),
    # --- 34. noise ---
    ("Give me a minute, the CA just hiccuped.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("WebAuthn with YubiKey 5 hardware tokens replaced TOTP for the admin console; phishing-resistant user verification was required by the new SOC 2 control.", "decision", "technical", False,
     [("WebAuthn", "protocol"), ("YubiKey 5", "technology"), ("TOTP", "protocol"), ("SOC 2", "concept")],
     [("WebAuthn", "TOTP", "REPLACES")],
     "which MFA scheme replaced TOTP on the admin console under SOC 2",
     "FIDO hardware phish resist admin user verification swap"),
    # --- 36 ---
    ("Titan Security Keys were issued as the secondary token; a dual-vendor policy avoided a single-firmware-recall event locking out the whole SRE team.", "decision", "technical", False,
     [("Titan Security Keys", "technology"), ("SRE", "organization")],
     [],
     "which secondary hardware token covered the dual-vendor MFA policy",
     "Titan dual vendor firmware recall lockout policy SRE"),
    # --- 37 ---
    ("FIDO2 resident credentials were enabled on the bastion hosts; username-less SSH via ssh-ed25519-sk keys matched the YubiKey residency.", "architecture", "technical", False,
     [("FIDO2", "protocol"), ("YubiKey", "technology"), ("SSH", "protocol"), ("ssh-ed25519-sk", "technology")],
     [],
     "which FIDO2 feature enabled username-less SSH on the bastion hosts",
     "resident credential username less SSH ed25519 sk bastion"),
    # --- 38 ---
    ("OCSP stapling was disabled on the edge after a responder outage; the short-lived Let's Encrypt cert lifetime made revocation latency a lesser worry anyway.", "decision", "technical", False,
     [("OCSP", "protocol"), ("Let's Encrypt", "service")],
     [],
     "which revocation feature was turned off after the responder outage",
     "OCSP staple responder outage short lived revocation latency"),
    # --- 39 ---
    ("Certificate Transparency logs were monitored via Cert Spotter; unauthorized issuances under the corporate apex triggered a PagerDuty in under a minute.", "architecture", "technical", False,
     [("Certificate Transparency", "concept"), ("Cert Spotter", "tool"), ("PagerDuty", "service")],
     [],
     "which CT monitoring tool paged on unauthorized issuance under the apex",
     "CT log monitor unauthorized issuance apex page minute"),
    # --- 40 ---
    ("CAA records were pinned to Let's Encrypt and BuyPass on the apex; third-party CAs were blocked from issuing even on social-engineered domain control checks.", "architecture", "technical", False,
     [("CAA", "protocol"), ("Let's Encrypt", "service"), ("BuyPass", "organization")],
     [],
     "which DNS record locked the apex to the two approved ACME CAs",
     "CAA record apex approve social engineer block issuer"),
    # --- 41 ---
    ("Vault's PKI secrets engine issued the internal-mesh leaf certs; the intermediate rolled every six months while the offline root stayed in a sealed envelope.", "architecture", "technical", False,
     [("Vault", "service"), ("PKI secrets engine", "service")],
     [("Vault", "PKI secrets engine", "BUILDS_ON")],
     "which Vault engine issued the mesh leaves while the root stayed offline",
     "PKI engine intermediate roll offline root seal envelope"),
    # --- 42 ---
    ("Vault's database secrets engine replaced long-lived Postgres passwords for the BI stack; per-session roles with 8-hour TTL satisfied the SOX reviewer.", "decision", "technical", False,
     [("Vault", "service"), ("database secrets engine", "service"), ("long-lived Postgres passwords", "pattern"), ("SOX", "concept")],
     [("database secrets engine", "long-lived Postgres passwords", "REPLACES")],
     "which Vault engine retired the long-lived Postgres passwords on BI",
     "dynamic database role TTL SOX reviewer BI pass retire"),
    # --- 43 ---
    ("Hashicorp Boundary fronted the bastion to managed Postgres databases; the ephemeral SSH-less brokered sessions paired with Vault dynamic credentials.", "architecture", "technical", False,
     [("Hashicorp Boundary", "service"), ("Postgres", "database"), ("SSH", "protocol"), ("Vault", "service")],
     [],
     "which tool brokered ephemeral DB sessions paired with Vault creds",
     "Boundary broker ephemeral SSH less dynamic DB session"),
    # --- 44 ---
    ("Teleport was preferred over raw SSH keys for the production bastions; per-session short-lived certificates plus the session recording shipped audit evidence out of the box.", "preference", "technical", False,
     [("Teleport", "service"), ("SSH keys", "pattern")],
     [("Teleport", "SSH keys", "PREFERS")],
     "which access tool beat raw SSH keys on the production bastions",
     "Teleport session certificate record audit evidence bastion"),
    # --- 45 ---
    ("Keybase-style end-to-end encryption via age recipients kept the pager runbook secrets readable to on-call only; the recipient set rotated when the rotation did.", "architecture", "technical", False,
     [("age", "tool"), ("Keybase", "service")],
     [],
     "which encryption scheme scoped runbook secrets to the on-call rotation",
     "age recipient rotate on call runbook end to end encrypt"),
    # --- 46 ---
    ("1Password Secrets Automation was preferred over Vault for the five-person startup; no server to host beat the dynamic-creds story at that scale.", "preference", "technical", False,
     [("1Password Secrets Automation", "service"), ("Vault", "service")],
     [("1Password Secrets Automation", "Vault", "PREFERS")],
     "which secrets platform beat Vault at the five-person startup scale",
     "1Password no server host small startup scale dynamic"),
    # --- 47 ---
    ("Mozilla SOPS documentation was the reference for the KMS key-rotation runbook; the `--rotate` flag plus updated-keys walkthrough settled the on-call question thread.", "reference", "technical", False,
     [("Mozilla SOPS", "tool"), ("KMS", "service")],
     [],
     "which SOPS documentation guided the KMS key-rotation runbook",
     "SOPS rotate flag doc reference rotation runbook on call"),
    # --- 48 ---
    ("Ephemeral GitHub Actions OIDC tokens replaced long-lived AWS access keys in the CI; the cloud-side IAM role trust policy pinned the repo and ref for least privilege.", "decision", "technical", False,
     [("GitHub Actions", "service"), ("OIDC", "protocol"), ("AWS access keys", "pattern"), ("IAM", "service")],
     [("OIDC", "AWS access keys", "REPLACES")],
     "which CI auth flow retired the long-lived AWS keys in GitHub Actions",
     "OIDC token ephemeral IAM role trust pin repo ref least"),
    # --- 49 ---
    ("CRL distribution was dropped for the internal CA on 2026-03-14; OCSP-only revocation with short-lived certs matched the mesh renewal cadence instead.", "milestone", "technical", False,
     [("CRL", "protocol"), ("OCSP", "protocol"), ("2026-03-14", "date")],
     [],
     "when did the internal CA drop CRL in favor of OCSP-only revocation",
     "CRL drop OCSP only short lived revoke mesh cadence date"),
    # --- 50 ---
    ("A Vault seal migration moved from Shamir to AWS KMS auto-unseal on 2026-03-28; operator-free restarts ended the 2 AM pages for the five-shard unseal ceremony.", "milestone", "technical", False,
     [("Vault", "service"), ("Shamir", "technology"), ("AWS KMS", "service"), ("2026-03-28", "date")],
     [("AWS KMS", "Shamir", "REPLACES")],
     "when did Vault move from Shamir unseal to AWS KMS auto-unseal",
     "seal migration Shamir auto unseal operator free page date"),
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
