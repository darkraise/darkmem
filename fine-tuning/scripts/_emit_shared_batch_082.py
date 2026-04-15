"""One-off emitter for shared-base batch-082 — technical domain (caching layers).

Writes 50 rows to data/v2/shared/batch_082.tmp.jsonl with ids shared-04051..04100.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_082.tmp.jsonl"
ID_OFFSET = 4050

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Valkey replaced Redis on the session cache after the licensing pivot; the BSD-fork stayed wire-compatible so the Jedis client never noticed the swap.", "decision", "technical", False,
     [("Valkey", "database"), ("Redis", "database"), ("Jedis", "library")],
     [("Valkey", "Redis", "REPLACES")],
     "which Redis fork took over the session cache after the license change",
     "Valkey Redis fork wire compatible session cache client swap"),
    # --- 2 ---
    ("Dragonfly improved on Redis throughput by 15x on the leaderboard workload; the multi-threaded shared-nothing design saturated the 32-core box where Redis used one core.", "milestone", "technical", False,
     [("Dragonfly", "database"), ("Redis", "database")],
     [("Dragonfly", "Redis", "IMPROVES_ON")],
     "which Redis-protocol cache pulled 15x throughput on the leaderboard box",
     "Dragonfly multi thread shared nothing throughput leaderboard"),
    # --- 3 ---
    ("KeyDB ran the geo-replicated chat presence cache; multi-master replication beat Redis Sentinel's single-writer model for the cross-region writes.", "decision", "technical", False,
     [("KeyDB", "database"), ("Redis Sentinel", "service")],
     [("KeyDB", "Redis Sentinel", "REPLACES")],
     "which Redis-compatible cache replaced Sentinel for cross-region presence",
     "KeyDB multi master replication geo presence Sentinel swap"),
    # --- 4 ---
    ("Caffeine replaced the Guava cache on the JVM service; the Window TinyLFU policy lifted hit ratio from 71 percent to 94 percent on the hot-key workload.", "decision", "technical", False,
     [("Caffeine", "library"), ("Guava", "library"), ("JVM", "platform"), ("Window TinyLFU", "algorithm")],
     [("Caffeine", "Guava", "REPLACES")],
     "which JVM cache library displaced Guava and lifted hit ratio past 90 percent",
     "Caffeine Guava Window TinyLFU JVM hit ratio hot key swap"),
    # --- 5 ---
    ("Memcached fronted the rendered HTML fragments behind nginx; the slab allocator avoided the fragmentation that bit the prior Redis-based cache after a week of churn.", "architecture", "technical", False,
     [("Memcached", "database"), ("nginx", "service"), ("Redis", "database")],
     [("Memcached", "Redis", "REPLACES")],
     "which fragment cache beat Redis on memory fragmentation under churn",
     "Memcached slab allocator fragment HTML nginx churn week"),
    # --- 6 ---
    ("Hazelcast IMap held the distributed session state on the JVM cluster; near-cache on each node cut the network round trip for read-heavy lookups.", "architecture", "technical", False,
     [("Hazelcast", "database"), ("IMap", "api"), ("JVM", "platform")],
     [],
     "which JVM grid cached session state with a near-cache on every node",
     "Hazelcast IMap near cache distributed session JVM cluster"),
    # --- 7 ---
    ("Write-through caching kept the user-profile Redis layer consistent with Postgres; every write hit both stores in the same request, trading p99 latency for read freshness.", "decision", "technical", False,
     [("Redis", "database"), ("Postgres", "database")],
     [],
     "which write strategy traded p99 latency for cache freshness on profiles",
     "write through Redis Postgres profile dual write freshness"),
    # --- 8 ---
    ("Write-back was rejected on the order-status cache; the eventual flush window lost three minutes of writes when the Redis primary OOMed during Black Friday.", "problem", "technical", False,
     [("Redis", "database")],
     [],
     "which write policy lost data when Redis OOMed during the holiday peak",
     "write back lose write OOM holiday peak order status reject"),
    # --- 9 ---
    ("Write-around landed on the bulk-import path into Redis; cold writes bypassed the cache entirely so a 50-million-row reload did not evict the hot working set.", "decision", "technical", False,
     [("Write-around", "pattern"), ("Redis", "database")],
     [],
     "which write policy kept the bulk import from evicting the hot keys",
     "write around bulk import cold write evict hot working set"),
    # --- 10. noise ---
    ("Hold on, my Redis is restarting.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Cache stampede on the homepage was fixed with a singleflight wrapper around the origin call; one goroutine populated the key while the rest waited on the same future.", "problem", "technical", False,
     [("singleflight", "pattern")],
     [],
     "which pattern collapsed concurrent origin calls during a cache stampede",
     "stampede singleflight goroutine future origin populate wait"),
    # --- 12 ---
    ("Randomized TTL jitter of plus-or-minus 10 percent on Memcached broke the synchronized expiry storm on the product catalog cache; without jitter, ten thousand keys expired in the same second.", "decision", "technical", False,
     [("TTL", "config"), ("Memcached", "database")],
     [],
     "which TTL trick broke the synchronized expiry storm on the catalog cache",
     "TTL jitter randomize expiry storm synchronize catalog avoid"),
    # --- 13 ---
    ("Probabilistic early expiration via the XFetch algorithm refreshed hot keys before TTL; the cache never went cold for the top 1 percent of products under load.", "architecture", "technical", False,
     [("XFetch", "algorithm")],
     [],
     "which algorithm refreshed hot keys before TTL on the product cache",
     "probabilistic early expire XFetch hot key refresh top product"),
    # --- 14 ---
    ("Request coalescing in the CDN-origin shield was paired with singleflight at the application cache; together they collapsed a thundering herd of 4000 concurrent requests into one origin call.", "architecture", "technical", False,
     [("singleflight", "pattern")],
     [],
     "which two layers cooperated to collapse the 4000-request thundering herd",
     "request coalesce shield singleflight thundering herd origin"),
    # --- 15 ---
    ("Cache invalidation moved from TTL-only to write-time bust on the user-permissions Redis namespace; stale role decisions had been holding for up to ten minutes after a revoke.", "decision", "technical", False,
     [("Redis", "database")],
     [],
     "which invalidation strategy replaced TTL-only on the permissions cache",
     "invalidation TTL only write time bust permission revoke stale"),
    # --- 16 ---
    ("Tag-based invalidation on Varnish let the editorial team purge all article-N pages in one PURGE call; per-URL purges had needed a 200-row sweep per article.", "architecture", "technical", False,
     [("Varnish", "service")],
     [],
     "which Varnish feature collapsed per-URL purges into one tag-based call",
     "Varnish tag invalidate purge editorial article URL sweep"),
    # --- 17 ---
    ("Varnish was preferred over nginx for the dynamic HTML cache; VCL's request mutation language gave the editorial team a finer surrogate-key vocabulary than nginx proxy_cache directives.", "preference", "technical", False,
     [("Varnish", "service"), ("nginx", "service"), ("VCL", "language")],
     [("Varnish", "nginx", "PREFERS")],
     "which edge cache beat nginx on the surrogate-key vocabulary for editorial",
     "Varnish nginx VCL surrogate key edge dynamic HTML prefer"),
    # --- 18 ---
    ("nginx proxy_cache stayed on the static asset tier; the simple key-based store outperformed Varnish on the cold-cache fill at the same memory budget.", "decision", "technical", False,
     [("nginx", "service"), ("Varnish", "service")],
     [],
     "which static-tier cache beat Varnish on cold fill at the same memory",
     "nginx proxy cache static tier cold fill memory budget"),
    # --- 19 ---
    ("Multi-tier caching layered Caffeine in-process, Redis cluster as L2, and Postgres as origin; the L1 hit ratio of 92 percent kept Redis QPS under a tenth of what direct hits would have asked.", "architecture", "technical", False,
     [("Caffeine", "library"), ("Redis", "database"), ("Postgres", "database")],
     [],
     "which three-tier cache stack kept Redis QPS to a tenth of direct load",
     "multi tier L1 L2 Caffeine Redis Postgres hit ratio offload"),
    # --- 20 ---
    ("Near-cache on Hazelcast clients was tuned with invalidation events over the cluster bus; without invalidation, near-cache stale reads bit the inventory check after every replenishment.", "problem", "technical", False,
     [("Hazelcast", "database")],
     [],
     "which Hazelcast feature stopped the near-cache from serving stale inventory",
     "near cache invalidation event bus stale inventory replenish"),
    # --- 21 ---
    ("Coherence near-cache pattern was lifted into the Caffeine plus Redis design via Redis keyspace notifications; the application library subscribed and evicted local entries on remote writes.", "architecture", "technical", False,
     [("Caffeine", "library"), ("Redis", "database")],
     [("Caffeine", "Redis", "BUILDS_ON")],
     "which Redis feature carried near-cache invalidation into the Caffeine layer",
     "Coherence near cache Caffeine Redis keyspace notify evict"),
    # --- 22 ---
    ("ETag plus If-None-Match cut the API egress by 38 percent on the mobile clients; 304 Not Modified responses replaced full JSON bodies for unchanged feeds.", "milestone", "technical", False,
     [("ETag", "protocol"), ("If-None-Match", "protocol")],
     [],
     "which HTTP cache pair cut mobile API egress by 38 percent",
     "ETag If None Match 304 mobile feed egress reduction header"),
    # --- 23 ---
    ("Cache-Control max-age and stale-while-revalidate were set on the static JS bundles; browsers served from disk cache while the revalidation happened in the background.", "decision", "technical", False,
     [("Cache-Control", "protocol")],
     [],
     "which Cache-Control directives let the browser serve JS from disk first",
     "Cache Control max age stale revalidate browser disk JS"),
    # --- 24 ---
    ("Browser cache headers were normalized via a middleware on Express; a stray Set-Cookie on the static path had been forcing every asset response to private and skipping the shared CDN cache.", "problem", "technical", False,
     [("Express", "framework"), ("Set-Cookie", "protocol"), ("CDN", "infrastructure")],
     [],
     "which header leak forced every static asset onto a private cache path",
     "Set Cookie static asset private CDN cache leak Express"),
    # --- 25 ---
    ("Vary: Accept-Encoding was added to the cache key on Varnish; brotli-supporting clients had been getting gzip-only responses cached against them.", "problem", "technical", False,
     [("Varnish", "service"), ("Vary", "protocol")],
     [],
     "which Vary header fixed the brotli-versus-gzip cache cross-pollution",
     "Vary Accept Encoding brotli gzip cache key fix client mismatch"),
    # --- 26 ---
    ("Negative caching of 404s for 60 seconds shielded the origin during a botnet probe; the cache absorbed 2 million 404 lookups that would have hit the Rails router otherwise.", "decision", "technical", False,
     [("Rails", "framework")],
     [],
     "which caching trick shielded the Rails router from a 404-probe botnet",
     "negative cache 404 botnet probe origin shield Rails router"),
    # --- 27 ---
    ("Bloom filter in front of the Redis cache stopped the cold-key lookups from reaching origin; the false-positive rate of 1 percent let the catalog page survive a directory-listing crawler.", "architecture", "technical", False,
     [("Redis", "database"), ("Bloom filter", "algorithm")],
     [],
     "which probabilistic structure shielded origin from cold-key Redis misses",
     "Bloom filter cold key Redis miss origin shield crawler probe"),
    # --- 28 ---
    ("Redis Cluster sharding by hash tag kept user-scoped keys on the same shard; multi-key MGET and Lua scripts that crossed users had failed under the slot-mismatch error.", "decision", "technical", False,
     [("Redis Cluster", "database"), ("Lua", "language")],
     [],
     "which Redis Cluster sharding trick kept user keys on a single shard",
     "Redis Cluster hash tag shard MGET Lua slot mismatch user"),
    # --- 29 ---
    ("Memcached binary protocol replaced ASCII on the photo service; multi-get pipelining cut the per-request cost from 8 round trips to 1 and dropped p99 by 40 ms.", "milestone", "technical", False,
     [("Memcached", "database")],
     [("Memcached", "Memcached", "IMPROVES_ON")],
     "which Memcached protocol switch collapsed the photo service round trips",
     "Memcached binary protocol multi get pipeline round trip p99"),
    # --- 30 ---
    ("Twemproxy was rejected for the Redis fan-out; client-side sharding via lettuce already handled topology refresh and added one less hop on the hot path.", "decision", "technical", False,
     [("Twemproxy", "tool"), ("lettuce", "library"), ("Redis", "database")],
     [],
     "which Redis proxy lost to client-side sharding on the hot path",
     "Twemproxy lettuce client shard topology refresh hop reject"),
    # --- 31 ---
    ("Caffeine's refreshAfterWrite was preferred over expireAfterWrite on the auth-token cache; users near the boundary got a synchronous hit and an async refresh instead of a cache miss.", "preference", "technical", False,
     [("Caffeine", "library")],
     [],
     "which Caffeine eviction policy avoided the boundary cache miss for auth",
     "refresh after write expire after write Caffeine async auth boundary"),
    # --- 32 ---
    ("LRU was replaced with W-TinyLFU on the document cache; the admission filter kept long-tail one-shot reads from polluting the hot working set.", "decision", "technical", False,
     [("LRU", "algorithm"), ("W-TinyLFU", "algorithm")],
     [("W-TinyLFU", "LRU", "REPLACES")],
     "which eviction algorithm displaced LRU on the document cache",
     "LRU W TinyLFU admission filter long tail one shot evict"),
    # --- 33 ---
    ("Redis maxmemory-policy was set to allkeys-lfu on the recommendation cache; volatile-lru had been evicting unscored keys before the rarely-touched but expensive ones.", "decision", "technical", False,
     [("Redis", "database")],
     [],
     "which Redis eviction policy beat volatile-lru on the recommendation cache",
     "Redis maxmemory allkeys lfu volatile lru evict recommendation"),
    # --- 34. noise ---
    ("Two seconds, the cache is warming.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Refresh-ahead on the Caffeine price cache fired at 80 percent of TTL; the background recompute kept the user-facing read at 0.4 ms with no cold-miss tail.", "architecture", "technical", False,
     [("Refresh-ahead", "pattern"), ("Caffeine", "library")],
     [],
     "which TTL fraction triggered the price-cache background refresh",
     "refresh ahead 80 percent TTL background recompute cold miss"),
    # --- 36 ---
    ("Read-through caching put the data loader inline with the cache library on the Caffeine layer; callers no longer had to remember the load-then-put dance and double-fetches went away.", "architecture", "technical", False,
     [("Caffeine", "library")],
     [],
     "which caching pattern eliminated the load-then-put dance on Caffeine",
     "read through cache loader inline double fetch Caffeine call"),
    # --- 37 ---
    ("Redis Streams plus consumer groups carried cache-invalidation events to the in-process L1 caches; the at-least-once delivery suited evict semantics fine since duplicate evictions are idempotent.", "architecture", "technical", False,
     [("Redis Streams", "database")],
     [],
     "which Redis primitive fanned cache-evict events to in-process L1 caches",
     "Redis Streams consumer group invalidation event L1 idempotent"),
    # --- 38 ---
    ("Hazelcast was replaced by Redis plus Caffeine on the JVM service; the operational cost of a separate JVM grid did not pay back versus a managed Redis with library-level near-cache.", "decision", "technical", False,
     [("Hazelcast", "database"), ("Redis", "database"), ("Caffeine", "library"), ("JVM", "platform")],
     [("Redis", "Hazelcast", "REPLACES")],
     "which combo retired the Hazelcast grid on the JVM service",
     "Hazelcast Redis Caffeine JVM grid managed near cache swap"),
    # --- 39 ---
    ("Apache Ignite was evaluated against Hazelcast for the compute-grid plus cache split; Ignite's SQL surface was richer but the Hazelcast operational story matched the team's runbooks.", "decision", "technical", False,
     [("Apache Ignite", "database"), ("Hazelcast", "database")],
     [],
     "which JVM grid won the compute-plus-cache evaluation against Ignite",
     "Apache Ignite Hazelcast compute grid SQL surface runbook eval"),
    # --- 40 ---
    ("Ehcache 3 with the off-heap tier hosted the warm document cache; the off-heap region kept GC pause out of the cache hot path under a 40 GB working set.", "architecture", "technical", False,
     [("Ehcache", "library")],
     [],
     "which JVM cache held a 40 GB working set off-heap to dodge GC pauses",
     "Ehcache off heap tier warm document GC pause working set"),
    # --- 41 ---
    ("Redis 7 functions replaced a sprawl of Lua scripts on the rate-limit path; the named function library was easier to version and load than EVAL plus SHA cache.", "decision", "technical", False,
     [("Redis", "database"), ("Lua", "language")],
     [("Redis", "Lua", "REPLACES")],
     "which Redis 7 feature retired the Lua EVAL plus SHA cache pattern",
     "Redis functions Lua script EVAL SHA library version load"),
    # --- 42 ---
    ("Negative TTLs on Memcached used the add-with-expiration semantic to dampen origin retries; a 1-second negative cache held off the retry storm without poisoning the next legitimate fetch.", "architecture", "technical", False,
     [("Memcached", "database")],
     [],
     "which Memcached pattern dampened origin retries without poisoning fetches",
     "negative TTL Memcached add expire retry storm origin damp"),
    # --- 43 ---
    ("Two-step cache lookup in Caffeine plus a remote Redis was wrapped in an AsyncLoadingCache; the loader pushed misses to Redis first then to Postgres, keeping the call site to a single get.", "architecture", "technical", False,
     [("Caffeine", "library"), ("Redis", "database"), ("Postgres", "database")],
     [],
     "which Caffeine API hid the Redis-then-Postgres miss path behind one get",
     "AsyncLoadingCache Caffeine Redis Postgres miss path single get"),
    # --- 44 ---
    ("Redis ACLs scoped each microservice to its own key prefix; an over-broad FLUSHALL in a debugging session had wiped a sibling service's cache the previous quarter.", "decision", "technical", False,
     [("Redis", "database")],
     [],
     "which Redis feature stopped a debugging FLUSHALL from blasting siblings",
     "Redis ACL key prefix microservice FLUSHALL debug sibling wipe"),
    # --- 45 ---
    ("Cache key versioning via a key prefix bump on Redis replaced explicit invalidation on the search results cache; the old version aged out under TTL while readers immediately swung to the new shape.", "decision", "technical", False,
     [("Redis", "database"), ("TTL", "config")],
     [],
     "which versioning trick replaced explicit invalidation on the search cache",
     "key prefix version bump invalidation TTL age out search results"),
    # --- 46 ---
    ("Surrogate-Control headers from the origin steered Fastly's edge cache differently from the browser Cache-Control; the split let the CDN hold for an hour while the browser revalidated every minute.", "architecture", "technical", False,
     [("Surrogate-Control", "protocol"), ("Fastly", "service"), ("Cache-Control", "protocol")],
     [],
     "which header split decoupled CDN TTL from browser TTL on Fastly",
     "Surrogate Control Cache Control Fastly browser CDN TTL split"),
    # --- 47 ---
    ("Redis client-side caching using RESP3 push notifications cut the chat presence read p50 from 0.6 ms to 0.07 ms; the server tracked invalidations and pushed evicts to subscribed clients.", "milestone", "technical", False,
     [("Redis", "database"), ("RESP3", "protocol")],
     [("Redis", "Redis", "IMPROVES_ON")],
     "which Redis protocol feature cut chat presence read p50 by 8x",
     "Redis client side cache RESP3 push invalidate evict presence"),
    # --- 48 ---
    ("Caffeine's documentation was the reference for the W-TinyLFU sizing on the document cache; the published frequency-sketch parameters matched the workload skew almost out of the box.", "reference", "technical", False,
     [("Caffeine", "library"), ("W-TinyLFU", "algorithm")],
     [],
     "which library docs guided the W-TinyLFU sizing on the document cache",
     "Caffeine documentation W TinyLFU sizing frequency sketch skew"),
    # --- 49 ---
    ("Memcached extstore on flash held the long-tail asset cache; spilling to NVMe at 200 GB beat scaling DRAM linearly with the catalog growth.", "architecture", "technical", False,
     [("Memcached", "database"), ("NVMe", "infrastructure")],
     [],
     "which Memcached feature spilled the long-tail cache to NVMe instead of DRAM",
     "Memcached extstore flash NVMe long tail asset DRAM scale"),
    # --- 50 ---
    ("The shared Redis to per-service Caffeine migration finished on 2026-03-14; cross-service cache contention dropped to zero and the central Redis QPS halved overnight.", "milestone", "technical", False,
     [("Redis", "database"), ("Caffeine", "library"), ("2026-03-14", "date")],
     [("Caffeine", "Redis", "REPLACES")],
     "when did the per-service Caffeine migration retire the shared Redis hot path",
     "Caffeine Redis migration per service contention QPS half date"),
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
