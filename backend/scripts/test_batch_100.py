import asyncio, json, time, httpx

MCP_URL = "http://localhost:8000/mcp"

entries = [
    # ── Algorithms & Data Structures (20) ──
    {"content": "Dijkstra's algorithm finds the shortest path in a weighted graph with non-negative edges. It uses a priority queue to greedily expand the nearest unvisited node. Time complexity is O((V+E) log V) with a binary heap.", "tags": ["tech/algorithms"], "source": "test-100", "memory_type": "fact"},
    {"content": "A bloom filter is a space-efficient probabilistic data structure that tests set membership. It can return false positives but never false negatives. Useful for cache-miss reduction and spell checkers.", "tags": ["tech/algorithms"], "source": "test-100", "memory_type": "fact"},
    {"content": "Red-black trees guarantee O(log n) insertion, deletion, and lookup by maintaining balance through color invariants. Every path from root to leaf has the same number of black nodes.", "tags": ["tech/algorithms"], "source": "test-100", "memory_type": "fact"},
    {"content": "Consistent hashing distributes keys across nodes so that adding or removing a node only remaps O(K/n) keys. Used by DynamoDB, Cassandra, and Memcached for partition assignment.", "tags": ["tech/algorithms", "tech/distributed"], "source": "test-100", "memory_type": "fact"},
    {"content": "The Raft consensus algorithm elects a leader among replicas and replicates log entries to followers. It is simpler than Paxos and used by etcd, CockroachDB, and TiKV.", "tags": ["tech/algorithms", "tech/distributed"], "source": "test-100", "memory_type": "fact"},
    {"content": "B-trees are optimized for disk I/O by storing multiple keys per node, reducing tree height. PostgreSQL uses B-tree indexes by default for equality and range queries.", "tags": ["tech/algorithms", "tech/databases"], "source": "test-100", "memory_type": "fact"},
    {"content": "Skip lists provide O(log n) search like balanced trees but with simpler implementation. Redis uses skip lists for sorted sets because they support efficient range queries.", "tags": ["tech/algorithms", "tech/databases"], "source": "test-100", "memory_type": "fact"},
    {"content": "The CAP theorem states that a distributed system can provide at most two of consistency, availability, and partition tolerance simultaneously. Most real systems choose AP or CP.", "tags": ["tech/distributed"], "source": "test-100", "memory_type": "fact"},
    {"content": "Merkle trees hash data blocks into a binary tree where each parent is the hash of its children. Git uses Merkle trees to efficiently detect changes between commits.", "tags": ["tech/algorithms"], "source": "test-100", "memory_type": "fact"},
    {"content": "LRU cache evicts the least recently used entry when the cache is full. Python's functools.lru_cache implements this with a doubly-linked list and a hash map for O(1) operations.", "tags": ["tech/algorithms", "tech/python"], "source": "test-100", "memory_type": "fact"},
    {"content": "Topological sort orders nodes in a DAG such that every edge goes from earlier to later in the ordering. Used for build systems, task scheduling, and dependency resolution.", "tags": ["tech/algorithms"], "source": "test-100", "memory_type": "fact"},
    {"content": "The A* search algorithm combines Dijkstra's actual cost with a heuristic estimate of remaining cost. It is optimal when the heuristic is admissible (never overestimates).", "tags": ["tech/algorithms"], "source": "test-100", "memory_type": "fact"},
    {"content": "Trie (prefix tree) stores strings character-by-character, enabling O(m) lookup where m is string length. Useful for autocomplete, IP routing tables, and dictionary search.", "tags": ["tech/algorithms"], "source": "test-100", "memory_type": "fact"},
    {"content": "Write-ahead logging (WAL) ensures durability by writing changes to a log before applying them to the database. PostgreSQL, SQLite, and InnoDB all use WAL for crash recovery.", "tags": ["tech/databases"], "source": "test-100", "memory_type": "fact"},
    {"content": "MVCC (Multi-Version Concurrency Control) allows readers and writers to operate without blocking each other by maintaining multiple versions of each row. PostgreSQL uses MVCC with transaction IDs.", "tags": ["tech/databases"], "source": "test-100", "memory_type": "fact"},
    {"content": "The two-phase commit protocol coordinates distributed transactions by having a coordinator ask all participants to prepare, then commit or abort. It blocks if the coordinator crashes.", "tags": ["tech/distributed"], "source": "test-100", "memory_type": "fact"},
    {"content": "Exponential backoff with jitter prevents thundering herd problems in retry logic. AWS recommends full jitter: sleep = random(0, min(cap, base * 2^attempt)).", "tags": ["tech/distributed", "infra/cloud"], "source": "test-100", "memory_type": "fact"},
    {"content": "CRDTs (Conflict-free Replicated Data Types) allow concurrent updates on different replicas without coordination. G-Counters, OR-Sets, and LWW-Registers are common CRDT types.", "tags": ["tech/distributed"], "source": "test-100", "memory_type": "fact"},
    {"content": "The actor model encapsulates state within actors that communicate via asynchronous messages. Erlang/OTP and Akka implement the actor model for fault-tolerant concurrent systems.", "tags": ["tech/concurrency"], "source": "test-100", "memory_type": "fact"},
    {"content": "Circuit breakers prevent cascading failures by stopping requests to a failing service after a threshold is reached. The states are closed (normal), open (blocked), and half-open (testing).", "tags": ["tech/distributed", "tech/patterns"], "source": "test-100", "memory_type": "fact"},

    # ── Language & Framework Specifics (20) ──
    {"content": "Python's GIL (Global Interpreter Lock) prevents true parallel execution of Python bytecodes. Use multiprocessing or asyncio for CPU-bound and I/O-bound parallelism respectively.", "tags": ["tech/python"], "source": "test-100", "memory_type": "fact"},
    {"content": "Rust's ownership system prevents data races at compile time without garbage collection. Each value has exactly one owner, and borrowing rules enforce either one mutable or many immutable references.", "tags": ["tech/rust"], "source": "test-100", "memory_type": "fact"},
    {"content": "Go channels provide typed conduits for goroutine communication. Unbuffered channels synchronize sender and receiver; buffered channels allow async sends up to the buffer size.", "tags": ["tech/go"], "source": "test-100", "memory_type": "fact"},
    {"content": "TypeScript's discriminated unions use a shared literal property to narrow types. Pattern: type Shape = { kind: 'circle'; radius: number } | { kind: 'square'; side: number }.", "tags": ["tech/typescript"], "source": "test-100", "memory_type": "fact"},
    {"content": "React's useEffect hook runs side effects after render. The dependency array controls when it re-runs: empty array means mount-only, no array means every render, specific deps mean on-change.", "tags": ["tech/react"], "source": "test-100", "memory_type": "fact"},
    {"content": "FastAPI uses Pydantic models for request validation and Python type hints for automatic OpenAPI schema generation. Dependency injection via Depends() enables clean separation of concerns.", "tags": ["tech/python", "tech/fastapi"], "source": "test-100", "memory_type": "fact"},
    {"content": "SQLAlchemy 2.0 introduced the select() style query API replacing the legacy Query object. Mapped columns use Mapped[type] annotations and mapped_column() for explicit column definitions.", "tags": ["tech/python", "tech/sqlalchemy"], "source": "test-100", "memory_type": "fact"},
    {"content": "Next.js App Router uses React Server Components by default. Server components run on the server and stream HTML to the client, reducing JavaScript bundle size.", "tags": ["tech/nextjs", "tech/react"], "source": "test-100", "memory_type": "fact"},
    {"content": "Docker multi-stage builds reduce image size by using separate stages for building and running. The final stage copies only the compiled artifacts, discarding build dependencies.", "tags": ["tech/docker"], "source": "test-100", "memory_type": "fact"},
    {"content": "Kubernetes liveness probes detect unhealthy pods and restart them. Readiness probes control whether a pod receives traffic. Startup probes handle slow-starting containers.", "tags": ["tech/kubernetes"], "source": "test-100", "memory_type": "fact"},

    # ── Decisions (15) ──
    {"content": "We chose PostgreSQL over MySQL because it has better support for JSONB, full-text search, and pgvector. The query planner is also more sophisticated for complex joins.", "tags": ["project/decisions", "tech/databases"], "source": "test-100", "memory_type": "decision"},
    {"content": "We decided to use Redis for session storage instead of in-memory sessions because we need horizontal scaling across multiple API servers.", "tags": ["project/decisions"], "source": "test-100", "memory_type": "decision"},
    {"content": "We went with gRPC instead of REST for internal service communication because of binary serialization, streaming support, and auto-generated client stubs from protobuf schemas.", "tags": ["project/decisions"], "source": "test-100", "memory_type": "decision"},
    {"content": "We switched from Jenkins to GitHub Actions because the YAML-based workflow is easier to maintain, and it integrates natively with our PR review process.", "tags": ["project/decisions", "workflow/ci"], "source": "test-100", "memory_type": "decision"},
    {"content": "We chose TanStack Router over React Router because it provides type-safe route params, built-in search param validation, and file-based route generation.", "tags": ["project/decisions", "tech/react"], "source": "test-100", "memory_type": "decision"},
    {"content": "We decided to implement rate limiting at the API gateway level using sliding window counters in Redis rather than per-service rate limiters to ensure consistent behavior.", "tags": ["project/decisions", "tech/architecture"], "source": "test-100", "memory_type": "decision"},
    {"content": "We picked Terraform over Pulumi for infrastructure as code because the team already knows HCL and the Terraform provider ecosystem is more mature.", "tags": ["project/decisions", "infra/iac"], "source": "test-100", "memory_type": "decision"},
    {"content": "We settled on Prometheus plus Grafana for monitoring instead of Datadog because we want to avoid per-host pricing and keep metrics data on-premises.", "tags": ["project/decisions", "infra/monitoring"], "source": "test-100", "memory_type": "decision"},
    {"content": "We decided against microservices for the MVP and went with a modular monolith. The team is small and deployment complexity would slow us down more than the coupling risk.", "tags": ["project/decisions", "tech/architecture"], "source": "test-100", "memory_type": "decision"},
    {"content": "We chose Alembic for database migrations over raw SQL scripts because it tracks migration history, supports auto-generation from SQLAlchemy models, and handles rollbacks.", "tags": ["project/decisions", "tech/python"], "source": "test-100", "memory_type": "decision"},
    {"content": "We replaced Celery with asyncio task queues because our workload is I/O-bound and the overhead of a separate message broker was not justified.", "tags": ["project/decisions", "tech/python"], "source": "test-100", "memory_type": "decision"},
    {"content": "We selected Tailwind CSS over styled-components because utility classes are faster to iterate with, produce smaller bundle sizes, and avoid runtime CSS-in-JS overhead.", "tags": ["project/decisions", "tech/frontend"], "source": "test-100", "memory_type": "decision"},
    {"content": "We opted for server-sent events over WebSockets for pipeline status updates because the data flow is unidirectional and SSE reconnects automatically.", "tags": ["project/decisions", "tech/web"], "source": "test-100", "memory_type": "decision"},
    {"content": "We decided to use Pydantic v2 instead of v1 because it is 5-17x faster for validation, uses Rust-based core, and has better TypedDict support.", "tags": ["project/decisions", "tech/python"], "source": "test-100", "memory_type": "decision"},
    {"content": "We went with uvicorn over gunicorn for ASGI because uvicorn has native asyncio support and lower memory footprint for our async FastAPI application.", "tags": ["project/decisions", "tech/python"], "source": "test-100", "memory_type": "decision"},

    # ── Debugging & Problems (15) ──
    {"content": "The OOM crash in the indexer was caused by loading all file contents into memory at once. Fixed by streaming files one at a time through the parser.", "tags": ["debug/root-cause"], "source": "test-100", "memory_type": "debug"},
    {"content": "The N+1 query in the memory listing endpoint was fetching tags one-by-one for each memory. Fixed by adding selectinload(Memory.tags) to the query.", "tags": ["debug/root-cause", "tech/sqlalchemy"], "source": "test-100", "memory_type": "debug"},
    {"content": "Connection pool exhaustion under load was caused by long-running background tasks holding sessions. Fixed by creating separate session factories for background workers.", "tags": ["debug/root-cause", "tech/sqlalchemy"], "source": "test-100", "memory_type": "debug"},
    {"content": "The CORS error on the frontend was caused by the API returning 500 before CORS headers were added. FastAPI's CORSMiddleware only adds headers to successful responses by default.", "tags": ["debug/root-cause", "tech/fastapi"], "source": "test-100", "memory_type": "debug"},
    {"content": "Alembic migration failed with 'relation already exists' because someone ran create_all() in production, creating tables outside of migration tracking. Had to stamp the current revision.", "tags": ["debug/root-cause", "tech/python"], "source": "test-100", "memory_type": "debug"},
    {"content": "The WebSocket kept disconnecting because Nginx proxy_read_timeout defaults to 60 seconds. Set proxy_read_timeout 86400s and added ping/pong keepalives.", "tags": ["debug/root-cause", "infra/nginx"], "source": "test-100", "memory_type": "debug"},
    {"content": "Hot module replacement in Vite stopped working after upgrading React. The issue was that the new JSX transform requires react-refresh to be explicitly configured in vite.config.ts.", "tags": ["debug/root-cause", "tech/frontend"], "source": "test-100", "memory_type": "debug"},
    {"content": "Docker build cache was invalidated on every build because COPY . . was before pip install. Reordered to COPY requirements.txt first, then install, then COPY the rest.", "tags": ["debug/workaround", "tech/docker"], "source": "test-100", "memory_type": "debug"},
    {"content": "The asyncio.gather was silently swallowing exceptions because return_exceptions=True was set but nobody checked the results for Exception instances.", "tags": ["debug/gotcha", "tech/python"], "source": "test-100", "memory_type": "debug"},
    {"content": "JWT tokens were being rejected after server restart because the secret was randomly generated at startup instead of loaded from environment. Tokens signed with the old secret became invalid.", "tags": ["debug/root-cause", "tech/security"], "source": "test-100", "memory_type": "debug"},
    {"content": "The Pydantic validation error 'field required' was misleading. The actual issue was sending camelCase JSON while the model expected snake_case. Fixed by adding model_config with populate_by_name.", "tags": ["debug/root-cause", "tech/python"], "source": "test-100", "memory_type": "debug"},
    {"content": "PostgreSQL VACUUM was not running because autovacuum was disabled on the large memories table. This caused transaction ID wraparound warnings. Re-enabled autovacuum with tuned thresholds.", "tags": ["debug/root-cause", "tech/databases"], "source": "test-100", "memory_type": "debug"},
    {"content": "The embedding dimension mismatch crash happened because the Ollama model was updated and the new version outputs 768-dim vectors while the database column expects 1024. Added a startup dimension probe.", "tags": ["debug/root-cause", "tech/ml"], "source": "test-100", "memory_type": "debug"},
    {"content": "Race condition in tag creation: two concurrent requests both tried to INSERT the same tag name, causing a unique constraint violation. Fixed with ON CONFLICT DO NOTHING.", "tags": ["debug/root-cause", "tech/databases"], "source": "test-100", "memory_type": "debug"},
    {"content": "Memory leak in the WebSocket manager: disconnected clients were not removed from the broadcast list. The list grew unbounded, and each broadcast iterated over dead connections.", "tags": ["debug/root-cause", "tech/web"], "source": "test-100", "memory_type": "debug"},

    # ── Infrastructure & DevOps (15) ──
    {"content": "Nginx reverse proxy configuration for WebSocket: requires proxy_http_version 1.1, proxy_set_header Upgrade $http_upgrade, and proxy_set_header Connection 'upgrade'.", "tags": ["infra/nginx", "tech/websocket"], "source": "test-100", "memory_type": "fact"},
    {"content": "Docker Compose health checks use test: ['CMD', 'pg_isready'] for PostgreSQL containers. The depends_on condition: service_healthy ensures dependent services wait for readiness.", "tags": ["infra/docker"], "source": "test-100", "memory_type": "fact"},
    {"content": "GitHub Actions caching with actions/cache speeds up CI by 60-80%. Cache key should include the lock file hash: hashFiles('**/package-lock.json').", "tags": ["workflow/ci", "infra/github"], "source": "test-100", "memory_type": "fact"},
    {"content": "Prometheus scrape interval should be set to 15-30 seconds for most services. Too frequent scraping wastes resources; too infrequent misses short-lived spikes.", "tags": ["infra/monitoring"], "source": "test-100", "memory_type": "fact"},
    {"content": "PostgreSQL connection pooling with PgBouncer in transaction mode allows hundreds of application connections to share a small pool of database connections.", "tags": ["infra/databases", "tech/postgresql"], "source": "test-100", "memory_type": "fact"},
    {"content": "Let's Encrypt certificates auto-renew every 60 days via certbot. The renewal hook should reload Nginx: certbot renew --deploy-hook 'systemctl reload nginx'.", "tags": ["infra/ssl"], "source": "test-100", "memory_type": "fact"},
    {"content": "Terraform state should be stored remotely in S3 with DynamoDB locking to prevent concurrent modifications. Never commit terraform.tfstate to version control.", "tags": ["infra/iac", "tech/terraform"], "source": "test-100", "memory_type": "fact"},
    {"content": "Kubernetes resource limits prevent noisy neighbor problems. Set requests (guaranteed) lower than limits (burstable). OOMKilled means the container exceeded its memory limit.", "tags": ["infra/kubernetes"], "source": "test-100", "memory_type": "fact"},
    {"content": "Grafana dashboard variables use label_values() to populate dropdown filters from Prometheus label data. Template variables make dashboards reusable across environments.", "tags": ["infra/monitoring", "tech/grafana"], "source": "test-100", "memory_type": "fact"},
    {"content": "SSH tunneling with -L flag forwards a local port to a remote service: ssh -L 5433:localhost:5432 user@bastion. Useful for accessing databases behind firewalls.", "tags": ["infra/networking"], "source": "test-100", "memory_type": "fact"},
    {"content": "Systemd service files should set Restart=on-failure and RestartSec=5 for production services. WantedBy=multi-user.target ensures the service starts on boot.", "tags": ["infra/linux"], "source": "test-100", "memory_type": "fact"},
    {"content": "CORS preflight requests (OPTIONS) are sent by browsers before cross-origin POST/PUT/DELETE. The server must respond with appropriate Access-Control-Allow-* headers.", "tags": ["infra/web", "tech/security"], "source": "test-100", "memory_type": "fact"},
    {"content": "Redis persistence has two modes: RDB (point-in-time snapshots) and AOF (append-only log). AOF with fsync every second provides the best durability-performance balance.", "tags": ["infra/databases", "tech/redis"], "source": "test-100", "memory_type": "fact"},
    {"content": "HAProxy health checks use option httpchk GET /health to verify backend servers. Servers failing 3 consecutive checks are marked down and removed from rotation.", "tags": ["infra/networking"], "source": "test-100", "memory_type": "fact"},
    {"content": "PostgreSQL pg_stat_statements extension tracks query execution statistics. ORDER BY total_exec_time DESC shows the most expensive queries for optimization.", "tags": ["infra/databases", "tech/postgresql"], "source": "test-100", "memory_type": "fact"},

    # ── Architecture & Patterns (15) ──
    {"content": "The repository pattern abstracts data access behind an interface. Services call repository methods instead of executing SQL directly, making the data layer testable and swappable.", "tags": ["tech/patterns", "tech/architecture"], "source": "test-100", "memory_type": "fact"},
    {"content": "Event sourcing stores state changes as an append-only sequence of events rather than mutable rows. The current state is reconstructed by replaying events from the beginning.", "tags": ["tech/patterns", "tech/architecture"], "source": "test-100", "memory_type": "fact"},
    {"content": "CQRS separates read and write models. Commands modify state through the write model; queries read from a denormalized read model optimized for specific access patterns.", "tags": ["tech/patterns", "tech/architecture"], "source": "test-100", "memory_type": "fact"},
    {"content": "The saga pattern manages distributed transactions as a sequence of local transactions with compensating actions. If step 3 fails, compensating actions for steps 2 and 1 are executed.", "tags": ["tech/patterns", "tech/distributed"], "source": "test-100", "memory_type": "fact"},
    {"content": "Hexagonal architecture (ports and adapters) isolates domain logic from external concerns. The domain defines port interfaces; adapters implement them for specific technologies.", "tags": ["tech/patterns", "tech/architecture"], "source": "test-100", "memory_type": "fact"},
    {"content": "The strangler fig pattern migrates legacy systems incrementally. New features are built in the new system while existing features are gradually migrated, with a routing layer directing traffic.", "tags": ["tech/patterns", "tech/architecture"], "source": "test-100", "memory_type": "fact"},
    {"content": "Bulkhead pattern isolates components so that failure in one does not cascade. Thread pools, connection pools, and separate process groups all implement bulkhead isolation.", "tags": ["tech/patterns", "tech/distributed"], "source": "test-100", "memory_type": "fact"},
    {"content": "API versioning via URL path (/v1/resource) is the simplest approach. Header-based versioning (Accept: application/vnd.api+json;version=2) is more RESTful but harder to test.", "tags": ["tech/api", "tech/architecture"], "source": "test-100", "memory_type": "fact"},
    {"content": "The outbox pattern ensures reliable event publishing by writing events to a database table in the same transaction as the state change, then a separate process publishes them.", "tags": ["tech/patterns", "tech/distributed"], "source": "test-100", "memory_type": "fact"},
    {"content": "Feature flags decouple deployment from release. They allow trunk-based development by hiding incomplete features behind runtime toggles that can be enabled per-user or per-environment.", "tags": ["tech/patterns", "workflow/deployment"], "source": "test-100", "memory_type": "fact"},
    {"content": "The sidecar pattern deploys auxiliary services alongside the main container in the same pod. Logging agents, proxy sidecars like Envoy, and config reloaders use this pattern.", "tags": ["tech/patterns", "tech/kubernetes"], "source": "test-100", "memory_type": "fact"},
    {"content": "Database sharding partitions data across multiple database instances by a shard key. Range-based sharding enables efficient range queries; hash-based sharding distributes load evenly.", "tags": ["tech/databases", "tech/architecture"], "source": "test-100", "memory_type": "fact"},
    {"content": "Blue-green deployment maintains two identical production environments. Traffic is switched from blue to green after deployment. Instant rollback is possible by switching back.", "tags": ["tech/patterns", "workflow/deployment"], "source": "test-100", "memory_type": "fact"},
    {"content": "The observer pattern notifies subscribers when state changes occur. In Python, signals libraries like blinker implement this. In JavaScript, EventEmitter and custom events serve the same purpose.", "tags": ["tech/patterns"], "source": "test-100", "memory_type": "fact"},
    {"content": "Backend-for-frontend (BFF) creates dedicated API layers for each client type (mobile, web, CLI). Each BFF aggregates and transforms data from backend services to match its client's needs.", "tags": ["tech/patterns", "tech/architecture"], "source": "test-100", "memory_type": "fact"},
]

async def main():
    async with httpx.AsyncClient(timeout=1200.0) as client:
        hdrs = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}

        init_resp = await client.post(f"{MCP_URL}/", json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}
        }, headers=hdrs)

        session_id = init_resp.headers.get("mcp-session-id")
        notify_hdrs = {**hdrs, "mcp-session-id": session_id} if session_id else hdrs
        await client.post(f"{MCP_URL}/", json={
            "jsonrpc": "2.0", "method": "notifications/initialized"
        }, headers=notify_hdrs)

        print(f"Sending {len(entries)} memories in batches of 20...")
        total_time = 0

        for batch_start in range(0, len(entries), 20):
            batch = entries[batch_start:batch_start+20]
            call_hdrs = {**hdrs, "mcp-session-id": session_id} if session_id else hdrs

            t0 = time.time()
            resp = await client.post(f"{MCP_URL}/", json={
                "jsonrpc": "2.0", "id": batch_start + 2, "method": "tools/call",
                "params": {"name": "memory_batch_add", "arguments": {"entries": batch}}
            }, headers=call_hdrs)
            elapsed = time.time() - t0
            total_time += elapsed

            data = resp.json()
            if "result" in data:
                print(f"  Batch {batch_start//20 + 1}: {len(batch)} memories in {elapsed:.1f}s")
            elif "error" in data:
                print(f"  Batch {batch_start//20 + 1}: ERROR - {data['error'].get('message', '')[:100]}")
            else:
                print(f"  Batch {batch_start//20 + 1}: unexpected response")

        print(f"\nTotal: {len(entries)} memories in {total_time:.1f}s")
        print(f"Avg: {total_time/len(entries)*1000:.0f}ms per memory")

asyncio.run(main())
