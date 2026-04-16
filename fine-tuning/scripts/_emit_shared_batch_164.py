"""One-off emitter for shared-base batch-164 — technical domain (vector databases and ANN indexes: HNSW, IVF, PQ, DiskANN, quantization, hybrid search, filtered search, sharding).

Writes 50 rows to data/v2/shared/batch_164.tmp.jsonl with ids shared-08151..08200.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_164.tmp.jsonl"
ID_OFFSET = 8150

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Swapped Pinecone for Qdrant on the staging vector store; self-hosting on a single GPU box cut the monthly bill and let the team tune HNSW parameters that the managed tier hid entirely.", "decision", "technical", False,
     [("Pinecone", "database"), ("Qdrant", "database"), ("HNSW", "algorithm")],
     [("Qdrant", "Pinecone", "REPLACES"), ("Qdrant", "HNSW", "USES")],
     "which managed vector database did the staging stack drop in favour of a self-hosted option and why",
     "qdrant pinecone hnsw self host gpu staging vector swap tune"),
    # --- 2 ---
    ("HNSW ef_construction jumped from 128 to 400 on the main index; recall at k=10 climbed about three points and build time roughly tripled, which the nightly rebuild window absorbed.", "fact", "technical", False,
     [("HNSW", "algorithm"), ("ef_construction", "config"), ("nightly rebuild", "pattern")],
     [],
     "which HNSW build parameter did the team raise and what was the recall versus build time trade",
     "hnsw ef construction recall build time nightly rebuild k10"),
    # --- 3 ---
    ("Weaviate's hybrid BM25+dense search replaced the two-stage fan-out the frontend used to do against Elasticsearch and Qdrant separately; alpha=0.5 stays default and tenants override per query.", "architecture", "technical", False,
     [("Weaviate", "database"), ("BM25", "algorithm"), ("Elasticsearch", "database"), ("Qdrant", "database")],
     [("Weaviate", "Elasticsearch", "REPLACES"), ("Weaviate", "BM25", "USES")],
     "which Weaviate feature replaced the two-stage dense plus lexical fan-out the frontend was running",
     "weaviate hybrid bm25 dense alpha elasticsearch qdrant fan out tenant"),
    # --- 4 ---
    ("Milvus cluster runs IVF_PQ with nlist=4096 and m=16 for the 128-dim embeddings; DiskANN was benched on the same data but the cold-cache query p99 on SATA tipped it out of the running.", "decision", "technical", False,
     [("Milvus", "database"), ("IVF_PQ", "algorithm"), ("DiskANN", "algorithm"), ("SATA", "infrastructure")],
     [("Milvus", "IVF_PQ", "USES"), ("IVF_PQ", "DiskANN", "REPLACES")],
     "which ANN index won out on the Milvus cluster over DiskANN and which hardware signal drove the call",
     "milvus ivfpq diskann nlist pq sata cold cache p99 128 dim embed"),
    # --- 5 ---
    ("The pgvector extension switched from IVFFLAT to HNSW once the 0.5.0 release shipped; query latency on the 20M-row table fell from about 180 ms to 35 ms at the same recall target.", "milestone", "technical", False,
     [("pgvector", "database"), ("IVFFLAT", "algorithm"), ("HNSW", "algorithm"), ("0.5.0", "date")],
     [("HNSW", "IVFFLAT", "REPLACES")],
     "which pgvector index upgrade cut the 20M-row query latency and what release unlocked it",
     "pgvector hnsw ivfflat 0 5 0 latency recall 20 million row upgrade"),
    # --- 6 ---
    ("Binary quantization on Qdrant shrank the 768-dim float32 payload index from 47 GB to under 2 GB on the product-catalog collection; reranking with full vectors recovers about 97 percent of original recall.", "fact", "technical", False,
     [("Binary quantization", "method"), ("Qdrant", "database"), ("product-catalog", "project")],
     [("Qdrant", "Binary quantization", "USES")],
     "which quantization method shrank the product catalog index on Qdrant and how much recall does rerank recover",
     "binary quantization qdrant 768 float32 product catalog rerank recall"),
    # --- 7 ---
    ("Chose LanceDB over Chroma for the local desktop app; the Arrow-backed columnar layout lets the same file serve analytics and vector search without a second store.", "decision", "technical", False,
     [("LanceDB", "database"), ("Chroma", "database"), ("Arrow", "technology")],
     [("LanceDB", "Chroma", "REPLACES"), ("LanceDB", "Arrow", "USES")],
     "which embedded vector store replaced Chroma for the desktop app and what format choice sealed the pick",
     "lancedb chroma arrow desktop embed analytics columnar vector local"),
    # --- 8 ---
    ("Vespa's native tensor plus BM25 ranking expression now drives the search frontend; the previous Elasticsearch kNN plus Qdrant two-hop was retired after the rank-profile migration stabilised.", "architecture", "technical", False,
     [("Vespa", "database"), ("BM25", "algorithm"), ("Elasticsearch", "database"), ("Qdrant", "database"), ("rank-profile", "config")],
     [("Vespa", "Elasticsearch", "REPLACES"), ("Vespa", "Qdrant", "REPLACES")],
     "which Vespa capability collapsed the old kNN plus vector two-hop into a single ranked query",
     "vespa tensor bm25 rank profile elasticsearch qdrant two hop migration"),
    # --- 9 ---
    ("Turbopuffer handles the archival tier: cold embeddings older than 90 days get offloaded from Pinecone to Turbopuffer at roughly a tenth of the cost, with a ten-second warm-up penalty on first hit.", "architecture", "technical", False,
     [("Turbopuffer", "database"), ("Pinecone", "database"), ("archival tier", "pattern")],
     [("Turbopuffer", "Pinecone", "REPLACES")],
     "which archival vector store takes cold embeddings off Pinecone and what is the first-hit warm-up cost",
     "turbopuffer pinecone archive cold 90 day warm up tenth cost offload"),
    # --- 10. noise ---
    ("The office succulent collection got a new grow-light timer and the peperomia finally stopped stretching toward the window by Tuesday.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Zilliz Cloud's serverless tier backs the prototype environment; auto-scale handles the evening spike from the embedding batch job without holding a reserved cluster overnight.", "architecture", "technical", False,
     [("Zilliz Cloud", "service"), ("serverless", "pattern"), ("embedding batch job", "pattern")],
     [("Zilliz Cloud", "serverless", "USES")],
     "which managed Milvus tier hosts the prototype and how does it handle the evening embedding spike",
     "zilliz serverless prototype embed batch auto scale evening spike"),
    # --- 12 ---
    ("HNSW M parameter pinned at 16 for the 1024-dim collection; bumping to 32 doubled graph memory without a recall improvement that justified the extra RAM on the 64 GB node.", "decision", "technical", False,
     [("HNSW", "algorithm"), ("M parameter", "config"), ("64 GB node", "infrastructure")],
     [],
     "which HNSW M value did the team lock in for the 1024-dim index and what trade-off drove the cap",
     "hnsw m 16 32 graph memory 1024 dim recall 64 gb node pin"),
    # --- 13 ---
    ("Product quantization with m=8 subvectors and 8-bit centroids is the memory default on Milvus; scalar quantization was kept for the smaller 256-dim shard since PQ overshot the quality floor.", "architecture", "technical", False,
     [("Product quantization", "method"), ("Milvus", "database"), ("scalar quantization", "method")],
     [("Milvus", "Product quantization", "USES")],
     "which quantization scheme is the Milvus memory default and where does scalar quantization still apply",
     "product quantization scalar milvus 8 subvector centroid 256 dim"),
    # --- 14 ---
    ("Reranker stage uses a cross-encoder bge-reranker-large on the top-50 candidates from dense search; the single-model two-stage pipeline beat a bigger dense-only retriever at a fraction of the index cost.", "decision", "technical", False,
     [("cross-encoder", "method"), ("bge-reranker-large", "framework"), ("dense search", "method")],
     [("bge-reranker-large", "dense search", "IMPROVES_ON")],
     "which cross-encoder reranker sits on top of dense retrieval and which alternative did it beat on cost",
     "bge reranker large cross encoder top 50 dense two stage cost"),
    # --- 15 ---
    ("Filtered search in Qdrant uses payload indexes on tenant_id and category; without the indexes the filter was post-filter and dropped recall to near zero on highly selective tenants.", "problem", "technical", False,
     [("Qdrant", "database"), ("payload index", "config"), ("post-filter", "pattern")],
     [("Qdrant", "payload index", "USES"), ("payload index", "post-filter", "FIXES")],
     "which Qdrant configuration fixed the near-zero recall on selective tenants from post-filtering",
     "qdrant payload index tenant category filter post filter recall"),
    # --- 16 ---
    ("MyScale is the analytical sidecar for vector plus SQL workloads; joining embeddings against a 400M-row fact table stays interactive where a bolt-on Qdrant plus ClickHouse dance stalled.", "decision", "technical", False,
     [("MyScale", "database"), ("Qdrant", "database"), ("ClickHouse", "database"), ("fact table", "pattern")],
     [("MyScale", "Qdrant", "REPLACES"), ("MyScale", "ClickHouse", "REPLACES")],
     "which combined vector plus SQL engine replaced the Qdrant plus ClickHouse two-store pattern",
     "myscale qdrant clickhouse vector sql join 400m fact table analytical"),
    # --- 17 ---
    ("DiskANN's Vamana graph now serves the 200M-embedding archive; NVMe random reads plus beamwidth=4 held p95 under 25 ms while keeping the RAM footprint at roughly a tenth of HNSW.", "milestone", "technical", False,
     [("DiskANN", "algorithm"), ("Vamana", "algorithm"), ("NVMe", "infrastructure"), ("HNSW", "algorithm")],
     [("DiskANN", "Vamana", "USES"), ("DiskANN", "HNSW", "IMPROVES_ON")],
     "which DiskANN graph structure serves the 200M archive and how does its RAM footprint compare to HNSW",
     "diskann vamana nvme beamwidth 200m archive ram footprint p95"),
    # --- 18 ---
    ("Typesense vector mode runs alongside its keyword index on the docs-site search box; the single binary deploys on a 2 GB VPS which ruled out a Milvus or Weaviate cluster for that surface.", "decision", "technical", False,
     [("Typesense", "database"), ("Milvus", "database"), ("Weaviate", "database"), ("2 GB VPS", "infrastructure")],
     [("Typesense", "Milvus", "REPLACES"), ("Typesense", "Weaviate", "REPLACES")],
     "which lightweight vector engine runs on the docs-site VPS and which clustered options were ruled out",
     "typesense milvus weaviate 2 gb vps docs site keyword vector binary"),
    # --- 19 ---
    ("Elasticsearch 8.8 kNN with int8 quantization serves the logs-search autocomplete; the pre-8.x plugin era we lived through turned the native ANN support into an easy migration target.", "milestone", "technical", False,
     [("Elasticsearch", "database"), ("kNN", "algorithm"), ("int8 quantization", "method"), ("8.8", "date")],
     [("Elasticsearch", "kNN", "USES"), ("Elasticsearch", "int8 quantization", "USES")],
     "which Elasticsearch release brought native kNN plus int8 quantization to the logs autocomplete surface",
     "elasticsearch 8 8 knn int8 quantization logs autocomplete plugin"),
    # --- 20 ---
    ("ScaNN powers the Google-style ads retrieval on the experimental branch; the asymmetric hashing and anisotropic quantization combination beat flat HNSW on both recall and query throughput.", "fact", "technical", False,
     [("ScaNN", "algorithm"), ("asymmetric hashing", "method"), ("anisotropic quantization", "method"), ("HNSW", "algorithm")],
     [("ScaNN", "HNSW", "IMPROVES_ON")],
     "which ANN library beat flat HNSW on ads retrieval and which two techniques did it combine",
     "scann asymmetric hashing anisotropic quantization hnsw ads retrieval"),
    # --- 21 ---
    ("HNSW ef_search tuned per query via a difficulty hint: ambiguous long queries use ef=256 while exact-match hits fall back to ef=64, which trimmed mean latency without hurting tail recall.", "architecture", "technical", False,
     [("HNSW", "algorithm"), ("ef_search", "config"), ("difficulty hint", "pattern")],
     [],
     "how does the retrieval stack vary HNSW ef_search per query and what latency and recall trade did it strike",
     "hnsw ef search difficulty hint 64 256 ambiguous tail latency recall"),
    # --- 22 ---
    ("Milvus sharding strategy keyed by tenant_id rather than hash; the routing layer pins every tenant query to one shard and removes the cross-shard merge that bled latency on the legacy layout.", "architecture", "technical", False,
     [("Milvus", "database"), ("sharding", "pattern"), ("tenant_id", "config"), ("cross-shard merge", "pattern")],
     [("sharding", "cross-shard merge", "REPLACES")],
     "which Milvus sharding key choice eliminated the cross-shard merge latency hit on tenant queries",
     "milvus shard tenant id hash routing cross shard merge latency"),
    # --- 23 ---
    ("Replica count on the Qdrant cluster is three with write-consistency set to majority; the previous single-replica deploy had a node-reboot window that dropped writes for about ninety seconds.", "decision", "technical", False,
     [("Qdrant", "database"), ("three", "config"), ("majority", "config"), ("single-replica", "pattern")],
     [("three", "single-replica", "REPLACES")],
     "which replication and consistency setting did the Qdrant cluster land on and what outage drove the change",
     "qdrant replica three majority consistency single node reboot write"),
    # --- 24 ---
    ("Consistency level on Milvus queries dropped from Strong to Bounded for the recommendations pipeline; the five-second staleness is acceptable and the cluster throughput roughly doubled on the same nodes.", "decision", "technical", False,
     [("Milvus", "database"), ("Strong", "config"), ("Bounded", "config"), ("recommendations pipeline", "project")],
     [("Bounded", "Strong", "REPLACES")],
     "which Milvus consistency level replaced Strong for recommendations and what throughput win did it unlock",
     "milvus strong bounded consistency recommendation staleness throughput"),
    # --- 25 ---
    ("Cohere's Embed v3 plus a cross-encoder reranker replaced the OpenAI text-embedding-ada-002 pipeline; retrieval MRR on the internal evaluation set climbed from 0.71 to 0.88.", "milestone", "technical", False,
     [("Cohere", "organization"), ("Embed v3", "framework"), ("cross-encoder", "method"), ("text-embedding-ada-002", "framework")],
     [("Embed v3", "text-embedding-ada-002", "REPLACES")],
     "which embedding plus reranker stack replaced ada-002 and what MRR gain did the internal eval show",
     "cohere embed v3 cross encoder ada 002 mrr 0 71 0 88 retrieval"),
    # --- 26 ---
    ("Prefer HNSW over IVF for collections under 10M rows where memory budget allows; IVF wins once the index exceeds RAM and disk-based search tolerates its coarser partitioning.", "preference", "technical", False,
     [("HNSW", "algorithm"), ("IVF", "algorithm"), ("RAM", "infrastructure")],
     [],
     "when does the team prefer HNSW over IVF and where does IVF still earn its place",
     "hnsw ivf prefer 10m row ram memory budget disk coarse partition"),
    # --- 27 ---
    ("Reference: the original HNSW paper by Malkov and Yashunin 2016 remains the canonical description of the hierarchical small-world graph and its search routine.", "reference", "technical", False,
     [("HNSW", "algorithm"), ("Malkov", "person"), ("Yashunin", "person")],
     [("HNSW", "Malkov", "AUTHORED_BY"), ("HNSW", "Yashunin", "AUTHORED_BY")],
     "which 2016 publication introduced HNSW and who were its authors",
     "hnsw malkov yashunin 2016 paper hierarchical small world graph"),
    # --- 28 ---
    ("Reference: the DiskANN Vamana paper from Microsoft Research 2019 details the greedy-plus-prune graph construction that targets SSD random-read patterns.", "reference", "technical", False,
     [("DiskANN", "algorithm"), ("Vamana", "algorithm"), ("Microsoft Research", "organization"), ("SSD", "infrastructure")],
     [("DiskANN", "Microsoft Research", "AUTHORED_BY")],
     "which 2019 Microsoft Research paper introduced the Vamana graph that DiskANN uses for SSD-friendly ANN",
     "diskann vamana microsoft research 2019 greedy prune ssd random read"),
    # --- 29 ---
    ("Prefer binary quantization for large-scale recall-heavy pipelines where a rerank stage follows; avoid it on short tail-queries where the quantization noise dominates the small candidate pool.", "preference", "technical", False,
     [("binary quantization", "method"), ("rerank stage", "pattern"), ("tail-queries", "pattern")],
     [],
     "when does the team reach for binary quantization and where does it actively hurt retrieval",
     "binary quantization prefer rerank stage tail query noise candidate"),
    # --- 30 ---
    ("Problem: Chroma on the laptop corrupted its index after an abrupt power cut and had no journal to recover from; switched the local-dev stack to LanceDB which survives crashes via its write-ahead log.", "problem", "technical", False,
     [("Chroma", "database"), ("LanceDB", "database"), ("write-ahead log", "pattern")],
     [("LanceDB", "Chroma", "REPLACES"), ("LanceDB", "write-ahead log", "USES")],
     "which local vector store replaced Chroma after a power-cut corruption and why",
     "chroma lancedb power cut corrupt write ahead log local dev laptop"),
    # --- 31 ---
    ("Hybrid search weighting on the support knowledge base uses reciprocal rank fusion with k=60; the earlier linear alpha blend of BM25 and dense scores was too sensitive to embedding magnitude drift.", "decision", "technical", False,
     [("reciprocal rank fusion", "algorithm"), ("BM25", "algorithm"), ("linear alpha blend", "method")],
     [("reciprocal rank fusion", "linear alpha blend", "REPLACES")],
     "which hybrid-search fusion method replaced the linear alpha blend and why",
     "reciprocal rank fusion bm25 dense alpha blend k 60 embedding drift"),
    # --- 32 ---
    ("A value of ef_search=200 on the HNSW index at serve time landed p95 latency at 38 ms and recall@10 at 0.94 on the 15M-row collection; ef=100 shaved 6 ms but cost 1.5 recall points.", "fact", "technical", False,
     [("HNSW", "algorithm"), ("ef_search", "config"), ("15M-row collection", "project")],
     [],
     "which HNSW ef_search value did serving land on and what latency and recall trade did it reflect",
     "hnsw ef search 200 100 p95 38 ms recall 0 94 15m row collection"),
    # --- 33 ---
    ("Problem: Pinecone pod hit its 5M-vector quota on p1.x1; migrated the overflow namespaces to Qdrant Cloud, keeping tier-1 tenants on Pinecone for its multi-region failover.", "problem", "technical", False,
     [("Pinecone", "database"), ("Qdrant Cloud", "service"), ("p1.x1", "config"), ("multi-region failover", "pattern")],
     [("Qdrant Cloud", "Pinecone", "REPLACES")],
     "which overflow strategy handled the Pinecone pod quota and why did tier-1 tenants stay on Pinecone",
     "pinecone qdrant cloud p1 x1 quota multi region failover tier 1"),
    # --- 34 ---
    ("Architecture: metadata payload lives next to the vector in Qdrant; joining against Postgres for filters was slower than push-down filtered search once payload indexes existed on the hot keys.", "architecture", "technical", False,
     [("Qdrant", "database"), ("Postgres", "database"), ("payload index", "config")],
     [("Qdrant", "Postgres", "REPLACES")],
     "how does the filter layout push metadata into Qdrant rather than joining Postgres at query time",
     "qdrant postgres payload index filter push down join hot key metadata"),
    # --- 35 ---
    ("Prefer Vespa for workloads that need structured ranking with learned-to-rank models on top of ANN recall; for pure dense retrieval the operational weight rarely pays back.", "preference", "technical", False,
     [("Vespa", "database"), ("learned-to-rank", "method"), ("ANN", "algorithm")],
     [],
     "when does the team pick Vespa and which workloads do not justify its operational cost",
     "vespa learned rank ann dense retrieval operational structured model"),
    # --- 36 ---
    ("Architecture: read traffic fans out to two Qdrant replicas behind a smart client that picks the lowest-latency node per request; writes still go to the primary and replicate asynchronously.", "architecture", "technical", False,
     [("Qdrant", "database"), ("replica", "pattern"), ("smart client", "pattern"), ("primary", "pattern")],
     [("Qdrant", "smart client", "USES")],
     "how does the routing layer split reads and writes across Qdrant replicas and the primary",
     "qdrant replica smart client latency primary async write read fan"),
    # --- 37 ---
    ("Milestone: the 500M-embedding migration from Pinecone to self-hosted Milvus completed over a three-week dual-write window; cutover moved traffic without a single cache-miss spike on the frontend.", "milestone", "technical", False,
     [("Pinecone", "database"), ("Milvus", "database"), ("dual-write", "pattern"), ("cutover", "pattern")],
     [("Milvus", "Pinecone", "REPLACES")],
     "which migration milestone moved 500M embeddings and how did the dual-write window protect the cutover",
     "pinecone milvus migrate 500m embedding dual write three week cutover"),
    # --- 38 ---
    ("Reference: Facebook AI Similarity Search (FAISS) from Jeff Johnson et al 2017 remains the reference implementation for IVF, PQ, and IVFPQ on GPU.", "reference", "technical", False,
     [("FAISS", "library"), ("Jeff Johnson", "person"), ("IVF", "algorithm"), ("PQ", "algorithm"), ("IVFPQ", "algorithm")],
     [("FAISS", "Jeff Johnson", "AUTHORED_BY"), ("FAISS", "IVF", "IMPLEMENTS"), ("FAISS", "IVFPQ", "IMPLEMENTS")],
     "which library is the canonical reference for IVF and IVFPQ on GPU and who originally published it",
     "faiss jeff johnson 2017 ivf pq ivfpq gpu facebook reference ann"),
    # --- 39 ---
    ("Problem: the 1536-dim OpenAI embeddings overshot Qdrant's default in-RAM budget on the 30M-row collection; scalar quantization to 8-bit halved the memory at roughly 0.5 recall points cost.", "problem", "technical", False,
     [("OpenAI", "organization"), ("Qdrant", "database"), ("scalar quantization", "method"), ("1536-dim", "config")],
     [("Qdrant", "scalar quantization", "USES")],
     "which quantization step rescued the 1536-dim OpenAI embeddings on Qdrant and what was the recall cost",
     "qdrant openai 1536 dim 30m row scalar quantization 8 bit ram"),
    # --- 40 ---
    ("Architecture: the reranker corpus pairs hard negatives mined from top-50 retrieval misses; random negatives plateaued the cross-encoder while mined negatives drove MRR up another four points.", "architecture", "technical", False,
     [("reranker", "method"), ("hard negatives", "pattern"), ("cross-encoder", "method"), ("MRR", "concept")],
     [("hard negatives", "reranker", "APPLIES_TO")],
     "which negative-sampling strategy drove the cross-encoder MRR past the random-negative plateau",
     "reranker hard negative top 50 mine random plateau cross encoder mrr"),
    # --- 41 ---
    ("Decision: dropped Elasticsearch kNN for the primary retrieval path after benchmarking showed Weaviate's HNSW implementation beat it by roughly a factor of three on recall-normalised QPS.", "decision", "technical", False,
     [("Elasticsearch", "database"), ("Weaviate", "database"), ("HNSW", "algorithm"), ("QPS", "concept")],
     [("Weaviate", "Elasticsearch", "REPLACES")],
     "which benchmark result drove the drop of Elasticsearch kNN in favour of Weaviate HNSW",
     "elasticsearch weaviate hnsw knn qps recall benchmark factor three"),
    # --- 42 ---
    ("Milestone: Qdrant 1.8 filterable HNSW shipped and replaced the pre-filter plus re-search hack the backend did on high-selectivity tenants; median latency for those queries dropped tenfold.", "milestone", "technical", False,
     [("Qdrant", "database"), ("1.8", "date"), ("filterable HNSW", "algorithm"), ("pre-filter", "pattern")],
     [("filterable HNSW", "pre-filter", "REPLACES")],
     "which Qdrant 1.8 feature retired the pre-filter plus re-search workaround on high-selectivity tenants",
     "qdrant 1 8 filterable hnsw pre filter re search selectivity tenant"),
    # --- 43. noise ---
    ("Bought a second monitor arm for the standing desk and the cable tray clears the keyboard tray by about two centimetres now.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Preference: for new projects start with pgvector and HNSW; graduate to Qdrant or Milvus only once the row count exceeds 50M or multi-tenant sharding becomes a real cost.", "preference", "technical", False,
     [("pgvector", "database"), ("HNSW", "algorithm"), ("Qdrant", "database"), ("Milvus", "database")],
     [("pgvector", "HNSW", "USES")],
     "which starter vector store does the team recommend and what signal prompts a graduation to Qdrant or Milvus",
     "pgvector hnsw qdrant milvus starter project 50m row multi tenant"),
    # --- 45 ---
    ("Fact: Weaviate's PQ implementation supports segment=96 for 1536-dim vectors at 6x compression with roughly 1.5 percent recall drop on the MTEB-retrieval benchmark we ran internally.", "fact", "technical", False,
     [("Weaviate", "database"), ("PQ", "method"), ("1536-dim", "config"), ("MTEB-retrieval", "project")],
     [("Weaviate", "PQ", "USES")],
     "which Weaviate PQ segment count fits 1536-dim vectors at 6x compression and what recall drop did MTEB show",
     "weaviate pq 96 segment 1536 dim 6x compression mteb retrieval recall"),
    # --- 46 ---
    ("Problem: Pinecone serverless cold-start on the eu-west index pushed first-query latency past two seconds; moved to a pod-based deployment for the latency-sensitive tenants and kept serverless for nightly batch.", "problem", "technical", False,
     [("Pinecone", "database"), ("serverless", "pattern"), ("eu-west", "place"), ("pod-based", "pattern")],
     [("pod-based", "serverless", "REPLACES")],
     "which Pinecone deployment mode replaced serverless for latency-sensitive tenants and what forced the change",
     "pinecone serverless pod eu west cold start latency two second batch"),
    # --- 47 ---
    ("Architecture: the retrieval tier accepts the filter predicate as a Qdrant JSON expression and the reranker stage receives top-50 results plus their payload; no round-trip to Postgres sits in the hot path.", "architecture", "technical", False,
     [("Qdrant", "database"), ("reranker", "method"), ("Postgres", "database"), ("hot path", "pattern")],
     [],
     "how does the retrieval tier keep Postgres out of the hot path during filtered search plus rerank",
     "qdrant json filter reranker top 50 payload postgres hot path"),
    # --- 48 ---
    ("Reference: Google's ScaNN paper by Guo et al 2020 introduced anisotropic vector quantization that motivated many of the subsequent quantization tweaks in Qdrant and Milvus.", "reference", "technical", False,
     [("ScaNN", "algorithm"), ("Guo", "person"), ("Qdrant", "database"), ("Milvus", "database"), ("anisotropic vector quantization", "method")],
     [("ScaNN", "Guo", "AUTHORED_BY"), ("Qdrant", "anisotropic vector quantization", "APPLIES_TO")],
     "which retrieval research publication from 2020 established the anisotropic quantization idea later adopted by several ANN engines",
     "scann guo 2020 anisotropic vector quantization qdrant milvus paper"),
    # --- 49 ---
    ("Reference: the IVFPQ combination traces to Jegou, Douze, and Schmid 2011 on product quantization for nearest neighbour search; still the baseline every new ANN library benchmarks against.", "reference", "technical", False,
     [("IVFPQ", "algorithm"), ("Jegou", "person"), ("Douze", "person"), ("Schmid", "person"), ("product quantization", "method")],
     [("IVFPQ", "Jegou", "AUTHORED_BY"), ("IVFPQ", "product quantization", "USES")],
     "which 2011 paper established product quantization as the baseline behind IVFPQ",
     "ivfpq jegou douze schmid 2011 product quantization nearest neighbour"),
    # --- 50 ---
    ("Milestone: the hybrid lexical-plus-dense pipeline on Vespa hit 0.91 NDCG@10 on the internal benchmark, beating the standalone Qdrant dense-only baseline at 0.83 by a full eight points.", "milestone", "technical", False,
     [("Vespa", "database"), ("Qdrant", "database"), ("NDCG@10", "concept"), ("hybrid lexical-plus-dense", "pattern")],
     [("Vespa", "Qdrant", "IMPROVES_ON")],
     "which hybrid lexical-plus-dense pipeline milestone topped the Qdrant dense-only baseline on NDCG@10",
     "vespa qdrant ndcg 10 hybrid lexical dense benchmark 0 91 0 83"),
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
