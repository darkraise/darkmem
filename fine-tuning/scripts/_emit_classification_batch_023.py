"""One-off emitter for classification top-up batch-023 — contrastive_decision_architecture mode, API and integration slice.

Writes 100 rows (50 pairs) to data/v2/classification/batch_023.tmp.jsonl with ids class-02201..02300.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_023.tmp.jsonl"
ID_OFFSET = 2200
PAIR_OFFSET = 850

# (decision_text, decision_domain, architecture_text, architecture_domain)
PAIRS: list[tuple[str, str, str, str]] = [
    # 1. REST vs gRPC-Web on mobile
    (
        "Switched the mobile client from REST to gRPC-Web after the battery cost of JSON-over-HTTPS caught up with us during the week-long field trial in Jakarta.",
        "technical",
        "Mobile clients call a gRPC-Web endpoint at /svc with protobuf schemas versioned under the v2/ package and backed by Envoy translating to internal gRPC on port 9000.",
        "technical",
    ),
    # 2. GraphQL federation
    (
        "Chose Apollo Federation v2 over a BFF layer because three product teams kept redefining the same User type in slightly incompatible shapes.",
        "technical",
        "The public GraphQL API is served by an Apollo Router 1.50 gateway composing four subgraphs (users, catalog, billing, orders) published to Apollo Studio with schema checks on every PR.",
        "technical",
    ),
    # 3. API versioning strategy
    (
        "Adopted URL-path versioning (/v1, /v2) over header-based versioning after support tickets kept tracing back to customers who forgot the Accept-Version header.",
        "technical",
        "The public HTTP API mounts versions at /v1 and /v2 path prefixes with FastAPI sub-applications, and an Nginx rule rewrites bare paths to /v1 for legacy clients.",
        "technical",
    ),
    # 4. Cursor pagination
    (
        "Switched list endpoints from offset+limit to opaque cursor pagination after a customer's 400k-row export consistently timed out past page 800.",
        "technical",
        "List endpoints return a base64-encoded cursor that packs (last_id, last_sort_key, tenant_id) and the server decodes it into a keyset query with LIMIT 200 plus a next_cursor field.",
        "technical",
    ),
    # 5. RFC 7807 error model
    (
        "Standardized on RFC 7807 application/problem+json error bodies over the in-house {code,msg} shape after the SDK team could not generate typed error classes reliably.",
        "technical",
        "All public endpoints return errors as application/problem+json documents with type, title, status, detail, instance, and a vendor-prefixed errors[] array generated from a shared Pydantic model.",
        "technical",
    ),
    # 6. API auth — OAuth2 machine-to-machine
    (
        "Adopted OAuth2 client_credentials with JWT assertions over long-lived API keys after a leaked key in a public GitHub repo took 48 hours to rotate across every partner.",
        "technical",
        "Partner integrations authenticate via OAuth2 client_credentials flow backed by a Keycloak realm issuing 10-minute access tokens scoped by audience and signed with per-partner RS256 key pairs.",
        "technical",
    ),
    # 7. Token-bucket rate limiting
    (
        "Chose a Redis-backed token-bucket rate limiter over fixed-window counters after bursty webhook retries kept tripping the 429 threshold for well-behaved clients.",
        "technical",
        "Rate limiting runs as an Envoy filter that calls a Redis Lua script implementing token-bucket with per-route capacity and refill rate, keyed by (tenant_id, api_key_hash).",
        "technical",
    ),
    # 8. Webhook delivery guarantees
    (
        "Moved webhook delivery from inline HTTP calls to a durable outbox plus Svix after a midnight DB failover silently dropped an hour of customer.created notifications.",
        "technical",
        "Webhooks are delivered by Svix reading a Postgres outbox table through CDC, with per-endpoint exponential backoff up to 72 hours, HMAC signatures, and a replay UI for ops.",
        "technical",
    ),
    # 9. Idempotency keys
    (
        "Adopted Stripe-style Idempotency-Key headers on payment and provisioning endpoints after a double-submitted form charged two customers twice on retry.",
        "technical",
        "Mutating endpoints require an Idempotency-Key header whose value is stored with the response body and status in a Redis cache for 24 hours, keyed by (api_key, path, key).",
        "technical",
    ),
    # 10. Schema registry for Kafka
    (
        "Chose Confluent Schema Registry with Protobuf over embedding schemas in each message after a consumer team shipped a producer that broke two downstream services at once.",
        "technical",
        "All Kafka topics carry Protobuf-encoded messages whose schema id is fetched from a Confluent Schema Registry cluster with FULL_TRANSITIVE compatibility and subject naming of <topic>-value.",
        "technical",
    ),
    # 11. API contracts — OpenAPI-first
    (
        "Switched to an OpenAPI-first workflow where the spec is the source of truth after hand-written docs diverged from the server behavior on three consecutive releases.",
        "technical",
        "The public API is defined in a single openapi.yaml stored in a shared repo, with FastAPI routes generated by datamodel-code-generator and client SDKs by openapi-generator on every merge.",
        "technical",
    ),
    # 12. SDK generation
    (
        "Adopted Speakeasy for typed SDK generation over hand-written clients because customer-reported bugs in the Python and Go SDKs kept diverging from each other.",
        "technical",
        "SDKs for Python, TypeScript, Go, and Java are generated from the OpenAPI spec by Speakeasy on every release tag, published to language registries and versioned in lockstep with the server.",
        "technical",
    ),
    # 13. OpenAPI tooling — Stoplight
    (
        "Picked Stoplight Spectral for API linting in CI over ad-hoc reviewers after inconsistent error shapes and missing examples slipped through three pull requests in a week.",
        "technical",
        "CI runs Spectral against openapi.yaml using the company rule set (required examples, consistent error schemas, snake_case fields) and blocks merges on any error-level finding.",
        "technical",
    ),
    # 14. Backward compatibility policy
    (
        "Adopted a strict additive-only evolution policy for v1 after renaming a field in a bugfix release broke a partner integration and triggered a contract penalty.",
        "technical",
        "A custom openapi-diff CI check flags any removed field, renamed field, narrowed type, or new required parameter on v1 routes and routes breaking changes to a v2 spec file instead.",
        "technical",
    ),
    # 15. Payload formats — MessagePack
    (
        "Switched the high-frequency trading sync endpoint from JSON to MessagePack after p95 payload serialization cost dominated the 4 ms budget on commodity hardware.",
        "technical",
        "The /sync endpoint negotiates application/msgpack via Accept headers, serializing order snapshots with msgpack-python using bin_type=True and strict_types=True, falling back to JSON when the header is absent.",
        "technical",
    ),
    # 16. Streaming — Server-Sent Events
    (
        "Chose Server-Sent Events over WebSockets for the LLM token-streaming endpoint because the product only needed one-way server-to-client delivery and wanted trivial HTTP/2 multiplexing.",
        "ai_coding",
        "The /chat/stream endpoint returns text/event-stream with each event carrying a JSON delta, flushed through a FastAPI StreamingResponse behind an Envoy proxy configured for idle_timeout=0 and per_connection_buffer_limit=2MB.",
        "ai_coding",
    ),
    # 17. Batch endpoints
    (
        "Added a POST /v1/batch endpoint mirroring OpenAI's batch semantics after enterprise customers hit per-minute rate limits running 200k classification jobs one at a time.",
        "ai_coding",
        "The batch API accepts a JSONL upload referencing other endpoints by path and body, stores the job in S3, and a background worker fans it out across a celery queue with a 24-hour completion SLO and signed result URLs.",
        "ai_coding",
    ),
    # 18. Async job APIs
    (
        "Adopted an RFC-7240-style async pattern (202 Accepted plus Location header) over blocking requests after long-running exports held HTTP connections for up to 40 minutes and blew out the ALB idle timeout.",
        "technical",
        "Long-running endpoints return 202 Accepted with a Location header pointing to /jobs/{id}, whose state machine (queued, running, succeeded, failed) is persisted in Postgres and polled by clients every 5 seconds until terminal.",
        "technical",
    ),
    # 19. Long-polling for legacy clients
    (
        "Kept long-polling on the legacy Android v4 app after a telemetry pass showed 12% of active users still on devices without reliable WebSocket support behind carrier proxies.",
        "technical",
        "Legacy clients poll /notifications/long-poll with a 25-second server hold implemented by asyncio.wait_for on a Redis Streams XREAD BLOCK call, returning 204 on timeout so the client reissues.",
        "technical",
    ),
    # 20. Webhook fanout via event bus
    (
        "Moved webhook fanout off the request hot path after a spiky partner endpoint held the main thread pool and starved synchronous customer requests.",
        "technical",
        "Domain events publish to an internal NATS JetStream subject, and a dedicated webhook-dispatcher service consumes per-tenant streams and delivers signed HTTPS callbacks with a 30-attempt retry curve.",
        "technical",
    ),
    # 21. Contract testing — Pact
    (
        "Adopted consumer-driven contract testing with Pact after three integration regressions shipped because unit tests on each side passed while the wire format quietly diverged.",
        "technical",
        "Consumer teams publish Pact contracts to a Pact Broker on each build, and provider CI runs pact-verifier against the broker's latest tagged contracts before allowing a merge to main.",
        "technical",
    ),
    # 22. Schema-driven mocks
    (
        "Chose Prism as a mock server over Express-based stubs after frontend and backend teams kept drifting apart on the same endpoint between sprints.",
        "ai_coding",
        "A Prism container runs the openapi.yaml in dynamic mode in the dev docker-compose stack, serving generated examples and validating outgoing requests against the spec before returning 4xx to the client.",
        "ai_coding",
    ),
    # 23. GraphQL persisted queries
    (
        "Adopted Apollo persisted queries over ad-hoc GraphQL documents after a mis-crafted query from the marketing site pulled 40 MB per pageview and tipped the API over.",
        "technical",
        "Public GraphQL traffic only accepts SHA256 query hashes registered at build time through Apollo's persisted-queries manifest, with the router refusing any non-persisted operations on the production plane.",
        "technical",
    ),
    # 24. CORS policy
    (
        "Tightened the CORS policy from Access-Control-Allow-Origin: * to an explicit allowlist after a pentester leveraged a permissive preflight to chain a token-exfiltration attack.",
        "technical",
        "The API gateway applies CORS per route using a Redis-backed allowlist of customer-registered origins, only echoing the matched origin on Access-Control-Allow-Origin and never allowing credentials with wildcards.",
        "technical",
    ),
    # 25. Multipart uploads — resumable
    (
        "Switched file upload endpoints from single POST to tus-protocol resumable uploads after mobile users on flaky 3G reported a 40% failure rate on uploads larger than 20 MB.",
        "technical",
        "Uploads run through a tusd 2.4 server behind Nginx, storing chunks in S3 via the tusd s3 backend with 5 MiB part sizes and a 7-day unfinished-upload TTL before multipart abort.",
        "technical",
    ),
    # 26. Signed URLs for downloads
    (
        "Moved large file downloads off the application tier and onto S3 presigned URLs after bandwidth costs on egress through the app servers became the single largest line item.",
        "technical",
        "The /files/{id}/download endpoint returns a 302 redirect to a 15-minute S3 presigned URL with response-content-disposition set per request, bypassing the app tier for the actual transfer.",
        "technical",
    ),
    # 27. HMAC-signed webhook verification
    (
        "Adopted HMAC-SHA256 request signing with a replay window after a partner's staging URL leaked into a public paste and started receiving forged callbacks.",
        "technical",
        "Outbound webhooks carry X-Signature (HMAC-SHA256 of timestamp.body using the per-endpoint secret) and X-Timestamp headers, which the receiver verifies within a 5-minute skew window and checks against a Redis nonce cache.",
        "technical",
    ),
    # 28. Protobuf schema evolution
    (
        "Enforced buf breaking and buf lint in CI after a field reuse on a deprecated tag number caused a silent payload corruption on a downstream Go consumer.",
        "technical",
        "All .proto files live in a central buf module, with buf breaking --against '.git#branch=main' and buf lint run in GitHub Actions on every PR and buf push to a BSR registry on merge.",
        "technical",
    ),
    # 29. API gateway — Kong to managed
    (
        "Migrated from self-hosted Kong to AWS API Gateway for the public edge after the ops team could no longer justify 3 am pages for plugin segfaults.",
        "technical",
        "Public API routes through AWS API Gateway REST APIs with a Lambda authorizer calling the Keycloak introspection endpoint, WAF rules for top-10 OWASP, and a private integration into an NLB fronting the service mesh.",
        "technical",
    ),
    # 30. GraphQL vs REST for internal
    (
        "Kept internal service-to-service calls on REST plus Protobuf even after adopting GraphQL for the public API because internal consumers have known fields and don't benefit from selection.",
        "technical",
        "Internal services speak REST over HTTP/2 with Protobuf bodies under application/x-protobuf, generated from shared .proto files, leaving GraphQL strictly on the public edge served by Apollo Router.",
        "technical",
    ),
    # 31. AsyncAPI for event docs
    (
        "Adopted AsyncAPI 3.0 as the spec for Kafka and NATS topics after new hires spent their first week manually tracing which service produced which event.",
        "technical",
        "Event documentation is authored in asyncapi.yaml per service, with a CI job publishing a static AsyncAPI Studio site per repo and a company-wide catalog aggregating all specs by subject and server.",
        "technical",
    ),
    # 32. Partner integration — Salesforce
    (
        "Chose a polling-based sync with Salesforce Bulk API 2.0 over Streaming API after three outages traced to missed CometD events during Salesforce maintenance windows.",
        "technical",
        "The Salesforce connector runs a Kubernetes CronJob every 10 minutes that issues a Bulk API 2.0 query with SystemModstamp > last_sync, streams results into S3, and upserts into Postgres with a merge statement keyed on sf_id.",
        "technical",
    ),
    # 33. Email provider integration
    (
        "Adopted a provider-abstraction layer in front of SendGrid and SES after a four-hour SendGrid outage burned the launch email window for a $2M campaign.",
        "technical",
        "Transactional email routes through an internal email-svc that exposes a single HTTP API, holds provider credentials for SendGrid, SES, and Postmark, and fails over on 5xx or DKIM failures using a weighted-round-robin policy.",
        "technical",
    ),
    # 34. Payment provider integration
    (
        "Switched from direct Stripe calls in each service to a central payments-svc after PCI scope audits started covering every repo that imported the Stripe SDK.",
        "technical",
        "All services call an internal payments-svc gRPC API whose handlers wrap Stripe, Adyen, and Braintree SDKs, keeping card tokens inside a single PCI-scoped deployment with VPC-isolated egress to provider endpoints.",
        "technical",
    ),
    # 35. OpenTelemetry on API boundaries
    (
        "Mandated OpenTelemetry propagation across all API boundaries after a cross-service bug investigation stalled because the edge gateway dropped the traceparent header.",
        "technical",
        "Every HTTP ingress and egress point passes through an OpenTelemetry middleware that reads and writes W3C traceparent and tracestate headers and emits spans to the Tempo collector over OTLP/gRPC.",
        "technical",
    ),
    # 36. Clock-skew-tolerant JWTs
    (
        "Added a 60-second leeway on JWT nbf and exp after a burst of spurious 401s traced back to a partner's VM drifting two minutes ahead of NTP.",
        "technical",
        "The API's JWT middleware uses jose.jwt.decode with leeway=60, enforces audience=api.example.com, and emits a structured audit log entry on every leeway-triggered acceptance for later drift monitoring.",
        "technical",
    ),
    # 37. Request compression
    (
        "Enabled Brotli content encoding on response bodies after large JSON payloads on the /search endpoint made up 35% of egress traffic during peak hours.",
        "technical",
        "Envoy sidecars apply the Brotli compressor filter at quality 5 for application/json and text/* responses above 1 KB, with a fallback Gzip compressor for clients that advertise only gzip in Accept-Encoding.",
        "technical",
    ),
    # 38. LLM provider abstraction
    (
        "Put all LLM calls behind an internal llm-gateway after Anthropic SDK upgrades required coordinated rollouts across seven repos last quarter.",
        "ai_coding",
        "The llm-gateway exposes a single /chat/completions endpoint mirroring the OpenAI schema, translates to Anthropic, Google, and local vLLM backends internally, and handles retries, spend caps, and prompt caching per virtual key.",
        "ai_coding",
    ),
    # 39. Contract for MCP integrations
    (
        "Adopted the Model Context Protocol as the contract for IDE-side tools after maintaining three different JSON-RPC dialects across Claude Code, Cursor, and internal VS Code extensions became untenable.",
        "ai_coding",
        "IDE integrations speak JSON-RPC 2.0 over stdio or streamable-HTTP implementing the MCP 2025-06-18 spec, with each tool server registered under a shared .mcp.json manifest and transport selected per environment.",
        "ai_coding",
    ),
    # 40. Feature-flag SDK integration
    (
        "Moved from direct LaunchDarkly client imports in each service to an OpenFeature SDK after swapping providers required rewriting 140 callsites across the monorepo last time.",
        "technical",
        "Services consume flags via the OpenFeature SDK with a flagd provider configured to read from a localhost:8013 sidecar, keeping business code free of provider imports and letting the platform swap providers via Helm values.",
        "technical",
    ),
    # 41. Integration testing — ephemeral env
    (
        "Switched integration tests from a shared staging to per-PR ephemeral environments after two teams stepped on each other's seed data on the same afternoon twice in a month.",
        "technical",
        "Every PR spawns a per-branch Kubernetes namespace via vcluster with its own Postgres and Redis instances, seeded by a fixtures Job, and the integration-tests Argo Workflow targets that namespace and tears it down on merge.",
        "technical",
    ),
    # 42. Contract tests for webhook receivers
    (
        "Adopted recorded VCR-style fixtures for partner webhook handlers after a Shopify schema tweak silently broke order ingestion and only surfaced through a customer complaint 48 hours later.",
        "technical",
        "Webhook handler tests replay cassettes stored under tests/fixtures/webhooks/<provider>/*.yaml through vcrpy, asserting both the parsed domain event and the outbound DB writes, with a nightly job re-recording against provider sandbox accounts.",
        "technical",
    ),
    # 43. BFF for mobile
    (
        "Introduced a mobile BFF after the React Native team kept composing 6-8 REST calls per screen and eating the battery on cold starts.",
        "technical",
        "A dedicated mobile-bff service exposes screen-shaped GraphQL queries to the React Native app and internally fans out to the users, catalog, and orders gRPC services, caching aggregated responses in Redis for 30 seconds.",
        "technical",
    ),
    # 44. Header-based tenancy
    (
        "Standardized on an X-Tenant-ID header propagated through every hop after query-parameter and subdomain-based tenancy both leaked data in separate incidents last year.",
        "technical",
        "The API gateway stamps X-Tenant-ID from the authenticated JWT's tenant claim and Envoy strips any inbound value at the edge, while every downstream service asserts its presence and uses it as a Postgres RLS session variable.",
        "technical",
    ),
    # 45. Partner sandbox environment
    (
        "Built a dedicated partner sandbox API after partners tested against production with seed accounts and a misconfigured script emailed 30k real customers.",
        "technical",
        "The sandbox API runs as a separate deployment at api.sandbox.example.com with its own Postgres, a time-capped data reset job, mocked payment and email providers, and OAuth clients scoped to sandbox:* audiences.",
        "technical",
    ),
    # 46. Event-driven fanout to CRM
    (
        "Moved CRM sync off synchronous API calls to an event-driven fanout after HubSpot's rate limits caused checkout latency to spike during the holiday rush.",
        "technical",
        "Customer lifecycle events publish to an NATS subject crm.events.>, and a hubspot-bridge consumer applies per-endpoint token-bucket rate limits and dead-letters rejected payloads into Postgres for manual replay.",
        "technical",
    ),
    # 47. Contract versioning of webhook payloads
    (
        "Embedded an explicit payload version field in every outbound webhook after partners asked for three months of grace between schema changes.",
        "technical",
        "Every outbound webhook body carries api_version and event_version fields, the delivery service stores per-endpoint subscribed versions, and transformer plugins downgrade the current internal event to a partner's pinned version before dispatch.",
        "technical",
    ),
    # 48. gRPC reflection gated
    (
        "Disabled gRPC server reflection in production after a security review flagged it as schema disclosure for internal methods not in the public proto.",
        "technical",
        "The production gRPC servers compile with -tags=noreflect, while staging and dev builds enable grpc.reflection.v1.ServerReflection behind an mTLS-only listener on :9001 for grpcurl-based debugging.",
        "technical",
    ),
    # 49. Integration test — toxiproxy
    (
        "Added Toxiproxy into the integration suite after a network partition on a partner's side took down the checkout service for eleven minutes, revealing a missing timeout.",
        "technical",
        "Integration tests run partner calls through a Toxiproxy container with named proxies per provider, and pytest fixtures inject latency, timeout, and reset toxics to exercise each outbound client's retry and circuit-breaker policy.",
        "technical",
    ),
    # 50. HTTP client — pooling + retries
    (
        "Standardized all outbound HTTP traffic on a single httpx client wrapper after a service opened 40k short-lived TCP connections per minute and exhausted ephemeral ports.",
        "technical",
        "Services import a shared http_client module built on httpx.AsyncClient with per-host connection pools (max_connections=100, max_keepalive_connections=20), a tenacity-driven retry policy, and OpenTelemetry instrumentation installed at import time.",
        "technical",
    ),
]


def emit() -> int:
    assert len(PAIRS) == 50, f"expected 50 pairs, got {len(PAIRS)}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (dec_text, dec_domain, arch_text, arch_domain) in enumerate(PAIRS, start=1):
            pair_id = f"cls-pair-{PAIR_OFFSET + i:05d}"
            dec_id = f"class-{ID_OFFSET + (2 * i - 1):05d}"
            arch_id = f"class-{ID_OFFSET + (2 * i):05d}"
            f.write(json.dumps({"id": dec_id, "domain": dec_domain, "text": dec_text, "memory_type": "decision", "pair_id": pair_id}, ensure_ascii=False) + "\n")
            f.write(json.dumps({"id": arch_id, "domain": arch_domain, "text": arch_text, "memory_type": "architecture", "pair_id": pair_id}, ensure_ascii=False) + "\n")
            written += 2
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
