"""One-off emitter for shared-base batch-089 — personal domain (vehicles / cars / personal transportation slice).

Writes 50 rows to data/v2/shared/batch_089.tmp.jsonl with ids shared-04401..04450.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_089.tmp.jsonl"
ID_OFFSET = 4400

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Traded the 2014 Honda Civic for a 2026 Kia Niro EV on 2026-03-22 at Westover Motors; the Civic had 138k miles and the clutch was starting to slip.", "milestone", "personal", False,
     [("Honda Civic", "organization"), ("Kia Niro EV", "organization"), ("2026-03-22", "date"), ("Westover Motors", "organization"), ("clutch", "infrastructure")],
     [("Kia Niro EV", "Honda Civic", "REPLACES")],
     "when did the old commuter car get traded in and for what",
     "trade in date civic EV replacement dealer mileage clutch reason"),
    # --- 2 ---
    ("Chose the hybrid RAV4 over the full-electric Ioniq 5 for the household second car; the driveway has no Level 2 charger and the annual ski trip kills EV range.", "decision", "personal", False,
     [("RAV4", "organization"), ("Ioniq 5", "organization"), ("Level 2 charger", "infrastructure"), ("ski trip", "event")],
     [("RAV4", "Ioniq 5", "PREFERS")],
     "which powertrain won for the second household car and why the EV lost",
     "hybrid over EV household second car no charger winter range reason"),
    # --- 3 ---
    ("Dmitri at Harbourside Auto has been my mechanic since 2019; he knows the Subaru's head-gasket history and will text before ordering any part over £200.", "reference", "personal", False,
     [("Dmitri", "person"), ("Harbourside Auto", "organization"), ("2019", "date"), ("Subaru", "organization"), ("head-gasket", "infrastructure")],
     [("Dmitri", "Harbourside Auto", "WORKS_AT")],
     "who is my long-standing mechanic and what does he know about the car",
     "mechanic since 2019 shop subaru head gasket parts text threshold"),
    # --- 4 ---
    ("The 2026 summer road trip prep list for the Outback: replace all four tyres, flush the coolant, pack the roof box, test the bike rack torque before leaving.", "architecture", "personal", False,
     [("Outback", "organization"), ("tyres", "infrastructure"), ("coolant", "infrastructure"), ("roof box", "tool"), ("bike rack", "tool")],
     [],
     "how is the long-haul car prep organised for the wagon this summer",
     "road trip prep outback tyre coolant flush roof box bike rack torque"),
    # --- 5 ---
    ("Prefers the Brompton folder over the full-size hybrid for the Tuesday office day; it clears the train-bay turnstile and stows under the desk.", "preference", "personal", False,
     [("Brompton", "organization"), ("hybrid", "concept"), ("Tuesday", "date"), ("train-bay turnstile", "infrastructure")],
     [("Brompton", "hybrid", "PREFERS")],
     "which bike wins for the weekly office commute and why the folder",
     "brompton over hybrid bike train turnstile under desk stow tuesday"),
    # --- 6 ---
    ("The Subaru Outback is named Badger; 2019 plate, crystal silver, 74k miles as of 2026-04, bought used from a GP in Winchester with full dealer history.", "reference", "personal", False,
     [("Subaru Outback", "organization"), ("Badger", "organization"), ("2019", "date"), ("2026-04", "date"), ("Winchester", "place"), ("GP", "person")],
     [],
     "what is the family wagon named and what are its provenance details",
     "outback nickname plate year mileage previous owner GP winchester"),
    # --- 7 ---
    ("Replaced the commuter train season pass with a Trek FX bike on 2026-02-10; the pass was £2,180 a year and the bike paid for itself in four months.", "decision", "personal", False,
     [("train season pass", "tool"), ("Trek FX", "organization"), ("2026-02-10", "date")],
     [("Trek FX", "train season pass", "REPLACES")],
     "which commute swap landed in early 2026 and how did the maths work",
     "train pass swap bike trek FX payback months annual cost commute"),
    # --- 8 ---
    ("Booked the motorbike CBT for 2026-05-02 at Thundersley Training; the plan is the A2 test by autumn so the Honda CB500F becomes legal.", "milestone", "personal", False,
     [("motorbike CBT", "event"), ("2026-05-02", "date"), ("Thundersley Training", "organization"), ("A2 test", "event"), ("Honda CB500F", "organization")],
     [],
     "when is the motorbike intro training and what is the licence plan after it",
     "CBT booking date training school A2 test autumn CB500F target"),
    # --- 9 ---
    ("The garage organising plan uses four zones: car bay, bike rack on the north wall, tool pegboard on the east, and winter-tyre rack above the freezer.", "architecture", "personal", False,
     [("garage", "place"), ("car bay", "place"), ("bike rack", "tool"), ("tool pegboard", "tool"), ("winter-tyre rack", "tool"), ("freezer", "tool")],
     [("bike rack", "garage", "LOCATED_IN"), ("tool pegboard", "garage", "LOCATED_IN")],
     "how is the garage laid out for the cars bikes and tools",
     "garage zones car bay bike rack pegboard winter tyre shelf layout"),
    # --- 10. noise ---
    ("Let me glance at the fuel log before I answer that.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("The Kia Niro EV's home charger is a Zappi 7 kW on the garage wall, installed on 2026-03-29 by Octopus Energy Services for £1,150 after the grant.", "fact", "personal", False,
     [("Kia Niro EV", "organization"), ("Zappi", "organization"), ("garage wall", "place"), ("2026-03-29", "date"), ("Octopus Energy Services", "organization")],
     [("Zappi", "garage wall", "LOCATED_IN")],
     "what home charger was fitted for the EV and who fitted it",
     "zappi 7kw charger install date installer cost after grant garage"),
    # --- 12 ---
    ("Prefers the 05:42 express train to driving into the city on Wednesdays; the congestion charge and the car-park fee together beat the rail fare every week.", "preference", "personal", False,
     [("express train", "infrastructure"), ("Wednesdays", "date"), ("congestion charge", "concept"), ("car-park fee", "concept")],
     [("express train", "congestion charge", "PREFERS")],
     "which Wednesday commute mode wins and what tips the maths",
     "early train over drive congestion charge park fee rail fare wednesday"),
    # --- 13 ---
    ("The used-car shopping trip to Arnold Clark Southampton on 2026-02-14 turned up three strong candidates; went home without signing because the Niro stock was in Leeds.", "fact", "personal", False,
     [("Arnold Clark Southampton", "organization"), ("2026-02-14", "date"), ("Niro", "organization"), ("Leeds", "place")],
     [],
     "what did the february dealer visit produce and why no deal on the day",
     "used car dealer trip candidates no deal stock location leeds date"),
    # --- 14 ---
    ("The CB500F has a 16-litre tank and I log every fill in a small notebook in the glovebox; average is 58 mpg over the last 1,200 miles.", "reference", "personal", False,
     [("CB500F", "organization"), ("16-litre tank", "concept"), ("notebook", "tool"), ("glovebox", "place"), ("1,200 miles", "concept")],
     [("notebook", "glovebox", "LOCATED_IN")],
     "how do I track the motorbike fuel and what has the economy been",
     "CB500F tank size fuel notebook glovebox mpg average mileage log"),
    # --- 15 ---
    ("Got full car licence on 2012-09-04 at Basingstoke test centre after three attempts; the second fail was for a missed mirror check on a roundabout.", "milestone", "personal", False,
     [("car licence", "concept"), ("2012-09-04", "date"), ("Basingstoke test centre", "place"), ("mirror check", "method"), ("roundabout", "infrastructure")],
     [],
     "when did the car licence finally pass and what tripped me up earlier",
     "driving licence pass date test centre attempts mirror fail reason"),
    # --- 16 ---
    ("The Outback's annual service with Dmitri is every March; 2026's came in at £412 including a new air filter and the rear wiper rubber.", "fact", "personal", False,
     [("Outback", "organization"), ("Dmitri", "person"), ("March", "date"), ("2026", "date"), ("air filter", "infrastructure"), ("rear wiper rubber", "infrastructure")],
     [],
     "what did the wagon's march service cost this year and what got replaced",
     "outback service march cost filter wiper rubber mechanic line items"),
    # --- 17 ---
    ("Chose the Thule EuroClassic G6 tow-ball bike rack over the roof-mounted Atera on 2026-01-18; the roof mount was killing Outback fuel economy by 18%.", "decision", "personal", False,
     [("Thule EuroClassic G6", "organization"), ("Atera", "organization"), ("2026-01-18", "date"), ("Outback", "organization")],
     [("Thule EuroClassic G6", "Atera", "REPLACES")],
     "which bike-carrier won out and what was the fuel-economy trigger",
     "thule tow ball over atera roof mount fuel economy hit 18 percent"),
    # --- 18 ---
    ("Parking permit for Zone C at 14 Marlow Avenue renewed on 2026-03-01 at £135 for the year; covers two vehicles and one visitor book of 20 day-passes.", "fact", "personal", False,
     [("Zone C", "place"), ("14 Marlow Avenue", "place"), ("2026-03-01", "date"), ("visitor book", "tool")],
     [],
     "when did the residential parking permit renew and what does it cover",
     "parking permit zone renewal cost two cars visitor passes address date"),
    # --- 19 ---
    ("The Honda Civic's head-unit died on 2025-12-19 on the M3 south of Fleet; limped to the services and Dmitri sourced a Pioneer replacement for £190 fitted.", "problem", "personal", False,
     [("Honda Civic", "organization"), ("2025-12-19", "date"), ("M3", "infrastructure"), ("Fleet", "place"), ("Dmitri", "person"), ("Pioneer", "organization")],
     [("Pioneer", "Honda Civic", "CONFIGURES")],
     "what broke on the civic in december and how did it get fixed",
     "civic head unit fail motorway services pioneer replacement cost date"),
    # --- 20 ---
    ("Prefers the back-lane cycle route to the main-road painted lane for the Wednesday bike commute; the painted lane has four right-turn conflicts in a mile.", "preference", "personal", False,
     [("back-lane cycle route", "infrastructure"), ("main-road painted lane", "infrastructure"), ("Wednesday", "date"), ("right-turn conflicts", "concept")],
     [("back-lane cycle route", "main-road painted lane", "PREFERS")],
     "which bike route wins for the wednesday commute and what is the safety read",
     "back lane over painted lane cycle route right turn conflict count"),
    # --- 21 ---
    ("Car camped in the Outback on the 2025-09-12 Lakes trip; foam mattress fits the folded-seat floor exactly and the cargo blind doubles as a privacy screen.", "fact", "personal", False,
     [("Outback", "organization"), ("2025-09-12", "date"), ("Lakes", "place"), ("foam mattress", "tool"), ("cargo blind", "tool")],
     [],
     "when did I first sleep in the wagon and what was the setup",
     "car camp outback lakes foam mattress cargo blind privacy date"),
    # --- 22 ---
    ("The winter tyres for the Niro are Michelin CrossClimate 2 in 215/60 R17; swap-on is 1 November, swap-off is the first mild week after 1 April.", "reference", "personal", False,
     [("Niro", "organization"), ("Michelin CrossClimate 2", "organization"), ("215/60 R17", "concept"), ("1 November", "date"), ("1 April", "date")],
     [],
     "which winter tyres does the EV run on and what is the swap schedule",
     "michelin cross climate size EV niro swap dates november april rule"),
    # --- 23 ---
    ("Replaced the old 2017 Specialized Sirrus with a Trek FX 3 Disc on 2026-02-08 after the Sirrus frame cracked at the bottom bracket weld.", "milestone", "personal", False,
     [("Specialized Sirrus", "organization"), ("Trek FX 3 Disc", "organization"), ("2026-02-08", "date"), ("bottom bracket weld", "infrastructure")],
     [("Trek FX 3 Disc", "Specialized Sirrus", "REPLACES")],
     "when did the commuter bike get replaced and why the old one was retired",
     "sirrus swap trek FX frame crack bottom bracket weld retirement date"),
    # --- 24 ---
    ("The leasing-vs-buy calculation for the Niro on 2026-03-05 showed PCP £318/month vs £27,400 cash; cash won because we plan to keep it past ten years.", "decision", "personal", False,
     [("Niro", "organization"), ("2026-03-05", "date"), ("PCP", "method"), ("cash", "method"), ("ten years", "concept")],
     [("cash", "PCP", "PREFERS")],
     "which funding route won for the EV and what horizon drove it",
     "niro lease vs buy PCP cash comparison ten year hold decision date"),
    # --- 25 ---
    ("Takes the number 17 bus into town on Saturdays; cheaper than parking and drops at the market square three minutes from the butcher.", "preference", "personal", False,
     [("number 17 bus", "infrastructure"), ("Saturdays", "date"), ("market square", "place"), ("butcher", "place")],
     [("number 17 bus", "market square", "LOCATED_IN")],
     "which saturday-into-town mode wins and what makes it convenient",
     "bus 17 over car saturday parking market square butcher walking"),
    # --- 26 ---
    ("The driveway is 4.9 m long which just fits the Niro nose-in with 10 cm behind the bumper; the Outback has to go on the road because it is 4.82 m and needs mirror clearance.", "fact", "personal", False,
     [("driveway", "place"), ("Niro", "organization"), ("Outback", "organization")],
     [("Niro", "driveway", "LOCATED_IN")],
     "how do the two cars fit the driveway and which one ends up on the road",
     "driveway length niro fit outback road parking mirror clearance reason"),
    # --- 27 ---
    ("The motorbike hobbyism is strictly dry-season; the CB500F gets laid up in the garage from November to March with a battery tender and a fuel stabiliser.", "architecture", "personal", False,
     [("CB500F", "organization"), ("garage", "place"), ("November", "date"), ("March", "date"), ("battery tender", "tool"), ("fuel stabiliser", "tool")],
     [("CB500F", "garage", "LOCATED_IN")],
     "how is the motorbike winter layup handled and over what months",
     "CB500F winter layup garage battery tender stabiliser months rule"),
    # --- 28 ---
    ("Switched from Shell V-Power to supermarket 95 RON on the Outback in 2025-10 after six months of A-B logging; no measurable mpg or smoothness difference.", "decision", "personal", False,
     [("Shell V-Power", "organization"), ("supermarket 95 RON", "concept"), ("Outback", "organization"), ("2025-10", "date")],
     [("supermarket 95 RON", "Shell V-Power", "REPLACES")],
     "which fuel grade won for the wagon and what evidence backed the swap",
     "shell vpower swap supermarket 95 ron outback A B test mpg date"),
    # --- 29 ---
    ("The bike commute kit lives in a hook by the back door: helmet, yellow jacket, ankle band, cable lock, and a Knog Blinder rear light on a strap.", "reference", "personal", False,
     [("bike commute kit", "tool"), ("back door", "place"), ("helmet", "tool"), ("yellow jacket", "tool"), ("ankle band", "tool"), ("Knog Blinder", "organization")],
     [("bike commute kit", "back door", "LOCATED_IN")],
     "where do I keep the cycling gear and what is in the set",
     "cycling gear storage hook entrance hi-vis vest strap light leg band"),
    # --- 30 ---
    ("Passed the A2 motorbike test at Tilford on 2026-04-11 on the school's CB650R; examiner was Clive, one minor for a late shoulder-check on the U-turn.", "milestone", "personal", False,
     [("A2 motorbike test", "event"), ("Tilford", "place"), ("2026-04-11", "date"), ("CB650R", "organization"), ("Clive", "person"), ("U-turn", "method")],
     [],
     "when did the A2 motorcycle test pass and how did it go",
     "A2 pass tilford CB650R examiner minor shoulder check u turn date"),
    # --- 31 ---
    ("The Outback's head-gasket replacement in 2023-05 at Harbourside Auto was £1,420; Dmitri kept the old gasket on a shelf as a reminder to change coolant annually.", "problem", "personal", False,
     [("Outback", "organization"), ("head-gasket", "infrastructure"), ("2023-05", "date"), ("Harbourside Auto", "organization"), ("Dmitri", "person"), ("coolant", "infrastructure")],
     [("head-gasket", "Outback", "CAUSES")],
     "what was the big wagon repair and what habit did it trigger",
     "outback head gasket cost shop shelf reminder annual coolant change"),
    # --- 32 ---
    ("Replaced the daily-drive car keys split-ring with a Keysmart compact holder on 2025-11-02; stops the Niro fob from scratching the Outback fob in the bowl.", "decision", "personal", False,
     [("Keysmart", "organization"), ("2025-11-02", "date"), ("Niro fob", "tool"), ("Outback fob", "tool"), ("bowl", "tool")],
     [("Keysmart", "Niro fob", "CONFIGURES")],
     "what key-storage swap happened in late 2025 and what problem did it fix",
     "keysmart holder split ring swap fob scratch bowl niro outback date"),
    # --- 33 ---
    ("The Niro's ABRP route plan for the 2026-07-18 Edinburgh trip has two charge stops: Gretna Gateway and Abington; 92% arrival state-of-charge.", "architecture", "personal", False,
     [("Niro", "organization"), ("ABRP", "api"), ("2026-07-18", "date"), ("Edinburgh", "place"), ("Gretna Gateway", "place"), ("Abington", "place")],
     [("Niro", "ABRP", "USES")],
     "how is the summer edinburgh charge plan laid out for the EV",
     "ABRP niro edinburgh trip two stop gretna abington arrival soc date"),
    # --- 34. noise ---
    ("One moment, I need to reset the trip computer first.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Prefers the Kwik Fit Andover branch to the Halfords Romsey for tyre work; Andover keeps the torque log and always re-torques after 50 miles.", "preference", "personal", False,
     [("Kwik Fit Andover", "organization"), ("Halfords Romsey", "organization"), ("torque log", "tool")],
     [("Kwik Fit Andover", "Halfords Romsey", "PREFERS")],
     "which tyre-fitter wins out and what is the technical reason",
     "kwik fit over halfords andover romsey torque log 50 mile retorque"),
    # --- 36 ---
    ("The Outback's boot organiser has three labelled boxes: Car-Camp, Dog, and Tools; this stops the CB500F kit migrating into the car on race weekends.", "architecture", "personal", False,
     [("Outback", "organization"), ("Car-Camp", "tool"), ("Dog", "tool"), ("Tools", "tool"), ("CB500F", "organization")],
     [],
     "how is the wagon boot compartmentalised and what problem does it solve",
     "outback boot organiser boxes car camp dog tools separation race"),
    # --- 37 ---
    ("Logged the first 1,000 miles on the Niro on 2026-04-13; averaged 4.2 miles per kWh mixed driving and 3.6 on the single motorway run to Bristol.", "milestone", "personal", False,
     [("Niro", "organization"), ("1,000 miles", "concept"), ("2026-04-13", "date"), ("Bristol", "place")],
     [],
     "when did the EV hit the first thousand miles and what was the efficiency",
     "niro 1000 mile mark efficiency mixed motorway bristol run date"),
    # --- 38 ---
    ("Chose the Midland BT-X2 Pro helmet intercom over the Cardo Packtalk for the pillion setup; cheaper pair-up and Dev's existing Midland pairs straight in.", "decision", "personal", False,
     [("Midland BT-X2 Pro", "organization"), ("Cardo Packtalk", "organization"), ("pillion", "concept"), ("Dev", "person")],
     [("Midland BT-X2 Pro", "Cardo Packtalk", "PREFERS")],
     "which helmet intercom won out for the two-up motorbike rides and why",
     "midland BTX2 over cardo packtalk pillion pair dev existing compat"),
    # --- 39 ---
    ("The MOT for the Outback is due 2026-09-14 at Harbourside Auto; the tester flagged a marginal front offside track-rod end last year so it is on the watch list.", "reference", "personal", False,
     [("MOT", "event"), ("Outback", "organization"), ("2026-09-14", "date"), ("Harbourside Auto", "organization"), ("track-rod end", "infrastructure")],
     [],
     "when is the wagon mot and what part is on the watch list",
     "outback MOT date shop track rod end marginal advisory watch list"),
    # --- 40 ---
    ("Replaced the Garmin Edge 130 with a Wahoo Elemnt Bolt v2 on 2026-03-02 for the bike commutes; the Wahoo's turn alerts are louder and survive the rain better.", "decision", "personal", False,
     [("Garmin Edge 130", "organization"), ("Wahoo Elemnt Bolt v2", "organization"), ("2026-03-02", "date"), ("turn alerts", "concept")],
     [("Wahoo Elemnt Bolt v2", "Garmin Edge 130", "REPLACES")],
     "which bike computer took over and what were the two drivers of the swap",
     "garmin swap wahoo elemnt bolt v2 turn alert loud rain resistance"),
    # --- 41 ---
    ("The car-share car-club membership with Enterprise Car Club renewed on 2026-01-20 at £60 a year; mainly for the van-hire day a month for the allotment runs.", "fact", "personal", False,
     [("Enterprise Car Club", "organization"), ("2026-01-20", "date"), ("van-hire", "activity"), ("allotment", "place")],
     [],
     "when did the car-club renewal happen and what is the use pattern",
     "enterprise car club renewal annual fee van hire allotment runs date"),
    # --- 42 ---
    ("Prefers the Camper Van category on Turo over hiring from Spaceships UK; Turo owners include kit like the stove and bedding, Spaceships charges extra per item.", "preference", "personal", False,
     [("Turo", "organization"), ("Spaceships UK", "organization"), ("stove", "tool"), ("bedding", "tool")],
     [("Turo", "Spaceships UK", "PREFERS")],
     "which van-hire platform wins for car-camping trips and why",
     "turo over spaceships camper kit stove bedding included pricing"),
    # --- 43 ---
    ("The garage door opener went dead on 2026-03-18 mid-storm; swapped the logic board with a Chamberlain MYQ retrofit and added a battery backup on the same circuit.", "problem", "personal", False,
     [("garage door opener", "tool"), ("2026-03-18", "date"), ("Chamberlain MYQ", "organization"), ("battery backup", "tool")],
     [("Chamberlain MYQ", "garage door opener", "FIXES")],
     "what failed in the garage during the march storm and what was the fix",
     "garage opener dead storm logic board chamberlain myq battery backup"),
    # --- 44 ---
    ("Bike commuted 184 days in 2025 out of a 220-target; weather cost the most days in February and November, not January as I had expected.", "fact", "personal", False,
     [("2025", "date"), ("220-target", "goal"), ("February", "date"), ("November", "date"), ("January", "date")],
     [],
     "how many bike-commute days landed in 2025 and which months cost the most",
     "bike commute count target miss february november january surprise"),
    # --- 45 ---
    ("Chose the £30 annual bike-shed membership at Waterloo Station over daily £2 locker fees; pays back at 15 trips and I do double that a year.", "decision", "personal", False,
     [("bike-shed membership", "concept"), ("Waterloo Station", "place"), ("locker fees", "concept")],
     [("bike-shed membership", "locker fees", "PREFERS")],
     "which station bike-parking plan wins and what was the payback maths",
     "waterloo bike shed annual over daily locker pay back trips volume"),
    # --- 46 ---
    ("The used-car road-test checklist I run on every viewing: cold start, first-gear creep on a hill, all three pedals to the floor on the motorway slip-road, and a merge at 50 mph.", "reference", "personal", False,
     [("used-car road-test checklist", "method"), ("cold start", "method"), ("motorway slip-road", "infrastructure")],
     [],
     "what is the fixed road-test routine for used-car viewings",
     "used car road test checklist cold start hill creep pedals merge 50"),
    # --- 47 ---
    ("The registration paperwork for the Niro arrived from the DVLA on 2026-04-02; V5C green slip filed in the car folder in the hallway cupboard.", "fact", "personal", False,
     [("Niro", "organization"), ("DVLA", "organization"), ("2026-04-02", "date"), ("V5C", "concept"), ("hallway cupboard", "place")],
     [("V5C", "hallway cupboard", "LOCATED_IN")],
     "when did the ev paperwork land and where does the green slip live",
     "niro V5C DVLA arrival filing hallway cupboard car folder date"),
    # --- 48 ---
    ("Prefers to pre-cool the Niro off the home charger for ten minutes before summer school runs; keeps the battery-conditioning load off the 12 V and the kids comfortable.", "preference", "personal", False,
     [("Niro", "organization"), ("home charger", "infrastructure"), ("school runs", "event"), ("12 V", "concept")],
     [("Niro", "home charger", "USES")],
     "which EV summer prep habit wins and what does it protect",
     "niro pre cool home charger school run summer 12v battery load"),
    # --- 49 ---
    ("The motorbike kit inventory lives on an index card in the tank bag: Alpinestars gloves, Arai helmet, Dainese D-Air vest, Oxford armoured jeans, Sidi boots.", "reference", "personal", False,
     [("tank bag", "tool"), ("Alpinestars", "organization"), ("Arai", "organization"), ("Dainese D-Air", "organization"), ("Oxford", "organization"), ("Sidi", "organization")],
     [],
     "what kit does the motorbike gear card list and where is the card",
     "motorbike kit card tank bag alpinestars arai dainese oxford sidi"),
    # --- 50 ---
    ("The 2026-04-19 road-trip prep for Cornwall included a full Outback service on 2026-04-15, a new set of Bridgestone Weather Control tyres, and a roof-box leak test with the hose.", "architecture", "personal", False,
     [("2026-04-19", "date"), ("Cornwall", "place"), ("Outback", "organization"), ("2026-04-15", "date"), ("Bridgestone Weather Control", "organization"), ("roof-box", "tool")],
     [],
     "how did the cornwall trip prep break down across dates and work items",
     "cornwall trip prep outback service bridgestone tyres roof box leak"),
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
