"""One-off emitter for shared-base batch-277 — personal domain (scuba diving and freediving: certifications, gases, equipment, sites, freediving).

Writes 50 rows to data/v2/shared/batch_277.tmp.jsonl with ids shared-13801..13850.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_277.tmp.jsonl"
ID_OFFSET = 13800

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Booked the PADI Open Water course at a Dahab centre after weighing SSI Open Water and NAUI alongside it; the instructor ratio and the lagoon checkouts on the first morning sold me.", "decision", "personal", False,
     [("PADI Open Water", "activity"), ("Dahab", "place"), ("SSI Open Water", "activity"), ("NAUI", "organization")],
     [("PADI Open Water", "SSI Open Water", "PREFERS"), ("PADI Open Water", "Dahab", "LOCATED_IN")],
     "which entry-level scuba certification did I end up booking and which town hosts the centre",
     "padi ssi naui open water dahab certification entry lagoon"),
    # --- 2 architecture ---
    ("My twinset rig runs a Halcyon Infinity backplate and wing with long-hose primary, bungee-mount backup, and an SPG on the left post; the configuration mirrors standard GUE Fundamentals trim drills.", "architecture", "personal", False,
     [("Halcyon Infinity", "organization"), ("GUE Fundamentals", "activity")],
     [("Halcyon Infinity", "GUE Fundamentals", "APPLIES_TO")],
     "how is my twinset rig laid out and which training programme informed the hose routing",
     "halcyon infinity backplate wing twinset gue fundamentals long hose"),
    # --- 3 milestone ---
    ("Completed Advanced Open Water on 2023-09-14 after the deep dive at Blue Hole Egypt; the nitrogen narcosis at forty metres was gentler than the briefing warned.", "milestone", "personal", False,
     [("Advanced Open Water", "activity"), ("2023-09-14", "date"), ("Blue Hole Egypt", "place")],
     [("Advanced Open Water", "Blue Hole Egypt", "LOCATED_IN"), ("Advanced Open Water", "2023-09-14", "HAPPENED_ON")],
     "when did I finish the advanced scuba cert and which deep site served as the checkout",
     "advanced open water blue hole egypt deep dive narcosis september"),
    # --- 4 fact ---
    ("My primary first stage is an Apeks XTX200 paired with a ScubaPro MK25 EVO on the pony bottle; both are sealed diaphragm designs rated for cold-water service.", "fact", "personal", False,
     [("Apeks XTX200", "tool"), ("ScubaPro MK25 EVO", "tool")],
     [("Apeks XTX200", "ScubaPro MK25 EVO", "RELATED_TO")],
     "which two regulators sit on my primary and pony rigs and what service class are they rated for",
     "apeks xtx200 scubapro mk25 evo cold water regulator pony"),
    # --- 5 reference ---
    ("Reference table I keep on the slate: EAN32 caps at a MOD of thirty-three metres on 1.4 ppO2, EAN36 caps at twenty-eight metres, air caps at forty-five and trimix extends the envelope.", "reference", "personal", False,
     [("EAN32", "concept"), ("MOD", "concept"), ("EAN36", "concept"), ("trimix", "concept")],
     [("EAN32", "MOD", "RELATED_TO"), ("EAN36", "MOD", "RELATED_TO")],
     "which MOD limits do I carry on slate for the common nitrox mixes and what does trimix do to the envelope",
     "ean32 ean36 mod nitrox trimix ppo2 depth limit slate"),
    # --- 6 preference ---
    ("I prefer a Shearwater Teric on the left wrist with a Perdix AI as backup on the right; the haptic alarms on the Teric cut through gloves better than any vibrate-only unit.", "preference", "personal", False,
     [("Shearwater Teric", "tool"), ("Perdix AI", "tool")],
     [("Shearwater Teric", "Perdix AI", "PREFERS")],
     "which dive computer do I wear on which wrist and why did the haptic alarms seal the choice",
     "shearwater teric perdix ai dive computer haptic wrist backup"),
    # --- 7 decision ---
    ("Chose the BARE Sentry Pro drysuit over the Santi E.Lite for the Silfra trip; the heavier trilaminate and the replaceable knee pads weighed more than the E.Lite packability win.", "decision", "personal", False,
     [("BARE Sentry Pro", "tool"), ("Santi E.Lite", "tool"), ("Silfra", "place")],
     [("BARE Sentry Pro", "Santi E.Lite", "PREFERS"), ("BARE Sentry Pro", "Silfra", "APPLIES_TO")],
     "which drysuit won the head-to-head for the Iceland fissure trip and which rival did it beat",
     "bare sentry pro santi elite drysuit silfra iceland trilaminate"),
    # --- 8 problem ---
    ("Lost buoyancy control on the Cozumel drift when the inflator stuck open; thumbed the dive, dumped from the shoulder, and the divemaster signalled the boat while I disconnected the hose.", "problem", "personal", False,
     [("Cozumel", "place"), ("divemaster", "activity")],
     [("divemaster", "Cozumel", "LOCATED_IN")],
     "which gear failure on the Mexico drift forced an emergency ascent and how did the team recover it",
     "cozumel drift inflator stuck runaway ascent dump shoulder hose"),
    # --- 9 architecture ---
    ("Side-mount rig stages two AL80 cylinders on Dive Rite rails with independent regulators; the failure domain on a burst disc stays on one cylinder and the other carries the dive out.", "architecture", "personal", False,
     [("Dive Rite", "organization"), ("AL80", "tool")],
     [("AL80", "Dive Rite", "USES")],
     "how does my side-mount rig isolate a burst-disc failure to a single cylinder on the rails",
     "side mount dive rite al80 cylinder burst disc independent regulator"),
    # --- 10 noise ---
    ("The lobby coffee machine at the dive centre finally got fixed on the same week the espresso beans ran out again.", "fact", "noise", True, [], [], None, None),
    # --- 11 milestone ---
    ("Passed Rescue Diver on 2024-06-08 after the tired-diver tow at Monterey Point Lobos; the surf exit in a seven-mil hooded suit was the hardest five minutes of the weekend.", "milestone", "personal", False,
     [("Rescue Diver", "activity"), ("2024-06-08", "date"), ("Monterey Point Lobos", "place")],
     [("Rescue Diver", "Monterey Point Lobos", "LOCATED_IN"), ("Rescue Diver", "2024-06-08", "HAPPENED_ON")],
     "when did I pass the rescue cert and which California site hosted the tow and surf exit",
     "rescue diver monterey point lobos tow surf exit june california"),
    # --- 12 decision ---
    ("Signed up for GUE Fundamentals instead of PADI Divemaster next; the DIR trim and team focus fit the overhead ambitions better than a pro-track internship would.", "decision", "personal", False,
     [("GUE Fundamentals", "activity"), ("PADI Divemaster", "activity")],
     [("GUE Fundamentals", "PADI Divemaster", "PREFERS")],
     "which training path did I commit to next and what was it chosen over",
     "gue fundamentals padi divemaster dir trim team overhead"),
    # --- 13 reference ---
    ("Keep a cheat card in the Peli case: best mix for twenty-eight metres is EAN36, for thirty-three metres it's EAN32, and for anything past forty-two metres trimix with helium enters the plan.", "reference", "personal", False,
     [("Peli case", "tool"), ("EAN36", "concept"), ("EAN32", "concept"), ("trimix", "concept")],
     [],
     "which cheat card lives in the hard case and how does it pick the best mix at each depth",
     "peli case cheat best mix ean36 ean32 trimix helium depth"),
    # --- 14 architecture ---
    ("Wing lift on my travel rig is thirty pounds on an aluminium backplate for warm-water trips; the cold-water kit swaps to a steel backplate and a fifty-five pound donut to float the twinset.", "architecture", "personal", False,
     [("backplate", "tool"), ("twinset", "tool")],
     [("twinset", "backplate", "USES")],
     "how does my backplate and wing configuration shift between warm-water travel and cold-water twinset diving",
     "wing lift aluminium steel backplate travel cold twinset donut"),
    # --- 15 fact ---
    ("The Atomic Aquatics T3 titanium second stage sits on the travel rig; the reduced swing weight in the mouth keeps jaw fatigue manageable on ninety-minute reef dives.", "fact", "personal", False,
     [("Atomic Aquatics T3", "tool")],
     [],
     "which titanium second stage rides on the travel rig and what ergonomic benefit does it bring on long dives",
     "atomic aquatics t3 titanium second stage travel jaw fatigue reef"),
    # --- 16 preference ---
    ("I prefer EAN32 as the default bottom mix for recreational reef work; the extra oxygen extends no-deco time on the back half of the dive without pushing the MOD uncomfortably shallow.", "preference", "personal", False,
     [("EAN32", "concept"), ("MOD", "concept")],
     [("EAN32", "MOD", "APPLIES_TO")],
     "which nitrox mix do I default to on reef dives and what trade-off drives that preference",
     "ean32 nitrox default reef no deco time mod recreational"),
    # --- 17 milestone ---
    ("Logged dive number 200 on 2024-11-22 at Raja Ampat during the manta cleaning-station hover; a group of five passed overhead at the safety stop like an air-show flypast.", "milestone", "personal", False,
     [("2024-11-22", "date"), ("Raja Ampat", "place")],
     [],
     "when did the two-hundredth logged dive land and which Indonesian site hosted the manta encounter",
     "dive 200 raja ampat manta cleaning station november 2024"),
    # --- 18 decision ---
    ("Picked the Shearwater Petrel 3 for the tec kit ahead of the Hollis DC1; the Petrel's GF-based deco model and the rechargeable option tipped it over the simpler Hollis UI.", "decision", "personal", False,
     [("Shearwater Petrel 3", "tool"), ("Hollis DC1", "tool")],
     [("Shearwater Petrel 3", "Hollis DC1", "PREFERS")],
     "which tec-kit dive computer won against the Hollis DC1 and what features decided it",
     "shearwater petrel 3 hollis dc1 tec gradient factor deco recharge"),
    # --- 19 reference ---
    ("Quick reference for AIDA freediving: CNF is constant weight no-fins, CWT is constant weight, DNF is dynamic no-fins in the pool, and DYN is dynamic with fins on the same horizontal course.", "reference", "personal", False,
     [("AIDA", "organization"), ("CNF", "concept"), ("CWT", "concept"), ("DNF", "concept"), ("DYN", "concept")],
     [("CNF", "AIDA", "RELATED_TO"), ("DYN", "AIDA", "RELATED_TO")],
     "what do the AIDA freediving discipline codes stand for and which are pool versus depth",
     "aida cnf cwt dnf dyn freediving constant dynamic discipline"),
    # --- 20 architecture ---
    ("Freediving training split: pool sessions Tuesday for DYN drills, dry static on Sunday morning, and one depth day a month at a quarry for CWT progression with a surface safety.", "architecture", "personal", False,
     [("DYN", "concept"), ("dry static", "concept"), ("CWT", "concept")],
     [],
     "how is my weekly freediving training split across pool, dry work, and depth days",
     "dyn pool dry static cwt depth quarry weekly split safety"),
    # --- 21 fact ---
    ("Herbert Nitsch holds the no-limits freediving record at two hundred fourteen metres, set on 2007-06-14; the suit recovery attempt in 2012 ended his record chasing after decompression injury.", "fact", "personal", False,
     [("Herbert Nitsch", "person"), ("2007-06-14", "date")],
     [("Herbert Nitsch", "2007-06-14", "HAPPENED_ON")],
     "which freediver holds the no-limits mark and when was the record dive completed",
     "herbert nitsch no limits 214 metre freediving record 2007"),
    # --- 22 decision ---
    ("Cancelled the Truk Lagoon liveaboard for August and rebooked Palau for the same window; the wreck-penetration certifications weren't quite current and Palau's shark action didn't need them.", "decision", "personal", False,
     [("Truk Lagoon", "place"), ("Palau", "place")],
     [("Palau", "Truk Lagoon", "REPLACES")],
     "which liveaboard destination swap happened for August and what drove the change",
     "truk lagoon palau liveaboard august wreck penetration cert shark"),
    # --- 23 architecture ---
    ("Doubles manifold setup runs an isolator between the two cylinders; a catastrophic free-flow on one post gets isolated by closing the valve while the other cylinder feeds the long-hose primary.", "architecture", "personal", False,
     [("Doubles", "tool"), ("manifold", "tool")],
     [("Doubles", "manifold", "HAS_PART")],
     "how does the isolator on my doubles handle a free-flow failure on a single post",
     "doubles manifold isolator free flow post long hose cylinder"),
    # --- 24 milestone ---
    ("Hit a 75-metre DYN on 2025-02-09 at the indoor fifty-metre pool; the final turn was clean and the samba on surfacing was mild enough that the coach signed the session as a PB.", "milestone", "personal", False,
     [("DYN", "concept"), ("2025-02-09", "date")],
     [("DYN", "2025-02-09", "HAPPENED_ON")],
     "when did the seventy-five metre DYN PB land and which pool hosted the attempt",
     "dyn 75 metre personal best february 2025 indoor pool samba"),
    # --- 25 decision ---
    ("Switched my primary agency from PADI to SSI for specialty cards going forward; the digital card system and the less rigid instructor material suited my travel pattern better.", "decision", "personal", False,
     [("PADI", "organization"), ("SSI", "organization")],
     [("SSI", "PADI", "REPLACES")],
     "which agency swap did I make for specialty cards and what practical reasons drove it",
     "padi ssi specialty card agency switch digital travel flexible"),
    # --- 26 reference ---
    ("Site-book shortlist: Silfra Iceland for clarity, Silent World Lembeh for macro, Cenotes Dos Ojos for cavern light, USS Kittiwake for penetration practice, and USS Oriskany for scale.", "reference", "personal", False,
     [("Silfra", "place"), ("Silent World Lembeh", "place"), ("Cenotes Dos Ojos", "place"), ("USS Kittiwake", "place"), ("USS Oriskany", "place")],
     [],
     "which five sites sit on my must-dive shortlist and what does each one offer",
     "silfra silent world lembeh cenotes dos ojos uss kittiwake oriskany"),
    # --- 27 architecture ---
    ("CCR plan I'm building toward: JJ-CCR rebreather body with Shearwater Petrel 3 as primary handset, bailout on a side-mounted AL40, and dil flushes scheduled every five minutes on ascent.", "architecture", "personal", False,
     [("JJ-CCR", "tool"), ("Shearwater Petrel 3", "tool"), ("AL40", "tool")],
     [("JJ-CCR", "Shearwater Petrel 3", "USES")],
     "what shape does my planned CCR configuration take from primary handset down to bailout",
     "jj ccr rebreather petrel 3 al40 bailout dil flush ascent"),
    # --- 28 decision ---
    ("Strongly prefer the Aqualung Legend over the mid-range ScubaPro lineup for rental fills on warm trips; the breathing resistance stays flat through the second half of a tank.", "decision", "personal", False,
     [("Aqualung Legend", "tool")],
     [],
     "which rental-grade regulator do I ask for on warm trips and what performance trait wins it for me",
     "aqualung legend rental regulator warm breathing resistance"),
    # --- 29 milestone ---
    ("Dived the USS Kittiwake on 2024-03-05 for the first proper wreck penetration; the engine-room swim-through was narrower than any training wreck and the silt-out drill from class paid off.", "milestone", "personal", False,
     [("USS Kittiwake", "place"), ("2024-03-05", "date")],
     [("USS Kittiwake", "2024-03-05", "HAPPENED_ON")],
     "when did the first real wreck penetration happen and which vessel hosted the engine-room swim",
     "uss kittiwake wreck penetration engine room silt out march"),
    # --- 30 fact ---
    ("Alexey Molchanov holds the current CWT mark at one hundred thirty metres in a monofin; his Deep Week courses in Dahab are on my short list for next spring.", "fact", "personal", False,
     [("Alexey Molchanov", "person"), ("CWT", "concept"), ("Dahab", "place")],
     [("Alexey Molchanov", "Dahab", "LOCATED_IN")],
     "which freediver holds the current constant-weight record and where does he run the Deep Week courses",
     "alexey molchanov cwt 130 monofin deep week dahab course"),
    # --- 31 architecture ---
    ("Transmitter pairing: a single Shearwater transmitter on the primary first stage feeds the Teric on the wrist; the pony bottle keeps an analog SPG because a battery there adds no safety.", "architecture", "personal", False,
     [("Shearwater", "organization"), ("transmitter", "tool"), ("Teric", "tool")],
     [("Teric", "transmitter", "USES")],
     "how is the air-integration transmitter paired to my wrist computer and why does the pony stay analog",
     "shearwater transmitter teric pony analog spg air integration"),
    # --- 32 decision ---
    ("Skipped the PADI Tec40 and jumped straight into TDI Intro to Tech; the TDI curriculum front-loads stage handling and valve drills in a way Tec40 defers to Tec45.", "decision", "personal", False,
     [("PADI Tec40", "activity"), ("TDI", "organization"), ("Tec45", "activity")],
     [("TDI", "PADI Tec40", "PREFERS")],
     "which tec entry path did I pick and what did it teach earlier than the PADI track",
     "padi tec40 tdi intro tech tec45 stage valve drill entry"),
    # --- 33 reference ---
    ("Heliox versus trimix quick note: heliox strips nitrogen entirely and removes narcosis but costs more and runs cold; trimix keeps enough nitrogen to buffer density and controls gas cost better on recreational tec depths.", "reference", "personal", False,
     [("heliox", "concept"), ("trimix", "concept")],
     [("heliox", "trimix", "RELATED_TO")],
     "how does heliox trade off against trimix on narcosis, cost, and warmth at recreational tec depths",
     "heliox trimix nitrogen narcosis cost density helium warmth tec"),
    # --- 34 fact ---
    ("Stig Severinsen holds the Guinness record for dry static apnea at twenty-two minutes; lung packing and ice-water face immersion are the two techniques he points to publicly.", "fact", "personal", False,
     [("Stig Severinsen", "person"), ("lung packing", "concept")],
     [("Stig Severinsen", "lung packing", "USES")],
     "which freediver holds the dry static apnea record and which two techniques does he credit",
     "stig severinsen dry static apnea 22 minute lung pack ice"),
    # --- 35 decision ---
    ("Depth-day safety configuration for CWT: lanyard on the line, two safety freedivers meeting at fifteen and thirty metres on the ascent, and a counterweight system rigged to pull an unconscious athlete from depth in under a minute.", "decision", "personal", False,
     [("CWT", "concept"), ("lanyard", "tool"), ("counterweight", "tool")],
     [("CWT", "lanyard", "USES")],
     "how is a CWT depth attempt protected by safety divers, line lanyard, and a counterweight rig",
     "cwt lanyard safety freediver meet 15 30 counterweight unconscious"),
    # --- 36 milestone ---
    ("Finished Silfra Iceland on 2025-04-18 after an aborted attempt the day before for wind; the twenty-metre viz through the Eurasian and American plates was every bit the postcard it promised.", "milestone", "personal", False,
     [("Silfra", "place"), ("2025-04-18", "date")],
     [("Silfra", "2025-04-18", "HAPPENED_ON")],
     "when did the Silfra fissure dive finally happen after the weather abort and what did the viz deliver",
     "silfra iceland april 2025 eurasian american plate viz abort"),
    # --- 37 decision ---
    ("Chose CMAS two-star over BSAC Ocean Diver for the Mediterranean club year; the CMAS card is more portable between dive clubs in France and Italy than the BSAC equivalent.", "decision", "personal", False,
     [("CMAS", "organization"), ("BSAC Ocean Diver", "activity")],
     [("CMAS", "BSAC Ocean Diver", "PREFERS")],
     "which European dive cert did I take for the Mediterranean club year and why over the British alternative",
     "cmas two star bsac ocean diver mediterranean france italy"),
    # --- 38 preference ---
    ("Prefer a DUI drysuit for extended cold-water work over the BARE line whenever budget allows; the custom fit and the self-donning zip cut solo-rigging time in half.", "preference", "personal", False,
     [("DUI", "organization"), ("BARE", "organization")],
     [("DUI", "BARE", "PREFERS")],
     "which drysuit brand do I prefer for extended cold work when budget is open and why over BARE",
     "dui drysuit bare cold water self donning zip solo custom fit"),
    # --- 39 fact ---
    ("William Trubridge holds the CNF record at one hundred two metres set at Dean's Blue Hole; the no-fins discipline is the purest test of freediving technique in the sport.", "fact", "personal", False,
     [("William Trubridge", "person"), ("CNF", "concept")],
     [("William Trubridge", "CNF", "USES")],
     "which freediver holds the constant weight no-fins mark and what is the discipline's reputation",
     "william trubridge cnf 102 metre dean blue hole no fins"),
    # --- 40 architecture ---
    ("Cenote dive planning: guideline reels primary and backup, three independent lights each with a burn-time buffer, gas thirds-rule by cylinder, and a map of the Cenotes Dos Ojos permanent line on the slate.", "architecture", "personal", False,
     [("Cenotes Dos Ojos", "place"), ("thirds-rule", "concept")],
     [("thirds-rule", "Cenotes Dos Ojos", "APPLIES_TO")],
     "how do I plan gas, lights, and guideline redundancy for a cavern dive at the Mexican cenote",
     "cenote dos ojos reel guideline light thirds gas redundancy slate"),
    # --- 41 decision ---
    ("Put the IANTD Normoxic Trimix course on the schedule for next winter instead of the TDI Extended Range; the IANTD gas-matrix approach maps better to the mixed-team dives I actually want to run.", "decision", "personal", False,
     [("IANTD", "organization"), ("TDI", "organization")],
     [("IANTD", "TDI", "PREFERS")],
     "which technical trimix course sits on the winter schedule and which alternative did it beat",
     "iantd normoxic trimix tdi extended range winter course gas matrix"),
    # --- 42 reference ---
    ("Mammalian dive reflex notes: bradycardia kicks in within the first fifteen seconds of facial immersion in water below twenty degrees, peripheral vasoconstriction follows, and the spleen contraction adds oxygenated red cells on longer breath-holds.", "reference", "personal", False,
     [("Mammalian dive reflex", "theory"), ("bradycardia", "concept")],
     [("Mammalian dive reflex", "bradycardia", "HAS_PART")],
     "which three physiological stages make up the mammalian dive reflex and in what order do they fire",
     "mammalian dive reflex bradycardia vasoconstriction spleen contraction"),
    # --- 43 noise ---
    ("The harbour-side cafe finally put their table tennis board out for the summer and it already has a crack running through the centre.", "fact", "noise", True, [], [], None, None),
    # --- 44 decision ---
    ("Went with the Apeks XTX200 over the Scubapro S600 for the stage-bottle second stage; Apeks service parts turn up faster in the shops I rely on while travelling.", "decision", "personal", False,
     [("Apeks XTX200", "tool"), ("Scubapro S600", "tool")],
     [("Apeks XTX200", "Scubapro S600", "PREFERS")],
     "which second stage did I pick for the stage bottle and why over the Scubapro equivalent",
     "apeks xtx200 scubapro s600 stage bottle service parts travel"),
    # --- 45 milestone ---
    ("Logged a 45-metre CWT at 2025-05-24 during a Molchanov Wave 3 course; the mouthfill equalisation finally clicked on the second-last dive of the week.", "milestone", "personal", False,
     [("CWT", "concept"), ("2025-05-24", "date"), ("Molchanov Wave 3", "activity")],
     [("CWT", "Molchanov Wave 3", "APPLIES_TO"), ("CWT", "2025-05-24", "HAPPENED_ON")],
     "when did the forty-five metre CWT land and which freediving course provided the structure",
     "cwt 45 metre molchanov wave 3 mouthfill equalisation may 2025"),
    # --- 46 problem ---
    ("Squeeze on a -32 metre attempt at a freediving training camp last month; pink sputum on surfacing, coach pulled me from depth for the rest of the week and scheduled an ultrasound before the next progression.", "problem", "personal", False,
     [("Squeeze", "concept"), ("freediving", "hobby")],
     [("Squeeze", "freediving", "APPLIES_TO")],
     "which freediving injury event cut a training camp short and what follow-up did the coach schedule",
     "squeeze freediving 32 metre pink sputum ultrasound coach pull"),
    # --- 47 fact ---
    ("Lung packing adds roughly a litre to total capacity beyond vital capacity for my size; the mediastinal stretch is uncomfortable enough that I keep it strictly to competition attempts, not training sessions.", "fact", "personal", False,
     [("Lung packing", "concept"), ("mediastinal stretch", "concept")],
     [("Lung packing", "mediastinal stretch", "CAUSES")],
     "how much extra capacity does lung packing buy me and why do I keep it to competition only",
     "lung packing litre mediastinal stretch vital capacity competition"),
    # --- 48 architecture ---
    ("USS Oriskany penetration plan I'd run if I ever get the ticket: trimix bottom gas, fifty-percent deco gas stage, reel-in from the superstructure entry, and a runtime ceiling on the island deck below eighty metres.", "architecture", "personal", False,
     [("USS Oriskany", "place"), ("trimix", "concept")],
     [("trimix", "USS Oriskany", "APPLIES_TO")],
     "how would a penetration plan for the Florida aircraft-carrier wreck be laid out around gas, deco, and runtime",
     "uss oriskany trimix 50 deco stage reel island deck runtime"),
    # --- 49 problem ---
    ("Mask squeeze on a breath-hold to twelve metres during freediving last summer showed up as capillary bleed in the eye whites; since then I equalise the mask by exhaling through the nose below six metres without fail.", "problem", "personal", False,
     [("Mask squeeze", "concept"), ("freediving", "hobby")],
     [("Mask squeeze", "freediving", "APPLIES_TO")],
     "which breath-hold injury taught me to equalise the mask early and what routine came out of it",
     "mask squeeze breath hold capillary eye equalise nose six metre"),
    # --- 50 preference ---
    ("I prefer a long-blade carbon monofin for pool DYN over the bi-fin option; the glide phase after each kick covers more distance per stroke which keeps the O2 budget honest on a 75-metre target.", "preference", "personal", False,
     [("monofin", "tool"), ("DYN", "concept")],
     [("monofin", "DYN", "APPLIES_TO")],
     "which fin type do I favour for pool DYN attempts and what performance property wins it for me",
     "monofin carbon bi fin dyn pool glide oxygen 75 metre target"),
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
