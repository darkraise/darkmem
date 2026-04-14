"""One-off emitter for shared-base batch-008 — personal domain (round 2).

Same pattern as _emit_shared_batch_007.py; only ENTRIES changes.
Appends 50 rows to data/v2/shared/shared.jsonl with ids shared-00351..00400.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
ID_OFFSET = 350  # batches 001..007 consumed shared-00001..00350

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Started pottery class on Tuesday evenings at the Camden studio with Priya.", "milestone", "personal", False,
     [("pottery class", "hobby"), ("Tuesday", "date"), ("Camden studio", "place"), ("Priya", "person")],
     [],
     "when and where did the new ceramics hobby begin",
     "clay craft weekday workshop friend attend"),
    # --- 2 ---
    ("Picked sourdough over banana bread as my weekend baking focus; the fermentation rhythm fits weekends better.", "decision", "personal", False,
     [("sourdough", "food"), ("banana bread", "food")],
     [("sourdough", "banana bread", "REPLACES")],
     "which baking project took priority on the weekends this season",
     "fermented loaf versus quick bread weekend rotation"),
    # --- 3 ---
    ("Mom's tiramisu recipe is on the blue index card in the kitchen drawer, taped to the back.", "reference", "personal", False,
     [("tiramisu", "food")],
     [],
     "where does the family Italian dessert recipe actually live",
     "layered coffee dessert card drawer hidden"),
    # --- 4 ---
    ("The knee brace made a huge difference on long hikes; the Dolomites trip went without a flare-up afterwards.", "fact", "personal", False,
     [("knee brace", "tool"), ("Dolomites", "place")],
     [],
     "how did the support gear affect a long mountain trip",
     "joint support long trek alpine outcome gear"),
    # --- 5 ---
    ("Anniversary dinner is booked at Osteria Francescana for 2026-07-04; saved for six months to afford it.", "milestone", "personal", False,
     [("Osteria Francescana", "organization"), ("2026-07-04", "date")],
     [],
     "where is the big marriage celebration meal happening",
     "Modena restaurant reservation anniversary date saved"),
    # --- 6 ---
    ("Keeps a running gratitude list in a small Moleskine at bedside; three entries before lights out, always.", "architecture", "personal", False,
     [("gratitude list", "activity"), ("Moleskine", "tool")],
     [],
     "what evening notebook practice closes out my day",
     "three-item thankfulness journal nighttime routine"),
    # --- 7 ---
    ("Prefers early-morning coffee on the balcony over breakfast inside; the first-light silence is the draw.", "preference", "personal", False,
     [("early-morning coffee", "activity"), ("balcony", "place"), ("breakfast inside", "activity")],
     [("early-morning coffee", "breakfast inside", "PREFERS")],
     "which morning ritual do I actually look forward to most",
     "dawn outdoor caffeine outdoor quiet appeal"),
    # --- 8 ---
    ("Lost touch with Uncle Ben after the 2024 family reunion blow-up; waiting for him to reach out first.", "problem", "personal", False,
     [("Uncle Ben", "person"), ("2024 family reunion", "event")],
     [],
     "which older relative has gone silent since the family flare-up",
     "estranged uncle reunion fallout waiting game"),
    # --- 9 ---
    ("Dog's vet recommended a grain-free kibble after the last skin flare-up; switching over two weeks.", "decision", "personal", False,
     [("grain-free kibble", "food"), ("vet", "organization")],
     [],
     "what dietary switch did the canine specialist suggest",
     "hypoallergenic dog food skin reaction transition"),
    # --- 10. noise ---
    ("Let me think about that and circle back in a bit.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Mum will be 70 on 2028-05-12 and Rachel is organising a surprise weekend away with the cousins.", "milestone", "personal", False,
     [("Mum", "person"), ("2028-05-12", "date"), ("Rachel", "person")],
     [],
     "whose milestone birthday is being planned in secret and by whom",
     "septuagenarian matriarch surprise getaway organiser"),
    # --- 12 ---
    ("Switched my commute to the 07:15 bus from the underground; the daylight view beats the fluorescent tunnel.", "decision", "personal", False,
     [("07:15 bus", "activity"), ("underground", "place"), ("daylight view", "concept")],
     [("07:15 bus", "underground", "REPLACES")],
     "why did the morning commute route change this month",
     "surface transit over subway natural light reason"),
    # --- 13 ---
    ("Prefers rooibos to black tea in the afternoons; no caffeine so the 3 PM crash doesn't show up.", "preference", "personal", False,
     [("rooibos", "food"), ("black tea", "food")],
     [("rooibos", "black tea", "PREFERS")],
     "which afternoon drink wins against its caffeinated cousin",
     "herbal infusion over tannin caffeine-free afternoon"),
    # --- 14 ---
    ("Dad keeps the old Kodak slides from the 1970s in the attic trunk; we digitised the first box last summer.", "architecture", "personal", False,
     [("Kodak", "organization"), ("1970s", "date"), ("attic trunk", "place")],
     [],
     "where do the oldest family photo slides live and what stage of digitisation are they at",
     "mid-century slide archive storage digitisation progress"),
    # --- 15 ---
    ("The pilates instructor Nadia recommended a standing desk for my lower-back issue; bought one the next day.", "reference", "personal", False,
     [("Nadia", "person"), ("standing desk", "tool")],
     [],
     "whose advice prompted the ergonomic desk purchase",
     "fitness coach suggestion ergonomic workstation buy"),
    # --- 16 ---
    ("Garden tomatoes came in early this year; harvested the first basket on 2026-06-22, two weeks ahead.", "milestone", "personal", False,
     [("tomatoes", "food"), ("2026-06-22", "date")],
     [],
     "when did the backyard fruit crop arrive this season",
     "kitchen garden early harvest first basket date"),
    # --- 17 ---
    ("Jake's new apartment in Lisbon has the spare room ready; sketched a visit for September.", "fact", "personal", False,
     [("Jake", "person"), ("Lisbon", "place"), ("September", "date")],
     [("Jake", "Lisbon", "LIVES_IN")],
     "who has a guest room ready for me in the Iberian city",
     "friend Portuguese flat spare bed autumn trip"),
    # --- 18 ---
    ("The foster kitten we took in this spring replaced our plan to get a second adult cat.", "decision", "personal", False,
     [("foster kitten", "person"), ("second adult cat", "person"), ("spring", "date")],
     [("foster kitten", "second adult cat", "REPLACES")],
     "how did the household pet plans shift this season",
     "young feline intake older cat adoption plan swap"),
    # --- 19 ---
    ("Jess cancelled the Barcelona trip because her contract got extended; rebooked for late autumn.", "problem", "personal", False,
     [("Jess", "person"), ("Barcelona", "place")],
     [],
     "why did the Spanish trip with my friend get pushed back",
     "holiday postpone work extension reschedule season"),
    # --- 20 ---
    ("Prefers Audible for audiobooks over Storytel; the library size and narrators are noticeably better.", "preference", "personal", False,
     [("Audible", "service"), ("Storytel", "service")],
     [("Audible", "Storytel", "PREFERS")],
     "which audiobook service wins on selection and narration",
     "spoken book platform catalogue voice comparison"),
    # --- 21 ---
    ("Holiday gift tradition with Sam: one experience, one handmade, no shop-bought; started in 2021.", "architecture", "personal", False,
     [("Sam", "person"), ("2021", "date"), ("handmade", "concept")],
     [],
     "what gifting rules have we kept between us since a few years ago",
     "experience craft gift rule partner tradition origin"),
    # --- 22 ---
    ("Fell off the meditation streak at day 143 after a rough week; restarted the count the following Monday.", "problem", "personal", False,
     [("meditation streak", "activity"), ("Monday", "date")],
     [],
     "why did the mindfulness habit reset and when did it pick back up",
     "mindfulness habit chain break restart day count"),
    # --- 23 ---
    ("Saved the Nigella chocolate olive oil cake recipe to the shared Notion; it is Jamie's go-to birthday bake.", "reference", "personal", False,
     [("Nigella", "person"), ("Notion", "tool"), ("Jamie", "person")],
     [],
     "where is the go-to celebratory cake recipe stored for quick access",
     "celebrity chef chocolate cake shared app location"),
    # --- 24 ---
    ("Helped Mum move into the Lisbon assisted-living flat on 2025-10-12; she settled in faster than expected.", "milestone", "personal", False,
     [("Mum", "person"), ("Lisbon", "place"), ("2025-10-12", "date")],
     [("Mum", "Lisbon", "LIVES_IN")],
     "when did my mother transition into supported housing",
     "elder relative relocation care flat settling date"),
    # --- 25 ---
    ("Prefers quiet Saturdays at home to long brunches; three hours of reading beats an hour of small talk.", "preference", "personal", False,
     [("quiet Saturdays", "activity"), ("long brunches", "activity")],
     [("quiet Saturdays", "long brunches", "PREFERS")],
     "which weekend rhythm do I actually enjoy more",
     "home day reading versus social brunch preference"),
    # --- 26 ---
    ("The Wednesday yoga class was replaced by pilates after the studio renovation; same teacher, different room.", "decision", "personal", False,
     [("Wednesday yoga class", "hobby"), ("pilates", "hobby")],
     [("pilates", "Wednesday yoga class", "REPLACES")],
     "which midweek studio class took over after the remodel",
     "midweek class swap studio renovation teacher continuity"),
    # --- 27 ---
    ("Joined the Friday night chess club at the community centre; finally applied my childhood King's Indian defence.", "milestone", "personal", False,
     [("chess club", "organization"), ("community centre", "place"), ("King's Indian defence", "concept")],
     [],
     "which weekly gathering did I sign up for at the local venue",
     "end-of-week board game group childhood opening return"),
    # --- 28 ---
    ("Rufus turned 5 on 2026-03-11 and took it very seriously; photos with a small cardboard crown.", "milestone", "personal", False,
     [("Rufus", "person"), ("2026-03-11", "date")],
     [],
     "when did the dog's small birthday milestone land and how did it look",
     "pet half-decade birthday photo props date"),
    # --- 29 ---
    ("The grandfather clock in the hallway came from Aunt Rosa's estate; keeps time to within a minute a week.", "fact", "personal", False,
     [("grandfather clock", "tool"), ("Aunt Rosa", "person")],
     [],
     "what heirloom timepiece lives in the hallway and from whom",
     "inherited hallway chime relative estate accuracy"),
    # --- 30 ---
    ("Dropped the personal newsletter after issue 24; the audience stalled and so did the motivation.", "problem", "personal", False,
     [("personal newsletter", "project")],
     [],
     "why did my email newsletter run out of steam",
     "writing project halt stagnant readership motivation drop"),
    # --- 31 ---
    ("Started tracking running pace on a paper log beside the treadmill; the phone app kept mis-logging indoor runs.", "decision", "personal", False,
     [("paper log", "tool"), ("treadmill", "tool"), ("phone app", "tool")],
     [("paper log", "phone app", "REPLACES")],
     "what replaced the app for logging indoor run speeds",
     "treadmill pace analogue record swap indoor tracking"),
    # --- 32 ---
    ("The pediatric dentist Dr. Singh scheduled Maya's braces consultation for 2026-05-07 after the X-rays.", "fact", "personal", False,
     [("Dr. Singh", "person"), ("Maya", "person"), ("2026-05-07", "date")],
     [],
     "when is the orthodontic follow-up booked for my kid",
     "braces consultation pediatric dentist appointment date"),
    # --- 33 ---
    ("Finally read the letters from Grandpa that Dad saved; they cover his Navy years between 1953 and 1957.", "reference", "personal", False,
     [("Grandpa", "person"), ("Dad", "person"), ("Navy", "organization"), ("1953", "date"), ("1957", "date")],
     [],
     "whose saved wartime letters did I finally sit with",
     "family letters servicemember midcentury years archive"),
    # --- 34. noise ---
    ("Hold on, let me pull up the right page first.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The kids prefer board games to video games on family nights; Catan gets three plays a month.", "preference", "personal", False,
     [("board games", "hobby"), ("video games", "hobby"), ("Catan", "hobby")],
     [("board games", "video games", "PREFERS")],
     "which play style wins on the weekly family gathering night",
     "tabletop sessions over screen gaming monthly count"),
    # --- 36 ---
    ("Hip MRI on 2026-04-03 showed mild labral wear; the orthopedist said no surgery, focus on strength work.", "milestone", "personal", False,
     [("2026-04-03", "date")],
     [],
     "what did the imaging appointment reveal about the joint",
     "scan finding orthopedic plan conservative path"),
    # --- 37 ---
    ("Jamie's side of the family does Easter lunch at noon; my side does it in the evening. We alternate years.", "architecture", "personal", False,
     [("Jamie", "person"), ("Easter", "event")],
     [],
     "how do the two sides of the family split the spring holiday meal",
     "alternate year spring meal midday evening split"),
    # --- 38 ---
    ("The Lisbon flat rental for the autumn trip costs a third of Barcelona's; booking it tomorrow.", "decision", "personal", False,
     [("Lisbon", "place"), ("Barcelona", "place")],
     [("Lisbon", "Barcelona", "PREFERS")],
     "which city ends up being the autumn holiday destination and why",
     "Iberian stay cost driver lodging choice fall"),
    # --- 39 ---
    ("Neighbour Clara left a basket of quinces last Sunday; the membrillo made from them turned out well.", "fact", "personal", False,
     [("Clara", "person"), ("quinces", "food"), ("membrillo", "food")],
     [],
     "what seasonal gift from the neighbour turned into a paste project",
     "fruit basket neighbour Spanish paste kitchen outcome"),
    # --- 40 ---
    ("Reached my 1000th logged kilometre on 2026-04-09; celebrated with an easy five down by the river.", "milestone", "personal", False,
     [("2026-04-09", "date"), ("river", "place")],
     [],
     "when did I hit the thousand-kilometre running total for the year",
     "distance milestone runner log easy celebratory run"),
    # --- 41 ---
    ("Sam prefers I handle the airport drop-offs; he handles the pickups because the late arrivals stress him less.", "preference", "personal", False,
     [("Sam", "person")],
     [],
     "how do we split the travel driving duties between us",
     "partner chauffeur split arrival departure stress trade"),
    # --- 42 ---
    ("The Christmas tree stays up until Epiphany; the kids decorate, the adults light it, and no one dismantles alone.", "architecture", "personal", False,
     [("Christmas tree", "event"), ("Epiphany", "event")],
     [],
     "what household rules govern the winter decoration schedule",
     "tree duration role split winter decorations household"),
    # --- 43 ---
    ("Stopped buying fast fashion two years ago; all new clothes now come from local vintage or second-hand.", "decision", "personal", False,
     [("fast fashion", "activity"), ("second-hand", "activity")],
     [("second-hand", "fast fashion", "REPLACES")],
     "what is my clothing-buying rule these days and when did it start",
     "ethical wardrobe thrift vintage rule cutover"),
    # --- 44 ---
    ("Nightly pepper-grinder pain traced to arthritis in my right thumb; the physio prescribed grip exercises.", "problem", "personal", False,
     [("arthritis", "concept"), ("right thumb", "concept"), ("physio", "organization")],
     [],
     "what kitchen tool discomfort led to a physiotherapy prescription",
     "grinder joint ache finger rehab plan routine"),
    # --- 45 ---
    ("Took Ben to see the Van Gogh exhibit in Amsterdam on 2025-09-18; he is still talking about the Wheatfield with Crows.", "reference", "personal", False,
     [("Ben", "person"), ("Van Gogh", "person"), ("Amsterdam", "place"), ("2025-09-18", "date")],
     [],
     "which art outing still lives rent-free in my friend's head",
     "post-Impressionist show Dutch capital friend visit"),
    # --- 46 ---
    ("The tea cupboard got a full reorganisation last weekend; all loose leaf now lives in labelled steel tins.", "architecture", "personal", False,
     [("tea cupboard", "place"), ("steel tins", "tool")],
     [],
     "how did the kitchen storage for loose leaf end up after the redo",
     "pantry overhaul container swap labelling loose leaf"),
    # --- 47 ---
    ("The Tokyo language exchange on Fridays moved online after Yuki relocated to Sapporo; still fun, less spontaneous.", "problem", "personal", False,
     [("Tokyo", "place"), ("Yuki", "person"), ("Sapporo", "place")],
     [("Yuki", "Sapporo", "LIVES_IN")],
     "why did the Friday language meetup lose its in-person energy",
     "language swap online shift relocation spontaneity loss"),
    # --- 48 ---
    ("Prefers hand-written thank-you cards over texts for real gifts; takes ten minutes, means a lot more.", "preference", "personal", False,
     [("hand-written thank-you cards", "activity"), ("texts", "activity")],
     [("hand-written thank-you cards", "texts", "PREFERS")],
     "which gratitude format wins when a real present arrives",
     "handwritten note over SMS present acknowledgement"),
    # --- 49 ---
    ("Mum's carrot cake is still the standard for my birthday; no substitutes accepted, even from bakeries.", "fact", "personal", False,
     [("carrot cake", "food"), ("Mum", "person")],
     [],
     "whose baking remains the birthday standard around here",
     "mother signature dessert birthday rule baker source"),
    # --- 50 ---
    ("Cancelled the gym membership and moved to outdoor workouts in the park; saved 40 pounds and gained views.", "decision", "personal", False,
     [("gym membership", "activity"), ("outdoor workouts", "activity"), ("park", "place")],
     [("outdoor workouts", "gym membership", "REPLACES")],
     "what replaced my paid indoor training and what were the two wins",
     "outdoor session shift subscription cancel nature gain"),
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
