"""One-off emitter for shared-base batch-242 — technical domain (PostgreSQL internals and operation).

Writes 50 rows to data/v2/shared/batch_242.tmp.jsonl with ids shared-12051..12100.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_242.tmp.jsonl"
ID_OFFSET = 12050

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Swapped pg_repack in for VACUUM FULL on the orders table; the repack rebuilds heap online with only a brief ACCESS EXCLUSIVE at swap time, so writers don't block for the two-hour compaction window.", "decision", "technical", False,
     [("pg_repack", "tool"), ("VACUUM FULL", "command"), ("ACCESS EXCLUSIVE", "concept"), ("orders", "database")],
     [("pg_repack", "VACUUM FULL", "REPLACES")],
     "which online compaction tool replaced VACUUM FULL for the orders table and what lock profile did it give us",
     "pg_repack vacuum full orders compaction access exclusive online rebuild"),
    # --- 2 architecture ---
    ("MVCC stores each tuple with xmin and xmax header fields; a row is visible to a snapshot only when xmin is committed and xmax is either zero or aborted, which lets readers run without blocking writers.", "architecture", "technical", False,
     [("MVCC", "concept"), ("xmin", "concept"), ("xmax", "concept"), ("tuple", "concept"), ("snapshot", "concept")],
     [("MVCC", "tuple", "USES"), ("snapshot", "xmin", "USES")],
     "how does the visibility check for a tuple work under MVCC using the xmin and xmax header fields",
     "mvcc xmin xmax tuple visibility snapshot reader writer header"),
    # --- 3 fact ---
    ("HOT updates skip index maintenance when no indexed column changes and the new tuple fits on the same heap page; the chain of tuples is walked via the t_ctid forward pointer until a live version is found.", "fact", "technical", False,
     [("HOT", "concept"), ("heap page", "concept"), ("t_ctid", "concept"), ("tuple", "concept")],
     [("HOT", "t_ctid", "USES")],
     "under which two conditions does a HOT update avoid touching indexes and how is the chain traversed",
     "hot update index heap page t_ctid chain live tuple pointer"),
    # --- 4 decision ---
    ("Moved the session pool from pgpool-II to PgBouncer in transaction mode; statement caching gave the app no real win and PgBouncer's smaller resident footprint saved about two gigabytes per pooler node.", "decision", "technical", False,
     [("pgpool-II", "tool"), ("PgBouncer", "tool"), ("transaction mode", "concept")],
     [("PgBouncer", "pgpool-II", "REPLACES")],
     "which connection pooler replaced pgpool-II for the session pool and what operational gains drove the swap",
     "pgbouncer pgpool transaction mode pool memory footprint swap reason"),
    # --- 5 architecture ---
    ("WAL records describe physical heap and index changes and are written to pg_wal before the dirty buffers get flushed; a checkpoint rotates the WAL and writes a REDO pointer that recovery will replay from on crash restart.", "architecture", "technical", False,
     [("WAL", "concept"), ("pg_wal", "concept"), ("checkpoint", "concept"), ("REDO pointer", "concept")],
     [("checkpoint", "WAL", "USES")],
     "how does WAL interact with checkpoints to bound the amount of work crash recovery has to redo",
     "wal pg_wal checkpoint redo pointer crash recovery replay dirty buffer"),
    # --- 6 problem ---
    ("The events table starved autovacuum because the insert-only workload never crossed the dead-tuple threshold; switched to autovacuum_vacuum_insert_scale_factor so anti-wraparound doesn't show up as a surprise.", "problem", "technical", False,
     [("autovacuum_vacuum_insert_scale_factor", "config"), ("events", "database"), ("autovacuum", "concept"), ("anti-wraparound", "concept")],
     [("autovacuum_vacuum_insert_scale_factor", "autovacuum", "CONFIGURES")],
     "which autovacuum setting did we reach for after insert-only events skipped vacuum until anti-wraparound kicked in",
     "autovacuum insert only events scale factor anti wraparound starve"),
    # --- 7 reference ---
    ("pg_stat_statements stores normalised query text with per-query totals for calls, total_exec_time, and shared block hits; enable it in shared_preload_libraries and read from the view keyed by queryid.", "reference", "technical", False,
     [("pg_stat_statements", "library"), ("shared_preload_libraries", "config"), ("queryid", "concept")],
     [("pg_stat_statements", "shared_preload_libraries", "DEPENDS_ON")],
     "which extension surfaces normalised query totals and which configuration entry must load it at startup",
     "pg_stat_statements normalised query total shared preload libraries queryid"),
    # --- 8 architecture ---
    ("The streaming replication path ships WAL from the primary to a hot_standby over a replication slot; the standby replays in real time and opens read-only queries once it reaches a consistent state.", "architecture", "technical", False,
     [("streaming replication", "concept"), ("WAL", "concept"), ("hot_standby", "config"), ("replication slot", "concept")],
     [("streaming replication", "WAL", "USES"), ("hot_standby", "streaming replication", "DEPENDS_ON")],
     "how does a hot standby consume WAL from the primary and when can it begin serving reads",
     "streaming replication wal hot standby slot replay consistent read only"),
    # --- 9 decision ---
    ("Chose pgoutput plus native publications over pglogical for the CDC pipeline; pgoutput ships with core and avoids the shared library deployment step, which the platform team had been blocking.", "decision", "technical", False,
     [("pgoutput", "concept"), ("pglogical", "library"), ("publication", "concept"), ("CDC", "concept")],
     [("pgoutput", "pglogical", "REPLACES")],
     "which logical decoding output plugin did we pick for the CDC pipeline and why did we skip pglogical",
     "pgoutput pglogical publication cdc logical decoding shared library"),
    # --- 10 noise ---
    ("The office coffee grinder developed a whine that rises in pitch when the bean hopper empties below the halfway line.", "fact", "noise", True, [], [], None, None),
    # --- 11 milestone ---
    ("Finished the Patroni rollout on the analytics cluster; three nodes run with etcd as DCS and a synchronous_standby_names list pins the named replica so planned failover is zero-data-loss.", "milestone", "technical", False,
     [("Patroni", "tool"), ("etcd", "database"), ("synchronous_standby_names", "config"), ("analytics", "project")],
     [("Patroni", "etcd", "USES")],
     "which HA stack shipped on the analytics cluster and how is the named replica pinned for zero-loss failover",
     "patroni etcd dcs synchronous standby names analytics failover zero data"),
    # --- 12 decision ---
    ("Set synchronous_commit to remote_apply on the billing primary; the tail latency went up by about four milliseconds but no replica ever serves a stale read for the payment confirmation endpoint.", "decision", "technical", False,
     [("synchronous_commit", "config"), ("remote_apply", "config"), ("billing", "project"), ("replica", "concept")],
     [("remote_apply", "synchronous_commit", "CONFIGURES")],
     "which synchronous_commit level did billing adopt and what trade-off came with guaranteeing fresh replica reads",
     "synchronous commit remote apply billing primary replica stale read latency"),
    # --- 13 architecture ---
    ("TOAST stores oversize attribute values out-of-line in a per-table TOAST relation; the main heap row keeps an 18-byte pointer and detoasting happens lazily whenever the column is actually read.", "architecture", "technical", False,
     [("TOAST", "concept"), ("TOAST relation", "concept"), ("heap row", "concept"), ("detoasting", "concept")],
     [("TOAST", "TOAST relation", "USES")],
     "how does TOAST keep oversize values out of the main heap and when does detoasting actually run",
     "toast oversize out of line pointer heap detoast lazy column read"),
    # --- 14 reference ---
    ("Postgres declarative partitioning supports RANGE, LIST, and HASH strategies; the parent holds metadata only and the planner uses partition constraints to prune non-matching children at query time.", "reference", "technical", False,
     [("declarative partitioning", "concept"), ("RANGE", "concept"), ("LIST", "concept"), ("HASH", "concept"), ("planner", "concept")],
     [("planner", "declarative partitioning", "USES")],
     "which partition strategies does declarative partitioning expose and how does the planner avoid scanning every child",
     "declarative partitioning range list hash planner prune constraint"),
    # --- 15 decision ---
    ("Dropped the btree index on sensor_readings.ts in favour of a BRIN index with pages_per_range 32; the data arrives in clock order so BRIN's min-max summary is tight and the index is a hundred times smaller.", "decision", "technical", False,
     [("BRIN", "concept"), ("btree", "concept"), ("sensor_readings", "database"), ("pages_per_range", "config")],
     [("BRIN", "btree", "REPLACES")],
     "which index type replaced the btree on the sensor_readings timestamp column and which property of the data made BRIN fit",
     "brin btree sensor readings pages per range clock order index size"),
    # --- 16 fact ---
    ("GIN indexes tsvector columns for full-text search; posting lists per lexeme keep lookups fast and fastupdate defers inserts into a pending list that gets merged on the next vacuum.", "fact", "technical", False,
     [("GIN", "concept"), ("tsvector", "concept"), ("posting list", "concept"), ("fastupdate", "config")],
     [("GIN", "tsvector", "APPLIES_TO")],
     "how does a GIN index on a tsvector column keep lookups fast and what does fastupdate change about write path",
     "gin tsvector posting list fastupdate pending list vacuum full text"),
    # --- 17 architecture ---
    ("GiST and SP-GiST both provide extensible operator-class-driven indexes; GiST fits overlap-heavy geometry while SP-GiST suits space-partitioning structures like quadtrees that produce non-overlapping regions.", "architecture", "technical", False,
     [("GiST", "concept"), ("SP-GiST", "concept"), ("operator-class", "concept"), ("quadtree", "algorithm")],
     [("SP-GiST", "quadtree", "IMPLEMENTS")],
     "how do GiST and SP-GiST differ in which shapes of data they're designed to index efficiently",
     "gist sp gist operator-class quadtree overlap space partition index"),
    # --- 18 decision ---
    ("Picked pgvector's HNSW over ivfflat for the embedding search; recall at k=10 is within half a point and HNSW doesn't need the periodic reindex that ivfflat's training step forced into the maintenance window.", "decision", "technical", False,
     [("pgvector", "library"), ("HNSW", "algorithm"), ("ivfflat", "algorithm"), ("recall at k=10", "concept")],
     [("HNSW", "ivfflat", "REPLACES")],
     "which pgvector index swap happened for embedding search and what maintenance headache did it retire",
     "pgvector hnsw ivfflat recall reindex training embedding maintenance"),
    # --- 19 milestone ---
    ("Finished the TimescaleDB upgrade on metrics-db to version 2.13; continuous aggregates on the five-minute rollup now use the new incremental refresh path and no longer lag behind during backfill.", "milestone", "technical", False,
     [("TimescaleDB", "library"), ("metrics-db", "project"), ("continuous aggregate", "concept"), ("incremental refresh", "concept")],
     [("TimescaleDB", "metrics-db", "DEPLOYED_ON")],
     "which TimescaleDB upgrade shipped on metrics-db and what changed about how rollups keep up under backfill",
     "timescaledb metrics db continuous aggregate incremental refresh rollup upgrade"),
    # --- 20 architecture ---
    ("Citus distributes tables by hashing a tenant_id column; the coordinator routes single-tenant queries to one shard and runs scatter-gather only on the analytics reports that need to cross tenants.", "architecture", "technical", False,
     [("Citus", "library"), ("tenant_id", "concept"), ("coordinator", "concept"), ("shard", "concept")],
     [("Citus", "tenant_id", "USES")],
     "how does Citus route tenant-scoped reads to a single shard while still allowing cross-tenant reports",
     "citus tenant id coordinator shard hash scatter gather cross tenant"),
    # --- 21 reference ---
    ("PostGIS adds GEOMETRY and GEOGRAPHY types, spatial operators like ST_Intersects, and a GiST operator family; the extension is loaded per database with CREATE EXTENSION postgis.", "reference", "technical", False,
     [("PostGIS", "library"), ("GEOMETRY", "concept"), ("GEOGRAPHY", "concept"), ("ST_Intersects", "method"), ("GiST", "concept")],
     [("PostGIS", "GiST", "USES")],
     "which types and operators does PostGIS add and how is it enabled on a single database",
     "postgis geometry geography st intersects gist create extension operator"),
    # --- 22 decision ---
    ("Standardised on EXPLAIN (ANALYZE, BUFFERS) for production query reviews; the plain form hides shared hit and read counts, and the hot reports really did come down to a five-times buffer amplification in one join.", "decision", "technical", False,
     [("EXPLAIN", "command"), ("ANALYZE", "command"), ("BUFFERS", "command"), ("shared hit", "concept")],
     [("EXPLAIN", "BUFFERS", "USES")],
     "which explain form became the standard for production query review and which signal made plain explain insufficient",
     "explain analyze buffers shared hit read amplification join review"),
    # --- 23 fact ---
    ("GEQO kicks in when the query has more than twelve joined relations; the genetic search beats exhaustive planning on huge join graphs but can pick a worse plan and is disabled by geqo = off.", "fact", "technical", False,
     [("GEQO", "algorithm"), ("exhaustive planning", "concept"), ("geqo", "config")],
     [("GEQO", "exhaustive planning", "REPLACES")],
     "at which join count does the planner fall back to GEQO and which setting turns it off",
     "geqo genetic query optimizer join count exhaustive planning disable"),
    # --- 24 architecture ---
    ("A materialized view stores the query result in a heap relation and stays stale until REFRESH MATERIALIZED VIEW is run; CONCURRENTLY builds the new snapshot and swaps it without blocking readers.", "architecture", "technical", False,
     [("materialized view", "concept"), ("REFRESH MATERIALIZED VIEW", "command"), ("CONCURRENTLY", "command"), ("heap relation", "concept")],
     [("materialized view", "heap relation", "USES")],
     "how does REFRESH MATERIALIZED VIEW CONCURRENTLY keep readers unblocked while the view is being rebuilt",
     "materialized view refresh concurrently heap relation stale snapshot swap"),
    # --- 25 milestone ---
    ("Delivered row-level security on the tenants schema; per-role policies bind current_setting('app.tenant_id') and application code uses SET LOCAL to pin tenant context at the start of each transaction.", "milestone", "technical", False,
     [("row-level security", "concept"), ("tenants", "database"), ("current_setting", "method"), ("SET LOCAL", "command")],
     [("row-level security", "tenants", "APPLIES_TO")],
     "how does the tenants schema enforce isolation through row-level security bound to a runtime setting",
     "row level security tenants policy current setting set local transaction"),
    # --- 26 decision ---
    ("Flipped logging aggregated read/write stats to psql's \\timing and \\gexec rather than piping explain through awk; the meta-commands are reliable across versions and the one-shot reports fit in a script file.", "decision", "technical", False,
     [("psql", "tool"), ("\\timing", "command"), ("\\gexec", "command"), ("awk", "tool")],
     [("\\timing", "awk", "REPLACES")],
     "which psql meta-commands replaced the old awk pipeline for capturing query timing in our scripts",
     "psql timing gexec meta command awk pipeline script version reliable"),
    # --- 27 problem ---
    ("A stale replication slot on the reporting replica held back WAL for weeks because the consumer crashed silently; added a max_slot_wal_keep_size ceiling so a stuck slot can't fill pg_wal and take the primary down.", "problem", "technical", False,
     [("replication slot", "concept"), ("reporting", "project"), ("max_slot_wal_keep_size", "config"), ("pg_wal", "concept")],
     [("max_slot_wal_keep_size", "replication slot", "CONFIGURES")],
     "which setting did we add after a stale replication slot on reporting filled pg_wal and threatened the primary",
     "replication slot reporting max slot wal keep size pg_wal stale consumer"),
    # --- 28 reference ---
    ("CTEs in Postgres 12 and up are inlined by default unless marked MATERIALIZED; the inlining lets the planner push predicates into the CTE body and often eliminates a redundant sort.", "reference", "technical", False,
     [("CTE", "concept"), ("MATERIALIZED", "command"), ("planner", "concept")],
     [("planner", "CTE", "APPLIES_TO")],
     "how did Postgres 12 change CTE semantics and which marker forces the old materialisation behaviour",
     "cte materialized inline planner predicate push sort version 12"),
    # --- 29 architecture ---
    ("A window function computes over an OVER frame without collapsing rows; the frame is defined by PARTITION BY, ORDER BY, and optional ROWS or RANGE bounds that scope running aggregates.", "fact", "technical", False,
     [("window function", "concept"), ("OVER", "command"), ("PARTITION BY", "command"), ("ORDER BY", "command"), ("ROWS", "command")],
     [("window function", "OVER", "USES")],
     "how is a window frame specified so a running aggregate can be scoped without collapsing rows",
     "window function over partition order rows range running aggregate frame"),
    # --- 30 decision ---
    ("Replaced the nightly pg_dump with a pg_basebackup plus WAL archive chain for the primary; the logical dump couldn't finish inside the maintenance window on the growing catalog and wasn't a crash-consistent snapshot anyway.", "decision", "technical", False,
     [("pg_dump", "tool"), ("pg_basebackup", "tool"), ("WAL archive", "concept"), ("maintenance window", "concept")],
     [("pg_basebackup", "pg_dump", "REPLACES")],
     "which backup approach replaced pg_dump on the primary and which two limits of pg_dump motivated the swap",
     "pg_dump pg_basebackup wal archive maintenance window logical physical"),
    # --- 31 fact ---
    ("A VACUUM FULL rewrites the table into a new relfilenode and holds an ACCESS EXCLUSIVE lock for the duration; readers and writers are blocked, which is why it's a tool of last resort on big heaps.", "fact", "technical", False,
     [("VACUUM FULL", "command"), ("relfilenode", "concept"), ("ACCESS EXCLUSIVE", "concept")],
     [("VACUUM FULL", "ACCESS EXCLUSIVE", "USES")],
     "what lock does VACUUM FULL take and what does it physically do to the relation that makes it so disruptive",
     "vacuum full relfilenode access exclusive rewrite heap block reader writer"),
    # --- 32 architecture ---
    ("Triggers fire in BEFORE, AFTER, and INSTEAD OF timing relative to the row event; FOR EACH ROW triggers see the NEW and OLD records, while FOR EACH STATEMENT triggers run once per affected table.", "fact", "technical", False,
     [("trigger", "concept"), ("BEFORE", "command"), ("AFTER", "command"), ("INSTEAD OF", "command"), ("FOR EACH ROW", "command")],
     [("trigger", "FOR EACH ROW", "USES")],
     "how do trigger timings and row versus statement scope compose when a row event fires multiple triggers",
     "trigger before after instead of row statement new old record event"),
    # --- 33 preference ---
    ("Prefer logical replication over trigger-based CDC for schema-mostly-stable services; catching up a subscription from pg_create_logical_replication_slot is dramatically simpler than replaying a triggers table.", "preference", "technical", False,
     [("logical replication", "concept"), ("trigger-based CDC", "concept"), ("pg_create_logical_replication_slot", "method")],
     [("logical replication", "trigger-based CDC", "PREFERS")],
     "why does the team lean on logical replication over trigger-based CDC when schemas don't change often",
     "logical replication trigger cdc subscription slot catch up schema stable"),
    # --- 34 decision ---
    ("Partitioned the events table by month with RANGE partitioning and a default partition; detach-then-drop of the trailing month keeps ninety days hot and retires the oldest partition in one DDL without a long delete.", "decision", "technical", False,
     [("events", "database"), ("RANGE partitioning", "concept"), ("default partition", "concept"), ("detach-then-drop", "concept")],
     [("events", "RANGE partitioning", "USES")],
     "how does the partitioning scheme on events retire old data cheaply and what catches untyped dates",
     "events range partition monthly default detach drop ninety day retention"),
    # --- 35 problem ---
    ("I always pair a lower checkpoint_completion_target with a larger max_wal_size when a checkpoint spike saturates the EBS write budget; the smoothing spreads the background writer load across the whole interval rather than clumping at the end.", "preference", "technical", False,
     [("checkpoint_completion_target", "config"), ("max_wal_size", "config"), ("EBS", "infrastructure"), ("checkpoint", "concept")],
     [("checkpoint_completion_target", "checkpoint", "CONFIGURES"), ("max_wal_size", "checkpoint", "CONFIGURES")],
     "which two checkpoint settings did we retune after EBS write spikes showed up every checkpoint cycle",
     "checkpoint ebs completion target max wal size background writer spike"),
    # --- 36 architecture ---
    ("A publication declares the tables and DML operations a subscriber can consume; the subscription on the downstream creates a replication slot on the publisher and drives pgoutput to emit wal into the consumer.", "architecture", "technical", False,
     [("publication", "concept"), ("subscription", "concept"), ("replication slot", "concept"), ("pgoutput", "concept")],
     [("subscription", "publication", "USES"), ("subscription", "pgoutput", "USES")],
     "which four moving parts make up the logical pipeline from writer to reader in this architecture",
     "publication subscription replication slot pgoutput wal downstream consumer"),
    # --- 37 fact ---
    ("pg_repack requires a primary key or unique not-null index on the target table; the tool uses that key to mirror changes from a log table into the shadow copy while the original stays writeable.", "fact", "technical", False,
     [("pg_repack", "tool"), ("primary key", "concept"), ("log table", "concept"), ("shadow copy", "concept")],
     [("pg_repack", "primary key", "DEPENDS_ON")],
     "which index pg_repack needs on the target and how does it keep the shadow copy in sync with live writes",
     "pg_repack primary key unique index log table shadow copy live write"),
    # --- 38 preference ---
    ("On small dev boxes I keep synchronous_commit at local rather than remote_apply; the faster commit path is a much bigger quality-of-life win than the cross-node durability guarantee which dev doesn't need anyway.", "preference", "technical", False,
     [("synchronous_commit", "config"), ("local", "config"), ("remote_apply", "config")],
     [("local", "remote_apply", "PREFERS")],
     "which synchronous_commit level do I default to on dev boxes and why is it fine without remote durability",
     "synchronous commit local remote apply dev box durability commit path"),
    # --- 39 milestone ---
    ("Rolled pgpool-II out of the legacy stack entirely; the last read-write split user moved to a PgBouncer fronting primary and a separate PgBouncer against the replica, with application-side routing picking the pool.", "milestone", "technical", False,
     [("pgpool-II", "tool"), ("PgBouncer", "tool"), ("primary", "concept"), ("replica", "concept")],
     [("PgBouncer", "pgpool-II", "REPLACES")],
     "how did the last read-write split user get off pgpool-II and what replaced its routing role",
     "pgpool pgbouncer read write split primary replica routing migrate"),
    # --- 40 reference ---
    ("EXPLAIN output's Buffers line breaks into shared hit, shared read, shared dirtied, and shared written; read plus dirtied is the real disk pressure while hit alone just measures cached throughput.", "reference", "technical", False,
     [("EXPLAIN", "command"), ("shared hit", "concept"), ("shared read", "concept"), ("shared dirtied", "concept")],
     [("EXPLAIN", "shared read", "PRODUCES")],
     "which fields in EXPLAIN's Buffers line actually indicate disk pressure versus cache-only throughput",
     "explain buffers shared hit read dirtied written disk pressure cache"),
    # --- 41 architecture ---
    ("The query planner costs candidate plans with random_page_cost, seq_page_cost, cpu_tuple_cost, and effective_cache_size inputs; tuning effective_cache_size alone reshaped a handful of plans from nested loop to hash join.", "architecture", "technical", False,
     [("query planner", "concept"), ("random_page_cost", "config"), ("seq_page_cost", "config"), ("effective_cache_size", "config"), ("hash join", "concept")],
     [("query planner", "effective_cache_size", "USES")],
     "which planner cost inputs shape plan choice and which single knob tipped nested loops into hash joins",
     "query planner random page cost seq effective cache size hash nested loop"),
    # --- 42 decision ---
    ("Switched the search index from a GIN on to_tsvector to a pg_trgm GIN for substring matches; the trigram index answers LIKE '%foo%' quickly while to_tsvector could not without an exact lexeme.", "decision", "technical", False,
     [("pg_trgm", "library"), ("GIN", "concept"), ("to_tsvector", "method"), ("trigram", "algorithm")],
     [("pg_trgm", "to_tsvector", "REPLACES")],
     "which trigram-backed index type replaced the to_tsvector GIN for substring search and why",
     "pg trgm gin to tsvector trigram substring like search index"),
    # --- 43 noise ---
    ("The hallway thermostat is two degrees ahead of the one in the main office and nobody has reconciled them since the remodel.", "fact", "noise", True, [], [], None, None),
    # --- 44 milestone ---
    ("Finished the PostGIS 3.4 upgrade on spatial-db; legacy ST_Intersects on GEOGRAPHY now uses the sphere-aware path and the twenty-kilometre radius queries came in at a third of the old latency.", "milestone", "technical", False,
     [("PostGIS", "library"), ("spatial-db", "project"), ("ST_Intersects", "method"), ("GEOGRAPHY", "concept")],
     [("PostGIS", "spatial-db", "DEPLOYED_ON")],
     "which PostGIS upgrade landed on spatial-db and which query profile saw a three-times latency win",
     "postgis 3 4 spatial db st intersects geography radius latency upgrade"),
    # --- 45 preference ---
    ("For ad-hoc inspection I reach for psql's \\d+, \\di, and \\dt+ before opening pgAdmin; the meta-commands are faster than the GUI round-trip and leave a scrollback the next engineer can diff.", "preference", "technical", False,
     [("psql", "tool"), ("\\d+", "command"), ("\\di", "command"), ("\\dt+", "command"), ("pgAdmin", "tool")],
     [("psql", "pgAdmin", "PREFERS")],
     "which psql meta-commands do I prefer over pgAdmin for quick schema inspection and what non-obvious benefit keeps them sticky",
     "psql meta command d di dt pgadmin scrollback ad hoc inspection"),
    # --- 46 architecture ---
    ("Shipped the logical replication filter stack: table-and-operation filters live in the publication and rows land into matching structures on the subscriber; DDL isn't replicated so the downstream runs its own migrations first.", "milestone", "technical", False,
     [("logical replication", "concept"), ("publication", "concept"), ("subscriber", "concept"), ("DDL", "concept"), ("migration", "concept")],
     [("logical replication", "publication", "USES")],
     "what does logical replication replicate and which class of change must the subscriber apply itself ahead of the data",
     "logical replication publication subscriber ddl migration downstream filter"),
    # --- 47 reference ---
    ("psql's \\copy streams a local file without superuser, unlike server-side COPY; the client reads the file and pushes rows over the connection so network and client disk are the real bottleneck.", "reference", "technical", False,
     [("psql", "tool"), ("\\copy", "command"), ("COPY", "command")],
     [("\\copy", "COPY", "IMPROVES_ON")],
     "how does psql's backslash copy differ from server-side COPY and where does its bottleneck live",
     "psql copy server side client stream file superuser network bottleneck"),
    # --- 48 decision ---
    ("Turned on autovacuum_work_mem and left maintenance_work_mem reserved for manual reindex jobs; the dedicated autovacuum budget stopped the big batch job from starving the vacuum workers mid-run.", "decision", "technical", False,
     [("autovacuum_work_mem", "config"), ("maintenance_work_mem", "config"), ("autovacuum", "concept"), ("reindex", "command")],
     [("autovacuum_work_mem", "maintenance_work_mem", "REPLACES")],
     "which split between autovacuum_work_mem and maintenance_work_mem did we pick and which starvation did it end",
     "autovacuum work mem maintenance reindex starve batch worker budget"),
    # --- 49 problem ---
    ("A foreign-key validation on a partitioned table required a global lock that blocked writes for minutes; switched to NOT VALID then VALIDATE CONSTRAINT so the long verification runs under a much weaker lock.", "problem", "technical", False,
     [("foreign-key", "concept"), ("partitioned table", "concept"), ("NOT VALID", "command"), ("VALIDATE CONSTRAINT", "command")],
     [("NOT VALID", "foreign-key", "APPLIES_TO")],
     "which two-step constraint pattern let us validate a foreign key on a partitioned table without the long write stall",
     "foreign key partitioned not valid validate constraint lock write stall"),
    # --- 50 milestone ---
    ("Cut over to Patroni-managed switchover for the primary on payments-db; the old manual promote-and-rewind runbook retired after a clean thirty-second failover under live traffic in the game-day drill.", "milestone", "technical", False,
     [("Patroni", "tool"), ("payments-db", "project"), ("switchover", "concept"), ("promote-and-rewind", "concept")],
     [("Patroni", "promote-and-rewind", "REPLACES")],
     "which Patroni capability retired the manual promote-and-rewind runbook on payments-db and how long did the drill take",
     "patroni payments db switchover promote rewind runbook game day failover"),
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
