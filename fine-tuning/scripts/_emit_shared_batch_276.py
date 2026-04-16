"""One-off emitter for shared-base batch-276 — personal domain (mushroom foraging and mycology).

Writes 50 rows to data/v2/shared/batch_276.tmp.jsonl with ids shared-13751..13800.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_276.tmp.jsonl"
ID_OFFSET = 13750

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Settled on Morchella importuna as the spring target on the black-cottonwood flats; Morchella esculenta shows up later under the ash grove once soil temperatures climb past fifty degrees.", "decision", "personal", False,
     [("Morchella importuna", "food"), ("black-cottonwood", "place"), ("Morchella esculenta", "food"), ("ash grove", "place")],
     [("Morchella importuna", "black-cottonwood", "LOCATED_IN"), ("Morchella esculenta", "ash grove", "LOCATED_IN")],
     "which morel species did the forager pick as the early spring target on the cottonwood flats and which one comes later",
     "morchella importuna esculenta morel cottonwood ash soil temperature"),
    # --- 2 ---
    ("Swapped the old fixed-blade for an Opinel No 8 with the carbon-steel blade; the curved belly takes spore prints cleanly and the wooden handle doesn't rattle loose in a damp wicker basket.", "decision", "personal", False,
     [("Opinel No 8", "tool"), ("wicker basket", "tool"), ("spore prints", "concept")],
     [("Opinel No 8", "wicker basket", "APPLIES_TO")],
     "which pocket knife did the forager switch to and what feature made it friendly with a wicker basket",
     "opinel no 8 knife carbon steel wicker basket spore print handle"),
    # --- 3 ---
    ("First confirmed Cantharellus californicus under the coast live oak across the ridge; the apricot smell and false gills lined up with Mushrooms Demystified before I trusted the ID.", "milestone", "personal", False,
     [("Cantharellus californicus", "food"), ("coast live oak", "place"), ("Mushrooms Demystified", "publication"), ("false gills", "concept")],
     [("Cantharellus californicus", "coast live oak", "LOCATED_IN")],
     "which chanterelle species did the forager confirm under coast live oak and which field guide sealed the ID",
     "cantharellus californicus chanterelle coast live oak apricot mushrooms demystified"),
    # --- 4 ---
    ("Learned the hard way that Omphalotus illudens glows faintly in the dark and has true gills, unlike the false-gilled Cantharellus cibarius; the jack-o'-lantern cluster on the stump was not dinner.", "problem", "personal", False,
     [("Omphalotus illudens", "food"), ("Cantharellus cibarius", "food"), ("true gills", "concept"), ("false-gilled", "concept")],
     [("Omphalotus illudens", "Cantharellus cibarius", "CONTRADICTS")],
     "which toxic jack-o'-lantern lookalike did the forager learn to separate from true chanterelles and by which feature",
     "omphalotus illudens jack lantern cantharellus cibarius true false gill"),
    # --- 5 ---
    ("Joined the local NAMA affiliated club and now have three experienced members who will double-check any Amanita before it leaves the basket; the walks cost nothing and the ID discipline is worth every minute.", "decision", "personal", False,
     [("NAMA", "organization"), ("Amanita", "food")],
     [("NAMA", "Amanita", "APPLIES_TO")],
     "which mycological club did the forager join and how does the membership reduce Amanita identification risk",
     "nama club membership amanita double check forager walk id"),
    # --- 6 ---
    ("Habitat-matching notebook pairs species to trees: Boletus edulis under spruce, chanterelles under oak, matsutake under tanoak, black trumpets under beech; I look up the host before walking a new patch.", "architecture", "personal", False,
     [("Boletus edulis", "food"), ("spruce", "place"), ("matsutake", "food"), ("tanoak", "place"), ("black trumpets", "food"), ("beech", "place")],
     [("Boletus edulis", "spruce", "LOCATED_IN"), ("matsutake", "tanoak", "LOCATED_IN"), ("black trumpets", "beech", "LOCATED_IN")],
     "how does the forager match species to host trees before walking an unfamiliar patch",
     "habitat match boletus edulis spruce matsutake tanoak black trumpet beech"),
    # --- 7 ---
    ("Prefer Paul Stamets Mycelium Running over generalist field guides when planning cultivation; the substrate tables for Pleurotus ostreatus and Hericium erinaceus are the ones I reach for most.", "preference", "personal", False,
     [("Paul Stamets", "person"), ("Mycelium Running", "publication"), ("Pleurotus ostreatus", "food"), ("Hericium erinaceus", "food")],
     [("Mycelium Running", "Pleurotus ostreatus", "APPLIES_TO"), ("Mycelium Running", "Hericium erinaceus", "APPLIES_TO")],
     "which cultivation reference does the forager prefer for oyster and lion's mane substrate planning",
     "paul stamets mycelium running pleurotus ostreatus hericium erinaceus substrate cultivation"),
    # --- 8 ---
    ("Spore-print protocol for every suspicious gilled find: cap on black-and-white paper overnight under a glass, colour is recorded before any taste test is even considered.", "architecture", "personal", False,
     [("Spore-print", "concept"), ("gilled", "concept")],
     [],
     "which routine does the forager run on suspicious gilled mushrooms before any taste test",
     "spore print protocol gill paper glass overnight colour record"),
    # --- 9 ---
    ("Rejected dehydrator-drying for Boletus edulis and went back to screens near the woodstove; low-and-slow preserves the nutty flavour the dehydrator bakes flat at its lowest setting.", "decision", "personal", False,
     [("Boletus edulis", "food"), ("dehydrator", "tool"), ("woodstove", "tool"), ("screens", "tool")],
     [("screens", "dehydrator", "REPLACES")],
     "which drying method did the forager prefer for porcini and why did the dehydrator lose out",
     "boletus edulis porcini dehydrator woodstove screen dry preserve flavour"),
    # --- 10. noise ---
    ("The cat discovered that the rain jacket hanging by the door is excellent for kneading and now it smells vaguely of damp fur.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Amanita phalloides death cap has a white spore print, a saccate volva at the base, and a greenish-olive cap; any white-gilled mushroom gets dug to the soil line before I accept an ID.", "reference", "personal", False,
     [("Amanita phalloides", "food"), ("saccate volva", "concept"), ("white spore print", "concept")],
     [],
     "which three diagnostic features does the forager check before trusting any white-gilled mushroom ID",
     "amanita phalloides death cap white spore volva green olive dig base"),
    # --- 12 ---
    ("Destroying angel Amanita virosa is pure white top to bottom and fruits near oak here; the pristine white cap in the grass is the one I warn beginners about on every walk.", "reference", "personal", False,
     [("Amanita virosa", "food"), ("oak", "place")],
     [("Amanita virosa", "oak", "LOCATED_IN")],
     "which deadly white Amanita does the forager flag near oak and why do beginners get the warning",
     "amanita virosa destroying angel white oak beginner warning walk"),
    # --- 13 ---
    ("Gyromitra esculenta still shows up in spring under pine and the old-timers still eat it; I don't, because the monomethylhydrazine load is cumulative and the so-called false morel is a hard no in my basket.", "preference", "personal", False,
     [("Gyromitra esculenta", "food"), ("pine", "place"), ("false morel", "concept")],
     [("Gyromitra esculenta", "pine", "LOCATED_IN")],
     "which false morel does the forager refuse to eat despite local tradition and why",
     "gyromitra esculenta false morel pine monomethylhydrazine cumulative refuse"),
    # --- 14 ---
    ("Target burn sites the spring after a fire for Morchella importuna; two years out the flush drops off sharply, and by year four the site stops producing entirely in my logbook.", "architecture", "personal", False,
     [("burn sites", "place"), ("Morchella importuna", "food")],
     [("Morchella importuna", "burn sites", "LOCATED_IN")],
     "how long does the forager's logbook say a burn site stays productive for black morels after a fire",
     "burn site morchella importuna morel flush year fire logbook"),
    # --- 15 ---
    ("Milestone: first Tricholoma magnivelare of the year under tanoak on the coastal bench, unearthed by its smell before it broke duff; the spicy-cinnamon note is unmistakable once you know it.", "milestone", "personal", False,
     [("Tricholoma magnivelare", "food"), ("tanoak", "place")],
     [("Tricholoma magnivelare", "tanoak", "LOCATED_IN")],
     "which matsutake find did the forager log under tanoak and which sense detected it before sight",
     "tricholoma magnivelare matsutake tanoak coastal bench smell spicy"),
    # --- 16 ---
    ("Foraging ethics rule one: never take more than half of any patch, and if it's a small flush I leave it entirely so the spores drop and the patch repeats next year.", "reference", "personal", False,
     [("Foraging ethics", "concept"), ("spores", "concept")],
     [],
     "which sustainability rule does the forager follow on patch harvest to keep flushes returning year over year",
     "foraging ethics half patch spore drop flush repeat sustain harvest"),
    # --- 17 ---
    ("Cultivation shelf now runs a sawdust-block kit of Hericium erinaceus next to a straw-log of Pleurotus ostreatus; both came from the same supplier and fruited within three weeks of pinning.", "milestone", "personal", False,
     [("Hericium erinaceus", "food"), ("Pleurotus ostreatus", "food"), ("sawdust-block", "tool"), ("straw-log", "tool")],
     [("sawdust-block", "Hericium erinaceus", "APPLIES_TO"), ("straw-log", "Pleurotus ostreatus", "APPLIES_TO")],
     "which two cultivation kits does the forager run side by side and what substrate does each need",
     "hericium erinaceus pleurotus ostreatus sawdust block straw log cultivation kit"),
    # --- 18 ---
    ("Lobster mushroom Hypomyces lactifluorum is a parasitic mould on Russula and Lactarius; the orange crust transforms the host flesh into something genuinely good, which is still a strange thing to say out loud.", "fact", "personal", False,
     [("Hypomyces lactifluorum", "food"), ("Russula", "food"), ("Lactarius", "food")],
     [("Hypomyces lactifluorum", "Russula", "APPLIES_TO"), ("Hypomyces lactifluorum", "Lactarius", "APPLIES_TO")],
     "which host genera does the lobster mushroom parasitise and what does the parasitism do to their flesh",
     "hypomyces lactifluorum lobster russula lactarius parasite orange crust"),
    # --- 19 ---
    ("Dropped the plastic grocery bag habit entirely for a wicker basket; spores can fall through and the mushrooms don't sweat into mush on the two-hour walk out.", "decision", "personal", False,
     [("plastic grocery bag", "tool"), ("wicker basket", "tool"), ("spores", "concept")],
     [("wicker basket", "plastic grocery bag", "REPLACES")],
     "which carry method did the forager retire and what two problems did the wicker basket solve",
     "plastic bag wicker basket spore drop sweat walk out preserve"),
    # --- 20 ---
    ("Galerina marginata fruits on the same rotten logs as Pleurotus ostreatus in fall; it's deadly and it's tiny, so I inspect every cluster base on the log before cutting oysters.", "reference", "personal", False,
     [("Galerina marginata", "food"), ("Pleurotus ostreatus", "food"), ("rotten logs", "place")],
     [("Galerina marginata", "rotten logs", "LOCATED_IN"), ("Pleurotus ostreatus", "rotten logs", "LOCATED_IN")],
     "which deadly small Galerina shares rotten-log habitat with oysters and how does the forager avoid a mix-up",
     "galerina marginata pleurotus ostreatus rotten log fall inspect cluster"),
    # --- 21 ---
    ("Hen of the woods Grifola frondosa comes back on the same white oak at the edge of the county park every September; the tree is a repeat producer and I keep its GPS waypoint off every shared map.", "architecture", "personal", False,
     [("Grifola frondosa", "food"), ("white oak", "place"), ("GPS waypoint", "concept")],
     [("Grifola frondosa", "white oak", "LOCATED_IN")],
     "which repeat Grifola tree does the forager keep quiet and what tool stays off shared maps",
     "grifola frondosa hen woods white oak september gps waypoint county"),
    # --- 22 ---
    ("Laetiporus sulphureus on a dead conifer turned my stomach; I now only harvest chicken of the woods from oak or other hardwoods, and always from younger margins that are still tender.", "decision", "personal", False,
     [("Laetiporus sulphureus", "food"), ("conifer", "place"), ("oak", "place"), ("hardwoods", "place")],
     [("Laetiporus sulphureus", "oak", "LOCATED_IN")],
     "which host tree made the forager sick on chicken of the woods and which hosts are the safer choice",
     "laetiporus sulphureus chicken woods conifer oak hardwood tender margin"),
    # --- 23 ---
    ("CleverCat harvesting knife lives in the basket now for the gentle saw-back: it cleans the base of Tricholoma magnivelare without disturbing the mycelial mat, which an Opinel tends to tear.", "decision", "personal", False,
     [("CleverCat", "tool"), ("Tricholoma magnivelare", "food"), ("mycelial mat", "concept"), ("Opinel", "tool")],
     [("CleverCat", "mycelial mat", "APPLIES_TO")],
     "which harvesting knife took over from the Opinel for matsutake and what ecological feature drove the change",
     "clevercat knife opinel matsutake tricholoma mycelial mat saw back"),
    # --- 24 ---
    ("Hydnum repandum hedgehog mushrooms under douglas fir carry tiny spines instead of gills; I teach every newcomer this species first because it has no deadly lookalike in the region.", "preference", "personal", False,
     [("Hydnum repandum", "food"), ("douglas fir", "place"), ("spines", "concept")],
     [("Hydnum repandum", "douglas fir", "LOCATED_IN")],
     "which beginner-safe mushroom does the forager teach first and which habitat matches it here",
     "hydnum repandum hedgehog douglas fir spine beginner teach safe"),
    # --- 25 ---
    ("Cortinarius orellanus contains orellanine that damages kidneys days to weeks after ingestion; any web-veiled rusty-gilled mushroom stays in the ground and gets photographed, nothing more.", "reference", "personal", False,
     [("Cortinarius orellanus", "food"), ("orellanine", "concept"), ("web-veiled", "concept")],
     [],
     "which toxin in Cortinarius orellanus strikes late and which visual features trigger a no-pick",
     "cortinarius orellanus orellanine kidney web veil rusty gill delayed toxicity"),
    # --- 26 ---
    ("Habit log now tags every find with host tree, elevation, slope aspect, and date; three seasons in, the patterns in the spreadsheet beat my memory for where to walk on a given week.", "architecture", "personal", False,
     [("host tree", "concept"), ("slope aspect", "concept"), ("spreadsheet", "tool")],
     [],
     "which four fields does the forager log per find and how did the spreadsheet change planning behaviour",
     "habit log host tree elevation slope aspect date spreadsheet pattern"),
    # --- 27 ---
    ("Entoloma sinuatum fruits near oak around here and pretends to be an edible Clitocybe; pink spore print is the giveaway, white for the edible, pink for the hospital visit.", "reference", "personal", False,
     [("Entoloma sinuatum", "food"), ("Clitocybe", "food"), ("oak", "place"), ("pink spore print", "concept")],
     [("Entoloma sinuatum", "Clitocybe", "CONTRADICTS"), ("Entoloma sinuatum", "oak", "LOCATED_IN")],
     "which spore colour separates the toxic Entoloma from the edible Clitocybe in oak habitat here",
     "entoloma sinuatum clitocybe oak pink spore print hospital lookalike"),
    # --- 28 ---
    ("Craterellus cornucopioides patches along the beech seep produced nearly two pounds dried last November; the black trumpets resprout in the same square metre for at least four seasons running.", "milestone", "personal", False,
     [("Craterellus cornucopioides", "food"), ("beech seep", "place")],
     [("Craterellus cornucopioides", "beech seep", "LOCATED_IN")],
     "which black trumpet patch produced the big November haul and how many seasons does it recur",
     "craterellus cornucopioides black trumpet beech seep november dry pound"),
    # --- 29 ---
    ("Coprinus comatus shaggy mane deliquesces into black ink within six hours of picking; same-day cooking is the only acceptable workflow, the fridge does nothing to slow the clock.", "fact", "personal", False,
     [("Coprinus comatus", "food"), ("deliquesces", "concept")],
     [],
     "which shaggy mane behaviour forces same-day cooking and why does the fridge not help",
     "coprinus comatus shaggy mane deliquesce black ink same day cook"),
    # --- 30 ---
    ("Lion's mane cultivation kit from the supplier fruited on oat-and-sawdust after a cold shock in the fridge; second flush came three weeks later with about sixty percent of the first yield.", "fact", "personal", False,
     [("Lion's mane", "food"), ("cultivation kit", "tool"), ("oat-and-sawdust", "concept"), ("cold shock", "concept")],
     [("cultivation kit", "Lion's mane", "APPLIES_TO")],
     "which trigger and substrate did the lion's mane kit need and what did the second flush yield",
     "lion mane cultivation kit oat sawdust cold shock flush yield"),
    # --- 31 ---
    ("Shiitake logs inoculated with plug spawn in March fruited in the second fall, not the first; patience on oak logs is the lesson, and stacking them in shade with a soaker hose kept the bark tight.", "milestone", "personal", False,
     [("Shiitake", "food"), ("plug spawn", "tool"), ("oak logs", "place"), ("soaker hose", "tool")],
     [("Shiitake", "oak logs", "LOCATED_IN")],
     "how long did the shiitake logs take to fruit and which moisture tool kept the bark right",
     "shiitake plug spawn march oak log fall soaker hose shade bark"),
    # --- 32 ---
    ("Enoki grown in jars under low light produced the tall pale cluster you see in grocery stores; bright light gave brown caps and stubby stems, interesting but nothing like the commercial product.", "fact", "personal", False,
     [("Enoki", "food"), ("low light", "concept"), ("jars", "tool")],
     [],
     "which light condition produced the commercial-looking enoki and how did bright light change the morph",
     "enoki jar low light tall pale cluster brown cap stub commercial"),
    # --- 33 ---
    ("Boletus edulis king bolete pinned up under spruce at eighteen hundred metres the morning after the first heavy fog; the reticulated stem and sponge under the cap separated it from the bitter Tylopilus felleus.", "milestone", "personal", False,
     [("Boletus edulis", "food"), ("spruce", "place"), ("Tylopilus felleus", "food"), ("reticulated stem", "concept")],
     [("Boletus edulis", "spruce", "LOCATED_IN"), ("Boletus edulis", "Tylopilus felleus", "CONTRADICTS")],
     "which porcini find came with heavy fog and which bitter lookalike did the forager rule out",
     "boletus edulis porcini spruce fog reticulate tylopilus felleus bitter"),
    # --- 34 ---
    ("Reject any Amanita with even slightly greenish or yellowish cap near oak without extended field consultation; the rule is blanket because phalloides variants show colour drift in dry weeks.", "decision", "personal", False,
     [("Amanita", "food"), ("oak", "place"), ("phalloides", "food")],
     [("phalloides", "oak", "LOCATED_IN")],
     "which Amanita colour shift forces a blanket reject near oak and why is the rule not narrower",
     "amanita phalloides oak green yellow cap drift reject blanket rule"),
    # --- 35 ---
    ("David Arora's Mushrooms Demystified sits in the truck with annotated margins; the genera keys are the part I actually use, and the regional notes flag which of my finds are east-coast-centric misleads.", "fact", "personal", False,
     [("David Arora", "person"), ("Mushrooms Demystified", "publication"), ("genera keys", "concept")],
     [],
     "which section of Mushrooms Demystified does the forager use most and which regional risk does the book flag",
     "david arora mushrooms demystified genera key regional east coast mislead"),
    # --- 36 ---
    ("Switched the drying rack from nylon mesh to cedar slats; nylon picked up the black-trumpet smell and the cedar breathes without transferring flavour between batches.", "decision", "personal", False,
     [("nylon mesh", "tool"), ("cedar slats", "tool"), ("black-trumpet", "food")],
     [("cedar slats", "nylon mesh", "REPLACES")],
     "which drying-rack material replaced nylon mesh and which flavour-carry problem did it solve",
     "nylon mesh cedar slat dry rack black trumpet smell transfer batch"),
    # --- 37 ---
    ("Pitched the idea of a club-wide patch-rotation map to the NAMA chapter; motion failed because the veterans prefer private notebooks, and I agreed after hearing the poaching histories.", "decision", "personal", False,
     [("NAMA", "organization"), ("patch-rotation map", "concept"), ("poaching", "concept")],
     [],
     "which club-wide mapping proposal did the forager drop and which historical issue changed the mind",
     "nama chapter patch rotation map veteran private notebook poaching"),
    # --- 38 ---
    ("Standing rule: no ingestion without a spore print and a confirmed ID from two sources, even for species I've eaten before; the complacency margin is where people get hurt.", "preference", "personal", False,
     [("spore print", "concept"), ("ingestion", "concept")],
     [],
     "which two-source ID rule does the forager apply even to familiar species and why",
     "ingest spore print confirm two source id familiar complacency rule"),
    # --- 39 ---
    ("Matsutake season timing tracks the first frost at the coastal bench; Tricholoma magnivelare pushes up the week after, and tanoak duff needs a gentle sweep with the hand rather than a rake.", "architecture", "personal", False,
     [("Matsutake", "food"), ("Tricholoma magnivelare", "food"), ("tanoak duff", "place")],
     [("Tricholoma magnivelare", "tanoak duff", "LOCATED_IN")],
     "which weather trigger precedes matsutake and which harvest tool is explicitly out of bounds",
     "matsutake tricholoma magnivelare frost coastal bench tanoak duff rake"),
    # --- 40 ---
    ("Oak duff plus a southwest slope at around eight hundred metres is the Cantharellus cibarius pattern that my logbook keeps confirming year after year.", "architecture", "personal", False,
     [("Oak duff", "place"), ("southwest slope", "concept"), ("Cantharellus cibarius", "food")],
     [("Cantharellus cibarius", "Oak duff", "LOCATED_IN")],
     "which three-factor pattern does the logbook repeatedly confirm for golden chanterelles",
     "oak duff southwest slope chanterelle cantharellus cibarius logbook pattern"),
    # --- 41 ---
    ("Tried a clamshell cultivation kit for Hericium erinaceus on the kitchen counter and the fruiting was weak; moved it to the unheated garage, humidity rose, and the beard-like clusters filled out within a week.", "problem", "personal", False,
     [("clamshell", "tool"), ("Hericium erinaceus", "food"), ("garage", "place"), ("humidity", "concept")],
     [("Hericium erinaceus", "garage", "LOCATED_IN")],
     "which environmental change fixed the weak lion's mane fruiting from the clamshell kit",
     "hericium erinaceus clamshell kit kitchen garage humidity fruit weak"),
    # --- 42 ---
    ("Pleurotus ostreatus on the cottonwood stump across the creek refruits every three weeks through October; it's the most reliable wild patch in the log and the shortest hike from the truck.", "fact", "personal", False,
     [("Pleurotus ostreatus", "food"), ("cottonwood stump", "place")],
     [("Pleurotus ostreatus", "cottonwood stump", "LOCATED_IN")],
     "which wild patch does the log call the most reliable and what is its refruit cadence",
     "pleurotus ostreatus oyster cottonwood stump october three week reliable"),
    # --- 43. noise ---
    ("The upstairs neighbour took up the accordion and by the sound of it is three weeks away from surprising a wedding party.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Separate baskets for identified and unknown finds is the new rule after a Cortinarius brushed against a confirmed Cantharellus cibarius last October and I had to toss the whole haul.", "decision", "personal", False,
     [("Cortinarius", "food"), ("Cantharellus cibarius", "food"), ("baskets", "tool")],
     [("Cortinarius", "Cantharellus cibarius", "CONTRADICTS")],
     "which cross-contamination event led to separate baskets and which genera were involved",
     "cortinarius cantharellus cibarius basket separate contaminate toss haul"),
    # --- 45 ---
    ("Cooked-taste-test rule: one tablespoon of any newly-accepted species first, wait twenty-four hours before eating a full portion; saved me once with a Laetiporus sulphureus that I personally don't tolerate.", "decision", "personal", False,
     [("taste-test", "concept"), ("Laetiporus sulphureus", "food")],
     [],
     "which personal-tolerance protocol runs before a full portion and which species surfaced an intolerance",
     "taste test tablespoon twenty four hour laetiporus sulphureus intolerance"),
    # --- 46 ---
    ("Hen of the woods cultivation failed twice on sawdust blocks and succeeded on an inoculated oak log buried half-deep in the shade bed; the species wants wood, not a brick.", "problem", "personal", False,
     [("Hen of the woods", "food"), ("sawdust blocks", "tool"), ("oak log", "place"), ("shade bed", "place")],
     [("Hen of the woods", "oak log", "LOCATED_IN")],
     "which cultivation substrate finally worked for hen of the woods after two sawdust-block failures",
     "hen woods sawdust block oak log buried shade bed cultivation fail"),
    # --- 47 ---
    ("Field-guide stack now sits at three: Mushrooms Demystified for breadth, a regional bolete monograph, and Mycelium Running for cultivation; anything else lives on the shelf.", "architecture", "personal", False,
     [("Mushrooms Demystified", "publication"), ("bolete monograph", "publication"), ("Mycelium Running", "publication")],
     [],
     "which three field guides does the forager actively carry and which role does each fill",
     "mushrooms demystified bolete monograph mycelium running field guide stack"),
    # --- 48 ---
    ("First true Morchella esculenta of the season came out under the old apple by the fence line; yellow morels on abandoned orchard ground is a pattern the logbook now predicts within about a week.", "fact", "personal", False,
     [("Morchella esculenta", "food"), ("apple", "place"), ("orchard", "place")],
     [("Morchella esculenta", "apple", "LOCATED_IN"), ("Morchella esculenta", "orchard", "LOCATED_IN")],
     "which yellow morel pattern does the logbook now predict and where did the first one of the season show",
     "morchella esculenta morel apple orchard fence logbook season predict"),
    # --- 49 ---
    ("Club walk this fall found a Cantharellus cibarius flush big enough for the whole group to leave with a pound each; foraging ethics of half-a-patch held and next year's potential is intact.", "milestone", "personal", False,
     [("Cantharellus cibarius", "food"), ("foraging ethics", "concept"), ("Club walk", "concept")],
     [],
     "which chanterelle flush did the club share while keeping the half-a-patch rule intact",
     "cantharellus cibarius chanterelle club walk fall pound ethics half"),
    # --- 50 ---
    ("Switched the primary carry to a two-basket rig strapped to the pack: a small wicker basket up top for fragile finds and a larger one below for porcini and chicken of the woods.", "architecture", "personal", False,
     [("two-basket rig", "tool"), ("wicker basket", "tool"), ("porcini", "food"), ("chicken of the woods", "food")],
     [("wicker basket", "porcini", "APPLIES_TO"), ("wicker basket", "chicken of the woods", "APPLIES_TO")],
     "which two-basket carry setup does the forager strap to the pack and how are species distributed between them",
     "two basket rig pack wicker porcini chicken woods fragile carry"),
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
