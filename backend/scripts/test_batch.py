import asyncio, json, time, httpx

MCP_URL = "http://localhost:8000/mcp"

entries = [
    {"content": "PostgreSQL HNSW indexes use a hierarchical navigable small world graph structure. The ef_construction parameter controls build-time accuracy vs speed tradeoff. Higher values (128-256) produce better recall but slower index builds.", "tags": ["tech/databases", "tech/pgvector"], "source": "test-batch", "memory_type": "fact"},
    {"content": "The Leiden algorithm improves on Louvain by guaranteeing that all communities are connected. It uses a refined local moving step that prevents poorly connected communities from forming during optimization.", "tags": ["tech/algorithms", "tech/graph"], "source": "test-batch", "memory_type": "fact"},
    {"content": "We decided to use pgvector instead of Qdrant for vector storage because it simplifies our infrastructure. One database handles both relational and vector data, reducing operational overhead.", "tags": ["project/decisions", "tech/pgvector"], "source": "test-batch", "memory_type": "decision"},
    {"content": "C3 linearization is Python MRO algorithm. It guarantees monotonicity and preserves local precedence ordering. When the hierarchy is inconsistent, C3 raises a TypeError rather than producing an ambiguous order.", "tags": ["tech/algorithms", "tech/python"], "source": "test-batch", "memory_type": "fact"},
    {"content": "Reciprocal Rank Fusion combines multiple ranked result lists using the formula score = sum(1/(k+rank_i)). The constant k (typically 60) dampens the influence of rank position, making RRF robust to score distribution differences.", "tags": ["tech/algorithms", "tech/search"], "source": "test-batch", "memory_type": "fact"},
    {"content": "When deploying Ollama behind a reverse proxy, set OLLAMA_NUM_PARALLEL to control concurrent request handling. Default is 1, which serializes all inference. Setting it to 4 allows 4 simultaneous requests but increases VRAM usage.", "tags": ["infra/ollama", "infra/deployment"], "source": "test-batch", "memory_type": "fact"},
    {"content": "SQLAlchemy AsyncSession is NOT safe for concurrent use from multiple coroutines. Each coroutine that needs database access should get its own session, or operations should be serialized within a single session.", "tags": ["tech/sqlalchemy", "debug/gotcha"], "source": "test-batch", "memory_type": "fact"},
    {"content": "The enrichment worker processes code symbols by generating LLM summaries. It runs as a background task with configurable batch_size and interval. Priority is based on the symbol enrichment_priority field.", "tags": ["project/darkmem", "tech/architecture"], "source": "test-batch", "memory_type": "fact"},
    {"content": "BM25 full-text search in PostgreSQL uses tsvector columns with GIN indexes. The ts_rank function scores matches based on term frequency. Combining BM25 with vector search via RRF provides better recall than either method alone.", "tags": ["tech/search", "tech/postgresql"], "source": "test-batch", "memory_type": "fact"},
    {"content": "Tree-sitter grammars parse source code into concrete syntax trees. The darkmem code pipeline uses tree-sitter for 32+ languages to extract symbols, calls, heritage relationships, and module structure.", "tags": ["project/darkmem", "tech/parsing"], "source": "test-batch", "memory_type": "fact"},
    {"content": "Process tracing identifies entry points in a codebase by scoring functions based on their caller/callee ratio, export status, name patterns (main, run, start), and framework decorators (@app, @router).", "tags": ["project/darkmem", "tech/algorithms"], "source": "test-batch", "memory_type": "fact"},
    {"content": "The memory palace metaphor organizes memories into wings (broad domains), rooms (specific topics), and halls (connecting pathways). Classification maps incoming memories to this spatial structure for intuitive retrieval.", "tags": ["project/darkmem", "tech/architecture"], "source": "test-batch", "memory_type": "fact"},
    {"content": "JWT tokens should include a jti claim to support revocation. A token blocklist table stores revoked jti values until they expire, preventing replay attacks without invalidating all tokens.", "tags": ["tech/security", "tech/jwt"], "source": "test-batch", "memory_type": "fact"},
    {"content": "Named binding propagation resolves import chains like from X import Y by mapping the import source to its resolved file path. Multi-hop chains require iterative resolution with cycle detection.", "tags": ["project/darkmem", "tech/algorithms"], "source": "test-batch", "memory_type": "fact"},
    {"content": "Community detection in code graphs reveals clusters of tightly coupled modules. The resolution parameter controls granularity: lower values produce fewer larger communities; higher values produce more smaller ones.", "tags": ["tech/algorithms", "tech/graph"], "source": "test-batch", "memory_type": "fact"},
    {"content": "Blast radius analysis uses a recursive CTE to walk the reverse call graph from a symbol. Each hop represents one degree of impact. Direct callers at distance 1 are highest priority for review during changes.", "tags": ["project/darkmem", "tech/algorithms"], "source": "test-batch", "memory_type": "fact"},
    {"content": "Server-Sent Events follow the format data: payload with each event terminated by double newlines. A done event signals stream completion. Error events should be formatted the same way for consistent client handling.", "tags": ["tech/web", "tech/streaming"], "source": "test-batch", "memory_type": "fact"},
    {"content": "Cosine similarity between embedding vectors ranges from -1 to 1. pgvector cosine distance operator is 1 minus similarity, so lower values mean more similar. HNSW indexes accelerate nearest-neighbor queries from O(n) to O(log n).", "tags": ["tech/pgvector", "tech/algorithms"], "source": "test-batch", "memory_type": "fact"},
    {"content": "The suffix index maps file name suffixes to full paths for O(1) import resolution. When multiple files share the same suffix like utils.py in different directories, the index returns None to signal ambiguity.", "tags": ["project/darkmem", "tech/algorithms"], "source": "test-batch", "memory_type": "fact"},
    {"content": "WebSocket connections require authentication via query parameter token since the WebSocket protocol does not support custom headers during the handshake. The token is validated on connection open.", "tags": ["tech/websocket", "tech/security"], "source": "test-batch", "memory_type": "fact"},
]

async def main():
    async with httpx.AsyncClient(timeout=600.0) as client:
        hdrs = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}

        # Initialize MCP session
        init_resp = await client.post(f"{MCP_URL}/", json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}
        }, headers=hdrs)
        session_id = init_resp.headers.get("mcp-session-id")
        print(f"Session: {session_id[:20] if session_id else 'NONE'}...")
        print(f"Init status: {init_resp.status_code}")

        # Send initialized notification
        notify_hdrs = {**hdrs, "mcp-session-id": session_id} if session_id else hdrs
        await client.post(f"{MCP_URL}/", json={
            "jsonrpc": "2.0", "method": "notifications/initialized"
        }, headers=notify_hdrs)

        # Call memory_batch_add
        print(f"\nSending batch of {len(entries)} memories...")
        t0 = time.time()
        call_hdrs = {**hdrs, "mcp-session-id": session_id} if session_id else hdrs
        resp = await client.post(f"{MCP_URL}/", json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "memory_batch_add", "arguments": {"entries": entries}}
        }, headers=call_hdrs)
        elapsed = time.time() - t0

        data = resp.json()
        if "result" in data:
            content = data["result"].get("content", [])
            if content and content[0].get("type") == "text":
                result_text = content[0]["text"]
                try:
                    parsed = json.loads(result_text)
                    print(f"\nCompleted in {elapsed:.1f}s")
                    if isinstance(parsed, dict):
                        print(f"Memories created: {len(parsed.get('memories', []))}")
                        statuses = parsed.get("pipeline_status", [])
                    elif isinstance(parsed, list):
                        print(f"Memories created: {len(parsed)}")
                        statuses = []
                    else:
                        statuses = []

                    if statuses:
                        total_entities = sum(s.get("entities_count", 0) for s in statuses)
                        total_relations = sum(s.get("relations_count", 0) for s in statuses)
                        errors = sum(1 for s in statuses if s.get("error"))
                        print(f"Pipeline: {len(statuses) - errors} ok, {errors} errors")
                        print(f"Extracted: {total_entities} entities, {total_relations} relations")
                        print(f"\nSample status: {json.dumps(statuses[0], indent=2)}")

                    print(f"\nThroughput: {len(entries)/elapsed:.1f} memories/sec")
                    print(f"Avg latency: {elapsed/len(entries)*1000:.0f}ms per memory")
                except json.JSONDecodeError:
                    print(f"Raw result ({elapsed:.1f}s): {result_text[:500]}")
            else:
                print(f"Result ({elapsed:.1f}s): {json.dumps(data['result'], indent=2)[:500]}")
        elif "error" in data:
            print(f"ERROR ({elapsed:.1f}s): {json.dumps(data['error'], indent=2)}")
        else:
            print(f"Unexpected ({elapsed:.1f}s): {json.dumps(data, indent=2)[:500]}")

asyncio.run(main())
