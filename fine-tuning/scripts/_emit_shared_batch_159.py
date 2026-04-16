"""One-off emitter for shared-base batch-159 — technical domain (workflow orchestration: Airflow, Dagster, Prefect, Temporal, Argo, Flyte, Step Functions, executors, sensors, retries, backfills, dynamic mapping).

Writes 50 rows to data/v2/shared/batch_159.tmp.jsonl with ids shared-07901..07950.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_159.tmp.jsonl"
ID_OFFSET = 7900

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the nightly ETL from Apache Airflow to Dagster so asset-based scheduling could express the warehouse tables directly instead of layering on top of a DAG of opaque operators.", "decision", "technical", False,
     [("Apache Airflow", "tool"), ("Dagster", "tool"), ("asset-based scheduling", "pattern"), ("DAG", "concept")],
     [("Dagster", "Apache Airflow", "REPLACES"), ("Dagster", "asset-based scheduling", "USES")],
     "which orchestrator swap let the nightly ETL express warehouse tables as first-class assets",
     "dagster airflow asset scheduling warehouse etl dag operator"),
    # --- 2 ---
    ("Prefect 2 replaced the homegrown cron runner for data pipelines; flow runs now show up in Prefect Cloud with retries and notifications without a babysitter script waking people at 3am.", "milestone", "technical", False,
     [("Prefect 2", "framework"), ("Prefect Cloud", "service"), ("cron", "tool")],
     [("Prefect 2", "cron", "REPLACES"), ("Prefect 2", "Prefect Cloud", "DEPLOYED_ON")],
     "which orchestrator retired the homegrown cron runner and gave ops a managed dashboard",
     "prefect cloud cron flow retry notification pipeline replace"),
    # --- 3 ---
    ("Long-running saga workflows moved to Temporal because Airflow's task model kept timing out on the external approval steps; Temporal activity heartbeats tolerate multi-day waits natively.", "decision", "technical", False,
     [("Temporal", "framework"), ("Airflow", "tool"), ("activity heartbeats", "pattern"), ("saga", "pattern")],
     [("Temporal", "Airflow", "REPLACES"), ("Temporal", "activity heartbeats", "USES")],
     "which workflow engine replaced Airflow for multi-day approval sagas and which feature sealed the choice",
     "temporal airflow saga activity heartbeat multi day approval timeout"),
    # --- 4 ---
    ("Argo Workflows runs the ML training DAGs on the GPU cluster because each step is already a container and the KubernetesPodOperator indirection in Airflow was just paperwork for the same result.", "architecture", "technical", False,
     [("Argo Workflows", "tool"), ("KubernetesPodOperator", "tool"), ("GPU cluster", "infrastructure"), ("Airflow", "tool")],
     [("Argo Workflows", "KubernetesPodOperator", "REPLACES"), ("Argo Workflows", "GPU cluster", "DEPLOYED_ON")],
     "which orchestrator runs the ML DAGs on the GPU cluster and why Kubernetes-native won over Airflow there",
     "argo workflow ml gpu kubernetes pod operator airflow container"),
    # --- 5 ---
    ("Kubeflow Pipelines handles the model training lifecycle end-to-end; experiment tracking, metadata, and the DAG scheduler are one package instead of three separate integrations glued together.", "fact", "technical", False,
     [("Kubeflow Pipelines", "tool"), ("experiment tracking", "pattern"), ("DAG scheduler", "pattern")],
     [("Kubeflow Pipelines", "DAG scheduler", "HAS_PART"), ("Kubeflow Pipelines", "experiment tracking", "HAS_PART")],
     "which ML orchestrator bundles experiment tracking, metadata, and DAG scheduling into a single package",
     "kubeflow pipeline experiment tracking metadata dag ml model lifecycle"),
    # --- 6 ---
    ("Flyte won the typed-pipeline bake-off against Airflow; strong static typing on task inputs caught three integration bugs at registration time that Airflow would have surfaced only at 4am.", "decision", "technical", False,
     [("Flyte", "tool"), ("Airflow", "tool"), ("static typing", "pattern")],
     [("Flyte", "Airflow", "PREFERS"), ("Flyte", "static typing", "USES")],
     "which orchestrator did we pick for typed ML pipelines and what class of bug did its typing catch early",
     "flyte airflow typed pipeline static type integration bug register"),
    # --- 7 ---
    ("Retired the last Luigi pipeline after the team agreed its target-file contract was a poor fit for cloud object stores where S3 consistency could mark a task done when the file wasn't visible yet.", "milestone", "technical", False,
     [("Luigi", "tool"), ("S3", "service"), ("target-file", "pattern")],
     [("Luigi", "target-file", "USES")],
     "which Luigi design choice pushed the team to retire it after S3 consistency bit the pipelines",
     "luigi s3 target file consistency cloud object store retire pipeline"),
    # --- 8 ---
    ("Kestra is the new orchestrator for the finance workflows because its YAML-declarative flows fit the analyst workflow where Python-first tools like Airflow needed a PR per trivial change.", "decision", "technical", False,
     [("Kestra", "tool"), ("Airflow", "tool"), ("YAML", "language")],
     [("Kestra", "Airflow", "PREFERS"), ("Kestra", "YAML", "USES")],
     "which orchestrator replaced Airflow for finance analysts and what workflow-authoring style sealed it",
     "kestra airflow yaml finance analyst declarative flow python pr"),
    # --- 9 ---
    ("AWS Step Functions glues the order-fulfilment Lambdas together; the state-machine JSON is version-controlled and the Express variant handles the high-throughput notification fan-out.", "architecture", "technical", False,
     [("AWS Step Functions", "service"), ("Lambda", "service"), ("Express", "service")],
     [("AWS Step Functions", "Lambda", "COMMUNICATES_WITH"), ("AWS Step Functions", "Express", "HAS_PART")],
     "which AWS service orchestrates the order-fulfilment Lambdas and which variant covers high-throughput fan-out",
     "step function lambda aws express state machine order fulfilment fan"),
    # --- 10. noise ---
    ("The office plant outside the kitchen keeps growing into the hallway and the facilities ticket has been open for six weeks.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Google Cloud Workflows runs the billing reconciliation because it ties directly into Cloud Run and Pub/Sub without an extra worker pool; the cost per invocation made it cheaper than a standing Airflow cluster.", "decision", "technical", False,
     [("Google Cloud Workflows", "service"), ("Cloud Run", "service"), ("Pub/Sub", "service"), ("Airflow", "tool")],
     [("Google Cloud Workflows", "Cloud Run", "COMMUNICATES_WITH"), ("Google Cloud Workflows", "Airflow", "REPLACES")],
     "which GCP orchestrator runs billing reconciliation and why it beat a standing Airflow cluster on cost",
     "google cloud workflow billing reconciliation run pub sub airflow cost"),
    # --- 12 ---
    ("GitHub Actions became the deploy DAG for the platform repo; needs and matrix together express a topological order and fan-out without bolting a separate orchestrator onto CI.", "architecture", "technical", False,
     [("GitHub Actions", "service"), ("needs", "config"), ("matrix", "config"), ("DAG", "concept")],
     [("GitHub Actions", "DAG", "IMPLEMENTS")],
     "which GitHub Actions primitives express deploy DAG topology and fan-out without an external orchestrator",
     "github actions deploy matrix needs dag topological fan out ci platform"),
    # --- 13 ---
    ("Airflow's SubDAGs got deleted from the repo; every SubDAG became a TaskGroup after the scheduler-deadlock incident where a SubDAGOperator blocked the pool for the whole DAG run.", "decision", "technical", False,
     [("Airflow", "tool"), ("SubDAG", "pattern"), ("TaskGroup", "pattern"), ("SubDAGOperator", "tool")],
     [("TaskGroup", "SubDAG", "REPLACES"), ("SubDAGOperator", "SubDAG", "IMPLEMENTS")],
     "which Airflow grouping pattern replaced SubDAGs after a scheduler deadlock and what was the failure mode",
     "airflow subdag taskgroup scheduler deadlock pool block operator"),
    # --- 14 ---
    ("Dynamic task mapping in Airflow 2.3 let us collapse a hand-rolled loop-generating DAG into a single expand() call; the number of file-chunks now flexes per-run without a restart.", "milestone", "technical", False,
     [("Airflow 2.3", "tool"), ("Dynamic task mapping", "pattern"), ("expand()", "api")],
     [("Airflow 2.3", "Dynamic task mapping", "USES")],
     "which Airflow 2.3 feature replaced the hand-rolled DAG-generating loop for per-run fan-out",
     "airflow dynamic task mapping expand fan out per run chunk loop"),
    # --- 15 ---
    ("Trigger rules on the cleanup task were set to all_done so the bucket-wipe still runs after an upstream failure; the default all_success had been silently keeping stale partitions around for weeks.", "fact", "technical", False,
     [("all_done", "config"), ("all_success", "config"), ("Trigger rules", "pattern"), ("bucket-wipe", "pattern")],
     [("all_done", "all_success", "REPLACES")],
     "which Airflow trigger rule replaced all_success on the cleanup task and what silent bug it fixed",
     "trigger rule all done success cleanup bucket wipe stale partition"),
    # --- 16 ---
    ("File-arrival sensor on the landing-zone bucket is an S3KeySensor in deferrable mode; the old poke mode pinned a worker slot for hours while waiting for the vendor's overnight drop.", "decision", "technical", False,
     [("S3KeySensor", "tool"), ("deferrable mode", "pattern"), ("poke mode", "pattern"), ("landing-zone", "pattern")],
     [("deferrable mode", "poke mode", "REPLACES")],
     "which Airflow sensor mode replaced poke for the vendor file-arrival watch and why",
     "s3 key sensor deferrable poke vendor landing zone worker slot pin"),
    # --- 17 ---
    ("Task retries on the flaky external API are exponential with a jitter: retries=5, retry_delay=60s, retry_exponential_backoff=True, max_retry_delay=30min; the flat 1-minute retry storm used to DoS the vendor.", "architecture", "technical", False,
     [("retry_exponential_backoff", "config"), ("retries", "config"), ("max_retry_delay", "config"), ("jitter", "pattern")],
     [],
     "which retry configuration tamed the external-API flakiness without DoSing the vendor",
     "retry exponential backoff jitter delay max external api flake dos"),
    # --- 18 ---
    ("SLA misses used to be an email nobody read; moved to a sla_miss_callback that pages the on-call and writes the miss into Snowflake for the weekly reliability review.", "decision", "technical", False,
     [("SLA miss", "concept"), ("sla_miss_callback", "api"), ("Snowflake", "database"), ("on-call", "concept")],
     [("sla_miss_callback", "Snowflake", "COMMUNICATES_WITH")],
     "how did the team turn Airflow SLA misses from dead-letter email into an actionable reliability signal",
     "sla miss callback snowflake page on call reliability review email"),
    # --- 19 ---
    ("Backfills for the customer-dimension table now go through airflow dags backfill with --run-backwards; running the oldest first used to block current-day ingestion behind a week of history.", "problem", "technical", False,
     [("Backfills", "concept"), ("airflow dags backfill", "command"), ("--run-backwards", "config"), ("customer-dimension", "pattern")],
     [],
     "which backfill flag stopped historical reruns from blocking current-day ingestion for a week",
     "backfill run backwards customer dimension airflow block current day"),
    # --- 20 ---
    ("The scheduler was swapped from the LocalExecutor to the CeleryExecutor once concurrent DAG runs crossed 200; the single-process local fork model couldn't keep up with task heartbeats.", "milestone", "technical", False,
     [("LocalExecutor", "tool"), ("CeleryExecutor", "tool"), ("scheduler", "concept"), ("task heartbeats", "pattern")],
     [("CeleryExecutor", "LocalExecutor", "REPLACES")],
     "which Airflow executor replaced LocalExecutor after concurrent DAG runs outgrew the single-process model",
     "celery executor local airflow concurrent dag heartbeat scheduler scale"),
    # --- 21 ---
    ("Rolled out the CeleryKubernetesExecutor: short Python tasks stay on Celery workers, heavy container tasks spawn a pod on Kubernetes, and we stopped paying for idle capacity between batch windows.", "decision", "technical", False,
     [("CeleryKubernetesExecutor", "tool"), ("Celery", "framework"), ("Kubernetes", "platform"), ("pod", "pattern")],
     [("CeleryKubernetesExecutor", "Celery", "USES"), ("CeleryKubernetesExecutor", "Kubernetes", "USES")],
     "which hybrid Airflow executor routes light Python tasks to Celery and heavy containers to Kubernetes",
     "celery kubernetes executor hybrid pod idle capacity batch window"),
    # --- 22 ---
    ("KubernetesPodOperator is how we isolate dependencies per task; the old BashOperator with a shared conda env kept colliding on NumPy versions between the forecasting and the geo teams.", "decision", "technical", False,
     [("KubernetesPodOperator", "tool"), ("BashOperator", "tool"), ("conda", "tool"), ("NumPy", "library")],
     [("KubernetesPodOperator", "BashOperator", "REPLACES")],
     "which operator replaced BashOperator to isolate per-task dependencies across teams",
     "kubernetes pod operator bash conda numpy isolate dependency team"),
    # --- 23 ---
    ("DAG serialisation is on by default; the webserver reads from the serialised DAG table instead of re-parsing Python files, which cut UI page-load from 14 seconds to under a second on the big repo.", "milestone", "technical", False,
     [("DAG serialisation", "pattern"), ("webserver", "service"), ("serialised DAG table", "pattern")],
     [("webserver", "serialised DAG table", "USES")],
     "which Airflow feature cut webserver page-load from 14 seconds to under a second on the big repo",
     "dag serialisation webserver page load parse python repo second"),
    # --- 24 ---
    ("The metadata database is Postgres 14 on RDS; MySQL was dropped because the scheduler's advisory-lock pattern on MySQL 5.7 deadlocked under parallel DAG-file parsing.", "problem", "technical", False,
     [("Postgres 14", "database"), ("RDS", "service"), ("MySQL 5.7", "database"), ("advisory-lock", "pattern")],
     [("Postgres 14", "MySQL 5.7", "REPLACES"), ("Postgres 14", "RDS", "DEPLOYED_ON")],
     "which metadata database replaced MySQL 5.7 after advisory-lock deadlocks bit the scheduler",
     "postgres mysql rds airflow metadata advisory lock deadlock scheduler"),
    # --- 25 ---
    ("Dagster software-defined assets model the dbt tables directly; a dbt model change auto-updates the asset lineage graph so stale tables stand out in the UI before anyone runs the pipeline.", "architecture", "technical", False,
     [("Dagster", "tool"), ("software-defined assets", "pattern"), ("dbt", "tool"), ("lineage graph", "pattern")],
     [("Dagster", "software-defined assets", "USES"), ("software-defined assets", "dbt", "APPLIES_TO")],
     "how do Dagster software-defined assets surface stale dbt tables before anyone runs the pipeline",
     "dagster software defined asset dbt lineage graph stale ui"),
    # --- 26 ---
    ("Prefect's task concurrency limits fence the database loader at 4 parallel writers; without the tag-based limit the worker fleet used to open 200 connections and starve the OLTP workload.", "fact", "technical", False,
     [("Prefect", "framework"), ("task concurrency", "pattern"), ("tag-based limit", "pattern"), ("OLTP", "concept")],
     [("tag-based limit", "task concurrency", "IMPLEMENTS")],
     "which Prefect feature capped parallel database writers to stop worker fleets from starving OLTP",
     "prefect concurrency tag limit database writer oltp connection starve"),
    # --- 27 ---
    ("Temporal workflows are versioned with GetVersion guards so a long-running workflow survives a deploy that changes the activity signature; otherwise the replay history breaks mid-flight.", "fact", "technical", False,
     [("Temporal", "framework"), ("GetVersion", "api"), ("replay history", "pattern")],
     [("Temporal", "GetVersion", "USES")],
     "which Temporal API keeps a long-running workflow valid across a deploy that changes activity signatures",
     "temporal getversion workflow version replay history deploy activity"),
    # --- 28 ---
    ("Argo's retry strategy is a combination of retryStrategy.limit and backoff.factor on the DAG template; a transient node eviction now retries silently instead of failing the whole pipeline.", "architecture", "technical", False,
     [("Argo", "tool"), ("retryStrategy", "config"), ("backoff.factor", "config"), ("node eviction", "pattern")],
     [],
     "which Argo retry config lets transient node evictions not take down the whole pipeline",
     "argo retry strategy backoff factor node eviction transient pipeline"),
    # --- 29 ---
    ("Cadence is still the engine for the legacy trade-settlement workflows; the team is gradually porting them to Temporal but activity-interface compatibility keeps the switch low-risk.", "fact", "technical", False,
     [("Cadence", "framework"), ("Temporal", "framework"), ("trade-settlement", "pattern")],
     [("Temporal", "Cadence", "REPLACES")],
     "which legacy workflow engine still runs trade settlement and what makes the Temporal migration low-risk",
     "cadence temporal trade settlement legacy activity interface migration"),
    # --- 30 ---
    ("The ExternalTaskSensor on the cross-DAG dependency was replaced by a Dataset-triggered schedule in Airflow 2.4; cross-DAG wiring is now declarative instead of a polling loop that burned a slot.", "decision", "technical", False,
     [("ExternalTaskSensor", "tool"), ("Dataset", "pattern"), ("Airflow 2.4", "tool")],
     [("Dataset", "ExternalTaskSensor", "REPLACES")],
     "which Airflow 2.4 primitive replaced ExternalTaskSensor for declarative cross-DAG dependencies",
     "external task sensor dataset airflow cross dag schedule poll slot"),
    # --- 31 ---
    ("Workflow logs got centralised to OpenSearch via a remote-logging config; the old per-worker disk layout meant you couldn't grep across tasks without SSHing to each Celery worker.", "architecture", "technical", False,
     [("OpenSearch", "service"), ("remote-logging", "config"), ("Celery worker", "service")],
     [("remote-logging", "OpenSearch", "COMMUNICATES_WITH")],
     "how did Airflow task logs stop requiring per-worker SSH to search across a failed DAG run",
     "airflow opensearch remote logging celery worker disk grep ssh"),
    # --- 32 ---
    ("Prefect deployments are driven from a GitHub Actions workflow on tag pushes; the pipeline builds the flow image, uploads the manifest, and applies it via prefect deployment apply.", "architecture", "technical", False,
     [("Prefect", "framework"), ("GitHub Actions", "service"), ("prefect deployment apply", "command"), ("manifest", "pattern")],
     [("GitHub Actions", "Prefect", "DEPLOYED_ON")],
     "which CI workflow applies Prefect deployments from tag pushes and what command does the apply",
     "prefect github actions deployment apply tag manifest flow image ci"),
    # --- 33 ---
    ("Flyte caching is keyed on the hash of task inputs plus the container digest; flipping cache_version lets us invalidate a specific node without nuking the whole lineage.", "fact", "technical", False,
     [("Flyte", "tool"), ("cache_version", "config"), ("container digest", "concept")],
     [],
     "how does Flyte key task caches and which knob invalidates a single node without nuking the lineage",
     "flyte cache version container digest task input hash invalidate node"),
    # --- 34 ---
    ("The preference for declarative flows pushed Kestra ahead of Prefect on the ops team's survey; analysts found the YAML-in-UI editor more approachable than Python classes for a glue workflow.", "preference", "technical", False,
     [("Kestra", "tool"), ("Prefect", "framework"), ("YAML-in-UI", "pattern")],
     [("Kestra", "Prefect", "PREFERS")],
     "which orchestrator does the ops team prefer for glue workflows and which editor style swung the vote",
     "kestra prefect yaml ui editor analyst python class glue survey"),
    # --- 35 ---
    ("Prefer Step Functions over a standing Temporal cluster for the infrequent account-closure workflow; the pay-per-transition pricing model wins when you're running tens of executions a day, not thousands.", "preference", "technical", False,
     [("Step Functions", "service"), ("Temporal", "framework"), ("account-closure", "pattern")],
     [("Step Functions", "Temporal", "PREFERS")],
     "for infrequent workflows which AWS service beats a standing Temporal cluster on cost",
     "step function temporal account closure pay transition pricing infrequent"),
    # --- 36 ---
    ("Prefer Argo Workflows when everything is already a container and the team owns a Kubernetes cluster; spinning up Airflow just to orchestrate pods doubles the ops surface for no benefit.", "preference", "technical", False,
     [("Argo Workflows", "tool"), ("Airflow", "tool"), ("Kubernetes", "platform")],
     [("Argo Workflows", "Airflow", "PREFERS")],
     "when the team already owns Kubernetes which orchestrator beats Airflow on ops surface",
     "argo workflow airflow kubernetes container ops surface team cluster"),
    # --- 37 ---
    ("The preference for typed pipelines landed Flyte on the ML platform roadmap; Kubeflow's weak typing on input artifacts kept leaking schema drift into production training runs.", "preference", "technical", False,
     [("Flyte", "tool"), ("Kubeflow", "tool"), ("typed pipelines", "pattern"), ("schema drift", "pattern")],
     [("Flyte", "Kubeflow", "PREFERS")],
     "which orchestrator got onto the ML platform roadmap for typed pipelines and why",
     "flyte kubeflow typed pipeline schema drift artifact input ml platform"),
    # --- 38 ---
    ("DAG parse time on the big monorepo is 2.4 seconds after turning on dag_discovery_safe_mode and pinning the dag_file_processor_timeout to 30s; the scheduler used to OOM under a Python import storm.", "problem", "technical", False,
     [("dag_discovery_safe_mode", "config"), ("dag_file_processor_timeout", "config"), ("scheduler", "service")],
     [],
     "which Airflow parse-config knobs stopped the scheduler OOM during Python import storms",
     "dag discovery safe mode file processor timeout parse scheduler oom"),
    # --- 39 ---
    ("The Celery broker is Redis with a dedicated sentinel tier; RabbitMQ ran the fleet for a year but the unacked-message pileup during worker restarts kept burning through the backlog budget.", "decision", "technical", False,
     [("Redis", "database"), ("RabbitMQ", "service"), ("Celery broker", "service"), ("sentinel", "pattern")],
     [("Redis", "RabbitMQ", "REPLACES"), ("Celery broker", "Redis", "USES")],
     "which Celery broker replaced RabbitMQ after unacked-message pileups during worker restarts",
     "redis rabbitmq celery broker sentinel unacked restart worker backlog"),
    # --- 40 ---
    ("Airflow secrets live in AWS Secrets Manager via a SecretsManagerBackend; the old Variables blob in the metadata DB exposed credentials to any read-only analyst with the UI password.", "fact", "technical", False,
     [("AWS Secrets Manager", "service"), ("SecretsManagerBackend", "tool"), ("Variables", "pattern")],
     [("SecretsManagerBackend", "Variables", "REPLACES"), ("SecretsManagerBackend", "AWS Secrets Manager", "USES")],
     "which backend replaced the Airflow Variables blob for credentials and why the old path leaked",
     "secrets manager backend variable airflow credential read only analyst ui"),
    # --- 41 ---
    ("Reference: the Airflow TaskFlow API decorator is @task from airflow.decorators; XCom pushes happen implicitly from the return value, which is why tuple returns fan out into separate keys.", "reference", "technical", False,
     [("TaskFlow API", "api"), ("@task", "api"), ("XCom", "pattern"), ("airflow.decorators", "file")],
     [("TaskFlow API", "XCom", "USES")],
     "which Airflow decorator drives TaskFlow and how does the return value get pushed into XCom",
     "taskflow api task decorator xcom return tuple fan out key airflow"),
    # --- 42 ---
    ("Reference: Dagster's op is the unit of computation and its graph composes ops into a job; asset-decorated functions add lineage metadata on top of the same op runtime.", "reference", "technical", False,
     [("Dagster", "tool"), ("op", "concept"), ("graph", "concept"), ("asset", "concept")],
     [("graph", "op", "HAS_PART"), ("asset", "op", "BUILDS_ON")],
     "which Dagster concepts compose ops into jobs and how do assets layer on top of the op runtime",
     "dagster op graph asset job lineage metadata runtime decorator"),
    # --- 43. noise ---
    ("Someone brought home-made bagels to the Friday standup and the tray was empty before the engineering update started.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Reference: Argo Workflows stores workflow state in etcd via Kubernetes CRDs; that's why a very fat workflow blows past the 1 MiB object size limit and needs artifacts or archiveLogs offloaded to S3.", "reference", "technical", False,
     [("Argo Workflows", "tool"), ("etcd", "database"), ("CRD", "concept"), ("S3", "service"), ("archiveLogs", "config")],
     [("Argo Workflows", "etcd", "USES"), ("archiveLogs", "S3", "DEPLOYED_ON")],
     "why do very fat Argo Workflows hit the 1 MiB limit and which offload targets keep them under it",
     "argo etcd crd kubernetes 1 mib object archive log s3 workflow fat"),
    # --- 45 ---
    ("Reference: Temporal activity timeouts are ScheduleToStart, StartToClose, and ScheduleToClose; skipping StartToClose is the usual cause of a worker that silently hangs a workflow for hours.", "reference", "technical", False,
     [("Temporal", "framework"), ("ScheduleToStart", "config"), ("StartToClose", "config"), ("ScheduleToClose", "config")],
     [],
     "which Temporal activity timeout do people skip and which silent failure mode does that unlock",
     "temporal schedule start close activity timeout worker hang workflow"),
    # --- 46 ---
    ("Reference: Prefect work pools decouple the flow definition from the execution infrastructure; the same flow deployment can target a process pool locally and a Kubernetes pool in staging.", "reference", "technical", False,
     [("Prefect", "framework"), ("work pool", "pattern"), ("process pool", "pattern"), ("Kubernetes", "platform")],
     [("Prefect", "work pool", "USES"), ("work pool", "Kubernetes", "DEPLOYED_ON")],
     "which Prefect primitive lets one flow deployment target a local process pool or a Kubernetes pool",
     "prefect work pool process kubernetes flow deployment staging infrastructure"),
    # --- 47 ---
    ("Reference: Step Functions Map state runs in two modes, Inline and Distributed; Distributed scales past the 40-concurrent-iteration cap and reads iteration inputs from S3 instead of the state input.", "reference", "technical", False,
     [("Step Functions", "service"), ("Map state", "pattern"), ("Distributed", "config"), ("Inline", "config"), ("S3", "service")],
     [("Distributed", "S3", "USES")],
     "which Step Functions Map mode scales past the 40-iteration cap and where does it read iteration inputs",
     "step function map distributed inline 40 concurrent iteration s3 input"),
    # --- 48 ---
    ("The weekly data-quality checks are written as Dagster asset checks co-located with the asset definition; breaking the contract fails the run instead of the analyst finding the gap on Monday morning.", "architecture", "technical", False,
     [("Dagster", "tool"), ("asset checks", "pattern"), ("asset definition", "pattern")],
     [("asset checks", "asset definition", "RELATED_TO")],
     "which Dagster feature co-locates data-quality checks with assets and what happens when a contract breaks",
     "dagster asset check quality contract fail run analyst monday weekly"),
    # --- 49 ---
    ("Migrated from the CeleryExecutor to the KubernetesExecutor for the research team; each task getting a fresh pod eliminated the inter-task state leakage that kept biasing the model-evaluation runs.", "milestone", "technical", False,
     [("CeleryExecutor", "tool"), ("KubernetesExecutor", "tool"), ("pod", "pattern"), ("model-evaluation", "pattern")],
     [("KubernetesExecutor", "CeleryExecutor", "REPLACES")],
     "which executor replaced Celery for the research team and which contamination class did pods fix",
     "kubernetes executor celery research pod state leak model evaluation fresh"),
    # --- 50 ---
    ("Shipped the on-call runbook that correlates Airflow task failures to the underlying Datadog alerts via the dag_id and run_id tags; MTTR on the nightly warehouse dropped from 47 minutes to 12.", "milestone", "technical", False,
     [("Airflow", "tool"), ("Datadog", "service"), ("dag_id", "config"), ("run_id", "config"), ("MTTR", "concept")],
     [("Datadog", "Airflow", "COMMUNICATES_WITH")],
     "which tag-based correlation cut warehouse MTTR from 47 to 12 minutes on the on-call path",
     "airflow datadog dag id run tag mttr warehouse on call runbook correlate"),
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
