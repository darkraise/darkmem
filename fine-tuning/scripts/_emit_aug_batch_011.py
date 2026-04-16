"""One-off emitter for retrieval aug batch-011 - multi-sentence queries.

Each row pairs a paragraph-shaped query (2-4 sentences, 20-60 words) with its
pre-picked source passage as the positive. Queries simulate a careful user
asking design-discovery questions about structure, layering, integration, and
ownership.

Reads data/v2/retrieval/aug_sources/aug_011.jsonl and writes 100 rows to
data/v2/retrieval/aug_011.tmp.jsonl with ids ret-04801..04900 (using new_id
from each source row).
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "v2" / "retrieval" / "aug_sources" / "aug_011.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "aug_011.tmp.jsonl"
QUERY_KIND = "multi-sentence"

# 100 multi-sentence queries, aligned in order with aug_011.jsonl rows 1..100.
QUERIES: list[str] = [
    # 04801 Vespa personalized news feed + tensor ranking
    "I'm onboarding onto the personalized news feed stack. Which engine handled serving at scale, and how did the ranking phase avoid a separate feature-blending sidecar? I want to understand where tensor work actually happens.",
    # 04802 2FA TOTP + 10 Argon2-hashed recovery codes
    "A new hire asked me to explain our 2FA shape. What factors are enrolled, how many recovery codes do users get, and what's the server-side storage format for those backups?",
    # 04803 R Markdown Polar HR export to PDF physiology journal
    "Someone asked me how the weekly training report reaches our coach. What toolchain turns the Polar heart-rate export into a PDF, and when does the mail actually go out?",
    # 04804 dbt Core state-based selection CI rebuild
    "I'm onboarding and need to understand how our warehouse transformations flow. Which tool compiles the models into dialect-specific SQL, and how does CI decide what to rebuild on each change?",
    # 04805 CAA pinned to Let's Encrypt + BuyPass
    "I'm auditing our certificate-issuance posture on the apex domain. Which CAs are allowed to issue, and what attack path does that pinning specifically shut down even when domain-control checks get social-engineered?",
    # 04806 Style Dictionary tokens to CSS, Swift, Android XML
    "I'm trying to understand how our design tokens propagate to three platforms. Which tool handles the pipeline, where do the source files live, and what outputs does a single pnpm run produce?",
    # 04807 direnv per-repo .envrc + use_flake Nix
    "A teammate asked why our shell rc files are so clean. Which tool scopes secrets per repository, and how does it integrate with Nix dev shells without manual sourcing?",
    # 04808 tsan/ubsan nightly Bazel, asan excluded from release
    "Someone asked how our sanitizer coverage is structured. Which sanitizers run nightly, on what build config, and why does asan not make it into the release pipeline?",
    # 04809 Pa11y CI staging per deploy, zero errors threshold
    "I'm mapping our accessibility gates. Which tool runs against staging on each deploy, where does the report land, and how tight is the pass threshold currently set?",
    # 04810 Coffee rule no espresso after 14:00
    "A friend asked how I avoid travel jet lag blowups. What coffee rule do I follow on the road, and where did that particular habit come from?",
    # 04811 Scientific method cycle
    "I'm reviewing the epistemology primer for the intro chapter. What phases does the scientific method cycle through in its canonical form, and how does it connect observation to revision?",
    # 04812 Great Expectations YAML + Airflow landing zone
    "I'm onboarding into our data-quality story. Which tool guards the landing-zone contracts, where are the expectations authored, and what orchestrator actually gates loads into the raw schema?",
    # 04813 Docker user namespace remap UID 100000 CI hosts
    "Someone asked why our CI host escapes aren't catastrophic. What Docker daemon feature is enabled on the shared hosts, which host UID does container root map to, and what's the security payoff?",
    # 04814 Sunday 16:00-19:00 self-care block
    "A friend wanted to understand my Sunday routine. When does the self-care block run, what's on the agenda inside it, and how strict am I about calendar invites during that window?",
    # 04815 Playwright RTL matrix ar/he screenshot diff
    "I need to understand how right-to-left reviews actually land. Which tool runs the locale matrix, which locales does it exercise, and what gates the PR before translators see it?",
    # 04816 Prometheus exemplars to Tempo span
    "Someone asked me how histogram buckets jump to traces in our observability stack. Which feature wires Prometheus to Tempo, and what does a single click on a slow bucket actually resolve to?",
    # 04817 Rubin potential outcomes framework 1970s
    "I'm prepping a short on causal-inference history for a journal club. Who developed the potential outcomes framework, roughly when, and what did it shift away from in the prior paradigm?",
    # 04818 Rootless containers /etc/subuid 65536 range
    "I'm setting up rootless containers and trying to understand the UID mapping. How do user namespaces remap UID 0 on the host, and what subuid range is sized to cover typical image needs?",
    # 04819 CSS logical properties + html dir attribute
    "Someone asked how we actually ship RTL layouts. Which HTML attribute toggles direction, which CSS properties replaced hard-coded left/right values, and what cleanup was done to the design tokens?",
    # 04820 Glimcher neuroeconomics basal-ganglia TD dopamine
    "I'm tracing the link between reinforcement learning and real brains. Whose neuroeconomics work extended the temporal-difference dopamine account, and what structure does the model assign to prediction error?",
    # 04821 Hudi merge-on-read Avro delta + Parquet base
    "I'm onboarding into our lakehouse ingestion layer. Which Hudi table type sits underneath the near-real-time feeds, and how does the delta-log layout avoid repeated Parquet rewrites?",
    # 04822 Karpathy YouTube lectures before bed
    "Someone asked how I keep up with neural network fundamentals casually. What lecture series do I watch, on which platform, and when during the week does that usually happen?",
    # 04823 Cornwall road-trip prep Outback service + tyres
    "A friend asked how I prepped the Outback for the Cornwall run. What service, tyres, and weather test did I line up before the 2026-04-19 departure?",
    # 04824 Descheduler + Karpenter topology spread
    "I'm onboarding onto our Kubernetes fleet hygiene. What role does the Descheduler play after the initial scheduling happens, and how does it pair with Karpenter in practice?",
    # 04825 Red Hat Satellite RHEL patch baseline 300 hosts
    "Someone asked how we keep RHEL hosts in lockstep on patches. Which product provisions the baseline, how are errata pinned, and roughly how many hosts does the monthly CVE batch land on?",
    # 04826 pre-commit config ruff mypy parity with CI
    "I'm onboarding and want to know why my laptop runs reproduce CI failures so exactly. Where do the pre-commit hooks live, and which checks mirror what CI runs upstream?",
    # 04827 Strangler fig Kong billing extraction
    "Someone asked how the billing service was carved out of the monolith. Which proxy layer hosted the strangler-fig cutover, at what traffic increment per week, and what safety mechanism sat on the header?",
    # 04828 dill allowlisted deserialiser ingestion worker
    "I need to understand the fix we landed on the ingestion worker after last quarter's deserialisation vuln. What replaced the raw loader, and what does the allowlist actually constrain about incoming classes?",
    # 04829 USGS NEIC Golden Colorado ANSS catalogue
    "I'm writing a short on seismic data sources. Which USGS center runs the national catalogue, where is it located, and what network does it operate underneath modern hazard maps?",
    # 04830 HomeAssistant tesla_custom fleet telemetry 5min limit
    "A friend asked why my Home Assistant Tesla dashboard actually works live now. Which integration replaced the old polling approach, when did the swap happen, and what upstream constraint forced the change?",
    # 04831 Watchdog goroutines 90s streaming ingestor
    "I'm onboarding onto the streaming ingestor and want to know how stuck stages get handled. What wraps each long-running goroutine, what's the timeout, and what does the supervisor restart?",
    # 04832 TrolMaster Hydro-X + Titan CO2 PPFD ramp flower tent
    "Someone asked how my flower tent handles the CO2 plus PPFD ramp. Which controller runs the show, which module talks to the generator, and when did that build land?",
    # 04833 Plum wine preserver RFID into Vivino
    "A friend asked why I stopped using my Coravin daily. Which preserver replaced it at the counter, and how does its RFID bottle recognition get pours logged without a manual scan?",
    # 04834 Core Data v4-to-v5 custom migration mapping model
    "I'm debugging an iOS migration failure. When does Core Data skip the lightweight path, and which NSPersistentStoreDescription flag is being flipped to force the custom migration?",
    # 04835 Marvin cast_to Literal triage worker
    "I want to understand why the triage worker has almost no switch statements. Which library handles ad-hoc classification, and what return shape does its Literal cast produce so we skip the dispatch code?",
    # 04836 SNS fan-out to SQS branches retry archive analytics
    "I'm onboarding onto our billing pipeline. Which AWS messaging pattern branches events into retry, archive, and analytics subscribers, and what does that pattern buy us in terms of coupling?",
    # 04837 Retirement glidepath 2025 target 58 + 529 plans
    "A friend asked how I'm thinking about retirement timing. When did I start the glidepath spreadsheet, what's the target exit age, and how do the kids' college savings fit alongside it?",
    # 04838 Preview envs per-PR flag prefix CI patches context
    "Someone asked how reviewers test flag changes without polluting staging. What prefix convention do PR environments use, and how does CI wire that into the flag evaluation context?",
    # 04839 QGIS Cloud stormwater GIS layers neighbourhood
    "I need to explain how the neighbourhood association saw the stormwater layers. Which platform did I publish them on, and why did that setup let the meeting project maps without any desktop installs?",
    # 04840 Shield TV Pro Kodi DTS-HD MA bitstreaming Jellyfin
    "A friend asked why I haven't swapped the Shield TV Pro yet. Which codec path keeps working there that others break, and how does the Jellyfin for Kodi add-on treat the device?",
    # 04841 Traefik ACME DNS-01 Route53 wildcard
    "I'm onboarding onto the multi-tenant TLS story. Which proxy fronts ACME, which challenge type runs against Route53, and how does the wildcard cert avoid per-tenant pinning?",
    # 04842 Harbourside Library book club last Thursday
    "A friend asked how the book club runs. When and where does it meet, what's the fiction/non-fiction cadence, and who owns the March pick?",
    # 04843 Self-study board Spanish/Rome/piano 2026 Q2
    "Someone asked what I'm working on outside work this quarter. What three tracks are on the fridge board, and where exactly am I aiming to get to on each of them by end of Q2?",
    # 04844 Ollama Mac Studio Sunday journal summarisation
    "A friend asked how I keep the journal review manageable. Which runtime handles local summarisation, what hardware hosts it, and when does the run fire each week?",
    # 04845 ADR confidence tag revisit experiment
    "I'm onboarding into our architectural review process. Which confidence tags ride on each ADR, and what specifically does a low-confidence tag commit us to before the next quarter closes?",
    # 04846 Saturday dinner menu planning Wednesday three dishes
    "A friend asked how the Saturday dinner parties always feel calm. When does the menu get locked, and what's the three-dish structure that makes the day-of easy?",
    # 04847 Google Calendar feed into Outlook daycare pickups
    "Someone asked how my work calendar knows about daycare pickups. Which calendar is the source, which one consumes the feed, and whose schedule is actually showing up?",
    # 04848 Board game night six players dining table
    "A friend asked why our game nights cap where they do. How many players fit at the dining table, how many more at the kitchen island, and what determines the total?",
    # 04849 Sonos Era 300 Atmos + Play:1 announcements
    "Someone asked how our whole-home audio is actually split by role. Which speaker plays Atmos Music in the kitchen, which one covers announcements in the hallway, and what sources drive each?",
    # 04850 ABRP Denver-Moab 2 CCS stops manual 65 mph cap
    "I'm planning the 2026-05-24 Denver-to-Moab drive. Which planner did I trust over the in-car Tesla route, how many CCS stops did each pick, and what manual constraint drove the difference?",
    # 04851 Scrivener outline + iA Writer morning pages grayscale
    "Someone asked how my novel workflow avoids morning fiddling. Which tool holds the outline, which one handles daily morning pages, and what feature keeps me out of chapter-structure edits at 6am?",
    # 04852 /.well-known/api-capabilities SDK cache per base URL
    "I'm reviewing our SDK design. Which endpoint advertises enabled features, how does the SDK cache it, and for how long does that cached capability list stay valid in the running process?",
    # 04853 Azure Key Vault HSM FIPS 140-2 L2 payment webhook
    "Someone asked how the payment webhook's signing certificate is protected. Which service stores it, which tier is it on, and what compliance boundary does the private key never leave?",
    # 04854 Domain services pricing Order + PricingPolicy + TaxTable
    "I'm onboarding into the domain model and want to understand where multi-aggregate logic goes. What role do domain services play, and what inputs and output does the pricing example actually have?",
    # 04855 PackPoint base + Google Keep loaned crampons Patagonia
    "A friend asked about the Patagonia trek packing list. Which tool generated the base checklist, where did the custom gear list move to, and what specifically did the first tool fail to track?",
    # 04856 Obsidian Readwise plugin 6am Dataview daily journal
    "Someone asked how my book highlights flow into daily journaling. Which plugin pulls the Readwise highlights, when does that run, and what query rolls the month's quotes into the daily note automatically?",
    # 04857 Debezium Postgres CDC Kafka downstream consistency
    "I'm onboarding onto our change-propagation flow. Which tool streams Postgres changes into Kafka, and what does that let downstream services stop doing to stay consistent?",
    # 04858 AGENTS.md alongside CLAUDE.md Codex + Claude Code
    "Someone asked why this repo has two instruction files. Which file did I add alongside CLAUDE.md, which two agents read it, and what's the operating principle behind keeping both?",
    # 04859 Maven enforcer requireReleaseDeps snapshot ban
    "I'm onboarding onto the Maven release path. Which enforcer plugin rule runs only in the release profile, and what specifically does it ban from slipping into a release build?",
    # 04860 Open enum Unknown(str) wrapper SDK forward compat
    "Someone asked how our SDK survives new enum variants from the server. What does deserialisation do with unknown values, and what does that design prevent from happening on older clients?",
    # 04861 Doppler secrets Vercel scoped tokens
    "Someone asked how we handle secrets injection for the Vercel monorepo. Which tool runs the injection, and what did its scoped-token model offer over the old Heroku-style per-app config vars?",
    # 04862 Kafka + Flink fan-out Elasticsearch + S3
    "I'm onboarding onto the ingestion pipeline. Which queue receives raw events, which processing framework fans them out, and which two sinks end up consuming the output?",
    # 04863 CSP strict-dynamic SRI inline script removal
    "Someone asked what XSS class we closed off with CSP. Which directives are being enforced, what SRI goes with them, and what was the week-long cleanup that made it all work?",
    # 04864 NIH grant review study sections primary reviewers
    "I'm explaining the NIH grant review process to a new PI. What bodies evaluate applications, what role do primary reviewers play, and when in the cycle does their scoring drive discussion?",
    # 04865 Fulcio short-lived certs GitHub OIDC workflow run
    "Someone asked how we tie release provenance to a specific build. Which component issues the signing certificate, which identity is it bound to, and how does verification trace back to the exact workflow run?",
    # 04866 Multi-variate flag cart-layout 40/30/20/10 fallback
    "I'm reviewing how the cart-layout experiment is wired. How are the four variants weighted, which one is hard-coded as fallback, and what triggers the fallback to kick in?",
    # 04867 Newborn sleep 7pm bath feed swaddle naps 9/12/3
    "A friend asked how the newborn evenings run. What sequence leads into bedtime, what's the target lights-out window, and how are the daytime naps spaced?",
    # 04868 ICU select gender profile page
    "Someone asked how our profile page avoids broken gender agreement in translated strings. Which ICU construct is being used, which grammatical categories does it cover, and why not just stitch phrases together?",
    # 04869 Ada Lovelace DLSS 3.5 Ray Reconstruction OFA frame gen
    "I'm writing up the Ada Lovelace rendering story. Which DLSS path ran on those cards, and what role did OFA motion vectors play in the single-frame Frame Generation pipeline?",
    # 04870 GOAP + behavior tree stealth game
    "I'm onboarding onto the stealth game's AI. How does GOAP sit alongside the behaviour tree, which part computes the plan, and which part executes each action?",
    # 04871 Python contextvars OpenTelemetry asyncio span
    "Someone asked how spans propagate across asyncio tasks in our Python services. Which stdlib feature carries the current span, and what helper do we wrap around the OTel context.attach call?",
    # 04872 Design doc graveyard /docs/retired banner
    "I'm onboarding and noticed a do-not-use banner on an old design doc. Where do retired proposals live, how does search still surface them, and what keeps readers from trusting them?",
    # 04873 Guest kit 14 Pennant Mews towels USB-C pillows
    "A friend asked what's in the spare-room guest kit. What toiletries, electronics, pillow mix, and bedside comforts should be waiting for the overnight visitor at 14 Pennant Mews?",
    # 04874 Voicemeeter Banana Reaper monitor OBS streaming
    "Someone asked how I avoid ASIO latency doubling on the streaming PC. Which virtual mixer routes the Reaper monitor mix into OBS, and what problem does going through it instead of a single ASIO driver avoid?",
    # 04875 focus-trap-react modal opener restore
    "I'm onboarding into our accessibility implementation for modals. Which library runs the focus trap, what does it record on open, and where does focus land when the modal closes?",
    # 04876 Pi-hole Raspberry Pi 4 YouTube Kids Apple TV
    "A friend asked how our Apple TV stopped leaking ad domains into YouTube Kids. Which DNS-level blocker runs on what hardware, and where is it physically sitting in the house?",
    # 04877 Tech radar tied to ADR ids move assess to adopt
    "Someone asked why our tech radar has ADR ids on every card. What rule did I introduce about moving a technology from assess to adopt, and what does that rule disallow in its place?",
    # 04878 Semantic chunking + BM25 first stage 1.2M LOC
    "I'm onboarding onto the long-codebase assistant. How big is the Python service, what chunking strategy feeds retrieval, and why do pure embeddings need a BM25 first stage on cross-cutting changes?",
    # 04879 Docusaurus GraphQL plugin introspection CI
    "Someone asked how our GraphQL reference docs stay in sync with the schema. Which Docusaurus plugin do we use, when does introspection run, and what does schema drift look like in CI?",
    # 04880 Structured JSON structlog correlation_id gateway
    "I'm onboarding onto our logging story. Which library produces the structured JSON across services, and where does the correlation_id for tracing first get injected?",
    # 04881 Sery_Bot Twitch Celeste Python + Discord webhook VOD
    "A friend asked how my Friday Celeste streams are moderated. Which bot runs in chat, what custom handler is wired into it, and how do VOD clips surface in Discord afterwards?",
    # 04882 London Fields Lido 2 km Sunday swim
    "Someone asked about my Sunday wake-up routine. Where do I swim, how far, and what specifically does the outdoor water do for me compared to coffee?",
    # 04883 Scala cats recursion schemes typed FP
    "I'm reviewing a Scala codebase that leans heavily on recursion schemes. Which library implements them, what does it lean on for structure, and where does this fit on the typed functional programming spectrum?",
    # 04884 IODP 2013 JOIDES Resolution Chikyu mission-specific
    "I'm explaining scientific ocean drilling governance. Which program succeeded IODP's predecessor, when did it launch, and which drilling platforms does it now coordinate under one umbrella?",
    # 04885 Bristol to Lisbon Allied Van Lines 20-foot GBP4,800
    "A friend asked about the Bristol-to-Lisbon move logistics. Which mover handled the 20-foot container, what was the quoted price and transit time, and when was the door-to-door window?",
    # 04886 SQS standard at-least-once idempotent email fan-out
    "Someone asked why we didn't bother with exactly-once for email sending. Which queue type backs the fan-out, what delivery guarantee does it give, and what pattern in the handlers made that the cheaper choice?",
    # 04887 KMS envelope per-tenant DEK yearly KEK rotation
    "I'm onboarding onto the multi-tenant encryption model. How are DEKs wrapped, how often does the KEK in KMS rotate, and what triggers rotation of the tenant-level DEKs?",
    # 04888 Go Discord bot arXiv ML digest 8 AM
    "A friend asked how my paper-reading channel stays fed. What language is the Discord bot written in, what feed does it rotate, and when does it drop each morning?",
    # 04889 Saga over distributed tx Vernon aggregate boundary
    "Someone asked how cross-aggregate invariants are maintained in our domain. Which pattern replaces a distributed transaction, and what specific book quote is pinned in the module doc as the guiding principle?",
    # 04890 Readwise to Zotero Sunday thesis prep
    "A friend asked how my highlights and PDF annotations sit next to each other for thesis work. Which two tools are wired together, and when does the sync run each week?",
    # 04891 Sentry init main traces_sample_rate before_send PII
    "I'm onboarding onto our error-reporting stack. Where does the Sentry SDK initialise, how is the sample rate configured, and what does the before_send hook do to PII and handled-domain errors?",
    # 04892 Flat 4B Iris parcel collection Tuesdays/Thursdays
    "A friend asked how my parcel collection works when I'm at work. Who's my backup neighbour, which flat are they in, and which days of the week does each of us cover for the other?",
    # 04893 Neumann KM184 + Zoom F3 cabin ambient EP
    "Someone asked why I hauled microphones to the cabin. Which Neumann pair and which recorder did I bring, who was using them, and what were they capturing for an upcoming release?",
    # 04894 Kardia 6L ECG MyChart Mayo afib
    "I'm explaining dad's cardiology setup to the family. Which home ECG feeds into the Mayo portal, and what does it catch that the Apple Watch ECG misses between readings?",
    # 04895 OctoPrint Raspberry Pi 4 Bambu X1C + Voron 2.4
    "Someone asked how the workshop tablet drives two different 3D printers. Which software runs on which hardware, which two printers share it, and what specific Bambu-side complication is it fighting through?",
    # 04896 Go slog handler trace SpanContextFromContext Loki
    "I'm onboarding onto our Go observability story. How do trace IDs end up in every log line, where does the handler pull them from, and what does that enable in Loki without a join?",
    # 04897 Social media fast 2026-03-15 to 2026-03-21 Signal exception
    "A friend asked about my recent social media detox. Which dates did the fast cover, which platforms and clients were off limits, and what single channel stayed open for a reason?",
    # 04898 Dinner party rota Bhattacharya four households
    "Someone asked how the dinner-party rota works among the four households. When does the schedule reset, which months do we host, and which months do the Bhattacharyas cover?",
    # 04899 Tenant BudgetExceeded event 429 backoff SDK
    "I'm onboarding onto our billing overrun handling. What structured event fires when a tenant blows its budget, and how does the SDK wrapper shape it so upstream backoff code doesn't have to change?",
    # 04900 Embrace + Sentry session timelines release health
    "I'm onboarding onto our mobile observability split. Which tool handles crashes, which one provides session timelines and breadcrumbs, and what release signal does the second one feed?",
]


def emit() -> int:
    assert len(QUERIES) == 100, f"expected 100 queries, got {len(QUERIES)}"
    with SOURCES.open("r", encoding="utf-8") as f:
        sources = [json.loads(l) for l in f if l.strip()]
    assert len(sources) == 100, f"expected 100 sources, got {len(sources)}"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for query, src in zip(QUERIES, sources):
            row = {
                "id": src["new_id"],
                "source_id": src["source_id"],
                "query": query,
                "positive": src["text"],
                "query_kind": QUERY_KIND,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
