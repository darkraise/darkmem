"""One-off emitter for shared-base batch-071 — ai_coding domain (error handling and resilience patterns slice).

Writes 50 rows to data/v2/shared/batch_071.tmp.jsonl with ids shared-03501..03550.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_071.tmp.jsonl"
ID_OFFSET = 3500

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Replaced the hand-rolled retry while-loop in the billing client with tenacity decorators; exponential backoff and full jitter come for free instead of being reinvented per call site.", "decision", "ai_coding", False,
     [("tenacity", "library"), ("billing client", "service"), ("exponential backoff", "pattern"), ("full jitter", "pattern")],
     [("tenacity", "billing client", "APPLIES_TO")],
     "which library replaced the bespoke retry loop in the billing client and what did that buy",
     "tenacity decorator retry exponential backoff jitter billing remove"),
    # --- 2 ---
    ("Added a circuit breaker around the recommendations API using resilience4j; after 20 failures inside a 60-second window the breaker opens for 30 seconds and serves a cached payload.", "architecture", "ai_coding", False,
     [("resilience4j", "library"), ("recommendations API", "api"), ("circuit breaker", "pattern")],
     [("resilience4j", "circuit breaker", "IMPLEMENTS")],
     "how does the recommendations call protect itself when the upstream starts failing in bursts",
     "resilience4j circuit breaker open threshold window cached fallback"),
    # --- 3 ---
    ("The Go inventory service stopped using panics for control flow and returns wrapped errors via fmt.Errorf with %w; recover is now reserved strictly for true invariants.", "decision", "ai_coding", False,
     [("Go", "language"), ("fmt.Errorf", "method"), ("recover", "method"), ("inventory service", "service")],
     [("fmt.Errorf", "recover", "REPLACES")],
     "which Go convention split panics from regular errors in the inventory service",
     "go panic recover error wrap fmt errorf percent w invariant only"),
    # --- 4 ---
    ("Migrated the Rust ingest module from unwrap-everywhere to Result types with thiserror; every fallible call site now propagates a typed IngestError instead of crashing the worker.", "milestone", "ai_coding", False,
     [("Rust", "language"), ("thiserror", "library"), ("Result", "pattern"), ("IngestError", "error")],
     [("Result", "IngestError", "USES")],
     "how did the Rust ingest module move away from unwrap and what error type carries the failures",
     "rust result type thiserror replace unwrap typed ingest error propagate"),
    # --- 5 ---
    ("Every POST to /payments requires an idempotency key; the server stores key plus request hash in Redis for 24 hours and returns the original response on replay.", "architecture", "ai_coding", False,
     [("idempotency key", "pattern"), ("/payments", "api"), ("Redis", "database")],
     [("idempotency key", "/payments", "APPLIES_TO")],
     "how does the payments endpoint handle duplicate POST retries from flaky clients",
     "idempotency key redis store request hash payment replay safe"),
    # --- 6 ---
    ("Polly pipelines on the .NET checkout client stack a timeout, retry, and circuit breaker policy in that order; the outer cancellation token aborts everything cleanly under load.", "architecture", "ai_coding", False,
     [("Polly", "library"), (".NET", "framework"), ("checkout client", "service"), ("cancellation token", "pattern")],
     [("Polly", ".NET", "APPLIES_TO")],
     "how is the Polly policy stack ordered on the checkout client and why that order",
     "polly dotnet pipeline timeout retry circuit breaker cancellation"),
    # --- 7 ---
    ("The python backoff library replaced our handwritten sleep-and-double helper across the SDK; @backoff.on_exception keeps the call sites readable and centralises the giveup predicate.", "decision", "ai_coding", False,
     [("backoff", "library"), ("@backoff.on_exception", "method"), ("sleep-and-double", "pattern"), ("SDK", "project")],
     [("backoff", "sleep-and-double", "REPLACES")],
     "which Python library standardised retry decorators across the SDK and replaced the bespoke helper",
     "python backoff library decorator on exception giveup centralise sdk"),
    # --- 8 ---
    ("Bulkhead isolation in the order processor partitions the thread pool by tenant tier; a noisy free-tier customer cannot starve the paid-tier workers any more.", "architecture", "ai_coding", False,
     [("Bulkhead", "pattern"), ("order processor", "service"), ("thread pool", "pattern")],
     [("Bulkhead", "thread pool", "USES")],
     "which isolation pattern stops a noisy tenant from monopolising worker threads in the order processor",
     "bulkhead isolation thread pool tenant partition starvation prevent"),
    # --- 9 ---
    ("The Node fetch wrapper hard-caps every outbound call at 5 seconds with an AbortController; without the explicit timeout a hung upstream used to pin event-loop workers indefinitely.", "problem", "ai_coding", False,
     [("Node", "platform"), ("AbortController", "api"), ("fetch", "method")],
     [("AbortController", "fetch", "APPLIES_TO")],
     "how did the Node fetch wrapper stop hung upstreams from pinning event-loop workers forever",
     "node fetch abort controller timeout hang upstream event loop fix"),
    # --- 10. noise ---
    ("Three pigeons argued on the windowsill for forty minutes about something only pigeons understood.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("The Saga pattern coordinates the booking workflow across hotel, flight, and car services; each step has a paired compensation handler that runs on downstream failure.", "architecture", "ai_coding", False,
     [("Saga", "pattern"), ("booking workflow", "project"), ("compensation", "pattern")],
     [("Saga", "compensation", "USES")],
     "which distributed-transaction pattern coordinates the multi-service booking workflow with rollbacks",
     "saga pattern compensation hotel flight car rollback orchestrate"),
    # --- 12 ---
    ("Dead-letter queue handling lives in the consumer code, not just the broker; messages failing five attempts get moved to a parking topic with the original error and stack attached.", "architecture", "ai_coding", False,
     [("Dead-letter queue", "pattern"), ("consumer", "service"), ("parking topic", "pattern")],
     [],
     "how does the consumer handle messages that exhaust their retry budget without losing context",
     "dead letter queue parking topic attempt error stack consumer code"),
    # --- 13 ---
    ("Switched from Hystrix to resilience4j after Hystrix entered maintenance mode; the functional API and reactive integration matched our Project Reactor stack better.", "decision", "ai_coding", False,
     [("Hystrix", "library"), ("resilience4j", "library"), ("Project Reactor", "framework")],
     [("resilience4j", "Hystrix", "REPLACES"), ("resilience4j", "Hystrix", "IMPROVES_ON")],
     "which fault-tolerance library replaced Hystrix and why did the swap fit our reactive stack",
     "resilience4j replace hystrix maintenance reactive project reactor"),
    # --- 14 ---
    ("Exception hierarchy in the platform package roots at PlatformError with NetworkError, StorageError, and ValidationError as direct subclasses; callers can catch broadly or narrowly without sniffing strings.", "architecture", "ai_coding", False,
     [("PlatformError", "error"), ("NetworkError", "error"), ("StorageError", "error"), ("ValidationError", "error")],
     [("NetworkError", "PlatformError", "EXTENDS"), ("StorageError", "PlatformError", "EXTENDS"), ("ValidationError", "PlatformError", "EXTENDS")],
     "how is the platform package's exception tree organised so callers can catch by category",
     "exception hierarchy platform error network storage validation subclass"),
    # --- 15 ---
    ("Python chained exceptions are mandatory in the data layer; every except block re-raises with raise NewError(...) from err so the original cause survives in __cause__.", "preference", "ai_coding", False,
     [("Python", "language"), ("__cause__", "pattern"), ("data layer", "service")],
     [],
     "which Python convention preserves the original cause when the data layer re-raises an exception",
     "python chained exception raise from cause attribute preserve trace"),
    # --- 16 ---
    ("The errors.Wrap calls in the Go services were replaced wholesale with the standard fmt.Errorf %w verb after Go 1.13; errors.Is and errors.As now drive every sentinel and type check.", "milestone", "ai_coding", False,
     [("errors.Wrap", "method"), ("Go 1.13", "platform"), ("errors.Is", "method"), ("errors.As", "method"), ("fmt.Errorf", "method")],
     [("fmt.Errorf", "errors.Wrap", "REPLACES"), ("errors.Is", "errors.Wrap", "IMPROVES_ON")],
     "which Go error-wrapping migration landed after 1.13 and what unlocked it",
     "go errors wrap percent w errors is as standard library 1.13"),
    # --- 17 ---
    ("Either<L, R> from fp-ts replaced thrown exceptions in the validation layer of the TypeScript API; the resolver chain stays type-checked end to end without try/catch noise.", "decision", "ai_coding", False,
     [("Either", "pattern"), ("fp-ts", "library"), ("TypeScript", "language"), ("resolver", "pattern"), ("exceptions", "pattern")],
     [("Either", "exceptions", "REPLACES")],
     "which functional pattern replaced thrown exceptions in the TypeScript validation layer",
     "either fp ts typescript validation replace throw exception type safe"),
    # --- 18 ---
    ("Decorrelated jitter follows the AWS Architecture Blog formula: sleep = min(cap, random_between(base, prev*3)); replaced equal-jitter after a thundering-herd incident on 2026-02-14.", "problem", "ai_coding", False,
     [("Decorrelated jitter", "algorithm"), ("equal-jitter", "algorithm"), ("AWS Architecture Blog", "publication"), ("2026-02-14", "date")],
     [("Decorrelated jitter", "equal-jitter", "REPLACES")],
     "which jitter algorithm replaced equal-jitter after a thundering-herd incident and where did the formula come from",
     "decorrelated jitter formula aws blog thundering herd incident replace"),
    # --- 19 ---
    ("Fallback responses on the search endpoint serve a stale Redis snapshot when the primary Elasticsearch cluster is breaker-open; the response carries an X-Stale: true header for clients to react.", "architecture", "ai_coding", False,
     [("search", "api"), ("Redis", "database"), ("Elasticsearch", "database"), ("X-Stale", "config")],
     [("Redis", "Elasticsearch", "REPLACES")],
     "what does the search endpoint serve when the primary cluster's circuit breaker is open",
     "fallback stale redis snapshot elasticsearch breaker x stale header"),
    # --- 20 ---
    ("Context propagation in the Go gateway uses context.WithValue sparingly — only request-scoped trace ids and tenant tags; business data flows through explicit struct fields so the context stays cheap to scan.", "preference", "ai_coding", False,
     [("context.WithValue", "method"), ("Go", "language"), ("gateway", "service")],
     [],
     "which Go convention restricts what gets attached to context.WithValue in the gateway",
     "go context with value request scope trace tenant business data"),
    # --- 21 ---
    ("Retry budget on the search proxy is capped at 10 percent of the originating request rate; the SRE-style budget prevents retry storms from doubling load on a degraded backend.", "architecture", "ai_coding", False,
     [("Retry budget", "pattern"), ("search proxy", "service"), ("SRE", "concept")],
     [],
     "which budget keeps retry storms from amplifying load when the search backend degrades",
     "retry budget percent originating rate sre prevent storm amplify"),
    # --- 22 ---
    ("Hedge requests on the read path fire a duplicate after p99 latency elapses; the first response wins and the loser is cancelled via grpc.WithCancel to avoid wasted work.", "architecture", "ai_coding", False,
     [("Hedge", "pattern"), ("p99", "concept"), ("grpc.WithCancel", "method")],
     [],
     "how does the read path use hedging to cut tail latency without doubling backend cost",
     "hedge request p99 duplicate first wins cancel grpc tail latency"),
    # --- 23 ---
    ("Compensating transactions for the loyalty-points ledger are written as named handlers registered with the saga coordinator; rollback runs them in reverse insertion order on any step failure.", "architecture", "ai_coding", False,
     [("Compensating transactions", "pattern"), ("loyalty-points", "project"), ("saga coordinator", "service")],
     [],
     "how are compensating transactions ordered when the loyalty-points saga rolls back",
     "compensating transaction reverse order saga coordinator handler rollback"),
    # --- 24 ---
    ("Token-bucket rate limiter trips a 429 with Retry-After well before the upstream timeout fires; clients that respect the header avoid wasting their own retry budget on doomed calls.", "fact", "ai_coding", False,
     [("Token-bucket", "algorithm"), ("Retry-After", "config"), ("429", "error")],
     [],
     "which header lets clients pace themselves when the token-bucket limiter trips before upstream timeout",
     "token bucket rate limit 429 retry after pace client budget"),
    # --- 25 ---
    ("Custom RetryableError marker interface lets infrastructure-level retry layers decide what's worth re-attempting; business errors implement it explicitly, defaults are non-retryable.", "architecture", "ai_coding", False,
     [("RetryableError", "error"), ("retry", "pattern")],
     [],
     "which marker interface lets infrastructure retry layers decide retryability without sniffing types",
     "retryable error marker interface infra retry default non explicit"),
    # --- 26 ---
    ("Outbox pattern landed in the orders service; domain events get inserted in the same transaction as the row, then a relay publishes to Kafka with at-least-once and de-dup keys.", "milestone", "ai_coding", False,
     [("Outbox", "pattern"), ("orders service", "service"), ("Kafka", "technology")],
     [("Outbox", "Kafka", "COMMUNICATES_WITH")],
     "which pattern atomically links a database write with a Kafka publish in the orders service",
     "outbox pattern transaction relay kafka at least once dedup"),
    # --- 27 ---
    ("Retry policies live in a single retry_policies.yaml file consumed by both the Go and Python SDKs; per-endpoint max_attempts and backoff overrides stay in version control.", "preference", "ai_coding", False,
     [("retry_policies.yaml", "file"), ("Go", "language"), ("Python", "language")],
     [],
     "where do the cross-language SDKs read their per-endpoint retry overrides",
     "retry policy yaml shared go python sdk per endpoint version control"),
    # --- 28 ---
    ("Replaced try/except Exception around startup with a typed StartupError; the supervisor distinguishes recoverable config faults from fatal binary mismatches and acts differently.", "decision", "ai_coding", False,
     [("StartupError", "error"), ("supervisor", "service"), ("try/except", "pattern"), ("Exception", "error")],
     [("StartupError", "Exception", "REPLACES")],
     "how did the supervisor learn to tell recoverable startup faults from fatal ones",
     "startup error typed supervisor recoverable fatal config binary"),
    # --- 29 ---
    ("The connection pool now raises PoolExhaustedError on exhaustion with the in-flight count and waiter queue depth attached; the metric label drives a dashboard alert before timeouts cascade.", "architecture", "ai_coding", False,
     [("PoolExhaustedError", "error"), ("connection pool", "pattern")],
     [],
     "which error carries diagnostic detail when the connection pool runs dry and what does it feed",
     "pool exhausted error in flight waiter dashboard cascade alert"),
    # --- 30 ---
    ("Watchdog timers wrap every long-running goroutine in the streaming ingestor; a stuck stage gets cancelled at the 90-second mark and the supervisor restarts only that stage.", "architecture", "ai_coding", False,
     [("Watchdog", "pattern"), ("goroutine", "pattern"), ("streaming ingestor", "service")],
     [],
     "how does the streaming ingestor detect and recover stuck stages without restarting the whole pipeline",
     "watchdog timer goroutine cancel restart stage supervisor streaming"),
    # --- 31 ---
    ("Resilience tests run with toxiproxy injecting latency, bandwidth caps, and resets on each upstream; CI fails if a critical-path call lacks a documented timeout or fallback.", "preference", "ai_coding", False,
     [("toxiproxy", "tool"), ("CI", "tool"), ("upstream", "pattern")],
     [("toxiproxy", "CI", "USES")],
     "which tool injects faults into upstream calls so the CI gate can verify timeouts and fallbacks",
     "toxiproxy fault injection latency reset ci timeout fallback gate"),
    # --- 32 ---
    ("Bulkheaded HTTP clients use separate aiohttp connection pools per downstream; a saturated pool to the analytics service can't exhaust the pool to the auth service any more.", "architecture", "ai_coding", False,
     [("aiohttp", "library"), ("connection pool", "pattern"), ("auth service", "service"), ("analytics service", "service")],
     [],
     "how does separating aiohttp pools per downstream prevent cross-service starvation",
     "aiohttp separate pool per downstream bulkhead starvation isolate"),
    # --- 33 ---
    ("Replaced a sentinel None return on cache lookup with a typed CacheResult union; downstream code now exhaustively matches Hit, Miss, and Stale instead of guessing.", "decision", "ai_coding", False,
     [("None", "pattern"), ("CacheResult", "pattern"), ("union", "pattern")],
     [("CacheResult", "None", "REPLACES")],
     "which return-type change made cache lookups exhaustive at downstream call sites",
     "cache result union hit miss stale replace none sentinel exhaustive"),
    # --- 34 ---
    ("Failsafe library on the JVM ingest worker handles retry, timeout, and fallback in a single FailsafeExecutor; the previous nest of try/catch and ScheduledExecutorService timers vanished.", "milestone", "ai_coding", False,
     [("Failsafe", "library"), ("JVM", "platform"), ("FailsafeExecutor", "method"), ("ScheduledExecutorService", "api")],
     [("Failsafe", "ScheduledExecutorService", "REPLACES")],
     "which library consolidated retry, timeout, and fallback on the JVM ingest worker",
     "failsafe library jvm executor retry timeout fallback consolidate"),
    # --- 35 ---
    ("The /healthz endpoint distinguishes liveness from readiness; degraded dependencies flip readiness off so the load balancer drains traffic without restarting the pod.", "architecture", "ai_coding", False,
     [("/healthz", "api"), ("liveness", "concept"), ("readiness", "concept")],
     [],
     "how does the health endpoint let the load balancer drain a degraded pod without a restart",
     "healthz liveness readiness drain load balancer degrade pod restart"),
    # --- 36 ---
    ("Graceful shutdown waits up to 30 seconds for in-flight requests after SIGTERM; new connections are refused via a draining flag while existing ones finish or hit their own timeout.", "architecture", "ai_coding", False,
     [("SIGTERM", "command"), ("draining", "pattern"), ("Graceful shutdown", "pattern")],
     [],
     "how does the service drain in-flight work after SIGTERM without dropping live requests",
     "graceful shutdown sigterm drain flag in flight grace period timeout"),
    # --- 37 ---
    ("Partial-failure semantics on the bulk-write API return per-item status codes inside a 207 envelope; clients no longer have to guess whether a 500 lost everything or just one row.", "architecture", "ai_coding", False,
     [("bulk-write", "api"), ("207", "error"), ("Partial-failure", "pattern")],
     [],
     "how does the bulk-write API report mixed success and failure across items in one response",
     "partial failure 207 multi status bulk write per item code envelope"),
    # --- 38 ---
    ("Switched the Spring Boot order service from RestTemplate to WebClient with a Reactor Retry spec; declarative backoff filters replaced an interceptor stack we kept getting wrong.", "decision", "ai_coding", False,
     [("Spring Boot", "framework"), ("RestTemplate", "library"), ("WebClient", "library"), ("Reactor Retry", "library")],
     [("WebClient", "RestTemplate", "REPLACES")],
     "which Spring Boot HTTP client swap landed declarative retry filters",
     "spring boot webclient resttemplate reactor retry filter declarative"),
    # --- 39 ---
    ("Failure-mode catalogue for the payments service lists each downstream, the failure modes, the chosen mitigation, and the owner; the doc lives in the runbooks repo and gates new integrations.", "reference", "ai_coding", False,
     [("Failure-mode catalogue", "concept"), ("payments service", "service"), ("runbooks", "project")],
     [],
     "which document captures failure modes and mitigations for each payments-service downstream",
     "failure mode catalogue payments downstream mitigation runbook gate"),
    # --- 40 ---
    ("anyhow plus thiserror split duty on the Rust CLI: anyhow for top-level error reporting with backtraces, thiserror for typed library errors that consumers can match on.", "architecture", "ai_coding", False,
     [("anyhow", "library"), ("thiserror", "library"), ("Rust", "language"), ("CLI", "tool")],
     [],
     "how do the anyhow and thiserror crates split responsibilities in the Rust CLI",
     "anyhow thiserror rust cli backtrace typed library boundary split"),
    # --- 41 ---
    ("Compaction job uses a leader-election lock in etcd so retries from a stuck worker can't double-compact; the lease auto-expires after 90 seconds if the worker disappears.", "architecture", "ai_coding", False,
     [("etcd", "database"), ("Compaction job", "service"), ("leader-election", "pattern")],
     [("Compaction job", "etcd", "USES")],
     "which lock keeps the compaction job from double-running when a stuck worker is retried",
     "etcd leader election lease compaction double run lock expire"),
    # --- 42 ---
    ("Outbox poller uses SELECT FOR UPDATE SKIP LOCKED on Postgres so multiple workers can publish concurrently without stepping on each other; ordering within an aggregate is preserved by a hash-sharded queue.", "architecture", "ai_coding", False,
     [("SKIP LOCKED", "pattern"), ("Postgres", "database"), ("Outbox poller", "service")],
     [("Outbox poller", "Postgres", "USES")],
     "how do parallel outbox workers avoid stepping on the same row while keeping per-aggregate order",
     "skip locked postgres outbox parallel worker hash shard order"),
    # --- 43 ---
    ("Adopted the Either monad in Kotlin via Arrow for the loan-decision pipeline; left holds DecisionError and right holds the approved offer, so flatMap chains stay total.", "decision", "ai_coding", False,
     [("Arrow", "library"), ("Kotlin", "language"), ("Either", "pattern"), ("DecisionError", "error")],
     [("Either", "DecisionError", "USES")],
     "which functional library brought Either-style total pipelines to the Kotlin loan-decision flow",
     "arrow kotlin either monad flat map loan decision total pipeline"),
    # --- 44 ---
    ("Replaced print-and-pray panic recovery with structured slog handlers in every Go binary; panics now produce a json line with goroutine id, request id, and a clipped stack.", "milestone", "ai_coding", False,
     [("slog", "library"), ("Go", "language"), ("panic", "pattern"), ("print-and-pray", "pattern")],
     [("slog", "print-and-pray", "REPLACES")],
     "how do Go binaries now report panics in a structured form callers can ingest",
     "slog structured panic recover json goroutine request id stack"),
    # --- 45 ---
    ("Bulk-import job swapped from at-most-once to exactly-once delivery using transactional writes plus an idempotency table keyed on (source, record_id); duplicates cost a primary key conflict, not a re-process.", "architecture", "ai_coding", False,
     [("Bulk-import", "service"), ("idempotency table", "pattern"), ("exactly-once", "concept"), ("at-most-once", "concept")],
     [("exactly-once", "at-most-once", "REPLACES")],
     "how did the bulk-import job move from at-most-once to exactly-once without re-processing duplicates",
     "exactly once idempotency table source record id transactional import"),
    # --- 46 ---
    ("Server timeouts are layered: ReadTimeout 5s, WriteTimeout 10s, IdleTimeout 60s, plus a per-handler context deadline; before the layering a slow client could keep a worker for hours.", "problem", "ai_coding", False,
     [("ReadTimeout", "config"), ("WriteTimeout", "config"), ("IdleTimeout", "config")],
     [],
     "which timeout layering closed a slow-client hold gap on the HTTP server",
     "read write idle handler timeout layer slow client worker pin"),
    # --- 47 ---
    ("Error budget ties the retry policy: when the SLO error budget is below 50 percent the SDK halves max_attempts to keep retries from burning what's left of the budget.", "architecture", "ai_coding", False,
     [("error budget", "concept"), ("SLO", "concept"), ("SDK", "project")],
     [],
     "how does the SDK's retry policy adapt when the SLO error budget runs low",
     "error budget slo retry attempt halve burn protect adaptive"),
    # --- 48. noise ---
    ("Someone keeps moving the spare keyboard one desk over each morning and nobody will admit to it.", "fact", "noise", True, [], [], None, None),
    # --- 49 ---
    ("Abandoned a custom finite-state-machine retry implementation after benchmarks showed Failsafe's RetryPolicy hit the same throughput with a tenth of the code; the FSM module was deleted on 2026-04-09.", "decision", "ai_coding", False,
     [("Failsafe", "library"), ("RetryPolicy", "method"), ("finite-state-machine", "pattern"), ("2026-04-09", "date")],
     [("Failsafe", "finite-state-machine", "REPLACES")],
     "why did the custom retry FSM get deleted in favour of Failsafe's RetryPolicy",
     "failsafe retry policy finite state machine delete benchmark parity"),
    # --- 50 ---
    ("Wrapping every external call in a TimeoutError-then-fallback decorator surfaced two upstreams without published p99 SLOs; the decorator now reports any call site lacking a timeout config to a registry.", "fact", "ai_coding", False,
     [("TimeoutError", "error"), ("fallback", "pattern"), ("registry", "pattern")],
     [],
     "which decorator pattern revealed external calls missing a configured timeout and SLO",
     "timeout error fallback decorator registry surface missing slo p99"),
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
