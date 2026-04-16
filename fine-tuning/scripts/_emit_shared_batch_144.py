"""One-off emitter for shared-base batch-144 — observability/telemetry domain (OpenTelemetry, Prometheus, Grafana, Loki, Tempo, Mimir, Jaeger, SLOs, structured logging).

Writes 50 rows to data/v2/shared/batch_144.tmp.jsonl with ids shared-07151..07200.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_144.tmp.jsonl"
ID_OFFSET = 7150

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Swapped the Jaeger all-in-one for Tempo backed by S3 object storage; span retention jumped from three days to thirty without a matching jump in the monthly infra bill.", "decision", "technical", False,
     [("Jaeger", "service"), ("Tempo", "service"), ("S3", "service")],
     [("Tempo", "Jaeger", "REPLACES"), ("Tempo", "S3", "USES")],
     "which tracing backend replaced Jaeger all-in-one and what storage tier unlocked the longer retention",
     "tempo jaeger s3 span retention trace storage swap backend"),
    # --- 2 ---
    ("Standardised on the OpenTelemetry Collector as the single ingest hop for traces, metrics, and logs; the old fan-out of Promtail, Fluent Bit, and a bespoke OTLP shim got retired.", "architecture", "technical", False,
     [("OpenTelemetry Collector", "service"), ("Promtail", "service"), ("Fluent Bit", "service"), ("OTLP", "protocol")],
     [("OpenTelemetry Collector", "Promtail", "REPLACES"), ("OpenTelemetry Collector", "Fluent Bit", "REPLACES")],
     "which single agent consolidated the trace, metric, and log ingest path for the platform",
     "otel collector promtail fluent bit otlp ingest consolidate agent"),
    # --- 3 ---
    ("Prometheus federation was dropped in favour of remote_write to Mimir; the global scrape view now lives in one tenant and HA pairs deduplicate at ingest rather than at query time.", "milestone", "technical", False,
     [("Prometheus", "service"), ("Mimir", "service"), ("remote_write", "api")],
     [("Mimir", "Prometheus", "REPLACES"), ("Prometheus", "remote_write", "USES")],
     "which long-term storage replaced Prometheus federation and where does HA deduplication happen now",
     "prometheus mimir remote write federation ha dedup global view"),
    # --- 4 ---
    ("Pinned the Grafana Loki deployment to the simple scalable mode; microservices mode was overkill for a hundred gigabytes of daily log volume and doubled the operator workload.", "decision", "technical", False,
     [("Grafana Loki", "service"), ("simple scalable mode", "config"), ("microservices mode", "config")],
     [("simple scalable mode", "microservices mode", "REPLACES")],
     "which Loki deployment topology replaced microservices mode and what log volume justified the downgrade",
     "loki simple scalable microservices deployment log volume operator"),
    # --- 5 ---
    ("Alertmanager now routes by the severity label: critical paging PagerDuty, warning hitting Slack, and info archived to a webhook; the old flat receiver list lost dedup context on storms.", "architecture", "technical", False,
     [("Alertmanager", "service"), ("PagerDuty", "service"), ("Slack", "platform"), ("severity", "config")],
     [("Alertmanager", "PagerDuty", "COMMUNICATES_WITH"), ("Alertmanager", "Slack", "COMMUNICATES_WITH")],
     "how does alert routing now split critical paging from warning chat notifications",
     "alertmanager pagerduty slack severity route critical warning info"),
    # --- 6 ---
    ("Metric cardinality exploded after a deploy stamped a user_id label on http_requests_total; a relabel_config drop on the scrape side cut series count from eight million back to two hundred thousand.", "problem", "technical", False,
     [("http_requests_total", "config"), ("user_id", "config"), ("relabel_config", "config")],
     [("relabel_config", "user_id", "FIXES")],
     "which label stamped on http_requests_total blew up cardinality and how did the scrape config fix it",
     "metric cardinality user id label relabel config http requests series"),
    # --- 7 ---
    ("SLO for the checkout API is 99.9% success over a 28-day rolling window; the error-budget burn-rate alert fires on a 2% burn in one hour or 5% in six hours per the multi-window policy.", "reference", "technical", False,
     [("SLO", "concept"), ("checkout API", "service"), ("burn-rate alert", "pattern")],
     [("burn-rate alert", "SLO", "APPLIES_TO")],
     "what error-budget burn rates trigger the multi-window alert for the checkout API SLO",
     "slo checkout api burn rate budget 28 day window multi alert"),
    # --- 8 ---
    ("Exemplars were enabled on the histogram_quantile buckets so a spike in p99 latency on the Grafana panel links straight into the matching trace in Tempo without a manual time-range juggle.", "milestone", "technical", False,
     [("Exemplars", "concept"), ("histogram_quantile", "api"), ("Grafana", "service"), ("Tempo", "service")],
     [("Exemplars", "Tempo", "RELATED_TO")],
     "which Prometheus feature lets a Grafana p99 spike click through directly into the matching trace",
     "exemplar histogram quantile grafana tempo p99 latency click trace"),
    # --- 9 ---
    ("Honeycomb handles the high-cardinality request traces the team cares about; retained Prometheus for low-cardinality RED metrics because per-event pricing made it the wrong tool for request counters.", "decision", "technical", False,
     [("Honeycomb", "service"), ("Prometheus", "service"), ("RED metrics", "pattern")],
     [("Honeycomb", "Prometheus", "RELATED_TO")],
     "which observability stack split did the team adopt between high-cardinality events and RED metrics",
     "honeycomb prometheus red metric high cardinality event pricing split"),
    # --- 10. noise ---
    ("The office espresso machine grinder needs a new burr set and the spare hopper lid has been missing since the last all-hands.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("TraceQL filter `{resource.service.name=\"checkout\" && duration > 2s}` is pinned as the saved query for slow-checkout triage in the Grafana explore tab.", "reference", "technical", False,
     [("TraceQL", "language"), ("Grafana", "service"), ("checkout", "service")],
     [("TraceQL", "Grafana", "APPLIES_TO")],
     "which saved TraceQL filter is pinned in Grafana for slow checkout triage sessions",
     "traceql grafana checkout duration 2s slow trace filter saved"),
    # --- 12 ---
    ("LogQL query `{app=\"api\"} |= \"panic\" | json | line_format \"{{.err}}\"` drives the on-call panic-detector dashboard and paired with a rate() over one minute to feed the alert.", "reference", "technical", False,
     [("LogQL", "language"), ("json", "technology"), ("rate()", "api")],
     [("LogQL", "rate()", "USES")],
     "which LogQL pipeline powers the panic-detector dashboard and feeds the rate-based alert",
     "logql panic detect json line format rate alert on call dashboard"),
    # --- 13 ---
    ("PromQL rule `sum by (job) (rate(http_requests_total{status=~\"5..\"}[5m])) / sum by (job) (rate(http_requests_total[5m])) > 0.01` fires the error-rate SLO burn alert.", "reference", "technical", False,
     [("PromQL", "language"), ("http_requests_total", "config"), ("SLO", "concept")],
     [("PromQL", "SLO", "APPLIES_TO")],
     "which PromQL expression drives the error-rate SLO burn alert for HTTP five-hundred responses",
     "promql http requests total 5xx rate error slo burn alert rule"),
    # --- 14 ---
    ("Trace propagation headers were unified on W3C traceparent; the legacy B3 multi-header format got flipped off once the last Zipkin-only service was re-instrumented with the OTel SDK.", "milestone", "technical", False,
     [("W3C traceparent", "protocol"), ("B3", "protocol"), ("Zipkin", "service"), ("OTel SDK", "library")],
     [("W3C traceparent", "B3", "REPLACES"), ("Zipkin", "OTel SDK", "REPLACES")],
     "which trace-context header format replaced B3 and what SDK landed on the last Zipkin-only service",
     "w3c traceparent b3 zipkin otel sdk trace context propagation"),
    # --- 15 ---
    ("Spanmetrics connector in the OTel Collector emits RED metrics derived from ingested traces; the service-graph dashboards in Grafana now render without a separate Prometheus exporter per service.", "architecture", "technical", False,
     [("Spanmetrics", "pattern"), ("OTel Collector", "service"), ("RED metrics", "pattern"), ("service-graph", "pattern")],
     [("Spanmetrics", "OTel Collector", "USES"), ("service-graph", "Spanmetrics", "USES")],
     "how does the spanmetrics connector eliminate per-service Prometheus exporters for the service-graph view",
     "spanmetrics otel collector red service graph grafana exporter replace"),
    # --- 16 ---
    ("Structured logging was standardised on zap with a Production encoder for Go services; free-form fmt.Printf lines got banned in code review because they broke Loki label parsing downstream.", "decision", "technical", False,
     [("zap", "library"), ("Go", "language"), ("fmt.Printf", "api"), ("Loki", "service")],
     [("zap", "fmt.Printf", "REPLACES")],
     "which Go logging library replaced fmt.Printf for structured output compatible with Loki parsing",
     "zap structured log go fmt printf loki label parse production encoder"),
    # --- 17 ---
    ("Pyroscope continuous profiling was rolled out to the payment workers; a ten-second CPU profile every minute caught a sync.Mutex contention on the ledger write path that metrics missed.", "milestone", "technical", False,
     [("Pyroscope", "service"), ("payment workers", "service"), ("sync.Mutex", "api")],
     [("Pyroscope", "payment workers", "DEPLOYED_ON")],
     "which profiler deployed on payment workers exposed the sync.Mutex contention metrics could not see",
     "pyroscope payment worker sync mutex ledger profile cpu contention"),
    # --- 18 ---
    ("VictoriaMetrics replaced the self-hosted Thanos sidecar setup; the single-binary deploy dropped operator toil and the vmagent remote-write buffer survives a two-hour Mimir outage without dropping series.", "milestone", "technical", False,
     [("VictoriaMetrics", "service"), ("Thanos", "service"), ("vmagent", "service"), ("Mimir", "service")],
     [("VictoriaMetrics", "Thanos", "REPLACES"), ("vmagent", "Mimir", "COMMUNICATES_WITH")],
     "which TSDB replaced Thanos and what remote-write buffer keeps series during a Mimir outage",
     "victoriametrics thanos vmagent mimir remote write buffer outage single binary"),
    # --- 19 ---
    ("SigNoz got evaluated as a single-pane replacement for the Grafana+Tempo+Loki trio and rejected; ClickHouse operator toil outweighed the UI win for the current team size.", "decision", "technical", False,
     [("SigNoz", "service"), ("Grafana", "service"), ("Tempo", "service"), ("Loki", "service"), ("ClickHouse", "database")],
     [("SigNoz", "ClickHouse", "USES")],
     "which single-pane tool was evaluated against the Grafana Tempo Loki stack and why was it rejected",
     "signoz grafana tempo loki clickhouse evaluate reject operator toil"),
    # --- 20 ---
    ("Datadog APM is retained only for the mobile SDK traces because the on-device library is best-in-class; everything server-side was migrated off to the OTel + Tempo stack to cut the contract.", "decision", "technical", False,
     [("Datadog APM", "service"), ("mobile SDK", "library"), ("OTel", "library"), ("Tempo", "service")],
     [("Datadog APM", "mobile SDK", "APPLIES_TO")],
     "why did we retain Datadog APM only for mobile SDK traces after migrating server traces off",
     "datadog apm mobile sdk otel tempo contract migrate server trace"),
    # --- 21 ---
    ("Span attributes for request_id and tenant_id are promoted to Loki labels via the OTel Collector's attributes processor so trace-to-log correlation in Grafana works with one click.", "architecture", "technical", False,
     [("request_id", "config"), ("tenant_id", "config"), ("Loki", "service"), ("OTel Collector", "service"), ("attributes processor", "pattern")],
     [("OTel Collector", "Loki", "COMMUNICATES_WITH"), ("attributes processor", "Loki", "CONFIGURES")],
     "which processor promotes span attributes into Loki labels to enable one-click trace-to-log correlation",
     "attributes processor otel collector loki request id tenant span label"),
    # --- 22 ---
    ("Recording rules precompute the p50, p95, and p99 latency histograms per service every thirty seconds; the dashboards stopped timing out on panels that used to run histogram_quantile ad hoc.", "fact", "technical", False,
     [("Recording rules", "pattern"), ("p99 latency", "concept"), ("histogram_quantile", "api")],
     [("Recording rules", "histogram_quantile", "IMPROVES_ON")],
     "which Prometheus feature precomputes latency quantiles to stop dashboard panel timeouts",
     "recording rule p50 p95 p99 latency histogram quantile precompute panel"),
    # --- 23 ---
    ("Grafana dashboards are provisioned as JSON from the observability-as-code repo; clicking edit still works but a CI job reverts drift at the top of every hour unless the change is committed.", "fact", "technical", False,
     [("Grafana", "service"), ("JSON", "technology"), ("CI", "tool")],
     [("Grafana", "JSON", "USES")],
     "how are Grafana dashboards kept in sync with the observability-as-code repo despite ad-hoc edits",
     "grafana dashboard json provision ci drift revert repo as code"),
    # --- 24 ---
    ("OTLP over gRPC is the wire format between the SDKs and the collector; the HTTP/protobuf fallback stays only for the two Lambda runtimes that can't hold a long-lived gRPC stream open.", "architecture", "technical", False,
     [("OTLP", "protocol"), ("gRPC", "protocol"), ("HTTP/protobuf", "protocol"), ("Lambda", "platform")],
     [("OTLP", "gRPC", "USES"), ("HTTP/protobuf", "Lambda", "APPLIES_TO")],
     "which OTLP transport is primary and where does the HTTP fallback still apply",
     "otlp grpc http protobuf lambda fallback wire format sdk collector"),
    # --- 25 ---
    ("Tail-based sampling in a dedicated collector tier keeps errors and slow traces at 100% while sampling the green path at 1%; the old head-based sampler dropped the interesting traces at random.", "decision", "technical", False,
     [("Tail-based sampling", "pattern"), ("collector tier", "infrastructure"), ("head-based sampler", "pattern")],
     [("Tail-based sampling", "head-based sampler", "REPLACES")],
     "which sampling strategy replaced head-based sampling and how does it preserve interesting traces",
     "tail based sampling head collector error slow trace 100 percent green"),
    # --- 26 ---
    ("The service graph view in Grafana is driven by the servicegraph connector; edge weights encode p99 latency while edge colour encodes error rate so hot dependencies are obvious at a glance.", "architecture", "technical", False,
     [("service graph", "pattern"), ("Grafana", "service"), ("servicegraph connector", "tool"), ("p99 latency", "concept")],
     [("service graph", "servicegraph connector", "USES")],
     "which connector drives the Grafana service graph and what do edge weight and colour encode",
     "service graph grafana connector edge weight colour p99 error rate"),
    # --- 27 ---
    ("Logs are parsed with the Loki logfmt parser at query time rather than re-indexed; keeping the index tiny kept the chunk store cheap while still letting LogQL filter on arbitrary fields.", "decision", "technical", False,
     [("Loki", "service"), ("logfmt", "protocol"), ("LogQL", "language")],
     [("Loki", "logfmt", "USES"), ("LogQL", "logfmt", "USES")],
     "why does Loki parse logfmt at query time instead of reindexing and what does it preserve",
     "loki logfmt parser query time index chunk store logql cheap"),
    # --- 28 ---
    ("Cortex was replaced by Mimir in the 2.4 upgrade window; the ingester WAL migration ran in-place and the remote_write endpoints kept the same URL so no agent reconfiguration was needed.", "milestone", "technical", False,
     [("Cortex", "service"), ("Mimir", "service"), ("WAL", "pattern"), ("remote_write", "api")],
     [("Mimir", "Cortex", "REPLACES"), ("Mimir", "WAL", "USES")],
     "which TSDB replaced Cortex in the 2.4 window and how did agent remote_write survive the swap",
     "cortex mimir 2 4 upgrade wal ingester remote write url migrate"),
    # --- 29 ---
    ("Kubernetes events get piped into Loki through the OpenTelemetry Collector's k8sobjects receiver; alerting on BackOff and OOMKilled events now shares the same LogQL plumbing as application logs.", "fact", "technical", False,
     [("Kubernetes", "platform"), ("Loki", "service"), ("OpenTelemetry Collector", "service"), ("k8sobjects", "api"), ("LogQL", "language")],
     [("OpenTelemetry Collector", "Loki", "COMMUNICATES_WITH"), ("k8sobjects", "Kubernetes", "COMMUNICATES_WITH")],
     "which receiver pipes Kubernetes events into Loki for BackOff and OOMKilled alerting",
     "kubernetes event loki otel collector k8sobjects receiver backoff oomkilled"),
    # --- 30 ---
    ("Alert silencing by maintenance window now lives in a Terraform module; ad-hoc silences through the Alertmanager UI expire at 4 hours max so a forgotten silence cannot hide a real outage overnight.", "reference", "technical", False,
     [("Terraform", "tool"), ("Alertmanager", "service")],
     [("Terraform", "Alertmanager", "CONFIGURES")],
     "how are long maintenance-window silences codified and what TTL bounds ad-hoc silences",
     "terraform alertmanager silence maintenance window 4 hour ttl ad hoc"),
    # --- 31 ---
    ("The Prometheus scrape interval was bumped from 15s to 30s on the noisy node-exporter jobs; storage pressure dropped 40% and none of the alerts needed a rewrite because all rules used rate over 1m minimum.", "fact", "technical", False,
     [("Prometheus", "service"), ("node-exporter", "service"), ("rate", "api")],
     [("Prometheus", "node-exporter", "USES")],
     "which scrape interval change cut storage pressure without breaking the rate-based alert rules",
     "prometheus node exporter scrape interval 30s storage rate alert"),
    # --- 32 ---
    ("Grafana Loki now uses a boltdb-shipper index with object-storage-backed chunks on GCS; the legacy filesystem-backed Loki install kept falling over during log bursts and got decommissioned.", "decision", "technical", False,
     [("Grafana Loki", "service"), ("boltdb-shipper", "config"), ("GCS", "service"), ("filesystem-backed", "config")],
     [("boltdb-shipper", "filesystem-backed", "REPLACES"), ("Grafana Loki", "GCS", "USES")],
     "which Loki storage layout replaced the filesystem-backed install after log-burst failures",
     "loki boltdb shipper gcs filesystem chunk object store burst decommission"),
    # --- 33 ---
    ("Instrumented the gRPC interceptors once in a shared module so every Go service exports the same request.duration_seconds histogram with identical buckets; previously each team picked their own.", "architecture", "technical", False,
     [("gRPC", "protocol"), ("Go", "language"), ("request.duration_seconds", "config")],
     [("gRPC", "request.duration_seconds", "PRODUCES")],
     "how did gRPC interceptors get unified so every Go service exports the same latency histogram",
     "grpc interceptor go request duration seconds histogram bucket share"),
    # --- 34 ---
    ("VictoriaLogs was added as a second log backend for the security team's 90-day retention requirement; Loki still serves the 7-day operational window because dashboards there were already wired up.", "architecture", "technical", False,
     [("VictoriaLogs", "service"), ("Loki", "service"), ("security team", "organization")],
     [("VictoriaLogs", "security team", "APPLIES_TO")],
     "which log backend serves the 90-day security retention alongside Loki's 7-day operational window",
     "victorialogs loki security 90 day retention log backend operational"),
    # --- 35 ---
    ("Host-level eBPF metrics flow through the Grafana Alloy agent rather than a separate Cilium exporter; the single daemonset footprint made the Ops team sign off on rollout.", "decision", "technical", False,
     [("eBPF", "technology"), ("Grafana Alloy", "service"), ("Cilium", "service")],
     [("Grafana Alloy", "Cilium", "REPLACES")],
     "which agent consolidated eBPF metric collection into a single daemonset footprint",
     "ebpf grafana alloy cilium exporter daemonset consolidate metric host"),
    # --- 36 ---
    ("A 40% CPU regression on the collector was traced to the batch processor's default timeout; bumping send_batch_size from 8192 to 16384 cut overhead because flushes were firing on timeout more than size.", "problem", "technical", False,
     [("batch processor", "pattern"), ("send_batch_size", "config"), ("collector", "service")],
     [("send_batch_size", "batch processor", "CONFIGURES")],
     "which batch-processor setting fixed the collector CPU regression caused by timeout-driven flushes",
     "batch processor send batch size 16384 timeout flush collector cpu"),
    # --- 37 ---
    ("Synthetic probes against the checkout flow run every minute from Grafana Cloud's k6 runners; a failed probe joins the same SLO burn calculation as real traffic, sourced via a distinct job label.", "architecture", "technical", False,
     [("Grafana Cloud", "platform"), ("k6", "tool"), ("checkout", "service"), ("SLO", "concept")],
     [("k6", "checkout", "APPLIES_TO"), ("k6", "SLO", "APPLIES_TO")],
     "how do k6 synthetic probes contribute to the checkout SLO burn alongside real traffic",
     "k6 grafana cloud checkout synthetic probe slo burn job label"),
    # --- 38 ---
    ("The Tempo trace retention was dropped from 30 to 14 days after a cost audit; the team confirmed that 95% of trace lookups happen within 72 hours of the originating alert anyway.", "decision", "technical", False,
     [("Tempo", "service"), ("trace retention", "config")],
     [("Tempo", "trace retention", "CONFIGURES")],
     "which Tempo retention change followed the cost audit and what lookup pattern justified it",
     "tempo retention 14 day 30 cost audit trace lookup 72 hours alert"),
    # --- 39 ---
    ("Error-tracking went from Sentry self-hosted to GlitchTip; the API remains Sentry-compatible so the fifteen SDKs in the repo kept working without a code change on the application side.", "decision", "technical", False,
     [("Sentry", "service"), ("GlitchTip", "service")],
     [("GlitchTip", "Sentry", "REPLACES")],
     "which self-hosted error tracker replaced Sentry and how did the SDKs survive untouched",
     "glitchtip sentry api compatible sdk error tracker self host replace"),
    # --- 40 ---
    ("Service-level indicators for the search path are latency p99 under 400ms and success rate above 99.5%; the SLO is computed on a 28-day window and the error budget remaining is surfaced on the team TV.", "reference", "technical", False,
     [("Service-level indicators", "concept"), ("search path", "service"), ("SLO", "concept"), ("error budget", "concept")],
     [("Service-level indicators", "SLO", "RELATED_TO")],
     "which two SLIs define the search SLO and how is the remaining error budget surfaced to the team",
     "sli slo search path p99 latency 400ms success 99 5 budget team tv"),
    # --- 41 ---
    ("Log-sample rate-limit at 1000 lines per second per container kicks in after a debug-logging incident paved over Loki ingesters with a ten-GB-per-minute firehose from one pod.", "problem", "technical", False,
     [("rate-limit", "config"), ("container", "infrastructure"), ("Loki", "service")],
     [("rate-limit", "Loki", "FIXES")],
     "which per-container log rate limit was added after a debug-log incident overwhelmed Loki ingesters",
     "rate limit container 1000 lines loki ingester firehose debug pod"),
    # --- 42 ---
    ("Trace IDs are injected into structured log lines by the OTel SDK bridge; grepping Loki for a trace_id value now produces the matching logs in order without any manual correlation work.", "fact", "technical", False,
     [("trace_id", "config"), ("OTel SDK", "library"), ("Loki", "service")],
     [("OTel SDK", "trace_id", "PRODUCES")],
     "how does searching Loki by trace_id surface correlated logs without manual correlation work",
     "trace id log line otel sdk bridge loki grep correlate structured"),
    # --- 43. noise ---
    ("A flock of geese took up residence on the side lawn and security has given up chasing them until nesting season ends.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("The Alertmanager cluster ran split-brain for twenty minutes during a partial network partition; switching the gossip port to TCP-only eliminated the half-open state that was confusing the mesh.", "fact", "technical", False,
     [("Alertmanager", "service"), ("gossip port", "config"), ("TCP", "protocol")],
     [("gossip port", "Alertmanager", "CONFIGURES")],
     "which Alertmanager gossip change fixed the split-brain window triggered by a partial partition",
     "alertmanager split brain gossip tcp partition mesh half open twenty"),
    # --- 45 ---
    ("Dashboard naming convention is service/environment/domain and all panels must have a description; the observability review gate rejects any dashboard PR that lacks either and has for six months.", "preference", "technical", False,
     [("dashboard", "concept"), ("observability review", "pattern")],
     [("observability review", "dashboard", "APPLIES_TO")],
     "which naming convention and review gate are enforced on new dashboards in the repo",
     "dashboard naming service environment domain description review gate pr"),
    # --- 46 ---
    ("Prefer OpenTelemetry auto-instrumentation agents over hand-written spans on Java services; the byte-code agent covers servlet, JDBC, and Kafka spans uniformly which beats the per-team rollout of manual code.", "preference", "technical", False,
     [("OpenTelemetry", "library"), ("Java", "language"), ("JDBC", "api"), ("Kafka", "service")],
     [("OpenTelemetry", "Java", "APPLIES_TO")],
     "which instrumentation style is preferred on Java services and which frameworks does the agent cover",
     "opentelemetry java auto instrument agent jdbc kafka servlet prefer manual"),
    # --- 47 ---
    ("Metric names follow the OpenMetrics convention with _total suffix on counters and base-unit seconds on durations; the old ad-hoc _ms and _count names were rewritten via a recording-rule shim during the cutover.", "preference", "technical", False,
     [("OpenMetrics", "protocol"), ("recording-rule", "pattern")],
     [("OpenMetrics", "recording-rule", "USES")],
     "which metric naming convention was adopted and what shim covered the old ad-hoc name migration",
     "openmetrics counter total seconds base unit recording rule shim ms"),
    # --- 48 ---
    ("Prefer Grafana's Explore tab over fresh dashboard clones for one-off debugging; the split-pane for LogQL on one side and PromQL on the other is faster than stitching panels together for a single incident.", "preference", "technical", False,
     [("Grafana", "service"), ("LogQL", "language"), ("PromQL", "language")],
     [("Grafana", "LogQL", "USES"), ("Grafana", "PromQL", "USES")],
     "which Grafana workflow is preferred for one-off incident debugging over cloning dashboards",
     "grafana explore split pane logql promql one off incident debug dashboard"),
    # --- 49 ---
    ("Trace sampling on the mobile client is 5% tail-based on session, with crash sessions always sampled; the battery cost of full sampling was the blocker and product signed off on the sampled view.", "fact", "technical", False,
     [("mobile client", "platform"), ("tail-based", "pattern"), ("crash sessions", "pattern")],
     [("tail-based", "mobile client", "APPLIES_TO")],
     "which mobile-client sampling ratio shipped and which sessions override it to be sampled in full",
     "mobile client tail based 5 percent session crash sample battery cost"),
    # --- 50 ---
    ("On-call runbook links are embedded in each alert annotation so the PagerDuty page opens a Notion doc with the top-three checks; link rot was caught by a nightly runbook-linter job against the annotations.", "milestone", "technical", False,
     [("PagerDuty", "service"), ("Notion", "service"), ("runbook-linter", "tool"), ("alert annotation", "config")],
     [("PagerDuty", "Notion", "COMMUNICATES_WITH"), ("runbook-linter", "alert annotation", "APPLIES_TO")],
     "how do alert annotations link into runbooks and what job keeps those links from rotting",
     "pagerduty notion runbook linter alert annotation link rot nightly"),
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
