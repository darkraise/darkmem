"""One-off emitter for shared-base batch-275 — personal domain (ceramics and pottery: clay bodies, wheels, kilns, firing, glazes, surface techniques, potters, studios, events).

Writes 50 rows to data/v2/shared/batch_275.tmp.jsonl with ids shared-13701..13750.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_275.tmp.jsonl"
ID_OFFSET = 13700

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 --- decision
    ("Switched my main throwing body from midfire Standard 308 to a cone 10 stoneware; the higher firing gave denser pots and my shino glazes finally broke properly on the rims.", "decision", "personal", False,
     [("midfire Standard 308", "concept"), ("cone 10 stoneware", "concept"), ("shino", "concept")],
     [("cone 10 stoneware", "midfire Standard 308", "REPLACES"), ("shino", "cone 10 stoneware", "APPLIES_TO")],
     "which higher-firing clay body did I move to from a midfire stoneware to make my shino rims break right",
     "midfire 308 cone 10 stoneware shino rim break swap throw"),
    # --- 2 --- architecture
    ("My studio runs three clay bodies in parallel: a Grolleg porcelain for translucent work, a cone 6 oxidation stoneware for the functional line, and a terra cotta for the garden pots that stay outside all winter.", "architecture", "personal", False,
     [("Grolleg porcelain", "concept"), ("cone 6 oxidation", "concept"), ("terra cotta", "concept")],
     [("Grolleg porcelain", "terra cotta", "RELATED_TO")],
     "how is my clay-body inventory split across translucent, functional, and outdoor garden work",
     "grolleg porcelain cone 6 oxidation terra cotta studio three body split"),
    # --- 3 --- milestone
    ("After two years of cracked rims I finally pulled a clean twelve-inch bowl off the Shimpo VL-Whisper; the quiet direct-drive motor let me feel the clay slipping before the wall collapsed.", "milestone", "personal", False,
     [("Shimpo VL-Whisper", "tool"), ("twelve-inch bowl", "concept")],
     [("twelve-inch bowl", "Shimpo VL-Whisper", "APPLIES_TO")],
     "which quiet direct-drive wheel finally let me throw a clean twelve-inch bowl after years of cracking rims",
     "shimpo vl whisper twelve inch bowl direct drive quiet wheel clean"),
    # --- 4 --- decision
    ("Picked the Brent CXC over a used Soldner at the studio sale; the CXC's flat wheelhead and reversible pedal suited my left-handed trimming better than the Soldner's centre post would have.", "decision", "personal", False,
     [("Brent CXC", "tool"), ("Soldner", "tool")],
     [("Brent CXC", "Soldner", "PREFERS")],
     "which wheel did I pick over a used Soldner and which feature sealed the choice for a left-handed trimmer",
     "brent cxc soldner wheel pick flat head reversible pedal left handed"),
    # --- 5 --- reference
    ("Bernard Leach's A Potter's Book from 1940 still sits on the studio shelf; the chapter on stoneware and porcelain kilns is where I first read a coherent description of a reduction atmosphere.", "reference", "personal", False,
     [("Bernard Leach", "person"), ("A Potter's Book", "publication"), ("1940", "date"), ("reduction", "concept")],
     [("A Potter's Book", "Bernard Leach", "AUTHORED_BY"), ("A Potter's Book", "1940", "HAPPENED_ON")],
     "which 1940 Leach book first gave me a coherent description of reduction atmosphere in stoneware kilns",
     "leach potters book 1940 stoneware porcelain reduction atmosphere chapter"),
    # --- 6 --- architecture
    ("The electric firing schedule runs a slow bisque 04 with a long sixty-minute hold at 1200 Fahrenheit to burn off organics, then a cone 6 oxidation glaze fire with a thirty-minute soak at peak.", "architecture", "personal", False,
     [("bisque 04", "concept"), ("cone 6 oxidation", "concept"), ("1200 Fahrenheit", "concept"), ("soak", "method")],
     [("soak", "cone 6 oxidation", "APPLIES_TO"), ("bisque 04", "1200 Fahrenheit", "APPLIES_TO")],
     "how does my electric schedule layer a bisque burn-off hold with a peak glaze soak",
     "bisque 04 cone 6 oxidation 1200 hold soak electric schedule burn"),
    # --- 7 --- fact
    ("My Skutt KM1027 draws about forty-eight amps on a hard cone 6 climb; I had to pull a dedicated line from the panel before the studio breaker stopped tripping on the final half hour.", "fact", "personal", False,
     [("Skutt KM1027", "tool"), ("cone 6", "concept")],
     [("Skutt KM1027", "cone 6", "APPLIES_TO")],
     "which Skutt model draws about forty-eight amps on a hard cone 6 climb and needed a dedicated panel line",
     "skutt km1027 forty eight amp cone 6 panel breaker dedicated line"),
    # --- 8 --- decision
    ("Chose an L&L e28T over a second Skutt for the new studio; the hard-ceramic element holders mean I can swap elements without digging brick, which mattered more than the price gap.", "decision", "personal", False,
     [("L&L e28T", "tool"), ("Skutt", "tool"), ("element holders", "concept")],
     [("L&L e28T", "Skutt", "PREFERS")],
     "which electric kiln did I pick over a second Skutt and what maintenance feature sealed the choice",
     "ll e28t skutt element holder kiln swap hard ceramic studio pick"),
    # --- 9 --- architecture
    ("The Bailey Gas Kiln lives in the back shed with a venturi burner setup; I run heavy reduction from cone 08 up to cone 10 by damping the flue progressively and reading the flame colour at the spyhole.", "architecture", "personal", False,
     [("Bailey Gas Kiln", "tool"), ("venturi burner", "concept"), ("cone 08", "concept"), ("cone 10", "concept"), ("reduction", "concept")],
     [("Bailey Gas Kiln", "reduction", "APPLIES_TO"), ("venturi burner", "Bailey Gas Kiln", "HAS_PART")],
     "how does my Bailey Gas Kiln run reduction from cone 08 to cone 10 and which burner type sits on it",
     "bailey gas venturi burner reduction cone 08 10 flue damp spyhole"),
    # --- 10. noise ---
    ("The studio cat has adopted the drying rack as her afternoon nap spot and nobody has the heart to move her once she settles.", "fact", "noise", True, [], [], None, None),
    # --- 11 --- decision
    ("Swapped my tenmoku recipe for a proper temmoku iron saturate after reading Shoji Hamada notes in translation; the new version breaks rust-red on the edges instead of sitting flat black across the whole pot.", "decision", "personal", False,
     [("tenmoku", "concept"), ("temmoku iron saturate", "concept"), ("Shoji Hamada", "person")],
     [("temmoku iron saturate", "tenmoku", "REPLACES")],
     "which iron glaze replaced my flat tenmoku after reading Hamada's notes and what visual did it unlock",
     "tenmoku temmoku iron saturate hamada rust red break edge black"),
    # --- 12 --- milestone
    ("Finally got a clean copper red out of the Bailey Gas Kiln this winter; the key turned out to be a heavy body reduction at cone 08 followed by a clearing oxidation hold before climbing to cone 10.", "milestone", "personal", False,
     [("copper red", "concept"), ("Bailey Gas Kiln", "tool"), ("body reduction", "method"), ("cone 08", "concept"), ("cone 10", "concept")],
     [("copper red", "Bailey Gas Kiln", "APPLIES_TO"), ("body reduction", "copper red", "APPLIES_TO")],
     "how did I finally pull a clean copper red and which reduction stage turned out to be the key",
     "copper red bailey body reduction cone 08 10 clearing oxidation hold"),
    # --- 13 --- reference
    ("Shoji Hamada's Mashiko pots from the nineteen-sixties set the grammar for the brushwork style I still chase; the loaded hake and single confident stroke is where my own decoration apprenticeship began.", "reference", "personal", False,
     [("Shoji Hamada", "person"), ("Mashiko", "place"), ("hake", "tool"), ("brushwork", "method")],
     [("Shoji Hamada", "Mashiko", "LIVES_IN"), ("brushwork", "Shoji Hamada", "AUTHORED_BY")],
     "which Hamada-era pots from Mashiko set the grammar for the loaded hake brushwork I chase",
     "hamada mashiko sixties hake brushwork decoration apprentice style"),
    # --- 14 --- decision
    ("Committed to single-firing the cone 6 oxidation line; skipping the bisque cut my kiln-hour bill in half and the glazes went on raw bone-dry work once I switched to a deflocculated dip.", "decision", "personal", False,
     [("single-firing", "method"), ("bisque", "concept"), ("cone 6 oxidation", "concept"), ("deflocculated dip", "method")],
     [("single-firing", "bisque", "REPLACES"), ("deflocculated dip", "single-firing", "APPLIES_TO")],
     "which firing schedule halved my kiln-hour bill by skipping bisque and what glaze change made it work",
     "single fire bisque cone 6 oxidation deflocculated dip raw bone dry"),
    # --- 15 --- architecture
    ("My surface decoration stack layers three techniques: a mishima black-line inlay for the rim, sgraffito through a white slip on the body, and a thin ash glaze over the foot that breaks on the throw rings.", "architecture", "personal", False,
     [("mishima", "method"), ("sgraffito", "method"), ("ash glaze", "concept"), ("white slip", "concept")],
     [("sgraffito", "white slip", "APPLIES_TO"), ("ash glaze", "mishima", "RELATED_TO")],
     "how does my surface stack layer mishima, sgraffito, and ash glaze across the rim, body, and foot",
     "mishima sgraffito ash glaze white slip rim body foot inlay stack"),
    # --- 16 --- milestone
    ("Sat through a two-week intensive with Simon Levin at Watershed Maine; the anagama wood kiln notes I took on flash-ash placement still drive how I stack my own wood firings.", "milestone", "personal", False,
     [("Simon Levin", "person"), ("Watershed Maine", "organization"), ("anagama wood kiln", "tool"), ("flash-ash", "concept")],
     [("Simon Levin", "Watershed Maine", "WORKS_AT"), ("flash-ash", "anagama wood kiln", "APPLIES_TO")],
     "which Watershed intensive with Simon Levin still drives how I stack an anagama for flash-ash placement",
     "simon levin watershed maine anagama wood flash ash stack intensive"),
    # --- 17 --- fact
    ("The nearest functional anagama wood kiln I can fire at is four hours north; the host kiln crew splits the stoking into six-hour shifts and the full firing runs just under four days.", "fact", "personal", False,
     [("anagama wood kiln", "tool"), ("stoking", "activity")],
     [("stoking", "anagama wood kiln", "APPLIES_TO")],
     "how long is the full firing cycle at the anagama I drive up to and how are the stoking shifts split",
     "anagama wood kiln stoking shift four day six hour north firing"),
    # --- 18 --- decision
    ("Dropped raku from my workshop rotation this year; the thermal shock on the Grolleg porcelain bodies I was teaching with was cracking half the pieces and students left the session demoralised.", "decision", "personal", False,
     [("raku", "concept"), ("Grolleg porcelain", "concept"), ("thermal shock", "concept")],
     [("thermal shock", "Grolleg porcelain", "APPLIES_TO")],
     "why did I pull raku from my workshop rotation and which clay body was cracking in thermal shock",
     "raku grolleg porcelain thermal shock workshop rotation crack student"),
    # --- 19 --- preference
    ("I prefer a salt firing over a soda firing on my cone 10 stoneware; the salt orange-peel texture on the shoulders reads sharper in photographs than the softer soda flash.", "preference", "personal", False,
     [("salt", "concept"), ("soda", "concept"), ("cone 10 stoneware", "concept"), ("orange-peel", "concept")],
     [("salt", "soda", "PREFERS"), ("orange-peel", "salt", "APPLIES_TO")],
     "which atmospheric firing do I prefer over soda on cone 10 stoneware and why for photography",
     "salt soda cone 10 stoneware orange peel photograph prefer shoulder"),
    # --- 20 --- milestone
    ("Sold out my booth at NCECA conference on the first afternoon; the Southern Ice porcelain cups with celadon interiors were what disappeared first and I had to ship the mailing-list orders from home.", "milestone", "personal", False,
     [("NCECA conference", "event"), ("Southern Ice", "concept"), ("celadon", "concept")],
     [("Southern Ice", "celadon", "APPLIES_TO"), ("Southern Ice", "NCECA conference", "APPLIES_TO")],
     "which porcelain-and-glaze combination sold out first at my NCECA booth on opening afternoon",
     "nceca southern ice porcelain celadon cup booth sell out first afternoon"),
    # --- 21 --- reference
    ("Chose a two-week residency at La Meridiana Italy over a slot at Penland this summer; the Italian maiolica tradition was further from my daily practice and I wanted the stretch.", "reference", "personal", False,
     [("La Meridiana Italy", "organization"), ("Penland", "organization"), ("maiolica", "concept")],
     [("La Meridiana Italy", "Penland", "PREFERS"), ("maiolica", "La Meridiana Italy", "APPLIES_TO")],
     "which Italian residency did I pick over a Penland slot this summer and what tradition drew me there",
     "la meridiana italy penland maiolica residency summer pick stretch"),
    # --- 22 --- architecture
    ("My handle recipe runs a pulled strap off a thick stub, compressed with a chamois for the grip, and set back onto leather-hard Frost porcelain mugs while the body is still pliable enough to weld cleanly.", "architecture", "personal", False,
     [("pulled strap", "method"), ("Frost porcelain", "concept"), ("leather-hard", "concept"), ("weld", "method")],
     [("pulled strap", "Frost porcelain", "APPLIES_TO"), ("weld", "leather-hard", "APPLIES_TO")],
     "how does my handle recipe move from a thick stub through a chamois-pulled strap onto leather-hard porcelain",
     "pulled strap handle frost porcelain leather hard weld chamois mug"),
    # --- 23 --- problem
    ("The oribe ran streaky across my faceting on the cone 10 stoneware tumblers; bumping the glaze thickness by ten percent and tightening the facet bevel fixed the pooling on the next batch.", "problem", "personal", False,
     [("oribe", "concept"), ("faceting", "method"), ("cone 10 stoneware", "concept")],
     [("oribe", "cone 10 stoneware", "APPLIES_TO")],
     "why did oribe run streaky over faceted cone 10 tumblers and which two tweaks fixed the pooling",
     "oribe faceting cone 10 stoneware tumbler streak pool thickness bevel"),
    # --- 24 --- reference
    ("Warren MacKenzie's mingei-influenced tableware is the practical template I circle back to when the studio drifts toward decorative work; the production-line ethic and humble forms are the whole point.", "reference", "personal", False,
     [("Warren MacKenzie", "person"), ("mingei", "concept"), ("tableware", "concept")],
     [("Warren MacKenzie", "mingei", "APPLIES_TO")],
     "which MacKenzie tradition is the template I return to when the studio drifts into decorative work",
     "warren mackenzie mingei tableware production line humble template drift"),
    # --- 25 --- decision
    ("Replaced the Olympic kiln controller with a Bartlett V6 after two runs finished cold; the old electromechanical timer was drifting badly and the V6's cone-fire mode does the peak hold without me babysitting.", "decision", "personal", False,
     [("Olympic kiln", "tool"), ("Bartlett V6", "tool"), ("cone-fire mode", "concept")],
     [("Bartlett V6", "Olympic kiln", "APPLIES_TO"), ("Bartlett V6", "cone-fire mode", "HAS_PART")],
     "which controller swap fixed cold-finishing runs on the Olympic and what mode removed the babysitting",
     "olympic kiln bartlett v6 controller cone fire timer drift cold finish"),
    # --- 26 --- architecture
    ("The Geil downdraft at the community studio is plumbed for both soda and reduction; the crew rotates a soda firing every six weeks and the schedule is posted on the kiln-room whiteboard a month out.", "architecture", "personal", False,
     [("Geil downdraft", "tool"), ("soda", "concept"), ("reduction", "concept")],
     [("Geil downdraft", "soda", "APPLIES_TO"), ("Geil downdraft", "reduction", "APPLIES_TO")],
     "how is the Geil downdraft plumbed at the community studio and how often is a soda firing scheduled",
     "geil downdraft community soda reduction schedule six week rotation"),
    # --- 27 --- milestone
    ("First successful kintsugi repair on a broken Jun Kaneko bowl I had been sitting on for three years; the urushi lacquer cure took a full three weeks in the damp-box before the gold dust held properly.", "milestone", "personal", False,
     [("kintsugi", "method"), ("Jun Kaneko", "person"), ("urushi", "concept"), ("damp-box", "tool")],
     [("kintsugi", "urushi", "USES"), ("kintsugi", "damp-box", "USES")],
     "how did my first kintsugi repair on a Kaneko bowl go and how long was the urushi cure in the damp-box",
     "kintsugi jun kaneko bowl urushi lacquer cure damp box three week gold"),
    # --- 28 --- preference
    ("I prefer throwing Frost porcelain over Southern Ice for teabowls; Frost holds a crisper foot ring under trimming even though Southern Ice fires whiter and more translucent.", "preference", "personal", False,
     [("Frost porcelain", "concept"), ("Southern Ice", "concept"), ("teabowls", "concept"), ("foot ring", "concept")],
     [("Frost porcelain", "Southern Ice", "PREFERS"), ("foot ring", "Frost porcelain", "APPLIES_TO")],
     "which porcelain do I prefer for teabowls and what trimming property makes the trade-off worth it",
     "frost southern ice porcelain teabowl foot ring trim crisp translucent"),
    # --- 29 --- fact
    ("Toshiko Takaezu's closed-form vessels rattle a small pellet of clay inside when you turn them; I learned that detail the afternoon a collector let me handle one at a gallery reception.", "fact", "personal", False,
     [("Toshiko Takaezu", "person"), ("closed-form", "concept"), ("pellet", "concept")],
     [("pellet", "closed-form", "APPLIES_TO"), ("closed-form", "Toshiko Takaezu", "AUTHORED_BY")],
     "which sonic detail inside Takaezu's closed-form vessels did I first notice handling one at a gallery",
     "toshiko takaezu closed form pellet rattle gallery reception handle"),
    # --- 30 --- decision
    ("Stopped using Lucie Rie's sgraffito-through-manganese approach on the cone 6 line; the manganese fume in an electric kiln was harder to vent properly and I switched to an iron-saturate line for the dark passages instead.", "decision", "personal", False,
     [("Lucie Rie", "person"), ("sgraffito", "method"), ("manganese", "concept"), ("cone 6", "concept"), ("iron-saturate", "concept")],
     [("iron-saturate", "manganese", "REPLACES")],
     "which Lucie Rie decoration did I retire from the cone 6 line and what replaced the dark passages",
     "lucie rie sgraffito manganese cone 6 iron saturate electric fume vent"),
    # --- 31 --- architecture
    ("The nerikomi log is built from three coloured porcelain slabs laminated with a calligraphy-brush of slip, rested overnight under plastic, then cross-sectioned with a thin wire into two-millimetre inlays.", "architecture", "personal", False,
     [("nerikomi", "method"), ("porcelain", "concept"), ("calligraphy-brush", "tool"), ("wire", "tool")],
     [("nerikomi", "porcelain", "APPLIES_TO"), ("wire", "nerikomi", "USES")],
     "how is my nerikomi log built from coloured slabs and cross-sectioned into thin inlays",
     "nerikomi porcelain slab calligraphy brush slip wire cross section log"),
    # --- 32 --- problem
    ("The chun glaze ran off the rim and welded my cone 10 stoneware bowls to the shelf; I now wash the shelves with a fresh zircopax-kaolin kiln wash before every reduction firing and set a drip-catch bisque disc under thin rims.", "problem", "personal", False,
     [("chun", "concept"), ("cone 10 stoneware", "concept"), ("kiln wash", "concept"), ("zircopax-kaolin", "concept")],
     [("chun", "cone 10 stoneware", "APPLIES_TO"), ("kiln wash", "chun", "FIXES")],
     "how did I stop a runny chun from welding bowls to the shelf on cone 10 reductions",
     "chun cone 10 run shelf weld kiln wash zircopax kaolin drip disc"),
    # --- 33 --- reference
    ("Akira Satake's Asheville studio notes on iron-bearing slips convinced me to mix my own basalt slip from the local river silt; the chapter on reading fire colour on dark bodies is dog-eared at this point.", "reference", "personal", False,
     [("Akira Satake", "person"), ("Asheville", "place"), ("basalt slip", "concept"), ("river silt", "concept")],
     [("Akira Satake", "Asheville", "LIVES_IN"), ("basalt slip", "river silt", "USES")],
     "which Satake notes convinced me to mix a basalt slip from local river silt and which chapter stays dog-eared",
     "akira satake asheville basalt slip river silt iron dark fire colour"),
    # --- 34 --- decision
    ("Switched my stamping workflow to bisque-fired plaster stamps instead of the laser-cut acrylic I had been using; the plaster draws enough moisture out of the slip to release cleanly on the first pull every time.", "decision", "personal", False,
     [("stamping", "method"), ("plaster stamps", "tool"), ("laser-cut acrylic", "tool")],
     [("plaster stamps", "laser-cut acrylic", "REPLACES")],
     "which stamp material replaced laser-cut acrylic in my workflow and why does it release cleanly",
     "stamp plaster bisque laser cut acrylic slip release moisture draw"),
    # --- 35 --- milestone
    ("Got accepted to Adam Field's throwing intensive after three years on the waitlist; the focus on the one-pound teabowl with a pulled lip rewrote how I centre small volumes.", "milestone", "personal", False,
     [("Adam Field", "person"), ("throwing intensive", "event"), ("teabowl", "concept"), ("pulled lip", "method")],
     [("throwing intensive", "Adam Field", "AUTHORED_BY"), ("pulled lip", "teabowl", "APPLIES_TO")],
     "which Adam Field intensive did I finally clear the waitlist for and what one-pound form rewrote my centring",
     "adam field throwing intensive wait list teabowl one pound pulled lip"),
    # --- 36 --- architecture
    ("The slip-trailing tray setup parks four bulb syringes over a foam block at the wheel; each holds a different engobe, and I rotate them between pots so the slip never skins over mid-decoration.", "architecture", "personal", False,
     [("slip-trailing", "method"), ("bulb syringe", "tool"), ("engobe", "concept"), ("foam block", "tool")],
     [("slip-trailing", "bulb syringe", "USES"), ("engobe", "slip-trailing", "APPLIES_TO")],
     "how is my slip-trailing station laid out to keep four engobes from skinning between pots",
     "slip trailing bulb syringe engobe foam block wheel rotate skin"),
    # --- 37 --- preference
    ("I prefer a shino over a celadon on Southern Ice when the form has a lot of throwing rings; shino breaks on the ridges and records the gesture, while celadon pools smooth and erases the throwing.", "preference", "personal", False,
     [("shino", "concept"), ("celadon", "concept"), ("Southern Ice", "concept"), ("throwing rings", "concept")],
     [("shino", "celadon", "PREFERS"), ("shino", "throwing rings", "APPLIES_TO")],
     "which glaze do I prefer over celadon on Southern Ice when the pot has visible throwing rings",
     "shino celadon southern ice throwing ring break record gesture pool"),
    # --- 38 --- decision
    ("Chose a Skutt over a Paragon when I bought my first home kiln; the three-inch element groove and the Bartlett controller integration were the tie-breakers after a week of spec sheets.", "decision", "personal", False,
     [("Skutt", "tool"), ("Paragon", "tool"), ("Bartlett controller", "tool")],
     [("Skutt", "Paragon", "PREFERS"), ("Bartlett controller", "Skutt", "APPLIES_TO")],
     "which electric kiln did I pick over a Paragon for the first home studio and what tie-broke the decision",
     "skutt paragon home kiln bartlett controller element groove spec"),
    # --- 39 --- fact
    ("My local clay supplier pugs a house-blend cone 10 stoneware with twelve percent Grolleg porcelain mixed in; the added kaolin cleans up the colour response under celadon without sacrificing throw-ability.", "fact", "personal", False,
     [("cone 10 stoneware", "concept"), ("Grolleg porcelain", "concept"), ("celadon", "concept"), ("kaolin", "concept")],
     [("Grolleg porcelain", "cone 10 stoneware", "APPLIES_TO"), ("celadon", "kaolin", "RELATED_TO")],
     "what does my clay supplier blend into the cone 10 stoneware and what glaze response does the kaolin clean up",
     "cone 10 stoneware grolleg porcelain kaolin celadon house blend twelve"),
    # --- 40. noise ---
    ("The workshop radio has been stuck on the same classical station for six weeks and nobody remembers where the remote went after the last open house.", "fact", "noise", True, [], [], None, None),
    # --- 41 --- milestone
    ("Finally fired a clean ash glaze over the anagama wood kiln shoulders without the usual crawling; three coats of thinned slip under the glaze gave the ash something to bite into on the raw stoneware.", "milestone", "personal", False,
     [("ash glaze", "concept"), ("anagama wood kiln", "tool"), ("crawling", "error"), ("slip", "concept")],
     [("ash glaze", "anagama wood kiln", "APPLIES_TO"), ("slip", "crawling", "FIXES")],
     "how did I stop ash-glaze crawling on anagama shoulders and what slip prep made it hold",
     "ash glaze anagama wood kiln crawl slip three coat shoulder bite"),
    # --- 42 --- fact
    ("My faceting workflow cuts eight flat sides on a leather-hard cylinder with a Japanese wire tool; I then re-throw the inside to tension the walls back outward so the facets read crisp after bisque.", "fact", "personal", False,
     [("faceting", "method"), ("leather-hard", "concept"), ("Japanese wire tool", "tool"), ("bisque", "concept")],
     [("faceting", "Japanese wire tool", "USES"), ("faceting", "leather-hard", "APPLIES_TO")],
     "how does my faceting workflow keep cut sides crisp through bisque and which tool drives the cut",
     "faceting leather hard japanese wire tool bisque re throw tension"),
    # --- 43 --- decision
    ("Dropped the chun from the cone 10 rotation after the community Geil downdraft got inconsistent reduction; chun needs a steady cone 08 soak and the crew's new schedule couldn't guarantee one.", "decision", "personal", False,
     [("chun", "concept"), ("cone 10", "concept"), ("Geil downdraft", "tool"), ("cone 08", "concept")],
     [("chun", "Geil downdraft", "APPLIES_TO")],
     "why did I pull chun from the cone 10 rotation on the community Geil downdraft and what soak did it need",
     "chun cone 10 geil downdraft community cone 08 soak reduction steady"),
    # --- 44 --- preference
    ("For a forty-dollar production mug I prefer the Brent CXC over the Shimpo VL-Whisper; the CXC's torque under a six-pound ball lets me stop pulling and start trimming within a minute.", "preference", "personal", False,
     [("Brent CXC", "tool"), ("Shimpo VL-Whisper", "tool"), ("production mug", "concept")],
     [("Brent CXC", "Shimpo VL-Whisper", "PREFERS")],
     "which wheel do I prefer on a production mug run and which mechanical property drives the choice",
     "brent cxc shimpo vl whisper production mug torque six pound trim"),
    # --- 45 --- reference
    ("Jun Kaneko's massive dango sculptures at the Bemis Center are the scale reference I pull up whenever I start doubting the slow coil build; his notes on wall thickness at three inches calmed my own cracking anxiety.", "reference", "personal", False,
     [("Jun Kaneko", "person"), ("dango", "concept"), ("Bemis Center", "organization"), ("coil build", "method")],
     [("Jun Kaneko", "Bemis Center", "WORKS_AT"), ("coil build", "dango", "APPLIES_TO")],
     "which Kaneko reference steadies me on slow coil builds and what wall thickness note calmed my cracking fears",
     "jun kaneko dango bemis center coil build wall thickness three inch"),
    # --- 46 --- architecture
    ("The studio's ame glaze recipe sits between a tenmoku and an oribe on the iron-oxide axis; at cone 10 reduction it breaks amber on the edges and sinks glossy black in the wells, which makes it read as both at once.", "architecture", "personal", False,
     [("ame", "concept"), ("tenmoku", "concept"), ("oribe", "concept"), ("cone 10", "concept"), ("reduction", "concept")],
     [("ame", "tenmoku", "RELATED_TO"), ("ame", "oribe", "RELATED_TO")],
     "where does my ame glaze sit between tenmoku and oribe and how does it read under cone 10 reduction",
     "ame tenmoku oribe iron oxide cone 10 reduction amber edge well"),
    # --- 47 --- problem
    ("The Frost porcelain rims kept S-cracking on bisque 04; slowing the ramp below 400 Fahrenheit to sixty degrees per hour and compressing the rim twice at throwing closed the problem out.", "problem", "personal", False,
     [("Frost porcelain", "concept"), ("S-cracking", "error"), ("bisque 04", "concept"), ("400 Fahrenheit", "concept")],
     [("S-cracking", "Frost porcelain", "APPLIES_TO"), ("bisque 04", "S-cracking", "CAUSES")],
     "how did I stop S-cracks on Frost porcelain rims at bisque 04 and which ramp range was the culprit",
     "frost porcelain s crack bisque 04 400 ramp sixty degree compress rim"),
    # --- 48 --- fact
    ("Got a solo show booked at a regional gallery on the strength of the shino-and-sgraffito cups I threw at Watershed Maine last summer; the opening runs a full month and the studio calendar rearranges around the kiln schedule.", "fact", "personal", False,
     [("shino", "concept"), ("sgraffito", "method"), ("Watershed Maine", "organization"), ("solo show", "event")],
     [("solo show", "Watershed Maine", "APPLIES_TO"), ("shino", "sgraffito", "RELATED_TO")],
     "which Watershed-era body of work landed me a regional solo show and how long does the opening run",
     "shino sgraffito watershed maine solo show gallery regional month kiln"),
    # --- 49 --- decision
    ("Picked earthenware over stoneware for the children's workshop series; the cone 04 firing lets me send finished pots home inside a week, which stoneware's cone 10 turnaround could never support.", "decision", "personal", False,
     [("earthenware", "concept"), ("stoneware", "concept"), ("cone 04", "concept"), ("cone 10", "concept")],
     [("earthenware", "stoneware", "PREFERS"), ("cone 04", "earthenware", "APPLIES_TO")],
     "which clay body did I pick over stoneware for a kids' workshop and what turnaround window sealed the choice",
     "earthenware stoneware cone 04 10 children workshop turnaround week"),
    # --- 50 --- fact
    ("I prefer stoking the anagama wood kiln on the graveyard shift; the flame colour at the firebox reads cleaner in the dark and the crew conversation after midnight is where the real technique gets passed down.", "fact", "personal", False,
     [("anagama wood kiln", "tool"), ("stoking", "activity"), ("firebox", "concept")],
     [("stoking", "anagama wood kiln", "APPLIES_TO"), ("firebox", "anagama wood kiln", "HAS_PART")],
     "which anagama stoking shift do I prefer and what two things make the graveyard slot worth it",
     "anagama wood kiln stoking graveyard shift firebox flame colour crew"),
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
