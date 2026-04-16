"""One-off emitter for shared-base batch-154 — technical domain (graph databases and query engines: Neo4j, Memgraph, Dgraph, TigerGraph, ArangoDB, JanusGraph, Amazon Neptune, Cosmos Graph, Nebula Graph, KuzuDB, FalkorDB, Apache Age, Cypher, Gremlin, SPARQL, property graphs, RDF, traversal, shortest-path, Louvain, PageRank, partitioning, vertex-centric indexes).

Writes 50 rows to data/v2/shared/batch_154.tmp.jsonl with ids shared-07651..07700.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_154.tmp.jsonl"
ID_OFFSET = 7650

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the social-graph service from Neo4j Community to Memgraph for the in-memory traversal path; p99 on 4-hop friends-of-friends queries dropped from 180 ms to 22 ms on the same hardware.", "decision", "technical", False,
     [("Neo4j", "database"), ("Memgraph", "database"), ("friends-of-friends", "pattern")],
     [("Memgraph", "Neo4j", "REPLACES")],
     "which graph database replaced Neo4j Community for the social service and what p99 win did the swap deliver",
     "memgraph neo4j social graph traversal p99 friends hop"),
    # --- 2 ---
    ("Dgraph handles the authoring backend because the DQL schema directives cut the hand-written resolver layer we used to maintain on top of Neo4j; mutations route through a single GraphQL endpoint now.", "architecture", "technical", False,
     [("Dgraph", "database"), ("DQL", "language"), ("Neo4j", "database"), ("GraphQL", "protocol")],
     [("Dgraph", "Neo4j", "REPLACES"), ("Dgraph", "GraphQL", "SUPPORTS")],
     "which graph database took over the authoring backend and which directive layer removed the resolver code",
     "dgraph dql graphql neo4j authoring schema directive resolver"),
    # --- 3 ---
    ("TigerGraph's GSQL loops outperformed our Cypher-on-Neo4j path for the 6-hop fraud pattern by roughly 8x; the accumulator abstraction maps onto vertex-centric work much more cleanly.", "fact", "technical", False,
     [("TigerGraph", "database"), ("GSQL", "language"), ("Cypher", "language"), ("Neo4j", "database"), ("vertex-centric", "pattern")],
     [("GSQL", "Cypher", "IMPROVES_ON")],
     "which GSQL feature made 6-hop fraud detection faster than Cypher on Neo4j by roughly an order of magnitude",
     "tigergraph gsql cypher neo4j fraud 6 hop vertex centric accumulator"),
    # --- 4 ---
    ("ArangoDB stayed as the multi-model store for the catalog service; AQL's ability to mix document filters with graph traversals in one query kept us off a second datastore.", "decision", "technical", False,
     [("ArangoDB", "database"), ("AQL", "language"), ("catalog service", "project")],
     [("ArangoDB", "AQL", "USES")],
     "which multi-model query language let the catalog avoid adding a second datastore alongside the graph",
     "arangodb aql multi model catalog document filter traversal mix"),
    # --- 5 ---
    ("JanusGraph on ScyllaDB backs the identity-resolution graph; the Cassandra-compatible wire plus ScyllaDB's lower tail latencies gave us Gremlin traversals without JVM-GC spikes on the storage side.", "architecture", "technical", False,
     [("JanusGraph", "database"), ("ScyllaDB", "database"), ("Cassandra", "database"), ("Gremlin", "language")],
     [("JanusGraph", "ScyllaDB", "DEPLOYED_ON"), ("JanusGraph", "Gremlin", "SUPPORTS")],
     "which storage backend did JanusGraph pair with to avoid JVM garbage collection spikes under Gremlin load",
     "janusgraph scylladb cassandra gremlin identity tail latency jvm gc"),
    # --- 6 ---
    ("Amazon Neptune serves the knowledge-graph reads behind the product recommender; the Gremlin and openCypher dual endpoints let us port a Cypher query without a rewrite when we migrated from a single-node Neo4j instance.", "milestone", "technical", False,
     [("Amazon Neptune", "database"), ("Gremlin", "language"), ("openCypher", "language"), ("Neo4j", "database"), ("Cypher", "language")],
     [("Amazon Neptune", "openCypher", "SUPPORTS"), ("Amazon Neptune", "Neo4j", "REPLACES")],
     "which dual-dialect support on Neptune made the port from Neo4j avoid a full Cypher rewrite",
     "neptune gremlin opencypher cypher neo4j knowledge graph recommender"),
    # --- 7 ---
    ("Azure Cosmos Graph runs the multi-tenant metadata store; partition keys on tenantId align with Gremlin's vertex partitioning so cross-partition traversals stay rare in the hot path.", "architecture", "technical", False,
     [("Azure Cosmos Graph", "database"), ("Gremlin", "language"), ("tenantId", "concept")],
     [("Azure Cosmos Graph", "Gremlin", "SUPPORTS")],
     "how does the Cosmos Graph partitioning scheme keep cross-partition Gremlin traversals off the hot path",
     "cosmos graph gremlin partition key tenant multi tenant metadata"),
    # --- 8 ---
    ("Nebula Graph handles the billion-edge recommendation subgraph; its shared-nothing storage shards on vertex id and the rank field in edges gave us natural multi-edge ordering for temporal rollups.", "fact", "technical", False,
     [("Nebula Graph", "database"), ("vertex id", "concept"), ("rank field", "concept")],
     [("Nebula Graph", "vertex id", "USES")],
     "which Nebula Graph feature supplies natural ordering across multi-edges for temporal recommendation rollups",
     "nebula graph shared nothing vertex rank multi edge temporal"),
    # --- 9 ---
    ("KuzuDB is the embedded analytics engine behind the notebook tooling; columnar vertex storage and vectorised execution read Parquet vertex and edge files directly without a load step.", "architecture", "technical", False,
     [("KuzuDB", "database"), ("Parquet", "technology"), ("notebook tooling", "project")],
     [("KuzuDB", "Parquet", "SUPPORTS")],
     "which embedded graph engine reads Parquet vertex and edge files without a separate load phase",
     "kuzudb columnar vector parquet vertex edge notebook embedded"),
    # --- 10. noise ---
    ("The break room's espresso machine started emitting a low harmonic hum only on rainy mornings and nobody has volunteered to debug it.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("FalkorDB replaced the abandoned RedisGraph deployment with minimal code change; the Cypher subset is nearly identical and the GRAPH.QUERY command stayed so the existing driver calls continued to work.", "decision", "technical", False,
     [("FalkorDB", "database"), ("RedisGraph", "database"), ("Cypher", "language"), ("GRAPH.QUERY", "command")],
     [("FalkorDB", "RedisGraph", "REPLACES")],
     "which graph module replaced the deprecated RedisGraph without forcing a driver rewrite",
     "falkordb redisgraph cypher graph query driver replacement"),
    # --- 12 ---
    ("Apache Age rides on the existing Postgres cluster for the audit graph; we trade raw traversal speed for one less system to operate, and openCypher parity lets most queries port over.", "decision", "technical", False,
     [("Apache Age", "database"), ("Postgres", "database"), ("openCypher", "language"), ("audit graph", "project")],
     [("Apache Age", "Postgres", "DEPLOYED_ON"), ("Apache Age", "openCypher", "SUPPORTS")],
     "why did we pick Apache Age on Postgres for the audit graph despite the traversal-speed trade-off",
     "apache age postgres opencypher audit graph single system operate"),
    # --- 13 ---
    ("openCypher became the lingua franca across the platform; new services default to it because Neo4j, Memgraph, Neptune, and Age all speak a compatible dialect and the query plans port with minor tweaks.", "preference", "technical", False,
     [("openCypher", "language"), ("Neo4j", "database"), ("Memgraph", "database"), ("Neptune", "database"), ("Age", "database")],
     [("Neo4j", "openCypher", "SUPPORTS"), ("Memgraph", "openCypher", "SUPPORTS"), ("Neptune", "openCypher", "SUPPORTS")],
     "which query dialect became the default across services because several backends implement it compatibly",
     "opencypher neo4j memgraph neptune age portable dialect platform"),
    # --- 14 ---
    ("GQL is now an ISO standard and we're tracking its adoption for the next platform revision; the overlap with openCypher means the migration path from current Cypher queries is mostly mechanical.", "reference", "technical", False,
     [("GQL", "language"), ("openCypher", "language"), ("Cypher", "language"), ("ISO", "organization")],
     [("GQL", "openCypher", "RELATED_TO")],
     "which ISO-standard graph query language overlaps enough with openCypher that migration is mostly mechanical",
     "gql iso opencypher cypher standard migration mechanical adopt"),
    # --- 15 ---
    ("Gremlin stayed as the glue for cross-backend tooling; a single traversal expressed via gremlin-python runs against Neptune, JanusGraph, and the local TinkerPop stack without rewrites.", "architecture", "technical", False,
     [("Gremlin", "language"), ("gremlin-python", "library"), ("Neptune", "database"), ("JanusGraph", "database"), ("TinkerPop", "framework")],
     [("gremlin-python", "Neptune", "COMMUNICATES_WITH"), ("gremlin-python", "JanusGraph", "COMMUNICATES_WITH")],
     "which traversal language lets the same Python code hit multiple backends in the tooling path",
     "gremlin tinkerpop python neptune janusgraph cross backend traversal"),
    # --- 16 ---
    ("SPARQL drives the semantic-web side via Blazegraph; RDF triples with named graphs encode provenance and the FROM NAMED clause isolates each dataset's facts at query time.", "architecture", "technical", False,
     [("SPARQL", "language"), ("Blazegraph", "database"), ("RDF", "protocol"), ("FROM NAMED", "pattern")],
     [("SPARQL", "Blazegraph", "USES"), ("SPARQL", "RDF", "APPLIES_TO")],
     "how do named graphs and FROM NAMED help SPARQL isolate dataset provenance in Blazegraph",
     "sparql blazegraph rdf named graph provenance from clause"),
    # --- 17 ---
    ("Property graphs beat RDF for the fraud-pattern use case; edge properties like amount and timestamp would have needed reification in RDF, which bloats triple count and kills traversal locality.", "decision", "technical", False,
     [("Property graphs", "concept"), ("RDF", "protocol"), ("reification", "pattern"), ("fraud-pattern", "pattern")],
     [("Property graphs", "RDF", "PREFERS")],
     "why did property graphs win over RDF for the fraud pattern and what RDF technique would have been required",
     "property graph rdf reification fraud edge property amount timestamp"),
    # --- 18 ---
    ("RDF triples still win for the reference-ontology service because SKOS and OWL inference is a native fit; the SHACL validator catches schema drift on ingest before the triples land.", "fact", "technical", False,
     [("RDF", "protocol"), ("SKOS", "protocol"), ("OWL", "protocol"), ("SHACL", "protocol")],
     [("SHACL", "RDF", "APPLIES_TO")],
     "which RDF-native validators and vocabularies made it the right fit for the reference ontology service",
     "rdf skos owl shacl inference ontology validate schema drift"),
    # --- 19 ---
    ("BFS beats DFS for the shortest unweighted path on a dense follower graph; we hit the iteration budget on DFS before finding the target at depth four even with a visited set.", "problem", "technical", False,
     [("BFS", "algorithm"), ("DFS", "algorithm"), ("follower graph", "pattern"), ("visited set", "concept")],
     [("BFS", "DFS", "IMPROVES_ON")],
     "which traversal beat DFS for shortest unweighted paths on the dense follower graph and why did DFS bust the budget",
     "bfs dfs shortest path unweighted follower dense iteration budget"),
    # --- 20 ---
    ("Dijkstra handles the shortest-path queries in the routing graph since edge weights are non-negative; A* is only used for the geographic search where the haversine heuristic is admissible.", "architecture", "technical", False,
     [("Dijkstra", "algorithm"), ("A*", "algorithm"), ("haversine", "algorithm"), ("routing graph", "project")],
     [("A*", "haversine", "USES")],
     "how does the routing stack split between Dijkstra and A* and which heuristic anchors the geographic case",
     "dijkstra astar haversine admissible heuristic routing weight path"),
    # --- 21 ---
    ("Bellman-Ford replaced Dijkstra on the currency-arbitrage graph because some edges represent discounts and end up negative; the negative-cycle detection also flags arbitrage loops directly.", "decision", "technical", False,
     [("Bellman-Ford", "algorithm"), ("Dijkstra", "algorithm"), ("currency-arbitrage", "project"), ("negative-cycle", "concept")],
     [("Bellman-Ford", "Dijkstra", "REPLACES")],
     "which shortest-path algorithm replaced Dijkstra on the arbitrage graph and what cycle behaviour did it give us",
     "bellman ford dijkstra negative edge arbitrage cycle currency graph"),
    # --- 22 ---
    ("Louvain partitioning landed first for the community detection pass; modularity hit 0.61 on the full collaboration graph and the runtime stayed under four minutes on the 40M-edge snapshot.", "milestone", "technical", False,
     [("Louvain", "algorithm"), ("community detection", "concept"), ("modularity", "concept"), ("collaboration graph", "project")],
     [("Louvain", "community detection", "IMPLEMENTS")],
     "which community-detection algorithm hit 0.61 modularity on the collaboration graph and at what runtime",
     "louvain community modularity collaboration graph 40m edge minute"),
    # --- 23 ---
    ("Leiden replaced Louvain for the next quarter because the guarantee of well-connected communities eliminated the disconnected-cluster artefacts we kept seeing at resolution 1.0.", "decision", "technical", False,
     [("Leiden", "algorithm"), ("Louvain", "algorithm"), ("disconnected-cluster", "pattern"), ("resolution", "concept")],
     [("Leiden", "Louvain", "REPLACES")],
     "why did Leiden replace Louvain at resolution 1.0 and what class of cluster artefact did it eliminate",
     "leiden louvain disconnected community resolution guarantee connected"),
    # --- 24 ---
    ("PageRank on the citation graph runs nightly in 14 iterations with damping 0.85; convergence to L1 delta under 1e-6 was enough for the downstream ranker without tightening further.", "fact", "technical", False,
     [("PageRank", "algorithm"), ("citation graph", "project"), ("damping", "config"), ("L1 delta", "concept")],
     [("PageRank", "citation graph", "APPLIES_TO")],
     "which PageRank parameters and convergence bound did we settle on for the nightly citation rank job",
     "pagerank citation damping 0.85 iteration convergence l1 delta ranker"),
    # --- 25 ---
    ("Personalized PageRank replaced the global score for the follow-recommendation feature; seeding the teleport vector with the viewer's followees gave far better rankings than the global rank re-weighted at read time.", "decision", "technical", False,
     [("Personalized PageRank", "algorithm"), ("teleport vector", "concept"), ("follow-recommendation", "project")],
     [("Personalized PageRank", "follow-recommendation", "APPLIES_TO")],
     "which PageRank variant replaced the global score for follow recommendations and which vector was personalised",
     "personalized pagerank teleport follow recommendation seed viewer"),
    # --- 26 ---
    ("Graph partitioning on the social store uses METIS-style edge-cut minimisation run offline; streaming partitioners like Fennel gave a quick start but the long-tail hot vertices stayed mis-placed.", "problem", "technical", False,
     [("METIS", "tool"), ("Fennel", "algorithm"), ("edge-cut", "concept"), ("hot vertices", "pattern")],
     [("METIS", "Fennel", "REPLACES")],
     "which partitioning scheme replaced Fennel streaming for the social store and what long-tail failure pushed the change",
     "metis fennel edge cut partition streaming hot vertex long tail"),
    # --- 27 ---
    ("Vertex-centric indexes in JanusGraph finally fixed the supernode problem on Justin Bieber's follower vertex; edge queries restricted by a time range now seek instead of scanning millions of edges.", "problem", "technical", False,
     [("Vertex-centric indexes", "pattern"), ("JanusGraph", "database"), ("supernode", "concept")],
     [("Vertex-centric indexes", "supernode", "FIXES")],
     "which index type in JanusGraph fixed the supernode scan on the celebrity follower vertex",
     "vertex centric index janusgraph supernode follower scan time range"),
    # --- 28 ---
    ("Nebula Graph's composite indexes cover the (label, property) pair lookups in the recommendation query; without the composite, each partition was doing a full vertex scan for tagged-by filters.", "fact", "technical", False,
     [("Nebula Graph", "database"), ("composite indexes", "pattern"), ("recommendation query", "project")],
     [("composite indexes", "Nebula Graph", "APPLIES_TO")],
     "which index form in Nebula Graph turned a per-partition vertex scan into a seek for tagged-by filters",
     "nebula composite index label property recommendation partition scan"),
    # --- 29 ---
    ("Cypher query plans are inspected with EXPLAIN and PROFILE before shipping to prod; an unexpected NodeByLabelScan is the clearest signal a missing label index is about to hurt p95 at scale.", "preference", "technical", False,
     [("Cypher", "language"), ("EXPLAIN", "command"), ("PROFILE", "command"), ("NodeByLabelScan", "pattern")],
     [],
     "which Cypher plan operator is the clearest signal of a missing label index before the query ships",
     "cypher explain profile node by label scan plan missing index p95"),
    # --- 30 ---
    ("Gremlin's withStrategies() lets us pin a ProductiveByStrategy during A/B of the recommendation traversal; swapping strategies out of band is safer than forking the traversal source at runtime.", "fact", "technical", False,
     [("Gremlin", "language"), ("withStrategies", "method"), ("ProductiveByStrategy", "pattern")],
     [],
     "which Gremlin mechanism pins a traversal strategy for A/B without forking the traversal source",
     "gremlin withstrategies productive strategy ab test traversal source"),
    # --- 31 ---
    ("Neo4j 5's block format replaced the legacy standard format on the main cluster; dense nodes compress better and the relationship lookup on high-degree vertices no longer thrashes the page cache.", "milestone", "technical", False,
     [("Neo4j 5", "database"), ("block format", "pattern"), ("standard format", "pattern"), ("page cache", "concept")],
     [("block format", "standard format", "REPLACES")],
     "which Neo4j 5 storage format replaced the legacy one and what page-cache behaviour did it improve on dense nodes",
     "neo4j 5 block standard format dense node page cache degree"),
    # --- 32 ---
    ("Memgraph's MAGE library plugged the NetworkX-style algorithms we needed into the server directly; Louvain, betweenness, and weakly connected components run inside the query engine instead of exporting data out.", "architecture", "technical", False,
     [("Memgraph", "database"), ("MAGE", "library"), ("NetworkX", "library"), ("Louvain", "algorithm"), ("betweenness", "algorithm")],
     [("MAGE", "Memgraph", "EXTENDS")],
     "which Memgraph library plugged graph algorithms into the query engine so we stopped exporting data to NetworkX",
     "memgraph mage networkx louvain betweenness component query engine"),
    # --- 33 ---
    ("Dgraph's @reverse directive on the authored-by predicate gave us cheap backlinks without defining a second edge; the resolver no longer hand-wrote the inverse traversal for every author query.", "fact", "technical", False,
     [("Dgraph", "database"), ("@reverse", "pattern"), ("authored-by", "pattern"), ("resolver", "pattern")],
     [("@reverse", "Dgraph", "APPLIES_TO")],
     "which Dgraph directive gave us cheap backlinks on authored-by without maintaining a second edge",
     "dgraph reverse directive backlink author predicate inverse edge"),
    # --- 34 ---
    ("TinkerPop 3.7 upgrade unblocked the gremlin-python async client on Neptune; the prior 3.6 path was blocking on the event loop and starving the ASGI worker under concurrent traversals.", "problem", "technical", False,
     [("TinkerPop", "framework"), ("gremlin-python", "library"), ("Neptune", "database"), ("ASGI", "framework")],
     [("TinkerPop", "gremlin-python", "SUPPORTS")],
     "which TinkerPop upgrade fixed the gremlin-python async client starvation on Neptune under ASGI",
     "tinkerpop 3.7 gremlin python async neptune asgi event loop starve"),
    # --- 35 ---
    ("TigerGraph's loading job scales a 2B-edge import over the cluster with a partitioned JSON feed; a naive single-file ingest used to bottleneck on the master GPE before the refactor.", "problem", "technical", False,
     [("TigerGraph", "database"), ("loading job", "pattern"), ("JSON", "technology"), ("GPE", "infrastructure")],
     [("loading job", "TigerGraph", "APPLIES_TO")],
     "how did the TigerGraph 2B-edge import stop bottlenecking the master GPE on ingest",
     "tigergraph loading 2b edge json partition gpe master bottleneck"),
    # --- 36 ---
    ("KuzuDB's MATCH-WHERE-RETURN dialect is close enough to Cypher that our notebook query layer ports with a trivial adapter; differences are mostly around type coercion and list comprehensions.", "fact", "technical", False,
     [("KuzuDB", "database"), ("Cypher", "language"), ("notebook query layer", "project"), ("adapter", "pattern")],
     [("KuzuDB", "Cypher", "RELATED_TO")],
     "which KuzuDB compatibility with Cypher let the notebook query layer port with only a trivial adapter",
     "kuzudb cypher match where return dialect adapter notebook port"),
    # --- 37 ---
    ("Cost-based planner in Memgraph picked a different join order than Neo4j on the same query; statistics on label cardinality made the IndexSeek-then-Expand path win over an Expand-then-Filter chain.", "fact", "technical", False,
     [("Memgraph", "database"), ("Neo4j", "database"), ("IndexSeek", "pattern"), ("Expand", "pattern")],
     [],
     "why did the Memgraph planner pick IndexSeek-then-Expand over Expand-then-Filter that Neo4j had chosen",
     "memgraph neo4j planner label cardinality index seek expand filter"),
    # --- 38 ---
    ("Schema migrations on property graphs use a forward-only ledger: each migration adds labels and relationships, never renames in place, so a partial rollout doesn't break readers on the older version.", "architecture", "technical", False,
     [("property graphs", "concept"), ("forward-only ledger", "pattern"), ("migration", "pattern")],
     [],
     "which migration pattern keeps older readers working while new labels and relationships roll out on the property graph",
     "property graph schema migration forward only ledger label relation"),
    # --- 39 ---
    ("Weighted shortest-path on the logistics graph uses A* with a landmark-based lower bound; ALT-style landmark distances precomputed per warehouse beat vanilla Dijkstra by 3-4x on long routes.", "decision", "technical", False,
     [("A*", "algorithm"), ("landmark", "concept"), ("Dijkstra", "algorithm"), ("ALT", "algorithm"), ("logistics graph", "project")],
     [("A*", "Dijkstra", "IMPROVES_ON"), ("ALT", "A*", "EXTENDS")],
     "which landmark-based heuristic did A* pair with to beat Dijkstra on the logistics long-route queries",
     "astar landmark alt dijkstra logistics warehouse shortest path"),
    # --- 40 ---
    ("Connected-components on the transaction graph runs with union-find at ingest time; the incremental merge keeps component ids stable and avoids a full rescan when new edges land.", "architecture", "technical", False,
     [("Connected-components", "algorithm"), ("union-find", "algorithm"), ("transaction graph", "project")],
     [("union-find", "Connected-components", "IMPLEMENTS")],
     "which data structure lets connected-component ids stay stable on the transaction graph as new edges arrive",
     "union find connected component transaction graph ingest merge stable"),
    # --- 41 ---
    ("Graph embedding for the similar-users panel uses node2vec at p=1 q=0.5 to bias toward structural equivalence; the embeddings feed an ANN index so the graph backend itself doesn't serve the similarity lookup.", "architecture", "technical", False,
     [("node2vec", "algorithm"), ("ANN", "concept"), ("similar-users panel", "project")],
     [("node2vec", "similar-users panel", "APPLIES_TO")],
     "how do node2vec parameters and an ANN index keep the similarity lookup off the main graph backend",
     "node2vec embedding ann similar user panel structural equivalence"),
    # --- 42 ---
    ("Triangle count and local clustering coefficient are computed offline in Spark GraphFrames; pushing these into Memgraph MAGE was tried but the whole-graph traversal blew past the memory budget on the 80M-edge snapshot.", "problem", "technical", False,
     [("Triangle count", "algorithm"), ("clustering coefficient", "algorithm"), ("Spark GraphFrames", "library"), ("Memgraph", "database"), ("MAGE", "library")],
     [("Spark GraphFrames", "Memgraph", "REPLACES")],
     "which triangle-count path replaced the Memgraph MAGE attempt and why did the in-database version fall over",
     "triangle clustering coefficient spark graphframes memgraph mage memory"),
    # --- 43. noise ---
    ("Someone labelled every drawer in the engineering kitchen but only the knives drawer is empty and the spatulas drawer is a historical disaster area.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Graph schema for identity uses a supernode-avoidance pattern: every high-degree vertex gets sharded into virtual buckets linked by meta-edges so traversals fan out evenly rather than hammering one physical row.", "architecture", "technical", False,
     [("supernode-avoidance", "pattern"), ("virtual buckets", "pattern"), ("meta-edges", "pattern")],
     [],
     "which schema pattern splits high-degree vertices into virtual buckets to avoid hammering a single physical row",
     "supernode avoidance virtual bucket meta edge identity high degree"),
    # --- 45 ---
    ("Read replicas in Neo4j Fabric route cross-graph federated queries; a USE clause picks which constituent graph runs each sub-query and results merge back in the driver layer transparently.", "reference", "technical", False,
     [("Neo4j Fabric", "database"), ("USE", "command"), ("federated queries", "pattern")],
     [("Neo4j Fabric", "federated queries", "SUPPORTS")],
     "which Neo4j Fabric clause dispatches a sub-query to a constituent graph in the federated setup",
     "neo4j fabric use clause federated cross graph sub query driver"),
    # --- 46 ---
    ("Apache Age pushes graph reads through Postgres MVCC which plays nicely with the existing audit-trail readers; the write path incurs the heap-tuple overhead but throughput stays inside budget for the audit volume.", "fact", "technical", False,
     [("Apache Age", "database"), ("Postgres", "database"), ("MVCC", "concept"), ("audit-trail", "project")],
     [("Apache Age", "MVCC", "USES")],
     "which Postgres concurrency feature does Apache Age inherit for the audit-trail read path and what's the trade-off",
     "apache age postgres mvcc audit trail heap tuple throughput"),
    # --- 47 ---
    ("BFS over the follow graph uses bitmap-visited sets instead of hash sets in the hot loop; the working set fits in L2 for snapshots up to 10M vertices and the 4x speedup held across CPU generations.", "fact", "technical", False,
     [("BFS", "algorithm"), ("bitmap-visited", "pattern"), ("hash set", "concept"), ("L2", "concept")],
     [("bitmap-visited", "hash set", "REPLACES")],
     "which visited-set representation made BFS fit in L2 on 10M-vertex snapshots for a 4x speedup",
     "bfs bitmap visited hash set follow graph l2 cache speedup"),
    # --- 48 ---
    ("GQL reference implementation tracking lives in docs/graph/gql-notes.md; we log divergences from openCypher so the platform team can decide which to backport into our internal Cypher dialect.", "reference", "technical", False,
     [("GQL", "language"), ("openCypher", "language"), ("docs/graph/gql-notes.md", "file"), ("Cypher", "language")],
     [("GQL", "openCypher", "RELATED_TO")],
     "where is the running log of GQL versus openCypher divergences maintained for the platform team",
     "gql opencypher cypher notes divergence backport reference doc"),
    # --- 49 ---
    ("The query engine picks Cypher's USING INDEX hint sparingly because the cost model in Neo4j 5 usually wins; the hint survives only on the flaky predicate where selectivity stats lie on extreme skew.", "preference", "technical", False,
     [("Cypher", "language"), ("USING INDEX", "command"), ("Neo4j 5", "database"), ("selectivity", "concept")],
     [],
     "why is Cypher's USING INDEX hint rarely needed on Neo4j 5 and when does it still survive in prod queries",
     "cypher using index hint neo4j 5 cost model selectivity skew predicate"),
    # --- 50 ---
    ("SPARQL 1.1 property paths replaced a hand-rolled recursive CTE in the ontology traversal; the `rdfs:subClassOf*` expression is a single line and the planner turns it into the right transitive walk without our help.", "milestone", "technical", False,
     [("SPARQL 1.1", "language"), ("property paths", "pattern"), ("recursive CTE", "pattern"), ("rdfs:subClassOf*", "pattern")],
     [("property paths", "recursive CTE", "REPLACES")],
     "which SPARQL 1.1 feature replaced the recursive CTE for the subclass traversal in the ontology service",
     "sparql 1.1 property path recursive cte subclass ontology transitive"),
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
