"""One-off emitter for shared-base batch-134 — personal domain (hosting and entertaining at home as the host slice).

Writes 50 rows to data/v2/shared/batch_134.tmp.jsonl with ids shared-06651..06700.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_134.tmp.jsonl"
ID_OFFSET = 6650

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The standing dinner-party seating plan at 14 Pennant Mews puts Priya at my right and Dev across from Osman so the architecture talk never stalls.", "architecture", "personal", False,
     [("14 Pennant Mews", "place"), ("Priya", "person"), ("Dev", "person"), ("Osman", "person"), ("architecture talk", "concept")],
     [("Priya", "14 Pennant Mews", "LOCATED_IN")],
     "how do I lay out the table for the regular dinner at mine",
     "dinner party seating plan regulars architecture conversation anchor"),
    # --- 2 ---
    ("Launched the Thursday supper club on 2026-02-05 with a Sichuan night; four courses, eight seats, bring-your-own wine, £18 towards ingredients.", "milestone", "personal", False,
     [("Thursday supper club", "event"), ("2026-02-05", "date"), ("Sichuan", "concept"), ("wine", "food")],
     [],
     "when did the themed dinner-series kick off at mine and what was the format",
     "supper club launch themed night seat count BYO wine cost share"),
    # --- 3 ---
    ("The game-night cupboard in the lounge holds Codenames, Wingspan, Azul and a Catan spare set; pulled Monopoly after a Dev-versus-Osman row in 2025-11.", "architecture", "personal", False,
     [("game-night", "event"), ("lounge", "place"), ("Codenames", "concept"), ("Wingspan", "concept"), ("Azul", "concept"), ("Catan", "concept"), ("Monopoly", "concept"), ("2025-11", "date")],
     [("Monopoly", "game-night", "RELATED_TO")],
     "what board games live in the lounge for game night and which got cut",
     "game night cupboard board games inventory monopoly removed row"),
    # --- 4 ---
    ("Prefers the kitchen island for cocktail parties over the dining-room sideboard; the island gives three sides of access and guests mix their own.", "preference", "personal", False,
     [("kitchen island", "place"), ("cocktail parties", "event"), ("dining-room sideboard", "place"), ("guests", "person")],
     [("kitchen island", "dining-room sideboard", "PREFERS")],
     "which bar setup wins at mine and why the kitchen wins over the dining room",
     "cocktail party bar kitchen island over sideboard three side access"),
    # --- 5 ---
    ("Replaced the laminated menu cards with hand-written ones on folded kraft stock starting 2026-03-10; the laminated ones always read as corporate.", "decision", "personal", False,
     [("laminated menu cards", "tool"), ("kraft stock", "tool"), ("2026-03-10", "date")],
     [("kraft stock", "laminated menu cards", "REPLACES")],
     "which menu-card style took over at the table and what drove the switch",
     "menu card swap handwritten kraft over laminate corporate feel date"),
    # --- 6 ---
    ("The kids' birthday party for Anya on 2026-05-16 is planned as a garden pirate theme; ten four-year-olds, 14:00 to 16:30, treasure dig in the raised bed.", "milestone", "personal", False,
     [("Anya", "person"), ("2026-05-16", "date"), ("garden", "place"), ("pirate theme", "concept"), ("raised bed", "place")],
     [],
     "when is the kid birthday party I am running and how is it themed",
     "kids birthday pirate garden theme headcount time window treasure dig"),
    # --- 7 ---
    ("Read Priya Parker's The Art of Gathering over 2025-12 and pulled three rules into my hosting: name the purpose, close the door, honour the guests.", "milestone", "personal", False,
     [("Priya Parker", "person"), ("The Art of Gathering", "publication"), ("2025-12", "date"), ("hosting", "activity")],
     [("The Art of Gathering", "hosting", "RELATED_TO")],
     "which hosting book reshaped how I run evenings and what stuck",
     "art of gathering priya parker rules purpose door guests hosting"),
    # --- 8 ---
    ("The overnight-guest kit for the spare room at 14 Pennant Mews: fresh towels, USB-C charger, two pillows firm and soft, a carafe on the bedside.", "architecture", "personal", False,
     [("overnight-guest kit", "tool"), ("spare room", "place"), ("14 Pennant Mews", "place"), ("USB-C charger", "tool"), ("carafe", "tool")],
     [("spare room", "14 Pennant Mews", "LOCATED_IN")],
     "what do I set up in the guest room before someone stays the night",
     "guest room prep kit towel charger pillow hard soft water carafe"),
    # --- 9 ---
    ("The Airbnb turnover at the loft runs 11:00 to 15:00: strip beds, run the dishwasher, wipe the hob, restock the welcome basket with oat milk and shortbread.", "architecture", "personal", False,
     [("Airbnb", "organization"), ("loft", "place"), ("dishwasher", "tool"), ("welcome basket", "tool"), ("oat milk", "food"), ("shortbread", "food")],
     [("welcome basket", "loft", "LOCATED_IN")],
     "how do I flip the short-let between guests and what is in the welcome basket",
     "airbnb turnover routine strip dishwasher hob welcome oat shortbread"),
    # --- 10. noise ---
    ("Let me chill the glasses first before we pour.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Ran the house-warming at 14 Pennant Mews on 2026-01-24; 32 people across the afternoon, a single rota door-person so the flow never bunched.", "milestone", "personal", False,
     [("house-warming", "event"), ("14 Pennant Mews", "place"), ("2026-01-24", "date"), ("door-person", "person")],
     [("house-warming", "14 Pennant Mews", "LOCATED_IN")],
     "when did I throw the housewarming at the new flat and how did the door work",
     "house warming date guest count door person flow management rota"),
    # --- 12 ---
    ("Hosting the book club rotation lands at mine every third month; chose the sofa-facing-fireplace layout over the round-table because Marianne reads aloud better standing.", "architecture", "personal", False,
     [("book club", "event"), ("sofa", "place"), ("fireplace", "place"), ("round-table", "place"), ("Marianne", "person")],
     [("sofa", "round-table", "PREFERS")],
     "how does the book-club layout at mine work and why the sofa set-up wins",
     "book club host rotation sofa fireplace over round table read aloud"),
    # --- 13 ---
    ("The run-club breakfast after the Sunday long run has been at mine since 2026-01-11; eggs and flat whites for seven, pre-prepped frittata saves the kitchen.", "fact", "personal", False,
     [("run-club", "organization"), ("Sunday", "date"), ("2026-01-11", "date"), ("eggs", "food"), ("flat whites", "food"), ("frittata", "food")],
     [("run-club", "Sunday", "RELATED_TO")],
     "when did the post-run breakfast move to mine and what do I actually cook",
     "run club breakfast sunday long run eggs flat white frittata prep"),
    # --- 14 ---
    ("Stocking the home bar: Tanqueray, Havana 7, a rye, Noilly Prat, Aperol, Campari, lemons, limes, good tonic, salt rimmer; no cheap vermouth ever.", "reference", "personal", False,
     [("Tanqueray", "food"), ("Havana 7", "food"), ("rye", "food"), ("Noilly Prat", "food"), ("Aperol", "food"), ("Campari", "food"), ("tonic", "food")],
     [],
     "what lives on the home bar for cocktail hosting and what is the one ban",
     "home bar stock gin rum rye vermouth aperol campari tonic no cheap"),
    # --- 15 ---
    ("Prefers hosting the in-laws in the guest room over the sofa bed; the guest room has blackout blinds and Pat wakes with any streetlight through the curtain.", "preference", "personal", False,
     [("in-laws", "person"), ("guest room", "place"), ("sofa bed", "place"), ("blackout blinds", "tool"), ("Pat", "person")],
     [("guest room", "sofa bed", "PREFERS")],
     "where do the in-laws sleep when they visit and why that over the sofa bed",
     "in law stay guest room over sofa bed blackout blinds pat streetlight"),
    # --- 16 ---
    ("The menu-planning workflow for dinners lands on Wednesdays for a Saturday party: one make-ahead main, one room-temperature side, one dessert that sits happily.", "architecture", "personal", False,
     [("menu-planning", "activity"), ("Wednesdays", "date"), ("Saturday", "date"), ("make-ahead main", "food"), ("dessert", "food")],
     [],
     "how do I plan a dinner-party menu in the week leading up",
     "menu planning wednesday saturday dinner make ahead room temp dessert"),
    # --- 17 ---
    ("Chose the smaller Globe-Williams round table for six over the long rectangular one for dinner parties; eye contact across six beats shouting across ten.", "decision", "personal", False,
     [("Globe-Williams", "organization"), ("round table", "tool"), ("rectangular", "tool"), ("dinner parties", "event")],
     [("round table", "rectangular", "PREFERS")],
     "which dining table wins for the regular suppers and what is the reasoning",
     "round table over rectangle dinner party eye contact six over ten"),
    # --- 18 ---
    ("International visitor prep for Osman's cousins arriving 2026-04-22: airport pickup sign ready, SIM card on the fridge, tube map annotated for their hotel route.", "reference", "personal", False,
     [("Osman", "person"), ("2026-04-22", "date"), ("SIM card", "tool"), ("fridge", "place"), ("tube map", "tool"), ("hotel", "place")],
     [],
     "what do I set up before international guests land and where do things live",
     "international guest prep airport sim fridge tube map hotel route"),
    # --- 19 ---
    ("The housekeeping-before-company checklist takes 75 minutes: hoover living room, bathroom deep wipe, candles lit 20 minutes before, coat rack cleared.", "architecture", "personal", False,
     [("housekeeping-before-company", "activity"), ("living room", "place"), ("bathroom", "place"), ("candles", "tool"), ("coat rack", "tool")],
     [],
     "how long does the pre-guests cleanup take and what is in it",
     "pre company clean hoover bathroom candles coat rack time budget"),
    # --- 20 ---
    ("Ran the cocktail party on 2026-02-14 with a Negroni station and a Paloma station; the two-cocktail rule kept the bar legible and the washing-up fast.", "decision", "personal", False,
     [("cocktail party", "event"), ("2026-02-14", "date"), ("Negroni", "food"), ("Paloma", "food")],
     [],
     "how did the last cocktail party run and why the two-drink limit",
     "cocktail party negroni paloma two drink rule bar legible wash up"),
    # --- 21 ---
    ("Prefers the back-garden barbecue setup at Pennant Mews over the front-drive one; back garden has the gas line and no neighbours watching the sear.", "preference", "personal", False,
     [("back-garden", "place"), ("barbecue", "event"), ("Pennant Mews", "place"), ("front-drive", "place"), ("gas line", "infrastructure")],
     [("back-garden", "front-drive", "PREFERS")],
     "which garden spot wins for the grill and what makes the difference",
     "barbecue back garden over front drive gas line neighbour privacy"),
    # --- 22 ---
    ("The themed supper club calendar for 2026 is Sichuan in February, Levantine in April, Lisbon in June, Hokkaido in October; slots fill the Monday they drop.", "architecture", "personal", False,
     [("supper club", "event"), ("2026", "date"), ("Sichuan", "concept"), ("Levantine", "concept"), ("Lisbon", "concept"), ("Hokkaido", "concept"), ("Monday", "date")],
     [],
     "what is the themed-dinner calendar for the year and how fast do seats go",
     "supper club calendar sichuan levantine lisbon hokkaido monday release"),
    # --- 23 ---
    ("Replaced the Spotify hosting playlist with three hand-curated 90-minute sets on 2026-03-18; algorithmic picks kept pushing sad songs into the apéritif.", "decision", "personal", False,
     [("Spotify", "organization"), ("hosting playlist", "tool"), ("2026-03-18", "date"), ("apéritif", "event"), ("hand-curated 90-minute sets", "tool")],
     [("hand-curated 90-minute sets", "Spotify", "REPLACES")],
     "which music rotation took over for parties and why the algorithm got dropped",
     "hosting playlist swap curated sets over spotify sad song aperitif"),
    # --- 24 ---
    ("The guest-room rituals on arrival: door open, lamp on, folded note with wifi and the fridge-snack rule, a fresh flower from the garden if the season allows.", "architecture", "personal", False,
     [("guest-room", "place"), ("lamp", "tool"), ("wifi", "tool"), ("fridge-snack rule", "concept"), ("flower", "concept")],
     [],
     "what ritual do I run when a guest first walks into the spare room",
     "guest room arrival lamp note wifi fridge snack rule flower seasonal"),
    # --- 25 ---
    ("Hosting the kids' birthday in the garden means the downstairs loo gets a kiddie step and a pile of flannels; Anya's friends forget the towel every time.", "fact", "personal", False,
     [("kids' birthday", "event"), ("garden", "place"), ("downstairs loo", "place"), ("kiddie step", "tool"), ("flannels", "tool"), ("Anya", "person")],
     [],
     "what loo prep do I do for a garden kid party and why",
     "kid birthday downstairs loo step flannels hand towel forget prep"),
    # --- 26 ---
    ("The Airbnb review streak sat at 4.93 across 2025; lost points only on parking which is a street-permit issue, not fixable on my side.", "fact", "personal", False,
     [("Airbnb", "organization"), ("2025", "date"), ("street-permit", "concept"), ("parking", "concept")],
     [],
     "how did the short-let ratings do last year and where did points leak",
     "airbnb review average year parking permit unfixable on side score"),
    # --- 27 ---
    ("Prefers doing the supper-club washing-up during dessert over leaving it to the end; the kitchen resets so the kettle round feels like a fresh room.", "preference", "personal", False,
     [("supper-club", "event"), ("washing-up", "activity"), ("dessert", "food"), ("kitchen", "place"), ("kettle round", "event")],
     [("washing-up", "kitchen", "RELATED_TO")],
     "when do I tackle the dishes during supper and why that timing",
     "dish timing mid meal reset kettle service flow tradeoff"),
    # --- 28 ---
    ("Marianne and Raul are the anchor guests for any new dinner; invite one stranger per table knowing they will carry any awkward silence at course two.", "reference", "personal", False,
     [("Marianne", "person"), ("Raul", "person"), ("dinner", "event"), ("stranger", "person"), ("course two", "concept")],
     [("Marianne", "dinner", "RELATED_TO"), ("Raul", "dinner", "RELATED_TO")],
     "which friends anchor a new dinner invite and what role do they play",
     "anchor guest marianne raul stranger carry silence course two"),
    # --- 29 ---
    ("The overnight-guest rota for 2026 has Pat and Liam across 04-10 to 04-14, Osman's cousins 04-22 to 04-26, Dev's sister over 05-03 to 05-05.", "architecture", "personal", False,
     [("overnight-guest rota", "tool"), ("2026", "date"), ("Pat", "person"), ("Liam", "person"), ("Osman", "person"), ("Dev", "person")],
     [],
     "who is staying over at mine this spring and when are the slots",
     "overnight guest rota spring pat liam osman cousins dev sister dates"),
    # --- 30 ---
    ("Feels proud that the first dinner at 14 Pennant Mews with Osman, Priya, Dev, Marianne and Raul on 2026-02-28 ended at 01:40 with the washing-up undone.", "milestone", "personal", False,
     [("14 Pennant Mews", "place"), ("Osman", "person"), ("Priya", "person"), ("Dev", "person"), ("Marianne", "person"), ("Raul", "person"), ("2026-02-28", "date")],
     [],
     "how did I feel about the first dinner with all the regulars at the new flat",
     "pride first dinner new flat regulars late finish washing up undone"),
    # --- 31 ---
    ("Replaced the sit-down birthday lunch for adults with a rolling afternoon on 2026-03-22; people came and went, nobody missed the speeches.", "decision", "personal", False,
     [("sit-down birthday lunch", "event"), ("rolling afternoon", "event"), ("2026-03-22", "date"), ("speeches", "concept")],
     [("rolling afternoon", "sit-down birthday lunch", "REPLACES")],
     "which adult-birthday format took over from the sit-down one and what did it drop",
     "adult birthday rolling afternoon over sit down lunch speeches drop"),
    # --- 32 ---
    ("The cheese-course rule at Pennant Mews: three cheeses, one soft, one hard, one blue, two crackers not five, a single honey and a single chutney.", "reference", "personal", False,
     [("cheese-course", "food"), ("Pennant Mews", "place"), ("crackers", "food"), ("honey", "food"), ("chutney", "food")],
     [("cheese-course", "Pennant Mews", "LOCATED_IN")],
     "what is the cheese-board rule at mine and the hidden restraint",
     "cheese course three cheese two cracker one honey chutney rule"),
    # --- 33 ---
    ("Hosting the run-club Christmas party on 2025-12-20 peaked at 23 people in the kitchen; next year the lounge gets the mulled wine station to spread the heat.", "problem", "personal", False,
     [("run-club", "organization"), ("Christmas party", "event"), ("2025-12-20", "date"), ("kitchen", "place"), ("lounge", "place"), ("mulled wine station", "tool")],
     [],
     "what bottlenecked at last year's run-club holiday party and how is it getting fixed",
     "run club christmas peak kitchen bottleneck lounge mulled wine move"),
    # --- 34. noise ---
    ("Let me top up the jug before anyone notices.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Chose beeswax candles over paraffin for dinners from 2026-01 onwards; the paraffin smell lingered in the curtains for a day after each party.", "decision", "personal", False,
     [("beeswax candles", "tool"), ("paraffin", "tool"), ("2026-01", "date"), ("curtains", "tool")],
     [("beeswax candles", "paraffin", "REPLACES")],
     "which candle wax took over at the table and what nudged the swap",
     "beeswax over paraffin dinner candle curtain smell linger reason"),
    # --- 36 ---
    ("The game-night house rules: no phones on the table, the host keeps score, losers do the next round of drinks, no post-midnight Catan.", "reference", "personal", False,
     [("game-night", "event"), ("host", "person"), ("Catan", "concept")],
     [],
     "what are the ground rules at game night here",
     "game night rules no phone host score drinks penalty no late catan"),
    # --- 37 ---
    ("Prefers Raul's ribs recipe to my own for the garden barbecue; his dry rub uses coffee grounds and the bark holds through a three-hour rest.", "preference", "personal", False,
     [("Raul", "person"), ("ribs recipe", "food"), ("garden barbecue", "event"), ("coffee grounds", "food"), ("bark", "concept")],
     [("Raul", "ribs recipe", "RELATED_TO")],
     "whose rib recipe wins for the garden grill and what makes it",
     "raul ribs over mine barbecue coffee rub bark rest three hour"),
    # --- 38 ---
    ("The cocktail party headcount cap for the flat is 18; beyond that the coat situation collapses and the hall becomes a jam at the 21:00 arrival wave.", "reference", "personal", False,
     [("cocktail party", "event"), ("flat", "place"), ("coat situation", "concept"), ("hall", "place")],
     [],
     "what is the hard guest cap for cocktails at mine and why that number",
     "cocktail headcount cap flat coat hall jam nine pm arrival wave"),
    # --- 39 ---
    ("Hosted the book club on 2026-04-02 for Tokarczuk's Flights; eight readers, three bottles of riesling, a single slow-cooked lamb shoulder.", "milestone", "personal", False,
     [("book club", "event"), ("2026-04-02", "date"), ("Tokarczuk", "person"), ("Flights", "publication"), ("riesling", "food"), ("lamb shoulder", "food")],
     [],
     "when did I last host book club and what did we read and eat",
     "book club host date tokarczuk flights riesling lamb shoulder"),
    # --- 40 ---
    ("Feels anxious the morning of any dinner with more than six guests; the fix is the 60-minute shower-music-apron loop that starts at T-minus three hours.", "problem", "personal", False,
     [("dinner", "event"), ("shower-music-apron loop", "activity")],
     [],
     "what do I feel on dinner-party mornings and what routine breaks it",
     "hosting anxiety dinner morning shower music apron loop three hour"),
    # --- 41 ---
    ("The Airbnb welcome note template lives in Notion under hosting/loft/welcome; tweaked the sign-off for Dutch guests after a 2025-09 review about formality.", "reference", "personal", False,
     [("Airbnb", "organization"), ("Notion", "organization"), ("loft", "place"), ("Dutch guests", "person"), ("2025-09", "date"), ("welcome note template", "tool")],
     [("welcome note template", "Notion", "LOCATED_IN")],
     "where is the short-let welcome note stored and what got tweaked for the Dutch",
     "airbnb welcome note notion loft dutch guest formality sign off fix"),
    # --- 42 ---
    ("Replaced the garden fairy lights with wired festoon on 2026-03-30 after the battery set died mid-dinner twice last year; wired into the shed outlet.", "decision", "personal", False,
     [("fairy lights", "tool"), ("festoon", "tool"), ("2026-03-30", "date"), ("shed outlet", "infrastructure"), ("garden", "place")],
     [("festoon", "fairy lights", "REPLACES")],
     "which garden lighting took over and what pushed the swap",
     "festoon over fairy lights garden wired shed outlet battery fail"),
    # --- 43 ---
    ("Prefers hosting brunch to dinner for new friendships; lower stakes, no booze pressure, and the morning version of me is the better host.", "preference", "personal", False,
     [("brunch", "event"), ("dinner", "event"), ("friendships", "concept")],
     [("brunch", "dinner", "PREFERS")],
     "which meal slot wins when I'm meeting newer people and why",
     "brunch over dinner new friendship low stake no booze morning self"),
    # --- 44 ---
    ("The dishwasher on the cocktail-party night gets loaded glasses-first, plates in the second run; this protects the Schott Zwiesel stems from the plate weight.", "architecture", "personal", False,
     [("dishwasher", "tool"), ("cocktail-party", "event"), ("Schott Zwiesel", "organization"), ("stems", "tool")],
     [],
     "how do I stack the dishwasher on party night and what is the reason",
     "dishwasher glasses first plates second schott zwiesel stem weight"),
    # --- 45 ---
    ("The housewarming aftermath on 2026-01-25 uncovered a broken tile in the downstairs loo and a wine stain on the sisal; budgeted £180 for the repair sweep.", "problem", "personal", False,
     [("housewarming", "event"), ("2026-01-25", "date"), ("tile", "infrastructure"), ("downstairs loo", "place"), ("wine stain", "concept"), ("sisal", "tool")],
     [],
     "what damage surfaced after the housewarming and what did the repairs cost",
     "housewarming aftermath tile break loo wine stain sisal repair budget"),
    # --- 46 ---
    ("Goal for 2026: host ten suppers, two cocktail evenings, one garden party, two book clubs and a single weekend with Pat and Liam.", "decision", "personal", False,
     [("2026", "date"), ("suppers", "event"), ("cocktail evenings", "event"), ("garden party", "event"), ("book clubs", "event"), ("Pat", "person"), ("Liam", "person")],
     [],
     "what is my hosting target for the year and how is it split",
     "hosting goal year supper count cocktail garden book club in laws"),
    # --- 47 ---
    ("The themed supper-club pricing model is £22 per head for ingredients, cash or bank transfer; surplus rolls to the next month's budget, never pocketed.", "architecture", "personal", False,
     [("supper-club", "event"), ("ingredients", "food"), ("cash", "concept"), ("bank transfer", "concept")],
     [],
     "how is the themed-dinner cost split and what happens to any surplus",
     "supper club price per head cash transfer surplus roll over budget"),
    # --- 48 ---
    ("Hosting Dev's sister at the loft 2026-05-03 to 05-05 requires stocking the oat milk, leaving out the French press, and hiding the spare keys behind the book.", "reference", "personal", False,
     [("Dev", "person"), ("loft", "place"), ("2026-05-03", "date"), ("oat milk", "food"), ("French press", "tool"), ("spare keys", "tool"), ("book", "place")],
     [],
     "what prep do I do for the short-let stay in May and where do the keys go",
     "loft guest may prep oat milk french press spare keys hide book"),
    # --- 49 ---
    ("Feels warm in hindsight about the Hokkaido supper club 2025-10-17; six friends, miso butter scallops, the quiet half-hour after the main when nobody checked a phone.", "milestone", "personal", False,
     [("Hokkaido", "concept"), ("supper club", "event"), ("2025-10-17", "date"), ("miso butter scallops", "food"), ("main", "food")],
     [],
     "what is the happy memory from last October's themed dinner",
     "hokkaido supper club warmth scallop miso quiet half hour no phone"),
    # --- 50 ---
    ("The post-party thank-you routine lands the next morning: one text to each guest, one photo to the group chat, a hand-written card only to anyone who brought wine.", "architecture", "personal", False,
     [("thank-you routine", "activity"), ("group chat", "platform"), ("hand-written card", "tool"), ("wine", "food")],
     [],
     "what is my day-after thanks workflow and who gets the paper card",
     "thank you routine text photo group chat hand written card wine bringer"),
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
