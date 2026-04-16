"""One-off emitter for shared-base batch-274 — personal domain (sewing and knitting: machines, fabrics, notions, patterns, yarns, techniques).

Writes 50 rows to data/v2/shared/batch_274.tmp.jsonl with ids shared-13651..13700.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_274.tmp.jsonl"
ID_OFFSET = 13650

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Upgraded from the Singer Heavy Duty 4452 to a Juki TL-2200QVP for the quilting corner; the long arm and knee lifter finally let me sail through king-sized sandwiches without fighting the throat plate.", "decision", "personal", False,
     [("Singer Heavy Duty 4452", "tool"), ("Juki TL-2200QVP", "tool"), ("quilting corner", "project")],
     [("Juki TL-2200QVP", "Singer Heavy Duty 4452", "REPLACES")],
     "which domestic machine got swapped out when a long-arm became necessary for king-sized quilts",
     "juki tl 2200 qvp singer heavy duty 4452 quilt long arm knee"),
    # --- 2 ---
    ("The Janome HD3000 stays as the travel backup; its all-metal frame survives rattling around in a car trunk and the bobbin tension has not drifted in three years of retreats.", "architecture", "personal", False,
     [("Janome HD3000", "tool"), ("bobbin tension", "concept"), ("retreats", "event")],
     [],
     "which backup machine earns its spot on sewing retreats and why does its tension behave",
     "janome hd3000 backup travel retreat metal frame bobbin tension"),
    # --- 3 ---
    ("Splurged on the Bernina 770 QE for garment work; the walking foot is optional rather than permanent and stitch regulation over knits removed the wavy-seam problem I kept hitting on ponte.", "milestone", "personal", False,
     [("Bernina 770 QE", "tool"), ("walking foot", "pattern"), ("ponte", "concept")],
     [("Bernina 770 QE", "ponte", "APPLIES_TO")],
     "which high-end machine landed for garment sewing and what knits problem did stitch regulation address",
     "bernina 770 qe walking foot ponte knit wavy seam regulation"),
    # --- 4 ---
    ("The Pfaff Performance Icon's built-in IDT dual-feed is the reason I stopped reaching for a separate walking foot on slippery Liberty Tana Lawn; layers stay aligned through curved hems now.", "architecture", "personal", False,
     [("Pfaff Performance Icon", "tool"), ("IDT", "pattern"), ("Liberty Tana Lawn", "concept")],
     [("IDT", "Liberty Tana Lawn", "APPLIES_TO")],
     "which built-in feed system keeps Liberty Tana Lawn layers aligned without an external walking foot",
     "pfaff performance icon idt dual feed liberty tana lawn curve hem"),
    # --- 5 ---
    ("Brother PQ1500S handles the free-motion quilting on charity tops; the knee lifter plus a 1500 stitch-per-minute top speed means I can push out a twin sandwich in an afternoon.", "fact", "personal", False,
     [("Brother PQ1500S", "tool"), ("free-motion quilting", "method"), ("charity tops", "project")],
     [],
     "which straight-stitch machine handles charity quilt tops and what makes it fast on twin sandwiches",
     "brother pq1500s free motion quilt charity twin sandwich knee"),
    # --- 6 ---
    ("Retired the old Husqvarna Viking from active duty after the exclusive sensor system went quirky; it still gets pulled out for decorative embroidery when the Bernina 770 QE is tied up on tailoring.", "decision", "personal", False,
     [("Husqvarna Viking", "tool"), ("Bernina 770 QE", "tool"), ("tailoring", "method")],
     [("Bernina 770 QE", "Husqvarna Viking", "REPLACES")],
     "which machine got shuffled to decorative-embroidery duty after its sensor system started acting up",
     "husqvarna viking bernina embroidery sensor tailor retire decorative"),
    # --- 7 ---
    ("The Babylock Imagine serger is a jet-air threading convert story; the loopers rethread in six seconds and I stopped dreading a thread-colour change on stretch knits jersey.", "architecture", "personal", False,
     [("Babylock Imagine", "tool"), ("jet-air threading", "method"), ("stretch knits jersey", "concept")],
     [("jet-air threading", "Babylock Imagine", "APPLIES_TO")],
     "which serger feature made thread-colour changes painless on stretch jersey projects",
     "babylock imagine jet air thread serger looper stretch jersey"),
    # --- 8 ---
    ("Added a Juki MCS-1500 coverstitch for t-shirt hems; the triple-needle chain stitch looks store-bought and the differential feed keeps the hem from flaring on rayon.", "milestone", "personal", False,
     [("Juki MCS-1500", "tool"), ("coverstitch", "method"), ("rayon", "concept"), ("differential feed", "pattern")],
     [("differential feed", "rayon", "APPLIES_TO")],
     "which dedicated coverstitch joined the studio and how does it keep rayon t-shirt hems flat",
     "juki mcs 1500 coverstitch rayon t shirt hem differential feed"),
    # --- 9 ---
    ("Robert Kaufman Kona is the default quilting-cotton bolt in the stash now; colour range is wide, the 60-square GSM holds a crisp seam, and bolt-to-bolt dye lots stay consistent.", "decision", "personal", False,
     [("Robert Kaufman Kona", "concept"), ("quilting-cotton", "concept"), ("dye lots", "concept")],
     [],
     "which quilting cotton brand became the default bolt and what makes it reliable for matching runs",
     "robert kaufman kona quilt cotton gsm dye lot bolt consistent"),
    # --- 10. noise ---
    ("The cat claimed the ironing-board cover as her afternoon nap spot and now shedding black hair is a permanent finishing step.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Essex linen-cotton blend earned a permanent slot on the shelf because it presses like linen but behaves like cotton under the machine; pockets and facings stop bulking on Closet Core Patterns jeans.", "decision", "personal", False,
     [("Essex linen-cotton", "concept"), ("Closet Core Patterns", "organization"), ("pockets", "pattern")],
     [("Essex linen-cotton", "Closet Core Patterns", "APPLIES_TO")],
     "which linen blend solved the facing and pocket bulk issue on Closet Core jeans makes",
     "essex linen cotton closet core pocket facing bulk jean press"),
    # --- 12 ---
    ("Ordered from Mood Fabrics for the silk crepe de chine bridesmaid run; swatches arrived fast and the hand matched the photos, which is not guaranteed with online silk shopping.", "fact", "personal", False,
     [("Mood Fabrics", "organization"), ("silk crepe de chine", "concept"), ("bridesmaid run", "project")],
     [("Mood Fabrics", "silk crepe de chine", "APPLIES_TO")],
     "which online source delivered reliable silk crepe de chine for the bridesmaid project",
     "mood fabrics silk crepe de chine bridesmaid swatch online shop"),
    # --- 13 ---
    ("Merchant and Mills heavy oilskin is going on the commuter tote; the waxed finish shrugs off rain but the Schmetz needles need to bump up to a 100/16 jeans point to punch through layered seams.", "milestone", "personal", False,
     [("Merchant and Mills", "organization"), ("Schmetz needles", "tool"), ("100/16", "concept"), ("commuter tote", "project")],
     [("Schmetz needles", "Merchant and Mills", "APPLIES_TO")],
     "which needle size and fabric combination solved the punch-through problem on the oilskin tote",
     "merchant mills oilskin schmetz 100 16 jean needle tote wax"),
    # --- 14 ---
    ("Japanese selvedge denim from Okayama is reserved for the keeper jeans project; each yard is expensive enough that I mock the fit on cheap indigo twill first and only cut once the muslin passes the sit-test.", "decision", "personal", False,
     [("Japanese selvedge", "concept"), ("Okayama", "place"), ("muslin", "concept"), ("keeper jeans", "project")],
     [],
     "how do I hedge the cost of Japanese selvedge on the keeper-jeans project before cutting",
     "japanese selvedge okayama denim muslin keeper jean fit sit test"),
    # --- 15 ---
    ("Wool suiting from a Woolmark-certified Italian mill is the fabric for the autumn blazer; the 280 GSM weight tailors crisply and a Hong Kong finish on the seams keeps the inside magazine-photo neat.", "architecture", "personal", False,
     [("Wool suiting", "concept"), ("Woolmark", "concept"), ("Hong Kong finish", "method"), ("autumn blazer", "project")],
     [("Hong Kong finish", "Wool suiting", "APPLIES_TO")],
     "which seam finish tidies the inside of the autumn blazer built from Italian wool suiting",
     "wool suiting woolmark italian hong kong finish blazer autumn"),
    # --- 16 ---
    ("Gütermann thread is the default for woven garments and Aurifil thread handles the quilting; mixing them on the same project caused top-tension fights on the Bernina 770 QE and I learned to pick one per bobbin session.", "problem", "personal", False,
     [("Gütermann thread", "concept"), ("Aurifil thread", "concept"), ("Bernina 770 QE", "tool")],
     [("Aurifil thread", "Gütermann thread", "REPLACES")],
     "which thread mismatch caused tension trouble on the Bernina and what rule keeps it from repeating",
     "gutermann aurifil thread tension bernina bobbin quilt woven"),
    # --- 17 ---
    ("YKK zippers go on the everyday makes and RiRi zippers are reserved for the leather bag commissions; the RiRi pulls feel substantial enough that the client price premium is easy to justify.", "preference", "personal", False,
     [("YKK zippers", "concept"), ("RiRi zippers", "concept"), ("leather bag", "project")],
     [("RiRi zippers", "leather bag", "APPLIES_TO")],
     "which zipper brand earns its place on paid leather bag commissions and which handles everyday makes",
     "ykk riri zipper leather bag everyday premium client commission"),
    # --- 18 ---
    ("Prym snaps with the Vario Plus pliers are the only hardware set that has not failed on me; cheap generic snaps popped open on the baby-romper run and the Vario's anvil seats properly.", "decision", "personal", False,
     [("Prym snaps", "concept"), ("Vario Plus", "tool"), ("baby-romper run", "project")],
     [("Vario Plus", "Prym snaps", "APPLIES_TO")],
     "which snap and plier combo finally held up after cheap snaps popped on the baby-romper project",
     "prym snap vario plus plier baby romper hardware generic pop"),
    # --- 19 ---
    ("Grainline Studio's Archer button-up is my tested-to-death pattern for shirt drafts; muslin number four locked the yoke width and every subsequent shirt starts from that traced block.", "reference", "personal", False,
     [("Grainline Studio", "organization"), ("Archer", "project"), ("yoke", "pattern")],
     [("Grainline Studio", "Archer", "APPLIES_TO")],
     "which button-up pattern serves as my traced block for shirts and how many muslins locked the fit",
     "grainline studio archer button up yoke muslin block trace"),
    # --- 20 ---
    ("True Bias Lander pants beat the Closet Core Patterns Ginger jeans for my wide-leg draft; the rise sits where I want without grading the waistband up a size, which saved the whole bake-off.", "decision", "personal", False,
     [("True Bias", "organization"), ("Lander", "project"), ("Closet Core Patterns", "organization"), ("Ginger jeans", "project")],
     [("Lander", "Ginger jeans", "PREFERS")],
     "which wide-leg pant pattern won the bake-off against Closet Core Ginger jeans and why",
     "true bias lander closet core ginger wide leg rise waistband"),
    # --- 21 ---
    ("Merchant and Mills Trapeze dress is my weekend sewing-afternoon pattern; five pattern pieces cut quickly and French seam the whole thing in under three hours on the Janome HD3000.", "reference", "personal", False,
     [("Merchant and Mills", "organization"), ("Trapeze", "project"), ("French seam", "method"), ("Janome HD3000", "tool")],
     [("French seam", "Trapeze", "APPLIES_TO")],
     "which five-piece dress serves as the weekend quick-make and which seam finish carries it",
     "merchant mills trapeze dress french seam janome hd3000 weekend"),
    # --- 22 ---
    ("Colette and its Seamwork offshoot got shelved after the size-range update still skipped my bust measurement; moved over to Cashmerette for the curvy-fit grading that actually includes cup sizes.", "decision", "personal", False,
     [("Colette", "organization"), ("Seamwork", "organization"), ("Cashmerette", "organization"), ("curvy-fit", "concept")],
     [("Cashmerette", "Colette", "REPLACES"), ("Cashmerette", "Seamwork", "REPLACES")],
     "which pattern company replaced Colette and Seamwork after the size-range update still missed my bust",
     "colette seamwork cashmerette curvy fit cup size grade bust"),
    # --- 23 ---
    ("Burda magazine tracings stay useful for unusual silhouettes; the trade-off is hand-drafted seam allowances, so the bound buttonhole timing adds a quarter-hour per placket that a Big Four pattern would have pre-marked.", "reference", "personal", False,
     [("Burda", "organization"), ("bound buttonhole", "method"), ("placket", "pattern"), ("Big Four", "concept")],
     [("bound buttonhole", "placket", "APPLIES_TO")],
     "which pattern source gives unusual silhouettes and what buttonhole overhead comes with the tracing workflow",
     "burda magazine trace seam allowance bound buttonhole placket big four"),
    # --- 24 ---
    ("Vogue Patterns 1756 is the designer silhouette I keep reaching for with wool suiting; the welt pocket placement already falls where the tailoring line expects and the shoulder cap ease is realistic.", "reference", "personal", False,
     [("Vogue Patterns 1756", "project"), ("welt pocket", "method"), ("wool suiting", "concept")],
     [("welt pocket", "Vogue Patterns 1756", "APPLIES_TO")],
     "which Vogue designer pattern pairs best with wool suiting and why does its welt pocket work",
     "vogue 1756 welt pocket wool suit designer shoulder cap ease"),
    # --- 25 ---
    ("McCall's pattern fit-runs the best for my 14-year-old niece; drafting age teens on Closet Core Patterns has been a grading headache because the block assumes a fully adult torso.", "fact", "personal", False,
     [("McCall's", "organization"), ("Closet Core Patterns", "organization"), ("niece", "person")],
     [("McCall's", "Closet Core Patterns", "PREFERS")],
     "which pattern company fits teens out of the envelope better than Closet Core for kids",
     "mccall closet core teen niece grade torso adult block"),
    # --- 26 ---
    ("Knit Picks nickel-plated fixed circular needles are the shop default now; the join is smooth and the 32-inch cable length handles top-down raglan sweaters without laddering at the magic loop switch.", "preference", "personal", False,
     [("Knit Picks", "organization"), ("circular needles", "tool"), ("top-down raglan", "method"), ("magic loop", "method")],
     [("circular needles", "top-down raglan", "APPLIES_TO")],
     "which fixed-length needle brand became the shop default for top-down sweaters and what laddering problem does the cable solve",
     "knit picks nickel circular 32 inch top down raglan magic loop"),
    # --- 27 ---
    ("Addi Turbo tips stay in the gift-only budget tier; the friction is lower than Knit Picks on alpaca merino which matters when stitches need to glide, but the price-per-pair is a stretch for stash tools.", "decision", "personal", False,
     [("Addi Turbo", "tool"), ("Knit Picks", "organization"), ("alpaca merino", "concept")],
     [("Addi Turbo", "Knit Picks", "IMPROVES_ON")],
     "which needle brand earns gifting status for alpaca merino despite the price over Knit Picks",
     "addi turbo knit picks alpaca merino friction glide price gift"),
    # --- 28 ---
    ("DPNs came back out of the drawer for the sock-toe turns; the five-needle dance beats fighting magic-loop ladder at 72 stitches of fingering weight, which is where my tension always breaks.", "fact", "personal", False,
     [("DPNs", "tool"), ("sock-toe", "pattern"), ("fingering weight", "concept"), ("magic-loop", "method")],
     [("DPNs", "magic-loop", "IMPROVES_ON")],
     "which needle style beats magic loop at sock-toe fingering-weight rounds and what tension failure does it dodge",
     "dpn sock toe fingering 72 stitch magic loop ladder tension"),
    # --- 29 ---
    ("Gauge swatch is non-negotiable on the Brooklyn Tweed commissions; swatching an 8-by-8-inch square and washing before measuring has saved the last three sweaters from a full reknit after blocking shrank the row count.", "milestone", "personal", False,
     [("Gauge swatch", "method"), ("Brooklyn Tweed", "organization"), ("blocking", "method")],
     [("Gauge swatch", "Brooklyn Tweed", "APPLIES_TO")],
     "which habit on Brooklyn Tweed commissions avoids a full reknit after blocking changes the row count",
     "gauge swatch brooklyn tweed wash block 8 inch square row"),
    # --- 30 ---
    ("Ravelry remains the queue-planner despite the site rebuild; the pattern library cross-search against stash yardage is where I live on Sunday mornings even when the new UI nudges me toward mobile.", "architecture", "personal", False,
     [("Ravelry", "platform"), ("pattern library", "concept"), ("stash yardage", "concept")],
     [],
     "which platform still serves as the queue planner for yarn versus pattern cross-search despite the rebuild",
     "ravelry pattern library stash yardage queue plan sunday mobile"),
    # --- 31 ---
    ("Wool and the Gang kits are a gift-purchase shortcut for knitting-curious friends; the colour kitting is tasteful, the pattern leaflet is beginner-safe, and the oversized-needle vibe finishes a scarf in a weekend.", "fact", "personal", False,
     [("Wool and the Gang", "organization"), ("pattern leaflet", "pattern"), ("scarf", "project")],
     [],
     "which kit company handles the knitting-gift shortcut for beginners and how quickly do their scarf kits finish",
     "wool gang kit gift beginner colour leaflet scarf weekend"),
    # --- 32 ---
    ("Drops Design free patterns are the worksheet for stash-busting; the PDF layout is charts-forward and most of the sport-weight archives are still in stock at the distributor which is rare for a free library.", "reference", "personal", False,
     [("Drops Design", "organization"), ("sport-weight", "concept"), ("PDF", "technology")],
     [],
     "which free-pattern library drives my stash-busting worksheet and what makes their archive reliable",
     "drops design free pattern sport weight pdf chart stash bust"),
    # --- 33 ---
    ("Brooklyn Tweed Shelter in the Cast Iron colourway is the yarn for the next fisherman pullover; the rustic tweed flecks disappear into the honeycomb cable pattern instead of fighting it.", "decision", "personal", False,
     [("Brooklyn Tweed", "organization"), ("Shelter", "concept"), ("Cast Iron", "concept"), ("honeycomb cable", "method")],
     [("Shelter", "honeycomb cable", "APPLIES_TO")],
     "which yarn and colourway earned the slot for the fisherman pullover and what did it do for the cable texture",
     "brooklyn tweed shelter cast iron fisherman honeycomb cable tweed"),
    # --- 34 ---
    ("Shetland wool from Jamieson's is going into the next fair isle yoke; the palette breadth means I can hold six colours at once without buying three off-brand substitutes and praying they bloom the same.", "architecture", "personal", False,
     [("Shetland wool", "concept"), ("Jamieson's", "organization"), ("fair isle", "method"), ("yoke", "pattern")],
     [("Shetland wool", "fair isle", "APPLIES_TO")],
     "which yarn source supplies the fair isle yoke and what palette advantage does it offer over substitutions",
     "shetland jamieson fair isle yoke six colour bloom palette"),
    # --- 35 ---
    ("DK-weight alpaca merino from a local indie dyer sits in the warm-layer rotation; alpaca lends the drape and merino keeps the pilling manageable on the elbows across a winter of wear.", "fact", "personal", False,
     [("DK", "concept"), ("alpaca merino", "concept"), ("indie dyer", "person"), ("warm-layer", "concept")],
     [("alpaca merino", "warm-layer", "APPLIES_TO")],
     "which fibre blend handles warm-layer drape while keeping elbow pilling under control through winter",
     "dk alpaca merino indie dyer warm layer drape pill elbow"),
    # --- 36 ---
    ("Worsted weight is the default for gift hats; the knit-time curve is forgiving enough that a surprise baby announcement still ends up with a finished hat before the shower.", "preference", "personal", False,
     [("Worsted", "concept"), ("gift hats", "project"), ("baby announcement", "event")],
     [],
     "which yarn weight earns the default slot for gift hats and what surprise deadline does it cover",
     "worsted weight gift hat baby announcement shower deadline"),
    # --- 37 ---
    ("Brioche stitch finally clicked on the two-colour cowl after switching to blocking-pin tensioning through the first row; the yarn-over columns lined up and the fabric stopped reading as a lumpy mess.", "problem", "personal", False,
     [("Brioche", "method"), ("two-colour cowl", "project"), ("blocking-pin", "tool"), ("yarn-over", "concept")],
     [("blocking-pin", "Brioche", "APPLIES_TO")],
     "which first-row trick made two-colour brioche line up on the cowl and stop looking lumpy",
     "brioche two colour cowl block pin tension yarn over column"),
    # --- 38 ---
    ("Entrelac remains a headache I revisit once a year on a throw pillow; the pick-up-stitch direction reversing every tier is where my brain drops threads and the project jar gets capped until summer.", "fact", "personal", False,
     [("Entrelac", "method"), ("throw pillow", "project"), ("pick-up-stitch", "method")],
     [],
     "which technique goes on the once-a-year revisit stack and which step reverses direction enough to stall me",
     "entrelac pick up stitch throw pillow direction reverse tier"),
    # --- 39 ---
    ("Mosaic colourwork is the gateway I recommend to friends nervous about stranded colourwork fair isle; only one strand is active per row so tension panic is taken off the table for the first sweater.", "preference", "personal", False,
     [("Mosaic colourwork", "method"), ("stranded colourwork fair isle", "method"), ("tension", "concept")],
     [("Mosaic colourwork", "stranded colourwork fair isle", "IMPROVES_ON")],
     "which entry colourwork technique do I recommend before fair isle and what beginner worry does it dodge",
     "mosaic colourwork fair isle stranded tension strand beginner"),
    # --- 40 ---
    ("French seam finishing is the default on the silk crepe de chine bridesmaid run; enclosed raw edges on the slippery fabric beat a serger pass that would push the seam allowance wavy.", "decision", "personal", False,
     [("French seam", "method"), ("silk crepe de chine", "concept"), ("bridesmaid run", "project"), ("serger", "tool")],
     [("French seam", "silk crepe de chine", "APPLIES_TO")],
     "which seam finish beats a serger pass on silk crepe de chine for the bridesmaid run",
     "french seam silk crepe de chine bridesmaid serger wavy enclose"),
    # --- 41 ---
    ("Hong Kong finish seams go on the autumn blazer interior; the bias-bound edges mean the blazer can be worn unlined in transitional weather without a raggy inside peeking out past the vent.", "architecture", "personal", False,
     [("Hong Kong finish", "method"), ("autumn blazer", "project"), ("bias-bound", "method"), ("vent", "pattern")],
     [("Hong Kong finish", "autumn blazer", "APPLIES_TO")],
     "which seam finish lets the autumn blazer go unlined in transitional weather without exposing raw edges",
     "hong kong finish blazer bias bound vent unlined transitional"),
    # --- 42 ---
    ("The welt pocket placement on the Vogue Patterns 1756 sample needed a chalk-line rebalance after the grain shift; I dropped the left pocket three-eighths of an inch so the stripe alignment reads level under the lapel.", "problem", "personal", False,
     [("welt pocket", "method"), ("Vogue Patterns 1756", "project"), ("chalk-line", "tool"), ("lapel", "pattern")],
     [("welt pocket", "Vogue Patterns 1756", "APPLIES_TO")],
     "which pocket rebalance fixed the Vogue 1756 stripe alignment issue under the lapel",
     "welt pocket vogue 1756 chalk line lapel stripe grain shift"),
    # --- 43. noise ---
    ("The studio houseplant fell over during the last storm and every pattern envelope on the low shelf now has a water-ring ghost.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("The bound buttonhole practice went on scraps of Kona first; a row of ten taught me the corner-clipping rhythm before I risked the first one on the autumn blazer lapel where a redo would show.", "milestone", "personal", False,
     [("bound buttonhole", "method"), ("Kona", "concept"), ("autumn blazer", "project"), ("lapel", "pattern")],
     [("bound buttonhole", "autumn blazer", "APPLIES_TO")],
     "which practice plan prepared me for the first bound buttonhole on the autumn blazer lapel",
     "bound buttonhole kona scrap autumn blazer lapel corner clip"),
    # --- 45 ---
    ("The top-down raglan is the construction default for gift sweaters; try-on at the underarm join lets me lengthen the body before committing the yarn, which matters on indie-dyer skeins that do not repeat.", "architecture", "personal", False,
     [("top-down raglan", "method"), ("gift sweaters", "project"), ("indie-dyer", "person"), ("underarm join", "pattern")],
     [("top-down raglan", "gift sweaters", "APPLIES_TO")],
     "which construction default on gift sweaters lets me fit-check before committing indie-dyer yarn",
     "top down raglan gift sweater underarm try indie dyer skein"),
    # --- 46 ---
    ("The Cashmerette Appleton dress pattern finished as the first completed make from their range; graded to an 18 GH cup and the underbust seam sat exactly where the line drawing promised, which was a first.", "milestone", "personal", False,
     [("Cashmerette", "organization"), ("Appleton", "project"), ("18 GH", "concept"), ("underbust seam", "pattern")],
     [("Appleton", "Cashmerette", "APPLIES_TO")],
     "which Cashmerette pattern was the first completed make and what grading detail finally matched the drawing",
     "cashmerette appleton dress 18 gh underbust seam grade cup"),
    # --- 47 ---
    ("Ravelry project notes now include blocking measurements before and after; the before-after delta on Shetland wool fair isle yokes is consistent enough that I pre-compensate row count by 4 percent on the next cast-on.", "reference", "personal", False,
     [("Ravelry", "platform"), ("Shetland wool", "concept"), ("fair isle", "method"), ("cast-on", "method")],
     [("Shetland wool", "fair isle", "APPLIES_TO")],
     "which Ravelry note habit lets me pre-compensate row count on Shetland fair isle yokes",
     "ravelry project note block measure shetland fair isle row 4 percent"),
    # --- 48 ---
    ("Schmetz needles in microtex 70/10 are the default for silk crepe de chine; the 80/12 universal I used on the first bridesmaid dress left visible puncture holes on the back neck facing.", "milestone", "personal", False,
     [("Schmetz needles", "tool"), ("microtex", "concept"), ("70/10", "concept"), ("80/12", "concept"), ("silk crepe de chine", "concept")],
     [("microtex", "silk crepe de chine", "APPLIES_TO")],
     "which sewing-machine needle gauge finally replaced the universal one that was scarring the bridesmaid-dress neck facing",
     "schmetz microtex 70 10 80 12 silk crepe neck facing puncture"),
    # --- 49 ---
    ("The stash inventory lives in a shared spreadsheet cross-referenced with Ravelry stash photos; when I hit 400 yards or fewer of a colour it auto-flags for the reorder cycle so lots stay matchable.", "architecture", "personal", False,
     [("stash inventory", "concept"), ("spreadsheet", "tool"), ("Ravelry", "platform"), ("reorder cycle", "method")],
     [],
     "how does the stash inventory stay matchable across dye lots and what yardage triggers the reorder",
     "stash inventory spreadsheet ravelry 400 yard reorder dye lot"),
    # --- 50 ---
    ("Retired the unlabelled vintage-thread spool collection from active sewing; three snapped mid-seam on the Juki TL-2200QVP and it is not worth pulling the bobbin case each time to fish out a broken tail.", "decision", "personal", False,
     [("vintage-thread", "concept"), ("Juki TL-2200QVP", "tool"), ("bobbin case", "pattern")],
     [("Juki TL-2200QVP", "vintage-thread", "REPLACES")],
     "which thread category got retired after mid-seam snaps on the Juki forced repeated bobbin case fishing",
     "vintage thread juki tl 2200 qvp bobbin case snap retire"),
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
