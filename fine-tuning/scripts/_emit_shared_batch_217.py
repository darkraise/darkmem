"""One-off emitter for shared-base batch-217 — personal domain (knife making and bladesmithing: steels, forges, hammers, heat treatment, Damascus, handles, knife designs, Japanese and custom makers).

Writes 50 rows to data/v2/shared/batch_217.tmp.jsonl with ids shared-10801..10850.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_217.tmp.jsonl"
ID_OFFSET = 10800

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Switched my go-to carbon bar from 1084 to 26C3 for petty blades because the finer grain holds a thinner edge after a quick oil quench.", "decision", "personal", False,
     [("1084", "technology"), ("26C3", "technology"), ("petty", "concept")],
     [("26C3", "1084", "REPLACES")],
     "which simple carbon steel did I pick over 1084 for petty blades and what grain behaviour drove it",
     "26c3 1084 carbon steel petty fine grain oil quench edge"),
    # --- 2 ---
    ("Upgraded the shop grinder from a Beaumont KMG-10 to a full 2x72 with variable frequency drive so I can crawl at twenty surface feet per minute on the hamon polish.", "milestone", "personal", False,
     [("Beaumont", "organization"), ("KMG-10", "tool"), ("2x72", "tool"), ("hamon", "concept")],
     [("2x72", "KMG-10", "REPLACES")],
     "which belt grinder setup replaced the KMG-10 for slow hamon polishing in the shop",
     "beaumont kmg 2x72 belt grinder vfd hamon polish slow"),
    # --- 3 ---
    ("My primary blade steel for the chef's knife line is now CPM MagnaCut; it dropped the chromium carbide problem that made S35VN chippy on bone contact.", "decision", "personal", False,
     [("CPM MagnaCut", "technology"), ("S35VN", "technology"), ("chef's knife", "concept")],
     [("CPM MagnaCut", "S35VN", "REPLACES")],
     "which stainless powder steel replaced S35VN for my chef's knives and which carbide issue prompted the switch",
     "magnacut s35vn chef chromium carbide chipping bone powder steel"),
    # --- 4 ---
    ("Finished a san-mai gyuto with an AEB-L core wrapped in nickel-damascus cladding; the contrast pops after a brief ferric chloride etch.", "milestone", "personal", False,
     [("san-mai", "pattern"), ("gyuto", "concept"), ("AEB-L", "technology"), ("nickel-damascus", "pattern"), ("ferric chloride", "technology")],
     [("san-mai", "AEB-L", "USES"), ("nickel-damascus", "san-mai", "HAS_PART")],
     "which three-layer lamination design did I finish for the gyuto and how did the cladding reveal itself",
     "san mai gyuto aeb-l nickel damascus cladding ferric etch contrast"),
    # --- 5 ---
    ("Decided to use clay quench on my W2 hunters rather than edge quench; the satoetsu-style clay line gives a wilder hamon than a straight edge dip into oil.", "decision", "personal", False,
     [("clay quench", "method"), ("W2", "technology"), ("edge quench", "method"), ("hamon", "concept")],
     [("clay quench", "edge quench", "PREFERS"), ("clay quench", "W2", "APPLIES_TO")],
     "which differential heat-treatment did I pick for W2 hunters over a straight edge dip and what visual did it unlock",
     "clay quench edge w2 hamon hunter satoetsu wild line differential"),
    # --- 6 ---
    ("Forge rebuild done: swapped the old brick coal forge for a dual-burner propane setup running at roughly nine psi for long bar soaks.", "milestone", "personal", False,
     [("coal forge", "tool"), ("propane", "technology"), ("dual-burner", "tool")],
     [("propane", "coal forge", "REPLACES")],
     "which forge did I rebuild around and what burner pressure runs the long bar soaks now",
     "propane coal forge dual burner soak nine psi rebuild shop"),
    # --- 7 ---
    ("Apex Ultra is my pick for outdoor fixed blades; its tungsten-molybdenum chemistry holds a working edge through a day of batoning hardwood without rolling.", "preference", "personal", False,
     [("Apex Ultra", "technology"), ("batoning", "activity")],
     [("Apex Ultra", "batoning", "APPLIES_TO")],
     "which high-alloy carbon steel did I settle on for outdoor fixed blades and what abuse can it take",
     "apex ultra outdoor fixed blade tungsten moly baton hardwood edge"),
    # --- 8 ---
    ("Differential heat treatment on my O1 kiritsuke used Satanite for the soft back and a thin itoh-style clay line along the edge; quench into fast oil at 1475 F.", "architecture", "personal", False,
     [("O1", "technology"), ("kiritsuke", "concept"), ("Satanite", "technology"), ("soft back", "concept"), ("1475 F", "config")],
     [("Satanite", "O1", "APPLIES_TO"), ("soft back", "kiritsuke", "HAS_PART")],
     "how did the clay layout and quench temperature shake out on the differential O1 kiritsuke",
     "o1 kiritsuke satanite clay soft back itoh quench fast oil 1475"),
    # --- 9 ---
    ("Tamahagane ingot from the last tatara run went into a single honesuki; the folding brought the carbon down to workable range and the hada showed up lightly after etch.", "milestone", "personal", False,
     [("Tamahagane", "technology"), ("tatara", "tool"), ("honesuki", "concept"), ("hada", "concept")],
     [("Tamahagane", "honesuki", "APPLIES_TO")],
     "what did the last tatara-sourced tamahagane ingot become and how did the folded grain pattern present",
     "tamahagane tatara honesuki hada fold carbon etch ingot single"),
    # --- 10. noise ---
    ("The cat keeps napping on the drill press stand despite the sign asking people not to put coffee there.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("My chef's knife blank pattern is the Kramer curve traced at eight inches; the belly profile rocks through a board of onions without knuckle drag.", "reference", "personal", False,
     [("Kramer", "person"), ("chef's knife", "concept")],
     [("chef's knife", "Kramer", "BUILDS_ON")],
     "whose chef's knife curve do I trace for my eight-inch blanks and why does the belly profile matter",
     "kramer chef knife curve eight inch belly rock onion knuckle"),
    # --- 12 ---
    ("Picked up a Takeda nakiri as a reference for edge geometry; the asymmetric grind and near-zero shoulder are what I want on my own stainless clad nakiri.", "reference", "personal", False,
     [("Takeda", "person"), ("nakiri", "concept"), ("asymmetric grind", "method")],
     [("nakiri", "Takeda", "BUILDS_ON")],
     "which Japanese maker's nakiri did I buy as a geometry reference and which grind features am I chasing",
     "takeda nakiri asymmetric grind shoulder reference stainless clad"),
    # --- 13 ---
    ("Cross-pein hammer at two and a half pounds is my drawing-out hammer; the ball-pein gets reserved for fullering and the straight-pein only comes out for tight ricasso work.", "preference", "personal", False,
     [("Cross-pein", "tool"), ("ball-pein", "tool"), ("straight-pein", "tool"), ("ricasso", "concept")],
     [("Cross-pein", "ball-pein", "PREFERS")],
     "which of my three pein hammers handles drawing out and what do the other two get used for",
     "cross pein ball straight hammer draw fuller ricasso weight"),
    # --- 14 ---
    ("Desert ironwood burl is my default handle wood for premium orders; stabilized maple burl goes on mid-tier blades and cocobolo is off the shop list now due to the dust sensitisation.", "preference", "personal", False,
     [("Desert ironwood", "technology"), ("stabilized maple burl", "technology"), ("cocobolo", "technology")],
     [("Desert ironwood", "cocobolo", "REPLACES")],
     "which handle wood sits on my premium builds and which one did I drop over dust sensitisation",
     "ironwood cocobolo maple burl stabilized handle premium dust"),
    # --- 15 ---
    ("Scales on the Micarta-handled bunka are pinned with three Corby bolts rather than mosaic pins; the Corbys bite into the tang and the joint survives a drop onto concrete.", "decision", "personal", False,
     [("Micarta", "technology"), ("bunka", "concept"), ("Corby bolts", "tool"), ("mosaic pins", "tool")],
     [("Corby bolts", "mosaic pins", "REPLACES")],
     "which fastener did I pick for the Micarta bunka over mosaic pins and what failure mode drove it",
     "corby bolt mosaic pin micarta bunka tang handle drop concrete"),
    # --- 16 ---
    ("52100 yanagiba blanks are prone to a micro-crack from the tip during oil quench whenever the tip soaks hotter than the rest of the blade in the forge; the quench-temp gradient is the load-bearing variable.", "fact", "personal", False,
     [("52100", "technology"), ("yanagiba", "concept"), ("oil quench", "method"), ("micro-crack", "finding")],
     [("micro-crack", "52100", "APPLIES_TO")],
     "which failure mode hit the 52100 yanagiba quench and what was the root cause on the forge side",
     "52100 yanagiba quench crack tip pre heat forge oil propagate"),
    # --- 17 ---
    ("Nitro-V is my budget stainless for the utility knife line; it takes a decent working edge, doesn't need a cryo soak to get the carbides in line, and the home heat treat oven handles it.", "fact", "personal", False,
     [("Nitro-V", "technology"), ("utility knife", "concept"), ("cryo soak", "method"), ("heat treat oven", "tool")],
     [("Nitro-V", "utility knife", "APPLIES_TO")],
     "which stainless steel sits in my budget utility knife slot and which treatment step does it skip",
     "nitro-v utility stainless cryo soak heat treat oven budget"),
    # --- 18 ---
    ("CPM M4 is the tool-steel choice for my competition cutters; it beats S35VN on rope-chop endurance but demands a wax-rub coat because it rusts under a damp chamois.", "fact", "personal", False,
     [("CPM M4", "technology"), ("S35VN", "technology"), ("rope-chop", "activity")],
     [("CPM M4", "S35VN", "IMPROVES_ON")],
     "which tool steel wins on competition rope-chop over S35VN and what corrosion care does it demand",
     "cpm m4 s35vn competition rope chop wax chamois rust tool"),
    # --- 19 ---
    ("Hamon visibility on the 1095 tanto ended up flat even after a two-pass clay reapply; the culprit was an over-long austenitise soak that let carbon diffuse too evenly.", "problem", "personal", False,
     [("1095", "technology"), ("tanto", "concept"), ("Hamon", "concept"), ("austenitise", "method")],
     [("austenitise", "Hamon", "CAUSES")],
     "which heat-treatment mistake killed hamon contrast on the 1095 tanto despite reapplied clay",
     "1095 tanto hamon clay austenitise long soak carbon diffusion"),
    # --- 20 ---
    ("Induction forge pilot at the collective shop pulled a 1084 bar from room temp to non-magnetic in under forty seconds; the uniform heat made quenching a joy but the hood draw couldn't keep up.", "fact", "personal", False,
     [("Induction forge", "tool"), ("1084", "technology"), ("non-magnetic", "concept")],
     [("Induction forge", "1084", "APPLIES_TO")],
     "what did the collective's induction forge trial show for 1084 heat-up and what shop bottleneck emerged",
     "induction forge 1084 non magnetic heat quench hood draw"),
    # --- 21 ---
    ("Pattern-welded billet of fifteen layers 1084 with O1 will get drawn out twice and then acid-etched; the goal is a tight ladder for a sujihiki order next month.", "architecture", "personal", False,
     [("Pattern-welded", "pattern"), ("1084", "technology"), ("O1", "technology"), ("sujihiki", "concept"), ("ladder", "pattern")],
     [("Pattern-welded", "sujihiki", "APPLIES_TO"), ("ladder", "Pattern-welded", "HAS_PART")],
     "how is the fifteen-layer pattern-welded billet routed to become a ladder-pattern sujihiki",
     "pattern weld 1084 o1 fifteen layer ladder sujihiki draw etch"),
    # --- 22 ---
    ("Kato-style grind on the petty means a near-convex primary with a short shinogi line; my grind sequence is rough bevel on the KMG, transition to a slack belt for the convex, then hand-stone the shinogi flat.", "architecture", "personal", False,
     [("Kato", "person"), ("petty", "concept"), ("shinogi", "concept"), ("convex", "method")],
     [("petty", "Kato", "BUILDS_ON")],
     "which Japanese maker's grind inspired my petty geometry and which line was hardest to keep straight",
     "kato petty convex shinogi grind geometry straight three months"),
    # --- 23 ---
    ("Shibata is a reference for thin stock chef's knives; the R2 powder steel he uses at 1.8 millimetres spine thickness is my target for the next batch of gyutos.", "reference", "personal", False,
     [("Shibata", "person"), ("R2", "technology"), ("gyuto", "concept")],
     [("Shibata", "R2", "USES"), ("gyuto", "Shibata", "BUILDS_ON")],
     "whose thin-stock powder-steel chef knives am I benchmarking the next gyuto batch against",
     "shibata r2 gyuto thin stock powder spine reference 1.8 mm"),
    # --- 24 ---
    ("Tsunehisa blue-two honyaki yanagiba bought at Tosho is on the tool rack as a finish-line reference; mirror polish, straight hamon, no visible grind marks anywhere on the ji.", "reference", "personal", False,
     [("Tsunehisa", "organization"), ("Tosho", "organization"), ("yanagiba", "concept"), ("honyaki", "method"), ("ji", "concept")],
     [("yanagiba", "Tsunehisa", "AUTHORED_BY")],
     "which shop's Tsunehisa honyaki yanagiba sits as my finishing reference and what polish details am I chasing",
     "tsunehisa tosho yanagiba honyaki mirror polish hamon ji reference"),
    # --- 25 ---
    ("Yoshikane SKD damascus santoku on the bench shows the exact wave pattern I want to reproduce; the layer count looks like roughly one hundred twenty layers before the final draw.", "reference", "personal", False,
     [("Yoshikane", "organization"), ("SKD", "technology"), ("santoku", "concept"), ("damascus", "pattern")],
     [("santoku", "Yoshikane", "AUTHORED_BY"), ("damascus", "SKD", "HAS_PART")],
     "whose damascus santoku am I copying the wave pattern from and roughly how many layers are there",
     "yoshikane skd santoku damascus wave pattern layer reference"),
    # --- 26 ---
    ("Decided to skip D2 entirely going forward; the huge primary carbides tore out under a polishing belt and the edge looked like a saw under the microscope.", "decision", "personal", False,
     [("D2", "technology"), ("primary carbides", "finding"), ("polishing belt", "tool")],
     [("primary carbides", "D2", "APPLIES_TO")],
     "which steel did I drop from the lineup due to carbide tear-out and what magnification revealed it",
     "d2 carbide tear out polishing belt microscope edge saw"),
    # --- 27 ---
    ("CPM 154 stays on the roster for the boning knife slot; it's forgiving at the home heat treat oven, takes a fine edge, and the chromium content shrugs off acidic marinades on the cutting board.", "fact", "personal", False,
     [("CPM 154", "technology"), ("boning knife", "concept"), ("chromium", "concept")],
     [("CPM 154", "boning knife", "APPLIES_TO")],
     "which powder stainless keeps its spot for my boning knives and why does it suit the kitchen environment",
     "cpm 154 boning stainless chromium heat treat oven fine edge"),
    # --- 28 ---
    ("Devin Thomas mosaic damascus billet bought for the anniversary gyuto gets cut to a pre-shaped blank before heat treat; no forging on that bar or the pattern smears in the bevel.", "decision", "personal", False,
     [("Devin Thomas", "person"), ("mosaic damascus", "pattern"), ("gyuto", "concept")],
     [("mosaic damascus", "Devin Thomas", "AUTHORED_BY"), ("gyuto", "mosaic damascus", "USES")],
     "whose mosaic damascus did I source for the anniversary gyuto and what process rule did I set on the billet",
     "devin thomas mosaic damascus gyuto anniversary stock removal blank"),
    # --- 29 ---
    ("Daitou stock came in at 2.2 millimetres for a batch of petty blades; the laminated white-two on soft iron cladding is stiff without being heavy.", "fact", "personal", False,
     [("Daitou", "organization"), ("petty", "concept"), ("white-two", "technology"), ("soft iron", "technology")],
     [("Daitou", "white-two", "USES")],
     "which laminated Japanese stock did I order and what thickness is it for the petty batch",
     "daitou white two soft iron petty laminate 2.2 mm stock"),
    # --- 30 ---
    ("Deba build in W2 needs a thick spine and a long ji polish; Sashiko-style rough stone before moving to natural fingerstones is the sequence I'll use.", "architecture", "personal", False,
     [("W2", "technology"), ("Deba", "concept"), ("ji", "concept"), ("fingerstones", "tool")],
     [("Deba", "W2", "USES")],
     "what stone sequence did I plan for the long ji polish on the W2 deba",
     "w2 deba ji polish sashiko rough fingerstone natural sequence"),
    # --- 31 ---
    ("Usuba experiment used single-bevel grinding on A2 instead of shirogami; the stainless-adjacent A2 held a passable ura but the edge felt buttery compared to white-steel sharpness.", "problem", "personal", False,
     [("Usuba", "concept"), ("A2", "technology"), ("shirogami", "technology"), ("ura", "concept")],
     [("A2", "shirogami", "CONTRADICTS")],
     "what happened when I tried A2 on a single-bevel usuba instead of shirogami and which edge trait suffered",
     "usuba a2 shirogami single bevel ura buttery edge experiment"),
    # --- 32 ---
    ("G10 scales on tactical fixed blades are bedded with West System epoxy and the liner is a 0.5 millimetre black G10 sheet; looks clean and the joint survives a salt soak.", "architecture", "personal", False,
     [("G10", "technology"), ("West System", "organization"), ("epoxy", "technology"), ("salt soak", "method")],
     [("G10", "West System", "USES")],
     "which epoxy system and liner setup am I using under G10 scales on the tactical builds",
     "g10 west system epoxy liner black 0.5 mm salt soak tactical"),
    # --- 33 ---
    ("Clay-quench recipe for 1095 nakiri now uses a thin Rutland furnace cement wash instead of a thick Satanite mix; the thinner coat produces a crisp notare hamon consistently across the batch.", "architecture", "personal", False,
     [("1095", "technology"), ("nakiri", "concept"), ("notare", "pattern"), ("Satanite", "technology"), ("Rutland", "organization")],
     [("Rutland", "Satanite", "REPLACES")],
     "which clay change finally gave the 1095 nakiri a crisp notare hamon",
     "1095 nakiri notare hamon rutland satanite clay slurry thin wash"),
    # --- 34 ---
    ("Soft back on the 26C3 bunka was spec'd at Rockwell 45 versus edge at 63; the shim-up tempering in the kitchen oven at 400 F twice nailed the differential hardness on a test coupon.", "architecture", "personal", False,
     [("Soft back", "concept"), ("26C3", "technology"), ("bunka", "concept"), ("Rockwell", "concept"), ("400 F", "config")],
     [("Soft back", "26C3", "APPLIES_TO")],
     "how did the differential hardness on the 26C3 bunka get dialed in between back and edge",
     "soft back 26c3 bunka rockwell 45 63 temper 400 f kitchen"),
    # --- 35 ---
    ("Plan for the next show is five blades: a gyuto, a petty, a nakiri, a honesuki, and a bunka, all in a matching handle set of desert ironwood with black Micarta bolster.", "architecture", "personal", False,
     [("gyuto", "concept"), ("petty", "concept"), ("nakiri", "concept"), ("honesuki", "concept"), ("bunka", "concept"), ("desert ironwood", "technology"), ("Micarta", "technology")],
     [("gyuto", "desert ironwood", "USES"), ("bunka", "Micarta", "USES")],
     "which five-blade lineup is planned for the next show and what handle set ties them together",
     "gyuto petty nakiri honesuki bunka ironwood micarta bolster show"),
    # --- 36 ---
    ("Forge welding the san-mai billet with borax flux worked at welding heat around 2300 F but I'm switching to Cherry Heat for cleaner welds and less scale in the seam.", "decision", "personal", False,
     [("san-mai", "pattern"), ("borax", "technology"), ("Cherry Heat", "technology"), ("2300 F", "config"), ("welding heat", "concept")],
     [("Cherry Heat", "borax", "REPLACES")],
     "which flux am I switching to for san-mai forge welds and what welding temperature does the process sit at",
     "san mai borax cherry heat flux forge weld 2300 seam clean"),
    # --- 37 ---
    ("After chatting with Kramer at the Oregon Knife Collectors show, decided to spec a heel drop of three millimetres below the handle plane on my eight-inch chef's knife across every new build going forward.", "decision", "personal", False,
     [("Oregon Knife Collectors", "organization"), ("Kramer", "person"), ("chef's knife", "concept"), ("heel drop", "concept")],
     [("Kramer", "Oregon Knife Collectors", "VISITED")],
     "what did I learn from Kramer at the Oregon Knife Collectors show about heel drop on the eight-inch chef",
     "oregon knife collector kramer chef heel drop three mm geometry"),
    # --- 38 ---
    ("Pattern-welded Damascus ended up being a rabbit hole; moved from random explosion patterns to deliberate twist-and-ladder combinations after studying Devin Thomas process photos.", "decision", "personal", False,
     [("Pattern-welded Damascus", "pattern"), ("explosion pattern", "pattern"), ("twist-and-ladder", "pattern"), ("Devin Thomas", "person")],
     [("twist-and-ladder", "explosion pattern", "REPLACES"), ("twist-and-ladder", "Devin Thomas", "BUILDS_ON")],
     "which damascus pattern category did I migrate toward after studying Devin Thomas process photos",
     "damascus twist ladder explosion devin thomas process photo pattern"),
    # --- 39 ---
    ("Built a post-forge grinding jig for the 2x72 that holds the tang at a fixed angle; it cut my bevel symmetry variance from half a millimetre to under two hundred microns across a batch.", "milestone", "personal", False,
     [("grinding jig", "tool"), ("2x72", "tool"), ("tang", "concept"), ("bevel", "concept")],
     [("grinding jig", "2x72", "CONFIGURES")],
     "which tooling change dropped my bevel symmetry variance on the 2x72 and by how much",
     "grinding jig 2x72 tang bevel symmetry variance micron batch"),
    # --- 40 ---
    ("My hardness target on hunting blades is Rockwell 60 to 61; softer than that and the edge rolls through deer bone, harder and the tip snaps when levering out a shoulder joint.", "fact", "personal", False,
     [("Rockwell 60 to 61", "config"), ("hunting blade", "concept"), ("deer bone", "concept")],
     [("Rockwell 60 to 61", "hunting blade", "APPLIES_TO")],
     "what hardness window do I target on hunting blades and what failure bounds it on each side",
     "rockwell 60 61 hunting blade deer bone roll snap target"),
    # --- 41 ---
    ("Finished the first mosaic pins inlay on a cocobolo handle using a copper-and-brass checker; the pin seats with five-minute epoxy and gets sanded flush at 400 grit before polish.", "milestone", "personal", False,
     [("mosaic pins", "tool"), ("cocobolo", "technology"), ("five-minute epoxy", "technology"), ("copper", "technology"), ("brass", "technology")],
     [("mosaic pins", "cocobolo", "APPLIES_TO")],
     "which handle build saw my first mosaic-pin inlay and how did the pin bedding and sanding go",
     "mosaic pin cocobolo copper brass epoxy 400 grit sand flush"),
    # --- 42 ---
    ("Tamahagane sourcing is now through the Shimane co-op smelt rather than the Hitachi producer run; price doubled but the iron sand consistency shows up in a cleaner shingane layer.", "decision", "personal", False,
     [("Tamahagane", "technology"), ("Shimane", "place"), ("Hitachi", "organization"), ("shingane", "concept")],
     [("Shimane", "Hitachi", "REPLACES")],
     "where am I sourcing tamahagane now and what quality gain justified the doubled price",
     "tamahagane shimane hitachi iron sand shingane layer source"),
    # --- 43. noise ---
    ("The neighbourhood cat has adopted the porch welcome mat as her mid-afternoon sunbathing post three days running.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Problem on a batch of 1084 camp knife blanks: the spine soaks were uneven because the propane forge had a hot spot near the front brick, cooking the tip three hundred degrees hotter than the ricasso.", "problem", "personal", False,
     [("1084", "technology"), ("propane forge", "tool"), ("camp knife", "concept"), ("ricasso", "concept")],
     [("propane forge", "1084", "CAUSES")],
     "which forge characteristic caused uneven soak on the 1084 camp knife batch and how big was the delta",
     "1084 propane forge hot spot front brick tip ricasso soak delta"),
    # --- 45 ---
    ("Decided the next series of kiritsuke will be built by stock removal from AEB-L instead of forged from W2; forging a 240 mm blade at my current forge length is a two-heat dance and it scales the steel badly.", "decision", "personal", False,
     [("kiritsuke", "concept"), ("AEB-L", "technology"), ("W2", "technology"), ("stock removal", "method")],
     [("AEB-L", "W2", "REPLACES"), ("stock removal", "kiritsuke", "APPLIES_TO")],
     "which steel and process did I pick for the next kiritsuke series and why move off forging",
     "kiritsuke aeb-l w2 stock removal forge length two heat scale"),
    # --- 46 ---
    ("The deba build plan calls for a 190 mm blade, 4.5 mm spine at the heel, and a single-bevel ura ground flat; hand-polish on natural stones from 1000 to 8000 grit.", "architecture", "personal", False,
     [("deba", "concept"), ("ura", "concept"), ("natural stones", "tool")],
     [("ura", "deba", "HAS_PART")],
     "what are the key dimensions and finishing stones planned for the deba build",
     "deba 190 mm spine 4.5 heel ura single bevel natural stone 8000"),
    # --- 47 ---
    ("Cryo soak at negative 320 F in liquid nitrogen between quench and temper became the default for every stainless I run; the carbide conversion is measurable in edge retention tests.", "decision", "personal", False,
     [("Cryo soak", "method"), ("liquid nitrogen", "technology"), ("negative 320 F", "config"), ("carbide conversion", "finding")],
     [("Cryo soak", "carbide conversion", "CAUSES")],
     "which between-quench-and-temper step is now default on my stainless steels and what does it measurably do",
     "cryo soak liquid nitrogen 320 f carbide conversion stainless edge"),
    # --- 48 ---
    ("Finished the half-tang test blade with brass pins and jigged bone scales; it's going into the kitchen as the daily beater so I can log edge retention on real prep over six months.", "milestone", "personal", False,
     [("half-tang", "pattern"), ("brass pins", "tool"), ("jigged bone", "technology"), ("edge retention", "concept")],
     [("half-tang", "brass pins", "HAS_PART")],
     "which test blade went into daily kitchen use and what data am I logging over the next six months",
     "half tang brass pin jigged bone daily kitchen beater retention log"),
    # --- 49 ---
    ("Switched to a Burr King 2x72 at the collective shop for the flat platen work; the Beaumont KMG is still mine at home but the tracking on the Burr King is a notch better for tight bevels.", "preference", "personal", False,
     [("Burr King", "organization"), ("2x72", "tool"), ("flat platen", "tool"), ("Beaumont", "organization"), ("KMG", "tool")],
     [("Burr King", "KMG", "PREFERS")],
     "which 2x72 platform do I prefer at the collective for flat platen work and why",
     "burr king 2x72 flat platen kmg beaumont tracking bevel collective"),
    # --- 50 ---
    ("Hamon activity scale is my own rating system: one for straight suguha, three for notare, five for choji with ashi, and seven for wild midareba; the 52100 hunters land at a solid four.", "reference", "personal", False,
     [("Hamon", "concept"), ("suguha", "pattern"), ("notare", "pattern"), ("choji", "pattern"), ("midareba", "pattern"), ("52100", "technology")],
     [("52100", "notare", "PRODUCES")],
     "how does my personal hamon activity scale rate the common styles and where do the 52100 hunters land",
     "hamon scale suguha notare choji midareba 52100 hunter four"),
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
