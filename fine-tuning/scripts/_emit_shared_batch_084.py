"""One-off emitter for shared-base batch-084 — technical domain (workflow orchestration / durable execution).

Writes 50 rows to data/v2/shared/batch_084.tmp.jsonl with ids shared-04151..04200.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_084.tmp.jsonl"
ID_OFFSET = 4150

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Apache Airflow scheduled the nightly ETL across 600 DAGs; the LocalExecutor was swapped for the CeleryExecutor once parallel task counts crossed 200.", "architecture", "technical", False,
     [("Apache Airflow", "framework"), ("LocalExecutor", "tool"), ("CeleryExecutor", "tool")],
     [("CeleryExecutor", "LocalExecutor", "REPLACES")],
     "which executor took over from LocalExecutor once parallelism crossed 200",
     "Airflow executor swap parallel task count nightly ETL"),
    # --- 2 ---
    ("Prefect 2 replaced Airflow for the dynamically shaped feature pipelines; flow-level mapping handled fan-out without the DAG-recompile dance.", "decision", "technical", False,
     [("Prefect 2", "framework"), ("Airflow", "framework")],
     [("Prefect 2", "Airflow", "REPLACES")],
     "which orchestrator displaced Airflow on the dynamic feature pipelines",
     "Prefect Airflow dynamic mapping fan out flow recompile"),
    # --- 3 ---
    ("Dagster improves on Airflow for the analytics warehouse; software-defined assets made lineage explicit instead of hidden inside operator code.", "decision", "technical", False,
     [("Dagster", "framework"), ("Airflow", "framework")],
     [("Dagster", "Airflow", "IMPROVES_ON")],
     "which orchestrator framework gave first-class assets over operator code",
     "Dagster software defined asset lineage warehouse explicit"),
    # --- 4 ---
    ("Argo Workflows replaced a homegrown Jenkins-as-pipeline rig on the Kubernetes cluster; native pod templates removed a 4000-line Groovy library.", "decision", "technical", False,
     [("Argo Workflows", "framework"), ("Jenkins", "tool"), ("Kubernetes", "platform"), ("Groovy", "language")],
     [("Argo Workflows", "Jenkins", "REPLACES")],
     "which orchestrator displaced the Jenkins-as-pipeline Groovy mess on K8s",
     "Argo Workflows Jenkins pipeline Kubernetes pod template swap"),
    # --- 5 ---
    ("Temporal replaced Cadence on the payments service; the SDK ergonomics for Go and the open governance won over the inherited Uber fork.", "decision", "technical", False,
     [("Temporal", "framework"), ("Cadence", "framework"), ("Go", "language"), ("Uber", "organization")],
     [("Temporal", "Cadence", "REPLACES")],
     "which durable execution engine took over from the Cadence fork",
     "Temporal Cadence Go SDK governance fork swap payments"),
    # --- 6 ---
    ("AWS Step Functions Express workflows replaced Standard for the order webhook fan-out; sub-second billing and at-least-once semantics fit the path.", "decision", "technical", False,
     [("AWS Step Functions", "service")],
     [],
     "which Step Functions tier displaced Standard on the webhook fan-out",
     "Step Functions Express Standard sub second billing webhook"),
    # --- 7 ---
    ("Google Cloud Workflows handled the cross-service orchestration for the invoice run; the YAML DSL beat a homegrown FastAPI saga coordinator.", "decision", "technical", False,
     [("Google Cloud Workflows", "service"), ("FastAPI", "framework")],
     [("Google Cloud Workflows", "FastAPI", "REPLACES")],
     "which managed orchestrator absorbed the homegrown saga coordinator",
     "Cloud Workflows YAML saga coordinator invoice run cross"),
    # --- 8 ---
    ("Kestra was preferred over Airflow for the Java-heavy team; the YAML-first declarative flows and built-in plugin marketplace lowered the Python tax.", "preference", "technical", False,
     [("Kestra", "framework"), ("Airflow", "framework"), ("Java", "language"), ("Python", "language"), ("YAML", "language")],
     [("Kestra", "Airflow", "PREFERS")],
     "which orchestrator the Java-heavy team picked over Airflow",
     "Kestra YAML declarative plugin marketplace Java team Python"),
    # --- 9 ---
    ("Luigi remained on the legacy Hadoop pipelines; Spotify's original target-based dependency model still fit the file-checkpointing batch jobs.", "fact", "technical", False,
     [("Luigi", "framework"), ("Hadoop", "platform"), ("Spotify", "organization")],
     [],
     "which legacy orchestrator stayed on the Hadoop file-checkpoint batches",
     "Luigi Hadoop target dependency Spotify legacy batch keep"),
    # --- 10. noise ---
    ("Hold on, the scheduler heartbeat just paused.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Flyte powered the ML training DAGs on the data platform; strongly typed task signatures plus container caching beat what Airflow KubernetesPodOperator gave us.", "architecture", "technical", False,
     [("Flyte", "framework"), ("Airflow", "framework"), ("KubernetesPodOperator", "tool")],
     [("Flyte", "Airflow", "REPLACES")],
     "which orchestrator ran the typed ML training DAGs on the data platform",
     "Flyte typed task signature container cache ML training pod"),
    # --- 12 ---
    ("Durable execution semantics in Temporal made the booking saga crash-safe; replays from the event history rebuilt local state without idempotency keys in user code.", "architecture", "technical", False,
     [("Temporal", "framework")],
     [],
     "which durable execution model made the booking saga crash-safe",
     "Temporal replay event history local state idempotency saga"),
    # --- 13 ---
    ("Idempotency at the orchestrator level let Step Functions safely retry the Stripe charge task; the integration token replaced a per-task UUID dance in the handler.", "decision", "technical", False,
     [("Step Functions", "service"), ("Stripe", "service"), ("UUID", "concept")],
     [],
     "which orchestrator feature absorbed the per-task UUID idempotency dance",
     "Step Functions integration token idempotency Stripe charge"),
    # --- 14 ---
    ("DAG scheduling in Airflow moved off the every-minute parser scan; the new DAG processor with serialized DAGs cut scheduler CPU by 70 percent.", "milestone", "technical", False,
     [("Airflow", "framework"), ("DAG processor", "tool")],
     [],
     "which Airflow change cut scheduler CPU by 70 percent on DAG scans",
     "Airflow scheduler DAG processor serialized parser CPU cut"),
    # --- 15 ---
    ("S3 sensors in Airflow polled the inbound bucket every 30 seconds; the deferrable variant with the triggerer freed a worker slot per sensor.", "decision", "technical", False,
     [("Airflow", "framework"), ("S3", "service"), ("triggerer", "tool")],
     [],
     "which Airflow sensor change freed a worker slot per S3 poll",
     "S3 sensor deferrable triggerer worker slot poll bucket"),
    # --- 16 ---
    ("Backfill semantics in Airflow replayed the 90-day window over the cleaned event source; --reset-dagruns plus --rerun-failed-tasks was the safe combination.", "reference", "technical", False,
     [("Airflow", "framework")],
     [],
     "which Airflow CLI flag combination is the safe replay recipe",
     "Airflow backfill replay reset dagruns rerun failed safe"),
    # --- 17 ---
    ("KubernetesPodOperator in Airflow ran the heavy Spark submit; per-task isolation with image pinning beat the brittle spark-submit on the worker host.", "architecture", "technical", False,
     [("KubernetesPodOperator", "tool"), ("Airflow", "framework"), ("Spark", "framework"), ("spark-submit", "command")],
     [("KubernetesPodOperator", "spark-submit", "REPLACES")],
     "which Airflow operator displaced spark-submit on the worker host",
     "Kubernetes pod operator Spark submit isolation image pin"),
    # --- 18 ---
    ("BashOperator was rejected for the SFTP sync step; the SFTPOperator gave a typed connection plus retries the bash retry loop never had.", "decision", "technical", False,
     [("BashOperator", "tool"), ("SFTPOperator", "tool"), ("SFTP", "protocol")],
     [("SFTPOperator", "BashOperator", "REPLACES")],
     "which named Airflow operator took over the SFTP sync from BashOperator",
     "BashOperator SFTPOperator typed connection retry sync SFTP"),
    # --- 19 ---
    ("PythonOperator gradually gave way to the TaskFlow API in Airflow 2; the @task decorator made XCom passing implicit and the DAG file half the size.", "decision", "technical", False,
     [("PythonOperator", "tool"), ("TaskFlow API", "api"), ("Airflow 2", "framework"), ("XCom", "concept")],
     [("TaskFlow API", "PythonOperator", "REPLACES")],
     "which Airflow 2 API displaced PythonOperator and shrank the DAG file",
     "TaskFlow API PythonOperator decorator XCom implicit DAG"),
    # --- 20 ---
    ("Task groups in Airflow replaced the SubDagOperator on the per-tenant fan-out; the deadlock-prone child scheduler went away and the UI grouping survived.", "decision", "technical", False,
     [("Airflow", "framework"), ("SubDagOperator", "tool"), ("Task groups", "pattern")],
     [("Task groups", "SubDagOperator", "REPLACES")],
     "which Airflow primitive displaced SubDagOperator for per-tenant fan-out",
     "task group SubDagOperator deadlock child scheduler tenant"),
    # --- 21 ---
    ("Dynamic task mapping in Airflow 2.3 expanded the per-customer extract to 1200 parallel tasks; the upstream list came from a single XCom.", "milestone", "technical", False,
     [("Airflow 2.3", "framework"), ("XCom", "concept")],
     [],
     "which Airflow feature expanded the per-customer extract dynamically",
     "dynamic task map expand XCom per customer parallel extract"),
    # --- 22 ---
    ("XCom replacement landed via the S3 XCom backend; payloads above 48 KB stopped clogging the metadata Postgres and the MySQL row-size cap stopped biting.", "decision", "technical", False,
     [("XCom", "concept"), ("S3", "service"), ("Postgres", "database"), ("MySQL", "database")],
     [],
     "which XCom backend swap kept large payloads out of metadata Postgres",
     "XCom S3 backend metadata database row size cap swap"),
    # --- 23 ---
    ("Resource pools in Airflow capped Snowflake-bound tasks at 12 concurrent slots; the warehouse credit burn fell back into the monthly allowance.", "decision", "technical", False,
     [("Airflow", "framework"), ("Snowflake", "database")],
     [],
     "which Airflow knob capped Snowflake-bound task concurrency",
     "Airflow resource pool Snowflake concurrent slot credit cap"),
    # --- 24 ---
    ("Retry policies at the workflow level in Temporal centralized backoff with maximum_attempts and initial_interval; per-activity ad-hoc retries went away from the worker code.", "decision", "technical", False,
     [("Temporal", "framework")],
     [],
     "which workflow-level Temporal feature centralized retry backoff",
     "Temporal retry policy workflow backoff max attempts central"),
    # --- 25 ---
    ("Argo Workflows retry strategies preferred onFailure with limit 5 and exponential backoff; the per-step exit-code branching the legacy script used was dropped.", "preference", "technical", False,
     [("Argo Workflows", "framework")],
     [],
     "which Argo Workflows retry strategy beat the per-step exit-code branching",
     "Argo retry on failure limit exponential backoff strategy"),
    # --- 26 ---
    ("Sensors and triggers split in Airflow let the triggerer process hold 5000 idle waits in one Python process; deferrable operators dropped the worker slot pin.", "architecture", "technical", False,
     [("Airflow", "framework"), ("triggerer", "tool"), ("Python", "language")],
     [],
     "which Airflow component holds thousands of idle waits in one process",
     "triggerer deferrable operator idle wait worker slot pin"),
    # --- 27 ---
    ("Prefect's work pools replaced the agent-per-deployment model; a single pool scheduled work to ephemeral Kubernetes jobs without long-running pollers.", "decision", "technical", False,
     [("Prefect", "framework"), ("Kubernetes", "platform")],
     [],
     "which Prefect change displaced the per-deployment agent model",
     "Prefect work pool agent per deployment ephemeral Kubernetes"),
    # --- 28 ---
    ("Dagster sensors fired the materialization on a new partition arriving in the lake; the cron schedule on the asset got dropped after the sensor went green for two weeks.", "decision", "technical", False,
     [("Dagster", "framework")],
     [],
     "which Dagster trigger replaced the cron schedule on the lake asset",
     "Dagster sensor materialization partition cron drop asset"),
    # --- 29 ---
    ("Cloud Composer 2 hosted Airflow on GKE Autopilot; Google's managed scheduler lifted the Postgres metadata DB and reverse-proxy headache off the team.", "architecture", "technical", False,
     [("Cloud Composer 2", "service"), ("Airflow", "framework"), ("GKE Autopilot", "service"), ("Postgres", "database")],
     [],
     "which managed Airflow service took the metadata DB headache off the team",
     "Cloud Composer Airflow GKE Autopilot Postgres metadata host"),
    # --- 30 ---
    ("MWAA on AWS was rejected for the heavy DAGs; the per-environment vCPU cap and the locked-down requirements.txt path made the team self-host on EKS instead.", "decision", "technical", False,
     [("MWAA", "service"), ("AWS", "organization"), ("EKS", "service")],
     [("EKS", "MWAA", "REPLACES")],
     "which AWS managed Airflow option got rejected and what replaced it",
     "MWAA AWS vCPU cap requirements path self host EKS swap"),
    # --- 31 ---
    ("Airflow's CeleryKubernetesExecutor split short tasks onto Celery workers and heavy Spark tasks onto pods; the hybrid beat picking one executor for everything.", "architecture", "technical", False,
     [("Airflow", "framework"), ("CeleryKubernetesExecutor", "tool"), ("Celery", "framework"), ("Spark", "framework")],
     [],
     "which Airflow executor mix split short Celery tasks from heavy pod tasks",
     "CeleryKubernetesExecutor hybrid Celery worker Spark pod split"),
    # --- 32 ---
    ("Workflow versioning in Temporal used GetVersion gates around the changed branch; running executions kept replaying the old branch deterministically.", "reference", "technical", False,
     [("Temporal", "framework"), ("GetVersion", "method")],
     [],
     "which Temporal API gates a deterministic workflow code change",
     "Temporal GetVersion versioning branch deterministic replay"),
    # --- 33 ---
    ("Cadence remained on the older risk service; the migration to Temporal was deferred until the running 90-day workflows drained naturally.", "fact", "technical", False,
     [("Cadence", "framework"), ("Temporal", "framework")],
     [],
     "which legacy durable engine stayed until the long workflows drained",
     "Cadence Temporal risk service drain ninety day defer"),
    # --- 34. noise ---
    ("Hang on, kicking the worker pod and rerunning.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Step Functions Map state replaced the homegrown SQS-fanout-plus-aggregator on the bulk import; the parallel branches with maxConcurrency capped DynamoDB write cost.", "decision", "technical", False,
     [("Step Functions", "service"), ("SQS", "service"), ("DynamoDB", "database")],
     [("Step Functions", "SQS", "REPLACES")],
     "which Step Functions state displaced the SQS-fanout-plus-aggregator hack",
     "Step Functions Map state SQS fan out aggregator DynamoDB cap"),
    # --- 36 ---
    ("Argo Events fired Argo Workflows on a Kafka topic message; the EventSource plus Sensor pair beat a CronWorkflow polling Kafka offsets every minute.", "decision", "technical", False,
     [("Argo Events", "framework"), ("Argo Workflows", "framework"), ("Kafka", "service"), ("CronWorkflow", "tool")],
     [("Argo Events", "CronWorkflow", "REPLACES")],
     "which Argo combo displaced the CronWorkflow polling Kafka offsets",
     "Argo Events Sensor Kafka topic EventSource CronWorkflow swap"),
    # --- 37 ---
    ("Flyte's strongly typed dataclass inputs caught a schema drift before the run started; Airflow's untyped XCom would have surfaced the same bug three hours in.", "fact", "technical", False,
     [("Flyte", "framework"), ("Airflow", "framework"), ("XCom", "concept")],
     [],
     "which Flyte feature caught a schema drift bug Airflow XCom would miss",
     "Flyte typed dataclass schema drift Airflow XCom untyped catch"),
    # --- 38 ---
    ("Prefect blocks held the Snowflake credentials and the S3 bucket reference; the team stopped baking secrets into the agent environment image.", "decision", "technical", False,
     [("Prefect", "framework"), ("Snowflake", "database"), ("S3", "service")],
     [],
     "which named primitive took over secret handling for the warehouse agent",
     "secret store warehouse agent reference container image swap"),
    # --- 39 ---
    ("Dagster's run queue throttled per-asset materializations to 4 in flight; the warehouse credit graph flattened off its Tuesday spike.", "milestone", "technical", False,
     [("Dagster", "framework")],
     [],
     "which orchestrator knob flattened the midweek warehouse credit graph",
     "concurrency cap asset job midweek bill smoothing weekday"),
    # --- 40 ---
    ("Apache Airflow 2.7 deprecated SubDagOperator officially; new DAGs lint-failed in CI when the import showed up after the migration deadline.", "milestone", "technical", False,
     [("Apache Airflow 2.7", "framework"), ("SubDagOperator", "tool"), ("CI", "infrastructure")],
     [],
     "which Airflow release officially deprecated SubDagOperator",
     "Airflow 2.7 deprecate SubDagOperator lint CI migration"),
    # --- 41 ---
    ("Backfill kicked on 2026-03-30 to refill the customer_event_daily asset across 60 days; Dagster's partitioned asset job let us pick the date range from the UI.", "milestone", "technical", False,
     [("Dagster", "framework"), ("2026-03-30", "date")],
     [],
     "when did the customer_event_daily backfill ship and which tool ran it",
     "backfill customer event daily Dagster partition asset date"),
    # --- 42 ---
    ("Argo Workflows artifact passing replaced shared NFS mounts between steps; S3-backed artifacts plus garbage collection beat the leaky NFS share.", "decision", "technical", False,
     [("Argo Workflows", "framework"), ("NFS", "protocol"), ("S3", "service")],
     [("Argo Workflows", "NFS", "REPLACES")],
     "which Argo feature displaced the shared NFS mount between steps",
     "Argo artifact S3 garbage collection NFS shared mount swap"),
    # --- 43 ---
    ("Temporal's signals drove the manual-approval step on the refund workflow; long-running waits cost nothing because the workflow was unloaded between events.", "architecture", "technical", False,
     [("Temporal", "framework")],
     [],
     "which Temporal mechanism drove the manual-approval step on refunds",
     "Temporal signal manual approval refund unload long wait"),
    # --- 44 ---
    ("Step Functions Standard workflows kept the year-long SLA tracking; the Express tier's 5-minute execution cap ruled it out for the long path.", "fact", "technical", False,
     [("Step Functions", "service")],
     [],
     "which Step Functions tier ran the year-long SLA tracking workflow",
     "Step Functions Standard year SLA Express five minute cap"),
    # --- 45 ---
    ("Cron-based DAG schedules in Airflow gave way to data-aware scheduling with Datasets; the daily marketing DAG fired only after the upstream events landed.", "decision", "technical", False,
     [("Airflow", "framework"), ("Datasets", "concept"), ("Cron", "pattern")],
     [("Datasets", "Cron", "REPLACES")],
     "which Airflow scheduling change replaced cron on the marketing DAG",
     "data aware schedule Dataset cron marketing DAG upstream"),
    # --- 46 ---
    ("Kestra's plugin for BigQuery handled the warehouse load step natively; the Python operator wrapping bq CLI was retired from the YAML flow.", "decision", "technical", False,
     [("Kestra", "framework"), ("BigQuery", "service"), ("Python", "language"), ("bq", "command")],
     [("Kestra", "bq", "REPLACES")],
     "which Kestra plugin displaced the bq CLI Python wrapper for warehouse loads",
     "Kestra plugin BigQuery YAML bq CLI Python wrap retire"),
    # --- 47 ---
    ("Workflow-level retry policy in Cloud Workflows used exponential backoff with max 7 attempts; per-step retry blocks were collapsed into the workflow default.", "decision", "technical", False,
     [("Cloud Workflows", "service")],
     [],
     "which Cloud Workflows pattern collapsed per-step retry blocks",
     "Cloud Workflows workflow retry exponential max attempts default"),
    # --- 48 ---
    ("Airflow's REST API replaced the experimental endpoints in 2.0; the Stable API gave the internal portal a contract that did not break across point releases.", "milestone", "technical", False,
     [("Airflow", "framework"), ("REST API", "api"), ("Stable API", "api"), ("experimental endpoints", "api")],
     [("Stable API", "experimental endpoints", "REPLACES")],
     "which Airflow 2 API surface stabilized the internal portal contract",
     "Airflow REST stable API experimental endpoint portal contract"),
    # --- 49 ---
    ("Workflow as code in Dagster fit the team's Python-first habit better than YAML-heavy Argo Workflows; ops cost dropped because Pull Requests reviewed the same way as services.", "preference", "technical", False,
     [("Dagster", "framework"), ("Argo Workflows", "framework"), ("Python", "language"), ("YAML", "language")],
     [("Dagster", "Argo Workflows", "PREFERS")],
     "which orchestrator fit the Python-first workflow-as-code habit best",
     "Dagster Argo Python YAML workflow as code review PR habit"),
    # --- 50 ---
    ("Idempotency tokens on Step Functions Task states landed across the integrations on 2026-04-02; duplicate StartExecution calls from the upstream API now collapsed safely.", "milestone", "technical", False,
     [("Step Functions", "service"), ("StartExecution", "method"), ("2026-04-02", "date")],
     [],
     "when did Step Functions idempotency tokens roll out across integrations",
     "Step Functions idempotency token StartExecution duplicate date"),
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
