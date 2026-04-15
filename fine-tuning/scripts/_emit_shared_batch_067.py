"""One-off emitter for shared-base batch-067 — technical domain (messaging, queues, streaming).

Writes 50 rows to data/v2/shared/batch_067.tmp.jsonl with ids shared-03301..03350.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_067.tmp.jsonl"
ID_OFFSET = 3300

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Apache Kafka backed the order-events backbone; a 12-partition topic gave the consumer group enough parallelism to keep lag under 200 ms.", "architecture", "technical", False,
     [("Apache Kafka", "technology")],
     [],
     "which broker carried the order-events backbone with 12 partitions",
     "Kafka backbone partition consumer group lag steady"),
    # --- 2 ---
    ("Apache Pulsar replaced Apache Kafka for the multi-tenant SaaS namespace; tiered storage on S3 cut the hot-disk footprint by 80 percent.", "decision", "technical", False,
     [("Apache Pulsar", "technology"), ("Apache Kafka", "technology"), ("S3", "service")],
     [("Apache Pulsar", "Apache Kafka", "REPLACES")],
     "which broker took over from Kafka on the multi-tenant namespace",
     "Pulsar tiered storage tenancy hot disk swap broker"),
    # --- 3 ---
    ("Redpanda improved on Apache Kafka for the trading desk; the Raft-per-partition design dropped tail latency below 5 ms at p99 without a JVM in the path.", "decision", "technical", False,
     [("Redpanda", "technology"), ("Apache Kafka", "technology"), ("Raft", "algorithm"), ("JVM", "technology")],
     [("Redpanda", "Apache Kafka", "IMPROVES_ON")],
     "which Kafka-compatible broker won on tail latency for the trading desk",
     "Redpanda Raft partition tail latency JVM trade desk"),
    # --- 4 ---
    ("NATS JetStream replaced RabbitMQ for the IoT telemetry fan-in; subject-based routing matched the device hierarchy without exchange topology gymnastics.", "decision", "technical", False,
     [("NATS JetStream", "technology"), ("RabbitMQ", "technology")],
     [("NATS JetStream", "RabbitMQ", "REPLACES")],
     "which message system absorbed the IoT telemetry fan-in from RabbitMQ",
     "NATS JetStream subject routing telemetry exchange swap"),
    # --- 5 ---
    ("RabbitMQ stayed on the legacy billing queues; the per-message TTL plus dead-letter exchange combo had no clean equivalent in the new stack.", "fact", "technical", False,
     [("RabbitMQ", "technology")],
     [],
     "which queue platform stayed on the billing path despite the migration",
     "RabbitMQ legacy billing TTL dead letter retain stack"),
    # --- 6 ---
    ("Confluent Schema Registry replaced ad-hoc JSON envelopes on the events topic; producers now fail fast on incompatible Avro changes instead of poisoning consumers.", "decision", "technical", False,
     [("Confluent Schema Registry", "service"), ("JSON", "protocol"), ("Avro", "protocol")],
     [("Confluent Schema Registry", "JSON", "REPLACES")],
     "which schema layer took over from raw JSON envelopes on the events topic",
     "schema registry Avro JSON producer compatibility break"),
    # --- 7 ---
    ("Apicurio Registry was preferred over Confluent Schema Registry for the on-prem cluster; Apache 2.0 licensing cleared the procurement review without legal back-and-forth.", "preference", "technical", False,
     [("Apicurio Registry", "service"), ("Confluent Schema Registry", "service")],
     [("Apicurio Registry", "Confluent Schema Registry", "PREFERS")],
     "which schema registry beat Confluent on the on-prem cluster",
     "Apicurio Apache license procurement on prem registry"),
    # --- 8 ---
    ("Protocol Buffers backed the event payloads after Avro compatibility checks blocked too many releases; field-tag stability gave the team a kinder evolution path.", "decision", "technical", False,
     [("Protocol Buffers", "protocol"), ("Avro", "protocol")],
     [("Protocol Buffers", "Avro", "REPLACES")],
     "which serialization replaced Avro for the event payloads on the topic",
     "protobuf payload evolution field tag stability swap"),
    # --- 9 ---
    ("Exactly-once semantics on Kafka Streams was enabled via processing.guarantee=exactly_once_v2; idempotent producers plus transactional commits closed the duplicate gap on the payments topic.", "architecture", "technical", False,
     [("Kafka Streams", "framework")],
     [],
     "which Kafka Streams setting closed the duplicate gap on payments",
     "exactly once v2 idempotent transactional commit duplicate"),
    # --- 10. noise ---
    ("Hold on, the broker's still rebalancing.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("AWS SQS standard queues backed the email send fan-out; at-least-once with idempotent handlers was cheaper than chasing exactly-once across services.", "architecture", "technical", False,
     [("AWS SQS", "service")],
     [],
     "which AWS queue carried the email fan-out with idempotent handlers",
     "SQS standard at least once idempotent email send fan"),
    # --- 12 ---
    ("AWS SNS plus SQS replaced a self-hosted RabbitMQ topic exchange for the platform events; the fanout cost was lower than running three RabbitMQ nodes.", "decision", "technical", False,
     [("AWS SNS", "service"), ("SQS", "service"), ("RabbitMQ", "technology")],
     [("AWS SNS", "RabbitMQ", "REPLACES")],
     "which AWS combo retired the RabbitMQ topic exchange for platform events",
     "SNS SQS fanout topic exchange self hosted swap cost"),
    # --- 13 ---
    ("SQS FIFO queues were rejected for the order pipeline; the 300 TPS per message-group ceiling did not survive the holiday peak load test.", "decision", "technical", False,
     [("SQS FIFO", "service")],
     [],
     "which SQS variant was rejected because the TPS ceiling failed at peak",
     "FIFO 300 TPS group ceiling holiday peak reject queue"),
    # --- 14 ---
    ("Google Pub/Sub replaced Apache Kafka on the analytics ingest path; managed scale-to-zero billing matched the bursty mobile traffic better than always-on brokers.", "decision", "technical", False,
     [("Google Pub/Sub", "service"), ("Apache Kafka", "technology")],
     [("Google Pub/Sub", "Apache Kafka", "REPLACES")],
     "which managed broker took over Kafka's role on the analytics ingest",
     "Pub Sub scale zero burst mobile broker swap analytics"),
    # --- 15 ---
    ("Pub/Sub Lite was preferred over Pub/Sub for the high-volume log topic; the per-throughput pricing model came in 70 percent cheaper at sustained 200 MB/s.", "preference", "technical", False,
     [("Pub/Sub Lite", "service"), ("Pub/Sub", "service")],
     [("Pub/Sub Lite", "Pub/Sub", "PREFERS")],
     "which Pub/Sub variant won on cost at sustained log throughput",
     "Pub Sub Lite throughput pricing log topic sustained cost"),
    # --- 16 ---
    ("Apache Flink ran the windowed sessionization over the click stream; event-time watermarks plus a 30-minute gap closed sessions cleanly across late-arriving mobile events.", "architecture", "technical", False,
     [("Apache Flink", "framework")],
     [],
     "which streaming engine ran windowed sessionization on click data",
     "Flink event time watermark session window late mobile"),
    # --- 17 ---
    ("Kafka Streams replaced Apache Spark Structured Streaming for the enrichment job; topology-local state stores beat shuffling RDDs on a 50-node cluster.", "decision", "technical", False,
     [("Kafka Streams", "framework"), ("Apache Spark Structured Streaming", "framework")],
     [("Kafka Streams", "Apache Spark Structured Streaming", "REPLACES")],
     "which streaming framework displaced Spark on the enrichment job",
     "Kafka Streams local state store shuffle Spark swap"),
    # --- 18 ---
    ("Consumer-group rebalances stormed the orders topic during deploys; cooperative-sticky assignment dropped pause time from 8 seconds to under 200 ms.", "problem", "technical", False,
     [("cooperative-sticky", "config")],
     [],
     "which assignor cut consumer-group pause time during deploys",
     "rebalance storm cooperative sticky assignor pause deploy"),
    # --- 19 ---
    ("A skewed partition strategy produced a hot key on customer_id 42; switching to murmur2 hashing on a synthetic key spread load across all 24 partitions.", "problem", "technical", False,
     [("murmur2", "algorithm")],
     [],
     "which hashing change defused the hot-partition customer-42 problem",
     "hot key skew partition murmur2 hash spread load fix"),
    # --- 20 ---
    ("Dead-letter topics replaced silent drops on the consumer; poison messages now land in orders.dlq with the original headers preserved for replay tooling.", "decision", "technical", False,
     [("orders.dlq", "config")],
     [],
     "which pattern replaced silent drops for poison messages on the consumer",
     "dead letter topic poison header replay drop pattern"),
    # --- 21 ---
    ("Backpressure on the Flink sink caused checkpoint timeouts against the slow JDBC writer; switching to async I/O with a 1000-deep queue cleared the wait without dropping events.", "problem", "technical", False,
     [("Flink", "framework"), ("JDBC", "protocol")],
     [],
     "which Flink fix cleared the JDBC sink backpressure on checkpoints",
     "backpressure async IO checkpoint JDBC sink queue depth"),
    # --- 22 ---
    ("Apache Pulsar Functions ran lightweight enrichment in-broker; standing up a separate Flink job was overkill for the 10-line lookup transform.", "architecture", "technical", False,
     [("Apache Pulsar Functions", "framework"), ("Flink", "framework")],
     [],
     "which in-broker compute handled the small enrichment without Flink",
     "Pulsar Functions in broker compute enrichment small job"),
    # --- 23 ---
    ("Tiered storage on Confluent Cloud held the 90-day retention window; hot brokers carried only 24 hours, slashing the SSD bill on the audit topic.", "architecture", "technical", False,
     [("Confluent Cloud", "service")],
     [],
     "which Confluent feature held the 90-day audit retention cheaply",
     "tiered storage hot broker retention SSD bill audit topic"),
    # --- 24 ---
    ("Kafka Connect's Debezium source replaced a homegrown CDC poller against Postgres; logical replication slots picked up row changes within 50 ms.", "decision", "technical", False,
     [("Kafka Connect", "framework"), ("Debezium", "tool"), ("Postgres", "database")],
     [("Debezium", "Kafka Connect", "BUILDS_ON")],
     "which CDC connector took over the homegrown Postgres poller",
     "Debezium logical replication slot CDC poll swap latency"),
    # --- 25 ---
    ("MirrorMaker 2 stretched the orders topic from us-east-1 to eu-west-1; offsets translated cleanly so failover consumers resumed without re-reading.", "architecture", "technical", False,
     [("MirrorMaker 2", "tool"), ("us-east-1", "place"), ("eu-west-1", "place")],
     [],
     "which Kafka tool replicated the orders topic across AWS regions",
     "MirrorMaker cross region offset translate failover resume"),
    # --- 26 ---
    ("Cluster Linking on Confluent Cloud replaced MirrorMaker 2 for the disaster recovery topic; byte-for-byte mirroring kept offsets identical without translation.", "decision", "technical", False,
     [("Cluster Linking", "service"), ("Confluent Cloud", "service"), ("MirrorMaker 2", "tool")],
     [("Cluster Linking", "MirrorMaker 2", "REPLACES")],
     "which Confluent feature retired MirrorMaker for DR topic mirroring",
     "cluster link byte mirror DR offset identical swap mirror"),
    # --- 27 ---
    ("ZooKeeper was retired on the Kafka cluster; KRaft mode controlled metadata with a quorum of three brokers and dropped the JVM count by a third.", "milestone", "technical", False,
     [("ZooKeeper", "service"), ("Kafka", "technology"), ("KRaft", "technology"), ("JVM", "technology")],
     [("KRaft", "ZooKeeper", "REPLACES")],
     "which Kafka mode retired ZooKeeper from the production cluster",
     "ZooKeeper retire KRaft quorum metadata JVM count drop"),
    # --- 28 ---
    ("Compacted topics held the customer-state changelog; consumers rebuilt local state from the latest value per key without a separate snapshot store.", "architecture", "technical", False,
     [("Compacted topics", "pattern")],
     [],
     "which Kafka topic mode let consumers rebuild local state from the log",
     "log compaction changelog rebuild local state per key keep"),
    # --- 29 ---
    ("Idempotent producer enable.idempotence=true caught a silent retry duplication during the 2026-02-14 incident; the broker dedup window covered the window the network split opened.", "milestone", "technical", False,
     [("enable.idempotence", "config"), ("2026-02-14", "date")],
     [],
     "which producer setting closed the retry duplication during the incident",
     "idempotent producer dedup network split incident date fix"),
    # --- 30 ---
    ("Transactional outbox pattern bridged Postgres writes to Kafka; Debezium tailed the outbox table so the application never wrote to two systems in one request.", "architecture", "technical", False,
     [("Postgres", "database"), ("Kafka", "technology"), ("Debezium", "tool"), ("Transactional outbox", "pattern")],
     [],
     "which pattern bridged Postgres writes to Kafka without dual writes",
     "outbox pattern dual write CDC tail table single tx"),
    # --- 31 ---
    ("RabbitMQ Streams were tested as a Kafka replacement; the lack of consumer-side stream offsets in the existing client library blocked the swap on a one-week deadline.", "problem", "technical", False,
     [("RabbitMQ Streams", "technology"), ("Kafka", "technology")],
     [],
     "why did the RabbitMQ Streams swap fail the one-week Kafka deadline",
     "RabbitMQ Streams offset client library swap deadline block"),
    # --- 32 ---
    ("Karapace replaced the licensed Confluent Schema Registry on the staging cluster; Aiven's Apache 2.0 fork stayed wire-compatible with the production producers.", "decision", "technical", False,
     [("Karapace", "tool"), ("Confluent Schema Registry", "service"), ("Aiven", "organization")],
     [("Karapace", "Confluent Schema Registry", "REPLACES")],
     "which open-source registry replaced Confluent on the staging cluster",
     "Karapace fork wire compatible staging registry license swap"),
    # --- 33 ---
    ("Kafka tiered storage on Apache 3.6 went GA on 2026-01-09; the team migrated the audit topic the next sprint to drop SSD spend by 60 percent.", "milestone", "technical", False,
     [("Apache 3.6", "technology"), ("2026-01-09", "date")],
     [],
     "when did Kafka tiered storage go GA and which topic moved first",
     "Apache 3.6 tier storage GA audit migrate SSD spend date"),
    # --- 34. noise ---
    ("Hang on, draining the consumer.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Kinesis Data Streams replaced AWS SQS for the click ingest; ordered per-shard reads matched the session reconstruction need that SQS could not promise.", "decision", "technical", False,
     [("Kinesis Data Streams", "service"), ("AWS SQS", "service")],
     [("Kinesis Data Streams", "AWS SQS", "REPLACES")],
     "which AWS streaming service replaced SQS for ordered click ingest",
     "Kinesis shard order session reconstruct SQS swap stream"),
    # --- 36 ---
    ("AWS MSK was preferred over self-hosted Kafka after the second on-call page from a broker disk; managed patching cost less than two engineer-weeks per quarter.", "preference", "technical", False,
     [("AWS MSK", "service"), ("Kafka", "technology")],
     [("AWS MSK", "Kafka", "PREFERS")],
     "which managed Kafka beat self-hosted on the engineer-time math",
     "MSK managed self host engineer time disk page swap"),
    # --- 37 ---
    ("EventBridge Pipes connected SQS to a Step Function workflow; the no-code mapping replaced a Lambda glue function that did just JSON shaping.", "decision", "technical", False,
     [("EventBridge Pipes", "service"), ("SQS", "service"), ("Step Function", "service"), ("Lambda", "service")],
     [("EventBridge Pipes", "Lambda", "REPLACES")],
     "which AWS glue service displaced the Lambda doing JSON shaping",
     "EventBridge Pipes SQS Step Function glue Lambda swap"),
    # --- 38 ---
    ("Azure Service Bus replaced AWS SQS during the Azure migration; sessions plus duplicate detection covered the FIFO use case that SQS FIFO throttled.", "decision", "technical", False,
     [("Azure Service Bus", "service"), ("AWS SQS", "service"), ("SQS FIFO", "service")],
     [("Azure Service Bus", "AWS SQS", "REPLACES")],
     "which Azure queue absorbed the FIFO workload from SQS during the move",
     "Service Bus session duplicate detect FIFO Azure swap"),
    # --- 39 ---
    ("Azure Event Hubs Capture wrote raw Kafka-protocol events to ADLS Gen2 in Parquet; the Synapse query path skipped a stand-alone Spark batch job.", "architecture", "technical", False,
     [("Azure Event Hubs", "service"), ("ADLS Gen2", "service"), ("Parquet", "technology"), ("Synapse", "service"), ("Spark", "framework")],
     [],
     "which Event Hubs feature wrote Kafka-protocol events to ADLS as Parquet",
     "Event Hubs Capture ADLS Parquet Synapse Spark skip path"),
    # --- 40 ---
    ("NATS core pub/sub was kept for the fire-and-forget metrics fan-out; JetStream durability was not needed and would have added per-message disk cost.", "decision", "technical", False,
     [("NATS", "technology"), ("JetStream", "service")],
     [],
     "which NATS mode stayed on the metrics fan-out and why not JetStream",
     "NATS core pub sub fire forget metric durability skip"),
    # --- 41 ---
    ("Apache Camel routes orchestrated the cross-broker integration between RabbitMQ and Kafka; the EIP DSL replaced a tangle of small Spring Boot bridges.", "decision", "technical", False,
     [("Apache Camel", "framework"), ("RabbitMQ", "technology"), ("Kafka", "technology"), ("Spring Boot", "framework")],
     [("Apache Camel", "Spring Boot", "REPLACES")],
     "which integration framework replaced the Spring Boot bridge tangle",
     "Camel EIP DSL bridge Spring Boot RabbitMQ Kafka swap"),
    # --- 42 ---
    ("CloudEvents v1.0 was adopted as the envelope format across the platform; consumers could route on type and source without parsing the payload.", "decision", "technical", False,
     [("CloudEvents v1.0", "protocol")],
     [],
     "which envelope format unified routing across the event platform",
     "CloudEvents envelope route type source payload skip parse"),
    # --- 43 ---
    ("Linus Torvalds' io_uring patches landed in the Redpanda hot path; the broker rolled the kernel 6.1 build out on 2026-02-28 to pick up batched submissions.", "fact", "technical", False,
     [("Linus Torvalds", "person"), ("io_uring", "technology"), ("Redpanda", "technology"), ("2026-02-28", "date")],
     [],
     "when did Redpanda pick up io_uring batched submissions in production",
     "io uring kernel Redpanda hot path batched submit date"),
    # --- 44 ---
    ("Kafka KIP-500 documentation is the reference for the KRaft migration runbook; the controller-quorum bootstrap order matters more than the docs admit.", "reference", "technical", False,
     [("KIP-500", "publication"), ("KRaft", "technology")],
     [],
     "which Kafka KIP guides the in-house KRaft migration runbook",
     "KIP 500 KRaft controller quorum bootstrap doc reference"),
    # --- 45 ---
    ("Strimzi on Kubernetes ran the Kafka cluster; the operator's rolling update logic respected min.insync.replicas without the team writing custom scripts.", "architecture", "technical", False,
     [("Strimzi", "tool"), ("Kubernetes", "platform"), ("Kafka", "technology"), ("min.insync.replicas", "config")],
     [],
     "which Kafka operator on Kubernetes respected min.insync.replicas on rolls",
     "Strimzi operator Kubernetes rolling update insync replica"),
    # --- 46 ---
    ("Schema evolution broke a downstream consumer when a required field was added to the Avro schema; backward-compatibility checks in CI now block the merge.", "problem", "technical", False,
     [("Avro", "protocol"), ("CI", "tool")],
     [],
     "which schema check now blocks required-field additions before merge",
     "schema evolve required field Avro backward compatibility CI"),
    # --- 47 ---
    ("ksqlDB held the materialized join across the inventory and orders streams; pushing the join into the broker tier dropped the warehouse query load by half.", "architecture", "technical", False,
     [("ksqlDB", "framework")],
     [],
     "which streaming SQL engine pushed the inventory-orders join broker-side",
     "ksqlDB materialized join broker tier warehouse load drop"),
    # --- 48 ---
    ("Benthos replaced a Logstash pipeline for the syslog-to-Kafka path; the declarative config file fit the GitOps flow better than Ruby filter snippets.", "decision", "technical", False,
     [("Benthos", "tool"), ("Logstash", "tool"), ("Kafka", "technology"), ("GitOps", "concept"), ("Ruby", "language")],
     [("Benthos", "Logstash", "REPLACES")],
     "which streaming tool retired Logstash on the syslog-to-Kafka path",
     "Benthos Logstash declarative config GitOps Ruby swap"),
    # --- 49 ---
    ("Confluent Kora engine GA on 2026-03-15 motivated the move to Confluent Cloud serverless tier; the per-MB billing matched the bursty nightly batch profile.", "milestone", "technical", False,
     [("Confluent Kora", "technology"), ("Confluent Cloud", "service"), ("2026-03-15", "date")],
     [],
     "when did Kora GA push the team toward the Confluent Cloud serverless tier",
     "Kora GA Confluent serverless per MB bursty batch date"),
    # --- 50 ---
    ("End-to-end exactly-once across Flink and Kafka was certified on the payments pipeline on 2026-04-02; two-phase commit sinks plus transactional producers closed the audit gap.", "milestone", "technical", False,
     [("Flink", "framework"), ("Kafka", "technology"), ("2026-04-02", "date")],
     [],
     "when did Flink-Kafka exactly-once close the payments audit gap",
     "exactly once two phase commit transactional payments date"),
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
