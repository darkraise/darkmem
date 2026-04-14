"""One-off emitter for shared-base batch-042 — ai_coding domain (API design / SDK ergonomics / client libraries / public-interface evolution).

Writes 50 rows to data/v2/shared/batch_042.tmp.jsonl with ids shared-02051..02100.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_042.tmp.jsonl"
ID_OFFSET = 2050

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Switched the public list endpoints from offset to cursor-based pagination; the opaque cursor hides the sort key and survives row inserts mid-scan.", "decision", "ai_coding", False,
     [("cursor-based pagination", "pattern"), ("offset", "pattern")],
     [("cursor-based pagination", "offset", "REPLACES")],
     "which pagination approach did we adopt for public list endpoints and why",
     "pagination cursor offset opaque sort key stable scan insert"),
    # --- 2 ---
    ("Made the payments POST endpoint accept an Idempotency-Key header; duplicate keys within 24 hours return the original 201 response bit-for-bit.", "architecture", "ai_coding", False,
     [("Idempotency-Key", "config"), ("payments", "api")],
     [],
     "how did we make the payments creation endpoint safe against client retries",
     "idempotency key header replay window duplicate request stripe style"),
    # --- 3 ---
    ("Renamed the rate-limit headers from X-RateLimit-* to the RFC 9156 RateLimit-* form; kept the old names as aliases for one major version.", "decision", "ai_coding", False,
     [("X-RateLimit", "config"), ("RateLimit", "config"), ("RFC 9156", "protocol")],
     [("RateLimit", "X-RateLimit", "REPLACES")],
     "which header name standardisation did the public API move to and what compat window",
     "rate limit header rename draft standard alias deprecation window"),
    # --- 4 ---
    ("Adopted RFC 7807 problem+json for all 4xx and 5xx bodies; the type URI doubles as a stable error code that SDKs pattern-match against.", "architecture", "ai_coding", False,
     [("RFC 7807", "protocol"), ("problem+json", "protocol")],
     [],
     "which error envelope standard did the public API settle on for failure responses",
     "error envelope problem details type URI stable code SDK match"),
    # --- 5 ---
    ("Added an ?expand= query param for opt-in field expansion on invoice responses; kept the default payload small so the list endpoint stayed fast.", "architecture", "ai_coding", False,
     [("expand", "pattern"), ("invoice", "api")],
     [],
     "how do clients pull related objects inline without bloating the default response",
     "field expansion opt in related object inline list performance"),
    # --- 6 ---
    ("Rejected JSON:API for the public interface; the included array and linkage shape forced every SDK to ship a normaliser before it felt idiomatic.", "decision", "ai_coding", False,
     [("JSON:API", "protocol"), ("SDK", "concept")],
     [],
     "which spec did we reject for the public API and what was the ergonomics objection",
     "json api spec reject included linkage normaliser ergonomic cost"),
    # --- 7 ---
    ("Sparse fieldsets via ?fields= cut mobile payload sizes by 60 percent on the timeline endpoint; the server rejects unknown fields instead of silently ignoring them.", "fact", "ai_coding", False,
     [("Sparse fieldsets", "pattern"), ("timeline", "api")],
     [],
     "which selection mechanism shrank the mobile list response and how does the server handle typos",
     "sparse fieldset selection payload shrink unknown field reject strict"),
    # --- 8 ---
    ("Streaming responses went SSE instead of WebSocket for the completions endpoint; HTTP semantics, intermediate proxies, and auth all worked unchanged.", "decision", "ai_coding", False,
     [("SSE", "protocol"), ("WebSocket", "protocol"), ("completions", "api")],
     [("SSE", "WebSocket", "PREFERS")],
     "which streaming transport did the completions API pick and what made it simpler",
     "server sent events WebSocket choice proxy auth HTTP semantics"),
    # --- 9 ---
    ("The SDK's retry policy is jittered exponential backoff capped at 30 seconds with a max of four attempts; only 408, 425, 429 and 5xx retry.", "architecture", "ai_coding", False,
     [("SDK", "concept")],
     [],
     "what retry policy ships in the client library and which statuses trigger it",
     "retry jitter exponential backoff cap attempt count idempotent status"),
    # --- 10. noise ---
    ("The coffee machine in the kitchen is back to beeping at random intervals again.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Marked the old /v1/charges endpoint with Deprecation and Sunset headers pointing at 2026-10-01; analytics now tells us exactly which keys still call it.", "milestone", "ai_coding", False,
     [("Deprecation", "config"), ("Sunset", "config"), ("2026-10-01", "date")],
     [],
     "which HTTP headers announce the retirement window for the legacy charges route",
     "deprecation sunset header retirement date analytics caller tracking"),
    # --- 12 ---
    ("Versioning moved to Stripe-style date pinning in the Api-Version header; URL path stays at /v1 forever and breaking changes land behind opt-in dates.", "decision", "ai_coding", False,
     [("Api-Version", "config"), ("/v1", "api")],
     [],
     "which versioning scheme did we adopt after rejecting URL path bumps",
     "date pin version header stripe style path freeze opt in break"),
    # --- 13 ---
    ("Rejected Accept-header content negotiation for versioning; CDNs cached the wrong variant twice and debug traces became a nightmare.", "decision", "ai_coding", False,
     [("Accept", "config"), ("CDN", "infrastructure")],
     [],
     "why did content-type-based API versioning get rejected during the design review",
     "accept header version negotiation CDN cache variant bug rationale"),
    # --- 14 ---
    ("Webhook signatures now rotate through a keyset rather than a single secret; publishers sign with the latest key, verifiers accept any active key.", "architecture", "ai_coding", False,
     [("Webhook", "pattern"), ("keyset", "pattern")],
     [],
     "how do webhook receivers verify payloads across a key rotation without downtime",
     "webhook signing key rotation active set rollover verify multi key"),
    # --- 15 ---
    ("Webhook replay protection uses a five-minute timestamp window plus a 24-hour Redis dedup on the signature; late retries still get the 200 they expect.", "architecture", "ai_coding", False,
     [("Webhook", "pattern"), ("Redis", "service")],
     [],
     "how does the webhook receiver stop replay attacks while staying friendly to late retries",
     "replay protect timestamp window signature dedup late retry ack"),
    # --- 16 ---
    ("Cursor pagination stayed consistent under deletes because the cursor encodes (created_at, id) from the snapshot; a removed row just no-ops.", "fact", "ai_coding", False,
     [("Cursor pagination", "pattern")],
     [],
     "why does the cursor-based list endpoint not skip or duplicate rows when items are deleted mid-scan",
     "pagination consistency deletion cursor encode tuple snapshot stable"),
    # --- 17 ---
    ("PATCH endpoints accept JSON Merge Patch by default; clients that need array reordering can opt into JSON Patch via a +json suffix media type.", "architecture", "ai_coding", False,
     [("JSON Merge Patch", "protocol"), ("JSON Patch", "protocol"), ("PATCH", "pattern")],
     [],
     "which partial-update semantics does the API default to and how do advanced clients switch",
     "merge patch json patch default semantics media type opt in"),
    # --- 18 ---
    ("Froze the spec at OpenAPI 3.1 despite tooling gaps; JSON Schema alignment was worth more than the codegen regression in one old generator.", "decision", "ai_coding", False,
     [("OpenAPI 3.1", "protocol"), ("JSON Schema", "protocol")],
     [("OpenAPI 3.1", "JSON Schema", "DEPENDS_ON")],
     "which OpenAPI version did we settle on and what trade-off made it worth the pain",
     "OpenAPI 3.1 pick json schema align tooling gap trade off"),
    # --- 19 ---
    ("Hand-rolled SDKs for Python and TypeScript; generated clients for Go, Ruby, Java and PHP — the core two carry the ergonomics budget the others don't need.", "decision", "ai_coding", False,
     [("Python", "language"), ("TypeScript", "language"), ("Go", "language"), ("Ruby", "language")],
     [],
     "which SDKs are hand-written versus generated and what drove the split",
     "hand roll SDK generate language split ergonomic budget priority"),
    # --- 20 ---
    ("Generated Go client used pointer-heavy optional fields; wrote a small post-processor to collapse them into nullable wrappers for ergonomic parity.", "problem", "ai_coding", False,
     [("Go", "language")],
     [],
     "which idiom in the generated Go SDK needed a post-pass to feel native",
     "generator Go pointer optional nullable wrapper post process ergonomic"),
    # --- 21 ---
    ("Public SDK constructors take an options bag instead of positional args; adding the Telemetry hook later didn't break anyone's call sites.", "preference", "ai_coding", False,
     [("Telemetry", "pattern"), ("SDK", "concept")],
     [],
     "which constructor shape did the SDKs standardise on and what future-proofing did it give",
     "options bag versus positional SDK constructor additive evolution"),
    # --- 22 ---
    ("Clients chain middleware in request order, response in reverse; the interceptor list is explicit on the client, never a global registry.", "architecture", "ai_coding", False,
     [("middleware", "pattern"), ("interceptor", "pattern")],
     [],
     "how does the SDK expose request interception and why not a global registry",
     "middleware chain client side explicit list global registry avoid"),
    # --- 23 ---
    ("Added a telemetry hook interface so hosts plug in their own logging or metrics; the SDK ships a no-op implementation by default.", "architecture", "ai_coding", False,
     [("telemetry hook", "pattern"), ("SDK", "concept")],
     [],
     "which SDK extension point lets the host app capture request timing and failures",
     "telemetry hook interface pluggable default no op observability"),
    # --- 24 ---
    ("Responses emit Cache-Control: stale-while-revalidate=60 on GETs; well-behaved clients serve the stale body while refreshing in the background.", "fact", "ai_coding", False,
     [("Cache-Control", "config"), ("stale-while-revalidate", "pattern")],
     [],
     "which caching directive lets the CDN serve old responses while refetching silently",
     "stale while revalidate cache control directive background refresh"),
    # --- 25 ---
    ("Enabled Server-Timing on every response; SDKs surface the breakdown through the telemetry hook so app owners see queue, db and compute segments.", "milestone", "ai_coding", False,
     [("Server-Timing", "config")],
     [],
     "which header now exposes server-side latency breakdown to SDK consumers",
     "server timing header segment expose SDK telemetry hook propagate"),
    # --- 26 ---
    ("SDKs inject traceparent and tracestate on every outbound request; if the host has an OpenTelemetry context, spans propagate end to end with no config.", "architecture", "ai_coding", False,
     [("traceparent", "config"), ("tracestate", "config"), ("OpenTelemetry", "tool")],
     [],
     "how does the client library propagate distributed tracing context automatically",
     "trace context inject SDK propagate host telemetry zero config"),
    # --- 27 ---
    ("Streaming SSE responses wrap events in a sealed envelope with type and seq; that lets reconnect-with-Last-Event-Id replay from the exact gap.", "architecture", "ai_coding", False,
     [("SSE", "protocol"), ("Last-Event-Id", "config")],
     [],
     "which envelope design lets clients resume a streaming response after disconnection",
     "sealed envelope sequence SSE reconnect last event id resume gap"),
    # --- 28 ---
    ("The Python SDK exposes both sync and async clients from the same package; the async variant is the blessed path and sync wraps it via asyncio.run internally.", "architecture", "ai_coding", False,
     [("Python", "language"), ("asyncio", "library")],
     [],
     "how does the Python SDK keep sync and async parity without two separate packages",
     "SDK sync async pair blessed path wrap single package parity"),
    # --- 29 ---
    ("Pagination helpers in the SDKs return AsyncIterator objects; for loops just work and the client handles cursor threading and backpressure transparently.", "fact", "ai_coding", False,
     [("AsyncIterator", "pattern"), ("SDK", "concept")],
     [],
     "which iteration primitive hides pagination cursor plumbing from SDK users",
     "async iterator pagination helper cursor threading user transparent"),
    # --- 30 ---
    ("Error classes mirror the problem+json type hierarchy: a ConflictError carries the retry_after and conflicting_id fields decoded from the envelope.", "architecture", "ai_coding", False,
     [("problem+json", "protocol"), ("ConflictError", "concept")],
     [],
     "how does the SDK surface structured error information from the RFC 7807 envelope",
     "error class hierarchy problem detail field decode retry after"),
    # --- 31 ---
    ("Removed positional arguments from every new public method on 2026-03-05; keyword-only signatures let us add parameters without breaking language bindings.", "milestone", "ai_coding", False,
     [("2026-03-05", "date")],
     [],
     "when did the SDK style guide switch to keyword-only parameters on new public methods",
     "keyword only argument rule SDK evolution additive date change"),
    # --- 32 ---
    ("Kept the Java SDK on a builder pattern for request construction; it matches idiom and keeps the fluent chain findable in IDE autocomplete.", "preference", "ai_coding", False,
     [("Java", "language"), ("builder pattern", "pattern")],
     [],
     "which construction style did the Java SDK keep and why against the shared options-bag rule",
     "Java SDK builder pattern idiom IDE autocomplete fluent chain"),
    # --- 33 ---
    ("Documented the SDK stability tiers: stable, preview and experimental; experimental classes live under a _preview subpackage and can break between minor versions.", "architecture", "ai_coding", False,
     [("SDK", "concept")],
     [],
     "which stability tiering scheme does the SDK publish and where do experimental APIs live",
     "stability tier stable preview experimental subpackage break policy"),
    # --- 34 ---
    ("Never reuse a removed field name inside the same API version; the status-field rebrand taught us this when it reassigned a string enum to an integer code.", "preference", "ai_coding", False,
     [("status", "pattern"), ("API version", "pattern")],
     [],
     "what public-API evolution rule did the status-field rebrand disaster teach us",
     "field name reuse avoid same version rebrand type change breakage"),
    # --- 35 ---
    ("The SDKs expose a raw_response property on every return object; power users can read headers, status and request id without a separate low-level client.", "fact", "ai_coding", False,
     [("SDK", "concept")],
     [],
     "which SDK affordance exposes underlying HTTP response details without a second client",
     "raw response property low level access header status request id"),
    # --- 36 ---
    ("Request IDs are echoed from the X-Request-Id header into every error object; the support runbook tells customers to paste that string first.", "architecture", "ai_coding", False,
     [("X-Request-Id", "config")],
     [],
     "which correlation identifier do errors carry and how is it surfaced to customers",
     "request id correlate error echo header support runbook trace"),
    # --- 37 ---
    ("Adopted additive JSON evolution only: new fields are optional, enum values are extensible, and unknown fields are preserved on round-trip.", "preference", "ai_coding", False,
     [("JSON", "concept")],
     [],
     "which JSON compatibility policy keeps the API backward compatible within a major version",
     "additive evolution optional field enum extensible unknown preserve"),
    # --- 38 ---
    ("Public enums are open sets in the SDKs: unknown variants deserialise into a typed Unknown(str) wrapper instead of crashing old clients.", "architecture", "ai_coding", False,
     [("SDK", "concept")],
     [],
     "how does the SDK keep old clients alive when the server adds new enum values",
     "open enum unknown variant wrapper forward compat old client"),
    # --- 39 ---
    ("Timeouts split into connect, read, and total on the HTTP client; a slow TLS handshake no longer eats the entire budget meant for the response.", "architecture", "ai_coding", False,
     [("HTTP client", "concept"), ("TLS", "protocol")],
     [],
     "which timeout model did the SDK adopt and what slow-connect bug did it fix",
     "timeout split connect read total TLS handshake budget isolate"),
    # --- 40 ---
    ("User-Agent is built from SDK name, SDK version, language version, and OS; server-side dashboards spot old SDK versions driving error spikes in minutes.", "fact", "ai_coding", False,
     [("User-Agent", "config"), ("SDK", "concept")],
     [],
     "what does the SDK's User-Agent encode and why does the server side care",
     "user agent format SDK version language OS dashboard drill error"),
    # --- 41 ---
    ("Conditional requests work through ETag and If-None-Match; a 304 in the SDK returns the cached object silently, hiding the conditional dance from callers.", "fact", "ai_coding", False,
     [("ETag", "config"), ("If-None-Match", "config")],
     [],
     "how does the SDK use conditional requests to avoid redundant payload parsing",
     "etag if none match conditional 304 cached object silent return"),
    # --- 42 ---
    ("Sparse update conflicts return 409 with a problem+json instance that includes current_version and expected_version; the SDK raises a single OptimisticLockError.", "architecture", "ai_coding", False,
     [("problem+json", "protocol"), ("OptimisticLockError", "concept")],
     [],
     "how does the API communicate optimistic-lock failures and how do SDKs surface them",
     "optimistic lock 409 version mismatch problem detail error class"),
    # --- 43 ---
    ("Docs publish a public deprecation policy: 180 days notice in changelog plus Deprecation header on every response, and usage reports for the owning team.", "preference", "ai_coding", False,
     [("Deprecation", "config")],
     [],
     "which deprecation commitment did we publish for public endpoints and how is it enforced",
     "deprecation policy notice window header changelog usage report"),
    # --- 44 ---
    ("Long-running operations return a 202 with an Operation-Location header; the SDK hides polling behind a wait_for method that respects Retry-After.", "architecture", "ai_coding", False,
     [("Operation-Location", "config"), ("Retry-After", "config")],
     [],
     "which pattern does the API use for long-running operations and how do SDKs abstract the poll",
     "long running operation 202 location poll retry after wait method"),
    # --- 45 ---
    ("The bulk endpoints accept a partial-success response body with per-item status; clients get a typed BulkResult with successes, retryable, and permanent sublists.", "fact", "ai_coding", False,
     [("BulkResult", "concept")],
     [],
     "how do bulk endpoints communicate per-item outcomes back to SDK callers",
     "bulk endpoint partial success per item status typed result split"),
    # --- 46 ---
    ("Every response carries an X-Idempotency-Replayed header when the key matched a prior request; tests assert this on retry paths to prove the write ran once.", "fact", "ai_coding", False,
     [("X-Idempotency-Replayed", "config")],
     [],
     "which header proves to clients and tests that an idempotent retry hit the cache path",
     "idempotency replayed header assert retry prior request prove"),
    # --- 47 ---
    ("SDK publishing pipeline enforces semantic version rules through a golden-diff check against the prior minor; a breaking change fails the release job.", "architecture", "ai_coding", False,
     [("SDK", "concept")],
     [],
     "which release-gate stops an accidental breaking change from shipping in a minor SDK bump",
     "semver check golden diff prior release breaking change gate"),
    # --- 48 ---
    ("Dropped the Accept: application/vnd.api+json content type once the JSON:API rewrite was abandoned; it survived for three months as dead config before removal.", "problem", "ai_coding", False,
     [("Accept", "config"), ("JSON:API", "protocol")],
     [],
     "which dead content-type survived an abandoned API rewrite and had to be cleaned up later",
     "dead media type json api abandoned rewrite cleanup delay config"),
    # --- 49 ---
    ("Capability discovery goes through a GET /.well-known/api-capabilities resource that enumerates enabled features; the SDK caches it per base URL for the process lifetime.", "architecture", "ai_coding", False,
     [(".well-known/api-capabilities", "api"), ("SDK", "concept")],
     [],
     "how do SDKs learn which optional API features the server has enabled",
     "capability discovery well known endpoint feature flag SDK cache"),
    # --- 50 ---
    ("Every SDK ships a single-line mock transport for tests; swapping it in requires one constructor arg and replays canned responses without touching HTTP.", "fact", "ai_coding", False,
     [("SDK", "concept")],
     [],
     "which SDK testing affordance lets consumers stub responses without running an HTTP server",
     "mock transport swap SDK test stub response HTTP bypass ergonomic"),
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
