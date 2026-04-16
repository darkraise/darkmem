"""One-off emitter for shared-base batch-201 — personal domain (fermentation: kimchi, miso, koji, SCOBY, kefir, cheese, lacto-ferments).

Writes 50 rows to data/v2/shared/batch_201.tmp.jsonl with ids shared-10001..10050.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_201.tmp.jsonl"
ID_OFFSET = 10000

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1. decision ---
    ("Settled on baechu kimchi as the household default after a three-month bake-off against kkakdugi and gat; the napa leaves hold brine better and the family actually eats it down.", "decision", "personal", False,
     [("baechu kimchi", "food"), ("kkakdugi", "food"), ("gat", "food"), ("napa", "food")],
     [("baechu kimchi", "kkakdugi", "PREFERS"), ("baechu kimchi", "gat", "PREFERS")],
     "which kimchi style became the household staple after comparing napa against radish and mustard green versions",
     "baechu napa kimchi kkakdugi gat household default bake off"),
    # --- 2. architecture ---
    ("The fermentation corner in the pantry is laid out as three temperature zones: a 4 C kimchi fridge, a 20 C counter shelf for miso and shoyu, and a 28 C warming cabinet for koji and natto.", "architecture", "personal", False,
     [("kimchi fridge", "tool"), ("counter shelf", "place"), ("warming cabinet", "tool"), ("miso", "food"), ("shoyu", "food"), ("koji", "food"), ("natto", "food")],
     [("warming cabinet", "koji", "APPLIES_TO"), ("warming cabinet", "natto", "APPLIES_TO")],
     "how is the home fermentation setup partitioned by temperature across the pantry",
     "fermentation pantry zone temperature kimchi fridge counter warming cabinet"),
    # --- 3. milestone ---
    ("First successful Aspergillus oryzae koji run hit full bloom on the 46th hour; the rice smelled of chestnut and sweet melon exactly like Sandor Katz described in The Art of Fermentation.", "milestone", "personal", False,
     [("Aspergillus oryzae", "concept"), ("koji", "food"), ("Sandor Katz", "person"), ("The Art of Fermentation", "publication")],
     [("The Art of Fermentation", "Sandor Katz", "AUTHORED_BY"), ("koji", "Aspergillus oryzae", "USES")],
     "when did the first koji inoculation reach bloom and which reference matched the aroma description",
     "aspergillus oryzae koji bloom 46 hour sandor katz art fermentation"),
    # --- 4. fact ---
    ("White shiro miso uses a high koji-to-soybean ratio and ferments in weeks, while hatcho miso is nearly all soybean and sits for two summers in cedar barrels weighted with river stones.", "fact", "personal", False,
     [("shiro miso", "food"), ("hatcho miso", "food"), ("koji", "food"), ("cedar barrels", "tool")],
     [("shiro miso", "koji", "USES"), ("hatcho miso", "cedar barrels", "USES")],
     "what distinguishes white miso from hatcho in terms of ratio and aging vessel",
     "shiro hatcho miso koji soybean ratio cedar barrel summer age"),
    # --- 5. decision ---
    ("Chose a 2.5 percent brine by weight for the sauerkraut crock this autumn; 2 percent was slipping kahm yeast by day four and 3 percent dulled the cabbage sweetness too aggressively.", "decision", "personal", False,
     [("2.5 percent brine", "concept"), ("sauerkraut", "food"), ("kahm yeast", "concept")],
     [("2.5 percent brine", "kahm yeast", "FIXES")],
     "which brine concentration landed as the sauerkraut sweet spot and which failure modes were on either side",
     "sauerkraut brine 2.5 percent kahm yeast cabbage autumn crock"),
    # --- 6. architecture ---
    ("The crock lineup uses Harsch-style water-seal airlocks for all lacto-fermented vegetables; the water channel around the lid stays anaerobic without me babysitting the weight stones daily.", "architecture", "personal", False,
     [("Harsch", "organization"), ("water-seal airlocks", "tool"), ("lacto-fermented vegetables", "food"), ("weight stones", "tool")],
     [("water-seal airlocks", "lacto-fermented vegetables", "APPLIES_TO")],
     "which airlock style handles the lacto vegetable crocks and how does it stay anaerobic without daily check-ins",
     "harsch water seal airlock crock lacto vegetable anaerobic weight"),
    # --- 7. preference ---
    ("Prefer mesophilic yogurt cultures over thermophilic for the kitchen counter; the 22 C room holds a mesophilic set overnight without a heating pad and the tang is milder than Bulgarian yogurt out of a Sofia farm culture.", "preference", "personal", False,
     [("mesophilic", "concept"), ("thermophilic", "concept"), ("yogurt", "food"), ("Bulgarian yogurt", "food")],
     [("mesophilic", "thermophilic", "PREFERS")],
     "which yogurt culture class wins for counter incubation and how does the flavour compare to Bulgarian",
     "mesophilic thermophilic yogurt counter bulgarian tang heating pad"),
    # --- 8. problem ---
    ("The kombucha SCOBY went pellicle-thin and sour after the kitchen dropped to 17 C; moving the jar onto the seed-mat shelf at 24 C restored the yeast balance within two cycles.", "problem", "personal", False,
     [("kombucha SCOBY", "food"), ("pellicle", "concept"), ("seed-mat shelf", "tool")],
     [("seed-mat shelf", "kombucha SCOBY", "APPLIES_TO")],
     "what caused the kombucha pellicle to thin out and which placement change fixed the yeast balance",
     "kombucha scoby pellicle thin sour 17 seed mat shelf yeast"),
    # --- 9. reference ---
    ("The Noma Guide to Fermentation by David Zilber is the primary reference for the lacto-fruit experiments; the blueberry lacto step count and target pH of 3.8 come straight from that book.", "reference", "personal", False,
     [("The Noma Guide to Fermentation", "publication"), ("David Zilber", "person"), ("lacto-fruit", "food"), ("pH of 3.8", "concept")],
     [("The Noma Guide to Fermentation", "David Zilber", "AUTHORED_BY")],
     "which book and target pH anchor the lacto-fruit experiments at home",
     "noma guide fermentation zilber lacto fruit blueberry ph 3.8"),
    # --- 10. noise ---
    ("The neighbour's tabby keeps sitting on the pantry windowsill and judging the bubbling crocks with unbroken suspicion.", "fact", "noise", True, [], [], None, None),
    # --- 11. decision ---
    ("Switched the starter for the alpine tomme from a generic mesophilic starter blend to a dedicated Thermo C culture; the rind tightened up and the paste stopped weeping on week three.", "decision", "personal", False,
     [("alpine tomme", "food"), ("mesophilic starter", "concept"), ("Thermo C", "concept")],
     [("Thermo C", "mesophilic starter", "REPLACES")],
     "which culture swap fixed the alpine tomme rind and paste issues",
     "alpine tomme mesophilic thermo c starter rind paste weep"),
    # --- 12. fact ---
    ("Roquefortii blue cheese mould only gets a foothold if the curd is needled at day ten and the cave humidity holds at 95 percent; below that the veins come in patchy and white.", "fact", "personal", False,
     [("Roquefortii", "concept"), ("blue cheese", "food"), ("needled", "method"), ("cave", "place")],
     [("needled", "Roquefortii", "APPLIES_TO")],
     "which two cave conditions determine whether blue cheese veins develop evenly",
     "roquefortii blue cheese needle day 10 cave humidity 95 vein"),
    # --- 13. milestone ---
    ("Finished building the cheese cave this spring out of a converted wine fridge with a humidifier wick tray and a PID-controlled heater; it now holds 12 C and 92 percent RH within a degree and two points of humidity.", "milestone", "personal", False,
     [("cheese cave", "place"), ("wine fridge", "tool"), ("humidifier wick tray", "tool"), ("PID-controlled heater", "tool")],
     [("PID-controlled heater", "cheese cave", "APPLIES_TO")],
     "how is the home cheese cave engineered to hold tight temperature and humidity",
     "cheese cave wine fridge humidifier pid heater 12 c 92 humidity"),
    # --- 14. milestone ---
    ("Finished the first 18-month hatcho miso in the back of the cedar cabinet; the paste cut like firm chocolate and the tamari layer on top filled a full 200 ml jar.", "milestone", "personal", False,
     [("hatcho miso", "food"), ("cedar cabinet", "tool"), ("tamari", "food")],
     [("hatcho miso", "tamari", "PRODUCES")],
     "when did the first long-aged hatcho reach maturity and what byproduct did the surface give up",
     "hatcho miso 18 month cedar cabinet tamari 200 ml jar"),
    # --- 15. decision ---
    ("Chose aka miso over shiro miso for daily soup stock; the longer ferment carries the dashi better and the umami depth survives a rolling boil, which the white variety never quite does.", "decision", "personal", False,
     [("aka miso", "food"), ("shiro miso", "food"), ("dashi", "food")],
     [("aka miso", "shiro miso", "PREFERS"), ("aka miso", "dashi", "APPLIES_TO")],
     "which miso style earned the daily soup slot and why does white miso lose out",
     "aka miso shiro dashi soup stock rolling boil umami depth"),
    # --- 16. architecture ---
    ("The natto incubator is a Styrofoam box with a seed-starter heat mat underneath and a damp towel draped over the soybeans; it holds 40 C through the twenty-hour stretch without a thermostat.", "architecture", "personal", False,
     [("natto", "food"), ("Styrofoam box", "tool"), ("seed-starter heat mat", "tool"), ("soybeans", "food")],
     [("seed-starter heat mat", "natto", "APPLIES_TO")],
     "how is the diy natto incubator built and how does it hold 40 C without a thermostat",
     "natto styrofoam seed heat mat soybean 40 c twenty hour damp"),
    # --- 17. milestone ---
    ("Hit the 100th loaf with the rye sourdough starter that branched off the kombucha SCOBY yeast bank; the same ambient microflora has been reliably doubling on a 12-hour feed for nine months straight.", "milestone", "personal", False,
     [("rye sourdough", "food"), ("kombucha SCOBY", "food"), ("12-hour feed", "concept")],
     [("rye sourdough", "kombucha SCOBY", "BUILDS_ON")],
     "what ferment anniversary did the rye starter hit and what feed cadence has held the culture stable",
     "rye sourdough 100 loaf kombucha yeast 12 hour feed double"),
    # --- 18. decision ---
    ("Picked water kefir grains over milk kefir for the afternoon drink rotation; lactose-free households around here mean the sugar-brine grains just work for everybody without a separate batch.", "decision", "personal", False,
     [("water kefir", "food"), ("milk kefir", "food")],
     [("water kefir", "milk kefir", "PREFERS")],
     "which kefir style won the drink rotation and what household constraint drove the choice",
     "water kefir milk kefir lactose free sugar brine grain rotation"),
    # --- 19. fact ---
    ("A healthy jar of milk kefir grains self-regulates to roughly 10 percent of the jar's liquid volume if fed daily; past that they slow down and start rejecting the extra mass as loose curd on the strainer.", "fact", "personal", False,
     [("milk kefir", "food"), ("grains", "food"), ("strainer", "tool")],
     [],
     "how do milk kefir grains self-regulate their mass relative to the feeding volume",
     "milk kefir grain 10 percent volume self regulate strainer loose"),
    # --- 20. architecture ---
    ("The gochujang fermentation rig is a single onggi pot on the sunny balcony with a muslin cover; direct sun and ambient temperature swing drive a layered character the indoor jars never match.", "architecture", "personal", False,
     [("gochujang", "food"), ("onggi", "tool"), ("balcony", "place"), ("muslin cover", "tool")],
     [("onggi", "gochujang", "APPLIES_TO")],
     "how is the gochujang set up outdoors and why does the balcony placement beat an indoor jar",
     "gochujang onggi balcony muslin cover sun layered indoor"),
    # --- 21. decision ---
    ("Bought a second onggi this year specifically for doenjang; keeping it separate from gochujang avoided the chili pigment bleeding into the soybean paste through the porous clay.", "decision", "personal", False,
     [("onggi", "tool"), ("doenjang", "food"), ("gochujang", "food")],
     [("onggi", "doenjang", "APPLIES_TO")],
     "why did the house need a second onggi and what cross-contamination did it prevent",
     "onggi doenjang gochujang chili pigment soybean porous clay"),
    # --- 22. reference ---
    ("Sandor Katz's Wild Fermentation has the sauerkraut chapter that taught me to salt cabbage by weight rather than by eye; the 2 percent by mass rule is pencilled on the inside of the pantry door.", "reference", "personal", False,
     [("Sandor Katz", "person"), ("Wild Fermentation", "publication"), ("sauerkraut", "food"), ("2 percent by mass", "concept")],
     [("Wild Fermentation", "Sandor Katz", "AUTHORED_BY")],
     "which book and rule converted the sauerkraut process from eyeballing to weighing",
     "sandor katz wild fermentation sauerkraut 2 percent salt weight"),
    # --- 23. problem ---
    ("The cortido batch turned unusably soft after I used table salt with anti-caking agents; the iodide inhibited the Lactobacillus plantarum and the cabbage went mushy instead of crisp.", "problem", "personal", False,
     [("cortido", "food"), ("table salt", "concept"), ("anti-caking agents", "concept"), ("Lactobacillus plantarum", "concept")],
     [("anti-caking agents", "Lactobacillus plantarum", "CONTRADICTS")],
     "what salt choice wrecked the cortido texture and which microbe got inhibited",
     "cortido table salt anti caking iodide lactobacillus plantarum mushy"),
    # --- 24. fact ---
    ("A jar of torshi liteh builds its heat from whole garlic cloves submerged in a 5 percent brine with dried chili; the pH drops below 4.0 by day seven and it keeps for a year on the pantry shelf.", "fact", "personal", False,
     [("torshi liteh", "food"), ("5 percent brine", "concept"), ("pH", "concept"), ("pantry shelf", "place")],
     [],
     "what brine concentration and pH target define the torshi liteh preservation profile",
     "torshi liteh 5 percent brine garlic chili ph 4 day seven"),
    # --- 25. decision ---
    ("Switched the tempeh incubator substrate from banana leaf to perforated plastic bags; Rhizopus oligosporus mycelium knits denser on the plastic surface and the cake cuts cleaner for frying.", "decision", "personal", False,
     [("tempeh", "food"), ("banana leaf", "tool"), ("perforated plastic bags", "tool"), ("Rhizopus oligosporus", "concept")],
     [("perforated plastic bags", "banana leaf", "REPLACES"), ("Rhizopus oligosporus", "tempeh", "USES")],
     "which substrate change tightened the tempeh mycelium cake for slicing",
     "tempeh banana leaf perforated plastic rhizopus oligosporus cut"),
    # --- 26. architecture ---
    ("The amazake workflow runs overnight: warm cooked rice, stir in koji at 55 C, wrap in a down sleeping bag with a 60 C water bottle, and unwrap in the morning to a sweet porridge.", "architecture", "personal", False,
     [("amazake", "food"), ("koji", "food"), ("down sleeping bag", "tool"), ("water bottle", "tool")],
     [("amazake", "koji", "USES")],
     "how does the overnight amazake process hold 55 C without a dedicated incubator",
     "amazake koji 55 c down sleeping bag water bottle overnight rice"),
    # --- 27. milestone ---
    ("Brewed a drinkable home sake for the first time on the fourth attempt; the moromi hit 16 percent ABV and pressed out clear, with the lees becoming the next amazake base.", "milestone", "personal", False,
     [("sake", "food"), ("moromi", "food"), ("amazake", "food"), ("lees", "food")],
     [("amazake", "lees", "BUILDS_ON")],
     "which attempt produced the first drinkable home sake and what downstream ferment did the lees feed",
     "sake fourth attempt moromi 16 abv lees amazake clear press"),
    # --- 28. decision ---
    ("Chose vegetarian microbial rennet over animal rennet for the household cheese; the alpine tomme set cleanly at 32 C and nobody asked for the traditional curdling agent instead.", "decision", "personal", False,
     [("microbial rennet", "concept"), ("animal rennet", "concept"), ("alpine tomme", "food")],
     [("microbial rennet", "animal rennet", "PREFERS")],
     "which rennet style did the household cheese work land on and did the set quality suffer",
     "microbial rennet animal vegetarian alpine tomme 32 c household"),
    # --- 29. fact ---
    ("The cheddaring step at home works on a tilted stainless pan with a warm water jacket under it; stacking and restacking the curd slabs every ten minutes at 38 C drives the whey out evenly.", "fact", "personal", False,
     [("cheddaring", "method"), ("stainless pan", "tool"), ("water jacket", "tool"), ("curd slabs", "food")],
     [("cheddaring", "curd slabs", "APPLIES_TO")],
     "how is the cheddaring stack set up at home and which temperature drives the whey out",
     "cheddaring stainless pan water jacket 38 c curd slab stack whey"),
    # --- 30. fact ---
    ("A pot of baekkimchi uses no gochugaru at all; flavour comes from Asian pear, ginger, garlic, and a small amount of fish sauce, with chestnut slivers layered between leaves for textural contrast.", "fact", "personal", False,
     [("baekkimchi", "food"), ("gochugaru", "food"), ("Asian pear", "food"), ("fish sauce", "food")],
     [],
     "which ingredients carry baekkimchi's flavour given the absence of red chili powder",
     "baekkimchi white kimchi asian pear ginger garlic fish sauce chestnut"),
    # --- 31. preference ---
    ("Prefer fermenting kkakdugi in small quart jars rather than the big crock; the daikon cubes stay in contact with the brine and I can open just one jar at a time for the week.", "preference", "personal", False,
     [("kkakdugi", "food"), ("quart jars", "tool"), ("crock", "tool"), ("daikon", "food")],
     [("quart jars", "crock", "PREFERS")],
     "why do small jars beat the crock for radish kimchi in this household",
     "kkakdugi quart jar crock daikon brine week single serve"),
    # --- 32. preference ---
    ("Prefer to include both leaves and stems of the mustard-green when making gat kimchi; a stems-only batch came out bitter and sharp, and the leaves clearly carry most of the round flavour the ferment needs.", "preference", "personal", False,
     [("gat kimchi", "food"), ("mustard-green", "food"), ("stems", "food"), ("leaves", "food")],
     [],
     "what part of the mustard green cannot be skipped when making gat kimchi",
     "gat kimchi mustard green stem leaf bitter sharp depth batch"),
    # --- 33. decision ---
    ("Standardised on a 2 percent brine by weight for all baechu kimchi; the six-hour wilt step lands consistently and the main ferment finishes predictably in 72 hours at 20 C.", "decision", "personal", False,
     [("2 percent brine", "concept"), ("baechu kimchi", "food"), ("wilt step", "method")],
     [("2 percent brine", "baechu kimchi", "APPLIES_TO")],
     "which brine-by-weight standard did the baechu kimchi settle on and what timing follows from it",
     "baechu kimchi 2 percent brine six hour wilt 72 hour 20 c"),
    # --- 34. reference ---
    ("David Zilber's lacto-blueberry recipe in the Noma Guide to Fermentation is the template for every fruit lacto experiment here; 2 percent salt, room temperature, and a taste check every day past day four.", "reference", "personal", False,
     [("David Zilber", "person"), ("Noma Guide to Fermentation", "publication"), ("lacto-blueberry", "food"), ("2 percent salt", "concept")],
     [("Noma Guide to Fermentation", "David Zilber", "AUTHORED_BY")],
     "whose recipe and which check cadence anchor the fruit lacto experiments in this kitchen",
     "zilber noma lacto blueberry 2 percent salt room temp day four"),
    # --- 35. milestone ---
    ("Noma's fermentation lab inspired the barley koji experiment that finally produced a drinkable barley shoyu at home; the final press gave 1.2 litres and the colour matched a light usukuchi.", "milestone", "personal", False,
     [("Noma", "organization"), ("barley koji", "food"), ("barley shoyu", "food"), ("usukuchi", "food")],
     [("barley shoyu", "barley koji", "USES")],
     "which Noma-inspired koji project ended in a drinkable home shoyu and how much did the press yield",
     "noma barley koji shoyu usukuchi 1.2 litre press home"),
    # --- 36. architecture ---
    ("The shoyu moromi tank is a food-grade HDPE barrel with a loose lid and a wooden paddle stuck in; the weekly stir keeps the mash oxygenated through the first three months before it settles.", "architecture", "personal", False,
     [("shoyu", "food"), ("moromi", "food"), ("HDPE barrel", "tool"), ("wooden paddle", "tool")],
     [("HDPE barrel", "shoyu", "APPLIES_TO")],
     "how is the shoyu moromi vessel set up and what weekly maintenance keeps it oxygenated",
     "shoyu moromi hdpe barrel wooden paddle weekly stir oxygen"),
    # --- 37. problem ---
    ("Early natto batches kept failing at the 40 C target until I switched from city tap water to filtered water; the chloramine was knocking back Bacillus subtilis and the beans never hit the stringy threads.", "problem", "personal", False,
     [("natto", "food"), ("chloramine", "concept"), ("Bacillus subtilis", "concept"), ("filtered water", "tool")],
     [("chloramine", "Bacillus subtilis", "CONTRADICTS")],
     "what water-quality issue sabotaged the natto batches and which microbe suffered",
     "natto chloramine bacillus subtilis filtered tap 40 c string"),
    # --- 38. decision ---
    ("Moved the kimchi fridge dedicated thermostat to 2 C after the fall batch; the slower post-fermentation holds the crunch and the carbonation finishes mellow rather than sharp.", "decision", "personal", False,
     [("kimchi fridge", "tool"), ("thermostat", "tool"), ("post-fermentation", "concept")],
     [("kimchi fridge", "post-fermentation", "APPLIES_TO")],
     "which fridge temperature set-point wins for post-fermentation kimchi and what flavour trade-off drives it",
     "kimchi fridge thermostat 2 c post fermentation crunch carbonation"),
    # --- 39. architecture ---
    ("Jars of lacto-fermented vegetables get a follower disc cut from a food-grade HDPE lid to keep solids submerged, and a fermentation-lock lid on top that vents CO2 without inviting oxygen back in.", "architecture", "personal", False,
     [("lacto-fermented vegetables", "food"), ("follower disc", "tool"), ("HDPE lid", "tool"), ("fermentation-lock lid", "tool")],
     [("fermentation-lock lid", "lacto-fermented vegetables", "APPLIES_TO")],
     "which two-part lid system keeps lacto-ferment jars anaerobic without manual burping",
     "follower disc hdpe fermentation lock vent co2 lacto vegetable"),
    # --- 40. reference ---
    ("The Sandor Katz SCOBY hotel guide convinced me to keep two reserve kombucha SCOBY mats in a separate jar with 15 percent starter liquid; a contaminated primary now gets replaced within one brew cycle.", "reference", "personal", False,
     [("Sandor Katz", "person"), ("SCOBY hotel", "concept"), ("kombucha SCOBY", "food"), ("15 percent starter", "concept")],
     [("SCOBY hotel", "Sandor Katz", "AUTHORED_BY")],
     "whose reserve-culture guidance shapes the SCOBY hotel and what ratio does it pin",
     "sandor katz scoby hotel kombucha 15 percent starter reserve"),
    # --- 41. decision ---
    ("Picked the 28 C warming cabinet over a dehydrator for koji incubation; the cabinet holds humidity naturally while a dehydrator dried the rice out within the first six hours every time.", "decision", "personal", False,
     [("warming cabinet", "tool"), ("dehydrator", "tool"), ("koji", "food")],
     [("warming cabinet", "dehydrator", "REPLACES")],
     "which koji incubator won against the dehydrator and why",
     "warming cabinet dehydrator koji 28 c humidity rice dry"),
    # --- 42. milestone ---
    ("Logged batch 50 of baechu kimchi this month; the spreadsheet tracks brine percent, wilt time, ferment temperature, and a tasting note, and the trend-line finally shows consistent timing.", "milestone", "personal", False,
     [("baechu kimchi", "food"), ("spreadsheet", "tool"), ("tasting note", "concept")],
     [],
     "which kimchi milestone hit this month and what does the logging spreadsheet capture",
     "baechu kimchi batch 50 spreadsheet brine wilt ferment tasting"),
    # --- 43. noise ---
    ("A jar of lemon curd fell off the top shelf and painted the pantry floor yellow from corner to corner on a Tuesday morning.", "fact", "noise", True, [], [], None, None),
    # --- 44. preference ---
    ("Prefer Bulgarian yogurt to the mesophilic strain for breakfast; the Lactobacillus bulgaricus tang cuts through honey and the thicker set carries granola without the spoon sinking.", "preference", "personal", False,
     [("Bulgarian yogurt", "food"), ("mesophilic", "concept"), ("Lactobacillus bulgaricus", "concept"), ("granola", "food")],
     [("Bulgarian yogurt", "mesophilic", "PREFERS"), ("Bulgarian yogurt", "Lactobacillus bulgaricus", "USES")],
     "which yogurt strain wins for breakfast and what structural quality matters with granola",
     "bulgarian yogurt mesophilic lactobacillus bulgaricus honey granola"),
    # --- 45. architecture ---
    ("The cheese press at home is a stacked plate setup with a 5 kg water jug on top of a hardwood follower; pressure increments come from swapping the jug for a 10 kg and then a 15 kg over eight hours.", "architecture", "personal", False,
     [("cheese press", "tool"), ("plate setup", "tool"), ("water jug", "tool"), ("hardwood follower", "tool")],
     [("water jug", "cheese press", "APPLIES_TO")],
     "how is the home cheese press built and what pressure ramp does it walk through",
     "cheese press plate water jug hardwood follower 5 10 15 kg"),
    # --- 46. fact ---
    ("Traditional hatcho miso weighs the cedar barrel with a tower of river stones totalling about one-third of the mash weight; the slow compression expresses tamari throughout the two-year ferment.", "fact", "personal", False,
     [("hatcho miso", "food"), ("cedar barrel", "tool"), ("river stones", "tool"), ("tamari", "food")],
     [("river stones", "hatcho miso", "APPLIES_TO"), ("hatcho miso", "tamari", "PRODUCES")],
     "which traditional weighting method drives tamari expression during a long hatcho ferment",
     "hatcho cedar barrel river stone one third weight tamari two year"),
    # --- 47. decision ---
    ("Adopted a strict pH meter check on every lacto batch at day three; taste-based judgement was missing early kahm blooms and the meter catches anything above 4.2 before it matters.", "decision", "personal", False,
     [("pH meter", "tool"), ("lacto batch", "food"), ("kahm", "concept"), ("4.2", "concept")],
     [("pH meter", "kahm", "FIXES")],
     "which instrument replaced taste judgement on lacto ferments and what threshold does it flag",
     "ph meter lacto day three kahm bloom 4.2 threshold taste"),
    # --- 48. architecture ---
    ("Sourdough and the kombucha SCOBY share a shelf but never a utensil; a colour-coded spoon system (red for kombucha, blue for sourdough) prevents cross-culture swaps from contaminating either starter.", "architecture", "personal", False,
     [("sourdough", "food"), ("kombucha SCOBY", "food"), ("colour-coded spoon", "tool")],
     [("colour-coded spoon", "sourdough", "APPLIES_TO")],
     "which low-tech system stops cross-contamination between the sourdough and kombucha shelf",
     "sourdough kombucha shelf colour code spoon red blue cross contaminate"),
    # --- 49. reference ---
    ("A local fermentation workshop run by a Noma alumnus drilled in the concept of fermenting by smell and pH curve first, taste second; the house pH log now always predates the taste log.", "reference", "personal", False,
     [("fermentation workshop", "activity"), ("Noma", "organization"), ("pH curve", "concept"), ("taste log", "concept")],
     [("fermentation workshop", "Noma", "RELATED_TO")],
     "which workshop-taught habit re-ordered how the kitchen evaluates a ferment each day",
     "fermentation workshop noma smell ph curve taste log order"),
    # --- 50. reference ---
    ("The Fermentation Journal by Sandor Katz is the logbook template on the pantry shelf; each page has fields for date, substrate, salt percent, temperature, pH, and tasting notes, and the stack goes back three years.", "reference", "personal", False,
     [("The Fermentation Journal", "publication"), ("Sandor Katz", "person"), ("logbook", "tool"), ("pantry shelf", "place")],
     [("The Fermentation Journal", "Sandor Katz", "AUTHORED_BY")],
     "which logbook template organises the home ferment records and which fields does each page carry",
     "fermentation journal katz logbook pantry date substrate salt ph"),
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
