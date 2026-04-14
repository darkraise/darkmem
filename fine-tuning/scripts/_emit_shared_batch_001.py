"""One-off emitter for shared-base batch-001.

Produces 50 rows in the `technical` domain, appends to
`data/v2/shared/shared.jsonl`. Character offsets are computed from
the entity name positions in the text so they cannot drift.

This file is committed as a reusable pattern for future batches;
new batches copy it and swap the ENTRIES list.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "shared.jsonl"

# Each entry: (text, memory_type, domain, noise, entities, relationships, query_question, query_keyword)
# entities: [(name, type), ...]
# relationships: [(source, target, relation_type), ...]
# For noise rows set query_question/keyword to None; they will be omitted.

ENTRIES: list[tuple] = [
    # --- 1. decision: migration ---
    ("We migrated from Celery to asyncio for task orchestration because Redis was the only remaining dependency.", "decision", "technical", False,
     [("Celery", "framework"), ("asyncio", "library"), ("Redis", "database")],
     [("asyncio", "Celery", "REPLACES")],
     "why did we move off Celery for background tasks",
     "Celery to asyncio migration rationale"),
    # --- 2. decision: vector store ---
    ("Chose pgvector over Qdrant for the memory store since we already operate Postgres in production.", "decision", "technical", False,
     [("pgvector", "library"), ("Qdrant", "database"), ("Postgres", "database")],
     [("pgvector", "Qdrant", "REPLACES")],
     "why pgvector instead of a dedicated vector database",
     "pgvector vs Qdrant selection"),
    # --- 3. architecture: service topology ---
    ("The ingestion pipeline writes to Kafka, and a Flink job fans out events to Elasticsearch and S3.", "architecture", "technical", False,
     [("Kafka", "infrastructure"), ("Flink", "framework"), ("Elasticsearch", "database"), ("S3", "service")],
     [("Flink", "Kafka", "DEPENDS_ON"), ("Flink", "Elasticsearch", "PRODUCES"), ("Flink", "S3", "PRODUCES")],
     "how do ingested events flow from Kafka to storage",
     "Kafka Flink Elasticsearch S3 pipeline topology"),
    # --- 4. problem: runtime bug ---
    ("Memory leaked in the Node.js worker because EventEmitter listeners were never removed after reconnects.", "problem", "technical", False,
     [("Node.js", "platform"), ("EventEmitter", "api")],
     [],
     "what caused the Node.js worker memory leak",
     "Node.js EventEmitter leak reconnect"),
    # --- 5. decision: CI ---
    ("Picked GitHub Actions over Jenkins for our new projects; simpler hosted runners and matrix builds out of the box.", "decision", "technical", False,
     [("GitHub Actions", "platform"), ("Jenkins", "service")],
     [("GitHub Actions", "Jenkins", "REPLACES")],
     "CI choice for greenfield services",
     "GitHub Actions vs Jenkins decision"),
    # --- 6. architecture: event bus ---
    ("Redis Streams carries task events between the scheduler and the worker pool.", "architecture", "technical", False,
     [("Redis Streams", "infrastructure"), ("scheduler", "service"), ("worker pool", "service")],
     [("scheduler", "Redis Streams", "COMMUNICATES_WITH"), ("worker pool", "Redis Streams", "COMMUNICATES_WITH")],
     "how do scheduler and workers exchange tasks",
     "Redis Streams task bus design"),
    # --- 7. problem: GraphQL ---
    ("The GraphQL resolver produced N+1 queries because DataLoader was never wired up for the author field.", "problem", "technical", False,
     [("GraphQL", "framework"), ("DataLoader", "library")],
     [],
     "what caused the N+1 query on the author field",
     "GraphQL N+1 DataLoader missing"),
    # --- 8. decision: language ---
    ("Moved the backend from JavaScript to TypeScript to tighten the contract at service boundaries.", "decision", "technical", False,
     [("JavaScript", "language"), ("TypeScript", "language")],
     [("TypeScript", "JavaScript", "REPLACES")],
     "why did we rewrite the backend in TypeScript",
     "JavaScript to TypeScript migration"),
    # --- 9. reference: spec ---
    ("HTTP caching semantics follow RFC 7234; stale-while-revalidate handling is documented in RFC 5861.", "reference", "technical", False,
     [("RFC 7234", "publication"), ("RFC 5861", "publication")],
     [],
     "which RFCs define HTTP caching and stale-while-revalidate",
     "RFC 7234 5861 HTTP caching"),
    # --- 10. milestone: throughput ---
    ("Ingestion crossed one million events per day on 2026-02-01 after enabling batched writes.", "milestone", "technical", False,
     [("2026-02-01", "date")],
     [],
     "when did ingestion first hit one million events per day",
     "1M events per day milestone date"),
    # --- 11. decision: container runtime ---
    ("Switched from Docker Compose to Podman on the dev laptops; rootless mode removed the last reason to keep Docker.", "decision", "technical", False,
     [("Docker Compose", "service"), ("Podman", "service")],
     [("Podman", "Docker Compose", "REPLACES")],
     "why did we replace Docker Compose with Podman locally",
     "Docker Compose to Podman migration dev laptops"),
    # --- 12. architecture: storage ---
    ("Hot data lives in Postgres, cold data moves to Parquet on S3, and Trino queries both uniformly.", "architecture", "technical", False,
     [("Postgres", "database"), ("Parquet", "technology"), ("S3", "service"), ("Trino", "service")],
     [("Trino", "Postgres", "COMMUNICATES_WITH"), ("Trino", "S3", "COMMUNICATES_WITH")],
     "how do we query hot and cold data uniformly",
     "Postgres Parquet S3 Trino tiered storage"),
    # --- 13. problem: OOM ---
    ("The reranker container hit OOM because torch cached tensors for every batch and never released them.", "problem", "technical", False,
     [("reranker", "service"), ("torch", "library")],
     [],
     "why did the reranker container go OOM",
     "reranker torch tensor cache OOM"),
    # --- 14. decision: observability ---
    ("Standardised logs on Loki and dropped the legacy ELK stack; Grafana already covered the dashboards.", "decision", "technical", False,
     [("Loki", "service"), ("ELK", "infrastructure"), ("Grafana", "service")],
     [("Loki", "ELK", "REPLACES")],
     "why did we move logs from ELK to Loki",
     "ELK to Loki log migration"),
    # --- 15. architecture: auth ---
    ("The API gateway verifies JWTs issued by Keycloak and injects a user context header downstream.", "architecture", "technical", False,
     [("API gateway", "service"), ("JWT", "protocol"), ("Keycloak", "service")],
     [("API gateway", "Keycloak", "DEPENDS_ON")],
     "how does the API gateway authenticate requests",
     "API gateway JWT Keycloak context propagation"),
    # --- 16. fact: performance ---
    ("On the 5060 GPU, GLiNER-small runs inference at about 50 ms per 200-token input.", "fact", "technical", False,
     [("5060", "infrastructure"), ("GLiNER-small", "library")],
     [],
     "how fast is GLiNER-small on the 5060",
     "GLiNER-small RTX 5060 inference latency"),
    # --- 17. decision: serialisation ---
    ("Switched internal service contracts from JSON to Protobuf; the schema registry paid for itself in one incident.", "decision", "technical", False,
     [("JSON", "technology"), ("Protobuf", "technology")],
     [("Protobuf", "JSON", "REPLACES")],
     "why did we adopt Protobuf for internal contracts",
     "JSON to Protobuf internal service migration"),
    # --- 18. problem: concurrency ---
    ("Duplicate row inserts slipped past the uniqueness check because the INSERT was not wrapped in a serializable transaction.", "problem", "technical", False,
     [("INSERT", "command")],
     [],
     "why did duplicate rows slip past the uniqueness check",
     "INSERT serializable transaction duplicate"),
    # --- 19. preference: code style ---
    ("Team prefers explicit Optional types over None defaults in the Python code base to keep null-handling visible.", "preference", "technical", False,
     [("Optional", "pattern"), ("Python", "language")],
     [],
     "what does the team prefer for nullable fields in Python",
     "Python Optional vs None default preference"),
    # --- 20. architecture: caching ---
    ("Memcached sits in front of the profile service to absorb read spikes during feed fan-out.", "architecture", "technical", False,
     [("Memcached", "service"), ("profile service", "service")],
     [("profile service", "Memcached", "DEPENDS_ON")],
     "what absorbs read spikes on the profile service",
     "Memcached profile service read cache"),
    # --- 21. milestone: release ---
    ("Shipped v2.0 of the extraction pipeline on 2026-03-18 after the GLiNER fine-tune beat the LLM baseline.", "milestone", "technical", False,
     [("v2.0", "project"), ("2026-03-18", "date"), ("GLiNER", "library")],
     [],
     "when did v2.0 of the extraction pipeline ship",
     "extraction pipeline v2.0 release date"),
    # --- 22. decision: queue ---
    ("Adopted NATS JetStream for durable queuing; AMQP latency was too spiky under our fan-out load.", "decision", "technical", False,
     [("NATS JetStream", "service"), ("AMQP", "protocol")],
     [("NATS JetStream", "AMQP", "REPLACES")],
     "why did we pick NATS JetStream over AMQP",
     "NATS JetStream AMQP replacement"),
    # --- 23. problem: TLS ---
    ("mTLS handshakes failed after the cert rotation because the sidecar cached the old CA bundle in memory.", "problem", "technical", False,
     [("mTLS", "protocol"), ("sidecar", "service"), ("CA bundle", "config")],
     [],
     "why did mTLS handshakes fail after the certificate rotation",
     "mTLS sidecar CA bundle cache rotation"),
    # --- 24. fact: version ---
    ("Production runs PostgreSQL 16.2 with pgvector 0.7.0.", "fact", "technical", False,
     [("PostgreSQL", "database"), ("pgvector", "library")],
     [],
     "which database versions are currently deployed",
     "16.2 and 0.7.0 in use"),
    # --- 25. architecture: search ---
    ("OpenSearch handles lexical search while the embedder service provides dense candidates; the reranker merges both.", "architecture", "technical", False,
     [("OpenSearch", "service"), ("embedder service", "service"), ("reranker", "service")],
     [("reranker", "OpenSearch", "DEPENDS_ON"), ("reranker", "embedder service", "DEPENDS_ON")],
     "how do we combine lexical and dense search results",
     "OpenSearch embedder reranker hybrid retrieval"),
    # --- 26. decision: infra-as-code ---
    ("Moved infra from Terraform to Pulumi so teams can write in TypeScript instead of HCL.", "decision", "technical", False,
     [("Terraform", "tool"), ("Pulumi", "tool"), ("TypeScript", "language"), ("HCL", "language")],
     [("Pulumi", "Terraform", "REPLACES")],
     "why did we switch from Terraform to Pulumi",
     "Terraform to Pulumi infra migration"),
    # --- 27. problem: DNS ---
    ("Intermittent 5xx errors traced back to the DNS cache in the sidecar not honouring low TTLs during deploys.", "problem", "technical", False,
     [("DNS", "protocol"), ("sidecar", "service")],
     [],
     "why did intermittent 5xx errors spike during deploys",
     "sidecar DNS TTL cache 5xx root cause"),
    # --- 28. architecture: batch pipeline ---
    ("Airflow orchestrates a nightly dbt run that materialises marts in BigQuery.", "architecture", "technical", False,
     [("Airflow", "service"), ("dbt", "tool"), ("BigQuery", "service")],
     [("Airflow", "dbt", "USES"), ("dbt", "BigQuery", "PRODUCES")],
     "what orchestrates our nightly analytics marts",
     "Airflow dbt BigQuery mart orchestration"),
    # --- 29. decision: migrations ---
    ("Replaced raw SQL migrations with Alembic so schema changes review as diffs against declarative models.", "decision", "technical", False,
     [("SQL", "language"), ("Alembic", "tool")],
     [("Alembic", "SQL", "REPLACES")],
     "why did we adopt Alembic for schema migrations",
     "SQL to Alembic migration tooling"),
    # --- 30. problem: GC ---
    ("Tail latency spikes correlated with JVM G1 mixed collections; tuning max heap down brought P99 back under 80 ms.", "problem", "technical", False,
     [("JVM", "platform"), ("G1", "algorithm")],
     [],
     "what caused the tail latency spikes and how did we fix them",
     "JVM G1 tail latency tuning"),
    # --- 31. fact: quota ---
    ("Each tenant is capped at 10,000 API calls per minute at the gateway.", "fact", "technical", False,
     [("API", "api"), ("gateway", "service")],
     [],
     "what is the per-tenant API rate limit",
     "tenant API gateway rate limit"),
    # --- 32. architecture: secrets ---
    ("Services fetch short-lived credentials from Vault at startup and refresh them on every token expiry.", "architecture", "technical", False,
     [("Vault", "service")],
     [],
     "how do services obtain and refresh credentials",
     "Vault short-lived credentials refresh pattern"),
    # --- 33. decision: vector store eviction ---
    ("Picked HNSW over IVF for the embedder index because recall-at-10 stayed flat while build time halved.", "decision", "technical", False,
     [("HNSW", "algorithm"), ("IVF", "algorithm")],
     [("HNSW", "IVF", "IMPROVES_ON")],
     "why did we choose HNSW instead of IVF",
     "HNSW vs IVF embedder index choice"),
    # --- 34. problem: encoding ---
    ("UTF-8 validation errors in the ingestor traced to a legacy CP1252 input that was never converted at the edge.", "problem", "technical", False,
     [("UTF-8", "protocol"), ("CP1252", "protocol"), ("ingestor", "service")],
     [],
     "what caused UTF-8 validation errors in the ingestor",
     "ingestor CP1252 UTF-8 encoding bug"),
    # --- 35. architecture: deployment ---
    ("Argo CD reconciles the cluster against Git, and Flagger progressively shifts traffic for canaries.", "architecture", "technical", False,
     [("Argo CD", "service"), ("Flagger", "service"), ("Git", "tool")],
     [("Argo CD", "Git", "DEPENDS_ON"), ("Flagger", "Argo CD", "DEPENDS_ON")],
     "how do we deploy and canary releases to the cluster",
     "Argo CD Flagger GitOps canary deployment"),
    # --- 36. decision: security ---
    ("Stopped issuing long-lived API tokens; everything goes through OIDC device flow plus short-lived bearer tokens.", "decision", "technical", False,
     [("OIDC", "protocol")],
     [],
     "why did we retire long-lived API tokens",
     "OIDC short-lived token migration"),
    # --- 37. fact: SLA ---
    ("The search API commits to a P99 latency of 200 ms for queries under ten terms.", "fact", "technical", False,
     [("search API", "api")],
     [],
     "what is the search API P99 latency target",
     "search API P99 latency SLA"),
    # --- 38. problem: deadlock ---
    ("Inventory updates deadlocked because two workers acquired row locks in opposite order; fixed by sorting keys before update.", "problem", "technical", False,
     [("Inventory", "service")],
     [],
     "why did inventory updates deadlock and how was it fixed",
     "inventory deadlock row lock ordering"),
    # --- 39. architecture: rate limit ---
    ("The token bucket rate limiter runs in Envoy via a WASM filter and syncs state through Redis.", "architecture", "technical", False,
     [("Envoy", "service"), ("WASM", "technology"), ("Redis", "database")],
     [("Envoy", "Redis", "COMMUNICATES_WITH")],
     "where does the rate limiter run and how is state shared",
     "Envoy WASM token bucket Redis"),
    # --- 40. preference: testing ---
    ("Team prefers table-driven tests in Go over many small functions; easier to extend and review.", "preference", "technical", False,
     [("Go", "language")],
     [],
     "how does the team like to structure Go tests",
     "Go table-driven tests preference"),
    # --- 41. noise ---
    ("Let me think about this for a moment before making any changes.", "fact", "noise", True, [], [], None, None),
    # --- 42. decision: backup ---
    ("Swapped pg_dump for WAL-E continuous archiving; we needed point-in-time recovery, not nightly snapshots.", "decision", "technical", False,
     [("pg_dump", "tool"), ("WAL-E", "tool")],
     [("WAL-E", "pg_dump", "REPLACES")],
     "why did we move from pg_dump to WAL-E",
     "pg_dump to WAL-E continuous archiving"),
    # --- 43. problem: caching ---
    ("Cache stampede after deploys traced to a hot key with zero jitter on TTL; added random 10 percent jitter.", "problem", "technical", False,
     [("TTL", "config")],
     [],
     "what caused the cache stampede after deploys",
     "cache stampede TTL jitter fix"),
    # --- 44. architecture: billing ---
    ("The billing service consumes Kafka events, aggregates per tenant in ClickHouse, and exports invoices nightly.", "architecture", "technical", False,
     [("billing service", "service"), ("Kafka", "infrastructure"), ("ClickHouse", "database")],
     [("billing service", "Kafka", "DEPENDS_ON"), ("billing service", "ClickHouse", "PRODUCES")],
     "how does the billing service aggregate tenant usage",
     "billing Kafka ClickHouse invoice pipeline"),
    # --- 45. fact: embedding ---
    ("The production embedder outputs 768-dimensional vectors.", "fact", "technical", False,
     [("embedder", "service")],
     [],
     "how wide is the output from our embedding model",
     "768-dim representation size"),
    # --- 46. decision: PR tooling ---
    ("Adopted graphite-cli for stacked PRs after repeated rebase pain with long feature branches.", "decision", "technical", False,
     [("graphite-cli", "tool")],
     [],
     "why did we adopt graphite-cli for PR workflow",
     "graphite-cli stacked PR adoption"),
    # --- 47. problem: timezone ---
    ("Scheduled jobs fired an hour late during DST because the scheduler used local time instead of UTC internally.", "problem", "technical", False,
     [("scheduler", "service"), ("UTC", "protocol")],
     [],
     "why did scheduled jobs fire an hour late during DST",
     "scheduler DST UTC off-by-one"),
    # --- 48. architecture: CDC ---
    ("Debezium streams Postgres CDC events into Kafka so downstream services stay consistent without polling.", "architecture", "technical", False,
     [("Debezium", "tool"), ("Postgres", "database"), ("Kafka", "infrastructure")],
     [("Debezium", "Postgres", "DEPENDS_ON"), ("Debezium", "Kafka", "PRODUCES")],
     "how do downstream services learn about Postgres changes",
     "Debezium Postgres Kafka CDC pattern"),
    # --- 49. noise ---
    ("That should do it for today; picking this back up tomorrow morning.", "fact", "noise", True, [], [], None, None),
    # --- 50. reference: standard ---
    ("Our webhook signatures follow the scheme described in the Standard Webhooks specification at standardwebhooks.com.", "reference", "technical", False,
     [("Standard Webhooks", "publication")],
     [],
     "which specification governs our webhook signatures",
     "Standard Webhooks signature specification"),
]


def _find_span(text: str, needle: str, used: list[tuple[int, int]]) -> tuple[int, int]:
    """Find the first occurrence of `needle` in `text` that doesn't overlap used spans."""
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
                "id": f"shared-{i:05d}",
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
