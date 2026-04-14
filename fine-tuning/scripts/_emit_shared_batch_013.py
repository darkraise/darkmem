"""One-off emitter for shared-base batch-013 — personal domain (family / household slice).

Writes to batch_013.tmp.jsonl for isolated parallel-writer safety.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_013.tmp.jsonl"
ID_OFFSET = 600

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("My sister Elena handles all the finances for our parents' house now; she took it over from Dad in 2025.", "decision", "personal", False,
     [("Elena", "person"), ("Dad", "person"), ("2025", "date")],
     [("Elena", "Dad", "REPLACES")],
     "who looks after the bills at the old family home these days",
     "household accounts transition sibling took charge year"),
    # --- 2 ---
    ("Grandpa Theo's old rocking chair sits by the window in the nursery; it creaks but Leo falls asleep in it fastest.", "fact", "personal", False,
     [("Theo", "person"), ("nursery", "place"), ("Leo", "person")],
     [],
     "which hand-me-down seat settles the baby the quickest at bedtime",
     "ancestor wooden seat infant sleep spot window corner"),
    # --- 3 ---
    ("Prefers splitting dinner cleanup with Noah over doing breakfast together; our evenings align better than mornings.", "preference", "personal", False,
     [("Noah", "person"), ("dinner cleanup", "activity"), ("breakfast", "activity")],
     [("dinner cleanup", "breakfast", "PREFERS")],
     "which shared kitchen duty fits our couple's rhythm best",
     "partner chores rhythm evening wash up versus morning meal"),
    # --- 4 ---
    ("My mother-in-law Colette brings kouign-amann every visit; we stash the extras in the freezer downstairs.", "architecture", "personal", False,
     [("Colette", "person"), ("kouign-amann", "food"), ("freezer", "tool")],
     [],
     "what Breton pastry habit has the in-law established at our place",
     "spouse parent visiting bake treat cold storage routine"),
    # --- 5 ---
    ("Aunt Priscilla moved into the granny flat behind our garage on 2026-02-14; she pays utilities and cooks Sundays.", "milestone", "personal", False,
     [("Priscilla", "person"), ("granny flat", "place"), ("2026-02-14", "date")],
     [("Priscilla", "granny flat", "LIVES_IN")],
     "when did the older relative move into the backyard annex",
     "extended family secondary unit move-in date arrangement"),
    # --- 6 ---
    ("Switched to letting Theo walk to school alone on 2026-03-04; he is nine and the route is three blocks.", "decision", "personal", False,
     [("Theo", "person"), ("2026-03-04", "date"), ("school", "place")],
     [("Theo", "school", "VISITED")],
     "when did the kid start walking to class on his own",
     "child independence morning commute short walk milestone"),
    # --- 7 ---
    ("Dad's hearing aids kept whistling during dinner; the audiologist refit them on 2026-01-19 and it stopped.", "problem", "personal", False,
     [("Dad", "person"), ("hearing aids", "tool"), ("audiologist", "organization"), ("2026-01-19", "date")],
     [],
     "what family-meal annoyance did a clinic visit fix",
     "assistive device feedback noise refitting appointment resolution"),
    # --- 8 ---
    ("Our cat Miso prefers my side of the bed once the lamp is off; Alex has stopped complaining about it.", "preference", "personal", False,
     [("Miso", "person"), ("Alex", "person")],
     [("Miso", "Alex", "PREFERS")],
     "which side of the bed does the cat claim after lights out",
     "feline bedtime spot partner acceptance lamp off choice"),
    # --- 9 ---
    ("Little cousin Mateo started calling me 'Tía Big' at the 2026 spring reunion and it stuck across the family.", "milestone", "personal", False,
     [("Mateo", "person"), ("2026 spring reunion", "event")],
     [],
     "how did I end up with a new family nickname this year",
     "small relative new name gathering event stuck family-wide"),
    # --- 10. noise ---
    ("Yeah, hang on — I need to grab a pen before you keep going.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("The family group chat on Signal replaced our old WhatsApp thread after my cousin's account got compromised.", "decision", "personal", False,
     [("Signal", "service"), ("WhatsApp", "service"), ("cousin", "person")],
     [("Signal", "WhatsApp", "REPLACES")],
     "why did the relatives move to a different messaging app",
     "messenger swap privacy incident relative account breach"),
    # --- 12 ---
    ("Uncle Reinhold's meatloaf recipe lives on a photocopied sheet tucked inside the 1982 Betty Crocker binder.", "reference", "personal", False,
     [("Reinhold", "person"), ("1982", "date"), ("Betty Crocker", "organization")],
     [],
     "where is the uncle's savoury loaf recipe actually filed",
     "older relative main dish formula cookbook insert decade"),
    # --- 13 ---
    ("Prefers quiet one-on-one walks with Dad to the big Thanksgiving crowd; we schedule a Wednesday morning loop.", "preference", "personal", False,
     [("quiet one-on-one walks", "activity"), ("Dad", "person"), ("big Thanksgiving crowd", "event"), ("Wednesday", "date")],
     [("quiet one-on-one walks", "big Thanksgiving crowd", "PREFERS")],
     "how do I actually spend meaningful time with my father at holidays",
     "midweek father stroll ritual over packed feast gathering"),
    # --- 14 ---
    ("Nibbles the hamster died on 2025-11-02 and the girls held a proper funeral by the rosebush.", "milestone", "personal", False,
     [("Nibbles", "person"), ("2025-11-02", "date"), ("rosebush", "place")],
     [],
     "when did the kids' small pet pass and where was it laid to rest",
     "rodent companion loss garden burial date children ceremony"),
    # --- 15 ---
    ("Our household chore rotation is pinned on the fridge in magnetic strips; it resets every Sunday at 7pm.", "architecture", "personal", False,
     [("fridge", "place"), ("magnetic strips", "tool"), ("Sunday", "date")],
     [],
     "how do we keep track of who does which task at home each week",
     "kitchen board duty schedule reset night family tasks"),
    # --- 16 ---
    ("My brother-in-law Arash pays the lawn service directly and we reimburse him quarterly for our share.", "fact", "personal", False,
     [("Arash", "person"), ("lawn service", "organization")],
     [],
     "how is the yard bill actually handled between the two households",
     "sibling spouse grass upkeep payment split reimbursement cadence"),
    # --- 17 ---
    ("Finally agreed with Maya that homework stays at the kitchen table, screens stay upstairs; it has been calmer since.", "decision", "personal", False,
     [("Maya", "person"), ("kitchen table", "place")],
     [],
     "what household rule did I settle on with the teenager about study and devices",
     "assignment location screen boundary household calm teen"),
    # --- 18 ---
    ("Grandma Ingrid and I argued over the 1997 Christmas photo; turns out the one she remembered is from 1995.", "problem", "personal", False,
     [("Ingrid", "person"), ("1997", "date"), ("1995", "date")],
     [],
     "which family photo year did we finally clear up between us",
     "elder relative memory mix-up winter snapshot date correction"),
    # --- 19 ---
    ("Prefers calling Mom on Sunday mornings to late-night texts; she actually picks up before church.", "preference", "personal", False,
     [("calling Mom on Sunday mornings", "activity"), ("late-night texts", "activity")],
     [("calling Mom on Sunday mornings", "late-night texts", "PREFERS")],
     "when does my mother actually answer and what format works",
     "weekend call slot elder parent availability worship routine"),
    # --- 20 ---
    ("Cousin Will's baby Iris was born 2026-02-28; we brought a hand-knit blanket from Grandma Ruth's leftover yarn.", "milestone", "personal", False,
     [("Will", "person"), ("Iris", "person"), ("2026-02-28", "date"), ("Ruth", "person")],
     [],
     "when did my cousin's newborn arrive and what heirloom gift did we bring",
     "relative's infant birth date knit present heritage supply"),
    # --- 21 ---
    ("The new shared Google Calendar improved on the paper wall calendar; the whole household finally sees each other's weeks.", "decision", "personal", False,
     [("Google Calendar", "service"), ("paper wall calendar", "tool")],
     [("Google Calendar", "paper wall calendar", "IMPROVES_ON")],
     "what upgrade actually got the family to sync schedules",
     "digital planner versus analog chart household visibility win"),
    # --- 22 ---
    ("My stepdad Ron builds birdhouses in the garage on Saturdays; the blue jays took one over last spring.", "fact", "personal", False,
     [("Ron", "person"), ("garage", "place"), ("blue jays", "person")],
     [],
     "what does the stepfather make in the garage on weekends",
     "non-biological father workshop craft bird home outcome"),
    # --- 23 ---
    ("The current weekend tradition of pancakes with the nieces builds on the waffle brunches we did before Clara was born.", "architecture", "personal", False,
     [("pancakes with the nieces", "activity"), ("waffle brunches", "activity"), ("Clara", "person")],
     [("pancakes with the nieces", "waffle brunches", "BUILDS_ON")],
     "how did the weekly breakfast ritual with the girls evolve over time",
     "breakfast flip cake versus iron grid history niece addition"),
    # --- 24 ---
    ("Sam and I split shared finances 60/40 because his income is higher; we rebalance every tax season.", "architecture", "personal", False,
     [("Sam", "person")],
     [],
     "how do the partner finances actually break down in our household",
     "couple cost share proportional income annual review"),
    # --- 25 ---
    ("Dog's evening walks were replaced by morning walks after Grandpa moved in; quieter streets suit his pace.", "decision", "personal", False,
     [("Grandpa", "person"), ("evening walks", "activity"), ("morning walks", "activity")],
     [("morning walks", "evening walks", "REPLACES")],
     "why did the canine routine shift after the relative arrived",
     "pet stroll time swap older person schedule street quiet"),
    # --- 26 ---
    ("Prefers hosting small Sunday lunches for six over big birthday parties; Oma Frieda is easier in small rooms.", "preference", "personal", False,
     [("small Sunday lunches for six", "activity"), ("big birthday parties", "event"), ("Oma Frieda", "person")],
     [("small Sunday lunches for six", "big birthday parties", "PREFERS")],
     "which hosting format suits my grandmother and me better",
     "intimate weekend meal versus large celebration elder comfort"),
    # --- 27 ---
    ("Found Great-Aunt Sabine's handwritten bread book in the pantry; it predates the family's move from Alsace in 1952.", "reference", "personal", False,
     [("Sabine", "person"), ("pantry", "place"), ("Alsace", "place"), ("1952", "date")],
     [],
     "what regional bread notebook surfaced and from whom",
     "great-aunt manuscript loaves pantry discovery regional origin year"),
    # --- 28 ---
    ("Jess and I stopped bickering about the thermostat after we agreed 19°C nights, 21°C mornings; set on the Nest.", "decision", "personal", False,
     [("Jess", "person"), ("Nest", "service")],
     [],
     "how did the household temperature argument finally get resolved",
     "partner climate dispute hvac schedule programmable rule"),
    # --- 29 ---
    ("Cousin Ade's engagement was announced at Sunday dinner on 2026-04-05; Auntie Pat cried into the gravy boat.", "milestone", "personal", False,
     [("Ade", "person"), ("2026-04-05", "date"), ("Pat", "person")],
     [],
     "when was the cousin's engagement revealed and how did the aunt react",
     "relative betrothal family meal announcement relative emotional response"),
    # --- 30 ---
    ("My nephew Felix refuses anything green unless it's wrapped in cheese; works for broccoli, fails on spinach.", "problem", "personal", False,
     [("Felix", "person"), ("broccoli", "food"), ("spinach", "food")],
     [],
     "what vegetable workaround works for my nephew and where does it fail",
     "kid greens aversion dairy wrap trick leafy exception"),
    # --- 31 ---
    ("We moved the family laundry hamper from the hallway to the upstairs landing; fewer piles on the stairs now.", "decision", "personal", False,
     [("laundry hamper", "tool"), ("hallway", "place"), ("upstairs landing", "place")],
     [("upstairs landing", "hallway", "REPLACES")],
     "what spatial change cut down on the clothes mess downstairs",
     "washing basket relocation household traffic flow improvement"),
    # --- 32 ---
    ("Grandma Ida only drinks her tea from the chipped blue mug; nobody else in the house touches it.", "fact", "personal", False,
     [("Ida", "person"), ("chipped blue mug", "tool")],
     [],
     "which specific cup does my grandmother insist on using",
     "elder relative favourite vessel house rule exclusive drinkware"),
    # --- 33 ---
    ("The every third weekend in-law visit rhythm replaced the drop-in chaos of last year; everyone prefers the structure now.", "architecture", "personal", False,
     [("every third weekend", "concept"), ("in-law visit", "activity"), ("drop-in chaos", "concept")],
     [("every third weekend", "drop-in chaos", "REPLACES")],
     "how did the spouse's parents' visits become predictable",
     "extended family drop-in cadence structure chaos cure"),
    # --- 34. noise ---
    ("Actually, scratch that — I meant the other one.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The kids' shared chore jar now builds on the old sticker chart; money instead of gold stars for ages 8 and up.", "decision", "personal", False,
     [("chore jar", "tool"), ("sticker chart", "tool")],
     [("chore jar", "sticker chart", "BUILDS_ON")],
     "how did the reward system for household tasks grow up with the kids",
     "cash incentive evolution childhood sticker token older graduation"),
    # --- 36 ---
    ("Neighbour Mrs. Okafor watches the dog when we visit Mom in Cleveland; she refuses payment, accepts baked goods.", "fact", "personal", False,
     [("Okafor", "person"), ("Mom", "person"), ("Cleveland", "place")],
     [("Mom", "Cleveland", "LIVES_IN")],
     "what is the arrangement with the neighbour during trips to my mother's city",
     "adjacent resident pet minding trip Ohio bake payment"),
    # --- 37 ---
    ("Younger brother Theodore called at 2am on 2026-04-06; his dog Whiskey had a seizure but pulled through.", "problem", "personal", False,
     [("Theodore", "person"), ("2026-04-06", "date"), ("Whiskey", "person")],
     [],
     "which late-night sibling call involved a pet emergency",
     "younger brother midnight phone call canine seizure recovery"),
    # --- 38 ---
    ("Prefers eating at the dining table with everyone over TV dinners on the couch; the kids linger longer.", "preference", "personal", False,
     [("eating at the dining table", "activity"), ("TV dinners on the couch", "activity")],
     [("eating at the dining table", "TV dinners on the couch", "PREFERS")],
     "which meal setup keeps the family together the longest",
     "formal seating versus living room eating linger duration"),
    # --- 39 ---
    ("Dad moved into our spare room after his hip surgery on 2026-01-08; the stay was meant for six weeks.", "milestone", "personal", False,
     [("Dad", "person"), ("spare room", "place"), ("2026-01-08", "date")],
     [("Dad", "spare room", "LIVES_IN")],
     "when did my father come to stay and for how long initially",
     "father recovery guest bedroom joint operation planned duration"),
    # --- 40 ---
    ("Our weekly family meeting improves on the old dinner-table ambush approach; everyone gets five minutes uninterrupted.", "decision", "personal", False,
     [("family meeting", "event"), ("dinner-table ambush approach", "concept")],
     [("family meeting", "dinner-table ambush approach", "IMPROVES_ON")],
     "how did the household conversations become less stressful",
     "structured regular discussion replaces ambush mealtime format"),
    # --- 41 ---
    ("Prefers my mother-in-law's quiche recipe over my own; she uses crème fraîche where I use heavy cream.", "preference", "personal", False,
     [("mother-in-law's quiche recipe", "food"), ("heavy cream", "food"), ("crème fraîche", "food")],
     [("mother-in-law's quiche recipe", "heavy cream", "PREFERS")],
     "whose savoury tart recipe actually wins in our kitchen",
     "spouse parent pie formula French cultured dairy twist"),
    # --- 42 ---
    ("My twin Marlene and I agreed to alternate hosting Hanukkah; even years her place, odd years mine, starting 2026.", "architecture", "personal", False,
     [("Marlene", "person"), ("Hanukkah", "event"), ("2026", "date")],
     [],
     "how did my twin and I split the winter holiday hosting",
     "twin sibling Jewish festival rotation host even odd year"),
    # --- 43 ---
    ("Grandpa Henri taught Leo to whistle through an acorn cap at the lake house on 2026-03-28; the kid practices daily.", "milestone", "personal", False,
     [("Henri", "person"), ("Leo", "person"), ("lake house", "place"), ("2026-03-28", "date")],
     [],
     "when did my child pick up a whistling trick from his grandfather",
     "elder teaches youngster nut shell tune water cottage date"),
    # --- 44 ---
    ("The shared household budget spreadsheet replaced our envelopes system; tracking subscriptions got way easier.", "decision", "personal", False,
     [("spreadsheet", "tool"), ("envelopes system", "concept")],
     [("spreadsheet", "envelopes system", "REPLACES")],
     "why did we ditch the cash envelopes at home",
     "digital money tracker over paper cash method subscription visibility"),
    # --- 45 ---
    ("Aunt Jolene's lasagne is strictly no-ricotta; she uses béchamel, and it builds on her Milanese grandmother's method.", "reference", "personal", False,
     [("Aunt Jolene's lasagne", "food"), ("béchamel", "food"), ("Milanese grandmother's method", "method")],
     [("Aunt Jolene's lasagne", "Milanese grandmother's method", "BUILDS_ON")],
     "what northern Italian technique shapes my aunt's pasta bake",
     "aunt baked pasta white sauce ancestral technique ricotta refusal"),
    # --- 46 ---
    ("Oldest daughter Fern asked to start locking her bedroom door on 2026-03-15; we talked through fire drills first.", "milestone", "personal", False,
     [("Fern", "person"), ("2026-03-15", "date")],
     [],
     "when did the eldest kid request a locked room and what did we discuss",
     "teen privacy bedroom access request safety conversation date"),
    # --- 47 ---
    ("Prefers handwritten birthday cards from the kids over store-bought ones; the crayon versions go on the fridge.", "preference", "personal", False,
     [("handwritten birthday cards", "activity"), ("store-bought ones", "activity"), ("fridge", "place")],
     [("handwritten birthday cards", "store-bought ones", "PREFERS")],
     "which kind of birthday card from the children wins the display spot",
     "homemade greeting kid drawing store printed appliance display"),
    # --- 48 ---
    ("We cannot agree on where to scatter Grandma Vera's ashes; the beach in Galway is losing to the rose garden.", "problem", "personal", False,
     [("Vera", "person"), ("Galway", "place"), ("rose garden", "place")],
     [],
     "which resting place for my grandmother's ashes is losing the family vote",
     "grandmother remains sibling disagreement Irish coast flower bed"),
    # --- 49 ---
    ("Our Sunday family video call with the Melbourne cousins starts at 8am here; three cameras, one shared slideshow.", "architecture", "personal", False,
     [("Melbourne", "place"), ("cousins", "person"), ("Sunday", "date")],
     [("cousins", "Melbourne", "LIVES_IN")],
     "how is the weekly video catch-up with the Australian relatives set up",
     "antipodean kin weekend call early hour multi-camera format"),
    # --- 50 ---
    ("Moved Dad's medication reminders from a paper list to the Medisafe app; fewer missed doses since 2026-02-01.", "decision", "personal", False,
     [("Dad", "person"), ("paper list", "tool"), ("Medisafe", "service"), ("2026-02-01", "date")],
     [("Medisafe", "paper list", "REPLACES")],
     "how did we cut down missed pills for my father this year",
     "elder parent drug schedule digital alert versus printed sheet date"),
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
    with OUT.open("a", encoding="utf-8") as f:
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
