"""One-off emitter for classification top-up batch-008 — decision/architecture, infra slice.

Same pattern as _emit_shared_batch_006.py; classification schema has only
{id, domain, text, memory_type, pair_id}. 50 pairs (100 rows), each pair = one
`decision` row + one `architecture` row on the same infrastructure topic.
Appends 100 rows to data/v2/classification/batch_008.tmp.jsonl with ids
class-00701..00800 and pair ids cls-pair-00351..00400.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_008.tmp.jsonl"
ID_OFFSET = 700
PAIR_OFFSET = 350

# (decision_text, architecture_text)
PAIRS: list[tuple[str, str]] = [
    # --- 1. cluster hosting: self-managed k8s -> GKE Autopilot ---
    ("Moved from self-managed Kubernetes to GKE Autopilot after the fourth CVE scramble in a quarter cost us two weekends.",
     "Workloads run on a GKE Autopilot cluster in europe-west1 fronted by a global HTTPS load balancer with Cloud Armor WAF rules."),
    # --- 2. cluster hosting: EKS -> AKS for Azure commitments ---
    ("Chose AKS over EKS for the new Azure commitment; the existing Enterprise Agreement absorbed the control plane cost entirely.",
     "The staging cluster is an AKS deployment in westeurope with three node pools: system, general workloads, and GPU-tainted inference nodes."),
    # --- 3. networking: Calico -> Cilium ---
    ("Swapped Calico for Cilium after the eBPF datapath benchmarks showed 30% lower p99 latency on east-west traffic.",
     "Pod networking runs on Cilium in kube-proxy-replacement mode with Hubble exporting flow logs to the observability cluster."),
    # --- 4. DNS: Route 53 + CoreDNS split ---
    ("Decided to keep Route 53 for public zones and CoreDNS for cluster-internal resolution instead of unifying on one provider.",
     "Public records live in Route 53 with health-checked failover; in-cluster lookups resolve via CoreDNS with a stub zone for corp.internal."),
    # --- 5. load balancing: ALB -> NLB for gRPC ---
    ("Moved gRPC ingress off ALBs onto NLBs after HTTP/2 connection reuse repeatedly pinned pods on a single target."),
    # placeholder second replaced below
    # --- placeholder to keep index alignment; real entry follows in list order ---
]

# Rebuilt cleanly below — ignore placeholder above.
PAIRS = [
    # --- 1. cluster hosting: self-managed k8s -> GKE Autopilot ---
    ("Moved from self-managed Kubernetes to GKE Autopilot after the fourth CVE scramble in a quarter cost us two weekends.",
     "Workloads run on a GKE Autopilot cluster in europe-west1 fronted by a global HTTPS load balancer with Cloud Armor WAF rules."),
    # --- 2. cluster hosting: EKS vs AKS ---
    ("Chose AKS over EKS for the new Azure commitment; the existing Enterprise Agreement absorbed the control plane cost entirely.",
     "The staging cluster is an AKS deployment in westeurope with three node pools: system, general workloads, and GPU-tainted inference nodes."),
    # --- 3. networking: Calico -> Cilium ---
    ("Swapped Calico for Cilium after the eBPF datapath benchmarks showed 30 percent lower p99 latency on east-west traffic.",
     "Pod networking runs on Cilium in kube-proxy-replacement mode with Hubble exporting flow logs to the observability cluster."),
    # --- 4. DNS: split authority ---
    ("Decided to keep Route 53 for public zones and CoreDNS for cluster-internal resolution instead of unifying on one provider.",
     "Public records live in Route 53 with health-checked failover while in-cluster lookups resolve via CoreDNS with a stub zone for corp.internal."),
    # --- 5. load balancing: ALB -> NLB for gRPC ---
    ("Moved gRPC ingress off ALBs onto NLBs after HTTP/2 connection reuse repeatedly pinned pods on a single target for minutes.",
     "gRPC traffic terminates on an NLB in each region which forwards to Envoy ingress pods that handle TLS and per-method routing."),
    # --- 6. CDN: Cloudflare over Fastly ---
    ("Chose Cloudflare over Fastly for the CDN layer because bundled bot management and WAF were a single contract.",
     "Static assets and image origin are fronted by Cloudflare CDN with cache-key normalisation and a same-origin worker injecting CSP headers."),
    # --- 7. container runtime: Docker -> containerd ---
    ("Dropped the Docker shim on worker nodes in favour of containerd after Kubernetes 1.24 made the deprecation final.",
     "All nodes run containerd 1.7 with the systemd cgroup driver; image pulling goes through a Harbor mirror on the same subnet."),
    # --- 8. hypervisor: VMware -> Proxmox ---
    ("Migrated the colo hypervisors from VMware vSphere to Proxmox VE once the Broadcom licensing hike made renewal untenable.",
     "The colo runs two Proxmox VE clusters of four nodes each with Ceph RBD as the shared storage backend for live migration."),
    # --- 9. IaC: CloudFormation -> Terraform ---
    ("Replaced the CloudFormation stacks with Terraform so we could manage AWS, GCP, and Cloudflare from one tool and one state backend.",
     "Infrastructure is defined in Terraform with state stored in an S3 bucket plus DynamoDB locks, organised into per-environment workspaces."),
    # --- 10. IaC: Terraform -> Pulumi TypeScript ---
    ("Picked Pulumi with TypeScript over another Terraform rollout because the platform team wanted real types and unit tests on stack outputs.",
     "The platform code is a Pulumi TypeScript monorepo that exposes a handful of component resources wrapping AWS, GitHub, and Datadog providers."),
    # --- 11. secrets: Vault -> AWS Secrets Manager ---
    ("Retired the self-hosted HashiCorp Vault cluster in favour of AWS Secrets Manager; the ops cost of two Vault outages per quarter was not worth it.",
     "Application secrets sit in AWS Secrets Manager with rotation lambdas on a 30-day cadence and IAM-scoped access per service role."),
    # --- 12. secrets: SOPS with age keys ---
    ("Standardised on SOPS with age keys for all in-repo secrets instead of encrypted dotenv files scattered per service.",
     "Each repo ships a .sops.yaml declaring its age recipients and a CI job decrypts the selected file into a short-lived env at deploy time."),
    # --- 13. PKI: ACME via cert-manager ---
    ("Moved away from the internal CA-signed certificates to ACME via Let's Encrypt after the internal CA expired unnoticed and took two regions offline.",
     "All ingress certificates are issued by cert-manager through the Let's Encrypt production issuer with HTTP-01 challenges terminated at the edge."),
    # --- 14. PKI: private CA for mTLS ---
    ("Kept the private PKI for workload mTLS even after moving public edges to ACME; service identity belongs to us, not a public CA.",
     "Workload identities are issued by an internal SPIFFE-compatible CA with 24-hour certificates distributed by a sidecar on every pod."),
    # --- 15. backup: pgBackRest over native dumps ---
    ("Adopted pgBackRest for Postgres backups after pg_dump slots held the WAL for hours and pushed disks to 95 percent on the primary.",
     "Each Postgres primary streams WAL to pgBackRest which writes full and differential backups to object storage with a 30-day retention window."),
    # --- 16. backup: Velero for cluster state ---
    ("Decided Velero was mandatory before we let product teams run Argo apps with stateful charts in the shared cluster.",
     "Velero runs on every cluster with a daily schedule that snapshots all namespaces and ships restic payloads plus PV snapshots to a regional bucket."),
    # --- 17. DR: warm standby over cold ---
    ("Rejected a cold DR target in favour of a warm standby after tabletop exercises showed we could not meet the 1-hour RTO with a cold spin-up.",
     "DR lives in us-east-2 as a warm standby: Aurora global database replica, scaled-to-one Kubernetes deployments, and DNS weighted at 0 until failover."),
    # --- 18. DR: multi-region active/active ---
    ("Committed to active/active across two AWS regions instead of active/passive so the quarterly failover game days were no longer a fire drill.",
     "Traffic is split 50/50 between us-east-1 and eu-west-1 via Route 53 latency records with per-region Aurora writers and conflict-free replicated state."),
    # --- 19. observability stack: Datadog -> OSS ---
    ("Dropped Datadog after the annual bill crossed mid six figures and the platform team said they could run the OSS stack for a fraction of the cost.",
     "Observability runs on a self-hosted stack of Prometheus, Loki, Tempo, and Grafana with Mimir fronting long-term metric storage on S3."),
    # --- 20. observability stack: adopting Honeycomb ---
    ("Picked Honeycomb for production tracing over an internal Jaeger build; BubbleUp paid for itself in the first two incidents.",
     "Application services emit OTLP spans to a Honeycomb ingest endpoint through a regional collector that handles sampling and tail-based retention."),
    # --- 21. logging: Fluent Bit over Fluentd ---
    ("Replaced the Fluentd daemonsets with Fluent Bit after the Ruby footprint cost us 1 GB of RAM per node for no functional gain.",
     "Every node runs a Fluent Bit daemonset that tails container logs, enriches with Kubernetes metadata, and forwards to Loki over gRPC."),
    # --- 22. logging: Vector for transformations ---
    ("Chose Vector as the aggregation layer instead of Logstash because the config is typed and the pipeline can be unit-tested offline.",
     "Per-region Vector aggregators receive logs from edge collectors, apply VRL-based PII scrubbing, and fan out to Loki, S3, and SIEM sinks."),
    # --- 23. metrics: VictoriaMetrics over Thanos ---
    ("Switched long-term metrics from Thanos to VictoriaMetrics; Thanos store-gateway cost and query latency at our cardinality were unworkable.",
     "Metrics are scraped by vmagent, shipped to a vmcluster of three vmstorage nodes per region, and queried through vmselect behind Grafana."),
    # --- 24. metrics: Prometheus remote_write to Mimir ---
    ("Kept Prometheus at the cluster edge but remote-wrote everything into Mimir so the on-call teams never had to federate by hand again.",
     "Each cluster runs a Prometheus pair with remote_write pointed at a central Mimir deployment backed by S3 for long-term blocks."),
    # --- 25. tracing: OpenTelemetry collector topology ---
    ("Standardised on the OpenTelemetry Collector as the single tracing ingress instead of running vendor agents next to each application.",
     "Applications emit OTLP to a collector daemonset which batches, samples, and exports to Tempo for trace storage and to Mimir for RED metrics."),
    # --- 26. tracing: Jaeger retention trim ---
    ("Cut Jaeger retention from 14 days to 3 after storage costs doubled in a quarter and nobody queried traces older than 48 hours.",
     "Jaeger runs with a Cassandra backend limited to 3-day TTL per span index and an archive path for flagged traces that writes to S3 for 90 days."),
    # --- 27. VPN: Tailscale over WireGuard hand-rolled ---
    ("Retired the hand-rolled WireGuard mesh in favour of Tailscale once the ACL tooling started reviewing itself and the key distribution broke in DR.",
     "Operator access to prod flows through Tailscale with ACLs generated from the HR system and exit nodes landing in each cloud VPC."),
    # --- 28. VPN: IPsec tunnels for partner B2B ---
    ("Kept IPsec tunnels for partner B2B links even after migrating staff to Tailscale; partners require dedicated static-routed endpoints.",
     "Partner integrations terminate on two IPsec VPN gateways in us-east-1 with BGP peering into a dedicated transit VPC that hosts the exchange services."),
    # --- 29. bastion: AWS SSM over SSH bastion ---
    ("Killed the SSH bastion fleet and switched to AWS Session Manager; key rotation and just-in-time access were both solved for free.",
     "Shell access to EC2 instances goes through AWS Session Manager with IAM roles gating which principals can start sessions on which tags."),
    # --- 30. bastion: Teleport for audited access ---
    ("Chose Teleport over Boundary for privileged access because the recording and RBAC model lined up cleanly with the SOC 2 audit requirements.",
     "Teleport proxies sit in a dedicated VPC and broker SSH, Kubernetes, and Postgres sessions with full session recording to an S3 bucket."),
    # --- 31. multi-region: failover automation ---
    ("Automated the regional failover runbook after the manual procedure missed a single Terraform variable and cost us another 20 minutes.",
     "Failover is driven by a Step Functions state machine that flips Route 53 weights, promotes the Aurora replica, and drains the stale ASG in parallel."),
    # --- 32. multi-region: data locality constraints ---
    ("Held the line on EU-only data storage for EU customers instead of a cheaper single-region design once GDPR legal review flagged the transfer risk.",
     "EU customer data lives in two eu-west subnets with replicated Postgres and S3 buckets, all KMS-encrypted with keys that never leave the region."),
    # --- 33. cost optimisation: Savings Plans over on-demand ---
    ("Committed to a three-year compute Savings Plan covering 70 percent of baseline EC2 usage; the finance team signed off after the first quarterly review.",
     "Baseline compute runs on reserved capacity backed by a compute Savings Plan with bursts served by on-demand and interruptible spot capacity."),
    # --- 34. cost optimisation: spot-first batch fleet ---
    ("Moved the batch ML fleet to spot-first after a month of checkpointing work proved interruptions were cheaper than on-demand pricing.",
     "Batch training jobs run on a Karpenter-managed spot node group with per-job checkpointing to S3 and a fallback on-demand pool for stragglers."),
    # --- 35. storage: EBS gp3 over gp2 ---
    ("Rolled the fleet from gp2 to gp3 volumes once the IOPS-per-dollar math became unambiguous at any volume size above 100 GiB.",
     "All stateful workloads use gp3 volumes with baseline IOPS provisioned per workload tier and snapshot schedules managed by AWS Backup."),
    # --- 36. storage: MinIO on-prem object store ---
    ("Stood up MinIO on the colo hardware instead of a pure cloud object store because the data residency contract required on-site copies.",
     "On-prem object storage is a four-node MinIO cluster in erasure-coded mode behind an HAProxy layer with replication to an offsite S3 bucket."),
    # --- 37. service mesh: Istio -> Linkerd ---
    ("Ripped out Istio after the third control-plane upgrade broke mTLS on a Friday afternoon; Linkerd's smaller surface area was worth the feature loss.",
     "Service-to-service traffic flows through a Linkerd mesh with automatic mTLS and per-deployment traffic shift manifests driving progressive rollouts."),
    # --- 38. service mesh: consul connect for VMs ---
    ("Chose Consul Connect over a pure Kubernetes mesh because half the workloads still run on VMs and needed the same identity fabric.",
     "VMs and pods share identity through Consul Connect; envoy sidecars are injected by Nomad or the Kubernetes webhook depending on workload type."),
    # --- 39. ingress: nginx -> Envoy ---
    ("Replaced the nginx ingress controller with Envoy-based Contour after per-tenant rate limiting turned into a lua maintenance problem.",
     "Edge ingress runs Contour with Envoy data planes; per-tenant RateLimitPolicy CRDs feed into a global ratelimit service backed by Redis."),
    # --- 40. ingress: API gateway consolidation ---
    ("Consolidated three separate API gateways onto a single Kong deployment after plugin drift caused contradictory auth behaviours across teams.",
     "All north-south HTTP traffic enters a Kong gateway tier where JWT validation, mTLS enforcement, and request transformation plugins run in a fixed order."),
    # --- 41. DB hosting: self-managed PG -> Aurora ---
    ("Moved the primary transactional database from self-managed Postgres on EC2 to Aurora PostgreSQL after the on-call rota blamed failovers three quarters running.",
     "OLTP workloads run on an Aurora PostgreSQL cluster with one writer and three readers, snapshotted daily and replicated to a second region for DR."),
    # --- 42. DB hosting: CockroachDB dedicated ---
    ("Chose CockroachDB Dedicated over self-hosting the same binary; we wanted the distributed SQL guarantees without owning the node repair story.",
     "Ledger workloads run on CockroachDB Dedicated in a three-region configuration with survival mode set to region failure and backups to object storage."),
    # --- 43. cache: Redis Cluster sharding ---
    ("Rejected a managed Redis in favour of self-hosted Redis Cluster once the managed per-shard pricing crossed the break-even against a small SRE rota.",
     "The shared cache tier is a six-shard Redis Cluster on dedicated nodes with TLS between primaries and replicas and Sentinel wired only for failover detection."),
    # --- 44. cache: Memcached for session store ---
    ("Kept Memcached for session storage even after moving everything else to Redis; the single-purpose simplicity kept paging incidents at zero for two years.",
     "Session data sits in a three-node Memcached fleet behind a consistent-hash client library with a TTL equal to the session cookie lifetime."),
    # --- 45. queueing: SQS over self-hosted Rabbit ---
    ("Retired the self-hosted RabbitMQ cluster in favour of SQS for general async work; quorum queue operations were eating one engineer-week per month.",
     "Async jobs flow through SQS standard queues with a separate FIFO queue for billing writes and DLQs configured for five retries before alerting."),
    # --- 46. queueing: Kafka over Kinesis ---
    ("Stuck with self-managed Kafka rather than Kinesis because exactly-once semantics with compacted topics were not achievable on the managed offering when we evaluated.",
     "Event backbone is a Kafka cluster of nine brokers per region using KRaft mode, TLS/SASL auth, and MirrorMaker 2 for cross-region topic replication."),
    # --- 47. CI/CD: GitHub Actions -> Buildkite ---
    ("Moved long CI pipelines from GitHub-hosted Actions to self-hosted Buildkite agents after single-job times consistently crossed the 6-hour hard limit.",
     "CI runs on a Buildkite agent fleet autoscaled on EKS with ephemeral runners per job and a shared S3-backed artifact cache keyed by dependency lockfile hashes."),
    # --- 48. CD: ArgoCD progressive delivery ---
    ("Adopted ArgoCD with Argo Rollouts over the home-grown deploy script once a bad canary slipped through and took 25 percent of traffic for 9 minutes.",
     "Every service deploys via ArgoCD with Rollouts CRDs driving 5/25/50/100 percent canary steps gated on Prometheus analysis queries and manual approval at 50."),
    # --- 49. WAF/edge security: Cloud Armor rules ---
    ("Shifted bot mitigation from an in-cluster nginx module up to Cloud Armor after a volumetric attack saturated the ingress NLB for 12 minutes.",
     "Public traffic passes a Cloud Armor policy with managed bot rules, a rate-limit rule per origin IP, and a WAF preconfigured rule set for OWASP top 10."),
    # --- 50. runbooks: SLO-driven alerting ---
    ("Dropped symptom-based CPU alerts in favour of SLO-driven alerting because two years of page data showed CPU alerts had a 6 percent precision rate.",
     "Alerting is driven by Sloth-generated SLOs; burn-rate alerts at 2 percent and 5 percent of the monthly budget page the on-call, everything else is a ticket."),
]


def emit() -> int:
    assert len(PAIRS) == 50, f"expected 50 pairs, got {len(PAIRS)}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (dec_text, arch_text) in enumerate(PAIRS, start=1):
            pair_id = f"cls-pair-{PAIR_OFFSET + i:05d}"
            dec_row = {
                "id": f"class-{ID_OFFSET + (2 * i - 1):05d}",
                "domain": "technical",
                "text": dec_text,
                "memory_type": "decision",
                "pair_id": pair_id,
            }
            arch_row = {
                "id": f"class-{ID_OFFSET + (2 * i):05d}",
                "domain": "technical",
                "text": arch_text,
                "memory_type": "architecture",
                "pair_id": pair_id,
            }
            f.write(json.dumps(dec_row, ensure_ascii=False) + "\n")
            f.write(json.dumps(arch_row, ensure_ascii=False) + "\n")
            written += 2
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
