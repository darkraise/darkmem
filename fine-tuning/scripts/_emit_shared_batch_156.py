"""One-off emitter for shared-base batch-156 — technical domain (data warehousing and OLAP: Snowflake, BigQuery, Redshift, ClickHouse, StarRocks, Databricks SQL, DuckDB, Druid, Pinot, Firebolt, Greenplum, Vertica, Trino, dbt, columnar storage, materialized views, micro-partitions, cost-based optimizer).

Writes 50 rows to data/v2/shared/batch_156.tmp.jsonl with ids shared-07751..07800.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_156.tmp.jsonl"
ID_OFFSET = 7750

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the nightly reporting warehouse from Redshift dc2.large to Snowflake; the old per-node disk attached compute pattern couldn't elastically scale during month-end close without a resize window.", "decision", "technical", False,
     [("Redshift", "database"), ("Snowflake", "database"), ("dc2.large", "config"), ("month-end close", "event")],
     [("Snowflake", "Redshift", "REPLACES")],
     "which warehouse swap retired the dc2.large node pattern before the month-end close window",
     "snowflake redshift dc2 migrate elastic scale month end close resize"),
    # --- 2 ---
    ("BigQuery slot reservations now back the finance workload: autoscaling was overspending on on-demand during quarter-close, so a 500-slot committed reservation with idle slot sharing cut costs by forty percent.", "decision", "technical", False,
     [("BigQuery", "database"), ("slot reservations", "concept"), ("autoscaling", "concept"), ("idle slot sharing", "concept")],
     [("slot reservations", "autoscaling", "REPLACES")],
     "which BigQuery pricing model replaced autoscaling for the finance workload and why",
     "bigquery slot reservation autoscaling finance quarter close commit share"),
    # --- 3 ---
    ("ClickHouse MergeTree is the default engine for the events fact table; a ReplacingMergeTree variant handles late-arriving upserts while SummingMergeTree rolls up per-minute metrics before dashboards hit them.", "architecture", "technical", False,
     [("ClickHouse", "database"), ("MergeTree", "algorithm"), ("ReplacingMergeTree", "algorithm"), ("SummingMergeTree", "algorithm")],
     [("ReplacingMergeTree", "MergeTree", "EXTENDS"), ("SummingMergeTree", "MergeTree", "EXTENDS")],
     "which ClickHouse engine family handles events ingestion, upserts, and per-minute rollups",
     "clickhouse mergetree replacing summing engine fact events upsert rollup"),
    # --- 4 ---
    ("StarRocks adopted for the ad-hoc analytics layer on top of Iceberg tables; the MPP architecture with pipelined execution and a cost-based optimizer beat Trino on p95 latency for the five-join attribution query.", "decision", "technical", False,
     [("StarRocks", "database"), ("Trino", "database"), ("Iceberg", "technology"), ("cost-based optimizer", "algorithm")],
     [("StarRocks", "Trino", "REPLACES")],
     "which MPP engine replaced Trino for ad-hoc analytics over Iceberg and which metric drove the swap",
     "starrocks trino iceberg mpp cost optimizer p95 attribution latency"),
    # --- 5 ---
    ("Databricks SQL warehouse is sized as a Medium Serverless for BI and a Large Pro for the ingestion-heavy ETL; Photon execution shaved about thirty-five percent off dbt model runtimes for the wide join stages.", "fact", "technical", False,
     [("Databricks SQL", "database"), ("Photon", "technology"), ("dbt", "tool"), ("Serverless", "concept")],
     [("dbt", "Photon", "USES")],
     "how is the Databricks SQL warehouse sized and what gave the thirty-five percent runtime drop for dbt",
     "databricks sql photon dbt serverless pro medium large runtime join"),
    # --- 6 ---
    ("DuckDB powers the local analyst notebooks: pulling a partition of parquet down to a laptop and querying it without standing up a cluster solved the iteration-speed complaint the BI team had been raising for months.", "decision", "technical", False,
     [("DuckDB", "database"), ("parquet", "technology"), ("BI team", "organization")],
     [("DuckDB", "parquet", "USES")],
     "which local analytics engine replaced cluster spin-ups for BI analyst parquet iteration",
     "duckdb parquet laptop local analyst notebook bi iteration cluster"),
    # --- 7 ---
    ("Apache Druid backs the real-time ops dashboard; rollup on ingestion plus the bitmap-indexed dimension columns keep p99 dashboard latency under 200 ms even during spiky promo events.", "architecture", "technical", False,
     [("Apache Druid", "database"), ("rollup", "concept"), ("bitmap-indexed", "algorithm"), ("promo events", "event")],
     [("Apache Druid", "rollup", "USES")],
     "which engine and indexing strategy keep the real-time ops dashboard under 200 ms at p99",
     "druid rollup bitmap index dashboard p99 promo event realtime ops"),
    # --- 8 ---
    ("Pinot replaced an in-house Elasticsearch aggregation layer for the user-facing analytics product; the segment-pruning plus star-tree index combination made per-tenant cohort queries sub-second.", "milestone", "technical", False,
     [("Pinot", "database"), ("Elasticsearch", "database"), ("star-tree index", "algorithm"), ("segment-pruning", "concept")],
     [("Pinot", "Elasticsearch", "REPLACES")],
     "which engine and index replaced the Elasticsearch aggregation layer for user-facing cohort queries",
     "pinot elasticsearch star tree segment prune cohort tenant sub second"),
    # --- 9 ---
    ("Firebolt was evaluated as a Snowflake alternative but declined: the sparse indexes helped on point lookups but the lack of time-travel and the smaller ecosystem around dbt adapters made adoption risky for the core finance mart.", "decision", "technical", False,
     [("Firebolt", "database"), ("Snowflake", "database"), ("sparse index", "algorithm"), ("time-travel", "concept"), ("dbt", "tool")],
     [("Snowflake", "Firebolt", "PREFERS")],
     "why did Firebolt lose the bake-off against Snowflake for the core finance mart",
     "firebolt snowflake sparse index time travel dbt adapter ecosystem finance"),
    # --- 10. noise ---
    ("The office espresso machine has started grinding unevenly and the morning queue has drifted backward by about four minutes.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Greenplum is on the decommission list: the append-optimized column tables served us for years, but the lack of separation of compute and storage is now the bottleneck for the data-science sandbox workload.", "decision", "technical", False,
     [("Greenplum", "database"), ("append-optimized", "concept"), ("data-science sandbox", "project")],
     [],
     "why is Greenplum being decommissioned for the data-science sandbox workload",
     "greenplum append optimized column compute storage separation decommission"),
    # --- 12 ---
    ("Vertica still owns the telecom billing mart; projections are hand-tuned per query class and the database designer auto-tune pass is run quarterly rather than after every schema change.", "fact", "technical", False,
     [("Vertica", "database"), ("projections", "concept"), ("database designer", "tool"), ("billing mart", "project")],
     [("Vertica", "projections", "USES")],
     "how does the Vertica telecom mart keep projections tuned without rerunning designer every change",
     "vertica projection database designer telecom billing mart quarterly tune"),
    # --- 13 ---
    ("Trino federates across Hive, Iceberg, and the MySQL transactional replica; the dynamic filtering pushdown on the Iceberg side eliminated the broadcast-join memory blowups we were seeing on the largest tenant.", "architecture", "technical", False,
     [("Trino", "database"), ("Hive", "database"), ("Iceberg", "technology"), ("MySQL", "database"), ("dynamic filtering", "concept")],
     [("Trino", "dynamic filtering", "USES")],
     "which Trino feature eliminated broadcast-join memory blowups on the largest tenant",
     "trino hive iceberg mysql dynamic filter pushdown broadcast join tenant"),
    # --- 14 ---
    ("Presto kept its seat for the legacy ad-hoc workload because rewriting the dashboard catalog to Trino dialect wasn't cheap; new workloads land on Trino by default per the architecture council note.", "preference", "technical", False,
     [("Presto", "database"), ("Trino", "database"), ("architecture council", "organization")],
     [("Trino", "Presto", "REPLACES")],
     "which engine is the new-workload default and why did legacy ad-hoc stay on Presto",
     "presto trino legacy ad hoc dashboard catalog dialect council default"),
    # --- 15 ---
    ("The dbt project is split into staging, intermediate, and marts layers with a semantic-layer manifest on top; the MetricFlow YAML centralises revenue definitions so Looker and Mode no longer disagree on monthly totals.", "architecture", "technical", False,
     [("dbt", "tool"), ("MetricFlow", "tool"), ("Looker", "tool"), ("Mode", "tool"), ("semantic-layer", "concept")],
     [("dbt", "MetricFlow", "USES")],
     "which semantic-layer tool stopped Looker and Mode from disagreeing on monthly revenue",
     "dbt metricflow looker mode semantic layer revenue manifest stage mart"),
    # --- 16 ---
    ("Cube was rejected for the semantic layer: MetricFlow integrated directly with dbt artifacts and reused the existing sources and exposures, while Cube required a parallel modelling layer the analytics team didn't want to maintain.", "decision", "technical", False,
     [("Cube", "tool"), ("MetricFlow", "tool"), ("dbt", "tool"), ("analytics team", "organization")],
     [("MetricFlow", "Cube", "PREFERS")],
     "why did MetricFlow beat Cube as the semantic layer for the dbt stack",
     "cube metricflow dbt semantic layer parallel modelling exposure source"),
    # --- 17 ---
    ("Snowflake micro-partitions are 50 to 500 MB compressed columnar chunks with automatic clustering metadata; pruning reads only the partitions whose min-max range overlaps the filter, which is why well-ordered date columns hit near-zero scan for recent queries.", "fact", "technical", False,
     [("Snowflake", "database"), ("micro-partitions", "concept"), ("clustering metadata", "concept"), ("min-max range", "algorithm")],
     [("micro-partitions", "min-max range", "USES")],
     "what gives Snowflake near-zero scan on well-ordered date-filtered queries",
     "snowflake micro partition min max prune cluster metadata columnar date"),
    # --- 18 ---
    ("Zero-copy clones on Snowflake back every dev environment: a production clone for debugging takes seconds and bills only the changed micro-partitions, so we stopped maintaining a dedicated snapshot refresh pipeline.", "architecture", "technical", False,
     [("Snowflake", "database"), ("Zero-copy clones", "concept"), ("dev environment", "concept"), ("snapshot refresh", "concept")],
     [("Zero-copy clones", "snapshot refresh", "REPLACES")],
     "which Snowflake feature retired the dedicated snapshot-refresh pipeline for dev environments",
     "snowflake zero copy clone dev environment snapshot refresh pipeline debug"),
    # --- 19 ---
    ("Snowflake time-travel retention is set to 7 days on production schemas and 1 day on staging; the AT(TIMESTAMP => ...) clause is the standard recovery tool for accidental merge-update wipes during dbt runs.", "reference", "technical", False,
     [("Snowflake", "database"), ("time-travel", "concept"), ("AT(TIMESTAMP =>", "api"), ("dbt", "tool")],
     [],
     "how is Snowflake time-travel configured and which syntax recovers from an accidental merge wipe",
     "snowflake time travel retention at timestamp dbt merge wipe recover"),
    # --- 20 ---
    ("BigQuery clustering on (tenant_id, event_date) cut the attribution query scan from 1.2 TB to 40 GB; partition-by-date alone wasn't enough because tenant access is always tenant-scoped in the WHERE clause.", "milestone", "technical", False,
     [("BigQuery", "database"), ("clustering", "concept"), ("tenant_id", "field"), ("event_date", "field")],
     [],
     "which BigQuery clustering key combo cut the attribution scan from 1.2 TB to 40 GB",
     "bigquery cluster tenant event date attribution scan partition tb gb"),
    # --- 21 ---
    ("Columnar storage on Parquet with Zstd level 3 compression was the sweet spot: level 9 squeezed another eight percent but doubled compression CPU, and the warehouse loader budget did not have room.", "decision", "technical", False,
     [("Parquet", "technology"), ("Zstd", "algorithm"), ("warehouse loader", "service")],
     [("Parquet", "Zstd", "USES")],
     "which Parquet compression setting won on the loader-budget tradeoff for the warehouse",
     "parquet zstd level 3 9 compression cpu loader budget columnar tradeoff"),
    # --- 22 ---
    ("ORC versus Parquet for the lakehouse: Parquet won because the entire Python and Spark ecosystem ships with better-optimised readers, even though ORC's stripe stats and built-in bloom filters are genuinely nicer on paper.", "decision", "technical", False,
     [("ORC", "technology"), ("Parquet", "technology"), ("Spark", "framework"), ("Python", "language"), ("bloom filter", "algorithm")],
     [("Parquet", "ORC", "PREFERS")],
     "why did Parquet win over ORC for the lakehouse despite ORC's stripe stats and bloom filters",
     "orc parquet lakehouse spark python reader stripe bloom ecosystem"),
    # --- 23 ---
    ("Apache Arrow is the in-memory format across the Python notebooks, the Rust ingestion service, and the DuckDB zero-copy integration; the old pandas-to-JSON-to-Spark path is a memory hog we no longer tolerate in production.", "architecture", "technical", False,
     [("Apache Arrow", "library"), ("Python", "language"), ("Rust", "language"), ("DuckDB", "database"), ("pandas", "library"), ("Spark", "framework")],
     [("Apache Arrow", "pandas", "REPLACES")],
     "which in-memory format replaced the pandas-to-JSON-to-Spark path across notebooks and ingestion",
     "arrow python rust duckdb pandas spark json memory zero copy notebook"),
    # --- 24 ---
    ("Materialized views on Redshift now refresh incrementally for the customer_daily mart; the AUTO REFRESH setting handles the trigger but we still pin a concurrency-scaling cluster window during the 08:00 load for predictability.", "architecture", "technical", False,
     [("Redshift", "database"), ("Materialized views", "concept"), ("customer_daily", "project"), ("concurrency-scaling", "concept")],
     [],
     "how does the customer_daily mart stay fresh on Redshift and why the pinned concurrency window",
     "redshift materialized view auto refresh customer daily concurrency scaling"),
    # --- 25 ---
    ("ClickHouse projections backed by a materialized column pulled the rollup-style group-by off the hot path; the storage overhead runs about 15 percent but p95 for the per-hour dashboards is now 80 ms flat.", "fact", "technical", False,
     [("ClickHouse", "database"), ("projections", "concept"), ("materialized column", "concept")],
     [],
     "which ClickHouse feature moved the rollup group-by off the hot path for per-hour dashboards",
     "clickhouse projection materialized column rollup group p95 dashboard hour"),
    # --- 26 ---
    ("Slot-based query scheduling on BigQuery was misconfigured for six weeks: the reservations were split across the BI project and the ML project without idle sharing, so ML training queues blocked dashboard users at month-end.", "problem", "technical", False,
     [("BigQuery", "database"), ("Slot-based query scheduling", "concept"), ("BI project", "project"), ("ML project", "project"), ("idle sharing", "concept")],
     [],
     "which BigQuery reservation misconfiguration let ML training queues block dashboard users",
     "bigquery slot reservation bi ml idle share block dashboard month end"),
    # --- 27 ---
    ("Snowflake resource monitors sit on the warehouses with a 100-credit daily cap on the ad-hoc pool; the suspension action triggered twice last quarter and caught a runaway SELECT * from a new analyst in the first hour.", "reference", "technical", False,
     [("Snowflake", "database"), ("resource monitors", "concept"), ("ad-hoc pool", "service"), ("SELECT *", "command")],
     [("resource monitors", "ad-hoc pool", "APPLIES_TO")],
     "how are Snowflake resource monitors set up to catch runaway analyst queries on the ad-hoc pool",
     "snowflake resource monitor credit cap ad hoc pool suspend analyst runaway"),
    # --- 28 ---
    ("Redshift workload management switched from manual queues to automatic WLM with query priority; short-query acceleration still runs as its own queue because the mart refresh jobs kept starving interactive BI users under auto alone.", "decision", "technical", False,
     [("Redshift", "database"), ("WLM", "concept"), ("query priority", "concept"), ("short-query acceleration", "concept"), ("manual queues", "concept")],
     [("WLM", "manual queues", "REPLACES")],
     "which Redshift WLM change kept BI users unblocked while mart refreshes ran",
     "redshift wlm automatic queue priority short query acceleration manual bi"),
    # --- 29 ---
    ("The Trino resource group tree has etl under 70 percent of cluster memory and adhoc under 25 percent, with a catch-all at 5 percent; long-running analyst queries on adhoc can no longer starve the nightly ETL jobs.", "reference", "technical", False,
     [("Trino", "database"), ("resource group", "concept"), ("etl", "project"), ("adhoc", "project")],
     [],
     "how is the Trino resource group tree carved to keep ETL unblocked by adhoc analyst queries",
     "trino resource group etl adhoc memory cluster analyst nightly starve"),
    # --- 30 ---
    ("The cost-based optimizer on Trino now has ANALYZE running nightly against Iceberg metadata; join-order regressions from stale stats that were showing up on the largest fact-fact join have not reappeared in three weeks.", "problem", "technical", False,
     [("Trino", "database"), ("cost-based optimizer", "algorithm"), ("ANALYZE", "command"), ("Iceberg", "technology")],
     [("ANALYZE", "cost-based optimizer", "SUPPORTS")],
     "which nightly job keeps the Trino cost-based optimizer honest on Iceberg join-order",
     "trino cost optimizer analyze iceberg stale stats join order regression"),
    # --- 31 ---
    ("Data skew on the customer_orders join was collapsing one Spark executor; salting the hot tenant_id with a random suffix on both sides and then stripping it post-aggregate brought the stage from 42 minutes down to 6.", "fact", "technical", False,
     [("customer_orders", "project"), ("Spark", "framework"), ("tenant_id", "field"), ("salting", "algorithm")],
     [("salting", "Spark", "APPLIES_TO")],
     "which skew-handling technique pulled the customer_orders join from 42 to 6 minutes on Spark",
     "spark skew salt tenant id customer orders join executor aggregate strip"),
    # --- 32 ---
    ("Snowflake search optimization service was enabled on the events table for point lookups on event_id; the cost is real but the support team's incident triage went from 8 seconds to 200 ms per lookup.", "decision", "technical", False,
     [("Snowflake", "database"), ("search optimization service", "concept"), ("events table", "project"), ("event_id", "field")],
     [],
     "which Snowflake feature pulled incident-triage event_id lookups from 8 s to 200 ms",
     "snowflake search optimization service event id point lookup triage ms"),
    # --- 33 ---
    ("BigQuery materialized views replaced a nightly scheduled query for the revenue_by_day rollup; incremental refresh runs every 30 minutes and BI users see intraday revenue without a manual kick.", "milestone", "technical", False,
     [("BigQuery", "database"), ("materialized views", "concept"), ("revenue_by_day", "project"), ("scheduled query", "concept")],
     [("materialized views", "scheduled query", "REPLACES")],
     "which BigQuery feature replaced the nightly scheduled-query pattern for revenue_by_day",
     "bigquery materialized view revenue by day scheduled query incremental bi"),
    # --- 34 ---
    ("Iceberg table format won over Delta Lake and Hudi for the lakehouse: hidden partitioning removed the dreaded WHERE partition_date-match dance, and the catalog-agnostic design meant Trino and Spark query the same metadata without a sync job.", "decision", "technical", False,
     [("Iceberg", "technology"), ("Delta Lake", "technology"), ("Hudi", "technology"), ("Trino", "database"), ("Spark", "framework")],
     [("Iceberg", "Delta Lake", "PREFERS"), ("Iceberg", "Hudi", "PREFERS")],
     "why did Iceberg win over Delta Lake and Hudi for the shared lakehouse",
     "iceberg delta hudi trino spark hidden partition catalog lakehouse"),
    # --- 35 ---
    ("Iceberg partition evolution let us re-partition the orders table from daily to hourly without a rewrite; old data keeps its daily layout and new writes land hourly, and planning still prunes correctly across both.", "fact", "technical", False,
     [("Iceberg", "technology"), ("partition evolution", "concept"), ("orders table", "project")],
     [("orders table", "Iceberg", "USES")],
     "which Iceberg feature re-partitioned the orders table from daily to hourly without a rewrite",
     "iceberg partition evolution orders daily hourly rewrite prune planning"),
    # --- 36 ---
    ("Snowflake automatic clustering on the orders_fact table kicked in after 200 million rows; we stopped manually scheduling REORG jobs because the background re-clustering keeps the min-max stats tight enough for pruning.", "milestone", "technical", False,
     [("Snowflake", "database"), ("automatic clustering", "concept"), ("orders_fact", "project"), ("REORG", "command")],
     [("automatic clustering", "REORG", "REPLACES")],
     "which Snowflake feature let us retire the manually scheduled REORG on orders_fact",
     "snowflake automatic clustering orders fact reorg min max prune manual"),
    # --- 37 ---
    ("Redshift Spectrum handles the cold historical range: queries over data older than 90 days transparently hit the S3-backed external schema, and the managed storage stays warm for recent partitions that drive the live BI views.", "milestone", "technical", False,
     [("Redshift Spectrum", "service"), ("S3", "service"), ("external schema", "concept"), ("managed storage", "concept")],
     [("Redshift Spectrum", "S3", "USES")],
     "how does Redshift Spectrum split cold historical data from the warm managed storage tier",
     "redshift spectrum s3 external schema managed storage cold warm bi partition"),
    # --- 38 ---
    ("ClickHouse distributed tables sit on top of sharded ReplicatedMergeTree; the sharding key is cityHash64(tenant_id) and the weight is tuned so the two biggest tenants don't end up on the same physical node.", "architecture", "technical", False,
     [("ClickHouse", "database"), ("distributed tables", "concept"), ("ReplicatedMergeTree", "algorithm"), ("cityHash64", "algorithm"), ("tenant_id", "field")],
     [("distributed tables", "ReplicatedMergeTree", "USES")],
     "how is the ClickHouse shard map laid out to keep the two biggest tenants on separate nodes",
     "clickhouse distributed shard replicated merge tree cityhash64 tenant weight"),
    # --- 39 ---
    ("Druid segment granularity is hourly with a one-month retention on the hot tier and a one-year retention on the cold tier; historical nodes serve the cold tier from S3-backed deep storage and the broker transparently stitches the two.", "architecture", "technical", False,
     [("Druid", "database"), ("segment granularity", "concept"), ("hot tier", "concept"), ("cold tier", "concept"), ("S3", "service"), ("broker", "service")],
     [("Druid", "S3", "USES")],
     "how does Druid split hot and cold tier retention and which component stitches them",
     "druid segment hourly hot cold tier s3 deep storage broker retention"),
    # --- 40 ---
    ("Pinot upsert tables back the live order-status dashboard; the primary key is order_id and partial upserts let us patch individual columns without a full row rewrite, which dropped ingestion CPU noticeably.", "fact", "technical", False,
     [("Pinot", "database"), ("upsert tables", "concept"), ("order_id", "field"), ("partial upserts", "concept")],
     [("Pinot", "partial upserts", "USES")],
     "which Pinot feature backs the live order-status dashboard and patches columns without full rewrite",
     "pinot upsert table order id partial column rewrite dashboard ingestion"),
    # --- 41 ---
    ("Preferring dbt Core over dbt Cloud for this shop: self-hosted Airflow already runs the schedule, the IDE-in-browser isn't a fit for analysts who live in VS Code, and the cost line item didn't clear the quarterly review.", "preference", "technical", False,
     [("dbt Core", "tool"), ("dbt Cloud", "tool"), ("Airflow", "tool"), ("VS Code", "tool")],
     [("dbt Core", "dbt Cloud", "PREFERS")],
     "why does the team prefer dbt Core over dbt Cloud given Airflow and VS Code are already in place",
     "dbt core cloud airflow vs code self host schedule ide browser cost"),
    # --- 42 ---
    ("Preferring Snowflake's Snowpark over pushing UDFs through Python UDTFs for the feature engineering: the vectorised DataFrame API keeps the data in-warehouse and avoids the round-trip the UDTF path was paying per batch.", "preference", "technical", False,
     [("Snowpark", "tool"), ("Python UDTF", "concept"), ("DataFrame API", "api"), ("feature engineering", "project")],
     [("Snowpark", "Python UDTF", "PREFERS")],
     "why prefer Snowpark over Python UDTFs for feature engineering in the warehouse",
     "snowpark python udtf dataframe api feature engineering round trip batch"),
    # --- 43. noise ---
    ("The building's elevator alarm has a new cadence that sounds uncomfortably close to the mainframe UPS beeper from the downstairs server room.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Preferring the star schema over a fully denormalised OBT for the finance mart: dbt tests are easier to write against a handful of dimensions, and the semantic-layer metrics compose cleaner when joins are explicit.", "preference", "technical", False,
     [("star schema", "pattern"), ("OBT", "pattern"), ("dbt", "tool"), ("finance mart", "project")],
     [("star schema", "OBT", "PREFERS")],
     "why prefer the star schema over a one-big-table approach for the finance mart",
     "star schema obt one big table dbt finance mart dimension semantic metric"),
    # --- 45 ---
    ("Milestone: the GA of the shared semantic layer landed this week, 34 metrics moved from scattered Looker PDT definitions into the MetricFlow YAML, and the cross-tool drift dashboard finally reads zero.", "milestone", "technical", False,
     [("semantic layer", "concept"), ("Looker", "tool"), ("PDT", "concept"), ("MetricFlow", "tool"), ("drift dashboard", "project")],
     [("MetricFlow", "PDT", "REPLACES")],
     "what was shipped with the semantic-layer GA and how did the drift dashboard behave after",
     "semantic layer ga metricflow looker pdt metric drift dashboard cross tool"),
    # --- 46 ---
    ("Reference config for Snowflake warehouses: X-Small auto-suspend 60, Small auto-suspend 120, Medium auto-suspend 300, and the Large reporting warehouse set to multi-cluster with min 1 max 4 and scaling policy STANDARD.", "reference", "technical", False,
     [("Snowflake", "database"), ("auto-suspend", "config"), ("multi-cluster", "concept"), ("STANDARD", "config")],
     [],
     "what are the standard Snowflake auto-suspend and multi-cluster settings per warehouse tier",
     "snowflake auto suspend multi cluster standard xs small medium large policy"),
    # --- 47 ---
    ("Reference pattern for a dbt incremental model on Snowflake: use merge with a unique_key, schedule after the staging load, and set on_schema_change to append_new_columns so a new source field lands without a full-refresh manual step.", "reference", "technical", False,
     [("dbt", "tool"), ("Snowflake", "database"), ("merge", "command"), ("unique_key", "config"), ("on_schema_change", "config")],
     [],
     "what is the canonical dbt incremental-model config on Snowflake for absorbing new source columns",
     "dbt incremental snowflake merge unique key on schema change append column"),
    # --- 48 ---
    ("Reference: Redshift distribution styles pick as follows, KEY for the largest fact joined on a stable key, EVEN for data without a clear join column, ALL for small dimensions under 2 million rows, AUTO for evolving tables.", "reference", "technical", False,
     [("Redshift", "database"), ("KEY", "config"), ("EVEN", "config"), ("ALL", "config"), ("AUTO", "config")],
     [],
     "which distribution styles apply to which Redshift table shapes as a reference rule of thumb",
     "redshift distribution key even all auto fact dimension stable evolving"),
    # --- 49 ---
    ("Problem: a slot-scheduler starvation bug hit the Trino cluster when a single analyst ran a 200-way UNION ALL; the fix was a per-user concurrent-query limit in the adhoc resource group plus a query-wall timeout of 30 minutes.", "problem", "technical", False,
     [("Trino", "database"), ("slot-scheduler", "concept"), ("UNION ALL", "command"), ("resource group", "concept"), ("query-wall timeout", "config")],
     [("resource group", "slot-scheduler", "FIXES")],
     "which Trino configuration change fixed the 200-way UNION ALL starvation incident",
     "trino slot scheduler starve union all resource group user limit timeout"),
    # --- 50 ---
    ("BigQuery BI Engine reservation of 16 GB pinned the exec-dashboard tables in memory; the sub-second p95 we promised the CFO is hitting now, and the cost is justified against the slot-hour savings from not scanning those tables each refresh.", "milestone", "technical", False,
     [("BigQuery", "database"), ("BI Engine", "service"), ("exec-dashboard", "project"), ("CFO", "person")],
     [("BI Engine", "exec-dashboard", "APPLIES_TO")],
     "which BigQuery feature pinned the exec-dashboard tables to hit the CFO's sub-second p95 promise",
     "bigquery bi engine reservation exec dashboard cfo p95 slot hour memory"),
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
