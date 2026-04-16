"""One-off emitter for shared-base batch-194 — technical domain (Kubernetes operators and controllers: Operator SDK, Kubebuilder, controller-runtime, CRDs, webhooks, ArgoCD, FluxCD, Crossplane, KEDA, cert-manager, Gatekeeper, Kyverno, Karpenter, Cluster API, etc.).

Writes 50 rows to data/v2/shared/batch_194.tmp.jsonl with ids shared-09651..09700.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_194.tmp.jsonl"
ID_OFFSET = 9650

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Scaffolded the billing-subscription controller with Kubebuilder v4 instead of Operator SDK; the cleaner controller-runtime surface and native conversion-webhook wiring mattered more than the Ansible operator mode we didn't need.", "decision", "technical", False,
     [("Kubebuilder", "framework"), ("Operator SDK", "framework"), ("controller-runtime", "library"), ("conversion-webhook", "pattern")],
     [("Kubebuilder", "Operator SDK", "PREFERS"), ("Kubebuilder", "controller-runtime", "USES")],
     "which scaffolding framework did the billing controller pick over Operator SDK and which features decided it",
     "kubebuilder operator sdk controller runtime conversion webhook scaffold"),
    # --- 2 ---
    ("The Subscription CRD uses a structural schema with x-kubernetes-preserve-unknown-fields only under spec.provider.config; the rest of the spec is strictly validated at the API server before reconcile even sees the object.", "architecture", "technical", False,
     [("Subscription", "concept"), ("structural schema", "pattern"), ("x-kubernetes-preserve-unknown-fields", "config"), ("API server", "service")],
     [("Subscription", "structural schema", "USES")],
     "how does the Subscription CRD allow provider-specific fields while still strictly validating the rest of the spec",
     "subscription crd structural schema preserve unknown fields validate"),
    # --- 3 ---
    ("Reconcile loop is idempotent and drives toward a declarative spec; every call re-reads the live cluster state, computes the diff, and issues a minimal patch, so a retry after transient apiserver 429 is safe.", "fact", "technical", False,
     [("Reconcile loop", "pattern"), ("declarative spec", "pattern"), ("apiserver", "service"), ("429", "protocol")],
     [],
     "which control-loop property makes reconcile safe to retry after a transient apiserver rate-limit",
     "reconcile loop idempotent declarative patch retry 429 apiserver"),
    # --- 4 ---
    ("Added a finalizer billing.darkmem.io/cleanup to the Subscription; deletion now blocks until the external Stripe subscription is cancelled, avoiding the orphan-charge bug that bit us in v0.3.", "milestone", "technical", False,
     [("finalizer", "pattern"), ("billing.darkmem.io/cleanup", "config"), ("Subscription", "concept"), ("Stripe", "service")],
     [("finalizer", "Subscription", "APPLIES_TO")],
     "which mechanism now blocks Subscription deletion until the external Stripe record is cancelled",
     "finalizer subscription stripe cleanup delete orphan charge"),
    # --- 5 ---
    ("Owner references link child Deployments and Services to the owning AppCluster CR with controller=true; garbage collection cascades on delete without writing any explicit cleanup code in the controller.", "fact", "technical", False,
     [("Owner references", "pattern"), ("AppCluster", "concept"), ("Deployment", "concept"), ("Service", "concept")],
     [("Owner references", "AppCluster", "APPLIES_TO")],
     "which Kubernetes primitive cascades Deployment and Service cleanup when the parent AppCluster is deleted",
     "owner reference appcluster deployment service garbage collect cascade"),
    # --- 6 ---
    ("Validating admission webhook on Subscription rejects plan downgrades during an active billing period; the policy lives in the controller binary behind /validate-v1-subscription and returns a structured warning payload.", "architecture", "technical", False,
     [("Validating admission webhook", "pattern"), ("Subscription", "concept"), ("/validate-v1-subscription", "api")],
     [("Validating admission webhook", "Subscription", "APPLIES_TO")],
     "how does the operator reject mid-period plan downgrades at admission time rather than in reconcile",
     "validating admission webhook subscription plan downgrade period"),
    # --- 7 ---
    ("Mutating webhook injects default resource limits and a darkmem.io/trace-id annotation on AppCluster create; the failurePolicy is Ignore so an outage of the webhook pod does not wedge new deployments.", "decision", "technical", False,
     [("Mutating webhook", "pattern"), ("AppCluster", "concept"), ("darkmem.io/trace-id", "config"), ("failurePolicy", "config")],
     [("Mutating webhook", "AppCluster", "APPLIES_TO")],
     "which failure policy does the mutating webhook use so an outage does not block AppCluster creation",
     "mutating webhook appcluster resource limit trace id failure policy"),
    # --- 8 ---
    ("Conversion webhook bridges v1alpha1 and v1 Subscription objects; the storage version is v1 and the webhook translates on the way in so old kubectl apply manifests keep working through the migration window.", "fact", "technical", False,
     [("Conversion webhook", "pattern"), ("v1alpha1", "config"), ("v1", "config"), ("Subscription", "concept"), ("kubectl", "tool")],
     [("Conversion webhook", "Subscription", "APPLIES_TO")],
     "how does the operator keep old v1alpha1 manifests working after promoting Subscription storage to v1",
     "conversion webhook v1alpha1 v1 subscription storage version migrate"),
    # --- 9 ---
    ("client-go informers back the controller cache; a SharedInformerFactory for Deployments, Services, and the CR feeds the workqueue so reconcile reads hit local memory instead of hammering the apiserver.", "fact", "technical", False,
     [("client-go", "library"), ("SharedInformerFactory", "api"), ("workqueue", "pattern"), ("apiserver", "service")],
     [("client-go", "SharedInformerFactory", "USES")],
     "which client-go primitive caches CR state so reconcile reads avoid hammering the apiserver",
     "client go shared informer factory workqueue reconcile cache apiserver"),
    # --- 10. noise ---
    ("The office plant on the NOC desk has been unofficially named Gerald and has a humidity chart taped next to its pot.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Adopted ArgoCD over FluxCD for the platform GitOps layer; the app-of-apps pattern and the sync-wave ordering gave us staged promotions without scripting and the UI shortened incident triage noticeably.", "decision", "technical", False,
     [("ArgoCD", "tool"), ("FluxCD", "tool"), ("app-of-apps", "pattern"), ("sync-wave", "pattern")],
     [("ArgoCD", "FluxCD", "PREFERS")],
     "which GitOps tool did the platform pick over FluxCD and which features drove the choice",
     "argocd fluxcd app of apps sync wave gitops platform promote"),
    # --- 12 ---
    ("FluxCD still runs in the edge fleet because its small footprint and Kustomize-first reconciler fit the constrained ARM nodes; ArgoCD's server footprint was too heavy to colocate with workloads there.", "decision", "technical", False,
     [("FluxCD", "tool"), ("Kustomize", "tool"), ("ArgoCD", "tool"), ("ARM", "platform")],
     [("FluxCD", "Kustomize", "USES")],
     "why does the edge fleet keep FluxCD instead of standardising on ArgoCD like the platform clusters",
     "fluxcd kustomize argocd edge arm footprint reconcile small"),
    # --- 13 ---
    ("Crossplane composes the RDS, S3, and IAM side of every tenant in a single XR; the old Terraform-plus-operator split had drift between the cloud state and the cluster view and one reconciler now owns both.", "architecture", "technical", False,
     [("Crossplane", "framework"), ("RDS", "service"), ("S3", "service"), ("IAM", "service"), ("XR", "concept"), ("Terraform", "tool")],
     [("Crossplane", "Terraform", "REPLACES")],
     "which control-plane composition tool replaced the Terraform-plus-operator split for tenant cloud resources",
     "crossplane xr composite rds s3 iam terraform tenant drift"),
    # --- 14 ---
    ("KEDA drives scale-to-zero on the ingestion workers; a Kafka lag trigger with a 5-minute cooldown keeps replicas honest and the HPA fallback rule retains a floor of two during business hours.", "architecture", "technical", False,
     [("KEDA", "framework"), ("Kafka", "service"), ("HPA", "concept"), ("cooldown", "config")],
     [("KEDA", "Kafka", "USES")],
     "which autoscaler gates the ingestion workers down to zero and which trigger source does it watch",
     "keda kafka lag hpa cooldown scale zero ingestion worker"),
    # --- 15 ---
    ("Keptn quality gates block the promotion stage when SLO error-budget burn exceeds the stage threshold; the release pipeline routes through a Keptn-Sequence resource instead of a hand-rolled Argo Workflows DAG.", "architecture", "technical", False,
     [("Keptn", "framework"), ("SLO", "concept"), ("Keptn-Sequence", "concept"), ("Argo Workflows", "tool")],
     [("Keptn", "Argo Workflows", "REPLACES")],
     "which promotion-gating tool replaced the Argo Workflows DAG and what signal does it evaluate",
     "keptn sequence slo error budget promote argo workflows dag"),
    # --- 16 ---
    ("OpenKruise's AdvancedStatefulSet unlocked in-place pod updates for the sharded cache fleet; rolling replacements on 200-pod StatefulSets were costing an hour of warm-cache rebuild per release.", "problem", "technical", False,
     [("OpenKruise", "framework"), ("AdvancedStatefulSet", "concept"), ("StatefulSet", "concept"), ("in-place", "pattern")],
     [("AdvancedStatefulSet", "StatefulSet", "IMPROVES_ON")],
     "which OpenKruise resource retired hour-long warm-cache rebuilds during sharded cache rollouts",
     "openkruise advanced statefulset in place update warm cache shard"),
    # --- 17 ---
    ("cert-manager handles all ingress TLS via the Let's Encrypt ACME DNS-01 solver with Route53; the HTTP-01 path was retired after the internal ALB rewrite broke the well-known challenge response on three services.", "decision", "technical", False,
     [("cert-manager", "tool"), ("Let's Encrypt", "service"), ("ACME", "protocol"), ("DNS-01", "protocol"), ("HTTP-01", "protocol"), ("Route53", "service")],
     [("cert-manager", "Let's Encrypt", "USES"), ("DNS-01", "HTTP-01", "REPLACES")],
     "which ACME challenge does cert-manager issue through now that HTTP-01 was retired",
     "cert manager lets encrypt acme dns 01 route53 http 01 ingress"),
    # --- 18 ---
    ("external-dns publishes Service and Ingress hostnames to Cloudflare with ownership annotations scoped to the cluster-name txt record; cross-cluster fights over a shared zone stopped after the txt-owner-id flag was set.", "milestone", "technical", False,
     [("external-dns", "tool"), ("Cloudflare", "service"), ("txt-owner-id", "config"), ("Ingress", "concept")],
     [("external-dns", "Cloudflare", "USES")],
     "which external-dns flag stopped cross-cluster fights over the shared Cloudflare zone",
     "external dns cloudflare txt owner id ingress cross cluster fight"),
    # --- 19 ---
    ("kube-state-metrics exposes CR-level gauges via the --custom-resource-state-config flag; we now alert on Subscription phase stuck at Reconciling for more than ten minutes without writing a new exporter per CRD.", "fact", "technical", False,
     [("kube-state-metrics", "tool"), ("--custom-resource-state-config", "config"), ("Subscription", "concept"), ("Reconciling", "concept")],
     [("kube-state-metrics", "Subscription", "APPLIES_TO")],
     "how does kube-state-metrics surface Subscription reconcile-stuck states without a bespoke exporter",
     "kube state metrics custom resource state config subscription stuck"),
    # --- 20 ---
    ("Prometheus Operator owns the ServiceMonitor objects for every tenant controller; the shared Prometheus ruleOwner label scopes PrometheusRule selection so tenant alerts never pollute the platform-level pager.", "reference", "technical", False,
     [("Prometheus Operator", "tool"), ("ServiceMonitor", "concept"), ("PrometheusRule", "concept"), ("ruleOwner", "config")],
     [("Prometheus Operator", "ServiceMonitor", "USES")],
     "how does Prometheus Operator keep tenant alerts out of the platform pager while sharing a Prometheus",
     "prometheus operator service monitor rule owner tenant alert pager"),
    # --- 21 ---
    ("Grafana Operator provisions dashboards from ConfigMaps tagged grafana-dashboard=true; the old hand-curl-to-API deployment method stopped drifting once the operator took over on the staging cluster.", "decision", "technical", False,
     [("Grafana Operator", "tool"), ("ConfigMap", "concept"), ("grafana-dashboard", "config")],
     [("Grafana Operator", "ConfigMap", "USES")],
     "which dashboard deployment method did Grafana Operator replace and how did it stop drift",
     "grafana operator configmap dashboard label drift curl api"),
    # --- 22 ---
    ("VolumeSnapshotClass csi-ebs-snapshot is the default for all RWO claims in prod; snapshots land in the backup account via cross-account IAM role and are retained 35 days before GC.", "reference", "technical", False,
     [("VolumeSnapshotClass", "concept"), ("csi-ebs-snapshot", "config"), ("RWO", "concept"), ("IAM", "service")],
     [],
     "which VolumeSnapshotClass serves prod RWO claims and where do the snapshots land for retention",
     "volume snapshot class csi ebs rwo prod backup iam retention"),
    # --- 23 ---
    ("PersistentVolumeClaim online expansion is enabled on the gp3 StorageClass; editing spec.resources.requests.storage expands in place without a pod restart, which retired the weekend-night manual resize playbook.", "milestone", "technical", False,
     [("PersistentVolumeClaim", "concept"), ("gp3", "config"), ("StorageClass", "concept"), ("online expansion", "pattern")],
     [],
     "which StorageClass feature retired the weekend-night manual PVC resize playbook",
     "persistent volume claim expansion gp3 storage class online resize"),
    # --- 24 ---
    ("Gatekeeper enforces a constraint that every workload namespace carry costCenter, team, and dataClassification labels; exceptions go through an audit-only constraint for two weeks before becoming deny.", "architecture", "technical", False,
     [("Gatekeeper", "tool"), ("constraint", "pattern"), ("costCenter", "config"), ("dataClassification", "config")],
     [("Gatekeeper", "constraint", "USES")],
     "how does Gatekeeper stage mandatory namespace labels from audit-only into a hard deny policy",
     "gatekeeper constraint cost center data classification audit deny"),
    # --- 25 ---
    ("Kyverno replaced the OPA pod-security policies after ClusterPolicy rules proved easier for platform engineers to read; the YAML-native syntax lowered the onboarding bar compared with Rego.", "decision", "technical", False,
     [("Kyverno", "tool"), ("OPA", "tool"), ("ClusterPolicy", "concept"), ("Rego", "language")],
     [("Kyverno", "OPA", "REPLACES")],
     "which policy engine replaced OPA for pod-security rules and why did engineers prefer its syntax",
     "kyverno opa cluster policy rego pod security yaml onboard"),
    # --- 26 ---
    ("Metrics Server ships as a hardened DaemonSet with kubelet-insecure-tls off; HPA queries now route through aggregated APIs and the old heapster remnants were purged during the 1.28 upgrade.", "milestone", "technical", False,
     [("Metrics Server", "service"), ("DaemonSet", "concept"), ("kubelet-insecure-tls", "config"), ("HPA", "concept"), ("heapster", "tool")],
     [("Metrics Server", "heapster", "REPLACES")],
     "which upgrade purged heapster and hardened Metrics Server TLS while keeping HPA queries working",
     "metrics server daemonset kubelet insecure tls hpa heapster 1 28"),
    # --- 27 ---
    ("Cluster Autoscaler on the CI node group used to flap on the spot-interruption signal; switching the expander to least-waste and pinning max-node-provision-time at 15m calmed the oscillation.", "problem", "technical", False,
     [("Cluster Autoscaler", "tool"), ("spot-interruption", "concept"), ("least-waste", "config"), ("max-node-provision-time", "config")],
     [],
     "which Cluster Autoscaler settings stopped the CI node-group flap on spot interruptions",
     "cluster autoscaler spot interruption least waste provision time ci"),
    # --- 28 ---
    ("Karpenter replaced the Cluster Autoscaler for stateless workloads; consolidation packs fragmented pods onto fewer nodes and the monthly compute bill dropped by roughly 28 percent after the switch.", "decision", "technical", False,
     [("Karpenter", "tool"), ("Cluster Autoscaler", "tool"), ("consolidation", "pattern")],
     [("Karpenter", "Cluster Autoscaler", "REPLACES")],
     "which autoscaler replaced Cluster Autoscaler for stateless workloads and what cost win did it deliver",
     "karpenter cluster autoscaler consolidation pack stateless cost 28"),
    # --- 29 ---
    ("Karpenter NodePool limits are carved per team with a requirements block pinning karpenter.sh/capacity-type to spot for dev and on-demand for the billing tenant; a budget rolls to on-demand if spot is unavailable for 15 minutes.", "reference", "technical", False,
     [("Karpenter", "tool"), ("NodePool", "concept"), ("karpenter.sh/capacity-type", "config"), ("spot", "concept"), ("on-demand", "concept")],
     [("NodePool", "Karpenter", "APPLIES_TO")],
     "how does the Karpenter NodePool split capacity between spot and on-demand with an availability fallback",
     "karpenter node pool capacity type spot on demand budget fallback"),
    # --- 30 ---
    ("vcluster hosts per-team control planes on the shared platform cluster; Argo RBAC grants each team cluster-admin inside their vcluster but only edit on the parent namespace, which killed the ticket queue for namespace creations.", "architecture", "technical", False,
     [("vcluster", "tool"), ("Argo", "tool"), ("RBAC", "concept"), ("cluster-admin", "concept")],
     [("vcluster", "Argo", "USES")],
     "how does vcluster give teams cluster-admin without handing out the platform cluster and what queue did it retire",
     "vcluster argo rbac cluster admin namespace ticket team platform"),
    # --- 31 ---
    ("Cluster API provisions all workload clusters on AWS through CAPA; the bootstrap controller hands off to KubeadmControlPlane and MachineDeployment manages rolling node images without Terraform touching the clusters.", "architecture", "technical", False,
     [("Cluster API", "framework"), ("CAPA", "tool"), ("KubeadmControlPlane", "concept"), ("MachineDeployment", "concept"), ("Terraform", "tool")],
     [("Cluster API", "CAPA", "USES"), ("Cluster API", "Terraform", "REPLACES")],
     "which Cluster API pieces own AWS cluster provisioning and which Terraform path was retired",
     "cluster api capa kubeadm control plane machine deployment aws"),
    # --- 32 ---
    ("kOps is kept only for the legacy us-east-2 billing cluster; new clusters go through Cluster API, and the kOps state S3 bucket is read-only with an IAM condition enforcing the freeze.", "decision", "technical", False,
     [("kOps", "tool"), ("Cluster API", "framework"), ("us-east-2", "place"), ("S3", "service"), ("IAM", "service")],
     [("Cluster API", "kOps", "REPLACES")],
     "which cluster-provisioning tool is frozen to a single legacy region and how is the freeze enforced",
     "kops cluster api us east 2 s3 iam freeze legacy billing"),
    # --- 33 ---
    ("controller-runtime's manager starts webhooks, metrics, and the leader-election lease in one ctrl.NewManager call; the previous hand-rolled cobra entrypoint missed leader-election on an operator restart and triggered duplicate reconciles.", "milestone", "technical", False,
     [("controller-runtime", "library"), ("ctrl.NewManager", "api"), ("leader-election", "pattern"), ("cobra", "library")],
     [("ctrl.NewManager", "cobra", "REPLACES")],
     "which controller-runtime entrypoint replaced the cobra boot and which duplicate-reconcile bug did it fix",
     "controller runtime manager leader election cobra duplicate reconcile"),
    # --- 34 ---
    ("RBAC for the operator is generated from kubebuilder markers; every +kubebuilder:rbac tag above the reconcile functions produces the exact ClusterRole so we don't drift between code paths and granted permissions.", "reference", "technical", False,
     [("kubebuilder markers", "pattern"), ("+kubebuilder:rbac", "config"), ("ClusterRole", "concept"), ("RBAC", "concept")],
     [],
     "how does the operator keep ClusterRole permissions aligned with reconcile code paths",
     "kubebuilder marker rbac cluster role reconcile drift generate"),
    # --- 35 ---
    ("Operator uses client-side RequeueAfter with jitter to stagger reconciles on mass-delete; the old immediate-requeue behaviour hammered the apiserver on a 1k-CR cleanup and contributed to the etcd compaction backlog.", "problem", "technical", False,
     [("RequeueAfter", "api"), ("jitter", "pattern"), ("apiserver", "service"), ("etcd", "database")],
     [],
     "which requeue pattern calmed the apiserver on a 1k-CR mass-delete and saved etcd from compaction backlog",
     "requeue after jitter apiserver etcd compaction mass delete 1k"),
    # --- 36 ---
    ("Status subresource is enabled on every CRD; conditions like Ready, Degraded, and Reconciling follow the Kubernetes condition contract so tooling like kubectl wait --for=condition=Ready works out of the box.", "reference", "technical", False,
     [("Status subresource", "pattern"), ("CRD", "concept"), ("Ready", "concept"), ("Degraded", "concept"), ("kubectl", "tool")],
     [],
     "which condition contract do the CRDs follow so kubectl wait --for=condition works unmodified",
     "status subresource crd ready degraded reconciling kubectl wait"),
    # --- 37 ---
    ("Leader-election lease is a coordination.k8s.io Lease with 15s lease duration and 10s renew deadline; the old endpoints-based lock was flapping on large clusters with slow endpoint propagation.", "decision", "technical", False,
     [("coordination.k8s.io", "api"), ("Lease", "concept"), ("endpoints", "concept"), ("15s", "config"), ("10s", "config")],
     [("Lease", "endpoints", "REPLACES")],
     "which lease backend replaced endpoints-based leader election and what lease and renew timers are set",
     "coordination lease endpoints leader election 15s 10s flap"),
    # --- 38 ---
    ("Envtest spins up a local etcd and kube-apiserver for controller-runtime unit tests; CI bakes the binaries into the image so setup-envtest doesn't reach out to the network on every run.", "fact", "technical", False,
     [("Envtest", "tool"), ("etcd", "database"), ("kube-apiserver", "service"), ("setup-envtest", "tool"), ("CI", "concept")],
     [("Envtest", "etcd", "USES")],
     "how do controller-runtime unit tests avoid pulling envtest binaries from the network on every CI run",
     "envtest etcd kube apiserver setup envtest ci binary cache"),
    # --- 39 ---
    ("Added a predicate on the watch filter so reconcile skips status-only updates; the reconcile rate dropped from 18k/h to 2.4k/h on the busy staging cluster and pager-duty tickets about apiserver latency stopped.", "decision", "technical", False,
     [("predicate", "pattern"), ("watch filter", "pattern"), ("reconcile", "pattern"), ("apiserver", "service")],
     [],
     "which watch-filter change cut reconcile rate from 18k/h to 2.4k/h and calmed apiserver pager noise",
     "predicate watch filter status reconcile rate apiserver pager"),
    # --- 40 ---
    ("Webhook certificates rotate through a cert-manager Certificate resource annotated cert-manager.io/inject-ca-from; the webhook ValidatingWebhookConfiguration caBundle is patched automatically on rotation.", "preference", "technical", False,
     [("cert-manager", "tool"), ("Certificate", "concept"), ("cert-manager.io/inject-ca-from", "config"), ("ValidatingWebhookConfiguration", "concept"), ("caBundle", "config")],
     [("cert-manager", "ValidatingWebhookConfiguration", "APPLIES_TO")],
     "how does the webhook caBundle stay current without a manual patch every time cert-manager rotates",
     "cert manager certificate inject ca from validating webhook bundle"),
    # --- 41 ---
    ("Reference architecture doc for new operators is at docs/platform/operators/playbook.md; it covers scaffold, CRD versioning, webhook TLS, finalizer hygiene, and the required Prometheus metrics contract.", "reference", "technical", False,
     [("docs/platform/operators/playbook.md", "file"), ("CRD", "concept"), ("webhook", "pattern"), ("Prometheus", "tool")],
     [],
     "where does a new team look up the required pattern for scaffold, CRD versioning, and webhook TLS",
     "playbook operator crd version webhook tls finalizer prometheus docs"),
    # --- 42 ---
    ("The platform prefers the controller-runtime builder pattern over raw informer wiring; the ctrl.NewControllerManagedBy builder reads cleaner and makes Owns, Watches, and WithEventFilter obvious in review.", "preference", "technical", False,
     [("controller-runtime", "library"), ("ctrl.NewControllerManagedBy", "api"), ("Owns", "api"), ("Watches", "api"), ("WithEventFilter", "api")],
     [],
     "which controller-runtime pattern does the platform prefer for watch wiring and why",
     "controller runtime builder new controller managed by owns watches"),
    # --- 43. noise ---
    ("Someone taped a photo of a kitten in a tiny hard hat above the cluster whiteboard and nobody has claimed it.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Operator metrics expose reconcile_total, reconcile_errors_total, and reconcile_time_seconds histogram via the default controller-runtime registry; the Prometheus Operator ServiceMonitor ships in the chart.", "fact", "technical", False,
     [("reconcile_total", "api"), ("reconcile_errors_total", "api"), ("reconcile_time_seconds", "api"), ("controller-runtime", "library"), ("ServiceMonitor", "concept")],
     [],
     "which three reconcile metrics does the operator publish and how does Prometheus scrape them by default",
     "reconcile total errors time seconds controller runtime service monitor"),
    # --- 45 ---
    ("Team prefers short, single-purpose CRDs over god-objects; splitting the Tenant CRD into Tenant, TenantQuota, and TenantNetwork made the reconcile loops smaller and diff review practical again.", "preference", "technical", False,
     [("Tenant", "concept"), ("TenantQuota", "concept"), ("TenantNetwork", "concept")],
     [],
     "which CRD split did the team prefer over a god-object Tenant resource and what review benefit did it give",
     "tenant quota network crd split god object reconcile loop review"),
    # --- 46 ---
    ("Platform style avoids blocking on external APIs inside reconcile; any outbound Stripe call goes through a bounded worker pool with a deadline context and the CR status records the attempt outcome for the next loop.", "preference", "technical", False,
     [("Stripe", "service"), ("worker pool", "pattern"), ("deadline context", "pattern"), ("reconcile", "pattern")],
     [],
     "which pattern does platform style require for external API calls from inside a reconcile function",
     "stripe worker pool deadline context reconcile external api status"),
    # --- 47 ---
    ("ArgoCD ApplicationSet generators build one Application per Cluster API Cluster object; adding a new tenant cluster produces the full platform addon stack without editing ArgoCD manifests directly.", "architecture", "technical", False,
     [("ArgoCD", "tool"), ("ApplicationSet", "concept"), ("Cluster API", "framework"), ("Cluster", "concept")],
     [("ApplicationSet", "Cluster API", "USES")],
     "how does ArgoCD deploy the platform addon stack automatically when Cluster API provisions a new cluster",
     "argocd application set cluster api generator tenant addon stack"),
    # --- 48 ---
    ("Gatekeeper exempts the kube-system and gatekeeper-system namespaces via the Config sync exclusion list; a misconfigured constraint that blocked CoreDNS startup during an upgrade forced this guardrail into the platform chart.", "decision", "technical", False,
     [("Gatekeeper", "tool"), ("kube-system", "concept"), ("gatekeeper-system", "concept"), ("CoreDNS", "service"), ("Config", "concept")],
     [],
     "which Gatekeeper exclusion prevents a bad constraint from blocking CoreDNS during a control-plane upgrade",
     "gatekeeper kube system gatekeeper system config exclusion coredns"),
    # --- 49 ---
    ("Kyverno mutate rule injects imagePullSecrets on every Deployment in tenant namespaces; the registry migration from ECR to Artifactory went through without a single tenant chart change thanks to the background scan.", "milestone", "technical", False,
     [("Kyverno", "tool"), ("imagePullSecrets", "config"), ("Deployment", "concept"), ("ECR", "service"), ("Artifactory", "service")],
     [("Kyverno", "Deployment", "APPLIES_TO")],
     "which Kyverno rule covered the ECR-to-Artifactory registry migration without touching tenant charts",
     "kyverno mutate image pull secret deployment ecr artifactory migration"),
    # --- 50 ---
    ("Operator release v2.0 cut over every tenant to the v1 Subscription API; the conversion webhook runs hot for a 30-day migration window and then v1alpha1 will be served-false in v2.1.", "milestone", "technical", False,
     [("v2.0", "config"), ("v1", "config"), ("v1alpha1", "config"), ("Subscription", "concept"), ("v2.1", "config"), ("conversion webhook", "pattern")],
     [("v2.0", "v1alpha1", "REPLACES")],
     "which release cut tenants over to v1 Subscription and when does v1alpha1 get served-false",
     "v2 0 v1 v1alpha1 subscription conversion webhook 30 day v2 1"),
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
