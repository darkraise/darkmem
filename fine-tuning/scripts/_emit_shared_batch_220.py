"""One-off emitter for shared-base batch-220 — personal domain (leatherworking and bookbinding: leathers, dyes, finishes, stitching, tools, patterns, bookbinding techniques, bindery references).

Writes 50 rows to data/v2/shared/batch_220.tmp.jsonl with ids shared-10951..11000.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_220.tmp.jsonl"
ID_OFFSET = 10950

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Switched the wallet line from chrome-tanned side leather to Horween Chromexcel; the pull-up character and hot-stuffed finish match the hand feel I wanted and the edges still burnish passably despite the fatliquor content.", "decision", "personal", False,
     [("chrome-tanned", "technology"), ("Horween Chromexcel", "technology"), ("pull-up", "technology")],
     [("Horween Chromexcel", "chrome-tanned", "REPLACES")],
     "which leather replaced the chrome-tanned side on the wallet line and what character did it bring",
     "horween chromexcel chrome tan wallet pull up burnish switch"),
    # --- 2 architecture ---
    ("The edge-finish stack for veg-tan projects is three passes: bevel, sand to 2000 grit, then Tokonole burnished with a canvas rag; paint only goes on top for dressy belts.", "architecture", "personal", False,
     [("veg-tan", "technology"), ("Tokonole", "technology"), ("bevel", "method"), ("burnished", "method")],
     [("Tokonole", "veg-tan", "APPLIES_TO")],
     "how is the standard veg-tan edge-finish stack layered before paint is even considered",
     "tokonole veg tan burnish bevel sand canvas edge finish stack"),
    # --- 3 milestone ---
    ("Finished the first full-grain Shell Cordovan wallet in shell number two from Horween Chicago; the shell pulled up beautifully under the glass slicker and the stitching held a true saddle stitch all the way round.", "milestone", "personal", False,
     [("Shell Cordovan", "technology"), ("Horween Chicago", "organization"), ("saddle stitch", "method")],
     [("Shell Cordovan", "Horween Chicago", "APPLIES_TO")],
     "which shell project finished using Horween Chicago stock and what stitch ran around the perimeter",
     "shell cordovan horween chicago wallet saddle stitch slicker"),
    # --- 4 fact ---
    ("Vegetable-tanned Tärnsjö bend at 3.5 mm is the baseline for belt blanks; the fibre is dense enough that edges burnish glass-smooth with just water and beeswax, no Tokonole needed.", "fact", "personal", False,
     [("Tärnsjö", "organization"), ("Vegetable-tanned", "technology"), ("beeswax", "technology"), ("Tokonole", "technology")],
     [("Tärnsjö", "beeswax", "APPLIES_TO")],
     "which Swedish tannery's veg-tan bend is my belt-blank baseline and what edge routine does it allow",
     "tarnsjo vegetable tan bend belt blank beeswax water burnish"),
    # --- 5 reference ---
    ("The MakeSupply card-holder pattern is the quickest teaching project I hand out; it pairs with a Fine Leatherworking bifold follow-up and leaves Tandy kits for the stitching drills alone.", "reference", "personal", False,
     [("MakeSupply", "organization"), ("Fine Leatherworking", "organization"), ("Tandy", "organization")],
     [("MakeSupply", "Fine Leatherworking", "RELATED_TO")],
     "which three pattern sources anchor the teaching sequence for a new student",
     "makesupply fine leatherworking tandy pattern card holder bifold"),
    # --- 6 preference ---
    ("Prefer Ritza 25 Tiger Thread over Barbour waxed linen for everyday wallets; the polyester braid keeps its twist through a saddle stitch without the linen's fuzz bloom at the awl hole.", "preference", "personal", False,
     [("Ritza 25 Tiger Thread", "technology"), ("Barbour waxed linen", "technology"), ("saddle stitch", "method")],
     [("Ritza 25 Tiger Thread", "Barbour waxed linen", "PREFERS")],
     "which stitching thread do I prefer for daily wallets and what flaw of linen does it avoid",
     "ritza 25 tiger thread barbour waxed linen wallet saddle stitch"),
    # --- 7 decision ---
    ("Picked KS Blade Punch irons over Kemovan for the 3.85 mm pitch set; the KS geometry leaves a flatter back on 2 mm veg-tan and the resharpening cycle is longer on the same hides.", "decision", "personal", False,
     [("KS Blade Punch", "organization"), ("Kemovan", "organization"), ("veg-tan", "technology")],
     [("KS Blade Punch", "Kemovan", "PREFERS")],
     "which pricking-iron brand beat out Kemovan for the 3.85 mm set and why",
     "ks blade punch kemovan pricking iron 3 85 mm veg tan"),
    # --- 8 problem ---
    ("The Fiebing's pro dye on Dublin kept rubbing off on jeans; sealing with two coats of Resolene cut the bleed but swapping to Angelus for black was the real fix because it penetrates the pull-up wax better.", "problem", "personal", False,
     [("Fiebing's pro dye", "technology"), ("Dublin", "technology"), ("Resolene", "technology"), ("Angelus", "technology")],
     [("Angelus", "Fiebing's pro dye", "REPLACES")],
     "which dye swap fixed the jeans-transfer issue on Dublin pull-up and which sealer only half-helped",
     "fiebings angelus dye dublin resolene bleed jeans pull up"),
    # --- 9 architecture ---
    ("The finishing bench is laid out in zones: dyeing on the left over a drip tray, Tan Kote application in the middle, Carnauba cream and Resolene stations on the right so each coat dries before the next station touches it.", "architecture", "personal", False,
     [("Tan Kote", "technology"), ("Carnauba cream", "technology"), ("Resolene", "technology"), ("drip tray", "tool")],
     [("Tan Kote", "Resolene", "APPLIES_TO")],
     "how is the finishing bench zoned so dye, Tan Kote, and Resolene never contaminate each other",
     "tan kote resolene carnauba bench zone dye drip tray finish"),
    # --- 10. noise ---
    ("The workshop radiator knocks whenever the heating cycles at dawn and the cat has started sleeping on the warmest pipe elbow.", "fact", "noise", True, [], [], None, None),
    # --- 11 decision ---
    ("Chose a Vergez Blanchard round knife over a Dixon head knife for skiving heavy Essex; the French grind clears the edge cleaner on 2.5 mm stock and the balance fits my grip from the first stroke.", "decision", "personal", False,
     [("Vergez Blanchard", "organization"), ("Dixon", "organization"), ("Essex", "technology"), ("round knife", "tool"), ("head knife", "tool")],
     [("Vergez Blanchard", "Dixon", "PREFERS")],
     "which round knife replaced the Dixon head knife for heavy Essex skiving and what drove the choice",
     "vergez blanchard dixon round head knife essex skive french grind"),
    # --- 12 architecture ---
    ("Tool roll layout orders by stroke direction: Blanchard edge bevelers in the top pocket, stitch marker and creaser in the middle, head knives sheathed at the bottom where the weight sits when the roll hangs on the bench hook.", "architecture", "personal", False,
     [("Blanchard", "organization"), ("edge bevelers", "tool"), ("stitch marker", "tool"), ("creaser", "tool"), ("head knives", "tool")],
     [("Blanchard", "edge bevelers", "APPLIES_TO")],
     "how is the tool roll laid out so weight hangs correctly on the bench hook and tools order by stroke",
     "blanchard edge beveler stitch marker creaser head knife tool roll"),
    # --- 13 fact ---
    ("Essex from Horween Chicago runs thinner than Dublin at the same weight; a 4 oz Essex skives to a card edge at 0.4 mm where 4 oz Dublin tears above 0.6 mm under the same French skiver.", "fact", "personal", False,
     [("Essex", "technology"), ("Dublin", "technology"), ("Horween Chicago", "organization"), ("French skiver", "tool")],
     [("Essex", "Horween Chicago", "APPLIES_TO")],
     "how does Essex compare to Dublin at the same weight under a French skiver in practice",
     "essex dublin horween chicago french skiver skive weight compare"),
    # --- 14 reference ---
    ("Keith Smith's non-adhesive binding volumes cover the Coptic stitch progression I learned from; the Das Werkbuch reference fills in the German case-binding details Smith skims.", "reference", "personal", False,
     [("Keith Smith", "person"), ("Das Werkbuch", "publication"), ("Coptic stitch", "method"), ("case-binding", "method")],
     [("Keith Smith", "Das Werkbuch", "RELATED_TO")],
     "which two bookbinding references split the Coptic and case-binding learning between them",
     "keith smith das werkbuch coptic case binding reference learn"),
    # --- 15 decision ---
    ("Moved edge paint from Fenice to Giardini for the black slim-wallet line; Giardini's thicker body needs fewer coats and the cured film survives the first week of pocket abrasion without a retouch.", "decision", "personal", False,
     [("Fenice", "organization"), ("Giardini", "organization"), ("edge paint", "technology")],
     [("Giardini", "Fenice", "REPLACES")],
     "which edge-paint brand replaced Fenice on the black slim-wallet line and what wear test sealed it",
     "giardini fenice edge paint black slim wallet coat cure abrasion"),
    # --- 16 architecture ---
    ("Case-binding setup flows text block, endpapers, headbands, bookcloth-covered boards, then casing-in; each station has its own press time so the glue cures before the next step pulls on the spine.", "architecture", "personal", False,
     [("Case-binding", "method"), ("endpapers", "concept"), ("headbands", "concept"), ("bookcloth", "technology"), ("text block", "concept")],
     [("Case-binding", "bookcloth", "APPLIES_TO")],
     "how does case-binding flow station-to-station so the glue cures between each spine-loading step",
     "case binding text block endpapers headbands bookcloth press flow"),
    # --- 17 milestone ---
    ("Bound the first full-leather tooled journal with gilt edges; the Coptic stitch holds flat, the tooling on the cover came out clean on vegetable-tanned calf, and the gilding survived the burnisher without flaking.", "milestone", "personal", False,
     [("Coptic stitch", "method"), ("tooling", "method"), ("gilding", "method"), ("vegetable-tanned calf", "technology")],
     [("Coptic stitch", "vegetable-tanned calf", "APPLIES_TO")],
     "which milestone journal combined Coptic, tooling, and gilding and what leather carried it",
     "coptic stitch tooling gilding vegetable tan calf journal milestone"),
    # --- 18 fact ---
    ("Golden Rule Paper stocks the marbled endpaper sheets that match the vegetable-tanned spine I use for custom journals; their long-grain sheets fold with the binding so the book opens flat.", "fact", "personal", False,
     [("Golden Rule Paper", "organization"), ("marbled endpaper", "concept"), ("long-grain", "concept")],
     [("Golden Rule Paper", "marbled endpaper", "APPLIES_TO")],
     "which paper supplier keeps the marbled endpaper stock I need and why does grain direction matter",
     "golden rule paper marbled endpaper long grain journal fold flat"),
    # --- 19 preference ---
    ("Prefer long stitch over saddle-stitched pamphlet for pocket notebooks; the exposed spine sews through a single cover and the book opens flatter than a pamphlet with the same page count.", "preference", "personal", False,
     [("long stitch", "method"), ("saddle-stitched pamphlet", "method"), ("pocket notebooks", "concept")],
     [("long stitch", "saddle-stitched pamphlet", "PREFERS")],
     "which exposed-spine binding do I prefer over saddle-stitched pamphlet for pocket notebooks and why",
     "long stitch saddle stitched pamphlet pocket notebook flat spine"),
    # --- 20 decision ---
    ("Retired perfect binding for personal journals; the PVA spine cracks after a year of pocket carry and a sewn case binding or Coptic stitch is worth the extra hour per book.", "decision", "personal", False,
     [("perfect binding", "method"), ("PVA", "technology"), ("case binding", "method"), ("Coptic stitch", "method")],
     [("case binding", "perfect binding", "REPLACES")],
     "which bindings replaced perfect binding for personal journals and what failure mode forced the change",
     "perfect binding pva sewn case coptic journal spine crack retire"),
    # --- 21 architecture ---
    ("Stitching workflow chains pricking iron marking, chisel deepening, then diamond awl punch-through; the three-stage rhythm stays cleaner on 2 mm veg-tan than hammering an iron all the way through in one go.", "architecture", "personal", False,
     [("pricking iron", "tool"), ("chisel", "tool"), ("diamond awl", "tool"), ("veg-tan", "technology")],
     [("pricking iron", "diamond awl", "APPLIES_TO")],
     "how does the three-stage pricking-to-awl workflow stay cleaner on thick veg-tan than a single-pass iron",
     "pricking iron chisel diamond awl veg tan three stage workflow"),
    # --- 22 decision ---
    ("Angelus black faded to brown on the bag strap after a month of UV; moved the strap line to Fiebing's pro dye with a Carnauba cream topcoat and the black held true through the next summer.", "decision", "personal", False,
     [("Angelus", "technology"), ("Fiebing's pro dye", "technology"), ("Carnauba cream", "technology"), ("UV", "concept")],
     [("Fiebing's pro dye", "Angelus", "REPLACES")],
     "which dye swap fixed the UV-fade-to-brown on the bag strap line and what topcoat paired with it",
     "angelus fiebings carnauba cream uv fade black bag strap"),
    # --- 23 fact ---
    ("Le Prevo ships pricking irons on a four-week turnaround to the UK; ordering alongside a restock of Barbour thread saves the combined shipping and keeps the bench never fully stocked out.", "fact", "personal", False,
     [("Le Prevo", "organization"), ("Barbour", "organization"), ("pricking irons", "tool")],
     [("Le Prevo", "Barbour", "RELATED_TO")],
     "which UK supplier handles pricking-iron reorders and which thread restock bundles with it to save shipping",
     "le prevo barbour pricking iron uk ship restock bundle"),
    # --- 24 decision ---
    ("Moved belt edging to a Fenice black applicator pen for the slim line; the controlled bead pays back in straighter edges on long runs versus brushing Giardini out of the pot for every six inches of belt.", "decision", "personal", False,
     [("Fenice", "organization"), ("Giardini", "organization"), ("applicator pen", "tool")],
     [("Fenice", "Giardini", "PREFERS")],
     "which edge-paint delivery method replaced pot-brushing on the slim belt line and what payoff drove it",
     "fenice giardini applicator pen belt edge slim pot brush"),
    # --- 25 milestone ---
    ("Leather storage rotates by tannage: chrome-tanned hides roll in the climate-controlled cabinet, Horween Chromexcel and pull-up leathers hang vertically, Shell Cordovan lives flat under acid-free paper so no grain stretch sneaks in.", "milestone", "personal", False,
     [("chrome-tanned", "technology"), ("Horween Chromexcel", "technology"), ("pull-up", "technology"), ("Shell Cordovan", "technology"), ("acid-free paper", "technology")],
     [("Shell Cordovan", "acid-free paper", "APPLIES_TO")],
     "how is the leather storage zoned by tannage to protect grain and avoid stretch on shell",
     "chrome horween chromexcel pull up shell cordovan storage zone paper"),
    # --- 26 milestone ---
    ("Ran a six-student weekend class through a Coptic-bound pocket notebook start to finish; every book sewed flat and no one cracked a signature, which was the goal after last year's long-stitch trial left a few wobbles.", "milestone", "personal", False,
     [("Coptic", "method"), ("long-stitch", "method"), ("pocket notebook", "concept")],
     [("Coptic", "long-stitch", "REPLACES")],
     "which teaching milestone was hitting six Coptic pocket notebooks in a weekend and what trial preceded it",
     "coptic long stitch pocket notebook weekend class teach six student"),
    # --- 27 reference ---
    ("Fine Leatherworking's bifold video series is the clearest demonstration of card-slot skiving I have found; the Tandy catalogue stays on the shelf for the consumable restock and the MakeSupply templates anchor the production pattern.", "reference", "personal", False,
     [("Fine Leatherworking", "organization"), ("Tandy", "organization"), ("MakeSupply", "organization")],
     [("Fine Leatherworking", "MakeSupply", "RELATED_TO")],
     "which reference trio anchor video instruction, consumable restock, and production templates in the shop",
     "fine leatherworking tandy makesupply bifold card slot skive"),
    # --- 28 fact ---
    ("A Horween Chromexcel watch-strap pair at 2 mm takes roughly forty minutes from cutting through burnished edges; Shell Cordovan at the same thickness doubles that because the glass-slicker burnish stage is the slow bit.", "fact", "personal", False,
     [("Horween Chromexcel", "technology"), ("Shell Cordovan", "technology"), ("watch-strap", "concept"), ("glass-slicker", "tool")],
     [("Shell Cordovan", "glass-slicker", "APPLIES_TO")],
     "how does a Chromexcel watch-strap pair compare to Shell Cordovan on time and why is the gap there",
     "chromexcel shell cordovan watch strap burnish glass slicker time"),
    # --- 29 decision ---
    ("Chose Tan Kote under Resolene for everyday wallets; Tan Kote alone scuffs too fast in a pocket and Resolene alone over raw dye looks plasticky, so the layered approach lands closest to a hand-finish look.", "decision", "personal", False,
     [("Tan Kote", "technology"), ("Resolene", "technology")],
     [("Tan Kote", "Resolene", "RELATED_TO")],
     "which two-coat finish layering won out over either coat alone on everyday wallets and why",
     "tan kote resolene wallet finish layer scuff plasticky hand"),
    # --- 30 preference ---
    ("Prefer Barbour waxed linen for exposed bookbinding stitches where I want the thread to bloom visually; Ritza stays crisp and clean, which is exactly what you don't want on a decorative spine.", "preference", "personal", False,
     [("Barbour waxed linen", "technology"), ("Ritza", "technology"), ("exposed bookbinding", "method")],
     [("Barbour waxed linen", "Ritza", "PREFERS")],
     "which thread do I prefer on decorative exposed spines and what visual property seals the choice",
     "barbour waxed linen ritza exposed bookbinding spine bloom visual"),
    # --- 31 architecture ---
    ("Bookcloth-to-board lamination uses wheat starch paste for archival journals and PVA for trade-run production; the paste allows later repair and the PVA shaves minutes off the press stack for each board.", "architecture", "personal", False,
     [("Bookcloth", "technology"), ("wheat starch paste", "technology"), ("PVA", "technology"), ("archival", "concept")],
     [("wheat starch paste", "PVA", "REPLACES")],
     "how is adhesive chosen between archival journals and trade-run production when laminating bookcloth",
     "bookcloth wheat starch paste pva archival journal trade run"),
    # --- 32 problem ---
    ("The headbands on the first hardcover journal detached within a week; root cause was skipping the spine-lining linen layer so the PVA bead sheared off the rounded spine, and adding a proper super layer fixed every build after.", "problem", "personal", False,
     [("headbands", "concept"), ("spine-lining linen", "concept"), ("PVA", "technology"), ("super", "concept")],
     [("super", "headbands", "FIXES")],
     "which missing layer caused the headband detach on the first hardcover and what fix landed after",
     "headband detach spine lining linen pva super hardcover journal"),
    # --- 33 decision ---
    ("Standardised on a 3.38 mm iron pitch across wallets after a side-by-side with 3 mm and 3.85 mm; 3.38 mm balances stitch density against thread wear on Ritza 25 and reads clean at arm's length.", "decision", "personal", False,
     [("3.38 mm", "concept"), ("3 mm", "concept"), ("3.85 mm", "concept"), ("Ritza 25", "technology")],
     [("3.38 mm", "3 mm", "PREFERS")],
     "which iron pitch became the wallet standard after the three-way side-by-side and what was the balance",
     "iron pitch 3 38 3 3 85 ritza 25 wallet stitch density"),
    # --- 34 architecture ---
    ("Pattern production chain runs MakeSupply PDF template, card-stock oak-tag tracing, mylar acetate final for repeatable runs; each stage is dated and initialled so the current revision is always the loose one on the bench.", "architecture", "personal", False,
     [("MakeSupply", "organization"), ("oak-tag", "technology"), ("mylar acetate", "technology"), ("PDF template", "concept")],
     [("oak-tag", "mylar acetate", "APPLIES_TO")],
     "how does the three-stage pattern production chain guarantee the right revision sits on the bench",
     "makesupply pdf oak tag mylar acetate pattern production revision"),
    # --- 35 fact ---
    ("A roll of Barbour 18/3 waxed linen lasts about four months of weekly wallet production; Ritza 25 at 0.6 mm stretches to about six months because the polyester braid wastes less on tie-off.", "fact", "personal", False,
     [("Barbour 18/3", "technology"), ("Ritza 25", "technology"), ("waxed linen", "technology")],
     [("Ritza 25", "Barbour 18/3", "IMPROVES_ON")],
     "how do Barbour 18/3 and Ritza 25 compare on consumption under weekly wallet production",
     "barbour 18 3 ritza 25 waxed linen wallet production consume"),
    # --- 36 reference ---
    ("Keith Smith's exposed-spine volume is still the cleanest teaching reference for long stitch and link stitch variations; the Das Werkbuch German material covers bradel binding in a depth Smith does not reach.", "reference", "personal", False,
     [("Keith Smith", "person"), ("Das Werkbuch", "publication"), ("long stitch", "method"), ("bradel binding", "method")],
     [("Keith Smith", "long stitch", "APPLIES_TO")],
     "which reference splits teach long stitch versus bradel binding between Smith and Das Werkbuch",
     "keith smith das werkbuch long stitch bradel binding exposed spine"),
    # --- 37 decision ---
    ("Dropped Dixon edge bevelers from the daily rotation after the Blanchard Nº 2 arrived; the Blanchard holds an edge through a full hide where the Dixon needed a strop every fifth belt.", "decision", "personal", False,
     [("Dixon", "organization"), ("Blanchard", "organization"), ("edge bevelers", "tool")],
     [("Blanchard", "Dixon", "REPLACES")],
     "which edge-beveler brand replaced Dixon in the daily rotation and what edge-retention gap drove it",
     "dixon blanchard edge beveler daily rotation strop hide edge"),
    # --- 38 preference ---
    ("Prefer hand-stitching on pricking-iron marks over a stitching pony for small goods; the pony slows me down on wallets and the pricking-iron rhythm keeps consistent slant without a clamp forcing the angle.", "preference", "personal", False,
     [("pricking-iron", "tool"), ("stitching pony", "tool"), ("small goods", "concept")],
     [("pricking-iron", "stitching pony", "PREFERS")],
     "which hand-stitching setup do I prefer on small goods and what does the stitching pony cost me",
     "pricking iron stitching pony small goods wallet slant clamp"),
    # --- 39 architecture ---
    ("The burnishing station pairs a cocobolo slicker with a canvas wheel on a slow speed motor; water-damp edges hit the slicker first for shape, then Tokonole or beeswax on the wheel for the final polish.", "architecture", "personal", False,
     [("cocobolo slicker", "tool"), ("canvas wheel", "tool"), ("Tokonole", "technology"), ("beeswax", "technology")],
     [("cocobolo slicker", "canvas wheel", "APPLIES_TO")],
     "how does the two-stage burnishing station split shape from polish between slicker and canvas wheel",
     "cocobolo slicker canvas wheel tokonole beeswax burnish station stage"),
    # --- 40 milestone ---
    ("Gilt edges kept cracking on the first tooled journal run; the bole layer was too thick and the agate burnisher was skipping over the bumps, so thinning the bole to three brush coats and warming the burnisher fixed the run.", "milestone", "personal", False,
     [("Gilt edges", "concept"), ("bole", "technology"), ("agate burnisher", "tool"), ("tooled journal", "concept")],
     [("bole", "Gilt edges", "CAUSES")],
     "which root cause cracked the gilt edges on the tooled journal run and what two changes fixed it",
     "gilt edge bole agate burnisher tooled journal crack warm thin"),
    # --- 41 milestone ---
    ("Ran a full hide of Horween Chromexcel through the shop without scrap above the usual five percent; the cutting plan mapped every wallet, strap, and bookcloth accent before the first knife touched the hide.", "milestone", "personal", False,
     [("Horween Chromexcel", "technology"), ("cutting plan", "method"), ("bookcloth accent", "concept")],
     [("cutting plan", "Horween Chromexcel", "APPLIES_TO")],
     "which yield milestone did the Chromexcel hide hit and what planning step unlocked it",
     "horween chromexcel hide scrap five percent cutting plan yield"),
    # --- 42 architecture ---
    ("Tooling workflow for leather covers uses heated brass type for titles and cold-pressed blind-tooling for borders; the blind work sets first so the heated type can hit registered corners without scorching the earlier impressions.", "architecture", "personal", False,
     [("Tooling", "method"), ("brass type", "tool"), ("blind-tooling", "method"), ("borders", "concept")],
     [("blind-tooling", "brass type", "APPLIES_TO")],
     "how is cover tooling sequenced so heated brass type does not scorch earlier blind work",
     "tooling brass type blind cold press border heat register scorch"),
    # --- 43. noise ---
    ("The hallway coat rack has started hoarding grocery bags and nobody admits to being the owner of the teal one.", "fact", "noise", True, [], [], None, None),
    # --- 44 decision ---
    ("Chose Tärnsjö vegetable-tanned bridle over Wickett & Craig for the premium belt line; the fibre density is visibly tighter at the cut edge and burnishes cleaner even before beeswax hits it.", "decision", "personal", False,
     [("Tärnsjö", "organization"), ("Wickett & Craig", "organization"), ("vegetable-tanned", "technology"), ("beeswax", "technology")],
     [("Tärnsjö", "Wickett & Craig", "PREFERS")],
     "which tannery won the premium-belt slot over Wickett & Craig and what cut-edge behaviour drove it",
     "tarnsjo wickett craig vegetable tan bridle belt beeswax burnish"),
    # --- 45 fact ---
    ("A single pot of Fenice edge paint covers roughly sixty slim wallets at two coats each before the pigment begins to settle and the applicator starts dragging; opening a second pot sooner gives cleaner edges on the late builds.", "fact", "personal", False,
     [("Fenice", "organization"), ("edge paint", "technology"), ("slim wallets", "concept")],
     [("Fenice", "edge paint", "APPLIES_TO")],
     "how many slim wallets does a pot of Fenice cover before pigment settling starts hurting the edge",
     "fenice edge paint pot sixty slim wallet two coat settle"),
    # --- 46 reference ---
    ("The Das Werkbuch section on signature spacing and kettle stitches anchored my first hardcover sewing passes; the Keith Smith volumes filled in the exposed-spine variations the same week.", "reference", "personal", False,
     [("Das Werkbuch", "publication"), ("Keith Smith", "person"), ("kettle stitches", "method"), ("hardcover sewing", "method")],
     [("Das Werkbuch", "kettle stitches", "APPLIES_TO")],
     "which reference anchored kettle-stitch spacing and which one covered exposed-spine variations the same week",
     "das werkbuch keith smith kettle stitch signature hardcover expose"),
    # --- 47 decision ---
    ("Swapped from a French creaser to a heated edge creaser for the formal-wallet line; the heated iron lays a crisper line on Shell Cordovan and does not skate when the edge is still tacky from Resolene.", "decision", "personal", False,
     [("French creaser", "tool"), ("heated edge creaser", "tool"), ("Shell Cordovan", "technology"), ("Resolene", "technology")],
     [("heated edge creaser", "French creaser", "REPLACES")],
     "which creaser replaced the French creaser on the formal-wallet line and what edge condition drove the swap",
     "french heated edge creaser shell cordovan resolene formal wallet"),
    # --- 48 problem ---
    ("Saddle stitches kept backing out on the pull-up wallet corners; the thread wasn't waxed heavily enough through Chromexcel's oils, so hand-waxing Ritza 25 with beeswax before each corner stopped the loosening entirely.", "problem", "personal", False,
     [("Saddle stitches", "method"), ("pull-up", "technology"), ("Chromexcel", "technology"), ("Ritza 25", "technology"), ("beeswax", "technology")],
     [("beeswax", "Saddle stitches", "FIXES")],
     "which wax step fixed the corner-stitch backout on pull-up Chromexcel wallets and why",
     "saddle stitch pull up chromexcel ritza beeswax corner back out"),
    # --- 49 reference ---
    ("The shop notebook tracks every hide batch with Horween lot numbers, Tärnsjö dispatch dates, and a swatch stapled to the page; a reorder reference back to the batch is one page flip rather than a supplier email chain.", "reference", "personal", False,
     [("Horween", "organization"), ("Tärnsjö", "organization"), ("shop notebook", "concept"), ("lot numbers", "concept")],
     [("Horween", "Tärnsjö", "RELATED_TO")],
     "how does the shop notebook keep hide-batch reordering a one-page-flip rather than an email chain",
     "shop notebook horween tarnsjo lot number swatch reorder batch"),
    # --- 50 milestone ---
    ("Finished a matched journal-and-wallet set in Horween Chromexcel with a Coptic-bound notebook and a saddle-stitched bifold; both pieces use the same edge treatment and Ritza 25 thread colour so the set reads as one object.", "milestone", "personal", False,
     [("Horween Chromexcel", "technology"), ("Coptic", "method"), ("saddle-stitched", "method"), ("Ritza 25", "technology"), ("bifold", "concept")],
     [("Coptic", "Horween Chromexcel", "APPLIES_TO")],
     "which matched set finished with Coptic notebook plus saddle-stitched bifold and what unified the two pieces",
     "horween chromexcel coptic saddle stitch bifold ritza 25 matched set"),
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
