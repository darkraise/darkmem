"""One-off emitter for shared-base batch-160 — technical domain (feature stores and MLOps metadata: Feast, Tecton, Hopsworks, Michelangelo, Zipline, Vertex/SageMaker/Databricks feature stores, streaming features, point-in-time correctness, online/offline parity, skew detection, materialization).

Writes 50 rows to data/v2/shared/batch_160.tmp.jsonl with ids shared-07951..08000.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_160.tmp.jsonl"
ID_OFFSET = 7950

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Adopted Feast as the feature store because the team needed an open-source option that plugged into an existing Redis online cache and a BigQuery offline warehouse without forcing a platform rewrite.", "decision", "technical", False,
     [("Feast", "framework"), ("Redis", "database"), ("BigQuery", "database")],
     [("Feast", "Redis", "USES"), ("Feast", "BigQuery", "USES")],
     "which open-source feature store did the team pick to bridge an existing Redis cache and a BigQuery warehouse",
     "feast feature store redis online bigquery offline adopt open source"),
    # --- 2 ---
    ("Tecton replaced an in-house feature pipeline at the fintech; the managed service handled streaming aggregations and point-in-time joins that the old Airflow batch graph could not express cleanly.", "decision", "technical", False,
     [("Tecton", "service"), ("Airflow", "tool"), ("streaming aggregations", "concept"), ("point-in-time joins", "concept")],
     [("Tecton", "Airflow", "REPLACES")],
     "which managed feature platform took over from the Airflow batch pipeline at the fintech and what capability drove that",
     "tecton airflow feature pipeline streaming aggregation point time join"),
    # --- 3 ---
    ("Hopsworks is the chosen platform for the on-prem deployment because its offline store sits on Apache Hudi and the online store runs RonDB, which the ops team could host without touching a cloud vendor.", "decision", "technical", False,
     [("Hopsworks", "platform"), ("Apache Hudi", "technology"), ("RonDB", "database")],
     [("Hopsworks", "Apache Hudi", "USES"), ("Hopsworks", "RonDB", "USES")],
     "why did the on-prem feature store land on Hopsworks rather than a cloud-hosted option",
     "hopsworks hudi rondb on prem offline online store self host"),
    # --- 4 ---
    ("Michelangelo is the internal ML platform at Uber and the feature store layer under it predates most open-source offerings; new teams onboard through a curated feature catalog rather than writing fresh pipelines.", "fact", "technical", False,
     [("Michelangelo", "platform"), ("Uber", "organization"), ("feature catalog", "concept")],
     [("Michelangelo", "Uber", "DEPLOYED_ON")],
     "which internal ML platform at Uber exposes features through a curated catalog instead of bespoke pipelines",
     "michelangelo uber internal ml platform feature catalog onboard"),
    # --- 5 ---
    ("Zipline, the feature engineering framework open-sourced by Airbnb, drives the bulk of the recommendation features because its temporal aggregation primitives map cleanly to the leave-one-out training windows.", "fact", "technical", False,
     [("Zipline", "framework"), ("Airbnb", "organization"), ("temporal aggregation", "concept")],
     [("Zipline", "Airbnb", "AUTHORED_BY")],
     "which Airbnb-authored feature framework handles temporal aggregations for the recommender's training windows",
     "zipline airbnb feature engineering temporal aggregation recommendation"),
    # --- 6 ---
    ("Vertex Feature Store backs the GCP-native model fleet; batch serving reads from BigQuery and online serving hits the managed low-latency endpoint without the team running any Redis cluster themselves.", "reference", "technical", False,
     [("Vertex Feature Store", "service"), ("GCP", "platform"), ("BigQuery", "database")],
     [("Vertex Feature Store", "GCP", "DEPLOYED_ON"), ("Vertex Feature Store", "BigQuery", "USES")],
     "which managed feature store powers the GCP-native models and how does it avoid a self-hosted online cache",
     "vertex feature store gcp bigquery online endpoint managed low latency"),
    # --- 7 ---
    ("SageMaker Feature Store is wired into the training jobs via the offline store on S3 while the online store serves real-time inference; the split keeps a single feature definition reused by both paths.", "architecture", "technical", False,
     [("SageMaker Feature Store", "service"), ("S3", "service"), ("online store", "concept"), ("offline store", "concept")],
     [("SageMaker Feature Store", "S3", "USES")],
     "how does SageMaker Feature Store keep a single feature definition consistent across training and online inference",
     "sagemaker feature store s3 offline online inference training single"),
    # --- 8 ---
    ("Databricks Feature Store publishes to a Delta Lake offline table and syncs to DynamoDB for online lookup; the lineage panel in Unity Catalog walks from the feature back to the notebook cell that produced it.", "architecture", "technical", False,
     [("Databricks Feature Store", "service"), ("Delta Lake", "technology"), ("DynamoDB", "database"), ("Unity Catalog", "tool")],
     [("Databricks Feature Store", "Delta Lake", "USES"), ("Databricks Feature Store", "DynamoDB", "USES")],
     "how does Databricks Feature Store surface lineage from a served feature back to its authoring notebook",
     "databricks feature store delta dynamodb unity catalog lineage notebook"),
    # --- 9 ---
    ("Chalk was evaluated for the fraud team because its resolver-based authoring lets an analyst express a streaming feature as a Python function without hand-rolling Kafka consumers.", "fact", "technical", False,
     [("Chalk", "platform"), ("Kafka", "technology"), ("resolver", "pattern")],
     [],
     "what did the anti-fraud group pick so analysts could pen Python snippets in place of bespoke message-bus code",
     "chalk resolver python streaming feature kafka consumer fraud analyst"),
    # --- 10. noise ---
    ("The office kombucha tap ran dry on a Tuesday and the facilities Slack channel spawned a seventy-reply argument over which flavour to rotate in.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Bytewax now handles the streaming aggregations that Flink used to own; the Python-native dataflow made it far easier to share feature-transform code between the batch notebooks and the stream operators.", "decision", "technical", False,
     [("Bytewax", "framework"), ("Flink", "framework"), ("Python", "language")],
     [("Bytewax", "Flink", "REPLACES")],
     "which streaming framework took over from Flink for feature aggregations and what code-reuse win sealed it",
     "bytewax flink python streaming aggregation dataflow batch share"),
    # --- 12 ---
    ("Point-in-time correctness is enforced by an as-of join at training time; every training row carries the feature values that were observable at its label timestamp, so no future leakage sneaks into the model.", "fact", "technical", False,
     [("Point-in-time correctness", "concept"), ("as-of join", "algorithm"), ("future leakage", "concept")],
     [("as-of join", "Point-in-time correctness", "IMPLEMENTS")],
     "which join strategy at training time guarantees features were observable as of the label timestamp and nothing later",
     "point in time as of join label timestamp leakage training correct"),
    # --- 13 ---
    ("Training-serving skew surfaced as a six-point AUC gap between offline eval and production; root cause was the online path using a stale Redis key and the offline path recomputing from the raw event log.", "problem", "technical", False,
     [("Training-serving skew", "concept"), ("AUC", "concept"), ("Redis", "database")],
     [("Redis", "Training-serving skew", "CAUSES")],
     "which production discrepancy produced the six-point AUC gap and which component drifted from the offline computation",
     "training serving skew auc gap redis stale key offline online"),
    # --- 14 ---
    ("Online and offline parity is verified by a nightly job that samples live inference payloads, re-runs the feature definition against the offline store, and alerts if divergence exceeds one percent on any feature.", "architecture", "technical", False,
     [("Online and offline parity", "concept"), ("nightly job", "pattern"), ("feature definition", "concept")],
     [],
     "how is the parity between online-served features and their offline recomputation monitored each night",
     "online offline parity nightly sample inference recompute divergence alert"),
    # --- 15 ---
    ("Feature freshness for the fraud model is pinned at under two minutes; anything staler triggers a pager because the upstream Kafka consumer lag is the usual culprit and it costs approved transactions.", "decision", "technical", False,
     [("Feature freshness", "concept"), ("Kafka", "technology"), ("pager", "tool")],
     [],
     "which freshness threshold guards the fraud model and which upstream component usually causes breaches",
     "feature freshness two minute fraud kafka lag pager threshold"),
    # --- 16 ---
    ("Feature lineage lives in an OpenLineage graph keyed by feature name; the UI walks from a model version through the features it consumed back to the source tables and the dbt node that wrote them.", "architecture", "technical", False,
     [("OpenLineage", "tool"), ("Feature lineage", "concept"), ("dbt", "tool")],
     [("Feature lineage", "OpenLineage", "USES"), ("Feature lineage", "dbt", "USES")],
     "how does the lineage UI trace from a model version back to the dbt node that produced an upstream table",
     "open lineage feature lineage dbt model version source table graph"),
    # --- 17 ---
    ("Materialization schedules are declared per feature view in Feast; heavy aggregates run hourly off Spark while cheap derived features run every ten minutes directly on the warehouse without spinning up a cluster.", "architecture", "technical", False,
     [("Feast", "framework"), ("Spark", "framework"), ("feature view", "concept"), ("Materialization", "concept")],
     [("Feast", "Spark", "USES")],
     "how does Feast split heavy hourly aggregates from cheap ten-minute derivations across Spark and the warehouse",
     "feast materialization schedule spark feature view warehouse hourly"),
    # --- 18 ---
    ("Skew detection ships as a continuous KS-test between a rolling window of online feature values and the training distribution; a breach opens a Jira ticket tagged with the feature view id for triage.", "reference", "technical", False,
     [("Skew detection", "concept"), ("KS-test", "algorithm"), ("Jira", "service"), ("feature view", "concept")],
     [("Skew detection", "KS-test", "USES")],
     "which statistical test backs the continuous skew detection and where does a breach land for triage",
     "skew detect ks test rolling window jira feature view ticket"),
    # --- 19 ---
    ("Entity, feature, and feature view abstractions come straight out of the Feast data model; the team refused to invent a parallel vocabulary so docs, code, and registry all speak the same three nouns.", "preference", "technical", False,
     [("Entity", "concept"), ("feature", "concept"), ("feature view", "concept"), ("Feast", "framework")],
     [],
     "which three Feast abstractions did the team adopt verbatim to keep docs, code, and registry aligned",
     "entity feature view feast abstraction vocabulary registry docs align"),
    # --- 20 ---
    ("Online store is Redis for sub-millisecond lookups while the offline store is an Iceberg table on S3; the split is non-negotiable because bulk scans over Redis are ruinous and point lookups over Iceberg are slow.", "decision", "technical", False,
     [("Redis", "database"), ("Iceberg", "technology"), ("S3", "service"), ("Online store", "concept"), ("offline store", "concept")],
     [("Online store", "Redis", "USES"), ("offline store", "Iceberg", "USES")],
     "why is the online-offline split pinned to Redis and Iceberg rather than a single unified store",
     "redis iceberg s3 online offline store sub millisecond bulk scan split"),
    # --- 21 ---
    ("DynamoDB replaced Redis as the online store after a regional failover exposed that the old single-AZ Redis cluster was a blast radius wider than the entire inference SLO for the checkout model.", "decision", "technical", False,
     [("DynamoDB", "database"), ("Redis", "database"), ("checkout model", "project")],
     [("DynamoDB", "Redis", "REPLACES")],
     "which online store replaced Redis for the checkout model and what incident forced the swap",
     "dynamodb redis online store failover single az blast radius checkout"),
    # --- 22 ---
    ("Feature backfills run through a dedicated batch DAG in Airflow; the DAG writes to the Delta offline table and only triggers the online sync once the checksum matches the expected row count.", "architecture", "technical", False,
     [("Airflow", "tool"), ("Delta", "technology"), ("Feature backfills", "concept"), ("checksum", "concept")],
     [("Feature backfills", "Airflow", "USES")],
     "how does the backfill DAG gate an online sync so partial writes never reach the serving path",
     "airflow backfill delta checksum online sync gate row count feature"),
    # --- 23 ---
    ("Streaming aggregations for the recommendation service use tumbling one-minute windows over Kafka keyed by user id; the sliding-window variant was rejected because state size grew unbounded during the holiday peak.", "decision", "technical", False,
     [("tumbling one-minute windows", "concept"), ("sliding-window", "concept"), ("Kafka", "technology"), ("recommendation service", "project")],
     [("tumbling one-minute windows", "sliding-window", "PREFERS")],
     "which windowing strategy won for the recommender's streaming features and which one blew up during holiday peak",
     "tumbling sliding window kafka recommendation state size holiday peak"),
    # --- 24 ---
    ("The feature registry is the source of truth; a pull-request gate rejects any notebook that materialises a feature whose name is not already declared, which killed the ad-hoc column-sprawl problem in a quarter.", "decision", "technical", False,
     [("feature registry", "concept"), ("pull-request gate", "pattern"), ("column-sprawl", "concept")],
     [("pull-request gate", "column-sprawl", "FIXES")],
     "which governance gate eliminated ad-hoc column sprawl around the feature registry",
     "feature registry pull request gate column sprawl notebook govern source"),
    # --- 25 ---
    ("Feast's materialize-incremental command became the default because the full-materialization path re-read months of history every run; incremental cut the Spark bill by roughly two-thirds on the top ten feature views.", "milestone", "technical", False,
     [("Feast", "framework"), ("materialize-incremental", "command"), ("Spark", "framework")],
     [("materialize-incremental", "Feast", "IMPROVES_ON")],
     "which Feast command became the default for materialization and what cost reduction did it yield",
     "feast materialize incremental spark cost cut full re read history"),
    # --- 26 ---
    ("Tecton's on-demand feature view encodes the last-mile transform that has to run at request time; the pattern kept the online store free of pre-joined user-session cross products that would have blown the memory budget.", "fact", "technical", False,
     [("Tecton", "service"), ("on-demand feature view", "concept"), ("online store", "concept")],
     [],
     "which Tecton primitive keeps pre-joined cross products out of the online store by running at request time",
     "tecton on demand feature view request time cross product memory budget"),
    # --- 27 ---
    ("Feature versioning follows a semver-like convention where a breaking schema change bumps the major and forces downstream models to opt in; silent shadow writes run for one week before the old version is retired.", "architecture", "technical", False,
     [("Feature versioning", "concept"), ("semver", "concept"), ("shadow write", "pattern")],
     [],
     "how are breaking feature schema changes rolled out without forcing an instant migration on downstream models",
     "feature version semver shadow write major bump opt in retire week"),
    # --- 28 ---
    ("Arrived at online/offline parity sign-off for the ranking model after six weeks of reconciliation; the final blocker was a timezone mismatch on the event timestamp where the offline job used UTC and the online path used local time.", "milestone", "technical", False,
     [("ranking model", "project"), ("UTC", "concept"), ("timezone mismatch", "concept")],
     [("timezone mismatch", "ranking model", "CAUSES")],
     "which subtle defect blocked parity sign-off for the ranking model until the sixth week of reconciliation",
     "online offline parity ranking timezone mismatch utc local sign off"),
    # --- 29 ---
    ("The feature store registry is persisted to a Postgres metadata DB; the old file-based registry kept racing on concurrent apply commands from CI and production, and two engineers lost an afternoon to a clobbered YAML.", "milestone", "technical", False,
     [("registry", "concept"), ("Postgres", "database"), ("YAML", "file"), ("CI", "service")],
     [("Postgres", "registry", "USES")],
     "why did the feature registry move from a file-based store to Postgres and what concrete bug forced it",
     "registry postgres yaml file race apply ci concurrent clobber"),
    # --- 30 ---
    ("Streaming feature freshness is monitored with a heartbeat event injected every thirty seconds; if the downstream feature does not update within two minutes the pipeline fires a synthetic null and pages the on-call.", "architecture", "technical", False,
     [("Streaming feature", "concept"), ("heartbeat event", "pattern"), ("on-call", "concept")],
     [],
     "how does the streaming pipeline detect a stalled feature without waiting for a real customer request to reveal it",
     "streaming feature heartbeat thirty second two minute page on call"),
    # --- 31 ---
    ("Chose Iceberg over Delta for the offline feature store because the team wanted hidden partitioning and partition-evolution without rewriting existing consumers; the rest of the lakehouse was already on Iceberg anyway.", "decision", "technical", False,
     [("Iceberg", "technology"), ("Delta", "technology"), ("offline feature store", "concept")],
     [("Iceberg", "Delta", "PREFERS")],
     "which table format did the offline feature store land on and which feature drove the preference over Delta",
     "iceberg delta offline feature store hidden partition evolution lakehouse"),
    # --- 32 ---
    ("Feature push ingestion bypasses the warehouse: a service writes a freshly computed feature value directly to the Feast online store via the gRPC push API when a user action needs a sub-second reflection in the model.", "fact", "technical", False,
     [("Feast", "framework"), ("gRPC", "protocol"), ("push API", "api"), ("online store", "concept")],
     [("Feast", "gRPC", "USES")],
     "which Feast ingestion path keeps a user-action feature under a second by skipping the warehouse hop",
     "feast push api grpc online store sub second user action ingest"),
    # --- 33 ---
    ("SageMaker Feature Store's time travel query replays the feature values as of a prior timestamp; the compliance audit used it to reproduce every decision the approvals model made during the quarter under review.", "fact", "technical", False,
     [("SageMaker Feature Store", "service"), ("time travel", "concept"), ("approvals model", "project")],
     [],
     "which SageMaker Feature Store capability let the compliance team reproduce past approvals-model decisions exactly",
     "sagemaker feature store time travel compliance audit approvals model"),
    # --- 34 ---
    ("Referenced the Uber Engineering blog post on Michelangelo's feature store evolution for the internal architecture review; the described dual-store pattern matched the direction the team had already sketched on the whiteboard.", "reference", "technical", False,
     [("Uber Engineering", "organization"), ("Michelangelo", "platform"), ("dual-store", "pattern")],
     [],
     "which external write-up anchored the internal architecture review for the dual-store feature platform",
     "uber engineering michelangelo blog dual store architecture review"),
    # --- 35 ---
    ("Referenced the Feast 0.40 release notes while scoping the migration because the breaking change to the registry proto required every downstream service to pin a new client version before the cutover window.", "reference", "technical", False,
     [("Feast 0.40", "date"), ("registry proto", "concept"), ("client version", "concept")],
     [],
     "which release-notes document scoped the Feast migration cutover because of a registry proto break",
     "feast 0 40 release notes registry proto client version migration"),
    # --- 36 ---
    ("Referenced the Tecton documentation page on materialization jobs to settle the debate over whether transformation SQL runs on Snowflake or on the Tecton-managed Spark cluster under the stream-batch split.", "reference", "technical", False,
     [("Tecton", "service"), ("Snowflake", "database"), ("Spark", "framework")],
     [],
     "which Tecton documentation page clarified where transformation SQL runs under the stream-batch split",
     "tecton materialization job doc snowflake spark transformation sql"),
    # --- 37 ---
    ("Prefer declarative feature definitions over imperative pipelines; the team standardised on YAML feature views reviewed in pull requests because imperative Python pipelines hid business logic inside scheduler configuration.", "preference", "technical", False,
     [("YAML", "file"), ("feature view", "concept"), ("pull request", "pattern")],
     [],
     "which feature authoring style does the team prefer and why was the imperative Python alternative rejected",
     "declarative yaml feature view pull request imperative python pipeline"),
    # --- 38 ---
    ("Prefer Bytewax dataflows over Spark Structured Streaming for small-to-medium feature pipelines because the Python-native operators let the ML engineers own the code without pulling a data engineer into every change.", "preference", "technical", False,
     [("Bytewax", "framework"), ("Spark Structured Streaming", "framework"), ("Python", "language")],
     [("Bytewax", "Spark Structured Streaming", "PREFERS")],
     "which streaming framework does the team prefer for ML-owned feature pipelines and what ownership outcome drove it",
     "bytewax spark structured streaming python ml engineer ownership pipeline"),
    # --- 39 ---
    ("Prefer naming feature views with the entity prefix and an aggregate-window suffix like user_clicks_7d; the convention keeps ambiguity out of the registry even when three teams own overlapping user-level features.", "preference", "technical", False,
     [("feature view", "concept"), ("entity prefix", "pattern"), ("aggregate-window suffix", "pattern"), ("user_clicks_7d", "concept")],
     [],
     "which naming convention keeps feature-view names unambiguous across teams authoring user-level features",
     "feature view name entity prefix aggregate window user clicks 7d"),
    # --- 40 ---
    ("The point-in-time join for the churn model was producing duplicate rows when two events landed in the same second; broke the tie with a monotonically increasing event sequence number and the dedup went away.", "problem", "technical", False,
     [("point-in-time join", "algorithm"), ("churn model", "project"), ("event sequence number", "concept")],
     [("event sequence number", "point-in-time join", "FIXES")],
     "which tie-breaker fixed the duplicate-row bug in the churn model's point-in-time join",
     "point time join churn duplicate row event sequence tie break"),
    # --- 41 ---
    ("Shipped the first end-to-end Feast deployment to production for the search ranker; sixty-two feature views crossed from a staging registry to the prod registry in a single atomic apply after two weeks of rehearsal.", "milestone", "technical", False,
     [("Feast", "framework"), ("search ranker", "project"), ("registry", "concept")],
     [("Feast", "search ranker", "APPLIES_TO")],
     "which production milestone moved sixty-two feature views from staging to prod for the search ranker",
     "feast search ranker sixty two feature view staging prod apply"),
    # --- 42 ---
    ("Cut over the churn model from the legacy in-house feature pipeline to Tecton; the first week showed training-serving skew dropping from eight percent to under half a percent on the top-twenty features.", "milestone", "technical", False,
     [("churn model", "project"), ("Tecton", "service"), ("training-serving skew", "concept")],
     [("churn model", "Tecton", "USES")],
     "which cutover slashed training-serving skew on the churn model's top features from eight percent to under half",
     "churn tecton legacy cutover training serving skew eight half percent"),
    # --- 43. noise ---
    ("Someone in accounting named the office plant Horace and now Horace has a small name tag taped to his pot.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Hit the point where every feature in the recommendations surface had documented lineage back to its source event; the audit dashboard turned green and the platform team closed the year-long compliance epic.", "milestone", "technical", False,
     [("recommendations surface", "project"), ("lineage", "concept"), ("audit dashboard", "tool")],
     [],
     "which milestone closed the year-long compliance epic for the recommendations surface lineage coverage",
     "recommendations lineage source event audit dashboard compliance epic"),
    # --- 45 ---
    ("Moved the offline feature materialization off Snowflake onto Databricks because Snowflake credit burn on repeated window aggregates was outrunning the savings; Delta plus Photon cut the monthly bill roughly in half.", "milestone", "technical", False,
     [("Snowflake", "database"), ("Databricks", "platform"), ("Delta", "technology"), ("Photon", "tool")],
     [("Databricks", "Snowflake", "REPLACES")],
     "which compute migration halved the monthly bill for offline feature materialization and what stack replaced Snowflake",
     "snowflake databricks delta photon credit burn window aggregate bill"),
    # --- 46 ---
    ("A silent schema drift broke the fraud model online: a new column was appended to the source table and the offline materialization picked it up, while the online feature writer kept serving the old payload.", "problem", "technical", False,
     [("schema drift", "concept"), ("fraud model", "project"), ("online feature writer", "concept"), ("source table", "concept")],
     [("schema drift", "fraud model", "CAUSES")],
     "which silent source-schema change broke fraud online by diverging the offline and online payloads",
     "schema drift fraud online offline source table append column feature"),
    # --- 47 ---
    ("The feature store now emits OpenTelemetry spans for every get-online-features call; p99 latency, hit ratio, and downstream Redis pool saturation all trace back to a single request id across services.", "reference", "technical", False,
     [("feature store", "concept"), ("OpenTelemetry", "tool"), ("get-online-features", "command"), ("Redis", "database"), ("p99 latency", "concept")],
     [("feature store", "OpenTelemetry", "USES")],
     "which observability stack now ties tail latency, cache hits, and pool pressure to one correlated trace id",
     "open telemetry get online feature redis p99 hit ratio request trace"),
    # --- 48 ---
    ("Zipline-style temporal aggregation primitives were reimplemented in-house on top of Flink because the open-source Zipline codebase lacked a supported Flink 1.18 runner and the team was already deep on Flink.", "decision", "technical", False,
     [("Zipline", "framework"), ("Flink", "framework"), ("Flink 1.18", "date"), ("temporal aggregation", "concept")],
     [],
     "why were Zipline-style aggregations rebuilt in-house on Flink instead of adopting the upstream Zipline codebase",
     "zipline flink 1 18 temporal aggregation in house runner reimplement"),
    # --- 49 ---
    ("The feast-spark-offline-store plugin replaced the vendored BigQuery offline store path once the team moved to a multi-cloud footprint; the plugin architecture kept the rest of the Feast config untouched.", "architecture", "technical", False,
     [("feast-spark-offline-store", "library"), ("BigQuery", "database"), ("Feast", "framework"), ("multi-cloud", "concept")],
     [("feast-spark-offline-store", "BigQuery", "REPLACES")],
     "which Feast plugin took over from the BigQuery offline store path after the move to multi-cloud",
     "feast spark offline store plugin bigquery multi cloud architecture"),
    # --- 50 ---
    ("Final call on the platform bake-off: Hopsworks for regulated workloads where on-prem was mandatory, Feast for the general-purpose OSS track, Tecton for teams that wanted streaming features without owning the infrastructure.", "decision", "technical", False,
     [("Hopsworks", "platform"), ("Feast", "framework"), ("Tecton", "service")],
     [("Hopsworks", "Feast", "RELATED_TO"), ("Feast", "Tecton", "RELATED_TO")],
     "how did the bake-off split regulated, general-purpose, and managed-streaming workloads across Hopsworks, Feast, and Tecton",
     "hopsworks feast tecton bake off regulated oss streaming managed split"),
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
