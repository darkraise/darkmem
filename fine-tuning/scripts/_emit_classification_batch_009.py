"""One-off emitter for classification top-up batch-009.

Mode: contrastive_decision_architecture — data-pipeline slice.
Each pair consists of one `decision` row (a data-engineering choice) and one
`architecture` row (an ongoing structural description of the pipeline).

Emits 50 pairs (100 rows) to data/v2/classification/batch_009.tmp.jsonl
with row ids class-00801..00900 and pair ids cls-pair-00401..00450.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_009.tmp.jsonl"
ID_OFFSET = 800
PAIR_OFFSET = 400

# Each entry: (decision_text, architecture_text)
# ≥20 distinct data-pipeline topics across: ingestion, stream processing, batch
# ETL, data-lake formats, warehouse, orchestrator, reverse ETL, CDC, schema
# registry, observability, quality testing, lineage, privacy, archival.
PAIRS: list[tuple[str, str]] = [
    # 1 — ingestion: Kinesis -> Redpanda
    (
        "Switched the event pipeline from Kinesis to Redpanda after throughput stopped keeping up with the dashboards.",
        "Events land in a Redpanda topic, feed a Flink job, and materialise into Iceberg tables partitioned by event_date.",
    ),
    # 2 — stream processing: Spark Streaming -> Flink
    (
        "Moved the real-time aggregations off Spark Structured Streaming onto Flink once watermark handling became too brittle.",
        "Flink jobs consume from Kafka, keyed by tenant_id, and sink rolling aggregates into a RocksDB-backed state store before emitting to a ClickHouse view.",
    ),
    # 3 — batch ETL: Airflow Bash -> dbt
    (
        "Replaced the hand-written Airflow Bash tasks with dbt models so analytics engineers could own transformation logic.",
        "dbt runs on a Snowflake warehouse, orchestrated by Airflow's KubernetesPodOperator, with sources mapped to raw Fivetran schemas.",
    ),
    # 4 — data lake format: Parquet flat -> Iceberg
    (
        "Adopted Apache Iceberg over plain Parquet directories because partition evolution kept breaking our backfills.",
        "Raw Parquet writes land in S3, a Glue job registers them as Iceberg tables, and Trino reads snapshots for ad-hoc analytics.",
    ),
    # 5 — warehouse: Redshift -> BigQuery
    (
        "Chose BigQuery over Redshift for the new analytics surface since the workload was bursty and columnar scan costs dominated.",
        "Fivetran lands CRM data into BigQuery raw datasets, dbt materialises marts, and Looker reads from a dedicated semantic layer project.",
    ),
    # 6 — orchestrator: Airflow -> Dagster
    (
        "Migrated orchestration from Airflow to Dagster after asset-centric lineage became a hard requirement for the platform team.",
        "Dagster assets define the warehouse graph, sensors poll S3 prefixes, and the daemon schedules partitioned backfills against the Snowflake target.",
    ),
    # 7 — reverse ETL: home-grown -> Hightouch
    (
        "Picked Hightouch for reverse ETL so that go-to-market syncs stopped living in a brittle Python cron job.",
        "Hightouch reads curated marts from Snowflake and syncs them into Salesforce and HubSpot on a 15-minute cadence with diff-based upserts.",
    ),
    # 8 — CDC: Kafka Connect -> Debezium embedded
    (
        "Replaced the Kafka Connect JDBC source with Debezium for Postgres CDC because logical replication slots gave us ordered change streams.",
        "Debezium reads from Postgres replication slots, publishes to Kafka topics per table, and a Flink job upserts them into an Iceberg mirror.",
    ),
    # 9 — schema registry: none -> Confluent Schema Registry
    (
        "Introduced Confluent Schema Registry after a malformed Avro message silently corrupted a downstream mart for two days.",
        "Producers register Avro schemas against the registry, Kafka brokers enforce compatibility, and consumers resolve schema ids lazily via a local cache.",
    ),
    # 10 — pipeline observability: custom -> Monte Carlo
    (
        "Adopted Monte Carlo for data observability since our custom freshness checks could not cover cross-schema volume anomalies.",
        "Monte Carlo agents query Snowflake INFORMATION_SCHEMA, detect freshness and volume anomalies, and post incidents into a dedicated Slack channel.",
    ),
    # 11 — data quality testing: bespoke -> Great Expectations
    (
        "Standardised on Great Expectations over the bespoke assertion library because suites needed to be generated from JSON schemas.",
        "Great Expectations runs inside Airflow, validates Parquet batches on S3, and writes data docs back to a versioned S3 bucket.",
    ),
    # 12 — lineage: docs -> OpenLineage
    (
        "Chose OpenLineage over the hand-maintained lineage wiki so upstream breakages would show up in pager alerts.",
        "Airflow emits OpenLineage events to a Marquez backend, dbt runs feed run-level lineage, and the UI surfaces downstream impact graphs.",
    ),
    # 13 — privacy / tokenisation: in-app -> Skyflow
    (
        "Moved PII tokenisation from an in-app library to Skyflow after auditors flagged inconsistent masking across services.",
        "Skyflow stores raw PII behind a vault proxy, services persist only tokens, and detokenisation happens at a policy-gated API during fulfilment.",
    ),
    # 14 — archival: on-warehouse -> S3 Glacier
    (
        "Tiered cold events out of Snowflake into S3 Glacier Deep Archive once query patterns showed no reads past 24 months.",
        "A nightly Dagster job exports partitions older than two years as Parquet to S3 Glacier and drops them from the warehouse with an audit row.",
    ),
    # 15 — ingestion connector: bespoke scripts -> Fivetran
    (
        "Replaced the bespoke SaaS ingestion scripts with Fivetran so that API schema drift stopped paging the data team.",
        "Fivetran connectors land raw tables in Snowflake, dbt sources reference them read-only, and a single orchestration DAG monitors sync cursors.",
    ),
    # 16 — stream storage: Kafka -> Pulsar
    (
        "Adopted Apache Pulsar over Kafka for the cross-region bus once geo-replication and multi-tenant isolation became first-class requirements.",
        "Pulsar brokers run per region with geo-replicated namespaces, functions handle lightweight enrichment, and BookKeeper provides the durable log layer.",
    ),
    # 17 — transformation language: Python -> SQL/dbt
    (
        "Rewrote the pandas transformation layer in SQL running under dbt so that analysts could own the models without touching Python.",
        "dbt models are organised into staging, intermediate, and marts layers, with exposures declared per dashboard and tests on every primary key.",
    ),
    # 18 — warehouse compute: multi-cluster shared -> per-team virtual warehouses
    (
        "Split the shared Snowflake warehouse into per-team virtual warehouses after noisy-neighbour pipelines starved the finance dashboards.",
        "Each team owns a dedicated virtual warehouse sized by workload, a resource monitor caps credits monthly, and queries route via role-based grants.",
    ),
    # 19 — batch engine: Hive -> Trino
    (
        "Replaced Hive-on-MR with Trino for interactive queries over the lake once analysts started abandoning queries at the 5-minute mark.",
        "Trino coordinators run on Kubernetes, workers autoscale on CPU pressure, and the Iceberg connector points at a shared Glue metastore.",
    ),
    # 20 — storage format: CSV drops -> Parquet
    (
        "Dropped CSV as the landing format in favour of Parquet after repeated quoting bugs corrupted downstream joins.",
        "Producers write Snappy-compressed Parquet to S3 with hourly prefixes, a Glue crawler registers the tables, and Athena exposes them for ad-hoc queries.",
    ),
    # 21 — scheduler: cron -> Prefect
    (
        "Swapped the legacy cron scheduler for Prefect so that retries and notifications stopped being copy-pasted into every script.",
        "Prefect flows run in an agent pool on ECS, use a Postgres backend for state, and register with a shared work queue per environment.",
    ),
    # 22 — notebook productionisation: ad-hoc -> Hex
    (
        "Adopted Hex for analyst-authored pipelines so that notebooks graduated into versioned, scheduled artifacts without a full rewrite.",
        "Hex projects connect to Snowflake via OAuth, publish scheduled runs, and expose parameterised apps that hand off heavy queries to dbt exposures.",
    ),
    # 23 — privacy: customer-managed keys decision
    (
        "Moved to customer-managed KMS keys for all warehouse object storage after a compliance review flagged tenant-level blast radius concerns.",
        "Each tenant's S3 prefix is encrypted with a dedicated KMS key, Snowflake external tables reference the key id, and revocation happens through a platform API.",
    ),
    # 24 — event schema evolution: JSON -> Protobuf
    (
        "Switched event payloads from ad-hoc JSON to Protobuf once producer-consumer drift became the most common data incident.",
        "Protobuf descriptors live in a versioned monorepo, a CI job publishes them to the schema registry, and Flink consumers resolve schemas by fingerprint.",
    ),
    # 25 — query federation: ETL copy -> Trino federation
    (
        "Adopted Trino federation instead of nightly ETL copies between warehouses once product analytics needed joins across Postgres and the lake.",
        "Trino exposes a single SQL surface that federates Postgres, MySQL, Iceberg, and Elasticsearch connectors behind a shared catalog namespace.",
    ),
    # 26 — ingestion: webhook buffer -> API Gateway + Firehose
    (
        "Replaced the home-grown webhook buffer service with API Gateway plus Kinesis Firehose once traffic spikes overwhelmed its Redis queue.",
        "API Gateway authenticates webhooks, Firehose buffers events for up to 60 seconds, and a Lambda transforms them into Parquet before landing on S3.",
    ),
    # 27 — stream processing: ksqlDB -> Flink SQL
    (
        "Moved streaming SQL workloads off ksqlDB onto Flink SQL after state store corruption recurred on the 0.29 release.",
        "Flink SQL jobs run on a session cluster, checkpoint to S3 every 30 seconds, and register sinks through the Hive catalog for cross-tool discovery.",
    ),
    # 28 — warehouse: on-prem Teradata -> Databricks
    (
        "Retired Teradata for Databricks SQL once hardware refresh costs crossed the three-year Databricks commit.",
        "Databricks workspaces host Unity Catalog, Delta Lake tables sit on ADLS Gen2, and SQL warehouses serve BI tools behind a Unity-governed metastore.",
    ),
    # 29 — orchestrator: Argo Workflows -> Flyte
    (
        "Chose Flyte over Argo Workflows for ML pipelines because typed interfaces and cached artifacts mattered more than generic container DAGs.",
        "Flyte executions run on a Kubernetes cluster, artifacts persist in an S3-backed data catalog, and task caching keys off input hashes and container digests.",
    ),
    # 30 — reverse ETL: Census -> Hightouch
    (
        "Switched the reverse ETL vendor from Census to Hightouch after their audience-builder better matched the marketing team's workflow.",
        "Hightouch models resolve against Snowflake marts, audiences sync incrementally into Braze and Iterable, and observability flows into the existing Datadog account.",
    ),
    # 31 — CDC: Maxwell -> Debezium
    (
        "Replaced Maxwell with Debezium for MySQL CDC once we needed transactional metadata and ordered schema change events.",
        "Debezium tails MySQL binlogs, emits events to Kafka topics keyed by primary key, and a downstream Kafka Streams job materialises a compacted changelog.",
    ),
    # 32 — schema registry: Confluent -> Apicurio
    (
        "Swapped Confluent Schema Registry for Apicurio after the self-hosted license model no longer matched the platform budget.",
        "Apicurio runs behind an internal gateway, stores artifacts in Postgres, and integrates with the Kafka connect cluster via the standard Avro serde.",
    ),
    # 33 — pipeline observability: logs -> Soda
    (
        "Added Soda Core for SQL-based data checks once shallow freshness alerts kept missing row-level quality regressions.",
        "Soda scans run as post-task steps in Airflow, write check results to a Postgres metadata store, and raise PagerDuty incidents on critical failures.",
    ),
    # 34 — data quality: Deequ -> Great Expectations
    (
        "Moved away from Deequ to Great Expectations once analysts without Scala experience needed to author and review checks.",
        "Great Expectations runs on a dedicated Kubernetes deployment, stores validation results in S3, and renders data docs behind an SSO-protected static site.",
    ),
    # 35 — lineage: Datahub -> OpenMetadata
    (
        "Chose OpenMetadata over Datahub for the lineage catalog because the bundled profiler and governance workflow covered a wider surface.",
        "OpenMetadata ingests Airflow, dbt, Snowflake, and Kafka metadata on a schedule, and exposes a GraphQL API that the platform UI embeds for search.",
    ),
    # 36 — privacy: retention automation
    (
        "Adopted a central retention service for the lake after legal teams rejected per-dataset manual purging policies.",
        "The retention service reads dataset policies from a YAML registry, issues Iceberg delete queries per partition age, and writes audit rows into a compliance bucket.",
    ),
    # 37 — archival: warehouse snapshots -> parquet exports
    (
        "Replaced Snowflake time-travel as the long-term archival story with scheduled Parquet exports to keep compliance snapshots vendor-neutral.",
        "A weekly Dagster job exports Snowflake tables as Parquet into a versioned S3 bucket, registers them as Iceberg metadata, and tags the run with a GDPR scope.",
    ),
    # 38 — ingestion: HTTP push -> Segment
    (
        "Replaced the home-grown HTTP event collector with Segment once mobile SDK work threatened to overflow the product engineering roadmap.",
        "Segment sources land client events into Snowflake via a managed warehouse destination, with PII filters applied via protocols before warehouse delivery.",
    ),
    # 39 — stream processing: Spark streaming -> Beam
    (
        "Picked Apache Beam over Spark Streaming for the cross-runner pipelines so the same code could run on Dataflow and Flink.",
        "Beam pipelines run on Google Dataflow in production and Flink locally, with side inputs backed by a BigQuery reference table refreshed hourly.",
    ),
    # 40 — batch ETL: Pandas -> Polars
    (
        "Rewrote the heavy transformation scripts from Pandas to Polars after memory spikes crashed the ECS tasks on month-end runs.",
        "Polars jobs stream Parquet batches from S3, group aggregations in a lazy plan, and write results back as partitioned Parquet for downstream dbt models.",
    ),
    # 41 — warehouse: MySQL reporting replica -> ClickHouse
    (
        "Moved reporting workloads off a MySQL read replica onto ClickHouse once dashboard queries started timing out at p95.",
        "ClickHouse runs a sharded cluster behind a chproxy layer, ingests events via Kafka engine tables, and serves BI tools through materialised view projections.",
    ),
    # 42 — orchestrator: Luigi -> Airflow 2
    (
        "Retired the remaining Luigi DAGs for Airflow 2 once dependency resolution and dynamic task mapping became platform-wide requirements.",
        "Airflow 2 runs on CeleryExecutor with Redis, DAGs live in a git-sync sidecar, and the scheduler uses a highly available Postgres metadata database.",
    ),
    # 43 — reverse ETL: Zapier glue -> Workato
    (
        "Swapped the Zapier glue for Workato after ops workflows started needing multi-step error handling and audit logs.",
        "Workato recipes pull curated marts from Snowflake, fan out to Salesforce, NetSuite, and Slack, and log every step into a central recipe audit table.",
    ),
    # 44 — CDC: Airbyte -> Debezium
    (
        "Replaced the Airbyte Postgres source with Debezium once batch-based CDC could no longer meet the 30-second freshness SLA.",
        "Debezium runs on a Kafka Connect cluster, publishes row-level changes to Kafka, and a Spark Structured Streaming job applies them to Delta tables.",
    ),
    # 45 — schema registry: static shared types -> Buf
    (
        "Adopted Buf Schema Registry for Protobuf sharing after manual vendored copies drifted across five repos in one quarter.",
        "Buf hosts the canonical Protobuf modules, CI checks enforce breaking-change policies, and code generation fans out into Go, Python, and TypeScript clients.",
    ),
    # 46 — pipeline observability: Datadog only -> Grafana + Loki
    (
        "Moved the data platform's pipeline logs from Datadog to a dedicated Grafana Loki stack because indexed log cost outgrew the per-month budget.",
        "Promtail ships pipeline logs to Loki, Grafana dashboards correlate with Prometheus pipeline metrics, and alerts route through a Grafana OnCall schedule.",
    ),
    # 47 — data quality: no tests -> dbt tests
    (
        "Committed to dbt tests as the minimum bar for every new mart after a silent dimension break caused a reporting-day incident.",
        "Every dbt model carries not-null and unique tests on its primary key, plus referential tests on foreign keys, gated by a CI check on pull requests.",
    ),
    # 48 — lineage: Atlas -> Marquez
    (
        "Replaced Apache Atlas with Marquez for lineage once the Hadoop-centric data model stopped matching our warehouse-first pipelines.",
        "Marquez stores OpenLineage events in Postgres, exposes a REST API for consumers, and a custom UI overlay surfaces column-level lineage for dbt models.",
    ),
    # 49 — privacy / DSR automation
    (
        "Built a dedicated subject-request service so that GDPR deletions stopped going through ad-hoc SQL scripts touching every warehouse table.",
        "The subject-request service reads a data map from a catalog, issues tombstone rows into Iceberg tables, and records per-request proofs in a tamper-evident log.",
    ),
    # 50 — archival / lakehouse migration
    (
        "Chose a lakehouse-only archival strategy over cross-region warehouse replicas to avoid doubling the Snowflake storage spend.",
        "Cold partitions live as Iceberg tables on S3 Glacier Instant Retrieval, a Unity Catalog external location governs access, and Databricks SQL reads them on demand.",
    ),
]


def emit() -> int:
    assert len(PAIRS) == 50, f"expected 50 pairs, got {len(PAIRS)}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for p, (decision_text, arch_text) in enumerate(PAIRS, start=1):
            pair_id = f"cls-pair-{PAIR_OFFSET + p:05d}"
            # decision row
            row_a = {
                "id": f"class-{ID_OFFSET + (2 * p - 1):05d}",
                "domain": "technical",
                "text": decision_text,
                "memory_type": "decision",
                "pair_id": pair_id,
            }
            # architecture row
            row_b = {
                "id": f"class-{ID_OFFSET + (2 * p):05d}",
                "domain": "technical",
                "text": arch_text,
                "memory_type": "architecture",
                "pair_id": pair_id,
            }
            f.write(json.dumps(row_a, ensure_ascii=False) + "\n")
            f.write(json.dumps(row_b, ensure_ascii=False) + "\n")
            written += 2
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
