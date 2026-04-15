"""One-off emitter for shared-base batch-127 — technical domain (observability platforms slice).

Writes 50 rows to data/v2/shared/batch_127.tmp.jsonl with ids shared-06301..06350.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_127.tmp.jsonl"
ID_OFFSET = 6300

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Grafana Mimir replaced Cortex on the metrics cluster; the simpler deploy and the unified ingester eased a painful 80-tenant upgrade path.", "decision", "technical", False,
     [("Grafana Mimir", "service"), ("Cortex", "service")],
     [("Grafana Mimir", "Cortex", "REPLACES")],
     "which time series backend took over from Cortex on the metrics cluster",
     "Mimir Cortex tenant upgrade unified ingester swap"),
    # --- 2 ---
    ("Grafana Tempo replaced Jaeger for distributed tracing; the object-store-only design cut the trace backend's memory footprint from 90 GB to 12 GB.", "decision", "technical", False,
     [("Grafana Tempo", "service"), ("Jaeger", "tool")],
     [("Grafana Tempo", "Jaeger", "REPLACES")],
     "which tracing backend displaced Jaeger and what cut the footprint",
     "Tempo Jaeger object store trace memory footprint drop"),
    # --- 3 ---
    ("Honeycomb replaced Datadog APM on the high-cardinality checkout path; per-user_id dimension slicing stopped getting aggregated away into the custom metric cap.", "decision", "technical", False,
     [("Honeycomb", "service"), ("Datadog APM", "service")],
     [("Honeycomb", "Datadog APM", "REPLACES")],
     "which observability tool took over from Datadog APM for high cardinality",
     "Honeycomb Datadog APM cardinality user id slice checkout"),
    # --- 4 ---
    ("Grafana Beyla improves_on manual OpenTelemetry SDK instrumentation for the Go services; eBPF auto-instrumented HTTP spans without a single code change.", "decision", "technical", False,
     [("Grafana Beyla", "tool"), ("OpenTelemetry", "framework"), ("Go", "language"), ("eBPF", "technology")],
     [("Grafana Beyla", "OpenTelemetry", "IMPROVES_ON")],
     "which eBPF tool trimmed the manual OTel SDK work on the Go services",
     "Beyla eBPF auto instrument Go HTTP span no code change"),
    # --- 5 ---
    ("BubbleUp on Honeycomb isolated the outlier pod in 40 seconds; the high-cardinality attribute search beat a classic Datadog facet drill by roughly an order of magnitude.", "milestone", "technical", False,
     [("BubbleUp", "tool"), ("Honeycomb", "service"), ("Datadog", "service")],
     [("BubbleUp", "Datadog", "IMPROVES_ON")],
     "which Honeycomb feature localized the outlier pod under a minute",
     "BubbleUp outlier pod isolate facet drill cardinality"),
    # --- 6 ---
    ("Loki replaced the ELK stack for application log ingestion; label-indexed storage dropped the monthly compute bill from 11k to under 2k dollars.", "decision", "technical", False,
     [("Loki", "service"), ("ELK", "service")],
     [("Loki", "ELK", "REPLACES")],
     "which log backend took over from ELK for application logs",
     "Loki ELK label index log backend compute bill cut"),
    # --- 7 ---
    ("VictoriaMetrics was benchmarked against Prometheus remote write at 3 million samples per second; ingest fell to 40 percent of the Prometheus CPU under identical cardinality.", "fact", "technical", False,
     [("VictoriaMetrics", "service"), ("Prometheus", "service")],
     [],
     "which metrics backend halved CPU under the 3M samples per second load",
     "VictoriaMetrics Prometheus ingest CPU benchmark cardinality"),
    # --- 8 ---
    ("Thanos sidecar fanout stitched Prometheus HA pairs into a global query layer; compactor downsampling kept 2-year retention under 4 TB per tenant.", "architecture", "technical", False,
     [("Thanos", "service"), ("Prometheus", "service")],
     [],
     "which Thanos component stitched the HA Prometheus pairs into a global view",
     "Thanos sidecar fanout compactor downsample retention global"),
    # --- 9 ---
    ("Chronosphere was preferred over Datadog on the pricing side for the metrics contract; per-metric shaping cut retained series by 60 percent pre-bill.", "preference", "technical", False,
     [("Chronosphere", "service"), ("Datadog", "service")],
     [("Chronosphere", "Datadog", "PREFERS")],
     "which metrics vendor beat Datadog on the retained series pricing model",
     "Chronosphere Datadog shape series retain bill preference"),
    # --- 10. noise ---
    ("Hold on, the dashboard is still loading panels.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("SigNoz replaced a self-hosted Jaeger plus Prometheus pair on the staging cluster; a single OTel-native UI handled traces, metrics, and logs together.", "decision", "technical", False,
     [("SigNoz", "service"), ("Jaeger", "tool"), ("Prometheus", "service"), ("OTel", "framework")],
     [("SigNoz", "Jaeger", "REPLACES")],
     "which unified backend took over from the Jaeger plus Prometheus pair",
     "SigNoz Jaeger Prometheus OTel unified UI trace log metric"),
    # --- 12 ---
    ("Dynatrace OneAgent was installed on the 400-host legacy estate; auto-discovery of Oracle and IBM MQ dependencies beat the manual Prometheus exporter slog.", "architecture", "technical", False,
     [("Dynatrace OneAgent", "tool"), ("Oracle", "database"), ("IBM MQ", "service"), ("Prometheus", "service")],
     [("Dynatrace OneAgent", "Prometheus", "IMPROVES_ON")],
     "which agent handled auto-discovery across the 400-host legacy estate",
     "Dynatrace OneAgent Oracle IBM MQ discover exporter legacy"),
    # --- 13 ---
    ("Splunk Observability Cloud covered the enterprise SOC feed; the MTS pricing and the SPL parity with Splunk Enterprise mattered more than raw ingest speed.", "decision", "technical", False,
     [("Splunk Observability Cloud", "service"), ("SPL", "language"), ("Splunk Enterprise", "service")],
     [],
     "which Splunk offering fed the enterprise SOC with SPL parity preserved",
     "Splunk Observability SPL enterprise SOC MTS ingest feed"),
    # --- 14 ---
    ("Elastic Observability consolidated the APM, log, and uptime dashboards on a single ECS; the Kibana Lens migration wiped out six Grafana instances.", "milestone", "technical", False,
     [("Elastic Observability", "service"), ("ECS", "framework"), ("Kibana Lens", "tool"), ("Grafana", "tool")],
     [("Elastic Observability", "Grafana", "REPLACES")],
     "which Elastic UI retired six Grafana instances during the consolidation",
     "Elastic Kibana Lens ECS consolidate Grafana retire dashboard"),
    # --- 15 ---
    ("New Relic One absorbed the mobile-plus-backend RUM story; distributed tracing across the Swift app and the Node origin landed without a custom SDK bridge.", "architecture", "technical", False,
     [("New Relic One", "service"), ("Swift", "language"), ("Node", "technology")],
     [],
     "which platform bridged Swift mobile RUM and the Node origin traces",
     "New Relic One mobile RUM Swift Node distributed trace bridge"),
    # --- 16 ---
    ("AWS CloudWatch Contributor Insights replaced a custom Athena-on-S3 log parser for the top-talkers query; the rule syntax matched the log format without ETL.", "decision", "technical", False,
     [("AWS CloudWatch Contributor Insights", "service"), ("Athena", "service"), ("S3", "service")],
     [("AWS CloudWatch Contributor Insights", "Athena", "REPLACES")],
     "which AWS feature took over from the Athena-on-S3 top talkers job",
     "CloudWatch Contributor Insights Athena S3 top talker rule"),
    # --- 17 ---
    ("CloudWatch Metric Streams to Kinesis Firehose pushed AWS metrics into Mimir; the pull-based Prometheus exporter was retired as the lag stayed under 20 seconds.", "architecture", "technical", False,
     [("CloudWatch Metric Streams", "service"), ("Kinesis Firehose", "service"), ("Mimir", "service"), ("Prometheus", "service")],
     [("CloudWatch Metric Streams", "Prometheus", "REPLACES")],
     "which streaming path replaced the pull-based exporter for AWS metrics",
     "CloudWatch Metric Stream Kinesis Firehose Mimir push exporter"),
    # --- 18 ---
    ("OpenSearch Observability ran on the AWS-managed cluster for the security-log lake; Piped Processing Language queries replaced a pile of Lucene syntax cheatsheets.", "decision", "technical", False,
     [("OpenSearch Observability", "service"), ("AWS", "organization"), ("Piped Processing Language", "language"), ("Lucene", "technology")],
     [("Piped Processing Language", "Lucene", "REPLACES")],
     "which query language took over from Lucene in the OpenSearch lake",
     "OpenSearch PPL Lucene query security log lake managed"),
    # --- 19 ---
    ("Alertmanager's inhibition rules silenced downstream alerts during the upstream database outage; pager volume dropped from 230 pages to 4 during the 90-minute event.", "milestone", "technical", False,
     [("Alertmanager", "service")],
     [],
     "which Alertmanager feature cut the 230 pages down to 4 during the outage",
     "Alertmanager inhibition silence downstream outage page volume"),
    # --- 20 ---
    ("Prometheus recording rules pre-aggregated the per-pod histograms nightly; the p99 dashboard query dropped from 14 seconds to under 400 ms.", "decision", "technical", False,
     [("Prometheus", "service")],
     [],
     "which Prometheus trick cut the p99 dashboard query under half a second",
     "Prometheus recording rule pre aggregate histogram p99 speed"),
    # --- 21 ---
    ("Tail-based sampling on the Tempo collector kept 100 percent of error traces and 5 percent of happy-path traces; head-based sampling's blind coin-flip had already dropped the critical 500s.", "decision", "technical", False,
     [("Tempo", "service")],
     [],
     "which sampling strategy kept every error trace while cutting happy path",
     "tail based sampling error trace head coin flip collector"),
    # --- 22 ---
    ("Head-based sampling stayed on the high-volume edge service; the OpenTelemetry Collector could not afford tail-based buffering under the 80k spans per second firehose.", "decision", "technical", False,
     [("OpenTelemetry Collector", "service")],
     [],
     "which sampling mode stayed on the 80k spans per second edge service",
     "head based sampling edge volume buffer span rate decide"),
    # --- 23 ---
    ("Honeycomb SLOs were defined on the 30-day burn-rate window for the login endpoint; the two-window alert suppressed the noisy 1-hour flaps that PagerDuty hated.", "architecture", "technical", False,
     [("Honeycomb", "service"), ("PagerDuty", "service")],
     [],
     "which SLO alert configuration stopped the 1-hour login flap pages",
     "Honeycomb SLO burn rate window two window flap suppress"),
    # --- 24 ---
    ("Grafana dashboards-as-JSON lived in the repo beside the Terraform modules; CI validated the panel schema on every PR, killing the last click-ops drift source.", "decision", "technical", False,
     [("Grafana", "tool"), ("Terraform", "tool")],
     [],
     "which workflow killed click-ops drift on the Grafana dashboards",
     "dashboard as code JSON repo CI schema validate drift kill"),
    # --- 25 ---
    ("Grafana dashboards-as-code via Grafonnet generated the per-service panel grid from a single Jsonnet template; duplicated JSON blobs across 120 services vanished.", "decision", "technical", False,
     [("Grafana", "tool"), ("Grafonnet", "framework"), ("Jsonnet", "language")],
     [("Grafonnet", "Grafana", "BUILDS_ON")],
     "which template tool collapsed 120 per-service dashboard JSONs",
     "Grafonnet Jsonnet template panel grid duplicate dashboard"),
    # --- 26 ---
    ("Pixie ran eBPF-based auto-tracing on the GKE cluster; PxL scripts gave L7 HTTP latency per pod without a sidecar proxy.", "architecture", "technical", False,
     [("Pixie", "tool"), ("eBPF", "technology"), ("GKE", "service"), ("PxL", "language")],
     [],
     "which eBPF observability tool gave per-pod L7 latency on GKE",
     "Pixie eBPF PxL GKE L7 latency per pod sidecar avoid"),
    # --- 27 ---
    ("Parca provided always-on continuous profiling via eBPF; the 90-day flamegraph history caught a slow 2 percent CPU regression no benchmark had flagged.", "milestone", "technical", False,
     [("Parca", "tool"), ("eBPF", "technology")],
     [],
     "which profiler caught the slow CPU regression benchmarks had missed",
     "Parca continuous profile eBPF flamegraph regression catch"),
    # --- 28 ---
    ("Grafana Pyroscope replaced Parca as the profiling backend; tight integration with the Grafana UI and Loki logs-to-profile linking won on UX.", "decision", "technical", False,
     [("Grafana Pyroscope", "service"), ("Parca", "tool"), ("Grafana", "tool"), ("Loki", "service")],
     [("Grafana Pyroscope", "Parca", "REPLACES")],
     "which profiling backend took over from Parca on the Grafana stack",
     "Pyroscope Parca profile UI log link integration swap"),
    # --- 29 ---
    ("OpenTelemetry Collector fan-out split traces to Tempo and metrics to Mimir; a single agent config replaced three vendor-specific SDKs in the node runtime.", "architecture", "technical", False,
     [("OpenTelemetry Collector", "service"), ("Tempo", "service"), ("Mimir", "service")],
     [],
     "which collector fanned out traces and metrics to Tempo and Mimir",
     "OTel collector fanout Tempo Mimir vendor SDK retire config"),
    # --- 30 ---
    ("Exemplar links on Grafana panels jumped from a histogram bucket straight into the matching Tempo trace; mean time to root-cause a latency spike fell from 15 minutes to 90 seconds.", "milestone", "technical", False,
     [("Grafana", "tool"), ("Tempo", "service")],
     [],
     "which Grafana feature cut root-cause time on latency spikes under 2 min",
     "exemplar panel histogram Tempo trace MTTR latency drill"),
    # --- 31 ---
    ("Grafana OnCall replaced PagerDuty as the paging router for the platform team; rotation schedules stayed in code and the bill dropped by 8k a month.", "decision", "technical", False,
     [("Grafana OnCall", "service"), ("PagerDuty", "service")],
     [("Grafana OnCall", "PagerDuty", "REPLACES")],
     "which paging router took over from PagerDuty for the platform team",
     "Grafana OnCall PagerDuty rotation code bill monthly swap"),
    # --- 32 ---
    ("Datadog Watchdog surfaced the MySQL connection-pool saturation before a human looked at the dashboard; anomaly detection flagged the p95 trend 12 minutes ahead.", "fact", "technical", False,
     [("Datadog Watchdog", "tool"), ("MySQL", "database")],
     [],
     "which Datadog feature flagged the MySQL pool trend 12 minutes early",
     "Datadog Watchdog anomaly MySQL pool saturation p95 detect"),
    # --- 33 ---
    ("New Relic CodeStream was rejected for the incident workflow; the repo-linked comments duplicated what the Slack channel already tracked and confused reviewers.", "decision", "technical", False,
     [("New Relic CodeStream", "service"), ("Slack", "service")],
     [],
     "which New Relic add-on was dropped because it overlapped with Slack",
     "CodeStream incident repo comment Slack duplicate reject"),
    # --- 34. noise ---
    ("Anyway, the alert just cleared on its own.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Service-level commitments on the checkout API targeted a 99.9 percent 30-day availability and a p95 under 250 ms; the error budget drove the freeze policy more than any gut feel.", "decision", "technical", False,
     [("checkout API", "service")],
     [],
     "which SLO targets drove the checkout API freeze policy",
     "service level commitment checkout budget freeze availability p95"),
    # --- 36 ---
    ("Error-budget burn alerts on Honeycomb fired on the 2-hour and 6-hour windows together; single-window alerts had previously missed a slow 3-percent burn that ate half the month.", "decision", "technical", False,
     [("Honeycomb", "service")],
     [],
     "which alert config caught the slow burn single windows had missed",
     "error budget burn two window slow single window miss month"),
    # --- 37 ---
    ("Tempo metrics-generator produced RED signals straight from trace spans; the manual Prometheus RED exporter on 40 services was retired in a single sprint.", "decision", "technical", False,
     [("Tempo", "service"), ("Prometheus", "service")],
     [("Tempo", "Prometheus", "REPLACES")],
     "which Tempo feature retired the manual RED exporter across 40 services",
     "Tempo metrics generator RED signal span exporter retire"),
    # --- 38 ---
    ("Mimir's per-tenant query limits improves_on the Cortex single-knob approach; the platform team carved heavy BI users off without touching interactive dashboards.", "decision", "technical", False,
     [("Mimir", "service"), ("Cortex", "service")],
     [("Mimir", "Cortex", "IMPROVES_ON")],
     "which Mimir feature isolated BI users without hurting dashboards",
     "Mimir per tenant query limit Cortex single knob isolate BI"),
    # --- 39 ---
    ("Grafana Agent Flow replaced the classic Prometheus agent on the EKS fleet; the component graph exposed per-target scrape durations straight in the UI.", "decision", "technical", False,
     [("Grafana Agent Flow", "tool"), ("Prometheus", "service"), ("EKS", "service")],
     [("Grafana Agent Flow", "Prometheus", "REPLACES")],
     "which agent took over from the classic Prometheus agent on EKS",
     "Grafana Agent Flow component graph scrape duration EKS"),
    # --- 40 ---
    ("Grafana Alloy unified the Agent Flow and Promtail footprints; a single binary shipped metrics, logs, and traces with one config per node.", "decision", "technical", False,
     [("Grafana Alloy", "tool"), ("Agent Flow", "tool"), ("Promtail", "tool")],
     [("Grafana Alloy", "Promtail", "REPLACES")],
     "which collector unified Agent Flow and Promtail on each node",
     "Grafana Alloy Agent Flow Promtail unify binary node config"),
    # --- 41 ---
    ("Loki's bloom filters for label-free lookups improves_on the naive full-chunk scan; a needle-in-haystack trace ID lookup on 30 days of logs finished in 8 seconds instead of 4 minutes.", "decision", "technical", False,
     [("Loki", "service")],
     [],
     "which Loki feature cut the trace-ID lookup from minutes to seconds",
     "Loki bloom filter label free trace ID lookup haystack"),
    # --- 42 ---
    ("SigNoz was rejected for the regulated SaaS tenant; single-tenant ClickHouse deployment per customer blew past the ops budget the team had for observability.", "decision", "technical", False,
     [("SigNoz", "service"), ("ClickHouse", "database")],
     [],
     "which observability stack lost on the regulated multi-tenant SaaS plan",
     "SigNoz ClickHouse single tenant deploy ops budget reject"),
    # --- 43 ---
    ("Datadog's Flex Logs tier replaced an S3-plus-Athena cold-log archive; query latency on the 90-day tail dropped from minutes to seconds without re-rehydration.", "decision", "technical", False,
     [("Datadog", "service"), ("S3", "service"), ("Athena", "service")],
     [("Datadog", "Athena", "REPLACES")],
     "which Datadog tier took over from the S3-plus-Athena cold log archive",
     "Datadog Flex Logs tier S3 Athena cold archive rehydrate"),
    # --- 44 ---
    ("Honeycomb's events model improves_on aggregate metrics on debugability; a single wide event with 200 columns beat 40 curated Grafana dashboards for interactive root cause.", "preference", "technical", False,
     [("Honeycomb", "service"), ("Grafana", "tool")],
     [("Honeycomb", "Grafana", "IMPROVES_ON")],
     "which observability model beat curated dashboards on interactive RCA",
     "Honeycomb wide event column aggregate metric debug interactive"),
    # --- 45 ---
    ("The OpenTelemetry semantic conventions 1.25 reference drove the span attribute audit; http.route and db.system renames wiped a week of Grafana query breakage.", "reference", "technical", False,
     [("OpenTelemetry", "framework"), ("Grafana", "tool")],
     [],
     "which OTel reference document guided the span attribute audit",
     "OpenTelemetry semantic convention span attribute audit rename"),
    # --- 46 ---
    ("Honeycomb's SLO burn-rate dashboard preference was keeping 1-hour and 6-hour together on the same panel; single-window ones had missed the long, slow checkout degradation.", "preference", "technical", False,
     [("Honeycomb", "service")],
     [],
     "which burn-rate dashboard layout beat the single-window alternative",
     "Honeycomb SLO burn rate dashboard one hour six hour layout"),
    # --- 47 ---
    ("Mimir ingested Graphite metrics through the graphite-write path; the legacy StatsD forwarders kept working while the wider Prometheus rewrite rolled out.", "architecture", "technical", False,
     [("Mimir", "service"), ("Graphite", "service"), ("StatsD", "tool"), ("Prometheus", "service")],
     [],
     "which Mimir path kept the StatsD plus Graphite forwarders alive",
     "Mimir Graphite StatsD forwarder ingest migration bridge"),
    # --- 48 ---
    ("Cilium Hubble traced service-to-service flows on the Kubernetes cluster; the eBPF-powered flow log cut a mystery egress leak to the source pod in 10 minutes.", "milestone", "technical", False,
     [("Cilium Hubble", "tool"), ("eBPF", "technology"), ("Kubernetes", "platform")],
     [],
     "which eBPF flow tool localized the mystery egress leak in 10 minutes",
     "Cilium Hubble eBPF flow log egress leak pod source find"),
    # --- 49 ---
    ("OpenTelemetry SDK for Python replaced the Datadog tracer on the Django monolith; vendor-neutral spans meant moving to Grafana Tempo needed zero app changes.", "decision", "technical", False,
     [("OpenTelemetry", "framework"), ("Python", "language"), ("Datadog", "service"), ("Django", "framework"), ("Grafana Tempo", "service")],
     [("OpenTelemetry", "Datadog", "REPLACES")],
     "which tracing SDK took over from the Datadog tracer on the Django app",
     "OpenTelemetry Python Datadog Django vendor neutral span swap"),
    # --- 50 ---
    ("Grafana Cloud trial started on 2026-03-18 with Mimir, Loki, and Tempo bundled; the 4-day self-hosted-to-cloud migration beat the internal build-a-stack estimate by two quarters.", "milestone", "technical", False,
     [("Grafana Cloud", "service"), ("Mimir", "service"), ("Loki", "service"), ("Tempo", "service"), ("2026-03-18", "date")],
     [],
     "when did the Grafana Cloud trial start and how did the migration go",
     "Grafana Cloud trial Mimir Loki Tempo migration quarter save"),
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
