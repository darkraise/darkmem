"""One-off emitter for retrieval aug batch-008 (typo-kind queries).

Reads the pre-picked source rows at
`data/v2/retrieval/aug_sources/aug_008.jsonl` and emits one retrieval
top-up row per source with a short, plausibly-misspelled query. Output
is written to `data/v2/retrieval/aug_008.tmp.jsonl` with ids
ret-04301..04400 taken from each source row's `new_id` field.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "v2" / "retrieval" / "aug_sources" / "aug_008.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "aug_008.tmp.jsonl"

QUERY_KIND = "typo"

# One typo-kind query per source row (100 entries).
# Each query contains 1-3 realistic typos across content words and stays readable.
QUERIES: list[str] = [
    "aqara fp2 mmwve sensrs replaced pir motion in livig room",  # 04301
    "nix-buit container images replced dockerfile for reserch toolbox",  # 04302
    "miscariage july 2025 reshapd next pregnacy no scan photos fridg",  # 04303
    "neo4j bloom rolled out to analyts no-cypher seach bar replced gephi",  # 04304
    "sansaire delta replced polyscience creatve on sous-vide webhook triger",  # 04305
    "chose saturdy slot over sunday at comunity garden dig-over group",  # 04306
    "cloudflre r2 kept blobs outsid d1 egres-free reads cut bandwith",  # 04307
    "btrfs subvolumes replced ext4 parttions on dev workstaions snaphots",  # 04308
    "petlibro polar ice-colled feder replced granary for raw-food diet",  # 04309
    "astro 5.2 rebuid replced gatsby 4 personl site march 2026",  # 04310
    "planer hints off by default pg_hint_plan only for escpe-hatch cases",  # 04311
    "airbye replced fivetran on low-priorty ad-platfom sources saved 18k",  # 04312
    "replced withings body scan with renpho elis 2 bioimpednce export",  # 04313
    "flux helm contoller replced legacy tilr install on lab clustr",  # 04314
    "mobx observbles still drive legacy reportng froze migraton decorater",  # 04315
    "swift concurency actors movd dashbord state off ad-hoc loks",  # 04316
    "pawlicy advisr steered peper insurnce to lemonad pet ivdd rider",  # 04317
    "miler-rabin primalty testng trades determnism for speed monte calro",  # 04318
    "okonkwos ofice swaped google forms for taly after ip leak",  # 04319
    "avro logicl types carry decmal timestam-milis uuid across warhouse",  # 04320
    "apche ignite evalated against hazlcast for compute-grd cache splt",  # 04321
    "droped reselect for native structurlsharing in rtk quiry 2",  # 04322
    "replced try except with typd startuperor supervsor distnguishes recverable",  # 04323
    "four princples framwork replces casuitic bioethcs shared vocabulry",  # 04324
    "linkerd multiclustr mirror servce replced homegrown dns-stb bridg",  # 04325
    "datahub took over from marqez as cross-team catalgue colum lineag",  # 04326
    "higher-kindd shape via fp-ts hkt trik kept reposity combinatr polymorhic",  # 04327
    "otlp metrcs over opentelmetry colector replced direct statsd shiping",  # 04328
    "swiched mornig prayer from brevary lauds to lectio divina esv",  # 04329
    "swiched from shel v-power to supermrket 95 ron outbak 2025",  # 04330
    "picked temporl for new biling retry engin determnstic replay",  # 04331
    "pulumi esc replced vaultd dotenv loadr on go servces encrypted",  # 04332
    "book of comon prayer daily prayr app replced paper brevary comute",  # 04333
    "web workr pool sizes to navigtor hardwreconcurency minus one editr",  # 04334
    "rtk quiry replced bespke fetch plus thunk layr in biling modue",  # 04335
    "redis maxmemry-policy set to allkeys-lfu on recomendation cach",  # 04336
    "birthdy marthon goal moved to septmber 2026 after whoop recvery",  # 04337
    "grafana pyrosope replced homegrown pprof scrap loop flme graphs",  # 04338
    "swiched spatal smothing prior from gausian to matren localy rougher",  # 04339
    "canceld zwift subscrption rebuit pain cave dumb trainr videos",  # 04340
    "lisbn flat rentl autum trip thrid of barcelna booking tomoro",  # 04341
    "klarna replced afirm for feb sonos era 300 split no cred pul",  # 04342
    "bandcmp replced itunes on janury 2026 for indi releases 24 bit wav",  # 04343
    "silvercloud cbt module replced weekly in-persn therpy aunt lila",  # 04344
    "retry policies at workfow level in temporl centralizd backof max atemps",  # 04345
    "swiched parakeet sed mix from trill to versle-laga prestge pip keel",  # 04346
    "datadog carryd application monitorng honycomb adoptd for deep trce",  # 04347
    "gradle verson catalogs libs versons toml replced ext propeties",  # 04348
    "workrd local dev replced minflare on workrs project parity runtme",  # 04349
    "replced runtpes with zod on legacy gatway inferd ts types one plce",  # 04350
    "jitsi videobridg retird from clasroom livekit simulcst covrage better",  # 04351
    "cloudflare queus carryd webhok retris out of worker 15 second cpu wal",  # 04352
    "hauld boss rc-600 from storge midi footswich loop acoustc clara zoom",  # 04353
    "zoxde replced z scrip on dotfiles rust rewrite respect xdg dirs",  # 04354
    "anbernc rg556 stayd in drawr steam dek oled emudeck syncthing nas",  # 04355
    "priceblnk browser compaison replced tab shufle sony wh 1000xm6 hunt",  # 04356
    "cohere rernk replced in-hous cross encodr long-tail queris ndcg up",  # 04357
    "swaped mytherpy for medisafe on mom iphone medfrind warfarn alert",  # 04358
    "opus at 32 kbps handld voice chanel swiched from g711 saved bandwith",  # 04359
    "strava segmnt chasng on gravl loop now pulls wahoo roam gpx not garmn",  # 04360
    "barns walis geodtic airfame first used on vickrs welingon 1936 bombr",  # 04361
    "cargo lock comited for cli crats too reprducible builds shiped binris",  # 04362
    "lent 2026 fast is alchol and weekdy social media ash wednesdy ashes",  # 04363
    "kagi replced gogle as default serch everywere ad-fre resuls ethos",  # 04364
    "crouton ios recipe libary replced mela on bedside ipad shortuts siri",  # 04365
    "biomejs is now formater plus lintr for new typscript repos oxc unfinshd",  # 04366
    "replced ray-ban wayfarrs with persol 714 foldabls in apirl pocket",  # 04367
    "contracter selecton for extention went to bevn builds over rockhil",  # 04368
    "zephr rtos devce tre overlys carryd custm board pinmux vendr hal out",  # 04369
    "envy replced ngix as l7 proxy infront of checout cluster xds dynamc",  # 04370
    "infuse on aple tv 4k replced stok tvos jelyfin dolby visn pasthrough",  # 04371
    "presto frozn after trino governnce split new conectors targt trino",  # 04372
    "movd anki reviws from desktp to mobil on comute 91 day streak",  # 04373
    "swaped picturethis for plantnt on pixel 9 quercus ilex cork oak",  # 04374
    "comfyu replced automatic1111 for album covr concpting node graph lora",  # 04375
    "graphsn replced homgrown binry dump on tinkerpp importp pipeline",  # 04376
    "apche camel routes orchstrated cross-brokr between rabitmq and kafa",  # 04377
    "efect-ts landd on new orchstration modue makes deps erors visble",  # 04378
    "karpentr replced clustr autoscalr on spot flet launches under 30s",  # 04379
    "advancd tables plugin rescud readng-log markdwn table 300 row pipe",  # 04380
    "beancont replced old gogle sheets ledgr on janury 2026 401k typo",  # 04381
    "wise bordrless multi-curency replced schwab checkng for atm withdrawls",  # 04382
    "wrote small codemd with jscodeshift from react fc to explict prop types",  # 04383
    "renovat config pins grup rules schedle windws per repo dependabt lacked",  # 04384
    "signd up for salsa clases at bar salsa temle replace pub quiz slot",  # 04385
    "mil replced sbt for new scla servces incremntal compilr quirks cold",  # 04386
    "pincone rejectd for on-prem deploymnt managed-ony not fit air-gaped",  # 04387
    "dxo photolb 8 deeprime xd nois reduction beats lightrom ai denois nikon",  # 04388
    "jetpack compse replced evry xml layut in onboardng flow viewbinding gon",  # 04389
    "templat engine picked jinja2 with autoescape true globaly safe filter",  # 04390
    "moved localisation pipline from crowdn to weblate self-hostng ownshp",  # 04391
    "smallstp replced hashcorp boundry for opertor acess acme enrolment",  # 04392
    "ice candidte gathring capped at 3 seconds on mobil battry life",  # 04393
    "steam dek libary stabilsed once proton-ge replced defult protn yakuza",  # 04394
    "etrade powr e-trade replced robinhod options on janury 2026 greks",  # 04395
    "randomised ttl jiter plus minus 10 percent memcached expire strm catalog",  # 04396
    "fredom mac block march 2026 replced manul etc hosts redircts sync",  # 04397
    "univrsal compacton on sesion store kept sst file count low bursts",  # 04398
    "woodworkng shop notebok moved from index cards to notion routr plans",  # 04399
    "ratgdo board replced chamberln logic on garag door esphome myq sub",  # 04400
]


def _load_sources() -> list[dict]:
    with SOURCES.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def emit() -> int:
    if len(QUERIES) != 100:
        raise ValueError(f"expected 100 queries, got {len(QUERIES)}")
    sources = _load_sources()
    if len(sources) != 100:
        raise ValueError(f"expected 100 source rows, got {len(sources)}")
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
