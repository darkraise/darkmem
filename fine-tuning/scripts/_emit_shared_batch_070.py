"""One-off emitter for shared-base batch-070 — ai_coding domain (observability, logging, and tracing as a coding practice — structured logging, OpenTelemetry SDK instrumentation, metrics emission, correlation IDs, log redaction).

Writes 50 rows to data/v2/shared/batch_070.tmp.jsonl with ids shared-03451..03500.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_070.tmp.jsonl"
ID_OFFSET = 3450

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the Go billing service from logrus to slog; the structured handler writes JSON to stdout and the existing field helpers were rewritten as slog.Attr factories.", "decision", "ai_coding", False,
     [("logrus", "library"), ("slog", "library"), ("billing", "service"), ("slog.Attr", "method")],
     [("slog", "logrus", "REPLACES")],
     "which logging library swap landed in the Go billing service and what got rewritten",
     "slog replace logrus go billing structured json handler attr"),
    # --- 2 ---
    ("Standardised on zap's SugaredLogger only at API boundaries; hot-path code uses the typed Logger so we stop allocating an interface{} per field on every request.", "preference", "ai_coding", False,
     [("zap", "library"), ("SugaredLogger", "method"), ("Logger", "method")],
     [("Logger", "SugaredLogger", "PREFERS")],
     "where do we use zap's sugared logger versus the typed logger in the codebase",
     "zap sugared typed logger hot path allocation interface field"),
    # --- 3 ---
    ("Pino replaced bunyan in the Node ingest gateway; the same JSON envelope ships out but pino's worker thread transport keeps the event loop free under burst load.", "decision", "ai_coding", False,
     [("Pino", "library"), ("bunyan", "library"), ("ingest gateway", "service")],
     [("Pino", "bunyan", "IMPROVES_ON")],
     "which Node logger replaced bunyan in the ingest gateway and why did it stick",
     "pino bunyan node logger worker thread transport event loop burst"),
    # --- 4 ---
    ("Python services use structlog with a processor chain ending in JSONRenderer; the dev shell swaps the last processor for ConsoleRenderer so local logs stay human-readable.", "architecture", "ai_coding", False,
     [("structlog", "library"), ("JSONRenderer", "method"), ("ConsoleRenderer", "method")],
     [("structlog", "JSONRenderer", "USES")],
     "how does the structlog processor chain switch between machine and human formats",
     "structlog processor json renderer console dev shell switch"),
    # --- 5 ---
    ("Log levels follow a strict ladder: TRACE for span events only, DEBUG behind a per-package flag, INFO for state transitions, WARN for handled anomalies, ERROR for unhandled.", "preference", "ai_coding", False,
     [("TRACE", "pattern"), ("DEBUG", "pattern"), ("INFO", "pattern"), ("WARN", "pattern"), ("ERROR", "pattern")],
     [],
     "which log-level convention does the codebase enforce across services",
     "log level ladder trace debug info warn error convention"),
    # --- 6 ---
    ("Sampling for DEBUG logs uses zap's NewSamplerWithOptions at 100 first and then 100 every second; production noise dropped tenfold without losing the leading-edge events.", "architecture", "ai_coding", False,
     [("zap", "library"), ("NewSamplerWithOptions", "method"), ("DEBUG", "pattern")],
     [],
     "how does the codebase sample DEBUG logs to keep volume bounded under load",
     "log sampling zap leading edge interval debug volume bound"),
    # --- 7 ---
    ("OpenTelemetry replaced OpenCensus across all services in 2026-Q1; the migration shim translated stats.Record calls into otel metric instruments before the cutover.", "milestone", "ai_coding", False,
     [("OpenTelemetry", "framework"), ("OpenCensus", "framework"), ("stats.Record", "method")],
     [("OpenTelemetry", "OpenCensus", "REPLACES")],
     "which telemetry SDK migration finished in Q1 and how were old call sites bridged",
     "opentelemetry opencensus migration shim stats record cutover"),
    # --- 8 ---
    ("Span attributes pin to the OpenTelemetry semantic conventions; http.request.method and url.path replace the legacy http.method and http.target across the gateway code.", "decision", "ai_coding", False,
     [("OpenTelemetry", "framework"), ("http.request.method", "config"), ("url.path", "config"), ("http.method", "config")],
     [("http.request.method", "http.method", "REPLACES")],
     "which span-attribute naming did we standardise on and what legacy keys did it retire",
     "otel semantic convention span attribute http request method url"),
    # --- 9 ---
    ("Trace context propagation uses W3C traceparent and tracestate headers only; the legacy b3 single header is still parsed inbound but never emitted outbound.", "architecture", "ai_coding", False,
     [("W3C", "organization"), ("traceparent", "config"), ("tracestate", "config"), ("b3", "config")],
     [("traceparent", "b3", "REPLACES")],
     "which propagation headers does the gateway emit and which legacy formats stay readable inbound",
     "w3c traceparent tracestate b3 single header propagation outbound"),
    # --- 10. noise ---
    ("Office bird outside the south window keeps mistaking the monitor reflection for a rival again.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Prometheus client_golang collectors register through a per-package registerer; the default registry is forbidden so a misnamed metric in one package can't poison the global namespace.", "architecture", "ai_coding", False,
     [("Prometheus", "tool"), ("client_golang", "library"), ("registerer", "pattern")],
     [],
     "how do Go services scope Prometheus collectors to avoid global-registry collisions",
     "prometheus client golang registerer per package default registry"),
    # --- 12 ---
    ("RED metrics for every HTTP handler emit through a single middleware: Rate counter, Errors counter, Duration histogram with the standard 8 buckets pinned to our SLO.", "architecture", "ai_coding", False,
     [("RED", "pattern"), ("middleware", "pattern"), ("Duration", "pattern"), ("SLO", "concept")],
     [],
     "which metrics pattern does the HTTP middleware emit and how are histogram buckets chosen",
     "red metrics rate error duration histogram bucket slo middleware"),
    # --- 13 ---
    ("USE metrics for the worker pool — Utilisation, Saturation, Errors — emit from the runtime hooks; queue depth and reject count are gauges scraped every fifteen seconds.", "architecture", "ai_coding", False,
     [("USE", "pattern"), ("worker pool", "pattern"), ("queue depth", "pattern")],
     [],
     "which metrics pattern instruments the worker pool internals and which gauges back it",
     "use metrics utilisation saturation error worker pool gauge depth"),
    # --- 14 ---
    ("Correlation IDs flow through context.Context as a typed key; every outbound HTTP and database call pulls it back out so spans, logs, and SQL comments all carry the same id.", "architecture", "ai_coding", False,
     [("context.Context", "method"), ("Correlation IDs", "pattern"), ("SQL comments", "pattern")],
     [],
     "how does the codebase carry correlation IDs across HTTP, database, and log boundaries",
     "correlation id context typed key outbound http database sql comment"),
    # --- 15 ---
    ("Request IDs are minted at the edge proxy via X-Request-Id and only generated inside the app if missing; downstream services must echo the inbound value rather than reroll.", "decision", "ai_coding", False,
     [("X-Request-Id", "config"), ("edge proxy", "service")],
     [],
     "where do request IDs originate and what's the rule for downstream services receiving one",
     "request id edge proxy x request id mint downstream echo reroll"),
    # --- 16 ---
    ("Log redaction lives in a structlog processor that walks the event dict and masks any key matching (?i)(password|token|secret|authorization|cookie); the mask preserves length for log shape.", "architecture", "ai_coding", False,
     [("structlog", "library"), ("password", "pattern"), ("token", "pattern"), ("authorization", "pattern")],
     [],
     "which logging stage redacts credential-shaped fields before records leave the process",
     "log redact structlog processor regex password token authorization"),
    # --- 17 ---
    ("A debug-flag toggle reads from /var/run/debug.flag every thirty seconds; flipping the file raises the package level to DEBUG without a restart, and a soft expiry resets it after an hour.", "architecture", "ai_coding", False,
     [("/var/run/debug.flag", "file"), ("DEBUG", "pattern")],
     [],
     "how does a service raise its log level to DEBUG without a redeploy or restart",
     "debug flag file toggle level raise hot reload soft expiry"),
    # --- 18 ---
    ("Dev-only logging uses a build tag in Go: files behind //go:build dev compile out of release binaries entirely so the verbose request-body dumps can't leak into prod.", "preference", "ai_coding", False,
     [("//go:build dev", "pattern"), ("Go", "language")],
     [],
     "how does the Go codebase keep verbose dev-only logging out of release binaries",
     "build tag go dev only logging compile out release request body"),
    # --- 19 ---
    ("Hot-reload of log config uses a SIGHUP handler that re-reads logging.yaml; the running zap logger swaps level via AtomicLevel.SetLevel without reallocating cores.", "architecture", "ai_coding", False,
     [("SIGHUP", "pattern"), ("logging.yaml", "file"), ("zap", "library"), ("AtomicLevel.SetLevel", "method")],
     [("zap", "AtomicLevel.SetLevel", "USES")],
     "how does the service hot-reload its log configuration without dropping in-flight requests",
     "sighup hot reload log config zap atomic level set yaml"),
    # --- 20 ---
    ("OpenTelemetry's BatchSpanProcessor exports over OTLP gRPC to a local agent; the in-process exporter ring buffer holds 2048 spans and drops oldest under back-pressure.", "architecture", "ai_coding", False,
     [("OpenTelemetry", "framework"), ("BatchSpanProcessor", "method"), ("OTLP", "protocol"), ("gRPC", "protocol")],
     [],
     "which OpenTelemetry export pipeline ships spans off-process and how does back-pressure work",
     "otel batch span processor otlp grpc ring buffer back pressure"),
    # --- 21 ---
    ("Span names follow a low-cardinality rule: HTTP spans use the route template, not the materialised path, so /users/:id replaces /users/8237 in the trace catalogue.", "decision", "ai_coding", False,
     [("HTTP", "protocol"), ("route template", "pattern")],
     [],
     "which span-naming rule keeps the trace catalogue from exploding under high-cardinality paths",
     "span name low cardinality route template http path materialised"),
    # --- 22 ---
    ("Sentry SDK init runs once in main with traces_sample_rate pulled from env; the before_send hook scrubs PII fields and drops handled-domain errors so noise stays tractable.", "architecture", "ai_coding", False,
     [("Sentry", "tool"), ("traces_sample_rate", "config"), ("before_send", "method"), ("PII", "concept")],
     [],
     "how is the Sentry SDK initialised and which hook keeps PII and known-noise errors out",
     "sentry init traces sample rate before send scrub pii hook"),
    # --- 23 ---
    ("OpenTelemetry auto-instrumentation for Python runs only for stdlib http.client and psycopg; framework instrumentation was disabled after a duplicate-span bug doubled the gateway latency view.", "problem", "ai_coding", False,
     [("OpenTelemetry", "framework"), ("http.client", "library"), ("psycopg", "library")],
     [],
     "which OpenTelemetry auto-instrumentations stay on in Python and which got disabled after a bug",
     "otel auto instrumentation python disable framework duplicate span"),
    # --- 24 ---
    ("Switched from Jaeger client to the OpenTelemetry SDK in 2026-02; Jaeger's UDP thrift exporter was dropping spans on the noisy worker host so OTLP HTTP became the new default.", "milestone", "ai_coding", False,
     [("Jaeger", "tool"), ("OpenTelemetry", "framework"), ("OTLP", "protocol"), ("2026-02", "date")],
     [("OpenTelemetry", "Jaeger", "REPLACES")],
     "which tracing client did we move off of and which transport replaced the dropped UDP path",
     "jaeger opentelemetry udp thrift drop otlp http exporter swap"),
    # --- 25 ---
    ("Histogram bucket boundaries on the request-duration metric are powers of two from 5ms to 10s; the SLO panel quantiles read clean and the per-route cardinality stays manageable.", "decision", "ai_coding", False,
     [("Histogram", "pattern"), ("SLO", "concept")],
     [],
     "which histogram bucket layout did we pick for request duration and what tradeoffs it balances",
     "histogram bucket power of two duration slo quantile cardinality"),
    # --- 26 ---
    ("Counter increments use Inc not Add(1) on the prometheus client_golang side; a quick benchmark showed Inc's specialised path skips the float conversion in the hot loop.", "fact", "ai_coding", False,
     [("Inc", "method"), ("Add", "method"), ("client_golang", "library")],
     [("Inc", "Add", "PREFERS")],
     "which Prometheus counter call do we prefer in hot loops and why",
     "prometheus inc add counter hot loop float conversion benchmark"),
    # --- 27 ---
    ("Span event versus log decision rule: anything that needs to be searchable across services uses a span event with attributes; intra-process state changes stay as plain logs.", "preference", "ai_coding", False,
     [("span event", "pattern"), ("log", "pattern")],
     [],
     "when do we attach a span event versus emit a regular log line in the codebase",
     "span event log decision searchable cross service intra process"),
    # --- 28 ---
    ("Trace IDs land in every log line via an slog handler that pulls trace.SpanContextFromContext at write time; Loki queries can pivot from a log to its trace by id without a join.", "architecture", "ai_coding", False,
     [("slog", "library"), ("trace.SpanContextFromContext", "method"), ("Loki", "tool")],
     [("slog", "trace.SpanContextFromContext", "USES")],
     "how do log lines carry the active trace ID so that Loki can pivot to a trace view",
     "slog trace id span context log line loki pivot exemplar"),
    # --- 29 ---
    ("Exemplars are attached to histogram observations using the otelprom bridge; the Grafana panel jumps from a high-latency bucket straight into the offending trace.", "architecture", "ai_coding", False,
     [("Exemplars", "pattern"), ("otelprom", "library"), ("Grafana", "tool"), ("histogram", "pattern")],
     [],
     "how do histograms expose exemplars so Grafana can jump from a bucket to a trace",
     "exemplar histogram otelprom bridge grafana trace pivot bucket"),
    # --- 30 ---
    ("Context propagation across goroutines uses errgroup.WithContext and explicit ctx params; bare go func() that captures a parent ctx is flagged by a vet rule.", "preference", "ai_coding", False,
     [("errgroup.WithContext", "method"), ("goroutines", "pattern"), ("vet", "tool")],
     [],
     "how does the Go codebase propagate trace context across goroutine boundaries",
     "errgroup with context goroutine ctx propagate vet rule capture"),
    # --- 31 ---
    ("Python's contextvars carry the current span across asyncio tasks; the OpenTelemetry SDK's context.attach is wrapped in a helper that pairs detach in a finally block.", "architecture", "ai_coding", False,
     [("contextvars", "library"), ("asyncio", "library"), ("OpenTelemetry", "framework"), ("context.attach", "method")],
     [],
     "how does Python carry the active span across asyncio tasks without leaking context",
     "contextvars asyncio span attach detach finally helper otel"),
    # --- 32 ---
    ("Metric label cardinality has a hard ceiling of 100 distinct values per label; a runtime guard in the metrics wrapper throws if a caller passes an unbounded user-supplied string.", "problem", "ai_coding", False,
     [("cardinality", "concept"), ("metrics", "pattern")],
     [],
     "which guard prevents unbounded metric label cardinality from blowing up the TSDB",
     "metric label cardinality cap guard wrapper unbounded string throw"),
    # --- 33 ---
    ("Replaced printf debugging with a per-package zap.SugaredLogger.Debugw plus a debug build tag; the lint rule bans fmt.Println in non-test code so stray prints can't ship.", "decision", "ai_coding", False,
     [("printf", "method"), ("zap", "library"), ("Debugw", "method"), ("fmt.Println", "method")],
     [("Debugw", "printf", "REPLACES")],
     "which debug-print pattern replaced ad-hoc printf and how is it enforced",
     "printf zap debugw build tag fmt println lint ban replace"),
    # --- 34 ---
    ("Exception logging uses logger.exception, never logger.error with str(e); the former preserves the traceback and lets the JSON formatter ship it as a structured stack field.", "preference", "ai_coding", False,
     [("logger.exception", "method"), ("logger.error", "method")],
     [("logger.exception", "logger.error", "PREFERS")],
     "which Python logging call do we use for caught exceptions and why",
     "logger exception versus error preserve traceback structured stack"),
    # --- 35 ---
    ("OTLP exporter timeout pins to 5 seconds and BatchSpanProcessor max queue size to 4096; a sticky outage at the collector won't backfill enough to OOM the app process.", "architecture", "ai_coding", False,
     [("OTLP", "protocol"), ("BatchSpanProcessor", "method"), ("collector", "service")],
     [],
     "how are the OTLP exporter timeout and batch queue tuned to survive collector outages",
     "otlp timeout batch processor queue size collector outage oom"),
    # --- 36 ---
    ("Custom span processor strips db.statement attribute when the SQL contains literal parameters; the parameterised template is kept so trace search by query shape still works.", "architecture", "ai_coding", False,
     [("db.statement", "config"), ("SQL", "language")],
     [],
     "how does the span pipeline keep SQL literals out of trace attributes without losing query identity",
     "db statement strip literal parameter sql template span processor"),
    # --- 37 ---
    ("Pinned the OpenTelemetry semantic-conventions Go module to v1.26.0; auto-bumps were silently shifting attribute keys mid-release and breaking saved Tempo queries.", "problem", "ai_coding", False,
     [("OpenTelemetry", "framework"), ("v1.26.0", "config"), ("Tempo", "tool")],
     [],
     "why is the OpenTelemetry semantic-conventions module pinned and what broke before the pin",
     "otel semantic conventions pin version tempo query attribute shift"),
    # --- 38 ---
    ("Health-check endpoints emit a tiny Prometheus gauge plus a structured log line per scrape; the gauge proves the scrape happened even when the service has nothing to say.", "architecture", "ai_coding", False,
     [("Prometheus", "tool"), ("Health-check", "api"), ("gauge", "pattern")],
     [],
     "how do health checks prove they were scraped when there's no other traffic to look at",
     "health check prometheus gauge scrape liveness structured log evidence"),
    # --- 39 ---
    ("Per-tenant log enrichment adds tenant_id and plan tier as bound fields on a child logger; the binding happens in middleware so handler code never threads them manually.", "architecture", "ai_coding", False,
     [("tenant_id", "pattern"), ("middleware", "pattern"), ("child logger", "pattern")],
     [],
     "how does the codebase add tenant context to every log line without threading it through handlers",
     "tenant id child logger bind middleware enrich plan tier handler"),
    # --- 40 ---
    ("Adopted slog's Handler interface to write a tee handler that forks records to stdout and a remote endpoint; only one allocation per record because Attrs are passed through.", "architecture", "ai_coding", False,
     [("slog", "library"), ("Handler", "method"), ("tee handler", "pattern")],
     [],
     "which slog primitive lets us fork log records to two sinks with one allocation",
     "slog handler tee fork stdout remote sink attr allocation"),
    # --- 41 ---
    ("OpenTelemetry's Logs SDK is gated behind an experimental feature flag in our Python services; we still ship logs via stdout to the agent rather than the OTLP logs exporter.", "decision", "ai_coding", False,
     [("OpenTelemetry", "framework"), ("Logs SDK", "library"), ("OTLP", "protocol")],
     [],
     "why are OpenTelemetry logs experimental in our Python stack and what ships logs instead",
     "otel logs sdk experimental flag python stdout agent otlp"),
    # --- 42 ---
    ("Prometheus summary type is banned in new code; histogram with native buckets covers the use cases and lets the server compute quantiles globally instead of per-instance.", "preference", "ai_coding", False,
     [("Prometheus", "tool"), ("summary", "pattern"), ("histogram", "pattern"), ("native buckets", "pattern")],
     [("histogram", "summary", "REPLACES")],
     "which Prometheus metric type is forbidden in new code and what replaces it",
     "prometheus summary ban histogram native bucket quantile global"),
    # --- 43 ---
    ("trace.WithAttributes calls inside hot loops moved to span.SetAttributes once after the loop; the pprof flame graph showed 7 percent CPU spent in attribute encoding before the change.", "problem", "ai_coding", False,
     [("trace.WithAttributes", "method"), ("span.SetAttributes", "method"), ("pprof", "tool")],
     [("span.SetAttributes", "trace.WithAttributes", "IMPROVES_ON")],
     "which span-attribute call pattern fixed a 7 percent CPU regression in hot loops",
     "span set attributes hot loop pprof flame graph encoding cpu"),
    # --- 44 ---
    ("Reference doc for the metrics taxonomy lives at docs/observability/metrics.md and pins the unit suffixes (_seconds, _bytes, _total) per Prometheus naming guidelines.", "reference", "ai_coding", False,
     [("docs/observability/metrics.md", "file"), ("Prometheus", "tool"), ("_seconds", "pattern"), ("_total", "pattern")],
     [],
     "where does the metrics naming reference live and which suffix conventions does it pin",
     "metrics taxonomy docs file unit suffix seconds bytes total naming"),
    # --- 45 ---
    ("Stripped raw request bodies from access logs after a 2025 pen-test report flagged a JWT echoed in a 4xx case; the body is now replaced with a sha256 prefix and length only.", "problem", "ai_coding", False,
     [("access logs", "pattern"), ("JWT", "protocol"), ("sha256", "algorithm")],
     [],
     "which access-log redaction landed after a pen-test caught a JWT in a 4xx body capture",
     "access log redact request body jwt sha256 prefix length pen test"),
    # --- 46 ---
    ("Adopted the OpenTelemetry resource detector for kubernetes; pod, namespace, and node land as resource attributes once at startup so every span and metric carries them for free.", "milestone", "ai_coding", False,
     [("OpenTelemetry", "framework"), ("kubernetes", "platform"), ("resource detector", "pattern")],
     [("resource detector", "kubernetes", "APPLIES_TO")],
     "which OpenTelemetry helper auto-attaches kubernetes pod and namespace to every span",
     "otel resource detector kubernetes pod namespace node attribute"),
    # --- 47 ---
    ("Replaced the in-house request-id middleware with otelhttp's built-in span and a small adapter; one less concept, and the propagation now follows the SDK contract for free.", "decision", "ai_coding", False,
     [("otelhttp", "library"), ("middleware", "pattern"), ("request-id", "pattern")],
     [("otelhttp", "middleware", "REPLACES")],
     "which middleware did otelhttp replace and what did the swap simplify",
     "otelhttp middleware request id adapter propagation in house swap"),
    # --- 48 ---
    ("logger fields enforce camelCase consistently across services; a CI lint script greps for snake_case keys in zap.Field constructors and fails the job if any slip in.", "preference", "ai_coding", False,
     [("camelCase", "pattern"), ("snake_case", "pattern"), ("zap.Field", "method")],
     [("camelCase", "snake_case", "PREFERS")],
     "which key-casing convention do log fields follow and how is it enforced in CI",
     "log field camel case snake case lint zap field ci script"),
    # --- 49. noise ---
    ("Someone left a half-eaten pastry on the standup table and nobody is admitting to it.", "fact", "noise", True, [], [], None, None),
    # --- 50 ---
    ("Adopted Vector as the in-process log forwarder embedded via vector-rs in the worker binary; replaces the sidecar fluent-bit and saves the pod a container plus a socket hop.", "milestone", "ai_coding", False,
     [("Vector", "tool"), ("vector-rs", "library"), ("fluent-bit", "tool"), ("worker", "service")],
     [("Vector", "fluent-bit", "REPLACES")],
     "what shipped logs out of the worker after we removed the sidecar container",
     "vector rs in process forwarder embed binary save container hop"),
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
