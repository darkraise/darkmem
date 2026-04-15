"""One-off emitter for classification top-up batch-006 — contrastive_decision_architecture mode, software system slice.

Writes 100 rows (50 pairs) to data/v2/classification/batch_006.tmp.jsonl with ids class-00501..00600.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_006.tmp.jsonl"
ID_OFFSET = 500
PAIR_OFFSET = 250

# (decision_text, decision_domain, architecture_text, architecture_domain)
PAIRS: list[tuple[str, str, str, str]] = [
    # 1. databases — multi-region OLTP
    (
        "Switched the customer billing tables from Postgres 15 to CockroachDB v24 after the Frankfurt failover drill exposed a six-minute RPO gap with streaming replication.",
        "technical",
        "Customer billing tables run on a three-region CockroachDB cluster spanning us-east-1, eu-west-1, and ap-southeast-2 with SERIALIZABLE isolation and survival goal region.",
        "technical",
    ),
    # 2. caching — read-through layer
    (
        "Chose Redis Enterprise with Active-Active CRDTs over a self-managed Redis Cluster because the ops team could not justify on-call rotation for gossip failures.",
        "technical",
        "Session and rate-limit state lives in a five-shard Redis Enterprise database with Active-Active replication across two datacenters and 15 GB RAM per shard.",
        "technical",
    ),
    # 3. queues — event backbone
    (
        "Adopted Kafka 3.7 with KRaft mode in place of RabbitMQ after the order-events topic backlog kept crashing the broker during Black Friday load tests.",
        "technical",
        "The event backbone is a nine-broker Kafka 3.7 cluster in KRaft mode with a replication factor of three and tiered storage to S3 after seven days.",
        "technical",
    ),
    # 4. api gateways
    (
        "Picked Kong Gateway 3.6 over AWS API Gateway because the platform team needed declarative config in Git and sub-millisecond plugin latency at the edge.",
        "technical",
        "Edge traffic terminates at a Kong Gateway 3.6 deployment of six pods behind an NLB, with rate-limit-advanced, OIDC, and request-transformer plugins applied per route.",
        "technical",
    ),
    # 5. auth — identity provider
    (
        "Decided to replace the home-grown JWT issuer with Keycloak 24 after the third CVE in the custom token signer in nine months.",
        "technical",
        "Authentication flows through a Keycloak 24 realm backed by a Postgres HA pair, issuing RS256 JWTs with a 15-minute access token and 30-day refresh token rotation.",
        "technical",
    ),
    # 6. service mesh
    (
        "Adopted Istio ambient mesh over the sidecar model because injecting Envoy into every pod doubled memory usage on the GPU inference nodes.",
        "technical",
        "Cluster traffic runs on Istio 1.22 in ambient mode with ztunnel DaemonSets for L4 mTLS and per-namespace waypoint proxies handling L7 policy.",
        "technical",
    ),
    # 7. deployment — rollout strategy
    (
        "Switched from rolling updates to Argo Rollouts canary deployments after a bad image shipped to 60% of pods before the readiness probe caught it.",
        "technical",
        "Production workloads deploy through Argo Rollouts with a 5/25/50/100 canary ladder gated on Prometheus latency and error SLO analyses between each step.",
        "technical",
    ),
    # 8. observability — tracing
    (
        "Chose OpenTelemetry Collector with the Tempo backend over Jaeger because we needed tail-based sampling and native OTLP receivers without a custom agent.",
        "technical",
        "Tracing is collected by a three-tier OpenTelemetry Collector deployment (agent DaemonSet, load-balancing layer, tail-sampling gateway) feeding Grafana Tempo on S3.",
        "technical",
    ),
    # 9. CI/CD runners
    (
        "Moved CI runners from hosted GitHub Actions to self-hosted Actions Runner Controller on EKS after monthly bills crossed thirty thousand dollars.",
        "technical",
        "CI executes on an Actions Runner Controller deployment with ephemeral runners auto-scaling from 0 to 400 pods on Karpenter-provisioned spot instances.",
        "technical",
    ),
    # 10. ingestion — CDC
    (
        "Adopted Debezium on Kafka Connect over dual-writes after two customer-facing inconsistencies traced back to partial writes during deploys.",
        "technical",
        "Change data capture runs through a Debezium 2.6 Kafka Connect cluster watching Postgres logical replication slots and fanning events into per-table topics.",
        "technical",
    ),
    # 11. search
    (
        "Replaced Elasticsearch 7 with OpenSearch 2.13 after the license change and because kNN vector search on the product catalog needed faster iteration.",
        "technical",
        "Product search runs on a three-master, twelve-data-node OpenSearch 2.13 cluster with a dedicated kNN index using HNSW and 768-dimensional embeddings.",
        "technical",
    ),
    # 12. ML serving
    (
        "Chose NVIDIA Triton Inference Server over a Flask wrapper after p99 latency on the recommender model doubled under concurrent tenants.",
        "technical",
        "The recommender endpoint is served by Triton 24.05 running TensorRT engines on four A10G GPUs with dynamic batching up to 32 requests per 5 ms window.",
        "technical",
    ),
    # 13. object storage
    (
        "Moved cold archives from EFS to S3 Glacier Instant Retrieval after storage costs exceeded the compute bill for the compliance pipeline.",
        "technical",
        "Compliance artifacts older than 30 days live in an S3 bucket with an Intelligent-Tiering policy that demotes objects to Glacier Instant Retrieval at 90 days.",
        "technical",
    ),
    # 14. data formats
    (
        "Standardized on Apache Parquet with Zstandard over CSV for analytics exports because query planners skipped 80% of row groups with column statistics.",
        "technical",
        "Analytics exports land as Parquet files partitioned by event_date and tenant_id, compressed with Zstd level 3 and registered in the Glue Data Catalog.",
        "technical",
    ),
    # 15. realtime — websockets
    (
        "Picked Centrifugo 5 over a custom Socket.IO service after the in-house fanout server dropped messages beyond 20 000 concurrent subscribers.",
        "technical",
        "Realtime notifications flow through a Centrifugo 5 cluster of eight nodes joined by a Redis Streams engine, sustaining 120 000 concurrent WebSocket clients.",
        "technical",
    ),
    # 16. graph store
    (
        "Adopted Neo4j 5 Aura over a homemade adjacency-list table when multi-hop fraud queries started timing out past three joins.",
        "technical",
        "The fraud graph lives in a Neo4j 5 Aura Enterprise instance with a core of three and two read replicas, indexed on actor_id and device_fingerprint.",
        "technical",
    ),
    # 17. workflow orchestration
    (
        "Switched from Airflow 2 to Temporal because long-running human-approval workflows kept expiring executor slots and wedging the scheduler.",
        "technical",
        "Durable workflows run on a Temporal Cloud namespace with Go workers sharded by task queue and a 30-day workflow execution retention window.",
        "technical",
    ),
    # 18. analytics warehouse
    (
        "Chose ClickHouse Cloud over Snowflake for product telemetry after the per-query costs on high-cardinality dashboards became unsustainable.",
        "technical",
        "Product telemetry is stored in a ClickHouse Cloud service with a ReplicatedMergeTree engine partitioned by toYYYYMM(event_time) and a 180-day TTL.",
        "technical",
    ),
    # 19. container runtime
    (
        "Migrated from Docker Engine to containerd on all Kubernetes nodes after dockershim removal in Kubernetes 1.24 and to drop an unnecessary daemon.",
        "technical",
        "All Kubernetes nodes run containerd 1.7 as the CRI runtime with the systemd cgroup driver and nerdctl available for debug shells on the host.",
        "technical",
    ),
    # 20. secrets management
    (
        "Adopted HashiCorp Vault over AWS Secrets Manager when multi-cloud GCP workloads needed the same dynamic database credentials flow.",
        "technical",
        "Secrets live in a Vault Enterprise cluster of five Raft nodes with the database and transit engines enabled and auto-unseal via AWS KMS.",
        "technical",
    ),
    # 21. vector database — AI coding
    (
        "Picked Qdrant over pgvector for the code-assistant embeddings after recall dropped below 0.85 at 40 million vectors on a shared Postgres instance.",
        "ai_coding",
        "Code embeddings are stored in a Qdrant 1.9 cluster of six shards with HNSW indexes (m=32, ef_construct=256) and payload-based tenant filtering.",
        "ai_coding",
    ),
    # 22. LLM gateway
    (
        "Adopted LiteLLM Proxy in front of OpenAI and Anthropic after prompt-injection logging and per-team spend caps could not be enforced at the SDK layer.",
        "ai_coding",
        "All LLM calls from IDE plugins route through a LiteLLM Proxy deployment with Redis for rate-limit state, Postgres for virtual-key budgets, and Langfuse for traces.",
        "ai_coding",
    ),
    # 23. prompt caching
    (
        "Chose Anthropic prompt caching for the repo-context block after measuring a 9x latency improvement on follow-up messages that re-send the same system prompt.",
        "ai_coding",
        "The code-assistant system prompt and repo manifest are sent as two cache_control=ephemeral blocks so the 30 000-token prefix is reused for five minutes across turns.",
        "ai_coding",
    ),
    # 24. retrieval — reranking
    (
        "Added a Cohere Rerank 3 stage after BM25 because top-1 accuracy on StackOverflow-style queries sat at 54% without cross-encoder scoring.",
        "ai_coding",
        "Retrieval runs a hybrid pipeline: BM25 over Tantivy plus dense search over Qdrant, fused by RRF, then the top 40 hits are reranked by Cohere Rerank 3 before prompt assembly.",
        "ai_coding",
    ),
    # 25. code parsing
    (
        "Chose tree-sitter over LSP for symbol extraction because the indexer had to work on partial files checked out from commits without a running language server.",
        "ai_coding",
        "The code indexer parses each file with tree-sitter grammars for Python, TypeScript, Go, and Rust, emitting a unified symbol table with byte-offset ranges into pgvector chunks.",
        "ai_coding",
    ),
    # 26. agent memory
    (
        "Adopted a dual-store memory (mem0 plus memora) because pure semantic recall kept missing structured items like ticket IDs and assignees.",
        "ai_coding",
        "Agent memory is split across mem0 for natural-language facts and memora for tag-indexed structured entries, queried in parallel on every user turn.",
        "ai_coding",
    ),
    # 27. embedding model
    (
        "Switched the code embedder from text-embedding-3-large to bge-code-v1 after internal evals showed a 6-point nDCG gain on cross-repo queries and 10x lower cost.",
        "ai_coding",
        "Code chunks are embedded by a self-hosted bge-code-v1 model on two L4 GPUs behind vLLM, producing 1024-dimensional vectors ingested into Qdrant.",
        "ai_coding",
    ),
    # 28. tool calling schema
    (
        "Chose JSON Schema tool definitions with strict mode over free-form function calls after 4% of agent outputs produced unparsable arguments under load.",
        "ai_coding",
        "Tool calls are defined as Anthropic tools with strict JSON Schema input definitions validated by pydantic on the server before dispatch to the handler registry.",
        "ai_coding",
    ),
    # 29. evaluation harness
    (
        "Adopted Promptfoo for offline regression runs because ad-hoc Jupyter evaluations made diffs between prompt versions impossible to review.",
        "ai_coding",
        "Prompt changes trigger a Promptfoo CI job that runs 400 fixture prompts against the new and old prompt variants and publishes a diff report to the PR.",
        "ai_coding",
    ),
    # 30. secrets scanning
    (
        "Chose Gitleaks in a pre-receive hook over a nightly scan after a leaked API token made it into main and took six hours to notice.",
        "technical",
        "The Git server enforces a Gitleaks pre-receive hook with a custom rule set and quarantine pushed refs until the scan exits cleanly.",
        "technical",
    ),
    # 31. feature flags
    (
        "Adopted OpenFeature with a flagd provider over LaunchDarkly for non-customer-facing flags because the team wanted on-cluster evaluation and no egress.",
        "technical",
        "Feature flags are served by flagd sidecars per pod reading a Git-synced ConfigMap, with SDKs talking localhost:8013 via the OpenFeature SDK.",
        "technical",
    ),
    # 32. error tracking
    (
        "Chose self-hosted Sentry over the SaaS offering after data-residency requirements from the EU customer demanded no telemetry leaving Frankfurt.",
        "technical",
        "Exceptions are captured by a self-hosted Sentry 24 deployment on eu-central-1 with ClickHouse for events and an 11-day retention per project.",
        "technical",
    ),
    # 33. logging pipeline
    (
        "Picked Vector over Fluent Bit for log shipping after the memory footprint under 30k events/s made Fluent Bit OOM on the smaller nodes.",
        "technical",
        "Logs flow from each node via a Vector DaemonSet through a Kafka transform topic and into Loki, with a parallel sink to S3 for long-term archival.",
        "technical",
    ),
    # 34. metrics backend
    (
        "Moved from standalone Prometheus to Mimir after cardinality from per-user labels pushed the single instance past 50 GB of head series.",
        "technical",
        "Metrics are written by Prometheus agents remote-writing to a Grafana Mimir cluster with four ingesters, three store-gateways, and S3 long-term blocks storage.",
        "technical",
    ),
    # 35. SSO
    (
        "Adopted Okta for workforce SSO because the previous Google Workspace-only setup could not integrate with the new SOC 2 session policies.",
        "technical",
        "All internal tools authenticate via Okta SAML with a 12-hour session, device-trust verification, and SCIM provisioning into the employee directory.",
        "technical",
    ),
    # 36. DNS
    (
        "Chose NS1 managed DNS over Route 53 because latency-based steering across multiple cloud providers required per-answer filter chains.",
        "technical",
        "External DNS is hosted on NS1 with filter-chain records performing geo, latency, and up/down health checks across AWS, GCP, and on-prem origins.",
        "technical",
    ),
    # 37. CDN
    (
        "Adopted Fastly in front of S3 because the product team needed edge compute with VCL to handle signed-URL rewrites closer to the user.",
        "technical",
        "Static assets and media segments are served via Fastly with a custom VCL service that validates short-lived HMAC tokens before hitting origin S3 buckets.",
        "technical",
    ),
    # 38. build system
    (
        "Switched the monorepo from Lerna to Turborepo 2 after build times on a twelve-package workspace exceeded twenty minutes on developer laptops.",
        "ai_coding",
        "The TypeScript monorepo is orchestrated by Turborepo 2 with a remote cache hosted on Vercel, task graph derived from package.json, and pnpm workspaces underneath.",
        "ai_coding",
    ),
    # 39. test runner
    (
        "Chose Vitest over Jest for the darkraise-ui package after ESM support and Vite HMR made the prior Jest setup impossible to maintain.",
        "ai_coding",
        "Frontend unit tests run under Vitest 1.6 with happy-dom, parallelized across eight workers and reporting coverage via v8 into a JUnit XML for CI.",
        "ai_coding",
    ),
    # 40. static analysis
    (
        "Adopted Ruff over Flake8 and isort because running three tools on every commit doubled pre-commit latency and caused developers to skip hooks.",
        "ai_coding",
        "Python linting runs a single Ruff 0.5 invocation configured in pyproject.toml with E, F, I, UP, and B rule sets and an auto-fix stage in the pre-commit hook.",
        "ai_coding",
    ),
    # 41. dependency management
    (
        "Switched from pip-tools to uv after lockfile resolution on the backend service dropped from 90 seconds to under three.",
        "ai_coding",
        "Python environments are managed with uv 0.4, using a pyproject.toml plus uv.lock checked into git and an in-CI uv sync --frozen to install deterministic dependencies.",
        "ai_coding",
    ),
    # 42. container registry
    (
        "Chose Harbor over Docker Hub Enterprise for internal images because CVE scanning and project-level RBAC were both required for the FedRAMP audit.",
        "technical",
        "Internal container images live in a Harbor 2.10 registry with Trivy scanning, Notary signing, and replication to a warm standby registry in a second region.",
        "technical",
    ),
    # 43. service discovery
    (
        "Adopted Consul over Kubernetes Services because bare-metal VMs outside the cluster still had to participate in the same service catalog.",
        "technical",
        "Service discovery is centralized in a Consul cluster of five servers with Consul agents on every VM and Kubernetes pod, exposing DNS on the local node at 127.0.0.1:8600.",
        "technical",
    ),
    # 44. IaC
    (
        "Picked Terraform Enterprise over Pulumi because the platform team had ten years of HCL modules that could not realistically be rewritten.",
        "technical",
        "Infrastructure is codified in Terraform 1.8 modules stored in a central repository, executed by Terraform Enterprise workspaces with Sentinel policies and Vault-issued cloud credentials.",
        "technical",
    ),
    # 45. package publishing
    (
        "Adopted Changesets for versioning because manual npm publish commits kept going out of sync across the five public packages in the repo.",
        "ai_coding",
        "The monorepo publishes packages via Changesets with a GitHub Action that opens a Version Packages PR, then runs changeset publish to npm on merge to main.",
        "ai_coding",
    ),
    # 46. migrations
    (
        "Chose Alembic with a single-head policy over bespoke SQL files after a merge produced two concurrent head revisions that broke production on deploy.",
        "ai_coding",
        "Database migrations are versioned with Alembic, enforced single-head by a CI check, and applied during a dedicated pre-deploy Kubernetes Job before rollout.",
        "ai_coding",
    ),
    # 47. build artifacts
    (
        "Adopted SLSA level 3 provenance on all release binaries after a supply-chain tabletop exercise revealed no way to verify which commit produced a given image.",
        "technical",
        "Release pipelines emit SLSA v1.0 provenance attestations signed by Sigstore cosign and stored alongside images in the OCI registry under the .att tag.",
        "technical",
    ),
    # 48. serverless functions
    (
        "Chose Cloudflare Workers over AWS Lambda for the URL-shortener edge tier because cold starts dominated p95 latency at 400 ms on Lambda.",
        "technical",
        "The URL-shortener runs as a Cloudflare Worker deployed to the global network with Workers KV for hot lookups and a D1 database as the durable store.",
        "technical",
    ),
    # 49. database — time series
    (
        "Adopted TimescaleDB over vanilla Postgres for IoT telemetry after ingest past 40k rows/second caused lock contention on the btree indexes.",
        "technical",
        "IoT telemetry is written to a TimescaleDB 2.15 hypertable chunked by one-hour intervals with continuous aggregates refreshed every five minutes for dashboard queries.",
        "technical",
    ),
    # 50. event schemas
    (
        "Picked Avro with a Confluent Schema Registry over raw JSON on Kafka after two consumer teams silently diverged on the order-created payload.",
        "technical",
        "Kafka topics carry Avro-encoded messages validated against a Confluent Schema Registry with BACKWARD_TRANSITIVE compatibility and subject naming of <topic>-value.",
        "technical",
    ),
]


def emit() -> int:
    assert len(PAIRS) == 50, f"expected 50 pairs, got {len(PAIRS)}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (dec_text, dec_domain, arch_text, arch_domain) in enumerate(PAIRS, start=1):
            pair_id = f"cls-pair-{PAIR_OFFSET + i:05d}"
            dec_id = f"class-{ID_OFFSET + (2 * i - 1):05d}"
            arch_id = f"class-{ID_OFFSET + (2 * i):05d}"
            f.write(json.dumps({"id": dec_id, "domain": dec_domain, "text": dec_text, "memory_type": "decision", "pair_id": pair_id}, ensure_ascii=False) + "\n")
            f.write(json.dumps({"id": arch_id, "domain": arch_domain, "text": arch_text, "memory_type": "architecture", "pair_id": pair_id}, ensure_ascii=False) + "\n")
            written += 2
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
