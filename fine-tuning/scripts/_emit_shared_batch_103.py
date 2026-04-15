"""One-off emitter for shared-base batch-103 — personal domain (moving, relocation, apartment hunting slice).

Writes 50 rows to data/v2/shared/batch_103.tmp.jsonl with ids shared-05101..05150.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_103.tmp.jsonl"
ID_OFFSET = 5100

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Decided on 2026-02-14 to leave Bristol for Edinburgh after the third winter of damp flats; the northern salary bump only covered half of the deposit.", "decision", "personal", False,
     [("Bristol", "place"), ("Edinburgh", "place"), ("2026-02-14", "date"), ("deposit", "concept")],
     [("Edinburgh", "Bristol", "REPLACES")],
     "when did I commit to the north-move and how did the finances stack up",
     "relocate south west to scotland salary bump partial deposit cover date"),
    # --- 2 ---
    ("Viewed the Leith Walk two-bed on 2026-03-02 with Rettie & Co; cornicing intact, south-facing kitchen, but the boiler cupboard reeked of gas.", "fact", "personal", False,
     [("Leith Walk", "place"), ("2026-03-02", "date"), ("Rettie & Co", "organization"), ("boiler cupboard", "place")],
     [("Leith Walk", "Rettie & Co", "RELATED_TO")],
     "what stood out at the first tenement viewing on that avenue",
     "flat viewing date agent features south kitchen gas smell cupboard"),
    # --- 3 ---
    ("Chose renting over buying in the new city for the first year; house prices in Stockbridge were above the pre-approval, and the market was cooling weekly.", "decision", "personal", False,
     [("renting", "concept"), ("buying", "concept"), ("Stockbridge", "place"), ("pre-approval", "concept")],
     [("renting", "buying", "PREFERS")],
     "which housing tenure won out for year one and why the numbers forced it",
     "rent over buy first year district price above approval market cool"),
    # --- 4 ---
    ("Hired Pickfords over the cheaper local crew for the Bristol-to-Edinburgh haul on 2026-04-10; insurance coverage up to £60,000 made the £480 premium worth it.", "decision", "personal", False,
     [("Pickfords", "organization"), ("Bristol", "place"), ("Edinburgh", "place"), ("2026-04-10", "date"), ("insurance", "concept")],
     [("Pickfords", "Bristol", "RELATED_TO")],
     "which movers did I pick for the cross-country day and what tipped it",
     "mover choice national firm over local insurance ceiling premium date"),
    # --- 5 ---
    ("Prefers booking the survey before the mortgage application; the Homebuyer Report on 12 Dean Street caught a lintel crack that shaved £4,000 off the offer.", "preference", "personal", False,
     [("survey", "method"), ("mortgage application", "concept"), ("Homebuyer Report", "tool"), ("12 Dean Street", "place"), ("lintel crack", "finding")],
     [("survey", "mortgage application", "PREFERS")],
     "which order for survey and finance steps wins and what did it catch",
     "survey before mortgage order report lintel finding price reduction"),
    # --- 6 ---
    ("Replaced the rolling twelve-month lease in Bristol with a six-month short assured tenancy in Edinburgh; wanted an exit ramp if the new job soured.", "decision", "personal", False,
     [("twelve-month lease", "concept"), ("Bristol", "place"), ("short assured tenancy", "concept"), ("Edinburgh", "place")],
     [("short assured tenancy", "twelve-month lease", "REPLACES")],
     "which tenancy length took over after the move and what motivated it",
     "lease swap yearly to six month new city exit option job risk"),
    # --- 7 ---
    ("Boxed up the kitchen on 2026-04-07 with Tara's colour-code system: red tape for fragile, blue for first-open, black for deep-storage attic stuff.", "architecture", "personal", False,
     [("kitchen", "place"), ("2026-04-07", "date"), ("Tara", "person"), ("colour-code system", "method"), ("attic", "place")],
     [("colour-code system", "Tara", "AUTHORED_BY")],
     "how did I tag the packing boxes and who taught me the trick",
     "packing colour tape fragile first open deep storage attic origin"),
    # --- 8 ---
    ("Drove the U-Haul 24-foot box truck from Austin to Denver on 2026-03-22, 920 miles over fourteen hours with Mia splitting the wheel at Amarillo.", "milestone", "personal", False,
     [("U-Haul", "organization"), ("Austin", "place"), ("Denver", "place"), ("2026-03-22", "date"), ("Mia", "person"), ("Amarillo", "place")],
     [("U-Haul", "Austin", "RELATED_TO")],
     "when did the cross-country drive happen and who shared the driving",
     "truck rental long haul mileage hours drive split handover city"),
    # --- 9 ---
    ("The settling-in ritual is the same every move: make the bed first, plug the kettle in second, hang the parents' photo third; takes twenty minutes.", "reference", "personal", False,
     [("bed", "infrastructure"), ("kettle", "tool"), ("photo", "tool")],
     [],
     "what is the first-night routine in a new place",
     "settle in ritual order bed kettle photo twenty minutes unpack start"),
    # --- 10. noise ---
    ("I've got the measuring tape somewhere in this pile of boxes — give me a minute.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("First impression of Morningside: quieter than the brochure suggested, but the 23 bus hits every eight minutes and the Bainfield bakery smells like Sunday.", "fact", "personal", False,
     [("Morningside", "place"), ("23 bus", "infrastructure"), ("Bainfield", "organization")],
     [("Bainfield", "Morningside", "LOCATED_IN")],
     "what did the new neighbourhood look like on the first walk-around",
     "district first take quiet bus frequency bakery smell location reason"),
    # --- 12 ---
    ("Leaving the Redland flat on 2026-04-09 was harder than expected; five years of wall dents, the cherry tree out back, Mrs Alby across the hall.", "fact", "personal", False,
     [("Redland", "place"), ("2026-04-09", "date"), ("cherry tree", "place"), ("Mrs Alby", "person")],
     [("Mrs Alby", "Redland", "LIVES_IN")],
     "what made leaving the old flat a hard day",
     "move out old address date years wall dents tree neighbour attachment"),
    # --- 13 ---
    ("Moved out of my parents' house in Guildford on 2026-01-18 at 28 years old; Mum cried at the drive, Dad spent the morning wiring the new hi-fi.", "milestone", "personal", False,
     [("parents' house", "place"), ("Guildford", "place"), ("2026-01-18", "date"), ("Mum", "person"), ("Dad", "person"), ("hi-fi", "tool")],
     [("parents' house", "Guildford", "LOCATED_IN")],
     "when did the leave-the-family-home day happen and how did each parent handle it",
     "parents house departure age date town reaction last morning wiring"),
    # --- 14 ---
    ("Landlord withheld £380 of the £1,200 deposit on the Redland flat for a carpet stain and a chipped architrave; deposit scheme ruled in my favour on 2026-05-02.", "problem", "personal", False,
     [("Landlord", "person"), ("Redland", "place"), ("deposit scheme", "organization"), ("2026-05-02", "date"), ("architrave", "infrastructure")],
     [],
     "what happened with the end-of-lease deposit dispute and when did it resolve",
     "deposit dispute withhold carpet architrave scheme ruling date"),
    # --- 15 ---
    ("Staged the Redland flat for sale on 2026-03-15: pulled the vinyl rug, swapped the hall bulbs for warm white, baked bread an hour before the first viewing.", "fact", "personal", False,
     [("Redland", "place"), ("2026-03-15", "date"), ("vinyl rug", "tool"), ("warm white", "concept"), ("bread", "food")],
     [],
     "what did the first-open-house prep actually involve",
     "home stage sale day rug removal bulb swap bread smell viewing prep"),
    # --- 16 ---
    ("Prefers MovingGiant over the man-with-a-van options for a two-bed move; crew of three, blankets included, no extra charge for stairs up to floor four.", "preference", "personal", False,
     [("MovingGiant", "organization"), ("man-with-a-van", "service"), ("blankets", "tool")],
     [("MovingGiant", "man-with-a-van", "PREFERS")],
     "which mover pattern wins for a mid-size flat move and what do I get for it",
     "mover pick firm over solo crew size blankets stairs flat move choice"),
    # --- 17 ---
    ("Shipped twelve boxes to the Lisbon flat via a Seven Seas Worldwide MoveCube on 2026-02-28; forty-day transit, £640 all in, no customs drama.", "milestone", "personal", False,
     [("Lisbon", "place"), ("Seven Seas Worldwide", "organization"), ("MoveCube", "service"), ("2026-02-28", "date"), ("customs", "organization")],
     [("MoveCube", "Seven Seas Worldwide", "IS_A")],
     "how did the shipping-container international leg go and what did it run to",
     "international ship container service transit weeks cost customs clean"),
    # --- 18 ---
    ("Viewed 21 flats over six weekends before the offer on 9 Warriston Crescent landed on 2026-03-25; the Warriston one was the first with south light in every room.", "milestone", "personal", False,
     [("9 Warriston Crescent", "place"), ("2026-03-25", "date"), ("south light", "concept")],
     [],
     "how many viewings before the winning offer and what made the place stand out",
     "viewing count weekends offer date south light all rooms winner pick"),
    # --- 19 ---
    ("Rejected the Stockbridge garden flat on 2026-03-10 despite the price; the main bedroom shared a wall with a pub cellar and the landlord refused a soundproofing clause.", "decision", "personal", False,
     [("Stockbridge", "place"), ("2026-03-10", "date"), ("pub cellar", "place"), ("soundproofing clause", "concept")],
     [],
     "which flat did I turn down and what was the dealbreaker",
     "flat reject district date bedroom pub noise landlord refuse clause"),
    # --- 20 ---
    ("Chose Dulux Timeless over a bespoke Farrow & Ball colour for all interior walls in the new flat; repaint touch-ups over the tenancy would be cheap and easy.", "decision", "personal", False,
     [("Dulux Timeless", "tool"), ("Farrow & Ball", "organization"), ("interior walls", "infrastructure")],
     [("Dulux Timeless", "Farrow & Ball", "PREFERS")],
     "which paint won for the new flat and what drove it",
     "wall paint choice mass over premium touch up cheap tenancy reason"),
    # --- 21 ---
    ("The move-out clean at Redland on 2026-04-08 used End Of Tenancy Cleaners UK at £210; they missed the oven roof and I did it myself with Oven Pride before handover.", "problem", "personal", False,
     [("Redland", "place"), ("2026-04-08", "date"), ("End Of Tenancy Cleaners UK", "organization"), ("oven", "infrastructure"), ("Oven Pride", "tool")],
     [],
     "what happened with the contract clean before handover and what did I have to finish",
     "end of tenancy clean contractor price miss oven roof self finish product"),
    # --- 22 ---
    ("Prefers viewing flats on rainy days; water stains, leaking frames, and damp smells hide in dry weather and the Warriston ceiling spot appeared only on a Tuesday downpour.", "preference", "personal", False,
     [("rainy days", "concept"), ("water stains", "finding"), ("damp", "concept"), ("Warriston", "place"), ("Tuesday", "date")],
     [("rainy days", "damp", "CAUSES")],
     "which weather suits flat viewings best and what did that unlock",
     "viewing weather wet reveal damp stain frame leak ceiling discovery"),
    # --- 23 ---
    ("Handed back the Redland keys to the agent on 2026-04-09 at Hopewell Lettings; signed the inventory snag list with four pencilled corrections.", "milestone", "personal", False,
     [("Redland", "place"), ("2026-04-09", "date"), ("Hopewell Lettings", "organization"), ("inventory snag list", "tool")],
     [("Hopewell Lettings", "Redland", "RELATED_TO")],
     "when did the old-flat key handback happen and what paperwork closed it",
     "keys return agent date inventory checkout list corrections sign"),
    # --- 24 ---
    ("The renters-versus-owners math said rent in year one, buy by year three; saving £620 a month toward the deposit rather than paying it down as principal.", "architecture", "personal", False,
     [("rent", "concept"), ("deposit", "concept"), ("principal", "concept")],
     [("rent", "deposit", "RELATED_TO")],
     "what does the rent-then-buy plan actually look like in numbers",
     "rent buy plan year horizon monthly saving deposit principal choice"),
    # --- 25 ---
    ("Booked Bishop's Move for the office-furniture leg separately from Pickfords for the household goods on 2026-04-10; two crews, two invoices, no conflict.", "architecture", "personal", False,
     [("Bishop's Move", "organization"), ("Pickfords", "organization"), ("2026-04-10", "date"), ("office-furniture", "infrastructure")],
     [],
     "how did the move split across two firms and what did each take",
     "mover split office home two firms date invoice crew coordination"),
    # --- 26 ---
    ("First night in Edinburgh slept on the sofa because the bed frame bolts were in a box I never labelled; Amazon Prime next-day dropped replacements for £12.", "problem", "personal", False,
     [("Edinburgh", "place"), ("bed frame bolts", "tool"), ("Amazon Prime", "service")],
     [],
     "what went wrong on the first night and what quick fix saved it",
     "first night sleep sofa bolts lost label next day delivery price fix"),
    # --- 27 ---
    ("Prefers a walk-through with the outgoing tenant over the agent-only handover; in the Warriston flat Liam flagged the radiator bleed key under the fridge.", "preference", "personal", False,
     [("outgoing tenant", "person"), ("agent-only handover", "method"), ("Warriston", "place"), ("Liam", "person"), ("radiator bleed key", "tool")],
     [("outgoing tenant", "agent-only handover", "PREFERS")],
     "which handover style wins and what detail did it surface",
     "handover walkthrough tenant over agent radiator key location discover"),
    # --- 28 ---
    ("Arranged the council tax move on 2026-04-11: closed the Bristol account, opened the Edinburgh single-person discount application, saved £42 a month.", "fact", "personal", False,
     [("council tax", "concept"), ("2026-04-11", "date"), ("Bristol", "place"), ("Edinburgh", "place"), ("single-person discount", "concept")],
     [],
     "when did I sort the council-tax move and what did it save",
     "council tax transfer date close open discount application saving month"),
    # --- 29 ---
    ("Chose the ground-floor Warriston flat over the third-floor Marchmont one; no lift, bad knee, and the cat carrier plus the grocery shop made the stairs a weekly ordeal.", "decision", "personal", False,
     [("Warriston", "place"), ("Marchmont", "place"), ("lift", "infrastructure"), ("cat carrier", "tool")],
     [("Warriston", "Marchmont", "PREFERS")],
     "which floor of flat won out and what drove the lift-free decision",
     "flat floor pick ground over third no lift knee cat grocery stairs"),
    # --- 30 ---
    ("Prefers a twelve-week notice period to a four-week one; selling furniture, timing the new lease, and booking movers all need runway the short window kills.", "preference", "personal", False,
     [("twelve-week notice period", "concept"), ("four-week", "concept"), ("furniture", "infrastructure"), ("lease", "concept")],
     [("twelve-week notice period", "four-week", "PREFERS")],
     "which notice length wins for a move and why",
     "notice period long over short sell furniture line up lease movers"),
    # --- 31 ---
    ("The offer on 9 Warriston Crescent went in at £245,000 against a £255,000 asking on 2026-03-25; Home Report flagged a damp patch in the bathroom wall.", "decision", "personal", False,
     [("9 Warriston Crescent", "place"), ("2026-03-25", "date"), ("Home Report", "tool"), ("bathroom wall", "infrastructure")],
     [],
     "when did the offer go in and what justified the below-asking number",
     "offer price asking below date report finding damp bathroom leverage"),
    # --- 32 ---
    ("The change-of-address list ran to 23 organisations; bank, HMRC, DVLA, GP, dentist, three subscription boxes, six retailers, and Mum's address book update last.", "reference", "personal", False,
     [("HMRC", "organization"), ("DVLA", "organization"), ("GP", "organization"), ("dentist", "organization"), ("Mum", "person")],
     [],
     "how many places had to get the new address and who was the last on the list",
     "address change list count HMRC DVLA GP dentist subs retailer final"),
    # --- 33 ---
    ("Chose the self-drive Luton van over a man-with-a-van service for the Guildford-to-London leg; Enterprise rental £85, fuel £40, two friends and pizza for the unload.", "decision", "personal", False,
     [("Luton van", "tool"), ("man-with-a-van", "service"), ("Guildford", "place"), ("London", "place"), ("Enterprise", "organization"), ("pizza", "food")],
     [("Luton van", "man-with-a-van", "PREFERS")],
     "which move method beat the hired-crew option for the short hop and what did it cost",
     "self drive van over hired crew short move rental fuel friends pizza"),
    # --- 34. noise ---
    ("Actually, leave those two together — they were sitting next to each other before.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The Warriston inventory check-in took ninety minutes on 2026-04-11; 47 photos, six flagged scuffs, the agent noted the dishwasher as beyond economic repair.", "reference", "personal", False,
     [("Warriston", "place"), ("2026-04-11", "date"), ("inventory", "tool"), ("dishwasher", "infrastructure")],
     [("inventory", "Warriston", "LOCATED_IN")],
     "how did the move-in inventory go and what was the headline flag",
     "check in duration photo count scuff flag dishwasher condition note"),
    # --- 36 ---
    ("Replaced Zoopla with Rightmove for the serious hunt after the Zoopla listings lagged three to five days behind; found 9 Warriston on Rightmove within an hour of listing.", "decision", "personal", False,
     [("Zoopla", "platform"), ("Rightmove", "platform"), ("9 Warriston", "place")],
     [("Rightmove", "Zoopla", "REPLACES")],
     "which property portal took over for the active search and why",
     "portal swap laggy to fresh days delay winning listing speed find"),
    # --- 37 ---
    ("Prefers unpacking the bathroom box before the bedroom one; a working shower on night one does more for morale than perfect sheets on a half-made bed.", "preference", "personal", False,
     [("bathroom box", "tool"), ("bedroom", "place"), ("shower", "infrastructure"), ("sheets", "tool")],
     [("bathroom box", "bedroom", "PREFERS")],
     "which unpack order wins on night one and why",
     "unpack order bathroom over bedroom first shower morale sheets waiting"),
    # --- 38 ---
    ("The mortgage in principle from Halifax came through at £185,000 on 2026-03-01; 4.64% five-year fix, which set the ceiling for every viewing after.", "fact", "personal", False,
     [("Halifax", "organization"), ("2026-03-01", "date"), ("mortgage in principle", "concept"), ("five-year fix", "concept")],
     [("mortgage in principle", "Halifax", "AUTHORED_BY")],
     "when did the borrowing headroom get set and what shape did it take",
     "MIP lender date ceiling rate fix term viewings constraint budget"),
    # --- 39 ---
    ("Cross-country drive pit stops are non-negotiable: coffee at two hours, lunch at four, legs-out walk at six; the 2026-03-22 Austin-to-Denver run proved it.", "architecture", "personal", False,
     [("Austin", "place"), ("Denver", "place"), ("2026-03-22", "date"), ("coffee", "food"), ("lunch", "food")],
     [],
     "how do I pace the long-haul moving drive",
     "drive pace stop cadence coffee lunch walk hours rule long haul"),
    # --- 40 ---
    ("Chose Store First self-storage in Bristol for a ten-week bridge on 2026-04-10; £68 a month for a 35-square-foot unit, twenty-four hour access, a five-minute detour off the M32.", "decision", "personal", False,
     [("Store First", "organization"), ("Bristol", "place"), ("2026-04-10", "date"), ("M32", "infrastructure")],
     [("Store First", "Bristol", "LOCATED_IN")],
     "which storage bridge did I pick between homes and what were the terms",
     "self storage firm bridge weeks rent size access motorway detour"),
    # --- 41 ---
    ("Prefers negotiating rent in person at the viewing over email follow-ups; in-person got the Warriston rent from £1,250 to £1,180 on the spot.", "preference", "personal", False,
     [("viewing", "event"), ("email", "service"), ("Warriston", "place")],
     [("viewing", "email", "PREFERS")],
     "which rent-haggle channel wins and what did it save on the new flat",
     "rent negotiate viewing over email live drop amount spot concession"),
    # --- 42 ---
    ("The Bristol-to-Lisbon international move used a 20-foot shipping container through Allied Van Lines; quoted £4,800, three-week transit, end-of-May door-to-door.", "architecture", "personal", False,
     [("Bristol", "place"), ("Lisbon", "place"), ("Allied Van Lines", "organization"), ("shipping container", "tool"), ("May", "date")],
     [],
     "how is the international move structured and what are the numbers",
     "international container firm size transit weeks price month door"),
    # --- 43 ---
    ("Took the first-impression walk around Morningside on 2026-04-12: butcher on the corner, independent bookshop two doors down, a park off the high street.", "fact", "personal", False,
     [("Morningside", "place"), ("2026-04-12", "date"), ("butcher", "organization"), ("bookshop", "place"), ("park", "place")],
     [],
     "what did the first neighbourhood scout turn up right after moving in",
     "first walk district butcher bookshop park corner high street take"),
    # --- 44 ---
    ("Prefers a Monday move-in to a Friday one; everything is open, admin offices answer the phone, the new gym signs you up the same day, recovery weekend follows.", "preference", "personal", False,
     [("Monday", "date"), ("Friday", "date"), ("admin offices", "organization"), ("gym", "place")],
     [("Monday", "Friday", "PREFERS")],
     "which weekday for move-in beats the others and what does it unlock",
     "move in weekday monday over friday open admin gym sign weekend rest"),
    # --- 45 ---
    ("The Redland sale completed on 2026-05-20 at £272,000 through Ocean Estate Agents; Jules drove the buyer side hard and chipped £3,000 off the asking at the last minute.", "milestone", "personal", False,
     [("Redland", "place"), ("2026-05-20", "date"), ("Ocean Estate Agents", "organization"), ("Jules", "person")],
     [("Ocean Estate Agents", "Redland", "RELATED_TO")],
     "when did the sale close and who ran the transaction",
     "sale completion date amount agent named buyer side haggle cut"),
    # --- 46 ---
    ("Packed books last on 2026-04-06 because the full boxes got heavy fast; at 18 kg per book box the movers appreciated the per-box cap.", "fact", "personal", False,
     [("books", "tool"), ("2026-04-06", "date"), ("boxes", "tool"), ("movers", "person")],
     [],
     "what was the packing rule for the heaviest category and why",
     "book pack last weight cap per box mover ergonomics date"),
    # --- 47 ---
    ("Chose Anglian Removals over Pickfords for the Norwich-to-Leeds leg on 2026-02-16; smaller firm, quoted £280 less, owner-operator showed up himself on the day.", "decision", "personal", False,
     [("Anglian Removals", "organization"), ("Pickfords", "organization"), ("Norwich", "place"), ("Leeds", "place"), ("2026-02-16", "date"), ("owner-operator", "person")],
     [("Anglian Removals", "Pickfords", "PREFERS")],
     "which mover beat the bigger name for that relocation and what sealed it",
     "mover small firm over national quote lower owner on site day date"),
    # --- 48 ---
    ("Prefers viewing on Saturday mornings to weekday evenings; natural light reveals the mould and the street traffic context that the evening viewings always softened.", "preference", "personal", False,
     [("Saturday mornings", "date"), ("weekday evenings", "date"), ("mould", "finding"), ("street traffic", "concept")],
     [("Saturday mornings", "weekday evenings", "PREFERS")],
     "which viewing time slot wins and what does it reveal",
     "viewing time morning weekend over evening weekday light mould traffic"),
    # --- 49 ---
    ("Set up a new-home first-week grocery list: olive oil, salt, eggs, bread, tea, milk, pasta, one vegetable, lemons, a bottle of wine for the first dinner.", "reference", "personal", False,
     [("olive oil", "food"), ("salt", "food"), ("eggs", "food"), ("bread", "food"), ("tea", "food"), ("milk", "food"), ("pasta", "food"), ("lemons", "food"), ("wine", "food")],
     [],
     "what goes on the first-week shopping list after moving",
     "first week grocery staple list oil salt egg bread tea milk wine list"),
    # --- 50 ---
    ("Hired Zen Movers for the final Edinburgh in-city shuffle from Leith to Morningside on 2026-06-03 after a lease swap; two hours, £140 flat, no stairs on either end.", "milestone", "personal", False,
     [("Zen Movers", "organization"), ("Edinburgh", "place"), ("Leith", "place"), ("Morningside", "place"), ("2026-06-03", "date")],
     [("Zen Movers", "Edinburgh", "LOCATED_IN")],
     "when did the short in-city mover run happen and what was the scope",
     "in city mover short hop lease swap date duration flat fee no stairs"),
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
