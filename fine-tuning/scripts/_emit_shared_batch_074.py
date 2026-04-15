"""One-off emitter for shared-base batch-074 — personal domain (fashion / style / personal appearance slice).

Writes 50 rows to data/v2/shared/batch_074.tmp.jsonl with ids shared-03651..03700.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_074.tmp.jsonl"
ID_OFFSET = 3650

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Settled the capsule wardrobe at 33 pieces on 2026-03-18 after a six-week trial; two pairs of jeans, eight tees, four button-downs, and one well-cut blazer carried the rotation.", "milestone", "personal", False,
     [("capsule wardrobe", "concept"), ("2026-03-18", "date"), ("blazer", "concept"), ("jeans", "concept")],
     [],
     "when did the pared-down closet experiment lock its final piece count and what made the cut",
     "capsule wardrobe trial end count blazer jeans tee shirt mix date"),
    # --- 2 ---
    ("Prefers the Uniqlo Airism crew over the Muji equivalent for daily undershirts; the Airism stays drier through a London commute and the seams sit flatter under a dress shirt.", "preference", "personal", False,
     [("Uniqlo", "organization"), ("Airism", "concept"), ("Muji", "organization"), ("London", "place"), ("dress shirt", "concept")],
     [("Uniqlo", "Muji", "PREFERS")],
     "which everyday undershirt brand wins for commute comfort and why",
     "uniqlo airism over muji undershirt commute dryness flat seam"),
    # --- 3 ---
    ("The shoe rotation is four pairs on a four-day cycle: Common Projects Achilles low, Clarks Desert Boot, New Balance 990v6, and a pair of Oxfords kept for client days.", "architecture", "personal", False,
     [("Common Projects", "organization"), ("Achilles", "concept"), ("Clarks", "organization"), ("Desert Boot", "concept"), ("New Balance", "organization"), ("Oxfords", "concept")],
     [],
     "how is the workweek shoe cycle laid out across pairs and days",
     "shoe rotation four day cycle sneaker boot trainer oxford lineup"),
    # --- 4 ---
    ("Replaced the old Warby Parker Percey frames with Moscot Lemtosh on 2026-02-09 after the bridge cracked; the Lemtosh sit lighter and the optician thinned the lenses by 1.6 mm.", "decision", "personal", False,
     [("Warby Parker", "organization"), ("Percey", "concept"), ("Moscot", "organization"), ("Lemtosh", "concept"), ("2026-02-09", "date"), ("optician", "person")],
     [("Moscot", "Warby Parker", "REPLACES")],
     "when did the eyewear swap happen and what improved with the new frames",
     "warby parker to moscot lemtosh frame swap weight lens thin date"),
    # --- 5 ---
    ("The seasonal closet swap happens the first Sunday of October and the first Sunday of April; winter coats and merino layers go into the under-bed vacuum bags and the linen comes out.", "architecture", "personal", False,
     [("seasonal closet swap", "activity"), ("October", "date"), ("April", "date"), ("merino", "concept"), ("linen", "concept"), ("vacuum bags", "tool")],
     [],
     "how is the spring-and-autumn wardrobe rotation actually scheduled and stored",
     "seasonal swap october april merino linen vacuum bag under bed cycle"),
    # --- 6 ---
    ("Booked the tailor at Henry Poole for the navy suit alterations on 2026-03-22; trouser hem to break cleanly on the brogue, jacket sleeves up 1 cm to show shirt cuff.", "milestone", "personal", False,
     [("Henry Poole", "organization"), ("navy suit", "concept"), ("2026-03-22", "date"), ("brogue", "concept"), ("jacket", "concept")],
     [("navy suit", "Henry Poole", "RELATED_TO")],
     "when did the suit alteration appointment land and what specifics were called",
     "henry poole tailor navy suit hem break sleeve cuff date"),
    # --- 7 ---
    ("Switched from Aesop Resurrection hand wash to Byredo Suede in the bathroom; same price tier, the Suede scent fades cleaner and doesn't compete with the cologne I actually wear.", "decision", "personal", False,
     [("Aesop", "organization"), ("Resurrection", "concept"), ("Byredo", "organization"), ("Suede", "concept"), ("cologne", "concept")],
     [("Byredo", "Aesop", "REPLACES")],
     "which bathroom hand wash took over from the previous one and why",
     "aesop resurrection to byredo suede hand wash scent fade cologne"),
    # --- 8 ---
    ("Prefers the barber Dimi at Ruffians Marylebone over the chain salons; he keeps the side parting at 4 mm tapered and remembers the cowlick at the crown.", "preference", "personal", False,
     [("Dimi", "person"), ("Ruffians Marylebone", "organization"), ("side parting", "concept"), ("cowlick", "concept")],
     [("Dimi", "Ruffians Marylebone", "WORKS_AT")],
     "which barber wins out and what makes the cut consistent",
     "dimi barber ruffians marylebone over chain side part taper cowlick"),
    # --- 9 ---
    ("The skincare routine settled on a three-step morning: CeraVe foaming cleanser, La Roche-Posay Anthelios SPF 50, and a pea-sized Vanicream moisturiser layered between.", "architecture", "personal", False,
     [("CeraVe", "organization"), ("foaming cleanser", "concept"), ("La Roche-Posay", "organization"), ("Anthelios", "concept"), ("Vanicream", "organization"), ("moisturiser", "concept")],
     [],
     "how is the morning face routine sequenced across cleanser sunscreen and moisturiser",
     "morning skincare cerave la roche posay vanicream three step layering"),
    # --- 10. noise ---
    ("Hold on, let me check the size tag before I forget.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("The thrifting habit lives at three shops on a Saturday loop: Crisis Finsbury, Mary's Living and Giving Primrose Hill, and the British Heart Foundation furniture shop on Holloway Road.", "reference", "personal", False,
     [("Crisis Finsbury", "organization"), ("Mary's Living and Giving", "organization"), ("Primrose Hill", "place"), ("British Heart Foundation", "organization"), ("Holloway Road", "place"), ("Saturday", "date")],
     [("Mary's Living and Giving", "Primrose Hill", "LOCATED_IN")],
     "where does the weekend charity shop loop go and which stops are on it",
     "thrift loop saturday crisis marys british heart foundation holloway"),
    # --- 12 ---
    ("Replaced the Daniel Wellington Classic with a Seiko SARB033 on 2026-01-30; mechanical movement, brushed dial, sits properly under a French cuff without snagging.", "decision", "personal", False,
     [("Daniel Wellington", "organization"), ("Classic", "concept"), ("Seiko", "organization"), ("SARB033", "concept"), ("2026-01-30", "date"), ("French cuff", "concept")],
     [("Seiko", "Daniel Wellington", "REPLACES")],
     "when did the everyday watch swap happen and what improved",
     "daniel wellington to seiko sarb033 watch swap mechanical cuff date"),
    # --- 13 ---
    ("The wedding outfit for Anjali and Tom on 2026-06-20 is locked: charcoal Drake's three-piece, white spread collar, burgundy grenadine tie, oxblood Crockett and Jones.", "decision", "personal", False,
     [("Anjali", "person"), ("Tom", "person"), ("2026-06-20", "date"), ("Drake's", "organization"), ("grenadine tie", "concept"), ("Crockett and Jones", "organization")],
     [],
     "what is the dressing plan locked for the june wedding",
     "wedding outfit charcoal three piece grenadine oxblood shoes date"),
    # --- 14 ---
    ("Prefers Tide Free and Gentle for everything cotton and the Eucalan no-rinse for merino and silk; the Eucalan keeps the merino base layers from pilling at the shoulder.", "preference", "personal", False,
     [("Tide Free and Gentle", "concept"), ("cotton", "concept"), ("Eucalan", "concept"), ("merino", "concept"), ("silk", "concept")],
     [("Eucalan", "Tide Free and Gentle", "PREFERS")],
     "which detergent serves which fabric in the laundry routine and why",
     "tide free gentle cotton eucalan merino silk pilling shoulder care"),
    # --- 15 ---
    ("The signet ring on the right pinky is a 9 ct rose gold piece reset by Rebus Hatton Garden in 2025-09; the original engraving from grandad sits inside the band, untouched.", "fact", "personal", False,
     [("signet ring", "concept"), ("Rebus", "organization"), ("Hatton Garden", "place"), ("2025-09", "date"), ("grandad", "person")],
     [("Rebus", "Hatton Garden", "LOCATED_IN")],
     "where was the family ring reset and what stayed original to it",
     "signet ring rose gold rebus hatton garden engraving grandad reset"),
    # --- 16 ---
    ("Switched from buying new white tees every six months to a five-pack of CDLP from Sweden once a year; the cost evens out and the neckline holds shape twice as long.", "decision", "personal", False,
     [("white tees", "concept"), ("CDLP", "organization"), ("Sweden", "place"), ("neckline", "concept")],
     [("CDLP", "white tees", "REPLACES")],
     "which white tee strategy took over and what shifted in cost and wear",
     "white tee swap cdlp sweden five pack annual neckline shape cost"),
    # --- 17 ---
    ("The annual brogue resole at Pediwear Halifax went in by post on 2026-02-05; Goodyear-welt rebuild, leather sole, half-rubber forefoot for London pavements.", "milestone", "personal", False,
     [("brogue", "concept"), ("Pediwear", "organization"), ("Halifax", "place"), ("2026-02-05", "date"), ("Goodyear-welt", "method"), ("London", "place")],
     [("Pediwear", "Halifax", "LOCATED_IN")],
     "when did the brogue resole go off and what spec was asked for",
     "brogue resole pediwear halifax goodyear welt half rubber pavements date"),
    # --- 18 ---
    ("Prefers the Mason Pearson Junior bristle brush over the Tangle Teezer for the morning hair routine; the boar bristle moves the natural oil out to the ends and tames the cowlick.", "preference", "personal", False,
     [("Mason Pearson", "organization"), ("Junior", "concept"), ("Tangle Teezer", "organization"), ("boar bristle", "concept"), ("cowlick", "concept")],
     [("Mason Pearson", "Tangle Teezer", "PREFERS")],
     "which morning hair brush wins and why for oil distribution",
     "mason pearson junior over tangle teezer boar bristle oil cowlick"),
    # --- 19 ---
    ("The colour palette for 2026 leans navy, oatmeal, olive, oxblood, and a soft ecru; black is reserved for funerals and one knit polo for late-night work events.", "preference", "personal", False,
     [("navy", "concept"), ("oatmeal", "concept"), ("olive", "concept"), ("oxblood", "concept"), ("ecru", "concept"), ("black", "concept")],
     [("navy", "black", "PREFERS")],
     "what colour spread is the wardrobe centred on this year and what is the exception",
     "color palette navy oatmeal olive oxblood ecru black funeral polo"),
    # --- 20 ---
    ("Started the wet-shave routine on 2026-03-02 with an Edwin Jagger DE89, a Personna lab blue blade, and Proraso Green soap; cuts dropped to zero by week three.", "milestone", "personal", False,
     [("wet-shave", "activity"), ("2026-03-02", "date"), ("Edwin Jagger", "organization"), ("DE89", "concept"), ("Personna", "organization"), ("Proraso", "organization")],
     [],
     "when did the safety razor routine start and what kit settled in",
     "wet shave start edwin jagger de89 personna proraso cuts learning curve"),
    # --- 21 ---
    ("The dry-cleaner relationship with Jeeves of Belgravia covers the suits and the silk ties; everything wool-knit goes to a hand-wash at home, never the dry-clean cycle.", "architecture", "personal", False,
     [("Jeeves of Belgravia", "organization"), ("suits", "concept"), ("silk ties", "concept"), ("wool-knit", "concept")],
     [("suits", "Jeeves of Belgravia", "RELATED_TO")],
     "which garments go to the dry cleaner and which stay home",
     "jeeves belgravia suits ties dry clean wool knit hand wash boundary"),
    # --- 22 ---
    ("Replaced the Levi's 511 dark wash with the A.P.C. Petit New Standard on 2026-03-09; the rigid raw denim broke in across six weeks and the rise sits where it should.", "decision", "personal", False,
     [("Levi's", "organization"), ("511", "concept"), ("A.P.C.", "organization"), ("Petit New Standard", "concept"), ("2026-03-09", "date"), ("raw denim", "concept")],
     [("A.P.C.", "Levi's", "REPLACES")],
     "when did the everyday jean swap happen and what changed in the fit",
     "levis 511 to apc petit new standard raw denim break in rise date"),
    # --- 23 ---
    ("The cologne lineup is two bottles only: Le Labo Santal 33 for evening, Acqua di Parma Colonia for daytime; the Santal in office hours felt too loud after a meeting note.", "preference", "personal", False,
     [("Le Labo", "organization"), ("Santal 33", "concept"), ("Acqua di Parma", "organization"), ("Colonia", "concept")],
     [("Acqua di Parma", "Le Labo", "PREFERS")],
     "how is the fragrance pair split between day and night and why the divide",
     "le labo santal 33 evening acqua di parma colonia daytime split"),
    # --- 24 ---
    ("Booked the colour analysis at House of Colour on 2026-04-02; came back as Soft Autumn, which finally explains why oatmeal and olive look right and pure white washes me out.", "milestone", "personal", False,
     [("House of Colour", "organization"), ("2026-04-02", "date"), ("Soft Autumn", "concept"), ("oatmeal", "concept"), ("olive", "concept")],
     [],
     "when was the personal colour consult and what was the result",
     "house of colour soft autumn season oatmeal olive white wash date"),
    # --- 25 ---
    ("The accessory upgrade for the year was a Bellroy Hide and Seek wallet in caramel; replaces a 12-year-old Mulberry that had finally split at the bill compartment.", "decision", "personal", False,
     [("Bellroy", "organization"), ("Hide and Seek", "concept"), ("caramel", "concept"), ("Mulberry", "organization"), ("bill compartment", "concept")],
     [("Bellroy", "Mulberry", "REPLACES")],
     "which wallet took over and what failure pushed the swap",
     "bellroy hide and seek caramel over mulberry split bill compartment"),
    # --- 26 ---
    ("Prefers the Stetson Hatteras flat cap in tweed over the Bailey one for autumn walks; the Hatteras grips the head better in wind off the heath.", "preference", "personal", False,
     [("Stetson", "organization"), ("Hatteras", "concept"), ("Bailey", "organization"), ("tweed", "concept"), ("heath", "place")],
     [("Stetson", "Bailey", "PREFERS")],
     "which flat cap wins for windy walks and why",
     "stetson hatteras tweed over bailey flat cap wind grip heath"),
    # --- 27 ---
    ("The skincare night step added tretinoin 0.025% on 2026-01-14 after the dermatology referral; pea-sized, three nights a week, and Vanicream every morning to ride out the peeling.", "milestone", "personal", False,
     [("tretinoin", "concept"), ("2026-01-14", "date"), ("dermatology", "field"), ("Vanicream", "organization"), ("peeling", "concept")],
     [],
     "when did tretinoin enter the routine and how is it dosed alongside moisturiser",
     "tretinoin start derm referral dose three nights vanicream peeling date"),
    # --- 28 ---
    ("The reading glasses are a separate prescription: +1.25 readers in tortoiseshell from Cubitts Marylebone; kept on the desk and on the bedside, never carried.", "reference", "personal", False,
     [("reading glasses", "tool"), ("tortoiseshell", "concept"), ("Cubitts", "organization"), ("Marylebone", "place"), ("bedside", "place")],
     [("Cubitts", "Marylebone", "LOCATED_IN")],
     "what is the reading-glasses setup and where do the pairs live",
     "reading glasses 1.25 cubitts marylebone tortoiseshell desk bedside"),
    # --- 29 ---
    ("Switched from the gym duffel to a Filson Field bag on 2026-03-15; the waxed canvas survives a Tuesday squash session and looks right walking into the office afterwards.", "decision", "personal", False,
     [("gym duffel", "concept"), ("Filson", "organization"), ("Field bag", "concept"), ("2026-03-15", "date"), ("squash", "hobby"), ("waxed canvas", "concept")],
     [("Filson", "gym duffel", "REPLACES")],
     "when did the bag swap happen and what dual role does the new one carry",
     "gym duffel to filson field waxed canvas squash office crossover date"),
    # --- 30 ---
    ("The wool overcoat from Drake's needs the brush-and-hang ritual after every wear: horsehair brush down the grain, ten minutes on the cedar hanger by the window.", "architecture", "personal", False,
     [("wool overcoat", "concept"), ("Drake's", "organization"), ("horsehair brush", "tool"), ("cedar hanger", "tool")],
     [],
     "how is the overcoat cared for between wears and why the steps matter",
     "wool overcoat brush hang horsehair cedar hanger window airing routine"),
    # --- 31 ---
    ("Prefers the John Smedley fine merino polo over the Sunspel one for smart-casual evenings; the Smedley collar holds shape after a wash and the cuff stays narrow.", "preference", "personal", False,
     [("John Smedley", "organization"), ("merino polo", "concept"), ("Sunspel", "organization"), ("collar", "concept"), ("cuff", "concept")],
     [("John Smedley", "Sunspel", "PREFERS")],
     "which knit polo brand wins for evenings out and why",
     "john smedley over sunspel merino polo collar shape cuff hold"),
    # --- 32 ---
    ("The salon visit at Larry King Soho on 2026-02-17 went wrong: the senior stylist took 2 cm too much off the back; rebooked with Fiona for the next round.", "problem", "personal", False,
     [("Larry King", "organization"), ("Soho", "place"), ("2026-02-17", "date"), ("senior stylist", "person"), ("Fiona", "person")],
     [("Larry King", "Soho", "LOCATED_IN")],
     "what went wrong at the salon visit and what is the recovery plan",
     "larry king soho cut too short senior stylist fiona rebook date"),
    # --- 33 ---
    ("The seasonal closet swap turned up six unworn shirts on 2026-04-05; sent four to Crisis Finsbury, kept two for painting around the house.", "fact", "personal", False,
     [("seasonal closet swap", "activity"), ("2026-04-05", "date"), ("shirts", "concept"), ("Crisis Finsbury", "organization")],
     [],
     "what did the spring wardrobe sweep surface and where did it go",
     "closet swap unworn shirt count crisis charity donate paint shirt"),
    # --- 34. noise ---
    ("Right, where did I leave the lint roller again.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The barber visit at Ted's Grooming Room is booked every four weeks on a Wednesday at 18:30; Idris keeps a card of the clipper grades to spare the conversation each time.", "architecture", "personal", False,
     [("Ted's Grooming Room", "organization"), ("Wednesday", "date"), ("Idris", "person"), ("clipper grades", "concept")],
     [("Idris", "Ted's Grooming Room", "WORKS_AT")],
     "how is the barber cadence set and what makes the chair-time efficient",
     "teds grooming four week wednesday idris clipper grade card cadence"),
    # --- 36 ---
    ("Replaced the Ray-Ban Wayfarers with Persol 714 foldables on 2026-04-08; the Persol fold flat into the jacket inside pocket and survive a beach week without a hard case.", "decision", "personal", False,
     [("Ray-Ban", "organization"), ("Wayfarers", "concept"), ("Persol", "organization"), ("714", "concept"), ("2026-04-08", "date"), ("jacket", "concept")],
     [("Persol", "Ray-Ban", "REPLACES")],
     "when did the sunglasses swap happen and what practical win came with it",
     "ray ban wayfarer to persol 714 foldable jacket pocket beach date"),
    # --- 37 ---
    ("The cashmere care routine is a once-a-season Eucalan soak in the kitchen sink, towel-roll dry, then flat dry on the airing rack; never on a hanger which warps the shoulder.", "reference", "personal", False,
     [("cashmere", "concept"), ("Eucalan", "concept"), ("kitchen sink", "place"), ("airing rack", "tool"), ("shoulder", "concept")],
     [],
     "how is cashmere washed and dried and what mistake is being avoided",
     "cashmere eucalan soak towel roll flat dry hanger shoulder warp rule"),
    # --- 38 ---
    ("Prefers the Smythson Panama notebook in nile blue as the everyday carry over the Moleskine; thinner paper but the cover survives a wet jacket pocket and a year of use.", "preference", "personal", False,
     [("Smythson", "organization"), ("Panama", "concept"), ("nile blue", "concept"), ("Moleskine", "organization"), ("jacket", "concept")],
     [("Smythson", "Moleskine", "PREFERS")],
     "which pocket notebook wins as a daily carry and why the cover matters",
     "smythson panama nile blue over moleskine cover survive jacket pocket"),
    # --- 39 ---
    ("The Drake's silk knit tie collection is up to seven now; rotated by colour, stored rolled in a drawer divider, never knotted overnight to keep the silk from creasing.", "architecture", "personal", False,
     [("Drake's", "organization"), ("silk knit tie", "concept"), ("drawer divider", "tool"), ("silk", "concept")],
     [],
     "how is the knit tie collection stored and why the no-overnight-knot rule",
     "drakes silk knit tie collection rolled drawer divider crease care"),
    # --- 40 ---
    ("Replaced the Bose QC35 with Sony WH-1000XM5 over-ears on 2026-01-08 as a daily accessory; the Sony tuck flatter against the head and don't ruin the hairline by lunchtime.", "decision", "personal", False,
     [("Bose", "organization"), ("QC35", "concept"), ("Sony", "organization"), ("WH-1000XM5", "concept"), ("2026-01-08", "date")],
     [("Sony", "Bose", "REPLACES")],
     "when did the over-ear swap happen and what appearance issue did it solve",
     "bose qc35 to sony wh1000xm5 headphone swap flat hairline date"),
    # --- 41 ---
    ("The dressing-for-court rule at the magistrate's hearing on 2026-04-16 is the navy two-piece, plain spread collar, navy grenadine; defence brief said no patterns and no double-breasted.", "reference", "personal", False,
     [("magistrate's hearing", "event"), ("2026-04-16", "date"), ("navy two-piece", "concept"), ("grenadine", "concept"), ("defence brief", "person")],
     [],
     "what is the courtroom dress brief for the april hearing and where did it come from",
     "court dress code navy two piece plain collar grenadine no pattern date"),
    # --- 42 ---
    ("Prefers the Persol 649 over the Persol 714 for spring driving; the 649 wider lens cuts the low east-bound sun on the M4 better than the foldable.", "preference", "personal", False,
     [("Persol", "organization"), ("649", "concept"), ("714", "concept"), ("M4", "place"), ("spring", "date")],
     [("649", "714", "PREFERS")],
     "which sunglasses model wins for spring driving and why",
     "persol 649 over 714 spring driving wider lens m4 east sun"),
    # --- 43 ---
    ("The grey at the temples gets a six-week tint at Larry King Soho with Fiona; she keeps it two shades softer than the base so the regrowth never reads as a hard line.", "architecture", "personal", False,
     [("grey", "concept"), ("temples", "concept"), ("Larry King", "organization"), ("Soho", "place"), ("Fiona", "person")],
     [("Fiona", "Larry King", "WORKS_AT")],
     "how is the temple grey covered and why the colour choice matters",
     "grey temple tint six week larry king fiona two shades softer regrowth"),
    # --- 44 ---
    ("The wedding-guest fitting at Anderson and Sheppard on 2026-04-22 confirmed the trouser leg at 18.5 cm at the hem and the jacket vent length at 24 cm; nothing else moved.", "fact", "personal", False,
     [("Anderson and Sheppard", "organization"), ("2026-04-22", "date"), ("trouser leg", "concept"), ("jacket vent", "concept")],
     [],
     "what came out of the savile row fitting and what numbers were locked",
     "anderson sheppard fitting trouser leg width jacket vent length date"),
    # --- 45 ---
    ("The shoe-tree rule is cedar in every pair within ten minutes of taking them off; the Woodlore trees from Pediwear go in by feel, never the spring-loaded plastic ones.", "preference", "personal", False,
     [("cedar", "concept"), ("Woodlore", "organization"), ("Pediwear", "organization"), ("plastic", "concept")],
     [("Woodlore", "plastic", "PREFERS")],
     "what is the shoe tree rule and which tree is preferred over which",
     "cedar shoe tree ten minute rule woodlore over plastic spring loaded"),
    # --- 46 ---
    ("Switched the office shirt order from Charles Tyrwhitt to Hawes and Curtis after 2026-02; the Hawes spread collar sits cleaner under a knit tie and the cuff length fits the Seiko.", "decision", "personal", False,
     [("Charles Tyrwhitt", "organization"), ("Hawes and Curtis", "organization"), ("2026-02", "date"), ("knit tie", "concept"), ("Seiko", "organization")],
     [("Hawes and Curtis", "Charles Tyrwhitt", "REPLACES")],
     "which dress shirt source took over and what fit detail decided it",
     "charles tyrwhitt to hawes curtis spread collar knit tie cuff seiko"),
    # --- 47 ---
    ("The eyebrow tidy at the salon is every eight weeks with Lana; she threads only the strays under the arch, never touches the top line which I want kept heavy.", "reference", "personal", False,
     [("eyebrow tidy", "activity"), ("Lana", "person"), ("arch", "concept"), ("top line", "concept")],
     [],
     "how is the brow upkeep handled and what direction is given each time",
     "eyebrow eight week lana thread under arch keep top heavy rule"),
    # --- 48 ---
    ("Prefers the Czech and Speake No. 88 shaving cream in the bowl over the Proraso green for special occasions; the No. 88 lather sits denser and the rose top note carries into the day.", "preference", "personal", False,
     [("Czech and Speake", "organization"), ("No. 88", "concept"), ("Proraso", "organization"), ("rose", "concept")],
     [("Czech and Speake", "Proraso", "PREFERS")],
     "which shaving cream wins for special days and why the lather and scent matter",
     "czech speake no 88 over proraso green dense lather rose note occasion"),
    # --- 49 ---
    ("The annual jewellery audit on 2026-01-04 turned up four pieces unworn in two years: sent the silver bangle and the cufflinks to Rebus for melt-and-recast credit toward a new pinky ring.", "milestone", "personal", False,
     [("jewellery audit", "activity"), ("2026-01-04", "date"), ("silver bangle", "concept"), ("cufflinks", "concept"), ("Rebus", "organization"), ("pinky ring", "concept")],
     [],
     "when was the jewellery audit and what was done with the unworn pieces",
     "jewellery audit unworn melt recast rebus credit pinky ring date"),
    # --- 50 ---
    ("The cologne lineup expansion to three bottles is on hold; tried the Frederic Malle Vetiver Extraordinaire on 2026-04-09 and it clashed with the Santal 33 in the same week.", "problem", "personal", False,
     [("Frederic Malle", "organization"), ("Vetiver Extraordinaire", "concept"), ("2026-04-09", "date"), ("Santal 33", "concept")],
     [],
     "what stalled the third-cologne addition and what was tried",
     "frederic malle vetiver extraordinaire trial clash santal 33 hold date"),
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
