"""One-off emitter for shared-base batch-195 — technical domain (infrastructure as code: Terraform, OpenTofu, Pulumi, CDK, CloudFormation, Bicep, Ansible, Chef, Puppet, Salt, Nix, Kustomize, Helm, Terragrunt, Atlantis, Spacelift, drift detection, state locking, lifecycle).

Writes 50 rows to data/v2/shared/batch_195.tmp.jsonl with ids shared-09701..09750.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_195.tmp.jsonl"
ID_OFFSET = 9700

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Forked the root module off Terraform 1.5 onto OpenTofu 1.7 after the license flip; the state file format stayed compatible and the provider registry mirror landed behind our internal Artifactory.", "decision", "technical", False,
     [("Terraform", "tool"), ("OpenTofu", "tool"), ("Artifactory", "service"), ("provider registry", "concept")],
     [("OpenTofu", "Terraform", "REPLACES"), ("OpenTofu", "Artifactory", "DEPENDS_ON")],
     "why did the team move the root module from Terraform to OpenTofu and what stayed the same",
     "opentofu terraform fork license state file provider registry artifactory"),
    # --- 2 decision ---
    ("Multi-account AWS layout uses Terragrunt with a live repo structure where each account has an env folder and a component folder; remote state lives in a per-account S3 bucket with DynamoDB locking.", "decision", "technical", False,
     [("Terragrunt", "tool"), ("AWS", "platform"), ("S3", "service"), ("DynamoDB", "database"), ("remote state", "concept")],
     [("Terragrunt", "S3", "USES"), ("Terragrunt", "DynamoDB", "USES"), ("remote state", "DynamoDB", "DEPENDS_ON")],
     "how is the Terragrunt live repo laid out across AWS accounts and where does state locking happen",
     "terragrunt aws account env component s3 dynamodb remote state lock"),
    # --- 3 problem ---
    ("State lock hung for forty minutes after a runner crashed mid-apply; force-unlock cleared the DynamoDB item once the orphan lease was confirmed in the audit log and the next plan ran clean.", "problem", "technical", False,
     [("DynamoDB", "database"), ("force-unlock", "command"), ("State lock", "concept"), ("audit log", "concept")],
     [("force-unlock", "State lock", "FIXES")],
     "how did the team recover after a runner crash left a Terraform state lock stuck on DynamoDB",
     "state lock force unlock dynamodb runner crash orphan lease audit"),
    # --- 4 decision ---
    ("Chose Pulumi with TypeScript over CDKTF for the edge team; the CDKTF abstraction still leaks Terraform HCL nuances on import whereas Pulumi's native resource model stayed consistent across stacks.", "decision", "technical", False,
     [("Pulumi", "tool"), ("TypeScript", "language"), ("CDKTF", "tool"), ("HCL", "language")],
     [("Pulumi", "CDKTF", "PREFERS"), ("CDKTF", "HCL", "DEPENDS_ON")],
     "why did the edge team pick Pulumi TypeScript over CDKTF for their stack definitions",
     "pulumi typescript cdktf hcl edge team stack resource model abstraction"),
    # --- 5 fact ---
    ("The AWS CDK app synthesises to CloudFormation and deploys via the bootstrap stack's cdk-assets S3 bucket; the app layer is TypeScript and the construct library is pinned at aws-cdk-lib 2.140.", "fact", "technical", False,
     [("AWS CDK", "framework"), ("CloudFormation", "service"), ("cdk-assets", "tool"), ("S3", "service"), ("aws-cdk-lib", "library"), ("TypeScript", "language")],
     [("AWS CDK", "CloudFormation", "PRODUCES"), ("AWS CDK", "cdk-assets", "USES")],
     "which CDK pipeline stage writes assets to S3 and at what version is the construct library pinned",
     "aws cdk cloudformation cdk assets s3 bootstrap typescript aws cdk lib"),
    # --- 6 architecture ---
    ("Terraform modules are organised as a monorepo with a modules/ root and a stacks/ root; each stack composes modules through a thin wrapper and pins versions via the terraform block required_providers.", "architecture", "technical", False,
     [("Terraform", "tool"), ("monorepo", "pattern"), ("required_providers", "config"), ("modules", "concept"), ("stacks", "concept")],
     [("stacks", "modules", "DEPENDS_ON"), ("stacks", "required_providers", "USES")],
     "how are Terraform modules and stacks laid out in the monorepo and where are provider versions pinned",
     "terraform monorepo modules stacks required providers version pin wrapper"),
    # --- 7 milestone ---
    ("Migrated the legacy CloudFormation stacks into a Terraform import workflow; thirty-two stacks rehydrated into the new state file over a weekend run with zero resource replacement after the moved blocks landed.", "milestone", "technical", False,
     [("CloudFormation", "service"), ("Terraform", "tool"), ("import", "command"), ("moved blocks", "pattern"), ("state file", "concept")],
     [("Terraform", "CloudFormation", "REPLACES"), ("import", "state file", "APPLIES_TO")],
     "how did the legacy CloudFormation stacks move into Terraform without resource replacement",
     "cloudformation terraform import moved block state file legacy rehydrate"),
    # --- 8 decision ---
    ("Kubernetes manifests generate through Kustomize overlays rather than Helm charts for the platform team; the base plus overlay model gave cleaner diffs on review than templated YAML with Helm values.", "decision", "technical", False,
     [("Kubernetes", "platform"), ("Kustomize", "tool"), ("Helm", "tool"), ("overlay", "pattern"), ("values", "config")],
     [("Kustomize", "Helm", "PREFERS"), ("Kustomize", "overlay", "USES")],
     "why did the platform team pick Kustomize over Helm for generating Kubernetes manifests",
     "kustomize helm overlay base kubernetes manifest diff review values"),
    # --- 9 architecture ---
    ("Helm charts for application teams ship through a chart repository hosted on ChartMuseum behind the internal registry; Argo CD subscribes with targetRevision pins and auto-syncs to staging only.", "architecture", "technical", False,
     [("Helm", "tool"), ("ChartMuseum", "service"), ("Argo CD", "tool"), ("targetRevision", "config"), ("staging", "concept")],
     [("Argo CD", "ChartMuseum", "COMMUNICATES_WITH"), ("Helm", "ChartMuseum", "DEPLOYED_ON"), ("Argo CD", "Helm", "USES")],
     "how are application Helm charts distributed and which tool auto-syncs them to staging",
     "helm chartmuseum argo cd target revision pin staging auto sync registry"),
    # --- 10 noise ---
    ("The office plants need watering twice a week and someone labelled the cacti with names written in silver marker.", "fact", "noise", True, [], [], None, None),
    # --- 11 reference ---
    ("Pulled the lifecycle meta-argument guidance from the HashiCorp docs page on create_before_destroy; the recipe we follow for blue-green RDS replacements is straight out of that reference.", "reference", "technical", False,
     [("HashiCorp", "organization"), ("create_before_destroy", "config"), ("RDS", "service"), ("lifecycle", "concept")],
     [("create_before_destroy", "lifecycle", "IS_A"), ("create_before_destroy", "RDS", "APPLIES_TO")],
     "which HashiCorp doc covers the lifecycle recipe we lean on for blue-green RDS swaps",
     "hashicorp lifecycle create before destroy rds blue green replacement doc"),
    # --- 12 milestone ---
    ("Rolled out Atlantis for pull-request driven Terraform plans across the infra org; every PR now gets an automatic terraform plan comment and apply-after-merge replaced the manual CI button we had before.", "milestone", "technical", False,
     [("Atlantis", "tool"), ("Terraform", "tool"), ("pull-request", "concept"), ("terraform plan", "command"), ("CI", "infrastructure")],
     [("Atlantis", "Terraform", "USES"), ("Atlantis", "CI", "REPLACES")],
     "which tool now posts automated Terraform plans on pull requests and what manual step did it replace",
     "atlantis terraform pull request plan apply comment automate ci button"),
    # --- 13 preference ---
    ("Infra team prefers Bicep over ARM templates for all new Azure work; the resource symbolic references read cleaner and the compiler catches naming typos before the deployment reaches the management group.", "preference", "technical", False,
     [("Bicep", "language"), ("ARM templates", "language"), ("Azure", "platform"), ("management group", "concept")],
     [("Bicep", "ARM templates", "PREFERS"), ("Bicep", "Azure", "APPLIES_TO")],
     "which Azure IaC language does the infra team prefer for new work and why",
     "bicep arm template azure symbolic reference compiler typo management group"),
    # --- 14 architecture ---
    ("Ansible playbooks sit in a control-node-free Molecule-tested collection; each role ships with a converge.yml and a verify.yml, and the CI runner uses ansible-navigator against an execution environment image.", "architecture", "technical", False,
     [("Ansible", "tool"), ("Molecule", "tool"), ("ansible-navigator", "command"), ("execution environment", "concept"), ("role", "concept"), ("CI", "infrastructure")],
     [("Ansible", "Molecule", "USES"), ("ansible-navigator", "execution environment", "DEPENDS_ON"), ("CI", "ansible-navigator", "USES")],
     "how are Ansible roles tested and which runner command the CI uses against the execution environment",
     "ansible molecule role converge verify navigator execution environment ci"),
    # --- 15 decision ---
    ("Chef Infra got phased out in favour of Ansible and Nix for the bare-metal fleet; the ohai attribute ceremony and run-list opinions cost us more in review than they saved in convergence.", "decision", "technical", False,
     [("Chef Infra", "tool"), ("Ansible", "tool"), ("Nix", "tool"), ("ohai", "tool"), ("run-list", "concept")],
     [("Ansible", "Chef Infra", "REPLACES"), ("Nix", "Chef Infra", "REPLACES")],
     "which two tools took over from Chef Infra on the bare-metal fleet and what drove the replacement",
     "chef infra ansible nix bare metal ohai run list converge attribute"),
    # --- 16 fact ---
    ("Puppet still drives the Windows file-server fleet because the resource model handles ACL and registry keys more cleanly than anything we've tried; the puppetserver runs on-prem behind a local CA.", "fact", "technical", False,
     [("Puppet", "tool"), ("Windows", "platform"), ("puppetserver", "service"), ("ACL", "concept"), ("registry", "concept"), ("local CA", "infrastructure")],
     [("Puppet", "Windows", "APPLIES_TO"), ("puppetserver", "local CA", "DEPENDS_ON")],
     "why does Puppet stay in place for Windows file servers and where is the puppetserver hosted",
     "puppet windows file server acl registry puppetserver local ca on prem"),
    # --- 17 architecture ---
    ("Salt drives the event-reactive pieces of the network fabric; the salt-master on the jump host fans reactor events out to minions on the leaf switches, and the beacon subsystem trips on interface flaps.", "architecture", "technical", False,
     [("Salt", "tool"), ("salt-master", "service"), ("reactor", "concept"), ("beacon", "concept"), ("jump host", "infrastructure"), ("leaf switch", "infrastructure")],
     [("salt-master", "jump host", "DEPLOYED_ON"), ("reactor", "beacon", "DEPENDS_ON"), ("Salt", "leaf switch", "APPLIES_TO")],
     "how does Salt tie network fabric events into automated reactions across leaf switches",
     "salt master minion reactor beacon jump host leaf switch network fabric"),
    # --- 18 decision ---
    ("Adopted Nix with nixos-rebuild for the build-farm images; reproducibility and binary cache speed made it worth the learning curve over a Packer plus Ansible combo we used to ship AMIs with.", "decision", "technical", False,
     [("Nix", "tool"), ("nixos-rebuild", "command"), ("Packer", "tool"), ("Ansible", "tool"), ("binary cache", "concept"), ("AMI", "concept")],
     [("Nix", "Packer", "REPLACES"), ("nixos-rebuild", "binary cache", "USES")],
     "why did the build farm switch from Packer and Ansible to Nix with nixos-rebuild",
     "nix nixos rebuild packer ansible binary cache ami reproducible image"),
    # --- 19 reference ---
    ("The Nickel docs page on merge semantics is what we hand to new engineers touching our config; the override priority rules there are easier to read than the equivalent section in the Nix manual.", "reference", "technical", False,
     [("Nickel", "language"), ("Nix", "tool"), ("merge semantics", "concept"), ("override priority", "concept")],
     [("Nickel", "merge semantics", "HAS_PART")],
     "which document anchors our onboarding explanation of config merge and override priority",
     "nickel nix merge semantics override priority docs onboarding config"),
    # --- 20 fact ---
    ("NixOps is still around for two legacy nodes that pre-date the flake migration; the deploy path is a single nixops deploy invocation wrapped by a make target and nobody touches it without senior review.", "fact", "technical", False,
     [("NixOps", "tool"), ("flake", "concept"), ("nixops deploy", "command"), ("make", "tool")],
     [("make", "nixops deploy", "USES")],
     "which legacy tool still deploys two pre-flake nodes and how is the command wrapped",
     "nixops flake legacy nixops deploy make target senior review wrap"),
    # --- 21 milestone ---
    ("Disnix handles the service-oriented deploy of the analytics cluster; a services.nix plus infrastructure.nix plus distribution.nix triple describe what, where, and how the heterogeneous hosts converge.", "milestone", "technical", False,
     [("Disnix", "tool"), ("services.nix", "file"), ("infrastructure.nix", "file"), ("distribution.nix", "file"), ("analytics cluster", "project")],
     [("Disnix", "analytics cluster", "APPLIES_TO"), ("distribution.nix", "services.nix", "DEPENDS_ON"), ("distribution.nix", "infrastructure.nix", "DEPENDS_ON")],
     "which three files describe the disnix deploy of the analytics cluster and how do they split concerns",
     "disnix services infrastructure distribution nix analytics cluster deploy"),
    # --- 22 decision ---
    ("Dropped the Serverless Framework and consolidated onto AWS SAM for the Lambda-heavy side of the stack; SAM's native CloudFormation story played nicer with our existing drift detection tooling.", "decision", "technical", False,
     [("Serverless Framework", "tool"), ("AWS SAM", "tool"), ("Lambda", "service"), ("CloudFormation", "service"), ("drift detection", "concept")],
     [("AWS SAM", "Serverless Framework", "REPLACES"), ("AWS SAM", "CloudFormation", "USES"), ("drift detection", "CloudFormation", "APPLIES_TO")],
     "why did the Lambda side consolidate from Serverless Framework onto AWS SAM",
     "serverless framework aws sam lambda cloudformation drift detection consolidate"),
    # --- 23 problem ---
    ("Terraform drift snuck into the IAM role inline policies because a sibling team edited through the console; tfexec's plan-json diff plus a weekly drift pipeline now alerts before the next apply inherits the change.", "problem", "technical", False,
     [("Terraform", "tool"), ("IAM", "service"), ("tfexec", "library"), ("drift pipeline", "project"), ("plan-json", "concept")],
     [("tfexec", "drift pipeline", "USES"), ("drift pipeline", "Terraform", "APPLIES_TO")],
     "how does the team catch IAM drift from console edits before the next Terraform apply inherits it",
     "terraform drift iam role inline policy tfexec plan json pipeline alert"),
    # --- 24 milestone ---
    ("Spacelift replaced our home-grown Terraform runner after the third concurrency-bug incident; the managed stack-dependency DAG plus VCS-driven policy cut the on-call page count in half inside a month.", "milestone", "technical", False,
     [("Spacelift", "tool"), ("Terraform", "tool"), ("VCS", "concept"), ("DAG", "concept"), ("on-call", "concept")],
     [("Spacelift", "Terraform", "USES"), ("Spacelift", "DAG", "HAS_PART")],
     "which managed runner replaced the home-grown Terraform system and what pain did it retire",
     "spacelift terraform runner stack dependency dag vcs policy on call page"),
    # --- 25 reference ---
    ("The Terraform Cloud workspace run-task API doc is the source of truth for our policy-as-code integration; every new rule lands with a link back to that doc in the PR description.", "reference", "technical", False,
     [("Terraform Cloud", "service"), ("run-task API", "api"), ("policy-as-code", "concept")],
     [("policy-as-code", "run-task API", "USES"), ("Terraform Cloud", "run-task API", "HAS_PART")],
     "which Terraform Cloud API anchors our policy-as-code integration and where does the link go",
     "terraform cloud run task api policy as code integration pr link doc"),
    # --- 26 architecture ---
    ("Terraform Enterprise sits in its own VPC with a Postgres backend and an S3 object store; workspaces map one-to-one onto service directories in the infra monorepo through VCS-driven working-directory settings.", "architecture", "technical", False,
     [("Terraform Enterprise", "service"), ("VPC", "infrastructure"), ("Postgres", "database"), ("S3", "service"), ("workspace", "concept"), ("working-directory", "config")],
     [("Terraform Enterprise", "VPC", "DEPLOYED_ON"), ("Terraform Enterprise", "Postgres", "DEPENDS_ON"), ("Terraform Enterprise", "S3", "USES"), ("workspace", "working-directory", "CONFIGURES")],
     "how is Terraform Enterprise hosted and how do workspaces map onto the infra monorepo",
     "terraform enterprise vpc postgres s3 workspace working directory monorepo vcs"),
    # --- 27 decision ---
    ("Env0 beat Scalr in the bake-off for the smaller platform org; the self-hosted agent model fit our air-gapped staging environment whereas Scalr's SaaS-only control plane would have needed an extra proxy hop.", "decision", "technical", False,
     [("Env0", "tool"), ("Scalr", "tool"), ("self-hosted agent", "concept"), ("air-gapped", "concept"), ("control plane", "concept")],
     [("Env0", "Scalr", "PREFERS"), ("Env0", "self-hosted agent", "SUPPORTS")],
     "which IaC platform won the Env0 versus Scalr bake-off and what was the deciding constraint",
     "env0 scalr self hosted agent air gapped control plane proxy bake off"),
    # --- 28 fact ---
    ("Tanka renders the observability stack through jsonnet and vendored libsonnet libraries; the tk apply command reconciles against the cluster and kubectl only shows up in break-glass playbooks now.", "fact", "technical", False,
     [("Tanka", "tool"), ("jsonnet", "language"), ("libsonnet", "library"), ("tk apply", "command"), ("kubectl", "command")],
     [("Tanka", "jsonnet", "USES"), ("Tanka", "libsonnet", "DEPENDS_ON"), ("tk apply", "kubectl", "REPLACES")],
     "which tool renders the observability stack and which command replaced routine kubectl use",
     "tanka jsonnet libsonnet tk apply kubectl observability stack vendor"),
    # --- 29 architecture ---
    ("cdk8s sits on top of the Python CDK construct library and emits plain Kubernetes YAML into a dist folder; Argo CD consumes the dist folder so the runtime cluster never imports a generator at all.", "architecture", "technical", False,
     [("cdk8s", "framework"), ("Python", "language"), ("Kubernetes", "platform"), ("Argo CD", "tool"), ("dist folder", "concept")],
     [("cdk8s", "Python", "USES"), ("cdk8s", "Kubernetes", "PRODUCES"), ("Argo CD", "dist folder", "USES")],
     "how does cdk8s hand off manifests to Argo CD without the runtime cluster importing a generator",
     "cdk8s python kubernetes argo cd dist folder yaml emit construct"),
    # --- 30 preference ---
    ("The platform team prefers importing existing resources through Terraform's import block over terraform import CLI invocations; declarative import keeps the PR diff honest and reviewable in one pass.", "preference", "technical", False,
     [("Terraform", "tool"), ("import block", "config"), ("terraform import", "command"), ("PR", "concept")],
     [("import block", "terraform import", "PREFERS")],
     "which Terraform import mechanism does the platform team prefer and why",
     "terraform import block cli command declarative pr diff reviewable platform"),
    # --- 31 milestone ---
    ("Cut over the whole compute plane from static AMI baking to a Pulumi-driven rolling replace; the new dependency graph produces a per-resource replacement plan that the team can diff before the apply lands.", "milestone", "technical", False,
     [("Pulumi", "tool"), ("AMI", "concept"), ("rolling replace", "pattern"), ("dependency graph", "concept"), ("compute plane", "infrastructure")],
     [("Pulumi", "AMI", "REPLACES"), ("Pulumi", "dependency graph", "PRODUCES"), ("rolling replace", "compute plane", "APPLIES_TO")],
     "which deployment model replaced static AMI baking on the compute plane and what artefact now gates the apply",
     "pulumi ami rolling replace dependency graph compute plane cut over"),
    # --- 32 reference ---
    ("The OpenTofu state-encryption RFC is the spec we follow for key material handling; encryption at rest for the tfstate blob is mandatory for every production workspace after that doc landed.", "reference", "technical", False,
     [("OpenTofu", "tool"), ("state-encryption", "concept"), ("tfstate", "file"), ("RFC", "publication"), ("production workspace", "concept")],
     [("OpenTofu", "state-encryption", "SUPPORTS"), ("state-encryption", "tfstate", "APPLIES_TO")],
     "which document defines our approach to encrypting Terraform state at rest",
     "opentofu state encryption tfstate rfc key material production workspace"),
    # --- 33 fact ---
    ("Each Terraform module exposes an explicit moved block list in a moves.tf file so refactors don't trigger destroy-recreate cycles; the CI fails the plan step if an unexpected resource-address change slips through.", "fact", "technical", False,
     [("Terraform", "tool"), ("moved block", "pattern"), ("moves.tf", "file"), ("CI", "infrastructure"), ("plan", "command")],
     [("moved block", "Terraform", "CONFIGURES"), ("CI", "plan", "USES")],
     "which file tracks Terraform moved blocks and what gate stops destroy-recreate from slipping past CI",
     "terraform moved block moves tf refactor destroy recreate ci plan gate"),
    # --- 34 architecture ---
    ("Dependency graph between Terragrunt modules is driven by dependency blocks pointing at outputs; terragrunt run-all plan walks the graph in topological order and parallelises independent branches with a concurrency cap.", "architecture", "technical", False,
     [("Terragrunt", "tool"), ("dependency block", "config"), ("run-all", "command"), ("topological order", "algorithm"), ("concurrency cap", "config")],
     [("Terragrunt", "dependency block", "USES"), ("run-all", "topological order", "IMPLEMENTS")],
     "how does Terragrunt order module plans across a dependency graph and where does parallelism kick in",
     "terragrunt dependency block run all plan topological order concurrency cap"),
    # --- 35 decision ---
    ("Picked the ignore_changes lifecycle meta-argument for the auto-scaling desired_capacity field; the autoscaler writes it out-of-band and we'd rather let the controller win than flap on every plan.", "decision", "technical", False,
     [("ignore_changes", "config"), ("lifecycle", "concept"), ("desired_capacity", "config"), ("autoscaler", "service")],
     [("ignore_changes", "desired_capacity", "APPLIES_TO"), ("ignore_changes", "autoscaler", "SUPPORTS")],
     "why is desired_capacity under ignore_changes and what controller gets to write it",
     "ignore changes lifecycle desired capacity autoscaler flap plan meta"),
    # --- 36 problem ---
    ("Taint plus replace dance on an RDS instance failed because the deletion protection flag wasn't cleared; the fix was a two-step plan that removed the flag on apply one and issued the replace on apply two.", "problem", "technical", False,
     [("Taint", "command"), ("replace", "command"), ("RDS", "service"), ("deletion protection", "config"), ("two-step plan", "pattern")],
     [("two-step plan", "deletion protection", "CONFIGURES"), ("replace", "RDS", "APPLIES_TO")],
     "why did a taint-then-replace on RDS fail and what sequence got the rebuild through",
     "taint replace rds deletion protection two step plan flag apply"),
    # --- 37 architecture ---
    ("Pulumi Python stacks use the automation API to drive ephemeral per-PR environments; the orchestrator spins a stack named after the PR, runs up, and destroys it when the PR merges or closes.", "architecture", "technical", False,
     [("Pulumi", "tool"), ("Python", "language"), ("automation API", "api"), ("PR", "concept"), ("up", "command"), ("destroy", "command")],
     [("Pulumi", "automation API", "USES"), ("automation API", "up", "IMPLEMENTS"), ("automation API", "destroy", "IMPLEMENTS")],
     "how do ephemeral per-PR environments get created and torn down with Pulumi's automation API",
     "pulumi automation api ephemeral pr environment up destroy stack orchestrator"),
    # --- 38 decision ---
    ("Pulumi Go won the backend-team bake-off over Pulumi Java; the compile-time errors on resource option typos were the deciding factor for the team after two Java stacks blew up at runtime on bad kwargs.", "decision", "technical", False,
     [("Pulumi", "tool"), ("Go", "language"), ("Java", "language"), ("resource option", "config")],
     [("Go", "Java", "PREFERS"), ("Pulumi", "Go", "SUPPORTS")],
     "which Pulumi language did the backend team pick and which runtime surprise drove the decision",
     "pulumi go java compile time resource option typo backend bake off"),
    # --- 39 preference ---
    ("Workspace layout prefers one Terraform workspace per environment per component rather than giant monoliths; smaller blast radius on apply failures is worth the extra wiring in the VCS-driven workspace config.", "preference", "technical", False,
     [("Terraform", "tool"), ("workspace", "concept"), ("environment", "concept"), ("component", "concept"), ("blast radius", "concept")],
     [("workspace", "component", "APPLIES_TO"), ("workspace", "environment", "APPLIES_TO")],
     "which Terraform workspace layout does the team prefer and what property drives the choice",
     "terraform workspace environment component blast radius apply monolith vcs"),
    # --- 40 fact ---
    ("Drift detection runs nightly via Atlantis planfile diffs against main; any non-empty plan posts a Slack message to the owning team with a link to the workspace run and the offending resource addresses.", "fact", "technical", False,
     [("Atlantis", "tool"), ("planfile", "file"), ("Slack", "service"), ("Drift detection", "concept"), ("main", "concept")],
     [("Atlantis", "Drift detection", "IMPLEMENTS"), ("Atlantis", "Slack", "COMMUNICATES_WITH"), ("planfile", "main", "APPLIES_TO")],
     "how does nightly drift detection surface results to owning teams through Atlantis",
     "atlantis planfile drift detection slack nightly main workspace run"),
    # --- 41 decision ---
    ("CDKTF runs sit behind Terraform Cloud agents in the restricted subnet; the synthesised HCL is checked in for traceability and the agent pool picks up plans with a least-privilege IAM role per stack.", "decision", "technical", False,
     [("CDKTF", "tool"), ("Terraform Cloud", "service"), ("agent pool", "infrastructure"), ("HCL", "language"), ("IAM", "service"), ("restricted subnet", "infrastructure")],
     [("CDKTF", "Terraform Cloud", "DEPENDS_ON"), ("CDKTF", "HCL", "PRODUCES"), ("agent pool", "restricted subnet", "DEPLOYED_ON"), ("agent pool", "IAM", "USES")],
     "how is CDKTF wired through Terraform Cloud agents and where does the synthesised HCL live",
     "cdktf terraform cloud agent pool restricted subnet hcl iam least privilege"),
    # --- 42 milestone ---
    ("Finished the Helm to Kustomize migration for the shared platform services; the final chart retired was the Prometheus stack and its CRD lifecycle now rides a separate install hook outside the main overlay.", "milestone", "technical", False,
     [("Helm", "tool"), ("Kustomize", "tool"), ("Prometheus", "service"), ("CRD", "concept"), ("install hook", "pattern"), ("overlay", "pattern")],
     [("Kustomize", "Helm", "REPLACES"), ("Prometheus", "CRD", "HAS_PART")],
     "which migration wrapped with the Prometheus stack and how did CRD lifecycle get handled",
     "helm kustomize migration prometheus crd install hook overlay platform"),
    # --- 43 noise ---
    ("A rogue office plant grew into the desk partition and the cleaning crew filed a maintenance ticket tagged plant versus partition.", "fact", "noise", True, [], [], None, None),
    # --- 44 preference ---
    ("When editing Ansible inventories, the team prefers YAML inventories with group_vars over the old INI format; nested groups and typed variables read cleaner and the schema diff in review is much easier to follow.", "preference", "technical", False,
     [("Ansible", "tool"), ("YAML", "technology"), ("INI", "technology"), ("group_vars", "config"), ("inventories", "concept")],
     [("YAML", "INI", "PREFERS"), ("inventories", "group_vars", "HAS_PART")],
     "which Ansible inventory format does the team prefer and which feature drives that preference",
     "ansible yaml ini group vars inventory nested typed variable schema diff"),
    # --- 45 fact ---
    ("Bicep modules live in a module registry hosted on Azure Container Registry; br: references pin by digest in production pipelines and by tag in the sandbox subscription for faster iteration.", "fact", "technical", False,
     [("Bicep", "language"), ("Azure Container Registry", "service"), ("br:", "pattern"), ("sandbox", "concept"), ("production pipeline", "concept")],
     [("Bicep", "Azure Container Registry", "DEPLOYED_ON"), ("br:", "Azure Container Registry", "USES")],
     "where are Bicep modules hosted and how do references differ between production and sandbox",
     "bicep azure container registry br reference digest tag sandbox production"),
    # --- 46 milestone ---
    ("Hit a hundred percent coverage on the state-lock timeout guardrail across every Terraform workspace; any apply over fifteen minutes without state progress now aborts the run and pages the on-call rotation.", "milestone", "technical", False,
     [("Terraform", "tool"), ("state-lock", "concept"), ("workspace", "concept"), ("apply", "command"), ("on-call", "concept")],
     [("Terraform", "state-lock", "USES"), ("apply", "on-call", "CAUSES")],
     "which guardrail now covers every Terraform workspace and when does it page the on-call rotation",
     "terraform state lock timeout workspace apply on call rotation guardrail coverage"),
    # --- 47 decision ---
    ("Standardised Terragrunt across Pulumi and raw Terraform stacks because the hierarchical config inheritance cut our per-environment copy-paste sprawl down to a single root file and a per-env override.", "decision", "technical", False,
     [("Terragrunt", "tool"), ("Pulumi", "tool"), ("Terraform", "tool"), ("hierarchical config", "pattern"), ("per-env override", "config")],
     [("Terragrunt", "Pulumi", "APPLIES_TO"), ("Terragrunt", "Terraform", "APPLIES_TO"), ("hierarchical config", "per-env override", "SUPPORTS")],
     "why was Terragrunt picked to sit over both Pulumi and Terraform stacks in the infra layout",
     "terragrunt pulumi terraform hierarchical config per env override copy paste"),
    # --- 48 reference ---
    ("Pulled the taint versus replace recipe from the Terraform CLI reference section on resource addresses; the command examples there save a support ticket every time a junior engineer asks about forcing a rebuild.", "reference", "technical", False,
     [("taint", "command"), ("replace", "command"), ("Terraform", "tool"), ("CLI reference", "publication"), ("resource address", "concept")],
     [("CLI reference", "taint", "HAS_PART"), ("CLI reference", "replace", "HAS_PART"), ("taint", "resource address", "APPLIES_TO")],
     "which Terraform doc covers the taint versus replace recipe and where in the reference does it sit",
     "terraform cli reference taint replace resource address force rebuild junior"),
    # --- 49 architecture ---
    ("State locking across the OpenTofu estate leans on DynamoDB for AWS and Azure Storage leases for Azure; the abstraction over both sits in a Terragrunt terragrunt.hcl include file that all stacks pull from root.", "architecture", "technical", False,
     [("OpenTofu", "tool"), ("DynamoDB", "database"), ("Azure Storage", "service"), ("Terragrunt", "tool"), ("terragrunt.hcl", "file"), ("State locking", "concept")],
     [("OpenTofu", "DynamoDB", "USES"), ("OpenTofu", "Azure Storage", "USES"), ("Terragrunt", "terragrunt.hcl", "CONFIGURES"), ("State locking", "DynamoDB", "APPLIES_TO")],
     "how is state locking abstracted across AWS and Azure in the OpenTofu estate",
     "opentofu dynamodb azure storage terragrunt hcl include state lock estate"),
    # --- 50 reference ---
    ("The Bicep what-if preview doc anchors how we review ARM deployments in pull requests; the what-if output structure and ignore-rule syntax described there map one-to-one onto our PR comment formatter.", "reference", "technical", False,
     [("Bicep", "language"), ("what-if", "command"), ("ARM", "language"), ("pull request", "concept"), ("ignore-rule", "config")],
     [("what-if", "Bicep", "APPLIES_TO"), ("what-if", "ARM", "APPLIES_TO"), ("what-if", "ignore-rule", "USES")],
     "which Bicep doc anchors the way ARM deployments get previewed in pull requests",
     "bicep what if arm pull request ignore rule preview comment formatter"),
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
