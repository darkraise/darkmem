"""One-off emitter for shared-base batch-128 — technical domain (analytics and BI infrastructure).

Writes 50 rows to data/v2/shared/batch_128.tmp.jsonl with ids shared-06351..06400.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_128.tmp.jsonl"
ID_OFFSET = 6350

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("dbt Core replaced the in-house ELT scripts on the marketing warehouse; Jinja macros collapsed 40 bespoke SQL files into a dozen reusable models.", "decision", "technical", False,
     [("dbt Core", "tool"), ("ELT scripts", "tool"), ("Jinja", "language"), ("SQL", "language")],
     [("dbt Core", "ELT scripts", "REPLACES")],
     "which transform tool took over from the hand-rolled ELT SQL scripts",
     "dbt core jinja macro consolidate bespoke warehouse transform"),
    # --- 2 ---
    ("SQLMesh improves on dbt for state-aware incremental runs; virtual environments and breaking-change detection cut rebuild cost on the 2 TB fact table.", "decision", "technical", False,
     [("SQLMesh", "tool"), ("dbt", "tool")],
     [("SQLMesh", "dbt", "IMPROVES_ON")],
     "which transform framework displaced dbt for state-aware incremental runs",
     "SQLMesh virtual environment breaking change incremental rebuild cost"),
    # --- 3 ---
    ("Fivetran pulled the Salesforce and Stripe feeds; the connector catalog and schema drift handling were worth the per-MAR pricing for the first year.", "architecture", "technical", False,
     [("Fivetran", "service"), ("Salesforce", "service"), ("Stripe", "service")],
     [],
     "which managed ELT vendor pulled the Salesforce and Stripe feeds initially",
     "fivetran connector schema drift per MAR pricing catalog"),
    # --- 4 ---
    ("Airbyte replaced Fivetran on the low-priority ad-platform sources; self-hosted OSS saved 18k per year once volume crossed the tier cliff.", "decision", "technical", False,
     [("Airbyte", "tool"), ("Fivetran", "service")],
     [("Airbyte", "Fivetran", "REPLACES")],
     "which OSS ELT took over ad-platform ingest from Fivetran on cost",
     "airbyte self hosted OSS volume tier cliff saving swap"),
    # --- 5 ---
    ("Stitch was retired on the legacy CRM feed after Talend pulled support timelines in; Airbyte absorbed the pipeline with a one-week rewrite.", "decision", "technical", False,
     [("Stitch", "tool"), ("Talend", "organization"), ("Airbyte", "tool")],
     [("Airbyte", "Stitch", "REPLACES")],
     "which ELT tool absorbed the legacy Stitch CRM pipeline",
     "stitch retire talend support timeline airbyte rewrite"),
    # --- 6 ---
    ("Meltano wrapped the Singer taps for the analytics platform; the meltano.yml config replaced a mess of cron-driven tap-to-target scripts.", "decision", "technical", False,
     [("Meltano", "tool"), ("Singer", "framework"), ("cron", "tool")],
     [("Meltano", "cron", "REPLACES")],
     "which orchestration layer tidied the Singer tap pipelines",
     "meltano singer yml tap target orchestration config replace"),
    # --- 7 ---
    ("Hightouch handled reverse ETL from Snowflake into HubSpot; the audience builder let growth ship sync definitions without a data engineer in the loop.", "architecture", "technical", False,
     [("Hightouch", "service"), ("Snowflake", "database"), ("HubSpot", "service")],
     [],
     "which reverse ETL platform pushed Snowflake audiences to HubSpot",
     "hightouch reverse ETL audience sync growth self serve"),
    # --- 8 ---
    ("Census replaced Hightouch on the reverse ETL leg; the Segment-style event-based sync fit the product analytics model better than row-based upserts.", "decision", "technical", False,
     [("Census", "service"), ("Hightouch", "service"), ("Segment", "service")],
     [("Census", "Hightouch", "REPLACES")],
     "which reverse ETL tool replaced Hightouch for event-style product syncs",
     "census reverse ETL event sync row upsert swap product"),
    # --- 9 ---
    ("Metabase served the internal dashboards; SQL question authoring was good enough for the analyst team without a semantic-layer tax.", "preference", "technical", False,
     [("Metabase", "tool"), ("SQL", "language")],
     [],
     "which BI tool covered the internal dashboards without semantic layer overhead",
     "metabase SQL question analyst self serve dashboard light"),
    # --- 10. noise ---
    ("Let me re-run the incremental model, snapshot lag looks off.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Apache Superset replaced a legacy Tableau deployment on the enterprise BI side; SQL Lab plus native charts covered 80 percent of the dashboards for a tenth of the license cost.", "decision", "technical", False,
     [("Apache Superset", "tool"), ("Tableau", "tool"), ("SQL Lab", "tool")],
     [("Apache Superset", "Tableau", "REPLACES")],
     "which open-source BI took over from legacy Tableau for enterprise dashboards",
     "superset tableau SQL lab license cost dashboard migration"),
    # --- 12 ---
    ("Looker held the governed semantic layer; LookML models owned the KPI definitions and downstream tools read from Looker's cached query results.", "architecture", "technical", False,
     [("Looker", "tool"), ("LookML", "language"), ("KPI", "concept")],
     [],
     "which BI tool owned the governed semantic KPI layer downstream",
     "looker LookML semantic layer governed KPI cache query"),
    # --- 13 ---
    ("Sigma Computing was preferred over Tableau for finance's spreadsheet-style exploration; the warehouse-native workbook model avoided the extract refresh tax.", "preference", "technical", False,
     [("Sigma Computing", "tool"), ("Tableau", "tool")],
     [("Sigma Computing", "Tableau", "PREFERS")],
     "which BI tool beat Tableau for finance's spreadsheet-style analysis",
     "sigma workbook warehouse native extract refresh finance"),
    # --- 14 ---
    ("Hex notebooks became the standard for ad-hoc analysis; Python plus SQL cells plus a shared warehouse connection killed three different ad-hoc tools.", "decision", "technical", False,
     [("Hex", "tool"), ("Python", "language"), ("SQL", "language")],
     [],
     "which notebook platform consolidated the ad-hoc analysis stack",
     "hex notebook Python SQL warehouse ad hoc consolidate tool"),
    # --- 15 ---
    ("Mode Analytics was dropped after the ThoughtSpot acquisition; Hex absorbed the analyst notebook workload and Lightdash picked up the governed charts.", "decision", "technical", False,
     [("Mode Analytics", "tool"), ("ThoughtSpot", "organization"), ("Hex", "tool"), ("Lightdash", "tool")],
     [("Hex", "Mode Analytics", "REPLACES"), ("Lightdash", "Mode Analytics", "REPLACES")],
     "which tools absorbed the Mode Analytics workload after the acquisition",
     "mode analytics thoughtspot acquire hex lightdash migration"),
    # --- 16 ---
    ("Lightdash exposed dbt metrics as the BI semantic layer; dbt YAML definitions became the single source of truth instead of duplicated LookML.", "architecture", "technical", False,
     [("Lightdash", "tool"), ("dbt", "tool"), ("LookML", "language"), ("YAML", "language")],
     [("Lightdash", "LookML", "REPLACES")],
     "which BI tool read dbt metric definitions as the single semantic source",
     "lightdash dbt metric YAML semantic truth LookML duplicate"),
    # --- 17 ---
    ("Evidence.dev generated the executive PDF reports from markdown plus SQL; the weekly board deck pipeline dropped from three hours to ten minutes.", "milestone", "technical", False,
     [("Evidence.dev", "tool"), ("SQL", "language")],
     [],
     "which code-first reporting tool shortened the weekly board deck pipeline",
     "evidence markdown SQL executive report board deck pipeline"),
    # --- 18 ---
    ("Preset hosted the managed Superset deployment for the ops team; self-host toil on Helm upgrades was not worth the 2k monthly saving.", "decision", "technical", False,
     [("Preset", "service"), ("Superset", "tool"), ("Helm", "tool")],
     [],
     "which managed Superset vendor took the self-host toil off ops",
     "preset managed superset helm upgrade ops saving hosting"),
    # --- 19 ---
    ("Omni was preferred over Looker for the new subsidiary rollout; the dual modeled-plus-ad-hoc layer fit analysts who resented strict LookML governance.", "preference", "technical", False,
     [("Omni", "tool"), ("Looker", "tool"), ("LookML", "language")],
     [("Omni", "Looker", "PREFERS")],
     "which BI tool displaced Looker for the subsidiary rollout and why",
     "omni looker modeled ad hoc LookML governance subsidiary"),
    # --- 20 ---
    ("Rill Data served the real-time exploration dashboards; DuckDB-backed local slicing kept the CEO's live revenue view under 200 ms.", "architecture", "technical", False,
     [("Rill Data", "tool"), ("DuckDB", "database")],
     [],
     "which BI tool powered the CEO live revenue exploration view",
     "rill DuckDB real time slice exploration CEO revenue live"),
    # --- 21 ---
    ("Cube.dev became the semantic layer between the warehouse and five BI tools; the REST and GraphQL APIs let the mobile app read the same measures.", "architecture", "technical", False,
     [("Cube.dev", "tool"), ("REST", "protocol"), ("GraphQL", "technology")],
     [],
     "which semantic layer unified measure definitions across BI and mobile",
     "cube semantic layer REST GraphQL mobile measure reuse"),
    # --- 22 ---
    ("MetricFlow from the dbt Labs stack replaced a homegrown metrics store; the dbt-integrated join graph beat the hand-written JSON mapping.", "decision", "technical", False,
     [("MetricFlow", "tool"), ("dbt Labs", "organization"), ("homegrown metrics store", "tool"), ("JSON", "language")],
     [("MetricFlow", "homegrown metrics store", "REPLACES")],
     "which metrics layer took over from the in-house metric store",
     "metricflow dbt labs metric store JSON join graph swap"),
    # --- 23 ---
    ("The Kimball star schema anchored the sales mart; dimensional conformed tables let three business lines share the same date and customer dimensions.", "architecture", "technical", False,
     [("Kimball", "pattern"), ("star schema", "pattern")],
     [],
     "which modeling methodology anchored the multi-line sales mart",
     "kimball star schema conformed dimension customer date mart"),
    # --- 24 ---
    ("Inmon's corporate information factory was rejected up front; the two-year upfront EDW build did not match the quarterly release pace.", "decision", "technical", False,
     [("Inmon", "pattern"), ("EDW", "concept")],
     [],
     "which modeling school was rejected for the quarterly release pace",
     "inmon corporate information factory EDW upfront build reject"),
    # --- 25 ---
    ("Data Vault 2.0 replaced a creaky third-normal-form EDW for the finance source; hubs, links and satellites absorbed the constant schema churn without breaking marts.", "decision", "technical", False,
     [("Data Vault 2.0", "pattern"), ("EDW", "concept")],
     [("Data Vault 2.0", "EDW", "REPLACES")],
     "which warehouse modeling approach absorbed the constant finance schema churn",
     "data vault hub link satellite EDW 3NF churn finance"),
    # --- 26 ---
    ("dbt model versioning let v1 and v2 of the orders model coexist during the pricing migration; the deprecation window ran for two sprints without breaking dashboards.", "milestone", "technical", False,
     [("dbt", "tool")],
     [],
     "how did the team run two orders definitions side by side during the rollout",
     "v1 v2 orders coexist deprecation window sprint dashboard"),
    # --- 27 ---
    ("Freshness tests on dbt sources caught the Stripe connector lag within 15 minutes; the Slack alert beat the old Monday-morning dashboard discovery loop.", "milestone", "technical", False,
     [("dbt", "tool"), ("Stripe", "service"), ("Slack", "service")],
     [],
     "which dbt test mechanism caught the Stripe connector lag in minutes",
     "dbt freshness source test stripe lag slack alert Monday"),
    # --- 28 ---
    ("OpenLineage emitted run events from Airflow and dbt into the Marquez backend; column-level lineage surfaced a stealth join on a deprecated field.", "architecture", "technical", False,
     [("OpenLineage", "framework"), ("Airflow", "tool"), ("dbt", "tool"), ("Marquez", "tool")],
     [],
     "which lineage stack caught the stealth join on a deprecated field",
     "openlineage airflow dbt marquez column lineage deprecated field"),
    # --- 29 ---
    ("Marquez replaced a hand-rolled lineage graph stored in Neo4j; OpenLineage-native ingestion avoided the mapper code that kept drifting.", "decision", "technical", False,
     [("Marquez", "tool"), ("Neo4j", "database"), ("OpenLineage", "framework")],
     [("Marquez", "Neo4j", "REPLACES")],
     "which lineage backend displaced the Neo4j-based in-house graph",
     "marquez neo4j hand rolled lineage openlineage mapper drift"),
    # --- 30 ---
    ("Monte Carlo monitored freshness and volume on the top-50 tables; the ML-driven anomaly detection caught a partition drop before the morning exec report.", "architecture", "technical", False,
     [("Monte Carlo", "service")],
     [],
     "which data observability vendor caught the partition drop pre-exec report",
     "monte carlo freshness volume anomaly top tables exec morning"),
    # --- 31 ---
    ("Bigeye was evaluated against Monte Carlo; Monte Carlo won on out-of-the-box coverage but Bigeye's SLA dashboards looked cleaner for contract negotiation.", "decision", "technical", False,
     [("Bigeye", "service"), ("Monte Carlo", "service"), ("SLA", "concept")],
     [],
     "which data observability vendor won the evaluation and on what axis",
     "bigeye monte carlo evaluation SLA dashboard coverage contract"),
    # --- 32 ---
    ("Elementary replaced Monte Carlo for the lean analytics team; dbt-native tests plus a local dashboard covered 80 percent of the use case for free.", "decision", "technical", False,
     [("Elementary", "tool"), ("Monte Carlo", "service"), ("dbt", "tool")],
     [("Elementary", "Monte Carlo", "REPLACES")],
     "which OSS observability tool took over from Monte Carlo on budget",
     "elementary monte carlo dbt native test dashboard cost cut"),
    # --- 33 ---
    ("re_data sat alongside Elementary for anomaly detection on dbt models; Z-score and Mann-Kendall metrics caught drift that fixed-threshold tests missed.", "architecture", "technical", False,
     [("re_data", "tool"), ("Elementary", "tool"), ("dbt", "tool")],
     [],
     "which OSS tool added statistical anomaly detection on dbt models",
     "re_data elementary dbt Z score Mann Kendall drift anomaly"),
    # --- 34. noise ---
    ("Hold on, the warehouse is queuing again, might be the autoscaler.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("dbt Cloud was preferred over self-hosted dbt Core for the analyst workflow; the IDE, job scheduler and metadata API beat the GitHub Actions setup on onboarding time.", "preference", "technical", False,
     [("dbt Cloud", "service"), ("dbt Core", "tool"), ("GitHub Actions", "service")],
     [("dbt Cloud", "dbt Core", "PREFERS")],
     "which dbt offering won the analyst onboarding race over the OSS core",
     "dbt cloud core IDE scheduler metadata github actions onboard"),
    # --- 36 ---
    ("dbt exposures documented the downstream BI consumers; the lineage graph caught a Superset dashboard pointing at a deprecated staging model.", "milestone", "technical", False,
     [("dbt", "tool"), ("Superset", "tool")],
     [],
     "which dbt feature caught a Superset dashboard on a deprecated stage",
     "dbt exposure downstream superset deprecated staging model lineage"),
    # --- 37 ---
    ("Dagster replaced Airflow for the analytics orchestration; software-defined assets and dbt integration meant the DAG followed the model graph instead of manual DAG wiring.", "decision", "technical", False,
     [("Dagster", "tool"), ("Airflow", "tool"), ("DAG", "concept"), ("dbt", "tool")],
     [("Dagster", "Airflow", "REPLACES")],
     "which orchestrator took over from Airflow for analytics-first DAGs",
     "dagster airflow software defined asset dbt DAG analytics wire"),
    # --- 38 ---
    ("Prefect was evaluated alongside Dagster for the analytics stack; Dagster's asset graph modeled dbt better but Prefect's Python-first ergonomics appealed to the ML side.", "decision", "technical", False,
     [("Prefect", "tool"), ("Dagster", "tool"), ("dbt", "tool"), ("Python", "language")],
     [],
     "which orchestrator lost to Dagster on the analytics stack fit",
     "prefect dagster python asset graph dbt ML ergonomics eval"),
    # --- 39 ---
    ("ThoughtSpot's search-based BI was rejected for the finance audience; CFOs wanted pixel-perfect board decks, not natural-language charts.", "decision", "technical", False,
     [("ThoughtSpot", "tool")],
     [],
     "which BI experiment was rejected because CFOs wanted pixel-perfect decks",
     "thoughtspot search BI finance CFO board deck pixel perfect"),
    # --- 40 ---
    ("Holistics.io was preferred over Metabase for the SE-Asia subsidiary; AML data model syntax matched the analyst team's prior Looker muscle memory.", "preference", "technical", False,
     [("Holistics.io", "tool"), ("Metabase", "tool"), ("Looker", "tool")],
     [("Holistics.io", "Metabase", "PREFERS")],
     "which BI tool beat Metabase for the SE-Asia subsidiary rollout",
     "holistics metabase AML looker muscle memory subsidiary model"),
    # --- 41 ---
    ("Great Expectations guarded the landing-zone data contracts; expectations in YAML plus Airflow gated loads into the warehouse raw schema.", "architecture", "technical", False,
     [("Great Expectations", "tool"), ("YAML", "language"), ("Airflow", "tool")],
     [],
     "which data quality tool gated loads into the warehouse raw schema",
     "great expectations landing zone contract YAML airflow gate"),
    # --- 42 ---
    ("Soda replaced Great Expectations on the newer pipelines; SodaCL was easier to diff in pull requests than Great Expectations' JSON checkpoints.", "decision", "technical", False,
     [("Soda", "tool"), ("Great Expectations", "tool"), ("SodaCL", "language"), ("JSON", "language")],
     [("Soda", "Great Expectations", "REPLACES")],
     "which data quality tool displaced Great Expectations on newer pipelines",
     "soda great expectations SodaCL JSON checkpoint diff review"),
    # --- 43 ---
    ("Fivetran Transformations was rejected for the modeling layer; dbt Core on Git with CI was worth the extra wiring for reviewability.", "decision", "technical", False,
     [("Fivetran Transformations", "service"), ("dbt Core", "tool"), ("Git", "tool"), ("CI", "concept")],
     [("dbt Core", "Fivetran Transformations", "PREFERS")],
     "which bundled transform offering was rejected in favor of dbt plus Git",
     "fivetran transformations dbt core git CI reviewable reject"),
    # --- 44 ---
    ("Atlan catalog replaced a Confluence-hosted data dictionary; automated lineage plus owner metadata cut the analyst onboarding path by two weeks.", "decision", "technical", False,
     [("Atlan", "service"), ("Confluence", "service")],
     [("Atlan", "Confluence", "REPLACES")],
     "which data catalog took over from the Confluence dictionary for onboarding",
     "atlan confluence catalog lineage owner metadata onboard"),
    # --- 45 ---
    ("Amundsen was deployed as the self-hosted data catalog for the platform team; the Lyft lineage model fit the Kafka-plus-warehouse shape better than Atlan's warehouse-first view.", "architecture", "technical", False,
     [("Amundsen", "tool"), ("Lyft", "organization"), ("Kafka", "service"), ("Atlan", "service")],
     [],
     "which self-hosted catalog fit the Kafka-plus-warehouse topology better",
     "amundsen lyft kafka warehouse atlan self hosted catalog fit"),
    # --- 46 ---
    ("DataHub from LinkedIn replaced Amundsen on the platform side; the typed metadata model and GraphQL API felt production-ready for cross-team search.", "decision", "technical", False,
     [("DataHub", "tool"), ("LinkedIn", "organization"), ("Amundsen", "tool"), ("GraphQL", "technology")],
     [("DataHub", "Amundsen", "REPLACES")],
     "which catalog took over from Amundsen on the platform side",
     "datahub linkedin amundsen GraphQL typed metadata cross team"),
    # --- 47 ---
    ("Semantic layer reuse between Cube and Lightdash failed on join semantics; Cube owned the API-served measures while Lightdash served the dbt-native metrics, duplicated but honest.", "problem", "technical", False,
     [("Cube", "tool"), ("Lightdash", "tool"), ("dbt", "tool")],
     [],
     "which semantic layer reuse attempt failed on join semantics",
     "cube lightdash semantic layer join duplicate dbt native API"),
    # --- 48 ---
    ("MotherDuck served the analyst laptops as a hybrid DuckDB frontend; local exploration against warehouse data avoided shipping 10 GB extracts around.", "architecture", "technical", False,
     [("MotherDuck", "service"), ("DuckDB", "database")],
     [],
     "which hybrid DuckDB service kept analysts off bulk extract workflows",
     "motherduck duckdb laptop hybrid extract warehouse explore"),
    # --- 49 ---
    ("dbt Semantic Layer on MetricFlow was preferred over the older dbt metrics; MetricFlow's join resolver and saved queries beat the deprecated dbt_metrics package.", "preference", "technical", False,
     [("dbt Semantic Layer", "tool"), ("MetricFlow", "tool"), ("dbt_metrics", "tool")],
     [("MetricFlow", "dbt_metrics", "REPLACES")],
     "which dbt metrics layer won over the older dbt_metrics package",
     "dbt semantic layer metricflow saved query join resolver deprecate"),
    # --- 50 ---
    ("Column-level lineage shipped into the catalog on 2026-04-02; OpenLineage facets from Spark, dbt and Airflow landed in DataHub and cut impact analysis to seconds.", "milestone", "technical", False,
     [("OpenLineage", "framework"), ("Spark", "service"), ("dbt", "tool"), ("Airflow", "tool"), ("DataHub", "tool"), ("2026-04-02", "date")],
     [],
     "when did column-level lineage land in the catalog and from which sources",
     "column lineage ship openlineage spark dbt airflow datahub"),
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
