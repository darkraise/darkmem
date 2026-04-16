"""One-off emitter for shared-base batch-153 — technical domain (time-series databases: InfluxDB 3.0, TimescaleDB, QuestDB, VictoriaMetrics, Prometheus, M3DB, Graphite, OpenTSDB, Druid, Pinot, ClickHouse, TDengine, hypertables, continuous aggregates, retention, downsampling, Gorilla codec, WAL, cardinality, line protocol, Flux/PromQL/SQL, Grafana).

Writes 50 rows to data/v2/shared/batch_153.tmp.jsonl with ids shared-07601..07650.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_153.tmp.jsonl"
ID_OFFSET = 7600

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Swapped the metrics backend from Graphite to VictoriaMetrics after the whisper files blew past the ssd budget; ingest settled around 900k samples/s on a single node with room to spare.", "decision", "technical", False,
     [("Graphite", "database"), ("VictoriaMetrics", "database"), ("whisper", "file")],
     [("VictoriaMetrics", "Graphite", "REPLACES")],
     "which time-series store replaced Graphite after whisper file storage costs got out of hand",
     "victoriametrics graphite whisper storage ssd replace ingest rate"),
    # --- 2 decision ---
    ("TimescaleDB hypertables shard the trades table by symbol and by a one-day chunk_time_interval; queries prune to a handful of chunks and the planner stops sequentially scanning the year.", "decision", "technical", False,
     [("TimescaleDB", "database"), ("hypertables", "concept"), ("chunk_time_interval", "config"), ("trades", "concept")],
     [("hypertables", "TimescaleDB", "HAS_PART")],
     "how does the trades table prune scans in TimescaleDB across a year of data",
     "timescaledb hypertable chunk interval symbol shard prune trades"),
    # --- 3 fact ---
    ("InfluxDB 3.0 ditched TSM in favour of an Apache Parquet object-store tier plus an Arrow ingester; queries route through DataFusion and line protocol writes still land through the v2 HTTP path.", "fact", "technical", False,
     [("InfluxDB 3.0", "database"), ("TSM", "concept"), ("Parquet", "technology"), ("Arrow", "technology"), ("DataFusion", "library"), ("line protocol", "protocol")],
     [("InfluxDB 3.0", "TSM", "REPLACES"), ("InfluxDB 3.0", "DataFusion", "USES")],
     "which storage and query engines did InfluxDB 3.0 swap in place of the older TSM format",
     "influxdb 3 tsm parquet arrow datafusion line protocol ingest query"),
    # --- 4 architecture ---
    ("Continuous aggregates in TimescaleDB materialise a one-minute ohlcv view that refresh policies top up every fifteen seconds; dashboards read the rollup and the raw table only gets hit for drill-downs.", "architecture", "technical", False,
     [("TimescaleDB", "database"), ("Continuous aggregates", "concept"), ("ohlcv", "concept"), ("refresh policies", "concept")],
     [("Continuous aggregates", "TimescaleDB", "HAS_PART")],
     "how do dashboards avoid hammering raw rows while keeping an almost-live ohlcv view in TimescaleDB",
     "continuous aggregate timescale ohlcv refresh policy dashboard rollup"),
    # --- 5 milestone ---
    ("Cut Prometheus TSDB cardinality from 4.2 million to 780 thousand active series by dropping pod_uid and hash-bucketing request_id; scrape memory halved and head compaction quit thrashing.", "milestone", "technical", False,
     [("Prometheus", "database"), ("cardinality", "concept"), ("pod_uid", "config"), ("request_id", "config")],
     [],
     "which label drops cut Prometheus active series and calmed the head compaction pressure",
     "prometheus cardinality pod uid request id label drop head compact"),
    # --- 6 decision ---
    ("Picked QuestDB over ClickHouse for the tick-ingest path: SIMD-accelerated ILP writer sustained 1.6M rows/s on a single m6i.4xlarge while the ClickHouse MergeTree flushes stalled behind part merges.", "decision", "technical", False,
     [("QuestDB", "database"), ("ClickHouse", "database"), ("ILP", "protocol"), ("MergeTree", "concept"), ("m6i.4xlarge", "infrastructure")],
     [("QuestDB", "ClickHouse", "PREFERS")],
     "which tick-ingest store won on a single m6i.4xlarge and what stalled the ClickHouse path",
     "questdb clickhouse ilp mergetree tick ingest simd m6i single node"),
    # --- 7 reference ---
    ("InfluxDB's line protocol encodes tags before fields with a comma delimiter and a trailing nanosecond timestamp; the reference grammar lives in the v1.8 docs and every client we ship follows it verbatim.", "reference", "technical", False,
     [("line protocol", "protocol"), ("InfluxDB", "database")],
     [("line protocol", "InfluxDB", "APPLIES_TO")],
     "where does the canonical grammar for InfluxDB line protocol ingestion live",
     "line protocol influx tag field timestamp nanosecond grammar v1 8"),
    # --- 8 architecture ---
    ("VictoriaMetrics cluster splits into vmstorage, vmselect, and vminsert pods; vmagent scrapes targets and replicates writes across two vmstorage shards using the consistent-hashing AccountID-VMInstance ring.", "architecture", "technical", False,
     [("VictoriaMetrics", "database"), ("vmstorage", "service"), ("vmselect", "service"), ("vminsert", "service"), ("vmagent", "service")],
     [("vmagent", "vminsert", "COMMUNICATES_WITH"), ("vminsert", "vmstorage", "COMMUNICATES_WITH"), ("vmselect", "vmstorage", "COMMUNICATES_WITH")],
     "how does a VictoriaMetrics cluster split responsibilities across scraping, writing, and querying services",
     "victoriametrics vmstorage vmselect vminsert vmagent cluster shard ring"),
    # --- 9 fact ---
    ("Facebook's Gorilla codec stores doubles as XOR deltas against the previous sample; a one-hour window of monotonic counters packs into about 1.37 bytes per point and the decoder walks the xor stream in a single pass.", "fact", "technical", False,
     [("Gorilla", "algorithm"), ("XOR deltas", "concept"), ("counters", "concept")],
     [],
     "how does the Gorilla codec pack double-precision samples down to roughly 1.37 bytes per point",
     "gorilla xor delta double compression codec counter monotonic byte"),
    # --- 10 noise ---
    ("The office foosball table developed a squeak in one of the goalkeeper rods and the patch notes on the whiteboard now track its decline week by week.", "fact", "noise", True, [], [], None, None),
    # --- 11 decision ---
    ("Moved the retention policy from a blanket 30-day drop to a tiered 7d raw, 90d 1m rollup, 2y 1h rollup on TimescaleDB; disk pressure on the hot SSD stopped paging and cold queries hit the slower pool.", "decision", "technical", False,
     [("retention policy", "concept"), ("TimescaleDB", "database"), ("rollup", "concept")],
     [],
     "which tiered retention layout replaced a flat 30-day drop on the TimescaleDB hot pool",
     "retention tier raw rollup timescale ssd cold hot pool drop policy"),
    # --- 12 problem ---
    ("Cardinality explosion on the payments namespace traced to a stripe_session_id label baked into every request counter; rewrote the recording rule to hash-bucket into sixteen buckets and memory-per-scrape fell 11x.", "problem", "technical", False,
     [("Cardinality explosion", "concept"), ("stripe_session_id", "config"), ("recording rule", "concept"), ("hash-bucket", "pattern")],
     [("hash-bucket", "Cardinality explosion", "FIXES")],
     "what label caused the payments namespace cardinality blow-up and which rewrite tamed it",
     "cardinality explosion stripe session id bucket hash recording rule"),
    # --- 13 architecture ---
    ("M3DB places a ratelimited ingestion aggregator in front of a three-node M3 cluster; the coordinator fans out to replicas with quorum writes and the local WAL flushes every two seconds to block storage.", "architecture", "technical", False,
     [("M3DB", "database"), ("aggregator", "service"), ("coordinator", "service"), ("WAL", "concept"), ("quorum", "concept")],
     [("coordinator", "M3DB", "COMMUNICATES_WITH"), ("aggregator", "coordinator", "COMMUNICATES_WITH")],
     "how does an M3DB deployment route writes from the aggregator through the coordinator to replicas",
     "m3db aggregator coordinator quorum wal replica fanout block storage"),
    # --- 14 preference ---
    ("Prefer PromQL's rate() over irate() in production dashboards because irate exaggerates spikes on sparse scrapes; irate stays in the live-debug panel where two-point derivatives actually help.", "preference", "technical", False,
     [("PromQL", "language"), ("rate()", "command"), ("irate()", "command")],
     [],
     "which PromQL derivative function is preferred in dashboards and why is irate kept only for live debug",
     "promql rate irate derivative dashboard sparse scrape spike live"),
    # --- 15 reference ---
    ("The InfluxDB Flux reference documents a pipe-forward syntax where from() feeds range() feeds filter() feeds aggregateWindow(); the 0.195.0 docs are the canonical source for the built-in transformations.", "reference", "technical", False,
     [("Flux", "language"), ("from()", "command"), ("range()", "command"), ("aggregateWindow()", "command")],
     [],
     "where is the authoritative Flux pipeline grammar documented for the current release",
     "flux pipe forward from range filter aggregate window reference 0 195"),
    # --- 16 decision ---
    ("Picked Apache Druid for the clickstream rollup ingest because a one-minute segment granularity with hash-partitioned shards beat Pinot's upsert mode on write amplification for our append-only funnel events.", "decision", "technical", False,
     [("Apache Druid", "database"), ("Pinot", "database"), ("hash-partitioned shards", "pattern")],
     [("Apache Druid", "Pinot", "PREFERS")],
     "which OLAP store won the clickstream rollup bake-off and what write-amplification property sealed it",
     "druid pinot clickstream rollup segment granularity hash partition"),
    # --- 17 milestone ---
    ("Finished migrating 86 TB of metrics from OpenTSDB on HBase to ClickHouse ReplicatedMergeTree; ingest throughput doubled and dashboard p95 query latency fell from 4.1s to 420ms on the same fleet.", "milestone", "technical", False,
     [("OpenTSDB", "database"), ("HBase", "database"), ("ClickHouse", "database"), ("ReplicatedMergeTree", "concept")],
     [("ClickHouse", "OpenTSDB", "REPLACES")],
     "which migration retired OpenTSDB and what did dashboard query latency do after the cutover",
     "opentsdb hbase clickhouse replicated mergetree migration latency p95"),
    # --- 18 architecture ---
    ("TDengine super-tables register per-device sub-tables with shared schema; the sensor fleet reuses one STable definition and device-level sub-tables inherit tag columns without recompilation on the writer.", "architecture", "technical", False,
     [("TDengine", "database"), ("super-tables", "concept"), ("sub-tables", "concept"), ("STable", "concept")],
     [("super-tables", "TDengine", "HAS_PART")],
     "how does TDengine's super-table model let a sensor fleet share schema across millions of devices",
     "tdengine super table sub table stable sensor fleet tag schema"),
    # --- 19 fact ---
    ("Prometheus TSDB blocks cover a two-hour range by default and compact into larger blocks at 2h, 8h, and 2d boundaries; the head block lives in memory and flushes on WAL checkpoint.", "fact", "technical", False,
     [("Prometheus", "database"), ("TSDB", "concept"), ("WAL", "concept"), ("head block", "concept")],
     [("TSDB", "Prometheus", "HAS_PART")],
     "how does Prometheus TSDB lay out blocks across the two-hour, eight-hour, and two-day compaction boundaries",
     "prometheus tsdb block compaction head wal checkpoint two hour"),
    # --- 20 decision ---
    ("Dropped Graphite's AggregationMethods config and standardised on StatsD-in-front with fixed 10s flush windows; mixed-method confusion across teams disappeared and percentile panels stopped lying.", "decision", "technical", False,
     [("Graphite", "database"), ("StatsD", "service"), ("AggregationMethods", "config")],
     [("StatsD", "AggregationMethods", "REPLACES")],
     "which aggregation scheme replaced Graphite's AggregationMethods and what dashboard lie did it stop",
     "graphite statsd aggregation method flush percentile panel standard"),
    # --- 21 preference ---
    ("On Grafana prefer the TimescaleDB Postgres datasource with $__timeBucket over the InfluxQL datasource; the SQL is legible in code review and the $__timeBucket macro honours time-zone offsets the InfluxQL one silently drops.", "preference", "technical", False,
     [("Grafana", "tool"), ("TimescaleDB", "database"), ("InfluxQL", "language"), ("$__timeBucket", "command")],
     [],
     "which Grafana datasource is preferred for TimescaleDB panels and why is InfluxQL avoided",
     "grafana timescale postgres timebucket influxql datasource timezone macro"),
    # --- 22 reference ---
    ("The VictoriaMetrics MetricsQL reference catalogues extensions over PromQL including histogram_quantiles() with bucket hints and keep_last_value(); every extension degrades gracefully to PromQL semantics when the hint is omitted.", "reference", "technical", False,
     [("VictoriaMetrics", "database"), ("MetricsQL", "language"), ("PromQL", "language"), ("histogram_quantiles()", "command"), ("keep_last_value()", "command")],
     [("MetricsQL", "PromQL", "EXTENDS")],
     "where do the VictoriaMetrics MetricsQL extensions to PromQL get specified along with fallback semantics",
     "metricsql promql extension histogram quantile keep last value reference"),
    # --- 23 problem ---
    ("Downsampling the 5s raw series into 1m rollups double-counted gauges that straddled bucket edges; switched the aggregator from sum() to last() for gauge metrics and the kernel_memory panel stopped spiking on the hour.", "problem", "technical", False,
     [("Downsampling", "concept"), ("gauges", "concept"), ("aggregator", "service"), ("kernel_memory", "concept")],
     [],
     "which aggregation change fixed the double-count on gauges that spanned rollup bucket edges",
     "downsample rollup gauge last sum bucket edge kernel memory spike"),
    # --- 24 decision ---
    ("Chose Snappy over Zstd for the ingest-path segment compression on the hot tier; p99 write latency stayed under 12 ms while Zstd at level 3 was shoving it past 40 ms on the same batch size.", "decision", "technical", False,
     [("Snappy", "algorithm"), ("Zstd", "algorithm"), ("ingest-path", "concept")],
     [("Snappy", "Zstd", "PREFERS")],
     "which segment compression won for hot-tier ingest latency and what did the loser cost at p99",
     "snappy zstd ingest segment compression latency p99 hot tier"),
    # --- 25 architecture ---
    ("Wrote the ingest write-path as a ring buffer that groups 8 kB WAL frames; the flusher fsyncs each frame and signals the index builder, which gives durability without blocking the hot producer on I/O.", "architecture", "technical", False,
     [("ring buffer", "pattern"), ("WAL", "concept"), ("flusher", "service"), ("index builder", "service")],
     [("WAL", "ring buffer", "HAS_PART")],
     "how does the ingest path guarantee WAL durability without blocking the hot producer on fsync",
     "ring buffer wal frame fsync flusher index builder producer path"),
    # --- 26 milestone ---
    ("Hit 2 billion active series across the VictoriaMetrics cluster after the shard-by-tenant rollout; query fan-out stayed bounded per vmselect because tenants never span shards and cross-shard joins are rejected at parse.", "milestone", "technical", False,
     [("VictoriaMetrics", "database"), ("vmselect", "service"), ("shard-by-tenant", "pattern")],
     [("shard-by-tenant", "VictoriaMetrics", "APPLIES_TO")],
     "which sharding change let the VictoriaMetrics fleet scale past 2 billion active series without fan-out blow-up",
     "victoriametrics shard tenant active series vmselect fan out billion"),
    # --- 27 fact ---
    ("ClickHouse for time-series uses the MergeTree family with ORDER BY (metric_name, timestamp); the primary-key skip index plus min-max per granule makes a range scan for one metric over a day touch a few dozen granules.", "fact", "technical", False,
     [("ClickHouse", "database"), ("MergeTree", "concept"), ("primary-key skip index", "concept"), ("granule", "concept")],
     [("MergeTree", "ClickHouse", "HAS_PART")],
     "how does ClickHouse MergeTree prune a day's range scan on one metric down to a handful of granules",
     "clickhouse mergetree primary skip index granule order metric timestamp"),
    # --- 28 architecture ---
    ("Chunk-based storage in TimescaleDB uses per-chunk compression: old chunks convert to a columnar layout with dictionary, delta-of-delta on timestamps, and Gorilla-like XOR on doubles once they age past seven days.", "architecture", "technical", False,
     [("TimescaleDB", "database"), ("chunk", "concept"), ("columnar", "concept"), ("delta-of-delta", "algorithm"), ("Gorilla", "algorithm")],
     [("chunk", "TimescaleDB", "HAS_PART")],
     "how do TimescaleDB chunks convert to columnar with delta-of-delta timestamps after an age threshold",
     "timescale chunk compression columnar delta gorilla xor age seven day"),
    # --- 29 decision ---
    ("Kept Prometheus as the alerting engine and routed long-term storage to Thanos with S3 object tier; the remote_write to Cortex path got shelved after the write amplification profile blew our per-write budget.", "decision", "technical", False,
     [("Prometheus", "database"), ("Thanos", "service"), ("S3", "platform"), ("Cortex", "service"), ("remote_write", "protocol")],
     [("Thanos", "Cortex", "PREFERS"), ("Thanos", "S3", "USES")],
     "which long-term metrics backend won over Cortex and what cost profile knocked remote_write out",
     "prometheus thanos cortex s3 remote write long term alerting shelf"),
    # --- 30 architecture ---
    ("Grafana dashboards panel-query templated variables resolve at refresh; a $instance variable injects a regex into PromQL label_values() and the template picks top-N by query-based selection rather than config.", "architecture", "technical", False,
     [("Grafana", "tool"), ("PromQL", "language"), ("label_values()", "command"), ("$instance", "config")],
     [],
     "how do Grafana dashboard variables template top-N PromQL label values without hardcoding a list",
     "grafana dashboard variable instance label values promql template regex"),
    # --- 31 fact ---
    ("QuestDB's storage engine column-files the partition-by-day tables under table_name/YYYY-MM-DD.N and keeps each column in a mapped file; range scans mmap the relevant columns and skip the unused ones entirely.", "fact", "technical", False,
     [("QuestDB", "database"), ("column-file", "concept"), ("partition-by-day", "concept"), ("mmap", "method")],
     [("column-file", "QuestDB", "HAS_PART")],
     "how does QuestDB lay partition-by-day tables as column-files and how does a range scan stay cheap",
     "questdb column file partition day mmap range scan skip column"),
    # --- 32 decision ---
    ("Replaced the per-pod OpenTelemetry collector sidecar with a DaemonSet node-agent feeding a central OTLP-to-Prometheus bridge; per-node scrape count dropped from 180 to 1 and kube-api watch pressure fell with it.", "decision", "technical", False,
     [("OpenTelemetry", "framework"), ("DaemonSet", "pattern"), ("OTLP", "protocol"), ("Prometheus", "database")],
     [("OTLP", "Prometheus", "COMMUNICATES_WITH")],
     "which collector topology replaced per-pod sidecars for metrics scraping and what pressure did it relieve",
     "opentelemetry daemonset otlp prometheus sidecar bridge node agent scrape"),
    # --- 33 preference ---
    ("Prefer continuous aggregates over materialised views for the analytics refresh window; refresh_continuous_aggregate() on a time-range argument beats a REFRESH MATERIALIZED VIEW rewrite by roughly 40x on our ohlcv table.", "preference", "technical", False,
     [("continuous aggregates", "concept"), ("materialised views", "concept"), ("refresh_continuous_aggregate()", "command"), ("REFRESH MATERIALIZED VIEW", "command")],
     [],
     "which TimescaleDB refresh primitive is preferred for the analytics window and why over plain materialised views",
     "continuous aggregate materialized view refresh time range ohlcv 40x"),
    # --- 34 architecture ---
    ("The metrics stack fronted Grafana with a per-tenant VMSelect and a stateless LB; VMSelect resolves tenant from the bearer token, rewrites the MetricsQL with an accountID filter, and hands to vmstorage shards.", "architecture", "technical", False,
     [("Grafana", "tool"), ("VMSelect", "service"), ("MetricsQL", "language"), ("accountID", "config"), ("vmstorage", "service")],
     [("VMSelect", "vmstorage", "COMMUNICATES_WITH")],
     "how does the per-tenant VMSelect fronting Grafana route a query down to the right vmstorage shards",
     "vmselect grafana tenant bearer accountid metricsql filter shard"),
    # --- 35 milestone ---
    ("Shipped the InfluxDB 3.0 cutover for the device-telemetry namespace; 11 TB reloaded from Parquet snapshots and the old TSM directory got archived after the one-week regression window closed clean.", "milestone", "technical", False,
     [("InfluxDB 3.0", "database"), ("Parquet", "technology"), ("TSM", "concept"), ("device-telemetry", "project")],
     [("InfluxDB 3.0", "TSM", "REPLACES")],
     "which telemetry namespace cut over to InfluxDB 3.0 and what happened to the old TSM directory",
     "influxdb 3 parquet tsm device telemetry cutover archive reload"),
    # --- 36 fact ---
    ("The Flux aggregateWindow() transformation takes an every and a period argument; setting period > every emits overlapping windows, which matters for sliding-percentile panels over rate-limited scrape targets.", "fact", "technical", False,
     [("Flux", "language"), ("aggregateWindow()", "command"), ("period", "config"), ("every", "config")],
     [],
     "how does Flux aggregateWindow use the period and every arguments to produce overlapping windows",
     "flux aggregate window period every overlap sliding percentile scrape"),
    # --- 37 decision ---
    ("Went with M3DB's downsampling aggregator instead of Prometheus recording rules for the fan-out heavy Istio mesh metrics; per-rule evaluation used to blow the rule_group_duration SLO on reload.", "decision", "technical", False,
     [("M3DB", "database"), ("Prometheus", "database"), ("recording rules", "concept"), ("Istio", "framework")],
     [("M3DB", "recording rules", "REPLACES")],
     "which downsampling mechanism replaced Prometheus recording rules for Istio mesh metrics and why",
     "m3db downsample aggregator recording rule istio mesh fan out slo"),
    # --- 38 reference ---
    ("Druid's ingestion uses a MiddleManager to build segments and a Historical to serve them; the Overlord schedules batch and Kafka indexing tasks, and the Broker fans queries out across Historicals by segment time range.", "reference", "technical", False,
     [("Druid", "database"), ("MiddleManager", "service"), ("Historical", "service"), ("Overlord", "service"), ("Broker", "service"), ("Kafka", "service")],
     [("MiddleManager", "Historical", "COMMUNICATES_WITH"), ("Overlord", "MiddleManager", "COMMUNICATES_WITH"), ("Broker", "Historical", "COMMUNICATES_WITH")],
     "which Druid services hand off between ingestion-time segment building and query-time segment serving",
     "druid middlemanager historical overlord broker kafka segment ingestion"),
    # --- 39 reference ---
    ("The Pinot docs define a star-tree index as a materialised multi-dimensional aggregate per split; the star-tree level cutoff and max-leaf-records knobs tune query acceleration vs segment size and live in table config.", "reference", "technical", False,
     [("Pinot", "database"), ("star-tree", "concept"), ("max-leaf-records", "config")],
     [("star-tree", "Pinot", "HAS_PART")],
     "where is the Pinot star-tree index documented and which knobs tune query acceleration against segment size",
     "pinot star tree index leaf records config reference accelerate"),
    # --- 40 problem ---
    ("Write amplification on the Prometheus remote_write path tripled after enabling WAL-based replay on the receiver; dropped the max_samples_per_send to 2000 and the send latency histogram stopped bimodal spiking.", "problem", "technical", False,
     [("Prometheus", "database"), ("remote_write", "protocol"), ("WAL", "concept"), ("max_samples_per_send", "config")],
     [("max_samples_per_send", "remote_write", "CONFIGURES")],
     "which remote_write knob tamed the write amplification after WAL-based replay on the receiver",
     "prometheus remote write wal replay amplify max samples per send bimodal"),
    # --- 41 decision ---
    ("The downsampling DAG runs hourly: raw 5s series fan into parallel aggregators producing 1m, 5m, 1h, 1d outputs; each level reads only the previous level so reprocessing a late arrival walks just one strand.", "decision", "technical", False,
     [("downsampling DAG", "pattern"), ("aggregators", "service")],
     [],
     "how does the hourly downsampling DAG layer 1m, 5m, 1h, 1d outputs so a late arrival only replays one strand",
     "downsample dag hourly aggregator 5s 1m 5m 1h 1d late arrival replay"),
    # --- 42 reference ---
    ("The TimescaleDB docs index hypertable maintenance under chunk_time_interval, compression policies, and retention policies; the add_retention_policy() and add_compression_policy() admin functions are the supported entry points.", "reference", "technical", False,
     [("TimescaleDB", "database"), ("chunk_time_interval", "config"), ("add_retention_policy()", "command"), ("add_compression_policy()", "command")],
     [],
     "where do the TimescaleDB admin functions for retention and compression policies get documented",
     "timescaledb retention compression chunk interval policy admin reference"),
    # --- 43 noise ---
    ("Someone left a thermos of cold brew coffee on the patio bench overnight and it has now become an office mystery that no one will claim.", "fact", "noise", True, [], [], None, None),
    # --- 44 preference ---
    ("Prefer SQL over PromQL for ad-hoc correlation queries spanning metrics and business tables; TimescaleDB's ability to JOIN a chunked trades hypertable against the accounts table is worth the slight verbosity.", "preference", "technical", False,
     [("SQL", "language"), ("PromQL", "language"), ("TimescaleDB", "database"), ("trades", "concept"), ("accounts", "concept")],
     [],
     "which query language is preferred for ad-hoc correlation between metrics and business tables and why",
     "sql promql timescale trade account join ad hoc correlation verbose"),
    # --- 45 milestone ---
    ("Rolled out Gorilla-style compression on the legacy OpenTSDB HBase tier with a custom codec; hot-region storage shrank 9.4x and region-server heap pressure finally dropped below the auto-split threshold.", "milestone", "technical", False,
     [("Gorilla", "algorithm"), ("OpenTSDB", "database"), ("HBase", "database"), ("region-server", "service")],
     [("Gorilla", "OpenTSDB", "APPLIES_TO")],
     "which compression rollout finally pushed OpenTSDB HBase region-server heap below the auto-split threshold",
     "gorilla opentsdb hbase compression region server heap auto split"),
    # --- 46 decision ---
    ("Sent TDengine to production for the IoT pipeline over InfluxDB 2.x after benchmarking; its sub-table model kept per-device metadata overhead flat as the fleet crossed 400k devices, where InfluxDB's series index ballooned.", "decision", "technical", False,
     [("TDengine", "database"), ("InfluxDB 2.x", "database"), ("sub-table", "concept"), ("IoT", "project")],
     [("TDengine", "InfluxDB 2.x", "PREFERS")],
     "which TSDB won for the IoT pipeline at 400k devices and what series-index behaviour drove the decision",
     "tdengine influxdb 2 iot sub table device series index benchmark 400k"),
    # --- 47 milestone ---
    ("Migrated the Graphite whisper archive off the NFS mount and into a Carbon-cache-to-VictoriaMetrics bridge; ingest-induced iowait fell from 38% to under 3% on the two storage nodes.", "milestone", "technical", False,
     [("Graphite", "database"), ("whisper", "file"), ("Carbon-cache", "service"), ("VictoriaMetrics", "database"), ("NFS", "protocol")],
     [("Carbon-cache", "VictoriaMetrics", "COMMUNICATES_WITH")],
     "which bridge moved Graphite whisper off NFS and what did storage-node iowait do after",
     "graphite whisper carbon cache victoria metrics nfs bridge iowait"),
    # --- 48 architecture ---
    ("ClickHouse-for-TS shards by (tenant_id, metric_name) hash and replicates 2-way through Keeper; distributed-table reads fan out to local replicas and the coordinator aggregates per-shard state before final merge.", "architecture", "technical", False,
     [("ClickHouse", "database"), ("tenant_id", "config"), ("metric_name", "config"), ("Keeper", "service"), ("distributed-table", "concept")],
     [("ClickHouse", "Keeper", "USES")],
     "how does the ClickHouse time-series deployment shard by tenant and metric and replicate through Keeper",
     "clickhouse shard tenant metric keeper distributed replica aggregate"),
    # --- 49 milestone ---
    ("WAL corruption on the VictoriaMetrics vmstorage after an abrupt node loss got the shard stuck in recovery; enabling -snapshot.createRestore on the next boot rebuilt the in-memory index and ingest resumed in under four minutes.", "milestone", "technical", False,
     [("WAL", "concept"), ("VictoriaMetrics", "database"), ("vmstorage", "service"), ("-snapshot.createRestore", "config")],
     [("-snapshot.createRestore", "WAL", "FIXES")],
     "which VictoriaMetrics recovery flag rebuilt vmstorage after WAL corruption from an abrupt node loss",
     "vmstorage wal corrupt snapshot create restore recovery node loss"),
    # --- 50 fact ---
    ("InfluxDB line protocol's nanosecond precision is the default but the /write endpoint accepts a ?precision=s|ms|us|ns override; Telegraf pins to ns to avoid quantisation drift when chaining multiple aggregator hops.", "fact", "technical", False,
     [("InfluxDB", "database"), ("line protocol", "protocol"), ("/write", "api"), ("Telegraf", "service")],
     [("Telegraf", "line protocol", "USES")],
     "how does the InfluxDB /write endpoint accept precision overrides and why does Telegraf pin to nanoseconds",
     "influxdb line protocol precision nanosecond write endpoint telegraf drift"),
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
