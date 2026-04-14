"""One-off emitter for shared-base batch-022 — technical domain, data platforms slice.

Same pattern as _emit_shared_batch_011.py; only ENTRIES and ID_OFFSET change.
Writes 50 rows to data/v2/shared/batch_022.tmp.jsonl with ids shared-01051..01100.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_022.tmp.jsonl"
ID_OFFSET = 1050

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Snowflake external tables over Iceberg point at the bronze layer so raw lake files stay queryable without a load step.", "architecture", "technical", False,
     [("Snowflake", "platform"), ("Iceberg", "framework")],
     [],
     "how does the warehouse read raw lake files without copying them in",
     "external table format reader bronze layer unload"),
    # --- 2 ---
    ("BigQuery slot reservations replaced on-demand pricing for the analytics workspace; autoscaling slots smoothed out quarter-close spikes.", "decision", "technical", False,
     [("BigQuery", "platform"), ("slot reservations", "concept"), ("on-demand pricing", "concept")],
     [("slot reservations", "on-demand pricing", "REPLACES")],
     "which pricing mode took over for the analytics tenant and why",
     "reservation capacity autoscale quarter close spike"),
    # --- 3 ---
    ("Databricks SQL warehouses share a Unity Catalog with the notebooks; governance rules now apply to both serverless SQL and job clusters.", "architecture", "technical", False,
     [("Databricks SQL", "platform"), ("Unity Catalog", "service")],
     [],
     "how is governance unified across the warehouse and notebook surfaces",
     "lakehouse catalog serverless job cluster governance"),
    # --- 4 ---
    ("Redshift RA3 nodes with managed storage let us resize compute without reshuffling blocks; cluster resize windows dropped from hours to minutes.", "decision", "technical", False,
     [("Redshift", "platform"), ("RA3", "infrastructure"), ("managed storage", "technology")],
     [],
     "what node family change shrank the warehouse resize window",
     "decoupled compute storage resize window elastic"),
    # --- 5 ---
    ("Delta Lake was the starting point, but the team moved new tables to Apache Iceberg for engine-agnostic reads from Trino and Flink.", "decision", "technical", False,
     [("Delta Lake", "framework"), ("Apache Iceberg", "framework"), ("Trino", "platform"), ("Flink", "framework")],
     [("Apache Iceberg", "Delta Lake", "REPLACES")],
     "which table format took over from the proprietary one for cross-engine reads",
     "open table format engine agnostic migration choice"),
    # --- 6 ---
    ("Apache Hudi copy-on-write tables backed the first CDC sink; merge-on-read variants arrived later for high-churn dimensions.", "architecture", "technical", False,
     [("Apache Hudi", "framework"), ("copy-on-write", "pattern"), ("merge-on-read", "pattern")],
     [],
     "how did the lake handle changing dimension rows as CDC volume grew",
     "table storage mode churn dimension write pattern"),
    # --- 7 ---
    ("Kafka Connect runs the Debezium Postgres connector in distributed mode; the replication slot survives connector restarts without replay storms.", "architecture", "technical", False,
     [("Kafka Connect", "framework"), ("Debezium", "tool"), ("Postgres", "database"), ("replication slot", "concept")],
     [],
     "how are Postgres row changes shipped onto the event bus without replay storms",
     "distributed connector slot durability restart safe"),
    # --- 8 ---
    ("Apache Pulsar is preferred over Kafka for the multi-tenant analytics bus because tiered storage and namespaces map cleanly to per-customer quotas.", "preference", "technical", False,
     [("Apache Pulsar", "platform"), ("Kafka", "platform"), ("tiered storage", "concept")],
     [("Apache Pulsar", "Kafka", "PREFERS")],
     "which event broker won the multi-tenant analytics bus role",
     "tenant namespace quota tiered offload broker choice"),
    # --- 9 ---
    ("Kinesis Data Streams backs the clickstream pipeline; on-demand mode removed the capacity-planning toil that plagued the provisioned setup.", "decision", "technical", False,
     [("Kinesis Data Streams", "service"), ("on-demand mode", "concept"), ("provisioned setup", "concept")],
     [("on-demand mode", "provisioned setup", "REPLACES")],
     "which capacity mode ended the shard planning grind for clickstream",
     "click stream shard capacity planning removal"),
    # --- 10. noise ---
    ("Let me double-check that partition spec real quick.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("ClickHouse powers the product analytics dashboards; Merge-tree partitioning by event day keeps TTL drops cheap.", "architecture", "technical", False,
     [("ClickHouse", "database"), ("Merge-tree", "algorithm")],
     [],
     "which OLAP engine and partitioning scheme the analytics UI sits on",
     "columnar engine daily partition TTL drop dashboard"),
    # --- 12 ---
    ("Apache Druid handles sub-second slice-and-dice on the funnel pages; roll-up at ingest trades fidelity for query speed at scale.", "architecture", "technical", False,
     [("Apache Druid", "database"), ("roll-up", "method")],
     [],
     "how does the funnel tool stay sub-second on large cardinalities",
     "ingest aggregation fidelity tradeoff slice dice speed"),
    # --- 13 ---
    ("Apache Pinot beat Druid for real-time leaderboards because the upsert tables closed the last-write-wins gap without a secondary reconciler.", "decision", "technical", False,
     [("Apache Pinot", "database"), ("Druid", "database"), ("upsert tables", "concept")],
     [("Apache Pinot", "Druid", "PREFERS")],
     "which real-time OLAP engine won the leaderboard job over the older option",
     "upsert real time last write reconcile gap close"),
    # --- 14 ---
    ("Apache Doris replaced a home-grown lambda pipeline for ad-hoc OLAP; unified batch and stream ingest cut two code paths to one.", "decision", "technical", False,
     [("Apache Doris", "database"), ("lambda pipeline", "pattern")],
     [("Apache Doris", "lambda pipeline", "REPLACES")],
     "what took over from the split batch-and-stream OLAP pipeline",
     "unified ingest ad hoc OLAP code path collapse"),
    # --- 15 ---
    ("StarRocks improves on legacy MPP warehouses for cost-per-query at mid-TB scale; vectorised execution keeps CPU busy without shuffle thrash.", "decision", "technical", False,
     [("StarRocks", "database"), ("legacy MPP warehouses", "concept")],
     [("StarRocks", "legacy MPP warehouses", "IMPROVES_ON")],
     "which engine got us better cost per query than the older MPP stack",
     "vectorised execution shuffle thrash cost query mid scale"),
    # --- 16 ---
    ("Airbyte took over bespoke Python ingest scripts for the SaaS connectors; normalisation into the warehouse now runs as a dbt step.", "decision", "technical", False,
     [("Airbyte", "tool"), ("bespoke Python ingest scripts", "concept"), ("dbt", "tool")],
     [("Airbyte", "bespoke Python ingest scripts", "REPLACES")],
     "which ingest tool replaced the handwritten SaaS pullers",
     "SaaS connector ingest swap normalisation step"),
    # --- 17 ---
    ("Fivetran was evaluated but rejected in favour of Airbyte; self-hosting control over PII residency outweighed the managed convenience.", "decision", "technical", False,
     [("Fivetran", "tool"), ("Airbyte", "tool")],
     [("Airbyte", "Fivetran", "PREFERS")],
     "which ingest vendor lost on residency control despite managed-ops appeal",
     "managed vendor rejection residency PII control self host"),
    # --- 18 ---
    ("Qlik Replicate covers the mainframe-to-lake CDC path; the DB2 source stays off the critical-path commit log for the other tools.", "architecture", "technical", False,
     [("Qlik Replicate", "tool"), ("DB2", "database")],
     [],
     "how does the legacy mainframe feed the lake without taxing the other CDC tools",
     "mainframe CDC isolation commit log source carve out"),
    # --- 19 ---
    ("dbt Core models compile into the warehouse-native SQL dialect; state-based selection lets CI only rebuild what changed downstream.", "architecture", "technical", False,
     [("dbt Core", "tool"), ("CI", "service")],
     [],
     "how does the transformation tool keep CI runs incremental",
     "state defer selection downstream rebuild incremental"),
    # --- 20 ---
    ("SQLMesh is preferred over dbt for the serious modelling workloads; virtual environments and column-level lineage removed the rebuild-everything reflex.", "preference", "technical", False,
     [("SQLMesh", "tool"), ("dbt", "tool"), ("virtual environments", "concept")],
     [("SQLMesh", "dbt", "PREFERS")],
     "which modelling tool wins when column lineage and cheap envs matter",
     "virtual environment column lineage rebuild reflex swap"),
    # --- 21 ---
    ("Dataform was shelved when the warehouse moved off BigQuery; the engine coupling no longer fit the polyglot stack.", "problem", "technical", False,
     [("Dataform", "tool"), ("BigQuery", "platform")],
     [],
     "why did the Google-native modelling tool stop fitting the warehouse stack",
     "engine coupling polyglot warehouse retirement reason"),
    # --- 22 ---
    ("Airflow scheduler ran out of heartbeat budget on dense DAG days; moving critical DAGs to Dagster stopped the silent task backfills.", "decision", "technical", False,
     [("Airflow", "tool"), ("Dagster", "tool")],
     [("Dagster", "Airflow", "REPLACES")],
     "which orchestrator replaced the old one for the heartbeat-heavy DAGs",
     "scheduler heartbeat dense DAG silent backfill swap"),
    # --- 23 ---
    ("Prefect 2 is preferred over Airflow for the small internal pipelines; Python-native flows avoided the DAG-authoring ceremony.", "preference", "technical", False,
     [("Prefect 2", "tool"), ("Airflow", "tool"), ("Python", "language")],
     [("Prefect 2", "Airflow", "PREFERS")],
     "which orchestrator fits the small Python pipelines better than the veteran one",
     "python native flow ceremony small pipeline choice"),
    # --- 24 ---
    ("Great Expectations suites gate merges on the core fact tables; expectation failures block the downstream dbt run instead of poisoning marts.", "architecture", "technical", False,
     [("Great Expectations", "tool"), ("dbt", "tool")],
     [],
     "how are bad fact-table rows stopped before they reach the marts",
     "data quality gate expectation merge block upstream"),
    # --- 25 ---
    ("Soda Core improves on ad-hoc SQL checks for data quality; YAML-first rules fit into the same review loop as the models themselves.", "decision", "technical", False,
     [("Soda Core", "tool"), ("ad-hoc SQL checks", "concept"), ("YAML", "language")],
     [("Soda Core", "ad-hoc SQL checks", "IMPROVES_ON")],
     "which quality tool replaced the handwritten check scripts",
     "declarative rule review loop quality check swap"),
    # --- 26 ---
    ("Monte Carlo alerted us to a stale Snowflake pipeline on 2026-03-02; the freshness anomaly fired three hours before a human noticed.", "milestone", "technical", False,
     [("Monte Carlo", "tool"), ("Snowflake", "platform"), ("2026-03-02", "date")],
     [],
     "when did the observability tool first beat a human to a staleness incident",
     "freshness anomaly stale pipeline detection early catch"),
    # --- 27 ---
    ("OpenLineage events from Airflow and dbt feed Marquez; a single graph now answers which model broke the downstream dashboard.", "architecture", "technical", False,
     [("OpenLineage", "framework"), ("Airflow", "tool"), ("dbt", "tool"), ("Marquez", "tool")],
     [],
     "how do we trace a broken dashboard back to the offending model",
     "lineage event collector graph blame downstream break"),
    # --- 28 ---
    ("DataHub took over from Marquez as the cross-team catalogue; column-level lineage plus ownership stubs stopped the shadow spreadsheets.", "decision", "technical", False,
     [("DataHub", "tool"), ("Marquez", "tool")],
     [("DataHub", "Marquez", "REPLACES")],
     "which catalogue replaced the lineage-only tool for discovery across teams",
     "column lineage ownership catalogue shadow sheet stop"),
    # --- 29 ---
    ("Apache Spark batch jobs migrated to Spark on Kubernetes; Yunikorn scheduling kept the mixed streaming and batch fleet fair.", "architecture", "technical", False,
     [("Apache Spark", "framework"), ("Kubernetes", "platform"), ("Yunikorn", "tool")],
     [],
     "how is batch processing isolated from streaming on the shared compute pool",
     "batch scheduler fair share mixed workload cluster"),
    # --- 30 ---
    ("Flink batch mode runs the nightly reconciliation over the same pipelines as streaming; one codebase beat the dual Spark-and-Flink setup.", "decision", "technical", False,
     [("Flink", "framework"), ("Spark", "framework")],
     [("Flink", "Spark", "REPLACES")],
     "which batch engine took over the reconciliation from the older split setup",
     "unified batch stream codebase dedup engine migration"),
    # --- 31 ---
    ("Trino federates queries across Iceberg and Postgres for the exploratory workbench; push-down predicates keep scans light on the lake side.", "architecture", "technical", False,
     [("Trino", "platform"), ("Iceberg", "framework"), ("Postgres", "database")],
     [],
     "how does the exploratory workbench query lake and operational stores together",
     "federation push down predicate lake relational mix"),
    # --- 32 ---
    ("Presto got frozen after Trino's governance split; new connectors target Trino and the legacy Presto cluster is read-only until sunset.", "decision", "technical", False,
     [("Presto", "platform"), ("Trino", "platform")],
     [("Trino", "Presto", "REPLACES")],
     "which fork wins new connector work after the governance split",
     "fork governance split new connector sunset read only"),
    # --- 33 ---
    ("Dremio provided a semantic layer on top of Iceberg; reflections let BI tools cache without us shipping cubes to a separate store.", "architecture", "technical", False,
     [("Dremio", "platform"), ("Iceberg", "framework"), ("reflections", "concept")],
     [],
     "how do BI tools get cube-like speed without a separate cube store",
     "semantic layer reflection cache BI skip cube store"),
    # --- 34. noise ---
    ("Kicking off the backfill now, give me a minute.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Iceberg hidden partitioning on event_hour removed the user-visible partition column; queries no longer need a magic date filter to prune.", "architecture", "technical", False,
     [("Iceberg", "framework"), ("hidden partitioning", "concept")],
     [],
     "how did the lake hide partitioning details from the analyst queries",
     "partition transform hide filter prune magic column"),
    # --- 36 ---
    ("ZSTD columnar compression beat Snappy on the fact tables for both size and scan time; the CPU cost was well inside the scan budget.", "decision", "technical", False,
     [("ZSTD", "algorithm"), ("Snappy", "algorithm")],
     [("ZSTD", "Snappy", "IMPROVES_ON")],
     "which columnar codec won on size and scan time against the old default",
     "codec compression scan time cpu tradeoff column file"),
    # --- 37 ---
    ("Parquet row-group sizing at 128 MB and dictionary encoding on low-cardinality columns cut the shuffle read volume roughly in half.", "reference", "technical", False,
     [("Parquet", "framework"), ("dictionary encoding", "concept")],
     [],
     "which Parquet tuning choices cut the downstream shuffle read most",
     "row group size dictionary encoding shuffle read cut"),
    # --- 38 ---
    ("ORC is preferred over Parquet for the Hive-heavy legacy warehouse; predicate push-down with bloom filters matches the stripe indexes there.", "preference", "technical", False,
     [("ORC", "framework"), ("Parquet", "framework"), ("Hive", "platform")],
     [("ORC", "Parquet", "PREFERS")],
     "which file format wins in the legacy Hive warehouse and why",
     "stripe index bloom filter legacy hive push down"),
    # --- 39 ---
    ("DuckDB builds on SQLite's embeddability but aims at OLAP; analysts pull Parquet slices locally without bouncing off the warehouse.", "preference", "technical", False,
     [("DuckDB", "database"), ("SQLite", "database"), ("Parquet", "framework")],
     [("DuckDB", "SQLite", "BUILDS_ON")],
     "which embedded engine lets analysts slice Parquet without the warehouse",
     "embedded analytics OLAP local notebook parquet slice"),
    # --- 40 ---
    ("Polars over Pandas became the default for the data-science feature extraction loop; lazy frames plus Arrow memory cut wall-clock time by 4x.", "decision", "technical", False,
     [("Polars", "library"), ("Pandas", "library"), ("Arrow", "framework")],
     [("Polars", "Pandas", "REPLACES")],
     "which dataframe library took over from the Python default for feature extraction",
     "lazy frame arrow memory wall clock speed swap"),
    # --- 41 ---
    ("Arrow Flight SQL replaced ODBC round-trips between the BI layer and the query engine; columnar wire format dropped result-set latency dramatically.", "decision", "technical", False,
     [("Arrow Flight SQL", "protocol"), ("ODBC", "protocol")],
     [("Arrow Flight SQL", "ODBC", "REPLACES")],
     "which wire protocol took over from the row-oriented BI connector",
     "columnar wire BI connector result set latency swap"),
    # --- 42 ---
    ("Iceberg REST catalog took over from Hive Metastore for table discovery; credential vending at the catalog tier simplified multi-engine auth.", "decision", "technical", False,
     [("Iceberg REST catalog", "service"), ("Hive Metastore", "service")],
     [("Iceberg REST catalog", "Hive Metastore", "REPLACES")],
     "which catalog replaced the Java-metastore for cross-engine table discovery",
     "REST catalog credential vending multi engine auth swap"),
    # --- 43 ---
    ("Partitioning switched from calendar-month to bucket-by-user-id for the top events table; hot-key skew on campaign days disappeared.", "decision", "technical", False,
     [("bucket-by-user-id", "concept"), ("calendar-month", "concept")],
     [("bucket-by-user-id", "calendar-month", "REPLACES")],
     "which partitioning scheme replaced the date-based one on the hot events table",
     "bucket partition skew campaign hot key redesign"),
    # --- 44 ---
    ("Materialize gave us incremental views over the CDC stream; dashboards update in milliseconds without polling the warehouse every minute.", "architecture", "technical", False,
     [("Materialize", "database"), ("CDC", "pattern")],
     [],
     "how do the dashboards stay live without polling the warehouse",
     "incremental view stream dataflow dashboard freshness"),
    # --- 45 ---
    ("RisingWave is preferred over Materialize for the cost-sensitive streaming SQL tier; decoupled storage on object-store kept the idle bill near zero.", "preference", "technical", False,
     [("RisingWave", "database"), ("Materialize", "database")],
     [("RisingWave", "Materialize", "PREFERS")],
     "which streaming SQL engine won the cost-sensitive tier over the incumbent",
     "decoupled storage object store idle cost streaming SQL"),
    # --- 46 ---
    ("Hot partitions in Kinesis caused a 45-minute backlog on 2026-02-18; switching the partition key from user_id to a composite key fanned out the shards.", "problem", "technical", False,
     [("Kinesis", "service"), ("user_id", "concept"), ("2026-02-18", "date")],
     [],
     "what caused the 45-minute stream backlog and how was it unstuck",
     "hot partition stream backlog composite key fan out"),
    # --- 47 ---
    ("Looked into Azure Synapse and rejected it in favour of Databricks SQL; the open Delta and Iceberg support won over the proprietary dedicated pool.", "decision", "technical", False,
     [("Azure Synapse", "platform"), ("Databricks SQL", "platform"), ("Delta", "framework"), ("Iceberg", "framework")],
     [("Databricks SQL", "Azure Synapse", "PREFERS")],
     "which lakehouse option beat the Azure-native warehouse on open formats",
     "dedicated pool rejection open format win lakehouse choice"),
    # --- 48 ---
    ("OpenLineage column-level lineage shipped for dbt on 2026-03-25; downstream impact review stopped being a grep-the-models exercise.", "milestone", "technical", False,
     [("OpenLineage", "framework"), ("dbt", "tool"), ("2026-03-25", "date")],
     [],
     "when did column-level lineage finally land for the modelling tool",
     "column lineage ship date impact review grep end"),
    # --- 49 ---
    ("Iceberg table maintenance jobs run weekly — expire snapshots, rewrite manifests, compact small files — so read planning stays cheap over time.", "fact", "technical", False,
     [("Iceberg", "framework"), ("expire snapshots", "concept"), ("compact small files", "concept")],
     [],
     "what housekeeping keeps the lake's read-planning cost stable",
     "snapshot expire manifest rewrite small file compaction"),
    # --- 50 ---
    ("Google Pub/Sub feeds a BigQuery subscription directly; skipping the Dataflow hop cut end-to-end latency and ownership cost on the telemetry pipe.", "decision", "technical", False,
     [("Google Pub/Sub", "service"), ("BigQuery", "platform"), ("Dataflow", "service")],
     [("Google Pub/Sub", "Dataflow", "REPLACES")],
     "which direct path replaced the Dataflow hop on the telemetry pipe",
     "direct subscription telemetry hop removal latency cost"),
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
