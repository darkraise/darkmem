"""One-off emitter for shared-base batch-206 — personal domain (gardening: home veg plots, composting, houseplants).

Writes 50 rows to data/v2/shared/batch_206.tmp.jsonl with ids shared-10251..10300.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_206.tmp.jsonl"
ID_OFFSET = 10250

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Converted the back lawn to four raised beds this spring and followed the Charles Dowding no-dig method; a two-inch compost top-up each autumn replaced any tilling and the weed pressure already dropped noticeably.", "milestone", "personal", False,
     [("raised beds", "method"), ("Charles Dowding", "person"), ("no-dig", "method"), ("compost", "concept")],
     [("no-dig", "Charles Dowding", "AUTHORED_BY"), ("raised beds", "no-dig", "USES")],
     "how did the backyard vegetable patch transition away from tilling using a named method",
     "raised bed no dig charles dowding compost mulch spring convert lawn"),
    # --- 2 ---
    ("Chose hugelkultur over a plain raised bed for the far-corner plot since the slope already held a rotting oak log; buried wood now acts as a slow-release water reservoir through the dry summer stretches.", "decision", "personal", False,
     [("hugelkultur", "method"), ("raised bed", "method"), ("oak log", "concept")],
     [("hugelkultur", "raised bed", "REPLACES")],
     "which bed-building approach won the corner plot and what made the decision easier on the slope",
     "hugelkultur raised bed oak log slope water reservoir dry summer"),
    # --- 3 ---
    ("Ruth Stout's lasagna gardening approach runs on top of the asparagus row; alternating straw and grass clippings at six-inch lifts smothered the bindweed without a single pass of the cultivator.", "architecture", "personal", False,
     [("Ruth Stout", "person"), ("lasagna gardening", "method"), ("asparagus", "concept"), ("straw", "concept"), ("grass clippings", "concept"), ("bindweed", "concept")],
     [("lasagna gardening", "Ruth Stout", "AUTHORED_BY"), ("lasagna gardening", "bindweed", "APPLIES_TO")],
     "which sheet-mulching method smothered bindweed around the asparagus row without cultivation",
     "ruth stout lasagna garden straw grass clipping asparagus bindweed"),
    # --- 4 ---
    ("The three-bin hot composting setup reliably hits 140F within four days if the C:N ratio is kept near 30:1; the middle bin is the active pile and the left bin is always the finishing stage.", "architecture", "personal", False,
     [("hot composting", "method"), ("C:N ratio", "concept"), ("three-bin", "pattern")],
     [("three-bin", "hot composting", "USES")],
     "how is the three-bin system arranged and what target drives the hot pile reaching temperature",
     "three bin hot compost c n ratio 30 140 degree active finish"),
    # --- 5 ---
    ("Vermicompost tray under the kitchen bench is run with red wigglers fed shredded cardboard plus veg scraps; citrus and onion skins go to the outdoor pile because Eisenia fetida refuses them.", "fact", "personal", False,
     [("Vermicompost", "method"), ("red wigglers", "concept"), ("Eisenia fetida", "concept"), ("cardboard", "concept")],
     [("Vermicompost", "red wigglers", "USES")],
     "which worms run the indoor bin and what kitchen scraps get routed out to the outdoor pile instead",
     "vermicompost red wiggler eisenia fetida citrus onion cardboard scrap"),
    # --- 6 ---
    ("Picked Bokashi for the meat-and-dairy stream over adding a second worm bin; the sealed bucket ferments two weeks with EM-1 bran and the fermented output buries under the fruit trees without attracting rats.", "decision", "personal", False,
     [("Bokashi", "method"), ("EM-1", "concept"), ("worm bin", "method"), ("fruit trees", "concept")],
     [("Bokashi", "worm bin", "PREFERS"), ("Bokashi", "EM-1", "USES")],
     "which fermentation method handles meat scraps and why did it beat a second worm bin",
     "bokashi em 1 bran meat dairy ferment bury fruit tree rat worm"),
    # --- 7 ---
    ("Leaf mold bin by the oak gets filled every November; two winters of weathering turns the maple and oak leaves into the crumbly black stuff that seed-starting mixes love.", "fact", "personal", False,
     [("Leaf mold", "concept"), ("oak", "concept"), ("maple", "concept"), ("seed-starting mix", "concept")],
     [("Leaf mold", "seed-starting mix", "APPLIES_TO")],
     "how long does the oak-and-maple leaf bin take before the crumbly output is ready for seed mixes",
     "leaf mold oak maple two winter crumbly seed start mix november"),
    # --- 8 ---
    ("Indeterminate tomatoes like 'Sungold' and 'Brandywine' get single-leader trained up jute twine; determinate varieties such as 'Roma' stay unpruned because pinching suckers on them just costs fruit set.", "reference", "personal", False,
     [("Sungold", "concept"), ("Brandywine", "concept"), ("Roma", "concept"), ("Indeterminate", "concept"), ("determinate", "concept"), ("jute twine", "concept")],
     [("Sungold", "Indeterminate", "APPLIES_TO"), ("Roma", "determinate", "APPLIES_TO")],
     "which tomato varieties get single-leader pruned and which stay untouched in the patch",
     "sungold brandywine roma indeterminate determinate sucker prune twine"),
    # --- 9 ---
    ("Blossom-end rot on the early 'San Marzano' fruit cleared up once the mulch went down and watering stabilised; the problem was never calcium content in the soil, it was swingy moisture interrupting uptake.", "problem", "personal", False,
     [("Blossom-end rot", "concept"), ("San Marzano", "concept"), ("mulch", "concept"), ("calcium", "concept")],
     [("mulch", "Blossom-end rot", "FIXES")],
     "what actually fixed the calcium-looking rot on the early San Marzano fruit that season",
     "blossom end rot san marzano mulch water calcium uptake swing moisture"),
    # --- 10. noise ---
    ("The neighbour's orange tabby has appointed herself the official greeter at the front gate and the postman brings her a treat on Tuesdays.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Crop rotation plan runs a four-year cycle: brassicas follow legumes, nightshades follow brassicas, roots follow nightshades, legumes close the loop; clubroot and verticillium wilt have stayed off the beds.", "architecture", "personal", False,
     [("Crop rotation", "method"), ("brassicas", "concept"), ("legumes", "concept"), ("nightshades", "concept"), ("clubroot", "concept"), ("verticillium wilt", "concept")],
     [("Crop rotation", "clubroot", "FIXES"), ("brassicas", "legumes", "APPLIES_TO")],
     "how is the four-bed rotation sequenced and which soil-borne diseases has it kept away",
     "crop rotation four year brassica legume nightshade root clubroot verticillium"),
    # --- 12 ---
    ("Intercropped lettuce between the 'Costoluto' tomato stakes through June; the shade kept the lettuce from bolting and the tomatoes hadn't canopied out yet so neither crop suffered.", "fact", "personal", False,
     [("Intercropped", "method"), ("lettuce", "concept"), ("Costoluto", "concept")],
     [("Intercropped", "lettuce", "APPLIES_TO")],
     "which intercropping pair kept the summer lettuce from bolting between the tomato stakes",
     "intercrop lettuce costoluto tomato shade bolt june stake canopy"),
    # --- 13 ---
    ("Succession planting of bush beans goes in every fourteen days from mid-May through July; the staggered harvest outlasts a single big planting by almost two months and never overwhelms the kitchen.", "architecture", "personal", False,
     [("Succession planting", "method"), ("bush beans", "concept")],
     [("Succession planting", "bush beans", "APPLIES_TO")],
     "how is the bush-bean planting paced to stretch the harvest and avoid a kitchen glut",
     "succession plant bush bean fourteen day may july harvest stagger"),
    # --- 14 ---
    ("Winter cover crop is a crimson clover and winter rye mix broadcast in late October; the rye scavenges nitrate, the clover fixes nitrogen, and both get crimped down in April under a tarp.", "architecture", "personal", False,
     [("crimson clover", "concept"), ("winter rye", "concept"), ("cover crop", "method"), ("nitrate", "concept"), ("nitrogen", "concept")],
     [("crimson clover", "nitrogen", "USES"), ("winter rye", "nitrate", "USES")],
     "which cover crop mix overwinters the beds and how does it get terminated in spring",
     "crimson clover winter rye cover crop nitrate nitrogen tarp crimp"),
    # --- 15 ---
    ("Green manure of buckwheat goes in any gap longer than six weeks between cash crops; flowers get mown before seed set so the next brassica succession isn't fighting volunteer buckwheat in the row.", "fact", "personal", False,
     [("Green manure", "method"), ("buckwheat", "concept")],
     [("Green manure", "buckwheat", "USES")],
     "how does the short-gap green manure work and what timing prevents it volunteering next season",
     "green manure buckwheat gap six week mow flower seed brassica volunteer"),
    # --- 16 ---
    ("Swapped the front fescue strip for a microclover-and-fine-fescue blend; mowing dropped to once a month, no fertiliser went down in the second year, and the bees show up for the white flowers.", "decision", "personal", False,
     [("microclover", "concept"), ("fescue", "concept"), ("bees", "concept")],
     [("microclover", "fescue", "REPLACES"), ("microclover", "bees", "APPLIES_TO")],
     "which lawn blend replaced the plain fescue strip and what maintenance and wildlife wins followed",
     "microclover fine fescue lawn replace mow fertiliser bee flower"),
    # --- 17 ---
    ("Lawn-to-meadow conversion on the side yard followed a smother-with-cardboard pass, then overseeding with a pollinator mix heavy on yarrow and black-eyed Susan; two growing seasons in and the monarchs arrived.", "milestone", "personal", False,
     [("Lawn-to-meadow", "method"), ("cardboard", "concept"), ("yarrow", "concept"), ("black-eyed Susan", "concept"), ("monarchs", "concept")],
     [("yarrow", "monarchs", "APPLIES_TO")],
     "which steps turned the side-yard grass into a functioning meadow and what visible fauna showed up",
     "lawn meadow convert cardboard smother yarrow black eyed susan monarch"),
    # --- 18 ---
    ("Drip irrigation on the veg beds runs off a quarter-inch line with half-gallon emitters spaced at twelve inches; the old overhead sprinkler got pulled because it kept wetting tomato foliage and inviting early blight.", "decision", "personal", False,
     [("Drip irrigation", "method"), ("sprinkler", "method"), ("early blight", "concept"), ("emitters", "tool")],
     [("Drip irrigation", "sprinkler", "REPLACES"), ("Drip irrigation", "early blight", "FIXES")],
     "which irrigation swap cut down on tomato foliar disease and what emitter spacing did it land on",
     "drip irrigation sprinkler emitter twelve inch tomato early blight foliage"),
    # --- 19 ---
    ("Two 55-gallon rain barrels sit under the south downspout linked with a siphon hose; a first-flush diverter keeps the roof-grit out and the barrels feed the drip system via a transfer pump.", "architecture", "personal", False,
     [("rain barrels", "tool"), ("first-flush diverter", "tool"), ("transfer pump", "tool"), ("downspout", "tool")],
     [("rain barrels", "transfer pump", "USES")],
     "how are the two rain barrels plumbed together and how do they feed the drip system",
     "rain barrel 55 gallon first flush diverter downspout siphon transfer pump"),
    # --- 20 ---
    ("Planted a native pollinator strip of Monarda fistulosa, Echinacea purpurea, and Asclepias tuberosa along the bed edge; native bees and syrphid flies showed up in week two and aphid pressure on the kale dropped.", "milestone", "personal", False,
     [("Monarda fistulosa", "concept"), ("Echinacea purpurea", "concept"), ("Asclepias tuberosa", "concept"), ("syrphid flies", "concept"), ("aphid", "concept"), ("kale", "concept")],
     [("Asclepias tuberosa", "syrphid flies", "APPLIES_TO"), ("syrphid flies", "aphid", "IMPROVES_ON")],
     "which native pollinator strip went in and what downstream pest effect appeared on the kale",
     "monarda echinacea asclepias pollinator native syrphid aphid kale"),
    # --- 21 ---
    ("Mulched the pepper bed with two inches of shredded straw after transplant; soil moisture held between irrigations, the splash-borne disease dropped, and weeding stayed under five minutes a week through August.", "fact", "personal", False,
     [("Mulched", "method"), ("straw", "concept"), ("pepper", "concept"), ("splash-borne disease", "concept")],
     [("straw", "splash-borne disease", "FIXES")],
     "which mulch went on the pepper bed and what moisture, disease, and weed wins followed",
     "mulch straw pepper transplant moisture splash disease weed august"),
    # --- 22 ---
    ("The orchard has four apple, two pear, and two plum trees; pruning follows an open-centre system for the stone fruit and modified central leader for the pome fruit, both done in late winter while dormant.", "reference", "personal", False,
     [("apple", "concept"), ("pear", "concept"), ("plum", "concept"), ("open-centre", "method"), ("modified central leader", "method")],
     [("open-centre", "plum", "APPLIES_TO"), ("modified central leader", "apple", "APPLIES_TO")],
     "which pruning systems does each stone-fruit versus pome-fruit group get in the home orchard",
     "apple pear plum open centre modified central leader prune dormant winter"),
    # --- 23 ---
    ("Espalier training on the south-fence 'Honeycrisp' and 'Fuji' runs a four-tier horizontal cordon; the tiers ripen fruit at eye level and harvest doesn't need a ladder for the first time in four seasons.", "architecture", "personal", False,
     [("Espalier", "method"), ("Honeycrisp", "concept"), ("Fuji", "concept"), ("horizontal cordon", "method")],
     [("Espalier", "horizontal cordon", "USES")],
     "which espalier form trains the south-fence apples and what picking-height benefit did it unlock",
     "espalier honeycrisp fuji horizontal cordon four tier south fence apple"),
    # --- 24 ---
    ("Grafted a 'Stayman Winesap' scion onto the wild apple rootstock in the back corner using a cleft graft; the union healed through the first summer and pushed a clean two-foot leader by September.", "milestone", "personal", False,
     [("Stayman Winesap", "concept"), ("cleft graft", "method"), ("rootstock", "concept"), ("scion", "concept")],
     [("cleft graft", "Stayman Winesap", "APPLIES_TO")],
     "which grafting technique put the heirloom scion onto the wild rootstock and how did it heal out",
     "stayman winesap cleft graft scion rootstock wild apple heal leader"),
    # --- 25 ---
    ("Repotted the Monstera deliciosa into a 14-inch terracotta with a chunky aroid mix of orchid bark, perlite, and coco coir; aerial roots now have something to grip and the fenestrations came in properly on the new leaves.", "fact", "personal", False,
     [("Monstera deliciosa", "concept"), ("terracotta", "concept"), ("orchid bark", "concept"), ("perlite", "concept"), ("coco coir", "concept")],
     [("Monstera deliciosa", "orchid bark", "USES")],
     "which potting mix and container landed the new Monstera leaves with proper fenestrations",
     "monstera deliciosa terracotta orchid bark perlite coir fenestration aroid"),
    # --- 26 ---
    ("Epipremnum aureum 'Marble Queen' climbs a moss pole under a north window; misting the pole twice weekly keeps the variegation stable and the leaves have tripled in size since going vertical.", "fact", "personal", False,
     [("Epipremnum aureum", "concept"), ("Marble Queen", "concept"), ("moss pole", "tool")],
     [("Epipremnum aureum", "moss pole", "USES")],
     "how is the Marble Queen pothos trained and what size and variegation gains followed the switch",
     "epipremnum aureum marble queen moss pole mist variegation leaf size"),
    # --- 27 ---
    ("The Philodendron 'Birkin' prefers a chunky aroid mix plus bottom watering once every ten days; top watering kept leaving black spots on the cream pinstripes and the new flush looks clean since the switch.", "problem", "personal", False,
     [("Philodendron", "concept"), ("Birkin", "concept"), ("aroid mix", "concept"), ("bottom watering", "method"), ("top watering", "method")],
     [("bottom watering", "top watering", "REPLACES"), ("bottom watering", "Birkin", "APPLIES_TO")],
     "which watering method cleared the black spots on the Birkin pinstripes and how often does it run",
     "philodendron birkin aroid bottom watering top water black spot pinstripe"),
    # --- 28 ---
    ("Anthurium andraeanum sits in a clear nursery pot inside a cachepot; roots stay visible so overwatering gets caught early, and the red spathes held for six weeks after the last feed of balanced 20-20-20.", "architecture", "personal", False,
     [("Anthurium andraeanum", "concept"), ("cachepot", "tool"), ("20-20-20", "concept")],
     [("Anthurium andraeanum", "cachepot", "USES")],
     "which pot-in-pot setup and feed routine held the Anthurium spathes for six weeks",
     "anthurium andraeanum clear nursery cachepot root spathe 20 feed balance"),
    # --- 29 ---
    ("Sansevieria trifasciata in the hallway goes 5-6 weeks between waterings; the old 10-day schedule rotted the rhizomes and a full repot into gritty mix with extra pumice saved the remaining pups.", "problem", "personal", False,
     [("Sansevieria trifasciata", "concept"), ("gritty mix", "concept"), ("pumice", "concept"), ("rhizome", "concept")],
     [("gritty mix", "rhizome", "FIXES")],
     "what root problem killed half the Sansevieria and which mix and schedule brought the rest back",
     "sansevieria trifasciata gritty pumice rhizome rot water schedule week"),
    # --- 30 ---
    ("Hoya carnosa 'Krimson Queen' blooms reliably on a south-east sill once a peduncle forms; never cut the spent spur because next year's cluster emerges from the same peduncle and breaking it resets the cycle.", "reference", "personal", False,
     [("Hoya carnosa", "concept"), ("Krimson Queen", "concept"), ("peduncle", "concept")],
     [("Hoya carnosa", "peduncle", "USES")],
     "why do the Hoya peduncles stay on the plant and which window aspect triggers reliable bloom",
     "hoya carnosa krimson queen peduncle spur south east sill bloom"),
    # --- 31 ---
    ("Koyama plants in the office — a Pilea peperomioides and a Ficus elastica — share the north window and rotate every two weeks to keep the growth even; a humidifier holds the room at 55 percent.", "fact", "personal", False,
     [("Koyama plants", "person"), ("Pilea peperomioides", "concept"), ("Ficus elastica", "concept"), ("humidifier", "tool")],
     [("Pilea peperomioides", "humidifier", "USES")],
     "which two office plants came from the Koyama crew and what environment and rotation keeps them even",
     "koyama pilea peperomioides ficus elastica north humidifier rotate"),
    # --- 32 ---
    ("LST on the young lemon tree used jute ties to pull two lateral branches horizontal to the main stem; hormone balance shifted toward lower buds, three new side branches broke within a month, and the canopy widened without topping.", "decision", "personal", False,
     [("LST", "method"), ("lemon tree", "concept"), ("jute ties", "concept"), ("topping", "method")],
     [("LST", "topping", "PREFERS"), ("LST", "lemon tree", "APPLIES_TO")],
     "which low-stress training move shaped the young lemon canopy without a topping cut",
     "lst low stress train lemon jute tie lateral horizontal branch bud"),
    # --- 33 ---
    ("Topped the fiddle-leaf fig at 48 inches once the apex slowed; within three weeks two axillary buds broke and the tree now carries three leaders instead of one skinny cane under the skylight.", "milestone", "personal", False,
     [("Topped", "method"), ("fiddle-leaf fig", "concept"), ("axillary buds", "concept")],
     [("Topped", "fiddle-leaf fig", "APPLIES_TO")],
     "what topping height and timing split the fiddle-leaf into three leaders under the skylight",
     "top fiddle leaf fig 48 inch axillary bud leader cane skylight"),
    # --- 34 ---
    ("Preferring soil-block seed starting over plastic cells this year; the blocks air-prune the taproots, transplant shock vanishes because there's no pot to escape, and only a single tray template is in the drawer.", "preference", "personal", False,
     [("soil-block", "method"), ("plastic cell", "method"), ("taproot", "concept"), ("transplant shock", "concept")],
     [("soil-block", "plastic cell", "PREFERS"), ("soil-block", "transplant shock", "FIXES")],
     "which seed-starting method got preferred this season and what transplant benefit drove the switch",
     "soil block plastic cell taproot air prune transplant shock seed start"),
    # --- 35 ---
    ("Prefer Johnny's 'Provider' bush bean over 'Contender' for early plantings; germinates in colder soil, resists bean common mosaic virus, and the pods hold quality on the bush for an extra two days before getting stringy.", "preference", "personal", False,
     [("Provider", "concept"), ("Contender", "concept"), ("bean common mosaic virus", "concept")],
     [("Provider", "Contender", "PREFERS"), ("Provider", "bean common mosaic virus", "FIXES")],
     "which bush bean gets picked for early plantings and what disease and holding benefits favour it",
     "provider contender bush bean cold germinate mosaic virus pod hold"),
    # --- 36 ---
    ("Tagged the orchard's sooty-blotch problem on the apples as a humidity-plus-airflow issue; opened the canopies with summer pruning in July, skipped a spray, and next-year fruit surface scored clean at picking.", "problem", "personal", False,
     [("sooty-blotch", "concept"), ("summer pruning", "method"), ("apples", "concept")],
     [("summer pruning", "sooty-blotch", "FIXES")],
     "what pruning change cleared the sooty-blotch issue on the apples without adding a spray",
     "sooty blotch apple summer prune airflow humidity canopy july spray"),
    # --- 37 ---
    ("Prefer a collinear hoe over a stirrup hoe for the no-dig bed tops; the flat blade skims a quarter inch under the surface, shears weed seedlings off cleanly, and leaves the mulch layer intact.", "preference", "personal", False,
     [("collinear hoe", "tool"), ("stirrup hoe", "tool"), ("mulch", "concept")],
     [("collinear hoe", "stirrup hoe", "PREFERS")],
     "which hoe gets picked for the no-dig tops and why does it beat the stirrup design there",
     "collinear hoe stirrup no dig bed top mulch weed seedling blade"),
    # --- 38 ---
    ("Decided to skip nitrogen-heavy feed on the fruiting tomatoes past the first flower cluster; leafy-green excess was delaying ripening, and a switch to 5-10-10 pushed flowering and set without burning the root zone.", "decision", "personal", False,
     [("nitrogen", "concept"), ("5-10-10", "concept"), ("tomatoes", "concept"), ("flower cluster", "concept")],
     [("5-10-10", "nitrogen", "REPLACES"), ("5-10-10", "tomatoes", "APPLIES_TO")],
     "which fertiliser change balanced the tomato growth once the first cluster set",
     "nitrogen 5 10 fruit tomato cluster feed ripen leafy green burn root"),
    # --- 39 ---
    ("The brassica bed wears a floating row cover from transplant through late July; cabbage white butterflies never laid, and the 'Lacinato' kale came out of summer without the usual green caterpillar damage.", "fact", "personal", False,
     [("floating row cover", "tool"), ("cabbage white", "concept"), ("Lacinato", "concept"), ("brassica", "concept")],
     [("floating row cover", "cabbage white", "FIXES"), ("floating row cover", "brassica", "APPLIES_TO")],
     "which physical barrier kept cabbage white butterflies off the brassica bed and through which months",
     "floating row cover cabbage white brassica lacinato kale caterpillar july"),
    # --- 40 ---
    ("Compost thermometer reads the pile core at 14-inch depth; below 130F after three days triggers a turn, above 160F also triggers a turn since the thermophiles are tipping into killing territory.", "reference", "personal", False,
     [("Compost thermometer", "tool"), ("thermophiles", "concept"), ("pile", "concept")],
     [("Compost thermometer", "pile", "APPLIES_TO")],
     "which temperature thresholds on the compost pile trigger a turn and which probe depth applies",
     "compost thermometer 14 inch 130 160 thermophile turn pile core"),
    # --- 41 ---
    ("Drip-line winterisation goes: close the hose bib, open every end cap, blow the main with 40 PSI compressed air in two passes; cracked emitters from last winter traced to leaving water in the laterals.", "reference", "personal", False,
     [("Drip-line", "tool"), ("end cap", "tool"), ("emitters", "tool")],
     [("Drip-line", "emitters", "USES")],
     "which winterisation steps clear the drip system and what failure from last year drove the routine",
     "drip line winterise hose bib end cap 40 psi compressed air emitter"),
    # --- 42 ---
    ("Inoculated the new blueberry bed with a mycorrhizal fungi powder at planting; the ericoid symbiosis lets 'Bluecrop' and 'Patriot' sip phosphorus from the acid peat mix that would otherwise lock it up.", "architecture", "personal", False,
     [("mycorrhizal fungi", "concept"), ("blueberry", "concept"), ("Bluecrop", "concept"), ("Patriot", "concept"), ("peat", "concept"), ("phosphorus", "concept")],
     [("mycorrhizal fungi", "blueberry", "APPLIES_TO"), ("Bluecrop", "phosphorus", "USES")],
     "which soil inoculant went under the blueberries and why does it matter in an acid peat mix",
     "mycorrhizal ericoid blueberry bluecrop patriot peat phosphorus inoculate"),
    # --- 43. noise ---
    ("The kitchen radio only picks up one station clearly and somehow it's always the one playing sea shanties at lunchtime.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Decided drip tape under the straw mulch over T-tape on top; the tape stays clean of UV degradation, emitters don't silt up with leaf litter, and the whole layout survived the second winter uncovered.", "decision", "personal", False,
     [("drip tape", "tool"), ("T-tape", "tool"), ("straw", "concept"), ("UV degradation", "concept")],
     [("drip tape", "T-tape", "PREFERS"), ("straw", "drip tape", "APPLIES_TO")],
     "which drip-tape placement won out this year and what degradation and silting issue did it address",
     "drip tape t tape straw mulch uv degrade emitter silt leaf litter"),
    # --- 45 ---
    ("The 'Bartlett' pear needed a cross-pollinator so a 'Bosc' went in twelve feet away; pollen transfer by the mason bees from the nearby bee house landed 80 percent fruit set on the 'Bartlett' the following May.", "milestone", "personal", False,
     [("Bartlett", "concept"), ("Bosc", "concept"), ("mason bees", "concept"), ("bee house", "tool")],
     [("Bosc", "Bartlett", "APPLIES_TO"), ("mason bees", "bee house", "USES")],
     "which pear cross-pollination setup and native bee presence lifted fruit set on the Bartlett",
     "bartlett bosc pear cross pollinator mason bee house twelve foot fruit"),
    # --- 46 ---
    ("Prefer a copper trowel over a stainless steel trowel around the slug-prone hosta bed; copper ion residue discourages the slugs from crossing freshly-worked soil and the beer traps got retired after one season.", "preference", "personal", False,
     [("copper trowel", "tool"), ("stainless steel trowel", "tool"), ("hosta", "concept"), ("slugs", "concept"), ("beer traps", "tool")],
     [("copper trowel", "stainless steel trowel", "PREFERS"), ("copper trowel", "slugs", "FIXES")],
     "which trowel material wins around the hosta bed and what slug-control gear did it retire",
     "copper trowel stainless hosta slug beer trap ion residue season"),
    # --- 47 ---
    ("Aphid flare on the indoor 'Mikado' chili plant got knocked out with a neem oil plus potassium soap spray at dusk; reapplied weekly for three weeks to hit each hatch cycle and the new growth came in glossy.", "problem", "personal", False,
     [("Aphid", "concept"), ("Mikado", "concept"), ("neem oil", "concept"), ("potassium soap", "concept")],
     [("neem oil", "Aphid", "FIXES")],
     "which spray mix cleared the indoor chili aphids and what reapplication cadence finished the job",
     "aphid mikado chili neem oil potassium soap dusk weekly hatch spray"),
    # --- 48 ---
    ("The tomato-hornworm problem on the 'Cherokee Purple' was handed off to parasitic Braconid wasps; once the white cocoons appeared on a hornworm the plant got left alone and the wasps finished the job.", "problem", "personal", False,
     [("tomato-hornworm", "concept"), ("Cherokee Purple", "concept"), ("Braconid wasps", "concept")],
     [("Braconid wasps", "tomato-hornworm", "FIXES"), ("Braconid wasps", "Cherokee Purple", "APPLIES_TO")],
     "which biological control finished the hornworm problem on the Cherokee Purple without a spray",
     "tomato hornworm cherokee purple braconid wasp parasitic cocoon white"),
    # --- 49 ---
    ("Soil test from the extension lab pegged the veg-bed pH at 5.6; applied dolomitic lime at four pounds per hundred square feet in autumn and the spring retest came back at 6.4 which the brassicas prefer.", "milestone", "personal", False,
     [("Soil test", "method"), ("pH", "concept"), ("dolomitic lime", "concept"), ("brassicas", "concept")],
     [("dolomitic lime", "pH", "FIXES"), ("dolomitic lime", "brassicas", "APPLIES_TO")],
     "which amendment brought the veg-bed pH from 5.6 up to 6.4 and at what application rate",
     "soil test ph 5 6 dolomitic lime brassica four pound autumn retest"),
    # --- 50 ---
    ("Seed-saving protocol for open-pollinated varieties: isolate by 150 feet for the 'Provider' bush bean, bag the 'Galina' tomato cluster with organza, ferment seed three days, dry seven, store at 40F in a jar with silica.", "reference", "personal", False,
     [("Seed-saving", "method"), ("Provider", "concept"), ("Galina", "concept"), ("organza", "concept"), ("silica", "concept")],
     [("Seed-saving", "Provider", "APPLIES_TO"), ("Seed-saving", "Galina", "APPLIES_TO")],
     "which isolation, fermenting, and storage steps define the home seed-saving routine for these varieties",
     "seed save provider galina organza bag ferment dry silica isolate 150"),
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
