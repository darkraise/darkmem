"""Generate and load 200+ realistic test memories via the darkmem MCP/API pipeline.

Usage: python scripts/seed_test_memories.py

Inserts memories through the MemoryService (with pipeline processing) to exercise
embedding, extraction, and classification. Memories span all types and simulate
real multi-project usage by a developer.
"""

import asyncio
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MEMORIES = [
    # ========================================================================
    # DECISIONS (35)
    # ========================================================================
    ("We chose PostgreSQL with pgvector over a separate Qdrant instance because consolidating to one database simplifies ops and backup.", ["project/darkmem", "project/decisions"], "decision"),
    ("Decided to use FastAPI instead of Flask for the backend because of native async support and automatic OpenAPI generation.", ["project/darkmem", "project/decisions"], "decision"),
    ("Went with Tree-sitter for code parsing over language-specific AST parsers because it supports 30+ languages with a single interface.", ["project/darkmem", "project/decisions"], "decision"),
    ("Chose the Leiden algorithm for community detection over Louvain because it guarantees well-connected communities.", ["project/darkmem", "project/decisions"], "decision"),
    ("Selected nomic-embed-text as the default embedding model — good balance of quality and speed for local inference.", ["project/darkmem", "project/decisions"], "decision"),
    ("Decided to implement MRO with language-specific strategies (C3 for Python, leftmost-base for C++) rather than a one-size-fits-all approach.", ["project/darkmem", "project/decisions"], "decision"),
    ("Chose RRF (Reciprocal Rank Fusion) over learned fusion for hybrid search because it needs no training data and works well out of the box.", ["project/darkmem", "project/decisions"], "decision"),
    ("Used SQLAlchemy async with asyncpg driver instead of raw SQL for the ORM layer — type safety and migration support outweigh the minor performance cost.", ["project/darkmem", "project/decisions"], "decision"),
    ("Decided against using Redis for caching — the system is single-node and PostgreSQL connection pooling is sufficient.", ["project/darkmem", "project/decisions"], "decision"),
    ("Chose Alembic for migrations over raw SQL files to get automatic diff generation and revision dependency tracking.", ["project/darkmem", "project/decisions"], "decision"),
    ("We picked TanStack Router for the frontend over React Router because of its type-safe route definitions and built-in search params handling.", ["project/darkmem-ui", "project/decisions"], "decision"),
    ("Selected Vite over Webpack for the frontend build — significantly faster HMR and simpler configuration.", ["project/darkmem-ui", "project/decisions"], "decision"),
    ("Decided to use Tailwind CSS instead of styled-components for consistent utility-first styling.", ["project/darkmem-ui", "project/decisions"], "decision"),
    ("Chose MCP (Model Context Protocol) over a custom REST tool interface for AI agent integration because MCP is becoming the industry standard.", ["project/darkmem", "project/decisions"], "decision"),
    ("Went with temporal knowledge triples (valid_from/valid_to) instead of simple entity-relation pairs to support time-scoped queries.", ["project/darkmem", "project/decisions"], "decision"),
    ("Decided to consolidate Neo4j + Qdrant + PostgreSQL into pgvector-only architecture to reduce operational complexity from 3 databases to 1.", ["project/darkmem", "project/decisions", "project/architecture"], "decision"),
    ("Selected the suffix index approach for import resolution — O(1) lookups instead of iterating path sets.", ["project/darkmem", "project/decisions"], "decision"),
    ("Chose to run LLM classification as opt-in alongside regex classification to allow A/B comparison before committing.", ["project/darkmem", "project/decisions"], "decision"),
    ("For the homelab, decided on Proxmox over ESXi because of better LXC support and no licensing costs.", ["project/homelab", "project/decisions"], "decision"),
    ("Chose Nginx Proxy Manager over Traefik for reverse proxy — simpler UI for managing SSL certs and routing rules.", ["project/homelab", "project/decisions"], "decision"),
    ("Picked Grafana + Loki for observability over the ELK stack — much lower memory footprint for a homelab.", ["project/homelab", "project/decisions"], "decision"),
    ("Went with Docker Compose over Kubernetes for homelab services — K8s is overkill for 15 containers.", ["project/homelab", "project/decisions"], "decision"),
    ("Selected WireGuard over OpenVPN for the VPN tunnel — faster, simpler config, lower overhead.", ["project/homelab", "project/decisions", "infra/networking"], "decision"),
    ("Decided to use Immich over PhotoPrism for photo management — better mobile app and face recognition.", ["project/homelab", "project/decisions"], "decision"),
    ("Chose Qdrant for mem0's vector store because it's purpose-built for vector search with filtering.", ["project/homelab", "project/decisions", "infra/services"], "decision"),
    ("Selected Cloudflare Tunnel over port forwarding for external access — no exposed ports on the router.", ["project/homelab", "project/decisions", "infra/networking"], "decision"),
    ("Went with PostgreSQL WAL mode for the darkmem database to handle concurrent readers during indexing.", ["project/darkmem", "project/decisions"], "decision"),
    ("Decided to implement BFS over DFS for process tracing because BFS gives breadth-first execution order which matches how developers reason about call flows.", ["project/darkmem", "project/decisions"], "decision"),
    ("Chose to port MemPalace's zero-LLM memory classifier instead of building from scratch — battle-tested regex patterns for 5 memory types.", ["project/darkmem", "project/decisions"], "decision"),
    ("Selected pydantic-settings for configuration management — .env file support with type validation out of the box.", ["project/darkmem", "project/decisions"], "decision"),
    ("Decided to use jsonb_to_recordset for batch SQL inserts instead of individual INSERT statements — 10-50x faster for bulk operations.", ["project/darkmem", "project/decisions"], "decision"),
    ("Went with bcrypt for password hashing over argon2 — wider library support and sufficient security for our use case.", ["project/darkmem", "project/decisions"], "decision"),
    ("Chose to implement the reranker via LLM chat scoring instead of a dedicated cross-encoder model — simpler deployment, uses existing Ollama infrastructure.", ["project/darkmem", "project/decisions"], "decision"),
    ("Selected igraph over networkx for graph algorithms — C-backed, 10-100x faster for community detection on large graphs.", ["project/darkmem", "project/decisions"], "decision"),
    ("Decided to use HNSW indexes over IVFFlat for pgvector — better recall without needing periodic rebuilds.", ["project/darkmem", "project/decisions"], "decision"),

    # ========================================================================
    # PREFERENCES (25)
    # ========================================================================
    ("I prefer dark mode in all editors and terminals.", ["user/preferences"], "preference"),
    ("Always use conventional commits: feat|fix|docs|style|refactor|test|chore|perf with scope.", ["user/preferences", "workflow/processes"], "preference"),
    ("Never add comments to code I didn't change in a PR.", ["user/preferences", "feedback/style"], "preference"),
    ("I prefer TypeScript over JavaScript for all new frontend code.", ["user/preferences", "project/tech-stack"], "preference"),
    ("Always use async/await instead of .then() chains.", ["user/preferences", "feedback/style"], "preference"),
    ("Prefer Docker Compose for local development, Kubernetes only for production clusters.", ["user/preferences", "workflow/processes"], "preference"),
    ("I use Neovim as my primary editor with LazyVim config.", ["user/preferences", "workflow/tooling"], "preference"),
    ("Never mock the database in integration tests — use a real test database with transaction rollback.", ["user/preferences", "feedback/behavior"], "preference"),
    ("I prefer Python type hints on all function signatures.", ["user/preferences", "feedback/style"], "preference"),
    ("Always use rg (ripgrep) instead of grep, and fd instead of find.", ["user/preferences", "workflow/tooling"], "preference"),
    ("Prefer single bundled PRs for refactors rather than splitting into many small ones.", ["user/preferences", "workflow/processes"], "preference"),
    ("I like concise commit messages — one line, 50 chars max, imperative mood.", ["user/preferences", "workflow/processes"], "preference"),
    ("Never use force push on shared branches without team agreement.", ["user/preferences", "workflow/processes"], "preference"),
    ("Prefer PostgreSQL over MySQL/MariaDB for all new projects.", ["user/preferences", "project/tech-stack"], "preference"),
    ("I always run linters before committing — ESLint for TS, ruff for Python.", ["user/preferences", "workflow/processes"], "preference"),
    ("Prefer explicit error handling over silent fallbacks.", ["user/preferences", "feedback/style"], "preference"),
    ("I use tmux with a custom status bar for terminal multiplexing.", ["user/preferences", "workflow/tooling"], "preference"),
    ("Always pin Docker image versions in production compose files.", ["user/preferences", "workflow/processes"], "preference"),
    ("Prefer functional React components with hooks over class components.", ["user/preferences", "feedback/style"], "preference"),
    ("I like keeping services on separate LXC containers in the homelab rather than one big Docker host.", ["user/preferences", "project/homelab"], "preference"),
    ("Never commit .env files or credentials — use examples and vault references.", ["user/preferences", "workflow/processes"], "preference"),
    ("Prefer early returns over deeply nested if/else blocks.", ["user/preferences", "feedback/style"], "preference"),
    ("I use bat instead of cat for syntax-highlighted file viewing.", ["user/preferences", "workflow/tooling"], "preference"),
    ("Always use timezone-aware datetimes — never naive datetime objects.", ["user/preferences", "feedback/style"], "preference"),
    ("Prefer pnpm over npm for faster installs and disk space savings.", ["user/preferences", "workflow/tooling"], "preference"),

    # ========================================================================
    # ARCHITECTURE (25)
    # ========================================================================
    ("darkmem architecture: FastAPI backend + PostgreSQL (pgvector) + Ollama for local LLM. Frontend is React + TanStack Router + Vite.", ["project/darkmem", "project/architecture"], "architecture"),
    ("The code indexing pipeline has 13 phases: file discovery, parsing, structure, imports, named bindings, call tracing, heritage MRO, cross-file binding, community detection, process detection, validation, embeddings, enrichment.", ["project/darkmem", "project/architecture"], "architecture"),
    ("Memory processing pipeline: embed content via Ollama → extract entities/relationships via LLM → upsert vector + graph → classify via regex.", ["project/darkmem", "project/architecture"], "architecture"),
    ("Three search modalities: semantic (pgvector cosine), keyword (tsvector BM25), and hybrid (RRF fusion of both).", ["project/darkmem", "project/architecture"], "architecture"),
    ("Code graph is stored in PostgreSQL tables: code_graph_nodes (symbols, files, communities, processes) and code_edges (calls, extends, implements, etc.).", ["project/darkmem", "project/architecture"], "architecture"),
    ("Entity extraction uses LLM (qwen3:8b) to identify people, services, projects, technologies, and their relationships from memory content.", ["project/darkmem", "project/architecture"], "architecture"),
    ("Knowledge triples store temporal facts as subject-predicate-object with valid_from/valid_to dates for time-scoped queries.", ["project/darkmem", "project/architecture"], "architecture"),
    ("MCP server exposes memory_add, memory_search, memory_update, memory_delete plus code_search, code_symbol, code_blast_radius tools.", ["project/darkmem", "project/architecture"], "architecture"),
    ("Homelab runs on Proxmox with LXC containers: each service gets its own container for isolation. Network is 192.168.0.0/24.", ["project/homelab", "project/architecture", "infra/networking"], "architecture"),
    ("Homelab monitoring stack: Grafana on .195:3000, Loki on .195:3100 for logs, Prometheus on .195:9090 for metrics.", ["project/homelab", "project/architecture", "infra/services"], "architecture"),
    ("NPM (Nginx Proxy Manager) on 192.168.0.100 handles all reverse proxy routing and SSL termination for homelab services.", ["project/homelab", "project/architecture", "infra/networking"], "architecture"),
    ("mem0 MCP server runs on 192.168.0.197:8001 — semantic memory via Qdrant backend. Memora on same host at port 8080 — structured memory with tags.", ["project/homelab", "project/architecture", "infra/services"], "architecture"),
    ("Ollama runs on the main workstation, not in a container — needs GPU access for inference.", ["project/homelab", "project/architecture", "infra/services"], "architecture"),
    ("darkmem's hybrid search works by running pgvector cosine similarity and PostgreSQL tsvector BM25 in parallel, then fusing results via Reciprocal Rank Fusion with k=60.", ["project/darkmem", "project/architecture"], "architecture"),
    ("The suffix index builds a HashMap of every file path suffix at pipeline start for O(1) import resolution.", ["project/darkmem", "project/architecture"], "architecture"),
    ("Call resolution uses a 6-stage confidence cascade: type-env member (0.92) → receiver (0.80) → local (0.95) → named imports (0.90) → wildcard (0.85) → global (0.50).", ["project/darkmem", "project/architecture"], "architecture"),
    ("C3 MRO linearization is used for Python classes, leftmost-base for C++, implements-split for Java/C#, qualified-syntax for Rust.", ["project/darkmem", "project/architecture"], "architecture"),
    ("Process tracing finds entry points via scoring formula: (callees/(callers+1)) × export × name × framework multipliers, then BFS with max_branching=4.", ["project/darkmem", "project/architecture"], "architecture"),
    ("Community detection runs Leiden algorithm via igraph — large graphs (>10K nodes) use resolution=2.0, max 3 iterations, 60s timeout.", ["project/darkmem", "project/architecture"], "architecture"),
    ("Vector clustering uses sklearn DBSCAN for density-based clusters and igraph Louvain for modularity-based communities.", ["project/darkmem", "project/architecture"], "architecture"),
    ("AAAK dialect compression encodes conversation context into ~30x compressed format: ZID:ENTITIES|topics|key_quote|EMOTIONS|FLAGS.", ["project/darkmem", "project/architecture"], "architecture"),
    ("Memory classifier is zero-LLM: ~100 regex patterns across 5 types (decision, preference, milestone, problem, emotional) with sentiment disambiguation.", ["project/darkmem", "project/architecture"], "architecture"),
    ("The frontend uses React Query (TanStack Query) for server state management with optimistic updates for memory CRUD.", ["project/darkmem-ui", "project/architecture"], "architecture"),
    ("WebSocket events broadcast pipeline status, indexing progress, and repo sync events to the frontend in real-time.", ["project/darkmem", "project/architecture"], "architecture"),
    ("Authentication uses JWT tokens with bcrypt password hashing. API keys use HMAC for stateless verification.", ["project/darkmem", "project/architecture"], "architecture"),

    # ========================================================================
    # DEBUG / PROBLEMS (30)
    # ========================================================================
    ("Bug: pgvector HNSW index creation fails if the vector extension isn't loaded. Fix: always run CREATE EXTENSION IF NOT EXISTS vector before table creation.", ["project/darkmem", "debug/root-cause"], "debug"),
    ("Pydantic Settings with extra='forbid' crashes on startup when .env has stale keys from the old Neo4j/Qdrant config. Fix: changed to extra='ignore'.", ["project/darkmem", "debug/root-cause"], "debug"),
    ("The hand-rolled DBSCAN in vector.py was O(n²) because it built a full similarity matrix. Replaced with sklearn DBSCAN which uses BallTree for O(n log n).", ["project/darkmem", "debug/root-cause"], "debug"),
    ("Process tracer was using list.pop(0) for BFS which is O(n) per pop. Switched to collections.deque.popleft() for O(1).", ["project/darkmem", "debug/root-cause"], "debug"),
    ("SymbolTable.lookup_by_owner wasn't actually filtering by the requested owner — it collected all methods with ANY owner_id. Fixed by adding an owner_name index.", ["project/darkmem", "debug/root-cause"], "debug"),
    ("The reranker was using embedding vector dimensions as relevance scores, which is meaningless. Rewrote to use LLM chat scoring with 0-10 scale.", ["project/darkmem", "debug/root-cause"], "debug"),
    ("Alembic migration fails with 'Can't locate revision' when old migration files are deleted but alembic_version still references them. Fix: DROP TABLE alembic_version and re-run.", ["project/darkmem", "debug/workaround"], "debug"),
    ("Tree-sitter parser segfaults on files larger than 500KB. Added MAX_FILE_SIZE=500_000 filter in phase 01.", ["project/darkmem", "debug/workaround"], "debug"),
    ("Leiden community detection hangs on pathological graphs. Added 60-second asyncio.wait_for timeout with single-community fallback.", ["project/darkmem", "debug/workaround"], "debug"),
    ("Ollama embedding endpoint returns 404 if the model isn't pulled. Need to run 'ollama pull nomic-embed-text' before starting.", ["project/darkmem", "debug/gotcha"], "debug"),
    ("PostgreSQL tsvector triggers don't fire on bulk INSERT via COPY. Need to run UPDATE ... SET search_vector = ... after bulk loads.", ["project/darkmem", "debug/gotcha"], "debug"),
    ("Cross-file binding phase 08 was running unnecessarily when resolution rate was already >97%. Added skip threshold at 3%.", ["project/darkmem", "debug/root-cause"], "debug"),
    ("Promtail OOM when Loki was down — unbounded log buffer. Fix: added client.backoff config and limits.readline_rate_enabled.", ["project/homelab", "debug/root-cause", "infra/services"], "debug"),
    ("Grafana dashboard load time was 30+ seconds. Root cause: default SQLite backend. Switched to filesystem store and it dropped to 2s.", ["project/homelab", "debug/root-cause", "infra/services"], "debug"),
    ("Immich needs Valkey (Redis fork) running before it starts, but Docker Compose depends_on doesn't wait for readiness. Added healthcheck with pg_isready equivalent.", ["project/homelab", "debug/gotcha", "infra/services"], "debug"),
    ("Cloudflare Tunnel randomly drops connections after 24h. Root cause: token expiry. Fix: use the named tunnel with cert-based auth instead of quick tunnel.", ["project/homelab", "debug/root-cause", "infra/networking"], "debug"),
    ("NPM container runs out of memory when renewing 20+ SSL certs simultaneously. Fix: set deploy.resources.limits.memory to 512m and stagger renewals.", ["project/homelab", "debug/workaround", "infra/services"], "debug"),
    ("Docker overlay2 storage driver fills up /var/lib/docker on small LXC root disks. Fix: mount a separate ZFS dataset for /var/lib/docker.", ["project/homelab", "debug/workaround", "infra/services"], "debug"),
    ("asyncpg connection pool exhaustion when running indexing pipeline + API requests concurrently. Fix: increased pool_size from 5 to 20.", ["project/darkmem", "debug/root-cause"], "debug"),
    ("JWT tokens were expiring during long-running MCP sessions. Increased token lifetime from 1h to 24h for MCP clients.", ["project/darkmem", "debug/workaround"], "debug"),
    ("Named binding propagation was single-hop — couldn't resolve TypeScript barrel re-exports. Extended to 5-hop chain walk with cycle detection.", ["project/darkmem", "debug/root-cause"], "debug"),
    ("Heritage resolver's recursive CTE wasn't respecting MRO ordering for Python diamond inheritance. Replaced with Python-side C3 linearization.", ["project/darkmem", "debug/root-cause"], "debug"),
    ("Memory search returned low-quality results for keyword-heavy queries. Root cause: vector-only search misses exact string matches. Fix: added BM25 + RRF hybrid.", ["project/darkmem", "debug/root-cause"], "debug"),
    ("Frontend hot-reload crashes when changing route files. Root cause: TanStack Router codegen race condition. Fix: add --poll flag to vite dev.", ["project/darkmem-ui", "debug/workaround"], "debug"),
    ("LXC container networking breaks after Proxmox kernel update. Fix: restart pve-firewall and reload bridge config.", ["project/homelab", "debug/workaround", "infra/networking"], "debug"),
    ("Loki rejects logs larger than 256KB. Fix: configure max_line_size in Promtail and truncate before sending.", ["project/homelab", "debug/gotcha", "infra/services"], "debug"),
    ("pgvector HNSW filtered queries (WHERE repo_id = X) return fewer results than LIMIT. Fix: enable hnsw.iterative_scan = relaxed_order (pgvector 0.8.0+).", ["project/darkmem", "debug/root-cause"], "debug"),
    ("Ollama runs out of VRAM when loading two models simultaneously. Fix: set OLLAMA_MAX_LOADED_MODELS=1.", ["project/darkmem", "debug/workaround", "infra/services"], "debug"),
    ("WebSocket connections drop silently after 60s idle. Root cause: Nginx proxy timeout. Fix: set proxy_read_timeout 3600s.", ["project/darkmem", "debug/root-cause", "infra/networking"], "debug"),
    ("Python 3.14 broke some tree-sitter bindings. Pinned tree-sitter>=0.23.0 which has the fix.", ["project/darkmem", "debug/workaround"], "debug"),

    # ========================================================================
    # FACTS (30)
    # ========================================================================
    ("darkmem backend runs on Python 3.12+ with FastAPI, SQLAlchemy 2.0 async, and pgvector 0.3.6+.", ["project/darkmem", "project/tech-stack"], "fact"),
    ("darkmem frontend uses React 18, TanStack Router, TanStack Query, Tailwind CSS, and Vite.", ["project/darkmem-ui", "project/tech-stack"], "fact"),
    ("pgvector latest version is 0.8.2. Docker image: pgvector/pgvector:0.8.2-pg17.", ["project/darkmem", "project/tech-stack"], "fact"),
    ("darkmem's embedding dimensions are 1024 (qwen3-embedding:0.6b model).", ["project/darkmem", "project/tech-stack"], "fact"),
    ("LLM inference uses llama3.2:3b via local Ollama for extraction, reasoning, and summarization.", ["project/darkmem", "project/tech-stack", "infra/services"], "fact"),
    ("PostgreSQL database is on port 5433 (Docker), accessible at localhost:5433 from the host.", ["project/darkmem", "infra/services"], "fact"),
    ("darkmem API runs on port 8000, frontend dev server on port 5173 (Vite default).", ["project/darkmem", "infra/services"], "fact"),
    ("The homelab network is 192.168.0.0/24 with Proxmox host at 192.168.0.1.", ["project/homelab", "infra/networking"], "fact"),
    ("NPM runs on 192.168.0.100, Grafana/Loki/Prometheus on 192.168.0.195, mem0/memora on 192.168.0.197.", ["project/homelab", "infra/services", "infra/networking"], "fact"),
    ("darkmem supports 32+ programming languages via Tree-sitter grammars.", ["project/darkmem", "project/tech-stack"], "fact"),
    ("The code indexing pipeline supports incremental indexing via git diff between commits.", ["project/darkmem"], "fact"),
    ("HNSW index parameters: m=16, ef_construction=128, ef_search=100 (set at connection level).", ["project/darkmem", "project/tech-stack"], "fact"),
    ("Memory classification has 5 types: decision, preference, milestone, problem, emotional.", ["project/darkmem"], "fact"),
    ("Call resolution confidence tiers: same-file 0.95, import-scoped 0.90, wildcard 0.85, interface-dispatch 0.70, global 0.50.", ["project/darkmem"], "fact"),
    ("The entity detector requires 3+ occurrences of a capitalized word to consider it a candidate.", ["project/darkmem"], "fact"),
    ("Process tracing caps at max_branching=4, min_edge_confidence=0.5, max_depth=10-20.", ["project/darkmem"], "fact"),
    ("RRF hybrid search uses k=60 constant, semantic_weight default 0.7, fetches 3x limit from each source.", ["project/darkmem"], "fact"),
    ("Proxmox version 8.x running on bare metal with ZFS storage pool.", ["project/homelab", "infra/services"], "fact"),
    ("WireGuard VPN tunnel connects homelab to a Hetzner VPS for external proxy routing.", ["project/homelab", "infra/networking"], "fact"),
    ("Immich runs on 192.168.0.150 with external storage mounted via NFS from the NAS.", ["project/homelab", "infra/services"], "fact"),
    ("Jellyfin media server on 192.168.0.110:8096, proxied through NPM.", ["project/homelab", "infra/services"], "fact"),
    ("The SearXNG meta-search instance on 192.168.0.195:8080 aggregates Google, Bing, and Brave results.", ["project/homelab", "infra/services"], "fact"),
    ("Context7 MCP server on 192.168.0.195:3101 provides library documentation lookup.", ["project/homelab", "infra/services"], "fact"),
    ("Playwright MCP server on 192.168.0.195:3102 for browser automation and visual testing.", ["project/homelab", "infra/services"], "fact"),
    ("darkmem's consolidated migration is revision 0001 — single file, creates the complete schema.", ["project/darkmem"], "fact"),
    ("Python igraph is used for both code community detection (Leiden) and vector clustering (Louvain).", ["project/darkmem", "project/tech-stack"], "fact"),
    ("scikit-learn is used for DBSCAN density-based clustering of memory vectors.", ["project/darkmem", "project/tech-stack"], "fact"),
    ("The SymbolTable has three indexes: _file_index (file→name→entries), _global_index (name→entries), _owner_index (owner→name→entries).", ["project/darkmem"], "fact"),
    ("darkmem's MCP server uses FastMCP with stateless_http transport at the /mcp/ path.", ["project/darkmem"], "fact"),
    ("All darkmem datetime columns use timezone-aware timestamps (DateTime(timezone=True)).", ["project/darkmem"], "fact"),

    # ========================================================================
    # WORKFLOW (25)
    # ========================================================================
    ("Dev workflow: start Postgres container → run alembic upgrade head → uvicorn with --reload → npm run dev for frontend.", ["project/darkmem", "workflow/processes"], "workflow"),
    ("To index a repo: POST /api/v1/repos with name + url/local_path → trigger sync → pipeline runs automatically.", ["project/darkmem", "workflow/processes"], "workflow"),
    ("Deployment: build Docker image → push to registry → docker compose pull && docker compose up -d on the target host.", ["project/darkmem", "workflow/processes"], "workflow"),
    ("Homelab service deployment: create LXC → install Docker → docker compose up -d → configure NPM reverse proxy → add Grafana dashboard.", ["project/homelab", "workflow/processes"], "workflow"),
    ("Database backup: pg_dump to NFS share nightly via cron. Retention: 7 daily + 4 weekly.", ["project/homelab", "workflow/processes"], "workflow"),
    ("When adding a new MCP tool: define the function in server.py with @mcp.tool decorator → add to agent_instructions prompt → test via MCP inspector.", ["project/darkmem", "workflow/processes"], "workflow"),
    ("PR workflow: create feature branch → implement → self-review → squash merge to main.", ["workflow/processes"], "workflow"),
    ("To add a new Tree-sitter language: pip install tree-sitter-<lang> → add to pyproject.toml → parser auto-discovers it.", ["project/darkmem", "workflow/processes"], "workflow"),
    ("Monitoring workflow: check Grafana dashboards → investigate Loki logs if alerts fire → fix → add runbook entry.", ["project/homelab", "workflow/processes"], "workflow"),
    ("To create a new migration: alembic revision --autogenerate -m 'description' → review generated SQL → alembic upgrade head.", ["project/darkmem", "workflow/processes"], "workflow"),
    ("LXC container creation: pct create <id> <template> --hostname <name> --net0 ... --rootfs ... → start → configure inside.", ["project/homelab", "workflow/processes"], "workflow"),
    ("Ollama model management: ollama pull <model> → ollama list to verify → update config.py if changing default model.", ["project/darkmem", "workflow/processes"], "workflow"),
    ("To test MCP tools locally: use the MCP inspector at http://localhost:8000/mcp/ or connect via Claude Desktop.", ["project/darkmem", "workflow/processes"], "workflow"),
    ("Frontend component pattern: create component file → export from index → add to route page → connect to API hook.", ["project/darkmem-ui", "workflow/processes"], "workflow"),
    ("SSL cert management: NPM auto-renews via Let's Encrypt. Check NPM dashboard if a cert fails to renew.", ["project/homelab", "workflow/processes"], "workflow"),
    ("To debug pipeline issues: check WebSocket events in the frontend → check uvicorn logs → check specific phase timing.", ["project/darkmem", "workflow/processes"], "workflow"),
    ("Git branching: main for releases, feat/ for features, fix/ for bugfixes. Squash merge everything.", ["workflow/processes"], "workflow"),
    ("When changing embedding dimensions: update config.py → update migration vector(N) → reset DB → re-index.", ["project/darkmem", "workflow/processes"], "workflow"),
    ("ZFS snapshot schedule: hourly for 24h, daily for 7d, weekly for 4w. Managed by zfs-auto-snapshot.", ["project/homelab", "workflow/processes"], "workflow"),
    ("To add a new API endpoint: create route function → add to router → register in main.py → add OpenAPI docs.", ["project/darkmem", "workflow/processes"], "workflow"),
    ("Proxmox cluster backup: vzdump runs nightly to NFS storage. Retention: 3 backups per container.", ["project/homelab", "workflow/processes"], "workflow"),
    ("darkmem code review checklist: check algorithm correctness → verify edge cases → confirm no SQL injection → run tests.", ["project/darkmem", "workflow/processes"], "workflow"),
    ("Container resource limits: most services get 512MB RAM. Ollama and PostgreSQL get 4GB each.", ["project/homelab", "workflow/processes", "infra/services"], "workflow"),
    ("When updating darkmem: git pull → pip install -e . → alembic upgrade head → restart uvicorn.", ["project/darkmem", "workflow/processes"], "workflow"),
    ("Log aggregation: all containers send logs to Promtail via Docker logging driver → Promtail forwards to Loki.", ["project/homelab", "workflow/processes", "infra/services"], "workflow"),

    # ========================================================================
    # SESSION SUMMARIES (15)
    # ========================================================================
    ("Session 2026-04-07: Reviewed all darkmem algorithms, identified 4 performance bottlenecks. Implemented fixes: sklearn DBSCAN, igraph Louvain, deque BFS, SymbolTable owner index.", ["session/summary", "project/darkmem"], "session"),
    ("Session 2026-04-08: Cross-project comparison vs GitNexus, MemPalace, mem0, Memora, supermemory. Identified 5 gaps: suffix index, BM25 hybrid search, multi-hop bindings, call cache, process tracing limits.", ["session/summary", "project/darkmem"], "session"),
    ("Session 2026-04-08: Implemented 5 work streams — C3 MRO, suffix index, call cache, LLM enrichment (opt-in), hybrid search with RRF + reranker. All 87 unit tests pass.", ["session/summary", "project/darkmem"], "session"),
    ("Session 2026-04-08: Code review found 1 critical (Settings extra=forbid) and 3 important issues (Louvain O(n²) loop, reranker scoring, __import__). All fixed.", ["session/summary", "project/darkmem"], "session"),
    ("Session 2026-04-08: Consolidated 8 migrations into single 0001_initial_schema.py. Updated pgvector to 0.8.2, HNSW params m=16 ef_construction=128, enabled iterative_scan.", ["session/summary", "project/darkmem"], "session"),
    ("Session 2026-04-08: Changed default LLM config to llama3.2:3b + qwen3-embedding:0.6b (1024 dims). Updated migration vector columns to 1024.", ["session/summary", "project/darkmem"], "session"),
    ("Session 2026-03-26: Initial darkmem project setup — FastAPI + PostgreSQL + SQLAlchemy async. Created core schema for memories, tags, API keys.", ["session/summary", "project/darkmem"], "session"),
    ("Session 2026-04-03: Added chat functionality — conversations and messages tables, chat API endpoints, basic RAG with memory context.", ["session/summary", "project/darkmem"], "session"),
    ("Session 2026-04-05: Added code indexing — repositories, code_files, code_symbols tables. Tree-sitter parser for 30+ languages.", ["session/summary", "project/darkmem"], "session"),
    ("Session 2026-04-05: Revamped system prompt profiles — simplified schema, added purpose-based lookup, seeder for 6 default profiles.", ["session/summary", "project/darkmem"], "session"),
    ("Session 2026-04-06: Built frontend with React + TanStack Router — pages for memories, chat, code graph, knowledge graph, vector space.", ["session/summary", "project/darkmem-ui"], "session"),
    ("Session 2026-04-07: Migrated frontend to darkraise-ui component library. Replaced all raw HTML primitives with themed components.", ["session/summary", "project/darkmem-ui"], "session"),
    ("Homelab setup session: Deployed Proxmox, created LXC containers for each service, configured NPM reverse proxy, set up Grafana monitoring.", ["session/summary", "project/homelab"], "session"),
    ("Homelab networking session: Set up WireGuard tunnel to VPS, configured Cloudflare Tunnel for external access, set up SearXNG for search.", ["session/summary", "project/homelab"], "session"),
    ("mem0/memora deployment session: Deployed both on 192.168.0.197, configured Qdrant for mem0, set up memora with SQLite + sentence-transformers.", ["session/summary", "project/homelab"], "session"),

    # ========================================================================
    # PEOPLE & CONTEXT (15)
    # ========================================================================
    ("User is a developer who manages a homelab on Proxmox and builds AI-integrated tools.", ["user/profile"], "fact"),
    ("User's primary languages: Python (backend), TypeScript (frontend), with exposure to Go, Rust, C#.", ["user/profile", "project/tech-stack"], "fact"),
    ("User prefers local-first AI — Ollama for inference, no external API dependencies for core functionality.", ["user/preferences", "user/profile"], "preference"),
    ("User runs Windows 11 Pro as the primary workstation with WSL2 for development.", ["user/profile", "infra/environment"], "fact"),
    ("Git user is 'Darkraise' — this is the handle across GitHub and homelab services.", ["user/profile"], "fact"),
    ("darkmem is a personal project — single developer, no team. Optimize for developer velocity over process.", ["project/darkmem", "project/context"], "fact"),
    ("The homelab serves dual purposes: personal infrastructure (media, photos, VPN) and development platform (CI, monitoring, AI services).", ["project/homelab", "project/context"], "fact"),
    ("darkmem's target users are AI coding assistants (Claude, GPT) that need persistent memory across sessions.", ["project/darkmem", "project/context"], "fact"),
    ("The architecture overhaul branch consolidates from 3 databases (PostgreSQL + Neo4j + Qdrant) to PostgreSQL-only with pgvector.", ["project/darkmem", "project/context"], "fact"),
    ("darkmem is inspired by 5 projects: GitNexus (code indexing), MemPalace (memory classification), mem0 (AI memory), Memora (structured memory), supermemory (knowledge management).", ["project/darkmem", "project/context"], "fact"),
    ("The MCP integration allows Claude Code and other AI assistants to store and retrieve memories during coding sessions.", ["project/darkmem", "project/context"], "fact"),
    ("Merge freeze happens on the homelab on Thursdays when services are backed up and Proxmox snapshots are verified.", ["project/homelab", "project/context"], "fact"),
    ("The darkraise-ui package is a shared component library used by darkmem frontend and other personal projects.", ["project/darkmem-ui", "project/context"], "fact"),
    ("darkmem repo is at D:\\Repositories\\_local_projects\\darkmem on the local workstation.", ["project/darkmem", "infra/environment"], "fact"),
    ("All Claude Code sessions use dual memory: mem0 for semantic search and memora for tagged/structured search.", ["workflow/tooling", "infra/services"], "fact"),
]


async def main():
    from app.config import settings
    from app.database import async_session_factory
    from app.schemas.memory import MemoryCreate
    from app.services.llm import LLMOrchestrator
    from app.services.memory import MemoryService
    from app.services.pipeline import ProcessingPipeline

    llm_config = {
        "embedding": settings.llm_embedding,
        "extraction": settings.llm_extraction,
        "reasoning": settings.llm_reasoning,
        "summarization": settings.llm_summarization,
    }
    llm = LLMOrchestrator(llm_config)

    pipeline = ProcessingPipeline(llm, async_session_factory, settings.embedding_dimensions)

    total = len(MEMORIES)
    logger.info("Loading %d test memories with full pipeline processing...", total)

    succeeded = 0
    failed = 0
    start = time.time()

    for i, (content, tags, memory_type) in enumerate(MEMORIES):
        try:
            async with async_session_factory() as session:
                service = MemoryService(session, pipeline=pipeline)
                data = MemoryCreate(
                    content=content,
                    tags=tags,
                    source="seed-script",
                    source_agent="test-seed",
                    memory_type=memory_type,
                )
                memory = await service.create_memory(data, api_key_id=None)
                await session.commit()
                succeeded += 1

                if (i + 1) % 10 == 0:
                    elapsed = time.time() - start
                    rate = (i + 1) / elapsed
                    logger.info(
                        "Progress: %d/%d (%.1f/s) — %d ok, %d failed",
                        i + 1, total, rate, succeeded, failed,
                    )
        except Exception as e:
            failed += 1
            logger.warning("Failed to create memory %d: %s", i + 1, e)

    elapsed = time.time() - start
    logger.info(
        "Done: %d/%d memories created in %.1fs (%.1f/s). %d failed.",
        succeeded, total, elapsed, succeeded / max(elapsed, 0.1), failed,
    )


if __name__ == "__main__":
    asyncio.run(main())
