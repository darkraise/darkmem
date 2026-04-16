"""One-off emitter for retrieval aug batch-001 — paraphrase kind over 250 aug_sources rows.

Writes 250 rows to data/v2/retrieval/aug_001.tmp.jsonl with ids ret-03001..03250.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "v2" / "retrieval" / "aug_sources" / "aug_001.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "aug_001.tmp.jsonl"
QUERY_KIND = "paraphrase"

# One paraphrase query per source row, ordered to match the sources file.
QUERIES: list[str] = [
    # 001: Mantine hooks package, CSS-free, 110 KB saved on marketing bundle
    "bundle savings from importing Mantine hooks without styles",
    # 002: IPCC distinguishes afforestation, reforestation, avoided deforestation
    "land-use categories IPCC separates for carbon accounting",
    # 003: Serious Eats rabbit hole produced wok burner CSV and Grafana dashboard
    "origin of the home wok-burner monitoring dashboard",
    # 004: Madhur Jaffrey Sunday curry rotation since 2025-09-14, chickpea masala keeper
    "when did the weekly Madhur Jaffrey curry experiment start",
    # 005: noise, checking notes
    "quick aside about needing to consult notes",
    # 006: Brutalism from beton brut, raw concrete civic buildings
    "etymology and aesthetic of postwar concrete civic design",
    # 007: Friday open-mic at Camden Head from 2020 lockdown guitar
    "how the Friday pub open-mic habit traces back",
    # 008: Bouldering at Arch Bermondsey Tuesday/Saturday, shared grade log
    "couple's climbing routine and how they track progress together",
    # 009: Water max density near 4 C, ice floats
    "temperature at which water is densest",
    # 010: filler uncertainty
    "hedging remark expressing uncertainty about something",
    # 011: Protothreads on AVR, MSP430 port keeps parity until Rust rewrite
    "why MSP430 firmware still uses protothreads",
    # 012: filler about checking codebook
    "pause to reference the codebook before recoding",
    # 013: Cadence stayed on risk service, Temporal migration deferred for 90-day workflows
    "reason Temporal migration was postponed on the risk service",
    # 014: Library of Alexandria gradual decline, no single fire
    "whether one fire destroyed the Library of Alexandria",
    # 015: Looker dashboard from GitHub events, time-to-first-review, TTM, reviewer load
    "where weekly code review metrics are published",
    # 016: go-fuzz from unit-test seeds found integer overflow in tariff calculator
    "bug fuzzing turned up in the tariff calculation code",
    # 017: Blue Letter Bible chronological plan at Leviticus 14 on 2026-04-12
    "progress on the chronological Bible reading plan this April",
    # 018: filler double-check
    "quick interjection saying to verify something",
    # 019: filler thinking time
    "request for a moment to consider a question",
    # 020: Sarah's Seder plate uses roasted beet, vegetarian since 2016
    "why Sarah's Passover plate substitutes a beet for the shank",
    # 021: filler about new chair lumbar support
    "offhand comment about office furniture being comfortable",
    # 022: Overnight swap of office wall clock to digital, no culprit
    "mystery of the unannounced office clock replacement",
    # 023: Rereading footnote in section four before judging rejoinder
    "plan to revisit a footnote before assessing a counter-argument",
    # 024: Apple M3 Max, Metal 3 dev kit, hardware RT, iPad-class power
    "hardware behind the studio's mobile path tracer demo",
    # 025: Muon g-2 at Fermilab, PRL 2021, 4.2 sigma above SM
    "Fermilab measurement that deviates from Standard Model muon prediction",
    # 026: Gina Perry 2013 Behind the Shock Machine contradicts Milgram narrative
    "book that challenges the clean obedience reading of Milgram",
    # 027: Beatriz Souza transition coach 2026-02-09 to 2026-04-06, £1,400
    "cost of the redundancy-period career coaching engagement",
    # 028: Kepler's three laws: ellipses, equal areas, period-distance
    "summary of planetary motion laws from Kepler",
    # 029: Mum's dementia mild to moderate between 2025-09 and 2026-03, sundowning 16:30
    "progression of mother's dementia across recent neurology reviews",
    # 030: Kraken 1099 reconciled with CoinTracker for 2025 tax year
    "tax reconciliation finally balancing for the crypto exchange",
    # 031: HoTT extends MLTT with types as spaces up to homotopy
    "how homotopy type theory reinterprets Martin-Lof types",
    # 032: Shake Shack coffee shift after $184/mo Starbucks spend flagged
    "what prompted the switch away from daily Starbucks lattes",
    # 033: Karachi to Bristol relocation 2025-04-22, meeting-style calibration took 9 months
    "hardest part of the move from Karachi to Bristol",
    # 034: Lost Generation 1920s Paris, Stein, Hemingway, Fitzgerald
    "expatriate writers who gathered around Stein in interwar Paris",
    # 035: async-profiler alloc event on Kotlin service clipped boxing hot spots
    "profiling tool that surfaced Kotlin autoboxing hot spots",
    # 036: filler about pulling up dashboard
    "pause to bring a dashboard into view",
    # 037: Early 20th century Modernism, fragmentation, stream of consciousness, mythic method
    "techniques that separated Modernist fiction from Victorian realism",
    # 038: Halifax MIP £185,000 on 2026-03-01, 4.64% five-year fix
    "terms of the Halifax mortgage in principle issued in March",
    # 039: PKI relies on trapdoor one-way functions
    "mathematical primitive underpinning public-key encryption",
    # 040: Hugo's booster at Cedar Lane 2026-05-09, lepto plus kennel cough, no rabies
    "vaccinations scheduled for the dog's May vet appointment",
    # 041: Cross-section normalisation to be checked against Physical Review supplement
    "intent to verify a cross-section value against a journal supplement",
    # 042: EmulationStation plus ScreenScraper on living-room HTPC organised ROMs
    "how the retro game library got tidied on the home theater PC",
    # 043: Second law of thermodynamics, entropy never decreases
    "principle stating isolated-system entropy cannot fall",
    # 044: DVLA V5C for Kia Niro arrived 2026-04-02
    "when the Niro's registration document was received from DVLA",
    # 045: filler kettle click
    "short wait because a kitchen appliance finished",
    # 046: Heart-rate zone training beats flat-pace stagnation
    "switch in cardio training approach that broke a plateau",
    # 047: Cursor pagination uses (created_at, id) snapshot, deletes no-op
    "why deleting rows doesn't break the paginated feed",
    # 048: filler node conditions
    "aside about inspecting Kubernetes node status",
    # 049: Northernlion moved Isaac to YouTube 2026-03-09, Premium kills mid-rolls
    "what pulled viewing away from the daily Twitch gameplay stream",
    # 050: Sutskever co-founded OpenAI in 2015, chief scientist through GPT-2/3/4
    "OpenAI co-founder who served as chief scientist across the GPT line",
    # 051: filler circle back later
    "deferring an answer until later",
    # 052: Bits UI is Svelte Radix equivalent, Svelte 5 pricing page uses it
    "library that mirrors Radix primitives for Svelte",
    # 053: Junior-led architecture review week with senior shadow
    "format of the rotating junior-chaired architecture meeting",
    # 054: filler bucket listing paginating
    "waiting on an S3 listing to finish paginating",
    # 055: Anchor Heating quote £3,450 for Worcester 30Si including flue relocation
    "price Anchor Heating quoted for the Worcester boiler swap",
    # 056: Franco from 2017 grad program, Barcelona fintech, role chat
    "reconnecting with an old grad programme peer about a job",
    # 057: InfluxQL on InfluxDB 1.8 for factory dashboards, Flux never landed
    "why the factory cluster never switched from InfluxQL to Flux",
    # 058: Apple Focus Commute filter, excludes Slack and mail, allows Spotify and CityMapper
    "what the Commute Focus filter allows and blocks",
    # 059: OpenWeightLifting CSV plus Julian's script produces Wilks timeline Hevy won't
    "how the Wilks progression chart gets built outside Hevy",
    # 060: Tambora 1815, Sumbawa, VEI 7, Year Without a Summer 1816
    "eruption that caused the 1816 volcanic winter",
    # 061: Martin and Steel 1988 proved projective determinacy from Woodin cardinals
    "paper establishing projective determinacy from Woodin cardinals",
    # 062: Thermodynamic arrow of time, entropy growth not fundamental laws
    "how macroscopic time asymmetry is explained thermodynamically",
    # 063: tree-sitter textobjects in Neovim, vaf and daf without Python plugin
    "Neovim feature enabling language-agnostic function editing",
    # 064: iPad Pro Sketchbook Pro continues 2019-2023 paper sketchbook habit
    "digital tool that took over from the analog sketchbook",
    # 065: Cursor 40% fewer stop-sign moments after one-paragraph specs before composer
    "practice that cut rework cycles when using Cursor composer",
    # 066: Ghostty fast adoption on macOS, zero tearing on 4K monitors
    "terminal emulator that spread quickly on the Mac side",
    # 067: filler double-check figure
    "wanting to verify a number before replying",
    # 068: filler school bus pulled up
    "observation about the school bus arriving outside",
    # 069: Philosophy podcast backlog at episode 460 on 2026-04-08, two behind
    "current position in the history of philosophy podcast queue",
    # 070: Flagger canary auto-rollback on error rate and p99 within four minutes
    "how a bad release got reverted without manual intervention",
    # 071: Arnold Clark Southampton 2026-02-14, Niro stock in Leeds
    "why the Southampton dealership visit ended without a purchase",
    # 072: bat with syntax highlighting, --style=plain pipes into fzf preview
    "cat replacement used for syntax-aware previews in fzf",
    # 073: filler pull that up
    "offhand remark about retrieving something quickly",
    # 074: filler sip of water
    "brief pause to drink water",
    # 075: filler pod events peek
    "quick look at Kubernetes pod events",
    # 076: filler dropped a frame
    "minor acknowledgement of a video hiccup",
    # 077: Richard Barrer zeolite work at Imperial, Mobil ZSM-5 catalytic cracking
    "chemist behind the systematisation of synthetic zeolites",
    # 078: Rust units crate with const generics attaches units to f64
    "how the Rust units library prevents mixing meters and seconds",
    # 079: filler kettle went off
    "interrupting because the kettle finished",
    # 080: Flyte typed dataclass caught schema drift, Airflow XCom would have failed later
    "orchestrator that caught an input schema bug before the run started",
    # 081: 6am RSS on Kindle Scribe via Inoreader, mass-mark-read unread over an hour
    "morning routine for processing RSS without guilt",
    # 082: Sutton Hoo 1939, richest Anglo-Saxon elite material culture
    "site excavated in 1939 that revealed early Anglo-Saxon elites",
    # 083: DragonFly Cobalt into IE 600 on 2026-03-02 Amtrak for 24/96 lossless
    "DAC used to unlock hi-res lossless on the train to Boston",
    # 084: Aider repo-map beat hand-crafted file lists on auth refactor
    "why Aider's auto file selection outperformed curated lists",
    # 085: Ricoh GR IIIx replacing Leica Q3 daily-carry on 2026-03-18, snap-focus
    "camera swap driven by preferring snap focus for street candids",
    # 086: 2022 Nature Human Behaviour replication of mortality salience, small heterogeneous effects
    "replication that weakened terror management findings",
    # 087: Roc lambda sets, every callback compiles to flat tag union, no boxing
    "how Roc resolved the closure allocation design question",
    # 088: Real-PR harness scores diffs, sonnet leads backend, gpt-4o frontend
    "benchmark ranking coding models against merged human PRs",
    # 089: Linux perf LBR sampling exposed JIT branch-misprediction hot spots
    "sampling technique that revealed JIT branch mispredictions",
    # 090: filler pull up paper
    "wanting to open the source paper before quoting it",
    # 091: Every SDK has single-line mock transport for tests
    "testing pattern every client library exposes for HTTP swaps",
    # 092: filler re-read the last part
    "brief pause to reread the previous sentence",
    # 093: filler reloading the driver
    "aside about restarting a hardware driver",
    # 094: Bluebikes data for Brookline bike lane Select Board 2026-03-15
    "data source used to argue for Brookline bike lanes",
    # 095: Kitchen espresso machine leaks on first pot every morning
    "recurring breakfast-time espresso machine problem",
    # 096: Nash equilibrium, no unilateral deviation improves payoff
    "definition of equilibrium where no player wants to deviate",
    # 097: Office cat portrait hung above snack shelf, anonymous
    "anonymous artwork that appeared in the office snack area",
    # 098: asyncio.Semaphore of 32 per process caps Anthropic calls
    "concurrency cap applied to Anthropic API calls per process",
    # 099: rollup-plugin-visualizer treemap exposed 2 MB vendor chunk owners
    "tool that made vendor chunk bloat readable quickly",
    # 100: filler check referral form
    "pause to look at a referral form",
    # 101: Pinatubo 1991, 20 Mt SO2, cooled Earth 0.5 C
    "eruption that injected sulphur dioxide and cooled the planet",
    # 102: Damasio somatic markers, bodily states bias decisions via vmPFC
    "hypothesis linking gut feelings to prefrontal decision making",
    # 103: Fuster prefrontal delay-period firing grounded working memory
    "single-unit recordings that anchored working memory theory",
    # 104: Levels CGM 2026-02-11 pinned post-run oatmeal at 180 mg/dL
    "glucose spike the CGM revealed after post-run oatmeal",
    # 105: Bronze Age collapse c. 1177 BCE, Mycenaean, Hittite, Levantine
    "civilisations that fell together around 1177 BCE",
    # 106: Java Flight Recorder continuous profile caught boxing cascade
    "low-overhead JVM profiler that revealed hidden boxing",
    # 107: Coming out at 2025-08-30 barbecue, Declan had guessed since 2014
    "family coming-out event that went smoother than expected",
    # 108: Duncan mobility tables formalised intergenerational status transitions
    "sociologist who quantified intergenerational status movement",
    # 109: tsup dual ESM/CJS with exports map
    "tooling that produced dual-format package output easily",
    # 110: filler minute to sit with it
    "asking for time to absorb something",
    # 111: Said's Orientalism 1978 reshaped postcolonial writing
    "1978 book foundational to postcolonial theory",
    # 112: Taizé pilgrimage 2024-07 shifted faith away from megachurch
    "retreat that changed the direction of religious practice",
    # 113: Pictures Generation NYC 1977, mass-media appropriation
    "late-1970s New York art group that critiqued authorship",
    # 114: Le Texier 2019 Histoire d'un mensonge documented SPE coaching
    "book contradicting the Stanford Prison Experiment narrative",
    # 115: filler pull that up
    "saying to pull up a reference quickly",
    # 116: use-context-selector cut nav tree renders by half
    "library that halved rerenders on the navigation tree",
    # 117: PyMC examples matched Efron 1979 bootstrap estimates
    "what convinced the user that Bayesian methods were reliable",
    # 118: Weekly review-of-reviews grades three random PR threads
    "process seniors use to audit code-review quality",
    # 119: Aunt Rosa's grandfather clock in hallway, accurate to a minute a week
    "origin and accuracy of the hallway grandfather clock",
    # 120: San Sebastián pintxos Calle 31 de Agosto beat tasting menus
    "San Sebastián food experience that outshone booked tastings",
    # 121: Lock screen breath cue 'long exhale' replaced by Rumi on 2026-03-25
    "evolution of the phone lock-screen mindfulness reminder",
    # 122: Apache Thrift on legacy analytics RPC with compact protocol
    "RPC framework behind the Hadoop-era analytics services",
    # 123: Co-op Funeralcare prepaid 2019, saved £1,900 vs 2026 rate
    "financial outcome of prepaying grandfather's funeral in 2019",
    # 124: Anki 87% mature retention on 2026-04-13 after 20-card cap
    "recent Anki retention figures after daily cap change",
    # 125: Rick Steves audio guide auto-advanced via beacons at Borghese
    "tour audio guide that synced to museum Bluetooth beacons",
    # 126: filler pull that up for you
    "offering to look something up",
    # 127: git log -S found unused legacy_bonus_calc since 2021, removed
    "command that proved the legacy helper was dead code",
    # 128: Mesa 24 with ANV Vulkan on Linux, RADV on AMD without rebuild
    "Vulkan driver stack update across the Linux test fleet",
    # 129: Film Formalism emphasises technique over narrative content
    "film theory school that values form over story",
    # 130: Bell tests violate local-hidden-variable bounds, nonlocality remains
    "experiments that rule out local hidden variables in quantum theory",
    # 131: Pocket Casts Plus paid off on 2026-01-19 flight with kids offline
    "travel moment that justified the podcast subscription",
    # 132: Zed multiplayer editing beat screen-share during incident review
    "collaborative editor that shone during an incident runbook update",
    # 133: Break-room kettle whistle bothers one specific engineer
    "office kettle noise that bothers a single teammate",
    # 134: Grandpa Theo's rocking chair by nursery window, puts Leo to sleep
    "heirloom chair Leo naps in fastest",
    # 135: Book boxes capped at 18 kg on 2026-04-06 pack-up
    "weight limit applied to book boxes during the move",
    # 136: ICML since 1980, co-equal with NeurIPS
    "year the flagship general-purpose ML conference began",
    # 137: Deno npm mostly works, postinstall scripts need workaround
    "Deno compatibility gap we route around by package",
    # 138: filler YubiKey blinking
    "interrupted because the hardware token is prompting",
    # 139: WGMS tracks global glacier mass since 1894, accelerating loss
    "organisation that has tracked glacier mass since 1894",
    # 140: Argo floats absorb >90% of excess heat in oceans
    "share of greenhouse heat absorbed by the ocean per Argo data",
    # 141: Daf yomi Berakhot 42a on 2026-03-09 via Zoom chavruta
    "Talmud daily page reached in early March with chavruta partner",
    # 142: Rootless Podman memory limits need cgroups v2 unified delegation
    "kernel feature required for rootless Podman memory caps",
    # 143: filler sign-up sheet check
    "pause to look at a signup sheet",
    # 144: Neo4j index-free adjacency won over triple store on recursive paths
    "property that made Neo4j outperform the triple store on path queries",
    # 145: Docusaurus 3 landed MDX 3, fixed React-in-prose AST corruption
    "documentation platform upgrade that fixed MDX AST issues",
    # 146: filler kettle clicked off
    "sorry interjection about a kettle finishing",
    # 147: Crystal Palace 1851 Great Exhibition, Paxton, cast-iron and plate-glass prefab
    "modular prefabricated 1851 exhibition building in London",
    # 148: Diablo IV gold market collapsed 2026-01-29 after Season 8 patch
    "when the Diablo IV auction economy crashed",
    # 149: Docs PRs get Read the Docs and Netlify previews
    "preview services used for reviewing documentation PRs",
    # 150: 2026-03-28 morning review found half-drafted Dad's 70th toast
    "pleasant surprise during a recent notes review",
    # 151: Austronesian dispersal from Taiwan to Madagascar and Rapa Nui
    "homeland and range of Austronesian seafaring expansion",
    # 152: ACL conference by Association for Computational Linguistics, with EMNLP and NAACL
    "primary NLP conference alongside EMNLP and NAACL",
    # 153: JWST launched 2021-12-25, replaces Spitzer, ~50x mirror area
    "JWST launch date and its Spitzer successor status",
    # 154: filler interesting point
    "brief acknowledgement that a point is interesting",
    # 155: filler re-read chapter before notes
    "wanting to reread a chapter before annotating",
    # 156: filler retention policy backfilling
    "waiting on a retention policy to finish backfilling",
    # 157: Mum's carrot cake is the birthday standard, no substitutes
    "traditional birthday cake that bakeries can't replace",
    # 158: DaVinci Resolve offline edit on friend's Premiere Pro rig 2026-02-19
    "why the February short film edit happened on Premiere instead",
    # 159: filler circle back
    "saying to come back to a point shortly",
    # 160: JetBrains Toolbox sync keeps SDK paths and keymap across machines
    "how IDE settings stay in sync across three workstations",
    # 161: Notion review handbook living doc with quarterly walk-through
    "where the team's review principles and SLAs are documented",
    # 162: filler check queue depth
    "pause to inspect queue depth",
    # 163: ZHeap Postgres in-place updates without MVCC bloat, stayed out of mainline
    "abandoned Postgres heap design aimed at reducing MVCC bloat",
    # 164: Ulm School 1953-1968 extended Bauhaus into systems thinking
    "postwar school that pushed Bauhaus toward scientific method",
    # 165: filler coffee brewing
    "apology about coffee finishing brewing",
    # 166: JetBrains Gateway drives dev container on build box, laptop no longer swaps
    "remote IDE setup that stopped the 32 GB laptop from swapping",
    # 167: Neptune kept for research group, REST access suits notebooks
    "experiment tracker retained for the notebook-heavy research team",
    # 168: Eva moved to Berlin 2025-09, Iona became central organiser
    "who took over friend-group organising after Eva's move",
    # 169: Credibility revolution makes open data and code first-class
    "shift in meta-science treating openness as mandatory",
    # 170: Enhanced rock weathering spreads crushed basalt for CO2 mineralisation
    "carbon removal method using crushed basalt on fields",
    # 171: OpenFeature's evaluationContext cleaner than Split.io traffic types
    "why OpenFeature replaced Split.io targeting vocabulary",
    # 172: filler what were you saying
    "asking the other person to repeat themselves",
    # 173: filler Wi-Fi drop
    "brief aside about Wi-Fi cutting out",
    # 174: filler dog wants out
    "asking for a moment because the dog needs to go out",
    # 175: LEP at CERN 1989-1995 measured Z resonance, three light neutrinos
    "collider measurement that fixed the light neutrino count",
    # 176: Heartcore reformer pilates built on 2022 mat pilates
    "studio where reformer pilates practice progressed",
    # 177: ORC Zlib kept for cold partitions, beats ZSTD on wide strings
    "why the warehouse kept Zlib over ZSTD on cold data",
    # 178: Bowler's declarative API let interns write refactors without AST knowledge
    "refactoring tool that hid Python AST details from interns",
    # 179: PhotoRec recovered 340 Sony A7 IV ARW files on 2026-02-27 from CFexpress
    "software that salvaged photos from the corrupted CFexpress card",
    # 180: Belle at KEK 2001 PRL measured sin(2 beta), confirmed KM
    "B-factory measurement that validated the Kobayashi-Maskawa prediction",
    # 181: Grief letter to Nan 2026-03-22 sealed in binder, therapy anchor
    "purpose of the sealed grief letter on the second shelf",
    # 182: Node import maps in package.json imports, replacing tsconfig paths for runtime
    "Node feature that moved aliasing out of tsconfig paths",
    # 183: Son Byong-hi 1905 rebranded Donghak as Cheondogyo
    "who reorganised Donghak into modern Cheondogyo in 1905",
    # 184: filler DNS stopped resolving
    "rushed aside about cluster DNS failing",
    # 185: Cody Enterprise beat Copilot Workspace on cold-repo onboarding
    "coding assistant that found cross-package helpers Copilot missed",
    # 186: Tabletop RPG group at Orc's Nest, Seb running Mothership
    "regular pub RPG night and current campaign system",
    # 187: Office kombucha tap flavour switch disliked by Android team
    "recent kombucha change that annoyed one team",
    # 188: filler look up exact figures
    "wanting to confirm exact numbers before continuing",
    # 189: Multi-burn-rate alert uses Google SRE 14.4 and 6 factors
    "source for the multi-burn-rate error budget alert factors",
    # 190: Informed consent needs capacity, voluntariness, disclosure of risks
    "elements required for valid informed consent",
    # 191: Repository<T extends {id: Brand<string,'Id'>}> blocks unbranded ids
    "TypeScript trick preventing unbranded ids in repositories",
    # 192: Mrs. Okafor watches dog during Cleveland visits, accepts only baked goods
    "neighbour who pet-sits and refuses cash payment",
    # 193: Gleam OTP wrappers let BEAM teams keep supervision trees
    "how Gleam preserves existing Erlang supervision structures",
    # 194: IPCC AR7 accelerated, WGI expected late 2020s
    "expected release window for IPCC AR7 Working Group I",
    # 195: filler find the receipt
    "pause to search for a receipt",
    # 196: fd replaces find, default ignores .gitignore and hidden files
    "find replacement whose defaults respect gitignore",
    # 197: Verify citation is 1983 Journal of Communication ferment issue or later
    "uncertainty about which ferment symposium a citation refers to",
    # 198: Cat allergic to fish, swells from tuna
    "pet's allergy that causes swelling from even a little tuna",
    # 199: sbt kept on Akka-based legacy services, mill migration not worth it
    "reason the Akka services stayed on sbt rather than mill",
    # 200: Flake dashboard fingerprints tests, seeded RNG caused half the flaps
    "root cause responsible for most recent test flakiness",
    # 201: Two-photon calcium imaging resolves hundreds of neurons with GCaMP plus IR
    "microscopy method for recording hundreds of neurons awake",
    # 202: Mila founded by Bengio in Montreal 1993
    "Montreal AI institute founded by Yoshua Bengio",
    # 203: Break-room whiteboard doodle war three iterations deep, two panels
    "office whiteboard doodle war sprawling across panels",
    # 204: filler warm the cache
    "short pause to warm a cache",
    # 205: filler think for a minute
    "asking for a minute to think before answering",
    # 206: Python structural pattern matching earned its keep on webhook dispatcher
    "feature that proved useful in the webhook dispatcher rewrite",
    # 207: filler lint roller location
    "wondering aloud where the lint roller went",
    # 208: filler fuel log glance
    "wanting to peek at the fuel log first",
    # 209: VictoriaMetrics 3M samples/s, 40% of Prometheus CPU
    "benchmark showing VictoriaMetrics ingest efficiency vs Prometheus",
    # 210: Jiaolong submersible reached 7062 m in Mariana Trench 2012
    "Chinese submersible that hit seven kilometres in the Mariana Trench",
    # 211: filler grab water
    "asking for a water break",
    # 212: Bird attacking monitor reflection outside south window
    "bird repeatedly confronting its own reflection in the window",
    # 213: filler dinner at seven
    "casual reminder about dinner timing",
    # 214: git-cliff renders changelog from conventional commits grouped by scope
    "tool that auto-builds changelogs from commit scopes",
    # 215: Theravada preserves Pali Canon and arhat ideal in Sri Lanka and SE Asia
    "Buddhist tradition dominant in Sri Lanka and mainland SE Asia",
    # 216: ColBERT late-interaction lifted MRR@10 from 0.41 to 0.58 on legal QA
    "reranker that boosted legal retrieval MRR by seventeen points",
    # 217: filler dog walk
    "short break for walking the dog",
    # 218: SDSS at Apache Point since 2000 replaced photographic plate surveys
    "survey that displaced photographic-plate galaxy catalogues",
    # 219: filler reflow joint
    "brief aside to reflow a solder joint",
    # 220: Construction Grammar basic unit is form-meaning pairings
    "linguistic theory treating form-meaning pairs as basic units",
    # 221: filler glass of water
    "asking for a quick water break",
    # 222: Mitochondrial circular DNA inherited maternally in most animals
    "how animal mitochondrial DNA typically passes between generations",
    # 223: Clara left quinces Sunday, made good membrillo
    "quince paste outcome from the neighbour's Sunday gift",
    # 224: 10,000 API calls/min per tenant at gateway
    "per-tenant gateway rate limit figure",
    # 225: Template-literal types on routing builder catch mistyped paths
    "how the router surfaces bad path strings before tests run",
    # 226: Neanderthal introgression 1-2% of non-African genomes
    "share of Neanderthal ancestry in most non-African humans",
    # 227: filler coffee and return
    "going to grab coffee before resuming",
    # 228: fzf CTRL-T and CTRL-G for git files
    "interactive file picker bound to CTRL-T in every shell",
    # 229: Windy forecast canceled 2026-05-09 Santorini ferry ahead of Ferryhopper
    "weather app that predicted the Santorini ferry cancellation early",
    # 230: RTX 5060 runs Baldur's Gate 3 evenings and Qwen 3.5 4B fine-tune nights
    "dual use of the home GPU between gaming and fine-tuning",
    # 231: Diminishing marginal utility, second slice satisfies less
    "economic concept explaining why the second slice underwhelms",
    # 232: Emporia Vue plus Wallbox caught 2026-02-14 derate at 175 A
    "how the home EV charging derate on Valentine's was detected",
    # 233: filler makes sense
    "short agreement that something makes sense",
    # 234: Neighbours replaced sticking garage door from November
    "neighbours finally fixing their cold-morning garage door",
    # 235: Krakatoa 1883 Sunda Strait, 36,000 dead from caldera tsunamis
    "1883 eruption whose tsunamis reached South Africa",
    # 236: Annals of Mathematics from Princeton and IAS, bimonthly
    "journal jointly published by Princeton and the IAS",
    # 237: Spectralism in 1970s France, Grisey and Murail, harmony from spectral analysis
    "French musical movement deriving harmony from spectra",
    # 238: Carly unlocked VIM on 2024 BMW 330i after iDrive 9 relocked on 2026-04-03
    "adapter that restored video-in-motion after the iDrive update",
    # 239: Meiji Restoration 1868 ended Tokugawa, centralised imperial rule
    "event that ended the Tokugawa shogunate and industrialised Japan",
    # 240: Benzene aromaticity, planar ring, six pi electrons, Huckel
    "why benzene is aromatic by Huckel's rule",
    # 241: 2026-04-09 pasta night Marcato Atlas, Mei rejects Philips Home Assistant integration
    "why the family pasta night stuck with the hand-cranked roller",
    # 242: ATLAS and CMS through 2023 PRL excluded gluinos below ~2.3 TeV
    "LHC mass limit placed on minimal supersymmetric gluinos",
    # 243: IPCC AR6 1.5C remaining carbon budget ~500 Gt from 2020
    "remaining carbon budget for 1.5 degrees per AR6",
    # 244: filler booking reference check
    "wanting to verify the booking reference first",
    # 245: Tushman and O'Reilly ambidexterity theory, exploit and explore
    "management theory that firms must exploit and explore simultaneously",
    # 246: 1971 San Fernando earthquake drove capacity design in reinforced concrete
    "earthquake that reshaped reinforced concrete seismic codes",
    # 247: griffe-based helper auto-generates function-calling schemas from docstrings
    "how tool-use schemas stay aligned with Python docstrings",
    # 248: Rust Send/Sync rejected Rc<RefCell>, Arc<Mutex> worked with short audit
    "Rust concurrency types that replaced a naive Rc RefCell",
    # 249: Verify chain-weighted deflator in national-accounts vintage before quoting growth
    "care taken before citing a GDP growth figure",
    # 250: filler Redis restarting
    "interrupting because Redis is coming back up",
]


def emit() -> int:
    with SOURCES.open("r", encoding="utf-8") as f:
        sources = [json.loads(line) for line in f if line.strip()]
    assert len(sources) == 250, f"expected 250 source rows, got {len(sources)}"
    assert len(QUERIES) == 250, f"expected 250 queries, got {len(QUERIES)}"
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
