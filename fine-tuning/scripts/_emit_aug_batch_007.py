"""One-off emitter for retrieval aug batch-007 (typo-kind queries).

Reads 150 milestone source rows from
`data/v2/retrieval/aug_sources/aug_007.jsonl` and emits one retrieval
top-up row per source with a short, plausibly-misspelled query. Output
is written to `data/v2/retrieval/aug_007.tmp.jsonl` with ids ret-04151
through ret-04300 (sourced from each row's `new_id`).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "v2" / "retrieval" / "aug_sources" / "aug_007.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "aug_007.tmp.jsonl"

QUERY_KIND = "typo"

# One typo-kind query per source row (150 entries, matching aug_007.jsonl indices 1..150).
# Each query carries 1-3 realistic typos on content words and stays readable.
QUERIES: list[str] = [
    "stravinksy rite of sprng paris 1913 riuot iregular rhythms",  # 04151 Stravinsky premiere riot
    "30th birthay dinner rosas soho march 2026 sclalops menu",  # 04152 Rosa's 30th birthday dinner
    "started 168 eatng windo janury 2026 hungr faded wek thre",  # 04153 16:8 fasting start
    "colour anaylsis house of coluor april 2026 sof autumn oatmal",  # 04154 House of Colour Soft Autumn
    "started potery class tuesdya evenigs camden studio priya",  # 04155 pottery class Camden
    "portfoli visualzer golden butterfy backtst march 2026 tresury",  # 04156 Golden Butterfly backtest
    "plausble graph kafkas castel esay hit 50k readers hn march",  # 04157 Kafka Castle essay HN
    "nextintl replced homegrwn locale ruter next js middlware",  # 04158 next-intl locale router
    "hays imbrie shakleton 1976 sciece paper pacemakr ice ages",  # 04159 Hays-Imbrie-Shackleton Milankovitch
    "rufus turend 5 march 2026 cardbord crwn photos serius",  # 04160 Rufus 5th birthday
    "induction cokptop swap ge profile php9036 boshc 800 matter thred",  # 04161 induction cooktop swap
    "abadie 2003 synthtic control basqu terorism case papr",  # 04162 Abadie synthetic control Basque
    "bakthins dialgic imaginaton 1930s heterglossia translted 1981",  # 04163 Bakhtin Dialogic Imagination
    "truman doctrne march 1947 congress speach greece turky aid",  # 04164 Truman Doctrine 1947
    "met clara roftop pub quiz shordich septembr 2025 napkn numbr",  # 04165 Met Clara pub quiz
    "launchd thursdya supper clb febuary 2026 sichuan nigt four curses",  # 04166 Thursday supper club launch
    "insar interfermetry massonet 1992 landrs erthquake replaces gps",  # 04167 InSAR Massonnet Landers
    "lattice climing app replced paper lgbook frist v6 bouldr",  # 04168 Lattice climbing app V6
    "adopted vector rs worker binry replaces fluent bit sidcar",  # 04169 Vector in-process log forwarder
    "april 2026 wake routne lutron serena blnds hue 1900k to 4000k",  # 04170 Lutron Serena wake routine
    "oura ring detcted pregnancy thre weks befor test confrimed",  # 04171 Oura Ring pregnancy detect
    "duolngo french owl retird feburary 2026 612 day strek grammr",  # 04172 Duolingo French 612-day streak
    "dmanisi georga 18 millon year hominn skulls out of africa",  # 04173 Dmanisi hominin skulls
    "gateway api rolled out febuary 2026 httprute ingres bake",  # 04174 Gateway API rollout
    "rechaed 90 percnt line coverage backend march 2026 ci gate",  # 04175 90% backend line coverage
    "s3 strng read aftr wrte consistncy 2020 deletd retry loop",  # 04176 S3 strong consistency retry loop
    "wasi 0.2 landd preview2 filesytem sockts api cli polyfll",  # 04177 WASI 0.2 preview2
    "encode projct 2012 releas 80 percnt human genom functonal",  # 04178 ENCODE 80 percent functional
    "bark weekly digst april 2026 zero concrning messges lena discrd",  # 04179 Bark Lena Discord
    "pagedattntion memry sharing sibing reqests 28 percnt kv cahce",  # 04180 PagedAttention KV cache
    "launchd neghborhood bil split bot signl feburary 2026 lawn care",  # 04181 Signal bill-split bot
    "pnin nabakov finshed april 2026 boox palma 2 mbta red lne",  # 04182 Pnin Nabokov Boox Palma
    "bahai fath bahaulah baghdad garen of ridvan 1863",  # 04183 Baha'i Faith origin
    "hero smart pil dispenser replced weekly pilbox mom janury 2026 metfromin",  # 04184 Hero pill dispenser mom
    "seligman csikzentmihalyi 2000 americn psycholgist positve psycholgy",  # 04185 Seligman 2000 positive psychology
    "ford power up 5.3 mach e bluecrue hands fre lane changeg may 2026",  # 04186 Ford Power-Up Mach-E
    "prject valhalla valu types cordnate class map tiles heep",  # 04187 Project Valhalla value types
    "reched 1000th loged kilomtre april 2026 celbrated esay fve",  # 04188 1000 logged km
    "heegr macdiarmd shirakaw 1977 iodne doped polyactylene nobl 2000",  # 04189 Heeger polyacetylene Nobel
    "whiskr sos alert litterobot kumo 2am april 2026 myvca vet",  # 04190 Whisker Litter-Robot Kumo
    "boudering strenght blck end febuary 2026 hangboad pr crmpd",  # 04191 bouldering hangboard PR
    "memcachd binry protcol replced ascii photo servce multi get p99",  # 04192 Memcached binary protocol
    "treaty of westfalia 1648 soverign stats modrn sytsem",  # 04193 Westphalia 1648
    "brewfathr aplp replced beermith desktp april 2026 ispindel mqtt",  # 04194 Brewfather iSpindel MQTT
    "john nash 1950 pnas papr equlibrium mixed strategis game thery",  # 04195 Nash 1950 PNAS
    "atended twon councl ofice hour march 2026 chevit row parkng sundya",  # 04196 Cheviot Row parking council
    "migrtated family recpe papaika 3 to notion febuary 2026 briskt ipd",  # 04197 Paprika to Notion recipes
    "intl datetmformat formatrange locle corrct en dash utlity",  # 04198 Intl.DateTimeFormat formatRange
    "substak note april 2026 hardcovr kaito osaka pre orderd second",  # 04199 Substack Kaito Osaka pre-order
    "camino santiago sara to santago septmber 2026 grandma rosas shel",  # 04200 Camino Sarria Santiago
    "shopgoodwll tenba bag aucton 18 dolars feburary 2026 amzon 240",  # 04201 ShopGoodwill Tenba bag
    "waltr munk 1950 wave forcasting d day surf prediciton normady",  # 04202 Munk D-day wave forecast
    "jospeh smith dictated book of mormn 1829 palmyr new york gld plates",  # 04203 Book of Mormon 1829
    "stryd duo footpod pair april 2026 left rigt powr balance marcuss pt",  # 04204 Stryd Duo footpod
    "criticl legal studes 1977 conferncee libral legalsm hierrchy",  # 04205 Critical Legal Studies 1977
    "recahed elo 1500 chess com april 2026 tacticss thre months grind",  # 04206 Chess.com Elo 1500
    "venziano 1968 nuovo cimneto dual resonnce string thery birth",  # 04207 Veneziano 1968 string theory
    "italain duolingo strek 400 dayas april 2026 valntina may lesons",  # 04208 Italian Duolingo 400 days
    "milnor 1956 anals exotc smoth structres seven spheree differntial",  # 04209 Milnor exotic seven-sphere
    "moved tumbr archive to hugo feburary 2026 200 lne python permalnks",  # 04210 Tumblr to Hugo
    "ripped out dv soup naviation marketig site ul naav landmrk screen redaer",  # 04211 nav landmark ul
    "pakon f135 replced epson v600 feburary 2026 color negtive 90 secnds",  # 04212 Pakon F135 color negs
    "mirzakhni 2014 feilds medl moduli riemnn surfces weil petrsson",  # 04213 Mirzakhani Fields Medal
    "marie tharps 1950s bathmetric map mid atlantc ridge rift spradng",  # 04214 Marie Tharp Mid-Atlantic
    "backblze personl seeded 2.4 teabytes leica archve march 2026 lacie rugged",  # 04215 Backblaze Leica seed
    "lora adaptr hot swap requst time march 2026 tenant cold relaod",  # 04216 LoRA hot-swap adapters
    "deepmnd alphfold 2 publshed natur 2021 casp14 protein crystal",  # 04217 AlphaFold 2 CASP14
    "replced chain lnk fence east bundary 1.8 m clsoeboard janury 2026 neghbour",  # 04218 east fence closeboard
    "endangerd ainu revitlisation hokaido 1997 act 2019 indignous recogntion",  # 04219 Ainu revitalisation Hokkaido
    "producton hit fve nnes availbility frist quarter row april 2026",  # 04220 five-nines availability
    "aws solutons architect associte passd feburary 2026 saa c03 780 marek",  # 04221 AWS SAA passed
    "pored frist mead bath feburary 2026 ornage blosom honey rackng april",  # 04222 mead batch February 2026
    "hokaido supper club octoer 2025 miso butter scallps phone off",  # 04223 Hokkaido supper club
    "atlas cms higs boson 125 gev july 2012 lhc 7 and 8 tev",  # 04224 Higgs ATLAS CMS July 2012
    "grandpad tblet lila anwsred family vido cals ipad fourten months unused",  # 04225 GrandPad aunt Lila
    "joyces uylsses 1922 shakespar and co paris baned woosley 1933",  # 04226 Ulysses Woolsey ban
    "clara moved in togther february 2026 pekham flt lease 5545 splt",  # 04227 Clara Peckham 55/45
    "nomad lst filters lisbon co workng under 200 euros fibr cutof",  # 04228 Nomad List Lisbon
    "ynab four rule methd groceris envelpe gve every dollar job q1 2026",  # 04229 YNAB four-rule method
    "kafa posthmous max brod the tria castel amerka modrnsim",  # 04230 Kafka Max Brod posthumous
    "moved forg to neforge march 2026 minecft 1.21 al the mods 10 dev",  # 04231 Forge to NeoForge Minecraft
    "live chat cut latncy 340 ms to 95 ms march 2026 centrfugo anycst mesh",  # 04232 Centrifugo anycast
    "planing permision side extsion aproved febuary 2026 dayligt neghbour",  # 04233 side extension planning
    "swtiched whoel fronted to reaact 19 janury 2026 zero runtme regresions",  # 04234 React 19 upgrade
    "unity dots burst jobs crowd simulaton manged monobehavour editor tooling",  # 04235 Unity DOTS Burst
    "life360 staed famly phones feburary 2026 sasha schol bus i90 lst seen",  # 04236 Life360 Sasha I-90
    "csrf moved double submt to samsite lax cokies march 2026 orign check",  # 04237 CSRF SameSite Lax
    "mba aplication londn busines school janury 2026 gmat 720 medcine pivot",  # 04238 LBS MBA application
    "cloudflre hyperrdive pooled postgres conecctions workrs 480 ms to 90 ms",  # 04239 Hyperdrive Workers Postgres
    "rebult frendship hyden erly 2026 five lng phone cals 2024 fght writng",  # 04240 Rebuilt friendship Hayden
    "rome statue 1998 intrnational crimnal court hague genocde war crmes",  # 04241 Rome Statute ICC
    "guru gobnd sing founded khlsa anadpur sahib 1699 fve ks",  # 04242 Khalsa 1699 five Ks
    "world nmads proceessd seoul fligt canclation claim feburary 2026 agoda",  # 04243 World Nomads Seoul claim
    "atlas cms anounced higs boson discovry 2012 07 04",  # 04244 Higgs announcement 2012-07-04
    "sundya tabltop simulator dnd night sharred foundry vtt calndar janury 2026 doodl",  # 04245 D&D Foundry calendar
    "docs seo cleanp cannonical urls per version satori og imag organc 18 prcent",  # 04246 Docs SEO canonical og:image
    "dating latoli fotprints 3.66 millon years bipeal early austrlopithecines",  # 04247 Laetoli footprints
    "daily notes disiclipne stuck janury 2026 templtr morning pages yesterdya todo",  # 04248 Templater morning pages
    "started alxander technque lesons marcus feburary 2026 neck tensn lesn four",  # 04249 Alexander Technique Marcus
    "kanwishr 1997 fsiform face area cortcal region slectively faces",  # 04250 Kanwisher fusiform face
    "shred redis to caffine per servce migraton march 2026 cross servce contntion",  # 04251 Redis to Caffeine
    "volunter canvs traning febuary 2026 google jamboad midtown chapter turf",  # 04252 Canvass training Jamboard
    "joy crackd april 2026 noa asked my nighbor ttoro overseerr jellysere radar",  # 04253 Noa Totoro Overseerr
    "anual brogue resole pediwer halifax feburary 2026 goodyer welt haf rubr",  # 04254 Pediwear brogue resole
    "cousin wlls bby iris born feburary 2026 hand knit blanket grama ruth yrn",  # 04255 Cousin Will baby Iris
    "s3 versonng plus mfa delet protcted artifct bcket staging rb fource",  # 04256 S3 versioning MFA Delete
    "finshed tokyo marthon march 2026 eigt months tranning",  # 04257 Tokyo Marathon finished
    "ligo detcted frist gravittional wave 2015 09 14 binry black hole",  # 04258 LIGO first GW detection
    "traded 2014 honda civc for 2026 kia nro ev march 2026 westovr motrs clutch",  # 04259 Civic to Kia Niro EV
    "replced paper meal plan whtboard mealime janury 2026 instacrt mei cilntro",  # 04260 Mealime Instacart Mei
    "deciddim participtory budgt pilt crosed 4000 voters april 2026 librry crds",  # 04261 Decidim 4000 voters
    "crowdn replced manul spredsheet ops team github translaton prs catlogs",  # 04262 Crowdin GitHub translations
    "first cheroke purle ripened april 2026 hortisketc mifloa moistre 35 percnt",  # 04263 Cherokee Purple MiFlora
    "tractve alret april 2026 dusk arlo two blcks nrth live trackng arteial",  # 04264 Tractive Arlo alert
    "split tuscny trip chianti maremma june 2026 soutern strch suprise win",  # 04265 Tuscany Chianti Maremma
    "sibling caregving rotaton group txt to cozi calendr march 2026 priya marcus dialyss",  # 04266 Cozi caregiving rotation
    "custm axe core rules desin systm primtives dialg role modl",  # 04267 axe-core design system rules
    "califronia condr recovry programe 27 birds 1987 to 500 2020 san diego zoo",  # 04268 California condor recovery
    "peuguot randoneur rebult gumtre frame dyname lighting broks b17",  # 04269 Peugeot randonneur rebuild
    "cargo workspces shared target direcory 14 mins to 6 monorpo scache",  # 04270 Cargo workspaces monorepo
    "wrote codql queris in hose taint surces grapql resolvr argumnts sinks",  # 04271 CodeQL GraphQL taint
    "hit sub 20 parkrn hampstead heth april 2026 seond lap fastr by five",  # 04272 Hampstead Heath parkrun
    "kobyashi maskawa 2008 nobl phyiscs quark mxing matrx",  # 04273 Kobayashi-Maskawa Nobel
    "migrtated intrnal docs obsidan valts to logseq march 2026 grph backlnks",  # 04274 Obsidian to Logseq docs
    "smale 1961 annls h cobordsm therem higher dim poncare dim five",  # 04275 Smale h-cobordism theorem
    "defualt mode netwrk raichl 2001 rest intenally dierected thoght",  # 04276 Default mode network Raichle
    "emapthy grief aplp estate close chcklist dad passd janury 2026 medicre advantge",  # 04277 Empathy grief estate close
    "clsed wels fargo cheking feburary 2026 atm fe schwab bank glbal refund",  # 04278 Wells Fargo to Schwab
    "shiped tree sitter code serch april 2026 reviews quoate snippts by rnges",  # 04279 tree-sitter code search
    "patreon teir restrcture feburary 2026 monthly novela 10 dolar wrld buildng 5",  # 04280 Patreon tier novella
    "coredns nodelcal cache dns p99 80 ms to 4 ms mesh droping conections",  # 04281 CoreDNS NodeLocal cache
    "postgrs 16 paralel hash agregate march 2026 analytcs funel worke mem",  # 04282 Postgres 16 parallel hash
    "andrw wiles 1995 anls mathmatics modularty semistbel ferats lst theorm",  # 04283 Wiles Fermat Last Theorem
    "exoplnet transit photmetry kepler dozns to thosand confrimed plants",  # 04284 Kepler exoplanet transits
    "started wekly therpy dr halpen janury 2026 cbt 50 minutes wednesdya 1400 vido",  # 04285 Dr Halpern weekly therapy
    "rust gats async strem adpater zero cost drped boxed futre shim 2021",  # 04286 Rust GATs Stream adapter
    "lambdamrt learnng to rnk clickstrem ndcg 10 lifted 6 point hand tuned",  # 04287 LambdaMART clickstream
    "ls50 wireles ii vs kef lsx ii audtion in livng stero march 2026 manhatn",  # 04288 KEF LS50 audition
    "oldst daughtr fern asked lck bedrom dor march 2026 fir drlis first",  # 04289 Fern lock bedroom door
    "polar vantge v3 fell behind garmn bke lght intgration march 2026 group rde",  # 04290 Polar V3 Backloop
    "sumer camp bokng both kds woodlan adventre april 2026 augst depsit 120",  # 04291 Woodland Adventure camp
    "portd chat presnce node eventemtter to elxir genserver supervsd restarts",  # 04292 Elixir GenServer chat
    "compartive law instittionalised 1900 paris congres salleles lambrt",  # 04293 Paris 1900 Comparative Law
    "endangerd hawaian revitlisation punana leo nest presscools 1984 kaipuni",  # 04294 Hawaiian Punana Leo
    "reactve dog clss pawsitve steps march 2026 thrshold distance hugo twleve to sevn",  # 04295 Pawsitive Steps Hugo
    "kata conatiners 3.0 dragnball feburary 2026 rust micro vm 40 mb qemu",  # 04296 Kata 3.0 Dragonball
    "pride hit april 2026 indie gme festvel accpeted pxel puzler aseprte ldtk godot 4",  # 04297 Indie Game Festival Aseprite
    "tesla ota march 2026 mdel y firmwre 2026.8.5 blnd spot camra overley",  # 04298 Tesla OTA blind-spot
    "fine tuneed reranker pased 0.85 ndcg threshld march 2026",  # 04299 reranker nDCG 0.85
    "zookepr retird kafa cluster kraft metdata qorum thre brokrs jvm count",  # 04300 ZooKeeper to KRaft
]


def _load_sources() -> list[dict]:
    with SOURCES.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def emit() -> int:
    if len(QUERIES) != 150:
        raise ValueError(f"expected 150 queries, got {len(QUERIES)}")
    sources = _load_sources()
    if len(sources) != 150:
        raise ValueError(f"expected 150 source rows, got {len(sources)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (src, query) in enumerate(zip(sources, QUERIES), start=1):
            word_count = len(query.split())
            if not (5 <= word_count <= 15):
                raise ValueError(f"query {i} has {word_count} words, out of 5-15 range: {query!r}")
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
