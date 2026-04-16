"""One-off emitter for retrieval aug batch-012 — multi-sentence queries.

Each row pairs a longer, paragraph-shaped query (2-4 sentences, 20-60 words) with
its source row as the positive. Queries simulate a careful user typing out
context and a specific question about a milestone, ship date, release, or
personal/project event.

Writes 100 rows to data/v2/retrieval/aug_012.tmp.jsonl with ids ret-04901..05000,
reading positives from data/v2/retrieval/aug_sources/aug_012.jsonl.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "v2" / "retrieval" / "aug_sources" / "aug_012.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "aug_012.tmp.jsonl"
QUERY_KIND = "multi-sentence"

# 100 multi-sentence queries, aligned in order with aug_012.jsonl rows.
QUERIES: list[str] = [
    # 04901 Grafana exemplars -> Tempo trace, MTTR 15m -> 90s
    "I'm writing up our observability wins for the quarterly review. Can you remind me what the actual mean-time-to-root-cause drop was after we wired Grafana histogram buckets into Tempo via exemplar links?",
    # 04902 Brazilian jiu-jitsu Gracie Barra first stripe
    "I'm updating the hobbies section of my year-end reflection. When exactly did I start jiu-jitsu at Gracie Barra, and did I end up earning that first stripe on the white belt?",
    # 04903 ClickHouse delta-delta timestamp 62 percent
    "Looking back at our storage wins on the metrics pipeline, I want to confirm a detail for a blog draft. Which ClickHouse encoding change cut the on-disk footprint, and what was the reduction versus plain LZ4?",
    # 04904 Jewellery audit Rebus melt-and-recast pinky ring
    "I'm reviewing my annual jewellery audit for the insurance rider renewal. What date did I actually do it, which pieces went out to Rebus for melt-and-recast, and what was the credit being put toward?",
    # 04905 First-phone Nokia 2660 flip year seven
    "For the parenting journal I want to nail down the first-phone decision. When did the negotiation land, what device did we agree on, and how long until a smartphone comes into the picture?",
    # 04906 Redland keys handover Hopewell Lettings
    "I'm pulling together evidence for the deposit-return dispute. When did I actually hand the Redland keys back to the agent at Hopewell, and did I put anything in writing on the inventory?",
    # 04907 Book-club Discord Piranesi Storygraph
    "I'm trying to remember when the book-club Discord setup actually clicked. What date was that Piranesi call, and did the Storygraph buddy-read badge fire for everyone on the call?",
    # 04908 Strangler PHP -> Symfony 14 months
    "Drafting the retrospective for the legacy decommission. When did the strangler migration finally wrap up, how long did it run end to end, and which framework is now serving the last pages?",
    # 04909 Voice Memos -> ModelTalker laryngeal cancer
    "I need this in the care plan document. When did mom's voice-banking actually move off Voice Memos, and why was ModelTalker the destination rather than keeping it on the phone?",
    # 04910 GraphQL Codegen client-preset useOrderQuery
    "I'm walking a new contractor through our frontend types story. Which GraphQL tooling gave us typed hooks, and what concretely changed on useOrderQuery after the switch?",
    # 04911 i18n README pnpm i18n:doctor ICU
    "For the onboarding docs retrospective I want to be precise. What actually lives behind the pnpm i18n:doctor script the README points at, and did a new contributor manage to run it on day one?",
    # 04912 Goodnight scene Aqara U100 Ecobee Reolink
    "I'm compiling the smart-home highlights for the newsletter. When the Goodnight scene finally worked end-to-end, which devices were actually orchestrated, and what temperature did the Ecobee drop to?",
    # 04913 Problem-based learning McMaster 1969
    "I'm sketching a history-of-medical-education slide. Where and when did problem-based learning launch, and what specifically did it replace as the curricular unit?",
    # 04914 slog panic handlers Go json line
    "I'm reviewing our reliability wins for the Go services. Which pattern replaced print-and-pray panic recovery across the binaries, and what fields end up in the structured log line after a panic?",
    # 04915 Frances Arnold directed evolution Caltech Nobel
    "For the talk on enzyme engineering I want a clean reference. When did Frances Arnold's Caltech directed-evolution programme get the big Nature review, and how did that feed into her Nobel?",
    # 04916 Docker Desktop macOS LinuxKit Apple Virtualization
    "A colleague asked about our Docker Desktop CPU numbers on the MacBooks. Which virtualization framework is Docker actually using under the hood now, and roughly how much idle CPU did the HyperKit switch save?",
    # 04917 Quarterly review 47 evergreen notes mood chart
    "I want to cite this in the PKM talk next month. When did that quarterly review happen, how many evergreen notes came out of the vault, and did the mood chart line up with anything in particular?",
    # 04918 Grothendieck 1957 Tohoku abelian categories
    "I'm writing an appendix on homological algebra's history. Which Grothendieck paper formalised abelian categories and derived functors, and what did it supersede from the Cartan-Eilenberg era?",
    # 04919 WHEP low-latency viewer 800 ms vs DASH
    "For the streaming architecture talk I want specifics. Which protocol handled low-latency viewer egress, and what were the typical connect times compared to the old DASH player?",
    # 04920 Synology UPS power surge Wojtek
    "Looking back at the family tech saves for the holiday newsletter. When did the Synology actually survive the power surge, and who had pushed for the UPS that made it possible?",
    # 04921 Will Hemsworth Solicitors Marie Curie
    "I'm updating my end-of-life planning binder. When did we last update the will with Hemsworth Solicitors, and did the Marie Curie gift survive the revision?",
    # 04922 Mum Lisbon assisted-living 2025-10-12
    "I'm trying to nail down the timeline for Mum's care plan. What was the exact date we moved her into the Lisbon assisted-living flat, and how did the transition go?",
    # 04923 GDS triangle counting Louvain co-purchase
    "I'm putting together the graph-analytics highlights from Q4. Which GDS algorithm surfaced the clustering coefficient bump on the co-purchase graph, and what did the community shift line up with?",
    # 04924 Leo's first loose tooth pear £2
    "The baby book needs a date and a little colour. When did Leo actually lose his first tooth, what was he eating at the time, and what did the tooth fairy leave?",
    # 04925 Booking.com vs Airbnb Buenos Aires
    "I'm reviewing travel booking choices for the expense report. Why did we switch off Airbnb for the Buenos Aires stay, how many listings canceled late, and what date was the trip?",
    # 04926 Specialized Sirrus cracked Trek FX 3 Disc
    "I'm updating the cycling log with the bike replacement. Which bike cracked at the bottom bracket, what replaced it, and what date did the swap happen?",
    # 04927 Four Tet Brooklyn Steel Bandsintown vs Songkick
    "For the concert-app comparison post I want the specifics. When was the Four Tet show at Brooklyn Steel, and which alert app tipped me off before the tickets cleared?",
    # 04928 Eero Secure NextDNS teen Hadi
    "I'm writing up the family internet-safety setup for another parent. What combination of tools is filtering my teen Hadi's gaming rig, and how did we know it was actually working?",
    # 04929 Motorbike CBT Thundersley A2 Honda CB500F
    "Getting my motorbike paperwork in order. What date is the CBT booked for, where, and what's the plan to make the Honda CB500F road-legal for me?",
    # 04930 Idempotency tokens Step Functions StartExecution
    "I'm documenting the deduplication work on our workflows. When did idempotency tokens land on the Step Functions Task states, and what problem from the upstream API did that actually close?",
    # 04931 Whisper Decoder Substack Tomas
    "I want to cite the side project in a talk about indie tooling. When did I ship the Whisper-powered Substack newsletter, and what problem was it specifically solving for Tomas?",
    # 04932 Rust ingest Result thiserror IngestError
    "I'm preparing a before-and-after slide on Rust error handling. What replaced the unwrap-everywhere style in the ingest module, and what's the typed error now flowing through the call sites?",
    # 04933 Arte Povera Germano Celant 1967
    "I'm fact-checking a catalog essay on Italian postwar art. Who theorised Arte Povera and in what year, and what materials stood in for what the movement was rejecting?",
    # 04934 Parquet encryption uniform mode footer-only
    "I'm writing up the data-at-rest encryption rollout for audit. When did Parquet encryption with uniform mode go live, and why did we pick footer-only key wrap over per-column?",
    # 04935 Dobbs Roe Casey 2022
    "I'm prepping a US constitutional-law timeline. Which Supreme Court case replaced the Roe and Casey framework, what year was it decided, and what was its short name?",
    # 04936 FFXIV WoL Maya Endwalker Dawntrail Mare Synchronos
    "For the gaming backlog update on the blog. Where has the Final Fantasy XIV WoL Maya actually reached in the story, and what combination of events got us to play again?",
    # 04937 LIGO GW150914 2016 PRL
    "I'm citing the first gravitational-wave detection in a physics primer. What was the event called, what journal published it, and what kind of merger was it?",
    # 04938 1918 Spanish flu 50 million deaths
    "For the pandemic-preparedness briefing I want a clean reference. How many deaths did the 1918 influenza actually cause, and how is it used as a benchmark today?",
    # 04939 Pixieset Santorini Printique Fujiflex
    "I want this in the photography-business retrospective. When did the Santorini elopement gallery cross 600 favorites, and which print ended up auto-ordering that same night?",
    # 04940 Hip MRI labral wear strength work
    "Updating the medical timeline in my health log. What date was the hip MRI, what did it actually show, and did the orthopedist push for surgery?",
    # 04941 Trusted Types admin SPA innerHTML
    "I'm writing up the XSS hardening for the security review. What policy rollout happened on the admin SPA, and what now occurs in production if someone assigns a raw string to innerHTML?",
    # 04942 Bill-splitting Google Apps Script
    "I want this in the boring-but-useful automations thread. When did I actually finish automating the bill-splitting spreadsheet, and what did the automation end up being built on?",
    # 04943 Mazur 1977 IHES torsion elliptic curves
    "For a number-theory seminar intro. Which Barry Mazur paper produced the torsion theorem for rational elliptic curves, and what was the year and venue?",
    # 04944 Harry Hess 1962 History of Ocean Basins seafloor spreading
    "I'm writing a plate-tectonics history sidebar. Which 1962 paper proposed seafloor spreading, and what gap in Wegener's continental drift did it actually fill?",
    # 04945 Carl Woese 1977 PNAS Archaea third domain
    "For the microbiology lecture slide. Which 1977 paper established Archaea as a third domain of life, and what technique did it rely on?",
    # 04946 OpenMP parallel for pthread schedule dynamic
    "I'm sketching the HPC refactor for the retro. What replaced the hand-written pthread fan-out in the simulation kernel, and which scheduling clause smoothed out the irregular workloads?",
    # 04947 SLAC deep inelastic scattering 1968-1969 partons
    "I'm building a particle-physics history slide. Which SLAC experiments gave the first evidence for partons inside the proton, and who did the key theoretical analysis?",
    # 04948 Morning pages 63 days A4 long-hand
    "For the habits journal entry. How many consecutive days in did the morning pages habit actually lock in, and what exactly is the format I settled on?",
    # 04949 MuseScore 4 violin niece recital MIDI
    "I'm writing the year's music-tech notes. When did I render the violin arrangement for the niece's recital in MuseScore 4, and did the accompanist get a playable file out of it?",
    # 04950 Memphis Group Milan 1981 Sottsass
    "For the design-history talk I want a precise reference. When and where was the Memphis Group formed, who was the central figure, and what were they reacting against?",
    # 04951 Grafana Cloud trial Mimir Loki Tempo 4-day
    "I'm defending the build-vs-buy call for observability. When did the Grafana Cloud trial actually start, how long did the migration take, and how much did it beat the in-house estimate by?",
    # 04952 Last.fm -> ListenBrainz podcast bridge
    "I'm writing a small post on scrobbling tools. When did I actually move from Last.fm to ListenBrainz, and what specifically broke on the Spotify side that tipped the switch?",
    # 04953 OpenTofu Argo CD Crossplane 11 clusters
    "For the platform-engineering quarterly report. When did the IaC cut-over land, which stack replaced which, and across how many clusters did the change go out?",
    # 04954 Belmont Report 1979 three principles
    "I need a clean citation for the research-ethics module. What year was the Belmont Report issued, who issued it, and what three principles did it name?",
    # 04955 Juno Pupford graduation nosework Dogo
    "I'm writing up the puppy-training tooling comparison. When did Juno graduate puppy class in Pupford, and what did that app offer that the Dogo subscription couldn't?",
    # 04956 Leo pink book band paired reading Priya
    "The parent-school diary needs confirming. When did Leo actually hit the pink book band, how long did the paired-reading run take, and who was tracking it?",
    # 04957 SNO 2001 PRL neutrino flavour oscillation
    "For the neutrino-physics section of my notes. Which observatory reported neutrino flavour change, in what journal, and what did that result actually confirm?",
    # 04958 Human genome 2004 Nature Collins finished
    "I'm writing a human-genome timeline sidebar. When did the finished reference sequence publish, who led it, and how did it differ from the 2001 draft?",
    # 04959 Willis Carrier 1902 air conditioning dehumidification
    "I need a clean origin story for the HVAC section. Who filed the 1902 air-conditioning patent, what industry was it serving, and what long-term research field did it seed?",
    # 04960 Berlin at-home Turmstrasse U-Bahn German
    "I want this in the expat reflection piece. When did Berlin actually start to feel like home, and what tiny moment at the U-Bahn made it click?",
    # 04961 Bartlett 1962 xenon hexafluoroplatinate noble gas
    "For the chemistry-history slide. Which 1962 synthesis broke the noble-gas inertness dogma, and who was the chemist behind it?",
    # 04962 International Style 1932 MoMA Hitchcock Johnson
    "I'm updating the architecture syllabus. Which 1932 MoMA exhibition codified the International Style, who curated it, and what were the movement's defining principles?",
    # 04963 Confirmation St Alban's Bishop Thornton Claire Teresa
    "For the family record. What date did the confirmation at St Alban's happen, who officiated, and what confirmation name did I actually pick?",
    # 04964 v2 shared base 6998 + 2 top-up 7000
    "For the fine-tuning corpus changelog. Where did the shared base close out after the 140 parallel-agent batches, and how did we end up exactly at 7000 rows for training?",
    # 04965 axe-core alt text low-contrast CI
    "I'm preparing the accessibility deck for the all-hands. Which tool got added to CI as an a11y gate, and what categories of findings now block a merge the same as other CI failures?",
    # 04966 Hubble 1929 PNAS distance-velocity
    "For the cosmology lecture intro. Which 1929 paper published Hubble's distance-velocity relation, where did it appear, and why does that specific result matter?",
    # 04967 One year sober 2026-04-07 Jess
    "I want to include this in the anniversary note to my sponsor. What was the exact date I hit one year sober, and who did I start the program with?",
    # 04968 Node problem detector Alertmanager NVMe wear
    "For the reliability retrospective. Which component feeds node-health events into Alertmanager as a DaemonSet, and what hardware signal actually pulled a box out before it failed?",
    # 04969 V8 heap snapshot nightly CI leak
    "For the frontend reliability writeup. Where does the V8 heap snapshot pipeline run now, and how quickly does a leak regression fail the build compared to the old cadence?",
    # 04970 BPF CO-RE single binary kernel versions
    "I'm documenting the eBPF tooling migration. What specifically did BPF CO-RE let us ship, and how did operator pain during rollouts change as a result?",
    # 04971 TikTok deleted 2026-03-20 Instagram web-only
    "I want to capture this for the digital-minimalism essay. When did I actually delete the TikTok account, what triggered it, and did Instagram survive the cut?",
    # 04972 Copilot Apple Card Hazel PDF-to-CSV
    "For the personal-finance tooling post. When did the Copilot update bring Apple Card transactions in natively, and what Mac-side workflow did that retire?",
    # 04973 BuildBuddy Bazel us-east-2 p95 halved
    "I'm writing up the build-infra performance wins. Which product handles our remote-execution farm for the Bazel monorepo, and what happened to p95 wall times after the self-hosted executors came online?",
    # 04974 Selene Scratch 2026-04-11 school coding fair
    "For the parenting update I want the specifics. When did Selene's Scratch project actually ship at the school coding fair, and what January goal did it close out?",
    # 04975 Atmos 5.1.4 Klipsch RP-500SA ceiling-bounce
    "Updating the home-theatre build log. When did the layout move to 5.1.4, which speakers were the new ceiling-bounce additions, and where on the couch did they end up?",
    # 04976 Feng Zhang 2013 Science CRISPR mammalian Broad
    "For the genome-editing history slide. Which January 2013 paper demonstrated CRISPR-Cas9 in mammalian cells, where was it done, and how did it relate to Doudna and Charpentier's earlier work?",
    # 04977 2006 uni reunion Durham Red Lion 28 of 54
    "I want to brief my partner on the reunion plans. When and where is the 2006 cohort reunion landing, and roughly how many people actually replied yes?",
    # 04978 Wiring redo eARC HDMI 2.1 LG C2 Denon UB820
    "For the home-cinema retrospective. When did the wiring redo finally solve the audio dropout, and what specific cabling change was the fix?",
    # 04979 bcrypt 10 -> 12 lazy rehash
    "I'm documenting the auth hardening for compliance. What did we bump the bcrypt cost factor to, and how are the legacy passwords being migrated without forcing a mass reset?",
    # 04980 Catechumenate St Alban's Margaret Holbrook Easter Vigil 2027
    "For the spiritual-journey notes. When did I start the Catechumenate at St Alban's, who runs the weekly classes, and when is reception scheduled?",
    # 04981 Warwick evening MBA 2026-09-14 Coventry
    "I'm updating the career plan document. When does the Warwick evening MBA cohort start, how long is it, and which days will I actually be on the Coventry campus?",
    # 04982 HSA $8,300 employer match HDHP February
    "For the annual-benefits note in my finance folder. When did I contribute to the family HSA, how much went in, and when does HDHP coverage kick in?",
    # 04983 STDP Bi Poo 1998 millisecond
    "I'm writing a computational-neuroscience syllabus note. Which 1998 paper characterised spike-timing-dependent plasticity, and what time resolution does the weight update actually depend on?",
    # 04984 Grafana Pyroscope diff mode templating synthetic
    "For the observability talk. Which tool's diff mode between deploy tags caught a regression before the synthetic monitor fired, and what kind of code was actually regressing?",
    # 04985 Panama Papers Pulitzer 2017 ICIJ Sueddeutsche McClatchy
    "I'm writing the journalism-history section of an essay on investigative reporting. What did the 2017 Pulitzer for Explanatory Reporting actually recognise, and which outlets shared it?",
    # 04986 Leeds MSc Health Economics 19 years later
    "For the personal record. When did I actually restart at Leeds with the part-time MSc in Health Economics, and how many years after the original degree did that happen?",
    # 04987 Dad hip surgery 2026-01-08 spare room six weeks
    "Updating the family care timeline. When did Dad move into the spare room after his hip surgery, and what was the intended length of stay?",
    # 04988 Cattime ragdoll Kumo hyperthyroid MyVCA
    "I want to capture this for the vet visit next week. Which app replaced Pet Notebook for the ragdoll Kumo, and what specifically did it flag before the bloodwork confirmed it?",
    # 04989 Riverside.fm Zoom H6 double-ender 2026-02-12
    "For the podcast setup writeup. Which product replaced the Zoom H6 backup habit, and what specific failure mode did its automatic double-ender save us from?",
    # 04990 Values clarification Dr Halpern four anchors
    "I'm drafting the therapy-journey essay. When did the values clarification happen with Dr Halpern, what were the four anchors that came out of it, and where did I put them?",
    # 04991 Renode nRF52 BME280 CI hardware-in-the-loop
    "For the embedded CI writeup. When did Renode start simulating the nRF52 plus BME280 board in CI, and what happened to the hardware-in-the-loop queues as a result?",
    # 04992 Materials Research Society 1973 Penn State
    "For the materials-science intro lecture. When and where was the Materials Research Society founded, and what research areas does it actually span?",
    # 04993 Alertmanager inhibition rules 230 -> 4 pages
    "I'm writing the incident-response retrospective. Which Alertmanager feature silenced downstream alerts during the database outage, and what happened to page volume across the 90-minute event?",
    # 04994 Leila Polish sentence Duolingo 2026-03-11
    "I want this for the heritage-language journal. When did Leila actually read her first Polish sentence, and how long had we been doing Duolingo together at that point?",
    # 04995 Bologna cooking class Signora Rosa tortellini ragu
    "Updating the travel plans folder. What date is the Bologna cooking class with Signora Rosa, and what is she actually going to teach versus the tourist version?",
    # 04996 Airflow REST API Stable 2.0 experimental
    "I'm putting together the data-platform stability writeup. What happened to Airflow's experimental endpoints in 2.0, and what did the Stable API give the internal portal in practice?",
    # 04997 Bandura 1961 Bobo doll Stanford observational
    "For the psychology-history slide. What did the 1961 Bobo doll experiments at Stanford demonstrate, and whose name is attached to the work?",
    # 04998 Brown v Board 1954 Earl Warren Plessy
    "I'm citing a landmark ruling in a US legal-history essay. When was Brown v Board decided, who was Chief Justice, and what earlier doctrine did it replace?",
    # 04999 Boundary session recording admin 2026-03-09 playback
    "For the security-incident review. When did Boundary capture that misbehaving admin session for review, and how did playback actually work for the reviewer?",
    # 05000 AlphaGo Lee Sedol Seoul 4-1 March 2016
    "For the AI-history timeline slide. When and where did AlphaGo beat Lee Sedol, what was the match score, and why did that result matter?",
]


def emit() -> int:
    assert len(QUERIES) == 100, f"expected 100 queries, got {len(QUERIES)}"
    with SOURCES.open("r", encoding="utf-8") as f:
        sources = [json.loads(line) for line in f if line.strip()]
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
