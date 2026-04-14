"""One-off emitter for shared-base batch-054 — technical domain (edge compute / CDN / serverless runtimes).

Writes 50 rows to data/v2/shared/batch_054.tmp.jsonl with ids shared-02651..02700.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_054.tmp.jsonl"
ID_OFFSET = 2650

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Cloudflare Workers KV backed the read-heavy feature flag store; eventual consistency across pops was acceptable for the 60-second rollout window.", "architecture", "technical", False,
     [("Cloudflare Workers KV", "service")],
     [],
     "which edge key-value store handled the read-heavy flag rollout",
     "edge KV store eventual consistency flag rollout window"),
    # --- 2 ---
    ("Cloudflare D1 replaced Workers KV for the session table; strong consistency on writes matched the login flow better than eventual reads.", "decision", "technical", False,
     [("Cloudflare D1", "database"), ("Workers KV", "service")],
     [("Cloudflare D1", "Workers KV", "REPLACES")],
     "which edge datastore took over session storage from the KV layer",
     "edge SQL session strong consistency login write swap"),
    # --- 3 ---
    ("Cloudflare R2 kept the large asset blobs outside D1; egress-free reads cut the monthly bandwidth bill by two thirds versus S3.", "decision", "technical", False,
     [("Cloudflare R2", "service"), ("D1", "database"), ("S3", "service")],
     [("Cloudflare R2", "S3", "REPLACES")],
     "which object store displaced S3 for the asset blobs and why",
     "edge object blob egress free bandwidth bill reduction"),
    # --- 4 ---
    ("Durable Objects held the per-room chat state; single-instance coordination beat Redis pubsub for ordering guarantees at low user counts.", "architecture", "technical", False,
     [("Durable Objects", "service"), ("Redis", "database")],
     [("Durable Objects", "Redis", "REPLACES")],
     "which Cloudflare primitive coordinated per-room chat state ordering",
     "single instance coordination ordering guarantee chat room"),
    # --- 5 ---
    ("Cloudflare Hyperdrive pooled Postgres connections from Workers; cold latency on the checkout handler dropped from 480 ms to 90 ms.", "milestone", "technical", False,
     [("Cloudflare Hyperdrive", "service"), ("Postgres", "database"), ("Workers", "platform")],
     [],
     "which edge pooling service cut cold Postgres latency on checkout",
     "connection pool cold start origin database latency drop"),
    # --- 6 ---
    ("Smart Placement moved the Workers execution next to the origin database; synchronous queries in the auth path paid less crossing cost.", "architecture", "technical", False,
     [("Smart Placement", "service"), ("Workers", "platform")],
     [],
     "which Cloudflare feature relocated Workers closer to their origin DB",
     "placement origin synchronous auth path crossing cost"),
    # --- 7 ---
    ("Fastly Compute@Edge ran the WASM image resizer; Rust plus the image crate matched VCL feature parity without the ESI string soup.", "decision", "technical", False,
     [("Fastly Compute@Edge", "platform"), ("WASM", "technology"), ("Rust", "language"), ("VCL", "language"), ("ESI", "technology")],
     [("Fastly Compute@Edge", "VCL", "REPLACES")],
     "which edge runtime replaced VCL for the image resizing path",
     "compute edge WebAssembly image resize VCL retire prefer"),
    # --- 8 ---
    ("Legacy VCL stayed on the marketing pages; Compute@Edge was scoped to dynamic APIs because VCL's header rewrites still carried most of the old A/B logic.", "fact", "technical", False,
     [("VCL", "language"), ("Compute@Edge", "platform")],
     [],
     "which pages kept the legacy VCL rules despite the Compute rollout",
     "header rewrite marketing legacy split test page keep"),
    # --- 9 ---
    ("Akamai EdgeWorkers was rejected for the heavy transform; the 512 ms CPU ceiling and 512 KB bundle cap choked the sharp-based resizer.", "decision", "technical", False,
     [("Akamai EdgeWorkers", "platform")],
     [],
     "why did the image resizer not land on the Akamai edge runtime",
     "CPU ceiling bundle cap resizer sharp limit block"),
    # --- 10. noise ---
    ("Give me a sec, I'll flush the edge cache.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Vercel Edge Functions handled the geolocation-aware redirects; the Node-based Serverless Functions stayed on the heavy SSR routes.", "architecture", "technical", False,
     [("Vercel Edge Functions", "platform"), ("Serverless Functions", "platform"), ("Node", "technology")],
     [],
     "which Vercel runtime split took the geo redirects from the SSR routes",
     "edge runtime split geolocation redirect SSR heavy Node"),
    # --- 12 ---
    ("Lambda@Edge was retired for the viewer-request logic; CloudFront Functions ran the header rewrites in microseconds without Node boot cost.", "decision", "technical", False,
     [("Lambda@Edge", "service"), ("CloudFront Functions", "service"), ("Node", "technology")],
     [("CloudFront Functions", "Lambda@Edge", "REPLACES")],
     "which AWS edge runtime took over the viewer-request header tweaks",
     "viewer request header rewrite microsecond boot cost avoid"),
    # --- 13 ---
    ("Netlify Edge Functions on Deno replaced an Express middleware for the auth cookie check; cold start dropped from 900 ms to under 50 ms.", "decision", "technical", False,
     [("Netlify Edge Functions", "platform"), ("Deno", "technology"), ("Express", "framework")],
     [("Netlify Edge Functions", "Express", "REPLACES")],
     "which edge runtime displaced the Express middleware for auth checks",
     "isolate runtime Express middleware cold start auth cookie"),
    # --- 14 ---
    ("Deno Deploy isolates handled the blog's RSS transform; V8 isolate boot under 5 ms let the route stay synchronous under the CDN.", "architecture", "technical", False,
     [("Deno Deploy", "platform"), ("V8", "technology")],
     [],
     "which isolate platform ran the synchronous RSS transform behind the CDN",
     "V8 isolate boot synchronous feed transform blog route"),
    # --- 15 ---
    ("Bun runtime was tested against Cloudflare Workers compatibility; node:crypto shims passed but Bun.serve did not map cleanly to the fetch handler.", "problem", "technical", False,
     [("Bun", "technology"), ("Cloudflare Workers", "platform")],
     [],
     "which Bun API failed to map onto the Workers fetch handler model",
     "runtime compatibility shim server fetch handler mapping"),
    # --- 16 ---
    ("Fermyon Spin shipped the WASM microservices to the self-hosted cluster; spin.toml component routing replaced a Traefik rules file.", "decision", "technical", False,
     [("Fermyon Spin", "platform"), ("WASM", "technology"), ("Traefik", "service")],
     [("Fermyon Spin", "Traefik", "REPLACES")],
     "which WASM platform took over routing from the Traefik rules file",
     "spin component WebAssembly self host route rule swap"),
    # --- 17 ---
    ("Fastly H2O documentation is the reference for the static site's HTTP/2 tuning; server push was disabled because the CDN hit ratio lost more than the push saved.", "reference", "technical", False,
     [("Fastly H2O", "service"), ("HTTP/2", "protocol")],
     [],
     "which documentation guides the static site HTTP/2 tuning decisions",
     "H2 server push documentation reference tuning guide static"),
    # --- 18 ---
    ("CDN cache-key design added the Accept-Language header after the geo-routing change; HIT ratio rose from 62 percent to 89 percent within an hour.", "milestone", "technical", False,
     [("CDN", "infrastructure"), ("Accept-Language", "protocol")],
     [],
     "which cache-key tweak lifted the HIT ratio past the 80-percent bar",
     "cache key header language ratio rise hour rollout"),
    # --- 19 ---
    ("Stale-while-revalidate replaced aggressive TTL bumps on the CDN layer; pages stayed fast during origin brownouts without serving stale errors.", "decision", "technical", False,
     [("Stale-while-revalidate", "pattern"), ("TTL", "config"), ("CDN", "infrastructure")],
     [("Stale-while-revalidate", "TTL", "IMPROVES_ON")],
     "which caching pattern took over from raw TTL extension for brownouts",
     "stale revalidate edge pattern brownout serve fast origin"),
    # --- 20 ---
    ("Soft purge was preferred over hard purge on the Fastly edge for the blog release; users saw stale-while-revalidate content instead of a cold MISS storm.", "preference", "technical", False,
     [("Fastly", "service")],
     [],
     "which purge mode won to avoid the MISS stampede on blog releases",
     "soft hard purge MISS storm stale serve release edge"),
    # --- 21 ---
    ("HIT ratio metrics were pulled from Cloudflare Logpush into Grafana; the per-path dashboard surfaced a bad Vary header in twenty minutes.", "problem", "technical", False,
     [("Cloudflare Logpush", "service"), ("Grafana", "tool"), ("Vary", "protocol")],
     [],
     "which observability path caught the broken Vary header on the CDN",
     "log push dashboard per path header miss cause trace"),
    # --- 22 ---
    ("Pop replication lag spiked on the APAC edge of the Cloudflare CDN during the release; purge propagation was eventually-consistent across 300 pops, not instantaneous.", "problem", "technical", False,
     [("Cloudflare CDN", "infrastructure"), ("APAC", "place")],
     [],
     "which operational surprise bit the APAC edge during the release",
     "replication lag region propagation eventual purge delay"),
    # --- 23 ---
    ("Origin shield on Fastly fronted a single pop for the origin; the origin's connection count fell from 4000 steady to under 300.", "architecture", "technical", False,
     [("Fastly", "service")],
     [],
     "which CDN pattern collapsed the origin connection count at steady state",
     "origin shield fan in connection count collapse steady"),
    # --- 24 ---
    ("Anycast routing on Bunny CDN beat DNS-based steering on GeoDNS for the new region; failover kicked in without a TTL wait.", "decision", "technical", False,
     [("Bunny CDN", "service"), ("GeoDNS", "service")],
     [("Bunny CDN", "GeoDNS", "REPLACES")],
     "which routing model replaced DNS steering on the new CDN region",
     "anycast DNS steer failover TTL wait region swap"),
    # --- 25 ---
    ("Cloudflare Argo Smart Routing trimmed 40 ms off the transatlantic path; the backbone preference weighed TCP retransmit rates, not just hops.", "architecture", "technical", False,
     [("Cloudflare Argo Smart Routing", "service"), ("TCP", "protocol")],
     [],
     "which smart routing layer cut the transatlantic path tail latency",
     "backbone retransmit weight path hop trim latency"),
    # --- 26 ---
    ("Cold-start warmups were scheduled via CloudWatch Events; a keep-alive ping every four minutes held the container provisioned under AWS heuristics.", "architecture", "technical", False,
     [("CloudWatch Events", "service"), ("AWS", "organization")],
     [],
     "which scheduled hack kept Lambda containers provisioned under the heuristic",
     "warmup ping schedule container provision heuristic cold"),
    # --- 27 ---
    ("Lambda SnapStart replaced the CloudWatch Events warmup ping on the Java auth service; cold start dropped from 3.2 s to 180 ms without cron hacks.", "decision", "technical", False,
     [("Lambda SnapStart", "service"), ("CloudWatch Events", "service"), ("Java", "language")],
     [("Lambda SnapStart", "CloudWatch Events", "REPLACES")],
     "which AWS feature retired the scheduled ping for the Java Lambda",
     "snapshot restore cold start JVM warmup ping retire"),
    # --- 28 ---
    ("Azure Functions Premium pre-warmed instances covered the SAP integration endpoint; the Azure Functions consumption plan blew the 5-second SLA on cold starts.", "decision", "technical", False,
     [("Azure Functions Premium", "service"), ("Azure Functions", "service"), ("SAP", "service")],
     [("Azure Functions Premium", "Azure Functions", "REPLACES")],
     "which Azure Functions plan met the SAP integration latency SLA",
     "premium plan pre warm consumption cold start SLA swap"),
    # --- 29 ---
    ("Google Cloud Run min instances were bumped from 0 to 2 on the checkout service; tail latency p99 fell under 300 ms during Monday ramp.", "milestone", "technical", False,
     [("Google Cloud Run", "service")],
     [],
     "which Cloud Run knob pulled the p99 tail latency under 300 ms",
     "minimum instance bump tail latency ramp Monday checkout"),
    # --- 30 ---
    ("Provisioned concurrency on Lambda was rejected on cost for the batch API; traffic was too bursty for the flat-rate hold.", "decision", "technical", False,
     [("Lambda", "service")],
     [],
     "which Lambda knob was rejected because traffic was too bursty to hold",
     "provisioned concurrency flat rate bursty batch cost reject"),
    # --- 31 ---
    ("Knative on GKE ran the event-driven video pipeline; serverless containers scaled from zero without the Cloud Run per-request billing bite.", "architecture", "technical", False,
     [("Knative", "framework"), ("GKE", "service"), ("Cloud Run", "service")],
     [],
     "which serverless container platform replaced Cloud Run for the video pipeline",
     "Knative GKE scale zero per request bill pipeline video"),
    # --- 32 ---
    ("AWS App Runner hosted the internal admin dashboard; rolling deploys plus managed TLS beat the Fargate plus ALB setup on ops effort.", "decision", "technical", False,
     [("AWS App Runner", "service"), ("Fargate", "service"), ("ALB", "service"), ("TLS", "protocol")],
     [("AWS App Runner", "Fargate", "REPLACES")],
     "which AWS container runtime simplified the admin dashboard deploys",
     "managed TLS roll deploy container runtime ops effort"),
    # --- 33 ---
    ("WebSocket support on Vercel Edge Functions was too limited for the live-cursor feature; a dedicated Fly.io region handled the long-lived sockets.", "problem", "technical", False,
     [("Vercel Edge Functions", "platform"), ("Fly.io", "service")],
     [("Fly.io", "Vercel Edge Functions", "REPLACES")],
     "which platform absorbed long-lived WebSocket traffic from the edge",
     "WebSocket limit live cursor long lived region dedicated"),
    # --- 34. noise ---
    ("One sec, resolver's still propagating.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("SSE fan-out at the edge used Durable Objects to multiplex subscribers; per-room broadcast avoided hammering the origin on every message.", "architecture", "technical", False,
     [("Durable Objects", "service"), ("SSE", "protocol")],
     [],
     "which edge primitive multiplexed SSE subscribers per room",
     "server sent events fan out multiplex subscriber room"),
    # --- 36 ---
    ("Cloudflare Realtime Logs replaced the batched Logpush pipeline for incident response; mean time to first log dropped from three minutes to five seconds.", "decision", "technical", False,
     [("Cloudflare Realtime Logs", "service"), ("Logpush", "service")],
     [("Cloudflare Realtime Logs", "Logpush", "REPLACES")],
     "which Cloudflare log feed displaced Logpush for incident response",
     "real time log incident response mean time first drop"),
    # --- 37 ---
    ("OpenTelemetry at the edge was enabled on Workers via the OTel trace API; spans landed in Honeycomb next to the origin service spans.", "architecture", "technical", False,
     [("OpenTelemetry", "framework"), ("Workers", "platform"), ("Honeycomb", "service")],
     [],
     "which tracing backend received the edge spans next to origin spans",
     "OTel edge trace span backend origin join observability"),
    # --- 38 ---
    ("Regional compliance routing split EU traffic onto Frankfurt pops only; GDPR data locality required the payload never touch a US pop, even transiently.", "decision", "technical", False,
     [("Frankfurt", "place"), ("GDPR", "concept"), ("US", "place")],
     [],
     "which routing change kept EU payload strictly on European pops",
     "region route compliance locality EU pop strict payload"),
    # --- 39 ---
    ("Cloudflare Regional Services was preferred over DIY geofencing; signed metadata guarantees the keys never leave the chosen jurisdiction.", "preference", "technical", False,
     [("Cloudflare Regional Services", "service")],
     [],
     "which Cloudflare offering replaced homegrown geofencing for key locality",
     "regional service signed metadata jurisdiction key locality"),
    # --- 40 ---
    ("Cloudflare Pages Functions handled the signup form action; the Workers binding to D1 kept the write path inside a single edge request.", "architecture", "technical", False,
     [("Cloudflare Pages Functions", "service"), ("Workers", "platform"), ("D1", "database")],
     [("Cloudflare Pages Functions", "Workers", "BUILDS_ON")],
     "which Pages feature kept the signup write inside one edge request",
     "form action binding write path single edge request"),
    # --- 41 ---
    ("Wrangler replaced the Serverless Framework on the Workers project; the typed bindings and live tail flow fit the monorepo better.", "decision", "technical", False,
     [("Wrangler", "tool"), ("Serverless Framework", "framework"), ("Workers", "platform")],
     [("Wrangler", "Serverless Framework", "REPLACES")],
     "which CLI took over from the Serverless Framework on the Workers repo",
     "typed binding live tail monorepo CLI fit swap tool"),
    # --- 42 ---
    ("SST on AWS was preferred over raw CDK for the edge-plus-origin stack; the constructs for CloudFront Functions and Lambda@Edge felt consistent.", "preference", "technical", False,
     [("SST", "framework"), ("AWS", "organization"), ("CDK", "framework"), ("CloudFront Functions", "service"), ("Lambda@Edge", "service")],
     [("SST", "CDK", "PREFERS")],
     "which framework beat raw CDK for the mixed edge-plus-origin stack",
     "framework construct edge origin stack consistent swap"),
    # --- 43 ---
    ("Workers AI handled on-edge inference for the spam classifier; the 256 MB model ran under 80 ms without a trip back to the GPU pool.", "architecture", "technical", False,
     [("Workers AI", "service")],
     [],
     "which edge inference runtime kept the spam filter off the central GPU",
     "edge inference classifier small model avoid GPU pool"),
    # --- 44 ---
    ("Cloudflare Queues carried the webhook retries out of the Worker; the 15-second CPU wall was not enough for the backoff windows.", "decision", "technical", False,
     [("Cloudflare Queues", "service"), ("Worker", "platform")],
     [],
     "which queue absorbed webhook retries past the Worker CPU wall",
     "queue retry backoff webhook CPU wall offload Worker"),
    # --- 45 ---
    ("Vercel KV on Upstash Redis stored the rate-limit counters at the edge; the sliding window beat the token bucket on traffic spikes.", "architecture", "technical", False,
     [("Vercel KV", "service"), ("Upstash Redis", "service")],
     [("Vercel KV", "Upstash Redis", "BUILDS_ON")],
     "which edge store held the rate-limit counters for the sliding window",
     "rate limit counter slide window token bucket spike edge"),
    # --- 46 ---
    ("Upstash QStash replaced a self-hosted Sidekiq for the serverless cron jobs; HTTP-native scheduling matched the Workers runtime cleanly.", "decision", "technical", False,
     [("Upstash QStash", "service"), ("Sidekiq", "framework"), ("Workers", "platform")],
     [("Upstash QStash", "Sidekiq", "REPLACES")],
     "which scheduler took over Sidekiq's role on the serverless edge",
     "HTTP native schedule cron runtime match serverless queue"),
    # --- 47 ---
    ("AWS Lambda function URLs replaced API Gateway for the single-endpoint webhook; cost fell without losing the IAM authorizer hook.", "decision", "technical", False,
     [("AWS Lambda", "service"), ("API Gateway", "service"), ("IAM", "service")],
     [("AWS Lambda", "API Gateway", "REPLACES")],
     "which AWS exposure path displaced API Gateway for the single webhook",
     "function URL webhook authorizer cost API gateway drop"),
    # --- 48 ---
    ("Fly Machines scaled to zero on the review apps; the per-region auto-start on first request bought back most of the cost of staging environments.", "architecture", "technical", False,
     [("Fly Machines", "service")],
     [],
     "which Fly primitive let review apps scale to zero by default",
     "scale zero review app region auto start first request"),
    # --- 49 ---
    ("Workerd local dev replaced miniflare on the Workers project; parity with the production runtime caught a subtle fetch cache bug.", "decision", "technical", False,
     [("Workerd", "tool"), ("miniflare", "tool"), ("Workers", "platform")],
     [("Workerd", "miniflare", "REPLACES")],
     "which local dev runtime took over from miniflare and caught the cache bug",
     "local runtime parity production fetch cache bug catch"),
    # --- 50 ---
    ("Edge rate-limiting landed on 2026-03-22 across the Workers fleet; the token-bucket plus Durable Object shard kept 99.5 percent of abuse traffic off origin.", "milestone", "technical", False,
     [("Workers", "platform"), ("Durable Object", "service"), ("2026-03-22", "date")],
     [],
     "when did edge rate limiting ship and how much abuse did it absorb",
     "rate limit ship fleet abuse traffic origin shield date"),
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
