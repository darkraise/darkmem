"""One-off emitter for shared-base batch-030 — personal domain (home / garden / DIY / repair / property slice).

Writes 50 rows to data/v2/shared/batch_030.tmp.jsonl with ids shared-01451..01500.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_030.tmp.jsonl"
ID_OFFSET = 1450

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The kitchen renovation is split into three phases: demolition in May, cabinetry in July, countertop fitting in September.", "architecture", "personal", False,
     [("kitchen renovation", "project"), ("demolition", "event"), ("cabinetry", "event"), ("countertop fitting", "event"), ("July", "date"), ("September", "date")],
     [],
     "how is the cooking-room overhaul structured across the calendar year",
     "cook-space remodel staged three-step calendar layout"),
    # --- 2 ---
    ("Chose the heat pump over a replacement gas boiler on 2026-03-15; the grant covered a third and running costs were lower on the model.", "decision", "personal", False,
     [("heat pump", "tool"), ("gas boiler", "tool"), ("2026-03-15", "date")],
     [("heat pump", "gas boiler", "REPLACES")],
     "which heating appliance won out over the fossil-fuel unit and on what date",
     "electrified heating swap combustion unit subsidy date choice"),
    # --- 3 ---
    ("The upstairs tap drip turned out to be a worn ceramic cartridge, not the washer I spent an hour replacing first.", "problem", "personal", False,
     [("upstairs tap", "infrastructure"), ("ceramic cartridge", "tool"), ("washer", "tool")],
     [("ceramic cartridge", "washer", "REPLACES")],
     "what part was actually leaking in the first-floor faucet after the wrong fix",
     "bathroom faucet drip cartridge root cause mis-diagnosis seal"),
    # --- 4 ---
    ("Prefers Farrow & Ball Skimming Stone for the hallway over the builder's magnolia; three coats cover without flashing.", "preference", "personal", False,
     [("Farrow & Ball", "organization"), ("Skimming Stone", "concept"), ("hallway", "place"), ("magnolia", "concept")],
     [("Skimming Stone", "magnolia", "PREFERS")],
     "which paint shade took over the corridor from the default builder's off-white",
     "premium interior paint warm neutral default cream swap corridor"),
    # --- 5 ---
    ("Completed the loft insulation top-up on 2026-02-28; raised the rating from D to C and the upstairs bedroom finally held warmth.", "milestone", "personal", False,
     [("loft insulation", "tool"), ("2026-02-28", "date"), ("upstairs bedroom", "place")],
     [],
     "when did the attic thermal upgrade finish and what grade did it shift",
     "roof cavity insulation boost rating bump warm upstairs outcome"),
    # --- 6 ---
    ("The raised bed layout in the back plot runs three two-metre frames along the south fence with a gravel path between them.", "architecture", "personal", False,
     [("raised bed", "method"), ("back plot", "place"), ("south fence", "place"), ("gravel path", "infrastructure")],
     [("raised bed", "back plot", "LOCATED_IN")],
     "how are the grow boxes arranged along the rear boundary with the walkway",
     "vegetable frame layout south-facing fence path between"),
    # --- 7 ---
    ("Hired Carmichael Electrical for the consumer unit upgrade after two DIY attempts left the downstairs circuit tripping.", "decision", "personal", False,
     [("Carmichael Electrical", "organization"), ("consumer unit", "infrastructure"), ("downstairs circuit", "infrastructure")],
     [("Carmichael Electrical", "consumer unit", "CONFIGURES")],
     "which contractor took over the fuse-box job after failed self-attempts",
     "electrician hire distribution board swap breaker trip handoff"),
    # --- 8 ---
    ("The bathroom retile took eleven days because the existing screed had dipped nine millimetres toward the door.", "problem", "personal", False,
     [("bathroom retile", "project"), ("screed", "tool")],
     [],
     "why did the lavatory tiling project blow out its schedule",
     "washroom tiling delay uneven floor substrate slope issue"),
    # --- 9 ---
    ("The gutter-cleaning routine is twice a year: once in late March after the blossom, once in early November after leaf-fall.", "architecture", "personal", False,
     [("gutter-cleaning", "method"), ("late March", "date"), ("early November", "date")],
     [],
     "how often and when do I clean the roof drainage channels",
     "eaves trough cleaning cadence spring autumn twice annual"),
    # --- 10. noise ---
    ("Let me grab the measuring tape before we continue.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("The Hitachi Airhome 3000 was specced for 8 kW output after the heat-loss survey came in at 6.4 kW including the cold utility room.", "reference", "personal", False,
     [("Hitachi Airhome 3000", "tool"), ("heat-loss survey", "method"), ("utility room", "place")],
     [],
     "which air-source unit model got picked after the thermal load calculation",
     "heat pump sizing survey kilowatt result cold side room"),
    # --- 12 ---
    ("Prefers oil-based decking stain to water-based after two seasons of comparison; the south deck held colour twelve months longer.", "preference", "personal", False,
     [("oil-based decking stain", "tool"), ("water-based", "tool"), ("south deck", "place")],
     [("oil-based decking stain", "water-based", "PREFERS")],
     "which timber-treatment base outperformed the other on the sunny platform",
     "deck finish oil vs water durability south exposure season test"),
    # --- 13 ---
    ("The quote from MPS Solar on 2026-04-05 was £9,800 for 4.2 kWp and a 5 kWh battery; two rival quotes came in within three percent.", "fact", "personal", False,
     [("MPS Solar", "organization"), ("2026-04-05", "date")],
     [],
     "what did the photovoltaic proposal cost and how close were the alternatives",
     "solar installer quote array size storage battery comparison spread"),
    # --- 14 ---
    ("Replaced the old chain-link fence along the east boundary with a 1.8 m closeboard on 2026-01-18; the neighbour agreed to split the cost.", "milestone", "personal", False,
     [("chain-link fence", "tool"), ("east boundary", "place"), ("closeboard", "tool"), ("2026-01-18", "date")],
     [("closeboard", "chain-link fence", "REPLACES")],
     "when did the east-side perimeter fence swap finish and what went up",
     "boundary fence replacement height wire to panel split cost date"),
    # --- 15 ---
    ("The smart thermostat install on 2026-03-02 hit a snag: the old hardwire needed a C-wire adapter before the Ecobee would stay on.", "problem", "personal", False,
     [("smart thermostat", "tool"), ("2026-03-02", "date"), ("C-wire adapter", "tool"), ("Ecobee", "tool")],
     [("Ecobee", "C-wire adapter", "DEPENDS_ON")],
     "what wiring piece did the new climate controller demand mid-install",
     "intelligent thermostat fit issue common wire missing adapter brand"),
    # --- 16 ---
    ("Prefers hand-pruning the three apple trees in February over hiring the tree surgeon; the crown shape stays more natural.", "preference", "personal", False,
     [("hand-pruning", "activity"), ("apple trees", "activity"), ("February", "date"), ("tree surgeon", "person")],
     [("hand-pruning", "tree surgeon", "PREFERS")],
     "which winter fruit-tree maintenance approach won over bringing in a professional",
     "self pruning orchard stone fruit winter month expert avoidance shape"),
    # --- 17 ---
    ("The mower service at Gravelly Hill Motors keeps the Honda HRX running a fourth season; £85 a visit, cheaper than replacing blades.", "reference", "personal", False,
     [("Gravelly Hill Motors", "organization"), ("Honda HRX", "tool")],
     [("Honda HRX", "Gravelly Hill Motors", "LOCATED_IN")],
     "which workshop keeps the rotary cutter running and what does the visit cost",
     "lawn equipment service centre brand keep-alive annual service price"),
    # --- 18 ---
    ("Scrapped the DIY rewire plan after reading the building regs; a notifiable job needs a certified sparks regardless of skill.", "decision", "personal", False,
     [("DIY rewire", "project"), ("building regs", "concept"), ("certified sparks", "person")],
     [("certified sparks", "DIY rewire", "REPLACES")],
     "why did I drop self-rewiring and who took over instead",
     "home electrical rewire regulations qualified electrician handover reason"),
    # --- 19 ---
    ("The compost setup is a three-bay Dalek arrangement behind the shed: fill, turn, mature; each bay cycles roughly sixteen weeks.", "architecture", "personal", False,
     [("compost setup", "method"), ("three-bay Dalek", "pattern"), ("shed", "place")],
     [("three-bay Dalek", "shed", "LOCATED_IN")],
     "how is the garden waste rotting system organised behind the outbuilding",
     "compost bins triple station rotation weeks behind shed layout"),
    # --- 20 ---
    ("Planning permission for the side extension was approved on 2026-02-14 after a first rejection on daylight rights to the neighbour.", "milestone", "personal", False,
     [("Planning permission", "concept"), ("side extension", "project"), ("2026-02-14", "date"), ("neighbour", "person")],
     [],
     "when did the lateral house extension get council sign-off and what had blocked it",
     "local authority approval sidewise addition sunlight objection resolution date"),
    # --- 21 ---
    ("The driveway sealing job on 2026-04-02 took two dry days; the tarmac colour came back by forty percent and the cracks disappeared.", "milestone", "personal", False,
     [("driveway sealing", "method"), ("2026-04-02", "date"), ("tarmac", "tool")],
     [],
     "when did the tar drive refresh happen and how much did it perk the surface",
     "driveway reseal date black top colour return crack close outcome"),
    # --- 22 ---
    ("Chose triple-glazed casements for the north elevation over double; the U-value on the brochure was 0.8 versus 1.3.", "decision", "personal", False,
     [("triple-glazed casements", "tool"), ("north elevation", "place"), ("double", "tool")],
     [("triple-glazed casements", "double", "REPLACES")],
     "which window spec won out on the cold side of the house and why",
     "north side window glass count U-value spec difference choice"),
    # --- 23 ---
    ("The fruit tree pruning schedule is taped inside the shed door: apples in February, plums in July, nothing else until next year.", "reference", "personal", False,
     [("fruit tree", "hobby"), ("shed", "place"), ("apples", "food"), ("plums", "food"), ("February", "date"), ("July", "date")],
     [],
     "where is the orchard trimming calendar kept and what does it cover",
     "pruning calendar fruit months stone fruit summer pome fruit winter"),
    # --- 24 ---
    ("The boiler replacement quote from Anchor Heating was £3,450 for a Worcester 30Si including flue relocation.", "fact", "personal", False,
     [("Anchor Heating", "organization"), ("Worcester 30Si", "tool")],
     [],
     "what did the gas heater quote come to and which model was specced",
     "heating installer estimate combi boiler model flue move inclusive price"),
    # --- 25 ---
    ("Prefers mineral weather-stripping foam to the rubber bulb seals on the back door; the foam compresses without deforming after a winter.", "preference", "personal", False,
     [("mineral weather-stripping foam", "tool"), ("rubber bulb seals", "tool"), ("back door", "place")],
     [("mineral weather-stripping foam", "rubber bulb seals", "PREFERS")],
     "which draught-sealing material wins on the rear entrance after a cold season",
     "draft proofing rear door foam over bulb seal cold season compare"),
    # --- 26 ---
    ("The side gate hinge finally snapped on 2026-01-05 after visible rust for two years; swapped it for stainless at the same time as the latch.", "problem", "personal", False,
     [("side gate", "place"), ("hinge", "tool"), ("2026-01-05", "date"), ("stainless", "tool"), ("latch", "tool")],
     [("stainless", "hinge", "REPLACES")],
     "when did the garden gate pivot give way and what combined upgrade followed",
     "side gate hinge failure corrosion rust steel upgrade latch combo"),
    # --- 27 ---
    ("Refinished the oak floor in the lounge with a water-based matt lacquer on 2026-03-20; three coats, 48-hour cure, dust-free thanks to the HEPA sander.", "milestone", "personal", False,
     [("oak floor", "infrastructure"), ("lounge", "place"), ("water-based matt lacquer", "tool"), ("2026-03-20", "date"), ("HEPA sander", "tool")],
     [],
     "when did the living-room timber floor get redone and what finish went on",
     "oak board refinish living room flat lacquer coats cure dust-free tool"),
    # --- 28 ---
    ("The gardening calendar rule: sow tomatoes indoors on 2026-03-10, harden off from 2026-04-28, plant out after last frost by 2026-05-15.", "architecture", "personal", False,
     [("tomatoes", "food"), ("2026-03-10", "date"), ("2026-04-28", "date"), ("2026-05-15", "date")],
     [],
     "what is the three-date timetable for the nightshade crop this spring",
     "tomato schedule sow harden out plant out dates frost window"),
    # --- 29 ---
    ("The property tax appeal on 2026-02-22 dropped the band from F to E after the comparables list from the neighbour's sale made the case.", "milestone", "personal", False,
     [("property tax", "concept"), ("2026-02-22", "date"), ("neighbour", "person")],
     [],
     "when did the council tax challenge succeed and what evidence carried it",
     "local tax appeal band drop comparable sale neighbour evidence outcome"),
    # --- 30 ---
    ("Tried the no-dig method on the back vegetable bed in 2025; the yield on brassicas doubled versus the rotavated patch last year.", "fact", "personal", False,
     [("no-dig method", "method"), ("back vegetable bed", "place"), ("2025", "date"), ("brassicas", "food"), ("rotavated patch", "place")],
     [("no-dig method", "rotavated patch", "REPLACES")],
     "which bed-prep technique beat rotavating for cabbages last growing season",
     "no dig bed cabbage family yield compare tilled plot prior year"),
    # --- 31 ---
    ("The mortgage refinance with Halifax on 2026-01-28 locked 4.12% for five years; saved the previous SVR payment by £218 a month.", "milestone", "personal", False,
     [("Halifax", "organization"), ("2026-01-28", "date"), ("SVR", "concept")],
     [],
     "when did the house-loan remortgage close and what did the rate and saving look like",
     "mortgage refix fixed rate lender five year SVR exit saving monthly"),
    # --- 32 ---
    ("The hired structural engineer Priya Patel signed off the load-bearing wall removal on 2026-02-10; steel beam spec W8x18.", "reference", "personal", False,
     [("Priya Patel", "person"), ("load-bearing wall", "infrastructure"), ("2026-02-10", "date"), ("steel beam", "tool")],
     [],
     "who approved the interior wall knock-through and what beam went in",
     "structural engineer sign-off wall removal steel section spec date"),
    # --- 33 ---
    ("Chose B&Q's Shaker white over Howdens for the utility cabinets; £1,600 cheaper for the run and the soft-close hinges were the same OEM.", "decision", "personal", False,
     [("B&Q", "organization"), ("Shaker white", "concept"), ("Howdens", "organization"), ("utility cabinets", "tool"), ("soft-close hinges", "tool")],
     [("B&Q", "Howdens", "PREFERS")],
     "which cabinet supplier won the utility room run over the rival and why",
     "cabinet shop choice Shaker door price gap hinge sameness utility"),
    # --- 34. noise ---
    ("Hold on, let me find the receipt for that one.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The neighbour fence dispute started on 2025-11-04 over a leaning post; resolved with a shared surveyor and a split cost by January.", "problem", "personal", False,
     [("neighbour", "person"), ("fence", "tool"), ("2025-11-04", "date"), ("surveyor", "person")],
     [],
     "when did the boundary argument with next door begin and how did it settle",
     "next-door fence dispute lean post surveyor joint cost resolution"),
    # --- 36 ---
    ("Prefers the Makita 18V line to the DeWalt 20V for household tools; shared battery across six devices beat the extra torque.", "preference", "personal", False,
     [("Makita 18V", "tool"), ("DeWalt 20V", "tool")],
     [("Makita 18V", "DeWalt 20V", "PREFERS")],
     "which cordless power tool platform won out and for what reason",
     "power tool ecosystem battery share over higher voltage rival torque"),
    # --- 37 ---
    ("The underfloor heating manifold lives in the downstairs WC cupboard with the pressure gauge reading 1.3 bar at rest.", "reference", "personal", False,
     [("underfloor heating", "infrastructure"), ("manifold", "tool"), ("downstairs WC", "place"), ("pressure gauge", "tool")],
     [("manifold", "downstairs WC", "LOCATED_IN")],
     "where is the floor-heat distribution block and what pressure should it hold",
     "UFH manifold location small toilet cupboard pressure bar idle reading"),
    # --- 38 ---
    ("Energy efficiency rating climbed from D60 to B84 on 2026-04-08 after the loft top-up, new windows, and heat pump; the certificate arrived the next week.", "milestone", "personal", False,
     [("Energy efficiency rating", "concept"), ("2026-04-08", "date"), ("loft top-up", "method"), ("new windows", "tool"), ("heat pump", "tool")],
     [],
     "when did the EPC banding jump and which three upgrades stacked to get it there",
     "EPC rating jump loft insulation glazing heat pump combo date shift"),
    # --- 39 ---
    ("The mower blade bent on 2025-09-12 after hitting a buried paving slab in the long grass; straightened it once, replaced it the second time.", "problem", "personal", False,
     [("mower blade", "tool"), ("2025-09-12", "date"), ("paving slab", "tool")],
     [],
     "when did the cutter vane get damaged and what hidden object caused it",
     "lawn mower blade bend buried slab long grass strike repair replace"),
    # --- 40 ---
    ("The bedding plant rotation runs tulips in the front borders from October planting to April flowering, then dahlia tubers in May.", "architecture", "personal", False,
     [("tulips", "food"), ("front borders", "place"), ("October", "date"), ("April", "date"), ("dahlia tubers", "food"), ("May", "date")],
     [("dahlia tubers", "tulips", "REPLACES")],
     "how do the front-garden beds switch over across the seasons",
     "bulb border rotation spring bulb summer tuber planting months swap"),
    # --- 41 ---
    ("The garden tap had to be isolated on 2026-01-22 for a split pipe; remembered the stopcock is behind the downstairs panel.", "reference", "personal", False,
     [("garden tap", "infrastructure"), ("2026-01-22", "date"), ("stopcock", "tool"), ("downstairs panel", "place")],
     [("stopcock", "downstairs panel", "LOCATED_IN")],
     "when did the outside tap need shut-off and where does the main valve hide",
     "outdoor tap pipe burst winter main valve location downstairs hidden"),
    # --- 42 ---
    ("Chose Howdens for the kitchen carcasses despite the B&Q win on utility; the oak frontals matched the Karndean floor sample better.", "decision", "personal", False,
     [("Howdens", "organization"), ("kitchen carcasses", "tool"), ("B&Q", "organization"), ("oak frontals", "tool"), ("Karndean", "organization")],
     [("Howdens", "B&Q", "PREFERS")],
     "which supplier won the kitchen cabinets even after the utility decision went the other way",
     "kitchen cabinets choice oak door match LVT floor colour tradeoff"),
    # --- 43 ---
    ("Prefers the electric Stihl MSA 220 chainsaw to the petrol MS 180 for pruning; weight drop and instant start outweigh the runtime.", "preference", "personal", False,
     [("Stihl MSA 220", "tool"), ("MS 180", "tool")],
     [("Stihl MSA 220", "MS 180", "PREFERS")],
     "which brand chainsaw model now wins for trimming work and why",
     "battery chainsaw swap petrol pruning weight start runtime tradeoff"),
    # --- 44 ---
    ("The spontaneous flood from the washing machine on 2025-12-02 revealed a failed inlet hose; now I change both hoses every five years.", "problem", "personal", False,
     [("washing machine", "tool"), ("2025-12-02", "date"), ("inlet hose", "tool")],
     [],
     "what laundry appliance leak triggered the maintenance rule I keep now",
     "washer flood hose fail supply line rule five year replace cadence"),
    # --- 45 ---
    ("The contractor selection for the extension went to Bevan Builds over Rockhill; Bevan had three finished jobs within five miles to visit.", "decision", "personal", False,
     [("Bevan Builds", "organization"), ("Rockhill", "organization")],
     [("Bevan Builds", "Rockhill", "PREFERS")],
     "which building firm landed the extension job over the rival and on what evidence",
     "builder choice local completed jobs reference walk five mile radius"),
    # --- 46 ---
    ("Keeps the annual lawn routine on one page: scarify early April, aerate late April, feed May and August, overseed mid-September.", "architecture", "personal", False,
     [("lawn routine", "method"), ("early April", "date"), ("late April", "date"), ("May", "date"), ("August", "date"), ("mid-September", "date")],
     [],
     "what is the single-page grass-care calendar I stick to every year",
     "lawn calendar scarify aerate feed overseed month sequence annual"),
    # --- 47 ---
    ("The new Ring doorbell install hit an 802.11 band mismatch; the hub only broadcasts 2.4 GHz at the front wall, fixed with a dedicated SSID.", "problem", "personal", False,
     [("Ring doorbell", "tool"), ("802.11", "protocol"), ("2.4 GHz", "protocol"), ("SSID", "config")],
     [("Ring doorbell", "2.4 GHz", "DEPENDS_ON")],
     "what network gotcha blocked the front-door camera setup and how was it resolved",
     "smart doorbell install WiFi band issue dedicated network name workaround"),
    # --- 48 ---
    ("Replaced the old thermostatic shower valve with a Grohe Grohtherm on 2026-03-25; the temperature locks at 38°C and the kids can't scald anymore.", "milestone", "personal", False,
     [("thermostatic shower valve", "tool"), ("Grohe Grohtherm", "tool"), ("2026-03-25", "date")],
     [("Grohe Grohtherm", "thermostatic shower valve", "REPLACES")],
     "when did the shower mixer get upgraded and what safety feature came with it",
     "shower mixer swap brand model scald safety lock temperature date"),
    # --- 49 ---
    ("The compost bin is officially half-full of leaf mould from the 2025 autumn drop; ready to spread on the roses by late April.", "fact", "personal", False,
     [("compost bin", "tool"), ("leaf mould", "tool"), ("2025", "date"), ("roses", "food"), ("late April", "date")],
     [],
     "what is in the garden bin from last autumn and when does it go on the flowers",
     "leaf mould pile last autumn rose bed mulch spread month"),
    # --- 50 ---
    ("The smart-meter readings since 2026-01 show the heat pump pulls 3.1 kW steady in cold snaps; sized it right after all.", "reference", "personal", False,
     [("smart-meter", "tool"), ("2026-01", "date"), ("heat pump", "tool")],
     [],
     "what have the energy readings told me about the air-source unit load in winter",
     "smart meter data heat pump draw winter peak kilowatt sizing confirmation"),
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
