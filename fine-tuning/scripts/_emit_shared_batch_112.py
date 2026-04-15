"""One-off emitter for shared-base batch-112 — technical domain (IaC and provisioning).

Writes 50 rows to data/v2/shared/batch_112.tmp.jsonl with ids shared-05551..05600.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_112.tmp.jsonl"
ID_OFFSET = 5550

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("OpenTofu replaced Terraform on the platform repo after the BSL license change; the state files and provider blocks migrated without edits.", "decision", "technical", False,
     [("OpenTofu", "tool"), ("Terraform", "tool"), ("BSL", "concept")],
     [("OpenTofu", "Terraform", "REPLACES")],
     "which IaC tool took over from Terraform after the license change",
     "fork license state migration provider block swap platform"),
    # --- 2 ---
    ("Pulumi with TypeScript replaced HCL modules on the networking stack; typed interfaces caught two dangling subnet references at compile time.", "decision", "technical", False,
     [("Pulumi", "tool"), ("TypeScript", "language"), ("HCL", "language")],
     [("Pulumi", "HCL", "IMPROVES_ON")],
     "which IaC language displaced HCL on the networking stack and why",
     "typed language compile check subnet dangle module swap"),
    # --- 3 ---
    ("AWS CDK in Python built the data-platform VPC and EKS cluster; the L3 constructs bundled IAM and security-group defaults that the raw CloudFormation templates kept getting wrong.", "architecture", "technical", False,
     [("AWS CDK", "framework"), ("Python", "language"), ("VPC", "service"), ("EKS", "service"), ("CloudFormation", "service"), ("IAM", "service")],
     [("AWS CDK", "CloudFormation", "IMPROVES_ON")],
     "which framework took over CloudFormation for the data-platform VPC stack",
     "high level construct default bundle IAM security group wrap"),
    # --- 4 ---
    ("CDK for Terraform ran the Pulumi-to-Terraform bridge on the multi-cloud stack; Python constructs rendered HCL so the existing Atlantis workflow kept working.", "decision", "technical", False,
     [("CDK for Terraform", "framework"), ("Pulumi", "tool"), ("Terraform", "tool"), ("Python", "language"), ("HCL", "language"), ("Atlantis", "tool")],
     [("CDK for Terraform", "Pulumi", "REPLACES")],
     "which framework bridged typed code back to HCL for the Atlantis flow",
     "CDKTF bridge HCL render Python Atlantis workflow keep"),
    # --- 5 ---
    ("Crossplane on the control-plane cluster replaced a home-grown Go operator for RDS provisioning; composition functions reconciled the database claim into a ready snapshot policy.", "decision", "technical", False,
     [("Crossplane", "framework"), ("Go", "language"), ("RDS", "service")],
     [("Crossplane", "Go", "REPLACES")],
     "which platform retired the custom Go operator for RDS provisioning",
     "control plane composition claim database reconcile operator"),
    # --- 6 ---
    ("Argo CD replaced Flux v1 on the main production cluster; the App-of-Apps pattern handled the 140 workloads better than the Flux Helm operator of the day.", "decision", "technical", False,
     [("Argo CD", "tool"), ("Flux v1", "tool"), ("Helm", "tool")],
     [("Argo CD", "Flux v1", "REPLACES")],
     "which GitOps controller took over from Flux v1 on the main cluster",
     "App of Apps pattern production migration controller swap"),
    # --- 7 ---
    ("Flux v2 landed on the edge clusters after the Argo CD audit; the Kustomize-native reconciler suited the small footprint better than Argo's UI-first model.", "decision", "technical", False,
     [("Flux v2", "tool"), ("Argo CD", "tool"), ("Kustomize", "tool")],
     [("Flux v2", "Argo CD", "REPLACES")],
     "which GitOps reconciler won the edge cluster slot over Argo CD",
     "edge footprint Kustomize native small install controller"),
    # --- 8 ---
    ("Ansible playbooks still ran the bare-metal bootstrap on the Proxmox hypervisors; Terraform could not cross the DHCP PXE step without a separate agent.", "fact", "technical", False,
     [("Ansible", "tool"), ("Proxmox", "service"), ("Terraform", "tool"), ("PXE", "protocol")],
     [],
     "which tool owned the bare-metal bootstrap that Terraform could not reach",
     "bare metal bootstrap PXE DHCP hypervisor agent gap"),
    # --- 9 ---
    ("SaltStack replaced Puppet on the Windows fleet; reactor events handled the AD-triggered reconfiguration faster than Puppet's 30-minute agent cycle.", "decision", "technical", False,
     [("SaltStack", "tool"), ("Puppet", "tool"), ("Windows", "platform"), ("AD", "service")],
     [("SaltStack", "Puppet", "REPLACES")],
     "which config manager displaced Puppet on the Windows fleet and why",
     "reactor event AD trigger agent cycle Windows fleet swap"),
    # --- 10. noise ---
    ("Hold on, the plan is still running.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Chef Infra kept the compliance baseline on the regulated subset; InSpec profiles were the auditor's reference artifact for the SOC 2 evidence pack.", "reference", "technical", False,
     [("Chef Infra", "tool"), ("InSpec", "tool"), ("SOC 2", "concept")],
     [],
     "which compliance tool produced the SOC 2 evidence profile",
     "baseline compliance profile auditor evidence regulated subset"),
    # --- 12 ---
    ("NixOS flakes built the reproducible developer laptop image; the lock file pinned 230 inputs so the 'works on my machine' drift disappeared.", "architecture", "technical", False,
     [("NixOS", "platform"), ("flakes", "technology")],
     [],
     "which build system froze the reproducible laptop image inputs",
     "reproducible lock input pin drift developer laptop image"),
    # --- 13 ---
    ("Nix replaced a shell-based bootstrap on the CI runner fleet; the derivation graph let cold runners warm from a binary cache in under 30 seconds.", "decision", "technical", False,
     [("Nix", "tool"), ("CI", "infrastructure")],
     [("Nix", "CI", "IMPROVES_ON")],
     "which tool replaced the shell bootstrap on the CI runners",
     "derivation graph binary cache cold runner warm bootstrap"),
    # --- 14 ---
    ("Packer baked the golden AMI for the autoscaling group; the HCL2 template ran goss tests inside the build before AWS took the snapshot.", "architecture", "technical", False,
     [("Packer", "tool"), ("AMI", "service"), ("HCL2", "language"), ("goss", "tool"), ("AWS", "organization")],
     [],
     "which tool produced the tested golden AMI for the autoscaling group",
     "golden image template test snapshot autoscaling build bake"),
    # --- 15 ---
    ("Docker buildx with the containerd image store replaced the legacy docker build on the multi-arch pipeline; arm64 and amd64 manifests landed in one push.", "decision", "technical", False,
     [("Docker buildx", "tool"), ("containerd", "technology"), ("arm64", "technology"), ("amd64", "technology")],
     [("Docker buildx", "containerd", "BUILDS_ON")],
     "which build tool delivered the multi-arch manifest in a single push",
     "multi arch manifest build image store legacy build swap"),
    # --- 16 ---
    ("BuildKit cache mounts cut Rust dependency rebuilds from nine minutes to under 40 seconds; the cargo registry lived in a persistent type=cache directory.", "milestone", "technical", False,
     [("BuildKit", "tool"), ("Rust", "language")],
     [],
     "which BuildKit feature cut the Rust dependency rebuild time",
     "cache mount persistent cargo registry dependency rebuild"),
    # --- 17 ---
    ("Earthly replaced a tangled Makefile plus Dockerfile combo on the monorepo; the Earthfile syntax expressed target dependencies without re-implementing make in Bash.", "decision", "technical", False,
     [("Earthly", "tool"), ("Dockerfile", "technology"), ("Makefile", "technology"), ("Bash", "language")],
     [("Earthly", "Makefile", "REPLACES")],
     "which build tool displaced the Makefile plus Dockerfile tangle",
     "monorepo target dependency express Bash avoid build swap"),
    # --- 18 ---
    ("cloud-init wrote the per-host seed on the Hetzner bare-metal order; the userdata injected the SSH trust anchor and Ansible pull URL on first boot.", "architecture", "technical", False,
     [("cloud-init", "tool"), ("Hetzner", "organization"), ("SSH", "protocol"), ("Ansible", "tool")],
     [],
     "which tool seeded the Hetzner hosts on first boot with SSH trust",
     "userdata first boot seed trust anchor pull URL order"),
    # --- 19 ---
    ("Terraform workspaces were dropped in favor of directory-per-environment layout; the shared state contention during concurrent apply was the deciding factor.", "decision", "technical", False,
     [("Terraform", "tool")],
     [],
     "which layout replaced Terraform workspaces on the environment split",
     "workspace directory layout concurrent apply state lock swap"),
    # --- 20 ---
    ("Terragrunt replaced hand-copied tfvars across the 14 Terraform account stacks; the include blocks killed 2000 lines of duplicated provider configuration.", "decision", "technical", False,
     [("Terragrunt", "tool"), ("Terraform", "tool")],
     [("Terragrunt", "Terraform", "IMPROVES_ON")],
     "which wrapper killed the duplicated tfvars across the 14 account stacks",
     "include block provider duplication account stack wrapper swap"),
    # --- 21 ---
    ("Atlantis drove the Terraform plan-and-apply on pull requests; the per-project lock file stopped two engineers from stepping on the same state at once.", "architecture", "technical", False,
     [("Atlantis", "tool"), ("Terraform", "tool")],
     [],
     "which CI tool serialized Terraform plan and apply on pull requests",
     "pull request lock plan apply state guard concurrent serialize"),
    # --- 22 ---
    ("Spacelift was evaluated against Atlantis for the platform team; the policy-as-code with OPA and drift detection tipped it over the free tool on compliance grounds.", "decision", "technical", False,
     [("Spacelift", "service"), ("Atlantis", "tool"), ("OPA", "tool")],
     [("Spacelift", "Atlantis", "REPLACES")],
     "which managed service replaced Atlantis on the platform compliance stack",
     "policy as code drift detection compliance ground platform swap"),
    # --- 23 ---
    ("Drift detection on the production state ran every 30 minutes; the Slack notifier surfaced a manual security-group edit within one cycle.", "architecture", "technical", False,
     [("Slack", "service")],
     [],
     "which cadence caught the manual security-group edit on production state",
     "drift cycle notifier surface manual edit state scan"),
    # --- 24 ---
    ("S3 plus DynamoDB locking backed the Terraform state backend; the versioning on the bucket was the only reason the accidental rm -rf recovered.", "architecture", "technical", False,
     [("S3", "service"), ("DynamoDB", "database"), ("Terraform", "tool")],
     [],
     "which state backend saved the Terraform state after the accidental delete",
     "remote state bucket lock version rollback recover backend"),
    # --- 25 ---
    ("Terraform Cloud was rejected for the state backend on cost; self-hosted S3 and DynamoDB ran at 2 percent of the per-user license with no HCP lock-in.", "decision", "technical", False,
     [("Terraform Cloud", "service"), ("S3", "service"), ("DynamoDB", "database"), ("HCP", "service")],
     [],
     "why did the team reject Terraform Cloud as the state backend",
     "per user license cost lock in self host state backend reject"),
    # --- 26 ---
    ("HashiCorp Vault provider in Terraform reconciled dynamic database credentials; the lease TTL flowed into the app config through consul-template on boot.", "architecture", "technical", False,
     [("HashiCorp Vault", "service"), ("Terraform", "tool"), ("consul-template", "tool")],
     [("Terraform", "HashiCorp Vault", "USES")],
     "which provider issued the dynamic database credentials at boot",
     "dynamic credential lease TTL template config boot provider"),
    # --- 27 ---
    ("Red Hat Satellite provisioned the RHEL patch baseline; the content views pinned errata so the monthly CVE batch landed identically on 300 hosts.", "architecture", "technical", False,
     [("Red Hat Satellite", "tool"), ("RHEL", "platform"), ("CVE", "concept")],
     [],
     "which Red Hat tool pinned the monthly RHEL errata across 300 hosts",
     "content view errata pin CVE patch baseline host identical"),
    # --- 28 ---
    ("Ansible Automation Platform replaced a self-hosted AWX tower; the execution environments decoupled collection dependencies from the control node Python.", "decision", "technical", False,
     [("Ansible Automation Platform", "tool"), ("AWX", "tool"), ("Python", "language")],
     [("Ansible Automation Platform", "AWX", "REPLACES")],
     "which Red Hat product took over from the self-hosted AWX tower",
     "execution environment collection isolate control Python tower"),
    # --- 29 ---
    ("Atlassian Bamboo specs in Java built the legacy CI as code; the migration to Bitbucket Pipelines YAML dropped 1200 lines and one Oracle JDK dependency.", "decision", "technical", False,
     [("Atlassian Bamboo", "service"), ("Java", "language"), ("Bitbucket Pipelines", "service"), ("Oracle", "organization"), ("JDK", "technology")],
     [("Bitbucket Pipelines", "Atlassian Bamboo", "REPLACES")],
     "which Atlassian product displaced the Bamboo specs pipeline",
     "specs YAML pipeline JDK dependency drop legacy CI swap"),
    # --- 30 ---
    ("Juju charms ran the OpenStack control plane on the lab cluster; the bundle file replaced a 400-line Heat template for the integration set.", "decision", "technical", False,
     [("Juju", "tool"), ("OpenStack", "platform"), ("Heat", "tool")],
     [("Juju", "Heat", "REPLACES")],
     "which Canonical tool replaced the OpenStack Heat template on the lab",
     "charm bundle integration control plane template swap lab"),
    # --- 31 ---
    ("MAAS handled the PXE-based bare-metal layer under Juju; the commissioning step tagged the NUMA layout into the machine metadata automatically.", "architecture", "technical", False,
     [("MAAS", "tool"), ("Juju", "tool"), ("PXE", "protocol"), ("NUMA", "technology")],
     [],
     "which Canonical tool commissioned the bare-metal hosts for Juju",
     "PXE commission NUMA tag metadata bare metal layer stack"),
    # --- 32 ---
    ("Foreman plus Puppet ran the legacy data center; the bare-metal build DB stayed the source of truth for two years after Terraform landed on the cloud side.", "fact", "technical", False,
     [("Foreman", "tool"), ("Puppet", "tool"), ("Terraform", "tool")],
     [],
     "which bare-metal pair kept running after Terraform owned the cloud side",
     "legacy data center source of truth build database split"),
    # --- 33 ---
    ("Terraform provider aws at v5.70 was pinned through the fleet; the auto-upgrade on v6 broke the default encryption flag on new S3 buckets.", "problem", "technical", False,
     [("Terraform", "tool"), ("aws", "technology"), ("S3", "service")],
     [],
     "which Terraform provider version was pinned after the v6 regression",
     "provider pin version encryption flag regression bucket fleet"),
    # --- 34. noise ---
    ("Sorry, my coffee just finished brewing.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Pulumi ESC replaced a vaulted dotenv loader on the Go services; the stack config encrypted per environment and resolved at pulumi up time.", "decision", "technical", False,
     [("Pulumi ESC", "service"), ("Go", "language")],
     [("Pulumi ESC", "Go", "REPLACES")],
     "which Pulumi feature displaced the dotenv loader on the Go services",
     "stack config encrypt environment resolve dotenv loader swap"),
    # --- 36 ---
    ("Helm charts drove the application layer under Argo CD; the values.yaml per environment kept the render deterministic across the four clusters.", "architecture", "technical", False,
     [("Helm", "tool"), ("Argo CD", "tool")],
     [("Argo CD", "Helm", "USES")],
     "which templating engine fed Argo CD for the application layer",
     "chart values environment deterministic render cluster fleet"),
    # --- 37 ---
    ("Kustomize overlays were preferred over Helm for the platform-owned CRDs; the patch semantics felt safer than free-form string templating at that layer.", "preference", "technical", False,
     [("Kustomize", "tool"), ("Helm", "tool"), ("CRDs", "technology")],
     [("Kustomize", "Helm", "PREFERS")],
     "which overlay tool was preferred over Helm for the platform CRDs",
     "patch semantics string template CRD layer safer preference"),
    # --- 38 ---
    ("Argo CD ApplicationSet generated the per-tenant namespace from a git list generator; adding a tenant was a three-line merge, not a cluster rollout.", "architecture", "technical", False,
     [("Argo CD", "tool"), ("ApplicationSet", "technology")],
     [],
     "which Argo CD primitive generated the per-tenant namespace from git",
     "list generator tenant namespace merge rollout cluster scale"),
    # --- 39 ---
    ("Flux Helm controller replaced the legacy Tiller install on the lab cluster; the server-side render killed the cluster-admin service account that used to sit idle.", "decision", "technical", False,
     [("Flux Helm controller", "tool"), ("Tiller", "tool")],
     [("Flux Helm controller", "Tiller", "REPLACES")],
     "which controller retired the Tiller service account on the lab cluster",
     "server side render cluster admin service account retire lab"),
    # --- 40 ---
    ("Terraform import was used 14 times to bring hand-created RDS instances under state; the generated blocks feature in 1.5 cut the boilerplate significantly.", "milestone", "technical", False,
     [("Terraform", "tool"), ("RDS", "service")],
     [],
     "which Terraform feature simplified the mass RDS import",
     "import generated block hand create bring under state RDS"),
    # --- 41 ---
    ("The OpenTofu state encryption feature was adopted over Terraform for the payments-state bucket; the symmetric key lived in AWS KMS with a grant to the CI role only.", "decision", "technical", False,
     [("OpenTofu", "tool"), ("Terraform", "tool"), ("AWS KMS", "service"), ("CI", "infrastructure")],
     [("OpenTofu", "Terraform", "IMPROVES_ON")],
     "which OpenTofu feature locked the payments state file at rest",
     "state encryption symmetric KMS grant CI role bucket swap"),
    # --- 42 ---
    ("Chef Zero replaced a full Chef Server for the disconnected site; kitchen-ec2 runs verified the cookbook set without phoning home.", "decision", "technical", False,
     [("Chef Zero", "tool"), ("Chef Server", "tool")],
     [("Chef Zero", "Chef Server", "REPLACES")],
     "which Chef mode ran the disconnected site without the full server",
     "disconnected site cookbook verify no phone home lightweight"),
    # --- 43 ---
    ("Packer ISO builder produced the Proxmox VM template for the Windows workstation lab; the Ansible provisioner domain-joined the machine before the template snapshot.", "architecture", "technical", False,
     [("Packer", "tool"), ("Proxmox", "service"), ("Windows", "platform"), ("Ansible", "tool")],
     [],
     "which Packer builder produced the Windows Proxmox template",
     "ISO builder VM template domain join snapshot provisioner"),
    # --- 44 ---
    ("Red Hat Ansible collections from Automation Hub replaced ad-hoc roles on the network fleet; the supported collection got CVE response lanes the community roles did not.", "decision", "technical", False,
     [("Red Hat Ansible", "tool"), ("Automation Hub", "service"), ("CVE", "concept")],
     [("Red Hat Ansible", "Automation Hub", "USES")],
     "which Red Hat channel replaced the ad-hoc community roles on network",
     "collection support CVE lane network fleet community role swap"),
    # --- 45 ---
    ("HashiCorp Waypoint was rejected for the deploy orchestration after the BSL shift; Argo CD plus Crossplane covered the same shape without the license clause.", "decision", "technical", False,
     [("HashiCorp Waypoint", "tool"), ("Argo CD", "tool"), ("Crossplane", "framework"), ("BSL", "concept")],
     [("Argo CD", "HashiCorp Waypoint", "REPLACES")],
     "why did the team reject Waypoint for the deploy orchestration slot",
     "license clause deploy orchestration shape reject BSL swap"),
    # --- 46 ---
    ("Pulumi automation API drove the tenant-onboarding service; the Go SDK invoked stack create inline so the webhook returned inside 10 seconds.", "architecture", "technical", False,
     [("Pulumi", "tool"), ("Go", "language")],
     [],
     "which Pulumi feature ran tenant onboarding inline from the service",
     "automation API SDK inline stack webhook tenant onboard Go"),
    # --- 47 ---
    ("Terraform test with the 1.6 framework ran plan assertions in CI; the checks caught a security-group rule regression before a single apply hit the sandbox.", "milestone", "technical", False,
     [("Terraform", "tool"), ("CI", "infrastructure")],
     [],
     "which Terraform feature caught the security-group rule regression in CI",
     "test framework plan assertion regression sandbox catch guard"),
    # --- 48 ---
    ("Nix home-manager was preferred over Ansible for per-user developer config; atomic generations made rollback a single switch command after a bad Neovim config.", "preference", "technical", False,
     [("Nix", "tool"), ("home-manager", "tool"), ("Ansible", "tool"), ("Neovim", "tool")],
     [("home-manager", "Ansible", "PREFERS")],
     "which tool was preferred over Ansible for per-user developer config",
     "atomic generation rollback switch user config developer prefer"),
    # --- 49 ---
    ("Puppet Bolt replaced ad-hoc SSH scripts for the DR runbook on the legacy fleet; the declarative plan ran idempotently when the initial network split stalled it mid-way.", "decision", "technical", False,
     [("Puppet Bolt", "tool"), ("SSH", "protocol"), ("DR", "concept")],
     [("Puppet Bolt", "SSH", "REPLACES")],
     "which Puppet tool replaced ad-hoc SSH for the legacy DR runbook",
     "declarative plan idempotent network split resume runbook swap"),
    # --- 50 ---
    ("The platform IaC cut-over landed on 2026-04-07; OpenTofu plus Argo CD plus Crossplane replaced the Terraform plus Flux v1 plus custom-operator stack across 11 clusters.", "milestone", "technical", False,
     [("OpenTofu", "tool"), ("Argo CD", "tool"), ("Crossplane", "framework"), ("Terraform", "tool"), ("Flux v1", "tool"), ("2026-04-07", "date")],
     [("OpenTofu", "Terraform", "REPLACES"), ("Argo CD", "Flux v1", "REPLACES")],
     "when did the platform IaC cut-over land and what stack replaced the old one",
     "cut over stack replace cluster fleet date platform IaC"),
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
