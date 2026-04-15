"""One-off emitter for retrieval top-up batch-007 (typo-kind queries).

Reads shared rows at 0-indexed line offsets 600..699 from
`data/v2/shared/shared.jsonl` and emits one retrieval top-up row per
source with a short, plausibly-misspelled query. Output is written to
`data/v2/retrieval/batch_007.tmp.jsonl` with ids ret-00601..00700.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_007.tmp.jsonl"

ID_OFFSET = 600
SHARED_OFFSET = 600
QUERY_KIND = "typo"

# One typo-kind query per source row (100 entries, matching shared lines 600..699).
# Each query contains 1-3 realistic typos across content words and stays readable.
QUERIES: list[str] = [
    "who hanldes the fiances for our parnets' house now",  # 601
    "grampa theos old rocing chair in the nurserey",  # 602
    "splitting dinenr cleanup with noah over breakfsat",  # 603
    "mother-in-law colete brings kouign amnan evry visit",  # 604
    "aunt priscila moved into the granny flate behind the garge",  # 605
    "letting theo wlak to shcool alone decision",  # 606
    "dads hearng aids wistling dinner audiolgist refit",  # 607
    "cat miso prefrs my side of the bd once lamp off",  # 608
    "cousin mateo calling me tia big at 2026 sprig reuinon",  # 609
    "hang on i need to gab a pen befor you keep going",  # 610
    "signal replcaed whatsap after cousins accont compromisd",  # 611
    "uncle reinholds meatlof recipe on photcopied sheet betty croker",  # 612
    "prefers queit one on one waks with dad over thanksgivng crowd",  # 613
    "nibbles the hampster died 2025 funeral by the rosbush",  # 614
    "household chor rotaton pined on fridge magntic strips",  # 615
    "brother-in-law arash pays law srvice we reimburse qurterly",  # 616
    "agreed with maya homwork at kichen tble screns upstais",  # 617
    "grandma ingrid argued about 1997 christmsas photo acutally 1995",  # 618
    "prefers caling mom sundya mornings over late-nigth texts",  # 619
    "cousin wills bby iris born feburary hand-kint blankt",  # 620
    "shred google calender replacd paper wal calendar househod",  # 621
    "stepdad ron buids birdhoses in garge saturdys blue jaays",  # 622
    "weeknd pancakes with neices builds on waffle bruches before clara",  # 623
    "sam and i split shraed fiances 60/40 higher incom",  # 624
    "dog evning walks replced by morning walks after grampa moved in",  # 625
    "prefers hostng small sundya luncehs over big brithday parties",  # 626
    "great-aunt sabines handwrtten bread book from alsaace 1952",  # 627
    "jess and i stoped bickering thermostt 19c nights 21c mornigns nest",  # 628
    "cousin ades engagment anounced sundya diner auntie pat cryed",  # 629
    "nephew felix refses anyhting green unless rapped in cheese",  # 630
    "moved lundry hampr from halway to upstais landig",  # 631
    "grandma ida only drnks tea from chiped blue mugg",  # 632
    "every thrid weeknd in-law vist rhythem replaced drop-in chaos",  # 633
    "actualy scratch that i ment the other one",  # 634
    "kids shared chor jar builds on old stiker chart money gold strs",  # 635
    "nieghbour mrs okafor watchs the dog when we vist mom cleveand",  # 636
    "younger borther theodore caled 2am his dog wiskey siezure",  # 637
    "prefers eating at dinning tble with everone over tv diners on couch",  # 638
    "dad moved in spar room aftr hip surgry janury six weks",  # 639
    "weekly famly meetng improves on old diner-tble ambush approch",  # 640
    "prefers mothr-in-law quche recipie over my own creme frache",  # 641
    "twin marlene alternat hostng hanuka even years hers odd mine",  # 642
    "grandpa henri tught leo to wistle through acorn cap lke house",  # 643
    "shared houshold budet spredsheet replced envelpes system subscribtions",  # 644
    "aunt jolens lasgne strictly no-ricota uses bechamel milaense grandmther",  # 645
    "oldest dauhgter fern asked to lock bedroom dor fire drils",  # 646
    "prefrs handwriten brithday cards from kids over stor-bought crayn",  # 647
    "cant agre where to scater grandma veras ases galway vs rose garden",  # 648
    "sundya famly vido cll with melborne cousins 8am thre cameras",  # 649
    "moved dads medication remiders from paper list to medsafe app",  # 650
    "swaped morning jog for indor rowing concept2 erg spars shins",  # 651
    "joined thursay ukulelle circle at dalston pub rotatig openng song",  # 652
    "prefers bouldring at the castel over rope climbing arch lunch windo",  # 653
    "finished kniting the cabl-knit jumpr 2026 after eighten months yok three atemps",  # 654
    "sourdough startr bubles in fride feed friday nigth bake sundya",  # 655
    "swiched from dslr to fuji xt5 for stret photgraphy leaf shuter silense",  # 656
    "stelarium app flagging jupter near westrn horizon 2130 april",  # 657
    "tomato seedings frose night of april 2 greenhous heatr unplugd",  # 658
    "prefers plein air skeching with pentl brush pen over indor watrcolor",  # 659
    "hang on i need to gab my coffe real quick",  # 660
    "started brazlian jiu jitsu at gracie bara janury frist stripe wite belt",  # 661
    "reformer pilats at hartcore builds on mat pilats foundaton from 2022",  # 662
    "aquired a frist pressng of kind of blue at brik lane fair sleve rogher",  # 663
    "swiched to darkrom printg on ilford multgrade retired scan and edit pipline",  # 664
    "sprint coach marco has me doing hil repets parliment hil tuesdya 0630",  # 665
    "hit a sub 20 parkun at hampsted heath apirl scond lap fater",  # 666
    "sprig triathlon may 23 at dornay lake is the gaol race this year",  # 667
    "prefers saito woodwrking chisels over narex set edge retenton not close",  # 668
    "poured frist mead batch feburary orange blosom honey raking late april",  # 669
    "cross stich samplr for grans 80th replacs stor-bought card plan",  # 670
    "saturdya caligraphy clas at drink shop and do coperplate oblque holders",  # 671
    "joined hakney rowing club sinle sculls programe frist capsiz drll april",  # 672
    "birdwatchng log 142 speceis london area firecrest walthamstow sundya",  # 673
    "origami dragn from robert lang book four hors two sheets kmi paper",  # 674
    "prefers niko sumi ink over chinse ink stik daily brush practce",  # 675
    "wheel thrwn mugs pulling ovall on shimpo bat is fine pulls uneven",  # 676
    "saturdya long rde 80 km through eping forst peleton splits wake arms",  # 677
    "reched elo 1500 on chess com april after grindig tacics thre months",  # 678
    "skechbook pro on ipad pro builds on paper skechbook habit 2019 to 2023",  # 679
    "signed up for salsa clases at bar salsa tempel replcae weekly pub quiz",  # 680
    "prefers thicer korean hangi for ink paintngs over standrd xuan less beed",  # 681
    "peugot randoneur rebuilt from gumtree frme dynamo lightng brooks b17",  # 682
    "italain dualingo streak 400 dyas april spekaing lesons valntina may",  # 683
    "right let me dubble-check somthing befor i answr",  # 684
    "heart rate zne traning improves on flat pce approch no progres for years",  # 685
    "japanes joinry bench built with only hand tols improves on dowl and glu 2021",  # 686
    "keeps tacle box sorted by target speceis trout flys top pike gear botom",  # 687
    "fridya open mic at camden head builds on bedrom guitr practce 2020 lokdown",  # 688
    "lost the handmde leather wallt on 5a bus to kew gardns april no luk lost proprty",  # 689
    "prefers strava segmnts for motivaton over garmin conect dashbords",  # 690
    "comunity choir at st marys sings evry other wednesdya ruth runs soprano",  # 691
    "miloga nights at negrcha improve on beginer socials tango west floorcaft",  # 692
    "canceled zwift subscripton rebuilt pain cav with dumb trainer cycling vidoes",  # 693
    "kew gardns membrship card pined to fridge orchid hose closes 1730 sprig",  # 694
    "comic colction outgrew ikea bily moving to oak shelfs dad built to spec",  # 695
    "prefers muji 038 gel pens over pilot g2 for bulet journaling line wegiht",  # 696
    "scale model spitfre 124 airfix on desk since janury canpy masking next",  # 697
    "figur drawing group at candid arts mondys improves on magzine pose boks at home",  # 698
    "swiming 2 km at london feilds lido sundya mornings wakes me faster than espreso",  # 699
    "tabletop rpg group at orcs nest evry other fridya seb runing motherhip campagin",  # 700
]


def _load_sources() -> list[dict]:
    with SHARED.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    slice_ = lines[SHARED_OFFSET:SHARED_OFFSET + 100]
    return [json.loads(line) for line in slice_]


def emit() -> int:
    if len(QUERIES) != 100:
        raise ValueError(f"expected 100 queries, got {len(QUERIES)}")
    sources = _load_sources()
    if len(sources) != 100:
        raise ValueError(f"expected 100 source rows at offset {SHARED_OFFSET}, got {len(sources)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (src, query) in enumerate(zip(sources, QUERIES), start=1):
            word_count = len(query.split())
            if not (4 <= word_count <= 18):
                raise ValueError(f"query {i} has {word_count} words, out of 4-18 range: {query!r}")
            row = {
                "id": f"ret-{ID_OFFSET + i:05d}",
                "source_id": src["id"],
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
