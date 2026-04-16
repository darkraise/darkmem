"""One-off emitter for shared-base batch-203 — personal domain (high-end loose-leaf tea culture: oolong, pu'erh, Japanese greens, Chinese greens, white, dark, gongfu brewing, ware, roasting, aging, storage, regs, ceremony, water).

Writes 50 rows to data/v2/shared/batch_203.tmp.jsonl with ids shared-10101..10150.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_203.tmp.jsonl"
ID_OFFSET = 10100

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Switched the daily morning pot from Tieguanyin to a mid-roast Rou Gui; the Wuyi yancha mineral bite carries me through morning writing where the floral Tieguanyin reads too soft on an empty stomach.", "decision", "personal", False,
     [("Tieguanyin", "food"), ("Rou Gui", "food"), ("Wuyi yancha", "concept")],
     [("Rou Gui", "Tieguanyin", "REPLACES")],
     "which oolong took over the morning slot after Tieguanyin felt too light for empty-stomach sessions",
     "rou gui tieguanyin wuyi yancha morning oolong roast switch"),
    # --- 2 architecture ---
    ("The tea shelf sits on a three-tier humidity split: sheng pu'erh at 65 percent RH in a cedar cabinet, shou pu'erh at 70 percent in sealed crocks, and oolong vacuum-sealed in the fridge at 50 percent.", "architecture", "personal", False,
     [("sheng pu'erh", "concept"), ("shou pu'erh", "concept"), ("cedar cabinet", "tool"), ("oolong", "concept")],
     [("sheng pu'erh", "cedar cabinet", "APPLIES_TO")],
     "how is the home tea shelf split by humidity across sheng, shou and oolong categories",
     "sheng shou pu erh humidity cedar cabinet oolong fridge storage"),
    # --- 3 milestone ---
    ("Cracked open the 2008 Yiwu sheng cake on my birthday; twelve years of clean dry storage turned the raw bitterness into a honeyed camphor that the 2018 pressing still doesn't carry.", "milestone", "personal", False,
     [("2008 Yiwu", "food"), ("sheng", "concept"), ("2018", "date")],
     [],
     "which aged Yiwu cake finally came out and what flavour shift showed up after the dry-storage decade",
     "yiwu 2008 sheng aged honey camphor birthday cake dry storage"),
    # --- 4 fact ---
    ("Lao Banzhang gushu maocha goes for roughly 8000 RMB per kilo at the 2026 spring pressing, and the Menghai counterfeits still flood Taobao within a week of each new batch announcement.", "fact", "personal", False,
     [("Lao Banzhang", "place"), ("Menghai", "place"), ("gushu maocha", "concept"), ("2026", "date"), ("Taobao", "service")],
     [("Menghai", "Lao Banzhang", "RELATED_TO")],
     "what is the current Lao Banzhang gushu price and which counterfeit channel shows up fastest online",
     "lao banzhang gushu maocha price menghai counterfeit taobao 2026"),
    # --- 5 reference ---
    ("Bookmarked the Kyoto Uji gyokuro tasting essay by Sakamoto-sensei as my anchor reference for shaded-tea umami evaluation; it fixes the language I use for amino sweetness versus grassy astringency.", "reference", "personal", False,
     [("Kyoto Uji gyokuro", "food"), ("Sakamoto-sensei", "person")],
     [("Sakamoto-sensei", "Kyoto Uji gyokuro", "AUTHORED_BY")],
     "which tasting essay became my reference anchor for shaded Japanese tea umami language",
     "gyokuro kyoto uji sakamoto tasting essay umami reference"),
    # --- 6 preference ---
    ("A gaiwan over yixing clay for every first session with a new cake; the porcelain reveals the tea honestly while a clay pot flatters and hides the rough notes I actually want to judge.", "preference", "personal", False,
     [("gaiwan", "tool"), ("yixing clay", "tool"), ("clay pot", "tool")],
     [("gaiwan", "yixing clay", "PREFERS")],
     "which brewing vessel do I reach for on a first-session evaluation and why is clay benched",
     "gaiwan yixing first session porcelain honest clay flatter judge"),
    # --- 7 problem ---
    ("Over-roasted the Dancong session at 120 C for too long and the Mi Lan Xiang fruit collapsed into burnt sugar; cut the finishing roast to 90 C for twenty minutes and the honey-orchid came back.", "problem", "personal", False,
     [("Dancong", "food"), ("Mi Lan Xiang", "food"), ("120 C", "config"), ("90 C", "config")],
     [],
     "how did I recover the Mi Lan Xiang honey-orchid after the first roasting pass burnt the fruit out",
     "dancong mi lan xiang roast temperature honey orchid burnt recover"),
    # --- 8 decision ---
    ("Picked Da Hong Pao from the Zhengyan core zone over the Banyan belt for the gift set; the mineral rock-rhyme yanyun on the core-zone leaves justifies the four-times premium for a guest who already drinks Wuyi yancha.", "decision", "personal", False,
     [("Da Hong Pao", "food"), ("Zhengyan", "place"), ("Banyan", "place"), ("yanyun", "concept"), ("Wuyi yancha", "concept")],
     [("Zhengyan", "Banyan", "PREFERS")],
     "why did the gift set end up with Zhengyan core-zone Da Hong Pao instead of the cheaper Banyan belt leaves",
     "da hong pao zhengyan banyan yanyun rock rhyme gift wuyi core"),
    # --- 9 architecture ---
    ("The gongfu station layout runs water-kettle to gaiwan to cha hai to tasting cups in a straight left-to-right line; the fairness pitcher sits between the gaiwan and the cups so decant timing stays visible across the session.", "architecture", "personal", False,
     [("gongfu", "concept"), ("gaiwan", "tool"), ("cha hai", "tool"), ("fairness pitcher", "tool"), ("tasting cups", "tool")],
     [("cha hai", "fairness pitcher", "RELATED_TO")],
     "how is the gongfu station laid out so decant timing stays visible from kettle to cup",
     "gongfu station layout gaiwan cha hai fairness pitcher cup kettle"),
    # --- 10 noise ---
    ("The new neighbour's wind chime hits a flat B above the fourth-floor balcony every time the easterly picks up after sunset.", "fact", "noise", True, [], [], None, None),
    # --- 11 milestone ---
    ("Finished a ten-session vertical tasting of Bingdao sheng from 2015 through 2024; the 2017 pressing turned out to be the inflection year where the bitterness locks into the hui gan aftertaste cleanly.", "milestone", "personal", False,
     [("Bingdao", "place"), ("sheng", "concept"), ("2015", "date"), ("2024", "date"), ("2017", "date"), ("hui gan", "concept")],
     [],
     "which Bingdao vintage emerged as the inflection year in my ten-session vertical tasting",
     "bingdao sheng vertical tasting 2017 hui gan bitterness vintage"),
    # --- 12 fact ---
    ("Bai Hao Yinzhen from Fuding uses only the silver-needle bud with no leaf, hand-plucked between the Qingming and Guyu solar terms, and the spring-2024 grade commanded 2400 RMB per 500 grams at the farmgate.", "fact", "personal", False,
     [("Bai Hao Yinzhen", "food"), ("Fuding", "place"), ("Qingming", "event"), ("Guyu", "event")],
     [("Bai Hao Yinzhen", "Fuding", "LOCATED_IN")],
     "what plucking window and farmgate price defined the 2024 Fuding Bai Hao Yinzhen grade I tracked",
     "bai hao yinzhen fuding silver needle qingming guyu price 2024"),
    # --- 13 decision ---
    ("Dropped sencha from the rotating daily brewer slot in favour of houjicha in the afternoon; the lower caffeine from the roast profile lets me keep drinking past four pm without wrecking the sleep onset.", "decision", "personal", False,
     [("sencha", "food"), ("houjicha", "food"), ("caffeine", "concept")],
     [("houjicha", "sencha", "REPLACES")],
     "which Japanese green lost the afternoon slot to houjicha and what sleep trade-off drove the swap",
     "sencha houjicha afternoon caffeine roast sleep onset daily rotation"),
    # --- 14 architecture ---
    ("Water for gongfu sessions runs through a three-stage build: RO strip, then a remineralisation cartridge targeting 60 ppm TDS with calcium-to-magnesium at 2:1, then a final carbon polish for chlorine residue.", "architecture", "personal", False,
     [("RO strip", "method"), ("remineralisation cartridge", "tool"), ("TDS", "concept"), ("carbon polish", "method")],
     [("remineralisation cartridge", "RO strip", "APPLIES_TO")],
     "how is the gongfu brewing water built from RO strip back up to a target TDS and mineral ratio",
     "water ro remineralisation tds calcium magnesium gongfu carbon"),
    # --- 15 reference ---
    ("Kakuzo Okakura's The Book of Tea stays on the brewing bench as the cross-reference for the philosophical side of the ceremony; the chapter on the tea-room architecture anchors my thinking when I arrange the tea corner.", "reference", "personal", False,
     [("Kakuzo Okakura", "person"), ("The Book of Tea", "publication"), ("ceremony", "concept")],
     [("Kakuzo Okakura", "The Book of Tea", "AUTHORED_BY")],
     "which book anchors my thinking about tea-room arrangement and ceremony philosophy",
     "okakura book of tea ceremony philosophy reference tea room"),
    # --- 16 preference ---
    ("I take matcha koicha-thick for the first bowl of a quiet morning and usucha-thin only when I'm sharing a session; the koicha viscosity reads more meditative than the whisked foam of the thin preparation.", "preference", "personal", False,
     [("matcha", "food"), ("koicha", "method"), ("usucha", "method")],
     [("koicha", "usucha", "PREFERS")],
     "which matcha preparation do I reach for on a solo morning and which one is reserved for company",
     "matcha koicha usucha thick thin whisk morning share preference"),
    # --- 17 decision ---
    ("Chose a Tokoname kyusu with a ceramic mesh over a mesh-free shiboridashi for daily sencha; the side-handle ergonomics beat the shiboridashi wrist-twist after the third pour and the mesh catches the finest Uji dust.", "decision", "personal", False,
     [("Tokoname kyusu", "tool"), ("ceramic mesh", "tool"), ("shiboridashi", "tool"), ("sencha", "food"), ("Uji", "place")],
     [("Tokoname kyusu", "shiboridashi", "PREFERS")],
     "which teapot style replaced the shiboridashi for daily sencha and which ergonomic factor decided it",
     "tokoname kyusu shiboridashi sencha uji mesh side handle ergonomic"),
    # --- 18 architecture ---
    ("Session logging runs in a single leather notebook: left page lists water TDS, leaf weight in grams, pot volume in ml and each steep time in seconds; right page captures aroma, mouthfeel and hui gan in free prose.", "architecture", "personal", False,
     [("leather notebook", "tool"), ("TDS", "concept"), ("hui gan", "concept"), ("steep time", "concept")],
     [],
     "how is the two-page tea-session log laid out between quantitative parameters and tasting prose",
     "notebook session log tds leaf weight steep aroma hui gan"),
    # --- 19 milestone ---
    ("Finally got a Fujian-origin Shui Xian through the importer after two failed shipments; the 2024 spring batch landed in November and the roast had settled enough to brew straight out of the bag.", "milestone", "personal", False,
     [("Shui Xian", "food"), ("Fujian", "place"), ("2024", "date"), ("November", "date")],
     [("Shui Xian", "Fujian", "LOCATED_IN")],
     "which long-awaited Fujian oolong finally cleared the importer and what timing worked for the roast settle",
     "shui xian fujian 2024 importer roast settle oolong shipment"),
    # --- 20 fact ---
    ("EU MRL regulations on anthraquinone in tea sit at 0.02 mg per kilo and Chinese export lots to Germany get rejected routinely; Taiwanese oolongs pass more often because charcoal-baking substitutes for the firewood drying that creates the residue.", "fact", "personal", False,
     [("EU", "organization"), ("MRL", "concept"), ("anthraquinone", "concept"), ("Germany", "place"), ("Taiwanese oolongs", "concept")],
     [("EU", "anthraquinone", "APPLIES_TO")],
     "which EU residue limit keeps rejecting Chinese tea lots and why do Taiwanese oolongs clear it more often",
     "eu mrl anthraquinone germany chinese taiwanese oolong reject charcoal"),
    # --- 21 decision ---
    ("Booked Master Chen's yixing workshop over the cheaper Jingdezhen porcelain tour; a single zisha teapot shaped by a named master with traceable clay beats ten mass-press porcelain cups for what I actually brew.", "decision", "personal", False,
     [("Master Chen", "person"), ("yixing", "place"), ("Jingdezhen", "place"), ("zisha", "concept")],
     [("Master Chen", "yixing", "APPLIES_TO")],
     "which pottery workshop won the trip booking and what craft argument beat the cheaper porcelain tour",
     "master chen yixing zisha jingdezhen workshop teapot named traceable"),
    # --- 22 architecture ---
    ("The pu'erh aging room keeps a 25 C ceiling year-round with two small humidifiers on a hygrostat; each cake lives in breathable mianzhi paper inside a bamboo tong and the tongs sit on cedar shelving with finger-gap airflow.", "architecture", "personal", False,
     [("25 C", "config"), ("hygrostat", "tool"), ("mianzhi paper", "tool"), ("bamboo tong", "tool"), ("cedar shelving", "tool")],
     [("mianzhi paper", "bamboo tong", "APPLIES_TO")],
     "how is the pu'erh aging room set up for temperature, humidity and per-cake wrapping",
     "puerh aging room 25c hygrostat mianzhi bamboo tong cedar shelf"),
    # --- 23 problem ---
    ("A fridge-stored Tieguanyin picked up a faint onion-garlic off-note from a neighbouring kimchi jar; moved all vacuum-sealed greens to the mini-fridge reserved for tea and swapped the bag film to a triple-layer foil.", "problem", "personal", False,
     [("Tieguanyin", "food"), ("vacuum-sealed greens", "concept"), ("mini-fridge", "tool"), ("triple-layer foil", "tool")],
     [("triple-layer foil", "Tieguanyin", "APPLIES_TO")],
     "how did the onion-garlic taint on the Tieguanyin get traced and what storage change locked it out",
     "tieguanyin fridge onion garlic kimchi mini fridge foil vacuum"),
    # --- 24 reference ---
    ("Zhang Jinghong's Puer Tea: Ancient Caravans and Urban Chic is the standing reference on the sheng-versus-shou fermentation split and the Menghai factory history that shaped the shou recipe after 1973.", "reference", "personal", False,
     [("Zhang Jinghong", "person"), ("Puer Tea: Ancient Caravans and Urban Chic", "publication"), ("Menghai", "place"), ("1973", "date")],
     [("Zhang Jinghong", "Puer Tea: Ancient Caravans and Urban Chic", "AUTHORED_BY")],
     "which book grounds my understanding of the sheng versus shou fermentation split and Menghai history",
     "zhang jinghong puer ancient caravan sheng shou menghai 1973"),
    # --- 25 decision ---
    ("For the winter session rotation I picked a 2015 Xiaguan iron cake over another Dayi loose shou; the tight Xiaguan compression slows the aging curve and the smoke note pairs better with the cold-kitchen morning light.", "decision", "personal", False,
     [("Xiaguan", "place"), ("iron cake", "food"), ("Dayi", "organization"), ("shou", "concept"), ("2015", "date")],
     [("Xiaguan", "Dayi", "PREFERS")],
     "which winter sheng cake won the rotation over the Dayi shou and what compression factor tipped it",
     "xiaguan iron cake 2015 dayi shou compression winter smoke"),
    # --- 26 fact ---
    ("The Japanese Food Sanitation Act sets a 0.01 ppm ceiling on residual glyphosate in tencha destined for matcha; Uji cooperatives moved to mechanical weeding after the 2019 rejection wave and the premium koicha grade tightened around that shift.", "fact", "personal", False,
     [("Japanese Food Sanitation Act", "organization"), ("glyphosate", "concept"), ("tencha", "food"), ("matcha", "food"), ("Uji", "place"), ("2019", "date"), ("koicha", "method")],
     [("Japanese Food Sanitation Act", "tencha", "APPLIES_TO")],
     "which Japanese residue rule forced Uji tencha growers onto mechanical weeding after 2019",
     "japan food sanitation glyphosate tencha uji 2019 koicha matcha"),
    # --- 27 reference ---
    ("The travel tea kit packs into a single cloth roll: a 90 ml porcelain gaiwan, three 30 ml cups, a folding cha hai, a pair of tongs and a small scale; weight under 600 grams and it survives a carry-on without breakage.", "reference", "personal", False,
     [("travel tea kit", "tool"), ("gaiwan", "tool"), ("cha hai", "tool"), ("scale", "tool")],
     [],
     "what fits in the travel tea kit roll and how does the weight budget stay under the carry-on ceiling",
     "travel tea kit gaiwan cha hai cup scale cloth roll carry on"),
    # --- 28 decision ---
    ("A cold-brewed gyokuro overnight in the fridge beats hot-brewed for the August heatwave; the slow infusion keeps the amino sweetness and drops the astringency that a hot steep pulls out of the shaded leaf.", "decision", "personal", False,
     [("gyokuro", "food"), ("cold-brewed", "method"), ("hot-brewed", "method")],
     [("cold-brewed", "hot-brewed", "PREFERS")],
     "which gyokuro preparation wins the summer heatwave and what does the slow fridge infusion trade off",
     "gyokuro cold brew overnight heatwave amino astringency fridge"),
    # --- 29 milestone ---
    ("Logged my hundredth gongfu session with the Dancong flight in October; the notebook spread makes it easy to see which leaves moved position in the shortlist over six months of steady brewing.", "milestone", "personal", False,
     [("gongfu", "concept"), ("Dancong", "food"), ("October", "date"), ("notebook", "tool")],
     [],
     "which session count and leaf flight marked the hundredth gongfu entry in the tasting log",
     "gongfu session hundred dancong october notebook shortlist flight"),
    # --- 30 decision ---
    ("Replaced the general-purpose electric kettle with a Tetsubin iron kettle heated on an induction plate; the iron leaches trace iron into soft water and flattens the edge that the steel kettle left in delicate silver-needle infusions.", "decision", "personal", False,
     [("Tetsubin", "tool"), ("iron kettle", "tool"), ("induction plate", "tool"), ("electric kettle", "tool"), ("silver-needle", "food")],
     [("Tetsubin", "electric kettle", "REPLACES")],
     "which kettle replaced the electric one for silver-needle brewing and what water-chemistry shift justified it",
     "tetsubin iron kettle induction electric silver needle soft water"),
    # --- 31 architecture ---
    ("The tasting-flight protocol runs three leaves at matched 5 g into 100 ml gaiwans, same water, staggered 30-second initial steeps; the staggered start keeps me from chasing three timers at once while preserving the comparison.", "architecture", "personal", False,
     [("tasting-flight", "method"), ("gaiwan", "tool"), ("5 g", "config"), ("100 ml", "config"), ("30-second", "config")],
     [],
     "how does the three-leaf tasting flight stagger timers while keeping the brew parameters matched",
     "tasting flight 5g 100ml gaiwan 30 second stagger timer match"),
    # --- 32 decision ---
    ("The 2021 Liu Bao I bought turned out over-fermented with a wet-pile funk that never cleaned up; six months of dry-storage airing in the cedar cabinet at 60 percent RH brought it back to the earthy-betel-nut profile it was supposed to carry.", "decision", "personal", False,
     [("Liu Bao", "food"), ("2021", "date"), ("cedar cabinet", "tool"), ("betel-nut", "concept")],
     [("cedar cabinet", "Liu Bao", "FIXES")],
     "how did the 2021 Liu Bao recover the betel-nut profile after the wet-pile funk persisted on arrival",
     "liu bao 2021 wet pile funk cedar cabinet 60 rh betel nut"),
    # --- 33 fact ---
    ("Taiwanese high-mountain oolong from Lishan above 2000 metres carries a characteristic sweet-cream nose that disappears below 1600 metres; the altitude-driven cool-night metabolism is the traceable reason and the TFDA terroir labelling codifies the boundary.", "fact", "personal", False,
     [("Lishan", "place"), ("Taiwanese high-mountain oolong", "food"), ("TFDA", "organization"), ("2000 metres", "config"), ("1600 metres", "config")],
     [("Taiwanese high-mountain oolong", "Lishan", "LOCATED_IN")],
     "which altitude threshold on Lishan separates the sweet-cream high-mountain oolong from the lower grades",
     "lishan taiwanese high mountain oolong altitude tfda terroir sweet"),
    # --- 34 architecture ---
    ("The chawan storage rotates four bowls by season: a thin summer natsu-jawan for usucha, a deep winter fuyu-jawan for koicha, and two shoulder-season bowls for transitional tastings; each lives in a cloth-wrapped kiribako.", "architecture", "personal", False,
     [("chawan", "tool"), ("natsu-jawan", "tool"), ("fuyu-jawan", "tool"), ("usucha", "method"), ("koicha", "method"), ("kiribako", "tool")],
     [("natsu-jawan", "usucha", "APPLIES_TO"), ("fuyu-jawan", "koicha", "APPLIES_TO")],
     "how are the four seasonal chawan rotated across usucha and koicha preparations throughout the year",
     "chawan natsu fuyu jawan usucha koicha kiribako season rotate"),
    # --- 35 reference ---
    ("Bruce Rich's survey paper on fu zhuan Golden Flower Eurotium cristatum colonies is the standing source when a dark-tea vendor claims higher mao cha fermentation; the colony count and moisture curve figures anchor the authenticity check.", "reference", "personal", False,
     [("Bruce Rich", "person"), ("fu zhuan", "food"), ("Eurotium cristatum", "concept"), ("mao cha", "concept")],
     [("Bruce Rich", "fu zhuan", "AUTHORED_BY")],
     "which fu zhuan reference paper do I reach for when a dark-tea vendor claims elevated fermentation activity",
     "bruce rich fu zhuan eurotium cristatum mao cha golden flower"),
    # --- 36 decision ---
    ("Picked a Taiping Houkui over another Biluochun for the spring green slot; the broad bamboo-press leaf of the Houkui reads unique on the palate where Biluochun starts to blur with other Dong Ting greens after two cups.", "decision", "personal", False,
     [("Taiping Houkui", "food"), ("Biluochun", "food"), ("Dong Ting", "place")],
     [("Taiping Houkui", "Biluochun", "PREFERS")],
     "which Chinese green won the spring slot over Biluochun and what leaf signature pushed the choice",
     "taiping houkui biluochun dong ting spring green bamboo press"),
    # --- 37 milestone ---
    ("First successful seasoning of the new 120 ml Chaozhou clay pot after twenty-two Dancong sessions; the pot now carries the orchid ghost between brews and the pour stream is finally stable without a choke at the spout.", "milestone", "personal", False,
     [("Chaozhou", "place"), ("clay pot", "tool"), ("Dancong", "food"), ("120 ml", "config")],
     [("clay pot", "Chaozhou", "LOCATED_IN")],
     "after how many Dancong sessions did the Chaozhou pot reach a stable seasoning and clean pour",
     "chaozhou clay pot dancong 120ml seasoning orchid pour stable"),
    # --- 38 preference ---
    ("I prefer Longjing pan-fired by a named farmer in Meijiawu over the bigger West Lake cooperative grades; the smaller-batch hand-press leaves the chestnut note sharper and the grassy edge never turns vegetal.", "preference", "personal", False,
     [("Longjing", "food"), ("Meijiawu", "place"), ("West Lake", "place")],
     [("Meijiawu", "West Lake", "PREFERS")],
     "which Longjing grade do I reach for over the large-cooperative West Lake labels and what leaf quality drives it",
     "longjing meijiawu west lake pan fired chestnut grassy hand"),
    # --- 39 fact ---
    ("Tea-session timing runs on a split-focus phone timer: first steep 10 seconds, second 8, third 12, then progressive +5 second bumps per steep; the schedule holds across Wuyi yancha and most sheng pu'erh without re-learning a new rhythm.", "fact", "personal", False,
     [("split-focus phone timer", "tool"), ("Wuyi yancha", "concept"), ("sheng pu'erh", "concept")],
     [("sheng pu'erh", "Wuyi yancha", "RELATED_TO")],
     "how is the per-steep timing curve laid out so Wuyi yancha and sheng pu'erh share one session rhythm",
     "timer split focus steep 10 8 12 wuyi yancha sheng puerh"),
    # --- 40 decision ---
    ("Routed bulk orders through the Shenzhen forwarder rather than a Hong Kong broker for 2026; the Shenzhen chain clears mainland inspection faster and the import tax on pressed pu'erh cakes sits lower after the January rule update.", "decision", "personal", False,
     [("Shenzhen", "place"), ("Hong Kong", "place"), ("2026", "date"), ("January", "date"), ("pu'erh", "concept")],
     [("Shenzhen", "Hong Kong", "REPLACES")],
     "which forwarding route replaced the Hong Kong broker for 2026 bulk pu'erh orders and why",
     "shenzhen hong kong forwarder puerh bulk 2026 tax january"),
    # --- 41 fact ---
    ("Shou Mei grades from Fuding skip the needle-bud plucking and take larger leaves including stems, which drops the farmgate price to one-sixth of Bai Hao Yinzhen while keeping the white-tea character for heavy daily drinking.", "fact", "personal", False,
     [("Shou Mei", "food"), ("Fuding", "place"), ("Bai Hao Yinzhen", "food")],
     [("Shou Mei", "Fuding", "LOCATED_IN")],
     "why does Fuding Shou Mei sit around a sixth of Bai Hao Yinzhen pricing while still being a daily drinker",
     "shou mei fuding bai hao yinzhen leaf stem daily price grade"),
    # --- 42 problem ---
    ("A vendor claimed 1990s dry-storage Menghai sheng but the cake surface was suspiciously even and the wet leaf showed no aged-leather note; reverse-image search on the neifei matched a 2014 replica run and I returned the order.", "problem", "personal", False,
     [("Menghai", "place"), ("sheng", "concept"), ("neifei", "concept"), ("2014", "date")],
     [("neifei", "Menghai", "RELATED_TO")],
     "how did the fake 1990s Menghai sheng get caught and which visual tell confirmed the 2014 replica",
     "menghai 1990 sheng neifei 2014 replica reverse image fake"),
    # --- 43 noise ---
    ("The pigeon pair on the opposite balcony are still arguing about nesting material and the debate has moved from twigs to a found piece of pink ribbon.", "fact", "noise", True, [], [], None, None),
    # --- 44 milestone ---
    ("Completed the yearlong tea-master apprenticeship log with Tanaka-sensei in Kyoto last week; the final chaji signed off the temae choreography and I can now run a four-person formal ceremony without a cheat sheet.", "milestone", "personal", False,
     [("Tanaka-sensei", "person"), ("Kyoto", "place"), ("chaji", "event"), ("temae", "method")],
     [("Tanaka-sensei", "Kyoto", "APPLIES_TO")],
     "which apprenticeship milestone signed off the temae choreography for running a four-person chaji solo",
     "tanaka kyoto chaji temae apprenticeship year ceremony formal"),
    # --- 45 preference ---
    ("For the evening wind-down I reach for shou pu'erh over sheng; the mellow earthy body without the sheng bitterness-and-kuwei edge doesn't spike my heart rate the way a young raw cake tends to after ten pm.", "preference", "personal", False,
     [("shou pu'erh", "concept"), ("sheng", "concept"), ("kuwei", "concept")],
     [("shou pu'erh", "sheng", "PREFERS")],
     "which pu'erh style wins the evening wind-down slot over sheng and what physiological effect drives it",
     "shou sheng puerh evening kuwei heart rate mellow earthy"),
    # --- 46 architecture ---
    ("The tea-ware cleaning chain runs three passes: hot water rinse with no soap for clay, a mild bicarbonate wipe for porcelain stains, and a yearly sun-drying exposure for the bamboo cha ze and cha ze holder to kill any humidity mould.", "architecture", "personal", False,
     [("cha ze", "tool"), ("clay", "tool"), ("porcelain", "tool"), ("bicarbonate", "method"), ("bamboo", "concept")],
     [("bicarbonate", "porcelain", "APPLIES_TO")],
     "how is the tea-ware cleaning chain split across clay, porcelain and bamboo without cross-contaminating seasoning",
     "clay porcelain bicarbonate bamboo cha ze clean sun dry mould"),
    # --- 47 reference ---
    ("The China National Standard GB/T 22111 on geographical-indication pu'erh tea defines the Yunnan-origin boundary and the sun-dried maocha requirement; it is the legal anchor when a vendor labels a cake as pu'erh outside Yunnan.", "reference", "personal", False,
     [("China National Standard GB/T 22111", "publication"), ("pu'erh tea", "food"), ("Yunnan", "place"), ("maocha", "concept")],
     [("China National Standard GB/T 22111", "pu'erh tea", "APPLIES_TO")],
     "which China national standard legally fixes the Yunnan boundary and sun-dried maocha rule for pu'erh labelling",
     "gb t 22111 yunnan puerh maocha geographical indication standard"),
    # --- 48 decision ---
    ("Went with a direct buy from the Anxi farmer co-op for 2026 Tieguanyin spring instead of the Taipei reseller; the extra two weeks of shipping is worth the 40 percent price cut and a traceable batch number on the sealed pouch.", "decision", "personal", False,
     [("Anxi", "place"), ("Tieguanyin", "food"), ("Taipei", "place"), ("2026", "date")],
     [("Anxi", "Taipei", "PREFERS")],
     "which 2026 Tieguanyin sourcing route replaced the Taipei reseller and what price and traceability gains followed",
     "anxi tieguanyin 2026 taipei reseller direct farmer co op trace"),
    # --- 49 architecture ---
    ("Each new pu'erh cake gets a three-datapoint intake log the day it arrives: dry-leaf photo, 0.5 g test-steep notes at 95 C for 30 seconds, and the vendor neifei scan; the intake log lives in a private Obsidian vault cross-linked to the storage location.", "architecture", "personal", False,
     [("pu'erh", "concept"), ("neifei", "concept"), ("Obsidian", "tool"), ("95 C", "config")],
     [("Obsidian", "neifei", "APPLIES_TO")],
     "how is the three-datapoint intake log for a new pu'erh cake captured and linked to its storage location",
     "puerh intake cake photo steep 95c neifei obsidian storage"),
    # --- 50 milestone ---
    ("Hit the 200-cake pu'erh collection mark last month with a 2017 Nannuo sheng that rounded out the Xishuangbanna coverage; the full map now spans Lincang, Menghai, Yiwu, Bingdao, Nannuo and Lao Banzhang with at least three vintages each.", "milestone", "personal", False,
     [("2017", "date"), ("Nannuo", "place"), ("Xishuangbanna", "place"), ("Lincang", "place"), ("Menghai", "place"), ("Yiwu", "place"), ("Bingdao", "place"), ("Lao Banzhang", "place")],
     [("Nannuo", "Xishuangbanna", "RELATED_TO")],
     "which cake pushed the pu'erh collection past 200 and which Yunnan regions now have three-vintage coverage",
     "nannuo 2017 xishuangbanna lincang menghai yiwu bingdao banzhang"),
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
