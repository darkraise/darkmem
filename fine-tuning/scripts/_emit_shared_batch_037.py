"""One-off emitter for shared-base batch-037 — technical domain (cloud-native / Kubernetes / observability / SRE slice).

Writes 50 rows to data/v2/shared/batch_037.tmp.jsonl with ids shared-01801..01850.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_037.tmp.jsonl"
ID_OFFSET = 1800

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Karpenter replaced the Cluster Autoscaler on the spot fleet; node launches dropped from two minutes to under thirty seconds.", "decision", "technical", False,
     [("Karpenter", "tool"), ("Cluster Autoscaler", "tool")],
     [("Karpenter", "Cluster Autoscaler", "REPLACES")],
     "which node provisioner took over from the Autoscaler on the spot fleet",
     "node provisioner spot replace launch latency"),
    # --- 2 ---
    ("Cluster Autoscaler stayed on the stateful node groups; predictable ASG shapes mattered more than Karpenter's bin-packing gains there.", "fact", "technical", False,
     [("Cluster Autoscaler", "tool"), ("Karpenter", "tool"), ("ASG", "technology")],
     [],
     "which node groups kept the old autoscaler instead of moving to Karpenter",
     "stateful ASG predictable shape bin pack keep"),
    # --- 3 ---
    ("Pod Disruption Budgets with maxUnavailable=0 stalled every node drain; switching to minAvailable let the rolling restart finish.", "problem", "technical", False,
     [("Pod Disruption Budget", "api")],
     [],
     "which PDB setting blocked node drains during the rolling restart",
     "disruption budget drain stuck max unavailable zero fix"),
    # --- 4 ---
    ("Taints with NoExecute on the GPU pool kept stray CPU workloads off; matching tolerations live in the inference Helm values file only.", "architecture", "technical", False,
     [("NoExecute", "api"), ("Helm", "tool")],
     [],
     "how is the GPU node pool kept isolated from general workloads",
     "taint toleration GPU isolation Helm values"),
    # --- 5 ---
    ("EndpointSlices replaced the legacy Endpoints object across the cluster; kube-proxy CPU dropped 22 percent on the big Service.", "decision", "technical", False,
     [("EndpointSlices", "api"), ("Endpoints", "api"), ("kube-proxy", "service")],
     [("EndpointSlices", "Endpoints", "REPLACES")],
     "which Service backend object took over from the legacy one",
     "endpoint slice legacy proxy CPU reduction"),
    # --- 6 ---
    ("Cilium's NetworkPolicy with FQDN selectors gated egress to the LLM provider list; the old IP-block approach kept breaking on DNS rotation.", "decision", "technical", False,
     [("Cilium", "tool"), ("NetworkPolicy", "api"), ("DNS", "technology")],
     [],
     "which network policy mechanism survived provider IP churn",
     "egress FQDN selector DNS rotation IP block replace"),
    # --- 7 ---
    ("Gateway API rolled out behind the ingress gateway on 2026-02-18; HTTPRoute kept the existing Ingress in parallel for a three-week bake.", "milestone", "technical", False,
     [("Gateway API", "api"), ("HTTPRoute", "api"), ("Ingress", "api"), ("2026-02-18", "date")],
     [],
     "when did the new routing API land alongside the old Ingress",
     "Gateway API HTTPRoute parallel bake rollout date"),
    # --- 8 ---
    ("Ingress with nginx-ingress-controller was deprecated for new services; Gateway API plus Envoy Gateway is the default going forward.", "decision", "technical", False,
     [("Ingress", "api"), ("nginx-ingress-controller", "tool"), ("Gateway API", "api"), ("Envoy Gateway", "tool")],
     [("Gateway API", "Ingress", "REPLACES")],
     "which routing stack became the new default for green-field services",
     "nginx ingress deprecate Envoy Gateway default"),
    # --- 9 ---
    ("KEDA scales the Kafka consumer deployments off lag metrics; HorizontalPodAutoscaler alone could not see the backlog signal.", "decision", "technical", False,
     [("KEDA", "tool"), ("Kafka", "service"), ("HorizontalPodAutoscaler", "api")],
     [("KEDA", "HorizontalPodAutoscaler", "REPLACES")],
     "which autoscaler reads Kafka lag for the consumer deployments",
     "event driven scaler lag queue backlog HPA gap"),
    # --- 10. noise ---
    ("Hold on, let me peek at the pod events.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Vertical Pod Autoscaler runs in recommend-only mode on production; automatic updates kept restarting long-running batch pods mid-flight.", "problem", "technical", False,
     [("Vertical Pod Autoscaler", "tool")],
     [],
     "why does the VPA only advise instead of applying changes in production",
     "vertical autoscale recommend only restart batch disrupt"),
    # --- 12 ---
    ("Helm subcharts were flattened after the values override tree grew four levels deep; upgrades stopped surprising reviewers.", "decision", "technical", False,
     [("Helm", "tool")],
     [],
     "what change cleaned up the layered override tree for chart upgrades",
     "subchart flatten values override depth upgrade review"),
    # --- 13 ---
    ("Kustomize overlays handle per-environment patches; Helm stays for third-party charts, so the repo now tolerates both tools side by side.", "architecture", "technical", False,
     [("Kustomize", "tool"), ("Helm", "tool")],
     [],
     "how do the two templating tools split responsibility in the gitops repo",
     "overlay per environment patch third party chart split"),
    # --- 14 ---
    ("Crossplane manages the RDS instances and S3 buckets from the cluster; Terraform was retired for those resource classes.", "decision", "technical", False,
     [("Crossplane", "tool"), ("RDS", "service"), ("S3", "service"), ("Terraform", "tool")],
     [("Crossplane", "Terraform", "REPLACES")],
     "which cloud resources moved off Terraform and onto in-cluster management",
     "managed resource RDS S3 retire IaC replace"),
    # --- 15 ---
    ("ArgoCD ApplicationSet with the git generator keeps one Application per tenant folder; adding a tenant is now a single directory commit.", "architecture", "technical", False,
     [("ArgoCD", "tool"), ("ApplicationSet", "api")],
     [],
     "which mechanism turns a tenant folder into a live Application automatically",
     "ApplicationSet git generator tenant folder onboarding"),
    # --- 16 ---
    ("FluxCD was evaluated against ArgoCD; ArgoCD's UI carried the tie-breaker for the support team who drive most rollouts.", "decision", "technical", False,
     [("FluxCD", "tool"), ("ArgoCD", "tool")],
     [],
     "which gitops tool won the bake-off and why",
     "gitops compare UI tie breaker support team rollout"),
    # --- 17 ---
    ("Velero restore drills run every month against a scratch cluster; the first dry run caught a missing PodSecurityPolicy mapping.", "architecture", "technical", False,
     [("Velero", "tool"), ("PodSecurityPolicy", "api")],
     [],
     "which monthly exercise verifies the cluster backup tool actually works",
     "backup restore drill dry run policy mapping catch"),
    # --- 18 ---
    ("etcd compaction lag triggered the API slowness on 2026-03-08; raising auto-compaction-retention from 1 to 8 hours fixed it.", "problem", "technical", False,
     [("etcd", "service"), ("2026-03-08", "date")],
     [],
     "why did the control plane go sluggish on the March incident day",
     "etcd compaction retention knob API slow latency"),
    # --- 19 ---
    ("kube-apiserver flow control with APF priority levels shielded the health endpoints from a rogue CronJob's list-pods loop.", "architecture", "technical", False,
     [("kube-apiserver", "service"), ("APF", "api"), ("CronJob", "api")],
     [],
     "which feature kept the apiserver healthy during the runaway listing loop",
     "priority fairness flow control rogue CronJob list"),
    # --- 20 ---
    ("CoreDNS NodeLocal cache cut DNS p99 inside the cluster from 80 ms to 4 ms; the mesh was dropping connections during the spikes.", "milestone", "technical", False,
     [("CoreDNS", "service"), ("NodeLocal", "technology")],
     [],
     "which DNS change flattened the tail latency inside the cluster",
     "node local cache p99 DNS mesh drop spike"),
    # --- 21 ---
    ("Prometheus federation was replaced by Thanos sidecar uploads to object storage; cross-region queries now hit the querier layer.", "decision", "technical", False,
     [("Prometheus", "tool"), ("Thanos", "tool")],
     [("Thanos", "Prometheus", "REPLACES")],
     "which long-term metric strategy retired Prometheus federation",
     "federation sidecar object store querier cross region"),
    # --- 22 ---
    ("Mimir beat Thanos on our ingestion benchmarks at 3 million samples per second; we moved the multi-tenant backend to Mimir.", "decision", "technical", False,
     [("Mimir", "tool"), ("Thanos", "tool")],
     [("Mimir", "Thanos", "REPLACES")],
     "which TSDB backend took over the multi-tenant metric store",
     "multi tenant ingest benchmark samples per second backend"),
    # --- 23 ---
    ("Cortex was considered alongside Mimir but its roadmap had forked; Mimir inherited the feature pace and the community attention.", "decision", "technical", False,
     [("Cortex", "tool"), ("Mimir", "tool")],
     [],
     "which Cortex fork collected the active development momentum",
     "Cortex fork roadmap community momentum decide"),
    # --- 24 ---
    ("Loki's TSDB shipper index replaced the older BoltDB shipper; label queries across 14 days dropped from 18 seconds to under 3.", "decision", "technical", False,
     [("Loki", "tool"), ("TSDB shipper", "technology"), ("BoltDB shipper", "technology")],
     [("TSDB shipper", "BoltDB shipper", "REPLACES")],
     "which Loki index layout replaced the BoltDB one",
     "log index shipper label query latency swap"),
    # --- 25 ---
    ("Tempo ships traces straight to S3; the monolithic binary runs with local ingesters only, no Cassandra or Elasticsearch backend.", "architecture", "technical", False,
     [("Tempo", "tool"), ("S3", "service"), ("Cassandra", "database"), ("Elasticsearch", "database")],
     [],
     "which trace backend dodged the usual stateful dependency chain",
     "trace object storage monolithic no cassandra elasticsearch"),
    # --- 26 ---
    ("Grafana Alloy replaced the legacy Grafana Agent on the collector fleet; one config language covered metrics, logs, and traces.", "decision", "technical", False,
     [("Grafana Alloy", "tool"), ("Grafana Agent", "tool")],
     [("Grafana Alloy", "Grafana Agent", "REPLACES")],
     "which unified collector took over from the older Grafana Agent",
     "Alloy agent unify collector signal config replace"),
    # --- 27 ---
    ("OpenTelemetry Collector pipelines split the trace path: sampler then batch then OTLP exporter, no vendor SDK in the app code.", "architecture", "technical", False,
     [("OpenTelemetry Collector", "tool"), ("OTLP", "technology")],
     [],
     "how is the trace path structured inside the otel collector pipeline",
     "pipeline sampler batch exporter vendor agnostic app"),
    # --- 28 ---
    ("Jaeger on Cassandra was retired after the compaction storms kept taking the trace UI offline; Tempo on S3 took over.", "decision", "technical", False,
     [("Jaeger", "tool"), ("Cassandra", "database"), ("Tempo", "tool"), ("S3", "service")],
     [("Tempo", "Jaeger", "REPLACES")],
     "which tracing backend fell after the Cassandra compaction incidents",
     "Jaeger Cassandra compaction storm trace backend retire"),
    # --- 29 ---
    ("Datadog carried the application monitoring; Honeycomb was adopted alongside for deep trace analytics the Datadog UI flattens.", "decision", "technical", False,
     [("Datadog", "service"), ("Honeycomb", "service")],
     [],
     "which vendor pair split application monitoring from deep trace analysis",
     "Datadog Honeycomb split analytics high cardinality"),
    # --- 30 ---
    ("New Relic lost the RFP against Datadog on cost scaling past 1000 hosts; the pricing curve was the single deciding factor.", "decision", "technical", False,
     [("New Relic", "service"), ("Datadog", "service")],
     [],
     "which observability vendor lost the RFP and why",
     "RFP pricing curve host count decide vendor"),
    # --- 31 ---
    ("Exemplars wire Prometheus histograms to Tempo trace IDs; one click on a slow-latency bucket jumps straight to a matching span.", "architecture", "technical", False,
     [("Prometheus", "tool"), ("Tempo", "tool")],
     [],
     "which link carries users from a latency histogram to a concrete trace",
     "exemplar histogram trace id jump span correlation"),
    # --- 32 ---
    ("RED metrics track request rate, errors, and duration on the API tier; USE was kept for the node-level resource view.", "architecture", "technical", False,
     [("RED", "concept"), ("USE", "concept"), ("API", "api")],
     [],
     "which metric methodology fits the API tier versus the node tier",
     "RED USE request rate error duration utilisation"),
    # --- 33 ---
    ("Error budget burn alerts in the SLO framework use a 2-hour and 24-hour multi-window pair; the fast window pages, the slow one only emails.", "architecture", "technical", False,
     [("SLO", "concept")],
     [],
     "how are fast and slow burn alerts paired in the SLO setup",
     "multi window burn rate page email pair SLO"),
    # --- 34. noise ---
    ("One sec, need to check the node conditions.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The multi-burn-rate alert definition draws from the Google SRE workbook; copying the 14.4 and 6 factors saved a week of tuning.", "fact", "technical", False,
     [("Google SRE workbook", "publication")],
     [],
     "which reference supplied the burn-rate factors for the SLO alerts",
     "workbook factor 14.4 copy SLO alert tuning shortcut"),
    # --- 36 ---
    ("Blameless postmortems follow a Markdown template with timeline, contributing factors, and remediation tickets; the template lives in the runbook repo on GitHub.", "architecture", "technical", False,
     [("Markdown", "language"), ("GitHub", "service")],
     [],
     "which postmortem template shape is enforced for incident writeups",
     "blameless template timeline factors remediation runbook"),
    # --- 37 ---
    ("Descheduler runs nightly to rebalance pods after taints shift; the default LowNodeUtilization plugin handled it without custom config.", "architecture", "technical", False,
     [("Descheduler", "tool"), ("LowNodeUtilization", "api")],
     [],
     "which controller rebalances pods after nightly node churn",
     "descheduler rebalance utilisation plugin taint shift"),
    # --- 38 ---
    ("NodeLocal DNSCache replaced the per-pod resolver hack; DNS errors in the mesh trace view dropped to zero over a week.", "decision", "technical", False,
     [("NodeLocal DNSCache", "tool")],
     [],
     "which addon made the pod-side DNS hack unnecessary",
     "node local DNS cache pod resolver hack replace"),
    # --- 39 ---
    ("Argo Rollouts drives canary and blue-green deploys using AnalysisTemplates; Prometheus query results gate the next step automatically.", "architecture", "technical", False,
     [("Argo Rollouts", "tool"), ("AnalysisTemplate", "api"), ("Prometheus", "tool")],
     [],
     "which controller automates the canary gates from Prometheus queries",
     "rollout analysis template canary gate promql auto"),
    # --- 40 ---
    ("Flagger was tried first for progressive delivery; Argo Rollouts' UI integration with ArgoCD won the follow-up bake-off.", "decision", "technical", False,
     [("Flagger", "tool"), ("Argo Rollouts", "tool"), ("ArgoCD", "tool")],
     [("Argo Rollouts", "Flagger", "REPLACES")],
     "which progressive delivery tool replaced Flagger on our clusters",
     "progressive delivery Flagger replace UI integration bake"),
    # --- 41 ---
    ("Kyverno replaced Gatekeeper for admission policy; writing rules in YAML felt native versus wrestling Rego for the platform team.", "decision", "technical", False,
     [("Kyverno", "tool"), ("Gatekeeper", "tool"), ("Rego", "language")],
     [("Kyverno", "Gatekeeper", "REPLACES")],
     "which policy engine beat Gatekeeper on authoring ergonomics",
     "admission policy YAML native Rego avoid engine swap"),
    # --- 42 ---
    ("cert-manager with DNS01 challenges issues certificates cluster-wide; HTTP01 was abandoned after the private subnets blocked the callbacks.", "decision", "technical", False,
     [("cert-manager", "tool"), ("DNS01", "technology"), ("HTTP01", "technology")],
     [("DNS01", "HTTP01", "REPLACES")],
     "which ACME challenge survived the private subnet constraints",
     "DNS challenge HTTP01 private subnet callback swap"),
    # --- 43 ---
    ("External Secrets Operator pulls from HashiCorp Vault into cluster Secrets; the old Vault Agent sidecar pattern was retired.", "decision", "technical", False,
     [("External Secrets Operator", "tool"), ("HashiCorp Vault", "service"), ("Vault Agent", "tool")],
     [("External Secrets Operator", "Vault Agent", "REPLACES")],
     "which secret delivery pattern replaced the per-pod Vault sidecar",
     "external secrets operator agent sidecar retire vault"),
    # --- 44 ---
    ("Istio ambient mode went live on the trust domain on 2026-03-22; sidecar injection stays on for workloads that need per-pod policy.", "milestone", "technical", False,
     [("Istio", "tool"), ("2026-03-22", "date")],
     [],
     "when did the sidecar-less mesh mode reach the trust domain",
     "ambient mesh sidecar optional trust domain date"),
    # --- 45 ---
    ("Linkerd was replaced by Istio on the payments cluster; mTLS plus AuthorizationPolicy covered the compliance ask without a second mesh.", "decision", "technical", False,
     [("Linkerd", "tool"), ("Istio", "tool"), ("AuthorizationPolicy", "api")],
     [("Istio", "Linkerd", "REPLACES")],
     "which mesh took over the payments cluster to meet the compliance ask",
     "payments mesh compliance mTLS policy replace"),
    # --- 46 ---
    ("OpenCost reports live cost per namespace off Prometheus data; finance stopped asking for manual exports from the cloud console.", "architecture", "technical", False,
     [("OpenCost", "tool"), ("Prometheus", "tool")],
     [],
     "which tool turned Prometheus data into per-namespace cost reports",
     "cost allocation namespace Prometheus finance self serve"),
    # --- 47 ---
    ("Falco streams syscall events to the SIEM; the default ruleset caught a kubectl exec into a payments pod within 40 seconds.", "architecture", "technical", False,
     [("Falco", "tool"), ("SIEM", "service"), ("kubectl", "tool")],
     [],
     "which runtime security tool caught the unauthorised exec into payments",
     "runtime syscall exec detection SIEM payments pod"),
    # --- 48 ---
    ("Tetragon runs alongside Falco for eBPF process-tree alerts; the two feeds converge into the detection pipeline without dedup noise.", "architecture", "technical", False,
     [("Tetragon", "tool"), ("Falco", "tool"), ("eBPF", "technology")],
     [],
     "which second runtime agent complements Falco with process-tree visibility",
     "eBPF process tree Tetragon Falco converge detection"),
    # --- 49 ---
    ("kube-bench runs on every node on a weekly CronJob; CIS drift now shows up as a ticket instead of a surprise audit finding.", "architecture", "technical", False,
     [("kube-bench", "tool"), ("CIS", "concept"), ("CronJob", "api")],
     [],
     "which recurring check catches CIS drift before audits do",
     "CIS benchmark drift weekly audit ticket recurring"),
    # --- 50 ---
    ("Robusta routes Prometheus alerts into Slack with enriched pod state; the runbook links live inside the alert payload itself.", "architecture", "technical", False,
     [("Robusta", "tool"), ("Prometheus", "tool"), ("Slack", "service")],
     [],
     "which alert router embeds the runbook link beside pod state in Slack",
     "alert routing Slack runbook payload pod state enrich"),
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
