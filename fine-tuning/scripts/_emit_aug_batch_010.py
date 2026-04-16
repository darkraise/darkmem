"""One-off emitter for retrieval aug-010 batch - multi-sentence problem queries.

Each row pairs a 2-4 sentence query (20-60 words) simulating a user describing a
debugging or problem scenario before asking the specific intent. Positives come
directly from the pre-picked sources file at data/v2/retrieval/aug_sources/aug_010.jsonl.

Writes 200 rows to data/v2/retrieval/aug_010.tmp.jsonl with ids ret-04601..04800.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "v2" / "retrieval" / "aug_sources" / "aug_010.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "aug_010.tmp.jsonl"
QUERY_KIND = "multi-sentence"

QUERIES: list[str] = [
    # 04601 Redland flat deposit dispute
    "We had a deposit dispute with the Redland flat landlord that went to the scheme. How much did they withhold, what did they try to charge for, and when did the ruling come through in our favour?",
    # 04602 Scratch Jr to Scratch iPad save loss
    "The kids' Scratch workflow on the iPad was losing large sprite projects mid-save. What move did we make for Ingrid to stabilise that, and which machine did the work migrate onto?",
    # 04603 Weaviate hybrid alpha tuning
    "We were tuning hybrid retrieval on Weaviate and the short-query results looked off. What did the default alpha over-weight, and where did we end up setting it to balance BM25 and HNSW?",
    # 04604 Mochi stuck behind dishwasher
    "Mochi got herself wedged behind the dishwasher one afternoon. What date did this happen, how did we get her out, and how did we block the gap so we never repeat it?",
    # 04605 GraphQL N+1 DataLoader missing
    "The GraphQL endpoint had nasty N+1 behaviour on a particular field. Which field was it blowing up on, and what tool was supposed to be wired up but never got connected?",
    # 04606 VS Code remote-container node_modules volume
    "Remote-container dev loops in VS Code felt sluggish for months. What was the fix that finally made them snappy, and which directory specifically benefited from the change?",
    # 04607 Prototype pollution deep-merge lodash
    "We had a prototype pollution scare on the admin dashboard. What pattern replaced the unsafe deep-merge helpers, and which specific library flow got banned in the linter afterwards?",
    # 04608 Logitech G Cloud hotel Wi-Fi shelved
    "The Logitech G Cloud handheld ended up shelved after a trip. Which game on which streaming service pushed it over the edge, and what visual artefacts gave it away?",
    # 04609 etcd compaction lag API slowness
    "The API went slow on a specific early-March date and we traced it to etcd. Which compaction setting was the culprit, and what was it changed from and to?",
    # 04610 Whistle Go Explore pogo pins Tractive
    "Our dog tracker broke its charging pogo pins and the replacement was backordered. Which tracker was it, how long was the backorder, and what migration did the delay finally push us into?",
    # 04611 SPSC ring lock-free per pair
    "The global event bus was causing cache-line bouncing on the 8-core profiler runs. What data structure replaced it between subsystems, and how is it organised per pair of producers and consumers?",
    # 04612 UTF-8 CP1252 ingestor
    "The ingestor kept throwing UTF-8 validation errors. Where did the bad bytes actually come from, what legacy encoding were they, and at which point in the pipeline should the conversion have happened?",
    # 04613 Jest to Vitest ESM surprises
    "We migrated the test runner away from Jest. Which runner did we move to, and what class of problems did the switch surface that the old transforms had been quietly papering over?",
    # 04614 MSO5074 CAN bus termination
    "We were chasing a signal-integrity issue on a CAN bus. Which scope and probe type did we use, and what specific feature of the waveform pointed at the missing termination?",
    # 04615 Bazarr Shokugeki no Soma season mapping
    "The Shokugeki no Soma library had subs out of sync with audio for half a year. What tool finally fixed it, and what specific mapping feature got the English subs aligned to the Japanese dub?",
    # 04616 Canon R5 firmware 2.2.0 Ninja V
    "A Canon camera firmware push broke the external recorder handshake over HDMI. Which camera, which recorder, and what firmware version did we end up rolling back to in order to restore the pair?",
    # 04617 Server timeouts layering read write idle
    "Before we layered server timeouts, a slow client could hold a worker basically indefinitely. What are the actual numeric limits now for read, write and idle, and what extra deadline sits alongside them per handler?",
    # 04618 Android repeatOnLifecycle STARTED
    "Android background coroutines were leaking on config changes. Which lifecycle helper did we standardise on to gate those starts, and what pattern did it replace that had been leaking?",
    # 04619 Hypothesis off-by-one pagination
    "Our pagination helper had a stubborn off-by-one bug that hand-written tests kept missing. Which property-based testing tool caught it, and roughly how many manual cases had missed it?",
    # 04620 Homebrew openssl@3 shadowing Brewfile pin
    "Homebrew autoupdates broke the dev environment one morning. Which formula shadowed the system version, what was the symptom, and how did we lock things down afterwards?",
    # 04621 Intl.DateTimeFormat timeZoneName longGeneric
    "Timezone names were drifting out of date in the UI. Which browser API do we now render them through, which option are we passing, and what event made the old static lookup table untenable?",
    # 04622 Mini Cooper SE FIXD pending codes
    "We test drove a used 2020 Mini Cooper SE. Which history service gave it a clean bill, and what dongle pulled pending codes during the drive that contradicted that?",
    # 04623 MVCC report autovacuum xmin horizon
    "A long-running report was blocking autovacuum on a hot Postgres table. What did the xmin horizon look like, and where did we move the report to actually free things up?",
    # 04624 Parallel-write Postgres to Citus
    "During the Postgres-to-Citus migration, we ran parallel writes for validation. What did that pattern catch, and roughly how long had those bugs been sitting in the code unnoticed?",
    # 04625 Gatsby to Astro personal blog
    "I regretted a framework choice made back in 2021 for my personal blog. Which framework was it, what did I rewrite it to, and what made the data layer so painful to untangle during the rewrite?",
    # 04626 Brod & Taylor proofer BLE sensor drift
    "A sourdough loaf failed and we traced it to a temperature mismatch. Which proofer was it, what was the actual vs claimed temperature, and which component had drifted to cause the bad reading?",
    # 04627 Matter-over-Thread Aqara U100 border router
    "Our Matter-over-Thread door lock stopped responding one evening. Which device was it, which Apple hardware was acting as the border router, and what sequence actually restored control?",
    # 04628 VPA recommend-only mode batch pods
    "Vertical Pod Autoscaler was restarting long-running batch pods mid-flight. What mode is it running in now on production, and why did the previous configuration end up being too disruptive?",
    # 04629 gRPC TLS renegotiation Go concurrent streams
    "Our gRPC clients were deadlocking under load. What TLS-level operation was involved, which language's client was the culprit, and which cap was it missing on the connection?",
    # 04630 plan_cache_mode force_custom_plan
    "Prepared-statement plan caching was burning a multi-tenant Postgres service. Which plan type was losing out for skewed tenants, and which GUC got flipped to force per-tenant plans?",
    # 04631 yaml.load to yaml.safe_load red team
    "A red-team exercise smuggled a rogue constructor through our config service via a feature flag file. Which unsafe YAML call was responsible, and what did every loader get swapped to afterwards?",
    # 04632 Saleae Logic Pro 16 I2C SDA rise time
    "We captured an I2C glitch on a power sequencer with a logic analyzer. Which analyzer did we use, what voltage were we running at, and which line's rise-time was out of spec?",
    # 04633 Django 3 to 4 USE_DEPRECATED_PYTZ
    "Migrating a legacy CRM from Django 3 to Django 4 left one compatibility knob on for a while. Which setting stayed True, for how long, and what test suite had to stay green before we flipped it?",
    # 04634 SEGGER SystemView priority inversion
    "We had a nasty priority inversion on a FreeRTOS system. Which tracing tool surfaced the task churn, and which two tasks were involved in the inversion?",
    # 04635 DNS cache sidecar low TTL 5xx
    "Intermittent 5xx errors showed up after every deploy. Where was the stale state actually living, and what aspect of our DNS records was it ignoring?",
    # 04636 Loom model checking dequeue memory ordering
    "A lock-free queue had a memory-ordering bug that would have hit production extremely rarely. Which tool caught it, which path in the queue had the miss, and roughly how rare was the bug's natural frequency?",
    # 04637 RxJava Schedulers.io bounded executor
    "An RxJava migration revealed that the cached io scheduler was spawning hundreds of threads under load. Which call got replaced and with what, and what did that replacement take a handle to?",
    # 04638 Scientist-style double-call fraud rounding
    "Before cutting the fraud service over, we ran a dual-call comparison for weeks. What pattern was that, how long did we run it, and what turned out to be the source of the 0.3% mismatch?",
    # 04639 Pixel Watch 3 fall-detection Bluetooth tether
    "The Pixel Watch 3's fall-detection SOS failed during a real incident. Why did it break specifically, whose fall was it, and what was happening with the paired phone at the time?",
    # 04640 Gluetun qBittorrent ProtonVPN port-forwarding
    "Our torrent container silently stalled for two days. Which stack was wrapping it, what change broke port forwarding, and which monitoring tool finally caught the zero-grab state?",
    # 04641 Tokyo language exchange Yuki Sapporo
    "The Tokyo language exchange group changed shape when one regular relocated. Who moved and to where, what day of the week does the group still meet, and how does the new format feel?",
    # 04642 Coursera Google UX Design Certificate
    "I finished a Google-branded design certificate on Coursera. When did it end, how long did it take, and did it actually land interviews on its own?",
    # 04643 dotTrace UI stutter logging lock
    "A UI stutter was appearing during traffic bursts. Which profiler's timeline view lined it up, and what was the background thread actually contending on?",
    # 04644 Run-club Christmas party kitchen crowding
    "Our run-club Christmas party got uncomfortably crowded in one room. What date did we host, how many peaked in the kitchen, and what's the plan to redistribute heat next year?",
    # 04645 Brother Theodore dog Whiskey seizure
    "My brother called in the middle of the night about his dog having a seizure. Which brother was it, which dog, what date, and did the dog recover?",
    # 04646 Fine-tuned checkpoint tokenizer save_pretrained
    "A fine-tuned checkpoint wouldn't load after training. What had been saved separately that shouldn't have been, and which method bundles everything correctly in one go?",
    # 04647 Schengen biometric expiring London
    "I had to refresh a visa stamp in London before a holiday. Which visa was it, what was the date, and what was about to expire mid-trip if I'd skipped it?",
    # 04648 goleak pprof goroutine ticker closure
    "We were hunting a goroutine leak in a Go service. Which pprof endpoint did we hit, which library's helper goes into test teardowns, and what kind of leaked goroutine was holding 30 MB of closures?",
    # 04649 Hugo Awards Sad Puppies Rabid Puppies
    "I'm reading up on the 2015 Hugo Awards controversy. Which two slates were behind it, and what broader fault lines in science fiction fandom did the whole episode expose?",
    # 04650 School vouchers charter-school mixed effects
    "I'm trying to summarise the evidence on school vouchers and charter schools for a policy note. What does the literature actually show, and what dominates the variation in results?",
    # 04651 Kellogg MMM deadline missed
    "I missed a dual-degree application deadline by a few hours. Which school, which programme, what was the original deadline, and which round am I resubmitting for instead?",
    # 04652 Asthma wildfire smoke inhaler
    "My asthma got bad during a wildfire smoke event. How much did the rescue inhaler usage change during that week, and what was the baseline frequency before?",
    # 04653 Reviewer cap five active PRs
    "We were seeing a Friday-afternoon dip in code review activity. What did the comment-per-PR drop look like, and what policy did we put in place to balance reviewer load going forward?",
    # 04654 Harbor pull-through cache Docker Hub
    "We were getting hit by Docker Hub rate limits. Which Harbor feature absorbed the load, and what were the before-and-after numbers for upstream pulls per node per day?",
    # 04655 Personal newsletter dropped issue 24
    "I ran a personal newsletter for a while and eventually stopped. Which issue number did I stop at, and what actually caused me to walk away from it?",
    # 04656 TurboTax joint return ITIN transposed
    "TurboTax kept bouncing our joint return. Whose identification number had the problem, what kind of number was it, and what specifically was wrong with it?",
    # 04657 Bali flight cancelled Singapore reroute
    "Our Bali trip in June got thrown off by a cancellation. Which flight leg did the airline reroute, and through which city did the replacement routing run?",
    # 04658 System ordering Inventory Collision coin
    "Players were occasionally walking through coins in our pickup system without grabbing them. Which two subsystems ran in the wrong order, and what kind of constraint did we add to fix it?",
    # 04659 Ollama response truncated max_response
    "Long Ollama responses were getting truncated on our extractor path. Which client-side limit was the culprit, what was the default, and what did we raise it to?",
    # 04660 Save corruption atomic write .tmp rename
    "Save corruption on a game patch came from mid-write crashes during platform suspend. Which patch version triggered the triage, and what atomic write pattern did we settle on afterwards?",
    # 04661 WAI-ARIA tooltip focus and hover
    "Our hover-only tooltips were inaccessible on keyboard and touch. What did we replace them with, and which design pattern library did we follow for the implementation?",
    # 04662 Docker multi-stage stale node_modules lockfile
    "A Docker multi-stage build kept reusing a stale node_modules layer. Which file was missing from the COPY step, and what effect did that omission have on cache invalidation?",
    # 04663 Pytest randomisation legacy registry
    "We had flaky CI that never reproduced locally. Which pytest feature exposed the true cause, and where in the codebase did the global state leak actually live?",
    # 04664 Readwise Kindle My Clippings calibre
    "Readwise's Kindle sync broke one morning and the fix took almost a week to land. Which Kindle app version rewrote the file schema, and what manual workflow filled the gap in the meantime?",
    # 04665 Dead Oceans Phoebe Bridgers Rough Trade
    "I missed out on a vinyl reissue during a label sale. Which label, which artist, which colour variant, and roughly how fast did the retailer sell out?",
    # 04666 Small-sample null hypothesis distributional
    "I'm trying to explain why someone's small-n A/B result might be misleading. What kinds of assumption tend to fail quietly at low sample sizes, and what does that do to standard tests?",
    # 04667 StockX Jordan 4 Military Black midsole
    "A shoe consignment on StockX got flagged at verification. Which pair was it, what date was the sale, what cosmetic issue did Verification Center flag, and did the seller fee still get taken?",
    # 04668 Whoop vs Oura wine pizza night
    "Whoop and Oura disagreed about how well I'd recovered one morning. What did Whoop claim, what did Oura catch instead, and what had actually happened the previous evening?",
    # 04669 Amazon KDP royalties DuckDB Quarto
    "I wasn't making sense of my book royalty reports. Where do the CSVs come from, what file format do they land in now for analysis, and which notebook tool drives the queries?",
    # 04670 Admin cookie SameSite Strict CSRF
    "A top-frame GET CSRF got past our existing SameSite=Lax setting. What specifically did we tighten it to on the admin console cookies?",
    # 04671 Perlin camera shake damage amplitude
    "Camera shake used to desync under slow-motion. What drives the shake now, what does its amplitude key off of, and what pattern did it replace?",
    # 04672 trace.WithAttributes span hot loop
    "Attribute encoding was chewing CPU on hot loops in our traced Go service. Which call was being made per-iteration, what did we move to instead after the loop, and roughly what share of CPU time did the old pattern account for?",
    # 04673 Match lobby CRDT ready-state flicker
    "Our match lobby was showing a flicker in the ready column when late joiners reconciled. What data structure replaced the old racy state, and what specific interaction was causing the flicker?",
    # 04674 Amazon Prime same-day 90210 outage
    "Amazon Prime's same-day shipping slipped to three days for an order of mine. What date did this happen, which fulfilment center was involved, and what was going wrong on their side?",
    # 04675 Readwise pre-2024 Kindle imports manual CSV
    "The weekly Kindle highlights pipeline broke when Readwise changed what it imports. Which imports were dropped, what date did the break happen, and what stopgap fed the system for the last month?",
    # 04676 Tomato seedlings greenhouse heater unplugged
    "Tomato seedlings froze one night in early April. Where were they being kept, what piece of equipment failed, and how exactly did it fail?",
    # 04677 Ex-flatmate Caleb Whitechapel gallery
    "I bumped into an ex-flatmate at a gallery opening and it was awkward. Which venue, which ex-flatmate, roughly how long did the small talk last, and how did we end the interaction?",
    # 04678 Kinesis hot partitions composite key
    "Kinesis hit a 45-minute backlog one day from hot partitions. Which date was it, what was the original partition key, and what did we switch it to in order to spread the load?",
    # 04679 PHP spx regex middleware Laravel
    "A Laravel middleware was dominating call time on a PHP service. Which profiling tool gave us the call graph, and what was the offending code actually doing?",
    # 04680 STUN TURN symmetric NAT carrier
    "Voice call quality was unacceptable on one carrier. What was special about their NAT that STUN couldn't handle, and what had to step in to keep calls working?",
    # 04681 Duolingo Lingvist Pimsleur Korean rotation
    "I plateaued on Korean after three months of using a single app. Which three apps do I rotate through now, and how often does the rotation cycle?",
    # 04682 Ecological validity lab messy real-world
    "I'm writing up some concerns about a lab-based study generalising to the field. Which methodological critique captures this, and what does it say specifically goes wrong?",
    # 04683 Cargo workspaces proc-macro circular
    "Sharing a proc-macro crate inside a Cargo workspace was throwing circular dependency warnings. What workspace arrangement finally worked, and what structural change was needed?",
    # 04684 Stanford marshmallow experiment family background
    "Someone cited the marshmallow experiment to me as strong evidence. What happened to its predictive power in later work, and what was the specific control that dulled the effect?",
    # 04685 Rust migrator Windows tokio blocking drop
    "Our Rust migrator was leaking file handles on Windows. Which async runtime was involved, what kind of tasks were staying alive past their expected drop, and why did this only show up on Windows?",
    # 04686 mypy CI cache stale dependency signature
    "mypy passed on my laptop but failed in CI. Where was the discrepancy coming from, and what exactly was wrong about the cache on CI?",
    # 04687 Alembic shared down_revision splice
    "Alembic migrations were running in the wrong order in a project. What had gone wrong between two revisions, and what command regenerated a correct chain?",
    # 04688 Tuskegee Syphilis Study 1932-1972
    "A colleague asked me for a historical benchmark ethical violation in clinical research. Which study do we typically cite, which agency ran it, where and when did it take place?",
    # 04689 Tractive firmware geofence Jiobit backup
    "A pet tracker's firmware update broke geofence alerts for several days. Which tracker had the problem, how long were alerts broken, and what backup device quietly took over in the meantime?",
    # 04690 Grandma Ingrid 1995 vs 1997 Christmas photo
    "Grandma Ingrid and I had an argument about the year of a Christmas photo. Which year did each of us think it was, and which of us ended up being wrong?",
    # 04691 panamax Cargo mirror yank leftpad
    "A Cargo crate yank incident came and went without breaking our reproducible builds. Which local mirror did the work, and why did builds remain stable despite the yank upstream?",
    # 04692 Researcher degrees of freedom false positives
    "I'm explaining to a teammate why many small analytical choices in a study can be a problem. Which term captures this, and what does the phenomenon actually do to false positive rates?",
    # 04693 IDDD ubiquitous language billing rewrite
    "I picked up a DDD book and it suggested a specific early-stage workflow. What does it recommend you do before touching code, and which project of ours paid for skipping it twice?",
    # 04694 Ecowitt WH40 rain hailstorm coldframe
    "A hailstorm destroyed my pepper starts because an automation wasn't wired up. Which rain sensor should have triggered what piece of equipment, and what date did this happen?",
    # 04695 CarBridge TrollStore iOS 18.3
    "A jailbreak-based hack on my iPhone let YouTube run on the head unit, then disappeared. What was the hack called, what sideload tool was involved, and which iOS version finally killed it?",
    # 04696 FMA replay determinism Ryzen trig
    "Replay determinism broke on Ryzen boxes specifically. Which compiler-level contraction was behind it, what numerical error size did it introduce per frame, and how fast did desyncs show up?",
    # 04697 Warp tmux copy-mode Ghostty kitty
    "I tried Warp's AI-powered terminal for a while. What specifically did it break when I used tmux inside it, and where am I keeping it out of as a result?",
    # 04698 GitHub Classroom nbgrader container
    "The GitHub Classroom autograder was failing edge cases for me. Which grading tool did I wire in, and which environment did I make sure both systems were sharing?",
    # 04699 auth_middleware.py line 42 UTC vs local
    "A specific auth-middleware bug turned out to be about timestamps. Which file and line was it at, and what was the actual mismatch between the token expiry check and the timestamp?",
    # 04700 Haskell QuickCheck Unicode slug Python port
    "A Haskell slug generator's test shrinkers found an edge case that the Python port of the same code hadn't caught. What was the root cause, and how had the Python port drifted?",
    # 04701 clinic.js doctor bcrypt sync async
    "p99 on our Node service tanked and we ran a profiler against it. Which profiler, what diagnosis did it give us, and what one-word change to the bcrypt call unblocked things?",
    # 04702 Twitch LIRIK 7MV emote stale tab
    "A Twitch ban from a channel confused me because I knew I hadn't misbehaved. Which channel was it, what date, and what was actually triggering the spam?",
    # 04703 Bun Cloudflare Workers Bun.serve fetch
    "We tested Bun's compatibility with Cloudflare Workers. What passed, what didn't, and what specific API didn't map cleanly to the Worker handler model?",
    # 04704 defusedxml lxml XXE /etc/hostname
    "XML parsing across the codebase was vulnerable to XXE and we cleaned it up. Which library did everything move to, what was the old library's unsafe default, and what was one of the test fixtures already pulling?",
    # 04705 Libby Kindle auto-return Oasis
    "Libby's 2026-03-22 update broke something on Kindle loans. Which behaviour broke specifically, how many holds expired mid-chapter as a result, and which device was affected?",
    # 04706 Thermohaline North Atlantic freshwater
    "I'm explaining a climate-model failure mode to a non-specialist. Which ocean circulation is affected, which region is where the trouble starts, and what kind of forcing weakens it?",
    # 04707 DynamoDB conditional write reserved word
    "A DynamoDB conditional write was failing silently. Which construct was referenced in the ConditionExpression, and what map was missing that would have made it work?",
    # 04708 Search relevance TREC synonym map
    "A search relevance regression got caught before it could ship. What kind of bug was it, which eval drove the block, and what held it back at deploy time?",
    # 04709 Garmin Connect FIT files sync collision
    "Garmin Connect lost three weeks of activity data on me. What date did the loss happen, and which two devices on the same account collided?",
    # 04710 argparse --foo=bar click switch
    "argparse was silently accepting a flag as positional in one of my scripts. What was misconfigured specifically, and which library did I move to afterwards?",
    # 04711 SteamOS exFAT btrfs CryoUtilities
    "SteamOS was eating my external SSD's partition every other boot. What filesystem was the problem, what did I move to, and which tool now manages the volume?",
    # 04712 Maya spelling homework pre-dinner
    "Our spelling-homework battle with Maya was getting nowhere. What small schedule change settled it, and how long does the new session actually last?",
    # 04713 Ecobee C-wire adapter install
    "Installing a smart thermostat on a specific date hit a wiring problem. Which brand of thermostat, what was missing from the wall, and what adapter got it staying on?",
    # 04714 Cloudflare CDN APAC purge propagation
    "CDN purge showed eventual-consistency pain during a release. Which CDN was it, roughly how many edges are we talking about, and which region saw the worst lag?",
    # 04715 Readwise daily review ten highlights iOS
    "We experimented with the Readwise daily review size on iOS. What's the current cap, what happened when we tried doubling it, and how fast did engagement drop?",
    # 04716 Helldivers 2 Backloggd Steam rate limit
    "A Steam achievement wouldn't propagate to my tracker for days. Which game, which tracker, and which Steam API's rate limit was the bottleneck?",
    # 04717 Flagsmith Java SDK async cold JVM
    "The Flagsmith Java SDK bit us on a cold JVM start. Which evaluator is pinned now on server-side, and what specifically went wrong when we were using the other flavour?",
    # 04718 Tekken 8 PowerLine Ethernet tournament
    "I was anxious about online lag during a Tekken 8 tournament. What did we install to fix it, and where in the house did the equipment land?",
    # 04719 Eufy HomeBase 3 firmware clip archive
    "A home camera firmware update wiped 30 days of footage for me. Which hub was it, what date did this happen, and how long did the support ticket sit unanswered?",
    # 04720 Hawaiian hotspot bend 47 Ma
    "I'm reading about mantle plume models and their gaps. Which hotspot track poses the problem, and roughly how long ago does the trouble spot in the track sit?",
    # 04721 Saga order-to-cash compensation choreography
    "Our order-to-cash saga went through two implementations. Which version did we ship, which version did we roll back after one sprint, and why?",
    # 04722 Koi pond pH peat bag filter sump
    "Our koi pond pH was reading high on a specific date. What was the number, what's the target, and what two corrective actions are underway?",
    # 04723 styled-components v6 SSR regression pin
    "We pinned a CSS-in-JS library to a specific version in one legacy app. Which library and version, what upstream bug keeps us there, and how is the rationale recorded in the repo?",
    # 04724 Terraform aws v5.70 v6 S3 encryption
    "A Terraform provider auto-upgrade broke encryption defaults on new buckets. Which provider was it, which major version jump caused it, and what version are we pinned to now?",
    # 04725 Washing machine inlet hose flood five years
    "A washing-machine flood at home kicked off a new replacement schedule. What date did it happen, what actually failed, and what's the standing rule for those parts now?",
    # 04726 Rachel Grandpa's cabin arbitration
    "An inheritance dispute with a family member dragged on. Which relative am I arguing with, what's the asset, and where has the dispute ended up?",
    # 04727 Ceph OSD PG autoscaler slow request
    "Adding an OSD to our Ceph cluster caused a slow-request spike during rebalance. Which subsystem's defaults overshot, and what property of the pool were they mis-sized against?",
    # 04728 Waveform Pro Melda vocal bus export crash
    "Our Waveform Pro project with Nora still crashes on export under specific conditions. Which plugin chain is the trigger, how many instances tips it over, and what's the workaround?",
    # 04729 npm workspaces pnpm patch upstream
    "npm workspaces was missing a feature we really needed. Which command did it lack, what external tool did contributors bring in, and how did fixes flow upstream from there?",
    # 04730 Medium cross-post canonical SEO excerpt
    "Medium cross-posting stopped helping our SEO in 2024. Which signal stopped getting honoured on which date, and what publishing pattern did the team switch to instead?",
    # 04731 ThreadSanitizer memory_order_release counter
    "A flaky test in our analytics aggregator had a subtle cause. Which sanitizer caught it in CI, and what memory-order mistake did it point at?",
    # 04732 Kayak Vueling Berlin Google Flights
    "I'm planning a Berlin trip and had to abandon one flight search tool. Which date is the trip, which tool kept hiding a specific carrier's leg, and which tool am I using instead?",
    # 04733 AccelaGov Juneteenth permit 30-day window
    "A block-party permit rejection on a government portal nearly blew a 30-day filing window. Which portal was it, what was the permit for, and how close did the rejection come to the deadline?",
    # 04734 Vercel Edge WebSocket Fly.io live-cursor
    "Our live-cursor feature outgrew one serverless platform's WebSocket support. Which platform was too limited, and which provider is now running the long-lived sockets?",
    # 04735 Pytest collection 3GB autouse DB conn
    "Pytest collection was blowing past 3 GB of RAM for us. What scope of fixture was the culprit, what decorator was it using, and what resource was being held?",
    # 04736 Rome Biome deprecation fork config
    "A linter project got deprecated mid-migration for us. Which project was replaced by which fork, and what property of the fork kept the diff small for us?",
    # 04737 OMAD trial quit sleep binges
    "I tried a one-meal-a-day eating pattern and gave up. How long did I stick with it, what date did I stop, and what was undermining the deficit?",
    # 04738 Clara Lisbon job remote Fridays
    "We had a rough two-week stretch over a job offer my partner received. Whose offer was it, which city was it in, what date did the disagreement land, and what compromise did we reach?",
    # 04739 Outback head gasket Harbourside Auto Dmitri
    "A head-gasket replacement on my Subaru came with a local-mechanic anecdote. When and where was the work done, who did it, how much did it cost, and what coolant habit did he drill into me?",
    # 04740 PayPal Honey eBay Amazon only
    "PayPal Honey pulled a weird move on an eBay checkout for me. What date did this happen, what did the extension do, and how did I lock it down afterwards?",
    # 04741 Object versioning ETL manifest.json overwrite
    "Object versioning revealed a silent overwrite bug in one of our ETL writers. What was being clobbered, and what was the upstream cause of the repeat overwrites?",
    # 04742 pull-bot reviewer load balancer
    "Our pull-bot used to assign reviewers round-robin and staff engineers kept getting buried. What policy replaced round-robin, and which group of engineers benefited most from the change?",
    # 04743 Pooled particle allocator Switch damage numbers
    "Damage numbers on enemies were thrashing the GC on Switch during boss phases. What spawning pattern replaced the old per-hit GameObject pattern, and which console surfaced it worst?",
    # 04744 py-spy folded stack regex middleware
    "Request middleware on our Python service was running hot. Which sampler did we point at it, what was the output format fed into a flame graph, and what did that flame graph surface?",
    # 04745 Garage door Chamberlain MYQ battery backup
    "Our garage door opener died during a storm mid-March. What date was it, what retrofit kit did I install to replace the logic board, and what else did I add to the same circuit?",
    # 04746 Scratch stage retro mode twins
    "The twins' Scratch birthday-card program kept freezing. What turned out to be the culprit, and what setting was pinned in the wrong mode?",
    # 04747 BuildKit COPY ordering package manifest
    "BuildKit was invalidating our cache in surprising ways. What was the specific COPY-ordering mistake we fixed, and where does the package manifest now sit in the Dockerfile?",
    # 04748 Hexagonal notification User row Expand Contract
    "Extracting the notification domain into a hexagonal design stalled at one key entity. Which row was owned by the wrong repo, and what migration pattern did we use to move ownership?",
    # 04749 rr record-and-replay C++ sidecar segfault
    "A non-deterministic segfault in a C++ sidecar was impossible to chase live. Which record-and-replay tool did we use, and roughly how quickly did it pin the root cause?",
    # 04750 memray pandas per-request copy RSS
    "A slow RSS climb on a Python service wasn't obvious from the metric itself. Which allocation tracer caught the real cause, and what per-request operation was leaking memory?",
    # 04751 Garmin Body Battery new puppy 3am wakes
    "Garmin's Body Battery drain was badly off one week. What caused the sleep deprivation, what specific aspect of the algorithm missed it, and what date did it hit?",
    # 04752 Tofu ExoticPet retained shed warm soak
    "One of my reptiles had a stuck shed on a specific toe. Which pet was it, which clinic flagged it, which toe, and what's the home-care plan?",
    # 04753 PARA Second Brain zettelkasten
    "I tried a named productivity system for six weeks before dropping it. Which system, what's the acronym expansion, and why did the hierarchy fight my existing notes?",
    # 04754 Node heap diff Map circuit breaker
    "We found a Node memory leak via heap snapshot diffing across load tests. Which collection type was the offender, and under what trigger ordering did it grow unbounded?",
    # 04755 KDP ePub TTF font preflight
    "A book launch on KDP failed preflight. What was the release date, what was embedded in the ePub that broke Amazon's validator, and what was the file format of that embedded asset?",
    # 04756 gdb scheduler-locking futex condvar
    "A stuck worker needed live inspection. Which debugger did we attach to the pid, what setting did we flip before stepping, and what was the backtrace revealing about the synchronisation primitive?",
    # 04757 Daryl Bem Feeling the Future 2011
    "A specific 2011 psychology paper helped spark the replication crisis. Who was the author, what was the claim, which journal published it, and what kind of reform movement did it set off?",
    # 04758 Go pprof allocation json.Marshal heap
    "Heap churn during peak load had a single dominant cause in our Go service. Which pprof mode surfaced it, and what percentage of allocations was it responsible for?",
    # 04759 Shoulder impingement bench press Dr Voss
    "A bench-press injury took several physio sessions to clear. Who cleared me and on what date, how many sessions did it take, and how long did I have to deload?",
    # 04760 Duplicate rows uniqueness serializable transaction
    "Duplicate rows slipped past a uniqueness check in one of our Postgres tables. What transaction-isolation pattern would have prevented it, and what was wrong about the insert?",
    # 04761 fast-check sort stability leaderboard
    "Unit tests kept missing a sort stability bug on our leaderboard. Which property-based framework caught it, and roughly how many hand-written tests had stepped past it?",
    # 04762 Jekyll 4.3 GitHub Pages Ruby 2.7
    "A Jekyll upgrade broke on a specific GitHub Pages pin. Which version of Jekyll, which Ruby pin, what date did this hit, and where did we move the build to?",
    # 04763 Chytridiomycosis Scheele 2019 Science
    "I'm summarising a driver of global amphibian declines. Which pathogen is the cause, which disease does it produce, and which landmark paper quantified the declines?",
    # 04764 V8 hidden classes inline cache event shape
    "V8 was penalising one of our event objects. What happened to the object's hidden class when a field was added late, and what pattern in the constructor fixed it?",
    # 04765 LSP server memory cap monorepo
    "Frontend engineers on large monorepos kept seeing their LSP server freeze. What limit did we raise and from what value to what value?",
    # 04766 Tesco panic five things texture
    "I had a panic episode in a supermarket queue on a specific date. How long did it last, and which grounding technique actually cut through when the breathing pattern I expected didn't?",
    # 04767 M'Cheyne Blue Letter Bible plan
    "I kept stalling on a year-long reading plan. What plan stalled where, which plan did I switch to on New Year's, how is that one structured, and how long have I held?",
    # 04768 Go generated client optional pointer nullable
    "A generated Go client was too pointer-heavy for comfort. What post-processing step did we add, and what did it do to the optional fields?",
    # 04769 WebRTC TCC BBR GCC mobile
    "Our WebRTC congestion handling needed custom tuning for mobile. Which estimator did we tune against which TCP congestion controller, and what was wrong with the default on our link?",
    # 04770 Molecular clock fossil calibration metazoan
    "I'm flagging a known methodological limit in evolutionary timing estimates. What methodology is affected, what calibration is the sticking point, and across which broad group does the uncertainty get wide?",
    # 04771 School run checklist bag lunch coat
    "Our 08:15 school-run handoff is now a thirty-second ritual. Where does it happen, what's on the checklist in order, and what one incident locked the list in?",
    # 04772 HBO Max rebrand Roku Bluey continue watching
    "A streaming rebrand wiped my kid's continue-watching list on Roku. Which service rebranded to which on what date, and which show caused the subsequent meltdown?",
    # 04773 Prisma TypeORM session boundary coexistence
    "We ran two ORMs in parallel for a while. Which ORM owned new writes, which served legacy reads, and roughly how long did it take to shake out the session-boundary bugs?",
    # 04774 Peak Design Wandrd Rollo zipper buckle
    "Two camera-bag accessories stopped fitting together on me. Which backpack version is the problem, which hip pouch was I using, and exactly where do they now foul each other?",
    # 04775 Project Zomboid Rin Seattle mod list
    "Project Zomboid was unstable on my gaming desktop until a friend's curated modlist. Who curated it, where are they based, and what broken mod did they rip out?",
    # 04776 Apple Health ARIMA desk bike R
    "I wanted to test whether my desk bike actually increased step count. What data did I export, which statistical model did I fit, and in which language did I run the analysis?",
    # 04777 Spotify DJ Post Malone downtempo
    "Spotify's DJ feature crashed the vibe of a long-running playlist of mine. What date did this happen, what kind of track did it insert, and what had the playlist consistently been for two years?",
    # 04778 WEIRD sample bias psychology
    "I'm explaining to a colleague that a psychology finding may not travel. Which sampling bias captures that concern, and what does the acronym stand for?",
    # 04779 CORS X-Request-Id preflight gateway
    "A CORS preflight kept failing for one of our custom headers. Which header was being stripped, by which component, and what was the fix?",
    # 04780 SQLAlchemy selectinload joined loading
    "SQLAlchemy's selectinload made our N+1 problem worse somehow. Why did the per-batch fetch still hurt, and what loading strategy fixed it?",
    # 04781 Warp tmux Ghostty kitty ssh colours
    "Running Warp with tmux over ssh gave me garbled 256-color output. Which terminals am I using instead on any box that runs tmux?",
    # 04782 Bambu X1C AMS runout cosplay
    "A 12-hour cosplay print jammed deep into the job. What date, which printer, and which spool-sensor feature failed to pause the print cleanly?",
    # 04783 Tacoma Narrows 1940 aeroelastic wind tunnel
    "I'm invoking a famous bridge collapse as a turning point for a design discipline. Which bridge, when did it collapse, and what practice did it push civil engineering to adopt?",
    # 04784 Finanzamt Steuer-ID Festsetzung
    "A German tax letter spooked me for a week. What agency sent it, which reference number was involved, what date, and which German word turned out to be harmless bureaucratese?",
    # 04785 WebTransport WebSocket datagrams lobby
    "We evaluated a newer transport for a game lobby against WebSockets. Which transport did we trial, which of its properties matched the player-position stream, and why didn't we ship it?",
    # 04786 RabbitMQ Streams Kafka consumer offsets
    "We tried swapping Kafka for RabbitMQ Streams. What one-week deadline blocker killed it, and which client feature was specifically missing?",
    # 04787 Nest Protect Google Home migration local API
    "Our Nest Protect alarms lost their battery-state reporting in Google Home. What date did the regression land, what migration triggered it, and what specifically got killed?",
    # 04788 Measurement invariance latent scores groups
    "I'm pushing back on a cross-group latent-variable comparison in a draft. What has to be established first, and across which dimensions?",
    # 04789 fMRI BOLD haemodynamic seconds
    "I'm explaining why higher-field-strength fMRI doesn't actually give you millisecond resolution. What is the BOLD signal a proxy for, and what sets the temporal ceiling?",
    # 04790 msan Rust C dependencies pure-C
    "MemorySanitizer adoption stalled for us on a Rust project. What was blocking full coverage, and which subtree did we end up scoping msan to in the interim?",
    # 04791 City University MSc Data Science ALC
    "A master's application got withdrawn on me for a missing prerequisite. Which programme and university, what date, what was missing, and what route am I resubmitting through?",
    # 04792 pg_stat_statements random_page_cost bitmap
    "One Postgres query was chewing 60 percent of our cluster CPU. Which extension surfaced it, and what change finally nudged the planner into a bitmap scan?",
    # 04793 Homepage singleflight cache stampede
    "Our homepage cache was stampeding on expiry. What concurrency pattern fixed it, and what does that pattern do when multiple goroutines ask for the same key?",
    # 04794 Imposter feeling principal week 11 logs
    "The first few months of my principal promotion were rough psychologically. Roughly when did the imposter feeling fade, and what habit helped get me there?",
    # 04795 Clovis-first Monte Verde 13000 BCE
    "I'm pushing back on a simplified model for the peopling of the Americas. Which model am I critiquing, roughly what date does it propose, and which archaeological site undermines it?",
    # 04796 SAML replay InResponseTo assertion
    "A stolen SAML assertion was replayed two seconds after issuance. Which check actually caught the replay, and what field tied the assertion back to the original request?",
    # 04797 deno.lock deno-std transitive bump
    "The deno.lock file got committed late on one project. What had been happening in tests before then, and how many times had a specific transitive dependency bumped in a single day?",
    # 04798 Rahim PIP exit management year
    "A performance improvement plan for one of my reports ended badly. Who was the report, what was the exit date, and how does that stretch compare to the rest of my management year?",
    # 04799 DevTools Performance JSON.parse 14MB hydration
    "Chrome DevTools caught a main-thread long task during hydration on one of our apps. Which panel recorded it, and what operation on how large a payload was the culprit?",
    # 04800 re to re2 catastrophic backtracking user-agent
    "A user-agent matcher in our ingest worker was hitting catastrophic backtracking. Which Python regex library did we move to, and what kind of input triggered the old one?",
]


def emit() -> int:
    assert len(QUERIES) == 200, f"expected 200 queries, got {len(QUERIES)}"
    with SOURCES.open("r", encoding="utf-8") as f:
        sources = [json.loads(line) for line in f if line.strip()]
    assert len(sources) == 200, f"expected 200 sources, got {len(sources)}"

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
