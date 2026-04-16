"""One-off emitter for shared-base batch-149 — technical domain (caching layers and CDNs: Redis, Valkey, Memcached, Varnish, CDN edges, HTTP cache semantics, eviction, stampede).

Writes 50 rows to data/v2/shared/batch_149.tmp.jsonl with ids shared-07401..07450.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_149.tmp.jsonl"
ID_OFFSET = 7400

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The session cluster moved from Redis 6 to Valkey 8 after the licence change; the wire protocol stayed compatible so our go-redis clients kept working without a code change.", "decision", "technical", False,
     [("Redis 6", "database"), ("Valkey 8", "database"), ("go-redis", "library")],
     [("Valkey 8", "Redis 6", "REPLACES")],
     "which in-memory store replaced Redis after the licence shift and did our clients have to change",
     "valkey redis licence fork go redis client protocol compatible swap"),
    # --- 2 ---
    ("Dragonfly replaced our three-shard Redis Cluster for the leaderboard tier; the single-process design handled the 1.2M ops/s peak without the gossip overhead the cluster was eating.", "decision", "technical", False,
     [("Dragonfly", "database"), ("Redis Cluster", "database"), ("leaderboard", "service")],
     [("Dragonfly", "Redis Cluster", "REPLACES")],
     "which single-process in-memory store took over the leaderboard from a Redis Cluster and why",
     "dragonfly redis cluster leaderboard shard gossip ops per second"),
    # --- 3 ---
    ("Cache-aside is the default pattern for the product catalog: the service reads Redis, falls back to Postgres on miss, and writes the loaded row back with a 300 second TTL.", "fact", "technical", False,
     [("Cache-aside", "pattern"), ("Redis", "database"), ("Postgres", "database"), ("product catalog", "service")],
     [("product catalog", "Cache-aside", "USES"), ("Cache-aside", "Redis", "USES")],
     "how does the product catalog combine Redis and Postgres to serve reads and populate misses",
     "cache aside redis postgres catalog miss fallback ttl populate"),
    # --- 4 ---
    ("A cache stampede took down checkout on Black Friday: one popular SKU expired and ten thousand workers hit Postgres at once; a per-key singleflight lock plus a jittered TTL fixed it.", "problem", "technical", False,
     [("cache stampede", "concept"), ("checkout", "service"), ("singleflight", "pattern"), ("Postgres", "database")],
     [("singleflight", "cache stampede", "FIXES")],
     "which two mitigations closed the Black Friday checkout stampede on a single expiring SKU",
     "cache stampede singleflight jitter ttl checkout black friday sku"),
    # --- 5 ---
    ("The edge cache uses stale-while-revalidate for 60 seconds on product pages; users see a slightly-old render while the origin fills a fresh copy in the background, and p99 latency halved.", "decision", "technical", False,
     [("stale-while-revalidate", "protocol"), ("edge cache", "infrastructure"), ("product pages", "service")],
     [("edge cache", "stale-while-revalidate", "USES")],
     "which HTTP caching directive halved product-page p99 by serving stale content during revalidation",
     "stale while revalidate edge cache product page p99 latency background"),
    # --- 6 ---
    ("ETag-based conditional GETs shaved 35 percent off bandwidth on the mobile API: the CDN now answers with 304 Not Modified when the weak ETag matches the client's If-None-Match header.", "milestone", "technical", False,
     [("ETag", "protocol"), ("304 Not Modified", "protocol"), ("If-None-Match", "protocol"), ("mobile API", "service")],
     [("mobile API", "ETag", "USES")],
     "which conditional-request mechanism cut mobile API bandwidth and how does the CDN answer a match",
     "etag conditional 304 not modified if none match mobile bandwidth"),
    # --- 7 ---
    ("Last-Modified fallback ships alongside ETag for the image service because some ancient Android WebViews mangle weak ETags; If-Modified-Since still validates correctly on those clients.", "fact", "technical", False,
     [("Last-Modified", "protocol"), ("ETag", "protocol"), ("If-Modified-Since", "protocol"), ("image service", "service")],
     [],
     "why does the image service keep Last-Modified alongside ETag for certain mobile clients",
     "last modified etag if modified since android webview image weak"),
    # --- 8 ---
    ("The Varnish tier in front of the monolith answers 92 percent of anonymous traffic; VCL handles ESI for the header fragment so logged-in personalisation still punches through to the origin.", "fact", "technical", False,
     [("Varnish", "service"), ("VCL", "language"), ("ESI", "protocol"), ("monolith", "service")],
     [("Varnish", "ESI", "USES")],
     "how does Varnish split anonymous cached pages from logged-in personalisation on the monolith",
     "varnish vcl esi monolith anonymous personalisation header fragment"),
    # --- 9 ---
    ("Nginx proxy_cache is configured with a two-tier key: the normalized query string plus the Accept-Encoding header so gzip and br responses land in separate slots and Vary doesn't explode.", "architecture", "technical", False,
     [("Nginx", "service"), ("proxy_cache", "config"), ("Accept-Encoding", "protocol"), ("Vary", "protocol")],
     [("Nginx", "proxy_cache", "CONFIGURES")],
     "how does the Nginx cache key keep gzip and brotli variants separate without a Vary explosion",
     "nginx proxy cache key accept encoding vary gzip brotli slot"),
    # --- 10. noise ---
    ("The office espresso machine is on its third grinder this year and the tamping mat has a permanent ring in the centre.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Cloudflare Workers KV fronts the feature-flag reads with a 60 second cold-start TTL; the write path goes to Durable Objects so a flag flip propagates to every edge within one revalidation cycle.", "decision", "technical", False,
     [("Cloudflare Workers KV", "service"), ("Durable Objects", "service"), ("feature-flag", "service")],
     [("feature-flag", "Cloudflare Workers KV", "USES")],
     "which Cloudflare edge primitives serve feature-flag reads and coordinate flips across the fleet",
     "cloudflare workers kv durable object feature flag edge ttl propagate"),
    # --- 12 ---
    ("Fastly VCL drives the news site: a custom surrogate-key purge invalidates every article tagged with a given author within 150 ms of publishing, which killed the daily full-zone purge.", "decision", "technical", False,
     [("Fastly", "service"), ("VCL", "language"), ("surrogate-key", "pattern"), ("news site", "service")],
     [("Fastly", "surrogate-key", "USES")],
     "how does Fastly invalidate author-scoped articles without issuing a full-zone purge on publish",
     "fastly vcl surrogate key purge news site author publish invalidate"),
    # --- 13 ---
    ("CloudFront sits in front of the static bucket with an origin shield in us-east-1; tail origin RPS dropped from roughly 4k to 120 once the shield coalesced requests from every edge POP.", "milestone", "technical", False,
     [("CloudFront", "service"), ("origin shield", "pattern"), ("us-east-1", "infrastructure"), ("static bucket", "service")],
     [("CloudFront", "origin shield", "USES")],
     "which CloudFront feature coalesced cross-region edge misses and what origin RPS drop did it deliver",
     "cloudfront origin shield us east 1 pop coalesce tail rps static"),
    # --- 14 ---
    ("Akamai still owns the video manifest tier because the prefetch hints on their media delivery product move HLS segment fetches ahead of the player's demand ring.", "fact", "technical", False,
     [("Akamai", "service"), ("HLS", "protocol"), ("prefetch", "pattern"), ("manifest tier", "service")],
     [("manifest tier", "Akamai", "DEPLOYED_ON")],
     "why does the video manifest tier stay on Akamai instead of migrating to another CDN",
     "akamai hls prefetch manifest player demand ring video segment"),
    # --- 15 ---
    ("Redis Cluster's hash-slot routing finally bit us: a hot shard pinned a single celebrity user's timeline key at 98 percent CPU until we sharded the fan-out list with a random suffix tag.", "problem", "technical", False,
     [("Redis Cluster", "database"), ("hash-slot", "algorithm"), ("hot shard", "concept"), ("timeline", "service")],
     [("timeline", "Redis Cluster", "USES")],
     "which hot-key mitigation broke up a celebrity timeline's hash-slot pinning in Redis Cluster",
     "redis cluster hash slot hot shard celebrity timeline suffix tag"),
    # --- 16 ---
    ("ElastiCache for Redis runs with cluster mode enabled across three AZs; the failover target is picked by node group priority so the replica in the primary's AZ always wins the election.", "reference", "technical", False,
     [("ElastiCache", "service"), ("cluster mode", "config"), ("AZ", "infrastructure"), ("replica", "concept")],
     [],
     "how does our ElastiCache topology bias failover elections toward a same-AZ replica",
     "elasticache cluster mode az failover replica priority node group"),
    # --- 17 ---
    ("KeyDB multi-master experiment got shelved: active-active writes under contention produced reconciliation spikes the SRE rotation didn't want to debug; we stuck with Valkey primary/replica.", "decision", "technical", False,
     [("KeyDB", "database"), ("multi-master", "pattern"), ("Valkey", "database"), ("SRE", "person")],
     [("Valkey", "KeyDB", "PREFERS")],
     "which multi-master in-memory store did SRE reject after active-active reconciliation spikes",
     "keydb multi master active active valkey primary replica reconcile"),
    # --- 18 ---
    ("Memcached still runs the session cache for the legacy PHP app: its slab allocator has no fragmentation tail after 400 days of uptime and operations haven't found a reason to migrate.", "fact", "technical", False,
     [("Memcached", "database"), ("slab allocator", "algorithm"), ("PHP", "language"), ("session cache", "service")],
     [("session cache", "Memcached", "USES")],
     "why has the legacy PHP session cache stayed on Memcached instead of migrating to Redis",
     "memcached slab allocator php session fragmentation uptime legacy"),
    # --- 19 ---
    ("LRU eviction on the recommendation cache starved long-tail items during the launch burst; switching the policy to LFU stabilised hit rate at 0.78 because hot items stopped cycling each other out.", "reference", "technical", False,
     [("LRU", "algorithm"), ("LFU", "algorithm"), ("recommendation cache", "service")],
     [("LFU", "LRU", "REPLACES")],
     "which eviction policy change rescued recommendation hit rate from the launch-day burst",
     "lru lfu eviction recommendation cache hit rate launch burst tail"),
    # --- 20 ---
    ("ARC eviction got tested on the catalog cache against LFU; ARC won on shifting-workload days but the extra bookkeeping cost made LFU the safer production pick on constant-traffic slices.", "decision", "technical", False,
     [("ARC", "algorithm"), ("LFU", "algorithm"), ("catalog cache", "service")],
     [("catalog cache", "LFU", "PREFERS")],
     "which eviction algorithm shootout kept LFU on the catalog cache over ARC in production",
     "arc lfu eviction catalog cache bookkeeping workload shift bake off"),
    # --- 21 ---
    ("TTL policy for user profile reads is 10 minutes with a plus-or-minus 90 second jitter applied at write time; without jitter, the morning login wave expired in lockstep and crushed the DB.", "decision", "technical", False,
     [("TTL", "concept"), ("jitter", "pattern"), ("user profile", "service"), ("login wave", "event")],
     [],
     "how does jittered TTL on user profile reads prevent a synchronised expiry wave each morning",
     "ttl jitter user profile login wave lockstep expire write time"),
    # --- 22 ---
    ("Hot-key mitigation for the trending-tweet endpoint splits the counter into 16 shard keys per minute; the aggregator rolls them up on read and origin RPS stays flat during spike events.", "milestone", "technical", False,
     [("Hot-key", "concept"), ("trending-tweet", "service"), ("shard keys", "pattern"), ("aggregator", "service")],
     [],
     "how does the trending endpoint split a hot counter across shard keys without losing accuracy",
     "hot key mitigation trending tweet shard counter aggregator spike"),
    # --- 23 ---
    ("Cache warming runs a pre-scheduled scan five minutes before the 9am ET traffic ramp: the top 10k SKUs are read from Postgres and written to Redis so the first wave lands on a warm tier.", "architecture", "technical", False,
     [("Cache warming", "pattern"), ("Postgres", "database"), ("Redis", "database"), ("9am ET", "date")],
     [("Cache warming", "Redis", "PRODUCES")],
     "which pre-scheduled routine warms the SKU cache ahead of the morning traffic ramp",
     "cache warm prescheduled scan sku postgres redis 9am morning ramp"),
    # --- 24 ---
    ("Negative caching for NXDOMAIN responses is set to 300 seconds on the DNS resolver tier; a typo in a service name used to hit upstream a hundred times a second until the negative TTL landed.", "fact", "technical", False,
     [("Negative caching", "pattern"), ("NXDOMAIN", "protocol"), ("DNS resolver", "service")],
     [("DNS resolver", "Negative caching", "USES")],
     "which caching behaviour spared upstream DNS from repeat NXDOMAIN lookups on a service typo",
     "negative caching nxdomain dns resolver ttl typo upstream repeat"),
    # --- 25 ---
    ("Write-through was chosen over write-back for the order cache because a crash after an acked write must not lose the row; Redis writes synchronously land in Postgres before the 200 returns.", "decision", "technical", False,
     [("Write-through", "pattern"), ("write-back", "pattern"), ("order cache", "service"), ("Redis", "database"), ("Postgres", "database")],
     [("order cache", "Write-through", "USES")],
     "which write pattern did the order cache pick and what durability concern ruled out the alternative",
     "write through write back order cache redis postgres durability ack"),
    # --- 26 ---
    ("Read-through via a thin Redis module wraps the inventory lookup: the module contacts the origin on miss, writes the row, and returns it in a single round trip so the app never sees the miss.", "reference", "technical", False,
     [("Read-through", "pattern"), ("Redis module", "library"), ("inventory lookup", "service")],
     [("inventory lookup", "Read-through", "USES")],
     "which cache-access pattern hides origin misses from the inventory app via a Redis module",
     "read through redis module inventory lookup origin miss round trip"),
    # --- 27 ---
    ("Write-back on the analytics counter flushes to ClickHouse every 5 seconds; losing the last 5 seconds on a Redis crash is acceptable for that pipeline and halves the per-event write pressure.", "decision", "technical", False,
     [("Write-back", "pattern"), ("ClickHouse", "database"), ("Redis", "database"), ("analytics counter", "service")],
     [("analytics counter", "Write-back", "USES")],
     "why does the analytics counter use write-back to ClickHouse despite potential 5 second data loss",
     "write back clickhouse redis analytics counter flush interval pressure"),
    # --- 28 ---
    ("Cache-Control: private, max-age=0, must-revalidate blocks CDN storage for the account page; the origin still controls every render because auth cookies must not leak across tenants.", "reference", "technical", False,
     [("Cache-Control", "protocol"), ("must-revalidate", "protocol"), ("account page", "service"), ("auth cookies", "concept")],
     [("account page", "Cache-Control", "USES")],
     "which Cache-Control combination prevents CDN storage of account pages carrying tenant auth cookies",
     "cache control private max age zero must revalidate account tenant"),
    # --- 29 ---
    ("Browser cache hints for hashed asset bundles use immutable with a one-year max-age; versioned filenames carry the content hash so purges are implicit on the next deploy.", "fact", "technical", False,
     [("Browser cache", "concept"), ("immutable", "protocol"), ("max-age", "protocol"), ("asset bundles", "service")],
     [("asset bundles", "immutable", "USES")],
     "which cache directive pair makes hashed asset bundles cacheable forever without manual purging",
     "browser cache immutable max age hashed bundle versioned filename"),
    # --- 30 ---
    ("Surrogate-Control lets Fastly hold content for an hour while Cache-Control tells browsers just 60 seconds; the split keeps the edge warm without turning client clocks into a staleness ceiling.", "reference", "technical", False,
     [("Surrogate-Control", "protocol"), ("Fastly", "service"), ("Cache-Control", "protocol")],
     [],
     "how do Surrogate-Control and Cache-Control split edge and browser TTLs for the same response",
     "surrogate control fastly cache control edge browser ttl split"),
    # --- 31 ---
    ("The Redis Sentinel setup is being retired; Valkey with the sentinel-compatible HA path covers the same failover topology and we don't want to run two flavours of the same tooling anymore.", "decision", "technical", False,
     [("Redis Sentinel", "service"), ("Valkey", "database"), ("HA", "concept")],
     [("Valkey", "Redis Sentinel", "REPLACES")],
     "which HA path replaced Redis Sentinel in our ops footprint and what drove the consolidation",
     "redis sentinel valkey ha failover tooling consolidate retire"),
    # --- 32 ---
    ("TinyLFU admission on the Caffeine cache inside the JVM service raised hit rate from 0.71 to 0.83; the old W-LRU variant was admitting one-shot scanners into the main segment too eagerly.", "milestone", "technical", False,
     [("TinyLFU", "algorithm"), ("Caffeine", "library"), ("W-LRU", "algorithm"), ("JVM", "platform")],
     [("TinyLFU", "W-LRU", "IMPROVES_ON")],
     "which Caffeine admission policy bumped hit rate and what pathological behaviour did it retire",
     "tinylfu caffeine w lru admission jvm hit rate scanner segment"),
    # --- 33 ---
    ("Dogpile prevention on the pricing endpoint uses a probabilistic early expiration: keys refresh ahead of TTL with a probability rising as expiry approaches, so the renewal herd never all lands.", "milestone", "technical", False,
     [("Dogpile", "concept"), ("probabilistic early expiration", "algorithm"), ("pricing endpoint", "service")],
     [("pricing endpoint", "probabilistic early expiration", "USES")],
     "which probabilistic refresh trick keeps the pricing endpoint from forming a renewal dogpile",
     "dogpile probabilistic early expiration pricing ttl refresh herd"),
    # --- 34 ---
    ("Request coalescing inside the Go service wraps Redis GETs with singleflight.Group; a thousand concurrent misses on the same key collapse into one origin fetch and a shared broadcast.", "architecture", "technical", False,
     [("singleflight.Group", "library"), ("Go", "language"), ("Redis", "database"), ("Request coalescing", "pattern")],
     [("Go", "singleflight.Group", "USES")],
     "which Go primitive coalesces concurrent Redis misses into one origin fetch and a broadcast",
     "singleflight group go redis coalesce miss origin fetch broadcast"),
    # --- 35 ---
    ("The CDN purge API moved from URL-based to tag-based after a release mispurged 40k unrelated URLs; tagging assets at push time scopes invalidation to the changed bundle only.", "problem", "technical", False,
     [("CDN purge", "api"), ("tag-based", "pattern"), ("URL-based", "pattern")],
     [("tag-based", "URL-based", "REPLACES")],
     "which purge-API redesign prevented a repeat of the 40k mispurged URLs incident",
     "cdn purge tag url based mispurge release scope invalidation bundle"),
    # --- 36 ---
    ("Cookie-stripping at the edge lets the CDN serve anonymous copies of pages to logged-out traffic; the tracking cookie is forwarded only for POST and a small allowlist of dynamic paths.", "architecture", "technical", False,
     [("Cookie-stripping", "pattern"), ("edge", "infrastructure"), ("tracking cookie", "concept")],
     [],
     "which edge trick lets the CDN cache pages for logged-out traffic despite a tracking cookie",
     "cookie stripping edge anonymous tracking post allowlist dynamic"),
    # --- 37 ---
    ("Vary: Accept-Language on the marketing site exploded the cache cardinality to half a million variants per URL; we normalised to a two-letter primary language in the edge before keying.", "preference", "technical", False,
     [("Vary", "protocol"), ("Accept-Language", "protocol"), ("marketing site", "service")],
     [],
     "which Vary-header normalisation shrank a half-million-variant cache explosion on the marketing site",
     "vary accept language marketing cache cardinality normalise two letter"),
    # --- 38 ---
    ("Redis persistence is RDB snapshots every 15 minutes plus AOF with everysec fsync; recovery testing shows p99 restart under 40 seconds on the 12 GB working set without losing confirmed writes.", "architecture", "technical", False,
     [("Redis", "database"), ("RDB", "config"), ("AOF", "config"), ("fsync", "config")],
     [("Redis", "RDB", "CONFIGURES"), ("Redis", "AOF", "CONFIGURES")],
     "which Redis persistence combination keeps restart under 40 seconds on a 12 GB working set",
     "redis rdb aof everysec fsync persistence restart 12 gb recovery"),
    # --- 39 ---
    ("Valkey is pinned to 64 GB maxmemory with allkeys-lfu as the eviction policy; the SRE runbook forbids noeviction because an OOM on that host cascades into checkout timeouts within 20 seconds.", "decision", "technical", False,
     [("Valkey", "database"), ("maxmemory", "config"), ("allkeys-lfu", "config"), ("noeviction", "config")],
     [("Valkey", "allkeys-lfu", "CONFIGURES")],
     "which Valkey eviction policy is mandatory and why is noeviction banned in the runbook",
     "valkey maxmemory allkeys lfu noeviction sre oom checkout cascade"),
    # --- 40 ---
    ("Pipelining reduced round trips on the bulk write path: batches of 200 SET commands per TCP exchange cut checkout-finalise latency from 140 ms to 35 ms against the Valkey primary.", "milestone", "technical", False,
     [("Pipelining", "pattern"), ("SET", "command"), ("TCP", "protocol"), ("Valkey", "database")],
     [("Pipelining", "Valkey", "APPLIES_TO")],
     "which Valkey client technique cut checkout-finalise latency from 140 ms to 35 ms",
     "pipeline set command tcp valkey checkout finalise latency batch"),
    # --- 41 ---
    ("Client-side caching in Redis 7 uses the RESP3 tracking mode; the Python service keeps a small local LRU and gets an invalidation push on key changes without polling.", "architecture", "technical", False,
     [("Redis 7", "database"), ("RESP3", "protocol"), ("tracking mode", "pattern"), ("Python", "language"), ("LRU", "algorithm")],
     [("Redis 7", "RESP3", "USES")],
     "which Redis 7 protocol feature lets the Python service keep a local LRU with server-side invalidation",
     "redis 7 resp3 tracking client side cache python lru invalidation"),
    # --- 42 ---
    ("Geo-distributed caches are partitioned by regional prefix; eu-west keys live only on the Frankfurt node and us-east only on the Virginia node, so compliance review stopped flagging replication.", "milestone", "technical", False,
     [("eu-west", "infrastructure"), ("us-east", "infrastructure"), ("Frankfurt", "place"), ("Virginia", "place")],
     [],
     "how does regional key partitioning keep cached data from crossing jurisdictions for compliance",
     "geo partition eu west us east frankfurt virginia compliance region"),
    # --- 43. noise ---
    ("The front desk plant got a little hat for the holidays and nobody has admitted to putting it there yet.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Circuit breaker on the Redis client opens after three consecutive timeouts and stays open for 20 seconds; requests skip the cache and read straight from Postgres so a cache outage can't bring the site down.", "architecture", "technical", False,
     [("Circuit breaker", "pattern"), ("Redis", "database"), ("Postgres", "database")],
     [("Circuit breaker", "Redis", "APPLIES_TO")],
     "how does the circuit breaker pattern make the site survive a Redis outage without 5xx cascades",
     "circuit breaker redis timeout postgres fallback outage survive"),
    # --- 45 ---
    ("The Envoy front proxy layers an L1 local cache above the CDN; a 50 MB in-memory slab catches hotshot requests within a pod so a traffic spike doesn't even leave the node.", "architecture", "technical", False,
     [("Envoy", "service"), ("L1 local cache", "pattern"), ("CDN", "infrastructure"), ("pod", "infrastructure")],
     [("Envoy", "L1 local cache", "USES")],
     "which in-pod caching layer does Envoy add above the CDN and what traffic shape does it catch",
     "envoy l1 local cache cdn pod slab hotshot spike node"),
    # --- 46 ---
    ("Bloom filter in front of the Redis GET path short-circuits obvious negatives on the email-exists check; false positives hit Redis anyway and the 1 percent rate beats an extra round trip for every miss.", "architecture", "technical", False,
     [("Bloom filter", "algorithm"), ("Redis", "database"), ("email-exists", "service")],
     [("email-exists", "Bloom filter", "USES")],
     "which probabilistic structure short-circuits negative lookups on the email-exists path and why tolerate its false positives",
     "bloom filter redis email exists negative false positive short circuit"),
    # --- 47 ---
    ("Preferred config for the chat service is Valkey over Dragonfly because the Pub/Sub fanout semantics match the existing client code; Dragonfly's BullMQ compatibility wasn't enough on its own.", "preference", "technical", False,
     [("Valkey", "database"), ("Dragonfly", "database"), ("Pub/Sub", "protocol"), ("BullMQ", "library"), ("chat service", "service")],
     [("chat service", "Valkey", "PREFERS")],
     "which in-memory store does the chat service prefer and what semantic mismatch kept Dragonfly off",
     "valkey dragonfly pub sub bullmq chat service fanout semantic"),
    # --- 48 ---
    ("Team prefers soft TTL plus hard TTL for any cached third-party API response; soft expiry triggers a background refresh, hard expiry forces a synchronous fetch if the refresh hasn't landed.", "preference", "technical", False,
     [("soft TTL", "pattern"), ("hard TTL", "pattern"), ("third-party API", "service")],
     [],
     "which dual-TTL pattern is preferred for third-party API responses and what behaviour does each trigger",
     "soft ttl hard ttl third party api refresh background sync fetch"),
    # --- 49 ---
    ("Team prefers explicit per-route Cache-Control headers at the app layer over CDN-page-rules overrides; the route source is the one place engineers look first and config drift stops happening.", "preference", "technical", False,
     [("Cache-Control", "protocol"), ("CDN", "infrastructure"), ("page-rules", "config")],
     [("Cache-Control", "page-rules", "PREFERS")],
     "why does the team set Cache-Control at the app layer rather than configuring CDN page-rules",
     "cache control app layer cdn page rules drift per route"),
    # --- 50 ---
    ("We reference RFC 9111 as the source of truth on HTTP caching semantics; RFC 7234 is obsolete and internal docs that still cite it get flagged during review so the team converges on one spec.", "reference", "technical", False,
     [("RFC 9111", "publication"), ("RFC 7234", "publication"), ("HTTP caching", "concept")],
     [("RFC 9111", "RFC 7234", "REPLACES")],
     "which HTTP caching RFC is the current source of truth and which obsolete one gets flagged in review",
     "rfc 9111 7234 http caching semantic source truth obsolete review"),
    # --- 51 placeholder not used; total entries = 50 ---
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
