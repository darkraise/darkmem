"""One-off emitter for shared-base batch-157 — technical domain (data lakes and lakehouse table formats: Delta Lake, Iceberg, Hudi, Paimon, Parquet, ORC, Arrow, catalogs, compaction, time travel, schema evolution).

Writes 50 rows to data/v2/shared/batch_157.tmp.jsonl with ids shared-07801..07850.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_157.tmp.jsonl"
ID_OFFSET = 7800

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the analytics warehouse from raw Parquet on S3 to Apache Iceberg tables; snapshot isolation and hidden partitioning finally let us drop the brittle Hive-style directory writes.", "decision", "technical", False,
     [("Parquet", "technology"), ("Apache Iceberg", "technology"), ("S3", "service"), ("Hive", "technology")],
     [("Apache Iceberg", "Hive", "REPLACES"), ("Apache Iceberg", "Parquet", "USES")],
     "which table format replaced Hive-style Parquet layouts on S3 and which two features sealed the choice",
     "iceberg parquet s3 hive snapshot hidden partition replace warehouse"),
    # --- 2 ---
    ("Delta Lake now backs the ingestion tables on Databricks; MERGE INTO handles the upsert stream and the old append-only Parquet dump got retired after the dedup job kept missing late records.", "decision", "technical", False,
     [("Delta Lake", "technology"), ("Databricks", "platform"), ("MERGE INTO", "command"), ("Parquet", "technology")],
     [("Delta Lake", "Parquet", "REPLACES"), ("Delta Lake", "MERGE INTO", "USES")],
     "which table format runs ingestion on Databricks and what SQL operation handles the upsert stream",
     "delta lake databricks merge into upsert parquet append dedup ingestion"),
    # --- 3 ---
    ("Apache Hudi's merge-on-read tables are driving the CDC sink; copy-on-write was rewriting whole files on every tiny update and blew the write-amplification budget by an order of magnitude.", "decision", "technical", False,
     [("Apache Hudi", "technology"), ("merge-on-read", "pattern"), ("copy-on-write", "pattern"), ("CDC", "pattern")],
     [("merge-on-read", "copy-on-write", "REPLACES"), ("Apache Hudi", "CDC", "APPLIES_TO")],
     "which Hudi table type replaced copy-on-write for the CDC sink and what write cost did it cut",
     "hudi merge on read copy on write cdc sink write amplification"),
    # --- 4 ---
    ("Paimon landed as the streaming lakehouse format on the Flink side; its LSM-style file layout keeps upsert throughput high where Iceberg's snapshot churn was choking on the per-minute commits.", "decision", "technical", False,
     [("Paimon", "technology"), ("Flink", "framework"), ("LSM", "pattern"), ("Iceberg", "technology")],
     [("Paimon", "Iceberg", "REPLACES"), ("Paimon", "Flink", "USES")],
     "which streaming lakehouse format beat Iceberg on the Flink per-minute upsert path and why",
     "paimon flink iceberg lsm streaming upsert commit churn lakehouse"),
    # --- 5 ---
    ("Z-ordering on the event_time and user_id columns cut point-lookup scan bytes by roughly eight times; a linear sort only helped the leading column and left user filters full-scanning.", "problem", "technical", False,
     [("Z-ordering", "algorithm"), ("event_time", "concept"), ("user_id", "concept"), ("linear sort", "algorithm")],
     [("Z-ordering", "linear sort", "IMPROVES_ON")],
     "which multidimensional clustering strategy beat a linear sort for two-column point lookups",
     "z order linear sort event time user id scan bytes point lookup"),
    # --- 6 ---
    ("Small-file compaction runs hourly on the bronze tables via an OPTIMIZE job; the Kafka sink was writing ten-megabyte files per partition per minute and query planning time had crept past thirty seconds.", "problem", "technical", False,
     [("compaction", "pattern"), ("OPTIMIZE", "command"), ("Kafka", "technology"), ("bronze tables", "pattern")],
     [("OPTIMIZE", "compaction", "IMPLEMENTS")],
     "how did we cut query planning time on the bronze ingestion tables from the Kafka sink",
     "small file compaction optimize kafka bronze planning time minute"),
    # --- 7 ---
    ("VACUUM retention is pinned to seven days on prod Delta tables; the default of seven kept a safety window for time-travel audits while still releasing orphan files from failed writes.", "decision", "technical", False,
     [("VACUUM", "command"), ("Delta", "technology"), ("time-travel", "pattern")],
     [("VACUUM", "Delta", "APPLIES_TO")],
     "which retention window did we pin VACUUM to on prod Delta tables and what trade-off drove it",
     "vacuum retention delta seven days time travel orphan file audit"),
    # --- 8 ---
    ("Iceberg expire_snapshots was pinned to thirty days on prod tables; the manifest list kept growing until planning hit thirty seconds on the largest fact table, and the nightly expire job restored sanity.", "decision", "technical", False,
     [("Iceberg", "technology"), ("expire_snapshots", "command"), ("manifest list", "pattern")],
     [("expire_snapshots", "Iceberg", "APPLIES_TO")],
     "which Iceberg maintenance command tames runaway manifest list growth and what symptom tipped us off",
     "iceberg expire snapshots manifest list planning time fact table"),
    # --- 9 ---
    ("Time-travel reads were standardised on snapshot id or timestamp pinning; the audit team picked AS OF TIMESTAMP for reproducing yesterday's dashboard state rather than restoring from backup.", "decision", "technical", False,
     [("Time-travel", "pattern"), ("snapshot id", "concept"), ("AS OF TIMESTAMP", "command"), ("audit team", "organization")],
     [("AS OF TIMESTAMP", "Time-travel", "IMPLEMENTS")],
     "which query clause lets the audit team reproduce a prior dashboard state without a backup restore",
     "time travel snapshot as of timestamp audit dashboard reproduce"),
    # --- 10. noise ---
    ("The office espresso machine finally got descaled after someone counted the brown rings on the drip tray and panicked.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Merge-on-read in Hudi keeps hot updates in row-based log files and compacts them into columnar base files on a schedule; reads stitch base plus log until the next compaction lands.", "architecture", "technical", False,
     [("Hudi", "technology"), ("Merge-on-read", "pattern"), ("log files", "pattern"), ("base files", "pattern")],
     [("Merge-on-read", "Hudi", "IMPLEMENTS")],
     "how does Hudi merge-on-read split hot updates from columnar storage and when do they reconcile",
     "hudi merge on read log base file compact stitch row column"),
    # --- 12 ---
    ("Copy-on-write rewrites the whole affected file for every update: good for read-heavy tables with rare mutations, terrible for the per-row CDC firehose where write amplification dominates.", "fact", "technical", False,
     [("Copy-on-write", "pattern"), ("CDC", "pattern"), ("write amplification", "concept")],
     [],
     "when does copy-on-write shine and when does write amplification make it the wrong fit for CDC",
     "copy on write rewrite file update cdc firehose write amplification"),
    # --- 13 ---
    ("Schema evolution in Iceberg is tracked by field id, not by name; renaming a column is a metadata-only operation and existing Parquet data files remain valid because field ids are stable.", "architecture", "technical", False,
     [("Iceberg", "technology"), ("Schema evolution", "pattern"), ("field id", "concept"), ("Parquet", "technology")],
     [("Iceberg", "field id", "USES")],
     "why can Iceberg rename a column without rewriting existing Parquet files on disk",
     "iceberg schema evolution field id column rename parquet metadata"),
    # --- 14 ---
    ("Partition evolution let us switch the sales table from days(ts) to hours(ts) without rewriting history; queries hitting the old partitions still work because Iceberg tracks the spec per snapshot.", "milestone", "technical", False,
     [("Partition evolution", "pattern"), ("sales table", "concept"), ("days(ts)", "method"), ("hours(ts)", "method"), ("Iceberg", "technology")],
     [("Partition evolution", "Iceberg", "APPLIES_TO")],
     "which Iceberg feature let the sales table move from daily to hourly partitioning without rewrites",
     "partition evolution iceberg days hours sales spec snapshot rewrite"),
    # --- 15 ---
    ("Hidden partitioning means queries filter on event_time and Iceberg derives the partition bucket automatically; the old WHERE dt = '2026-04-15' boilerplate disappeared across the BI layer.", "architecture", "technical", False,
     [("Hidden partitioning", "pattern"), ("event_time", "concept"), ("Iceberg", "technology"), ("BI layer", "concept")],
     [("Hidden partitioning", "Iceberg", "IMPLEMENTS")],
     "which Iceberg feature retired the WHERE dt= boilerplate from BI queries and how",
     "hidden partition iceberg event time bi where dt boilerplate derive"),
    # --- 16 ---
    ("Snapshot isolation was adopted as the concurrency story across Delta, Iceberg, and Hudi; readers pin to a snapshot id at query start and writers append new snapshots, so readers never see torn state mid-commit.", "decision", "technical", False,
     [("Snapshot isolation", "pattern"), ("Delta", "technology"), ("Iceberg", "technology"), ("Hudi", "technology")],
     [("Delta", "Snapshot isolation", "IMPLEMENTS"), ("Iceberg", "Snapshot isolation", "IMPLEMENTS"), ("Hudi", "Snapshot isolation", "IMPLEMENTS")],
     "which concurrency model do Delta, Iceberg, and Hudi all use to keep readers from seeing torn commits",
     "snapshot isolation delta iceberg hudi reader writer torn commit pin"),
    # --- 17 ---
    ("Parquet remains the columnar file format under every lakehouse table here; ORC was benched for its bloom filters but the ecosystem tooling around Parquet for Spark and Trino was decisive.", "decision", "technical", False,
     [("Parquet", "technology"), ("ORC", "technology"), ("bloom filters", "concept"), ("Spark", "framework"), ("Trino", "technology")],
     [("Parquet", "ORC", "PREFERS"), ("Spark", "Parquet", "USES"), ("Trino", "Parquet", "USES")],
     "why did Parquet beat ORC under the lakehouse tables despite ORC's bloom-filter advantage",
     "parquet orc bloom filter spark trino ecosystem columnar lakehouse"),
    # --- 18 ---
    ("Apache Arrow is the in-memory interchange between the query engine and the Python UDF layer; zero-copy handoff saved roughly forty percent of the per-row serialisation cost we measured on Trino.", "architecture", "technical", False,
     [("Apache Arrow", "technology"), ("Python UDF", "pattern"), ("Trino", "technology"), ("zero-copy", "concept")],
     [("Apache Arrow", "Python UDF", "APPLIES_TO"), ("Trino", "Apache Arrow", "USES")],
     "which in-memory format backs zero-copy handoff between Trino and Python UDFs and what cost did it cut",
     "arrow trino python udf zero copy interchange serialisation cost"),
    # --- 19 ---
    ("Manifest files in Iceberg are themselves Avro, listing data files with min/max stats per column; the planner prunes manifests first, then data files, which keeps planning cost bounded on huge tables.", "architecture", "technical", False,
     [("manifest", "pattern"), ("Iceberg", "technology"), ("Avro", "technology"), ("planner", "pattern")],
     [("Iceberg", "Avro", "USES"), ("manifest", "Iceberg", "HAS_PART")],
     "how does the Iceberg planner bound cost with a two-level manifest and data file prune",
     "iceberg manifest avro planner prune min max stat data file"),
    # --- 20 ---
    ("Unity Catalog is the governance layer for the Databricks side; grants propagate down to table, column, and row-filter level, which replaced the home-grown IAM-policy JSON we used to ship per table.", "decision", "technical", False,
     [("Unity Catalog", "service"), ("Databricks", "platform"), ("IAM-policy", "concept"), ("row-filter", "concept")],
     [("Unity Catalog", "IAM-policy", "REPLACES"), ("Unity Catalog", "Databricks", "DEPLOYED_ON")],
     "which Databricks governance layer replaced hand-rolled IAM policies and at which grants granularity",
     "unity catalog databricks iam policy grant row column table filter"),
    # --- 21 ---
    ("Polaris catalog is running as the open Iceberg REST catalog for cross-engine reads; Snowflake, Spark, and Trino all resolve tables through the same metadata service with no format translation.", "architecture", "technical", False,
     [("Polaris", "service"), ("Iceberg", "technology"), ("Snowflake", "technology"), ("Spark", "framework"), ("Trino", "technology")],
     [("Snowflake", "Polaris", "USES"), ("Spark", "Polaris", "USES"), ("Trino", "Polaris", "USES")],
     "which Iceberg REST catalog gives Snowflake, Spark, and Trino a single source of table metadata",
     "polaris iceberg rest catalog snowflake spark trino metadata cross engine"),
    # --- 22 ---
    ("Project Nessie layers Git-style branches over Iceberg metadata; the analytics team now runs experiment branches against prod data and merges or discards without touching the main namespace.", "milestone", "technical", False,
     [("Nessie", "project"), ("Iceberg", "technology"), ("branches", "pattern"), ("analytics team", "organization")],
     [("Nessie", "Iceberg", "EXTENDS")],
     "which catalog adds Git-style branches on top of Iceberg and what workflow did it unlock for analytics",
     "nessie iceberg branch git analytics experiment main namespace merge"),
    # --- 23 ---
    ("Tabular's managed Iceberg service was evaluated but not picked; in-house Polaris plus S3 costs less at our current volume and the Databricks acquisition added vendor-lock concerns.", "decision", "technical", False,
     [("Tabular", "service"), ("Polaris", "service"), ("S3", "service"), ("Databricks", "platform")],
     [("Polaris", "Tabular", "PREFERS")],
     "why did the team pass on Tabular's managed Iceberg offering in favour of self-hosted Polaris",
     "tabular polaris iceberg managed self host databricks lock volume"),
    # --- 24 ---
    ("MinIO provides the S3-compatible object store for the on-prem lakehouse; tests run against MinIO in CI and prod uses AWS S3, with the same Iceberg code path for both.", "architecture", "technical", False,
     [("MinIO", "service"), ("S3", "service"), ("AWS", "platform"), ("Iceberg", "technology"), ("CI", "pattern")],
     [("MinIO", "S3", "IMPLEMENTS"), ("Iceberg", "MinIO", "DEPLOYED_ON")],
     "which S3-compatible object store backs the on-prem lakehouse and how does CI stay faithful to prod",
     "minio s3 on prem lakehouse iceberg aws ci compatible object"),
    # --- 25 ---
    ("AWS Lake Formation handles fine-grained access on the Glue-registered tables for the legacy analytics cluster; the team is migrating off it as Unity Catalog and Polaris cover the same ground on the new stack.", "fact", "technical", False,
     [("AWS Lake Formation", "service"), ("Glue", "service"), ("Unity Catalog", "service"), ("Polaris", "service")],
     [("Unity Catalog", "AWS Lake Formation", "REPLACES"), ("Polaris", "AWS Lake Formation", "REPLACES")],
     "which AWS governance service is being retired as Unity Catalog and Polaris take over on the new stack",
     "aws lake formation glue unity polaris fine grained access legacy"),
    # --- 26 ---
    ("Reference for the Iceberg spec lives at iceberg.apache.org/spec; the v2 format added row-level deletes via position and equality delete files, which Hudi-style merge-on-read borrows conceptually.", "reference", "technical", False,
     [("Iceberg", "technology"), ("iceberg.apache.org/spec", "api"), ("v2 format", "concept"), ("Hudi", "technology")],
     [("Iceberg", "Hudi", "RELATED_TO")],
     "where is the Iceberg spec hosted and which v2 feature enabled row-level deletes on immutable files",
     "iceberg spec v2 row level delete position equality hudi merge"),
    # --- 27 ---
    ("Reference note: Delta Lake's transaction log is a monotonically increasing sequence of JSON commit files under _delta_log; checkpoints every ten commits roll the state into a Parquet snapshot.", "reference", "technical", False,
     [("Delta Lake", "technology"), ("_delta_log", "file"), ("checkpoint", "pattern"), ("Parquet", "technology")],
     [("Delta Lake", "_delta_log", "USES")],
     "how does the Delta Lake transaction log structure its commits and what role do checkpoints play",
     "delta lake transaction log json commit delta log checkpoint parquet"),
    # --- 28 ---
    ("Reference: Parquet row-group size is a read-unit knob; default 128 MB works for Spark scans but Trino's split planner benefits from 64 MB for better worker parallelism on narrow tables.", "reference", "technical", False,
     [("Parquet", "technology"), ("row-group", "concept"), ("Spark", "framework"), ("Trino", "technology")],
     [("Parquet", "row-group", "HAS_PART")],
     "which Parquet knob controls the read unit and how should it be tuned for Trino versus Spark",
     "parquet row group size spark trino split parallel narrow table"),
    # --- 29 ---
    ("Reference for ORC stripe structure: each stripe carries its own index, data, and footer; predicate push-down skips stripes on min/max mismatches before reading any column data.", "reference", "technical", False,
     [("ORC", "technology"), ("stripe", "concept"), ("predicate push-down", "pattern")],
     [("ORC", "stripe", "HAS_PART"), ("predicate push-down", "ORC", "APPLIES_TO")],
     "how does an ORC stripe lay out index and data to enable predicate push-down on skipped stripes",
     "orc stripe index data footer predicate push down skip min max"),
    # --- 30 ---
    ("Reference: Apache Arrow's IPC format uses a length-prefixed stream of record batches with a schema message at the head; Flight builds a gRPC transport on top without copying buffers on either side.", "reference", "technical", False,
     [("Apache Arrow", "technology"), ("IPC", "protocol"), ("Flight", "protocol"), ("gRPC", "protocol")],
     [("Flight", "Apache Arrow", "EXTENDS"), ("Flight", "gRPC", "USES")],
     "which Arrow transport wraps the IPC record-batch stream in gRPC without buffer copies",
     "arrow ipc flight grpc record batch schema length prefix buffer"),
    # --- 31 ---
    ("Reference: Iceberg manifests use content=data versus content=deletes to separate immutable data files from row-level delete files, so merge-on-read v2 can apply deletes cheaply at read time.", "reference", "technical", False,
     [("Iceberg", "technology"), ("manifest", "pattern"), ("content=data", "config"), ("content=deletes", "config"), ("merge-on-read", "pattern")],
     [("merge-on-read", "Iceberg", "APPLIES_TO")],
     "how do Iceberg manifests split data files from delete files to cheapen merge-on-read v2 scans",
     "iceberg manifest content data deletes merge on read v2 row level"),
    # --- 32 ---
    ("Preference: the team defaults to Iceberg for new batch tables and Paimon for streaming sinks; Delta stays on tables co-located with Databricks and Hudi is reserved for legacy CDC pipelines.", "preference", "technical", False,
     [("Iceberg", "technology"), ("Paimon", "technology"), ("Delta", "technology"), ("Hudi", "technology"), ("Databricks", "platform")],
     [("Delta", "Databricks", "DEPLOYED_ON")],
     "which lakehouse format does the team default to per workload family in the current stack",
     "iceberg paimon delta hudi databricks batch stream cdc legacy default"),
    # --- 33 ---
    ("Preference for file sizes: target 256 MB post-compaction for Parquet data files; smaller files inflate the manifest list and planning, larger ones hurt selective point-query latency on wide columns.", "preference", "technical", False,
     [("Parquet", "technology"), ("compaction", "pattern"), ("manifest list", "pattern")],
     [("compaction", "Parquet", "APPLIES_TO")],
     "which post-compaction Parquet file size does the team target and what trade-off bounds it on each side",
     "parquet file size compaction manifest planning point query latency"),
    # --- 34 ---
    ("Preference: run VACUUM with DRY RUN first on any shared Delta table; a two-step audit plus execute avoided the on-call incident from dropping recent files under a misread retention window.", "preference", "technical", False,
     [("VACUUM", "command"), ("DRY RUN", "command"), ("Delta", "technology")],
     [("VACUUM", "Delta", "APPLIES_TO")],
     "which operational habit keeps VACUUM on shared Delta tables from dropping recent files by accident",
     "vacuum dry run delta audit two step retention window incident"),
    # --- 35 ---
    ("Preference: we skip bloom filter indexes on columns with cardinality below one thousand; the filter false-positive rate stays usable, but the index build time and storage cost no longer pay for the prune.", "preference", "technical", False,
     [("bloom filter", "concept"), ("cardinality", "concept")],
     [],
     "which cardinality threshold decides whether we build a bloom filter index on a column",
     "bloom filter cardinality threshold thousand build storage prune false"),
    # --- 36 ---
    ("Milestone: Delta Lake 3.0 shipped UniForm, a metadata shim that exposes the same Parquet files under Iceberg and Hudi reads; downstream engines can bind either spec without rewriting data.", "milestone", "technical", False,
     [("Delta Lake", "technology"), ("UniForm", "technology"), ("Iceberg", "technology"), ("Hudi", "technology"), ("Parquet", "technology")],
     [("UniForm", "Delta Lake", "EXTENDS"), ("UniForm", "Iceberg", "SUPPORTS"), ("UniForm", "Hudi", "SUPPORTS")],
     "which Delta Lake 3.0 feature exposes the same files to Iceberg and Hudi readers without data rewrite",
     "delta lake 3.0 uniform iceberg hudi parquet metadata shim rewrite"),
    # --- 37 ---
    ("Fact: Iceberg position delete files record the file path plus row ordinal to mask, while equality delete files hold predicate tuples; writers pick whichever matches their delete pattern cheaper.", "fact", "technical", False,
     [("Iceberg", "technology"), ("position delete", "concept"), ("equality delete", "concept")],
     [("Iceberg", "position delete", "HAS_PART"), ("Iceberg", "equality delete", "HAS_PART")],
     "which two Iceberg delete file flavours exist and what information does each carry",
     "iceberg position delete equality file path row ordinal predicate tuple"),
    # --- 38 ---
    ("Fact: Hudi's timeline is the authoritative log of instants under .hoodie/; queries filter the timeline to a commit instant to get snapshot reads, and cleaning expires old file groups on schedule.", "fact", "technical", False,
     [("Hudi", "technology"), ("timeline", "pattern"), (".hoodie/", "file"), ("cleaning", "command")],
     [("Hudi", "timeline", "USES")],
     "where does Hudi store its authoritative commit history and which job expires old file groups",
     "hudi timeline hoodie instant commit snapshot clean file group"),
    # --- 39 ---
    ("Fact: Paimon's LSM levels compact from L0 upward using a leveled strategy; upserts hit L0 quickly and the background compactor merges into larger leveled files, similar to RocksDB's shape.", "fact", "technical", False,
     [("Paimon", "technology"), ("LSM", "pattern"), ("RocksDB", "database"), ("compactor", "pattern")],
     [("Paimon", "LSM", "USES"), ("Paimon", "RocksDB", "RELATED_TO")],
     "how does Paimon organise its LSM levels and which well-known engine shares the shape",
     "paimon lsm level compact rocksdb upsert l0 background merge"),
    # --- 40 ---
    ("Fact: Iceberg's sort-order spec is decoupled from the partition spec; a table can cluster data on user_id via Z-order while still partitioning by day, and each evolves independently.", "fact", "technical", False,
     [("Iceberg", "technology"), ("sort-order spec", "concept"), ("partition spec", "concept"), ("Z-order", "algorithm")],
     [("Iceberg", "sort-order spec", "HAS_PART"), ("Iceberg", "partition spec", "HAS_PART")],
     "how does Iceberg let clustering and partitioning evolve independently on the same table",
     "iceberg sort order partition spec z order user id day decouple"),
    # --- 41 ---
    ("Fact: Trino's Iceberg connector supports predicate push-down on partition transforms, so filtering on day(ts) uses the hidden partition metadata without the user spelling it out in SQL.", "fact", "technical", False,
     [("Trino", "technology"), ("Iceberg", "technology"), ("predicate push-down", "pattern"), ("partition transforms", "concept")],
     [("Trino", "Iceberg", "USES"), ("predicate push-down", "partition transforms", "APPLIES_TO")],
     "which Trino feature pushes day(ts) filters down to Iceberg hidden partitions transparently",
     "trino iceberg connector push down partition transform day hidden"),
    # --- 42 ---
    ("Decision: we keep ORC's ACID variant in place for the Hive LLAP transactional tables via base and delta directories plus a compactor; the model predates Iceberg but informed the v2 row-delete design.", "decision", "technical", False,
     [("ORC", "technology"), ("Hive LLAP", "technology"), ("compactor", "pattern"), ("Iceberg", "technology")],
     [("Hive LLAP", "ORC", "USES"), ("Iceberg", "ORC", "BUILDS_ON")],
     "which ORC-based transactional model predates Iceberg v2 and influenced its delete-file design",
     "orc acid hive llap base delta compactor iceberg v2 delete"),
    # --- 43. noise ---
    ("The rooftop herb garden has lost two basil plants to the heatwave and the rosemary is the only survivor left in the back row.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Architecture: the lakehouse stack runs Iceberg tables on S3, Polaris as the catalog, Trino for ad-hoc queries, and Spark Structured Streaming for ingestion; the bronze-silver-gold tiers each own a namespace.", "architecture", "technical", False,
     [("Iceberg", "technology"), ("S3", "service"), ("Polaris", "service"), ("Trino", "technology"), ("Spark Structured Streaming", "framework")],
     [("Iceberg", "S3", "DEPLOYED_ON"), ("Trino", "Polaris", "USES"), ("Spark Structured Streaming", "Iceberg", "PRODUCES")],
     "which components make up the lakehouse stack and how are the medallion tiers scoped in the catalog",
     "iceberg s3 polaris trino spark streaming bronze silver gold medallion"),
    # --- 45 ---
    ("Milestone: the Q1 migration off Hive external tables onto Iceberg closed at 14 PB of data and 38 warehouses; schema evolution via field ids cut per-team rename coordination from days to minutes.", "milestone", "technical", False,
     [("Hive", "technology"), ("Iceberg", "technology"), ("schema evolution", "pattern"), ("field id", "concept")],
     [("Iceberg", "Hive", "REPLACES"), ("schema evolution", "field id", "USES")],
     "what volume moved off Hive onto Iceberg in Q1 and which feature cut rename coordination to minutes",
     "q1 migration hive iceberg 14 pb schema evolution field id rename"),
    # --- 46 ---
    ("Milestone: cutover to Unity Catalog for Databricks workspaces finished on 2026-03-14; row and column masking policies now live in one place instead of spread across 200+ notebook bootstraps.", "milestone", "technical", False,
     [("Unity Catalog", "service"), ("Databricks", "platform"), ("2026-03-14", "date"), ("row", "concept"), ("column", "concept")],
     [("Unity Catalog", "Databricks", "DEPLOYED_ON")],
     "when did the Unity Catalog cutover finish and which policy sprawl did it eliminate",
     "unity catalog databricks cutover 2026 03 14 row column mask notebook"),
    # --- 47 ---
    ("Milestone: Nessie branches went GA in the analytics sandbox on 2026-02-28; four experiments cut and merged cleanly against prod data without blocking the main catalog namespace.", "milestone", "technical", False,
     [("Nessie", "project"), ("2026-02-28", "date"), ("analytics sandbox", "project"), ("prod", "concept")],
     [("Nessie", "analytics sandbox", "DEPLOYED_ON")],
     "when did Nessie branches go GA in the analytics sandbox and how many experiments used them",
     "nessie branch ga 2026 02 28 analytics sandbox experiment merge"),
    # --- 48 ---
    ("Milestone: Paimon streaming sinks hit a billion upserts per hour on the Flink cluster without backpressure; the equivalent Iceberg pipeline at the same rate had caused snapshot commit contention.", "milestone", "technical", False,
     [("Paimon", "technology"), ("Flink", "framework"), ("Iceberg", "technology"), ("backpressure", "concept")],
     [("Paimon", "Flink", "DEPLOYED_ON"), ("Paimon", "Iceberg", "REPLACES")],
     "what throughput did Paimon hit on Flink and which Iceberg failure mode did it avoid",
     "paimon flink billion upsert hour backpressure iceberg snapshot commit"),
    # --- 49 ---
    ("Problem: a stale manifest cache in Trino served rows from an expired snapshot for six minutes after a VACUUM; the fix was to pin the snapshot at plan time and pass the id through execution.", "problem", "technical", False,
     [("Trino", "technology"), ("manifest cache", "pattern"), ("VACUUM", "command"), ("snapshot", "concept")],
     [("VACUUM", "Trino", "CAUSES")],
     "which Trino caching bug leaked expired-snapshot rows after VACUUM and how did the planner fix it",
     "trino manifest cache stale vacuum expire snapshot plan pin id"),
    # --- 50 ---
    ("Architecture: CDC flows land into Hudi merge-on-read tables in bronze, compact into Iceberg copy-on-write in silver, and project into aggregated Iceberg gold tables via scheduled Spark jobs.", "architecture", "technical", False,
     [("CDC", "pattern"), ("Hudi", "technology"), ("merge-on-read", "pattern"), ("Iceberg", "technology"), ("copy-on-write", "pattern"), ("Spark", "framework")],
     [("Hudi", "merge-on-read", "USES"), ("Iceberg", "copy-on-write", "USES"), ("Spark", "Iceberg", "PRODUCES")],
     "how do CDC flows move from Hudi bronze through Iceberg silver to aggregated Iceberg gold",
     "cdc hudi merge read bronze iceberg copy write silver gold spark"),
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
