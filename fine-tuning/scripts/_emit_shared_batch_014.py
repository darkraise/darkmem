"""One-off emitter for shared-base batch-014 — personal domain (hobbies/leisure/sports/creative).

Same pattern as _emit_shared_batch_008.py; only ENTRIES and offsets change.
Writes 50 rows to data/v2/shared/batch_014.tmp.jsonl with ids shared-00651..00700.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_014.tmp.jsonl"
ID_OFFSET = 650

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Swapped the morning jog for indoor rowing on the Concept2; the erg spares my shins on winter mornings.", "decision", "personal", False,
     [("morning jog", "activity"), ("indoor rowing", "activity"), ("Concept2", "tool")],
     [("indoor rowing", "morning jog", "REPLACES")],
     "what took over as my cold-weather aerobic session this season",
     "winter cardio switch shin relief machine choice"),
    # --- 2 ---
    ("Joined a Thursday ukulele circle at the Dalston pub; we rotate who picks the opening song.", "milestone", "personal", False,
     [("ukulele circle", "hobby"), ("Thursday", "date"), ("Dalston pub", "place")],
     [],
     "when and where does the string-instrument meetup happen",
     "weekly strum gathering east London venue rotation"),
    # --- 3 ---
    ("Prefers bouldering at The Castle to rope climbing at Arch; the short problems suit my lunch window better.", "preference", "personal", False,
     [("bouldering", "activity"), ("The Castle", "place"), ("rope climbing", "activity"), ("Arch", "place")],
     [("bouldering", "rope climbing", "PREFERS")],
     "which climbing style fits my midday schedule",
     "short wall problems over lead work lunchtime session"),
    # --- 4 ---
    ("Finished knitting the cable-knit jumper on 2026-03-29 after eighteen months; the yoke took three attempts.", "milestone", "personal", False,
     [("cable-knit jumper", "hobby"), ("2026-03-29", "date")],
     [],
     "when did the long sweater project finally come off the needles",
     "large woollen garment completion date redos involved"),
    # --- 5 ---
    ("My sourdough starter, Bubbles, sits in the fridge between bakes; feed Friday night, bake Sunday morning.", "architecture", "personal", False,
     [("Bubbles", "food"), ("fridge", "place"), ("Friday", "date"), ("Sunday", "date")],
     [],
     "how is the wild-yeast culture managed across the week",
     "refrigerated levain schedule feed bake cadence"),
    # --- 6 ---
    ("Switched from a DSLR to the Fuji X-T5 for street photography; the leaf-shutter silence matters in markets.", "decision", "personal", False,
     [("DSLR", "tool"), ("Fuji X-T5", "tool"), ("street photography", "hobby")],
     [("Fuji X-T5", "DSLR", "REPLACES")],
     "which camera became the new everyday body for candid work",
     "mirrorless body candid shooting quiet shutter reason"),
    # --- 7 ---
    ("The Stellarium app keeps flagging Jupiter near the western horizon at 21:30 through April.", "reference", "personal", False,
     [("Stellarium", "tool"), ("Jupiter", "concept"), ("April", "date")],
     [],
     "which sky app is showing the gas giant low in the west",
     "astronomy software planet alert evening low spring"),
    # --- 8 ---
    ("The tomato seedlings froze on the night of 2026-04-02; the greenhouse heater had unplugged itself.", "problem", "personal", False,
     [("tomato seedlings", "food"), ("2026-04-02", "date"), ("greenhouse heater", "tool")],
     [],
     "why did the young plants die overnight last week",
     "greenhouse loss cold snap heater fault seedling"),
    # --- 9 ---
    ("Prefers plein-air sketching with a Pentel brush pen over indoor watercolour sessions when the weather allows.", "preference", "personal", False,
     [("plein-air sketching", "hobby"), ("Pentel brush pen", "tool"), ("indoor watercolour", "hobby")],
     [("plein-air sketching", "indoor watercolour", "PREFERS")],
     "which drawing approach wins when the sky cooperates",
     "outdoor brush pen work over inside wash art"),
    # --- 10. noise ---
    ("Hang on, I need to grab my coffee real quick.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Started Brazilian jiu-jitsu at Gracie Barra in January; earned the first stripe on my white belt last week.", "milestone", "personal", False,
     [("Brazilian jiu-jitsu", "hobby"), ("Gracie Barra", "organization"), ("January", "date")],
     [],
     "which grappling art did I take up at the start of the year",
     "mat training school enrollment stripe progression"),
    # --- 12 ---
    ("The reformer pilates at Heartcore builds on the mat pilates foundation I had from 2022.", "fact", "personal", False,
     [("reformer pilates", "hobby"), ("Heartcore", "organization"), ("mat pilates", "hobby"), ("2022", "date")],
     [("reformer pilates", "mat pilates", "BUILDS_ON")],
     "how does my current studio practice tie back to the earlier floor work",
     "spring-loaded apparatus session earlier floor base continuity"),
    # --- 13 ---
    ("Acquired a first pressing of Kind of Blue at the Brick Lane fair; the sleeve was rougher than the vinyl.", "fact", "personal", False,
     [("Kind of Blue", "publication"), ("Brick Lane fair", "event")],
     [],
     "which jazz record did I score at the east London collectors' market",
     "rare jazz LP vintage market pickup sleeve condition"),
    # --- 14 ---
    ("Switched to darkroom printing on Ilford Multigrade and retired the scan-and-edit pipeline for the black-and-white project.", "decision", "personal", False,
     [("darkroom printing", "activity"), ("Ilford Multigrade", "tool"), ("scan-and-edit pipeline", "activity")],
     [("darkroom printing", "scan-and-edit pipeline", "REPLACES")],
     "what took over from the digital workflow for monochrome prints",
     "wet print tradition over hybrid scanner darkroom paper"),
    # --- 15 ---
    ("The sprint coach Marco has me doing hill repeats on Parliament Hill every Tuesday at 06:30.", "reference", "personal", False,
     [("Marco", "person"), ("Parliament Hill", "place"), ("Tuesday", "date")],
     [],
     "who prescribed the weekly incline session and when does it run",
     "speed coach gradient drill dawn slot location"),
    # --- 16 ---
    ("Hit a sub-20 parkrun at Hampstead Heath on 2026-04-04; the second lap was five seconds faster than the first.", "milestone", "personal", False,
     [("parkrun", "event"), ("Hampstead Heath", "place"), ("2026-04-04", "date")],
     [],
     "when did the five-kilometre time finally dip under twenty minutes",
     "weekend timed run breakthrough heath negative split"),
    # --- 17 ---
    ("The spring triathlon on 2026-05-23 at Dorney Lake is the goal race this year.", "milestone", "personal", False,
     [("spring triathlon", "event"), ("2026-05-23", "date"), ("Dorney Lake", "place")],
     [],
     "which multi-sport event is the A-race on the calendar",
     "three-discipline race target date rowing lake venue"),
    # --- 18 ---
    ("Prefers the Saito woodworking chisels over the Narex set I started with; edge retention is not close.", "preference", "personal", False,
     [("Saito woodworking chisels", "tool"), ("Narex set", "tool")],
     [("Saito woodworking chisels", "Narex set", "PREFERS")],
     "which bench tools won out after a year of use",
     "Japanese chisel over Czech set hardness comparison"),
    # --- 19 ---
    ("Poured the first mead batch on 2026-02-11 using orange blossom honey; racking scheduled for late April.", "milestone", "personal", False,
     [("mead", "food"), ("2026-02-11", "date"), ("orange blossom honey", "food")],
     [],
     "when did the honey wine brew begin and what is the next step",
     "mead start date racking schedule honey variety"),
    # --- 20 ---
    ("The cross-stitch sampler for Gran's 80th replaces the store-bought card plan; three evenings of work so far.", "decision", "personal", False,
     [("cross-stitch sampler", "hobby"), ("Gran", "person"), ("store-bought card plan", "activity")],
     [("cross-stitch sampler", "store-bought card plan", "REPLACES")],
     "what homemade present is standing in for the shop gift",
     "embroidered sampler milestone birthday gift swap effort"),
    # --- 21 ---
    ("The Saturday calligraphy class at Drink, Shop & Do teaches copperplate with oblique holders.", "fact", "personal", False,
     [("calligraphy class", "hobby"), ("Saturday", "date"), ("Drink, Shop & Do", "organization"), ("copperplate", "concept")],
     [],
     "what lettering hand does the weekend class focus on",
     "pointed pen session weekend shop venue script"),
    # --- 22 ---
    ("Joined the Hackney Rowing Club single sculls programme; the first capsize drill is on 2026-04-19.", "milestone", "personal", False,
     [("Hackney Rowing Club", "organization"), ("single sculls programme", "activity"), ("2026-04-19", "date")],
     [],
     "when is the solo boat swim test happening at the new club",
     "rowing beginner programme capsize test date"),
    # --- 23 ---
    ("My birdwatching log now has 142 species for the London area; spotted a firecrest at Walthamstow last Sunday.", "fact", "personal", False,
     [("birdwatching log", "tool"), ("London", "place"), ("firecrest", "concept"), ("Walthamstow", "place")],
     [("firecrest", "Walthamstow", "LOCATED_IN")],
     "how many species are on the city-area list and what was the newest",
     "urban birding tally recent rare addition reservoir"),
    # --- 24 ---
    ("The origami dragon from the Robert Lang book took four hours and ate two sheets of kami paper.", "fact", "personal", False,
     [("origami dragon", "hobby"), ("Robert Lang", "person"), ("kami paper", "tool")],
     [],
     "which folded-figure project chewed up most of yesterday afternoon",
     "paper dragon complex fold designer book session"),
    # --- 25 ---
    ("Prefers the Nikko sumi ink over the Chinese ink stick for daily brush practice; the pine soot is softer.", "preference", "personal", False,
     [("Nikko sumi ink", "tool"), ("Chinese ink stick", "tool")],
     [("Nikko sumi ink", "Chinese ink stick", "PREFERS")],
     "which black media won out for regular brush drills",
     "Japanese bottled versus Chinese stick soot comparison"),
    # --- 26 ---
    ("Wheel-thrown mugs keep pulling oval on the Shimpo; the bat is fine, my pulls are still uneven.", "problem", "personal", False,
     [("Shimpo", "tool")],
     [],
     "why do the new cups keep coming out lopsided on the wheel",
     "pottery throw imbalance beginner centering issue"),
    # --- 27 ---
    ("The Saturday long ride hits 80 km through Epping Forest; the peloton splits at the Wake Arms roundabout.", "architecture", "personal", False,
     [("Saturday long ride", "activity"), ("Epping Forest", "place"), ("Wake Arms roundabout", "place")],
     [],
     "how is the weekend cycling route shaped around the forest",
     "weekend bike loop woodland split point distance"),
    # --- 28 ---
    ("Reached Elo 1500 on Chess.com on 2026-04-08 after grinding tactics for three months straight.", "milestone", "personal", False,
     [("Chess.com", "service"), ("2026-04-08", "date")],
     [],
     "when did the online chess rating cross the four-digit line",
     "online chess rating milestone tactic grind date"),
    # --- 29 ---
    ("Sketchbook Pro on the iPad Pro builds on the paper sketchbook habit I ran through 2019 to 2023.", "fact", "personal", False,
     [("Sketchbook Pro", "tool"), ("iPad Pro", "tool"), ("paper sketchbook habit", "activity"), ("2019", "date"), ("2023", "date")],
     [("Sketchbook Pro", "paper sketchbook habit", "BUILDS_ON")],
     "how does the digital drawing setup carry over from the old paper routine",
     "tablet drawing continuation prior notebook habit years"),
    # --- 30 ---
    ("Signed up for salsa classes at Bar Salsa Temple to replace the weekly pub quiz slot; two more hips, fewer pints.", "decision", "personal", False,
     [("salsa classes", "hobby"), ("Bar Salsa Temple", "organization"), ("weekly pub quiz", "activity")],
     [("salsa classes", "weekly pub quiz", "REPLACES")],
     "what dance practice took over the trivia evening slot",
     "latin dance lesson swap trivia night venue"),
    # --- 31 ---
    ("Prefers the thicker Korean hanji for ink paintings over standard Xuan; less bleed, more forgiving.", "preference", "personal", False,
     [("Korean hanji", "tool"), ("Xuan", "tool")],
     [("Korean hanji", "Xuan", "PREFERS")],
     "which paper stock wins for controlled ink work",
     "Korean mulberry sheet over Chinese paper ink control"),
    # --- 32 ---
    ("The Peugeot randonneur I rebuilt from a Gumtree frame now has proper dynamo lighting and a Brooks B17.", "milestone", "personal", False,
     [("Peugeot randonneur", "tool"), ("Gumtree", "service"), ("Brooks B17", "tool")],
     [],
     "what did the steel bike project end up with for touring kit",
     "vintage frame build dynamo lamp leather saddle"),
    # --- 33 ---
    ("The Italian Duolingo streak hit 400 days on 2026-04-10; speaking lessons with Valentina start in May.", "milestone", "personal", False,
     [("Italian", "language"), ("Duolingo", "service"), ("2026-04-10", "date"), ("Valentina", "person"), ("May", "date")],
     [],
     "when did the language app run cross the four-hundred mark",
     "Italian app chain milestone tutor start next step"),
    # --- 34. noise ---
    ("Right, let me double-check something before I answer.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("My heart-rate zone training improves on the flat-pace approach I stuck with for years without progress.", "fact", "personal", False,
     [("heart-rate zone training", "method"), ("flat-pace approach", "method")],
     [("heart-rate zone training", "flat-pace approach", "IMPROVES_ON")],
     "how is the new training method better than the old one",
     "zoned aerobic regime over uniform tempo plateau breakthrough"),
    # --- 36 ---
    ("The Japanese joinery bench I built with only hand tools improves on the dowel-and-glue one from 2021.", "fact", "personal", False,
     [("Japanese joinery bench", "tool"), ("hand tools", "tool"), ("dowel-and-glue", "method"), ("2021", "date")],
     [("Japanese joinery bench", "dowel-and-glue", "IMPROVES_ON")],
     "how is the new workbench a step up from the earlier one",
     "handcraft bench joinery leap earlier glued build comparison"),
    # --- 37 ---
    ("Keeps the tackle box sorted by target species; trout flies in the top tray, pike gear in the bottom.", "architecture", "personal", False,
     [("tackle box", "tool"), ("trout flies", "tool"), ("pike gear", "tool")],
     [],
     "how is my fishing kit organised inside the box",
     "angling storage layout species segmentation trays"),
    # --- 38 ---
    ("The Friday open-mic at The Camden Head builds on the bedroom guitar practice I started during 2020 lockdown.", "fact", "personal", False,
     [("open-mic", "event"), ("The Camden Head", "organization"), ("bedroom guitar practice", "activity"), ("2020 lockdown", "event")],
     [("open-mic", "bedroom guitar practice", "BUILDS_ON")],
     "how did the public performance night grow out of private practice",
     "pub stage origin private strumming pandemic start progression"),
    # --- 39 ---
    ("Lost the handmade leather wallet on the 5a bus to Kew Gardens on 2026-04-11; no luck at lost property.", "problem", "personal", False,
     [("handmade leather wallet", "tool"), ("5a bus", "activity"), ("Kew Gardens", "place"), ("2026-04-11", "date")],
     [],
     "what personal craft item went missing on the way to the botanic garden",
     "wallet loss crafted good transit botanic destination"),
    # --- 40 ---
    ("Prefers Strava segments for motivation over Garmin Connect's dashboards; the live leaderboard nudges me harder.", "preference", "personal", False,
     [("Strava", "service"), ("Garmin Connect", "service")],
     [("Strava", "Garmin Connect", "PREFERS")],
     "which tracking platform keeps me pushing in workouts",
     "segment leaderboard motivator dashboard alternative choice"),
    # --- 41 ---
    ("The community choir at St Mary's sings every other Wednesday; Ruth runs the soprano section.", "fact", "personal", False,
     [("community choir", "organization"), ("St Mary's", "place"), ("Wednesday", "date"), ("Ruth", "person")],
     [],
     "who leads my part at the fortnightly church-hall choir session",
     "neighbourhood singing group soprano lead biweekly"),
    # --- 42 ---
    ("The Milonga nights at Negracha improve on the beginner socials at Tango West; the floorcraft is cleaner.", "fact", "personal", False,
     [("Milonga nights", "event"), ("Negracha", "organization"), ("beginner socials", "event"), ("Tango West", "organization")],
     [("Milonga nights", "beginner socials", "IMPROVES_ON")],
     "how does the advanced tango venue compare with the learners' one",
     "experienced milonga floor advanced setting learner contrast"),
    # --- 43 ---
    ("Cancelled the Zwift subscription and rebuilt the pain cave with a dumb trainer and open-window cycling videos.", "decision", "personal", False,
     [("Zwift", "service"), ("pain cave", "place"), ("dumb trainer", "tool")],
     [("dumb trainer", "Zwift", "REPLACES")],
     "what replaced the indoor cycling app for winter sessions",
     "simple trainer shift subscription cancel basement training"),
    # --- 44 ---
    ("The Kew Gardens membership card is pinned to the fridge; the orchid house closes at 17:30 in spring.", "reference", "personal", False,
     [("Kew Gardens", "place"), ("fridge", "place"), ("orchid house", "place"), ("spring", "date")],
     [],
     "where is the botanic-garden pass kept and when does the flower house shut",
     "botanic pass location glasshouse closing springtime"),
    # --- 45 ---
    ("The comic collection outgrew the Ikea Billy; moving it all to oak shelves Dad built to spec.", "problem", "personal", False,
     [("comic collection", "hobby"), ("Ikea Billy", "tool"), ("oak shelves", "tool"), ("Dad", "person")],
     [("oak shelves", "Ikea Billy", "REPLACES")],
     "what shelving upgrade is the graphic-novel hoard forcing",
     "comics growth flatpack limit solid wood build upgrade"),
    # --- 46 ---
    ("Prefers the Muji 0.38 gel pens over Pilot G2 for bullet journaling; line weight is more consistent.", "preference", "personal", False,
     [("Muji 0.38 gel pens", "tool"), ("Pilot G2", "tool")],
     [("Muji 0.38 gel pens", "Pilot G2", "PREFERS")],
     "which pens took the journaling job over from the others",
     "fine gel ink Japanese option over American pen planner use"),
    # --- 47 ---
    ("The scale-model Spitfire, 1:24 Airfix, has been on the desk since 2026-01; canopy masking is next.", "fact", "personal", False,
     [("Spitfire", "tool"), ("Airfix", "organization"), ("2026-01", "date")],
     [],
     "how long has the large aircraft kit been on the workbench",
     "quarter-scale fighter kit desk duration glazing step"),
    # --- 48 ---
    ("The figure drawing group at Candid Arts on Mondays improves on the magazine pose-books I used at home.", "fact", "personal", False,
     [("figure drawing group", "organization"), ("Candid Arts", "organization"), ("Monday", "date"), ("magazine pose-books", "tool")],
     [("figure drawing group", "magazine pose-books", "IMPROVES_ON")],
     "how does the live model session beat the at-home reference books",
     "life drawing room over static book pose study contrast"),
    # --- 49 ---
    ("Swimming 2 km at London Fields Lido on Sunday mornings; the outdoor water wakes me up faster than espresso.", "architecture", "personal", False,
     [("London Fields Lido", "place"), ("Sunday", "date")],
     [],
     "what is the weekly open-water swim routine looking like",
     "lido weekend distance swim wake-up effect"),
    # --- 50 ---
    ("The tabletop RPG group at Orc's Nest meets every other Friday; Seb is running a Mothership campaign now.", "fact", "personal", False,
     [("tabletop RPG group", "organization"), ("Orc's Nest", "organization"), ("Friday", "date"), ("Seb", "person"), ("Mothership", "publication")],
     [],
     "who is currently running our fortnightly pen-and-paper game",
     "role-play session frequency current game master system"),
]


def _find_span(text: str, needle: str, used: list[tuple[int, int]]) -> tuple[int, int]:
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx < 0:
            raise ValueError(f"entity name {needle!r} not found in text {text!r}")
        end = idx + len(needle)
        overlap = any(not (end <= s or idx >= e) for s, e in used)
        if not overlap:
            return idx, end
        start = idx + 1


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, entry in enumerate(ENTRIES, start=1):
            text, mt, domain, noise, ents, rels, qq, qk = entry
            used: list[tuple[int, int]] = []
            entities = []
            for name, typ in ents:
                s, e = _find_span(text, name, used)
                used.append((s, e))
                entities.append({"name": name, "type": typ, "start": s, "end": e})
            row: dict = {
                "id": f"shared-{ID_OFFSET + i:05d}",
                "domain": domain,
                "text": text,
                "memory_type": mt,
                "noise": noise,
                "entities": entities,
                "relationships": [{"source": s, "target": t, "type": r} for s, t, r in rels],
            }
            if qq is not None and qk is not None:
                row["queries"] = [
                    {"form": "question", "text": qq},
                    {"form": "keyword", "text": qk},
                ]
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
