"""One-off emitter for retrieval aug-batch-009 — multi-sentence queries.

Reads data/v2/retrieval/aug_sources/aug_009.jsonl (200 pre-picked source rows,
memory_type=fact) and writes data/v2/retrieval/aug_009.tmp.jsonl with one
multi-sentence-style query per source. Queries are 2-4 sentences (~20-60 words),
leading with scenario or context and ending with the specific retrieval intent.
Ids run ret-04401..ret-04600, positives are the source text verbatim.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "v2" / "retrieval" / "aug_sources" / "aug_009.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "aug_009.tmp.jsonl"
QUERY_KIND = "multi-sentence"

# 200 multi-sentence queries, aligned in order with aug_009.jsonl rows 1..200.
QUERIES: list[str] = [
    # 04401 Mosquitto kept on-prem, EMQX in cloud, bridge mode
    "The factory-floor team is asking why we did not consolidate everything onto EMQX when the cloud broker moved over. Which MQTT broker stayed on the on-prem gateway, and what property of it actually suited the air-gapped edge better?",
    # 04402 Super Bowl LX rewatch on Jellyfin DVR because Paramount+ cut halftime
    "Someone wanted to rewatch the halftime show from this year's Super Bowl and Paramount+ was not showing it. Which recording did we end up using instead, and why was the streaming version missing that segment in the first place?",
    # 04403 Yamnaya migration reshaped Europe around 3000 BCE
    "A friend was asking about where the genetic makeup of modern Europeans actually comes from. What does ancient DNA work on the Yamnaya steppe culture suggest about Bronze Age migration, and roughly when did that major movement take place?",
    # 04404 MPS Solar quote £9,800 for 4.2 kWp + 5 kWh battery on 2026-04-05
    "We're comparing solar installer quotes from earlier this month. What did MPS Solar come back with for a 4.2 kWp array plus a 5 kWh battery, and how tightly did the two rival quotes cluster around it?",
    # 04405 noise: lab portal loading
    "I just heard the other person say something about loading a page before continuing. Was that a filler pause or is there something they actually need me to wait on before we resume the conversation?",
    # 04406 USDT probes in postgres binary correlate stalls with lock waits
    "Query stalls on Postgres had been slippery to correlate with lock-manager activity without recompiling the server. What mechanism baked into the Postgres binary lets us pull that correlation, and does it involve patching anything in production?",
    # 04407 Mindful-eating first-bite rule: 20 chews, fork down
    "I'm trying to rebuild a slower eating habit. What's the exact first-bite rule that starts the meal off right, and roughly when in the meal does the discipline tend to fall apart even when it does work?",
    # 04408 Pact pending state lets new consumer publish failing contracts
    "A new consumer team wants to publish Pact contracts that are still stabilising without breaking the provider pipeline. What Pact feature is designed for that situation, and what does it let the provider build do in the meantime?",
    # 04409 TensorRT-LLM vs vLLM summarisation
    "We're running both vLLM and TensorRT-LLM on the same model. Which of the two wins on single-stream latency for the summarisation endpoint, and which one is still the right pick when concurrency matters more?",
    # 04410 Sino-Tibetan linguistic grouping
    "I've been reading a primer on language families and something was unclear. How does the Sino-Tibetan family lump Chinese together with Tibeto-Burman, and how settled is the internal subgrouping beyond those two branches?",
    # 04411 pnpm patch fixed broken third-party SDK type
    "A third-party SDK shipped a broken TypeScript type and we needed to unblock work before waiting on upstream. Which pnpm feature let us patch the package locally and commit the diff, and did the upstream PR happen before or after?",
    # 04412 git-absorb changed stacked-diff review loop
    "Our stacked-diff review loop used to involve a lot of interactive rebasing to land WIP fixes on the right commit. Which tool ended up simplifying that workflow, and what does its single command actually do to your pending edits?",
    # 04413 Bun fetch reuses one HTTP client per origin
    "Webhook fan-out on our old runtime was churning TCP connections. After we ported the service, what did the new runtime's fetch implementation do differently at the connection layer, and how did that show up in our metrics?",
    # 04414 Realm backs offline sync queue on partner tablet app
    "Someone floated ripping Realm out of the partner tablet app and replacing it. Why does it still back the offline sync queue there, and what exactly about its live-objects model would a replacement need to match?",
    # 04415 noise: checking partition spec
    "The other side just paused and said they were verifying a partition specification. Is that a meaningful signal about the system state, or just a brief filler while they check their notes?",
    # 04416 noise: tailing logs
    "I just got a short aside about tailing log output while we wait. Should I treat that as a substantive pause in the conversation, or is it the kind of filler that just precedes the real answer?",
    # 04417 Dad's Medicare Part B premium + IRMAA 2026
    "The 2026 Medicare bill for Dad jumped this year and I'm trying to reconcile why. What's the new Part B premium, and which income threshold from the 2024 MAGI triggered the IRMAA surcharge on top?",
    # 04418 Buckner default mode network + early Alzheimer amyloid
    "I'm trying to line up the neuroscience with the clinical picture of early Alzheimer disease. Whose body of work ties default mode network dysfunction to early amyloid deposition, and where on the cortex does that overlap sit?",
    # 04419 rubber duck with knit scarf on fridge
    "I'm trying to describe a strange decoration I spotted in the kitchen earlier. What exactly was sitting on top of the fridge, and was it wearing anything particular that made it stand out?",
    # 04420 Mono-ha raw materials in late-1960s Japan
    "An art-history friend was quizzing me about post-war Japanese movements. Which group in late-1960s Japan foregrounded raw material encounter, and what kinds of materials did they tend to arrange in their presentations?",
    # 04421 noise: site report before quoting date
    "The other person said they wanted to dig something out before committing to a date. Is that a meaningful hold, and should I push back on the pause or just let them check the reference first?",
    # 04422 Orthodox Nativity Fast broken once, Fr Demetrios guidance
    "Last year's Nativity Fast was the first time I really attempted it end to end. When did it start, what broke it along the way, and what did Father Demetrios actually tell me to do when it did?",
    # 04423 noise: looking at file before changes
    "The other side just said they wanted to read something before touching anything. Is that a substantive review step I should plan around, or just a pause before the real work begins?",
    # 04424 cat walked across keyboard
    "We had a small interruption a moment ago that wasn't the usual system blip. What exactly happened on the other side, and was it the kind of thing that actually needed hands-on intervention?",
    # 04425 noise: tough call
    "I asked about one of the trickier calls a moment ago and got a non-committal reply. Was that an acknowledgement that it's genuinely a hard judgement, or more of a filler while they thought?",
    # 04426 Projection Lab split chart, backdoor Roth costing $2400/yr
    "I've been reviewing the retirement-account split in the budgeting tool. Which chart in Projection Lab revealed the backdoor Roth timing problem, and roughly how much ordinary income was it costing per year?",
    # 04427 Aerosol cooling partly masks warming
    "A newsroom piece claimed we know exactly how much aerosols cool the climate. How does anthropogenic aerosol cooling physically offset greenhouse warming, and how well pinned down is the actual magnitude?",
    # 04428 Reflux condenser possibly leaking toluene
    "Something smelled off in the lab hood a second ago and I flagged it to the other person on the bench. What exactly did I say I was smelling, and which piece of glassware was I worried about?",
    # 04429 kettle whistling in hallway
    "The background noise on the call just got louder and I had to step away. What was actually going on down the hallway, and was it the kind of thing that needed handling right now?",
    # 04430 cargo tree --duplicates surfaced four serde minor drifts
    "We were tightening up a Rust release audit and wanted to catch duplicated transitive deps. Which cargo command surfaced the four minor-version drifts of serde, and what would have happened without it?",
    # 04431 Adolescent synaptic pruning reshapes prefrontal circuits
    "I was explaining teenage cognitive development to a friend and got the mechanism a bit hazy. How does synaptic pruning reshape prefrontal circuits during adolescence, and what kinds of connections survive that process?",
    # 04432 Zipf's law token frequency 1/n
    "I'm trying to remember the exact statement of Zipf's law. How is the frequency of the nth most common token in a corpus related to n, and what's the simple formulation of that relationship?",
    # 04433 office plant near printer points at coffee machine
    "There's a tiny office quirk I keep noticing. What's happening with the plant next to the printer, and what direction has its crooked shoot actually grown toward over time?",
    # 04434 Grief after Dad's death cracked faith open
    "Someone asked me how I'd describe the effect of grief on my faith recently. What happened after Dad died last spring, and what was the honest response I kept giving for about six months before the parish?",
    # 04435 noise: unmute
    "The other person just said something about hearing me and unmuting. Is that a meaningful connection issue I should wait for, or just a filler as they get back into the call?",
    # 04436 Fundamental theorem of calculus
    "I was sketching out the big ideas of first-year calculus for a tutoring session. What's the one-line summary of the fundamental theorem of calculus and what two operations does it actually tie together?",
    # 04437 office plant by window flowering after moving near heater
    "A coworker mentioned one of the office plants started blooming again recently. Which plant was it, and what small thing did someone adjust about its position that seems to have caused the change?",
    # 04438 noise: resolver propagating
    "The other side said they needed a moment for something to propagate. Is this the kind of pause where I should just wait quietly, or is there something on my end that might be relevant to check?",
    # 04439 WezTerm Lua config, per-domain launch profiles
    "Prod typos into the wrong SSH host had been a near-miss for us. Which terminal emulator's configuration ended up preventing that, and what visual trick does each per-domain profile actually use?",
    # 04440 noise: VM resuming from snapshot
    "The other person just said their VM was still coming up. Is that a hard wait I should budget for, or more of a quick interruption before we can keep going?",
    # 04441 Outback annual service with Dmitri, March 2026, £412
    "I'm trying to remember what the car bill looked like last month. When did the Outback go in for its annual service, who did the work, and what came to on the invoice including the extras?",
    # 04442 Prometheus client_golang: Inc over Add(1) skips float conversion
    "A code-review comment flagged Add(1) on a Prometheus counter. Why does the Go client prefer Inc over Add(1) on a counter, and what did a quick benchmark show was happening in the hot loop?",
    # 04443 Library friends group renewed 2026-01-09, £25, AGM voting
    "The annual subscription to the local library friends group came through in early January. What was the fee this year, and what exactly does it get me in terms of rights and early access?",
    # 04444 noise: checking notes
    "The other side just said they needed to check their notes. Should I read anything into that pause, or is it pure filler until they've glanced at whatever they were trying to remember?",
    # 04445 Optically stimulated luminescence dating beyond radiocarbon
    "An archaeologist friend was explaining how they date sediment beyond radiocarbon range. What does optically stimulated luminescence actually measure, and what's the event it pins down in the history of a sediment sample?",
    # 04446 Step Functions Standard for year-long SLA, Express cap
    "Our long-duration workflow for yearly SLAs needed to survive past any short execution cap. Which Step Functions tier is carrying it, and what specifically ruled out the cheaper option from handling the long path?",
    # 04447 Diaspora Pragati turmeric triggered HA notification via Sahil Bloom iCal
    "The Home Assistant notification that fired in mid-March was a bit Rube Goldberg. Which turmeric arrival triggered it, and which newsletter's iCal event hooked into the order webhook to make it happen?",
    # 04448 Mira Ceramics DM on Instagram, off-platform Wise payment
    "I bought a ceramic piece directly from a maker rather than through Etsy in late February. Which seller was it, how did we actually end up transacting, and what did that save us both in the process?",
    # 04449 Type II supernovae, SN 1987A nearby example
    "I was explaining supernova endpoints and blanked on the closest well-studied example. What do Type II core-collapse supernovae leave behind, and which nearby event in the Large Magellanic Cloud is still the reference modern case?",
    # 04450 noise: pulling up the map
    "The other person just paused and mentioned pulling something up. Was that an actual map reference I should wait for, or is it the kind of filler that doesn't really indicate progress?",
    # 04451 Alacritty on low-spec boxes, 60 fps on Pi 4
    "Some of our low-spec dashboards still run a minimal terminal. Which one is it, and what property of it actually keeps it at full frame rate even on the Raspberry Pi cluster?",
    # 04452 noise: catalogue raisonne attribution
    "The other person said they needed to check an art-history reference before committing to something. Is that a substantive pause for a real attribution question, or just a polite delay before they answer?",
    # 04453 lang attribute on html and spans, German press page English bios
    "Screen reader voices were switching incorrectly on one of our multilingual pages. What change did we make at the markup level, and specifically which page benefited from the inline language tags on embedded bios?",
    # 04454 Homelab cookbook deadline 2026-06-30 Toronto meetup
    "The side project with Nadia has a fixed end date tied to an event. When does the homelab cookbook need to be finished by, and which meetup are we aiming to present it at?",
    # 04455 TCK identity, home town question, default to Berlin
    "A friend asked how I answer the home-town field on forms these days. Given that I was born in Manila and raised across Dubai and Singapore, what do I actually put down and what city tips the balance?",
    # 04456 noise: column eluting, fraction collector
    "The other person said they needed a moment because the instrument was doing its thing. What exactly was happening with their column run, and is that the kind of pause that's worth waiting through?",
    # 04457 noise: runoff vote share first or second round
    "They paused to clarify a political figure's vote share. Did they actually commit to a number, or are they flagging that they want to reconfirm which round of the runoff the figure came from?",
    # 04458 Carbon Engineering DAC plant Texas 1 Mt/yr
    "A climate policy piece mentioned a specific DAC project at commercial scale. Which company is building the plant in Texas, and how much CO2 per year is it designed to capture when it's operational?",
    # 04459 noise: kicking worker pod
    "The other side said they were bouncing a worker pod before retrying. Is this a routine hiccup, or does it indicate something deeper is misbehaving that I should be aware of?",
    # 04460 Ash Wednesday 2026-02-18 St Alban's lay-led, Rev Sinclair in hospital
    "The Ash Wednesday service this year at our parish was unusual. Who actually presided on the day, why was the usual priest not there, and roughly how long had it been since the last lay-led service?",
    # 04461 noise: think before changes
    "The other side just said they wanted to think for a moment before moving on. Is that pause meaningful to how I should respond next, or just a thinking filler I can read past?",
    # 04462 Go select with default branch avoids deadlock
    "I was reviewing a Go scheduler shim and ran into the channel pattern for non-blocking probes. How is the select statement structured there, and why does having a default branch prevent the deadlock when no peer is ready?",
    # 04463 Coral bleaching above summer max by ~1C for weeks
    "A marine biologist friend was explaining the thermal trigger for bleaching events. Roughly how far above the local summer maximum do sea-surface temperatures have to sit, and for how long, to cause widespread bleaching?",
    # 04464 Player loadout as structural diff vs class default, 60% smaller
    "The profile save blob on the game shrank significantly after a refactor. What approach are we using now to serialise player loadouts, and roughly how much smaller is the file as a result?",
    # 04465 noise: cache warming
    "The other side said the cache was warming and asked for a short pause. Should I treat this as a quick filler, or does it suggest we're about to see visibly slower responses until it finishes?",
    # 04466 Turbopack HMR <50ms on 200k-LOC Next app
    "We were sceptical the new Next.js bundler would hold up on a large codebase. How fast did hot module replacement actually stay on a 200k-line app, and what design choice in the bundler made that possible?",
    # 04467 noise: checking translation
    "The other person paused to double-check which translation of a passage they were quoting. Should I treat that as a meaningful accuracy hedge, or just a pause before they finish the quotation?",
    # 04468 IdeaVim in IntelliJ, ~/.ideavimrc Plug for visual-block
    "One of our engineers insists on keeping Vim muscle memory inside IntelliJ. What plugin covers most of that, and what residual pattern still needs a specific Plug entry in the config file to work right?",
    # 04469 Sublime Text 4 <300ms boot, 2 GB log tailing
    "Post-mortem log analysis on the ancient build server needs something that starts fast. Which editor did we keep around for that job, and what size of log file does it cope with day to day?",
    # 04470 noise: pre-registration covered delayed or immediate post-test
    "The other person paused to reconsider a pre-registration detail. Are they verifying something substantive about their study protocol, or is this more of a rhetorical hedge before they answer?",
    # 04471 Redland flat leaving 2026-04-09 harder than expected
    "The move last week hit harder emotionally than I expected to admit. What specifically made leaving the flat tough, and what details of the building and neighbours stuck with me the most?",
    # 04472 noise: exhibition dates
    "The other side paused to double-check a set of exhibition dates before giving them. Is that substantive or just ordinary caution before committing to specific calendar information?",
    # 04473 HNSW vs IVF-PQ recall@10 went 0.86 to 0.97
    "We re-ran the small-to-medium recall benchmark and saw a big jump. Which index replaced IVF-PQ, and what did recall@10 actually move to at the same query budget after the switch?",
    # 04474 Airbnb review streak 4.93 in 2025, parking permit
    "The Airbnb review stats came in for 2025. What rating did the listing average across the year, and what single category kept dragging the score down that I can't actually fix from my side?",
    # 04475 Engagement ring resized size M to K at Beaverbrooks 2026-04-02
    "Clara's engagement ring went in for resizing earlier this month. Which jeweller handled it, what was the actual size change, and what administrative step came right after on the same day?",
    # 04476 Dog refuses everything except salmon and peanut butter
    "Friends were asking if our dog is picky about food and I laughed a little. Which two specific things will it reliably eat, and what's the failure mode with just about everything else we've tried?",
    # 04477 noise: control plane reconciling
    "The other side paused and said the cluster's control plane was still sorting itself out. Should I keep waiting quietly, or is that hint actually a sign something is broken rather than recovering?",
    # 04478 Microwave buzz breaking concentration during bug hunt
    "There was an annoying environmental noise that wrecked my focus during a tricky debugging session recently. What exactly was the source, and roughly what was I trying to get done while it was happening?",
    # 04479 Signet ring 9ct rose gold reset by Rebus 2025-09, original engraving
    "I was asked about the signet ring on my right hand. What material is it made of, who did the reset last year, and what detail from the original piece deliberately stayed untouched during the work?",
    # 04480 noise: pull something up
    "The other person said to hang on while they pulled something up on their side. Is that a meaningful pause for me to worry about, or more of a rhetorical stall before they answer the real question?",
    # 04481 Shallice and Warrington patient KF 1970 short-term vs long-term
    "A cognitive neuroscience intro was talking about classic dissociations in memory research. Which 1970 patient case from Shallice and Warrington is the reference, and what did their memory profile challenge about the dominant model at the time?",
    # 04482 'morriña' Galician homesickness, ache for A Coruña sea smell
    "I was trying to describe a feeling in English that didn't quite fit. Which Galician word did my grandmother use instead, and what exact sensory memory does that word actually point to for me?",
    # 04483 DTI tractography anisotropic water diffusion
    "A neuroimaging course was covering how we see long-range white matter bundles in vivo. What specifically does DTI tractography model physically, and what does that let us reconstruct in the brain?",
    # 04484 Advent wreath 2025-12-01 lit by Aoife, purple candle for hope
    "The Advent wreath went up at home at the start of last December. Who lit it that first Sunday, which candle did we start with, and what else is sitting alongside it on the dining table?",
    # 04485 direnv + uv-python auto activates interpreter on cd
    "Managing per-project Python versions by hand kept getting stale. What combination of tools is handling interpreter selection on directory change now, and what did that eliminate from the day-to-day workflow?",
    # 04486 Valtio derive helper for computed layout
    "We wanted a layout computation that tracks updates without us wiring effects everywhere. Which state library supplies the derive helper we used, and how does the derived recomputation actually get triggered?",
    # 04487 GLiNER-small 50ms per 200-token input on RTX 5060
    "I was benchmarking the small extraction model on my home GPU. What hardware did I run it on, and how fast did inference come in per 200-token input on that card?",
    # 04488 One Sec pause Q1 2026, 1142 attempts, 684 opens blocked, 60% abandonment
    "The phone-use data for the first quarter of this year came in. How many pause attempts did the intervention app log, how many app opens did it actually block, and what abandonment rate fell out of that?",
    # 04489 SDK raw_response property exposes headers, status, request id
    "Power users of our SDK were asking how to get at transport-level information without dropping to a low-level client. Which property on the return object exposes it, and what three things specifically can they read off it?",
    # 04490 AeroPress ratio 14g/220ml at 85C
    "I've been tinkering with my morning coffee for a while and finally settled. What's the ratio I now brew my AeroPress at, and what water temperature do I keep it at each time?",
    # 04491 Rachio 3 controllers, drip lines before summer 2026
    "The garden irrigation plan came up at dinner again. What hardware are we intending to rebuild it with, and roughly when do we want that plus the drip lines ready to go?",
    # 04492 Whiteboard marker dried out three days before kickoff
    "There was a minor supply-closet mishap right before the on-site sprint kickoff. What exactly went dry on the mobile pod, and how many days ahead of the kickoff did it happen?",
    # 04493 noise: reopen Cypher session
    "The other person said they were about to reopen a Cypher session before continuing. Is that a meaningful tool context they need, or more of a filler pause I can safely talk through?",
    # 04494 Tokyo gaijin card replacement 40 min at Shinjuku-ku Yakusho 2025-08-11
    "The residence card replacement in Tokyo last summer went smoother than expected in person. Where did I do it, how long did the actual counter visit take, and what was the real bottleneck in the process?",
    # 04495 noise: top up the jug
    "The other side said they were going to refill a jug before continuing. Is that a substantive interruption, or is it the kind of small aside I can just wait out without reading anything into it?",
    # 04496 Libby via Fairfax County, OverDrive Advantage, three copies
    "My Kindle wishlist has been getting absurd and I'm trying to borrow more of it. Which library card covers most of it, and what's the platform underneath that makes availability so reliable for new releases?",
    # 04497 GLiNER small training 40 min per epoch on RTX 5060
    "I was pricing out home fine-tuning on my consumer card. Roughly how long does one epoch of GLiNER small training take on an RTX 5060 at home, and does that feel workable over a weekend?",
    # 04498 Turbo remote cache auth, short-lived per-CI-job token
    "Forked PR runners used to linger with team-wide tokens in their cache setup. How does Turbo remote cache authenticate CI jobs now, and what changed so stale tokens don't persist in fork runners?",
    # 04499 Bridget Riley op-art geometric rules
    "A gallery guide was framing op-art in terms of rules rather than spontaneity. Which artist's paintings are the reference example, and what exactly generates the optical vibration in her compositions?",
    # 04500 Apple VideoToolbox on M2 Mac mini vs Intel N100 QuickSync
    "Infuse library thumbnails used to churn overnight on an older home-theatre box. Which machine and hardware pipeline do we use for them now, and how much faster is it compared to the Intel setup that came before?",
    # 04501 Parca continuous profiling caught slow leak below OOMKill
    "A slow memory leak in the API gateway was sneaking under the OOMKill threshold and never triggering alerts. What observability tool finally caught it, and what kind of profiling was it doing over time to do so?",
    # 04502 Opal Deep Focus 2026-03-25 06:30-09:00, essay finished
    "The morning deep-focus session in late March actually produced something. When did it run, which apps did it block, and what did I manage to get done in that single sit-down?",
    # 04503 Nextdoor reunited Councillor Park's beagle via Bayview crosspost
    "The lost-pet story from last week had an interesting network shape. Whose dog was it, on which platform did the reunion start, and what detail about a cross-post to another platform actually closed the loop?",
    # 04504 Grief sessions for Nan, continuing-bonds frame, Dr Halpern
    "Therapy around Nan's death had been stuck on five-stages framing and wasn't helping. Which alternative frame did the clinician use instead, and what specific permission turned out to be the unlock?",
    # 04505 Coursera Scala specialisation, Akka cluster on laptop
    "I've been trying to internalise actor supervision for years and finally got it. Which online course did I take to land that, and what hands-on setup on the capstone finally made it click?",
    # 04506 noise: pull up the right page
    "The other person said they wanted to pull up the right page first. Is that a meaningful pause I should budget time around, or the sort of filler where I can keep talking through it?",
    # 04507 noise: re-pull funnel plot
    "The other side asked for a moment to re-pull a funnel plot before claiming anything. Are they flagging a real methodological concern, or is this just a hedging pause?",
    # 04508 Critical regionalism, Kenneth Frampton, local climate/material/topography
    "An architecture friend mentioned a framework that pushes back on globalised modernism. Which theoretical stance is it, who articulated it, and what three local anchors does it ask architects to ground buildings in?",
    # 04509 Maggie Appleton garden post explained Obsidian graph shape
    "Last weekend I went down a rabbit hole about why my note graph looked so chaotic. Whose post set it off, and what did it help me see about the difference between my vault's graph and a well-kept one?",
    # 04510 SDK Endpoint<TPath, TMethod> conditional types derive request/response
    "The IDE now autocompletes API paths from the spec without hand-maintained types. What TypeScript construct in the SDK drives that, and how are the request and response types derived in practice?",
    # 04511 Pydantic v2 discriminated union Field(discriminator='kind')
    "Our Event model had become a mess of duck-typed unions. Which Pydantic v2 feature tightened it up, what's the actual field hint, and what benefit did the OpenAPI export see from the change?",
    # 04512 noise: striatum anatomy
    "The other person said they needed to double-check a brain region before committing to a label. What specifically were they hesitating on, and is that pause a signal they'll come back with a correction?",
    # 04513 gRPC streaming HTTP/2 multiplexing, head-of-line blocking at TCP
    "Someone claimed gRPC streaming fully eliminates head-of-line blocking thanks to HTTP/2. Is that actually true at every layer, or does the blocking still surface somewhere specific in the stack?",
    # 04514 noise: ablation in appendix or main text
    "They paused to check whether an ablation figure was in the main paper or the appendix. Is this a substantive correction they're about to make, or just a cautious pause before referring to the result?",
    # 04515 Valgrind DHAT surfaced retained allocation jemalloc rounded away
    "Jemalloc stats had been hiding a parser retention bug in the noise. Which profiling tool finally surfaced the retained allocation, and what did the existing stats collector appear to be doing with the signal?",
    # 04516 Driveway 4.9m, Niro fits, Outback 4.82m needs road
    "Parking both cars at home has been an awkward negotiation. What's the exact driveway length, which car does it fit nose-in, and why does the other one have to go out on the road instead?",
    # 04517 esm.sh for prototypes, CSP had to allow host
    "We wanted install-free demo prototypes that just run. Which CDN are we using for the ESM imports, and what trade-off did we have to accept on the security-policy side to make it work?",
    # 04518 Fields Medal first 1936 Oslo ICM, under 40, IMU
    "I was telling someone how the Fields Medal differs from the Nobel and blanked on some specifics. When was it first awarded, what age cap applies, and which international body administers it?",
    # 04519 Ebbinghaus forgetting curve exponential decay over hours
    "A study-skills coach was pointing at research behind spaced repetition. Whose forgetting curve is the original reference, what specifically does it describe, and roughly what shape does unreinforced memory decay follow?",
    # 04520 WASI component model for CLIs parked until Q3 due to debug tooling
    "We looked at the WASI component model for some CLIs but held off. What was the reason we parked that spike, and when did we plan to revisit the idea?",
    # 04521 noise: baby monitor chirping
    "A small background interruption pulled the other side away for a moment. What specifically was going off in their house, and is that the kind of pause that usually resolves quickly?",
    # 04522 coffee-machine filter light blinks morse for help
    "There's a running joke in the office about a piece of kitchen hardware. What's the device, and what exactly is its blink pattern oddly reminiscent of lately?",
    # 04523 BaBar at SLAC CP violation in B-mesons 2001-2008, CKM
    "I was refreshing on experimental confirmations of the CKM picture. Which experiment at SLAC published the key CP-violation measurements in the B-meson system, and what was the journal and rough window of publication?",
    # 04524 Cook's theorem SAT NP-complete first complete problem
    "A theoretical CS revision prompt came up and I wanted to nail the history. Which theorem first established that Boolean satisfiability is NP-complete, and what did that result actually give the field?",
    # 04525 Brother-in-law Arash pays lawn service, we reimburse quarterly
    "The household finances include a small quarterly reimbursement. Who pays the lawn service directly on our street, and how does the settlement with him actually happen each quarter?",
    # 04526 Espresso machine floor two stopped leaking after drip tray replaced
    "A long-running hardware nuisance at the office finally got fixed this week. What was the issue, which floor was it on, and what did someone quietly replace to make it go away?",
    # 04527 Luigi on legacy Hadoop pipelines
    "Our Hadoop-era pipelines never migrated off their orchestration tool. Which tool stayed on the legacy batch jobs, and what about its design made it a fit for checkpoint-heavy work?",
    # 04528 Buzsaki hippocampal sharp-wave ripples, offline replay
    "A neuroscience lunch seminar was about memory consolidation. Whose group has recorded the hippocampal sharp-wave ripples most influentially, what do they compress in behavioural terms, and what role are they hypothesised to play offline?",
    # 04529 Foreman + Puppet on bare metal, build DB source of truth two years
    "The data-center side held onto its old stack longer than the cloud side. Which two tools were running legacy provisioning, and for roughly how long did their build database remain the source of truth after Terraform landed?",
    # 04530 Knee brace helped Dolomites hike
    "I was reminiscing about a trip that could have been derailed by my knee. Which piece of equipment actually saved the hike, and which trip afterwards went through without another flare-up?",
    # 04531 Doom-scrolling log Jan-Mar 2026, Reddit 41%, Freedom weekday profile
    "The first-quarter attention log came back and Reddit was the worst offender. What percentage of idle time did it eat, and what specific Freedom profile have I set up now to deal with it on weekdays?",
    # 04532 Lucene segments immutable, merge policy compacts
    "Someone was confused about why deletes are cheap in Lucene even though data is on disk. What's actually happening at the segment level, and what does the merge policy do in the background to compact everything?",
    # 04533 Brewfile snapshots, brew bundle dump diff
    "Reproducible macOS base images had been painful to keep honest. Which Homebrew feature are we using now, and what specific workflow catches drift between a clean install and what's supposed to be installed?",
    # 04534 World Weather Attribution rapid attribution studies
    "A news piece about a recent extreme event cited an attribution study. Which group runs those rapid analyses, and what question exactly does their methodology try to quantify about the role of climate change?",
    # 04535 Kepler transit method 2009-2018 replaced ground-based
    "A space-science article was tracing the dominant exoplanet detection pipeline over time. Which NASA mission took over from ground-based transit surveys, what method did it use, and what years did it operate?",
    # 04536 noise: second monitor for config files
    "The other person mentioned juggling too many config files at once. Is that a real ergonomic concern they're going to act on, or more of a lighthearted aside I can let go past?",
    # 04537 Birdwatching 142 species London, firecrest at Walthamstow
    "My birdwatching log is up to a decent count for the London area. Roughly how many species is that, and what was the most memorable sighting last Sunday that I haven't shut up about?",
    # 04538 Williamson transaction-cost economics, Coase 1937 Nature of the Firm
    "An economic-governance seminar traced a specific lineage of theory. Whose transaction-cost framework extends Coase's 1937 paper The Nature of the Firm, and what two concepts did it add as governance drivers?",
    # 04539 noise: grabbing explain plan
    "The other side said they needed to grab an explain plan before discussing something. Should I treat that as a meaningful investigative pause, or is it closer to a stall tactic before they answer?",
    # 04540 Clara's mother Ileana Sunday 17:00 phone call
    "There's a standing weekly call in my calendar that means a lot more than it started as. Who's the call with, when does it happen, and what incident did it originally come out of?",
    # 04541 Valtio proxy for drag-and-drop, subscribers only fire for touched keys
    "The drag-and-drop state on our board was making subscribers re-render too eagerly. Which library are we using for the ephemeral proxy, and what precisely is the subscriber behaviour now when only position.x changes?",
    # 04542 Kurrent EventStoreDB successor, client libraries compatible
    "We've been watching the EventStoreDB brand evolve. What's the successor brand we added to the evaluation shortlist, and how big a change was needed for existing client libraries to work against it?",
    # 04543 Many Labs 2, thirteen of twenty-eight effects replicated
    "A psychology-methods class was debating replication. Which large multi-lab project reported how thirteen of twenty-eight classic effects held up at full sample, and what does that headline number actually mean in that context?",
    # 04544 Diamond ferret rewiring, retinal inputs to auditory thalamus
    "A developmental neuroscience lecture referenced classic cross-modal plasticity work from the late 1990s. Whose ferret rewiring experiments are the reference, and what did they show happens when you route retinal inputs to auditory thalamus?",
    # 04545 gron flattens JSON into greppable paths vs deep jq
    "Deep jq expressions kept becoming unreadable on some logs. What tool did I switch to instead, and how does it change the way you actually search through nested JSON content?",
    # 04546 TanStack Query onMutate optimistic + setQueryData rollback
    "The comment composer's optimistic writes needed a clean rollback path. Which TanStack Query hook drives the optimistic write, and how is the revert handled if the mutation fails?",
    # 04547 noise: pulling up something
    "The other person asked for a moment to pull something up. Is this a meaningful pause to plan around, or the sort of routine filler I can ignore and keep the conversation moving through?",
    # 04548 Friday Jummah 13:15 winter 13:45 summer, Imam Yusuf sabr khutbah 2026-03-20
    "Friday prayers at my mosque have a seasonal time change I always have to remember. What are the winter and summer prayer times, and whose khutbah on patience from late March has stayed with me?",
    # 04549 Dependabot grouped patch weekly, security individual
    "We tuned Dependabot to stop drowning people in small PRs. How are routine patch updates grouped now, and why are security alerts still allowed to open individual pull requests?",
    # 04550 Retrieval eval headline recall@k and MRR, nDCG secondary
    "The retrieval evaluation harness needed a small stable set of metrics for reviews. Which two metrics ended up being the headline numbers, and what kept nDCG as only a secondary view in the reports?",
    # 04551 OpenSearch k-NN Lucene HNSW from 2.4, swap from nmslib cut memory
    "OpenSearch 2.4 quietly changed the k-NN backend. What engine did it switch to, what library had been handling vectors before, and roughly how much did memory overhead drop at the same recall?",
    # 04552 NDJSON and JSON Lines equivalent in spec
    "Two producers were emitting what looked like different formats to the loader. How did the specification treat NDJSON versus JSON Lines, and what did the loader do on the extension side to keep backwards compatibility?",
    # 04553 origami crane on whiteboard eraser
    "Someone left a small paper object by the whiteboard earlier. What exactly was it, how was it folded, and where was it placed that made it easy to notice on the way in?",
    # 04554 noise: coat left at table
    "The other person suddenly realised they'd left something personal behind. What was it, where had they left it, and is that the kind of pause that means we'll need to wait a while before resuming?",
    # 04555 MTEB bge-large beat e5-base by 4 points at 2x inference cost
    "Embedding model selection on the MTEB-style leaderboard produced a clear winner-with-tradeoff. Which model came out on top, by roughly how many points, and what was the cost we had to swallow to pick it?",
    # 04556 noise: index warming up
    "The other person said their index was still warming up. Does that warrant a real pause, or is this filler that means they can keep talking while the system catches up in the background?",
    # 04557 Methane satellites show oil and gas leaks beat official inventories
    "A climate explainer article said atmospheric methane budgets don't match the inventories. What's the rough pattern for oil and gas leakage, and what kind of measurement is driving the revised estimates?",
    # 04558 Off-CPU flame graphs showed workers on semaphore
    "CPU-only flame graphs had been blaming the wrong thing on a perf investigation. What kind of flame graph finally revealed what the workers were actually doing, and where were they spending their time?",
    # 04559 Kids' birthday in garden, downstairs loo kiddie step, Anya friends forget towel
    "We've settled into a standard routine for the kids' summer birthday parties. What's the main venue at home, what adjustments do we make to the downstairs loo, and what do Anya's friends always manage to forget?",
    # 04560 Kia Niro EV Zappi 7kW installed 2026-03-29 by Octopus £1,150 after grant
    "The home EV charger went live recently. Which charger brand and rating did we install for the Niro, who did the installation, and what did it actually cost after the grant?",
    # 04561 New Criticism mid-century, close reading as self-contained artifact
    "A literature refresher brought up a dominant mid-century Anglophone school. Which school is it, what did it treat the poem as, and what method did it centre in practice?",
    # 04562 David Silver DeepMind AlphaGo/AlphaZero/MuZero
    "Someone asked which researcher ties together the AlphaGo, AlphaZero, and MuZero projects. Which DeepMind group does he lead, and which research thread has he been the throughline on?",
    # 04563 noise: SMJ May or August issue
    "They paused to verify whether a Strategic Management Journal piece was the May or August issue before citing it. Is this a substantive reference check or just a careful hedge?",
    # 04564 three pigeons on windowsill arguing
    "There was a lovely little distraction at the window earlier. How many pigeons were involved, roughly how long did it go on, and what was the obvious-but-opaque subject of their argument?",
    # 04565 GRACE satellite ice-sheet mass loss since 2002
    "Ice-sheet mass loss numbers keep getting quoted with increasing confidence. Which satellite mission underpins the direct gravity-based estimates, and since roughly when has it been operating in the background?",
    # 04566 2026-04-12 Italian-night menu via Paprika 3 web clipper Hazan sauce
    "Last weekend's Italian-night menu came together through a slightly convoluted clipping workflow. Which recipe did we pull, which app's web clipper did it, and what did our usual recipe app fail to parse that forced the switch?",
    # 04567 Strontium isotopes in tooth enamel, childhood mobility
    "An archaeology podcast was describing how we reconstruct individual life histories from bones. Which isotope in which tissue helps map childhood mobility, and what does it actually correspond to geologically?",
    # 04568 Post-1945 decolonisation, Asia and Africa, arbitrary colonial borders
    "I was sketching a twentieth-century history timeline for a student. What global wave replaced European colonial administration after 1945, and what inheritance did it leave in the shape of successor states?",
    # 04569 noise: size tag
    "The other person paused to check a size tag on something before they forgot. Is that a meaningful retail-level pause to wait through, or more of an aside I can just nod along with?",
    # 04570 Barista seasonal poems on takeaway cups
    "There's a small weekly delight from a local cafe I keep looking forward to. Which person at the shop started doing it again this month, and what exactly are they writing on the takeaway cups?",
    # 04571 noise: ordination date against diocesan archive
    "They asked for a moment to verify an ordination date against a diocesan archive. Is that the sort of detail they'll come back with a correction on, or just a careful pause before citing?",
    # 04572 Byzantine fault tolerance >2/3 honest for safety
    "A distributed-systems reading group came back to the classic fault-tolerance thresholds. Under Byzantine fault tolerance, what fraction of participants has to be honest for the system to stay safe against arbitrary failures?",
    # 04573 Community choir St Mary's every other Wednesday, Ruth sopranos
    "Someone was asking whether I still do the choir thing. Where does the community choir meet, how often does it run, and who actually looks after the soprano section?",
    # 04574 Preact signals rendering shell dependency tracking no useEffect
    "The real-time tick counter in the rendering shell works without a single useEffect. Which library's primitive carries the value, and how does the dependency tracking get wired up implicitly when a component reads it?",
    # 04575 Patagonia return 2026-03-18 Happy Returns QR Staples kiosk
    "Returning the Patagonia order last month was easier than expected. Which returns platform handled it, where did I drop the item off, and what did the QR-code flow let me skip entirely?",
    # 04576 Crystal type inference CLI rewrite, ll.bc cache kept compiles sharp
    "A hobby CLI rewrite stayed pleasant despite being in a more static language. Which language was it, how much manual typing did it need, and what specifically kept the incremental compile times fast?",
    # 04577 Bike commuted 184/220 days 2025, Feb and Nov worst
    "The 2025 cycling-commute total came in under target but the distribution surprised me. How many days did I make it out of 220, and which two months ate the most weather days against my earlier guess?",
    # 04578 JetBrains Rider profiler, attach-and-sample menu item
    "Adoption of profiling inside our team jumped after a tool change. Which IDE's profiler made attach-and-sample into a menu item, and what cultural shift followed once using it was this easy?",
    # 04579 Shadow reviews: senior leaves non-binding PR comments, staff rolls up
    "We've been experimenting with how aspiring seniors practise review work. What's the process called, who writes the comments first, and how do they make their way back to the author in the end?",
    # 04580 240 whips into brook corridor 2026-02-07, tread don't stamp
    "The tree-planting day in early February felt properly organised. How many whips went into the brook corridor, and what specifically were volunteers told to do and not do with the root balls?",
    # 04581 Frank Press 1960 Chile earthquake normal modes, Lamb 1882
    "A seismology lecture tied twentieth-century observation back to a nineteenth-century prediction. Whose free-oscillation studies of the 1960 Chile earthquake confirmed the normal-mode spectrum, and who originally predicted it?",
    # 04582 Helioseismology Sun interior pressure modes, Bahcall neutrino problem
    "A solar-physics overview mentioned calibrating the Sun's interior against standard models. What method probes it through pressure modes, and which figure's benchmarking is tied to the solar neutrino problem?",
    # 04583 Jenny Odell How to Do Nothing 2025-12-29 reframed phone detox
    "My attitude toward phone detoxing changed after a book I finished last December. Which book was it, when did I finish it, and what reframing of attention did the argument turn on for me?",
    # 04584 noise: revisit that question in a moment
    "The other person said they'd circle back to a question in a bit. Should I plan to push them to come back to it, or is this the sort of parked item that might quietly drop?",
    # 04585 noise: grab a tea before trying passage again
    "They asked for a quick break to grab a drink before trying a passage again. Is this actually a study-rhythm pause that'll help, or just a polite way to defer something tricky?",
    # 04586 Python async context manager needs __aenter__/__aexit__
    "A junior on our team wrote an async context manager using only __enter__ and __exit__. Which dunders should they actually have implemented, and what's the reason Python needs a different pair for the async version?",
    # 04587 Nature Materials launched 2002, perovskite and 2D materials venue
    "A materials-science PhD was ranking the main publication venues. Which journal launched in 2002 has become the leading home for perovskite and 2D materials work, and whose submissions did it start pulling away from?",
    # 04588 Production embedder outputs 768-dim vectors
    "I was writing up the index dimensions for an architecture diagram. How many dimensions do our production embedder's vectors actually have, and is that what I should assume downstream components are storing?",
    # 04589 Pact provider verification caught breaking payload rename
    "A consumer team almost shipped a breaking rename on their end without anyone noticing. What testing discipline on the provider side caught it, and did the consumer even get to pulling the new build before it was flagged?",
    # 04590 Natufian culture Levant 12500-9500 BCE, sedentary before farming
    "An archaeology podcast covered pre-agricultural settlement in the Levant. Which culture is the earliest evidence for sedentary hunter-gatherer villages before farming, and what's the rough date range it's been placed in?",
    # 04591 Biochar pyrolysis low-oxygen stabilises soil carbon decades-centuries
    "A soil-science blog post was explaining how biochar can stabilise carbon in soil. How is biochar actually produced, and roughly how long does the stabilised biogenic carbon tend to stick around in amended soils?",
    # 04592 AngelScript drives boss-fight choreography, dev hot-reload
    "Designer iteration on a boss-fight flow used to require restarting the level. Which scripting language is driving the choreography in our dev build, and what feature of the hot-reload setup preserves boss phase state?",
    # 04593 Fauci led NIAID 1984-2022 HIV, H1N1, COVID
    "A public-health history primer mentioned one long-serving US institute director. Which institute did Anthony Fauci lead, over what years, and which major outbreaks was he shaping responses to in that period?",
    # 04594 Pixel 8 Digital Wellbeing grayscale vs iOS Downtime
    "My bedtime-phone experiment last quarter ran on two devices side by side. Which phone's grayscale enforcement actually held up through bedtime mode, and which platform kept silently dropping the setting?",
    # 04595 Spin WASM runtime stateless webhook cold start 800ms to 40ms
    "We briefly spiked a WASM runtime on Kubernetes for one low-volume webhook. Which runtime was it, what kind of workload did we point at it, and how dramatically did cold start actually change?",
    # 04596 Reports now 8 after reorg 2026-03-15, 6 eng + 2 design from Sonia
    "The team shape has shifted materially in the last few weeks. How many reports do I have after the 2026-03-15 reorg, what's the engineer-to-designer split, and who did I inherit most of them from?",
    # 04597 Hugo's microchip 985112004128756 Petlog address updated 2026-04-02
    "The dog's records needed updating right after we moved. What's his microchip number, which registry is it with, and when did I change the address there in relation to the move?",
    # 04598 Vindolanda waterlogged wooden writing tablets Roman frontier
    "A Roman archaeology talk was on everyday life at the frontier. Which site's waterlogged deposits preserved hundreds of wooden writing tablets, and how did that discovery change what we know about military life there?",
    # 04599 noise: plan still running
    "The other side just said to hang on while a plan was still running. Is that a signal that something is genuinely slow or stuck, or the routine sort of wait I should read no deeper meaning into?",
    # 04600 Yogacara alayavijnana, Asanga and Vasubandhu, 4th c. CE
    "A Buddhist philosophy reading group was discussing the storehouse consciousness. Which school articulated it, who are the two main figures associated with its classical formulation, and roughly when did they write?",
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
