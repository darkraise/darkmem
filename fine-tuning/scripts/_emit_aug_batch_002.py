"""One-off emitter for retrieval aug batch-002 — paraphrase kind, architecture sources.

Reads data/v2/retrieval/aug_sources/aug_002.jsonl (150 rows) and writes
data/v2/retrieval/aug_002.tmp.jsonl with ids ret-03251..ret-03400.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "v2" / "retrieval" / "aug_sources" / "aug_002.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "aug_002.tmp.jsonl"
QUERY_KIND = "paraphrase"

# One query per source row, in the same order as the source file.
QUERIES: list[str] = [
    # 001: FreshRSS VPS feeding Fiery reader with morning news + HN
    "which self-hosted backend supplies the Fiery reader's headlines",
    # 002: CMIP6 coordinates climate models for IPCC
    "protocol aligning global climate modelling groups for IPCC work",
    # 003: improves-on ADR relation keeps older doc accepted with successor link
    "how additive ADR updates relate to the earlier decision record",
    # 004: Parquet Bloom filter page enabled for point-lookup columns
    "columnar storage trick speeding point lookups with tight false-positive rates",
    # 005: LG C2 + Harmony Night-In activity maps orange button to Kodi
    "why Kodi launches a single Harmony press away on the living-room TV",
    # 006: New Relic One unifying Swift + Node tracing
    "observability product tying mobile and backend spans without custom glue",
    # 007: VictoriaLogs joins VictoriaMetrics using shared label model
    "logging engine that reuses the metrics stack's label semantics",
    # 008: pip-compile with --generate-hashes from requirements.in
    "deterministic Python dependency pinning with hashed transitive deps",
    # 009: Ark UI primitives shared between Vue admin and React marketing
    "cross-framework widget library giving Vue and React the same behaviour",
    # 010: OpenRA via single Bottles prefix for Linux Red Alert nights
    "how a compatibility wrapper lets OpenRA launch natively on Linux",
    # 011: Furbo webhook dims Hue via Home Assistant for dog reactivity
    "smart-home chain calming the crated dog when barking is detected",
    # 012: Sunday journal holds weekly Screen Time numbers
    "where four-number phone usage summaries get captured each week",
    # 013: February career narrative, five years, three decision points
    "structure of the long-range career roadmap drafted earlier this year",
    # 014: Hue strip dims when the Denon DP-300F spins
    "automation tying vinyl playback to accent lighting behind the turntable",
    # 015: SPIFFE workload API injects short-lived SVIDs via unix socket
    "identity framework delivering ephemeral certs to pods without disk writes",
    # 016: Yjs CRDT kept concurrent doc edits conflict-free without central server
    "library handling concurrent text edits without a coordinating authority",
    # 017: AnyList populated from Mealie recipe tags
    "how the grocery app gets fed automatically from recipe metadata",
    # 018: Sunday couples check-in, three prompts, 30-minute cap
    "format and timing of the weekly relationship review with tea",
    # 019: JuiceFS over S3 giving POSIX to PyTorch DataLoader
    "bridge giving object storage POSIX semantics for ML training loaders",
    # 020: Aloe Care Smart Hub with ceiling radar fall detection
    "which sensor handles fall detection in mom's condo given her aversion to wearables",
    # 021: Neo4j GDS PageRank nightly + Louvain for recommendations
    "graph algorithms driving nightly citation ranking and community buckets",
    # 022: Tokio 8-worker multi-thread + LocalSet for websocket !Send handle
    "runtime configuration pinning websocket state to a single thread",
    # 023: USE metrics emitted from runtime hooks, scraped every 15s
    "monitoring model and cadence for the worker pool health signals",
    # 024: Ambient mesh waypoint proxies opt-in per namespace for L7
    "service-mesh pattern keeping log shippers on the cheap L4 path",
    # 025: hmac.compare_digest everywhere after webhook timing leak
    "library call replacing equality checks on webhook signatures",
    # 026: £22 per head supper-club pricing, surplus rolls forward
    "per-guest cost arrangement for the themed dinner evenings",
    # 027: Polly .NET timeout -> retry -> circuit-breaker order
    "policy ordering around the .NET checkout resilience stack",
    # 028: Songkick merged into Google Calendar via IFTTT on 2026-03-05
    "how gig listings appear inside the main calendar alongside work",
    # 029: Outbox relay sidecar tailing logical replication into Kafka
    "at-least-once delivery without dual-writes between Postgres and Kafka",
    # 030: Syft generating SPDX + CycloneDX attestations in OCI registry
    "where per-image SBOM attestations are stored after build",
    # 031: Flink windowed sessionization with 30-min event-time gap
    "how mobile click streams get sessionised despite late arrivals",
    # 032: £2,500 Amex Savings floor, sweeps to Wealthfront on the 25th
    "rule moving spare checking-account cash into higher-yield savings",
    # 033: Risk-tier labels determine PR review rigor
    "how PR review requirements scale with the change's risk rating",
    # 034: Hyper Island diploma Stockholm Aug 2026 - Jun 2027
    "dates and location of the upcoming data-strategist diploma programme",
    # 035: Doc-link tool call required before any new import generation
    "guardrail preventing the agent from inventing third-party imports",
    # 036: Required checks codified in yaml beside CODEOWNERS
    "moving required-status-check config out of repo settings clicks",
    # 037: Two books for Maya, one Narnia chapter for Leo, 8:15pm lights out
    "household bedtime reading routine for the two kids",
    # 038: Atlassian design system tokens in confluence-plugin package
    "why the Confluence plugin's buttons visually match the host platform",
    # 039: Langfuse traces feed autoscaler backpressure
    "observability layer supplying cost signals to the LLM autoscaler",
    # 040: Acapella iOS app records quartet to iCloud for Logic mixdown
    "multitracking workflow feeding the weekend barbershop mixes",
    # 041: Cassandra composite clustering with bucketed time prefix
    "schema change that kept Cassandra tombstone scans under control",
    # 042: AirTag in Oliver's backpack pings HomePod mini
    "locator setup alerting the kitchen speaker when a child's bag goes missing",
    # 043: PR preview URLs via Vercel, bot posts link on green build
    "per-PR preview environments surfaced through a bot comment",
    # 044: Daycare rota Mon/Wed Little Acorns, Tue/Thu Nana, Fri home
    "weekly caregiver split for the young child",
    # 045: Rails initializers wire ldclient-rb with per-env SDK keys
    "how feature-flag SDK keys stay environment-scoped in the Ruby apps",
    # 046: Spark batch migrated to Kubernetes with Yunikorn scheduling
    "scheduler chosen to share a cluster between streaming and batch Spark",
    # 047: Airtable shares Khan Academy progress with grandma in Lisbon
    "how the cousin's calculus streak reaches a remote family member",
    # 048: KServe InferenceService with traffic-percentage canary splits
    "Kubernetes-native way the team rolls out scoring model canaries",
    # 049: Home Assistant cuts dryer below 2 kW solar via Emporia Vue
    "automation turning off appliances when solar generation dips",
    # 050: Triton ensemble pipelines reranker behind generator
    "inference server chaining a reranker after a generator in one call",
    # 051: 2026-11-14 hospice chapel then pier walk with dad's thermos
    "planned observance for the annual remembrance date",
    # 052: TeamSnap plus Python Parks permit sync for Newton Rec league
    "tooling mix running the neighbourhood basketball league logistics",
    # 053: Rill Data with DuckDB local slicing under 200ms
    "dashboard tool keeping the CEO's live revenue view snappy",
    # 054: Splitwise daily, monthly settle to joint Chase account
    "cadence for reconciling shared expenses with Maya",
    # 055: Helm under Argo CD, values.yaml per environment across 4 clusters
    "packaging used for app deployment beneath GitOps reconciliation",
    # 056: Caddy autocert + Cloudflare DNS-01, no port 80 exposure
    "how public dashboards get TLS certs without opening HTTP on the bastion",
    # 057: Services take a settings object at construction for tests
    "construction pattern letting tests swap service configuration",
    # 058: Great Expectations gates dbt runs on core facts
    "data-quality gating that blocks mart builds when facts fail",
    # 059: Pokemon ROM hacks in separate EmulationStation collection for 9yo
    "how age-appropriate game builds stay partitioned from the rest",
    # 060: Flyte with typed task signatures and container caching
    "orchestrator selected over Airflow KubernetesPodOperator for ML DAGs",
    # 061: Confluent Schema Registry enforcing Avro compat at publish
    "registry catching incompatible Avro changes before consumers see them",
    # 062: SSE envelope with type/seq enables Last-Event-Id replay
    "streaming envelope fields enabling exact-gap reconnect replay",
    # 063: 45-minute Lombard commute repurposed as audiobook time
    "reframing that turned the daily drive into a highlight of the day",
    # 064: Proxmox mixing LXC and KVM on same node
    "hypervisor running containers and full VMs side by side on one host",
    # 065: 05:40 water, mobility, espresso before screens
    "sequence opening the early-morning routine before any device",
    # 066: SDK golden-diff check versus prior minor for semver enforcement
    "release gate blocking accidental SDK breaking changes",
    # 067: Airflow deferrable operators with 5000 waits in triggerer
    "Airflow feature unpinning worker slots for long sensor waits",
    # 068: MLIR split into three dialects from frontend to vendor backend
    "compiler IR restructured into layered dialects for clarity",
    # 069: CareZone for meds, Google Calendar for appointment SMS to aunt
    "tool split between medication tracking and reminder delivery for mom",
    # 070: Phone-off Friday board games until nine
    "weekly family evening rule that removes screens",
    # 071: Everplans vault with POA, living will, HIPAA for dad
    "where critical caregiving documents sit for rapid sharing with a hospital",
    # 072: Immich on basement NAS replacing Google Photos
    "self-hosted replacement chosen for the family photo sharing pipeline",
    # 073: Istio ingress + sidecar proxies for east-west mTLS
    "mesh topology terminating public TLS and encrypting internal hops",
    # 074: Outback boot: Car-Camp, Dog, Tools boxes prevent kit drift
    "car storage scheme stopping motorbike gear from mixing with camp kit",
    # 075: Billing consumes Kafka, ClickHouse per-tenant, nightly invoices
    "pipeline from usage events to tenant invoices",
    # 076: Multi-step form fieldset/legend + aria-live polite for VoiceOver
    "accessibility changes announcing wizard step transitions to screen readers",
    # 077: 20 min sit, walk the lane, then laptop
    "retreat-origin protocol replacing the phone-first morning",
    # 078: Gelato on Shopify POD beating Etsy's native rate for Rosa
    "print-on-demand choice preserving margin on small tote runs",
    # 079: Command pattern undo/redo stack with do/undo pairs
    "state pattern powering editor time travel through action pairs",
    # 080: Insight Timer, Plum Village, no-app Friday rotation
    "weekly cycling schedule across meditation apps plus an offline day",
    # 081: Four garage zones: car, bike, pegboard, tyre rack
    "layout partitioning the garage for car, bike, tools, and tyres",
    # 082: Lunch Money categorises Priyanka freelance invoices
    "app keeping freelance income tagged for the 2026 household taxes",
    # 083: Aftership iOS widget shows Shopify merchant hop first
    "widget surfacing the early-stage merchant handoff ahead of carrier scans",
    # 084: LHC 27km superconducting proton ring replacing LEP in 2008
    "the underground ring that took over the LEP tunnel at CERN",
    # 085: Ramadan 2026-02-18 start, iftar at Masjid Al-Noor Fridays
    "fasting-month schedule and where Friday breaks are shared",
    # 086: Hiking crew thread uses boot/mountain/sleeping-bag reactions only
    "three-emoji voting scheme for the seven-person trip chat",
    # 087: Memcached add-with-expiration 1s negative cache dampens retries
    "caching trick that throttles origin retries without poisoning next fetch",
    # 088: Dinner seating: Priya right, Dev across from Osman
    "fixed arrangement keeping the architecture conversation flowing at dinner",
    # 089: Knapsack MDX docs embed Storybook iframes per page
    "docs site giving API descriptions and live component demos together",
    # 090: DOMPurify after locale formatting to protect RTL bidi
    "sanitisation ordering that keeps bidirectional layout intact",
    # 091: CERN LHC 27km synchrotron of superconducting magnets, Franco-Swiss
    "underground accelerator spanning the border between France and Switzerland",
    # 092: Charitable giving 5% gross, DAF bunched biennially
    "giving strategy alternating heavy DAF contributions with lean years",
    # 093: ADR proposed -> accepted after PR approve + 48h silence
    "promotion criteria moving a decision record to accepted status",
    # 094: XState idle/visible/dismissing for toast with exit animation
    "state machine coordinating toast lifecycle including dismissal animation",
    # 095: ArgoCD ApplicationSet git generator per tenant folder
    "how onboarding a tenant reduces to a single directory commit",
    # 096: MessagePack halved payload size for mobile clients
    "serialisation that kept schemaless payloads small over mobile links",
    # 097: boto3 per-tenant AssumeRole least privilege base credentials
    "AWS credential pattern isolating job-runner tenants with role assumption",
    # 098: Stanpit Park 1.4km gravel walking meditation loop
    "route and posture for the park-based walking meditation practice",
    # 099: SDK tiers stable/preview/experimental, _preview subpackage
    "how experimental SDK surfaces signal instability to consumers",
    # 100: pnpm workspaces + Turborepo + changesets
    "monorepo toolkit covering workspaces, caching, and package versioning",
    # 101: Doctest executes fenced python blocks in SDK docs across versions
    "CI step keeping documentation code examples from silently rotting",
    # 102: Backdoor Roth January $7,000 Schwab routine
    "yearly contribution-then-convert move executed at Schwab each January",
    # 103: 21:00 paperback + chamomile armchair reading hour
    "evening wind-down ritual that excludes phones and screens",
    # 104: Templater JS hooks pull weather + calendar at note-open time
    "Obsidian plugin fetching live data into daily notes at open time",
    # 105: HackRF One GQRX on 40m band Saturdays
    "Saturday hobby combining software-defined radio hardware with a receiver app",
    # 106: Prometheus remote_write into Mimir for long-term multi-tenant metrics
    "long-term metrics backend chosen at the cost of a bigger ingester fleet",
    # 107: INCLUDE covering indexes took heap fetches to zero on Postgres 15
    "index feature eliminating heap visits for a reporting query",
    # 108: Normalised notifications slice by id + byId map
    "store shape replacing the O(n) nested toast array",
    # 109: Airflow nightly dbt materialising marts in BigQuery
    "scheduler driving the overnight analytics materialisation",
    # 110: 20-min Beaulieu Gardens walk at 15:00 Fridays alone
    "Friday afternoon reset walk done solo on a fixed loop",
    # 111: Dynatrace OneAgent auto-discovery on 400-host legacy estate
    "APM tool picking up Oracle and MQ dependencies without exporter work",
    # 112: Yearly 2026-09-14 relationship audit, three worked, two not, one new
    "anniversary review ritual Clara and I run each September",
    # 113: Read-only Instagram: signed out of app, web login, muted stories
    "approach that kept Instagram access while cutting its pull",
    # 114: Google Calendar feeds Echo Show 8 hallway piano reminders
    "announcer surfacing piano practice before the school bus",
    # 115: Saturday 6am community pool swim before kids wake
    "early Saturday exercise slot happening before family wake-up",
    # 116: Runbooks fixed schema symptom/scope/diagnosis/mitigation/follow-up
    "template fields on-call engineers fill when drafting a runbook",
    # 117: BVH rebuild on compute queue parallel to gbuffer, 0.6ms budget
    "how the renderer keeps BVH rebuilds off the graphics critical path",
    # 118: CloudWatch Events keep-alive ping every 4 minutes for cold starts
    "scheduler trick keeping Lambda containers warm under AWS heuristics",
    # 119: Glowforge Pro handles 2026-04-12 birthday card inserts over Cricut
    "machine chosen for delicate cotton paper card inserts in the makerspace",
    # 120: Rent year one, buy by year three, £620/month deposit savings
    "three-year plan comparing renting against buying with monthly savings",
    # 121: Bitmask per-component delta snapshots, full snapshot only for joins
    "networking trick limiting full-state snapshots to new peers joining",
    # 122: Unpackerr replaces manual RARBG nested archive extraction
    "automation bridging German nested archives into Sonarr imports",
    # 123: Helicone proxies OpenAI for cost attribution via session header
    "proxy capturing per-user OpenAI spend through injected headers",
    # 124: Bayesian brain generalises predictive coding as posterior inference
    "cognitive theory framing perception as inference over sensory causes",
    # 125: XFetch probabilistic early expiration keeps hot keys warm
    "algorithm refreshing popular cache entries before their TTL expires",
    # 126: Petcube Play 2 feeds Cattime via webhook JSON
    "webhook chain sending cat playtime minutes into the weight-trend chart",
    # 127: Tulips October-April, dahlias May in front borders
    "seasonal rotation between tulips and dahlias in the front bed",
    # 128: chezmoi-managed dotfiles + shell + Python utilities
    "tool keeping dotfiles and personal scripts under one managed repo",
    # 129: devpi homelab PyPI mirror for restricted-network CI
    "private PyPI mirror feeding air-gapped CI runners nightly",
    # 130: Inception before ADR, design before implementation, never merged
    "two design-review checkpoints the team refuses to collapse",
    # 131: Tasmota Sonoff MQTT espresso warmup for kitchen dashboard
    "smart plug reporting espresso machine warm-up into MQTT",
    # 132: Stream Deck page for Amelie's game-night OBS scene swaps
    "hardware control surface letting OBS scenes swap with one tap",
    # 133: SOURCE_DATE_EPOCH through Debian/Nix/npm, diffoscope clean
    "environment variable eliminating timestamp-only differences in builds",
    # 134: Syft CycloneDX JSON attached + signed on GitHub releases
    "SBOM artefact attached next to each signed release binary",
    # 135: Hedge requests fire duplicate after p99, cancel loser via WithCancel
    "tail-latency strategy firing a duplicate call once p99 elapses",
    # 136: PostHog flags for experiments; ConfigCat for plain toggles
    "flag-tool split between experimentation and simple toggles",
    # 137: Fulcio keyless signing with OIDC, Rekor logs rollbacks
    "signing chain issuing ephemeral certs tied to OIDC identities",
    # 138: Idris elaborator reflection generates JSON codec at type-check
    "how the library avoided a separate derivation macro for JSON codecs",
    # 139: Medisafe + Omron 7 Series caught creeping systolic trend
    "health app that surfaced the BP trend the doctor missed",
    # 140: Sam gift tradition: one experience, one handmade, since 2021
    "rule governing the annual gift exchange with Sam",
    # 141: Polar H10 GPX into Komoot for Mallorca turn-by-turn on Garmin
    "data handoff giving the Garmin better turn cues than the Polar watch",
    # 142: 2026-04-07 poll worker shifts in shared colour-coded Google Calendar
    "calendar layout tracking precinct assignments for the spring primary",
    # 143: JUnit 4 -> 5 incremental via vintage engine, removed year later
    "engine that let the test migration happen gradually before cleanup",
    # 144: BroadcastChannel API cross-tab settings with last-write-wins
    "browser API syncing preference edits between open tabs",
    # 145: Ports-and-adapters: services call repositories wrapping drivers
    "layering convention for how backend services reach the database",
    # 146: Hetzner git vault pushed via Obsidian Git every 15 minutes
    "backup cadence that saved every note through the March laptop failure",
    # 147: AWS CDK Python L3 constructs for VPC + EKS bundling IAM/SG
    "IaC choice bundling IAM and security defaults into reusable constructs",
    # 148: ldap3 escape_filter_chars + escape_rdn for LDAP injection safety
    "functions protecting LDAP filter and dn paths from injection",
    # 149: Calibre-Web on Unraid 192.168.1.42 streams to Kobo Clara
    "home server streaming the family ebook library to the kids' e-readers",
    # 150: SOPS + AWS KMS for prod, age keys as offline break-glass
    "secret management split between KMS-backed prod and offline age fallback",
]


def emit() -> int:
    with SRC.open("r", encoding="utf-8") as f:
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
