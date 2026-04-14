"""One-off emitter for shared-base batch-006 — technical domain (round 2).

Same pattern as _emit_shared_batch_005.py; only ENTRIES changes.
Appends 50 rows to data/v2/shared/shared.jsonl with ids shared-00251..00300.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
ID_OFFSET = 250  # batches 001..005 consumed shared-00001..00250

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Picked Temporal for the new billing retry engine; deterministic replay simplified the retry story.", "decision", "technical", False,
     [("Temporal", "service"), ("billing retry engine", "project")],
     [],
     "what workflow engine did we pick for the new retry system",
     "deterministic replay orchestrator billing adoption"),
    # --- 2 ---
    ("Cassandra tombstone read path spiked when a nightly TTL job deleted 200k rows at once; switched to per-partition expiry.", "problem", "technical", False,
     [("Cassandra", "database")],
     [],
     "what caused read latency spikes in the wide-column store",
     "NoSQL tombstone read cost nightly expiry fix"),
    # --- 3 ---
    ("OpenTelemetry traces reached parity with the legacy Zipkin pipeline on 2026-03-05; turned Zipkin off the next day.", "milestone", "technical", False,
     [("OpenTelemetry", "framework"), ("Zipkin", "service"), ("2026-03-05", "date")],
     [("OpenTelemetry", "Zipkin", "REPLACES")],
     "when did the modern tracing stack replace the older one",
     "tracer parity cutover legacy pipeline shutdown"),
    # --- 4 ---
    ("gRPC streaming uses HTTP/2 multiplexing, which means head-of-line blocking still happens at the TCP layer.", "fact", "technical", False,
     [("gRPC", "protocol"), ("HTTP/2", "protocol"), ("TCP", "protocol")],
     [],
     "how does high-level multiplexing interact with the transport layer",
     "RPC stream kernel socket head-of-line blocking"),
    # --- 5 ---
    ("Chose Bun over Node.js for the new gateway; startup time dropped from 800 ms to 40 ms on the edge runtime.", "decision", "technical", False,
     [("Bun", "platform"), ("Node.js", "platform")],
     [("Bun", "Node.js", "REPLACES")],
     "which runtime replaced the JavaScript one and what was the boot-time gain",
     "edge runtime swap cold start speedup"),
    # --- 6 ---
    ("Cloudflare Workers run auth edge validation; origin servers only see pre-authenticated traffic from Workers.", "architecture", "technical", False,
     [("Cloudflare Workers", "platform")],
     [],
     "where does authentication actually run before traffic reaches our origins",
     "edge compute auth terminus origin protection"),
    # --- 7 ---
    ("Dynamo conditional writes failed silently when the ConditionExpression referenced a reserved word without the ExpressionAttributeNames map.", "problem", "technical", False,
     [("Dynamo", "database"), ("ConditionExpression", "api"), ("ExpressionAttributeNames", "api")],
     [],
     "what gotcha did conditional writes have with reserved attribute names",
     "NoSQL attribute names map required escape reserved"),
    # --- 8 ---
    ("Adopted Iceberg over Delta Lake for the data lake; vendor neutrality mattered more than Spark integration convenience.", "decision", "technical", False,
     [("Iceberg", "framework"), ("Delta Lake", "framework"), ("Spark", "framework")],
     [("Iceberg", "Delta Lake", "REPLACES")],
     "which open table format did we pick for the warehouse and why",
     "vendor neutral table standard rationale compute"),
    # --- 9 ---
    ("The Raft consensus paper by Diego Ongaro and John Ousterhout underpins the etcd cluster design.", "reference", "technical", False,
     [("Raft", "algorithm"), ("Diego Ongaro", "person"), ("John Ousterhout", "person"), ("etcd", "database")],
     [("Raft", "Diego Ongaro", "AUTHORED_BY"), ("Raft", "John Ousterhout", "AUTHORED_BY")],
     "whose paper underpins the key-value cluster's consensus layer",
     "distributed agreement paper authors etcd backing"),
    # --- 10. noise ---
    ("Alright, I need to run the build again to confirm.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("The Rust migrator leaked file handles on Windows because tokio kept spawned blocking tasks alive past drop.", "problem", "technical", False,
     [("Rust", "language"), ("tokio", "library"), ("Windows", "platform")],
     [],
     "why did the migrator leak handles on the Windows builds",
     "async runtime blocking task drop handles OS bug"),
    # --- 12 ---
    ("Feature store separates online Redis and offline BigQuery materialisations behind a single Python DSL.", "architecture", "technical", False,
     [("Redis", "database"), ("BigQuery", "database"), ("Python", "language")],
     [],
     "how is the feature store split between online and batch lookups",
     "online offline feature materialisation DSL unified"),
    # --- 13 ---
    ("A JWT's alg=none vulnerability remains a reason to enforce allow-listed algorithms on every verification path.", "fact", "technical", False,
     [("JWT", "protocol"), ("alg=none", "config")],
     [],
     "what long-standing token algorithm pitfall still needs guarding",
     "signing flag bypass verification allowlist hardening"),
    # --- 14 ---
    ("Switched from pip to uv for dependency management; lockfile resolution went from 90 s to under 2 s.", "decision", "technical", False,
     [("pip", "tool"), ("uv", "tool")],
     [("uv", "pip", "REPLACES")],
     "which dependency manager came in and how much faster is it",
     "lockfile resolver swap install speedup large"),
    # --- 15 ---
    ("Zero-downtime Postgres major version upgrade completed on 2026-01-27 using logical replication.", "milestone", "technical", False,
     [("Postgres", "database"), ("2026-01-27", "date")],
     [],
     "when did the seamless database engine bump finish",
     "major version cutover logical replication date"),
    # --- 16 ---
    ("The Kafka consumer hit rebalance storms because session.timeout.ms was shorter than the worst-case message processing time.", "problem", "technical", False,
     [("Kafka", "service"), ("session.timeout.ms", "config")],
     [],
     "what queue setting caused the constant consumer group churn",
     "streaming broker timeout processing length misfit"),
    # --- 17 ---
    ("Job scheduling uses Hashicorp Nomad; services run on the same cluster as the ML training jobs with GPU bin-packing.", "architecture", "technical", False,
     [("Nomad", "service"), ("Hashicorp", "organization")],
     [],
     "what scheduler shares the cluster with our ML training jobs",
     "workload orchestrator GPU bin-packing same fleet"),
    # --- 18 ---
    ("Replaced the home-grown cron scheduler with Dagster; data lineage and backfills need first-class tooling.", "decision", "technical", False,
     [("cron", "tool"), ("Dagster", "framework")],
     [("Dagster", "cron", "REPLACES")],
     "which platform took over from the handcrafted scheduler",
     "data pipeline tool swap lineage backfill reason"),
    # --- 19 ---
    ("Prefers Rust over Go for critical-path services; lifetimes catch resource bugs that escape Go's runtime.", "preference", "technical", False,
     [("Rust", "language"), ("Go", "language")],
     [("Rust", "Go", "PREFERS")],
     "which systems language wins for hot paths and why",
     "memory-safe lifetime bug catch versus alternative"),
    # --- 20 ---
    ("The AES-GCM authenticated encryption mode is preferred over AES-CBC with HMAC for new TLS deployments.", "preference", "technical", False,
     [("AES-GCM", "algorithm"), ("AES-CBC", "algorithm"), ("HMAC", "algorithm"), ("TLS", "protocol")],
     [("AES-GCM", "AES-CBC", "PREFERS")],
     "which symmetric cipher mode wins for new secure transport stacks",
     "authenticated encryption choice over separate MAC"),
    # --- 21 ---
    ("Cold paths proxy through CloudFront, warm paths hit an internal ALB fronted by Route 53 weighted records.", "architecture", "technical", False,
     [("CloudFront", "service"), ("ALB", "service"), ("Route 53", "service")],
     [],
     "how do cold and warm request paths split across the AWS edges",
     "CDN versus load balancer routing weighted DNS"),
    # --- 22 ---
    ("Pytest collection exploded past 3 GB of RAM because conftest autouse fixtures held onto database connections.", "problem", "technical", False,
     [("Pytest", "library"), ("conftest", "file")],
     [],
     "why did the test collector balloon in memory",
     "autouse fixture database handle retention leak"),
    # --- 23 ---
    ("OAuth 2.0 PKCE details are in RFC 7636; mobile clients rely on the verifier-challenge flow.", "reference", "technical", False,
     [("OAuth 2.0", "protocol"), ("RFC 7636", "publication"), ("PKCE", "protocol")],
     [],
     "which document defines the mobile-friendly code exchange",
     "specification native app exchange hardening"),
    # --- 24 ---
    ("Production hit five-nines availability for the first quarter in a row on 2026-04-01.", "milestone", "technical", False,
     [("2026-04-01", "date")],
     [],
     "when did uptime stay at top-tier for a whole quarter",
     "reliability number streak quarterly metric"),
    # --- 25 ---
    ("CPython's GIL is released during C extension calls, which is why numpy loops often parallelise under it.", "fact", "technical", False,
     [("CPython", "language"), ("GIL", "concept"), ("numpy", "library")],
     [],
     "why can scientific library loops run in parallel despite the interpreter lock",
     "C extension interpreter lock release parallelism"),
    # --- 26 ---
    ("Adopted Litestream for SQLite replication to S3 on the edge nodes; a full Postgres there was overkill.", "decision", "technical", False,
     [("Litestream", "service"), ("SQLite", "database"), ("S3", "service"), ("Postgres", "database")],
     [],
     "how do edge nodes replicate their local database to the cloud",
     "edge datastore object store streaming replication"),
    # --- 27 ---
    ("Gateway then rate limiter Envoy then auth service then business handler is the canonical request path.", "architecture", "technical", False,
     [("Envoy", "service")],
     [],
     "what sits between inbound requests and the business handlers",
     "ingress limiter auth chain canonical flow"),
    # --- 28 ---
    ("Homebrew autoupdates broke the local dev environment when openssl@3 shadowed the system version; pinned via Brewfile.", "problem", "technical", False,
     [("Homebrew", "tool"), ("openssl@3", "library"), ("Brewfile", "file")],
     [],
     "what broke local dev after a package manager update and how was it pinned",
     "macOS library shadow pin recipe file"),
    # --- 29 ---
    ("Linux cgroups v2 unifies resource controllers under a single hierarchy; systemd delegates slices accordingly.", "fact", "technical", False,
     [("Linux", "platform"), ("cgroups v2", "technology"), ("systemd", "service")],
     [],
     "how does modern kernel resource control organise its controllers",
     "kernel group hierarchy single tree unit manager"),
    # --- 30 ---
    ("Chose RabbitMQ quorum queues over classic mirrored queues for the billing retry topic; mirror drift caused data loss twice.", "decision", "technical", False,
     [("RabbitMQ", "service"), ("quorum queues", "pattern"), ("classic mirrored queues", "pattern")],
     [("quorum queues", "classic mirrored queues", "REPLACES")],
     "why did the retry broker move off its old replication mode",
     "consensus queue swap broker data loss incident"),
    # --- 31 ---
    ("For infrastructure-as-code we prefer CDK over raw CloudFormation; Python abstractions encode team conventions.", "preference", "technical", False,
     [("CDK", "framework"), ("CloudFormation", "service"), ("Python", "language")],
     [("CDK", "CloudFormation", "PREFERS")],
     "which IaC layer wins over the raw AWS variant",
     "infrastructure code abstraction language convention"),
    # --- 32 ---
    ("CoreDNS returned SERVFAIL intermittently when the upstream resolver rate-limited us; switched to 1.1.1.1 plus Unbound locally.", "problem", "technical", False,
     [("CoreDNS", "service"), ("Unbound", "service")],
     [],
     "how did we stabilise name resolution after the upstream got rate-limited",
     "DNS failover public resolver local cache fix"),
    # --- 33 ---
    ("The Go codebase hit version 1.22 adoption across all services on 2026-03-10 with the new range-over-func builds.", "milestone", "technical", False,
     [("Go", "language"), ("2026-03-10", "date")],
     [],
     "when did the fleet finish rolling to the new major language release",
     "language version rollout date fleet-wide"),
    # --- 34. noise ---
    ("Okay, re-running this with the debug flag now.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("All internal HTTPS traffic terminates at Istio's ingress gateway; sidecar proxies handle east-west mTLS.", "architecture", "technical", False,
     [("Istio", "service"), ("HTTPS", "protocol"), ("mTLS", "protocol")],
     [],
     "where does internal secure traffic get terminated in this mesh",
     "service mesh ingress sidecar mutual TLS east-west"),
    # --- 36 ---
    ("B-tree indexes in Postgres are good for equality and range queries; BRIN indexes excel for append-only ordered data.", "fact", "technical", False,
     [("B-tree", "concept"), ("Postgres", "database"), ("BRIN", "concept")],
     [],
     "which index type suits append-only ordered columns best",
     "range scan block index use case choice"),
    # --- 37 ---
    ("Moved from Webpack to Vite for all frontend builds; dev server boot dropped from 25 s to under 2 s.", "decision", "technical", False,
     [("Webpack", "tool"), ("Vite", "tool")],
     [("Vite", "Webpack", "REPLACES")],
     "which bundler replaced the older one and how big was the dev server gain",
     "web build tool swap boot time reduction"),
    # --- 38 ---
    ("For CI runners the team prefers self-hosted over GitHub cloud runners; build cache locality saves 40 percent on long pipelines.", "preference", "technical", False,
     [("self-hosted", "infrastructure"), ("GitHub", "organization")],
     [],
     "why do we run our own CI agents instead of the hosted ones",
     "build agent locality cache long pipeline savings"),
    # --- 39 ---
    ("ClickHouse merge storms blocked inserts because the default parts-to-throw threshold was too low for our batch size.", "problem", "technical", False,
     [("ClickHouse", "database")],
     [],
     "what caused insert stalls in the columnar database",
     "merge storm parts threshold batch size mismatch"),
    # --- 40 ---
    ("The Google SRE book's error budget chapter shapes how we weight feature velocity against reliability work.", "reference", "technical", False,
     [("Google SRE book", "publication"), ("error budget", "concept")],
     [],
     "which text shapes how the team trades shipping speed against uptime",
     "SRE literature budget chapter trade-off weighting"),
    # --- 41 ---
    ("Migrated the last Oracle database off-prem to AWS Aurora PostgreSQL-compatible on 2025-12-15.", "milestone", "technical", False,
     [("Oracle", "database"), ("AWS Aurora", "service"), ("2025-12-15", "date")],
     [("AWS Aurora", "Oracle", "REPLACES")],
     "when did the final legacy relational box leave the data centre",
     "managed cloud RDBMS cutover long migration"),
    # --- 42 ---
    ("Request IDs propagate via W3C Trace Context headers; Tempo stores them and Grafana queries by correlation.", "architecture", "technical", False,
     [("W3C Trace Context", "protocol"), ("Tempo", "service"), ("Grafana", "service")],
     [],
     "how do request IDs travel across services and where do they land",
     "trace context propagation storage correlation lookup"),
    # --- 43 ---
    ("Python 3.12 introduced per-interpreter GIL support via PEP 684, paving the way for true parallel interpreters.", "fact", "technical", False,
     [("Python 3.12", "language"), ("PEP 684", "publication")],
     [],
     "what language change points toward fully parallel interpreter execution",
     "per-interpreter lock update concurrency direction"),
    # --- 44 ---
    ("Adopted Snyk for SCA scanning over Dependabot; transitive CVE coverage was deeper and autofix PRs were cleaner.", "decision", "technical", False,
     [("Snyk", "tool"), ("Dependabot", "tool")],
     [("Snyk", "Dependabot", "REPLACES")],
     "which vulnerability scanner replaced the GitHub default",
     "SCA vendor swap deeper CVE autofix quality"),
    # --- 45 ---
    ("gRPC clients deadlocked on TLS renegotiation under load because the Go client did not cap concurrent streams per connection.", "problem", "technical", False,
     [("gRPC", "protocol"), ("Go", "language"), ("TLS", "protocol")],
     [],
     "what caused the RPC clients to hang under heavy load",
     "renegotiation stream cap client bug deadlock"),
    # --- 46 ---
    ("Message dedup relies on idempotency keys at the gateway and a 24-hour SETNX in Redis per key.", "architecture", "technical", False,
     [("Redis", "database"), ("SETNX", "command")],
     [],
     "how does the gateway deduplicate inbound events over a day",
     "idempotency key TTL cache mechanism entry"),
    # --- 47 ---
    ("Prefer ArgoCD's app-of-apps pattern over Helmfile for gitops at the fleet scale; easier promotion paths.", "preference", "technical", False,
     [("ArgoCD", "service"), ("Helmfile", "tool"), ("app-of-apps", "pattern")],
     [("ArgoCD", "Helmfile", "PREFERS")],
     "what layout approach beats the Helm alternative at multi-cluster size",
     "gitops multi-cluster promotion pattern choice"),
    # --- 48 ---
    ("The HTTP/3 spec is RFC 9114; QPACK header compression is documented in RFC 9204.", "reference", "technical", False,
     [("HTTP/3", "protocol"), ("RFC 9114", "publication"), ("QPACK", "protocol"), ("RFC 9204", "publication")],
     [],
     "where are the new transport and its header compression written up",
     "web transport third version companion specs"),
    # --- 49 ---
    ("Horizontal pod autoscaler oscillated when the CPU metric resolution was lower than the cool-down period.", "problem", "technical", False,
     [("Horizontal pod autoscaler", "service"), ("CPU", "concept")],
     [],
     "why did the scaling controller bounce up and down in production",
     "scaler metric resolution cool-down mismatch oscillation"),
    # --- 50 ---
    ("First production deploy of the eBPF-based network policy enforcement landed on 2026-02-20.", "milestone", "technical", False,
     [("eBPF", "technology"), ("2026-02-20", "date")],
     [],
     "when did kernel-level network policies first go live in production",
     "kernel filter policy rollout date milestone"),
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
    with OUT.open("a", encoding="utf-8") as f:
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
