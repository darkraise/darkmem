"""One-off emitter for shared-base batch-158 — technical domain (ETL/ELT tooling: dbt, Airbyte, Fivetran, Meltano, Singer, Matillion, ADF, AWS Glue, dlthub, reverse ETL, CDC, data contracts).

Writes 50 rows to data/v2/shared/batch_158.tmp.jsonl with ids shared-07851..07900.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_158.tmp.jsonl"
ID_OFFSET = 7850

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Swapped the bespoke Python extract scripts for Airbyte connectors on the Postgres and Stripe sources; the self-managed OSS deployment handles schema discovery and backfills without custom code.", "decision", "technical", False,
     [("Airbyte", "tool"), ("Postgres", "database"), ("Stripe", "service"), ("Python", "language")],
     [("Airbyte", "Python", "REPLACES"), ("Airbyte", "Postgres", "COMMUNICATES_WITH"), ("Airbyte", "Stripe", "COMMUNICATES_WITH")],
     "which ingestion tool replaced the bespoke Python scripts for Postgres and Stripe pulls",
     "airbyte connector postgres stripe ingest replace python script"),
    # --- 2 ---
    ("dbt Core runs the warehouse transformations against Snowflake; the Cloud tier was dropped after budget review because GitHub Actions with dbt-core and an OIDC role covers scheduling for a fraction of the cost.", "decision", "technical", False,
     [("dbt Core", "tool"), ("Snowflake", "database"), ("GitHub Actions", "service"), ("OIDC", "protocol")],
     [("dbt Core", "Snowflake", "APPLIES_TO"), ("GitHub Actions", "dbt Core", "USES")],
     "why did the team drop dbt Cloud in favour of dbt Core on GitHub Actions",
     "dbt core cloud snowflake github actions oidc schedule budget"),
    # --- 3 ---
    ("Incremental models in dbt use the merge strategy on BigQuery keyed by event_id with a 3-day lookback; the old full-refresh pattern was rebuilding a 900M-row fact table every night.", "architecture", "technical", False,
     [("dbt", "tool"), ("BigQuery", "database"), ("merge", "method"), ("event_id", "concept")],
     [("dbt", "BigQuery", "APPLIES_TO"), ("dbt", "merge", "USES")],
     "which incremental strategy and key does the dbt fact model use on BigQuery to avoid full refresh",
     "dbt incremental merge bigquery event id lookback full refresh fact"),
    # --- 4 ---
    ("Fivetran handles the Salesforce and NetSuite extracts on a 15-minute sync cadence; the MAR-based pricing for those two sources is lower than self-hosting Airbyte for a team of two engineers.", "decision", "technical", False,
     [("Fivetran", "tool"), ("Salesforce", "service"), ("NetSuite", "service"), ("Airbyte", "tool")],
     [("Fivetran", "Salesforce", "COMMUNICATES_WITH"), ("Fivetran", "NetSuite", "COMMUNICATES_WITH"), ("Fivetran", "Airbyte", "PREFERS")],
     "why did Fivetran win over Airbyte for the Salesforce and NetSuite pipelines",
     "fivetran salesforce netsuite airbyte mar pricing sync cadence"),
    # --- 5 ---
    ("Meltano orchestrates the Singer taps in the analytics repo; tap-shopify streams orders into target-snowflake and the whole flow is declared in meltano.yml so CI can spin up an isolated run per PR.", "architecture", "technical", False,
     [("Meltano", "tool"), ("tap-shopify", "tool"), ("target-snowflake", "tool"), ("meltano.yml", "config"), ("Singer", "protocol")],
     [("Meltano", "Singer", "USES"), ("tap-shopify", "target-snowflake", "COMMUNICATES_WITH"), ("Meltano", "meltano.yml", "CONFIGURES")],
     "how does Meltano wire the Shopify tap to Snowflake with per-PR isolated runs",
     "meltano singer tap shopify target snowflake yaml ci pr isolate"),
    # --- 6 ---
    ("Snapshots in dbt track slowly-changing dimensions on the customers table with the timestamp strategy on updated_at; downstream marts join against the valid_from and valid_to columns for point-in-time correctness.", "architecture", "technical", False,
     [("dbt", "tool"), ("Snapshots", "pattern"), ("customers", "database"), ("updated_at", "field"), ("valid_from", "field"), ("valid_to", "field")],
     [("dbt", "Snapshots", "USES"), ("Snapshots", "customers", "APPLIES_TO")],
     "which dbt mechanism tracks SCD history on the customers table and which fields bound validity",
     "dbt snapshot scd timestamp updated customers valid from to mart"),
    # --- 7 ---
    ("Shipped the reverse-ETL layer on Hightouch; it syncs the marts.active_users model to HubSpot and Intercom on a 30-minute schedule and the diff-based sync keeps API call volume under the contract ceiling.", "milestone", "technical", False,
     [("Hightouch", "tool"), ("marts.active_users", "database"), ("HubSpot", "service"), ("Intercom", "service")],
     [("Hightouch", "HubSpot", "COMMUNICATES_WITH"), ("Hightouch", "Intercom", "COMMUNICATES_WITH"), ("Hightouch", "marts.active_users", "USES")],
     "which reverse-ETL product sends the active_users mart to HubSpot and Intercom on a half-hour cadence",
     "hightouch reverse etl active users hubspot intercom diff sync"),
    # --- 8 ---
    ("CDC from the production Postgres feeds into Snowflake through Debezium writing to Kafka, then a Kafka Connect Snowflake sink lands the raw change stream into a _raw schema for dbt to flatten.", "architecture", "technical", False,
     [("Debezium", "tool"), ("Postgres", "database"), ("Kafka", "platform"), ("Snowflake", "database"), ("Kafka Connect", "tool"), ("dbt", "tool")],
     [("Debezium", "Postgres", "COMMUNICATES_WITH"), ("Debezium", "Kafka", "PRODUCES"), ("Kafka Connect", "Snowflake", "COMMUNICATES_WITH")],
     "how does the CDC pipeline move Postgres changes through Kafka into Snowflake for dbt processing",
     "debezium kafka connect postgres snowflake cdc raw schema dbt"),
    # --- 9 ---
    ("Schema drift on the Stripe source now auto-propagates: Airbyte's incremental schema refresh adds new columns to the raw table and a dbt pre-hook nulls them in staging until a human reviews the change.", "architecture", "technical", False,
     [("Stripe", "service"), ("Airbyte", "tool"), ("dbt", "tool"), ("pre-hook", "pattern")],
     [("Airbyte", "Stripe", "COMMUNICATES_WITH"), ("dbt", "pre-hook", "USES")],
     "how does the pipeline handle new columns appearing in the Stripe source between ingest and staging",
     "airbyte stripe schema drift column dbt pre hook staging review"),
    # --- 10 noise ---
    ("The office plant watering rota sits on a sticky note by the coffee machine and nobody has admitted to killing the fiddle-leaf fig.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Stitch was retired last quarter; the vendor-locked connectors were cheaper to replace with self-hosted Airbyte than to renew at the new tier pricing after the Talend acquisition shook out.", "milestone", "technical", False,
     [("Stitch", "tool"), ("Airbyte", "tool"), ("Talend", "organization")],
     [("Airbyte", "Stitch", "REPLACES")],
     "which vendor did Airbyte replace after the Talend acquisition changed the pricing tiers",
     "stitch airbyte talend retire vendor lock pricing tier replace"),
    # --- 12 ---
    ("Freshness SLA on orders_raw is 15 minutes; dbt source freshness checks emit a warning at 20 minutes and fail the run at 60, pinging the data-platform on-call through PagerDuty.", "architecture", "technical", False,
     [("orders_raw", "database"), ("dbt", "tool"), ("PagerDuty", "service"), ("source freshness", "pattern")],
     [("dbt", "source freshness", "USES"), ("dbt", "PagerDuty", "COMMUNICATES_WITH")],
     "what freshness thresholds and alerting path does the orders_raw table use in dbt",
     "freshness sla orders raw dbt source pagerduty warn fail threshold"),
    # --- 13 ---
    ("Exposures in dbt declare the downstream Looker dashboards that read from marts.revenue; a model delete triggers a dbt-project-evaluator warning that the Finance dashboard would break on the next run.", "fact", "technical", False,
     [("Exposures", "pattern"), ("dbt", "tool"), ("Looker", "service"), ("marts.revenue", "database"), ("dbt-project-evaluator", "tool")],
     [("dbt", "Exposures", "USES"), ("Exposures", "Looker", "APPLIES_TO")],
     "which dbt feature wires downstream Looker dashboards into the lineage graph to catch breakages",
     "dbt exposure looker marts revenue finance dashboard lineage break"),
    # --- 14 ---
    ("Data contracts are enforced on the public.orders model: column types, not-null constraints, and unique keys are in the YAML, and dbt fails the build if the SELECT drifts from the declared schema.", "architecture", "technical", False,
     [("Data contracts", "pattern"), ("public.orders", "database"), ("dbt", "tool"), ("YAML", "technology")],
     [("dbt", "Data contracts", "IMPLEMENTS"), ("Data contracts", "public.orders", "APPLIES_TO")],
     "how does dbt enforce column types and uniqueness on the public.orders model at build time",
     "data contract public orders dbt yaml column type unique null"),
    # --- 15 ---
    ("Matillion was evaluated for the Snowflake stack and rejected; the ELT-in-the-GUI model fought with our GitOps workflow and version-controlling job exports turned into a merge-conflict generator.", "decision", "technical", False,
     [("Matillion", "tool"), ("Snowflake", "database"), ("GitOps", "pattern")],
     [("Matillion", "Snowflake", "APPLIES_TO")],
     "why was Matillion rejected for the Snowflake ELT workload and what process friction drove it",
     "matillion snowflake elt gui gitops version control merge conflict"),
    # --- 16 ---
    ("Azure Data Factory orchestrates the daily SAP extract into ADLS Gen2; a Mapping Data Flow does the pivot and a copy activity lands the Parquet into the bronze zone of the lakehouse.", "architecture", "technical", False,
     [("Azure Data Factory", "service"), ("SAP", "service"), ("ADLS Gen2", "service"), ("Mapping Data Flow", "tool"), ("Parquet", "technology")],
     [("Azure Data Factory", "SAP", "COMMUNICATES_WITH"), ("Azure Data Factory", "ADLS Gen2", "PRODUCES"), ("Mapping Data Flow", "Parquet", "PRODUCES")],
     "how does Azure Data Factory move the daily SAP extract into the lakehouse bronze zone",
     "adf azure data factory sap adls parquet mapping flow bronze"),
    # --- 17 ---
    ("AWS Glue crawlers populate the Glue Data Catalog for the S3 landing bucket; a Glue Job written in PySpark normalises partition layout and writes Iceberg tables for Athena to query.", "architecture", "technical", False,
     [("AWS Glue", "service"), ("Glue Data Catalog", "service"), ("S3", "service"), ("PySpark", "framework"), ("Iceberg", "technology"), ("Athena", "service")],
     [("AWS Glue", "S3", "COMMUNICATES_WITH"), ("AWS Glue", "Glue Data Catalog", "PRODUCES"), ("AWS Glue", "Iceberg", "PRODUCES"), ("Athena", "Iceberg", "USES")],
     "how do AWS Glue crawlers and Glue Jobs feed the Iceberg tables Athena reads",
     "aws glue crawler catalog s3 pyspark iceberg athena partition"),
    # --- 18 ---
    ("dlthub powers the one-off Notion export pipeline; the @dlt.resource decorator handles pagination and the built-in schema inference lands a flat Parquet file into DuckDB for ad-hoc analysis.", "fact", "technical", False,
     [("dlthub", "library"), ("Notion", "service"), ("DuckDB", "database"), ("Parquet", "technology"), ("@dlt.resource", "api")],
     [("dlthub", "Notion", "COMMUNICATES_WITH"), ("dlthub", "DuckDB", "PRODUCES"), ("dlthub", "@dlt.resource", "USES")],
     "which SDK-based pipeline lands Notion data into DuckDB with automatic schema inference",
     "dlthub notion duckdb parquet resource decorator pagination infer"),
    # --- 19 ---
    ("Informatica PowerCenter still runs the legacy mainframe feeds into the Teradata enterprise warehouse; the IICS upgrade is on the FY27 roadmap but nobody is touching the COBOL copybook parsers until then.", "fact", "technical", False,
     [("Informatica PowerCenter", "tool"), ("Teradata", "database"), ("IICS", "service"), ("COBOL", "language")],
     [("Informatica PowerCenter", "Teradata", "COMMUNICATES_WITH")],
     "which legacy ETL tool still feeds the Teradata warehouse from the mainframe",
     "informatica powercenter teradata mainframe cobol iics upgrade legacy"),
    # --- 20 ---
    ("Singer taps wrap APIs that Airbyte doesn't support; we author small tap-<vendor> packages in Python and run them under Meltano rather than maintaining bespoke cron jobs in the old monorepo.", "decision", "technical", False,
     [("Singer", "protocol"), ("Airbyte", "tool"), ("Meltano", "tool"), ("Python", "language")],
     [("Meltano", "Singer", "USES"), ("Singer", "Airbyte", "SUPPORTS")],
     "how does the team cover vendors Airbyte lacks without resurrecting the cron monorepo",
     "singer tap airbyte meltano vendor python wrap api custom"),
    # --- 21 ---
    ("JSON flattening of the Intercom payload used to blow up in BigQuery; switched to dbt's dbt_utils.unpivot with a declared column list so new nested keys don't auto-widen the staging table.", "problem", "technical", False,
     [("Intercom", "service"), ("BigQuery", "database"), ("dbt_utils.unpivot", "method"), ("dbt", "tool")],
     [("dbt", "dbt_utils.unpivot", "USES"), ("dbt_utils.unpivot", "Intercom", "APPLIES_TO")],
     "which dbt macro fixed the BigQuery blow-up from Intercom JSON payloads widening unexpectedly",
     "intercom json flatten bigquery dbt utils unpivot nested widen stage"),
    # --- 22 ---
    ("Census handles the reverse-ETL sync into Marketo; the audit log ships to Datadog and the SOC2 reviewer signed off on it because the destination-level OAuth scopes match the least-privilege policy.", "decision", "technical", False,
     [("Census", "tool"), ("Marketo", "service"), ("Datadog", "service"), ("OAuth", "protocol"), ("SOC2", "concept")],
     [("Census", "Marketo", "COMMUNICATES_WITH"), ("Census", "Datadog", "COMMUNICATES_WITH"), ("Census", "OAuth", "USES")],
     "which reverse-ETL product sends data to Marketo and how was SOC2 compliance satisfied",
     "census marketo reverse etl datadog soc2 oauth scope least privilege"),
    # --- 23 ---
    ("Grouparoo was dropped from the shortlist once Airbyte acquired it; the project stopped getting releases and the migration guide pointed at Hightouch, which we were already piloting.", "fact", "technical", False,
     [("Grouparoo", "tool"), ("Airbyte", "tool"), ("Hightouch", "tool")],
     [("Airbyte", "Grouparoo", "REPLACES"), ("Hightouch", "Grouparoo", "REPLACES")],
     "what happened to Grouparoo after the Airbyte acquisition and where did the migration go",
     "grouparoo airbyte hightouch acquisition migration dead project sunset"),
    # --- 24 ---
    ("Hevo was piloted for two weeks and cut because the transformation layer only exposes Python snippets rather than proper version control; dbt was already doing the heavy transforms anyway.", "decision", "technical", False,
     [("Hevo", "tool"), ("Python", "language"), ("dbt", "tool")],
     [("dbt", "Hevo", "PREFERS")],
     "why did the Hevo pilot fail and which tool kept ownership of the transform layer",
     "hevo pilot cut python snippet version control dbt transform"),
    # --- 25 ---
    ("Talend Open Studio jobs were rewritten into dbt models during the 2026 migration; the graphical job metadata is archived in the legacy repo for audit but the runtime was decommissioned in Q1.", "milestone", "technical", False,
     [("Talend Open Studio", "tool"), ("dbt", "tool")],
     [("dbt", "Talend Open Studio", "REPLACES")],
     "which tool replaced Talend Open Studio during the 2026 migration and what did we keep for audit",
     "talend open studio dbt rewrite 2026 migration decommission audit"),
    # --- 26 ---
    ("Airbyte's normalization step was disabled for the raw_stripe connection; dbt handles the unnesting explicitly because the auto-generated SQL produced brittle downstream names like _airbyte_ab_id.", "problem", "technical", False,
     [("Airbyte", "tool"), ("raw_stripe", "database"), ("dbt", "tool"), ("_airbyte_ab_id", "field")],
     [("dbt", "Airbyte", "REPLACES")],
     "why is Airbyte's built-in normalization disabled on the raw_stripe connection",
     "airbyte normalization disable raw stripe dbt unnest name brittle"),
    # --- 27 ---
    ("The dbt seeds directory holds the reference tables for country_codes and currency_codes; the CI check forbids adding seeds over 5 MB to keep the repo clone time reasonable.", "preference", "technical", False,
     [("dbt", "tool"), ("country_codes", "database"), ("currency_codes", "database"), ("CI", "service")],
     [("dbt", "country_codes", "USES"), ("dbt", "currency_codes", "USES")],
     "which reference tables live in dbt seeds and what CI constraint prevents bloat",
     "dbt seed country currency code reference ci clone size limit"),
    # --- 28 ---
    ("Prefer dlthub over a custom requests-based loader for any new ad-hoc extract; the state management and incremental cursor save us from hand-rolling pagination and resume logic every single time.", "preference", "technical", False,
     [("dlthub", "library"), ("requests", "library")],
     [("dlthub", "requests", "PREFERS")],
     "why does the team reach for dlthub rather than a raw requests loader on ad-hoc extracts",
     "dlthub requests loader ad hoc extract state cursor pagination resume"),
    # --- 29 ---
    ("Slowly-changing dimension type 2 is the default for every dimension table in the finance mart; type 1 overwrites only happen on reference tables where history has no analytical value.", "preference", "technical", False,
     [("Slowly-changing dimension", "concept"), ("type 2", "pattern"), ("type 1", "pattern"), ("finance mart", "database")],
     [("finance mart", "type 2", "USES")],
     "which SCD variant is the default for finance dimension tables and when is type 1 acceptable",
     "slowly changing dimension type 2 1 finance mart default reference"),
    # --- 30 ---
    ("Fivetran's History Mode was enabled on the NetSuite vendors table specifically; the audit team needed every row version and the 4x storage cost was cheaper than building SCD type 2 by hand in dbt.", "decision", "technical", False,
     [("Fivetran", "tool"), ("History Mode", "pattern"), ("NetSuite", "service"), ("dbt", "tool")],
     [("Fivetran", "History Mode", "USES"), ("Fivetran", "NetSuite", "COMMUNICATES_WITH")],
     "why was Fivetran History Mode picked for NetSuite vendors over hand-rolled SCD in dbt",
     "fivetran history mode netsuite vendor audit scd type 2 dbt"),
    # --- 31 ---
    ("The Debezium connector kept pausing after a Postgres WAL restart; tuning heartbeat.interval.ms and publication.autocreate.mode to disabled stopped the replication slot from bloating and the sync caught back up.", "problem", "technical", False,
     [("Debezium", "tool"), ("Postgres", "database"), ("WAL", "concept"), ("heartbeat.interval.ms", "config"), ("publication.autocreate.mode", "config")],
     [("Debezium", "Postgres", "COMMUNICATES_WITH"), ("Debezium", "heartbeat.interval.ms", "CONFIGURES")],
     "which Debezium settings fixed the WAL-restart pause and replication slot bloat on the Postgres source",
     "debezium postgres wal heartbeat publication autocreate slot bloat"),
    # --- 32 ---
    ("dbt Cloud was kept for one team only; the Analytics group uses the IDE and job scheduler because their analysts aren't comfortable with CLI workflows, while the platform team stays on dbt Core in CI.", "decision", "technical", False,
     [("dbt Cloud", "service"), ("dbt Core", "tool"), ("CLI", "pattern")],
     [("dbt Cloud", "dbt Core", "RELATED_TO")],
     "how is dbt Cloud usage split between the Analytics and platform teams",
     "dbt cloud core analytics platform ide cli scheduler split team"),
    # --- 33 ---
    ("Airbyte Cloud was considered and rejected; the self-hosted deployment on EKS with the low-code connector builder lets us fork connectors internally without waiting on vendor release cycles.", "decision", "technical", False,
     [("Airbyte Cloud", "service"), ("EKS", "platform"), ("low-code connector builder", "tool")],
     [("Airbyte Cloud", "EKS", "RELATED_TO")],
     "why did self-hosted Airbyte on EKS win over Airbyte Cloud for the connector workflow",
     "airbyte cloud eks self host low code connector fork vendor"),
    # --- 34 ---
    ("The fact_orders incremental model uses the insert_overwrite strategy on Databricks because merge performance on a 2-billion-row Delta table was bottlenecked on the file-level stats compaction.", "architecture", "technical", False,
     [("fact_orders", "database"), ("insert_overwrite", "method"), ("Databricks", "service"), ("Delta", "technology"), ("merge", "method")],
     [("fact_orders", "insert_overwrite", "USES"), ("insert_overwrite", "merge", "REPLACES")],
     "which dbt incremental strategy does fact_orders use on Databricks and why not merge",
     "fact orders insert overwrite databricks delta merge stats compaction"),
    # --- 35 ---
    ("Shipped the v2 data contract rollout in March 2026: every public-marts model now has enforced column types and a dbt-checkpoint pre-commit blocks PRs that break the contract.", "milestone", "technical", False,
     [("data contract", "pattern"), ("public-marts", "database"), ("dbt-checkpoint", "tool"), ("March 2026", "date")],
     [("dbt-checkpoint", "data contract", "IMPLEMENTS"), ("data contract", "public-marts", "APPLIES_TO")],
     "when did the v2 data contract rollout ship and which pre-commit tool guards it",
     "data contract v2 march 2026 public marts dbt checkpoint pre commit"),
    # --- 36 ---
    ("The dbt docs site is regenerated nightly and hosted on Cloudflare Pages; lineage diffs between main and the PR branch render through dbt-project-evaluator in the GitHub PR preview.", "architecture", "technical", False,
     [("dbt docs", "service"), ("Cloudflare Pages", "service"), ("dbt-project-evaluator", "tool"), ("GitHub", "service")],
     [("dbt docs", "Cloudflare Pages", "DEPLOYED_ON"), ("dbt-project-evaluator", "GitHub", "COMMUNICATES_WITH")],
     "where do the dbt docs live and how do lineage diffs appear on pull requests",
     "dbt docs cloudflare pages lineage diff evaluator github pr preview"),
    # --- 37 ---
    ("Reached the 1000-model mark in the dbt project on April 3 2026; the selector tags for mart, staging, and intermediate keep the `dbt build --select tag:daily` run under the 45-minute SLA.", "milestone", "technical", False,
     [("dbt", "tool"), ("April 3 2026", "date"), ("staging", "pattern"), ("intermediate", "pattern"), ("mart", "pattern")],
     [("dbt", "mart", "USES"), ("dbt", "staging", "USES")],
     "when did the dbt project hit 1000 models and how is the daily build kept under its SLA",
     "dbt 1000 model april 2026 tag mart staging intermediate daily sla"),
    # --- 38 ---
    ("Kafka Connect JDBC source was tried on the MySQL replica but dropped; the lack of proper DDL capture meant a column rename silently dropped rows, and Debezium's logical replication caught every change.", "problem", "technical", False,
     [("Kafka Connect", "tool"), ("JDBC", "protocol"), ("MySQL", "database"), ("Debezium", "tool"), ("DDL", "concept")],
     [("Debezium", "Kafka Connect", "REPLACES"), ("Kafka Connect", "MySQL", "COMMUNICATES_WITH")],
     "why did the Kafka Connect JDBC source lose to Debezium on the MySQL replica",
     "kafka connect jdbc mysql debezium ddl column rename drop row"),
    # --- 39 ---
    ("Airflow triggers the dbt build via the DbtTaskGroup from the cosmos provider; the per-model task mapping gives actually-useful retries instead of the old monolithic BashOperator that lost state on failure.", "architecture", "technical", False,
     [("Airflow", "framework"), ("DbtTaskGroup", "api"), ("cosmos", "library"), ("BashOperator", "api"), ("dbt", "tool")],
     [("Airflow", "dbt", "USES"), ("DbtTaskGroup", "BashOperator", "REPLACES"), ("Airflow", "cosmos", "USES")],
     "how does Airflow orchestrate dbt now and what did the cosmos provider improve over BashOperator",
     "airflow cosmos dbt task group bash operator retry state failure"),
    # --- 40 ---
    ("Prefer thin staging models that only rename and cast; business logic belongs in intermediate or mart layers so downstream debugging doesn't have to untangle a CTE with fifteen joins and three window functions.", "preference", "technical", False,
     [("staging", "pattern"), ("intermediate", "pattern"), ("mart", "pattern"), ("CTE", "concept")],
     [("staging", "mart", "RELATED_TO")],
     "what layering rule governs where business logic lives across staging, intermediate, and mart models",
     "staging intermediate mart business logic cte rename cast thin"),
    # --- 41 ---
    ("The raw layer in Snowflake is read-only to everyone except the Airbyte service role; schemas follow the pattern raw_<source> and the dbt project only reads from them, never writes back.", "architecture", "technical", False,
     [("Snowflake", "database"), ("Airbyte", "tool"), ("dbt", "tool"), ("raw_<source>", "pattern")],
     [("Airbyte", "Snowflake", "COMMUNICATES_WITH"), ("dbt", "Snowflake", "COMMUNICATES_WITH")],
     "how is write access to the raw Snowflake layer restricted between Airbyte and dbt",
     "snowflake raw layer airbyte service role dbt read only schema"),
    # --- 42 ---
    ("Broken Fivetran historical resync on the Zendesk connector after a 7-day outage; support advised resetting the connector, but we instead ran a Singer tap-zendesk backfill through Meltano to avoid the 14-day replay window.", "problem", "technical", False,
     [("Fivetran", "tool"), ("Zendesk", "service"), ("tap-zendesk", "tool"), ("Meltano", "tool"), ("Singer", "protocol")],
     [("tap-zendesk", "Fivetran", "REPLACES"), ("Meltano", "tap-zendesk", "USES")],
     "how did the team backfill Zendesk after Fivetran's historical resync broke post-outage",
     "fivetran zendesk resync outage meltano singer tap backfill replay"),
    # --- 43 noise ---
    ("A stray seagull has been stealing chips from the rooftop terrace three days running and security camera footage is now a running joke in Slack.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Reference model: staging layer materialisations default to view, intermediate to ephemeral, and mart to table; overrides happen only when profiling shows the default is too slow on production data.", "reference", "technical", False,
     [("staging", "pattern"), ("intermediate", "pattern"), ("mart", "pattern"), ("view", "concept"), ("ephemeral", "concept"), ("table", "concept")],
     [("staging", "view", "USES"), ("intermediate", "ephemeral", "USES"), ("mart", "table", "USES")],
     "what materialisation defaults does each dbt layer use and when do overrides apply",
     "staging view intermediate ephemeral mart table materialisation default"),
    # --- 45 ---
    ("Reference list of dbt tests shipping on every source: source_freshness, not_null on primary keys, unique on natural keys, accepted_values for enum columns, and relationships tests for FK integrity.", "reference", "technical", False,
     [("dbt", "tool"), ("source_freshness", "method"), ("not_null", "method"), ("unique", "method"), ("accepted_values", "method"), ("relationships", "method")],
     [("dbt", "source_freshness", "USES"), ("dbt", "not_null", "USES"), ("dbt", "unique", "USES")],
     "which dbt tests are mandatory on every source and what does each one check",
     "dbt test source freshness not null unique accepted values relationships"),
    # --- 46 ---
    ("Connector reference: Airbyte handles Postgres, MySQL, Stripe, GitHub, and Zendesk; Fivetran owns Salesforce, NetSuite, and HubSpot; Meltano runs the bespoke Singer taps for the niche vendors.", "reference", "technical", False,
     [("Airbyte", "tool"), ("Fivetran", "tool"), ("Meltano", "tool"), ("Salesforce", "service"), ("NetSuite", "service"), ("HubSpot", "service"), ("Postgres", "database"), ("MySQL", "database")],
     [("Airbyte", "Postgres", "COMMUNICATES_WITH"), ("Airbyte", "MySQL", "COMMUNICATES_WITH"), ("Fivetran", "Salesforce", "COMMUNICATES_WITH"), ("Fivetran", "NetSuite", "COMMUNICATES_WITH"), ("Fivetran", "HubSpot", "COMMUNICATES_WITH")],
     "which sources belong to Airbyte, Fivetran, and Meltano in the current connector catalogue",
     "airbyte fivetran meltano postgres mysql salesforce netsuite catalogue"),
    # --- 47 ---
    ("Reverse-ETL destinations reference: Hightouch syncs to HubSpot and Intercom; Census pushes to Marketo and Zendesk; both read from the marts.customer_360 model as the single source of truth.", "reference", "technical", False,
     [("Hightouch", "tool"), ("Census", "tool"), ("HubSpot", "service"), ("Intercom", "service"), ("Marketo", "service"), ("Zendesk", "service"), ("marts.customer_360", "database")],
     [("Hightouch", "HubSpot", "COMMUNICATES_WITH"), ("Hightouch", "Intercom", "COMMUNICATES_WITH"), ("Census", "Marketo", "COMMUNICATES_WITH"), ("Census", "Zendesk", "COMMUNICATES_WITH"), ("Hightouch", "marts.customer_360", "USES"), ("Census", "marts.customer_360", "USES")],
     "which reverse-ETL tools send which downstream destinations and what model do they share as source",
     "hightouch census hubspot intercom marketo zendesk customer 360 reverse"),
    # --- 48 ---
    ("Reference: the freshness ladder is 5 minutes for CDC sources, 15 minutes for API pulls, 1 hour for batch exports, and 24 hours for the vendor CSV drop that still arrives over SFTP from one partner.", "reference", "technical", False,
     [("CDC", "pattern"), ("API", "concept"), ("SFTP", "protocol"), ("CSV", "technology")],
     [("CDC", "SFTP", "RELATED_TO")],
     "what freshness tiers does the pipeline enforce across CDC, API, batch, and SFTP sources",
     "freshness ladder cdc api batch sftp csv 5 15 minute hour"),
    # --- 49 ---
    ("Reference on Singer spec compliance: tap-<name> emits RECORD, SCHEMA, STATE messages on stdout, and target-<name> consumes them on stdin; the state file persists the replication cursor between runs.", "reference", "technical", False,
     [("Singer", "protocol"), ("RECORD", "concept"), ("SCHEMA", "concept"), ("STATE", "concept"), ("tap-<name>", "pattern"), ("target-<name>", "pattern")],
     [("tap-<name>", "Singer", "IMPLEMENTS"), ("target-<name>", "Singer", "IMPLEMENTS")],
     "how do Singer taps and targets communicate and what persists the replication cursor across runs",
     "singer tap target record schema state stdin stdout cursor persist"),
    # --- 50 ---
    ("Prefer landing raw extracts as Parquet in object storage rather than straight into the warehouse; replay and reprocessing are cheap, and multiple engines like Athena and Snowflake can read the same files.", "preference", "technical", False,
     [("Parquet", "technology"), ("Athena", "service"), ("Snowflake", "database"), ("object storage", "infrastructure")],
     [("Athena", "Parquet", "USES"), ("Snowflake", "Parquet", "USES")],
     "why land raw extracts as Parquet in object storage rather than directly into the warehouse",
     "parquet object storage athena snowflake raw replay reprocess engine"),
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
