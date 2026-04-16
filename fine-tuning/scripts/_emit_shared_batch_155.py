"""One-off emitter for shared-base batch-155 — technical domain (search engines and lexical/BM25 retrieval).

Writes 50 rows to data/v2/shared/batch_155.tmp.jsonl with ids shared-07701..07750.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_155.tmp.jsonl"
ID_OFFSET = 7700

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Replaced the Elasticsearch 7 cluster with OpenSearch 2.11 after the licence change; the query DSL stayed compatible and the ingest pipelines transferred without rewrites.", "decision", "technical", False,
     [("Elasticsearch", "service"), ("OpenSearch", "service"), ("ingest pipelines", "pattern")],
     [("OpenSearch", "Elasticsearch", "REPLACES")],
     "which search engine replaced the old Elasticsearch cluster and how much query rewrite was needed",
     "opensearch elasticsearch migrate licence query dsl ingest pipeline"),
    # --- 2 ---
    ("BM25 replaced the legacy TF-IDF scorer in the product-search index; k1 tuned to 1.2 and b to 0.75 aligned recall with the Lucene default profile.", "decision", "technical", False,
     [("BM25", "algorithm"), ("TF-IDF", "algorithm"), ("Lucene", "library"), ("k1", "config"), ("b", "config")],
     [("BM25", "TF-IDF", "REPLACES")],
     "which scoring algorithm replaced TF-IDF on the product index and what k1 and b values were chosen",
     "bm25 tf idf score k1 b lucene product search default tune"),
    # --- 3 ---
    ("The analyzer chain for the title field is standard tokenizer, lowercase filter, asciifolding, then a synonym graph filter referencing synonyms.txt with expand=false.", "architecture", "technical", False,
     [("standard tokenizer", "pattern"), ("lowercase filter", "pattern"), ("asciifolding", "pattern"), ("synonym graph filter", "pattern"), ("synonyms.txt", "file")],
     [("synonym graph filter", "synonyms.txt", "USES")],
     "which analyzer chain does the title field run and where does the synonym graph pull its mappings from",
     "analyzer standard lowercase asciifolding synonym graph title field"),
    # --- 4 ---
    ("Edge n-gram tokenizer with min_gram 2 and max_gram 15 powers the autocomplete field; search_analyzer stays a plain keyword tokenizer to avoid n-gramming the query itself.", "architecture", "technical", False,
     [("Edge n-gram tokenizer", "pattern"), ("min_gram", "config"), ("max_gram", "config"), ("search_analyzer", "config"), ("keyword tokenizer", "pattern")],
     [("Edge n-gram tokenizer", "keyword tokenizer", "COMMUNICATES_WITH")],
     "how is the autocomplete field tokenized at index time versus query time to avoid double n-gramming",
     "edge ngram min max gram autocomplete search analyzer keyword token"),
    # --- 5 ---
    ("Migrated the full-text store from Solr 8 to Meilisearch for the docs site; typo tolerance out of the box and a much smaller ops surface sold the swap.", "decision", "technical", False,
     [("Solr", "service"), ("Meilisearch", "service"), ("typo tolerance", "pattern")],
     [("Meilisearch", "Solr", "REPLACES")],
     "which search backend replaced Solr for the docs site and which built-in feature clinched it",
     "meilisearch solr docs typo tolerance ops surface replace swap"),
    # --- 6 ---
    ("Typesense runs behind the marketing site search; the 512 MB RAM box holds the full collection in memory and p95 query latency stays under 8 ms for fielded searches.", "fact", "technical", False,
     [("Typesense", "service"), ("marketing site search", "project"), ("p95", "concept")],
     [],
     "which engine backs the marketing site search and what latency profile does the in-memory model deliver",
     "typesense marketing site search in memory p95 latency 8 ms"),
    # --- 7 ---
    ("Shard routing uses the tenant_id as the routing key; queries scoped to a single tenant hit one shard instead of fanning out, which dropped p99 by roughly forty percent.", "architecture", "technical", False,
     [("Shard routing", "pattern"), ("tenant_id", "config"), ("p99", "concept")],
     [],
     "how does shard routing keep tenant-scoped queries off the full fan-out path and what latency win did it deliver",
     "shard routing tenant id key scoped query fan out p99 latency"),
    # --- 8 ---
    ("Replica placement is constrained by zone awareness: no primary and replica land in the same availability zone, so a single-AZ outage never takes a shard fully offline.", "architecture", "technical", False,
     [("Replica placement", "pattern"), ("zone awareness", "config"), ("availability zone", "infrastructure")],
     [("Replica placement", "zone awareness", "USES")],
     "which allocation rule keeps a shard's primary and replica across different availability zones",
     "replica placement zone awareness availability shard primary outage"),
    # --- 9 ---
    ("Refresh interval on the hot index got bumped from the 1 s default to 30 s during bulk ingest; index throughput doubled and near-real-time search fell well within SLA.", "decision", "technical", False,
     [("Refresh interval", "config"), ("hot index", "pattern"), ("near-real-time search", "concept")],
     [],
     "which refresh-interval tweak doubled bulk-ingest throughput on the hot index without breaking search SLA",
     "refresh interval bulk ingest throughput near real time hot index"),
    # --- 10. noise ---
    ("The deli across from the office swapped in a new sourdough starter and the Tuesday queue has been out the door since.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Segment merging kept spiking heap on the logs index; force-merging to 1 segment per shard after rollover cut search latency and memory churn in half.", "problem", "technical", False,
     [("Segment merging", "pattern"), ("logs index", "pattern"), ("force-merging", "command"), ("rollover", "pattern")],
     [("force-merging", "Segment merging", "FIXES")],
     "which post-rollover operation tamed the segment-merge heap spikes on the logs index",
     "segment merge force merge rollover logs index heap latency"),
    # --- 12 ---
    ("Painless scripting powers the custom boost: recency decay multiplied by a category weight, capped to avoid one popular SKU dominating the whole results page.", "architecture", "technical", False,
     [("Painless", "language"), ("recency decay", "pattern"), ("category weight", "config")],
     [("Painless", "recency decay", "IMPLEMENTS")],
     "which scripting layer implements the recency-decay boost and how is runaway dominance capped",
     "painless script recency decay category weight boost cap sku"),
    # --- 13 ---
    ("Percolator queries flip the index on its head: documents get matched against a stored query library so alerting fires when an incoming log hits a saved rule.", "fact", "technical", False,
     [("Percolator", "pattern"), ("stored query library", "pattern"), ("alerting", "service")],
     [("Percolator", "alerting", "APPLIES_TO")],
     "how does the percolator invert the index to drive alerting against a stored query library",
     "percolator stored query alert log rule invert index match"),
    # --- 14 ---
    ("Completion suggester replaced the custom prefix-tree typeahead; the FST-backed structure halved memory on the suggestions field and delivered sub-millisecond lookups.", "decision", "technical", False,
     [("Completion suggester", "pattern"), ("prefix-tree", "algorithm"), ("FST", "algorithm"), ("suggestions field", "config")],
     [("Completion suggester", "prefix-tree", "REPLACES")],
     "which suggester replaced the custom prefix-tree typeahead and what underlying structure made it cheaper",
     "completion suggester prefix tree fst typeahead memory latency"),
    # --- 15 ---
    ("Scoring functions in the function_score query combine BM25 with a field_value_factor on review_count using log1p modifier so a review-heavy item doesn't swamp everything else.", "architecture", "technical", False,
     [("function_score", "pattern"), ("BM25", "algorithm"), ("field_value_factor", "config"), ("log1p", "method"), ("review_count", "config")],
     [("function_score", "BM25", "USES")],
     "how does the function_score blend BM25 with review counts without letting review-heavy items swamp results",
     "function score bm25 field value factor log1p review count damp"),
    # --- 16 ---
    ("Term vectors stored with positions and offsets let the highlighter avoid re-analysing the source; the fast vector highlighter is about 4x quicker on long-form articles.", "fact", "technical", False,
     [("Term vectors", "pattern"), ("fast vector highlighter", "pattern"), ("positions", "config"), ("offsets", "config")],
     [("fast vector highlighter", "Term vectors", "USES")],
     "which term-vector storage lets the fast vector highlighter skip re-analysis on long-form articles",
     "term vector position offset fast highlighter long form article"),
    # --- 17 ---
    ("The core Lucene version on the pinned cluster is 9.11; upgrading was blocked by a custom tokenfilter that reached into an internal API removed in Lucene 10.", "problem", "technical", False,
     [("Lucene", "library"), ("9.11", "date"), ("Lucene 10", "date"), ("custom tokenfilter", "pattern")],
     [],
     "which Lucene version pins the cluster and what custom piece blocks the Lucene 10 jump",
     "lucene 9 11 upgrade blocked custom token filter internal api 10"),
    # --- 18 ---
    ("Tantivy backs the Rust service's embedded search; the single-binary deploy and zero JVM tuning were the reasons we walked away from a co-located Elasticsearch node.", "decision", "technical", False,
     [("Tantivy", "library"), ("Rust", "language"), ("Elasticsearch", "service"), ("JVM", "platform")],
     [("Tantivy", "Elasticsearch", "REPLACES")],
     "which embedded search library replaced co-located Elasticsearch in the Rust service and why",
     "tantivy rust embedded search elasticsearch jvm single binary"),
    # --- 19 ---
    ("Quickwit ingests the cold log stream and writes splits to S3; query fan-out stays cheap because only the splits whose timestamp range overlaps the query get pulled.", "architecture", "technical", False,
     [("Quickwit", "service"), ("S3", "service"), ("splits", "pattern"), ("cold log stream", "pattern")],
     [("Quickwit", "S3", "DEPLOYED_ON")],
     "how does Quickwit keep cold-log query costs down with object-store splits and timestamp pruning",
     "quickwit split s3 cold log timestamp prune fan out cheap"),
    # --- 20 ---
    ("Zinc replaced a two-node Elasticsearch cluster for the SaaS free tier; the 1 GB memory footprint and single-binary install cut infra cost to roughly a tenth.", "decision", "technical", False,
     [("Zinc", "service"), ("Elasticsearch", "service"), ("SaaS free tier", "project")],
     [("Zinc", "Elasticsearch", "REPLACES")],
     "which lightweight search engine replaced Elasticsearch on the free tier and what cost ratio did it hit",
     "zinc elasticsearch free tier single binary footprint cost cut"),
    # --- 21 ---
    ("Sonic is the lightweight search index behind the chat-history drawer; it does fuzzy prefix search with no stored documents, so privacy review waved it through quickly.", "fact", "technical", False,
     [("Sonic", "service"), ("chat-history drawer", "project"), ("fuzzy prefix search", "algorithm")],
     [("chat-history drawer", "Sonic", "USES")],
     "which minimal search engine drives the chat-history drawer and why did privacy review move fast on it",
     "sonic chat history drawer fuzzy prefix no store privacy review"),
    # --- 22 ---
    ("Manticore Search took over the MySQL fulltext role; its SphinxQL surface let the app layer keep its SQL-like query code while gaining real analyzer chains.", "decision", "technical", False,
     [("Manticore", "service"), ("MySQL fulltext", "service"), ("SphinxQL", "api"), ("analyzer chain", "pattern")],
     [("Manticore", "MySQL fulltext", "REPLACES")],
     "which search engine replaced MySQL fulltext and which query surface kept app-layer changes minimal",
     "manticore mysql fulltext sphinxql analyzer chain sql compatible"),
    # --- 23 ---
    ("Vespa runs the hybrid search for the e-commerce catalog; BM25 over text fields combines with a tensor rank feature against the embedding field in a single phased ranking expression.", "architecture", "technical", False,
     [("Vespa", "service"), ("BM25", "algorithm"), ("tensor rank feature", "config"), ("phased ranking", "pattern"), ("embedding field", "config")],
     [("Vespa", "BM25", "USES"), ("Vespa", "embedding field", "USES")],
     "how does Vespa combine BM25 and a tensor rank feature in a single phased ranking expression",
     "vespa bm25 tensor rank feature phased ranking embedding hybrid"),
    # --- 24 ---
    ("The stop-words filter is disabled on the product-title analyzer after a regression where 'the north face' matched any document with north or face; the full phrase now scores intact.", "problem", "technical", False,
     [("stop-words filter", "pattern"), ("product-title analyzer", "config")],
     [],
     "which analyzer change fixed the regression where brand phrases lost their stop-word tokens at match time",
     "stop words filter product title brand phrase north face regression"),
    # --- 25 ---
    ("A multi_match cross_fields query replaced the OR-of-match_queries on the people search; tie_breaker 0.3 across first_name, last_name, and email aligned recall with what recruiters expected.", "decision", "technical", False,
     [("multi_match", "pattern"), ("cross_fields", "config"), ("tie_breaker", "config"), ("people search", "project")],
     [("multi_match", "cross_fields", "USES")],
     "which multi_match mode replaced a naive OR query for people search and what tie_breaker value was chosen",
     "multi match cross fields tie breaker people search recruiter recall"),
    # --- 26 ---
    ("The custom ICU folding filter handles Turkish dotted-i correctly; the built-in asciifolding had been mangling user names with Turkish locale rules into unsearchable forms.", "problem", "technical", False,
     [("ICU folding filter", "library"), ("asciifolding", "pattern"), ("Turkish dotted-i", "concept")],
     [("ICU folding filter", "asciifolding", "REPLACES")],
     "what change fixed broken matches on Turkish names that had been mangled by the default folding step",
     "icu folding asciifolding turkish dotted i user name mangle"),
    # --- 27 ---
    ("Synonym graph reload is done via the _reload_search_analyzers API; the old file-watcher rebuild cycled the whole index and left a 20-second hole in search availability.", "fact", "technical", False,
     [("Synonym graph", "pattern"), ("_reload_search_analyzers", "api"), ("file-watcher rebuild", "pattern")],
     [("_reload_search_analyzers", "file-watcher rebuild", "REPLACES")],
     "which API swap eliminated the 20-second availability gap during synonym reloads",
     "synonym graph reload search analyzers api file watcher hole"),
    # --- 28 ---
    ("Relevance tuning sessions run against an offline judgements set stored in TREC format; Rank-Biased Overlap measured against the baseline keeps us honest about incremental regressions.", "architecture", "technical", False,
     [("judgements set", "pattern"), ("TREC format", "config"), ("Rank-Biased Overlap", "algorithm")],
     [],
     "which offline-eval setup catches incremental relevance regressions during tuning sessions",
     "trec judgement rank biased overlap relevance offline tuning baseline"),
    # --- 29 ---
    ("Hit the 1024 shard-per-node soft limit during log rollover; dropping the hot-index shard count from 12 to 3 and using ILM rollover cured the cluster-state bloat.", "problem", "technical", False,
     [("1024 shard-per-node", "config"), ("ILM rollover", "pattern"), ("cluster-state", "concept"), ("hot-index", "pattern")],
     [("ILM rollover", "cluster-state", "FIXES")],
     "which shard-count change and rollover policy fixed the cluster-state bloat from too many shards",
     "shard per node ilm rollover cluster state bloat hot index 12 3"),
    # --- 30 ---
    ("Snapshot repositories point at S3 with server_side_encryption true; the nightly snapshot runs in about eleven minutes for a 2 TB index thanks to incremental segment copies.", "fact", "technical", False,
     [("Snapshot repositories", "pattern"), ("S3", "service"), ("server_side_encryption", "config"), ("incremental segment", "pattern")],
     [("Snapshot repositories", "S3", "DEPLOYED_ON")],
     "where do nightly index snapshots live and what makes the 2 TB snapshot finish in roughly eleven minutes",
     "snapshot repository s3 encryption incremental segment nightly 2 tb"),
    # --- 31 ---
    ("The pattern_capture token filter extracts camelCase boundaries so a search for 'url' finds 'getUserUrl' in source-code indexing without a separate camel-split pass.", "architecture", "technical", False,
     [("pattern_capture", "pattern"), ("camelCase", "concept"), ("source-code indexing", "project")],
     [],
     "how does the code index let short lowercase queries find identifiers joined inside larger mixed-case names",
     "pattern capture camel case token source code index split url"),
    # --- 32 ---
    ("KNN pre-filter on the Vespa query narrows the candidate set by tenant and date range before the embedding nearest-neighbour pass runs, so HNSW traversal stays in the working set.", "architecture", "technical", False,
     [("KNN pre-filter", "pattern"), ("Vespa", "service"), ("HNSW", "algorithm"), ("embedding nearest-neighbour", "algorithm")],
     [("Vespa", "HNSW", "USES")],
     "how does the Vespa query keep HNSW traversal cheap when filtering by tenant and date range",
     "knn pre filter vespa hnsw embedding nearest neighbour tenant date"),
    # --- 33 ---
    ("The common-terms query got retired; match queries with cutoff_frequency 0.001 delivered the same high-DF handling without the deprecated two-tier scorer.", "decision", "technical", False,
     [("common-terms query", "pattern"), ("match queries", "pattern"), ("cutoff_frequency", "config")],
     [("match queries", "common-terms query", "REPLACES")],
     "which query type replaced the deprecated common-terms query and which parameter kept high-DF handling",
     "common terms query match cutoff frequency 0 001 high df deprecate"),
    # --- 34 ---
    ("search.max_buckets bumped from the 10_000 default to 65_536 after the cardinality aggregation on user_id consistently tripped the circuit breaker on the analytics dashboard.", "fact", "technical", False,
     [("search.max_buckets", "config"), ("cardinality aggregation", "pattern"), ("circuit breaker", "pattern"), ("analytics dashboard", "project")],
     [],
     "which setting was raised to keep the user_id cardinality aggregation from tripping the circuit breaker",
     "search max buckets 10000 65536 cardinality aggregation breaker"),
    # --- 35 ---
    ("Milestone: launched bilingual search by switching to a language-detect ingest processor that routes Arabic docs to an arabic_analyzer pipeline and English docs to english_analyzer.", "milestone", "technical", False,
     [("language-detect", "algorithm"), ("arabic_analyzer", "config"), ("english_analyzer", "config"), ("bilingual search", "project")],
     [("language-detect", "arabic_analyzer", "USES")],
     "which ingest routing enabled bilingual search by picking a per-language analyzer at index time",
     "language detect ingest processor arabic english analyzer bilingual"),
    # --- 36 ---
    ("Rolled out a Lucene MoreLikeThis query for 'related articles'; feeding in a handful of min_term_freq 2 selections matched the old embedding recommender on click-through within 3 points.", "milestone", "technical", False,
     [("MoreLikeThis", "pattern"), ("Lucene", "library"), ("min_term_freq", "config"), ("related articles", "project")],
     [("MoreLikeThis", "Lucene", "USES")],
     "which Lucene query shipped the related-articles feature and which parameter shaped its term selection",
     "more like this lucene min term freq related articles click"),
    # --- 37 ---
    ("Milestone: hit p95 under 40 ms on the global product search after moving term dictionaries to the off-heap codec and cutting doc-values memory pressure on the 128 GB nodes.", "milestone", "technical", False,
     [("off-heap codec", "pattern"), ("term dictionaries", "pattern"), ("doc-values", "pattern"), ("global product search", "project")],
     [("off-heap codec", "term dictionaries", "CONFIGURES")],
     "which codec change pulled p95 under 40 ms on global product search on the 128 GB nodes",
     "off heap codec term dictionary doc values p95 40 ms product"),
    # --- 38 ---
    ("Prefer 'keyword' mapping over 'text' for exact-match fields like SKUs and email addresses; the analyzer overhead and token-stream allocations are pure waste for codes that should compare verbatim.", "preference", "technical", False,
     [("keyword", "config"), ("text", "config"), ("SKU", "concept"), ("email address", "concept")],
     [],
     "when should fields be mapped as keyword rather than text and why",
     "keyword text mapping sku email exact match analyzer overhead"),
    # --- 39 ---
    ("Prefer OpenSearch's Security plugin role-scoped index patterns over per-index API keys; it keeps audit lineage clean and lets tenant offboarding remove access in one revocation step.", "preference", "technical", False,
     [("OpenSearch", "service"), ("Security plugin", "service"), ("role-scoped index patterns", "pattern"), ("API keys", "concept")],
     [],
     "which OpenSearch access-control model is preferred over per-index API keys for tenant offboarding",
     "opensearch security plugin role index pattern api key tenant offboard"),
    # --- 40 ---
    ("Prefer Typesense for small-collection instant-search UX where tuning is minimal; Elasticsearch wins once you need painless scripting, ingest pipelines, or cross-cluster search.", "preference", "technical", False,
     [("Typesense", "service"), ("Elasticsearch", "service"), ("painless scripting", "language"), ("cross-cluster search", "pattern")],
     [],
     "when is Typesense preferred over Elasticsearch and where does Elasticsearch still win",
     "typesense elasticsearch small collection instant painless cross cluster"),
    # --- 41 ---
    ("Prefer explicit mappings over dynamic templates for production indices; a surprise 'long' vs 'keyword' inference once cost a week of reindexing on a 400 GB orders index.", "preference", "technical", False,
     [("explicit mappings", "pattern"), ("dynamic templates", "pattern"), ("orders index", "project")],
     [],
     "why use explicit mappings instead of dynamic templates for production indices",
     "explicit mapping dynamic template reindex long keyword inference"),
    # --- 42 ---
    ("Reference: Solr's reference guide documents the eDisMax parser fields qf, pf, bf, and mm; the mm min-should-match expression of '3<-25%' is a robust relevance default.", "reference", "technical", False,
     [("Solr", "service"), ("eDisMax parser", "pattern"), ("qf", "config"), ("pf", "config"), ("mm", "config")],
     [("eDisMax parser", "Solr", "HAS_PART")],
     "which Solr parser exposes qf, pf, bf, and mm, and what mm default is widely used",
     "solr edismax qf pf bf mm 3 25 percent min should match default"),
    # --- 43. noise ---
    ("Someone in the kitchen keeps labelling the oat milk with a new pseudonym every Tuesday and the conspiracy thread on Slack has its own emoji now.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Reference: Elasticsearch's analyze API accepts a raw analyzer spec and dumps the token stream; invaluable for debugging why a query unexpectedly misses a document.", "reference", "technical", False,
     [("Elasticsearch", "service"), ("analyze API", "api"), ("token stream", "concept")],
     [("analyze API", "Elasticsearch", "HAS_PART")],
     "which Elasticsearch API dumps the token stream from an analyzer spec for debugging",
     "elasticsearch analyze api token stream debug miss document"),
    # --- 45 ---
    ("Reference: the BM25 formula is score = IDF * (f * (k1+1)) / (f + k1 * (1 - b + b * |d|/avgdl)); k1 controls term-frequency saturation and b controls length normalisation.", "reference", "technical", False,
     [("BM25", "algorithm"), ("IDF", "concept"), ("k1", "config"), ("b", "config"), ("avgdl", "concept")],
     [],
     "what are the k1 and b knobs in the BM25 formula controlling and how is the score composed",
     "bm25 formula idf k1 b avgdl term frequency length normalisation"),
    # --- 46 ---
    ("Reference: Vespa's ranking framework supports first-phase and second-phase expressions; second-phase runs only on the top-k of the first and is the right home for expensive tensor ops.", "reference", "technical", False,
     [("Vespa", "service"), ("first-phase", "pattern"), ("second-phase", "pattern"), ("tensor ops", "concept")],
     [("Vespa", "second-phase", "HAS_PART")],
     "which Vespa ranking phase is intended for expensive tensor operations and why",
     "vespa first phase second phase ranking top k tensor expensive"),
    # --- 47 ---
    ("Reference: Quickwit splits are immutable and identified by a ULID; the split metastore stores just the pointers and timestamp ranges, which keeps fan-out pruning nearly free.", "reference", "technical", False,
     [("Quickwit", "service"), ("ULID", "concept"), ("split metastore", "pattern"), ("fan-out pruning", "concept")],
     [("split metastore", "Quickwit", "HAS_PART")],
     "what identifies a Quickwit split and what does the metastore keep to enable cheap fan-out pruning",
     "quickwit split ulid metastore pointer timestamp fan out prune"),
    # --- 48 ---
    ("Reference: Meilisearch ranking rules default to words, typo, proximity, attribute, sort, exactness; re-ordering is the main knob when the out-of-the-box relevance misses.", "reference", "technical", False,
     [("Meilisearch", "service"), ("ranking rules", "config"), ("proximity", "config"), ("exactness", "config")],
     [("ranking rules", "Meilisearch", "HAS_PART")],
     "which ordered list of ranking rules does Meilisearch default to and how is relevance tuned",
     "meilisearch ranking rule words typo proximity attribute sort exact"),
    # --- 49 ---
    ("Milestone: the OpenSearch 2.11 cluster cleared a full region failover drill; cross-cluster replication caught the standby up in 18 minutes and the cutover was scripted end-to-end.", "milestone", "technical", False,
     [("OpenSearch", "service"), ("cross-cluster replication", "pattern"), ("region failover drill", "event")],
     [("OpenSearch", "cross-cluster replication", "USES")],
     "which replication feature let the OpenSearch cluster clear its region failover drill in 18 minutes",
     "opensearch cross cluster replication region failover drill 18 min"),
    # --- 50 ---
    ("Milestone: retired the last Solr node after a six-month Elasticsearch migration; 2.4 billion documents now live on the new tier and the legacy schema.xml tree finally got deleted.", "milestone", "technical", False,
     [("Solr", "service"), ("Elasticsearch", "service"), ("schema.xml", "file")],
     [("Elasticsearch", "Solr", "REPLACES")],
     "which migration milestone retired the final Solr node and how many documents moved in total",
     "solr elasticsearch retire schema xml 2 4 billion migration 6 month"),
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
