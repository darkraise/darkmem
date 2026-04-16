"""One-off emitter for shared-base batch-271 — technical domain (distributed OLTP databases: Spanner, CockroachDB, YugabyteDB, TiDB, Vitess, Aurora, Neon, DynamoDB, Redis Cluster, Cassandra, Cosmos DB, FoundationDB, DuckDB, MongoDB, RocksDB, isolation levels, WAL, Paxos/Raft, TrueTime, HLC).

Writes 50 rows to data/v2/shared/batch_271.tmp.jsonl with ids shared-13501..13550.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_271.tmp.jsonl"
ID_OFFSET = 13500

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Picked CockroachDB over Google Spanner for the multi-region OLTP tier; HLC gave us the external-consistency story we needed without leasing an atomic clock per data centre.", "decision", "technical", False,
     [("CockroachDB", "database"), ("Google Spanner", "database"), ("HLC", "algorithm"), ("OLTP", "concept")],
     [("CockroachDB", "Google Spanner", "PREFERS"), ("CockroachDB", "HLC", "USES")],
     "which distributed SQL engine won the multi-region OLTP bake-off against Spanner and why",
     "cockroachdb spanner hlc multi region oltp external consistency"),
    # --- 2 architecture ---
    ("Spanner's TrueTime API exposes a now() that returns an interval rather than an instant; the commit path waits out the uncertainty bound so serialisable transactions get globally consistent timestamps.", "architecture", "technical", False,
     [("Spanner", "database"), ("TrueTime", "api"), ("serialisable", "concept")],
     [("Spanner", "TrueTime", "USES"), ("TrueTime", "serialisable", "APPLIES_TO")],
     "how does Spanner guarantee globally consistent commit timestamps without trusting a single clock",
     "spanner truetime uncertainty interval commit wait serialisable"),
    # --- 3 architecture ---
    ("CockroachDB replaces TrueTime with an HLC per node and a max-clock-offset guard; transactions that read across ranges restart if a timestamp uncertainty window is violated.", "architecture", "technical", False,
     [("CockroachDB", "database"), ("HLC", "algorithm"), ("TrueTime", "api"), ("max-clock-offset", "config")],
     [("HLC", "TrueTime", "REPLACES"), ("CockroachDB", "HLC", "USES")],
     "how does CockroachDB approximate TrueTime semantics without specialised clock hardware",
     "cockroachdb hlc clock offset uncertainty restart truetime"),
    # --- 4 fact ---
    ("YugabyteDB stores its tablets in a fork of RocksDB with a DocDB layer on top; the LSM engine handles persistence while DocDB maps YSQL rows to encoded keys.", "fact", "technical", False,
     [("YugabyteDB", "database"), ("RocksDB", "database"), ("DocDB", "service"), ("YSQL", "api"), ("LSM", "pattern")],
     [("YugabyteDB", "RocksDB", "USES"), ("DocDB", "YSQL", "APPLIES_TO")],
     "which storage engine sits under YugabyteDB's DocDB and how is YSQL mapped to keys",
     "yugabytedb rocksdb docdb ysql lsm tablet encode key"),
    # --- 5 decision ---
    ("TiDB's compute layer talks to TiKV for row storage and TiFlash for columnar replicas; we kept HTAP off for now since the extra Raft group per table doubled the write amplification on the ingest cluster.", "decision", "technical", False,
     [("TiDB", "database"), ("TiKV", "database"), ("TiFlash", "database"), ("Raft", "algorithm"), ("HTAP", "concept")],
     [("TiDB", "TiKV", "USES"), ("TiDB", "TiFlash", "USES"), ("TiFlash", "Raft", "USES")],
     "why did we disable TiFlash on the ingest cluster despite the HTAP story",
     "tidb tikv tiflash raft htap write amplification ingest"),
    # --- 6 decision ---
    ("Adopted PlanetScale's Vitess-based control plane for the MySQL fleet; the VTGate router and the VReplication online-resharding workflow retired our homegrown sharding proxy and its weekly maintenance window.", "decision", "technical", False,
     [("PlanetScale", "database"), ("Vitess", "framework"), ("VTGate", "service"), ("MySQL", "database"), ("VReplication", "service")],
     [("PlanetScale", "Vitess", "USES"), ("Vitess", "VTGate", "USES"), ("Vitess", "MySQL", "APPLIES_TO")],
     "which Vitess pieces does PlanetScale lean on for online resharding of a MySQL fleet",
     "planetscale vitess vtgate mysql vreplication reshard keyspace"),
    # --- 7 milestone ---
    ("Cut over the billing service from Amazon Aurora to Aurora DSQL last Friday; the active-active multi-region write path collapsed the cross-region failover runbook from thirty minutes to a DNS flip.", "milestone", "technical", False,
     [("Amazon Aurora", "database"), ("Aurora DSQL", "database"), ("billing service", "project"), ("multi-region", "concept")],
     [("Aurora DSQL", "Amazon Aurora", "REPLACES"), ("billing service", "Aurora DSQL", "USES")],
     "which managed SQL engine did the billing service migrate to and what failover win did it unlock",
     "aurora dsql billing multi region active active failover dns"),
    # --- 8 fact ---
    ("Aurora Limitless shards a single logical Aurora cluster across many writers; routing lives in the shard group and transactions that span shards use a two-phase commit coordinator under the hood.", "fact", "technical", False,
     [("Aurora Limitless", "database"), ("Aurora", "database"), ("two-phase commit", "algorithm"), ("shard group", "service")],
     [("Aurora Limitless", "Aurora", "EXTENDS"), ("Aurora Limitless", "two-phase commit", "USES")],
     "how does Aurora Limitless handle transactions that span more than one writer shard",
     "aurora limitless shard group two phase commit writer"),
    # --- 9 architecture ---
    ("Neon Postgres separates compute from storage: pageservers hold the LSN-indexed page history and safekeepers run Paxos for the WAL, so a branch is a pointer into the same page history.", "architecture", "technical", False,
     [("Neon Postgres", "database"), ("pageserver", "service"), ("safekeeper", "service"), ("Paxos", "algorithm"), ("WAL", "concept"), ("LSN", "concept")],
     [("Neon Postgres", "Paxos", "USES"), ("safekeeper", "WAL", "APPLIES_TO")],
     "how does Neon make branching cheap by separating compute from storage at the WAL layer",
     "neon postgres pageserver safekeeper paxos wal lsn branch"),
    # --- 10 noise ---
    ("The vending machine on floor three is eating quarters again and the facilities ticket has been open for a month with no ETA.", "fact", "noise", True, [], [], None, None),
    # --- 11 decision ---
    ("Moved the auth service from Firebase Firestore to Supabase Postgres; the row-level security model mapped onto our tenant tree in a way Firestore's rules DSL kept fighting.", "decision", "technical", False,
     [("Firebase Firestore", "database"), ("Supabase Postgres", "database"), ("auth service", "project"), ("row-level security", "pattern")],
     [("Supabase Postgres", "Firebase Firestore", "REPLACES"), ("auth service", "Supabase Postgres", "USES")],
     "which database did the auth service move to after Firestore's rules DSL hit its limits",
     "supabase firestore auth rls tenant row level security"),
    # --- 12 architecture ---
    ("FaunaDB fronts its Calvin-derived transaction log with a query coordinator; every transaction is ordered by the log before execution, so read-write conflicts resolve deterministically without lock escalation.", "architecture", "technical", False,
     [("FaunaDB", "database"), ("Calvin", "algorithm"), ("query coordinator", "service"), ("transaction log", "pattern")],
     [("FaunaDB", "Calvin", "USES")],
     "how does FaunaDB order transactions deterministically without traditional lock escalation",
     "faunadb calvin transaction log coordinator deterministic order"),
    # --- 13 fact ---
    ("ScyllaDB is a C++ rewrite of Apache Cassandra that pins one shard per CPU core; the shard-per-core model lets it run the LSM compaction loop without a cross-core scheduler fighting the network poller.", "fact", "technical", False,
     [("ScyllaDB", "database"), ("Apache Cassandra", "database"), ("C++", "language"), ("LSM", "pattern"), ("shard-per-core", "pattern")],
     [("ScyllaDB", "Apache Cassandra", "REPLACES"), ("ScyllaDB", "shard-per-core", "USES")],
     "which architectural choice lets ScyllaDB avoid cross-core contention that trips up Cassandra",
     "scylla cassandra shard per core lsm compaction cpp"),
    # --- 14 milestone ---
    ("Cassandra 5.0 SAI landed in the analytics cluster last sprint; storage-attached indexing replaced our hand-rolled secondary index path and the p99 range-read latency dropped by about forty percent.", "milestone", "technical", False,
     [("Cassandra 5.0 SAI", "database"), ("secondary index", "pattern"), ("analytics cluster", "project"), ("p99", "concept")],
     [("Cassandra 5.0 SAI", "secondary index", "REPLACES")],
     "which Cassandra 5.0 feature replaced the hand-rolled secondary index and what latency win did it deliver",
     "cassandra sai storage attached index p99 range read"),
    # --- 15 architecture ---
    ("Azure Cosmos DB exposes five consistency levels from strong down to eventual; our order-service tenant sits on bounded staleness so cross-region reads are cheap while single-region reads stay session-consistent.", "architecture", "technical", False,
     [("Azure Cosmos DB", "database"), ("bounded staleness", "concept"), ("order-service", "project")],
     [("order-service", "Azure Cosmos DB", "USES"), ("order-service", "bounded staleness", "USES")],
     "which Cosmos DB consistency level does the order-service pick and what tradeoff does it buy",
     "cosmos db bounded staleness consistency order service session"),
    # --- 16 fact ---
    ("FoundationDB is a layered key-value store whose core guarantees serializable isolation via a shared-nothing transaction system; higher-level data models like the Record Layer and Document Layer sit on top of that primitive.", "fact", "technical", False,
     [("FoundationDB", "database"), ("serializable isolation", "concept"), ("Record Layer", "service"), ("Document Layer", "service")],
     [("FoundationDB", "serializable isolation", "USES")],
     "which isolation guarantee does FoundationDB expose at its core and what sits above it",
     "foundationdb serializable record layer document layer key value"),
    # --- 17 decision ---
    ("Chose DynamoDB single-table design over a per-entity table layout; one PK/SK schema plus three GSIs covered every access pattern the order service needed and held the per-month bill flat.", "decision", "technical", False,
     [("DynamoDB", "database"), ("single-table design", "pattern"), ("GSI", "pattern"), ("order service", "project")],
     [("order service", "DynamoDB", "USES"), ("order service", "single-table design", "USES")],
     "which DynamoDB modelling style did the order service pick and how many GSIs did it need",
     "dynamodb single table gsi access pattern order service"),
    # --- 18 reference ---
    ("DynamoDB LSI shares the partition key with the base table and must be created at table-creation time; unlike GSI it counts against the 10 GB partition size limit, which bit us on one hot tenant.", "reference", "technical", False,
     [("DynamoDB", "database"), ("LSI", "pattern"), ("GSI", "pattern"), ("partition key", "concept")],
     [("LSI", "partition key", "APPLIES_TO")],
     "what are the creation-time and size constraints on a DynamoDB LSI versus a GSI",
     "dynamodb lsi gsi partition key size limit create time"),
    # --- 19 decision ---
    ("Swapped the hot-path read from cache-aside on DAX to a DynamoDB Streams plus Lambda materialised view; the old cache-aside pattern kept missing on cold keys and the p99 story didn't survive a launch campaign.", "decision", "technical", False,
     [("DynamoDB Streams", "api"), ("Lambda", "service"), ("DAX", "service"), ("materialised view", "pattern"), ("cache-aside", "pattern")],
     [("DynamoDB Streams", "Lambda", "USES"), ("DAX", "cache-aside", "REPLACES")],
     "how do DynamoDB Streams and DAX cooperate to replace the cache-aside pattern on the hot read path",
     "dynamodb streams dax lambda cache aside materialised view p99"),
    # --- 20 preference ---
    ("Prefer DuckDB over a Spark cluster for single-node OLAP work under a few hundred gigabytes; the columnar vectorised engine runs analysts' queries in-process without the JVM warmup or shuffle overhead.", "preference", "technical", False,
     [("DuckDB", "database"), ("Spark", "framework"), ("OLAP", "concept"), ("JVM", "platform")],
     [("DuckDB", "Spark", "PREFERS")],
     "when does DuckDB beat Spark for analyst queries and why does the in-process model help",
     "duckdb spark olap single node vectorised jvm shuffle"),
    # --- 21 architecture ---
    ("Redis Cluster shards keys by a 16384-slot CRC16 hash; MOVED and ASK redirections let a client reach the right shard after a resharding without a cluster-wide lock on the slot map.", "architecture", "technical", False,
     [("Redis Cluster", "database"), ("CRC16", "algorithm"), ("MOVED", "protocol"), ("ASK", "protocol")],
     [("Redis Cluster", "CRC16", "USES")],
     "how does Redis Cluster route keys to shards and handle in-flight resharding redirections",
     "redis cluster crc16 slot moved ask reshard redirection"),
    # --- 22 decision ---
    ("Switched the session cache from Redis Cluster to KeyDB on the gateway tier; the multithreaded fork handled our fan-in workload on a single node and cut the active-active replica count in half.", "decision", "technical", False,
     [("Redis Cluster", "database"), ("KeyDB", "database"), ("session cache", "project"), ("multithreaded", "concept")],
     [("KeyDB", "Redis Cluster", "REPLACES"), ("session cache", "KeyDB", "USES")],
     "which Redis fork replaced Redis Cluster on the gateway session cache and why",
     "keydb redis cluster session cache multithread gateway fan in"),
    # --- 23 milestone ---
    ("Dragonfly hit feature parity for our ingest cache last quarter; the shared-nothing shard-per-thread design reached a million ops per second on a single node during the load test.", "milestone", "technical", False,
     [("Dragonfly", "database"), ("ingest cache", "project"), ("shard-per-thread", "pattern")],
     [("ingest cache", "Dragonfly", "USES")],
     "which Redis-compatible engine reached feature parity for the ingest cache and what throughput did it hit",
     "dragonfly ingest cache shard per thread million ops load"),
    # --- 24 decision ---
    ("Adopted the Valkey fork of Redis after the licence change; the Linux Foundation governance model and the open BSD roadmap convinced the platform team to stop pinning to Redis 7.2.", "decision", "technical", False,
     [("Valkey", "database"), ("Redis", "database"), ("Linux Foundation", "organization")],
     [("Valkey", "Redis", "REPLACES")],
     "which Redis fork did the platform team pick after the licence change and why",
     "valkey redis fork licence linux foundation bsd platform"),
    # --- 25 decision ---
    ("Deployed the new MongoDB sharded cluster with a dedicated config server replica set and three mongos routers rather than co-locating them; the windowed balancer then ran without the op-latency spikes that plagued the shared-host test bed.", "decision", "technical", False,
     [("MongoDB", "database"), ("config server", "service"), ("mongos", "service")],
     [("MongoDB", "config server", "USES"), ("MongoDB", "mongos", "USES")],
     "how does MongoDB route and balance chunks across a sharded cluster without spiking latency",
     "mongodb mongos config server chunk shard balance schedule"),
    # --- 26 fact ---
    ("MongoDB Atlas Search indexes collections with Lucene under the hood; the search nodes run the inverted index off the replica-set oplog so the main cluster's primary is not on the query path.", "fact", "technical", False,
     [("MongoDB Atlas Search", "service"), ("Lucene", "library"), ("oplog", "concept"), ("inverted index", "pattern")],
     [("MongoDB Atlas Search", "Lucene", "USES"), ("MongoDB Atlas Search", "oplog", "USES")],
     "which engine powers MongoDB Atlas Search and how does it avoid loading the primary",
     "atlas search lucene oplog inverted index replica primary"),
    # --- 27 fact ---
    ("RocksDB is the pluggable LSM-tree storage engine spun out of LevelDB; column families let one instance hold several logical keyspaces with independent compaction schedules and options.", "fact", "technical", False,
     [("RocksDB", "database"), ("LevelDB", "database"), ("LSM-tree", "pattern"), ("column families", "pattern")],
     [("RocksDB", "LevelDB", "REPLACES"), ("RocksDB", "LSM-tree", "USES")],
     "how did RocksDB evolve from LevelDB and which feature lets one instance hold several keyspaces",
     "rocksdb leveldb lsm column family compaction keyspace"),
    # --- 28 decision ---
    ("Migrated the analytics OLTP partition from InnoDB to MyRocks; the LSM write amplification profile suited the insert-heavy workload and the on-disk footprint dropped by sixty percent.", "decision", "technical", False,
     [("MyRocks", "database"), ("InnoDB", "database"), ("analytics OLTP", "project"), ("LSM", "pattern")],
     [("MyRocks", "InnoDB", "REPLACES"), ("analytics OLTP", "MyRocks", "USES")],
     "which MySQL storage engine swap shrank the analytics OLTP footprint and why",
     "myrocks innodb analytics oltp lsm write amplification disk"),
    # --- 29 reference ---
    ("Serializable isolation forbids the anomalies snapshot isolation allows, including write skew; Postgres calls it SERIALIZABLE SSI and uses predicate locking rather than strict two-phase locking.", "reference", "technical", False,
     [("Serializable isolation", "concept"), ("snapshot isolation", "concept"), ("write skew", "concept"), ("SSI", "algorithm"), ("Postgres", "database")],
     [("Postgres", "SSI", "USES"), ("Serializable isolation", "write skew", "APPLIES_TO")],
     "which anomaly does serializable isolation block that snapshot isolation allows, and what does Postgres implement it with",
     "serializable snapshot write skew ssi postgres predicate lock"),
    # --- 30 reference ---
    ("Snapshot isolation reads from a consistent snapshot taken at transaction start and commits if no write-write conflict exists; it's the default in Oracle, Postgres READ COMMITTED-ish default, and MySQL InnoDB REPEATABLE READ.", "reference", "technical", False,
     [("Snapshot isolation", "concept"), ("Oracle", "database"), ("Postgres", "database"), ("InnoDB", "database")],
     [("Oracle", "Snapshot isolation", "USES"), ("InnoDB", "Snapshot isolation", "USES")],
     "which mainstream engines default to snapshot isolation and what's the commit-time check",
     "snapshot isolation oracle postgres innodb repeatable read write"),
    # --- 31 architecture ---
    ("Write-Ahead Log on Postgres is the crash-recovery contract; every page dirty in shared buffers has its redo record fsynced before the page itself, and replication streams the same WAL to standbys.", "architecture", "technical", False,
     [("Write-Ahead Log", "concept"), ("Postgres", "database"), ("shared buffers", "service"), ("replication", "concept")],
     [("Postgres", "Write-Ahead Log", "USES"), ("replication", "Write-Ahead Log", "USES")],
     "how does Postgres use WAL for both crash recovery and replication of standbys",
     "postgres wal write ahead log crash redo fsync standby"),
    # --- 32 reference ---
    ("Paxos and Raft solve the same consensus problem but Raft splits leader election, log replication, and safety into separate modules; Raft is what most new open-source systems pick because the reference paper is easier to implement.", "reference", "technical", False,
     [("Paxos", "algorithm"), ("Raft", "algorithm"), ("consensus", "concept"), ("leader election", "concept")],
     [("Raft", "Paxos", "REPLACES")],
     "why do most new open-source distributed databases pick Raft over Paxos",
     "paxos raft consensus leader election log replication"),
    # --- 33 fact ---
    ("CockroachDB uses Raft per range; TiKV uses Raft per region; YugabyteDB uses Raft per tablet; Spanner uses Paxos per group; FoundationDB uses a custom shared-nothing transaction coordinator rather than per-shard consensus.", "fact", "technical", False,
     [("CockroachDB", "database"), ("TiKV", "database"), ("YugabyteDB", "database"), ("Spanner", "database"), ("FoundationDB", "database"), ("Raft", "algorithm"), ("Paxos", "algorithm")],
     [("CockroachDB", "Raft", "USES"), ("TiKV", "Raft", "USES"), ("YugabyteDB", "Raft", "USES"), ("Spanner", "Paxos", "USES")],
     "which distributed SQL engines use Raft per shard and which pick Paxos or a different coordinator",
     "cockroachdb tikv yugabytedb spanner foundationdb raft paxos"),
    # --- 34 preference ---
    ("Prefer a follow-up base-table read over trusting a DynamoDB GSI for checkout confirmation; the GSI is eventually consistent and a read from it can trail the base table by seconds, which is longer than our confirmation SLA tolerates.", "preference", "technical", False,
     [("DynamoDB", "database"), ("GSI", "pattern"), ("eventually consistent", "concept"), ("base-table read", "pattern")],
     [("DynamoDB", "GSI", "USES"), ("base-table read", "GSI", "PREFERS")],
     "why do we re-read the base table after a DynamoDB GSI lookup on checkout confirmation",
     "dynamodb gsi eventual consistent checkout base table read"),
    # --- 35 problem ---
    ("Hit a hotspot on the Spanner orders table because every row keyed on a monotonically increasing order_id; bit-reversing the prefix spread the load across splits and tail latency came back to normal.", "problem", "technical", False,
     [("Spanner", "database"), ("orders table", "project"), ("order_id", "concept"), ("bit-reversing", "pattern")],
     [("orders table", "Spanner", "USES"), ("bit-reversing", "orders table", "APPLIES_TO")],
     "which Spanner key-design fix killed the hotspot from a monotonically increasing order id",
     "spanner hotspot monotonic bit reverse split tail latency"),
    # --- 36 preference ---
    ("Prefer HLC timestamps over physical clocks for causal ordering across microservices; HLC keeps wall-time proximity while still guaranteeing a total order under bounded clock skew.", "preference", "technical", False,
     [("HLC", "algorithm"), ("physical clock", "concept"), ("causal ordering", "concept"), ("microservices", "concept")],
     [("HLC", "physical clock", "PREFERS")],
     "why do we pick HLC over raw physical clocks for causal ordering across services",
     "hlc physical clock causal order microservice skew wall time"),
    # --- 37 decision ---
    ("Went with FoundationDB for the control plane's metadata store; its serializable isolation and deterministic simulation test harness reduced the fear of multi-key transaction bugs on the shard map.", "decision", "technical", False,
     [("FoundationDB", "database"), ("control plane", "project"), ("serializable isolation", "concept"), ("simulation test", "pattern")],
     [("control plane", "FoundationDB", "USES"), ("FoundationDB", "serializable isolation", "USES")],
     "which database did the control plane pick for metadata and what testing property sold the choice",
     "foundationdb control plane metadata serializable simulation"),
    # --- 38 problem ---
    ("Cassandra repair was blocking reads during compaction because we'd left the default STCS policy on a write-heavy table; switching to TWCS aligned file lifetimes with the TTL and the read stall disappeared.", "problem", "technical", False,
     [("Cassandra", "database"), ("STCS", "pattern"), ("TWCS", "pattern"), ("compaction", "concept"), ("TTL", "concept")],
     [("TWCS", "STCS", "REPLACES")],
     "which Cassandra compaction strategy swap aligned file lifetimes with TTL and cleared the read stall",
     "cassandra stcs twcs compaction ttl repair read stall"),
    # --- 39 milestone ---
    ("Shipped the first TiDB Placement Driver rule into prod last week; the voter quorum now stays pinned in one AZ while a learner replica streams to a DR region on TiKV, closing a compliance gap that had been open for two quarters.", "milestone", "technical", False,
     [("TiDB", "database"), ("Placement Driver", "service"), ("TiKV", "database"), ("learner replica", "pattern"), ("AZ", "concept")],
     [("TiDB", "Placement Driver", "USES"), ("Placement Driver", "TiKV", "APPLIES_TO")],
     "how does TiDB's Placement Driver keep voter quorums in one AZ while still streaming to DR",
     "tidb placement driver tikv learner quorum az dr region"),
    # --- 40 milestone ---
    ("Flipped the primary key strategy on the Vitess orders keyspace to a hash-distributed vindex; the scatter-gather on the old range vindex was pegging VTGate CPU during peak and the resharding cutover finished clean.", "milestone", "technical", False,
     [("Vitess", "framework"), ("orders keyspace", "project"), ("vindex", "pattern"), ("VTGate", "service")],
     [("orders keyspace", "Vitess", "USES"), ("orders keyspace", "vindex", "USES")],
     "which Vitess vindex swap relieved VTGate CPU during peak traffic on the orders keyspace",
     "vitess vindex hash range vtgate scatter gather reshard"),
    # --- 41 problem ---
    ("Neon Postgres page fetch latency regressed after a safekeeper disk filled up and Paxos stalled on append; expanding the volume and tuning wal_keep_size brought commit latency back under the SLO.", "problem", "technical", False,
     [("Neon Postgres", "database"), ("safekeeper", "service"), ("Paxos", "algorithm"), ("wal_keep_size", "config"), ("SLO", "concept")],
     [("Neon Postgres", "Paxos", "USES")],
     "what caused the Neon Postgres commit-latency regression and which knob restored the SLO",
     "neon safekeeper paxos stall wal keep size commit slo"),
    # --- 42 preference ---
    ("Prefer bounded staleness to eventual consistency when the read model is a user-facing cache; the read-your-writes guarantee on the same session avoids the ticket storms we got with pure eventual reads.", "preference", "technical", False,
     [("bounded staleness", "concept"), ("eventual consistency", "concept"), ("read-your-writes", "concept"), ("user-facing cache", "project")],
     [("bounded staleness", "eventual consistency", "PREFERS")],
     "when do we pick bounded staleness over eventual consistency on a user-facing cache",
     "bounded staleness eventual read your writes cache session"),
    # --- 43 architecture ---
    ("ScyllaDB's materialised views are driven by the base-table commit log; each view update is replicated through the same Raft group as the base row so a view is never lost if a replica dies mid-write.", "architecture", "technical", False,
     [("ScyllaDB", "database"), ("materialised view", "pattern"), ("commit log", "concept"), ("Raft", "algorithm")],
     [("ScyllaDB", "materialised view", "USES"), ("ScyllaDB", "Raft", "USES")],
     "how does ScyllaDB keep materialised views durable across replica failures",
     "scylla materialised view commit log raft replica durable"),
    # --- 44 reference ---
    ("Cassandra's read path is coordinator-fanout with a tunable consistency level: QUORUM reads touch ceil(RF/2)+1 replicas; LOCAL_QUORUM stays in one DC; ONE is fastest but can read stale until a repair.", "reference", "technical", False,
     [("Cassandra", "database"), ("QUORUM", "config"), ("LOCAL_QUORUM", "config"), ("coordinator", "service")],
     [("Cassandra", "QUORUM", "USES")],
     "what do Cassandra's QUORUM, LOCAL_QUORUM, and ONE consistency levels cost on the read path",
     "cassandra quorum local one consistency coordinator replica"),
    # --- 45 decision ---
    ("Picked Aurora DSQL over a self-hosted CockroachDB cluster for the payments ledger; the managed active-active multi-region writes plus Postgres wire compat pulled out a year of operator toil we couldn't staff.", "decision", "technical", False,
     [("Aurora DSQL", "database"), ("CockroachDB", "database"), ("payments ledger", "project"), ("Postgres", "database")],
     [("Aurora DSQL", "CockroachDB", "PREFERS"), ("payments ledger", "Aurora DSQL", "USES")],
     "why did the payments ledger pick Aurora DSQL over a self-hosted CockroachDB cluster",
     "aurora dsql cockroachdb payments ledger managed active active"),
    # --- 46 architecture ---
    ("DuckDB runs in the analytics notebook process and reads Parquet from S3 directly; the vectorised execution plus predicate pushdown means a ten-billion-row scan completes without ever loading the full file.", "architecture", "technical", False,
     [("DuckDB", "database"), ("Parquet", "technology"), ("S3", "service"), ("analytics notebook", "project"), ("predicate pushdown", "pattern")],
     [("analytics notebook", "DuckDB", "USES"), ("DuckDB", "Parquet", "USES")],
     "how does DuckDB scan a ten-billion-row Parquet file on S3 without loading the whole thing",
     "duckdb parquet s3 vectorised predicate pushdown notebook scan"),
    # --- 47 reference ---
    ("Dynamo-style systems classify conflicts with vector clocks or last-write-wins; Cassandra picks LWW with a client-supplied timestamp and ScyllaDB follows the same convention for wire compat.", "reference", "technical", False,
     [("Cassandra", "database"), ("ScyllaDB", "database"), ("vector clock", "algorithm"), ("last-write-wins", "pattern")],
     [("Cassandra", "last-write-wins", "USES"), ("ScyllaDB", "last-write-wins", "USES")],
     "which conflict-resolution strategy do Cassandra and ScyllaDB pick and why",
     "cassandra scylla vector clock last write wins lww timestamp"),
    # --- 48 milestone ---
    ("Spun up the first cross-region Aurora Limitless shard group in prod last week; one logical Postgres endpoint now fronts three writer shards and the order service doesn't need a client-side router anymore.", "milestone", "technical", False,
     [("Aurora Limitless", "database"), ("shard group", "service"), ("order service", "project"), ("Postgres", "database")],
     [("order service", "Aurora Limitless", "USES"), ("Aurora Limitless", "Postgres", "USES")],
     "which Aurora Limitless milestone retired the order service's client-side router",
     "aurora limitless shard group order postgres writer router"),
    # --- 49 milestone ---
    ("Cassandra 5.0 SAI plus Accord transactions shipped to the catalogue cluster in the same release; Accord's leaderless consensus let us run multi-partition writes without the classic lightweight-transaction latency hit.", "milestone", "technical", False,
     [("Cassandra 5.0 SAI", "database"), ("Accord", "algorithm"), ("catalogue cluster", "project"), ("lightweight-transaction", "pattern")],
     [("catalogue cluster", "Cassandra 5.0 SAI", "USES"), ("Accord", "lightweight-transaction", "REPLACES")],
     "which two Cassandra 5.0 features shipped to the catalogue cluster and what did Accord replace",
     "cassandra sai accord catalogue lightweight transaction leaderless"),
    # --- 50 noise ---
    ("The office plant on the south window ledge is now officially taller than the monitor and the sysadmin refuses to repot it.", "fact", "noise", True, [], [], None, None),
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
