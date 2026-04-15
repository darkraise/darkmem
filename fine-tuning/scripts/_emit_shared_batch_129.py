"""One-off emitter for shared-base batch-129 — technical domain (graph databases).

Writes 50 rows to data/v2/shared/batch_129.tmp.jsonl with ids shared-06401..06450.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_129.tmp.jsonl"
ID_OFFSET = 6400

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Neo4j Community Edition hosted the small ontology; Cypher queries answered the taxonomy lookups without any APOC extension needed.", "architecture", "technical", False,
     [("Neo4j Community Edition", "service"), ("Cypher", "language"), ("APOC", "framework")],
     [],
     "which graph engine carried the small taxonomy without APOC help",
     "community edition taxonomy lookup Cypher base engine graph"),
    # --- 2 ---
    ("Memgraph replaced Neo4j on the fraud-detection feed; in-memory traversal cut p99 path queries from 420 ms to 28 ms under the real-time budget.", "decision", "technical", False,
     [("Memgraph", "database"), ("Neo4j", "database")],
     [("Memgraph", "Neo4j", "REPLACES")],
     "which graph database took over fraud detection for latency reasons",
     "in memory traversal latency real time fraud path query swap"),
    # --- 3 ---
    ("APOC procedures drove the bulk import of the supplier graph into Neo4j; apoc.load.csv fed the MERGE cycle with idempotent keys.", "architecture", "technical", False,
     [("APOC", "framework"), ("Neo4j", "database")],
     [("APOC", "Neo4j", "BUILDS_ON")],
     "which Neo4j extension drove the idempotent supplier bulk import",
     "APOC load CSV MERGE idempotent bulk import procedure"),
    # --- 4 ---
    ("The Neo4j Graph Data Science library ran PageRank nightly on the citation graph; Louvain communities fed the recommendation bucketing.", "architecture", "technical", False,
     [("Neo4j Graph Data Science", "framework"), ("PageRank", "algorithm"), ("Louvain", "algorithm")],
     [],
     "which GDS algorithms carried the nightly citation analytics",
     "PageRank Louvain community detection citation nightly GDS"),
    # --- 5 ---
    ("Leiden replaced Louvain on the co-authorship graph; the resolution-limit fix made the medium-size clusters actually reflect lab groupings.", "decision", "technical", False,
     [("Leiden", "algorithm"), ("Louvain", "algorithm")],
     [("Leiden", "Louvain", "IMPROVES_ON")],
     "which community algorithm corrected the co-authorship resolution limits",
     "resolution limit cluster quality community co authorship swap"),
    # --- 6 ---
    ("Node2Vec ran on the product graph to seed the recommender embeddings; random-walk parameters p=1 q=2 balanced homophily and structural equivalence.", "architecture", "technical", False,
     [("Node2Vec", "algorithm")],
     [],
     "which graph embedding drove the product recommender cold start",
     "random walk embedding parameter balance homophily structural"),
    # --- 7 ---
    ("Dgraph replaced JanusGraph on the social ops stack; a single Go binary beat the three-tier Cassandra plus Elasticsearch plus TinkerPop setup.", "decision", "technical", False,
     [("Dgraph", "database"), ("JanusGraph", "database"), ("Go", "language"), ("Cassandra", "database"), ("Elasticsearch", "service"), ("TinkerPop", "framework")],
     [("Dgraph", "JanusGraph", "REPLACES")],
     "which graph engine collapsed the JanusGraph operational stack",
     "single binary ops simplify three tier retire social graph"),
    # --- 8 ---
    ("JanusGraph on BigTable backed the archival graph; the read-mostly pattern matched the LSM engine better than the Cassandra variant under scan load.", "decision", "technical", False,
     [("JanusGraph", "database"), ("BigTable", "database"), ("Cassandra", "database")],
     [("BigTable", "Cassandra", "IMPROVES_ON")],
     "which backend paired best with JanusGraph on the archival read workload",
     "LSM scan read mostly archive backend fit tune choice"),
    # --- 9 ---
    ("ArangoDB absorbed the knowledge graph plus the document catalog; the multi-model store retired a split MongoDB plus OrientDB deployment.", "decision", "technical", False,
     [("ArangoDB", "database"), ("MongoDB", "database"), ("OrientDB", "database")],
     [("ArangoDB", "OrientDB", "REPLACES"), ("ArangoDB", "MongoDB", "REPLACES")],
     "which multi-model store replaced the split document and graph setup",
     "multi model unify document graph consolidate swap store"),
    # --- 10. noise ---
    ("Give me a sec, I'll reopen the Cypher session.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Amazon Neptune exposed both Gremlin and openCypher on the same cluster; the team migrated dashboards off Gremlin to openCypher without a reload.", "architecture", "technical", False,
     [("Amazon Neptune", "service"), ("Gremlin", "language"), ("openCypher", "language")],
     [("openCypher", "Gremlin", "PREFERS")],
     "which dual-query support smoothed the Neptune dashboard migration",
     "dual query engine migrate dashboard no reload Neptune"),
    # --- 12 ---
    ("openCypher replaced proprietary Cypher extensions in the shared query library; standardisation let the queries run on Memgraph and Neptune alike.", "decision", "technical", False,
     [("openCypher", "language"), ("Cypher", "language"), ("Memgraph", "database"), ("Neptune", "service")],
     [("openCypher", "Cypher", "REPLACES")],
     "which standardisation retired the proprietary Cypher extensions",
     "standard query portable cross engine library retire extension"),
    # --- 13 ---
    ("GQL was tracked as the ISO successor to openCypher and PGQ; the team kept the query layer abstracted to ease the eventual migration.", "fact", "technical", False,
     [("GQL", "language"), ("openCypher", "language"), ("PGQ", "language")],
     [],
     "which ISO graph query standard will succeed openCypher and PGQ",
     "ISO standard successor abstract layer future migration ready"),
    # --- 14 ---
    ("RedisGraph reached end of life in 2023; production clusters were migrated to FalkorDB to keep the Cypher-on-Redis workflow alive.", "decision", "technical", False,
     [("RedisGraph", "database"), ("FalkorDB", "database"), ("Redis", "database")],
     [("FalkorDB", "RedisGraph", "REPLACES")],
     "which graph engine picked up the retired RedisGraph workloads",
     "end of life successor Cypher on Redis workflow keep alive"),
    # --- 15 ---
    ("FalkorDB's sparse matrix engine drove triangle counting faster than the old RedisGraph build; GraphBLAS primitives sat under the traversal.", "architecture", "technical", False,
     [("FalkorDB", "database"), ("RedisGraph", "database"), ("GraphBLAS", "framework")],
     [("FalkorDB", "RedisGraph", "IMPROVES_ON")],
     "which primitive engine sped up the triangle counting on FalkorDB",
     "sparse matrix GraphBLAS triangle count traversal speed"),
    # --- 16 ---
    ("TigerGraph was preferred over Neo4j for the 10-billion-edge fraud ring detection; the parallel query language GSQL spread the traversal across shards.", "preference", "technical", False,
     [("TigerGraph", "database"), ("Neo4j", "database"), ("GSQL", "language")],
     [("TigerGraph", "Neo4j", "PREFERS")],
     "which graph database won the ten billion edge fraud ring run",
     "parallel query shard distribute traversal scale fraud ring"),
    # --- 17 ---
    ("The TigerGraph GSQL documentation is the reference for the fraud analytics team; the accumulator patterns shaped the ring-detection templates.", "reference", "technical", False,
     [("TigerGraph", "database"), ("GSQL", "language")],
     [],
     "which documentation anchors the fraud ring accumulator patterns",
     "documentation reference accumulator pattern template fraud guide"),
    # --- 18 ---
    ("AgensGraph built graph features on Postgres; the team tested it against pgvector for mixed vector plus graph queries on a knowledge graph pilot.", "architecture", "technical", False,
     [("AgensGraph", "database"), ("Postgres", "database"), ("pgvector", "framework")],
     [("AgensGraph", "Postgres", "BUILDS_ON")],
     "which Postgres-based graph extension carried the hybrid pilot",
     "Postgres graph extension vector mix hybrid knowledge pilot"),
    # --- 19 ---
    ("EdgeDB modelled the project schema as a property graph over Postgres; the typed EdgeQL queries replaced a handwritten Cypher layer.", "decision", "technical", False,
     [("EdgeDB", "database"), ("Postgres", "database"), ("EdgeQL", "language"), ("Cypher", "language")],
     [("EdgeQL", "Cypher", "REPLACES")],
     "which typed query layer displaced the handwritten Cypher on the project",
     "typed schema property graph Postgres query layer swap"),
    # --- 20 ---
    ("Kuzu's embedded columnar store replaced an in-process NetworkX cache for the analyst notebooks; cold load dropped from 90 s to 4 s on a 20 M-edge dataset.", "decision", "technical", False,
     [("Kuzu", "database"), ("NetworkX", "framework")],
     [("Kuzu", "NetworkX", "REPLACES")],
     "which embedded graph store replaced NetworkX in the analyst notebooks",
     "embedded columnar cold load notebook analyst swap cache"),
    # --- 21 ---
    ("Index-free adjacency was the selling point for Neo4j over the triple store on the recursive path queries; pointer hops stayed O(1) per edge.", "fact", "technical", False,
     [("Neo4j", "database")],
     [],
     "which native graph property justified Neo4j over the triple store",
     "index free adjacency pointer hop recursive path constant"),
    # --- 22 ---
    ("Stardog replaced GraphDB on the compliance RDF triple store; SPARQL plus reasoning with inline explanations was easier for the auditors.", "decision", "technical", False,
     [("Stardog", "database"), ("GraphDB", "database"), ("SPARQL", "language"), ("RDF", "technology")],
     [("Stardog", "GraphDB", "REPLACES")],
     "which RDF store displaced GraphDB for the compliance auditors",
     "SPARQL reasoning explanation auditor triple store compliance"),
    # --- 23 ---
    ("AnzoGraph ran the analytic SPARQL queries on the knowledge graph; the MPP engine beat Virtuoso on the 50-way join benchmark.", "architecture", "technical", False,
     [("AnzoGraph", "database"), ("SPARQL", "language"), ("Virtuoso", "database")],
     [("AnzoGraph", "Virtuoso", "IMPROVES_ON")],
     "which MPP triple store won the 50-way SPARQL join benchmark",
     "massively parallel SPARQL join benchmark analytic triple"),
    # --- 24 ---
    ("Virtuoso kept the legacy linked-data endpoint on the open-data portal; the SPARQL federation pattern was stable across DBpedia sources.", "architecture", "technical", False,
     [("Virtuoso", "database"), ("SPARQL", "language"), ("DBpedia", "service")],
     [],
     "which triple store anchored the legacy linked-data federation path",
     "federation linked data open portal SPARQL stable endpoint"),
    # --- 25 ---
    ("Property graphs were preferred over RDF triple stores for the operational use case; the weighted edge attributes were a pain to model as reified triples.", "preference", "technical", False,
     [("RDF", "technology")],
     [],
     "which model won the operational case over triple store reification",
     "property graph edge attribute weight reify triple pain"),
    # --- 26 ---
    ("Gremlin traversals were rewritten in openCypher on the Neptune cluster; declarative patterns halved the query line count and were easier to review.", "decision", "technical", False,
     [("Gremlin", "language"), ("openCypher", "language"), ("Neptune", "service")],
     [("openCypher", "Gremlin", "REPLACES")],
     "which query language replaced Gremlin on the Neptune cluster review",
     "declarative pattern line count review rewrite swap traversal"),
    # --- 27 ---
    ("Neptune Analytics replaced the batch GDS job on Neo4j for the weekly PageRank; the in-memory snapshot ran the full graph in under 12 minutes.", "decision", "technical", False,
     [("Neptune Analytics", "service"), ("GDS", "framework"), ("Neo4j", "database"), ("PageRank", "algorithm")],
     [("Neptune Analytics", "GDS", "REPLACES")],
     "which AWS analytics job retired the Neo4j GDS weekly PageRank",
     "in memory snapshot weekly PageRank analytic job swap run"),
    # --- 28 ---
    ("The Apache TinkerPop Gremlin console stayed the debugging tool of choice across Neptune and JanusGraph; one REPL covered both property graphs.", "preference", "technical", False,
     [("Apache TinkerPop", "framework"), ("Gremlin", "language"), ("Neptune", "service"), ("JanusGraph", "database")],
     [],
     "which REPL unified debugging across the two property graph backends",
     "console REPL debug shared property graph cross engine"),
    # --- 29 ---
    ("GraphML replaced a custom JSON dump for interchange with the Gephi visualiser; the XML schema was lossy on numeric edge weights but covered the typing.", "decision", "technical", False,
     [("GraphML", "technology"), ("JSON", "technology"), ("Gephi", "tool"), ("XML", "technology")],
     [("GraphML", "JSON", "REPLACES")],
     "which serialisation format took over the Gephi interchange path",
     "interchange visual dump schema type cover numeric lossy"),
    # --- 30 ---
    ("GraphSON replaced a homegrown binary dump on the TinkerPop import pipeline; version 3 JSON typing carried the date and UUID fidelity across engines.", "decision", "technical", False,
     [("GraphSON", "technology"), ("TinkerPop", "framework"), ("JSON", "technology")],
     [("GraphSON", "TinkerPop", "BUILDS_ON")],
     "which serialisation captured the date and UUID types for TinkerPop",
     "typed JSON format binary replace date UUID fidelity pipe"),
    # --- 31 ---
    ("ArangoDB was preferred over OrientDB for the multi-model rebuild; active maintenance and the AQL optimizer decided it over OrientDB's stalled roadmap.", "preference", "technical", False,
     [("ArangoDB", "database"), ("OrientDB", "database"), ("AQL", "language")],
     [("ArangoDB", "OrientDB", "IMPROVES_ON")],
     "which multi-model store replaced OrientDB on the rebuild project",
     "active maintenance optimizer stalled roadmap rebuild swap"),
    # --- 32 ---
    ("Cypher index hints on the :Person(email) lookup cut an OLTP path query from 180 ms to 6 ms; the planner had been picking a label scan instead.", "problem", "technical", False,
     [("Cypher", "language")],
     [],
     "which Cypher hint fix rescued the OLTP person-lookup path query",
     "index hint planner label scan swap OLTP path email"),
    # --- 33 ---
    ("Neo4j Bloom was rolled out to the analysts for exploratory graph views; the no-Cypher search bar replaced their ad-hoc Gephi exports.", "decision", "technical", False,
     [("Neo4j Bloom", "tool"), ("Cypher", "language"), ("Gephi", "tool")],
     [("Neo4j Bloom", "Gephi", "REPLACES")],
     "which exploration tool replaced the analyst Gephi export loop",
     "no Cypher search bar exploratory view analyst swap tool"),
    # --- 34. noise ---
    ("Hold on, the graph server is just finishing its compaction pass.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Memgraph's streaming Kafka source drove the continuous trigger on the fraud detection path; the MAGE module library covered the custom traversals.", "architecture", "technical", False,
     [("Memgraph", "database"), ("Kafka", "service"), ("MAGE", "framework")],
     [("MAGE", "Memgraph", "BUILDS_ON")],
     "which streaming hook fed the Memgraph continuous fraud triggers",
     "streaming Kafka source trigger continuous fraud MAGE module"),
    # --- 36 ---
    ("Property graphs were mapped to RDF via RDF-star for the interop layer; reified edge properties stayed addressable without blowing up the triple count.", "architecture", "technical", False,
     [("RDF-star", "technology"), ("RDF", "technology")],
     [("RDF-star", "RDF", "IMPROVES_ON")],
     "which RDF extension carried the property graph interop neatly",
     "star reify edge property triple count interop layer"),
    # --- 37 ---
    ("Kuzu's vectorised execution replaced a NetworkX BFS on the dependency graph; the wide-row columnar layout gave a 30x speedup on path-of-length-k queries.", "decision", "technical", False,
     [("Kuzu", "database"), ("NetworkX", "framework"), ("BFS", "algorithm")],
     [("Kuzu", "NetworkX", "IMPROVES_ON")],
     "which embedded engine sped up the BFS on the dependency graph",
     "vectorised columnar path length speedup BFS dependency"),
    # --- 38 ---
    ("Neo4j 5 Fabric replaced the manual federation layer across the regional graphs; the query router pushed sub-queries down without a write coordinator.", "decision", "technical", False,
     [("Neo4j 5", "database"), ("Fabric", "framework")],
     [("Fabric", "Neo4j 5", "BUILDS_ON")],
     "which Neo4j feature displaced the manual cross-region federation",
     "federation router push sub query region coordinator swap"),
    # --- 39 ---
    ("The Bolt protocol drove the Cypher driver choice on the Spring Data Neo4j project; HTTP was retired for the binary, pipelined channel.", "decision", "technical", False,
     [("Bolt", "protocol"), ("Cypher", "language"), ("Spring Data Neo4j", "framework"), ("HTTP", "protocol")],
     [("Bolt", "HTTP", "REPLACES")],
     "which Neo4j transport displaced HTTP on the Spring Data driver",
     "binary pipeline Bolt HTTP retire driver Spring transport"),
    # --- 40 ---
    ("The pattern-matching PGQ extension to SQL was piloted on DuckDB; the analyst team kept their SQL habits on a property graph view.", "architecture", "technical", False,
     [("PGQ", "language"), ("SQL", "language"), ("DuckDB", "database")],
     [("PGQ", "SQL", "BUILDS_ON")],
     "which ISO extension let analysts do graph queries from SQL habits",
     "pattern match property graph SQL habit analyst extension"),
    # --- 41 ---
    ("JanusGraph's composite indexes were preferred over mixed indexes for the exact-match lookups; the Elasticsearch hop added a round trip the flow could not afford.", "preference", "technical", False,
     [("JanusGraph", "database"), ("Elasticsearch", "service")],
     [],
     "which JanusGraph index style won the exact-match latency case",
     "composite mixed exact match round trip avoid lookup"),
    # --- 42 ---
    ("Dgraph's built-in GraphQL layer replaced a bespoke Apollo resolver stack on the social feed; the schema-first flow cut the API boilerplate in half.", "decision", "technical", False,
     [("Dgraph", "database"), ("GraphQL", "technology"), ("Apollo", "framework")],
     [("Dgraph", "Apollo", "REPLACES")],
     "which built-in API layer retired the Apollo resolver stack",
     "schema first resolver layer boilerplate GraphQL swap social"),
    # --- 43 ---
    ("Neo4j AuraDB took over the dev-stage graph on 2026-02-10; the managed service freed the platform team from the VM snapshot rotation.", "milestone", "technical", False,
     [("Neo4j AuraDB", "service"), ("2026-02-10", "date")],
     [],
     "when did the managed Neo4j service absorb the dev-stage graph",
     "managed service VM snapshot retire platform date absorb"),
    # --- 44 ---
    ("A cross-database federation query on Neptune Analytics pulled from both the openCypher graph and a Gremlin-typed archive; the federation cost stayed inside the 60-second SLA.", "architecture", "technical", False,
     [("Neptune Analytics", "service"), ("openCypher", "language"), ("Gremlin", "language")],
     [],
     "which federation path kept the cross-database query under SLA",
     "cross database federation query SLA archive analytic"),
    # --- 45 ---
    ("Memgraph High Availability clusters replaced a single-node deployment after the 2025 outage; Raft consensus on the three-replica group kept writes live through the upgrade.", "decision", "technical", False,
     [("Memgraph", "database"), ("Raft", "algorithm")],
     [("Memgraph", "Raft", "BUILDS_ON")],
     "which Memgraph topology retired the single-node deployment post-outage",
     "Raft consensus replica availability upgrade write live topology"),
    # --- 46 ---
    ("Cypher subqueries with CALL { ... } IN TRANSACTIONS replaced a client-side batch loop on the 200 M-edge import; the driver round-trip cost vanished.", "decision", "technical", False,
     [("Cypher", "language")],
     [],
     "which Cypher construct replaced the client-side import batch loop",
     "subquery transaction batch import round trip cost import"),
    # --- 47 ---
    ("An embedded Kuzu database shipped inside the desktop app; the 20 MB binary replaced a SQLite plus hand-rolled adjacency list for the knowledge map.", "decision", "technical", False,
     [("Kuzu", "database"), ("SQLite", "database")],
     [("Kuzu", "SQLite", "REPLACES")],
     "which embedded graph store shipped inside the desktop knowledge map",
     "embedded desktop binary adjacency list swap knowledge map"),
    # --- 48 ---
    ("Gremlin OLAP traversals over Spark on JanusGraph drove the overnight analytics; the TinkerPop Spark module handled the partitioning across the Cassandra backend.", "architecture", "technical", False,
     [("Gremlin", "language"), ("Spark", "framework"), ("JanusGraph", "database"), ("TinkerPop", "framework"), ("Cassandra", "database")],
     [],
     "which OLAP layer drove the overnight JanusGraph analytics run",
     "OLAP Spark partition backend overnight analytic traversal"),
    # --- 49 ---
    ("Triangle counting on the GDS library surfaced the clustering coefficient bump on the co-purchase graph; the Louvain community shift matched the holiday basket mix.", "milestone", "technical", False,
     [("GDS", "framework"), ("Louvain", "algorithm")],
     [],
     "which GDS pass surfaced the holiday co-purchase community shift",
     "triangle count cluster coefficient holiday basket community"),
    # --- 50 ---
    ("FalkorDB replaced a Neo4j staging instance for the agent-memory prototype; the Redis-like command surface fit the existing Redis ops playbook.", "decision", "technical", False,
     [("FalkorDB", "database"), ("Neo4j", "database"), ("Redis", "database")],
     [("FalkorDB", "Neo4j", "REPLACES")],
     "which graph engine took over the agent-memory prototype from Neo4j",
     "agent memory prototype command surface ops playbook swap"),
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
