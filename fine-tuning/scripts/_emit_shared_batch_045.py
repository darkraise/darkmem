"""One-off emitter for shared-base batch-045 — personal domain (volunteering / community / civic life / local engagement slice).

Writes 50 rows to data/v2/shared/batch_045.tmp.jsonl with ids shared-02201..02250.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_045.tmp.jsonl"
ID_OFFSET = 2200

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The food-bank rotation at Trussell Harbourside runs every second Saturday from 08:30 to 12:00, sorting donations before the queue opens.", "architecture", "personal", False,
     [("Trussell Harbourside", "organization"), ("Saturday", "date"), ("donations", "concept")],
     [("Trussell Harbourside", "donations", "RELATED_TO")],
     "how is the fortnightly soup-kitchen shift structured across the morning",
     "food bank biweekly shift sort donations queue time window"),
    # --- 2 ---
    ("Signed up as a poll worker for the 2026-05-07 local elections at the Elmwood Library precinct after a pitch from the clerk at a town hall.", "milestone", "personal", False,
     [("poll worker", "activity"), ("2026-05-07", "date"), ("Elmwood Library", "place"), ("town hall", "event")],
     [],
     "when did I commit to staffing the ballot booth and at which venue",
     "election day volunteer enroll library precinct clerk recruit date"),
    # --- 3 ---
    ("The neighbourhood association meeting moved from the school hall to the parish room on 2026-03-11; quieter room, better coffee, worse parking.", "fact", "personal", False,
     [("neighbourhood association", "organization"), ("school hall", "place"), ("parish room", "place"), ("2026-03-11", "date")],
     [("parish room", "school hall", "REPLACES")],
     "when did the street committee change its meeting venue and what was the trade-off",
     "resident group meeting room swap quieter parking tradeoff date"),
    # --- 4 ---
    ("Prefers the Meals on Wheels Tuesday route over the Friday one; the Tuesday list has six stops instead of nine and ends before school pickup.", "preference", "personal", False,
     [("Meals on Wheels", "organization"), ("Tuesday", "date"), ("Friday", "date"), ("school pickup", "event")],
     [("Tuesday", "Friday", "PREFERS")],
     "which weekday meal-delivery run wins out and why",
     "meals on wheels route choice fewer stops earlier finish school run"),
    # --- 5 ---
    ("Chaired the first HOA meeting on 2026-02-18 after Margaret stepped down; pushed through the bin-store rebuild vote on the same night.", "milestone", "personal", False,
     [("HOA", "organization"), ("2026-02-18", "date"), ("Margaret", "person"), ("bin-store", "infrastructure")],
     [],
     "when did I take the residents'-board chair and what got decided first",
     "homeowners association chair handover first meeting bin store vote"),
    # --- 6 ---
    ("The community garden plot at Allenby Fields is bed 14, eight square metres, shared with Dev and cropped on a three-sister rotation.", "reference", "personal", False,
     [("Allenby Fields", "place"), ("bed 14", "place"), ("Dev", "person"), ("three-sister rotation", "method")],
     [("bed 14", "Allenby Fields", "LOCATED_IN"), ("three-sister rotation", "bed 14", "RELATED_TO")],
     "where is the shared allotment patch and who do I grow it with",
     "community garden plot number shared partner rotation layout"),
    # --- 7 ---
    ("Switched canvassing shifts from door-knock to phone-bank for the council byelection; two bad knees made the estate stairs a no-go.", "decision", "personal", False,
     [("canvassing", "activity"), ("door-knock", "method"), ("phone-bank", "method"), ("council byelection", "event")],
     [("phone-bank", "door-knock", "REPLACES")],
     "which volunteer-outreach method took over from the walking one and why",
     "canvass swap phone calls over doors knee issue estate stairs reason"),
    # --- 8 ---
    ("The charity 5k on 2026-06-13 needs 22 marshals; four corner stations, two water tables, one lead bike, the rest on the route.", "architecture", "personal", False,
     [("charity 5k", "event"), ("2026-06-13", "date"), ("marshals", "person"), ("lead bike", "tool")],
     [],
     "how are the race-day stewards laid out for the fundraiser run",
     "5k race marshals plan corner water lead bike headcount distribution"),
    # --- 9 ---
    ("The new-baby meal train for Priya's family runs 2026-04-20 through 2026-05-11; fourteen slots, vegetarian only, no nuts, drop-offs at the porch.", "architecture", "personal", False,
     [("meal train", "event"), ("Priya", "person"), ("2026-04-20", "date"), ("2026-05-11", "date"), ("porch", "place")],
     [],
     "how is the postpartum food-rota set up and what are the constraints",
     "meal train new parent vegetarian allergy porch drop date range"),
    # --- 10. noise ---
    ("Let me double-check the sign-up sheet before we finalise.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("The Habitat for Humanity build day on 2026-03-28 ran short on framing nails by noon; the site lead now keeps a spare 9 kg box in the van.", "problem", "personal", False,
     [("Habitat for Humanity", "organization"), ("2026-03-28", "date"), ("framing nails", "tool"), ("site lead", "person")],
     [],
     "what ran out on the affordable-housing volunteer day and what change followed",
     "habitat build day nail shortage site lead van spare box fix"),
    # --- 12 ---
    ("Prefers the animal-shelter cat room over the dog kennels on Saturday shifts; quieter for the socialisation work I actually enjoy.", "preference", "personal", False,
     [("animal-shelter", "organization"), ("cat room", "place"), ("dog kennels", "place"), ("Saturday", "date")],
     [("cat room", "dog kennels", "PREFERS")],
     "which wing of the animal refuge wins for the weekend slot and why",
     "shelter volunteer cat area quieter socialisation over dog noise"),
    # --- 13 ---
    ("The ESL tutoring pair-up through Harbourside Community Centre matches me with Osman every Thursday at 19:00 for an hour.", "reference", "personal", False,
     [("ESL tutoring", "activity"), ("Harbourside Community Centre", "organization"), ("Osman", "person"), ("Thursday", "date")],
     [("ESL tutoring", "Harbourside Community Centre", "LOCATED_IN")],
     "who do I tutor in English through the community centre and when",
     "ESL tutoring pairing partner weekly evening community centre hour"),
    # --- 14 ---
    ("Took over the Little Free Library on Marlow Avenue after Jim moved away; check stock Sundays and seal the door hinge each spring.", "milestone", "personal", False,
     [("Little Free Library", "infrastructure"), ("Marlow Avenue", "place"), ("Jim", "person"), ("Sundays", "date"), ("spring", "date")],
     [("Little Free Library", "Marlow Avenue", "LOCATED_IN")],
     "when did the street book-box become my responsibility and what is the routine",
     "little free library stewardship handover weekly check hinge seal"),
    # --- 15 ---
    ("The mutual-aid pod for Ward 7 runs a signal thread of 41 neighbours; winter storm cover is assigned by odd and even house numbers.", "architecture", "personal", False,
     [("mutual-aid pod", "organization"), ("Ward 7", "place"), ("signal thread", "tool"), ("winter storm", "event")],
     [("mutual-aid pod", "Ward 7", "LOCATED_IN")],
     "how is the district neighbour-help group organised for severe weather",
     "mutual aid pod ward thread size winter cover odd even roster"),
    # --- 16 ---
    ("The hospice volunteer induction at St Bede's on 2026-01-22 covered safeguarding, manual handling, and the two-visitor rule; three hours, four forms.", "reference", "personal", False,
     [("hospice", "organization"), ("St Bede's", "organization"), ("2026-01-22", "date"), ("safeguarding", "field"), ("manual handling", "method")],
     [],
     "what did the end-of-life volunteer onboarding at the hospice cover",
     "hospice induction safeguarding moving lifting two visitor rule forms"),
    # --- 17 ---
    ("Chose the Friends of Stanpit Marsh conservation group over the wider Wildlife Trust; the work days are closer and tree-planting is the bulk of it.", "decision", "personal", False,
     [("Friends of Stanpit Marsh", "organization"), ("Wildlife Trust", "organization"), ("tree-planting", "activity")],
     [("Friends of Stanpit Marsh", "Wildlife Trust", "PREFERS")],
     "which conservation group won out over the regional one and why",
     "friends of marsh local over wildlife trust tree planting proximity"),
    # --- 18 ---
    ("The book drive for St Mary's Primary collected 612 titles by 2026-03-31, over the 500 target; the PTA kept the overflow for the summer fair raffle.", "milestone", "personal", False,
     [("book drive", "event"), ("St Mary's Primary", "organization"), ("2026-03-31", "date"), ("PTA", "organization"), ("summer fair", "event")],
     [],
     "when did the school literature collection close and how did it do against target",
     "book drive tally target beat school PTA raffle overflow date"),
    # --- 19 ---
    ("The tree-planting day on 2026-02-07 put 240 whips into the brook corridor; volunteers were told to back-fill and tread, never stamp, the root balls.", "fact", "personal", False,
     [("tree-planting", "activity"), ("2026-02-07", "date"), ("brook corridor", "place"), ("root balls", "concept")],
     [],
     "when was the sapling planting and how many went into the stream corridor",
     "tree planting day count corridor whip backfill tread technique"),
    # --- 20 ---
    ("Attended the town council office-hour on 2026-03-04 to push for the parking-free Sunday block on Cheviot Row; got three councillors to co-sign.", "milestone", "personal", False,
     [("town council", "organization"), ("2026-03-04", "date"), ("Cheviot Row", "place"), ("councillors", "person")],
     [],
     "when did I lobby for the car-free Sunday street and what came of it",
     "town council surgery parking free sunday co-sign councillors date"),
    # --- 21 ---
    ("The blood donation cadence held up in 2025: four sessions at Westfield Centre, all on Tuesday evenings, all whole-blood not platelets.", "fact", "personal", False,
     [("blood donation", "activity"), ("2025", "date"), ("Westfield Centre", "place"), ("Tuesday", "date"), ("whole-blood", "concept"), ("platelets", "concept")],
     [("whole-blood", "platelets", "PREFERS")],
     "how many donation sessions did I hit last year and in what setting",
     "blood donation count venue evening weekday whole blood not platelet"),
    # --- 22 ---
    ("The park clean-up is first Saturday of the month at Queensdown Meadow; bring a picker, claim a grid square, end at the bandstand for tea.", "architecture", "personal", False,
     [("park clean-up", "event"), ("Saturday", "date"), ("Queensdown Meadow", "place"), ("bandstand", "place")],
     [("park clean-up", "Queensdown Meadow", "LOCATED_IN")],
     "how is the monthly green-space litter pick organised and where does it finish",
     "park cleanup first saturday meadow grid square bandstand finish"),
    # --- 23 ---
    ("The library friends group membership renewed on 2026-01-09 at £25 for the year; covers voting rights at the AGM and early notice on used-book sales.", "fact", "personal", False,
     [("library friends group", "organization"), ("2026-01-09", "date"), ("AGM", "event"), ("used-book sales", "event")],
     [],
     "when did I renew the library supporter subscription and what does it unlock",
     "friends of library dues renewal year AGM vote book sale preview"),
    # --- 24 ---
    ("Prefers paper sign-in sheets to the QR code at the community centre; older regulars were getting locked out of the volunteer log.", "preference", "personal", False,
     [("paper sign-in sheets", "tool"), ("QR code", "tool"), ("community centre", "place"), ("volunteer log", "tool")],
     [("paper sign-in sheets", "QR code", "PREFERS")],
     "which attendance-tracking method wins at the community hub and why",
     "sign in sheet paper over QR accessibility older volunteer lockout"),
    # --- 25 ---
    ("The HOA bin-store rebuild budget came in at £3,200 on 2026-03-05; three quotes, Rambridge Joinery was the median and landed the job.", "decision", "personal", False,
     [("HOA", "organization"), ("bin-store", "infrastructure"), ("2026-03-05", "date"), ("Rambridge Joinery", "organization")],
     [],
     "when did the refuse shed contract land and which builder took it",
     "HOA bin store quote median tender joiner pick budget date"),
    # --- 26 ---
    ("The canvassing clipboard kit is kept in the hall cupboard: 30 door-hanger leaflets, two high-vis vests, one clicker, spare biros in the ziplock.", "reference", "personal", False,
     [("canvassing", "activity"), ("hall cupboard", "place"), ("door-hanger leaflets", "tool"), ("high-vis vests", "tool"), ("clicker", "tool"), ("biros", "tool")],
     [("canvassing", "hall cupboard", "LOCATED_IN")],
     "where do I keep the volunteer-outreach gear and what is in the kit",
     "canvassing kit cupboard leaflets vests clicker pens ziplock inventory"),
    # --- 27 ---
    ("The town-hall attendance log for 2025 hit eight of twelve meetings; missed February, June, August, October for work travel.", "fact", "personal", False,
     [("town-hall", "event"), ("2025", "date"), ("February", "date"), ("June", "date"), ("August", "date"), ("October", "date")],
     [],
     "how often did I make the civic meetings last year and which did I miss",
     "town hall attendance count missed months travel conflict year"),
    # --- 28 ---
    ("The block-party bylaws at 36 Acacia Drive require a 23:00 music cut-off, two no-alcohol tables, and a pedestrian lane kept open across the close.", "reference", "personal", False,
     [("block-party", "event"), ("36 Acacia Drive", "place"), ("music cut-off", "concept"), ("pedestrian lane", "infrastructure")],
     [],
     "what are the ground rules for the street party we host and where",
     "block party rules music curfew dry tables pedestrian path address"),
    # --- 29 ---
    ("Switched from Amnesty local group letter-writing to the climate-justice chapter after 2025-11; the letters felt rote and the climate briefings were sharper.", "decision", "personal", False,
     [("Amnesty", "organization"), ("letter-writing", "activity"), ("climate-justice chapter", "organization"), ("2025-11", "date")],
     [("climate-justice chapter", "Amnesty", "REPLACES")],
     "which campaigning group replaced the human-rights letter nights and why",
     "amnesty letters swap climate chapter sharper briefing late 2025"),
    # --- 30 ---
    ("The ballot measure Prop 14 research binder lives in the kitchen drawer: pro sheet, con sheet, funding map, my margin notes from the library teach-in.", "reference", "personal", False,
     [("Prop 14", "concept"), ("kitchen drawer", "place"), ("pro sheet", "tool"), ("con sheet", "tool"), ("funding map", "tool"), ("teach-in", "event")],
     [("Prop 14", "kitchen drawer", "LOCATED_IN")],
     "where is the local ballot-question research kept and what is inside it",
     "prop 14 binder drawer pro con funding map library teach in notes"),
    # --- 31 ---
    ("Prefers the time-bank hour-swap over cash-paying the handyman; Raul fixed the side gate, I taught his son piano for three weeks.", "preference", "personal", False,
     [("time-bank", "organization"), ("hour-swap", "method"), ("handyman", "person"), ("Raul", "person"), ("piano", "hobby")],
     [("time-bank", "handyman", "PREFERS")],
     "which neighbourly barter pattern won over straight cash work and how",
     "time bank hour swap handyman cash alternative gate piano trade"),
    # --- 32 ---
    ("The neighbour-coordinator role during the 2026-01-12 storm meant checking on 14 households on the east side of the block within two hours.", "milestone", "personal", False,
     [("neighbour-coordinator", "person"), ("2026-01-12", "date"), ("east side", "place")],
     [],
     "what did the storm-day co-ordinator role actually cover and how fast",
     "storm coordinator east side household check count time bound"),
    # --- 33 ---
    ("Chose the Saturday slot over the Sunday slot at the community garden; the Saturday group does the hard dig-over and the Sunday group just does watering.", "decision", "personal", False,
     [("community garden", "place"), ("Saturday", "date"), ("Sunday", "date"), ("dig-over", "activity"), ("watering", "activity")],
     [("Saturday", "Sunday", "PREFERS")],
     "which garden-workday pick wins out and what makes the difference",
     "community garden saturday over sunday heavier work watering tradeoff"),
    # --- 34. noise ---
    ("One second, I'll grab the clipboard from the car.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The PTA treasurer handover on 2026-02-25 included the Barclays account, the petty-cash tin, and a binder of 2024 receipts Marianne had kept spotless.", "milestone", "personal", False,
     [("PTA", "organization"), ("2026-02-25", "date"), ("Barclays", "organization"), ("petty-cash tin", "tool"), ("Marianne", "person")],
     [],
     "when did the parent-council finance handover happen and what came across",
     "PTA treasurer handover account petty cash receipts binder date"),
    # --- 36 ---
    ("The petition for Cheviot Row parking-free blocks hit 312 signatures by 2026-04-10, clearing the council trigger threshold of 250.", "milestone", "personal", False,
     [("petition", "goal"), ("Cheviot Row", "place"), ("2026-04-10", "date"), ("council", "organization")],
     [],
     "when did the street-calming petition clear the threshold and by how much",
     "petition signature count trigger threshold council pass margin date"),
    # --- 37 ---
    ("The community garden compost bay lives at the back of Allenby Fields by the water butt; turn it every fortnight, never add citrus peel.", "reference", "personal", False,
     [("compost bay", "infrastructure"), ("Allenby Fields", "place"), ("water butt", "tool"), ("citrus peel", "food"), ("fortnight", "date")],
     [("compost bay", "Allenby Fields", "LOCATED_IN")],
     "where is the allotment rot-bin sited and what is the turn rule",
     "compost bay allotment back water butt fortnight turn no citrus"),
    # --- 38 ---
    ("Prefers the library teach-ins on ballot measures to the Facebook group threads; the librarian keeps it civil and the handouts cite sources.", "preference", "personal", False,
     [("library teach-ins", "event"), ("ballot measures", "concept"), ("Facebook group", "platform"), ("librarian", "person")],
     [("library teach-ins", "Facebook group", "PREFERS")],
     "which civic-learning channel wins over the online one for voting research",
     "library teach in over facebook group ballot measure civility citation"),
    # --- 39 ---
    ("The hospice shift pattern is two three-hour visits a week with the same patient where possible; continuity matters more than total hours.", "architecture", "personal", False,
     [("hospice", "organization"), ("shift pattern", "method"), ("continuity", "concept")],
     [],
     "how are the end-of-life volunteer visits structured and why",
     "hospice shift pattern twice weekly three hour same patient continuity"),
    # --- 40 ---
    ("Replaced the paper volunteer rota at the food bank with a shared Google Sheet on 2026-02-02; no-show rate halved in the first month.", "decision", "personal", False,
     [("paper volunteer rota", "tool"), ("food bank", "organization"), ("Google Sheet", "tool"), ("2026-02-02", "date")],
     [("Google Sheet", "paper volunteer rota", "REPLACES")],
     "which scheduling tool took over at the food bank and what did it shift",
     "volunteer rota swap paper to sheet no show rate drop first month"),
    # --- 41 ---
    ("The Bluecoat tutoring programme at Harbourside pairs tutors with adult learners on a six-week cycle; I'm on my fourth cycle with Osman.", "fact", "personal", False,
     [("Bluecoat tutoring programme", "organization"), ("Harbourside", "place"), ("Osman", "person"), ("six-week cycle", "concept")],
     [("Bluecoat tutoring programme", "Harbourside", "LOCATED_IN")],
     "which tutoring scheme runs at the community hub and how are learners matched",
     "bluecoat tutoring six week cycle adult learner pairing count"),
    # --- 42 ---
    ("Chose the daytime mutual-aid prescription-run over the evening food-drop rota; pharmacies close before the evening shift would have hit them.", "decision", "personal", False,
     [("mutual-aid", "organization"), ("prescription-run", "activity"), ("food-drop rota", "activity"), ("pharmacies", "place")],
     [("prescription-run", "food-drop rota", "PREFERS")],
     "which mutual-aid task won out and why the scheduling forced it",
     "mutual aid day prescription run over evening food drop pharmacy hours"),
    # --- 43 ---
    ("Prefers the March clean-up to the September one at Queensdown Meadow; the March haul uncovers what the winter hid but the ground is still firm.", "preference", "personal", False,
     [("March", "date"), ("September", "date"), ("Queensdown Meadow", "place")],
     [("March", "September", "PREFERS")],
     "which park litter pick month beats the other for hauls and footing",
     "park cleanup march over september winter debris firm ground reason"),
    # --- 44 ---
    ("The neighbourhood association budget for 2026 is £4,800: £2,200 for the bin-store rebuild, £1,400 for the summer fete, £1,200 contingency.", "reference", "personal", False,
     [("neighbourhood association", "organization"), ("2026", "date"), ("bin-store", "infrastructure"), ("summer fete", "event")],
     [],
     "how is the residents'-group annual budget split across the big-ticket items",
     "residents group budget line items bin store fete contingency year"),
    # --- 45 ---
    ("The mutual-aid signal thread broke on 2026-01-30 when the admin phone died mid-storm; rotated admin rights to three people as a standing rule.", "problem", "personal", False,
     [("mutual-aid", "organization"), ("signal thread", "tool"), ("2026-01-30", "date"), ("admin", "person")],
     [],
     "what communications failure hit the neighbour-help chat during the storm and what fixed it",
     "signal thread admin single point failure storm rotation rule fix date"),
    # --- 46 ---
    ("The school governor application to St Mary's Primary went in on 2026-04-06; two references from Priya and Raul, DBS already current.", "milestone", "personal", False,
     [("school governor", "person"), ("St Mary's Primary", "organization"), ("2026-04-06", "date"), ("Priya", "person"), ("Raul", "person"), ("DBS", "concept")],
     [],
     "when did the primary-school board application go in and who backed it",
     "school governor application references DBS check primary date"),
    # --- 47 ---
    ("Prefers the paper blood-donation appointment card over the NHS Give Blood app; the card sits in the wallet and never logs me out before a session.", "preference", "personal", False,
     [("paper blood-donation appointment card", "tool"), ("NHS Give Blood app", "tool"), ("wallet", "place")],
     [("paper blood-donation appointment card", "NHS Give Blood app", "PREFERS")],
     "which donation-appointment reminder wins out and why",
     "blood donation card over app wallet logout reliability session"),
    # --- 48 ---
    ("The ward councillor surgery runs the first Tuesday of the month at The Crown pub back room, 18:00 to 19:30, walk-in only.", "reference", "personal", False,
     [("ward councillor", "person"), ("Tuesday", "date"), ("The Crown", "place")],
     [("ward councillor", "The Crown", "LOCATED_IN")],
     "when and where does my local elected rep hold open hours",
     "elected rep drop-in evening venue pub monthly cadence walk-in format"),
    # --- 49 ---
    ("The charity 5k organising committee meets every Wednesday at 19:30 at the rugby clubhouse; ten weeks out from race day, everyone has two jobs.", "architecture", "personal", False,
     [("charity 5k", "event"), ("Wednesday", "date"), ("rugby clubhouse", "place")],
     [("charity 5k", "rugby clubhouse", "LOCATED_IN")],
     "how does the fundraiser run planning group operate in the final stretch",
     "5k organising committee weekly meet clubhouse ten weeks two jobs"),
    # --- 50 ---
    ("The blood-donation appointment on 2026-04-25 at Westfield Centre is booked for 17:40; iron level was fine at the last session, no need to load up on spinach.", "fact", "personal", False,
     [("blood-donation", "activity"), ("2026-04-25", "date"), ("Westfield Centre", "place"), ("iron level", "finding"), ("spinach", "food")],
     [],
     "when is the next donation slot booked and do I need to prep for iron this time",
     "blood donation booking date venue time iron level prior no spinach"),
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
