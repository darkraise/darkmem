"""One-off emitter for shared-base batch-202 — personal domain (coffee brewing and espresso: machines, grinders, recipes, origins, processing, extraction science).

Writes 50 rows to data/v2/shared/batch_202.tmp.jsonl with ids shared-10051..10100.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_202.tmp.jsonl"
ID_OFFSET = 10050

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Swapped the Niche Zero for a DF64 on the espresso bench because the flat-burr clarity on washed Kenya AA beat the conical dark-roast body I was chasing before.", "decision", "personal", False,
     [("Niche Zero", "tool"), ("DF64", "tool"), ("Kenya AA", "food")],
     [("DF64", "Niche Zero", "REPLACES"), ("DF64", "Kenya AA", "APPLIES_TO")],
     "which grinder swap did the home bar settle on after chasing clarity on washed Kenyan coffee",
     "df64 niche zero flat conical grinder kenya espresso swap"),
    # --- 2 architecture ---
    ("Dialled the espresso workflow around an 18 gram VST basket pulling a 36 gram yield in 28 seconds at 93 degrees, with a WDT tool and paper puck screen sitting between dose and tamp.", "architecture", "personal", False,
     [("VST basket", "tool"), ("WDT tool", "tool"), ("paper puck screen", "tool"), ("espresso", "food")],
     [("WDT tool", "espresso", "APPLIES_TO")],
     "how is the morning espresso pipeline ordered from dose through tamp on the 18 gram VST basket",
     "vst basket wdt puck screen dose yield ratio time temperature"),
    # --- 3 milestone ---
    ("First clean Rao shot landed on the Lelit Bianca after weeks of declining profiles: nine bars for five seconds, ramp to full, taper to six bars over the last third of the pour.", "milestone", "personal", False,
     [("Rao shot", "method"), ("Lelit Bianca", "tool"), ("nine bars", "config")],
     [("Rao shot", "Lelit Bianca", "APPLIES_TO")],
     "which pressure profile finally produced a clean Rao shot on the home paddle machine",
     "rao shot lelit bianca declining profile pressure ramp taper"),
    # --- 4 fact ---
    ("The Decent DE1 logs every pour with flow and pressure curves into the Insight app, so comparing two dials on a single Geisha tin is straightforward evidence rather than guesswork.", "fact", "personal", False,
     [("Decent DE1", "tool"), ("Insight", "api"), ("Geisha", "food")],
     [("Decent DE1", "Insight", "COMMUNICATES_WITH")],
     "how does the Decent machine make comparing two espresso dials on the same tin an evidence call",
     "decent de1 insight log flow pressure curve geisha dial compare"),
    # --- 5 preference ---
    ("Prefer a washed Ethiopia Yirgacheffe as the daily filter bean because the jasmine and bergamot notes pop cleanest through a V60 02 with a Cafec Abaca filter.", "preference", "personal", False,
     [("Ethiopia Yirgacheffe", "food"), ("V60", "tool"), ("Cafec Abaca", "tool")],
     [("V60", "Cafec Abaca", "USES")],
     "which origin and pour-over rig did the daily filter routine settle on for floral clarity",
     "yirgacheffe washed ethiopia v60 cafec abaca filter floral daily"),
    # --- 6 reference ---
    ("The Tetsu Kasuya 4:6 method on a V60 splits the 300 gram brew into two early pours for sweetness-acidity balance and three later pours for strength, all finishing by three and a half minutes.", "reference", "personal", False,
     [("Tetsu Kasuya 4:6", "method"), ("V60", "tool")],
     [("Tetsu Kasuya 4:6", "V60", "APPLIES_TO")],
     "how does the 4:6 pour-over method divide the water pulses between sweetness and strength",
     "tetsu kasuya 4 6 method v60 pour split sweetness strength"),
    # --- 7 decision ---
    ("Retired the Moka pot after buying the Flair 58 because lever control over temperature and pressure gave me espresso-grade extraction without another ten kilos of plumbed steel on the counter.", "decision", "personal", False,
     [("Moka pot", "tool"), ("Flair 58", "tool"), ("espresso", "food")],
     [("Flair 58", "Moka pot", "REPLACES")],
     "which lever machine replaced the Moka pot for actual espresso-grade shots at home",
     "flair 58 moka pot lever espresso replace temperature pressure"),
    # --- 8 architecture ---
    ("The morning routine layers an EK43 for filter coffee beside the Mazzer Mini for espresso, so neither grinder gets single-dose purge waste when the bean changes between cups.", "architecture", "personal", False,
     [("EK43", "tool"), ("Mazzer Mini", "tool"), ("filter coffee", "food"), ("espresso", "food")],
     [("EK43", "filter coffee", "APPLIES_TO"), ("Mazzer Mini", "espresso", "APPLIES_TO")],
     "how do two dedicated grinders split filter duty from espresso duty without purge waste",
     "ek43 mazzer mini filter espresso single dose purge bean change"),
    # --- 9 fact ---
    ("A Difluid R2 refractometer reads TDS on espresso pucks within plus or minus 0.03 percent, which is tight enough to notice a grinder burr alignment drift between cleanings.", "fact", "personal", False,
     [("Difluid R2", "tool"), ("TDS", "concept"), ("espresso", "food")],
     [("Difluid R2", "TDS", "PRODUCES")],
     "what measurement tolerance does the refractometer hit and which maintenance signal does that expose",
     "difluid r2 refractometer tds espresso burr alignment drift tolerance"),
    # --- 10 noise ---
    ("The laundry room door developed a squeak that seems to come back every third week no matter how much WD-40 goes into the hinge pin.", "fact", "noise", True, [], [], None, None),
    # --- 11 decision ---
    ("Picked the Profitec Pro 600 over the La Marzocco Linea Mini for the kitchen because dual PID and E61 flow control covered every profile I wanted at two-thirds the spend.", "decision", "personal", False,
     [("Profitec Pro 600", "tool"), ("La Marzocco Linea Mini", "tool"), ("E61", "pattern")],
     [("Profitec Pro 600", "La Marzocco Linea Mini", "PREFERS")],
     "which dual-boiler espresso machine won the kitchen slot against the pricier La Marzocco option",
     "profitec pro 600 la marzocco linea mini e61 dual boiler pid"),
    # --- 12 milestone ---
    ("Hit a 22 percent extraction on a natural Colombia Huila after two weeks of dialling the Timemore C3 on the Kalita Wave 155, which finally closed the underdeveloped gap.", "milestone", "personal", False,
     [("Colombia Huila", "food"), ("Timemore C3", "tool"), ("Kalita Wave 155", "tool")],
     [("Timemore C3", "Kalita Wave 155", "USES")],
     "which hand grinder and brewer combination finally hit 22 percent extraction on a Colombian natural",
     "timemore c3 kalita wave 155 colombia huila natural 22 percent"),
    # --- 13 reference ---
    ("Lance Hedrick's Aeropress world-championship recipe inverts the chamber, uses 11 grams on 200 grams of water, and calls for a 1:30 steep then a slow 30 second press through paper.", "reference", "personal", False,
     [("Lance Hedrick", "person"), ("Aeropress", "tool")],
     [("Lance Hedrick", "Aeropress", "USES")],
     "how does the Hedrick Aeropress recipe stage the invert steep and press on 11 grams of coffee",
     "lance hedrick aeropress invert 11 gram 200 steep press recipe"),
    # --- 14 preference ---
    ("Prefer a Chemex over a V60 on Sunday mornings because the thicker bonded filter on a washed Panama Geisha pulls a cleaner cup that rewards the slower 4 minute pour.", "preference", "personal", False,
     [("Chemex", "tool"), ("V60", "tool"), ("Panama Geisha", "food")],
     [("Chemex", "Panama Geisha", "APPLIES_TO")],
     "which pour-over brewer and origin does the slow Sunday ritual lean toward over the V60",
     "chemex v60 panama geisha washed bonded filter sunday slow"),
    # --- 15 architecture ---
    ("Espresso station runs a Flair 58 on a bench scale next to a Fellow Stagg EKG kettle, with the Acaia Lunar feeding weight into the Decent profile tablet over Bluetooth for live yield tracking.", "architecture", "personal", False,
     [("Flair 58", "tool"), ("Fellow Stagg EKG", "tool"), ("Acaia Lunar", "tool"), ("Bluetooth", "protocol")],
     [("Acaia Lunar", "Bluetooth", "COMMUNICATES_WITH")],
     "how does the lever station wire weight, kettle, and profile tablet together for live yield tracking",
     "flair 58 fellow stagg ekg acaia lunar bluetooth yield weight"),
    # --- 16 decision ---
    ("Dropped the anaerobic naturals from the house rotation after three consecutive lots tasted of overripe strawberry yoghurt; washed and honey processing cover the flavour map I actually want.", "decision", "personal", False,
     [("anaerobic", "method"), ("washed", "method"), ("honey", "method")],
     [("washed", "anaerobic", "REPLACES")],
     "which processing styles stayed in the house rotation after three anaerobic lots went off the flavour map",
     "anaerobic natural washed honey processing rotation flavour map drop"),
    # --- 17 fact ---
    ("James Hoffmann's French press technique skims the crust at four minutes, lets the silt settle for five more, then pours the clear top layer off without a plunger press at all.", "fact", "personal", False,
     [("James Hoffmann", "person"), ("French press", "tool")],
     [("James Hoffmann", "French press", "USES")],
     "how does the Hoffmann French press method handle the crust and silt without plunging",
     "james hoffmann french press crust skim silt settle pour technique"),
    # --- 18 architecture ---
    ("Brew temperature curves on the Lelit Bianca sit inside the paddle: a preinfusion at two bars for six seconds, then a full nine-bar flat through the shot, tuned per roast level in a notebook.", "architecture", "personal", False,
     [("Lelit Bianca", "tool"), ("paddle", "tool"), ("preinfusion", "method")],
     [("preinfusion", "Lelit Bianca", "APPLIES_TO")],
     "how is the paddle-driven pressure profile split between preinfusion and the nine-bar shot body",
     "lelit bianca paddle preinfusion nine bar profile shot body"),
    # --- 19 problem ---
    ("Fixed a chronic channelling issue by adding a 0.3 mm spacer under the 18 gram VST screen; the old setup let the headspace collapse unevenly and the extraction came out sour on the right edge.", "problem", "personal", False,
     [("channelling", "concept"), ("VST", "tool"), ("spacer", "tool")],
     [("spacer", "channelling", "FIXES")],
     "which hardware tweak on the VST basket eliminated the sour edge extraction from channelling",
     "channelling vst spacer headspace sour edge extraction fix"),
    # --- 20 reference ---
    ("Scott Rao's book Everything But Espresso treats TDS and extraction yield as orthogonal knobs, which changed how I dial a V60: strength by ratio, flavour by grind.", "reference", "personal", False,
     [("Scott Rao", "person"), ("Everything But Espresso", "publication"), ("TDS", "concept"), ("V60", "tool")],
     [("Everything But Espresso", "Scott Rao", "AUTHORED_BY")],
     "which Rao book reframed TDS and yield as orthogonal knobs for pour-over dialling",
     "scott rao everything but espresso tds extraction yield v60 knob"),
    # --- 21 milestone ---
    ("Reached a consistent 10.5 percent TDS on espresso with an 1:2 ratio after swapping SSP MP burrs into the DF64; the clarity jump on a medium Ethiopia was worth the install fiddle.", "milestone", "personal", False,
     [("TDS", "concept"), ("SSP MP", "tool"), ("DF64", "tool"), ("Ethiopia", "place")],
     [("SSP MP", "DF64", "CONFIGURES")],
     "which burr swap pushed espresso TDS to a stable 10.5 percent on a medium Ethiopian roast",
     "ssp mp burr df64 tds espresso 10 5 percent ethiopia medium"),
    # --- 22 decision ---
    ("Switched from bottled Volvic to a custom remineralised RO water built on the Third Wave Water espresso profile because scale buildup was killing the Profitec Pro 600 steam boiler.", "decision", "personal", False,
     [("Volvic", "tool"), ("Third Wave Water", "tool"), ("Profitec Pro 600", "tool")],
     [("Third Wave Water", "Volvic", "REPLACES")],
     "which water swap protected the steam boiler after scale damage showed up on the Profitec",
     "volvic third wave water ro remineralise profitec scale boiler"),
    # --- 23 fact ---
    ("Cold brew at 1:8 coffee-to-water with a Toddy for 18 hours at room temperature pulls a chocolate-heavy cup that still reads 1.2 percent TDS on the refractometer.", "fact", "personal", False,
     [("Cold brew", "food"), ("Toddy", "tool"), ("TDS", "concept")],
     [("Toddy", "Cold brew", "USES")],
     "which cold-brew ratio and vessel hits a chocolate profile at 1.2 percent TDS after 18 hours",
     "cold brew toddy 1 8 18 hour tds 1 2 percent chocolate"),
    # --- 24 architecture ---
    ("Weekly bean rotation keeps two SOE espresso tins and one omni-roast filter tin open at once; the SOEs get labelled with roast date and dev time so staleness is visible at a glance.", "architecture", "personal", False,
     [("SOE", "concept"), ("omni-roast", "concept"), ("roast date", "date")],
     [],
     "how does the weekly rotation keep SOE espresso tins readable for staleness alongside a filter omni",
     "soe single origin espresso omni roast filter tin rotation label"),
    # --- 25 preference ---
    ("Prefer a medium-light roast with a seven to nine percent development time ratio because anything darker mutes the acidity I want on a Kenyan washed lot.", "preference", "personal", False,
     [("medium-light roast", "concept"), ("development time", "concept"), ("Kenyan washed", "food")],
     [],
     "which roast and development window does the Kenyan washed cup lean toward for bright acidity",
     "medium light roast development time kenyan washed acidity prefer"),
    # --- 26 decision ---
    ("Swapped the Fellow Stagg EKG for a Brewista Artisan because the Artisan's narrower spout gives better pour control on a Kalita Wave with a 20 gram dose.", "decision", "personal", False,
     [("Fellow Stagg EKG", "tool"), ("Brewista Artisan", "tool"), ("Kalita Wave", "tool")],
     [("Brewista Artisan", "Fellow Stagg EKG", "REPLACES")],
     "which kettle swap gave better pour control on the Kalita Wave at a 20 gram dose",
     "fellow stagg ekg brewista artisan kalita wave kettle spout"),
    # --- 27 reference ---
    ("The Matt Winton syphon method uses an inverted stir at the crest and a downward stir on descent to force a clear mid-body separation between acidity and sugars.", "reference", "personal", False,
     [("Matt Winton", "person"), ("syphon", "tool")],
     [("Matt Winton", "syphon", "USES")],
     "which syphon stirring technique separates acidity from sugars across the crest and descent",
     "matt winton syphon stir crest descent acidity sugar separate"),
    # --- 28 problem ---
    ("Fixed the chalky tails on medium-dark espresso by cutting the shot at 34 grams instead of 40; the Mazzer burrs were overextracting the fines during the last four seconds.", "problem", "personal", False,
     [("Mazzer", "tool"), ("espresso", "food"), ("fines", "concept")],
     [],
     "which yield cut fixed the chalky tails from overextracted fines on the Mazzer grinder",
     "mazzer espresso fines chalky tail yield cut 34 medium dark"),
    # --- 29 milestone ---
    ("First Geisha from Panama Elida Estate landed and pulled a floral-honey espresso at 1:3 ratio with a slow 35 second pour, which was nothing like a traditional 1:2 shot on it.", "milestone", "personal", False,
     [("Panama Elida Estate", "place"), ("Geisha", "food"), ("espresso", "food")],
     [("Geisha", "Panama Elida Estate", "LOCATED_IN")],
     "which ratio and pour time pulled a floral Geisha espresso on the Panama Elida Estate lot",
     "panama elida estate geisha espresso 1 3 ratio 35 second pour"),
    # --- 30 architecture ---
    ("The crust-break step on French press happens at exactly 4 minutes with three slow stirs on a bamboo paddle; skimming grounds follows immediately so no silt rides into the pour.", "architecture", "personal", False,
     [("crust-break", "method"), ("French press", "tool"), ("bamboo paddle", "tool")],
     [("crust-break", "French press", "APPLIES_TO")],
     "how is the crust-break step timed and executed on the French press before pouring",
     "french press crust break 4 minute bamboo paddle stir skim silt"),
    # --- 31 decision ---
    ("Picked a Weber Workshops EG-1 over a second EK43 for the filter station because the small footprint cleared bench space and the SSP Cast burr set handled the same light-roast clarity I wanted.", "decision", "personal", False,
     [("Weber Workshops EG-1", "tool"), ("EK43", "tool"), ("SSP Cast", "tool")],
     [("Weber Workshops EG-1", "EK43", "PREFERS")],
     "which grinder replaced a second EK43 on the filter station for footprint and clarity reasons",
     "weber workshops eg1 ek43 ssp cast burr filter bench footprint"),
    # --- 32 fact ---
    ("Espresso basket depth matters more than diameter for headspace: the VST 18 gram runs 25.5 mm, and tamping to within 2 mm of the top rim is the repeatable target.", "fact", "personal", False,
     [("VST", "tool"), ("Espresso", "food"), ("headspace", "concept")],
     [],
     "which headspace target does the 18 gram VST basket demand on a repeatable tamp",
     "vst 18 gram basket headspace 25 5 mm tamp rim espresso"),
    # --- 33 reference ---
    ("The James Hoffmann V60 technique uses a 50 gram bloom pour swirled immediately, then two central pours at 45 seconds and 1:15 to finish 500 grams of water with a drawdown under 3:30.", "reference", "personal", False,
     [("James Hoffmann", "person"), ("V60", "tool")],
     [("James Hoffmann", "V60", "USES")],
     "how does the Hoffmann V60 recipe schedule the bloom, central pours, and drawdown on 500 grams",
     "hoffmann v60 bloom swirl central pour drawdown 500 3 30"),
    # --- 34 architecture ---
    ("Puck prep sequence is strict: grind into a dosing cup, WDT with 0.35 mm needles, settle with a leveller at 8 mm depth, then tamp with a calibrated 30 pound spring pusher.", "architecture", "personal", False,
     [("Puck prep", "method"), ("WDT", "tool"), ("leveller", "tool"), ("tamp", "tool")],
     [("WDT", "Puck prep", "APPLIES_TO")],
     "how is the espresso puck prep ordered from dosing cup through the calibrated tamp",
     "puck prep wdt leveller tamp dosing cup 8 mm 30 pound"),
    # --- 35 milestone ---
    ("Celebrated one year on the Decent DE1 by pulling a blind profile test: the Londinium-style lever curve beat both my Rao declining and Stephen Perger flat profiles on the same Ethiopian tin.", "milestone", "personal", False,
     [("Decent DE1", "tool"), ("Londinium-style", "method"), ("Rao declining", "method"), ("Ethiopian", "food")],
     [("Londinium-style", "Rao declining", "PREFERS")],
     "which pressure profile won the one-year blind test on the Decent against Rao and Perger shapes",
     "decent de1 londinium rao declining perger blind profile ethiopian"),
    # --- 36 decision ---
    ("Chose Moccamaster over a Breville Precision for batch brew because the copper element holds 96 degrees through the full basket and the plastic Breville drifted 4 degrees by cup eight.", "decision", "personal", False,
     [("Moccamaster", "tool"), ("Breville Precision", "tool"), ("batch brew", "food")],
     [("Moccamaster", "Breville Precision", "PREFERS")],
     "which batch brewer won on thermal stability across a full ten-cup basket",
     "moccamaster breville precision batch brew copper element 96 degree"),
    # --- 37 problem ---
    ("Static cling from the DF64 was throwing grounds onto the bench until I added a few drops of RDT to each dose; the clump-bust step cleaned up and WDT got smoother by half.", "problem", "personal", False,
     [("DF64", "tool"), ("RDT", "method"), ("WDT", "tool"), ("Static", "concept")],
     [("RDT", "Static", "FIXES")],
     "which spray trick cleaned up DF64 static clings and made WDT smoother on the home grinder",
     "df64 static rdt drop dose clump wdt grinder spray"),
    # --- 38 architecture ---
    ("Bean-freshness ledger tracks roast date, tin open date, and first brew date per lot in a Notion table so I can correlate cup scores to dev time across 90 days of tasting.", "architecture", "personal", False,
     [("Notion", "tool"), ("Bean-freshness ledger", "pattern"), ("dev time", "concept")],
     [("Bean-freshness ledger", "Notion", "DEPLOYED_ON")],
     "which ledger correlates roast date, tin opening, and cup scores across three months of bean rotation",
     "notion bean freshness ledger roast date tin open cup score"),
    # --- 39 decision ---
    ("Swapped the Baratza Encore for a 1Zpresso K-Ultra for travel brewing after the Encore burrs chattered on dense Kenya lots; the handheld finally hits pour-over grind uniformity.", "decision", "personal", False,
     [("Baratza Encore", "tool"), ("1Zpresso K-Ultra", "tool"), ("Kenya", "place")],
     [("1Zpresso K-Ultra", "Baratza Encore", "REPLACES")],
     "which travel grinder replaced the Baratza Encore after dense Kenyan beans exposed burr chatter",
     "baratza encore 1zpresso k ultra kenya travel grinder uniformity"),
    # --- 40 milestone ---
    ("Finished a 30-day cupping journal covering Yirgacheffe, Huila, Kenya AA, and a Sumatra Mandheling, which pinned my palate on washed African origins over Indonesian wet-hulled.", "milestone", "personal", False,
     [("Yirgacheffe", "food"), ("Huila", "food"), ("Kenya AA", "food"), ("Sumatra Mandheling", "food")],
     [],
     "which cupping exercise pinned the palate preference between African washed and Indonesian wet-hulled lots",
     "cupping journal yirgacheffe huila kenya aa sumatra mandheling palate"),
    # --- 41 reference ---
    ("Perger's turbo shot pulls a 1:3 ratio in 12 seconds on a coarse grind; the original aim is sweetness without the bitterness of a traditional 25 second pour.", "reference", "personal", False,
     [("Perger", "person"), ("turbo shot", "method")],
     [("Perger", "turbo shot", "AUTHORED_BY")],
     "how does the turbo shot pull a 1:3 ratio in 12 seconds and what flavour goal drives the technique",
     "perger turbo shot 1 3 12 second coarse grind sweetness espresso"),
    # --- 42 architecture ---
    ("The pour-over kit stores the V60, Kalita Wave, and Origami in a vertical rack above the kettle so each session picks a brewer in three seconds without opening a cabinet.", "architecture", "personal", False,
     [("V60", "tool"), ("Kalita Wave", "tool"), ("Origami", "tool")],
     [],
     "how is the pour-over kit arranged for three-second brewer selection at the morning bench",
     "v60 kalita wave origami rack vertical pour over bench morning"),
    # --- 43 noise ---
    ("The stairwell lightbulb flickered for two weeks before I finally pulled the fixture and found a tiny moth pressed against the ballast.", "fact", "noise", True, [], [], None, None),
    # --- 44 fact ---
    ("Thermal shock processing on a Costa Rica lot from Chirripo pushes sharp grapefruit acidity that cuts straight through the sweetness I expect from standard washed Costa Ricans.", "fact", "personal", False,
     [("Thermal shock", "method"), ("Costa Rica", "place"), ("Chirripo", "place")],
     [("Chirripo", "Costa Rica", "LOCATED_IN")],
     "which processing method on a Costa Rica Chirripo lot delivered sharp grapefruit acidity over typical sweetness",
     "thermal shock costa rica chirripo grapefruit acidity washed"),
    # --- 45 preference ---
    ("Prefer a 1:16 ratio on V60 over the James Hoffmann 1:17 default because the thicker body suits my medium-roast Huilas and the extraction still lands under 22 percent.", "preference", "personal", False,
     [("V60", "tool"), ("Huila", "food"), ("James Hoffmann", "person")],
     [],
     "which V60 ratio preference beat the Hoffmann default on the medium-roast Huila lots",
     "v60 1 16 1 17 hoffmann huila medium roast body ratio"),
    # --- 46 decision ---
    ("Moved espresso scales from a Hario V60 Drip Scale to an Acaia Pyxis because the half-second latency on the Hario was hurting my Rao-style cut points at the end of a pour.", "decision", "personal", False,
     [("Hario V60 Drip Scale", "tool"), ("Acaia Pyxis", "tool"), ("Rao", "method")],
     [("Acaia Pyxis", "Hario V60 Drip Scale", "REPLACES")],
     "which scale swap fixed the half-second latency that was hurting Rao-style pour cut points",
     "hario v60 drip scale acaia pyxis espresso latency rao cut"),
    # --- 47 architecture ---
    ("Acidity balance on a syphon brew is managed by a 15 second pre-stir before drawdown and a Kone metal filter that lets oils through; paper filters were muting the citrus edge.", "architecture", "personal", False,
     [("syphon", "tool"), ("Kone", "tool"), ("paper filter", "tool")],
     [("Kone", "paper filter", "REPLACES")],
     "how does the syphon setup preserve citrus edge and acidity through filter and stir choices",
     "syphon kone metal filter paper 15 second stir drawdown citrus"),
    # --- 48 problem ---
    ("Dealt with boiler hammer on the Lelit Bianca after a descale cycle by purging through the group for 10 seconds each morning; trapped air was causing pressure spikes on the first shot.", "problem", "personal", False,
     [("Lelit Bianca", "tool"), ("boiler hammer", "concept"), ("descale", "method")],
     [("descale", "boiler hammer", "CAUSES")],
     "which morning purge routine cleared the post-descale boiler hammer on the Lelit Bianca",
     "lelit bianca boiler hammer descale purge group air pressure"),
    # --- 49 milestone ---
    ("Completed a Q-grader style triangulation on three Yirgacheffe micro-lots and scored the Kochere washed at 88.5 against Gedeb naturals at 86 and 85, which matched the importer notes.", "milestone", "personal", False,
     [("Yirgacheffe", "food"), ("Kochere", "place"), ("Gedeb", "place"), ("Q-grader", "method")],
     [("Kochere", "Yirgacheffe", "LOCATED_IN")],
     "which triangulation exercise pinned Kochere washed above Gedeb naturals against importer scoring",
     "q grader triangulation yirgacheffe kochere gedeb 88 5 score"),
    # --- 50 architecture ---
    ("Temperature control on pour-over kettles runs a pre-boil to 100 degrees, drop to target over 30 seconds with the lid off, then start the bloom; the ramp-down avoids scalding lighter roasts.", "architecture", "personal", False,
     [("pour-over", "method"), ("kettle", "tool"), ("bloom", "method")],
     [],
     "how does the pre-boil and ramp-down pattern protect lighter roasts from scald during bloom",
     "pour over kettle pre boil ramp down bloom light roast scald"),
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
