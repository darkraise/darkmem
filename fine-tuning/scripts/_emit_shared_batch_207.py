"""One-off emitter for shared-base batch-207 — personal domain (hiking and trail running: thru-hikes, ultralight gear, navigation, nutrition, ultramarathons, training).

Writes 50 rows to data/v2/shared/batch_207.tmp.jsonl with ids shared-10301..10350.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_207.tmp.jsonl"
ID_OFFSET = 10300

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Swapped the Osprey Exos for a Zpacks Arc Blast before the Pacific Crest Trail attempt; the frame carries the same twenty-pound load at almost a pound less on the shoulders.", "decision", "personal", False,
     [("Osprey Exos", "tool"), ("Zpacks Arc Blast", "tool"), ("Pacific Crest Trail", "place")],
     [("Zpacks Arc Blast", "Osprey Exos", "REPLACES"), ("Zpacks Arc Blast", "Pacific Crest Trail", "APPLIES_TO")],
     "which ultralight pack replaced the Osprey Exos before the PCT thru-hike and why",
     "zpacks arc blast osprey exos pct pacific crest ultralight pack swap"),
    # --- 2 ---
    ("Finished the Appalachian Trail northbound from Springer to Katahdin in one hundred and forty-two days; the final climb up Katahdin happened in a cold rain that turned the rock slabs slick.", "milestone", "personal", False,
     [("Appalachian Trail", "place"), ("Springer", "place"), ("Katahdin", "place")],
     [("Appalachian Trail", "Katahdin", "APPLIES_TO")],
     "how long did the northbound Appalachian Trail thru-hike take from Springer to the summit",
     "appalachian trail at nobo springer katahdin thru hike days finish"),
    # --- 3 ---
    ("Use a Hyperlite Mountain Gear Dyneema stuff sack for the quilt and food bag rotation; the fabric sheds rain without a dry-bag liner and weighs almost nothing on the scale.", "preference", "personal", False,
     [("Hyperlite Mountain Gear", "organization"), ("Dyneema", "technology"), ("quilt", "tool")],
     [],
     "which stuff-sack fabric do I prefer for the quilt and food bag to skip the dry-bag liner",
     "hyperlite mountain gear dyneema stuff sack quilt food dry bag"),
    # --- 4 ---
    ("Switched from a mummy sleeping bag to an Enlightened Equipment Revelation quilt for three-season trips; the open back keeps side-sleepers from fighting hood tension all night.", "decision", "personal", False,
     [("mummy sleeping bag", "tool"), ("Enlightened Equipment Revelation", "tool"), ("quilt", "tool")],
     [("Enlightened Equipment Revelation", "mummy sleeping bag", "REPLACES")],
     "which sleep system replaced the mummy bag for three-season use and what problem did it solve",
     "enlightened equipment revelation quilt mummy bag side sleeper hood"),
    # --- 5 ---
    ("The Tarptent Notch Li is the shelter for shoulder-season Sierra trips; trekking-pole pitch and full double-wall keep condensation off the quilt when temperatures drop into the twenties.", "fact", "personal", False,
     [("Tarptent Notch Li", "tool"), ("Sierra", "place"), ("trekking-pole", "tool")],
     [("Tarptent Notch Li", "Sierra", "APPLIES_TO")],
     "which shelter did I settle on for shoulder-season Sierra trips and what makes its double-wall win",
     "tarptent notch li sierra shoulder season trekking pole double wall"),
    # --- 6 ---
    ("Blew out the calves on a descent of Forester Pass by braking too hard with the quads; switching to a forward-lean chop-step stride cut the soreness in half on the next big drop.", "problem", "personal", False,
     [("Forester Pass", "place"), ("chop-step", "method"), ("quads", "concept")],
     [("chop-step", "Forester Pass", "APPLIES_TO")],
     "which downhill technique fixed the post-Forester-Pass calf blow-out by changing the brake pattern",
     "forester pass descent downhill chop step forward lean brake quad calf"),
    # --- 7 ---
    ("Altra Lone Peak is the default trail shoe for long-distance hiking; the zero-drop platform keeps the toes spread and has survived seven hundred trail miles without the midsole packing out.", "preference", "personal", False,
     [("Altra Lone Peak", "tool"), ("zero-drop", "technology"), ("midsole", "concept")],
     [],
     "which trail shoe stays on my rotation for long-distance hiking and what about the platform wins",
     "altra lone peak zero drop trail shoe long distance midsole pack"),
    # --- 8 ---
    ("Swapped the Altra Lone Peak for a Hoka Speedgoat on the Continental Divide Trail after the Colorado snow patches shredded the Lone Peak outsole on talus.", "decision", "personal", False,
     [("Altra Lone Peak", "tool"), ("Hoka Speedgoat", "tool"), ("Continental Divide Trail", "place"), ("Colorado", "place")],
     [("Hoka Speedgoat", "Altra Lone Peak", "REPLACES"), ("Hoka Speedgoat", "Continental Divide Trail", "APPLIES_TO")],
     "which shoe replaced the Altra on the CDT after Colorado talus chewed up the outsole",
     "altra lone peak hoka speedgoat cdt continental divide colorado talus"),
    # --- 9 ---
    ("Darn Tough Hiker Micro Crew is the only sock that lasted a full Pacific Crest Trail without a blow-out at the heel; the lifetime warranty turned out to be real and the replacement arrived in a week.", "fact", "personal", False,
     [("Darn Tough", "organization"), ("Hiker Micro Crew", "tool"), ("Pacific Crest Trail", "place")],
     [("Darn Tough", "Pacific Crest Trail", "APPLIES_TO")],
     "which sock survived a full PCT without a heel blow-out and how did the warranty play out",
     "darn tough hiker micro crew sock pct warranty heel blow out"),
    # --- 10. noise ---
    ("The neighbour's cat climbed onto the kitchen windowsill at five in the morning and yowled until I opened the blind.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Carry a BearVault BV500 through the Sierra even though the Ursack Major is lighter; the John Muir Trail permit stipulates a hard-sided canister and rangers do spot-checks at Whitney Portal.", "decision", "personal", False,
     [("BearVault BV500", "tool"), ("Ursack Major", "tool"), ("Sierra", "place"), ("John Muir Trail", "place"), ("Whitney Portal", "place")],
     [("BearVault BV500", "Ursack Major", "PREFERS"), ("BearVault BV500", "John Muir Trail", "APPLIES_TO")],
     "why does the BearVault beat the lighter Ursack on the John Muir Trail despite the weight penalty",
     "bearvault bv500 ursack major sierra jmt whitney portal permit"),
    # --- 12 ---
    ("CalTopo is the desk-planning tool and Gaia GPS runs on the phone for in-field navigation; the CalTopo export-to-Gaia workflow saves the night-before route edits without re-tracing.", "architecture", "personal", False,
     [("CalTopo", "tool"), ("Gaia GPS", "tool")],
     [("CalTopo", "Gaia GPS", "APPLIES_TO")],
     "which two-tool navigation stack covers desk planning and in-field GPS and how do they hand off",
     "caltopo gaia gps navigation plan field export route phone workflow"),
    # --- 13 ---
    ("Dropped AllTrails from the planning rotation; the crowd-sourced track quality is inconsistent and two routes put me on illegal cuts across private land in Northern California.", "decision", "personal", False,
     [("AllTrails", "tool"), ("Northern California", "place")],
     [],
     "why did AllTrails get removed from the navigation stack after two Northern California trips",
     "alltrails crowd source track private land illegal route quality drop"),
    # --- 14 ---
    ("The Garmin inReach Mini 2 is the satellite-messenger baseline for solo trips; the MapShare link lets family see the nightly camp without a daily check-in text that I'll forget.", "architecture", "personal", False,
     [("Garmin inReach Mini 2", "tool"), ("MapShare", "service")],
     [("Garmin inReach Mini 2", "MapShare", "USES")],
     "which satellite messenger covers solo-trip check-ins without requiring a daily manual text",
     "garmin inreach mini satellite messenger mapshare solo family check"),
    # --- 15 ---
    ("Suunto 9 Baro is the navigation watch for ultras; the barometric altimeter holds calibration over a forty-hour race while the Coros Vertix 2 drifts past a hundred feet without a manual reset.", "decision", "personal", False,
     [("Suunto 9 Baro", "tool"), ("Coros Vertix 2", "tool"), ("barometric altimeter", "technology")],
     [("Suunto 9 Baro", "Coros Vertix 2", "PREFERS")],
     "which GPS watch wins for multi-day ultras because the altimeter stays calibrated over forty hours",
     "suunto 9 baro coros vertix barometric altimeter ultra forty hour"),
    # --- 16 ---
    ("Tailwind Endurance Fuel is the default drink-mix for anything over four hours; a single scoop per bottle covers calories and electrolytes without the stomach twist I get from gels past hour six.", "fact", "personal", False,
     [("Tailwind Endurance Fuel", "tool"), ("electrolytes", "concept"), ("gels", "tool")],
     [("Tailwind Endurance Fuel", "gels", "PREFERS")],
     "which drink-mix replaces gels past hour six on long efforts without the stomach twist",
     "tailwind endurance fuel drink mix electrolyte scoop gel stomach"),
    # --- 17 ---
    ("Spring Energy Awesome Sauce is the gel I keep in rotation; the real-food base of rice and banana sits lighter than a maltodextrin gel like Gu on hot-weather races.", "preference", "personal", False,
     [("Spring Energy Awesome Sauce", "tool"), ("Gu", "tool"), ("maltodextrin", "concept")],
     [("Spring Energy Awesome Sauce", "Gu", "PREFERS")],
     "which real-food gel beats Gu on hot-weather races and why does the base matter",
     "spring energy awesome sauce gu maltodextrin gel real food hot"),
    # --- 18 ---
    ("LMNT electrolyte tabs went into the vest for desert sections; plain water with a tab every two hours fixed the cramping that plagued the Hat Creek Rim crossing on the last PCT attempt.", "decision", "personal", False,
     [("LMNT", "tool"), ("Hat Creek Rim", "place"), ("PCT", "place")],
     [("LMNT", "Hat Creek Rim", "APPLIES_TO")],
     "which electrolyte tab fixed the cramping on the Hat Creek Rim desert section of the PCT",
     "lmnt electrolyte tab hat creek rim pct desert cramp water vest"),
    # --- 19 ---
    ("Ran UTMB in forty-six hours and change on a conservative nutrition plan; slowing the climbs to keep heart rate under one-forty saved the legs for the last descent to Chamonix.", "milestone", "personal", False,
     [("UTMB", "event"), ("Chamonix", "place")],
     [("UTMB", "Chamonix", "APPLIES_TO")],
     "what was the UTMB finish time and which heart-rate discipline saved the final descent to Chamonix",
     "utmb chamonix forty six hour heart rate climb descent finish ultra"),
    # --- 20 ---
    ("Hardrock 100 qualifier strategy is to run Bear 100 the year before; the altitude overlap and the San Juans-adjacent course give the best chance of adapting before the lottery even runs.", "decision", "personal", False,
     [("Hardrock 100", "event"), ("Bear 100", "event"), ("San Juans", "place")],
     [("Bear 100", "Hardrock 100", "APPLIES_TO")],
     "which qualifier race sets up the Hardrock 100 best because of altitude and terrain overlap",
     "hardrock 100 bear qualifier san juan altitude lottery terrain"),
    # --- 21 ---
    ("The Barkley Marathons is off the bucket list; the course keeps evolving and the petitioner application process is not a race strategy I want to optimise around for years.", "decision", "personal", False,
     [("Barkley Marathons", "event"), ("petitioner", "concept")],
     [],
     "why is the Barkley Marathons off the race goal list despite the obvious appeal",
     "barkley marathons petitioner bucket list course evolve application"),
    # --- 22 ---
    ("Western States entry came through the lottery on the third ticket; running the canyon sections at mile sixty with ice in a bandana kept core temperature manageable in a ninety-degree year.", "milestone", "personal", False,
     [("Western States", "event"), ("canyon sections", "place")],
     [("Western States", "canyon sections", "APPLIES_TO")],
     "what did the Western States lottery take and which cooling trick worked for the hot canyon sections",
     "western states lottery third ticket canyon mile sixty ice bandana"),
    # --- 23 ---
    ("Zone 2 running caps heart rate at one-forty-four based on the lactate test at the university lab; eighty percent of weekly volume sits under that ceiling and long-run paces dropped a minute per mile without extra effort.", "architecture", "personal", False,
     [("Zone 2", "method"), ("lactate test", "method"), ("heart rate", "concept")],
     [],
     "which training method caps weekly volume at eighty percent under one-forty-four heart rate",
     "zone 2 running lactate test heart rate ceiling volume pace drop"),
    # --- 24 ---
    ("The MAF method set the aerobic ceiling at one-fifty by age-based formula; calibration against a lab lactate test showed it sat about five beats high for me, so the floor moved down to match.", "problem", "personal", False,
     [("MAF method", "method"), ("lactate test", "method"), ("aerobic ceiling", "concept")],
     [("MAF method", "lactate test", "IMPROVES_ON")],
     "why did the MAF aerobic ceiling get adjusted down five beats after the lab calibration",
     "maf method aerobic ceiling lactate test five beat calibration age"),
    # --- 25 ---
    ("Elevation training runs go up Mount Tam twice on Saturdays; three thousand feet of gain on trail builds the specific climbing muscle that flat tempo work never touches before a Hardrock attempt.", "architecture", "personal", False,
     [("Mount Tam", "place"), ("Hardrock", "event"), ("climbing muscle", "concept")],
     [("Mount Tam", "Hardrock", "APPLIES_TO")],
     "which weekly elevation workout builds climbing-specific muscle ahead of a Hardrock attempt",
     "mount tam saturday elevation three thousand gain hardrock climbing"),
    # --- 26 ---
    ("Te Araroa remains the open thru-hike plan for the next three-year window; the flip-flop logistics across Cook Strait are the main open question before the southbound start in Bluff.", "milestone", "personal", False,
     [("Te Araroa", "place"), ("Cook Strait", "place"), ("Bluff", "place")],
     [("Te Araroa", "Bluff", "APPLIES_TO")],
     "which thru-hike is still on the three-year plan and which logistic question is still open",
     "te araroa new zealand cook strait bluff south thru hike flip flop"),
    # --- 27 ---
    ("Attempted the GR20 in Corsica last September; the chains on Cirque de la Solitude and the exposure on the Monte Cinto ridge made it the technically hardest European trail I've been on.", "milestone", "personal", False,
     [("GR20", "place"), ("Corsica", "place"), ("Cirque de la Solitude", "place"), ("Monte Cinto", "place")],
     [("GR20", "Corsica", "APPLIES_TO")],
     "which European trail turned out to be the hardest technically and which sections defined it",
     "gr20 corsica cirque solitude monte cinto chain exposure technical"),
    # --- 28 ---
    ("The Tour du Mont Blanc is the fallback trip when a longer thru-hike falls through; the refuges let a light pack carry only a liner and a wind shell without a shelter.", "fact", "personal", False,
     [("Tour du Mont Blanc", "place"), ("refuges", "concept"), ("wind shell", "tool")],
     [("Tour du Mont Blanc", "refuges", "USES")],
     "which multi-day trip is the fallback when a longer thru-hike slot falls through and why",
     "tour du mont blanc tmb refuges light pack liner shelter fallback"),
    # --- 29 ---
    ("The TGO Challenge in Scotland is a coast-to-coast route you plan yourself; the vetting committee approves or rejects the line, which forces a real pre-trip map study rather than following a painted blaze.", "reference", "personal", False,
     [("TGO Challenge", "event"), ("Scotland", "place"), ("vetting committee", "concept")],
     [("TGO Challenge", "Scotland", "APPLIES_TO")],
     "how does the TGO Challenge differ from a signed thru-hike and what does the vetting step enforce",
     "tgo challenge scotland coast to coast vetting committee map study"),
    # --- 30 ---
    ("Six Moons Designs Lunar Solo is the backup shelter when weight is the only constraint; at twenty-six ounces it still pitches tight in wind when the Tarptent is in for seam seal.", "fact", "personal", False,
     [("Six Moons Designs Lunar Solo", "tool"), ("Tarptent", "organization"), ("seam seal", "concept")],
     [("Six Moons Designs Lunar Solo", "Tarptent", "REPLACES")],
     "which backup shelter stands in when the Tarptent is out for seam seal and what does it weigh",
     "six moons designs lunar solo tarptent seam seal shelter backup weight"),
    # --- 31 ---
    ("LiteAF made a custom Curve 42 pack with a bear-canister shelf for the Sierra trips; the extra ten dollars for a hip-belt pocket on the left kept the inReach accessible all day.", "reference", "personal", False,
     [("LiteAF", "organization"), ("Curve 42", "tool"), ("inReach", "tool"), ("Sierra", "place")],
     [("LiteAF", "Sierra", "APPLIES_TO")],
     "which custom pack maker built the Sierra-specific rig and which pocket tweak was worth the upcharge",
     "liteaf curve 42 pack bear canister sierra hip belt pocket inreach"),
    # --- 32 ---
    ("Gossamer Gear Mariposa 60 stays in rotation for longer food carries; the mesh back panel runs hotter than Dyneema packs but the side stretch pocket swallows a bear canister on its side.", "fact", "personal", False,
     [("Gossamer Gear Mariposa 60", "tool"), ("Dyneema", "technology"), ("bear canister", "tool")],
     [],
     "which pack survives long food carries because the side pocket takes a bear canister horizontally",
     "gossamer gear mariposa 60 dyneema bear canister food carry pocket"),
    # --- 33 ---
    ("Big Agnes Copper Spur HV UL2 is the shelter when I hike with a partner; the double-door double-vestibule layout ends the crawling-over-someone problem that killed morale on the AT section hike.", "decision", "personal", False,
     [("Big Agnes Copper Spur HV UL2", "tool"), ("AT", "place")],
     [("Big Agnes Copper Spur HV UL2", "AT", "APPLIES_TO")],
     "which two-person tent won after the crawling-over-a-partner problem ruined morale on the AT",
     "big agnes copper spur hv ul2 at partner double door vestibule"),
    # --- 34 ---
    ("Downhill technique drill is five-minute rock-field descents on the Dipsea steps; landing with a slightly flexed knee and scanning two footfalls ahead cut the quad trashing that used to end long-day runs.", "architecture", "personal", False,
     [("Dipsea", "place"), ("rock-field", "concept"), ("quad", "concept")],
     [("Dipsea", "quad", "APPLIES_TO")],
     "which weekly downhill drill on the Dipsea cut the quad trashing and what did the landing change look like",
     "dipsea steps rock field downhill technique flexed knee footfall quad"),
    # --- 35 ---
    ("Running Salomon S/Lab Pulsar on shorter technical races; the forty-millimeter stack on the Hoka Speedgoat rolls too much on off-camber traverses in the Marin hills.", "decision", "personal", False,
     [("Salomon S/Lab Pulsar", "tool"), ("Hoka Speedgoat", "tool"), ("Marin", "place")],
     [("Salomon S/Lab Pulsar", "Hoka Speedgoat", "PREFERS"), ("Salomon S/Lab Pulsar", "Marin", "APPLIES_TO")],
     "which technical race shoe beats the Speedgoat on off-camber Marin traverses and why",
     "salomon s lab pulsar hoka speedgoat marin off camber technical race"),
    # --- 36 ---
    ("Bear canister weight versus the Ursack trade-off resolved in favour of the canister after a Yosemite bear flattened a hung Ursack overnight; the bag survived but the calories were mulch.", "architecture", "personal", False,
     [("Ursack", "tool"), ("Bear canister", "tool"), ("Yosemite", "place")],
     [("Bear canister", "Ursack", "REPLACES")],
     "why did the bear-canister-versus-Ursack debate finally resolve after a Yosemite night",
     "ursack bear canister yosemite flatten calorie food storage trade"),
    # --- 37 ---
    ("The Continental Divide Trail attempt is parked for a year while the knee rehab finishes; the orthopaedist flagged a patellar tracking issue that descent volume only makes worse.", "milestone", "personal", False,
     [("Continental Divide Trail", "place"), ("knee rehab", "concept"), ("patellar tracking", "concept"), ("orthopaedist", "person")],
     [("patellar tracking", "Continental Divide Trail", "APPLIES_TO")],
     "why is the CDT attempt deferred by a year and which diagnosis drove the decision",
     "continental divide trail cdt knee rehab patellar tracking orthopaedist"),
    # --- 38 ---
    ("Pre-dawn long runs on Saturdays start at four-thirty from the Mill Valley trailhead; the cooler air keeps the heart rate down for the Zone 2 block without an afternoon melt on the fire roads.", "architecture", "personal", False,
     [("Mill Valley", "place"), ("Zone 2", "method"), ("fire roads", "place")],
     [("Zone 2", "Mill Valley", "APPLIES_TO")],
     "which Saturday start-time and trailhead combo keeps the Zone 2 block sustainable in summer",
     "mill valley saturday pre dawn four thirty zone 2 fire road heart"),
    # --- 39 ---
    ("The Coros Vertix 2 stays on the nightstand after the Suunto 9 decision; training load analytics from the Coros still import into TrainingPeaks via the FIT export, so the data doesn't leave the ecosystem.", "fact", "personal", False,
     [("Coros Vertix 2", "tool"), ("Suunto 9", "tool"), ("TrainingPeaks", "service"), ("FIT", "technology")],
     [("Coros Vertix 2", "TrainingPeaks", "USES")],
     "what still uses the benched Coros Vertix 2 after the Suunto switch and how does data flow",
     "coros vertix 2 suunto 9 trainingpeaks fit export training load"),
    # --- 40 ---
    ("Gu Roctane caffeinated gels are the emergency backup at aid stations; not the default fuel but useful when the stomach closes on Tailwind and plain sugar is the only thing that stays down.", "reference", "personal", False,
     [("Gu Roctane", "tool"), ("Tailwind", "tool"), ("caffeinated", "concept")],
     [],
     "which gel is the emergency fuel when Tailwind stops sitting well mid-race",
     "gu roctane caffeinated tailwind emergency aid station stomach close"),
    # --- 41 ---
    ("Ice-bandana cooling during Western States canyon sections: soak a bandana in a creek, pack it with ice from the aid-station cooler, and wrap it around the neck over the carotids for ten degrees of apparent cooling.", "reference", "personal", False,
     [("Ice-bandana", "method"), ("Western States", "event"), ("carotids", "concept")],
     [("Ice-bandana", "Western States", "APPLIES_TO")],
     "what is the ice-bandana method that made the Western States canyons survivable",
     "ice bandana western states canyon carotid cool aid station creek"),
    # --- 42 ---
    ("The altitude protocol for Hardrock is four weeks at Silverton in a rental plus sleep-high-train-low shuttles up Kendall; the one-week crash camp attempt two years ago did not close the gap.", "architecture", "personal", False,
     [("Hardrock", "event"), ("Silverton", "place"), ("Kendall", "place"), ("sleep-high-train-low", "method")],
     [("Silverton", "Hardrock", "APPLIES_TO")],
     "which altitude acclimatisation protocol replaces the one-week crash camp for Hardrock prep",
     "hardrock silverton kendall sleep high train low altitude four week"),
    # --- 43. noise ---
    ("The downstairs dishwasher stopped draining and the repair guy rescheduled twice before finally clearing the impeller on a Thursday.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Trekking poles are Black Diamond Distance Carbon Z; the fixed-length Z-fold deploys in two seconds at the top of a climb and weighs less than the Leki adjustables I retired last year.", "preference", "personal", False,
     [("Black Diamond Distance Carbon Z", "tool"), ("Leki", "organization"), ("Z-fold", "technology")],
     [("Black Diamond Distance Carbon Z", "Leki", "PREFERS")],
     "which trekking pole replaced the Leki adjustables and what about the fold matters",
     "black diamond distance carbon z leki z fold trekking pole fixed"),
    # --- 45 ---
    ("Navigation-watch discipline during ultras is to ignore pace on the climb screen and watch only heart rate and grade-adjusted pace; the raw pace number triggered pushing hard up Green Gate on a bad year.", "reference", "personal", False,
     [("Navigation-watch", "tool"), ("grade-adjusted pace", "concept"), ("Green Gate", "place")],
     [("grade-adjusted pace", "Green Gate", "APPLIES_TO")],
     "which two watch metrics should be the only ones on the climb screen during a race, and why",
     "navigation watch climb heart rate grade adjusted pace green gate"),
    # --- 46 ---
    ("The Appalachian Trail section-hike plan for the next two years is Harper's Ferry to Mount Washington; the New Hampshire whites are the technical part and the timing has to dodge black-fly season in June.", "milestone", "personal", False,
     [("Appalachian Trail", "place"), ("Harper's Ferry", "place"), ("Mount Washington", "place"), ("New Hampshire", "place")],
     [("Appalachian Trail", "Mount Washington", "APPLIES_TO")],
     "which AT section is on the two-year plan and which seasonal hazard sets the window",
     "appalachian trail section harper ferry mount washington new hampshire"),
    # --- 47 ---
    ("Backup headlamp is a Nitecore NU25 clipped to the hip belt; the rechargeable main is a Petzl Swift RL but the Nitecore weighs less than an ounce and has saved two night descents when the main battery died.", "architecture", "personal", False,
     [("Nitecore NU25", "tool"), ("Petzl Swift RL", "tool")],
     [("Nitecore NU25", "Petzl Swift RL", "APPLIES_TO")],
     "which backup headlamp rides the hip belt in case the Petzl main dies on a night descent",
     "nitecore nu25 petzl swift rl headlamp backup hip belt night"),
    # --- 48 ---
    ("Skurka-style under-quilt-free setup for summer thru-hikes uses a CCF pad under the Revelation quilt; the Neoair XLite is warmer but fails catastrophically on a talus campsite the one time it matters.", "decision", "personal", False,
     [("CCF pad", "tool"), ("Neoair XLite", "tool"), ("Revelation", "tool")],
     [("CCF pad", "Neoair XLite", "PREFERS")],
     "which sleeping pad wins for summer thru-hikes despite being colder than the Neoair XLite",
     "ccf pad neoair xlite revelation quilt summer thru hike puncture"),
    # --- 49 ---
    ("CalTopo layer preset for off-trail navigation stacks USGS quads, slope-angle shading, and MapBuilder Topo; the slope layer highlights avalanche-angle terrain on spring corn-snow exits from the Sierra high country.", "reference", "personal", False,
     [("CalTopo", "tool"), ("USGS quads", "technology"), ("slope-angle", "concept"), ("MapBuilder Topo", "technology"), ("Sierra", "place")],
     [("CalTopo", "Sierra", "APPLIES_TO")],
     "which CalTopo layer preset covers off-trail Sierra planning and why does slope shading matter",
     "caltopo usgs quad slope angle mapbuilder topo sierra avalanche"),
    # --- 50 ---
    ("Race-week taper rule: cut volume by fifty percent and keep intensity at two short threshold sessions; the old long-run-on-Wednesday taper left the legs heavy at the UTMB start line and cost an hour over the first climb.", "problem", "personal", False,
     [("taper", "method"), ("threshold", "method"), ("UTMB", "event")],
     [("taper", "UTMB", "APPLIES_TO")],
     "which taper rule replaced the long-run-on-Wednesday taper after the UTMB first-climb blow-up",
     "taper race week volume threshold utmb long run wednesday heavy legs"),
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
