"""One-off emitter for shared-base batch-139 — technical domain (time-series databases).

Writes 50 rows to data/v2/shared/batch_139.tmp.jsonl with ids shared-06901..06950.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_139.tmp.jsonl"
ID_OFFSET = 6900

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("TimescaleDB hypertables partitioned the sensor feed by hour; the chunk_time_interval tuned to 3600 seconds kept each chunk around 500 MB for fast drop.", "architecture", "technical", False,
     [("TimescaleDB", "database"), ("hypertables", "concept")],
     [],
     "which TimescaleDB primitive held the hourly sensor partitions",
     "hypertable chunk interval partition hour sensor drop fast"),
    # --- 2 ---
    ("TimescaleDB replaced InfluxDB 1.x for the SQL-first analytics team; standard Postgres JOINs against dimension tables beat Flux transpilation tricks.", "decision", "technical", False,
     [("TimescaleDB", "database"), ("InfluxDB 1.x", "database"), ("Flux", "language"), ("Postgres", "database")],
     [("TimescaleDB", "InfluxDB 1.x", "REPLACES")],
     "which time-series engine displaced InfluxDB for the SQL-first analytics team",
     "SQL first join dimension table transpile swap engine analyst"),
    # --- 3 ---
    ("Continuous aggregates on TimescaleDB pre-rolled the 1-minute and 1-hour buckets; dashboard queries that scanned a month dropped from 14 seconds to 180 ms.", "milestone", "technical", False,
     [("TimescaleDB", "database"), ("Continuous aggregates", "concept")],
     [],
     "which TimescaleDB feature collapsed the monthly dashboard query latency",
     "continuous aggregate pre roll bucket minute hour month scan"),
    # --- 4 ---
    ("InfluxDB 3 on IOx replaced the 2.x TSM storage engine; Parquet files on object storage plus DataFusion query let the team cap retention without the tombstone churn.", "decision", "technical", False,
     [("InfluxDB 3", "database"), ("IOx", "technology"), ("TSM", "technology"), ("Parquet", "technology"), ("DataFusion", "framework")],
     [("InfluxDB 3", "TSM", "REPLACES")],
     "which InfluxDB engine replaced TSM and removed tombstone churn",
     "IOx Parquet DataFusion engine retention tombstone swap storage"),
    # --- 5 ---
    ("Flux was retired on the new InfluxDB 3 deployment; SQL through the FlightSQL endpoint matched the BI tools the team already had.", "decision", "technical", False,
     [("Flux", "language"), ("InfluxDB 3", "database"), ("FlightSQL", "protocol")],
     [("FlightSQL", "Flux", "REPLACES")],
     "which query surface displaced Flux on the new InfluxDB 3 cluster",
     "SQL Flight endpoint BI tool swap query language retire"),
    # --- 6 ---
    ("InfluxQL stayed on the legacy InfluxDB 1.8 cluster feeding the factory floor dashboards; the operators knew the syntax and Flux never landed there.", "fact", "technical", False,
     [("InfluxQL", "language"), ("InfluxDB 1.8", "database"), ("Flux", "language")],
     [],
     "which query language kept the legacy factory floor dashboards alive",
     "legacy cluster factory operator syntax familiar keep language"),
    # --- 7 ---
    ("Line Protocol ingest from Telegraf kept landing on the InfluxDB 2.7 write endpoint; the OTLP metrics receiver on InfluxDB 3 handled the new Kubernetes fleet.", "architecture", "technical", False,
     [("Line Protocol", "protocol"), ("Telegraf", "tool"), ("InfluxDB 2.7", "database"), ("OTLP", "protocol"), ("InfluxDB 3", "database")],
     [],
     "which ingest protocols split traffic between the old and new Influx clusters",
     "line protocol OTLP metric ingest split legacy new receiver"),
    # --- 8 ---
    ("QuestDB beat InfluxDB on the market-data tick ingest benchmark; the SIMD-accelerated query engine pulled 4.3 million rows per second per core.", "milestone", "technical", False,
     [("QuestDB", "database"), ("InfluxDB", "database"), ("SIMD", "technology")],
     [("QuestDB", "InfluxDB", "IMPROVES_ON")],
     "which time-series engine won the market-data tick ingest benchmark",
     "SIMD vector query row per second core tick ingest bench"),
    # --- 9 ---
    ("VictoriaMetrics cluster replaced the Thanos sidecar plus store gateway on the Prometheus stack; storage footprint fell by 7x with no object storage dependency.", "decision", "technical", False,
     [("VictoriaMetrics", "database"), ("Thanos", "tool"), ("Prometheus", "database")],
     [("VictoriaMetrics", "Thanos", "REPLACES")],
     "which long-term store took over from Thanos on the Prometheus fleet",
     "storage footprint drop object store drop sidecar gateway swap"),
    # --- 10. noise ---
    ("Give me a moment, the retention policy's still backfilling.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("MetricsQL extended PromQL with keep_last_value and range_first on the VictoriaMetrics cluster; the alerting rules stayed readable without window stuffing.", "architecture", "technical", False,
     [("MetricsQL", "language"), ("PromQL", "language"), ("VictoriaMetrics", "database")],
     [("MetricsQL", "PromQL", "IMPROVES_ON")],
     "which query dialect extended PromQL for the alerting rules",
     "dialect extend keep last range first alert rule readable"),
    # --- 12 ---
    ("Prometheus TSDB head block compaction stalled during the 7-million-series overload; the out-of-order sample flag let late scrapes land without restart.", "problem", "technical", False,
     [("Prometheus TSDB", "database"), ("out-of-order sample", "concept")],
     [],
     "which Prometheus feature let late scrapes land without a restart",
     "head block compaction stall out of order sample series load"),
    # --- 13 ---
    ("Gorilla compression on the Prometheus TSDB squeezed 16 bytes per sample down to 1.37 bytes on steady-state metrics; Facebook Beringei was the original reference.", "fact", "technical", False,
     [("Gorilla", "technology"), ("Prometheus TSDB", "database"), ("Facebook Beringei", "technology")],
     [("Prometheus TSDB", "Gorilla", "BUILDS_ON")],
     "which compression scheme shrank Prometheus samples to near a byte each",
     "Gorilla Beringei compression sample byte steady state ref"),
    # --- 14 ---
    ("Delta-delta encoding on the timestamp column of the ClickHouse MergeTree table cut the on-disk metrics footprint by 62 percent versus plain LZ4.", "milestone", "technical", False,
     [("Delta-delta encoding", "technology"), ("ClickHouse", "database"), ("MergeTree", "technology"), ("LZ4", "technology")],
     [],
     "which encoding trimmed the ClickHouse timestamp column footprint",
     "delta encoding timestamp column compression footprint cut"),
    # --- 15 ---
    ("ClickHouse with the MergeTree engine replaced Apache Druid for the ad-tech metrics rollup; the SELECT-driven workflow beat Druid's segment tuning knobs.", "decision", "technical", False,
     [("ClickHouse", "database"), ("MergeTree", "technology"), ("Apache Druid", "database")],
     [("ClickHouse", "Apache Druid", "REPLACES")],
     "which columnar engine retired Druid on the ad-tech rollup pipeline",
     "columnar engine segment tune rollup ad tech swap workflow"),
    # --- 16 ---
    ("Apache Pinot held the user-facing real-time leaderboard; sub-second p99 on streaming ingest beat the Druid lambda path the team ran before.", "architecture", "technical", False,
     [("Apache Pinot", "database"), ("Druid", "database")],
     [("Apache Pinot", "Druid", "REPLACES")],
     "which real-time OLAP engine powered the leaderboard over Druid",
     "real time leaderboard sub second p99 stream ingest lambda"),
    # --- 17 ---
    ("Kdb+ kept the high-frequency trading desk's nanosecond tick store; q syntax and columnar memory-mapped files still beat open-source TSDBs on latency.", "fact", "technical", False,
     [("Kdb+", "database"), ("q", "language")],
     [],
     "which proprietary engine held the HFT desk's nanosecond ticks",
     "high frequency trade nano second tick column mmap latency"),
    # --- 18 ---
    ("OpenTSDB on HBase was retired from the ops stack in 2026-02-18; the HBase operational burden outweighed any benefit over VictoriaMetrics for the 200k-series fleet.", "decision", "technical", False,
     [("OpenTSDB", "database"), ("HBase", "database"), ("VictoriaMetrics", "database"), ("2026-02-18", "date")],
     [("VictoriaMetrics", "OpenTSDB", "REPLACES")],
     "when was OpenTSDB retired and which engine absorbed its series",
     "retire HBase operational burden series fleet swap engine date"),
    # --- 19 ---
    ("M3DB backed Uber's metrics platform reference; the index sharding plus tag-based query model informed the tag cardinality budgets on our smaller setup.", "reference", "technical", False,
     [("M3DB", "database"), ("Uber", "organization")],
     [],
     "which reference architecture shaped the tag cardinality budgeting",
     "reference tag cardinality index shard budget inform plan"),
    # --- 20 ---
    ("Grafana Mimir on object storage replaced the standalone Prometheus pair for long-term retention; horizontally scalable ingesters beat vertical scaling on the primary pair.", "decision", "technical", False,
     [("Grafana Mimir", "database"), ("Prometheus", "database")],
     [("Grafana Mimir", "Prometheus", "REPLACES")],
     "which long-term store absorbed the Prometheus pair's retention role",
     "horizontal scale ingester object storage long term retention swap"),
    # --- 21 ---
    ("Thanos Compactor downsampling to 5-minute and 1-hour resolutions was preferred over raw retention bumps; year-old queries answered from 1-hour blocks in seconds.", "preference", "technical", False,
     [("Thanos Compactor", "tool")],
     [],
     "which Thanos tool collapsed year-old query latency via downsampling",
     "downsample resolution minute hour year query block swap"),
    # --- 22 ---
    ("Retention policies on InfluxDB 1.8 were set to 30 days raw and 2 years at 1-minute rollup; the continuous query wrote into the downsampled measurement nightly.", "architecture", "technical", False,
     [("InfluxDB 1.8", "database"), ("continuous query", "concept")],
     [],
     "which InfluxDB retention setup fed the long-term rollup measurement",
     "retention policy raw minute rollup continuous query nightly"),
    # --- 23 ---
    ("Shard-by-time scheme on the TimescaleDB hypertable used a 7-day chunk interval on the archival tier; drop_chunks() retired old chunks without VACUUM churn.", "architecture", "technical", False,
     [("TimescaleDB", "database"), ("hypertable", "concept")],
     [],
     "which sharding scheme retired archival chunks without VACUUM churn",
     "shard time seven day archive chunk drop retire vacuum avoid"),
    # --- 24 ---
    ("Prometheus remote-write shipped the scrape results to the central VictoriaMetrics cluster; the local TSDB kept only a 2-hour window for debugging.", "architecture", "technical", False,
     [("Prometheus", "database"), ("remote-write", "protocol"), ("VictoriaMetrics", "database"), ("TSDB", "database")],
     [],
     "which protocol shipped Prometheus scrapes to the central cluster",
     "remote write central cluster local window debug scrape ship"),
    # --- 25 ---
    ("OTLP metrics over the OpenTelemetry Collector replaced direct StatsD shipping on the mobile backend; native histograms made p99 bucket error disappear.", "decision", "technical", False,
     [("OTLP", "protocol"), ("OpenTelemetry Collector", "tool"), ("StatsD", "protocol")],
     [("OTLP", "StatsD", "REPLACES")],
     "which metrics protocol took over StatsD on the mobile backend",
     "OTLP collector native histogram bucket p99 error swap metric"),
    # --- 26 ---
    ("Gap-filling with time_bucket_gapfill on TimescaleDB handled the missing-sample dashboard panels; LOCF filled blanks without inventing fake values.", "architecture", "technical", False,
     [("time_bucket_gapfill", "method"), ("TimescaleDB", "database"), ("LOCF", "concept")],
     [],
     "which TimescaleDB function filled dashboard gaps with last-observation carry",
     "gap fill bucket last observation carry missing sample panel"),
    # --- 27 ---
    ("ZSTD level 6 replaced Snappy compression on the ClickHouse time-series columns; disk usage fell 34 percent and CPU stayed under the 60 percent budget.", "decision", "technical", False,
     [("ZSTD", "technology"), ("Snappy", "technology"), ("ClickHouse", "database")],
     [("ZSTD", "Snappy", "REPLACES")],
     "which compression codec displaced Snappy on the ClickHouse TS columns",
     "ZSTD level Snappy column compression disk CPU budget swap"),
    # --- 28 ---
    ("Grafana panel tuning set max_data_points to 500 and used the $__interval macro; the dashboard stopped pulling 40k points through the browser on each load.", "milestone", "technical", False,
     [("Grafana", "tool")],
     [],
     "which Grafana knob stopped the dashboard from pulling 40k points per load",
     "max data points interval macro panel tune browser load cut"),
    # --- 29 ---
    ("VictoriaLogs was added next to VictoriaMetrics for the log pipeline; the LogsQL language shared the label model and avoided a second operational skill tree.", "architecture", "technical", False,
     [("VictoriaLogs", "database"), ("VictoriaMetrics", "database"), ("LogsQL", "language")],
     [],
     "which log engine shared the VictoriaMetrics label model on the pipeline",
     "logs label model share skill tree language same operate"),
    # --- 30 ---
    ("VictoriaMetrics replaced Thanos for the single-cluster setup; the 7-way smaller RAM footprint meant the dev environment ran on a 4 GB node.", "decision", "technical", False,
     [("VictoriaMetrics", "database"), ("Thanos", "tool")],
     [("VictoriaMetrics", "Thanos", "REPLACES")],
     "which engine took over Thanos on the smaller single-cluster setup",
     "RAM footprint small dev node small cluster swap engine"),
    # --- 31 ---
    ("QuestDB Line Protocol ingest over UDP was preferred over HTTP on the local pipeline; batched commits at 200 ms tick matched the ingest rate cleanly.", "preference", "technical", False,
     [("QuestDB", "database"), ("Line Protocol", "protocol"), ("UDP", "protocol")],
     [],
     "which QuestDB ingest path beat HTTP on the local tick pipeline",
     "UDP HTTP batch commit interval tick rate line protocol"),
    # --- 32 ---
    ("InfluxDB 2.x cardinality explosion hit the Kubernetes pod label set; the pod_name tag added 120k series per day and broke the TSI index.", "problem", "technical", False,
     [("InfluxDB 2.x", "database"), ("Kubernetes", "technology"), ("TSI", "technology")],
     [],
     "which cardinality source broke the TSI index on the InfluxDB 2.x fleet",
     "cardinality explode pod label tag series break index fleet"),
    # --- 33 ---
    ("Kapacitor for InfluxDB alerting was rejected on maintenance cost; Grafana Alerting on the same dashboards covered the rule set with no second agent.", "decision", "technical", False,
     [("Kapacitor", "tool"), ("InfluxDB", "database"), ("Grafana Alerting", "service")],
     [("Grafana Alerting", "Kapacitor", "REPLACES")],
     "which alerting path retired Kapacitor on the InfluxDB stack",
     "alerting maintenance cost rule dashboard agent swap retire"),
    # --- 34. noise ---
    ("Hang on, backfill window's still compacting chunks.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Druid segment size tuning set target_rows_per_segment to 5 million on the ad-tech cluster; broker fan-out dropped and p95 query fell from 4.1 s to 900 ms.", "milestone", "technical", False,
     [("Druid", "database")],
     [],
     "which Druid knob pulled the ad-tech p95 query under one second",
     "segment size target row broker fan out p95 query drop tune"),
    # --- 36 ---
    ("Apache Pinot star-tree index replaced the sum-on-the-fly scan path for the dashboards; pre-aggregated rows cut query latency by 12x on the revenue cube.", "decision", "technical", False,
     [("Apache Pinot", "database"), ("star-tree", "technology"), ("sum-on-the-fly scan", "pattern")],
     [("star-tree", "sum-on-the-fly scan", "REPLACES")],
     "which Pinot index killed the sum-on-the-fly path for the revenue cube",
     "star tree index pre aggregate revenue cube latency cut swap"),
    # --- 37 ---
    ("Prometheus exemplars were enabled on the histogram metrics; linking a slow request trace from the latency bucket to Tempo saved 20 minutes per incident.", "milestone", "technical", False,
     [("Prometheus", "database"), ("exemplars", "concept"), ("Tempo", "tool")],
     [],
     "which Prometheus feature linked histogram buckets to a Tempo trace",
     "exemplar histogram bucket trace link incident minute save"),
    # --- 38 ---
    ("OpenTSDB wire protocol support stayed on the VictoriaMetrics ingress to avoid a client rewrite; legacy collectors on embedded boards shipped unchanged.", "architecture", "technical", False,
     [("OpenTSDB", "database"), ("VictoriaMetrics", "database")],
     [],
     "which VictoriaMetrics ingress kept the embedded collectors unchanged",
     "wire protocol legacy collector embedded board ship unchanged"),
    # --- 39 ---
    ("Native histograms on Prometheus 2.48 replaced the classic le-bucket histograms on the latency SLO; cardinality fell 18x with better quantile accuracy.", "decision", "technical", False,
     [("Prometheus 2.48", "database"), ("Native histograms", "concept"), ("le-bucket histograms", "concept")],
     [("Native histograms", "le-bucket histograms", "REPLACES")],
     "which Prometheus histogram flavor replaced the le-bucket classic one",
     "native histogram bucket quantile cardinality SLO swap accuracy"),
    # --- 40 ---
    ("TimescaleDB compression policy on the hypertable compressed chunks older than 7 days; columnar format trimmed disk from 1.2 TB to 180 GB in the first week.", "milestone", "technical", False,
     [("TimescaleDB", "database"), ("hypertable", "concept")],
     [],
     "which TimescaleDB policy shrank the disk footprint by nearly 7x",
     "compression policy chunk age columnar format disk week trim"),
    # --- 41 ---
    ("InfluxDB 3 Parquet files on S3 replaced the local TSM disk tier; cold queries landed in 1.8 s and storage cost dropped to 20 percent of the EBS bill.", "decision", "technical", False,
     [("InfluxDB 3", "database"), ("Parquet", "technology"), ("S3", "service"), ("TSM", "technology"), ("EBS", "service")],
     [("Parquet", "TSM", "REPLACES")],
     "which storage tier replaced TSM on disk and trimmed the EBS bill",
     "Parquet S3 cold query storage cost EBS bill tier swap"),
    # --- 42 ---
    ("Carbon-C-Relay still front-ended the Graphite cluster for the finance team; it was preferred over rewriting collectors to remote-write for a frozen dataset.", "preference", "technical", False,
     [("Carbon-C-Relay", "tool"), ("Graphite", "database")],
     [],
     "which relay kept the frozen Graphite dataset untouched for finance",
     "relay front end frozen dataset collector rewrite avoid team"),
    # --- 43 ---
    ("Cortex was deprecated in favor of Grafana Mimir on the shared-tenant cluster; the hard-fork lineage meant migration was a binary swap plus config port.", "decision", "technical", False,
     [("Cortex", "database"), ("Grafana Mimir", "database")],
     [("Grafana Mimir", "Cortex", "REPLACES")],
     "which long-term TSDB replaced Cortex on the shared-tenant cluster",
     "hard fork lineage migration binary config port swap tenant"),
    # --- 44 ---
    ("Grafana Tempo was kept separate from the metrics TSDB; traces and metrics shared labels via exemplars but stayed in different storage engines on purpose.", "architecture", "technical", False,
     [("Grafana Tempo", "tool"), ("exemplars", "concept")],
     [],
     "which architectural choice kept traces and metrics in separate engines",
     "trace metric storage separate engine label exemplar bridge"),
    # --- 45 ---
    ("VictoriaMetrics vmagent replaced the Prometheus scraper on the edge boxes; remote-write compression and disk-backed queue survived 6-hour network outages.", "decision", "technical", False,
     [("vmagent", "tool"), ("Prometheus", "database"), ("VictoriaMetrics", "database")],
     [("vmagent", "Prometheus", "REPLACES")],
     "which agent replaced the Prometheus scraper on the edge boxes",
     "remote write compression disk queue outage survive edge agent"),
    # --- 46 ---
    ("InfluxDB Flux task retries were capped at 3 with a 90-second backoff; the upstream API's flaky 502s stopped poisoning the bucket with partial windows.", "architecture", "technical", False,
     [("Flux", "language"), ("InfluxDB", "database")],
     [],
     "which Flux task setting stopped the partial-window poisoning",
     "task retry backoff flaky upstream partial window bucket guard"),
    # --- 47 ---
    ("Percentile aggregations on the TDigest extension of TimescaleDB beat exact percentile queries for the SLO dashboards; error stayed under 0.5 percent at the p99.", "decision", "technical", False,
     [("TDigest", "technology"), ("TimescaleDB", "database"), ("exact percentile", "method")],
     [("TDigest", "exact percentile", "IMPROVES_ON")],
     "which TimescaleDB extension replaced exact percentiles on the SLO board",
     "TDigest percentile approximate accuracy SLO p99 swap query"),
    # --- 48 ---
    ("QuestDB SYMBOL columns stored the high-cardinality instrument tags; interning the string once cut the on-disk size by 11x versus VARCHAR.", "architecture", "technical", False,
     [("QuestDB", "database"), ("SYMBOL", "technology")],
     [],
     "which QuestDB column type shrank the instrument tag storage",
     "symbol intern string cardinality disk size instrument column"),
    # --- 49 ---
    ("Prometheus WAL corruption hit the blackbox_exporter node after a sudden power loss; the recovery flag --storage.tsdb.wal-compression=false let the block load past the torn record.", "problem", "technical", False,
     [("Prometheus", "database"), ("WAL", "technology"), ("blackbox_exporter", "tool")],
     [],
     "which Prometheus recovery flag cleared the torn WAL record block",
     "WAL torn record recovery flag power loss load past block"),
    # --- 50 ---
    ("Grafana Mimir ruler replaced the standalone Prometheus rule evaluator on 2026-03-07; rule groups scaled horizontally and the evaluator lag dropped under 2 seconds.", "milestone", "technical", False,
     [("Grafana Mimir", "database"), ("Prometheus", "database"), ("2026-03-07", "date")],
     [("Grafana Mimir", "Prometheus", "REPLACES")],
     "when did Mimir ruler replace the standalone Prometheus evaluator",
     "ruler rule group horizontal scale evaluator lag date swap"),
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
