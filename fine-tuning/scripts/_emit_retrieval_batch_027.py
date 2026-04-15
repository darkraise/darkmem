"""One-off emitter for retrieval top-up batch-027 — multi-sentence queries.

Each row pairs a longer, paragraph-shaped query (2-4 sentences, 20-60 words) with
its source shared row as the positive. Queries simulate a careful user typing out
context and a specific question instead of a terse search phrase.

Writes 100 rows to data/v2/retrieval/batch_027.tmp.jsonl with ids ret-02601..02700,
pulling positives from shared rows at zero-indexed offsets 2600..2699.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_027.tmp.jsonl"
ID_OFFSET = 2600
SHARED_OFFSET = 2600
QUERY_KIND = "multi-sentence"

# 100 multi-sentence queries, aligned in order with shared rows 2601..2700.
QUERIES: list[str] = [
    # 02601 EngFlow vs BuildBuddy bakeoff
    "We're reviewing our Bazel remote execution vendor choice. Which of the two we evaluated lost on unit pricing for the cache-miss profile, and what did the winner give up compared to the other's scheduler fairness?",
    # 02602 Buck2 replaced Bazel on Rust subtree
    "Our Rust-heavy subtree used to live under Bazel. Which build tool took over that subtree, and what specifically about its daemon gave a much better no-op rebuild on cold caches than the Starlark DAG did?",
    # 02603 Hermetic C++ from Nix pinned narHash
    "The hermetic C++ build used to leak the host clang occasionally. Where does the toolchain come from now, and what property of that derivation stopped CROSSTOOL from picking up /usr/bin/clang?",
    # 02604 mold 2.4 replaced lld on release link
    "Release link times used to stretch past ten seconds on the server binary. Which linker swap cut that down, and roughly how much wall time did the change save on the same box?",
    # 02605 lld kept on Apple Silicon
    "The macOS builders didn't follow the main linker swap. Which linker kept running there, and what about the replacement's platform support was the blocker during the cutover window?",
    # 02606 sccache + S3 beat local redis
    "Cold Rust CI runs were stuck around 22 minutes earlier this year. Which compiler cache backend finally brought that down to roughly 7, and what was wrong with the local redis layer we tried first?",
    # 02607 ccache 4.9 depend_mode restores hits after format
    "clang-format was shuffling headers and tanking our ccache hit rate. Which ccache option restored the hits across those reshuffles, and roughly how much did hit rate climb on the core repo?",
    # 02608 distcc retired after tailnet + sccache
    "Our distcc-over-ssh setup was retired once the mesh VPN was in place. What ended up carrying the remote compile load afterwards, and why was the middle hop no longer useful?",
    # 02609 noise fan spun up
    "Somebody on the call just said their laptop fan spun up and to hold on. Is that a pause I should work around, or is it effectively just filler until they're back?",
    # 02610 Ninja replaced Make in CMake preset
    "Our CMake presets used to fall back to Make generators. Which generator replaced that, and roughly how much did the no-op rebuild on a warm tree drop after the switch?",
    # 02611 CMake EXPORT_COMPILE_COMMANDS for clangd
    "Editor index files kept drifting between developer laptops. Which CMake preset setting standardised the compile_commands.json output, and which editor backend finally stopped diverging once it was on?",
    # 02612 Zig 0.13 cross-compile wraps glibc toolchain
    "Cross-compiling for five target triples used to need separate sysroots. Which toolchain collapsed them into a single host install, and what specifically is it wrapping on the link-and-libc side?",
    # 02613 Zig uses ld.lld for aarch64 cross
    "The aarch64 Linux cross link had a vendored ld sitting in the repo for years. Which wrapper replaced that path, and what actually ships the final link for the arm64 target now?",
    # 02614 Reproducible Builds 2021 SOURCE_DATE_EPOCH spec
    "I'm reviewing the release runbook's timestamp guidance. Which upstream specification is cited there for SOURCE_DATE_EPOCH behaviour, and what part of that document do we quote verbatim for the fallback semantics?",
    # 02615 Debian 13 mandatory PIE
    "The Debian 13 release tier recently tightened its hardening posture. Which executable flag became mandatory, and what happens in our build scripts now if -fPIE is missing from CFLAGS?",
    # 02616 objcopy split debug + strip saves 140MB
    "Our shipped artefact used to carry a lot of debug info weight. Which two tools were chained in the release pipeline to split debug info out, and did we give up crash symbolication in the process?",
    # 02617 tsan/ubsan nightly, asan too costly
    "Nightly sanitizer coverage got expanded earlier this year. Which two sanitizers run on a dedicated Bazel config now, and why does the release pipeline still skip asan on the main flow?",
    # 02618 msan stalled on Rust crates
    "We tried to push msan further than the C subtree. Why did adoption stall on the Rust crates specifically, and what's the current scope msan is limited to as a result?",
    # 02619 AutoFDO profiles cut p99 9 percent
    "Production profiling fed into our optimizer for a month. Which tool collected the samples, and what did the PGO relink do for request p99 latency and instruction cache behaviour?",
    # 02620 Propeller stacks on AutoFDO for +3%
    "After AutoFDO landed we layered another post-link step on top. Which tool handles that layout pass, and roughly how much additional p99 reduction did it buy once wired into the release script?",
    # 02621 Full LTO yearly, ThinLTO daily
    "The nightly relink budget is 45 minutes and we blew past it with one LTO mode. Which LTO variant was held back for the yearly hardening release, and which stayed on daily CI?",
    # 02622 SOURCE_DATE_EPOCH across Debian/Nix/npm
    "diffoscope used to flag timestamp-only differences between identical-input rebuilds. Which environment variable was threaded through the packaging formats to silence that, and which three packagers pick it up now?",
    # 02623 Nix narHash caught OpenSSL host leak
    "Two Nix builders were producing different store paths from the same sources. Which hashing mechanism exposed the hidden host library leak, and what had to be pinned explicitly in the derivation to fix it?",
    # 02624 Guix vs Nix on reproducibility bench
    "We ran two functional packagers side by side on the reproducibility bench. Which packager won on bit-for-bit results for the Scheme-heavy packages, and which kept the Python data-science closures?",
    # 02625 Debian reproducible-builds 96 percent 2026-03-04
    "Debian's reproducible-builds initiative hit a coverage milestone earlier this year. When did the server base image cross 96 percent certification, and what kind of binary still accounted for the remaining drift?",
    # 02626 Bazel grpcs remote_cache for cross-site sharing
    "Two geographic sites wanted to share Bazel artefacts without waiting on a registry sync. Which Bazel remote cache configuration made that work, and what was avoided by going that route over registry replication?",
    # 02627 JFrog Artifactory promotion pipeline
    "Our dev-to-staging-to-prod binary promotion needs traceable signatures per stage. Which registry carries that pipeline today, and which build metadata document do the signatures stay pinned to through the stages?",
    # 02628 Cloudsmith replaced Sonatype Nexus
    "We moved off a self-hosted Maven and npm registry earlier this year. Which managed service replaced Sonatype Nexus, and what tipped the decision between licence savings and operational burden of HA clusters?",
    # 02629 Verdaccio local npm mirror prewarm
    "Offline laptops needed to keep building against npm. Which local mirror was put in front of the public registry, and what trigger prewarms the cache so dependabot-introduced deps don't stall on first fetch?",
    # 02630 devpi PyPI mirror on homelab box
    "Our restricted-network CI runners can't reach the public PyPI. Which proxy is feeding them wheels from a homelab box, and where does it refresh its simple index from on its nightly rebuild?",
    # 02631 panamax Cargo mirror caught yank
    "A crate yank incident hit us last week. Which local Rust mirror shielded the builds, and why did having it in front of crates.io keep the artefacts reproducible through the yank?",
    # 02632 cosign on npm publish, rekor + GitHub Actions
    "The public SDK's npm publish step grew a new signing phase. Which tool handles the signing, and what does the transparency log cross-reference so auditors can trace back to the GitHub Actions workflow run?",
    # 02633 noise coffee cup
    "Someone just made an offhand comment about a missing coffee cup. Should I treat that as useful context for the work, or is it just noise I can skip past without losing anything?",
    # 02634 Gradle cache moved to Develocity from S3
    "Our Gradle remote build cache migrated earlier this year. Which managed node took over from the S3-backed bucket, and what analytics feature made regression bisection easier than sifting through raw object store logs?",
    # 02635 mill replaced sbt on new Scala services
    "The new Scala services picked a different build tool than the legacy ones. Which tool replaced sbt, and what about sbt's incremental compiler on cold CI clones pushed the decision over the line?",
    # 02636 sbt stayed on Akka legacy
    "Not every Scala service moved off sbt. Which stack stayed on sbt, and what cost-benefit argument around the plugin surface and current maintenance freeze kept the migration on hold?",
    # 02637 Cargo workspaces + sccache on monorepo
    "Fresh-checkout compile times on the Rust monorepo used to hit 14 minutes. Which Cargo structure cut the bulk of that, and which cache piled on the remaining gains after the layout change?",
    # 02638 buck2 beats Cargo past 1200 crates
    "Past a certain dep-graph size Cargo workspaces stopped scaling on the Rust subtree. Which build tool outran it, and what was the actual bottleneck that made the swap worthwhile once the graph crossed 1200 crates?",
    # 02639 Bazel BwoB keeps laptops off intermediates
    "Developer laptops were filling up with Bazel intermediate artefacts. Which pair of flags on the BuildBuddy remote cache stopped the local materialisation, and what did that do to dev-fleet disk pressure?",
    # 02640 Gradle config cache + predictive test selection
    "The accountant was asking about the Android CI bill. Which two Gradle and Develocity features combined to bring the dollar cost down, and which team stopped asking follow-up questions after the rollout?",
    # 02641 CMake FetchContent retired for CPM
    "Our CMake dependency fetcher got swapped out after a supply-chain scare. Which fetcher was retired, which prewarm-capable alternative replaced it, and what specifically about a force-moved GitHub tag exposed the old setup?",
    # 02642 rules_python hermetic interpreter 2026-02-27
    "The Bazel Python toolchain stopped pulling the interpreter from the host earlier this year. When did that change land, and what is the shared PyPI mirror still doing in the flow even after the cutover?",
    # 02643 rules_rust prebuilt toolchain URL
    "The in-tree rustc_binary pattern was replaced on our Bazel setup. Which rules layout took over, and what did the prebuilt toolchain URL buy us on CI warm-cache startup while keeping the pinned channel?",
    # 02644 Nix flakes pin gcc-arm-none-eabi 13.2.1
    "The embedded firmware C++ toolchain needs bit-for-bit reproducibility. Which packaging mechanism locks it, and down to what level of precision is the gcc-arm-none-eabi version pinned across CI builders?",
    # 02645 Guix channel for scientific Python
    "The scientific Python environment used to drift between collaborators. Which packaging mechanism now holds it identical across repo clones, and what two libraries specifically stopped wobbling once it was in place?",
    # 02646 Fulcio keyless replaced Yubikey signing
    "The weekly Cargo publish used to block on a human keyholder. Which signing flow replaced the local Yubikey setup, and what operational win did engineers get back after that swap?",
    # 02647 Conan registry requires CycloneDX SBOM
    "Our Conan registry now enforces SBOM attachment at promotion time. Which SBOM format sits alongside the .tgz, and at which pipeline stage is it verified before the tag is applied?",
    # 02648 -ffunction-sections + --gc-sections trim embedded
    "The embedded image was crowding out the bootloader sector. Which compiler-linker flag pair enabled dead-code elimination at link time, and roughly how much image shrinkage did that buy us?",
    # 02649 rules_cuda hermetic CUDA 2026-04-02
    "The GPU test farm couldn't always reproduce driver-version-sensitive failures. Which hermetic CUDA setup landed on the Bazel side, when did it go in, and what category of January failures can it now replay on demand?",
    # 02650 Cloudflare Workers KV read-heavy flags
    "Feature flags see far more reads than writes. Which edge key-value store backs that read-heavy path, and why was eventual consistency across pops acceptable for the 60-second rollout window?",
    # 02651 Cloudflare D1 replaced KV for sessions
    "Session storage moved off the edge KV store earlier this year. Which edge datastore took over, and why did strong consistency on writes suit the login flow better than eventual reads?",
    # 02652 Cloudflare R2 replaced S3 for assets
    "Large asset blobs got pulled out of D1. Which object store holds them now, and roughly how much did egress-free reads cut off the monthly bandwidth bill compared to the old S3 setup?",
    # 02653 Durable Objects for per-room chat
    "Per-room chat state needed tight ordering guarantees. Which Cloudflare primitive ended up holding that state, and what did it beat Redis pubsub on specifically at our low user counts?",
    # 02654 Hyperdrive pools Postgres from Workers
    "Checkout handler cold latency used to sit around 480 ms. Which Cloudflare service pooled the Postgres connections from Workers, and what did the cold number drop to after the pooling layer was in front?",
    # 02655 Smart Placement collocates Workers with origin
    "Synchronous auth queries from Workers were paying a lot of crossing cost. Which Cloudflare feature relocated the Workers execution closer to the origin database, and what class of request benefited the most?",
    # 02656 Fastly Compute@Edge replaced VCL image resize
    "Our VCL-based image handling had grown into string soup. Which Fastly platform and language combination replaced it, and what did the new stack match on feature parity without the ESI mess?",
    # 02657 VCL kept on marketing pages
    "Not every edge path moved off VCL. Which pages stayed on the legacy setup, and what about those pages' A/B logic in the existing header rewrites made the migration to Compute@Edge not worth it?",
    # 02658 Akamai EdgeWorkers rejected for resizer
    "We considered Akamai's edge runtime for the heavy image transform. Why didn't it land there, and which two runtime limits on CPU and bundle size were the ones that choked the sharp-based resizer?",
    # 02659 noise flush edge cache
    "One side of the chat just asked for a second to flush the edge cache. Do I need to do anything while that runs, or is this just a brief wait before the conversation picks back up?",
    # 02660 Vercel Edge Functions for geo redirects, Node SSR stays
    "Vercel is running two different runtimes in front of the app. Which runtime handles geolocation-aware redirects, and which one was kept for the heavy SSR routes because the Node surface was still needed?",
    # 02661 CloudFront Functions replaced Lambda@Edge for viewer request
    "Viewer-request header rewrites used to run on Lambda@Edge. Which lighter AWS edge service replaced it there, and what made it faster in practice given there was no Node boot cost to pay?",
    # 02662 Netlify Edge Functions on Deno replaced Express middleware
    "The auth cookie check moved out of an Express middleware. Which edge runtime on Deno absorbed it, and what did cold start look like before and after the swap on that path?",
    # 02663 Deno Deploy isolates for RSS
    "The blog's RSS transform needed to stay synchronous behind the CDN. Which isolate platform runs it, and what did its sub-5-millisecond boot time let the route keep in the request flow?",
    # 02664 Bun against Workers compatibility
    "We tested Bun against Workers compatibility earlier. Which Bun API did not map cleanly to the fetch handler model, and which node shim did make it through the initial compatibility pass?",
    # 02665 Fermyon Spin replaced Traefik rules
    "WASM microservices on the self-hosted cluster needed their own routing. Which platform shipped them, and what configuration file replaced the old Traefik rules file for routing between components?",
    # 02666 Fastly H2O reference for HTTP/2 tuning
    "The static site's HTTP/2 settings have a specific reference behind them. Which documentation guides the tuning, and what specific feature did we leave disabled because the CDN hit ratio lost more than it gained?",
    # 02667 Accept-Language cache key lifts HIT ratio
    "CDN HIT ratio jumped within an hour after a small cache-key tweak. Which header was added to the cache key after the geo-routing change, and roughly how far did the ratio rise once it was deployed?",
    # 02668 stale-while-revalidate over TTL bumps
    "Aggressive TTL extensions used to be our answer to origin brownouts. Which caching pattern replaced that approach, and what behaviour does it give users during origin hiccups instead of a cold error page?",
    # 02669 Soft purge preferred on Fastly
    "Blog releases used to cause a MISS stampede at the edge. Which purge mode did we prefer on the Fastly tier to avoid that, and what did users actually see during the propagation window?",
    # 02670 Logpush-to-Grafana caught bad Vary header
    "A cache HIT ratio regression was spotted from metrics rather than user reports. Which log pipeline feeds Cloudflare data into Grafana, and which broken response header did the per-path dashboard surface within twenty minutes?",
    # 02671 APAC pop replication lag on Cloudflare
    "The release hit a rough patch on the Cloudflare CDN in Asia-Pacific. Which operational property of purge propagation bit us, and how many pops was that eventual-consistency window spanning in practice?",
    # 02672 Fastly origin shield collapses connections
    "Our origin was seeing 4000 concurrent connections at steady state. Which Fastly pattern was introduced in front of it, and roughly how far did the connection count fall once that single-pop fan-in was in place?",
    # 02673 Bunny CDN anycast vs GeoDNS
    "A new CDN region needed faster failover than DNS could offer. Which routing model on Bunny CDN beat DNS-based steering on GeoDNS, and what did that change let us skip during failover?",
    # 02674 Argo Smart Routing saves 40ms transatlantic
    "Transatlantic tail latency was pulled down earlier this year. Which routing service trimmed 40 ms from the path, and what did its backbone preference weigh besides raw hop count?",
    # 02675 CloudWatch Events warm ping
    "Our first attempt at beating Lambda cold starts was a scheduled ping. Which AWS service fired that ping, and how often did it run to keep the container provisioned under the AWS heuristics?",
    # 02676 Lambda SnapStart replaced warmup ping for Java
    "The Java auth Lambda had a scheduled warmup hack wrapped around it. Which AWS feature replaced that ping, and roughly how much did cold start drop once the snapshot-restore flow took over?",
    # 02677 Azure Functions Premium for SAP endpoint
    "The SAP integration endpoint has a strict five-second cold start SLA. Which Azure Functions plan is covering that endpoint now, and why did the consumption plan fall short on the same path?",
    # 02678 Cloud Run min-instances bumped for checkout
    "Monday ramp on the checkout service was pushing tail latency around. Which Cloud Run setting was nudged upward, and what did p99 look like after the change once the ramp hit again?",
    # 02679 Provisioned concurrency rejected for batch API
    "We considered provisioned concurrency on Lambda for the batch API. Why did we end up rejecting it, and what property of the traffic shape made the flat-rate hold not pencil out financially?",
    # 02680 Knative on GKE for video pipeline
    "The event-driven video pipeline needed scale-to-zero without per-request billing pain. Which serverless container platform on GKE runs it today, and what did we avoid from the Cloud Run billing model by going that direction?",
    # 02681 AWS App Runner for admin dashboard
    "The internal admin dashboard used to ride on Fargate behind an ALB. Which AWS container service took over, and which two operational features tipped the comparison on ops effort for that workload?",
    # 02682 Fly.io absorbs WebSockets from Vercel Edge
    "The live-cursor feature needs long-lived WebSocket connections. Which platform hosts that traffic now, and which Vercel runtime ran into WebSocket limits that forced the split in the first place?",
    # 02683 noise resolver propagating
    "The other side just said the resolver's still propagating and to hang on. Is this something I should dig into, or is it a routine pause I can just wait out before continuing?",
    # 02684 SSE fan-out on Durable Objects
    "We needed to fan server-sent events out per room without hammering origin. Which edge primitive is multiplexing subscribers, and what pattern does it apply so each message reaches every subscriber without origin load?",
    # 02685 Realtime Logs replaced batched Logpush
    "Incident response was slowed by batched log delivery earlier this year. Which Cloudflare log feed replaced the Logpush pipeline for that path, and roughly how much did mean time to first log drop?",
    # 02686 OpenTelemetry on Workers to Honeycomb
    "Edge spans now sit next to origin spans in our observability stack. Which framework was enabled on Workers for that, and which backend ends up receiving both the edge and origin traces together?",
    # 02687 Frankfurt-only routing for EU under GDPR
    "EU payload traffic can't transit a US pop even briefly. Which location is the traffic now pinned to, and what specific regulatory requirement was behind the tightened locality rule?",
    # 02688 Cloudflare Regional Services preferred over DIY
    "We preferred a managed offering over writing geofencing ourselves. Which Cloudflare product absorbed that responsibility, and what cryptographic guarantee does it ship so keys are provably held in the chosen jurisdiction?",
    # 02689 Pages Functions + D1 binding for signup
    "The signup form's write path is now fully inside one edge request. Which Cloudflare Pages feature runs the action, and what binding to the edge SQL database keeps the write from hopping to origin?",
    # 02690 Wrangler replaced Serverless Framework
    "The Workers project moved off the framework it was originally scaffolded with. Which CLI replaced the Serverless Framework, and what about its typed bindings and live tail flow made it a better fit for the monorepo?",
    # 02691 SST preferred over raw CDK
    "Our edge-plus-origin stack on AWS could have lived on raw CDK. Which framework did we prefer instead, and which two edge constructs in particular did it keep consistent across the stack?",
    # 02692 Workers AI for spam classifier
    "The spam classifier doesn't need to call back to the central GPU pool. Which edge inference service runs it, and roughly how large is the model and what latency does it hit in that configuration?",
    # 02693 Cloudflare Queues for webhook retries
    "Webhook retries were bumping up against a hard CPU limit inside the Worker. Which Cloudflare service took the retry traffic off the Worker path, and what backoff-window constraint was the underlying reason for the split?",
    # 02694 Vercel KV on Upstash Redis for rate limits
    "Rate-limit counters at the edge needed a shared store. Which Vercel offering holds them, which Redis provider does it sit on top of, and which limiting algorithm did we end up preferring on spikes?",
    # 02695 Upstash QStash replaced Sidekiq crons
    "Serverless cron jobs used to run on a self-hosted Sidekiq. Which HTTP-native scheduler replaced that, and what property of the new scheduler made it a cleaner fit for the Workers runtime specifically?",
    # 02696 Lambda function URLs replaced API Gateway
    "A single-endpoint webhook didn't need the full API Gateway surface. Which AWS Lambda exposure path replaced it, and what authorizer mechanism did we manage to keep even after dropping Gateway?",
    # 02697 Fly Machines scale-to-zero review apps
    "Review apps used to cost real money even when idle. Which Fly primitive lets them scale to zero, and what behaviour on first request keeps latency acceptable once developers come back to the app?",
    # 02698 Workerd replaced miniflare
    "Local development on the Workers project recently changed runtimes. Which local runtime replaced miniflare, and what class of bug around fetch caching did the move to production-parity tooling catch early?",
    # 02699 Edge rate-limiting rollout 2026-03-22
    "Edge rate-limiting went live fleet-wide earlier this year. When did that rollout happen across the Workers fleet, and roughly what percentage of abuse traffic did the token-bucket plus Durable Object shard keep off origin?",
    # 02700 Diátaxis restructuring of handbook
    "Our handbook was a mess of mixed task and concept pages. Which documentation framework drove the restructuring, and which four section types did the old content get split into as part of the rewrite?",
]


def emit() -> int:
    assert len(QUERIES) == 100, f"expected 100 queries, got {len(QUERIES)}"
    with SHARED.open("r", encoding="utf-8") as f:
        shared_lines = f.readlines()
    positives = [json.loads(l) for l in shared_lines[SHARED_OFFSET:SHARED_OFFSET + 100]]
    assert len(positives) == 100, f"expected 100 positives, got {len(positives)}"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (query, pos) in enumerate(zip(QUERIES, positives), start=1):
            row_id = f"ret-{ID_OFFSET + i:05d}"
            row = {
                "id": row_id,
                "source_id": pos["id"],
                "query": query,
                "positive": pos["text"],
                "query_kind": QUERY_KIND,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
