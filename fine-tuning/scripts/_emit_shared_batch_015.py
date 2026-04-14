"""One-off emitter for shared-base batch-015 — personal domain (travel / food slice).

Same pattern as _emit_shared_batch_008.py; only ENTRIES and offsets change.
Writes 50 rows to data/v2/shared/batch_015.tmp.jsonl with ids shared-00701..00750.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_015.tmp.jsonl"
ID_OFFSET = 700

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The pintxos crawl in San Sebastián around Calle 31 de Agosto beat every tasting menu I had booked that week.", "fact", "personal", False,
     [("pintxos crawl", "activity"), ("San Sebastián", "place"), ("Calle 31 de Agosto", "place")],
     [],
     "which Basque bar walk outshone the fancy set-course dinners",
     "Basque small-plate stroll lane evening outshine"),
    # --- 2 ---
    ("Booked the overnight sleeper train from Paris to Venice over the morning flight; the carbon math and the views sealed it.", "decision", "personal", False,
     [("sleeper train", "activity"), ("Paris", "place"), ("Venice", "place"), ("morning flight", "activity")],
     [("sleeper train", "morning flight", "REPLACES")],
     "what transport choice took me from the French capital to the lagoon city this trip",
     "night rail Adriatic swap aviation emissions scenery reason"),
    # --- 3 ---
    ("The congee cart behind Yau Ma Tei opens at 05:30 and Uncle Fung remembers my order from three years back.", "reference", "personal", False,
     [("congee cart", "food"), ("Yau Ma Tei", "place"), ("05:30", "date"), ("Uncle Fung", "person")],
     [],
     "where is the early-morning rice porridge stall the vendor still remembers me at",
     "Hong Kong dawn porridge hawker recall regular order"),
    # --- 4 ---
    ("Shellfish allergy surfaced badly after a bowl of tom yum in Chiang Mai; carry the EpiPen on every trip now.", "problem", "personal", False,
     [("Shellfish allergy", "concept"), ("tom yum", "food"), ("Chiang Mai", "place"), ("EpiPen", "tool")],
     [],
     "which northern Thailand meal triggered the medical scare that changed my packing",
     "crustacean reaction spicy soup northern kingdom kit change"),
    # --- 5 ---
    ("Anniversary dinner at Asador Etxebarri is locked in for 2027-05-09; got the single-seating slot after a year on the list.", "milestone", "personal", False,
     [("Asador Etxebarri", "organization"), ("2027-05-09", "date")],
     [],
     "when is the wood-fire Basque grill booked for our big evening",
     "Axpe grill anniversary slot waitlist year reservation"),
    # --- 6 ---
    ("I keep the packing system at three cubes: one shirts, one trousers, one socks-plus-electronics; a carry-on always fits a week.", "architecture", "personal", False,
     [("packing system", "activity"), ("carry-on", "tool")],
     [],
     "how is the luggage layout structured so a week fits in hand baggage",
     "three-bag kit cube division cabin luggage week"),
    # --- 7 ---
    ("Prefers natural wine bars in Lyon to the Michelin bouchons; the lineup changes weekly and the markup is fair.", "preference", "personal", False,
     [("natural wine bars", "activity"), ("Lyon", "place"), ("Michelin bouchons", "organization")],
     [("natural wine bars", "Michelin bouchons", "PREFERS")],
     "which drinking spots do I actually revisit in the Rhône city",
     "low-intervention pour over starred bistro weekly rotation"),
    # --- 8 ---
    ("Lost my passport in Buenos Aires on 2025-11-22 the day before the Iguazú flight; embassy turnaround took 36 hours.", "problem", "personal", False,
     [("Buenos Aires", "place"), ("2025-11-22", "date"), ("Iguazú", "place")],
     [],
     "when and where did the travel document disaster happen before the waterfall trip",
     "Porteño capital passport loss falls flight delay embassy"),
    # --- 9 ---
    ("Cooking class with Signora Rosa in Bologna on 2026-09-14 covers tortellini and the real ragù, not the tourist one.", "milestone", "personal", False,
     [("Signora Rosa", "person"), ("Bologna", "place"), ("2026-09-14", "date"), ("tortellini", "food"), ("ragù", "food")],
     [],
     "which Emilian pasta workshop is locked in and what does it cover",
     "Emilia workshop meat sauce filled pasta authentic syllabus"),
    # --- 10. noise ---
    ("Let me double-check the booking reference before we go further.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Chose the riad in Fes over the resort in Marrakech; narrow alleys and a rooftop courtyard trumped the pool.", "decision", "personal", False,
     [("riad", "place"), ("Fes", "place"), ("resort", "place"), ("Marrakech", "place")],
     [("riad", "resort", "PREFERS")],
     "which Moroccan lodging style won out for the trip and why",
     "medina courtyard stay versus pool resort tradeoff"),
    # --- 12 ---
    ("The jet-lag reset trick from the Seoul trip: no naps, daylight walk on arrival, first meal at local dinner time.", "reference", "personal", False,
     [("jet-lag reset", "activity"), ("Seoul", "place")],
     [],
     "what three-step arrival routine keeps me functional after a long eastward flight",
     "long-haul recovery daylight walk meal timing protocol"),
    # --- 13 ---
    ("Prefers the Airbnb above the bakery on Rua do Almada to any hotel I have tried in Porto; the cortado downstairs is reason enough.", "preference", "personal", False,
     [("Airbnb", "service"), ("Rua do Almada", "place"), ("Porto", "place"), ("hotel", "place"), ("cortado", "food")],
     [("Airbnb", "hotel", "PREFERS")],
     "which short-term stay on that particular Porto street keeps pulling me back",
     "bakery flat Douro city short-term lodging draw espresso"),
    # --- 14 ---
    ("Tipping in Tokyo caused a polite mess on the first night; learned quickly that leaving coins on the counter is an insult.", "problem", "personal", False,
     [("Tipping", "activity"), ("Tokyo", "place")],
     [],
     "which customary gesture backfired on the opening evening of the Japan trip",
     "gratuity misstep Japanese capital etiquette loop learning"),
    # --- 15 ---
    ("The ramen at Menya Saimi in Sapporo is the reference bowl I judge every miso broth against now.", "reference", "personal", False,
     [("Menya Saimi", "organization"), ("Sapporo", "place"), ("miso", "food")],
     [("Menya Saimi", "Sapporo", "LOCATED_IN")],
     "which Hokkaido shop set my benchmark for the fermented-soy noodle soup",
     "Hokkaido noodle house soybean paste broth standard reference"),
    # --- 16 ---
    ("Crossed the Alaska Marine Highway off the bucket list on 2026-08-02; the Juneau to Whittier leg ran three days.", "milestone", "personal", False,
     [("Alaska Marine Highway", "activity"), ("2026-08-02", "date"), ("Juneau", "place"), ("Whittier", "place")],
     [],
     "when did I finally do the northern ferry run and which segment was it",
     "Pacific Northwest ferry bucket item capital-to-port segment date"),
    # --- 17 ---
    ("The Moleskine with the faded orange cover has every restaurant I cared about from 2019 onward; it lives in the carry-on.", "architecture", "personal", False,
     [("Moleskine", "tool"), ("2019", "date"), ("carry-on", "tool")],
     [],
     "what hand-kept travel log catalogues my favourite eateries by year",
     "notebook colour cover dining list since six-year hand record"),
    # --- 18 ---
    ("Gave up the no-carb experiment in Naples after the pizza at Da Michele; two weeks of keto gone and zero regret.", "decision", "personal", False,
     [("no-carb experiment", "activity"), ("Naples", "place"), ("Da Michele", "organization"), ("pizza", "food"), ("keto", "activity")],
     [],
     "which southern Italian pizzeria ended the low-carb run and how long had it lasted",
     "ketogenic stint end pizzeria Campania fortnight collapse"),
    # --- 19 ---
    ("Prefers the Caltrain to the rental car between San Francisco and Palo Alto; the writing hour beats the parking fuss.", "preference", "personal", False,
     [("Caltrain", "service"), ("rental car", "activity"), ("San Francisco", "place"), ("Palo Alto", "place")],
     [("Caltrain", "rental car", "PREFERS")],
     "what transport pairing do I keep choosing on the Peninsula corridor",
     "Bay rail over hire auto writing productive corridor drive"),
    # --- 20 ---
    ("The Oaxacan mole class with Doña Eva on 2026-02-17 covered seven chiles and three toasting stages; wrote it all down.", "milestone", "personal", False,
     [("Oaxacan mole", "food"), ("Doña Eva", "person"), ("2026-02-17", "date")],
     [],
     "when did the southern Mexico sauce lesson happen and who taught it",
     "Mexican state rich sauce workshop pepper count teacher date"),
    # --- 21 ---
    ("Swapped the Bangkok stopover for a Doha transit on the Sydney flight; hotel-included layovers beat a chaotic airport shuffle.", "decision", "personal", False,
     [("Bangkok", "place"), ("Doha", "place"), ("Sydney", "place")],
     [("Doha", "Bangkok", "REPLACES")],
     "which Middle East stopover replaced the Southeast Asia one on the Australia run",
     "Thai layover swap Gulf transit long-haul Oceania route"),
    # --- 22 ---
    ("Coffee rule while travelling: no espresso after 14:00 local; learned the hard way after a white night in Rome.", "architecture", "personal", False,
     [("espresso", "food"), ("14:00", "date"), ("Rome", "place")],
     [],
     "what caffeine cut-off rule did an Italian sleepless night teach me",
     "travel caffeine hour limit capital insomnia lesson rule"),
    # --- 23 ---
    ("The tagine at Café Clock in Chefchaouen keeps pulling me back up north; three visits in two years.", "fact", "personal", False,
     [("tagine", "food"), ("Café Clock", "organization"), ("Chefchaouen", "place")],
     [("Café Clock", "Chefchaouen", "LOCATED_IN")],
     "which blue-city restaurant keeps drawing me back for the clay-pot dish",
     "mountain town stew house repeat visits two-year span"),
    # --- 24 ---
    ("Had to get a proper Schengen visa stamp in London on 2025-12-03; the old biometric was just expiring mid-Croatia hike.", "problem", "personal", False,
     [("Schengen visa", "concept"), ("London", "place"), ("2025-12-03", "date"), ("Croatia", "place")],
     [],
     "when did the European travel paperwork almost derail the Dalmatian hiking plan",
     "EU travel doc renewal winter date Dalmatian coast trek risk"),
    # --- 25 ---
    ("Prefers street-side banh mi in Hoi An to anything the hotel buffet serves; Madam Khanh's cart wins the market.", "preference", "personal", False,
     [("banh mi", "food"), ("Hoi An", "place"), ("hotel buffet", "activity"), ("Madam Khanh", "person")],
     [("banh mi", "hotel buffet", "PREFERS")],
     "which central Vietnam sandwich source beats the lodging breakfast",
     "old-town baguette cart over morning spread vendor name"),
    # --- 26 ---
    ("The packing cube system replaced the old rolled-bundle method I stole from a forum in 2016; nothing wrinkles anymore.", "decision", "personal", False,
     [("packing cube system", "tool"), ("rolled-bundle method", "activity"), ("2016", "date")],
     [("packing cube system", "rolled-bundle method", "REPLACES")],
     "what luggage-organising approach took over from the older rolling technique",
     "compression pouch swap legacy folding method outcome"),
    # --- 27 ---
    ("Took the cacao class in Ubud with Pak Wayan on 2026-01-28; grinding by hand on a stone metate is harder than it sounds.", "milestone", "personal", False,
     [("cacao class", "activity"), ("Ubud", "place"), ("Pak Wayan", "person"), ("2026-01-28", "date"), ("metate", "tool")],
     [],
     "when was the Balinese chocolate workshop and who ran it",
     "Bali cocoa lesson grinder stone teacher highland date"),
    # --- 28 ---
    ("Dietary rule abroad: always try the weirdest thing on the menu once, but never on a travel day.", "architecture", "personal", False,
     [("weirdest thing on the menu", "food")],
     [],
     "what two-part eating rule do I keep while on the road",
     "novel dish trial guardrail transit day restriction"),
    # --- 29 ---
    ("The sparkling Furmint from Tokaj on the tasting flight outshone every Champagne I brought home last year.", "fact", "personal", False,
     [("Furmint", "food"), ("Tokaj", "place"), ("Champagne", "food")],
     [("Furmint", "Champagne", "PREFERS")],
     "which Hungarian sparkling wine beat the French bottles in the home rotation",
     "Hungarian bubbles tasting list French region comparison outcome"),
    # --- 30 ---
    ("Dropped the Patagonia hike after a torn meniscus on 2025-11-08; flew to Mendoza instead, ate a lot and read in courtyards.", "problem", "personal", False,
     [("Patagonia", "place"), ("torn meniscus", "concept"), ("2025-11-08", "date"), ("Mendoza", "place")],
     [],
     "which Argentine hike had to be abandoned and where did I end up instead",
     "southern trek injury pivot wine region courtyard recovery"),
    # --- 31 ---
    ("Started logging coffee shops by latitude in a simple Notion table after the Reykjavík trip; already at 40 entries.", "decision", "personal", False,
     [("coffee shops", "place"), ("Notion", "tool"), ("Reykjavík", "place")],
     [],
     "what tracking habit started after the Icelandic capital visit and where does it live",
     "café logbook geographic sort digital table catalyst trip"),
    # --- 32 ---
    ("Chef Bruno in Tbilisi promised a khinkali lesson in the spring; I need to confirm the 2026-04-20 date soon.", "fact", "personal", False,
     [("Bruno", "person"), ("Tbilisi", "place"), ("khinkali", "food"), ("2026-04-20", "date")],
     [("Bruno", "Tbilisi", "LIVES_IN")],
     "which Georgian dumpling lesson is pencilled in and whose is it",
     "Caucasian dumpling class instructor confirmation pending date"),
    # --- 33 ---
    ("The 1998 Saint-Émilion Sam's parents opened at dinner in Bordeaux remains the reference bottle; everything is post-that.", "reference", "personal", False,
     [("Saint-Émilion", "food"), ("Sam", "person"), ("Bordeaux", "place"), ("1998", "date")],
     [],
     "which Right Bank vintage set my wine benchmark and where was it poured",
     "late-nineties red right-bank Gironde milestone pour benchmark"),
    # --- 34. noise ---
    ("Hmm, one moment — pulling up the map.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Prefers cash markets to card-only grocery shops while travelling; Mercado da Ribeira is the weekly Saturday stop in Lisbon.", "preference", "personal", False,
     [("cash markets", "place"), ("card-only grocery shops", "place"), ("Mercado da Ribeira", "place"), ("Lisbon", "place")],
     [("cash markets", "card-only grocery shops", "PREFERS"), ("Mercado da Ribeira", "Lisbon", "LOCATED_IN")],
     "which bill-paying market style do I prefer abroad and what is the Saturday regular",
     "open-air stall physical money Saturday ritual Portuguese"),
    # --- 36 ---
    ("Split the Tuscany trip into two weeks of Chianti and one of Maremma on 2026-06-01; the southern stretch was the surprise win.", "milestone", "personal", False,
     [("Tuscany", "place"), ("Chianti", "place"), ("Maremma", "place"), ("2026-06-01", "date")],
     [],
     "when did the Italian wine-region split trip start and which half shocked me",
     "central Italy two-region split start date surprise outcome"),
    # --- 37 ---
    ("The shoe rule that saved my feet in Vietnam: one broken-in trail runner, one sandal, no loafers ever.", "architecture", "personal", False,
     [("Vietnam", "place"), ("trail runner", "tool"), ("sandal", "tool"), ("loafers", "tool")],
     [("trail runner", "loafers", "PREFERS")],
     "what two-pair footwear protocol made the Southeast Asia trip bearable",
     "humid country footwear rule trail shoe open strap avoid"),
    # --- 38 ---
    ("Chose the island ferry from Naxos to Santorini over the high-speed catamaran; four hours of deck chairs beat two of bouncing.", "decision", "personal", False,
     [("island ferry", "activity"), ("Naxos", "place"), ("Santorini", "place"), ("catamaran", "activity")],
     [("island ferry", "catamaran", "PREFERS")],
     "which slower Aegean crossing won out between the two islands and why",
     "Cycladic boat choice slower deck option bouncy fast alternative"),
    # --- 39 ---
    ("The sambuca flight on Vulcano with Antonio is still a highlight; we ended the night on the black-sand beach.", "fact", "personal", False,
     [("sambuca flight", "activity"), ("Vulcano", "place"), ("Antonio", "person"), ("black-sand beach", "place")],
     [("black-sand beach", "Vulcano", "LOCATED_IN")],
     "which Aeolian island night with the anise liqueur still comes up in stories",
     "volcanic island anise tasting companion beach close"),
    # --- 40 ---
    ("Hit 50 countries on 2026-03-30 when the Mongolia visa finally came through; celebrated with khorkhog in a ger outside Ulaanbaatar.", "milestone", "personal", False,
     [("Mongolia", "place"), ("2026-03-30", "date"), ("khorkhog", "food"), ("Ulaanbaatar", "place")],
     [],
     "when did I hit the half-century country count and how was it marked",
     "steppe country travel tally milestone stone-cooked meat yurt meal"),
    # --- 41 ---
    ("Takes less than ten minutes to photograph a dish on trips now; two overheads, one side, one context shot, then eat.", "architecture", "personal", False,
     [("photograph a dish", "activity")],
     [],
     "what is my short and sweet meal-photography protocol on the road",
     "four-shot food picture routine quick capture minute cap"),
    # --- 42 ---
    ("Prefers the Rome Trattoria Morgana for cacio e pepe over every carbonara spot I keep meaning to queue for at Roscioli.", "preference", "personal", False,
     [("Trattoria Morgana", "organization"), ("Rome", "place"), ("cacio e pepe", "food"), ("carbonara", "food"), ("Roscioli", "organization")],
     [("Trattoria Morgana", "Roscioli", "PREFERS")],
     "which Roman pasta shop tops the list for me and what dish specifically",
     "capital trattoria cheese pepper pasta queue alternative skip"),
    # --- 43 ---
    ("Souvenir policy now: one small edible and one photo print framed at home, nothing else. Started after the 2023 Kyoto trip.", "decision", "personal", False,
     [("Souvenir policy", "concept"), ("2023", "date"), ("Kyoto", "place")],
     [],
     "what two-item memento rule did the ancient-capital trip trigger",
     "keepsake rule consumable plus image print trigger trip"),
    # --- 44 ---
    ("Food poisoning from raw oysters in Saint-Malo on 2025-10-11 meant two lost days; shellfish out of the rotation for six months.", "problem", "personal", False,
     [("raw oysters", "food"), ("Saint-Malo", "place"), ("2025-10-11", "date")],
     [],
     "which Breton shellfish meal landed me in bed and how long was the fallout",
     "Breton raw bivalve illness autumn date lost day count recovery"),
    # --- 45 ---
    ("The Istanbul spice vendor by the Galata bridge recommended the urfa biber blend for lamb; that jar now rides in checked luggage both ways.", "reference", "personal", False,
     [("Istanbul", "place"), ("Galata bridge", "place"), ("urfa biber", "food")],
     [],
     "whose Bosphorus stall-keeper recommendation changed my home pantry for lamb",
     "Bosporus market blend suggestion roasted pepper protein pairing"),
    # --- 46 ---
    ("The whisky preference shifted from Islay peat to Speyside after the Aberlour tour on 2025-08-15.", "preference", "personal", False,
     [("Islay", "place"), ("Speyside", "place"), ("Aberlour", "organization"), ("2025-08-15", "date")],
     [("Speyside", "Islay", "PREFERS")],
     "which Scottish region took over the glass after the distillery tour and when",
     "Scotch region swap smoke to orchard distillery tour date"),
    # --- 47 ---
    ("Keeps a loose rule to sleep in neighbourhoods, not near stations; the Madrid trip in Lavapiés beat the Atocha hotel stay.", "architecture", "personal", False,
     [("neighbourhoods", "place"), ("stations", "place"), ("Madrid", "place"), ("Lavapiés", "place"), ("Atocha", "place")],
     [("Lavapiés", "Atocha", "PREFERS")],
     "what stay-location rule produced the better Spanish-capital experience",
     "neighbourhood lodging rule transit hub avoidance Spanish capital comparison"),
    # --- 48 ---
    ("The cancelled cooking school in Marrakech on 2026-02-08 pushed me into a spontaneous desert overnight; best accident of that trip.", "problem", "personal", False,
     [("cooking school", "organization"), ("Marrakech", "place"), ("2026-02-08", "date"), ("desert overnight", "activity")],
     [],
     "which Moroccan lesson fell through and what unexpected detour resulted",
     "Moroccan class cancel Sahara pivot accidental highlight outcome"),
    # --- 49 ---
    ("Replaced the usual French Riviera summer with a Croatian island week in 2025; Vis over Villefranche, will repeat.", "decision", "personal", False,
     [("French Riviera", "place"), ("Croatian island", "place"), ("2025", "date"), ("Vis", "place"), ("Villefranche", "place")],
     [("Croatian island", "French Riviera", "REPLACES"), ("Vis", "Villefranche", "PREFERS")],
     "what Adriatic trip took over the usual Côte d'Azur summer last year",
     "Adriatic swap Riviera customary summer island over coast choice"),
    # --- 50 ---
    ("The tea ceremony host Hiroko in Uji gave me her matcha source on 2026-03-02; I order two tins a year from them now.", "reference", "personal", False,
     [("Hiroko", "person"), ("Uji", "place"), ("matcha", "food"), ("2026-03-02", "date")],
     [("Hiroko", "Uji", "LIVES_IN")],
     "whose ceremony-day recommendation became my annual green-powder supplier",
     "Japanese tea town host powdered green supplier annual order"),
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
