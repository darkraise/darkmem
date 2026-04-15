"""One-off emitter for shared-base batch-069 — technical domain (search and information-retrieval systems).

Writes 50 rows to data/v2/shared/batch_069.tmp.jsonl with ids shared-03401..03450.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_069.tmp.jsonl"
ID_OFFSET = 3400

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("OpenSearch replaced Elasticsearch on the log analytics cluster after the SSPL relicense; the API surface stayed compatible enough to keep most queries unchanged.", "decision", "technical", False,
     [("OpenSearch", "service"), ("Elasticsearch", "service"), ("SSPL", "concept")],
     [("OpenSearch", "Elasticsearch", "REPLACES")],
     "which search engine took over from Elasticsearch on the log cluster",
     "fork license swap log analytics API compatibility surface"),
    # --- 2 ---
    ("BM25 replaced TF-IDF as the default similarity in the catalog index; length normalization handled long product descriptions far more gracefully.", "decision", "technical", False,
     [("BM25", "algorithm"), ("TF-IDF", "algorithm")],
     [("BM25", "TF-IDF", "REPLACES")],
     "which similarity scoring took over from TF-IDF on the catalog index",
     "scoring length normalize product description swap default"),
    # --- 3 ---
    ("HNSW improved on IVF-PQ for the small-to-medium recall benchmark; recall@10 climbed from 0.86 to 0.97 at the same query budget.", "fact", "technical", False,
     [("HNSW", "algorithm"), ("IVF-PQ", "algorithm")],
     [("HNSW", "IVF-PQ", "IMPROVES_ON")],
     "which vector index beat IVF-PQ on the small corpus recall test",
     "graph quantization recall benchmark query budget rise"),
    # --- 4 ---
    ("Lucene segments are immutable on disk; a merge policy compacts them in the background, which is why deletes are cheap markers and not in-place edits.", "fact", "technical", False,
     [("Lucene", "library")],
     [],
     "why are deletes cheap on a Lucene segment until the next merge runs",
     "immutable segment merge background delete tombstone marker"),
    # --- 5 ---
    ("Reciprocal Rank Fusion combined BM25 and dense retrieval results on the hybrid pipeline; nDCG@10 rose 8 points without per-query weight tuning.", "milestone", "technical", False,
     [("Reciprocal Rank Fusion", "algorithm"), ("BM25", "algorithm")],
     [],
     "which fusion method merged the lexical and dense lists for the hybrid run",
     "rank fusion lexical dense combine nDCG no weight tune"),
    # --- 6 ---
    ("Meilisearch was preferred over a custom Postgres trigram setup for the docs site search; typo tolerance and prefix ranking shipped out of the box.", "preference", "technical", False,
     [("Meilisearch", "service"), ("Postgres", "database")],
     [("Meilisearch", "Postgres", "PREFERS")],
     "which search engine beat the Postgres trigram homegrown for docs search",
     "typo tolerance prefix ranking docs site box ship swap"),
    # --- 7 ---
    ("Typesense replaced Algolia on the e-commerce site; the self-hosted footprint stayed cheap and the curation API matched what the merch team needed.", "decision", "technical", False,
     [("Typesense", "service"), ("Algolia", "service")],
     [("Typesense", "Algolia", "REPLACES")],
     "which search service displaced Algolia on the e-commerce front-end",
     "self host curation merch team cheap footprint swap"),
    # --- 8 ---
    ("Vespa handled the personalized news feed at scale; tensor expressions in the ranking phase kept feature blending inside the engine, not in a sidecar service.", "architecture", "technical", False,
     [("Vespa", "service")],
     [],
     "which engine kept feature blending inside the ranker for the news feed",
     "tensor ranking phase feature blend sidecar avoid scale"),
    # --- 9 ---
    ("Solr stayed on the legacy intranet search; the admin UI and config-set workflow were familiar to the librarians and the corpus barely changed.", "fact", "technical", False,
     [("Solr", "service")],
     [],
     "which search engine held the intranet despite the modernization push",
     "admin UI config set legacy intranet librarian familiar"),
    # --- 10. noise ---
    ("Hold on, my index is still warming up.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("LSH was rejected for the deduplication pipeline; recall on near-duplicate webpages lagged HNSW by 12 points at the same memory budget.", "decision", "technical", False,
     [("LSH", "algorithm"), ("HNSW", "algorithm")],
     [("HNSW", "LSH", "IMPROVES_ON")],
     "why did LSH lose the dedup pipeline shootout to HNSW",
     "near duplicate recall memory budget hash bucket lose"),
    # --- 12 ---
    ("ColBERT late-interaction reranking lifted MRR@10 from 0.41 to 0.58 on the legal QA corpus; the storage cost for token embeddings was the painful trade-off.", "fact", "technical", False,
     [("ColBERT", "method"), ("MRR@10", "concept")],
     [],
     "which reranker lifted MRR on the legal QA corpus and what was the cost",
     "late interaction token embed storage trade off rerank lift"),
    # --- 13 ---
    ("Cross-encoder reranking on top of BM25 beat dense single-vector retrieval on the FAQ benchmark; the candidate pool was small enough that the latency hit was acceptable.", "fact", "technical", False,
     [("BM25", "algorithm")],
     [],
     "which two-stage setup beat single-vector dense on the FAQ task",
     "cross encoder rerank candidate pool small latency accept"),
    # --- 14 ---
    ("Faiss IVF-PQ was preferred over a flat index for the 50M-vector corpus; recall@100 stayed above 0.95 while memory dropped from 200 GB to 12 GB.", "preference", "technical", False,
     [("Faiss", "library"), ("IVF-PQ", "algorithm")],
     [],
     "which Faiss index handled the 50M-vector corpus under tight memory",
     "inverted file product quantization memory recall corpus huge"),
    # --- 15 ---
    ("ScaNN replaced HNSW on the recommendation candidate generator; the asymmetric hashing path served 10x QPS at the same recall on the GPU node.", "decision", "technical", False,
     [("ScaNN", "library"), ("HNSW", "algorithm"), ("GPU", "infrastructure")],
     [("ScaNN", "HNSW", "REPLACES")],
     "which ANN library took over from HNSW on the recommender candidate gen",
     "asymmetric hash QPS GPU recall recommend candidate swap"),
    # --- 16 ---
    ("LambdaMART trained the learning-to-rank model on the search clickstream; nDCG@10 lifted 6 points over the hand-tuned function score.", "milestone", "technical", False,
     [("LambdaMART", "algorithm"), ("nDCG@10", "concept")],
     [],
     "which LTR algorithm trained the click model that lifted the nDCG bar",
     "learning to rank clickstream gradient boost function score"),
    # --- 17 ---
    ("Elasticsearch function_score queries were retired after the LambdaMART rollout; tuning by hand could not catch the model's per-query feature weighting.", "decision", "technical", False,
     [("Elasticsearch", "service"), ("LambdaMART", "algorithm")],
     [("LambdaMART", "Elasticsearch", "REPLACES")],
     "which scoring approach displaced the hand-tuned function_score queries",
     "function score retire model per query feature weight"),
    # --- 18 ---
    ("Qdrant carried the dense vector path for the multilingual support search; payload filtering on language code happened inside the same query, not as a post-filter.", "architecture", "technical", False,
     [("Qdrant", "database")],
     [],
     "which vector store kept the language filter inside the dense query",
     "payload filter language code single query post avoid"),
    # --- 19 ---
    ("Weaviate hybrid search blended BM25 and HNSW with an alpha knob; the default 0.5 over-weighted the dense path on short queries and was tuned to 0.3.", "problem", "technical", False,
     [("Weaviate", "database"), ("BM25", "algorithm"), ("HNSW", "algorithm")],
     [],
     "which hybrid search knob was tuned away from the default for short queries",
     "alpha blend short query dense over weight tune lower"),
    # --- 20 ---
    ("Pinecone was rejected for the on-prem deployment; the managed-only model did not fit the air-gapped customer's compliance requirement.", "decision", "technical", False,
     [("Pinecone", "service")],
     [],
     "why was Pinecone rejected for the on-prem search deployment",
     "managed only air gap compliance customer reject vector"),
    # --- 21 ---
    ("Milvus was deployed on Kubernetes for the image search workload; the data node and index node split let storage and indexing scale independently.", "architecture", "technical", False,
     [("Milvus", "database"), ("Kubernetes", "platform")],
     [("Milvus", "Kubernetes", "DEPLOYED_ON")],
     "which vector database split data and index nodes for the image search",
     "image search node split scale independent index storage"),
    # --- 22 ---
    ("recall@k and MRR were the headline metrics on the retrieval evaluation harness; nDCG was kept as a secondary view because the graded judgments were sparse.", "fact", "technical", False,
     [("recall@k", "concept"), ("MRR", "concept"), ("nDCG", "concept")],
     [],
     "which metrics led the retrieval harness when graded labels were thin",
     "evaluation metric headline secondary judgment sparse bar"),
    # --- 23 ---
    ("BEIR benchmark exposed a domain gap on the dense retriever; recall on FiQA dropped 18 points versus MSMARCO, prompting a domain-tuned model swap.", "fact", "technical", False,
     [("BEIR", "publication"), ("FiQA", "publication"), ("MSMARCO", "publication")],
     [],
     "which benchmark exposed the dense retriever domain gap on finance text",
     "domain shift finance recall drop benchmark prompt swap"),
    # --- 24 ---
    ("MTEB scoreboard ranked the candidate embedding models; bge-large beat e5-base by 4 points on average across retrieval tasks at twice the inference cost.", "fact", "technical", False,
     [("MTEB", "publication"), ("bge-large", "method"), ("e5-base", "method")],
     [],
     "which embedding model led the MTEB retrieval slice and at what cost",
     "embedding leaderboard average retrieval slice cost trade"),
    # --- 25 ---
    ("Sparse retrieval with SPLADE replaced a hand-tuned synonym list on the medical search; learned term expansion caught suffix variants the synonym file kept missing.", "decision", "technical", False,
     [("SPLADE", "method")],
     [],
     "which sparse retriever displaced the hand-curated synonym list for medical search",
     "learned expansion suffix variant synonym retire medical"),
    # --- 26 ---
    ("Elasticsearch reindex API copied the production index into the new mapping; alias swap kept the search downtime to a single second.", "architecture", "technical", False,
     [("Elasticsearch", "service")],
     [],
     "which Elasticsearch operation enabled the zero-downtime mapping change",
     "reindex alias swap zero downtime mapping change index"),
    # --- 27 ---
    ("ngram tokenizer was preferred over wildcard queries for the in-app search-as-you-type; latency dropped from 280 ms to 22 ms on the busiest field.", "preference", "technical", False,
     [("ngram", "method")],
     [],
     "which tokenizer choice replaced wildcard queries for as-you-type search",
     "edge ngram wildcard prefix latency drop in app type"),
    # --- 28 ---
    ("Lucene's FST powered the suggest component; the finite state transducer kept the autosuggest dictionary inside RAM at 40 MB instead of 300 MB.", "fact", "technical", False,
     [("Lucene", "library"), ("FST", "algorithm")],
     [],
     "which Lucene structure shrank the suggest dictionary footprint to 40 MB",
     "finite state transducer suggest RAM dictionary footprint shrink"),
    # --- 29 ---
    ("Vespa's tensor framework let the team express the cross-feature ranking model in stanza; expressing it as Elasticsearch painless was rejected on maintainability.", "decision", "technical", False,
     [("Vespa", "service"), ("Elasticsearch", "service"), ("painless", "language")],
     [("Vespa", "Elasticsearch", "PREFERS")],
     "which engine's expression layer beat painless on cross-feature ranking",
     "tensor express stanza painless maintain reject ranking"),
    # --- 30 ---
    ("OpenSearch k-NN plugin used Lucene's HNSW implementation in 2.4 onward; the engine swap from nmslib cut memory overhead by roughly a third on the same recall.", "fact", "technical", False,
     [("OpenSearch", "service"), ("Lucene", "library"), ("HNSW", "algorithm"), ("nmslib", "library")],
     [("Lucene", "nmslib", "REPLACES")],
     "which HNSW backend took over inside the OpenSearch k-NN plugin",
     "engine swap memory overhead recall plugin backend cut"),
    # --- 31 ---
    ("Query understanding rewrote the user's free text into a structured filter plus a free-text remnant; precision@10 climbed without hurting recall on the broad queries.", "architecture", "technical", False,
     [("precision@10", "concept")],
     [],
     "which pipeline stage lifted precision without losing recall on broad queries",
     "query rewrite structured filter free text remnant precision"),
    # --- 32 ---
    ("DPR-style dual encoders carried the first-stage retrieval for the chatbot RAG; ANN over the passage embeddings replaced the BM25 first stage on the technical corpus.", "decision", "technical", False,
     [("DPR", "method"), ("BM25", "algorithm"), ("ANN", "algorithm")],
     [("DPR", "BM25", "REPLACES")],
     "which retriever displaced BM25 as the first stage in the RAG pipeline",
     "dual encoder dense first stage RAG technical corpus swap"),
    # --- 33 ---
    ("Hybrid retrieval landed on 2026-02-18 in production; BM25 plus dense plus RRF beat each individual retriever by 5 points nDCG@10 on the QA holdout.", "milestone", "technical", False,
     [("BM25", "algorithm"), ("RRF", "algorithm"), ("2026-02-18", "date")],
     [],
     "when did the hybrid retrieval pipeline ship and how much did it lift nDCG",
     "hybrid lexical dense fusion ship date production lift bar"),
    # --- 34. noise ---
     ("Give me a tick, the rerank batch is queued.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Anserini was the reference toolkit for reproducing the BM25 baselines on TREC topics; deviation from the published numbers stayed under 0.5 nDCG points.", "reference", "technical", False,
     [("Anserini", "tool"), ("BM25", "algorithm"), ("TREC", "publication")],
     [],
     "which toolkit served as the reproducible BM25 baseline on TREC topics",
     "reference baseline reproducibility deviation publication topic"),
    # --- 36 ---
    ("PyTerrier wrapped the experiment harness for retrieval ablations; pipe operators kept the multi-stage pipelines readable in a notebook.", "architecture", "technical", False,
     [("PyTerrier", "library")],
     [],
     "which Python toolkit wrapped the retrieval ablation experiments",
     "pipe operator notebook multi stage retrieval ablation harness"),
    # --- 37 ---
    ("Search relevance regressions caught a synonym map bug; nightly TREC eval against a held-out judgment set blocked the deploy automatically.", "problem", "technical", False,
     [("TREC", "publication")],
     [],
     "which automated check blocked the synonym map regression from shipping",
     "regression synonym map nightly evaluation deploy block judge"),
    # --- 38 ---
    ("Pairwise judgments from clicks were noisy; the team adopted SDBN click models to factor out position bias before training the LTR ranker.", "decision", "technical", False,
     [("SDBN", "method"), ("LTR", "concept")],
     [],
     "which click model fixed the position bias before LTR training",
     "click model position bias dynamic Bayesian factor pairwise"),
    # --- 39 ---
    ("Cohere Rerank replaced an in-house cross-encoder for the long-tail queries; nDCG@10 climbed 3 points and the team avoided the GPU serving overhead.", "decision", "technical", False,
     [("Cohere Rerank", "service"), ("cross-encoder", "method")],
     [("Cohere Rerank", "cross-encoder", "REPLACES")],
     "which rerank service displaced the in-house cross-encoder model",
     "long tail rerank nDCG GPU serve overhead avoid swap"),
    # --- 40 ---
    ("Manticore Search was tested as a Sphinx-compatible drop-in; throughput on the keyword-only workload doubled, but multi-tenant isolation pushed the team back to OpenSearch.", "problem", "technical", False,
     [("Manticore Search", "service"), ("Sphinx", "service"), ("OpenSearch", "service")],
     [],
     "which Sphinx-compatible engine was tried and why did it not stick",
     "drop in throughput double tenant isolation push back swap"),
    # --- 41 ---
    ("Zinc Search ran on a single node for the small audit log; the SQLite-style operational footprint was preferred over a full Elasticsearch deployment.", "preference", "technical", False,
     [("Zinc Search", "service"), ("Elasticsearch", "service")],
     [("Zinc Search", "Elasticsearch", "PREFERS")],
     "which lightweight engine beat Elasticsearch on the small audit log job",
     "single node small footprint audit log lightweight prefer"),
    # --- 42 ---
    ("Quickwit indexed the cold log archive on object storage; the columnar tantivy backend kept the search-on-S3 latency under 2 seconds for monthly windows.", "architecture", "technical", False,
     [("Quickwit", "service"), ("tantivy", "library"), ("S3", "service")],
     [("Quickwit", "tantivy", "BUILDS_ON")],
     "which engine kept cold log search on object storage under 2 seconds",
     "object storage columnar cold archive monthly window latency"),
    # --- 43 ---
    ("tantivy replaced an embedded Lucene-on-JNI setup inside the Rust binary; startup time dropped from 4 seconds to 200 ms on the search subprocess.", "decision", "technical", False,
     [("tantivy", "library"), ("Lucene", "library"), ("JNI", "technology"), ("Rust", "language")],
     [("tantivy", "Lucene", "REPLACES")],
     "which Rust-native library replaced the embedded Lucene-on-JNI setup",
     "embed Rust startup JNI subprocess library swap time"),
    # --- 44 ---
    ("Cohere embed-v3 replaced text-embedding-ada-002 on the multilingual catalog; recall@10 rose 7 points on the non-English slice.", "decision", "technical", False,
     [("Cohere embed-v3", "method"), ("text-embedding-ada-002", "method")],
     [("Cohere embed-v3", "text-embedding-ada-002", "REPLACES")],
     "which embedding model displaced ada-002 on the multilingual catalog",
     "multilingual recall non English slice embedding model swap"),
    # --- 45 ---
    ("Recall is the headline retrieval metric for the RAG pipeline; precision is fixed by the LLM reranker downstream, so the retriever optimizes for recall@50.", "fact", "technical", False,
     [("RAG", "concept"), ("LLM", "concept")],
     [],
     "which metric does the retriever optimize for in the RAG pipeline split",
     "RAG retriever recall optimize precision rerank downstream"),
    # --- 46 ---
    ("Boolean filters were preferred over scoring tweaks for hard requirements; in-stock and shipping-region constraints belonged in the filter clause, not the scorer.", "preference", "technical", False,
     [("Boolean", "method")],
     [],
     "which clause type held the hard requirements instead of the scorer",
     "filter clause hard requirement stock shipping region prefer"),
    # --- 47 ---
    ("Spell correction used a noisy-channel model on top of a query log dictionary; precision climbed over the trie-only suggester because rare brand names stopped getting rewritten.", "architecture", "technical", False,
     [("noisy-channel", "method"), ("trie", "algorithm")],
     [("noisy-channel", "trie", "IMPROVES_ON")],
     "which spell correction approach replaced the trie-only suggester",
     "noisy channel query log dictionary brand name rewrite stop"),
    # --- 48 ---
    ("Elasticsearch _msearch replaced a serial loop on the multi-shard dashboard; tail latency on the dashboard query dropped from 1.4 s to 380 ms.", "decision", "technical", False,
     [("Elasticsearch", "service")],
     [],
     "which Elasticsearch endpoint cut the dashboard tail latency under 400 ms",
     "multi search serial loop dashboard tail latency drop swap"),
    # --- 49 ---
    ("OpenSearch Search Pipelines hosted the hybrid blend and the cross-encoder rerank; processor chaining replaced an external orchestration script.", "architecture", "technical", False,
     [("OpenSearch Search Pipelines", "service")],
     [],
     "which OpenSearch feature absorbed the external rerank orchestration",
     "search pipeline processor chain hybrid blend rerank script"),
    # --- 50 ---
    ("Recall@10 climbed past 0.95 on the support corpus on 2026-03-09; the milestone unlocked the rollout of LLM answer generation on top of the retriever.", "milestone", "technical", False,
     [("Recall@10", "concept"), ("LLM", "concept"), ("2026-03-09", "date")],
     [],
     "when did support corpus recall cross 0.95 and unlock LLM answer rollout",
     "recall milestone support corpus LLM answer rollout date"),
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
