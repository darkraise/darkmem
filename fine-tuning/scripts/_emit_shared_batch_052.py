"""One-off emitter for shared-base batch-052 — technical domain (database internals).

Writes 50 rows to data/v2/shared/batch_052.tmp.jsonl with ids shared-02551..02600.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_052.tmp.jsonl"
ID_OFFSET = 2550

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Postgres WAL replay stalled on the replica because wal_receiver_timeout was shorter than the primary's checkpoint fsync window; tuning both aligned the streaming lag to under a second.", "problem", "technical", False,
     [("Postgres", "database"), ("WAL", "concept")],
     [],
     "why did the standby fall behind until the receiver timeout was lengthened",
     "write ahead log replay stall timeout checkpoint fsync align"),
    # --- 2 ---
    ("Autovacuum thresholds dropped to 2 percent on the orders table after bloat hit 40 percent between manual runs; cost_limit went up in lockstep to keep cleanup aggressive.", "decision", "technical", False,
     [("Autovacuum", "concept"), ("orders", "database")],
     [],
     "how were the vacuum thresholds changed once bloat overran the manual schedule",
     "scale factor aggressive cleanup cost limit raise tune"),
    # --- 3 ---
    ("HOT updates kept the ctid chain inside one heap page until a non-HOT update migrated the tuple; the ratio fell once a covering index stopped touching updated columns.", "fact", "technical", False,
     [("HOT", "concept"), ("ctid", "concept")],
     [],
     "what made the heap-only-tuple ratio recover on the frequently updated table",
     "chain same page covering index untouched column ratio"),
    # --- 4 ---
    ("TOAST compression switched from pglz to LZ4 on the document column; read latency dropped and compression ratio held within a few percent of the older scheme.", "decision", "technical", False,
     [("TOAST", "concept"), ("pglz", "algorithm"), ("LZ4", "algorithm")],
     [("LZ4", "pglz", "REPLACES")],
     "which toast codec displaced the legacy compressor for large documents",
     "out of line storage codec swap latency ratio hold"),
    # --- 5 ---
    ("fillfactor on the heavily updated ledger table dropped to 70; free space on every page let HOT updates avoid index churn during the peak hour.", "decision", "technical", False,
     [("fillfactor", "config"), ("ledger", "database"), ("HOT", "concept")],
     [],
     "how was the ledger table tuned so peak updates stayed inside the same page",
     "page free space hot update index churn avoid peak"),
    # --- 6 ---
    ("pg_stat_statements surfaced a single prepared statement chewing 60 percent of the cluster CPU; plan flipped to a bitmap scan once random_page_cost dropped.", "problem", "technical", False,
     [("pg_stat_statements", "tool"), ("random_page_cost", "config")],
     [],
     "which extension pointed at the runaway plan and which knob fixed it",
     "hotspot query cpu bitmap plan cost parameter tune"),
    # --- 7 ---
    ("pg_repack replaced VACUUM FULL for the clustering maintenance window; locks stayed concurrent-safe and the billion-row table rebuilt without a downtime banner.", "decision", "technical", False,
     [("pg_repack", "tool"), ("VACUUM FULL", "command")],
     [("pg_repack", "VACUUM FULL", "REPLACES")],
     "which tool took over the online clustering rebuild that previously needed an outage",
     "online rebuild concurrent lock billion row window swap"),
    # --- 8 ---
    ("BRIN beat GIN on the time-series partition scans because the column was naturally correlated with insertion order; index size shrank by two orders of magnitude.", "decision", "technical", False,
     [("BRIN", "algorithm"), ("GIN", "algorithm")],
     [("BRIN", "GIN", "REPLACES")],
     "which index kind took over the time-series scans once correlation was confirmed",
     "block range summary correlated insert index shrink swap"),
    # --- 9 ---
    ("GiST handled the geometry overlap predicates that GIN could not express cleanly; operator class alignment decided the index kind for the spatial workload.", "decision", "technical", False,
     [("GiST", "algorithm"), ("GIN", "algorithm")],
     [],
     "which index structure won the spatial overlap workload over the inverted option",
     "generalised search tree operator class spatial overlap pick"),
    # --- 10. noise ---
    ("Hold on, let me grab the explain plan.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Covering indexes with INCLUDE columns let the dashboard query go index-only on Postgres 15; the heap fetch count in EXPLAIN fell to zero once VACUUM caught up.", "architecture", "technical", False,
     [("INCLUDE", "command"), ("Postgres 15", "database"), ("EXPLAIN", "command"), ("VACUUM", "command")],
     [],
     "which feature made the dashboard query skip the heap after a vacuum pass",
     "index only scan heap fetch zero included column"),
    # --- 12 ---
    ("Parallel sequential scan only paid off past roughly 2 GB on the analytics cluster; under that threshold the worker startup cost dominated and the planner rightly stayed serial.", "fact", "technical", False,
     [("Parallel sequential scan", "concept")],
     [],
     "at what table size did parallel scanning stop being a net loss in the analytics cluster",
     "worker startup cost threshold serial small table loss"),
    # --- 13 ---
    ("Hash join replaced merge join on the join between orders and customers once work_mem doubled; sort spills disappeared and latency dropped by a third.", "decision", "technical", False,
     [("Hash join", "algorithm"), ("merge join", "algorithm"), ("orders", "database"), ("customers", "database"), ("work_mem", "config")],
     [("Hash join", "merge join", "REPLACES")],
     "which join strategy took over once working memory per worker got bumped",
     "build probe sort spill memory grant latency drop"),
    # --- 14 ---
    ("MVCC snapshot semantics made the long-running report block autovacuum on the hot table; moving the report to a read replica freed the xmin horizon.", "problem", "technical", False,
     [("MVCC", "concept"), ("autovacuum", "concept"), ("xmin", "concept")],
     [],
     "why did the long report keep the vacuum horizon pinned on the primary",
     "snapshot transaction horizon pin vacuum block replica offload"),
    # --- 15 ---
    ("Serializable Snapshot Isolation on Postgres caught the phantom write in the reservation flow; a retry loop on serialization_failure kept throughput acceptable.", "architecture", "technical", False,
     [("Serializable Snapshot Isolation", "concept"), ("Postgres", "database"), ("serialization_failure", "error")],
     [],
     "which isolation mode caught the phantom in the reservation path and how was retry handled",
     "SSI predicate lock retry phantom write reservation"),
    # --- 16 ---
    ("InnoDB clustered index pushed the primary-key design towards monotonic ULIDs for the orders table; random UUIDs were fragmenting the B+ tree and bloating secondary indexes.", "decision", "technical", False,
     [("InnoDB", "database"), ("ULID", "concept"), ("UUID", "concept"), ("B+ tree", "algorithm")],
     [("ULID", "UUID", "REPLACES")],
     "why did the primary key shape change once the MySQL fragmentation showed up",
     "clustered primary fragmentation secondary bloat monotonic"),
    # --- 17 ---
    ("MyISAM was retired from the legacy reporting database in favour of InnoDB; crash recovery gaps and table-level locks had no defence against the new write volume.", "decision", "technical", False,
     [("MyISAM", "database"), ("InnoDB", "database")],
     [("InnoDB", "MyISAM", "REPLACES")],
     "which storage engine left the legacy reporting database and why",
     "non transactional table lock crash recovery swap engine"),
    # --- 18 ---
    ("InnoDB undo tablespaces were split out from the system tablespace; truncation during off-hours reclaimed 200 GB without bouncing the instance.", "architecture", "technical", False,
     [("InnoDB", "database")],
     [],
     "how was the undo log growth contained without a restart on the MySQL cluster",
     "undo tablespace split truncate reclaim online no restart"),
    # --- 19 ---
    ("RocksDB write stalls cleared once level0_slowdown_writes_trigger and max_background_compactions were both raised; L0 drained faster than the incoming flush rate.", "problem", "technical", False,
     [("RocksDB", "database")],
     [],
     "which knobs cleared the level-zero write stalls on the RocksDB cluster",
     "write stall level zero drain compaction throughput tune"),
    # --- 20 ---
    ("Leveled compaction suited the read-heavy metrics store; tiered compaction stayed on the write-heavy audit log where read amplification mattered less.", "preference", "technical", False,
     [("Leveled compaction", "algorithm"), ("tiered compaction", "algorithm")],
     [],
     "which compaction strategy fits the read-heavy store and which stayed on the audit log",
     "read write amplification mixed workload split strategy"),
    # --- 21 ---
    ("Universal compaction on the session store kept SST file count low during bursts; space amplification was the acceptable trade against stall risk.", "decision", "technical", False,
     [("Universal compaction", "algorithm"), ("SST", "concept")],
     [],
     "which compaction scheme tamed the session store bursts at a space cost",
     "universal burst file count space amplification trade"),
    # --- 22 ---
    ("Bloom filters on SSTable reads cut negative lookups on the key-not-found path; bits-per-key went from 10 to 16 after the miss rate spiked.", "decision", "technical", False,
     [("Bloom filter", "algorithm"), ("SSTable", "concept")],
     [],
     "how were false-positive point lookups tamed in the LSM read path",
     "probabilistic filter bits per key negative lookup miss"),
    # --- 23 ---
    ("ClickHouse MergeTree tiered storage pushed cold parts to S3-backed volumes; TTL move rules kept the hot NVMe tier under 2 TB.", "architecture", "technical", False,
     [("ClickHouse", "database"), ("MergeTree", "algorithm"), ("S3", "service"), ("NVMe", "technology")],
     [],
     "how does the MergeTree tiering keep the hot local disk bounded",
     "cold part object storage ttl move rule hot tier"),
    # --- 24 ---
    ("FoundationDB versionstamps keyed the append-only event feed; clients stopped embedding wall clocks once the transactional version was authoritative.", "architecture", "technical", False,
     [("FoundationDB", "database")],
     [],
     "which primitive replaced wall-clock suffixes in the event feed keys",
     "version stamp transactional authoritative clock free append"),
    # --- 25 ---
    ("CockroachDB range splits kicked in around 512 MB; raft groups rebalanced automatically but lease transfers spiked p99 latency for seconds at a time.", "problem", "technical", False,
     [("CockroachDB", "database"), ("raft", "algorithm")],
     [],
     "what caused the p99 spikes on the CockroachDB cluster during range rebalancing",
     "range split raft lease transfer tail latency spike"),
    # --- 26 ---
    ("Spanner TrueTime bounded clock uncertainty for external consistency; the commit wait added a handful of milliseconds but the linearisable promise held globally.", "reference", "technical", False,
     [("Spanner", "database"), ("TrueTime", "concept")],
     [],
     "which mechanism gives Spanner external consistency across regions",
     "clock uncertainty commit wait linearisable external consistency"),
    # --- 27 ---
    ("TiDB Placement Rules pinned the compliance tenant to EU-only replicas; cross-region follower reads stayed on for analytics under a separate rule set.", "architecture", "technical", False,
     [("TiDB", "database")],
     [],
     "which feature kept the compliance workload on in-region replicas while letting analytics roam",
     "placement rule region pin follower read compliance split"),
    # --- 28 ---
    ("Yugabyte tablet auto-splitting kept hot shards from hogging a single node; the sharding strategy flipped to range-based once composite keys entered the schema.", "decision", "technical", False,
     [("Yugabyte", "database")],
     [],
     "how did the sharding approach change after composite keys were added to Yugabyte",
     "tablet split hot shard range composite key strategy"),
    # --- 29 ---
    ("DuckDB vectorised execution beat a Python-pandas pipeline at aggregation; the same laptop ran the ETL in under ten seconds on a 5 GB parquet.", "milestone", "technical", False,
     [("DuckDB", "database"), ("Python", "language"), ("pandas", "library"), ("parquet", "concept")],
     [("DuckDB", "pandas", "REPLACES")],
     "which in-process engine took over the laptop ETL from the pandas pipeline",
     "vectorised aggregation laptop parquet seconds speedup"),
    # --- 30 ---
    ("MonetDB's column-at-a-time operators compared unfavourably with Vertica's pipelined vectorised execution on the OLAP bench; Vertica won on long join chains.", "fact", "technical", False,
     [("MonetDB", "database"), ("Vertica", "database")],
     [],
     "which columnar engine won the long-join OLAP bake-off on the bench workload",
     "column at a time pipeline join chain olap compare"),
    # --- 31 ---
    ("Extended statistics on Postgres fixed the row-count underestimate for correlated predicates; the planner flipped from nested loop to hash join once the ndistinct was honest.", "problem", "technical", False,
     [("Postgres", "database"), ("Extended statistics", "concept"), ("nested loop", "algorithm"), ("hash join", "algorithm")],
     [("hash join", "nested loop", "REPLACES")],
     "which stats helped the planner abandon the losing nested-loop plan",
     "multi column correlation ndistinct planner pick improve"),
    # --- 32 ---
    ("Planner hints stayed off by default; pg_hint_plan was approved only for documented escape-hatch cases where the cost model misbehaved on extreme skew.", "decision", "technical", False,
     [("pg_hint_plan", "tool")],
     [],
     "what is the policy on planner hints and when are they allowed",
     "hint escape hatch skew cost model policy documented"),
    # --- 33 ---
    ("Prepared-statement plan caching bit the multi-tenant service; a generic plan lost against custom plans for skewed tenants until plan_cache_mode was set to force_custom_plan.", "problem", "technical", False,
     [("plan_cache_mode", "config"), ("force_custom_plan", "config")],
     [],
     "which caching setting resolved the skewed-tenant plan regression",
     "prepared statement generic custom plan skew tenant mode"),
    # --- 34. noise ---
    ("Give me a sec, I'm tailing the log.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Online DDL on MySQL used pt-online-schema-change for the column-type widening; gh-ost replaced it once foreign-key handling and binlog tailing matured.", "decision", "technical", False,
     [("MySQL", "database"), ("pt-online-schema-change", "tool"), ("gh-ost", "tool")],
     [("gh-ost", "pt-online-schema-change", "REPLACES")],
     "which online DDL tool displaced the trigger-based option on the MySQL fleet",
     "online schema change trigger binlog tail replace migrate"),
    # --- 36 ---
    ("Logical replication on Postgres replaced physical streaming for the cross-major-version upgrade path; per-table filtering also unlocked the partial-copy migration.", "decision", "technical", False,
     [("Postgres", "database"), ("Logical replication", "concept"), ("physical streaming", "concept")],
     [("Logical replication", "physical streaming", "REPLACES")],
     "which replication mode took over to bridge the major-version upgrade",
     "logical physical streaming version upgrade filter partial"),
    # --- 37 ---
    ("WAL shipping via archive_command held the warm standby during the outage window; streaming replication resumed once the network link returned.", "architecture", "technical", False,
     [("WAL shipping", "pattern"), ("archive_command", "config"), ("streaming replication", "pattern")],
     [],
     "how was the standby kept fresh while the streaming link was down",
     "archive ship warm standby outage network link resume"),
    # --- 38 ---
    ("ClickHouse SIMD kernels on AVX-512 hosts doubled the aggregation throughput on the funnel query; the older AVX2 path was kept as a compile-time fallback.", "fact", "technical", False,
     [("ClickHouse", "database"), ("AVX-512", "technology"), ("AVX2", "technology")],
     [],
     "which instruction set gave the funnel aggregation its big throughput win",
     "simd kernel wide register aggregate throughput fallback"),
    # --- 39 ---
    ("RocksDB replaced LevelDB in the embedded metadata service; the write-stall controls and column families alone justified the swap, tombstone handling was a bonus.", "decision", "technical", False,
     [("RocksDB", "database"), ("LevelDB", "database")],
     [("RocksDB", "LevelDB", "REPLACES")],
     "which LSM engine took over from LevelDB in the metadata service",
     "embedded metadata column family write stall swap engine"),
    # --- 40 ---
    ("Cassandra wide-row design moved from a single clustering key to a composite with a bucketed time prefix; tombstone scans on deletes fell inside safe thresholds again.", "architecture", "technical", False,
     [("Cassandra", "database")],
     [],
     "how was the cassandra wide-row model reshaped to control tombstone scans on delete-heavy paths",
     "composite clustering bucket time prefix wide row tombstone"),
    # --- 41 ---
    ("B+ tree storage won the small-key OLTP workload against an LSM alternative; point-read latency and range-scan cache efficiency tipped the call.", "decision", "technical", False,
     [("B+ tree", "algorithm"), ("LSM", "algorithm")],
     [("B+ tree", "LSM", "PREFERS")],
     "which on-disk structure was preferred for the small-key OLTP workload",
     "point read range scan cache oltp small key prefer"),
    # --- 42 ---
    ("LSM design was preferred over the B-tree for the ingestion-heavy telemetry store; write amplification was acceptable and compactions ran during the quiet window.", "decision", "technical", False,
     [("LSM", "algorithm"), ("B-tree", "algorithm")],
     [("LSM", "B-tree", "PREFERS")],
     "which structure was chosen for the ingestion-heavy telemetry store",
     "write heavy ingestion amplification compaction quiet prefer"),
    # --- 43 ---
    ("CockroachDB's rebalancer built on the raft lease design pioneered by etcd; the range-level abstraction generalised the single-keyspace etcd pattern.", "reference", "technical", False,
     [("CockroachDB", "database"), ("raft", "protocol"), ("etcd", "database")],
     [("CockroachDB", "etcd", "BUILDS_ON")],
     "which prior system's raft pattern did CockroachDB's range lease design extend",
     "raft lease range abstraction keyspace build upon"),
    # --- 44 ---
    ("Citus sharding on Postgres improved on the manual partitioning scheme the team hand-rolled before; the hash-distributed tables cut cross-node shuffles for the multi-tenant reports.", "decision", "technical", False,
     [("Citus", "database"), ("Postgres", "database")],
     [("Citus", "Postgres", "IMPROVES_ON")],
     "which extension improved on the hand-rolled partitioning scheme for multi-tenant reports",
     "shard hash distribute shuffle tenant partition improve"),
    # --- 45 ---
    ("CockroachDB SQL layer improves on the Spanner F1 approach for open-source workloads; Spanner's commit-wait remains the gold standard but TrueTime is not broadly available.", "reference", "technical", False,
     [("CockroachDB", "database"), ("Spanner", "database"), ("TrueTime", "concept")],
     [("CockroachDB", "Spanner", "IMPROVES_ON")],
     "which open-source design improves on Spanner's F1 approach without TrueTime hardware",
     "open source commit wait hardware clock approach improve"),
    # --- 46 ---
    ("Vitess sharding on MySQL builds on the YouTube proxy pattern from the pre-open-source era; VTGate abstracted the shard map so application code stayed single-node-like.", "reference", "technical", False,
     [("Vitess", "database"), ("MySQL", "database"), ("VTGate", "service")],
     [("Vitess", "MySQL", "BUILDS_ON")],
     "which proxy abstraction lets the Vitess client code stay single-node-like",
     "shard map proxy gate abstract legacy pattern extend"),
    # --- 47 ---
    ("ScyllaDB's shard-per-core model improves on Cassandra's thread-pool architecture for modern NVMe hosts; the Seastar framework ties each shard to a reactor on a dedicated core.", "reference", "technical", False,
     [("ScyllaDB", "database"), ("Cassandra", "database"), ("Seastar", "framework"), ("NVMe", "technology")],
     [("ScyllaDB", "Cassandra", "IMPROVES_ON")],
     "which architecture swap pushed Scylla past Cassandra on modern NVMe hosts",
     "shard per core reactor thread pool modern hardware improve"),
    # --- 48 ---
    ("ZHeap experiments in Postgres aimed at in-place updates without MVCC bloat; the feature stayed out of mainline but the design informed later heap-storage discussions.", "fact", "technical", False,
     [("ZHeap", "concept"), ("Postgres", "database"), ("MVCC", "concept")],
     [],
     "which experimental heap storage explored in-place updates to avoid MVCC bloat",
     "in place update heap experiment bloat free storage design"),
    # --- 49 ---
    ("pgBackRest replaced a homegrown basebackup wrapper for the primary cluster backups; parallel restore and archive expiry policy were the decisive features.", "decision", "technical", False,
     [("pgBackRest", "tool"), ("basebackup", "command")],
     [("pgBackRest", "basebackup", "REPLACES")],
     "which backup tool took over from the homegrown script on the primary cluster",
     "parallel restore archive expiry backup wrapper swap"),
    # --- 50 ---
    ("Postgres 16 parallel hash aggregate landed in the analytics cluster on 2026-03-09; funnel queries cut runtime by half with work_mem tuned upward.", "milestone", "technical", False,
     [("Postgres 16", "database"), ("parallel hash aggregate", "algorithm"), ("work_mem", "config"), ("2026-03-09", "date")],
     [],
     "when did the parallel hash aggregate deliver the analytics runtime halving",
     "parallel aggregate analytics runtime memory grant date"),
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
