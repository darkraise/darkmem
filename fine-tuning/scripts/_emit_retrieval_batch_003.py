"""One-off emitter for retrieval top-up batch-003.

Reads 100 source rows from shared.jsonl starting at SHARED_OFFSET and
emits a paraphrase-kind query per row into a tmp jsonl. The output is
written to data/v2/retrieval/batch_003.tmp.jsonl and validated by
scripts.validate_v2.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_003.tmp.jsonl"
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"

ID_OFFSET = 200
SHARED_OFFSET = 200
QUERY_KIND = "paraphrase"

QUERIES: list[str] = [
    # 200 - lab prefers preprints on arXiv
    "Where does the research group share early drafts ahead of formal journal submission?",
    # 201 - Obsidian for personal and Lumen engineering docs
    "Which markdown app holds both my private journal and Lumen's design write-ups?",
    # 202 - Anki over Quizlet for Spanish on commute
    "Which spaced-repetition tool replaced the other one for my language drilling?",
    # 203 - Garmin Friday sync issue after firmware update
    "Why did my wrist tracker stop pushing daily steps following a software refresh?",
    # 204 - shipped marathon training tracker on 2026-03-15
    "On what date did my long-distance running companion app finally launch?",
    # 205 - Peak by Anders Ericsson reshaped code reviews
    "Which book on expert performance changed how I run engineering critique meetings?",
    # 206 - Todoist + Linear synced via Zapier
    "What automation keeps my home to-dos in lockstep with the office ticket queue?",
    # 207 - Kindle preferred over tablet for technical papers
    "Which device do I reach for when reading dense scholarly articles?",
    # 208 - Spotify family plan kicking Jamie off after IP changes
    "Which audio subscription kept booting my partner whenever the router cycled addresses?",
    # 209 - switched running playlists from Apple Music to Spotify
    "What workout streaming app did I move to for better tempo recommendations?",
    # 210 - noise: quick look and get back
    "Pause briefly, review, then circle back with more information.",
    # 211 - GLiNER on RTX 5060 takes 40 minutes per epoch
    "Roughly how long is a single training pass for the small extractor at home?",
    # 212 - first LAN party at flat on 2026-02-14
    "When did I first host a multiplayer gaming night in our apartment?",
    # 213 - watching Karpathy lectures before bed
    "Whose machine-learning videos do I queue up most weekend evenings?",
    # 214 - migraines from launch stress, cut Slack notifications
    "How did I tame the headaches caused by the launch crunch?",
    # 215 - chose Proxmox over Unraid for cluster failover
    "Which virtualization platform won the homelab pick due to its clustering story?",
    # 216 - UniFi gateway, IoT VLAN, WireGuard
    "How is the household network sliced and reached securely from the road?",
    # 217 - prefers async standups over daily video calls
    "Which standup style fits the team's neurodiverse rhythm better?",
    # 218 - Ollama on Mac Studio for journal summarisation Sundays
    "What Sunday routine runs my desktop language model on personal diary entries?",
    # 219 - 200k step week on 2026-04-10 in Kyoto
    "When and where did I rack up two hundred thousand steps in seven days?",
    # 220 - iCloud Photos hit 5 GB cap mid-trip
    "Why did vacation pictures stop uploading partway through the holiday?",
    # 221 - Dr. Huberman caffeine 2 PM cutoff
    "Which podcast advice drives my afternoon coffee deadline at the desk?",
    # 222 - moved family budget Google Sheet to YNAB
    "What pushed our household money tracking off a spreadsheet onto envelope software?",
    # 223 - uses Markdown everywhere
    "Which lightweight text format covers all my writing from work to greeting cards?",
    # 224 - home Kubernetes runs Immich, Paperless-ngx, Ghost
    "Which self-hosted apps live on the household container orchestrator?",
    # 225 - dotfiles and Python utilities managed by chezmoi
    "How does my developer setup stay reproducible across machines?",
    # 226 - noise: re-read the last part
    "Hold on a moment so I can review the closing portion again.",
    # 227 - first embedder finished on 2026-04-12 on RTX 5060
    "When did my debut embedding-model run wrap up on the home GPU?",
    # 228 - swapped Gmail for Fastmail for Anna's wedding archive
    "Which email host swap was driven by needing a searchable wedding thread?",
    # 229 - Apple Watch GPS drops in Dolomites canyons
    "Where did my smartwatch lose satellite lock during a recent hike?",
    # 230 - Tolstoy paperback, textbooks on reMarkable
    "How do I decide between paper and e-paper for different reading material?",
    # 231 - Nix config for ThinkPad also sets up Jamie's laptop
    "Which configuration tool unifies my dev box with my partner's work machine?",
    # 232 - Andy Matuschak evergreen notes shapes code comments and recipes
    "Whose note philosophy guides both my source comments and family cookbook?",
    # 233 - Postgres on home server for habit tracker, meal planner, training log
    "What single datastore underpins my routine-tracking side projects at home?",
    # 234 - Tailscale over self-hosted VPN for Maya into Plex
    "What network layer did we adopt to give a friend remote media library access?",
    # 235 - dog GPS collar drained battery, returned
    "Why did the canine tracking gadget head back to the retailer?",
    # 236 - bill-splitting spreadsheet automated via Apps Script on 2026-03-30
    "When did the shared expense sheet finally get its scripted automation?",
    # 237 - prefers outdoor desk with Kyoto skyline over home office
    "Which spot do I favour for video calls when given a choice?",
    # 238 - AeroPress recipe: 14g coffee, 220ml water, 85C
    "What are my locked-in numbers for the manual brewer each morning?",
    # 239 - Getting Things Done by David Allen drives inbox and groceries
    "Which productivity book runs both my work queue and shopping list?",
    # 240 - paid for ChatGPT Plus for Sarah's college essays
    "What family editing need pushed me onto the paid AI assistant tier?",
    # 241 - Home Assistant motion in hallway triggers night lights
    "How does the smart home react when someone walks down the corridor at night?",
    # 242 - VS Code crashed opening Whole30 spreadsheet via SQLite extension
    "Which app and plugin combination froze on a meal-plan database file?",
    # 243 - Kayak beats Google Flights for Berlin-Lisbon family travel
    "Which booking site predicts our European family flights more accurately?",
    # 244 - RTX 5060 handles gaming and GLiNER without throttling
    "How is the household graphics card holding up under both gaming and model training?",
    # 245 - first conference talk at DevOpsCon Kyoto on 2026-04-08
    "When and where did I deliver my inaugural conference presentation on homelab observability?",
    # 246 - ZFS pool on NAS holds photo archive back to 2005, weekly snapshots
    "Where does the long-running family picture history sit and how is it snapshotted?",
    # 247 - Logseq over Notion for medical-record privacy
    "Which personal note app earned the spot thanks to keeping health data local?",
    # 248 - Atul Gawande checklist philosophy for deployment pre-flight
    "Whose surgical-style checklist thinking shaped our release readiness gates?",
    # 249 - Garmin + Strava double-counted runs in leaderboard
    "What integration bug counted my training sessions twice on the social ladder?",
    # 250 - Radicale on NAS, CalDAV over WireGuard
    "How does the household sync schedules across phones with self-hosted bits?",
    # 251 - Picked Temporal for billing retry engine
    "Which workflow engine took on the new payments retry component?",
    # 252 - Cassandra tombstone read path, switched to per-partition expiry
    "What change to expiry strategy resolved the wide-column read latency issue?",
    # 253 - OpenTelemetry parity with Zipkin on 2026-03-05
    "When did the modern tracer take over from the older one in production?",
    # 254 - gRPC over HTTP/2 still has TCP head-of-line blocking
    "Why does fancy multiplexing still suffer at the kernel transport layer?",
    # 255 - Bun over Node.js for gateway, 800 ms to 40 ms
    "Which JavaScript runtime swap dropped boot time by an order of magnitude on the edge?",
    # 256 - Cloudflare Workers run auth at the edge
    "Where in the request path is authentication actually performed before reaching origins?",
    # 257 - Dynamo conditional write reserved-word silent failure
    "What naming pitfall silently broke conditional writes in the key-value store?",
    # 258 - Iceberg over Delta Lake for vendor neutrality
    "Why did we land on the open table format over the alternative for the lake?",
    # 259 - Raft paper by Ongaro and Ousterhout underpins etcd
    "Whose consensus paper sits behind the cluster behind our key-value coordinator?",
    # 260 - noise: run the build again
    "Time to rerun the build process so the result is verified.",
    # 261 - Rust migrator leaked file handles on Windows due to tokio blocking tasks
    "Why did the Rust migration tool hold onto operating system handles on Windows?",
    # 262 - Feature store: Redis online + BigQuery offline behind Python DSL
    "How is feature retrieval split between fast online and bulk offline paths?",
    # 263 - JWT alg=none vulnerability, allow-list algorithms
    "What old token signing pitfall still demands a verified algorithm allowlist?",
    # 264 - pip to uv, 90s to under 2s
    "Which Python dependency tool replaced the standard one and how big was the speedup?",
    # 265 - Postgres major version upgrade on 2026-01-27 via logical replication
    "When did the seamless relational engine bump finish using logical replication?",
    # 266 - Kafka rebalance storms from short session.timeout.ms
    "What broker setting caused continuous consumer group churn under heavy processing?",
    # 267 - Hashicorp Nomad scheduler shares cluster with ML jobs, GPU bin-packing
    "Which orchestrator shares hosts with the model training fleet using GPU bin-packing?",
    # 268 - Replaced cron with Dagster for lineage and backfills
    "Which orchestration platform replaced our handcrafted scheduler for first-class backfills?",
    # 269 - Rust over Go for critical-path services
    "Which systems language wins for hot paths thanks to compile-time resource catches?",
    # 270 - AES-GCM preferred over AES-CBC + HMAC for new TLS
    "Which symmetric mode is recommended over the older encrypt-then-MAC pairing for fresh TLS?",
    # 271 - CloudFront for cold paths, ALB + Route 53 for warm
    "How are cold and warm request paths distributed across our AWS edge layers?",
    # 272 - Pytest collection ballooned because of autouse fixtures keeping DB connections
    "Why did test collection blow past three gigabytes of memory?",
    # 273 - OAuth 2.0 PKCE in RFC 7636 for mobile clients
    "Which RFC defines the verifier-challenge dance used by mobile OAuth clients?",
    # 274 - Production hit five-nines for first quarter on 2026-04-01
    "When did availability hold at top-tier across an entire quarter for once?",
    # 275 - CPython releases GIL in C extensions, numpy parallelises
    "Why can numerical loops run in parallel under the interpreter lock?",
    # 276 - Litestream for SQLite to S3 on edge nodes, Postgres overkill
    "How do edge devices ship their tiny database to the object store instead of running Postgres?",
    # 277 - canonical request path: gateway, rate limiter, Envoy, auth, business
    "What does the standard inbound chain look like before requests reach our handlers?",
    # 278 - Homebrew autoupdates broke dev with openssl@3, pinned Brewfile
    "What macOS package manager update broke local dev and how was it locked down?",
    # 279 - Linux cgroups v2 unified hierarchy, systemd delegates slices
    "How does the modern Linux resource control system organize its controllers?",
    # 280 - RabbitMQ quorum queues over classic mirrored, mirror drift
    "Why did the broker move off mirrored queues onto consensus-based ones for retries?",
    # 281 - prefer CDK over raw CloudFormation
    "Which infrastructure-as-code abstraction beats the bare AWS template language for us?",
    # 282 - CoreDNS SERVFAIL from upstream rate limit, switched to 1.1.1.1 + Unbound
    "How did we stabilize cluster name resolution after upstream limits?",
    # 283 - Go 1.22 across all services on 2026-03-10 with range-over-func
    "When did every service finish moving to the new compiler version with range-over-func?",
    # 284 - noise: re-running with debug flag
    "Now retrying that command with verbose mode switched on.",
    # 285 - Istio ingress terminates HTTPS, sidecars handle east-west mTLS
    "Where does internal encrypted traffic terminate inside the mesh?",
    # 286 - B-tree vs BRIN in Postgres
    "Which Postgres index pays off for append-only ordered data over the standard one?",
    # 287 - Webpack to Vite, 25s to 2s dev boot
    "Which frontend bundler replaced the older choice and slashed dev startup time?",
    # 288 - prefers self-hosted CI runners over GitHub cloud, build cache locality
    "Why does the team keep running its own CI agents rather than the hosted fleet?",
    # 289 - ClickHouse merge storms from low parts threshold for batch size
    "What configuration mismatch stalled inserts in the columnar warehouse during merges?",
    # 290 - Google SRE error budget chapter shapes feature vs reliability
    "Which reliability text guides our trade-off between shipping speed and uptime?",
    # 291 - Migrated last Oracle to AWS Aurora Postgres on 2025-12-15
    "When did the final on-prem Oracle box move to managed Aurora?",
    # 292 - W3C Trace Context, Tempo storage, Grafana correlation
    "How do request identifiers travel and where can engineers query them later?",
    # 293 - Python 3.12 per-interpreter GIL via PEP 684
    "What language proposal began enabling true parallel Python interpreter execution?",
    # 294 - Snyk over Dependabot for SCA
    "Which vulnerability scanning vendor took the slot from the GitHub default?",
    # 295 - gRPC clients deadlocked on TLS renegotiation under load, Go client uncapped streams
    "What caused the RPC clients to lock up during high-traffic TLS renegotiation?",
    # 296 - idempotency keys at gateway, 24h SETNX in Redis
    "How does the gateway suppress duplicate inbound events over a daily window?",
    # 297 - ArgoCD app-of-apps over Helmfile for fleet-scale gitops
    "Which gitops layout beats the Helm tooling for promoting changes across many clusters?",
    # 298 - HTTP/3 in RFC 9114, QPACK in RFC 9204
    "Which RFCs cover the new web transport and its header compression scheme?",
    # 299 - HPA oscillation when CPU metric resolution lower than cool-down
    "What metric timing mismatch caused the autoscaler to oscillate in production?",
]

assert len(QUERIES) == 100, f"expected 100 queries, got {len(QUERIES)}"


def emit() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    with SHARED.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))

    slice_rows = rows[SHARED_OFFSET : SHARED_OFFSET + 100]
    if len(slice_rows) != 100:
        raise SystemExit(
            f"shared.jsonl slice yielded {len(slice_rows)} rows; expected 100"
        )

    with OUT.open("w", encoding="utf-8") as out_f:
        for i, (src, query) in enumerate(zip(slice_rows, QUERIES)):
            row = {
                "id": f"ret-{ID_OFFSET + i + 1:05d}",
                "source_id": src["id"],
                "query": query,
                "positive": src["text"],
                "query_kind": QUERY_KIND,
            }
            out_f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"wrote {len(slice_rows)} rows to {OUT}")


if __name__ == "__main__":
    emit()
