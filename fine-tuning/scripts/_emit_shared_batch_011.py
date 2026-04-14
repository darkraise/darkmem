"""One-off emitter for shared-base batch-011 — technical domain (round 3).

Same pattern as _emit_shared_batch_006.py; only ENTRIES and ID_OFFSET change.
Writes 50 rows to data/v2/shared/batch_011.tmp.jsonl with ids shared-00501..00550.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_011.tmp.jsonl"
ID_OFFSET = 500

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Flink state backend moved to RocksDB because the on-heap option kept tipping the job manager into long GC pauses.", "decision", "technical", False,
     [("Flink", "framework"), ("RocksDB", "library")],
     [],
     "which store powers the streaming job's checkpointed state now",
     "keyed backend embedded kv migration reason pauses"),
    # --- 2 ---
    ("Prometheus remote_write into Mimir gave us multi-tenant long-term metrics; the tradeoff was a hefty ingester fleet.", "architecture", "technical", False,
     [("Prometheus", "service"), ("remote_write", "api"), ("Mimir", "service")],
     [],
     "how did we get long-retention tenancy for scrape samples",
     "monitoring forwarding multi-tenant cost fleet size"),
    # --- 3 ---
    ("Thanos was rejected in favour of Mimir; the hash-ring ingest path fit our write volumes better than sidecar upload.", "decision", "technical", False,
     [("Thanos", "service"), ("Mimir", "service")],
     [("Mimir", "Thanos", "REPLACES")],
     "which global metrics stack beat the sidecar-upload alternative",
     "horizontal ingester ring choice sidecar upload rejected"),
    # --- 4 ---
    ("Ceph pool layouts split hot RGW buckets onto NVMe OSDs while cold archives live on spinning rust with erasure coding.", "architecture", "technical", False,
     [("Ceph", "service"), ("RGW", "service"), ("NVMe", "technology"), ("erasure coding", "algorithm")],
     [],
     "how are hot and cold object buckets physically separated in the cluster",
     "storage tier device class archive coding layout"),
    # --- 5 ---
    ("MinIO drifted from S3 semantics on multipart abort behaviour; caught the gap in an integration contract test.", "problem", "technical", False,
     [("MinIO", "service"), ("S3", "service")],
     [],
     "where did the self-hosted object store disagree with the AWS original",
     "compatible object abort multipart drift caught test"),
    # --- 6 ---
    ("Vault dynamic secrets now issue short-lived Postgres roles per application instance; no more shared service passwords.", "decision", "technical", False,
     [("Vault", "service"), ("Postgres", "database")],
     [],
     "how are database credentials scoped per service instance now",
     "dynamic role short-lived shared password retirement"),
    # --- 7 ---
    ("SOPS with age keys replaced the legacy PGP workflow for encrypted config in git; onboarding stopped being a ceremony.", "decision", "technical", False,
     [("SOPS", "tool"), ("age", "tool"), ("PGP", "protocol")],
     [("age", "PGP", "REPLACES")],
     "which key scheme took over from the older GnuPG flow for repo secrets",
     "secrets committed file encryption scheme swap onboarding"),
    # --- 8 ---
    ("MySQL 8 replication outperformed MariaDB for our write-heavy tenant shards; we committed to MySQL for new shards.", "decision", "technical", False,
     [("MySQL 8", "database"), ("MariaDB", "database")],
     [("MySQL 8", "MariaDB", "PREFERS")],
     "which relational engine wins for write-heavy shards and why",
     "SQL fork benchmark write heavy shard choice"),
    # --- 9 ---
    ("MongoDB change streams drive the search indexer; resume tokens survive replica-set elections cleanly.", "architecture", "technical", False,
     [("MongoDB", "database")],
     [],
     "how does the search side stay in sync with the document store",
     "document database oplog follower resilience failover"),
    # --- 10. noise ---
    ("Hmm, one moment while I pull up the dashboard.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("etcd compaction lagged behind the defrag schedule; write latency doubled until we wired both to the same cron.", "problem", "technical", False,
     [("etcd", "database")],
     [],
     "what happened when maintenance jobs fell out of sync for the control-plane store",
     "KV log pruning defrag cadence latency root cause"),
    # --- 12 ---
    ("Helm templating pain drove us to Kustomize overlays for environment-specific config; Go template escaping became a source of bugs.", "decision", "technical", False,
     [("Helm", "tool"), ("Kustomize", "tool"), ("Go template", "library")],
     [("Kustomize", "Helm", "REPLACES")],
     "which config tool replaced the chart-based one for per-environment variants",
     "overlay patches environment override template escape pain"),
    # --- 13 ---
    ("Crossplane manages a handful of RDS instances as Kubernetes resources; drift detection catches manual console edits.", "architecture", "technical", False,
     [("Crossplane", "framework"), ("RDS", "service"), ("Kubernetes", "platform")],
     [],
     "how are cloud databases exposed as cluster-native objects in our stack",
     "managed resource controller console drift detect"),
    # --- 14 ---
    ("Gatekeeper policies backed by OPA block any workload that requests privileged mode or hostPath without an exemption label.", "architecture", "technical", False,
     [("Gatekeeper", "tool"), ("OPA", "framework"), ("hostPath", "api")],
     [],
     "what stops privileged or host-mounted pods from landing in the cluster",
     "admission rule engine escape hatch label guardrail"),
    # --- 15 ---
    ("Falco caught a cryptominer drop via an unexpected syscall on 2026-03-18; runtime detection has paid for itself.", "milestone", "technical", False,
     [("Falco", "tool"), ("2026-03-18", "date")],
     [],
     "when did the runtime detector first catch an active intruder in our fleet",
     "kernel audit miner drop detection date win"),
    # --- 16 ---
    ("Trivy runs in CI on every image build; the supply-chain job also emits SBOMs to an OCI artifact registry.", "architecture", "technical", False,
     [("Trivy", "tool"), ("CI", "service"), ("SBOM", "concept"), ("OCI", "protocol")],
     [],
     "what does the image pipeline do for vulnerability and provenance coverage",
     "scanner SBOM artifact registry build step"),
    # --- 17 ---
    ("SLSA provenance level 3 landed for the payments service after we switched build signing to a hardened runner pool.", "milestone", "technical", False,
     [("SLSA", "concept"), ("payments service", "project")],
     [],
     "which team first reached the higher supply-chain attestation tier",
     "provenance attestation tier hardened runner payments"),
    # --- 18 ---
    ("Reproducible builds shifted from raw Bazel to Nix for the toolchain layer; hermetic inputs stopped leaking host clock skew.", "decision", "technical", False,
     [("Bazel", "tool"), ("Nix", "tool")],
     [("Nix", "Bazel", "REPLACES")],
     "which tool took the toolchain layer over from the previous hermetic builder",
     "deterministic rebuild toolchain pinning host clock leak"),
    # --- 19 ---
    ("Tilt replaced ad-hoc Makefiles for the inner loop; live-update of Go binaries in-cluster cut edit-to-run to six seconds.", "decision", "technical", False,
     [("Tilt", "tool"), ("Makefiles", "file"), ("Go", "language")],
     [("Tilt", "Makefiles", "REPLACES")],
     "what replaced handwritten build shortcuts for the local dev loop",
     "inner loop live update in-cluster edit run speed"),
    # --- 20 ---
    ("Skaffold is preferred over Tilt for CI ephemeral previews; YAML-first config slots into review pipelines cleanly.", "preference", "technical", False,
     [("Skaffold", "tool"), ("Tilt", "tool"), ("YAML", "language")],
     [("Skaffold", "Tilt", "PREFERS")],
     "which ephemeral preview tool wins in the review pipeline over the live loop one",
     "declarative preview pipeline config reviewers"),
    # --- 21 ---
    ("Traefik v3 labels confused an older provider; upgrading the Docker provider to v3-native syntax stopped the silent 404s.", "problem", "technical", False,
     [("Traefik v3", "service"), ("Docker", "tool")],
     [],
     "why were routes returning not-found after the ingress upgrade",
     "label provider schema syntax bump silent miss"),
    # --- 22 ---
    ("Caddy handles autocert for the public dashboards; DNS-01 via Cloudflare avoids exposing port 80 on the bastion.", "architecture", "technical", False,
     [("Caddy", "service"), ("Cloudflare", "service")],
     [],
     "how do the public dashboards get their TLS certs without opening http",
     "reverse proxy DNS challenge bastion port closed"),
    # --- 23 ---
    ("HAProxy dynamic resolvers cache DNS answers for upstream services; stale TTLs still bit us during a Consul flap.", "problem", "technical", False,
     [("HAProxy", "service"), ("DNS", "protocol"), ("Consul", "service")],
     [],
     "what gotcha showed up around cached name lookups in the load balancer",
     "dynamic resolver TTL service discovery flap bite"),
    # --- 24 ---
    ("Adopted io_uring for the high-throughput log shipper; syscall overhead halved on the ARM64 edge boxes.", "decision", "technical", False,
     [("io_uring", "technology"), ("ARM64", "platform")],
     [],
     "which kernel interface drove the log shipper speedup on edge hardware",
     "async submission ring edge ARM syscall halving"),
    # --- 25 ---
    ("Pixie's eBPF profiler surfaced a chatty health-check loop that was burning 8 percent of cluster CPU.", "problem", "technical", False,
     [("Pixie", "tool"), ("eBPF", "technology")],
     [],
     "what did the low-overhead profiler find chewing cluster CPU",
     "kernel tracing health ping hotspot cluster burn"),
    # --- 26 ---
    ("OpenTelemetry Collector processors handle tail-based sampling and PII redaction before export to the vendor backend.", "architecture", "technical", False,
     [("OpenTelemetry Collector", "service")],
     [],
     "what does the telemetry gateway do between apps and the vendor backend",
     "sampling redaction processor chain export vendor"),
    # --- 27 ---
    ("Zig cross-compilation toolchains dropped our Linux binary build time to seconds; the libc matrix is included in the compiler.", "fact", "technical", False,
     [("Zig", "language"), ("Linux", "platform"), ("libc", "library")],
     [],
     "which compiler gives us near-instant cross builds for the Linux targets",
     "cross toolchain bundled system library time drop"),
    # --- 28 ---
    ("C++20 modules finally replaced precompiled headers in the rendering core; incremental rebuilds got predictable again.", "decision", "technical", False,
     [("C++20", "language"), ("modules", "concept"), ("precompiled headers", "concept")],
     [("modules", "precompiled headers", "REPLACES")],
     "what new language feature took over from the old header caching in the renderer",
     "standard import unit incremental rebuild predictable"),
    # --- 29 ---
    ("LLVM ThinLTO link-time optimisation trimmed 12 percent off the release binary; full LTO was too slow to merge every PR.", "decision", "technical", False,
     [("LLVM", "framework"), ("ThinLTO", "algorithm"), ("full LTO", "algorithm")],
     [("ThinLTO", "full LTO", "IMPROVES_ON")],
     "which build optimisation shrank the release image without blocking every PR",
     "link optimiser parallel summary binary size cut"),
    # --- 30 ---
    ("Swift concurrency actors moved mutable dashboard state off of ad-hoc locks; race reports in production dropped to zero.", "decision", "technical", False,
     [("Swift", "language"), ("actors", "concept")],
     [],
     "what concurrency model finally killed the mutable-state races in the dashboard",
     "actor model isolation lock removal race reports"),
    # --- 31 ---
    ("Kotlin coroutines over Project Reactor kept the Android client clean; backpressure was rarely the interesting axis.", "preference", "technical", False,
     [("Kotlin", "language"), ("Project Reactor", "framework"), ("Android", "platform")],
     [("Kotlin", "Project Reactor", "PREFERS")],
     "which async style the mobile client picked and why",
     "structured concurrency mobile reactive backpressure tradeoff"),
    # --- 32 ---
    ("Lua on OpenResty handles rate limiting at the edge; co-routines per request kept the memory footprint predictable.", "architecture", "technical", False,
     [("Lua", "language"), ("OpenResty", "platform")],
     [],
     "how does the edge handle per-request rate limiting without bloating memory",
     "scripting edge limiter coroutine footprint stable"),
    # --- 33 ---
    ("Cilium replaced kube-proxy on the production clusters on 2026-02-12; eBPF datapath cut P99 service latency by 30 percent.", "milestone", "technical", False,
     [("Cilium", "service"), ("kube-proxy", "service"), ("eBPF", "technology"), ("2026-02-12", "date")],
     [("Cilium", "kube-proxy", "REPLACES")],
     "when did the eBPF networking layer fully push out the older proxy",
     "datapath swap cluster rollout latency reduction"),
    # --- 34. noise ---
    ("Give me a second to tail the logs.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Linkerd identity issues workload certificates rooted in a shared trust anchor; rotation is automatic on the 24-hour mark.", "architecture", "technical", False,
     [("Linkerd", "service")],
     [],
     "how do pods prove their identity in the lightweight mesh",
     "mesh identity anchor certificate rotation window"),
    # --- 36 ---
    ("Sidekiq moved off Resque for the Ruby job fleet; Redis-backed reliability features removed a class of duplicate runs.", "decision", "technical", False,
     [("Sidekiq", "library"), ("Resque", "library"), ("Ruby", "language"), ("Redis", "database")],
     [("Sidekiq", "Resque", "REPLACES")],
     "which Ruby worker library replaced the older forked one",
     "background jobs Ruby swap duplicate run removal"),
    # --- 37 ---
    ("BullMQ powers the Node.js queue tier; delayed jobs and prioritised lanes shipped without custom Redis scripts.", "architecture", "technical", False,
     [("BullMQ", "library"), ("Node.js", "platform"), ("Redis", "database")],
     [],
     "which library handles delayed and priority jobs on the Node side",
     "Node queue delay priority lane builtin features"),
    # --- 38 ---
    ("Prefers Pub/Sub over SQS for global fan-out; at-least-once across regions saved a bespoke bridge service.", "preference", "technical", False,
     [("Pub/Sub", "service"), ("SQS", "service")],
     [("Pub/Sub", "SQS", "PREFERS")],
     "which managed queue wins for worldwide delivery scenarios",
     "global topic delivery semantics region bridge saved"),
    # --- 39 ---
    ("SNS fan-out into multiple SQS subscribers lets the billing pipeline branch into retry, archive, and analytics without coupling.", "architecture", "technical", False,
     [("SNS", "service"), ("SQS", "service")],
     [],
     "how does one upstream event reach several downstream consumers without tight coupling",
     "topic subscriber fanout decoupled consumer pattern"),
    # --- 40 ---
    ("AWS IAM Identity Center became the single sign-on source for all engineering consoles on 2026-01-05.", "milestone", "technical", False,
     [("AWS IAM Identity Center", "service"), ("2026-01-05", "date")],
     [],
     "when did our engineers get a single login for every AWS account",
     "SSO consolidation console sign in launch"),
    # --- 41 ---
    ("GitHub Advanced Security code scanning caught a SQL injection in a rarely-touched admin blade during a merge queue run.", "milestone", "technical", False,
     [("GitHub Advanced Security", "service"), ("SQL", "language")],
     [],
     "what saved us from a dormant injection bug right before merge",
     "static scan merge queue admin blade injection catch"),
    # --- 42 ---
    ("Renovate config pins group rules and schedule windows per repo; Dependabot could not express weekday-only updates.", "decision", "technical", False,
     [("Renovate", "tool"), ("Dependabot", "tool")],
     [("Renovate", "Dependabot", "REPLACES")],
     "which updater replaced the GitHub default and what gap closed it",
     "grouping schedule window expression weekday restrict"),
    # --- 43 ---
    ("sigstore cosign signs every release image; verification webhooks block unsigned pulls in the prod admission controller.", "architecture", "technical", False,
     [("sigstore", "service"), ("cosign", "tool")],
     [],
     "how do prod clusters ensure only signed images can land",
     "release signature admission verify webhook block"),
    # --- 44 ---
    ("Tekton PipelineRun resources execute the promotion stages; Argo Events trigger them off git tag webhooks.", "architecture", "technical", False,
     [("Tekton", "framework"), ("PipelineRun", "api"), ("Argo Events", "service")],
     [],
     "what drives release promotion runs off of tag events",
     "tag event pipeline trigger promotion chain resource"),
    # --- 45 ---
    ("FluxCD GitOps loops reconcile the platform cluster every two minutes; Argo CD still handles application deploys.", "architecture", "technical", False,
     [("FluxCD", "service"), ("Argo CD", "service")],
     [],
     "how are platform versus application deploys divided across our two GitOps tools",
     "reconcile loop platform app split interval responsibility"),
    # --- 46 ---
    ("Karpenter autoscaling cut our EC2 spend by 22 percent versus Cluster Autoscaler; bin-packing picks odd instance types nicely.", "decision", "technical", False,
     [("Karpenter", "tool"), ("Cluster Autoscaler", "tool"), ("EC2", "service")],
     [("Karpenter", "Cluster Autoscaler", "IMPROVES_ON")],
     "which node provisioner cut the cloud bill versus the prior scaler",
     "node scaler savings bin packing mixed families choice"),
    # --- 47 ---
    ("Descheduler evicts pods that violate topology spread long after scheduling; pairs with Karpenter for fleet hygiene.", "architecture", "technical", False,
     [("Descheduler", "tool"), ("Karpenter", "tool")],
     [],
     "how do we keep pod placement healthy after initial scheduling decisions drift",
     "post-schedule rebalance spread violation eviction pair"),
    # --- 48 ---
    ("Node problem detector feeds DaemonSet events into Alertmanager; a recurring NVMe wear flag pulled a box early.", "milestone", "technical", False,
     [("Node problem detector", "tool"), ("DaemonSet", "api"), ("Alertmanager", "service"), ("NVMe", "technology")],
     [],
     "what early-warning system pulled a failing disk host out of rotation",
     "daemon event alerting storage wear preemptive pull"),
    # --- 49 ---
    ("Velero backup and restore covered the DR drill last month; restores to a fresh account finished under the 4-hour RTO target.", "milestone", "technical", False,
     [("Velero", "tool")],
     [],
     "which tool carried the disaster recovery drill under the target window",
     "backup restore drill recovery time objective target"),
    # --- 50 ---
    ("Citus shard rebalance ran online while TimescaleDB hypertables kept ingesting; the combo beat a planned maintenance window.", "architecture", "technical", False,
     [("Citus", "framework"), ("TimescaleDB", "database")],
     [],
     "how did the sharded timeseries store rebalance without downtime",
     "distributed extension online redistribute timeseries ingest"),
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
