"""One-off emitter for shared-base batch-145 — stream processing (Kafka/Flink/Pulsar).

Writes 50 rows to data/v2/shared/batch_145.tmp.jsonl with ids shared-07201..07250.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_145.tmp.jsonl"
ID_OFFSET = 7200

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the order-events pipeline from Apache Kafka 2.8 to Redpanda 23.2; broker RAM dropped by half and the absence of a JVM cut p99 publish latency on the checkout topic.", "decision", "technical", False,
     [("Apache Kafka", "platform"), ("Redpanda", "platform"), ("checkout", "service")],
     [("Redpanda", "Apache Kafka", "REPLACES")],
     "which broker replaced Apache Kafka for the order-events pipeline and what metrics moved",
     "redpanda kafka replace broker ram jvm latency checkout topic"),
    # --- 2 ---
    ("Kafka Streams topology for fraud scoring was split into two sub-topologies; the repartition topic for the keyed join stopped exploding to hundreds of gigabytes after the rebalance tuning.", "problem", "technical", False,
     [("Kafka Streams", "framework"), ("repartition topic", "concept"), ("keyed join", "concept")],
     [("keyed join", "repartition topic", "CAUSES")],
     "why did the fraud-scoring Kafka Streams topology need a sub-topology split and what blew up first",
     "kafka streams topology repartition keyed join fraud rebalance split"),
    # --- 3 ---
    ("Switched the change-data capture layer from Maxwell to Debezium 2.5 with the Postgres pgoutput plugin; schema evolution on nullable columns now flows through without a manual snapshot dance.", "decision", "technical", False,
     [("Maxwell", "tool"), ("Debezium", "tool"), ("pgoutput", "library"), ("Postgres", "database")],
     [("Debezium", "Maxwell", "REPLACES"), ("Debezium", "pgoutput", "USES")],
     "which CDC tool replaced Maxwell and which Postgres plugin handles the logical replication stream",
     "debezium maxwell cdc postgres pgoutput replicate schema evolve plugin"),
    # --- 4 ---
    ("Apache Flink 1.18 drives the sessionization job over clickstream events; event-time watermarks with a five-minute bounded out-of-orderness absorb late arrivals from the mobile SDK without side outputs.", "architecture", "technical", False,
     [("Apache Flink", "framework"), ("event-time watermarks", "concept"), ("clickstream", "concept"), ("mobile SDK", "technology")],
     [("Apache Flink", "event-time watermarks", "USES")],
     "which Flink mechanism absorbs late mobile clickstream events without falling back to side outputs",
     "flink sessionize event time watermark late mobile clickstream bound"),
    # --- 5 ---
    ("Exactly-once semantics on the payments sink were flaky under Flink checkpoint failures; pinning transaction.timeout.ms above the checkpoint interval and shortening the commit phase finally stabilised the two-phase commit.", "problem", "technical", False,
     [("Flink", "framework"), ("transaction.timeout.ms", "config"), ("two-phase commit", "algorithm")],
     [("transaction.timeout.ms", "two-phase commit", "CONFIGURES")],
     "which config knob stabilised Flink's two-phase commit sink after checkpoint failures broke exactly-once",
     "flink checkpoint exactly once payment transaction timeout two phase"),
    # --- 6 ---
    ("Spark Structured Streaming batches at a one-second micro-batch over the ad-impressions Kafka topic; we preferred it over continuous processing mode after seeing maturity gaps in the 3.5 branch.", "decision", "technical", False,
     [("Spark Structured Streaming", "framework"), ("continuous processing", "concept"), ("ad-impressions", "concept")],
     [("Spark Structured Streaming", "continuous processing", "PREFERS")],
     "which Spark streaming mode won for ad-impressions and why was continuous processing rejected",
     "spark structured streaming micro batch continuous ad impression kafka"),
    # --- 7 ---
    ("Confluent Schema Registry is now the single source of truth for Avro schemas across the data platform; producers resolve subject compatibility in BACKWARD_TRANSITIVE mode before publishing to the broker.", "architecture", "technical", False,
     [("Confluent Schema Registry", "service"), ("Avro", "technology"), ("BACKWARD_TRANSITIVE", "config")],
     [("Confluent Schema Registry", "Avro", "USES")],
     "which compatibility mode guards Avro producers against breaking consumer deserialisation",
     "confluent schema registry avro backward transitive compatibility producer"),
    # --- 8 ---
    ("Adopted Protobuf over Avro for the telemetry topic after the .proto schemas plugged cleanly into the existing gRPC service definitions and the cross-language code generation story was less painful.", "decision", "technical", False,
     [("Protobuf", "technology"), ("Avro", "technology"), ("gRPC", "protocol"), ("telemetry", "service")],
     [("Protobuf", "Avro", "PREFERS"), ("Protobuf", "gRPC", "RELATED_TO")],
     "why did the telemetry topic pick Protobuf over Avro for its wire format",
     "protobuf avro telemetry grpc schema code generation cross language"),
    # --- 9 ---
    ("Consumer group rebalances on the analytics-enrichment service were stalling for ninety seconds; switching to the cooperative-sticky partition assignor dropped stop-the-world rebalance time to under five seconds.", "milestone", "technical", False,
     [("Consumer group", "concept"), ("cooperative-sticky", "algorithm"), ("analytics-enrichment", "service")],
     [("cooperative-sticky", "Consumer group", "IMPROVES_ON")],
     "which partition assignor replaced the eager strategy on analytics-enrichment and what stall did it cure",
     "consumer group rebalance cooperative sticky assignor stall analytics"),
    # --- 10. noise ---
    ("The office terrarium lost its tree frog for two days before someone found him behind the server rack drinking condensation off the chiller line.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Kafka Connect runs in distributed mode across three workers for the Debezium source and the S3 sink; dead-letter queue config catches malformed records without halting the whole connector.", "fact", "technical", False,
     [("Kafka Connect", "framework"), ("Debezium", "tool"), ("S3 sink", "service"), ("dead-letter queue", "pattern")],
     [("Kafka Connect", "Debezium", "USES"), ("Kafka Connect", "dead-letter queue", "USES")],
     "how does Kafka Connect keep the S3 sink connector alive when a poison record lands upstream",
     "kafka connect distributed debezium s3 sink dead letter queue poison"),
    # --- 12 ---
    ("Apache Pulsar replaced RabbitMQ for the notification fan-out; topic-level geo-replication between clusters shipped out of the box without a bolt-on MirrorMaker equivalent.", "decision", "technical", False,
     [("Apache Pulsar", "platform"), ("RabbitMQ", "platform"), ("geo-replication", "concept"), ("MirrorMaker", "tool")],
     [("Apache Pulsar", "RabbitMQ", "REPLACES")],
     "which broker replaced RabbitMQ for notifications and which built-in feature sealed the decision",
     "pulsar rabbitmq replace notification geo replication mirrormaker fanout"),
    # --- 13 ---
    ("RocksDB backs every Kafka Streams state store on the risk-scoring service; block-cache tuning to four gigabytes and bloom-filter bits per key at ten dropped p99 state lookups under the SLA.", "architecture", "technical", False,
     [("RocksDB", "database"), ("Kafka Streams", "framework"), ("risk-scoring", "service"), ("bloom-filter", "concept")],
     [("Kafka Streams", "RocksDB", "USES")],
     "which storage engine backs Kafka Streams state stores and which tuning knobs met the p99 SLA",
     "rocksdb kafka streams state store block cache bloom filter risk"),
    # --- 14 ---
    ("Materialize replaced a Flink SQL prototype for the realtime BI dashboards; the Postgres wire protocol meant Looker and dbt connected without a custom JDBC adapter.", "decision", "technical", False,
     [("Materialize", "platform"), ("Flink SQL", "framework"), ("Postgres wire protocol", "protocol"), ("Looker", "tool"), ("dbt", "tool")],
     [("Materialize", "Flink SQL", "REPLACES"), ("Materialize", "Postgres wire protocol", "USES")],
     "which streaming database displaced Flink SQL for BI and how did Looker connect to it",
     "materialize flink sql postgres wire looker dbt realtime bi dashboard"),
    # --- 15 ---
    ("RisingWave handles the materialised-view workload for the fraud team now; its decoupled storage-compute split on S3 lets us scale compute nodes on a spiky ingest pattern without reshuffling state.", "architecture", "technical", False,
     [("RisingWave", "platform"), ("S3", "service"), ("compute nodes", "infrastructure"), ("fraud team", "organization")],
     [("RisingWave", "S3", "DEPLOYED_ON")],
     "which streaming database separates storage from compute on S3 and why did that matter for fraud",
     "risingwave materialized view fraud s3 decouple storage compute scale"),
    # --- 16 ---
    ("Compacted topics hold the latest account-state keyed by customer id; log.cleanup.policy=compact with a segment.ms of one hour keeps the snapshot replay cost bounded for new consumers.", "reference", "technical", False,
     [("Compacted topics", "concept"), ("log.cleanup.policy", "config"), ("segment.ms", "config"), ("customer id", "concept")],
     [("log.cleanup.policy", "Compacted topics", "CONFIGURES")],
     "which broker settings keep the account-state compacted topic cheap for new consumer bootstrap",
     "kafka compacted topic cleanup policy segment ms account state snapshot"),
    # --- 17 ---
    ("Offset commit strategy on the billing consumer moved from auto-commit to manual after duplicate charges surfaced; we now commit after the database insert returns and rely on idempotent writes for the replay window.", "reference", "technical", False,
     [("auto-commit", "pattern"), ("manual", "pattern"), ("billing consumer", "service"), ("idempotent writes", "pattern")],
     [("manual", "auto-commit", "REPLACES")],
     "which offset-commit change stopped duplicate billing charges under consumer retries",
     "offset commit auto manual billing duplicate idempotent replay charge"),
    # --- 18 ---
    ("Apache Beam runners now target Dataflow for batch and Flink for streaming; the same pipeline code behind the PCollection API ships to either without a second implementation for each environment.", "architecture", "technical", False,
     [("Apache Beam", "framework"), ("Dataflow", "platform"), ("Flink", "framework"), ("PCollection", "api")],
     [("Apache Beam", "PCollection", "USES"), ("Apache Beam", "Dataflow", "DEPLOYED_ON")],
     "how does the Beam pipeline code target both Dataflow batch and Flink streaming from one source",
     "beam dataflow flink pcollection runner batch streaming portable"),
    # --- 19 ---
    ("Windowing on the ride-hailing surge-pricing job uses tumbling windows of thirty seconds with allowed lateness of two minutes; sliding windows were tried first but dropped due to state-size blow-up.", "decision", "technical", False,
     [("tumbling windows", "pattern"), ("sliding windows", "pattern"), ("surge-pricing", "service"), ("allowed lateness", "config")],
     [("tumbling windows", "sliding windows", "REPLACES")],
     "which window type replaced sliding windows on the surge-pricing job and why",
     "tumbling sliding window surge pricing lateness state size ride hail"),
    # --- 20 ---
    ("Watermark generation on the IoT telemetry pipeline uses a bounded-out-of-orderness strategy per source partition; per-key watermarks got rejected after testing showed it stalled the full pipeline on one noisy sensor.", "fact", "technical", False,
     [("Watermark", "concept"), ("bounded-out-of-orderness", "algorithm"), ("IoT telemetry", "service"), ("per-key watermarks", "pattern")],
     [("bounded-out-of-orderness", "per-key watermarks", "REPLACES")],
     "which watermark strategy was chosen for IoT telemetry after per-key watermarks stalled on noisy sensors",
     "watermark bounded out of orderness per key iot telemetry stall sensor"),
    # --- 21 ---
    ("KRaft mode replaced ZooKeeper on the new Kafka 3.7 clusters; controller failover time dropped from tens of seconds to under two and the ZooKeeper ensemble team finally got retired from the on-call rota.", "milestone", "technical", False,
     [("KRaft", "protocol"), ("ZooKeeper", "service"), ("Kafka 3.7", "platform")],
     [("KRaft", "ZooKeeper", "REPLACES")],
     "which consensus protocol replaced ZooKeeper on Kafka 3.7 and how did failover time move",
     "kraft zookeeper kafka controller failover on call retire consensus"),
    # --- 22 ---
    ("Tiered storage on Confluent Cloud ships cold segments to object storage after seven days; the broker local disk footprint on the audit-log topic shrank from forty to under six terabytes.", "milestone", "technical", False,
     [("Tiered storage", "pattern"), ("Confluent Cloud", "platform"), ("object storage", "infrastructure"), ("audit-log", "service")],
     [("Confluent Cloud", "Tiered storage", "USES")],
     "which Confluent Cloud feature shrank the audit-log broker footprint and by how much",
     "tiered storage confluent cloud object audit log broker disk shrink"),
    # --- 23 ---
    ("ksqlDB was evaluated and rejected for the user-activity aggregation; query planner opacity and limited UDF hot-reload pushed us back to plain Kafka Streams with handwritten topologies.", "decision", "technical", False,
     [("ksqlDB", "platform"), ("Kafka Streams", "framework"), ("user-activity aggregation", "service"), ("UDF", "concept")],
     [("Kafka Streams", "ksqlDB", "PREFERS")],
     "why did the user-activity aggregation reject ksqlDB in favour of plain Kafka Streams",
     "ksqldb kafka streams udf hot reload planner opacity aggregation reject"),
    # --- 24 ---
    ("Pulsar Functions power the enrichment step between the raw-events topic and the cleaned-events topic; stateless mode with no key_shared subscription made horizontal scaling trivial per partition.", "architecture", "technical", False,
     [("Pulsar Functions", "framework"), ("raw-events", "concept"), ("cleaned-events", "concept"), ("key_shared", "config")],
     [("Pulsar Functions", "cleaned-events", "PRODUCES")],
     "which Pulsar abstraction handles the raw-to-cleaned enrichment and what subscription mode was chosen",
     "pulsar function enrichment raw cleaned key shared stateless horizontal"),
    # --- 25 ---
    ("Apache NiFi was retired in favour of Kafka Connect plus Debezium for the CDC backbone; the visual dataflow was pleasant but cluster state migrations during upgrades kept biting us.", "milestone", "technical", False,
     [("Apache NiFi", "tool"), ("Kafka Connect", "framework"), ("Debezium", "tool")],
     [("Kafka Connect", "Apache NiFi", "REPLACES")],
     "which stack replaced Apache NiFi for the CDC backbone and what upgrade pain drove the move",
     "nifi kafka connect debezium cdc retire upgrade cluster state migration"),
    # --- 26 ---
    ("Idempotent producer is on by default across every Kafka client in the payments domain; enable.idempotence=true combined with acks=all is the baseline for any topic touching money.", "preference", "technical", False,
     [("Idempotent producer", "pattern"), ("enable.idempotence", "config"), ("acks", "config"), ("payments", "service")],
     [("enable.idempotence", "Idempotent producer", "CONFIGURES")],
     "which producer defaults are mandatory on any Kafka topic in the payments domain",
     "idempotent producer enable idempotence acks all payment default baseline"),
    # --- 27 ---
    ("Partition count on the user-events topic was bumped from 32 to 128 to absorb the Black Friday spike; we burned a weekend adjusting consumer group sizing and state-store rebalance windows afterwards.", "milestone", "technical", False,
     [("Partition count", "concept"), ("user-events", "service"), ("Black Friday", "event")],
     [("Black Friday", "Partition count", "CAUSES")],
     "why was the user-events partition count quadrupled and what ripple effects followed",
     "partition count user events black friday bump consumer rebalance window"),
    # --- 28 ---
    ("Min.insync.replicas=2 combined with replication.factor=3 is the durability floor for production topics; anything below that gets blocked at the topic-creation admission controller.", "reference", "technical", False,
     [("Min.insync.replicas", "config"), ("replication.factor", "config"), ("admission controller", "service")],
     [("admission controller", "Min.insync.replicas", "IMPLEMENTS")],
     "which two broker settings form the durability floor enforced at topic creation",
     "min insync replicas replication factor admission controller durability"),
    # --- 29 ---
    ("Schema Registry subjects follow the record-name strategy rather than topic-name so multiple event types can share a topic; the ingest team prefers topic-per-entity but the analytics feed needs envelope events.", "preference", "technical", False,
     [("Schema Registry", "service"), ("record-name strategy", "pattern"), ("topic-name", "pattern"), ("analytics feed", "service")],
     [("Schema Registry", "record-name strategy", "USES")],
     "which subject naming strategy does Schema Registry use to let multiple event types share a topic",
     "schema registry subject record name strategy topic envelope event"),
    # --- 30 ---
    ("Flink savepoint on the risk pipeline is taken before every deploy and uploaded to S3; restore from savepoint lets us roll back a bad topology in under four minutes without reprocessing weeks of state.", "architecture", "technical", False,
     [("Flink savepoint", "pattern"), ("S3", "service"), ("risk pipeline", "service")],
     [("Flink savepoint", "S3", "DEPLOYED_ON")],
     "which Flink mechanism underwrites the four-minute rollback for the risk pipeline during deploys",
     "flink savepoint s3 rollback deploy risk pipeline restore topology"),
    # --- 31 ---
    ("Consumer lag alerting on Burrow flagged the recommendations pipeline when lag crossed ten thousand messages; we tuned the evaluation interval down to fifteen seconds for the priority topics.", "fact", "technical", False,
     [("Burrow", "tool"), ("recommendations pipeline", "service"), ("Consumer lag", "concept")],
     [("Burrow", "Consumer lag", "SUPPORTS")],
     "which tool flags consumer lag on the recommendations pipeline and at what threshold",
     "burrow consumer lag recommendation threshold alert evaluation interval"),
    # --- 32 ---
    ("Processing-time triggers replaced event-time triggers on the near-realtime dashboards; the fifteen-minute refresh spec doesn't need event-time correctness and triggers fire deterministically on wall-clock.", "decision", "technical", False,
     [("Processing-time", "concept"), ("event-time", "concept"), ("near-realtime dashboards", "service")],
     [("Processing-time", "event-time", "REPLACES")],
     "why did the near-realtime dashboards swap event-time triggers for processing-time",
     "processing time event time trigger dashboard realtime fifteen minute"),
    # --- 33 ---
    ("Exactly-once across Kafka Connect sinks is best-effort only for non-transactional sinks; we document that the S3 sink is effectively-once on the data-platform runbook and dedupe downstream in Snowflake.", "reference", "technical", False,
     [("Kafka Connect", "framework"), ("S3 sink", "service"), ("Snowflake", "database"), ("data-platform runbook", "file")],
     [("Snowflake", "S3 sink", "SUPPORTS")],
     "which runbook covers the S3 sink effectively-once caveat and where does dedupe actually happen",
     "kafka connect exactly once s3 sink effectively snowflake dedupe runbook"),
    # --- 34 ---
    ("Dead-letter topic format includes the original payload, the source topic, the partition, the offset, and the exception stack trace; reprocessing tools read the envelope and can retry the original.", "reference", "technical", False,
     [("Dead-letter topic", "concept"), ("payload", "concept"), ("exception stack trace", "concept"), ("reprocessing tools", "tool")],
     [("reprocessing tools", "Dead-letter topic", "USES")],
     "which fields does the dead-letter topic envelope carry for reprocessing tools to retry",
     "dead letter topic envelope payload partition offset stack trace retry"),
    # --- 35 ---
    ("Kafka cluster on AWS MSK Serverless is provisioned per business domain with a shared Schema Registry; multi-tenant clusters were rejected after noisy-neighbour traffic from the ops-events domain took down a broker.", "decision", "technical", False,
     [("AWS MSK Serverless", "platform"), ("Schema Registry", "service"), ("ops-events", "service"), ("multi-tenant", "pattern")],
     [("AWS MSK Serverless", "multi-tenant", "REPLACES")],
     "why did MSK Serverless move to per-domain clusters after noisy-neighbour traffic caused broker outages",
     "msk serverless schema registry ops events multi tenant noisy neighbour"),
    # --- 36 ---
    ("Debezium CDC to the data lake writes to an iceberg-formatted S3 bucket via Kafka Connect; we run a compaction job every six hours to keep small files out of the Trino query path.", "preference", "technical", False,
     [("Debezium", "tool"), ("iceberg", "technology"), ("S3", "service"), ("Kafka Connect", "framework"), ("Trino", "tool")],
     [("Debezium", "iceberg", "PRODUCES"), ("Trino", "iceberg", "USES")],
     "how does CDC land in the lake via Debezium and what keeps Trino query latency down afterwards",
     "debezium iceberg s3 kafka connect compaction trino small file"),
    # --- 37 ---
    ("Transactional outbox pattern handles the write-then-publish consistency problem on the orders service; a Debezium connector tails the outbox table and routes envelope rows to per-event topics.", "architecture", "technical", False,
     [("Transactional outbox", "pattern"), ("orders service", "service"), ("Debezium", "tool"), ("outbox table", "concept")],
     [("Debezium", "outbox table", "USES"), ("Transactional outbox", "orders service", "APPLIES_TO")],
     "which pattern solves write-then-publish on orders and how does Debezium route outbox rows to topics",
     "transactional outbox order service debezium envelope per event topic"),
    # --- 38 ---
    ("Redpanda Console replaced AKHQ for operator UX across the clusters; the UI's built-in Schema Registry integration and per-topic ACL view sped up customer-support escalations.", "decision", "technical", False,
     [("Redpanda Console", "tool"), ("AKHQ", "tool"), ("Schema Registry", "service"), ("ACL", "concept")],
     [("Redpanda Console", "AKHQ", "REPLACES")],
     "which operator UI replaced AKHQ and what features sped up support escalations",
     "redpanda console akhq operator ui schema registry acl support escalation"),
    # --- 39 ---
    ("Stream-table join on the enrichment topology keys the stream by account-id and looks up against a compacted account-state topic; stream-stream joins over windowed data were tried first but blew the state store.", "reference", "technical", False,
     [("Stream-table join", "pattern"), ("enrichment topology", "concept"), ("account-state", "concept"), ("stream-stream joins", "pattern")],
     [("Stream-table join", "stream-stream joins", "REPLACES")],
     "which join type replaced stream-stream on the enrichment topology after state-store blow-up",
     "stream table join enrichment account state window stream state blow"),
    # --- 40 ---
    ("Protobuf schema for the order-created event is frozen at v3; adding fields uses optional semantics only and the breaking-change policy is documented in the data-contracts wiki.", "fact", "technical", False,
     [("Protobuf", "technology"), ("order-created", "event"), ("data-contracts wiki", "file")],
     [("data-contracts wiki", "Protobuf", "SUPPORTS")],
     "which schema version is frozen on the order-created event and where is the evolution policy documented",
     "protobuf order created v3 optional breaking change data contract wiki"),
    # --- 41 ---
    ("Flink operator on Kubernetes replaced the YARN-hosted deployment in the old Hadoop cluster; savepoint lifecycle, rolling upgrades, and HA via the config map landed cleanly without custom shell scripts.", "milestone", "technical", False,
     [("Flink operator", "tool"), ("Kubernetes", "platform"), ("YARN", "platform"), ("Hadoop cluster", "infrastructure")],
     [("Flink operator", "YARN", "REPLACES"), ("Flink operator", "Kubernetes", "DEPLOYED_ON")],
     "which runtime displaced YARN for Flink jobs and what operational concerns did the operator handle",
     "flink operator kubernetes yarn hadoop savepoint rolling upgrade ha"),
    # --- 42 ---
    ("Kafka rack-awareness across three AZs is configured with broker.rack=<az-id>; replica placement now spreads across zones and a single-AZ outage stopped taking down the user-events topic last week.", "milestone", "technical", False,
     [("rack-awareness", "concept"), ("broker.rack", "config"), ("user-events", "service"), ("single-AZ outage", "event")],
     [("broker.rack", "rack-awareness", "CONFIGURES")],
     "which broker config enables rack-awareness and what outage scenario did it resolve last week",
     "kafka rack awareness broker rack az user events outage replica"),
    # --- 43. noise ---
    ("The coffee machine in the devops room finally gave up and now brews only the espresso setting regardless of which button anyone presses.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Pulsar Functions with effectively-once delivery guarantees handle the deduplication for idempotency keys; message ids plus the ledger cursor give us the replay safety Kafka's transactional API costs more to run.", "fact", "technical", False,
     [("Pulsar Functions", "framework"), ("effectively-once", "concept"), ("idempotency keys", "concept"), ("ledger cursor", "concept")],
     [("Pulsar Functions", "effectively-once", "SUPPORTS")],
     "how do Pulsar Functions deliver effectively-once and what replaces Kafka's transactional API overhead",
     "pulsar function effectively once idempotency ledger cursor replay dedupe"),
    # --- 45 ---
    ("Materialized view refresh in RisingWave updates incrementally on each upstream event; we prefer it over a nightly Airflow batch rebuild because the BI team expects sub-minute freshness on dashboards.", "preference", "technical", False,
     [("RisingWave", "platform"), ("Airflow", "tool"), ("BI team", "organization"), ("Materialized view", "concept")],
     [("RisingWave", "Airflow", "PREFERS")],
     "why is RisingWave preferred over an Airflow nightly rebuild for the BI team's dashboards",
     "risingwave airflow bi team materialized view freshness nightly batch"),
    # --- 46 ---
    ("UnknownTopicOrPartitionException kept surfacing on the new fraud topic right after creation; the auto-create race between the admin client and the producer was fixed by pre-provisioning topics via Terraform.", "problem", "technical", False,
     [("UnknownTopicOrPartitionException", "error"), ("fraud topic", "service"), ("admin client", "service"), ("Terraform", "tool")],
     [("Terraform", "UnknownTopicOrPartitionException", "FIXES")],
     "which workflow eliminated the UnknownTopicOrPartitionException race on the fraud topic at creation",
     "unknown topic partition exception fraud admin client terraform race"),
    # --- 47 ---
    ("Serde choice in Kafka Streams is wired at the topology level via Serdes.String and a custom AvroSerde; leaving Serdes to the DSL default byte[] caused deserialisation errors buried deep in the topology graph.", "fact", "technical", False,
     [("Kafka Streams", "framework"), ("Serdes.String", "api"), ("AvroSerde", "library"), ("byte[]", "concept")],
     [("AvroSerde", "byte[]", "REPLACES")],
     "why did the Kafka Streams topology move off the DSL default byte[] Serde to explicit AvroSerde",
     "kafka streams serde avro byte array dsl default deserialisation error"),
    # --- 48 ---
    ("Reprocessing the last thirty days of events is done by resetting the consumer group offset to a timestamp via kafka-consumer-groups.sh; the offsets-by-time API made the old earliest-then-seek dance obsolete.", "fact", "technical", False,
     [("kafka-consumer-groups.sh", "command"), ("consumer group", "concept"), ("offsets-by-time", "api")],
     [("kafka-consumer-groups.sh", "offsets-by-time", "USES")],
     "which CLI command drives thirty-day reprocessing and which API replaced the earliest-then-seek workflow",
     "kafka consumer groups script offset timestamp reprocess earliest seek"),
    # --- 49 ---
    ("End-to-end encryption on the PII topic uses a Kafka Connect SMT that encrypts sensitive fields against a Vault-managed key before the record leaves the producer; brokers never see plaintext.", "architecture", "technical", False,
     [("Kafka Connect SMT", "pattern"), ("PII topic", "service"), ("Vault", "tool"), ("brokers", "infrastructure")],
     [("Kafka Connect SMT", "Vault", "USES")],
     "how does the PII topic keep plaintext away from brokers and which tool holds the key",
     "kafka connect smt pii vault encrypt field producer broker plaintext"),
    # --- 50 ---
    ("Hybrid batch-streaming lambda architecture was retired in favour of a pure streaming kappa architecture on Flink; the duplicated business logic between the batch and speed layers was the real operational tax.", "decision", "technical", False,
     [("lambda architecture", "pattern"), ("kappa architecture", "pattern"), ("Flink", "framework"), ("batch", "concept"), ("speed layers", "concept")],
     [("kappa architecture", "lambda architecture", "REPLACES")],
     "which streaming architecture replaced the lambda split and what cost drove the consolidation",
     "lambda kappa architecture flink batch speed layer duplicate logic"),
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
