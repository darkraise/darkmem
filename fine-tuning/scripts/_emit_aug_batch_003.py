"""One-off emitter for retrieval aug batch-003 — paraphrase kind over problem sources.

Writes 150 rows to data/v2/retrieval/aug_003.tmp.jsonl with ids ret-03401..03550,
pulling source rows from data/v2/retrieval/aug_sources/aug_003.jsonl.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "v2" / "retrieval" / "aug_sources" / "aug_003.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "aug_003.tmp.jsonl"
QUERY_KIND = "paraphrase"

# One query per source row, in the same order as the source rows.
QUERIES: list[str] = [
    # 001: Plant Jammer recipe app shutdown leaves gap in pantry substitutions
    "what did we lose when Plant Jammer closed down",
    # 002: MinIO multipart abort drift caught by contract test
    "how MinIO diverged from S3 on multipart uploads",
    # 003: GraphQL codegen optional everywhere due to missing non-null
    "cause of everything being optional in generated GraphQL types",
    # 004: Rust workspace-hack crate avoids triple serde rebuild
    "trick preventing repeated serde rebuilds across the Rust workspace",
    # 005: Parking feud with upstairs neighbor Martin unresolved
    "ongoing dispute with the neighbour upstairs",
    # 006: SmartThings lost Family Hub fridge before grocery run
    "why the Saturday shopping routine broke on 2026-03-08",
    # 007: Node.js worker leak from unremoved EventEmitter listeners
    "source of the leak in the Node worker process",
    # 008: poetry.lock rebase conflicts drove move to uv
    "reason CI kept breaking on dependency lockfile conflicts",
    # 009: GraalVM native-image reflection hit Jackson polymorphic
    "GraalVM trouble with Jackson polymorphism and the fix",
    # 010: Bun-produced lockfile unreadable by Yarn
    "why we delayed adopting Bun as the package manager",
    # 011: Manticore doubled throughput but lacked tenant isolation
    "why Manticore Search was rejected despite speed gains",
    # 012: Pydantic v2 killed Config inner class, moved to ConfigDict
    "how we migrated model settings onto Pydantic 2",
    # 013: Hello Fresh auto-canceled as duplicate against Mealime
    "why the meal-kit subscription got killed by the bank export",
    # 014: Dog GPS collar battery outpaced escape time
    "reason the pet tracker was returned",
    # 015: Voluntary carbon offsets criticised for inflated claims
    "credibility problems with voluntary carbon credits",
    # 016: Housewarming damage budget £180 for tile and sisal
    "repairs needed after the 2026-01-25 party and cost",
    # 017: React Context split into auth/theme/flags to stop re-renders
    "fix for the whole-tree re-render on feature flag fetch",
    # 018: Play Console signing rotation broke assetlinks.json
    "what broke Android App Links verification for a week",
    # 019: Whiskers died after 17 years; routine hurts most
    "what was hardest about losing the old cat",
    # 020: Milgram obedience findings contested by reanalysis
    "problems with the classical obedience study conclusions",
    # 021: Flutter engine 3.22 broke PlatformView on Android
    "why we pinned the Flutter engine on the Android build",
    # 022: Prometheus TSDB compaction stalled; out-of-order sample flag
    "how we handled Prometheus compaction stalls at 7M series",
    # 023: Rollup kept lodash because sideEffects false missing
    "why Rollup failed to tree-shake unused lodash helpers",
    # 024: Direct collapse vs Population III for early supermassive quasars
    "theories competing to explain early billion-solar-mass quasars",
    # 025: App Store 4.3 rejection forced separate SKU for rebrand
    "reason the white-label rebrand became its own app binary",
    # 026: Habitat build ran out of framing nails by noon
    "supply shortage on the 2026-03-28 volunteer build day",
    # 027: Cube vs Lightdash duplicated metrics; join semantics broke
    "why Cube and Lightdash both kept their own metric layer",
    # 028: ensure_ascii=False preserves emoji and non-BMP plurals
    "setting that keeps emoji intact through the catalog pipeline",
    # 029: Skewed partition on customer_id 42 fixed by murmur2 on synthetic key
    "how we fixed the hot Kafka partition on one customer",
    # 030: Xcode Time Profiler caught offscreen table auto-sizing storm
    "tool that exposed the main-thread layout spike in iOS",
    # 031: OTel Python auto-instrumentation disabled due to double spans
    "reason framework auto-instrumentation was turned off in Python",
    # 032: HFSM with Act sub-states replaces thousands of quest flags
    "structure adopted to tame quest flag ordering bugs",
    # 033: Soil carbon permanence contested; carbon cycles back in decades
    "doubts about the durability of soil carbon sequestration",
    # 034: Tokyo tipping insulted counter staff on first night
    "cultural gaffe learned the hard way in Tokyo",
    # 035: Bedtime negotiation with Priya settled at 7:45 weekdays
    "compromise reached over the kid's bedtime dispute",
    # 036: Xfinity outage + disconnected landline stranded dad on Alexa Together
    "reason reaching dad via Alexa Together failed on 2026-02-12",
    # 037: Traefik v3 label syntax caused silent 404s on older provider
    "origin of the silent 404s after the Traefik upgrade",
    # 038: Stray Set-Cookie made static assets private, skipping CDN
    "why static assets were bypassing the shared CDN cache",
    # 039: Dead vnd.api+json header lingered three months post rewrite
    "obsolete content type that stayed in config after cancellation",
    # 040: Descript Overdub made Lena think intro was re-recorded
    "AI tool that misled Lena about the podcast intro",
    # 041: BSON kept on-disk only; wire traffic moved to MessagePack
    "reason wire protocol swapped BSON for MessagePack",
    # 042: Vary: Accept-Encoding fixed brotli-vs-gzip Varnish caching
    "why brotli clients got stuck with gzip responses from Varnish",
    # 043: DATEBASE_URL typo silently hit default dev database in CI
    "typo that made CI connect to the wrong database",
    # 044: Variance annotations caught covariance bug in Reader cache
    "type annotation work that surfaced a Reader covariance issue",
    # 045: Prometheus WAL corruption after power loss; recovery flag
    "recovery flag that let Prometheus load past a torn WAL record",
    # 046: Linode outage took down Docker registry before CS50x deadline
    "why the 2026-03-15 homework submission was delayed",
    # 047: LaunchDarkly webhooks dropped events; moved to polling + ETag
    "reason we stopped trusting LaunchDarkly flag webhooks",
    # 048: Booking.com Genius discount silently dropped; refund took weeks
    "why the Porto hotel booking sparked a long refund fight",
    # 049: lockfile-lint gates unknown registries after fork incident
    "guardrail added after a transitive pointed at a forked repo",
    # 050: nosniff header added after JSON sniffed as HTML in legacy IE
    "header added to stop MIME sniffing of JSON responses",
    # 051: 2014-16 West African Ebola exposed WHO gaps; 2016 assessment
    "outbreak that triggered the WHO interim assessment report",
    # 052: Brotli on Parquet abandoned due to 6x encode slowdown
    "why brotli compression did not stick for Parquet archives",
    # 053: JTAG via PEMicro needed for K22F clock tree bug
    "debugging hardware required for the K22F clock tree issue",
    # 054: Backblaze 640 GB restore took 14 hours on fiber cap
    "why the Iceland photo restore took most of a day",
    # 055: NGP VAN sync dropped Spanish-language voter flags
    "outage that lost Spanish voter flags before the primary",
    # 056: Dweck growth mindset effects shrink in large replications
    "replication problems with growth mindset research",
    # 057: HAProxy DNS resolver stale TTL during Consul flap
    "how stale DNS answers hurt us during a Consul flap",
    # 058: terraform fmt churn fixed by pre-commit whitespace hook
    "how we stopped terraform fmt diff noise between editors",
    # 059: Waisbord 2013 Reinventing Professionalism diagnoses journalism crisis
    "book diagnosing journalism's professionalism crisis beyond the US",
    # 060: Subaru STARLINK lapse made remote-start a paywall prompt
    "reason the Outback remote-start suddenly required payment",
    # 061: Yodlee Capital One feed dropped; Tiller moved to CSV
    "why Tiller switched away from Yodlee for the savings account",
    # 062: webOS firmware fixed LG C2 SDR drop with Denon AVR
    "fix for the Sunday-night HDR dropout on the LG TV",
    # 063: Ghost 5.80 default theme flip broke Liebling fork
    "why the custom Ghost theme stopped rendering cards",
    # 064: Torn meniscus cancelled Patagonia; swapped to Mendoza
    "injury that forced the Patagonia trip to be scrapped",
    # 065: PMU LLC-miss counters found pointer-chasing hot loop
    "how PMU counters located the memory-bound hot loop",
    # 066: Bidi isolation via bdi or FSI; RLO flipped file list
    "attack that flipped a Hebrew user's file list display",
    # 067: Jess extended contract, rebooked Barcelona to late autumn
    "why Jess's Barcelona trip was pushed to later in the year",
    # 068: Superhuman abandoned because Raya couldn't share PTA filters
    "reason we went back to Gmail after trying Superhuman",
    # 069: Ring doorbell install fixed with dedicated 2.4 GHz SSID
    "how we got the Ring doorbell onto Wi-Fi at the front wall",
    # 070: Node fetch AbortController 5s cap stops event loop pin
    "why every outbound fetch has a hard five-second timeout",
    # 071: Google Family Link region bug broke Zara's downtime
    "bug that pushed the family off Android parental controls",
    # 072: ICU strings escape apostrophes with double single-quote
    "how to escape apostrophes without breaking ICU placeholders",
    # 073: Mutual-aid thread broke when admin phone died mid-storm
    "rule change after the signal thread went down during the storm",
    # 074: Missing CLDR bundle fell Russian plurals back to English
    "why Russian plural forms were rendering as English ones",
    # 075: Prime auto-renewed before EBT tier discovery
    "why we overpaid for Amazon Prime on 2026-01-22",
    # 076: Dependabot jsonwebtoken bump flipped default algorithm
    "what silently broke JWT verification in staging",
    # 077: Scheduler used local time; DST fired jobs an hour late
    "cause of the hour-off job firing around daylight saving",
    # 078: Schwab Intelligent Portfolios cash drag cost 2% vs Vanguard
    "how much the Schwab cash allocation underperformed by",
    # 079: Fight with Clara about two kids by 34 vs one later
    "disagreement with Clara about having children",
    # 080: TinaCMS upgrade dropped drafts before Monday publish
    "CMS upgrade that lost the interview series drafts",
    # 081: AFL++ found stack buffer overflow in TLV reader
    "fuzzer that uncovered the TLV parsing vulnerability",
    # 082: Android 15 background-audio throttle broke Dogo clicker
    "why the dog-training app stopped clicking on the Pixel 9",
    # 083: Rivian OTA 2026.14 killed RivianTracker's edge feature
    "Rivian update that obsoleted the third-party tracker app",
    # 084: HPA oscillation from CPU metric resolution vs cool-down
    "cause of the autoscaler flapping up and down",
    # 085: Concept2 ergdata needs home-server cron to reach Strava
    "workaround for Concept2 Bluetooth handoff to iPhone failing",
    # 086: npm scripts failed because CI image shipped sh not bash
    "why npm scripts failed on the CI container despite install success",
    # 087: Lloyds caught £2,400 cold-caller scam targeting Dad
    "near-miss financial scam on Dad and the guardrails added",
    # 088: Felix only eats greens wrapped in cheese
    "nephew's strategy for accepting vegetables",
    # 089: Q3 2025 burnout signs: weekends, flat affect, skipped therapy
    "warning signs that were missed in the burnout episode",
    # 090: Toyota remote-start paywall killed RAV4 key-fob feature
    "Toyota subscription paywall that disabled the fob feature",
    # 091: Themed time-blocking collapsed at first plumber interruption
    "why the Deep Work Monday experiment failed quickly",
    # 092: Moved list data out of Redux into TanStack Query cache
    "how server-side lists got separated from Redux state",
    # 093: Blanton and Jaccard 2006 critique of IAT zero point
    "psychology paper criticising the IAT's diagnostic scale",
    # 094: Croup ER visit; steam bathroom helped before drive
    "home remedy that bought time before the croup ER trip",
    # 095: Bathroom retile ran long because screed sloped 9mm
    "reason the bathroom tiling job took eleven days",
    # 096: Kafka rebalance storms from too-short session.timeout.ms
    "setting that was causing Kafka consumer rebalance storms",
    # 097: Hubble tension between local H0 ~73 and Planck ~67
    "discrepancy in the two main measurements of the Hubble constant",
    # 098: Team fish adoption failed; kept zsh default
    "why the team never moved to fish as the default shell",
    # 099: Family can't agree where to scatter Grandma Vera's ashes
    "unresolved decision about scattering Grandma's ashes",
    # 100: Side gate hinge snapped after 2 years of rust
    "what finally forced the side gate replacement",
    # 101: Eysenck 1952 claimed psychotherapy no better than remission
    "1952 paper that ignited decades of psychotherapy outcome research",
    # 102: Nintendo cloud save limits pushed to JKSV on Switch
    "why the family uses JKSV to back up Animal Crossing",
    # 103: Cloudflare Logpush to Grafana surfaced bad Vary header
    "how a cache hit-ratio dashboard exposed a Vary header bug",
    # 104: Windows paths broke loader; standardized pathlib.Path
    "fix for the cross-platform path issue in the fine-tune loader",
    # 105: P-hacking surfaces when only significant tests reported
    "statistical malpractice from running many tests and cherry-picking",
    # 106: Passport lost in Buenos Aires before Iguazú; 36h embassy
    "travel emergency the day before the Iguazú flight",
    # 107: SWR cached stale cursor; fast back-clicks wrong page
    "pagination bug caused by SWR caching the cursor",
    # 108: Yarn PnP migration rolled back over Jest/Webpack resolver gaps
    "why Yarn PnP was abandoned a second time",
    # 109: DeprecationWarning stacklevel=2 surfaced warnings in callers
    "Python setting that made deprecation warnings actually visible",
    # 110: Phoenix presence heartbeats batched into audit log
    "how we stopped presence events from flooding the audit log",
    # 111: Language toggle persists via cookie with server-side dir
    "why client-only language toggles hurt accessibility",
    # 112: Added username hash to rate-limit key; per-IP alone insufficient
    "why per-IP rate limiting failed against the signup botnet",
    # 113: aria-live status region announces async loading
    "accessibility fix so JAWS users hear loading states",
    # 114: tsc-alias rewrites tsconfig paths for Node runtime
    "tool that made tsconfig path aliases work at runtime",
    # 115: Cloud feedback uncertainty dominates climate sensitivity spread
    "largest source of uncertainty in climate sensitivity estimates",
    # 116: Garmin-Strava pairing doubled leaderboard runs
    "unintended effect of linking Garmin to Strava",
    # 117: PlushCare routed refill to wrong state physician
    "app that kept sending mom's prescription to the wrong state",
    # 118: Flutter hot reload broke after riverpod provider-scope move
    "why hot reload stopped working after the Riverpod upgrade",
    # 119: Leo's bath drain fear fixed with stopper and ducks
    "how we got Leo back into the bath after the drain scare",
    # 120: Date JSON hydration mismatch fixed with reviver
    "source of the Date hydration mismatch between server and client",
    # 121: Dataform shelved after moving off BigQuery
    "why Dataform was dropped from the stack",
    # 122: Oakridge fall; sensor mat caught the bed exit
    "assistive device that detected Dad's night-time fall",
    # 123: TypeError str vs UUID; str(memory_id) fix
    "remedy for the UUID type error at the vector repo boundary",
    # 124: Whoop strain-coach conflicted with Saturday long run plan
    "conflict between Whoop coaching and the long run schedule",
    # 125: CUDA OOM from grad accum; smaller batch, more steps
    "how we stopped the fine-tune job running out of GPU memory",
    # 126: Royal Oak function room deposit due by 2026-04-30
    "deadline to confirm the parents' 50th anniversary venue",
    # 127: Boxed.com shutdown redirected bulk orders to Costco
    "why bulk pantry orders shifted back to Costco",
    # 128: Alexa Together 4am light event ambiguous until Ring clip
    "how we ruled out Dad wandering at 4am on 2026-02-28",
    # 129: Omegle install on family iPad led to MDM reset
    "incident that forced the switch to Apple Configurator for the iPad",
    # 130: InfluxDB pod_name tag cardinality blew up TSI index
    "Kubernetes label that exploded InfluxDB cardinality",
    # 131: DayZ community moved from DayZSA Launcher to DZSA
    "launcher swap that fixed DayZ desync for the London group",
    # 132: pyrefly parked over third-party stub gaps
    "type-checker trial that was shelved over stub coverage",
    # 133: Echo Studio misheard 'Low Roar' and lagged Spotify handoff
    "why the Echo Studio lost its place in the kitchen rotation",
    # 134: Repo-map index cut tokens 4x on 800k LOC Java
    "how we eased context window pressure on the huge Java repo",
    # 135: Xdebug caught DB lookup inside a PHP menu loop
    "profiling tool that found the per-menu-item database query",
    # 136: Petcube Bites 2 servo jammed and dumped treats
    "pet-feeder malfunction that dumped the hopper on the floor",
    # 137: iOS 18 reset Screen Time downtime for Mei
    "iOS update that wiped the kid's downtime restrictions",
    # 138: Lisbon SEF to AIMA transition tripled residency wait
    "what the SEF-to-AIMA handover did to residency wait times",
    # 139: Gettier cases undermine justified true belief account of knowledge
    "philosophical counterexamples challenging the JTB definition of knowledge",
    # 140: Type Ia supernova vs CMB dark energy tension
    "tension between supernova and CMB measurements of expansion",
    # 141: aria-current='page' added for screen reader nav context
    "accessibility attribute added to mark the active nav link",
    # 142: PerfView heap diff traced leak to DI-cached collection
    "how we traced the slow .NET leak to a DI scope mistake",
    # 143: Audible clawed back credits; moved to Libro.fm
    "why audiobook purchases moved off Audible",
    # 144: Inkscape SVG rounding drift broke golden files; pinned renderer
    "how we stopped SVG golden file tests from drifting",
    # 145: Unit-of-work aggregate flush replaced ORM cascade saves
    "fix that eliminated orphaned partial saves in support tickets",
    # 146: Embedder fine-tune stalled when dehumidifier tripped breaker
    "why the overnight embedder training run didn't finish",
    # 147: Claude Code rate limits pushed to Continue.dev + Mistral
    "fallback used when hitting Claude Code rate limits during crunch",
    # 148: OBS NDI dropped; telemetry reverted to CS spectator default
    "why the charity stream lost its custom on-screen telemetry",
    # 149: 2019 Nobel Literature controversy over Handke on Milosevic
    "controversy attached to the 2019 literature Nobel laureate",
    # 150: 04:45 wake experiment collapsed in 11 days under sleep debt
    "why the early-morning wake experiment failed after eleven days",
]


def emit() -> int:
    with SOURCES.open("r", encoding="utf-8") as f:
        sources = [json.loads(line) for line in f if line.strip()]
    assert len(sources) == 150, f"expected 150 source rows, got {len(sources)}"
    assert len(QUERIES) == 150, f"expected 150 queries, got {len(QUERIES)}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as out:
        for query, src in zip(QUERIES, sources):
            row = {
                "id": src["new_id"],
                "source_id": src["source_id"],
                "query": query,
                "positive": src["text"],
                "query_kind": QUERY_KIND,
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
