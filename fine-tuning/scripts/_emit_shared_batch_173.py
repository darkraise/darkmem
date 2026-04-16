"""One-off emitter for shared-base batch-173 — technical domain (secrets management and key storage: Vault, AWS/GCP/Azure secret stores, SOPS, age, sealed-secrets, ESO, CSI, KMS/HSM, rotation, dynamic secrets, IRSA, Workload Identity, leak detection).

Writes 50 rows to data/v2/shared/batch_173.tmp.jsonl with ids shared-08601..08650.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_173.tmp.jsonl"
ID_OFFSET = 8600

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the platform-API secrets from a .env checked into a private repo to HashiCorp Vault with AppRole auth; the old shared token got rotated out within the same hour.", "decision", "technical", False,
     [("HashiCorp Vault", "tool"), ("AppRole", "method"), (".env", "file")],
     [("HashiCorp Vault", ".env", "REPLACES")],
     "which secret backend and auth method replaced the checked-in dotenv for the platform API",
     "vault approle env secret rotate platform api token migrate"),
    # --- 2 ---
    ("AWS Secrets Manager holds the RDS credentials for the billing service with a 30-day rotation lambda; Parameter Store keeps the non-secret feature flags and remains unencrypted on purpose.", "architecture", "technical", False,
     [("AWS Secrets Manager", "service"), ("Parameter Store", "service"), ("RDS", "database"), ("billing service", "service")],
     [("AWS Secrets Manager", "RDS", "APPLIES_TO"), ("billing service", "AWS Secrets Manager", "USES")],
     "how are RDS credentials and non-secret feature flags split between the two AWS stores for billing",
     "aws secrets manager parameter store rds rotation lambda flag"),
    # --- 3 ---
    ("Chose Google Secret Manager over a self-hosted Vault for the GKE workloads because Workload Identity bindings let pods pull secrets without a mounted service-account key on disk.", "decision", "technical", False,
     [("Google Secret Manager", "service"), ("Vault", "tool"), ("GKE", "platform"), ("Workload Identity", "method")],
     [("Google Secret Manager", "Vault", "PREFERS"), ("GKE", "Workload Identity", "USES")],
     "why did the GKE workloads pick Google Secret Manager instead of self-hosted Vault",
     "google secret manager vault gke workload identity pod key disk"),
    # --- 4 ---
    ("Azure Key Vault stores the signing certs for the document service; the Managed Identity on the AKS pod replaced the client-secret login path that used to ship the secret in a ConfigMap.", "architecture", "technical", False,
     [("Azure Key Vault", "service"), ("AKS", "platform"), ("Managed Identity", "method"), ("ConfigMap", "pattern")],
     [("Azure Key Vault", "ConfigMap", "REPLACES"), ("AKS", "Managed Identity", "USES")],
     "which Azure identity pattern replaced the ConfigMap-based client secret for Key Vault access on AKS",
     "azure key vault aks managed identity configmap client secret cert"),
    # --- 5 ---
    ("Adopted Doppler as the central secret plane for the node services; developers edit values in the Doppler UI and the CLI injects them at boot so nothing lands in the repo or the shell history.", "decision", "technical", False,
     [("Doppler", "tool"), ("Doppler UI", "tool"), ("CLI", "tool")],
     [("Doppler", "Doppler UI", "HAS_PART")],
     "which secret delivery flow replaced repo-checked config for the node services via Doppler",
     "doppler ui cli node service inject boot repo shell history"),
    # --- 6 ---
    ("Infisical replaced our previous in-house secret proxy; the SDK has a drop-in Python client and the self-host image runs fine on a single-node k3s cluster for the staging environment.", "decision", "technical", False,
     [("Infisical", "tool"), ("Python", "language"), ("k3s", "platform"), ("secret proxy", "pattern")],
     [("Infisical", "secret proxy", "REPLACES"), ("Infisical", "k3s", "DEPLOYED_ON")],
     "which open-source secret platform replaced the in-house proxy in the staging k3s cluster",
     "infisical python sdk k3s self host secret proxy staging drop in"),
    # --- 7 ---
    ("Integrated the 1Password SDK into the dev CLI so engineers pull their personal vault items into environment variables without copy-paste; the previous clipboard-driven workflow was the main leak source.", "fact", "technical", False,
     [("1Password SDK", "library"), ("dev CLI", "tool"), ("clipboard", "pattern")],
     [("1Password SDK", "clipboard", "REPLACES")],
     "how did the 1Password SDK change the dev CLI flow and which leak source did it retire",
     "1password sdk dev cli env variable clipboard copy paste leak"),
    # --- 8 ---
    ("Bitwarden Secrets Manager covers the small-team side projects; the free self-host tier on a single Caddy-fronted container handled a six-month load test with no drift in the encrypted blob.", "fact", "technical", False,
     [("Bitwarden Secrets Manager", "service"), ("Caddy", "tool")],
     [("Bitwarden Secrets Manager", "Caddy", "DEPLOYED_ON")],
     "which lightweight self-host stack covers secrets for the small-team side projects",
     "bitwarden secrets manager caddy self host free container small team"),
    # --- 9 ---
    ("SOPS with an age recipient key encrypts the Helm values files checked into the platform repo; the public recipient is committed, the private age identity lives only on the CI KMS key.", "architecture", "technical", False,
     [("SOPS", "tool"), ("age", "tool"), ("Helm", "tool"), ("CI", "service"), ("KMS", "service")],
     [("SOPS", "age", "USES"), ("SOPS", "Helm", "APPLIES_TO")],
     "how does SOPS with age protect Helm values in the platform repo while keeping the private key off disk",
     "sops age helm values encrypt ci kms private identity recipient"),
    # --- 10. noise ---
    ("The office coffee machine grew a second sticker claiming it was now sentient and accepting tribute in the form of oat milk.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("age encryption replaced gpg across the ops scripts; the keypair format is shorter, there's no web-of-trust to maintain, and the library has clean Go bindings for our internal tools.", "decision", "technical", False,
     [("age", "tool"), ("gpg", "tool"), ("Go", "language")],
     [("age", "gpg", "REPLACES")],
     "which encryption tool replaced gpg in the ops scripts and what made age a better fit for internal Go tools",
     "age gpg ops script go binding keypair web of trust replace"),
    # --- 12 ---
    ("Bitnami sealed-secrets lets us commit encrypted Secret manifests to the GitOps repo; the controller on the cluster decrypts them on reconcile and only the controller's asymmetric private key can unseal.", "architecture", "technical", False,
     [("sealed-secrets", "tool"), ("Bitnami", "organization"), ("GitOps", "pattern"), ("Secret", "api")],
     [("sealed-secrets", "Secret", "PRODUCES"), ("sealed-secrets", "GitOps", "SUPPORTS")],
     "how do sealed-secrets let the team commit encrypted Kubernetes Secrets to the GitOps repo safely",
     "sealed secrets bitnami gitops controller decrypt private key commit"),
    # --- 13 ---
    ("External Secrets Operator pulls from AWS Secrets Manager into native Kubernetes Secret objects on a five-minute refresh; the prior init-container fetch pattern missed mid-life rotations.", "architecture", "technical", False,
     [("External Secrets Operator", "tool"), ("AWS Secrets Manager", "service"), ("Kubernetes Secret", "api"), ("init-container", "pattern")],
     [("External Secrets Operator", "AWS Secrets Manager", "COMMUNICATES_WITH"), ("External Secrets Operator", "init-container", "REPLACES")],
     "which operator replaced init-container fetches and how often does it refresh from AWS Secrets Manager",
     "external secrets operator aws refresh init container rotation kubernetes"),
    # --- 14 ---
    ("CSI Secrets Store driver mounts Vault leases as tmpfs files on the pod; the app re-reads on SIGHUP so a short TTL lease is cycled in place without a pod restart.", "architecture", "technical", False,
     [("CSI Secrets Store", "tool"), ("Vault", "tool"), ("tmpfs", "technology"), ("SIGHUP", "protocol")],
     [("CSI Secrets Store", "Vault", "COMMUNICATES_WITH"), ("CSI Secrets Store", "tmpfs", "USES")],
     "how does the CSI Secrets Store driver deliver Vault leases and how does the app refresh them",
     "csi secrets store vault tmpfs sighup lease pod restart mount"),
    # --- 15 ---
    ("Kubernetes Secrets base64 encoding is not encryption and we finally wrote that on the onboarding doc; the at-rest etcd encryption provider is now mandatory and verified via an audit hook on cluster spin-up.", "reference", "technical", False,
     [("Kubernetes Secrets", "api"), ("etcd", "database"), ("base64", "algorithm"), ("encryption provider", "config")],
     [("encryption provider", "etcd", "APPLIES_TO")],
     "which etcd-level protection did we make mandatory after clarifying that Secret base64 is not encryption",
     "kubernetes secret base64 encryption etcd provider audit onboarding"),
    # --- 16 ---
    ("Envelope encryption is the pattern: a DEK encrypts the payload, a KEK in KMS encrypts the DEK, and only the ciphertext DEK travels alongside the payload at rest.", "reference", "technical", False,
     [("Envelope encryption", "pattern"), ("DEK", "concept"), ("KEK", "concept"), ("KMS", "service")],
     [("Envelope encryption", "KMS", "USES")],
     "how does envelope encryption split the data and key encryption responsibilities between DEK and KEK",
     "envelope encryption dek kek kms ciphertext payload pattern rest"),
    # --- 17 ---
    ("AWS KMS customer-managed keys back the envelope encryption for S3 object payloads; the key policy denies everything except a single IAM role and the decrypt operation is logged to CloudTrail.", "architecture", "technical", False,
     [("AWS KMS", "service"), ("S3", "service"), ("IAM", "service"), ("CloudTrail", "service")],
     [("S3", "AWS KMS", "USES"), ("AWS KMS", "CloudTrail", "COMMUNICATES_WITH")],
     "how does AWS KMS back S3 envelope encryption and where do the decrypt calls get audited",
     "aws kms s3 envelope encryption iam role cloudtrail audit decrypt"),
    # --- 18 ---
    ("GCP KMS owns the KEKs for BigQuery CMEK on the analytics dataset; the key ring is pinned to the same region as the dataset so cross-region failover plans have to duplicate the key material.", "fact", "technical", False,
     [("GCP KMS", "service"), ("BigQuery", "service"), ("CMEK", "concept"), ("key ring", "concept")],
     [("BigQuery", "GCP KMS", "USES")],
     "how does GCP KMS protect the BigQuery analytics dataset and what does the regional pin mean for failover",
     "gcp kms bigquery cmek key ring region failover analytics kek"),
    # --- 19 ---
    ("Azure Key Vault Managed HSM replaced the software-backed Key Vault tier for the signing keys that touch customer data; the HSM-backed attestation satisfies the SOC 2 control we previously waved off with a compensating control.", "decision", "technical", False,
     [("Azure Key Vault Managed HSM", "service"), ("Key Vault", "service"), ("SOC 2", "publication")],
     [("Azure Key Vault Managed HSM", "Key Vault", "REPLACES"), ("Azure Key Vault Managed HSM", "SOC 2", "SUPPORTS")],
     "which HSM-backed Azure service replaced software-backed Key Vault for the signing keys under SOC 2",
     "azure key vault managed hsm signing key soc 2 attestation"),
    # --- 20 ---
    ("YubiHSM 2 devices guard the code-signing keys on the release workstations; two hardware devices in a threshold config mean no single machine loss compromises the signing chain.", "architecture", "technical", False,
     [("YubiHSM 2", "infrastructure"), ("code-signing", "concept"), ("threshold", "pattern")],
     [("YubiHSM 2", "code-signing", "APPLIES_TO")],
     "which hardware device protects the code-signing keys and how does the threshold config handle a device loss",
     "yubihsm code signing release workstation threshold hardware key"),
    # --- 21 ---
    ("AWS CloudHSM fronts the TDE keys for the regulated Postgres cluster; the integration is FIPS 140-2 Level 3 and the cluster never sees the key material outside the HSM's secure channel.", "architecture", "technical", False,
     [("AWS CloudHSM", "service"), ("Postgres", "database"), ("TDE", "concept"), ("FIPS 140-2", "publication")],
     [("Postgres", "AWS CloudHSM", "USES"), ("AWS CloudHSM", "FIPS 140-2", "SUPPORTS")],
     "how does AWS CloudHSM protect Postgres TDE keys under FIPS 140-2 Level 3 expectations",
     "aws cloudhsm postgres tde fips regulated key material channel"),
    # --- 22 ---
    ("Secret rotation policy is 90 days for long-lived credentials and 1 hour for dynamic leases; the calendar reminder got retired after the scheduler hook into Vault stopped failing silently.", "preference", "technical", False,
     [("rotation policy", "pattern"), ("dynamic leases", "concept"), ("Vault", "tool"), ("scheduler hook", "pattern")],
     [("Vault", "rotation policy", "IMPLEMENTS")],
     "what are the rotation windows for long-lived versus dynamic secrets and what retired the calendar reminder",
     "rotation policy 90 days dynamic lease vault scheduler hook"),
    # --- 23 ---
    ("Vault dynamic secrets for the database tier cut the blast radius of the last leaked credential incident; each app gets a unique 30-minute Postgres role instead of one shared application user.", "milestone", "technical", False,
     [("Vault", "tool"), ("dynamic secrets", "concept"), ("Postgres", "database"), ("application user", "pattern")],
     [("Vault", "dynamic secrets", "PRODUCES"), ("dynamic secrets", "application user", "REPLACES")],
     "which Vault feature shrank blast radius on leaks and what lifetime do the Postgres roles hold",
     "vault dynamic secret postgres role 30 minute blast radius leak"),
    # --- 24 ---
    ("Leasing in Vault is not a TTL you set once; the lease gets renewed up to a max TTL, and clients that forget to call renew are evicted which is the whole point of the design.", "reference", "technical", False,
     [("Vault", "tool"), ("lease", "concept"), ("TTL", "concept"), ("max TTL", "concept")],
     [("lease", "max TTL", "HAS_PART")],
     "how does Vault leasing differ from a simple TTL and what happens when a client forgets to renew",
     "vault lease ttl max renew evict client forget design"),
    # --- 25 ---
    ("Vault Agent sidecars auth once using the Kubernetes auth method, then template secret files into the app's filesystem; the app code stays unaware of Vault entirely.", "architecture", "technical", False,
     [("Vault Agent", "tool"), ("Kubernetes auth", "method"), ("sidecar", "pattern")],
     [("Vault Agent", "Kubernetes auth", "USES")],
     "how does Vault Agent deliver secrets to an app without the app having to know about Vault",
     "vault agent sidecar kubernetes auth template filesystem app"),
    # --- 26 ---
    ("Vault Transit engine handles our encryption-as-a-service for the notifications pipeline; the app never holds the key, it just submits ciphertext and decrypt requests over the Vault API.", "architecture", "technical", False,
     [("Vault Transit", "service"), ("notifications pipeline", "service"), ("Vault API", "api")],
     [("notifications pipeline", "Vault Transit", "USES"), ("Vault Transit", "Vault API", "COMMUNICATES_WITH")],
     "which Vault engine gives the notifications pipeline encryption without ever holding the key itself",
     "vault transit encryption service notification pipeline ciphertext api"),
    # --- 27 ---
    ("Short-lived credentials are the default for every human session; an SSO-issued token exchanges for a 1-hour AWS STS pair and the old access-key-on-laptop pattern is banned by policy.", "preference", "technical", False,
     [("Short-lived credentials", "concept"), ("SSO", "method"), ("AWS STS", "service"), ("access-key-on-laptop", "pattern")],
     [("AWS STS", "access-key-on-laptop", "REPLACES")],
     "what is the default credential model for humans and which legacy pattern was banned by policy",
     "short lived credential sso sts access key laptop policy human"),
    # --- 28 ---
    ("IRSA bindings give each EKS pod a scoped IAM role through the cluster's OIDC provider; the nodegroup-wide instance role that used to grant everything got stripped of all non-node policies.", "architecture", "technical", False,
     [("IRSA", "method"), ("EKS", "platform"), ("IAM", "service"), ("OIDC", "protocol"), ("nodegroup", "concept")],
     [("EKS", "IRSA", "USES"), ("IRSA", "OIDC", "USES")],
     "how does IRSA scope IAM permissions per pod and which overly-wide role got trimmed down",
     "irsa eks iam oidc pod nodegroup instance role scope"),
    # --- 29 ---
    ("GKE Workload Identity maps the Kubernetes service account to a GCP service account through a 1:1 annotation; the older node-metadata token path is disabled cluster-wide.", "architecture", "technical", False,
     [("Workload Identity", "method"), ("GKE", "platform"), ("Kubernetes service account", "concept"), ("GCP service account", "concept"), ("node-metadata", "pattern")],
     [("GKE", "Workload Identity", "USES"), ("Workload Identity", "node-metadata", "REPLACES")],
     "what annotation model ties pods to GCP IAM on GKE and which legacy token route was turned off",
     "workload identity gke kubernetes gcp service account annotation metadata"),
    # --- 30 ---
    ("trufflehog runs on every push and on a nightly sweep of the full git history; the first sweep surfaced a years-old Slack webhook in a deleted branch that had never rotated.", "milestone", "technical", False,
     [("trufflehog", "tool"), ("git history", "concept"), ("Slack webhook", "api")],
     [("trufflehog", "Slack webhook", "PRODUCES")],
     "what did the first nightly trufflehog sweep surface across git history that had gone unrotated",
     "trufflehog git history slack webhook nightly sweep rotate deleted"),
    # --- 31 ---
    ("gitleaks is wired into the pre-commit hook and the CI gate; the pre-commit blocks locally, CI fails the PR, and a baseline file pins known false positives from third-party test fixtures.", "architecture", "technical", False,
     [("gitleaks", "tool"), ("pre-commit", "tool"), ("CI gate", "service"), ("baseline file", "file")],
     [("pre-commit", "gitleaks", "USES"), ("CI gate", "gitleaks", "USES")],
     "how does the gitleaks integration combine pre-commit and CI and what pins known false positives",
     "gitleaks pre commit ci gate pr baseline false positive fixture"),
    # --- 32 ---
    ("Secret rotation on a leaked key is a drill we run quarterly; the playbook rotates Vault, AWS IAM, and the GitHub deploy keys within fifteen minutes and logs the diff to the incident channel.", "preference", "technical", False,
     [("Vault", "tool"), ("AWS IAM", "service"), ("GitHub deploy keys", "api"), ("incident channel", "service")],
     [("Vault", "incident channel", "COMMUNICATES_WITH")],
     "which three secret surfaces does the quarterly rotation drill cover and what window does the playbook target",
     "rotation drill quarterly vault iam github deploy key incident"),
    # --- 33 ---
    ("Dynamic AWS credentials from Vault replaced the static IAM user for the data-pipeline; each run gets a scoped STS pair valid for the job duration and no longer.", "decision", "technical", False,
     [("Vault", "tool"), ("IAM user", "concept"), ("data-pipeline", "project"), ("STS", "service")],
     [("Vault", "IAM user", "REPLACES"), ("Vault", "STS", "PRODUCES")],
     "what took over from the long-lived IAM user inside the analytics job runs on each kickoff",
     "vault dynamic aws iam user sts data pipeline job duration"),
    # --- 34 ---
    ("Adopted SPIFFE IDs for workload identity across the service mesh; each workload gets an x509 SVID rotated every hour, and service-to-service mTLS uses the SVID as the trust anchor.", "architecture", "technical", False,
     [("SPIFFE", "framework"), ("SVID", "concept"), ("service mesh", "pattern"), ("mTLS", "protocol")],
     [("service mesh", "SPIFFE", "USES"), ("mTLS", "SVID", "USES")],
     "how does SPIFFE identify workloads in the service mesh and what trust anchor does mTLS rely on",
     "spiffe svid service mesh mtls x509 workload identity rotate"),
    # --- 35 ---
    ("Vault audit logs ship to Loki with a retention of one year on the encrypted bucket; any detect-secret tool that fires also opens a Linear ticket through the audit webhook.", "architecture", "technical", False,
     [("Vault", "tool"), ("Loki", "service"), ("Linear", "service"), ("audit webhook", "api")],
     [("Vault", "Loki", "COMMUNICATES_WITH"), ("audit webhook", "Linear", "COMMUNICATES_WITH")],
     "where do Vault audit logs ship and what happens when a leak-detection tool fires an event",
     "vault audit log loki linear ticket retention webhook encrypted bucket"),
    # --- 36 ---
    ("The Parameter Store SecureString tier uses KMS-backed envelope encryption; the cheaper Standard tier is prohibited for anything that would appear in a legal hold, since it's plaintext.", "preference", "technical", False,
     [("Parameter Store", "service"), ("SecureString", "concept"), ("KMS", "service"), ("Standard tier", "concept")],
     [("SecureString", "KMS", "USES")],
     "which Parameter Store tier is the default and why is the Standard tier off-limits for legal-hold data",
     "parameter store securestring kms standard tier legal hold"),
    # --- 37 ---
    ("AWS Secrets Manager rotation lambdas live in the same account as the secret to avoid cross-account trust sprawl; the pattern was codified after the last drift audit flagged three orphaned roles.", "decision", "technical", False,
     [("AWS Secrets Manager", "service"), ("rotation lambda", "service"), ("drift audit", "event"), ("orphaned roles", "pattern")],
     [("rotation lambda", "AWS Secrets Manager", "SUPPORTS")],
     "why do Secrets Manager rotation lambdas live in the secret's own account and what audit triggered the rule",
     "aws secrets manager rotation lambda account cross trust drift orphan"),
    # --- 38 ---
    ("SOPS ages-encrypted file pattern supports multiple recipients; the CI age key and each platform engineer's age public key are listed, so revoking a leaver is a delete-and-rekey run.", "architecture", "technical", False,
     [("SOPS", "tool"), ("age", "tool"), ("CI", "service"), ("platform engineer", "person")],
     [("SOPS", "age", "USES")],
     "how does SOPS handle multiple recipients and what is the offboarding flow when a platform engineer leaves",
     "sops age recipient ci public key engineer offboard revoke rekey"),
    # --- 39 ---
    ("The External Secrets Operator ClusterSecretStore is scoped by AWS account via IRSA; ESO in the staging cluster cannot reach prod secrets even if someone misconfigures a namespace binding.", "architecture", "technical", False,
     [("External Secrets Operator", "tool"), ("ClusterSecretStore", "api"), ("IRSA", "method"), ("staging cluster", "infrastructure")],
     [("External Secrets Operator", "IRSA", "USES")],
     "how does the ESO ClusterSecretStore get scoped per account so staging cannot reach prod secrets",
     "eso cluster secret store irsa staging prod account namespace scope"),
    # --- 40 ---
    ("Picked CSI Secrets Store over External Secrets Operator for the HPC workload because the pod mounts the Vault lease directly and no native Kubernetes Secret object is ever created for scanners to exfiltrate.", "decision", "technical", False,
     [("CSI Secrets Store", "tool"), ("External Secrets Operator", "tool"), ("HPC", "platform"), ("Kubernetes Secret", "api"), ("Vault", "tool")],
     [("CSI Secrets Store", "External Secrets Operator", "PREFERS")],
     "why did the HPC workload pick CSI Secrets Store over External Secrets Operator",
     "csi secrets store eso hpc kubernetes secret vault mount scanner"),
    # --- 41 ---
    ("Vault Transit keys use the convergent_encryption option for the dedupe index so identical plaintext yields identical ciphertext; the trade-off was documented since it leaks equality information.", "reference", "technical", False,
     [("Vault Transit", "service"), ("convergent_encryption", "config"), ("dedupe index", "pattern")],
     [("Vault Transit", "convergent_encryption", "CONFIGURES")],
     "which Vault Transit option backs the dedupe index and what information does it leak",
     "vault transit convergent encryption dedupe index equality leak"),
    # --- 42 ---
    ("Secret-zero bootstrap is an IRSA-issued token that unwraps a short-lived Vault wrapping token; the pattern avoids ever shipping a Vault root token to CI in any form.", "architecture", "technical", False,
     [("Secret-zero", "concept"), ("IRSA", "method"), ("Vault", "tool"), ("wrapping token", "concept"), ("CI", "service")],
     [("IRSA", "wrapping token", "PRODUCES")],
     "how does the secret-zero bootstrap avoid shipping a Vault root token into CI workflows",
     "secret zero bootstrap irsa vault wrapping token ci root avoid"),
    # --- 43. noise ---
    ("Building security left a sticky note saying the door sensor thinks the bike rack is a tailgater and won't stop chirping after 6pm.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("SOPS with GCP KMS encrypts the Terraform state backend config; the state bucket itself is also CMEK-encrypted so two independent keys have to fail for the plaintext to leak.", "architecture", "technical", False,
     [("SOPS", "tool"), ("GCP KMS", "service"), ("Terraform", "tool"), ("CMEK", "concept")],
     [("SOPS", "GCP KMS", "USES"), ("Terraform", "SOPS", "USES")],
     "how does the SOPS plus GCP KMS layer plus CMEK bucket achieve two-key failure independence",
     "sops gcp kms terraform state cmek bucket independent key fail"),
    # --- 45 ---
    ("Hit a Vault outage last quarter when the Raft cluster lost quorum during a rolling AZ reboot; the fix pinned the leader to survive single-AZ loss and added a pre-reboot quorum check.", "problem", "technical", False,
     [("Vault", "tool"), ("Raft", "algorithm"), ("quorum", "concept"), ("AZ reboot", "event")],
     [("Vault", "Raft", "USES"), ("Raft", "quorum", "HAS_PART")],
     "which Vault HA incident hit last quarter and what guard rails now protect quorum across AZ reboots",
     "vault raft quorum az reboot outage pin leader pre check"),
    # --- 46 ---
    ("Doppler integration with Vercel replaced a hand-maintained env list on each project; the project-to-environment mapping is now declared once and drift detection catches divergence in the next deploy.", "milestone", "technical", False,
     [("Doppler", "tool"), ("Vercel", "service"), ("drift detection", "pattern")],
     [("Doppler", "Vercel", "COMMUNICATES_WITH"), ("Doppler", "drift detection", "SUPPORTS")],
     "which Doppler to Vercel integration replaced per-project env lists and how is drift caught",
     "doppler vercel env list drift detection project environment map"),
    # --- 47 ---
    ("Infisical's secret scanning caught a committed Stripe key in the monorepo within twenty seconds of the push; the block-on-push policy landed the same week as a team-wide rule.", "milestone", "technical", False,
     [("Infisical", "tool"), ("Stripe", "service"), ("monorepo", "concept"), ("block-on-push", "pattern")],
     [("Infisical", "Stripe", "PRODUCES"), ("Infisical", "block-on-push", "IMPLEMENTS")],
     "which Infisical feature caught the Stripe key leak and what policy rolled out the same week",
     "infisical secret scan stripe monorepo block on push policy"),
    # --- 48 ---
    ("The 1Password Connect server runs on-prem for the regulated workload; SDK calls stay inside the VPC and the cloud-hosted 1Password vaults sync only the items flagged for automation use.", "architecture", "technical", False,
     [("1Password Connect", "service"), ("1Password", "service"), ("VPC", "infrastructure"), ("regulated workload", "project")],
     [("1Password Connect", "1Password", "COMMUNICATES_WITH"), ("regulated workload", "1Password Connect", "USES")],
     "how does 1Password Connect keep SDK traffic on-prem while still syncing the automation items",
     "1password connect on prem vpc regulated workload sync automation"),
    # --- 49 ---
    ("Bitwarden export-on-offboard is scripted; the script rotates the departing engineer's items into the team vault and invalidates their device keys on the same run, auditable through the admin console.", "fact", "technical", False,
     [("Bitwarden", "tool"), ("team vault", "concept"), ("admin console", "tool"), ("device keys", "concept")],
     [("Bitwarden", "admin console", "HAS_PART")],
     "how does the Bitwarden offboarding script rotate items and invalidate device keys in one audited pass",
     "bitwarden offboard export rotate team vault device key admin"),
    # --- 50 ---
    ("Published the secrets-management runbook covering Vault, AWS Secrets Manager, SOPS, and age; the one-page version lists which tool owns which surface so engineers stop mixing SOPS into runtime pulls.", "reference", "technical", False,
     [("secrets-management runbook", "publication"), ("Vault", "tool"), ("AWS Secrets Manager", "service"), ("SOPS", "tool"), ("age", "tool")],
     [("secrets-management runbook", "Vault", "APPLIES_TO"), ("secrets-management runbook", "SOPS", "APPLIES_TO")],
     "which document maps tools to surfaces so engineers stop mixing SOPS into runtime secret pulls",
     "secrets management runbook vault aws sops age surface tool"),
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
