"""One-off emitter for classification top-up batch-014 — multi_type mode, technical slice.

Writes 100 rows to data/v2/classification/batch_014.tmp.jsonl with ids class-01301..01400.

Distribution (exact):
  fact         : 15
  decision     : 15
  preference   : 15
  problem      : 15
  architecture : 15
  milestone    : 15
  reference    : 10 (each with a citable source)

No pair_id. Schema: {id, domain, text, memory_type}.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_014.tmp.jsonl"
ID_OFFSET = 1300

# Each row: (text, domain, memory_type). Text length 15–45 words.
ROWS: list[tuple[str, str, str]] = [
    # ---------------- fact (15) ----------------
    (
        "PostgreSQL's MVCC implementation stores each row version with xmin and xmax transaction identifiers, allowing readers and writers to operate on the same row without blocking each other.",
        "technical",
        "fact",
    ),
    (
        "The Linux kernel's completely fair scheduler tracks virtual runtime per task in a red-black tree, selecting the leftmost node on each context switch to approximate ideal multitasking.",
        "technical",
        "fact",
    ),
    (
        "Redis stores all keys in a single in-memory hash table per database, with optional persistence via either periodic RDB snapshots or an append-only file log of write commands.",
        "technical",
        "fact",
    ),
    (
        "Kubernetes uses etcd as its sole persistent state store, serializing every API object as a key under /registry with optimistic concurrency control through resource versions.",
        "technical",
        "fact",
    ),
    (
        "The Raft consensus algorithm elects a single leader per term, and all client writes flow through that leader, which replicates log entries to followers before committing.",
        "technical",
        "fact",
    ),
    (
        "HTTP/2 multiplexes concurrent streams over a single TCP connection using binary framing, eliminating the head-of-line blocking problem that plagued HTTP/1.1 pipelining implementations.",
        "technical",
        "fact",
    ),
    (
        "TLS 1.3 reduces the full handshake to a single round trip and removes support for legacy cipher suites including RC4, 3DES, and static RSA key exchange.",
        "technical",
        "fact",
    ),
    (
        "The CPython global interpreter lock serializes bytecode execution to one thread per process, which limits CPU-bound multithreaded workloads but simplifies the implementation of reference counting.",
        "technical",
        "fact",
    ),
    (
        "Docker images are stored as a stack of read-only layers identified by content-addressable digests, with a single thin writable layer created on top when a container starts.",
        "technical",
        "fact",
    ),
    (
        "Git stores every tracked file as a zlib-compressed blob addressed by its SHA-1 hash, and commits reference a tree object that recursively names all blobs under the project root.",
        "technical",
        "fact",
    ),
    (
        "Elasticsearch builds an inverted index per shard using Lucene segments, and queries that span multiple shards are scatter-gathered by a coordinating node and merged before returning.",
        "technical",
        "fact",
    ),
    (
        "The Go garbage collector is a concurrent tri-color mark-sweep collector with short stop-the-world pauses typically under a millisecond even on multi-gigabyte heaps.",
        "ai_coding",
        "fact",
    ),
    (
        "PyTorch tensors carry autograd metadata through every operation on the computational graph, and calling backward on a scalar output produces gradients for every leaf tensor with requires_grad enabled.",
        "ai_coding",
        "fact",
    ),
    (
        "A transformer self-attention layer computes query, key, and value projections from its input and scales the dot product of queries and keys by the inverse square root of the head dimension.",
        "ai_coding",
        "fact",
    ),
    (
        "Kafka partitions a topic into an ordered sequence of immutable log segments per partition, and consumer offsets are committed back to an internal __consumer_offsets topic for replay.",
        "technical",
        "fact",
    ),

    # ---------------- decision (15) ----------------
    (
        "We chose PostgreSQL with pgvector over a dedicated vector database because we already operate Postgres in production and the extra operational surface of another store was not worth the marginal recall gain.",
        "technical",
        "decision",
    ),
    (
        "The team decided to standardize on gRPC with protobuf for internal service traffic because schema evolution and strongly typed clients outweighed the debugging friction compared to JSON over HTTP.",
        "technical",
        "decision",
    ),
    (
        "We adopted a trunk-based branching model with short-lived feature branches because long-running release branches were accumulating merge debt and delaying security patches by several weeks.",
        "technical",
        "decision",
    ),
    (
        "After benchmarking, we selected ScyllaDB instead of Cassandra for the event store because its shard-per-core architecture delivered roughly three times the throughput on our workload with identical hardware.",
        "technical",
        "decision",
    ),
    (
        "We are migrating from AWS Lambda to Fargate for the ingestion pipeline because cold starts on large Python containers were adding tail latency that our downstream SLA could not absorb.",
        "technical",
        "decision",
    ),
    (
        "The architecture review settled on server-sent events rather than WebSockets for the notification channel because our traffic is unidirectional and SSE flows cleanly through existing HTTP load balancers.",
        "technical",
        "decision",
    ),
    (
        "We decided to implement feature flags through LaunchDarkly instead of building in-house because the cost of self-hosted targeting rules, audit logs, and SDK maintenance exceeded two engineer-years of effort.",
        "technical",
        "decision",
    ),
    (
        "For the new billing service we chose Temporal over Airflow because the workflows require long-running stateful retries with human-in-the-loop approval, which fit Temporal's programming model more naturally.",
        "technical",
        "decision",
    ),
    (
        "The platform team ruled out service mesh sidecars in favor of a gateway-per-namespace pattern because the per-pod memory overhead of Envoy sidecars was unacceptable at our pod density.",
        "technical",
        "decision",
    ),
    (
        "We will keep using SQLAlchemy ORM rather than migrate to raw SQL because the test suite relies heavily on session-level transaction rollback for isolation, and rewriting that machinery would stall the roadmap.",
        "ai_coding",
        "decision",
    ),
    (
        "After two spikes, we chose to fine-tune a small encoder model locally rather than call a hosted API because throughput requirements combined with per-token cost projected to over twenty thousand dollars monthly.",
        "ai_coding",
        "decision",
    ),
    (
        "The data team decided to land raw events in S3 Parquet and run ELT in dbt on Snowflake rather than maintain a Spark cluster, trading some flexibility for an order-of-magnitude lower ops burden.",
        "technical",
        "decision",
    ),
    (
        "We picked Ruff over Flake8 plus Black as our combined linter and formatter because Ruff runs roughly a hundred times faster on our monorepo and covers the superset of rules we already enforce.",
        "ai_coding",
        "decision",
    ),
    (
        "The security working group decided to enforce mTLS between internal services through SPIFFE identities instead of shared static certificates, because rotation of static certs had already caused two production incidents.",
        "technical",
        "decision",
    ),
    (
        "We chose to use FastAPI for the new public API rather than extend the existing Flask service because dependency injection and automatic OpenAPI generation meaningfully reduce the boilerplate our team rewrites per endpoint.",
        "ai_coding",
        "decision",
    ),

    # ---------------- preference (15) ----------------
    (
        "I prefer writing database migrations with Alembic autogenerate as a starting point, then manually editing the output to add data backfills and verify that no unintended index changes snuck in.",
        "technical",
        "preference",
    ),
    (
        "My default is to use pytest fixtures with explicit scope rather than setUp and tearDown methods, because fixture composition keeps integration tests readable even when they touch several subsystems at once.",
        "ai_coding",
        "preference",
    ),
    (
        "I like running ripgrep over find plus grep for large repositories because the default respect for gitignore and the multi-threaded search deliver results an order of magnitude faster on any codebase I use.",
        "technical",
        "preference",
    ),
    (
        "When writing shell scripts I always set errexit, nounset, and pipefail at the top because silent failures in production cron jobs have bitten me too many times to count.",
        "technical",
        "preference",
    ),
    (
        "For container debugging I prefer running an ephemeral distroless image with a shell sidecar rather than baking busybox into production images, because it keeps the attack surface minimal.",
        "technical",
        "preference",
    ),
    (
        "I write commit messages in the imperative mood following the Conventional Commits specification because it makes the changelog generation deterministic and pairs well with automated semantic versioning.",
        "technical",
        "preference",
    ),
    (
        "My preferred editor configuration is Neovim with a minimal Lua config using lazy.nvim for plugin management, because I dislike opaque startup times and want every loaded plugin to justify its cost.",
        "technical",
        "preference",
    ),
    (
        "I prefer explicit type hints on all public function signatures in Python, even when mypy could infer them, because hints serve as primary documentation and catch refactoring mistakes early in CI.",
        "ai_coding",
        "preference",
    ),
    (
        "For dependency management in Python I use uv with a locked pyproject.toml because it resolves and installs orders of magnitude faster than pip plus pip-tools and produces deterministic cross-platform lockfiles.",
        "ai_coding",
        "preference",
    ),
    (
        "I prefer structured logging with JSON lines over human-readable log formats in all production services because downstream aggregation in Loki or Elasticsearch is strictly cheaper when the format is machine parseable.",
        "technical",
        "preference",
    ),
    (
        "When writing tests I prefer table-driven style with clearly named cases rather than one assertion per test function, because it captures coverage intent compactly without sacrificing readable failure messages.",
        "ai_coding",
        "preference",
    ),
    (
        "I like pinning container base images to a specific digest rather than a floating tag because tag mutation has caused me reproducibility problems that took hours to diagnose across environments.",
        "technical",
        "preference",
    ),
    (
        "I prefer using just or make for task running over shell scripts scattered across a repository because a single discoverable entry point lowers onboarding friction for new contributors.",
        "technical",
        "preference",
    ),
    (
        "For API documentation I favor generating the OpenAPI spec from code annotations rather than hand-writing YAML, because drift between the implementation and the contract is the most common source of integration bugs.",
        "technical",
        "preference",
    ),
    (
        "I prefer reviewing pull requests on the command line with gh pr diff and a local checkout rather than in the browser UI, because I can run tests and explore adjacent code without context switching.",
        "ai_coding",
        "preference",
    ),

    # ---------------- problem (15) ----------------
    (
        "The checkout service is dropping requests under load because the connection pool to the payment processor is configured with a hard cap of twenty, and burst traffic regularly exceeds that limit.",
        "technical",
        "problem",
    ),
    (
        "Our nightly ETL job has started timing out after a schema migration, and the new bigint primary key caused the join planner to fall back to a hash join that spills to disk.",
        "technical",
        "problem",
    ),
    (
        "The Kubernetes cluster is OOM-killing the ingestion pods every few hours because memory limits were copied from the old VM sizing and never adjusted for the heavier workload after the feature launch.",
        "technical",
        "problem",
    ),
    (
        "We are seeing intermittent 502 responses from the API gateway that correlate with upstream keepalive timeouts, suggesting the gateway is reusing connections that the backend has already closed.",
        "technical",
        "problem",
    ),
    (
        "The fine-tuning run keeps diverging around the second epoch because the learning rate warmup is too short, and gradient norms briefly spike above the clip threshold before stabilizing.",
        "ai_coding",
        "problem",
    ),
    (
        "Our Postgres replica lag has been growing unboundedly during business hours because a long-running analytical query on the primary is holding locks that block WAL application on the follower.",
        "technical",
        "problem",
    ),
    (
        "The CI pipeline on the main branch is flaky because the integration tests depend on system clock ordering, and GitHub-hosted runners occasionally step time backwards during VM migration.",
        "technical",
        "problem",
    ),
    (
        "The search index is returning stale results for roughly ten minutes after a product update because the change-data-capture pipeline has a batch flush interval that compounds with Elasticsearch refresh latency.",
        "technical",
        "problem",
    ),
    (
        "Training throughput on the GPU cluster has collapsed to half its expected value because NCCL is falling back to TCP transport instead of using the RDMA fabric that the nodes were provisioned with.",
        "ai_coding",
        "problem",
    ),
    (
        "The mobile app is crashing at startup for a subset of Android users because a native dependency silently requires armv8 instructions that older devices on the long tail do not support.",
        "ai_coding",
        "problem",
    ),
    (
        "We are leaking file descriptors in the log shipper because the rotation handler is not closing the previous file when the underlying inode changes, leading to an eventual crash after several days.",
        "technical",
        "problem",
    ),
    (
        "The rate limiter is blocking legitimate traffic because its sliding window is keyed by a forwarded IP that is often set to the reverse proxy's own address when the trusted-proxy list is misconfigured.",
        "technical",
        "problem",
    ),
    (
        "Our vector search recall has quietly dropped on a specific tenant because their embeddings were re-indexed with a different model version, and the ANN index still points at the older centroids.",
        "ai_coding",
        "problem",
    ),
    (
        "The deployment pipeline is silently deploying stale container images because the image tag in the Helm values file is not updated atomically with the digest pinned in the admission controller policy.",
        "technical",
        "problem",
    ),
    (
        "We are seeing a steady increase in 5xx responses from the authentication service that correlates with JWT verification time, which points at an expanded JWKS cache miss rate after a recent key rotation.",
        "technical",
        "problem",
    ),

    # ---------------- architecture (15) ----------------
    (
        "The platform is organized as a set of independently deployable services communicating over gRPC, fronted by an Envoy edge proxy that terminates TLS and performs authentication through a sidecar policy agent.",
        "technical",
        "architecture",
    ),
    (
        "Our data plane follows a medallion lakehouse pattern, landing raw CDC events in a bronze layer, curating them into silver tables with dbt, and materializing gold aggregates consumed by BI tools.",
        "technical",
        "architecture",
    ),
    (
        "The ingestion pipeline uses a claim-check pattern: producers write large payloads to object storage, publish only the reference on Kafka, and consumers dereference the claim when they are ready to process it.",
        "technical",
        "architecture",
    ),
    (
        "The authentication subsystem is split into an identity provider, a token service issuing signed JWTs, and a policy decision point evaluating Rego rules against request context at ingress.",
        "technical",
        "architecture",
    ),
    (
        "Our billing system applies event sourcing: every state change is an immutable event written to a durable log, and current balances are projected into read models rebuilt whenever the projection logic evolves.",
        "technical",
        "architecture",
    ),
    (
        "The frontend is a single-page application shipped as static assets behind a CDN, hydrating against a GraphQL gateway that fans out to several internal REST services and caches responses in Redis.",
        "technical",
        "architecture",
    ),
    (
        "The machine learning serving stack runs Triton as the model server behind a KServe control plane, with model artifacts stored in MinIO and a Kafka feedback loop feeding online metrics back to training.",
        "ai_coding",
        "architecture",
    ),
    (
        "Our search architecture places a primary Elasticsearch cluster for user-facing queries, a secondary cluster for analytics, and a replication bridge that keeps them in sync through a cross-cluster replication link.",
        "technical",
        "architecture",
    ),
    (
        "The observability stack consists of OpenTelemetry collectors on every node, forwarding metrics to Prometheus, traces to Tempo, and logs to Loki, with Grafana as the single-pane-of-glass visualization layer.",
        "technical",
        "architecture",
    ),
    (
        "The notification system uses a publish-subscribe core on NATS JetStream with separate consumer groups per channel, allowing email, push, and SMS workers to scale independently based on their downstream latency budgets.",
        "technical",
        "architecture",
    ),
    (
        "Our multi-tenant SaaS uses a shared database with a tenant_id column on every table, enforced through Postgres row-level security policies and a connection-level SET that establishes the current tenant per request.",
        "technical",
        "architecture",
    ),
    (
        "The storage tier is structured as a log-structured merge tree with memtables in RAM, immutable sorted string tables on disk, and a background compactor that merges levels to bound read amplification.",
        "technical",
        "architecture",
    ),
    (
        "The CI/CD architecture uses GitHub Actions for build and test, Argo CD for pull-based deployment, and a promotion pipeline that moves signed container digests through staging, canary, and production clusters.",
        "technical",
        "architecture",
    ),
    (
        "Our retrieval-augmented generation pipeline chunks documents with a semantic splitter, indexes them into a hybrid store combining BM25 and dense embeddings, and reranks top candidates with a cross-encoder before generation.",
        "ai_coding",
        "architecture",
    ),
    (
        "The payment service follows a hexagonal architecture: the domain core is framework-free, adapters on the edge translate to Stripe and internal ledger APIs, and tests exercise the core through in-memory adapter fakes.",
        "technical",
        "architecture",
    ),

    # ---------------- milestone (15) ----------------
    (
        "We completed the migration of the primary database from MySQL 5.7 to PostgreSQL 16 last Thursday, cutting over during a two-hour maintenance window with less than thirty seconds of write unavailability.",
        "technical",
        "milestone",
    ),
    (
        "The platform team shipped the first production rollout of the new service mesh this sprint, bringing fifteen services under mutual TLS with zero customer-visible downtime during the switchover.",
        "technical",
        "milestone",
    ),
    (
        "We closed out the quarter by reducing median API tail latency from three hundred milliseconds to ninety milliseconds after the query plan caching and connection-pool tuning work landed in production last week.",
        "technical",
        "milestone",
    ),
    (
        "The fine-tuning team delivered the first internal release of the in-house embedding model, hitting 93 percent recall at ten on our retrieval benchmark, a four-point improvement over the hosted baseline.",
        "ai_coding",
        "milestone",
    ),
    (
        "We finished migrating every workload off the legacy monolith last Friday, decommissioned the final EC2 auto-scaling group, and retired roughly forty thousand lines of code that had not changed in two years.",
        "technical",
        "milestone",
    ),
    (
        "The observability rollout reached full coverage this week, with every service emitting OpenTelemetry traces and the engineering organization now capable of tracing any request end to end through a single Grafana URL.",
        "technical",
        "milestone",
    ),
    (
        "We hit general availability for the multi-region active-active deployment yesterday, with synthetic probes confirming sub-fifty-millisecond failover across us-east-1, eu-west-1, and ap-southeast-2 during the scheduled game-day exercise.",
        "technical",
        "milestone",
    ),
    (
        "The mobile team shipped version 5.0 to production this morning, completing the twelve-month rewrite onto Kotlin Multiplatform and eliminating the last Objective-C code from the iOS target along the way.",
        "ai_coding",
        "milestone",
    ),
    (
        "We closed the last blocker for SOC 2 Type II this afternoon, completing the audit evidence collection for the final control family and putting the formal report on track for issuance next month.",
        "technical",
        "milestone",
    ),
    (
        "The data platform reached feature parity with the old warehouse last week, and every downstream dashboard has been validated byte-for-byte, allowing us to schedule the decommission for the end of the quarter.",
        "technical",
        "milestone",
    ),
    (
        "We completed the zero-downtime rollout of the new authentication stack this sprint, migrating all forty million active sessions to the new token format over a seven-day gradual cutover with no support escalations.",
        "technical",
        "milestone",
    ),
    (
        "The deep learning team finished the pretraining run for the 7B parameter model yesterday, logging a final validation loss of 1.82 after processing two trillion tokens across the production GPU fleet.",
        "ai_coding",
        "milestone",
    ),
    (
        "We shipped the new code review automation to the entire engineering org last Monday, and it is already catching roughly thirty percent of the nit-level comments that previously consumed human reviewer time.",
        "ai_coding",
        "milestone",
    ),
    (
        "The infrastructure team completed the rollout of IPv6 dual-stack across every production subnet this quarter, closing the last remaining item on the multi-year networking modernization roadmap owned by the platform group.",
        "technical",
        "milestone",
    ),
    (
        "We landed the last piece of the encryption-at-rest migration yesterday, rotating all customer-managed keys through the new KMS hierarchy and closing out the compliance finding that had been open for roughly eighteen months.",
        "technical",
        "milestone",
    ),

    # ---------------- reference (10) — each has a real citable source ----------------
    (
        "According to RFC 9110 section 9.3.1, the HTTP GET method is defined as safe and idempotent, meaning a correctly implemented GET request does not cause observable state change on the origin server.",
        "technical",
        "reference",
    ),
    (
        "Per RFC 7519, a JSON Web Token consists of three base64url-encoded segments — header, payload, and signature — joined by dot separators, as specified in the JWT proposed standard published by the IETF.",
        "technical",
        "reference",
    ),
    (
        "The PostgreSQL 16 documentation chapter on Write-Ahead Logging states that WAL records must be flushed to durable storage before the corresponding dirty data pages, which is the mechanism enabling crash recovery.",
        "technical",
        "reference",
    ),
    (
        "Vaswani et al., Attention Is All You Need, published at NeurIPS 2017 as arXiv:1706.03762, introduced the Transformer architecture based on scaled dot-product self-attention without recurrence or convolution.",
        "ai_coding",
        "reference",
    ),
    (
        "The Kubernetes API reference for version 1.29 specifies that a Pod's restartPolicy field applies to every container in the Pod and defaults to Always when the field is omitted from the manifest.",
        "technical",
        "reference",
    ),
    (
        "According to the CUDA C++ Programming Guide published by NVIDIA, threads within the same warp execute instructions in lockstep, and divergent control flow across those threads is serialized by the hardware scheduler.",
        "technical",
        "reference",
    ),
    (
        "As established in RFC 8446, TLS version 1.3 completes a full handshake in a single round trip and removes support for legacy cipher suites including RC4, 3DES, and static RSA key transport.",
        "technical",
        "reference",
    ),
    (
        "The Semantic Versioning 2.0.0 specification maintained at semver.org defines that the MAJOR version must be incremented for incompatible API changes while MINOR is reserved for backward-compatible additions of functionality.",
        "technical",
        "reference",
    ),
    (
        "According to Designing Data-Intensive Applications by Martin Kleppmann, linearizability is the strongest real-time consistency guarantee and is fundamentally more expensive to provide than sequential or causal consistency in distributed systems.",
        "technical",
        "reference",
    ),
    (
        "The Raft consensus paper by Ongaro and Ousterhout, published at USENIX ATC 2014 under the title In Search of an Understandable Consensus Algorithm, defines leader election, log replication, and safety in clear terms.",
        "technical",
        "reference",
    ),
]


def emit() -> int:
    assert len(ROWS) == 100, f"expected 100 rows, got {len(ROWS)}"
    counts: dict[str, int] = {}
    for _, _, mt in ROWS:
        counts[mt] = counts.get(mt, 0) + 1
    expected = {
        "fact": 15,
        "decision": 15,
        "preference": 15,
        "problem": 15,
        "architecture": 15,
        "milestone": 15,
        "reference": 10,
    }
    assert counts == expected, f"distribution mismatch: {counts} != {expected}"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (text, domain, mt) in enumerate(ROWS, start=1):
            row_id = f"class-{ID_OFFSET + i:05d}"
            f.write(
                json.dumps(
                    {"id": row_id, "domain": domain, "text": text, "memory_type": mt},
                    ensure_ascii=False,
                )
                + "\n"
            )
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
