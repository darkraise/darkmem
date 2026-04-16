"""One-off emitter for shared-base batch-171 — technical domain (REST API design and HTTP semantics: OpenAPI, pagination, conditional requests, problem+json, rate limits, versioning).

Writes 50 rows to data/v2/shared/batch_171.tmp.jsonl with ids shared-08501..08550.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_171.tmp.jsonl"
ID_OFFSET = 8500

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Pinned the public API spec to OpenAPI 3.1 so JSON Schema 2020-12 lines up with our validation layer; the old Swagger 2.0 spec had to shim nullable and oneOf by hand on every release.", "decision", "technical", False,
     [("OpenAPI 3.1", "protocol"), ("JSON Schema 2020-12", "protocol"), ("Swagger 2.0", "protocol")],
     [("OpenAPI 3.1", "Swagger 2.0", "REPLACES"), ("OpenAPI 3.1", "JSON Schema 2020-12", "USES")],
     "which spec version did the public API adopt so schema validation stopped needing handwritten shims",
     "openapi 3.1 swagger 2.0 json schema 2020 nullable oneof shim"),
    # --- 2 architecture ---
    ("Resource modelling treats invoices as the aggregate root and line-items as a sub-collection under /invoices/{id}/items; cross-resource writes go through a dedicated transfer endpoint rather than PATCH chains.", "architecture", "technical", False,
     [("invoices", "concept"), ("line-items", "concept"), ("PATCH", "method")],
     [("invoices", "line-items", "HAS_PART")],
     "how are invoices and line-items modelled as nested resources and where do cross-resource writes land",
     "invoice line item aggregate root sub collection transfer patch chain"),
    # --- 3 milestone ---
    ("Shipped idempotency-key support on all POST mutation endpoints; replays within the 24-hour window return the cached response body and status without re-executing the write path.", "milestone", "technical", False,
     [("idempotency-key", "pattern"), ("POST", "method")],
     [("idempotency-key", "POST", "APPLIES_TO")],
     "which header landed on POST mutations so safe retries return the cached response within a day",
     "idempotency key post mutation replay cache 24 hour window retry"),
    # --- 4 decision ---
    ("Cursor pagination replaced the offset-based listing on the events API; deep pages on offset were running seq-scans on the audit_log table and p99 latency spiked past three seconds.", "decision", "technical", False,
     [("Cursor pagination", "pattern"), ("offset-based", "pattern"), ("audit_log", "database"), ("events API", "api")],
     [("Cursor pagination", "offset-based", "REPLACES")],
     "which pagination flavour replaced offset on the events API and which table drove the change",
     "cursor offset pagination event api audit log seq scan latency"),
    # --- 5 architecture ---
    ("ETag headers on resource reads are a weak hash of the JSON body plus the row's updated_at timestamp; clients send If-Match on PUT and the server returns 412 Precondition Failed if the value drifted.", "architecture", "technical", False,
     [("ETag", "pattern"), ("If-Match", "pattern"), ("PUT", "method"), ("412 Precondition Failed", "pattern")],
     [("If-Match", "ETag", "USES")],
     "how does the PUT pathway use ETag and If-Match to reject stale writes from concurrent clients",
     "etag if match put 412 precondition failed weak hash updated at"),
    # --- 6 fact ---
    ("GET collection endpoints emit a strong ETag derived from the max updated_at of the listing; a matching If-None-Match returns 304 Not Modified without serialising the body or hitting the read replica.", "fact", "technical", False,
     [("If-None-Match", "pattern"), ("304 Not Modified", "pattern"), ("strong ETag", "pattern")],
     [("If-None-Match", "strong ETag", "USES")],
     "how does a collection GET short-circuit to 304 when the client already has the latest listing",
     "if none match 304 not modified strong etag collection get replica"),
    # --- 7 decision ---
    ("Versioning moved from URL prefixes to an Accept header with application/vnd.company.v3+json; the old /v1, /v2, /v3 paths were fragmenting URL-based caches and breaking clean HATEOAS links.", "decision", "technical", False,
     [("Accept header", "pattern"), ("URL prefixes", "pattern"), ("application/vnd.company.v3+json", "protocol"), ("HATEOAS", "pattern")],
     [("Accept header", "URL prefixes", "REPLACES")],
     "which versioning scheme replaced URL prefixes and which discovery pattern did it stop fragmenting",
     "accept header url prefix media type vendor vnd hateoas cache v3"),
    # --- 8 reference ---
    ("RFC 7807 specifies the problem+json error shape with fields type, title, status, detail, and instance; the API contract mandates every 4xx and 5xx response carry this envelope.", "reference", "technical", False,
     [("RFC 7807", "protocol"), ("problem+json", "protocol")],
     [("problem+json", "RFC 7807", "IMPLEMENTS")],
     "which spec defines the problem+json error envelope and which status classes have to carry it",
     "rfc 7807 problem json type title status detail instance 4xx 5xx"),
    # --- 9 milestone ---
    ("Long-running imports return 202 Accepted with a Location header pointing at /jobs/{id}; clients poll that URL and get 200 with the finished resource once the job state flips to succeeded.", "milestone", "technical", False,
     [("202 Accepted", "pattern"), ("Location", "pattern"), ("/jobs/{id}", "api")],
     [("202 Accepted", "Location", "USES")],
     "how does the import endpoint hand off long work and where do clients poll for completion",
     "202 accepted location header job poll long running async import"),
    # --- 10 noise ---
    ("The kitchen microwave keeps adding thirty seconds to whatever time you enter and nobody has admitted to programming it that way.", "fact", "noise", True, [], [], None, None),
    # --- 11 decision ---
    ("Picked Redoc over Swagger UI for the public docs site; the single-page layout rendered the 1800-operation spec without the sidebar stalls that Swagger UI hit around operation 600.", "decision", "technical", False,
     [("Redoc", "tool"), ("Swagger UI", "tool")],
     [("Redoc", "Swagger UI", "PREFERS")],
     "which documentation renderer won the public docs bake-off on the large operation count",
     "redoc swagger ui public docs render 1800 operation sidebar stall"),
    # --- 12 preference ---
    ("The platform team uses Stoplight Studio for spec authoring; the visual editor caught three malformed $ref cycles that the text editor workflow kept missing on review.", "preference", "technical", False,
     [("Stoplight Studio", "tool"), ("$ref", "pattern")],
     [],
     "which spec-authoring tool does the platform team favour and which class of bug did it catch",
     "stoplight studio spec author visual ref cycle review malformed"),
    # --- 13 architecture ---
    ("HATEOAS links ride inside a _links map on every resource; clients follow rel names like self, next, and cancel rather than string-concatenating URLs from ids.", "architecture", "technical", False,
     [("HATEOAS", "pattern"), ("_links", "pattern"), ("rel", "concept")],
     [("_links", "HATEOAS", "IMPLEMENTS")],
     "how does the API expose navigation so clients stop concatenating URLs from resource ids",
     "hateoas links rel self next cancel concatenate url client follow"),
    # --- 14 decision ---
    ("Dropped JSON:API in favour of a hand-rolled envelope; the sparse fieldsets feature looked clean on paper but teams kept over-fetching anyway and the spec overhead wasn't paying rent.", "decision", "technical", False,
     [("JSON:API", "protocol"), ("sparse fieldsets", "pattern")],
     [],
     "which hypermedia standard got dropped in favour of a custom envelope and what feature never paid off",
     "json api sparse fieldset envelope overhead hand rolled over fetch"),
    # --- 15 reference ---
    ("HAL and Siren are two hypermedia formats layered over JSON; HAL stays minimal with _links and _embedded while Siren adds actions and classes for richer client affordances.", "reference", "technical", False,
     [("HAL", "protocol"), ("Siren", "protocol"), ("_embedded", "pattern")],
     [("Siren", "HAL", "EXTENDS")],
     "how do HAL and Siren compare for hypermedia affordances beyond plain JSON payloads",
     "hal siren hypermedia links embedded action class affordance format"),
    # --- 16 problem ---
    ("CORS preflight started failing on the new admin subdomain because an OPTIONS handler returned 404 instead of 204; Access-Control-Allow-Origin never reached the browser and fetch threw network error.", "problem", "technical", False,
     [("CORS", "protocol"), ("OPTIONS", "method"), ("Access-Control-Allow-Origin", "pattern"), ("admin subdomain", "service")],
     [("OPTIONS", "CORS", "APPLIES_TO")],
     "which missing handler broke CORS preflight on the admin subdomain and how did the failure surface",
     "cors preflight options 404 204 allow origin admin network error"),
    # --- 17 preference ---
    ("Session cookies carry SameSite=Lax plus a double-submit CSRF token; the legacy SameSite=None flow stayed only for the embedded partner widget and tightened its origin allowlist.", "preference", "technical", False,
     [("SameSite=Lax", "pattern"), ("CSRF token", "pattern"), ("SameSite=None", "pattern"), ("partner widget", "service")],
     [("SameSite=Lax", "CSRF token", "USES")],
     "how does the session layer defend against CSRF and where does the older SameSite=None mode survive",
     "samesite lax csrf double submit token none partner widget cookie"),
    # --- 18 decision ---
    ("OAuth 2.1 bearer tokens replaced the in-house session cookie for third-party access; the API gateway acts as the resource server and validates tokens against the JWKS endpoint on every request.", "decision", "technical", False,
     [("OAuth 2.1", "protocol"), ("bearer tokens", "pattern"), ("API gateway", "service"), ("JWKS", "protocol"), ("session cookie", "pattern")],
     [("OAuth 2.1", "session cookie", "REPLACES"), ("API gateway", "JWKS", "USES")],
     "which token scheme replaced session cookies for third-party access and what validates each request",
     "oauth bearer session cookie api gateway jwks resource server"),
    # --- 19 fact ---
    ("Rate-limit headers follow the X-RateLimit-Limit, X-RateLimit-Remaining, and X-RateLimit-Reset convention; a 429 response always carries Retry-After so clients can back off deterministically.", "fact", "technical", False,
     [("X-RateLimit-Limit", "pattern"), ("X-RateLimit-Remaining", "pattern"), ("X-RateLimit-Reset", "pattern"), ("429", "pattern"), ("Retry-After", "pattern")],
     [("429", "Retry-After", "USES")],
     "which headers advertise rate-limit state and what does a 429 attach so clients back off deterministically",
     "x ratelimit limit remaining reset 429 retry after back off header"),
    # --- 20 reference ---
    ("Deprecated endpoints return the Sunset header with an RFC 3339 date plus a Deprecation: true flag; SDK release notes pin the sunset date three minor versions ahead of removal.", "reference", "technical", False,
     [("Sunset header", "pattern"), ("Deprecation", "pattern"), ("RFC 3339", "protocol")],
     [("Sunset header", "RFC 3339", "USES")],
     "how does the API signal an endpoint is on its way out and how far ahead do SDK release notes pin the date",
     "sunset deprecation header rfc 3339 date sdk release note remove"),
    # --- 21 decision ---
    ("Keyset pagination went in for the reports endpoint because cursor tokens were getting opaque-blob-leaked into client bug reports; keyset uses a signed (updated_at, id) tuple clients can paste safely.", "decision", "technical", False,
     [("Keyset pagination", "pattern"), ("cursor tokens", "pattern"), ("reports endpoint", "api")],
     [("Keyset pagination", "cursor tokens", "REPLACES")],
     "which pagination flavour replaced cursor tokens on the reports endpoint and why",
     "keyset cursor pagination report updated at id tuple leak bug"),
    # --- 22 milestone ---
    ("Filtering uses RSQL-style query strings on the list endpoints; sorting passes a comma-separated sort=field,-other parameter and the server caps it at three fields to keep index planning bounded.", "milestone", "technical", False,
     [("RSQL", "protocol"), ("sort", "pattern")],
     [],
     "which filter syntax does the list endpoint expose and how is sort capped to keep query plans sane",
     "rsql filter sort comma field list endpoint three cap index plan"),
    # --- 23 fact ---
    ("Content negotiation broke on one legacy client that sent Accept: */* and expected application/xml; the server correctly chose JSON and the client silently parsed nothing, so we pinned a default per OAuth client.", "fact", "technical", False,
     [("Accept", "pattern"), ("application/xml", "protocol"), ("JSON", "protocol"), ("OAuth client", "service")],
     [],
     "which content negotiation edge case broke a legacy client and how did we pin the default",
     "content negotiation accept xml json legacy wildcard default oauth"),
    # --- 24 decision ---
    ("Chose Spectral for CI spec linting; the ruleset blocks operations without summary, missing error schemas, and any 4xx that isn't problem+json, so regressions never reach the preview docs.", "decision", "technical", False,
     [("Spectral", "tool"), ("CI", "service")],
     [("Spectral", "CI", "DEPLOYED_ON")],
     "which linter gates the spec in CI and what rules block regressions before the preview docs ship",
     "spectral spec lint ci summary error schema 4xx problem json block"),
    # --- 25 architecture ---
    ("POST /payments accepts an Idempotency-Key header, writes a (key, request_hash) row in Postgres within the same transaction, and rejects reuse across different bodies with 422 Unprocessable Entity.", "architecture", "technical", False,
     [("Idempotency-Key", "pattern"), ("Postgres", "database"), ("/payments", "api"), ("422 Unprocessable Entity", "pattern")],
     [("/payments", "Idempotency-Key", "USES"), ("/payments", "Postgres", "DEPENDS_ON")],
     "how does the payments endpoint persist idempotency keys and what status rejects key reuse with a new body",
     "idempotency key payments postgres request hash 422 unprocessable reuse"),
    # --- 26 milestone ---
    ("Public beta of the v4 API went live behind application/vnd.company.v4+json content type; clients opting in also get the new Problem Details extension members per RFC 9457.", "milestone", "technical", False,
     [("v4 API", "api"), ("application/vnd.company.v4+json", "protocol"), ("RFC 9457", "protocol"), ("Problem Details", "pattern")],
     [("Problem Details", "RFC 9457", "IMPLEMENTS")],
     "which API version went to public beta and which problem-details update ships alongside opt-in clients",
     "v4 api beta media type vendor problem details rfc 9457 extension"),
    # --- 27 decision ---
    ("Conditional POST-to-create uses If-None-Match: * so a retry that races with the first write returns 412 instead of creating a duplicate; the old natural-key upsert kept racing under load.", "decision", "technical", False,
     [("If-None-Match: *", "pattern"), ("POST", "method"), ("natural-key upsert", "pattern")],
     [("If-None-Match: *", "natural-key upsert", "REPLACES")],
     "which conditional header replaced natural-key upsert for racing create retries and what status signals it",
     "if none match star post create 412 duplicate race natural key upsert"),
    # --- 28 fact ---
    ("PATCH semantics on the API follow RFC 7396 JSON Merge Patch; the alternative JSON Patch from RFC 6902 is only exposed on /documents where array splice semantics matter.", "fact", "technical", False,
     [("RFC 7396", "protocol"), ("JSON Merge Patch", "protocol"), ("RFC 6902", "protocol"), ("JSON Patch", "protocol"), ("/documents", "api")],
     [("JSON Patch", "RFC 6902", "IMPLEMENTS"), ("/documents", "JSON Patch", "USES")],
     "which two PATCH bodies does the API support and which endpoint specifically needs array splice ops",
     "rfc 7396 merge patch 6902 json patch documents array splice"),
    # --- 29 architecture ---
    ("Webhook deliveries sign the payload with HMAC-SHA256 in an X-Signature header and include an X-Delivery-Id for idempotent consumers; receivers must ack 2xx within ten seconds or the delivery retries.", "architecture", "technical", False,
     [("HMAC-SHA256", "algorithm"), ("X-Signature", "pattern"), ("X-Delivery-Id", "pattern"), ("Webhook", "pattern")],
     [("Webhook", "HMAC-SHA256", "USES")],
     "how are webhook payloads authenticated and what does the receiver need to do within ten seconds",
     "webhook hmac sha256 x signature delivery id idempotent retry ack"),
    # --- 30 preference ---
    ("The backend team prefers verb-free URLs: /orders/{id}/cancel is modelled as POST /orders/{id}/cancellations producing a Cancellation resource, keeping HTTP verbs doing the action layer.", "preference", "technical", False,
     [("/orders/{id}/cancellations", "api"), ("Cancellation", "concept")],
     [],
     "which URL style does the backend team prefer for actions like cancel on orders",
     "verb free url order cancel cancellation post resource action http"),
    # --- 31 problem ---
    ("304 Not Modified responses were leaking a Content-Length of the full body because the CDN was adding it post-origin; fixed by stripping headers on the cache layer and returning a truly empty response.", "problem", "technical", False,
     [("304 Not Modified", "pattern"), ("Content-Length", "pattern"), ("CDN", "infrastructure")],
     [],
     "which CDN bug broke 304 responses by attaching a body length and where did we fix it",
     "304 not modified content length cdn cache strip empty body leak"),
    # --- 32 milestone ---
    ("Discovery is served from /.well-known/openapi.json and /.well-known/oauth-authorization-server; SDK generators pin both URLs and regenerate clients weekly in CI.", "milestone", "technical", False,
     [("/.well-known/openapi.json", "api"), ("/.well-known/oauth-authorization-server", "api"), ("SDK generators", "tool")],
     [],
     "which two well-known URLs does the API publish for SDK generators to discover the spec and auth server",
     "well known openapi oauth authorization server sdk discovery generate"),
    # --- 33 decision ---
    ("Skipped gRPC for external traffic and stuck with JSON over HTTP/2; grpc-web would have needed a translating proxy anyway and the team's tooling around curl, Postman, and Redoc stays useful.", "decision", "technical", False,
     [("gRPC", "protocol"), ("HTTP/2", "protocol"), ("grpc-web", "protocol"), ("Postman", "tool")],
     [("gRPC", "grpc-web", "DEPENDS_ON")],
     "why did the external traffic stay JSON over HTTP/2 instead of adopting gRPC as the transport",
     "grpc json http 2 grpc web proxy curl postman redoc external"),
    # --- 34 fact ---
    ("Every successful mutation returns the full updated resource in the response body instead of a bare 204; this keeps clients from chasing the write with a GET round-trip on slow links.", "fact", "technical", False,
     [("204", "pattern"), ("GET", "method"), ("mutation", "concept")],
     [],
     "why do mutation responses return the full resource instead of a bare 204 across the API",
     "204 no content get round trip mutation full resource body slow link"),
    # --- 35 architecture ---
    ("Cursor tokens are opaque base64-encoded HMAC-signed payloads carrying (last_id, sort_direction, filter_hash); tampering fails verification and the server returns 400 Bad Request with a problem+json body.", "architecture", "technical", False,
     [("Cursor tokens", "pattern"), ("HMAC", "algorithm"), ("base64", "algorithm"), ("400 Bad Request", "pattern")],
     [("Cursor tokens", "HMAC", "USES")],
     "how are cursor tokens signed and what status does a tampered cursor get back on the next listing call",
     "cursor token hmac base64 sign last id filter hash 400 bad request"),
    # --- 36 decision ---
    ("Rate limits are per-token-per-route and tracked in Redis with a sliding-window counter; the earlier fixed-window counter was letting traffic double at window boundaries during synthetic load tests.", "decision", "technical", False,
     [("Redis", "database"), ("sliding-window", "algorithm"), ("fixed-window", "algorithm"), ("Rate limits", "pattern")],
     [("sliding-window", "fixed-window", "REPLACES"), ("Rate limits", "Redis", "DEPLOYED_ON")],
     "which rate-limit algorithm replaced fixed-window and where is the counter state kept",
     "rate limit redis sliding window fixed window boundary double synthetic"),
    # --- 37 problem ---
    ("A 502 Bad Gateway spike traced to the upstream resetting HTTP/2 streams mid-response; switched the gateway's idle timeout up and added h2 ping-frame keepalives to the origin pool.", "problem", "technical", False,
     [("502 Bad Gateway", "pattern"), ("HTTP/2", "protocol"), ("gateway", "service"), ("h2 ping-frame", "pattern")],
     [("gateway", "HTTP/2", "USES")],
     "which HTTP/2 tuning knobs cleared the 502 spike on the gateway and why were streams resetting mid-response",
     "502 bad gateway http 2 stream reset idle timeout h2 ping keepalive"),
    # --- 38 milestone ---
    ("The contract-test harness now diff-checks the deployed OpenAPI against the merged spec on every canary; a breaking change fails the canary promotion and pages the on-call.", "milestone", "technical", False,
     [("contract-test harness", "tool"), ("OpenAPI", "protocol"), ("canary", "pattern")],
     [("contract-test harness", "OpenAPI", "USES")],
     "which automated gate catches a breaking API change and what does it do during canary promotion",
     "contract test openapi diff canary promote breaking change page on call"),
    # --- 39 reference ---
    ("RFC 9110 consolidated HTTP semantics across 7230-7235; the team cites it for caching, conditional requests, and method idempotency rather than chasing the older doc chain.", "reference", "technical", False,
     [("RFC 9110", "protocol"), ("HTTP semantics", "concept")],
     [("RFC 9110", "HTTP semantics", "IMPLEMENTS")],
     "which consolidated spec does the team now cite for HTTP semantics instead of the older RFC chain",
     "rfc 9110 http semantics 7230 7235 cache conditional idempotent consolidate"),
    # --- 40 architecture ---
    ("Error payloads include an extension member trace_id mapped to the W3C Trace Context traceparent header; support can correlate a problem+json response to an OpenTelemetry span in under a minute.", "architecture", "technical", False,
     [("trace_id", "pattern"), ("W3C Trace Context", "protocol"), ("traceparent", "pattern"), ("OpenTelemetry", "framework"), ("problem+json", "protocol")],
     [("problem+json", "trace_id", "HAS_PART"), ("trace_id", "traceparent", "USES")],
     "how does a problem+json response let support jump straight to the OpenTelemetry span for a failing request",
     "trace id traceparent w3c trace context opentelemetry problem json correlate"),
    # --- 41 decision ---
    ("Soft-deleted resources respond with 410 Gone rather than 404 so clients can tell permanent removal from never-existed; SDK retry logic treats 410 as terminal and 404 as possibly a typo.", "decision", "technical", False,
     [("410 Gone", "pattern"), ("404", "pattern"), ("Soft-deleted", "pattern")],
     [],
     "why do soft-deleted resources return 410 instead of 404 and how do SDK retries treat each code",
     "410 gone 404 soft delete terminal retry sdk typo permanent removal"),
    # --- 42 preference ---
    ("Engineering prefers cursor tokens over page numbers in SDK method signatures; page numbers encourage jump-to-page UIs that scale-test badly against the keyset-backed index.", "preference", "technical", False,
     [("cursor tokens", "pattern"), ("page numbers", "pattern"), ("SDK", "tool"), ("keyset", "pattern")],
     [],
     "why does engineering keep page numbers out of SDK signatures despite client demand for jump-to-page UIs",
     "cursor token page number sdk jump page keyset index scale signature"),
    # --- 43 noise ---
    ("The office parrot mastered the sound of a Slack notification and half the floor keeps checking a phone that never buzzed.", "fact", "noise", True, [], [], None, None),
    # --- 44 architecture ---
    ("Expand queries pull a whitelisted set of sub-resources via ?expand=customer,shipments; each expansion cost is budgeted in the query planner and a breach returns 413 Payload Too Large before serialisation.", "architecture", "technical", False,
     [("Expand queries", "pattern"), ("query planner", "service"), ("413 Payload Too Large", "pattern")],
     [],
     "how does the expand parameter guard against runaway joins and what status rejects a too-heavy expansion",
     "expand query whitelist sub resource budget planner 413 payload too large"),
    # --- 45 fact ---
    ("Bearer tokens are JWTs with a 15-minute access lifetime and refresh tokens rotate on each use; audience claim pins a token to one resource server so cross-API replay stops at validation.", "fact", "technical", False,
     [("JWT", "protocol"), ("Bearer tokens", "pattern"), ("refresh tokens", "pattern"), ("audience claim", "pattern")],
     [("Bearer tokens", "JWT", "IMPLEMENTS")],
     "how do the token lifetimes and audience claim limit blast radius on a stolen bearer credential",
     "jwt bearer 15 minute access refresh rotate audience claim replay"),
    # --- 46 architecture ---
    ("A caching bug on the /me endpoint served one user's profile to another behind a shared CDN key; fixed by setting Cache-Control: private and adding Vary: Authorization on every authenticated response.", "architecture", "technical", False,
     [("/me", "api"), ("Cache-Control", "pattern"), ("Vary: Authorization", "pattern"), ("CDN", "infrastructure")],
     [],
     "which two cache headers landed on authenticated responses after the /me cross-user leak on the CDN",
     "me endpoint cache control private vary authorization cdn shared leak"),
    # --- 47 reference ---
    ("Problem Details extension members live in a reserved company namespace like errors.company.com/trace_id; RFC 7807 allows arbitrary keys but the style guide mandates URIs for cross-team uniqueness.", "reference", "technical", False,
     [("Problem Details", "pattern"), ("RFC 7807", "protocol"), ("errors.company.com/trace_id", "pattern")],
     [("Problem Details", "RFC 7807", "IMPLEMENTS")],
     "which namespace rule keeps Problem Details extension members unique across teams and which RFC permits them",
     "problem details extension member uri namespace rfc 7807 style guide"),
    # --- 48 reference ---
    ("Method safety and idempotency are documented per operation in the spec with x-safe and x-idempotent vendor extensions; the generator uses them to decide which SDK methods are auto-retryable.", "reference", "technical", False,
     [("x-safe", "pattern"), ("x-idempotent", "pattern"), ("SDK", "tool")],
     [],
     "which vendor extensions in the spec drive automatic SDK retry logic per operation",
     "x safe x idempotent vendor extension sdk auto retry spec operation"),
    # --- 49 milestone ---
    ("The API style guide hit v2.0 with enforcement baked into Spectral and a pre-merge GitHub Action; naming, pagination, and error shape are now lint-gated rather than reviewer-gated.", "milestone", "technical", False,
     [("API style guide", "concept"), ("Spectral", "tool"), ("GitHub Action", "tool")],
     [("API style guide", "Spectral", "USES")],
     "which style-guide release moved naming and error-shape checks from reviewer gates to lint gates",
     "api style guide v2 spectral github action lint naming pagination error"),
    # --- 50 fact ---
    ("HEAD requests on collection endpoints skip body serialisation and return the same ETag and X-Total-Count headers as GET; monitoring uses HEAD to avoid hammering the read replica every minute.", "fact", "technical", False,
     [("HEAD", "method"), ("X-Total-Count", "pattern"), ("ETag", "pattern"), ("GET", "method")],
     [("HEAD", "GET", "RELATED_TO")],
     "how does monitoring avoid full body serialisation while still checking ETag and total count each minute",
     "head request collection etag x total count get monitor replica skip"),
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
