"""One-off emitter for shared-base batch-200 — personal domain (baking: sourdough starter, levain, bulk ferment, shaping, cold retard, Dutch oven, laminated doughs — croissants, pain au chocolat, kouign-amann, panettone).

Writes 50 rows to data/v2/shared/batch_200.tmp.jsonl with ids shared-09951..10000.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_200.tmp.jsonl"
ID_OFFSET = 9950

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Switched the weekday starter feed from the old 1:1:1 ratio to a 1:5:5 refresh eight hours before the levain build; the peak window now lines up with my evening mix and the starter smells like yogurt instead of acetone.", "decision", "personal", False,
     [("starter", "food"), ("1:1:1", "concept"), ("1:5:5", "concept"), ("levain", "food")],
     [("1:5:5", "1:1:1", "REPLACES"), ("starter", "levain", "PRODUCES")],
     "which starter feeding ratio replaced the 1:1:1 refresh and how did it change the evening mix timing",
     "starter feed ratio 1:5:5 levain peak evening mix yogurt"),
    # --- 2 architecture ---
    ("The weekend loaf now runs as a three-stage build: levain from the rye-boosted starter the night before, one-hour autolyse with T65 and water at twenty-six degrees, then bulk fermentation with four stretch-and-folds at forty-five-minute intervals.", "architecture", "personal", False,
     [("levain", "food"), ("rye-boosted starter", "food"), ("autolyse", "method"), ("T65", "food"), ("bulk fermentation", "method"), ("stretch-and-fold", "method")],
     [("levain", "rye-boosted starter", "BUILDS_ON"), ("bulk fermentation", "stretch-and-fold", "USES")],
     "which three-stage process does the weekend loaf follow from levain through bulk fermentation",
     "levain rye autolyse t65 bulk ferment stretch fold weekend loaf"),
    # --- 3 fact ---
    ("The house hydration for the country loaf settled at seventy-eight percent after a summer of mushy bases; the crumb stays open without the dough spilling out of the banneton during cold retard.", "fact", "personal", False,
     [("hydration", "concept"), ("country loaf", "food"), ("banneton", "tool"), ("cold retard", "method")],
     [("country loaf", "banneton", "USES")],
     "which hydration level did the country loaf land on and what problem did lowering it from summer levels solve",
     "hydration seventy eight percent country loaf banneton cold retard crumb"),
    # --- 4 reference ---
    ("Chad Robertson's Tartine Bread is still the reference for the basic country loaf process; the overnight leaven and the twenty-five percent whole wheat blend are copied almost verbatim in my home build.", "reference", "personal", False,
     [("Chad Robertson", "person"), ("Tartine Bread", "publication"), ("country loaf", "food"), ("leaven", "food")],
     [("Tartine Bread", "Chad Robertson", "AUTHORED_BY"), ("country loaf", "Tartine Bread", "BUILDS_ON")],
     "which book and author anchor the country loaf process and which two elements did the home build copy",
     "tartine bread chad robertson country loaf leaven whole wheat reference"),
    # --- 5 reference ---
    ("Ken Forkish's Flour Water Salt Yeast, always shorthanded as FWSY in my notes, is the go-to for the same-day straight doughs and the pH-and-time tables for the commercial yeast comparison bakes.", "reference", "personal", False,
     [("Ken Forkish", "person"), ("Flour Water Salt Yeast", "publication"), ("FWSY", "publication"), ("straight doughs", "food"), ("commercial yeast", "food")],
     [("Flour Water Salt Yeast", "Ken Forkish", "AUTHORED_BY"), ("FWSY", "Flour Water Salt Yeast", "RELATED_TO")],
     "which Forkish book covers the same-day straight doughs and what does FWSY abbreviate in my notes",
     "ken forkish fwsy flour water salt yeast straight dough reference"),
    # --- 6 preference ---
    ("I prefer coil folds over stretch-and-folds once the dough hits seventy-five percent hydration; the wetter the dough the more a stretch tears the gluten and the coil respects the shape better in the tub.", "preference", "personal", False,
     [("coil fold", "method"), ("stretch-and-fold", "method"), ("hydration", "concept"), ("gluten", "concept")],
     [("coil fold", "stretch-and-fold", "PREFERS")],
     "which folding technique do I prefer above seventy-five percent hydration and why does the stretch variant underperform",
     "coil fold stretch and fold high hydration gluten tear tub"),
    # --- 7 milestone ---
    ("First batch of croissants with proper honeycomb landed on the third attempt; the détrempe rested overnight in the fridge, the beurrage was pounded to a flat square of cold butter, and three book-folds produced eighty-one layers before shaping.", "milestone", "personal", False,
     [("croissants", "food"), ("honeycomb", "concept"), ("détrempe", "food"), ("beurrage", "food"), ("book-fold", "method")],
     [("croissants", "book-fold", "USES"), ("croissants", "détrempe", "USES")],
     "which laminated-dough milestone finally produced a honeycomb crumb and which fold pattern got me to eighty-one layers",
     "croissants honeycomb detrempe beurrage book fold eighty one layer"),
    # --- 8 decision ---
    ("Settled on three single-folds over the classic two book-folds plus one single for my croissants; the thinner butter sheet in the tourage step stays cold longer in my flat and leaks less butter out the sides during proof.", "decision", "personal", False,
     [("croissants", "food"), ("single-folds", "method"), ("book-folds", "method"), ("tourage", "method"), ("butter sheet", "food")],
     [("single-folds", "book-folds", "PREFERS"), ("tourage", "butter sheet", "USES")],
     "which lamination pattern did I pick for the home croissant and what butter-sheet behaviour drove the choice",
     "croissant three fold book fold tourage butter sheet leak proof"),
    # --- 9 milestone ---
    ("The fiftieth sourdough of the year hit a genuinely open crumb wall to wall after two months of flat-crumb batches; pushing bulk fermentation forty percent longer past the windowpane stretch test was the unlock that the oven spring reflected immediately.", "milestone", "personal", False,
     [("bulk fermentation", "method"), ("windowpane", "method"), ("stretch test", "method"), ("oven spring", "concept"), ("crumb", "concept")],
     [],
     "which milestone bake ended the flat-crumb streak and which fermentation change produced the open wall-to-wall crumb",
     "fiftieth sourdough open crumb bulk ferment windowpane oven spring"),
    # --- 10. noise ---
    ("The neighbours repainted their front door a startling Yves Klein blue and the whole cul-de-sac has been arguing about it on the group chat for a week.", "fact", "noise", True, [], [], None, None),
    # --- 11 decision ---
    ("Pinned the bench flow to preshape, twenty-minute bench rest under a cloth, then final shape into a batard after a spring of skipping the rest; the preshape tightens the gluten loosely so the final shape doesn't fight the dough or tear the skin.", "decision", "personal", False,
     [("preshape", "method"), ("bench rest", "method"), ("final shape", "method"), ("batard", "food"), ("gluten", "concept")],
     [("final shape", "preshape", "BUILDS_ON"), ("batard", "final shape", "USES")],
     "which three-step bench sequence builds the batard and what role does the bench rest play between shapes",
     "preshape bench rest final shape batard gluten tighten skin tear"),
    # --- 12 preference ---
    ("I prefer shaping a boule for the Dutch oven bake and a batard for the baking steel; the round shape fits the cast iron cleanly and the elongated loaf shows off scoring ears better on the steel.", "preference", "personal", False,
     [("boule", "food"), ("batard", "food"), ("Dutch oven", "tool"), ("baking steel", "tool"), ("scoring", "method")],
     [("boule", "Dutch oven", "APPLIES_TO"), ("batard", "baking steel", "APPLIES_TO")],
     "which shape do I prefer for which bake vessel and what aesthetic drives each choice",
     "boule batard dutch oven baking steel scoring ear shape preference"),
    # --- 13 decision ---
    ("Dropped the spray-bottle steam trick for the first ten minutes and went to a preheated Dutch oven with the lid on; the oven spring is dramatic and the crust blisters the way it never did on the stone setup.", "decision", "personal", False,
     [("spray-bottle steam", "method"), ("Dutch oven", "tool"), ("oven spring", "concept"), ("stone setup", "tool"), ("crust", "concept")],
     [("Dutch oven", "spray-bottle steam", "REPLACES")],
     "which steam method did I replace with a lidded Dutch oven and which crust property improved after the swap",
     "dutch oven spray bottle steam oven spring crust blister stone"),
    # --- 14 fact ---
    ("The Lodge Combo Cooker I picked up used handles the 900 gram batards comfortably; the shallow pan acts as the base and the deep skillet inverts as the lid, which loads easier than a round Dutch oven with oven mitts.", "fact", "personal", False,
     [("Lodge Combo Cooker", "tool"), ("batard", "food"), ("Dutch oven", "tool")],
     [("Lodge Combo Cooker", "batard", "APPLIES_TO")],
     "which cast-iron vessel did I pick for 900 gram batards and why does it load easier than a Dutch oven",
     "lodge combo cooker batard 900 gram shallow pan invert lid"),
    # --- 15 architecture ---
    ("Cold retard in the fridge sits at four degrees for twelve to sixteen hours in a banneton under a shower cap; the crumb develops more flavour from the long slow fermentation and scoring cuts clean on the cold skin.", "architecture", "personal", False,
     [("Cold retard", "method"), ("banneton", "tool"), ("scoring", "method"), ("crumb", "concept"), ("fermentation", "method")],
     [("Cold retard", "banneton", "USES"), ("scoring", "Cold retard", "APPLIES_TO")],
     "which cold retard window and setup do my loaves rest in and why does scoring benefit from the cold skin",
     "cold retard four degrees banneton shower cap scoring crumb flavour"),
    # --- 16 decision ---
    ("Moved the levain build to the Rubaud method of vigorous one-handed mixing for the first three minutes; the dough reaches the windowpane faster without a stand mixer and the high-hydration batches stop slipping in the bowl.", "decision", "personal", False,
     [("levain", "food"), ("Rubaud method", "method"), ("windowpane", "method"), ("stand mixer", "tool"), ("hydration", "concept")],
     [("Rubaud method", "stand mixer", "REPLACES"), ("Rubaud method", "windowpane", "PRODUCES")],
     "which hand-mixing technique replaced the stand mixer for the levain build and what advantage did it bring at high hydration",
     "rubaud method levain one handed mix stand mixer windowpane"),
    # --- 17 fact ---
    ("My rye starter lives in a separate jar and gets fed twice a week with dark rye flour at a stiff 1:2:2 ratio; it peaks slower than the wheat starter but gives the seeded rye loaves a much deeper sour note.", "fact", "personal", False,
     [("rye starter", "food"), ("dark rye flour", "food"), ("1:2:2", "concept"), ("wheat starter", "food"), ("seeded rye", "food")],
     [("rye starter", "dark rye flour", "PRODUCES"), ("seeded rye", "rye starter", "BUILDS_ON")],
     "which feeding ratio and flour keep my rye starter going and which loaves rely on its deeper sour note",
     "rye starter dark rye 1:2:2 wheat starter seeded rye sour"),
    # --- 18 architecture ---
    ("Scoring pattern for the country boule is a single offset arc held at a forty-five-degree blade angle; the ear lifts cleanly in the Dutch oven bake where a decorative wheat score tears and closes under the lid.", "architecture", "personal", False,
     [("Scoring", "method"), ("country boule", "food"), ("ear", "concept"), ("Dutch oven", "tool"), ("wheat score", "method")],
     [("country boule", "Scoring", "USES"), ("Scoring", "wheat score", "REPLACES")],
     "which scoring pattern and blade angle give the country boule a reliable ear under the Dutch oven lid",
     "scoring arc ear country boule dutch oven wheat"),
    # --- 19 preference ---
    ("For the everyday bake I prefer T65 over T55 from the same French mill; the slightly higher ash content gives a creamier crumb colour and holds hydration a little better during the long cold retard.", "preference", "personal", False,
     [("T65", "food"), ("T55", "food"), ("crumb", "concept"), ("cold retard", "method"), ("hydration", "concept")],
     [("T65", "T55", "PREFERS")],
     "which French flour do I prefer for the everyday bake and what property pushed me off T55",
     "t65 t55 french flour ash crumb colour hydration cold retard"),
    # --- 20 reference ---
    ("Trevor Wilson's Open Crumb Mastery is the reference I keep open on the iPad during bulk; his chapter on gum lines, underproofed crumb, and kitchen temperature diagnosed why the eighteen-degree counter was the culprit before I even tried a seed mat.", "reference", "personal", False,
     [("Trevor Wilson", "person"), ("Open Crumb Mastery", "publication"), ("gum line", "concept"), ("underproofed", "concept"), ("seed mat", "tool")],
     [("Open Crumb Mastery", "Trevor Wilson", "AUTHORED_BY")],
     "which reference do I keep open during bulk and how did it diagnose the cold-kitchen gum-line failure",
     "trevor wilson open crumb mastery gum line underproof reference"),
    # --- 21 milestone ---
    ("Panettone attempt number four finally held its shape after hanging upside down overnight on the two wooden skewers; the pasta madre feed cycle of three refreshes in eight hours was the breakthrough against the earlier collapses.", "milestone", "personal", False,
     [("Panettone", "food"), ("pasta madre", "food"), ("wooden skewers", "tool")],
     [("Panettone", "pasta madre", "BUILDS_ON"), ("Panettone", "wooden skewers", "USES")],
     "which panettone attempt finally held its shape and which starter feed cadence was the breakthrough",
     "panettone pasta madre wooden skewer hang upside down refresh"),
    # --- 22 reference ---
    ("The Perfect Loaf by Maurizio Leo is the default troubleshooting reference when the crumb goes wrong; his bulk-fermentation-by-temperature table is pinned to the fridge next to the proofing chart.", "reference", "personal", False,
     [("The Perfect Loaf", "publication"), ("Maurizio Leo", "person"), ("bulk-fermentation-by-temperature table", "tool"), ("proofing chart", "tool"), ("crumb", "concept")],
     [("The Perfect Loaf", "Maurizio Leo", "AUTHORED_BY")],
     "which blog-and-book reference do I reach for when the crumb goes wrong and which table lives on the fridge",
     "perfect loaf maurizio leo bulk ferment temperature table proof"),
    # --- 23 reference ---
    ("Peter Reinhart's The Bread Baker's Apprentice is still my reference for the baker's percentages chapter; the pre-ferment comparison between biga, poolish, and pâte fermentée is the clearest writeup I know.", "reference", "personal", False,
     [("Peter Reinhart", "person"), ("The Bread Baker's Apprentice", "publication"), ("baker's percentages", "concept"), ("biga", "food"), ("poolish", "food"), ("pâte fermentée", "food")],
     [("The Bread Baker's Apprentice", "Peter Reinhart", "AUTHORED_BY")],
     "which Reinhart book anchors my baker's percentages knowledge and which three pre-ferments does it compare",
     "peter reinhart bread baker apprentice bakers percentage biga poolish"),
    # --- 24 reference ---
    ("The baker's percentages chapter in Hamelman's Bread is the one I pull off the shelf when building a new formula; flour as the hundred-percent base, hydration, salt, and levain percentages come straight out of his worked examples.", "reference", "personal", False,
     [("baker's percentages", "concept"), ("Hamelman", "person"), ("Bread", "publication"), ("hydration", "concept"), ("salt", "food"), ("levain", "food")],
     [("Bread", "Hamelman", "AUTHORED_BY")],
     "which Hamelman reference anchors my baker's percentages work when building a new formula",
     "hamelman bread bakers percentage flour hydration salt levain reference"),
    # --- 25 decision ---
    ("Dropped the autolyse from thirty minutes to sixty minutes before adding salt and levain; the dough picks up strength with fewer folds and the extensibility at shaping makes the ear pop reliably on the batard.", "decision", "personal", False,
     [("autolyse", "method"), ("salt", "food"), ("levain", "food"), ("extensibility", "concept"), ("batard", "food"), ("ear", "concept")],
     [("autolyse", "batard", "APPLIES_TO")],
     "which autolyse duration change reduced the fold count and improved ear reliability on the batard",
     "autolyse sixty minute salt levain extensibility ear batard"),
    # --- 26 milestone ---
    ("First successful pain au chocolat batch came out of the oven the Sunday after the layered-butter test: strip of détrempe, two chocolate batons, roll tight with the seam underneath, proof at twenty-four degrees for two hours, egg wash twice.", "milestone", "personal", False,
     [("pain au chocolat", "food"), ("détrempe", "food"), ("chocolate batons", "food"), ("egg wash", "food"), ("proof", "method")],
     [("pain au chocolat", "détrempe", "USES"), ("pain au chocolat", "egg wash", "USES")],
     "which assembly and proof sequence does the pain au chocolat follow and when does the egg wash get applied",
     "pain au chocolat detrempe chocolate baton egg wash proof"),
    # --- 27 milestone ---
    ("Kouign-amann shipped a proper caramelised base on the second try; folding granulated sugar into the final book-fold and baking in a well-greased muffin tin at two-twenty gave the glassy amber bottom the recipe promised.", "milestone", "personal", False,
     [("Kouign-amann", "food"), ("granulated sugar", "food"), ("book-fold", "method"), ("muffin tin", "tool")],
     [("Kouign-amann", "book-fold", "USES"), ("Kouign-amann", "muffin tin", "USES")],
     "which kouign-amann attempt hit a glassy caramelised base and which sugar step made the difference",
     "kouign amann granulated sugar book fold muffin tin caramel"),
    # --- 28 decision ---
    ("Switched the croissant tourage surface from the wooden board to a chilled marble slab; the butter stays in one sheet through the lamination instead of smearing into the flour and bleeding out of the edges.", "decision", "personal", False,
     [("croissant", "food"), ("tourage", "method"), ("wooden board", "tool"), ("marble slab", "tool"), ("butter", "food"), ("lamination", "method")],
     [("marble slab", "wooden board", "REPLACES"), ("lamination", "marble slab", "APPLIES_TO")],
     "which tourage surface did I swap in for the wooden board and what butter-behaviour improvement followed",
     "croissant tourage marble slab wooden board butter lamination"),
    # --- 29 problem ---
    ("Croissant butter broke through the détrempe on the first fold and leaked grease onto the counter; the beurrage had been pulled from the fridge too recently and was still plastic at fifteen degrees, so I now rest it ten minutes between folds.", "problem", "personal", False,
     [("Croissant", "food"), ("détrempe", "food"), ("beurrage", "food"), ("fold", "method")],
     [("beurrage", "détrempe", "CAUSES")],
     "which croissant-lamination failure leaked butter on the first fold and which rest schedule fixes it",
     "croissant butter break detrempe beurrage fold plastic fifteen"),
    # --- 30 architecture ---
    ("Bulk fermentation tracking uses a straight-sided clear tub with rubber bands marking twenty-five, fifty, and seventy-five percent rise; the end-of-bulk call is by volume jump rather than by clock, which survives temperature swings.", "architecture", "personal", False,
     [("Bulk fermentation", "method"), ("clear tub", "tool"), ("rubber bands", "tool"), ("temperature", "concept")],
     [("Bulk fermentation", "clear tub", "USES")],
     "which volume-based tracking setup calls end-of-bulk by rise rather than by clock and what does it survive",
     "bulk ferment clear tub rubber band volume rise temperature"),
    # --- 31 fact ---
    ("The Brod and Taylor proofer sits on the bottom shelf of the pantry and holds the bulk dough at a rock-steady twenty-six degrees; the previous oven-with-light trick varied by four degrees overnight and wrecked the timing.", "fact", "personal", False,
     [("Brod and Taylor proofer", "tool"), ("bulk dough", "food"), ("oven-with-light", "method")],
     [("Brod and Taylor proofer", "oven-with-light", "REPLACES")],
     "which proofing appliance holds the bulk at a steady temperature and which improvised trick did it replace",
     "brod taylor proofer bulk dough oven light twenty six degree"),
    # --- 32 decision ---
    ("Dropped Kiwi rice flour in the bannetons in favour of a fifty-fifty rice flour and semolina blend; the loaves release cleaner on wet doughs and the semolina gives the crust a faint nutty note on the base.", "decision", "personal", False,
     [("rice flour", "food"), ("semolina", "food"), ("banneton", "tool"), ("crust", "concept")],
     [("semolina", "rice flour", "REPLACES"), ("banneton", "rice flour", "USES")],
     "which banneton-dusting blend replaced pure rice flour and what crust property did the semolina add",
     "rice flour semolina banneton release wet dough crust nutty"),
    # --- 33 architecture ---
    ("Oven spring is coaxed by preheating the Dutch oven at two-sixty for forty-five minutes, dropping the scored loaf in on parchment, and baking twenty minutes with the lid on before the final coloring bake at two-thirty.", "architecture", "personal", False,
     [("Oven spring", "concept"), ("Dutch oven", "tool"), ("parchment", "tool"), ("scored", "method")],
     [("Oven spring", "Dutch oven", "USES")],
     "which preheat-and-bake sequence maximises oven spring and when does the lid come off during the bake",
     "oven spring dutch oven preheat parchment lid score bake"),
    # --- 34 decision ---
    ("Standardised on a UFO lame with a curved blade and retired the straight razor for scoring the batard; the curve holds the forty-five-degree slash angle more consistently and cuts cleaner through the cold skin off the retard.", "decision", "personal", False,
     [("UFO lame", "tool"), ("straight razor", "tool"), ("scoring", "method"), ("batard", "food"), ("retard", "method")],
     [("UFO lame", "straight razor", "PREFERS")],
     "which scoring tool do I prefer for the batard and what cutting behaviour drove the choice over a straight razor",
     "ufo lame curved blade straight razor scoring batard retard"),
    # --- 35 milestone ---
    ("First 1000 gram weekend loaf hit a 3.5 height-to-width ratio after the second coil fold was pushed back by thirty minutes; the crumb is even from crust to crust with no dense band, which had been the holdout from the last six bakes.", "milestone", "personal", False,
     [("1000 gram weekend loaf", "food"), ("coil fold", "method"), ("crumb", "concept"), ("dense band", "concept")],
     [("1000 gram weekend loaf", "coil fold", "USES")],
     "which loaf size finally hit a 3.5 height-to-width ratio and which timing change eliminated the dense band",
     "1000 gram loaf coil fold height width dense band crumb"),
    # --- 36 problem ---
    ("Pale crust on the first attempts at pain au chocolat traced to the egg wash being whole egg plus cream; switched to a yolk-and-milk wash with a pinch of salt and the tops finally took on that lacquered mahogany colour.", "problem", "personal", False,
     [("pain au chocolat", "food"), ("egg wash", "food"), ("yolk-and-milk wash", "food"), ("salt", "food"), ("crust", "concept")],
     [("yolk-and-milk wash", "egg wash", "REPLACES")],
     "which egg-wash formulation replaced the whole-egg-plus-cream version and what colour improvement followed",
     "pain au chocolat egg wash yolk milk salt mahogany crust"),
    # --- 37 fact ---
    ("Scoring lives on a fixed vocabulary: single arc for the batard, plus cross for the boule, wheat stalk for special bakes, and an inverted V for the sandwich pan loaf when I want a dome rather than a flat top.", "fact", "personal", False,
     [("Scoring", "method"), ("single arc", "concept"), ("plus cross", "concept"), ("wheat stalk", "concept"), ("inverted V", "concept"), ("sandwich pan", "tool")],
     [("Scoring", "sandwich pan", "APPLIES_TO")],
     "which scoring patterns pair with which loaf shapes in my fixed vocabulary",
     "scoring single arc plus cross wheat stalk inverted v sandwich"),
    # --- 38 architecture ---
    ("The laminated-dough timeline runs détrempe Friday evening, beurrage Saturday morning with an hour rest between each of the three folds, shape Saturday afternoon, retard overnight, then proof and bake Sunday morning at seven.", "architecture", "personal", False,
     [("laminated-dough", "food"), ("détrempe", "food"), ("beurrage", "food"), ("fold", "method"), ("retard", "method"), ("proof", "method")],
     [("laminated-dough", "détrempe", "USES"), ("laminated-dough", "retard", "USES")],
     "which weekend timeline spreads the laminated-dough work from Friday through Sunday morning",
     "laminated dough timeline detrempe beurrage fold retard proof"),
    # --- 39 decision ---
    ("Pulled the stand-mixer dough hook off the hydration over seventy-five percent bakes; the Rubaud method plus four coil folds reaches the windowpane faster than the machine did and the crumb is noticeably more open.", "decision", "personal", False,
     [("stand-mixer dough hook", "tool"), ("Rubaud method", "method"), ("coil fold", "method"), ("windowpane", "method"), ("crumb", "concept")],
     [("Rubaud method", "stand-mixer dough hook", "REPLACES")],
     "which hand-mixing combo replaced the stand-mixer dough hook above seventy-five percent hydration",
     "stand mixer dough hook rubaud coil fold windowpane crumb"),
    # --- 40 fact ---
    ("My daily driver digital scale is the Escali Primo at 0.1 gram resolution up to 2 kilograms; the larger Ozeri sits underneath the Dutch oven on bake day for the pre- and post-bake weight loss measurement.", "fact", "personal", False,
     [("Escali Primo", "tool"), ("Ozeri", "tool"), ("Dutch oven", "tool"), ("weight loss", "concept")],
     [("Ozeri", "Dutch oven", "APPLIES_TO")],
     "which two scales handle the bakery's daily and bake-day roles and what measurement does the larger one support",
     "escali primo ozeri scale dutch oven weight loss bake"),
    # --- 41 architecture ---
    ("Starter maintenance sits on a jar-rotation system: jar A holds the active feed, jar B gets scraped and washed after the next refresh, and a discard jar in the fridge collects the trimmings for weekend pancakes.", "architecture", "personal", False,
     [("Starter", "food"), ("jar-rotation", "method"), ("discard jar", "tool"), ("pancakes", "food")],
     [("Starter", "jar-rotation", "USES"), ("discard jar", "pancakes", "APPLIES_TO")],
     "which jar-rotation system keeps the starter clean and what happens to the discard on the weekends",
     "starter jar rotation active feed discard fridge pancake weekend"),
    # --- 42 decision ---
    ("Moved the bread flour order from the supermarket private label to Shipton Mill No.4 by the 16 kilogram sack; the protein at 12.8 percent gives a more reliable windowpane and the per-kilo price is lower once the shipping is amortised.", "decision", "personal", False,
     [("bread flour", "food"), ("Shipton Mill No.4", "food"), ("protein", "concept"), ("windowpane", "method")],
     [("Shipton Mill No.4", "bread flour", "REPLACES")],
     "which bread flour replaced the supermarket private label and which two properties justified the sack buy",
     "shipton mill no 4 bread flour protein windowpane sack"),
    # --- 43. noise ---
    ("The hedgehog that lives under the compost bin has started showing up right at dusk and stares at the kitchen window for a few minutes before trundling off into the neighbour's yard.", "fact", "noise", True, [], [], None, None),
    # --- 44 problem ---
    ("Tight crumb with a shiny grey interior on a rye blend loaf traced to an over-fermented starter; the jar had peaked and collapsed back four hours before the levain build, so I now dial in the feed ratio to peak at the build time.", "problem", "personal", False,
     [("Tight crumb", "concept"), ("rye blend loaf", "food"), ("starter", "food"), ("levain", "food")],
     [("starter", "levain", "PRODUCES")],
     "which over-fermentation failure caused the tight shiny rye crumb and which starter-peak adjustment fixed it",
     "tight crumb rye blend starter peak collapse levain feed"),
    # --- 45 decision ---
    ("Switched the winter bulk ferment from a counter rest to the oven with the light on and a shallow dish of boiling water at the start; the four-degree colder kitchen no longer stretches bulk past six hours and the crumb stays consistent.", "decision", "personal", False,
     [("winter bulk ferment", "method"), ("counter rest", "method"), ("oven with the light on", "tool"), ("boiling water", "food"), ("crumb", "concept")],
     [("oven with the light on", "counter rest", "REPLACES")],
     "which winter bulk-ferment setup replaced the counter rest and which consistency problem did it fix",
     "winter bulk ferment counter oven light boiling water crumb"),
    # --- 46 architecture ---
    ("Stretch test protocol: pinch a walnut-sized piece, stretch between thumbs into a translucent windowpane the size of a playing card; if the sheet tears or stays opaque, push bulk another thirty minutes and recheck.", "architecture", "personal", False,
     [("Stretch test", "method"), ("windowpane", "method"), ("bulk", "method")],
     [("Stretch test", "windowpane", "USES")],
     "which stretch test protocol gates end-of-bulk and what happens if the windowpane tears or stays opaque",
     "stretch test windowpane walnut translucent playing card bulk"),
    # --- 47 milestone ---
    ("First bake of the year with oven spring visibly cresting the Dutch oven rim landed on the bake-eighteen retrospective; the combination of a stiffer levain at fifty percent hydration and the sixty-minute autolyse turned out to be the winning pair.", "milestone", "personal", False,
     [("oven spring", "concept"), ("Dutch oven", "tool"), ("stiffer levain", "food"), ("hydration", "concept"), ("autolyse", "method")],
     [("stiffer levain", "autolyse", "APPLIES_TO")],
     "which two process changes combined to finally crest the Dutch oven rim on bake eighteen",
     "oven spring dutch oven rim stiff levain autolyse bake eighteen"),
    # --- 48 preference ---
    ("I prefer oval willow bannetons over cane for the batards; the looser weave leaves a sharper spiral imprint, and the cloth liners come off faster without sticking to the seventy-eight-percent-hydration skin.", "preference", "personal", False,
     [("oval willow bannetons", "tool"), ("cane", "tool"), ("batards", "food"), ("cloth liners", "tool"), ("hydration", "concept")],
     [("oval willow bannetons", "cane", "PREFERS"), ("oval willow bannetons", "batards", "APPLIES_TO")],
     "which banneton material do I prefer for batards and which two practical properties drive the choice",
     "oval willow banneton cane batard cloth liner spiral hydration"),
    # --- 49 architecture ---
    ("The croissant shaping flow cuts triangles from a rectangle with a 9 centimetre base and a 22 centimetre height, notches the base centre, and rolls from base to tip with light pressure so the tip ends up underneath the final curl.", "architecture", "personal", False,
     [("croissant", "food"), ("triangle", "concept"), ("shaping", "method")],
     [("croissant", "shaping", "USES")],
     "which triangle dimensions and roll direction does the croissant shaping flow rely on to land the tip underneath",
     "croissant triangle 9 22 base height notch roll tip curl"),
    # --- 50 fact ---
    ("Loaf post-bake cooling sits on a wire rack for at least two hours before slicing; cutting into a warm crumb on a trial bake last spring turned the slices gummy and proved the wait time isn't optional for properly set gelatinised starch.", "fact", "personal", False,
     [("wire rack", "tool"), ("crumb", "concept"), ("gelatinised starch", "concept")],
     [("wire rack", "crumb", "APPLIES_TO")],
     "which post-bake cooling protocol is non-negotiable and which past failure proved the wait time matters",
     "wire rack cool two hour slice gummy gelatinised starch"),
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
