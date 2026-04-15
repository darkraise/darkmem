"""One-off emitter for shared-base batch-065 — cross domain.

Slice: cooking and smart kitchen meets tech (recipe apps, sous-vide rigs, smart
ovens, scales, meal planning, kitchen home automations). Writes 50 rows to
data/v2/shared/batch_065.tmp.jsonl with ids shared-03201..03250. The main
session aggregates the tmp file into shared.jsonl after validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_065.tmp.jsonl"
ID_OFFSET = 3200

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the family recipe collection from Paprika 3 to a Notion database on 2026-02-14 because the shared-edit story across iPad and the kitchen iMac kept forking the brisket recipe.", "milestone", "cross", False,
     [("Paprika 3", "tool"), ("Notion", "tool"), ("2026-02-14", "date"), ("iPad", "infrastructure"), ("iMac", "infrastructure"), ("brisket", "food")],
     [("Notion", "Paprika 3", "REPLACES")],
     "when did the shared recipe library leave the Paprika app and why",
     "recipe library migration shared editing fork conflict tablet desktop"),
    # --- 2 ---
    ("Prefers the Anova Precision Cooker over the Joule for sous-vide pork belly because the Anova app keeps the bath log even when the iPhone falls off Wi-Fi mid-cook.", "preference", "cross", False,
     [("Anova Precision Cooker", "infrastructure"), ("Joule", "infrastructure"), ("pork belly", "food"), ("Anova", "service"), ("iPhone", "infrastructure")],
     [("Anova Precision Cooker", "Joule", "PREFERS")],
     "which immersion circulator wins for long sous-vide runs and why",
     "immersion circulator sous vide app log offline wifi drop preference"),
    # --- 3 ---
    ("The Acaia Pearl scale streams the morning espresso shot's flow curve over Bluetooth into Beanconqueror, and the curve finally explained why Tuesday's Ethiopian pull tasted so sour.", "fact", "cross", False,
     [("Acaia Pearl", "infrastructure"), ("Bluetooth", "protocol"), ("Beanconqueror", "tool"), ("Ethiopian", "food")],
     [("Acaia Pearl", "Beanconqueror", "COMMUNICATES_WITH"), ("Acaia Pearl", "Bluetooth", "USES")],
     "what tooling caught the sour shot on the Tuesday espresso pull",
     "connected coffee scale flow profile bluetooth tracking app espresso"),
    # --- 4 ---
    ("Replaced the paper meal-plan whiteboard with a Mealime subscription on 2026-01-08 because the auto-generated Instacart cart finally stopped Mei from buying duplicate cilantro every week.", "milestone", "cross", False,
     [("Mealime", "service"), ("2026-01-08", "date"), ("Instacart", "service"), ("Mei", "person"), ("cilantro", "food")],
     [("Mealime", "Instacart", "COMMUNICATES_WITH")],
     "when did the weekly meal plan move off of the whiteboard",
     "meal planning saas auto grocery cart duplicate ingredient avoidance"),
    # --- 5 ---
    ("The Combustion Predictive Thermometer beat the MEATER Block on the Christmas prime rib because Combustion's eight-sensor probe surfaced the carryover curve a full nine minutes before MEATER did.", "decision", "cross", False,
     [("Combustion Predictive Thermometer", "infrastructure"), ("MEATER Block", "infrastructure"), ("prime rib", "food"), ("Combustion", "organization")],
     [("Combustion Predictive Thermometer", "MEATER Block", "REPLACES")],
     "which wireless meat thermometer won the Christmas roast",
     "wireless meat probe predictive carryover curve roast comparison"),
    # --- 6. noise ---
    ("Hold on, I need to grab a sip of water.", "fact", "noise", True, [], [], None, None),
    # --- 7 ---
    ("The Home Assistant kitchen automation triggers the Shelly plug under the kettle at 06:45 every weekday because Excitement of cold-pour mornings finally outweighed the spousal complaints about counter clutter.", "architecture", "cross", False,
     [("Home Assistant", "platform"), ("Shelly", "infrastructure"), ("Excitement", "emotion")],
     [("Home Assistant", "Shelly", "CONFIGURES")],
     "how does the morning kettle actually get started before anyone walks in",
     "smart plug kettle schedule home automation morning routine trigger"),
    # --- 8 ---
    ("Prefers the Breville Joule Oven over the June Oven because the Joule's Air-fryer mode actually pulls the convection profile from the Breville cloud instead of needing a paid Yummly tier.", "preference", "cross", False,
     [("Breville Joule Oven", "infrastructure"), ("June Oven", "infrastructure"), ("Yummly", "service"), ("Breville", "organization")],
     [("Breville Joule Oven", "June Oven", "PREFERS")],
     "which connected countertop oven won the kitchen and why",
     "smart oven cloud profile air fry convection subscription tier"),
    # --- 9 ---
    ("The 2026-03-22 sourdough disaster traced back to the Brod & Taylor proofer holding 26C instead of the 24C the Home Assistant dashboard claimed because the BLE sensor's battery had drifted.", "problem", "cross", False,
     [("2026-03-22", "date"), ("sourdough", "food"), ("Brod & Taylor", "organization"), ("Home Assistant", "platform"), ("BLE", "protocol")],
     [("Home Assistant", "BLE", "USES")],
     "what caused the late-March sourdough loaf to flop badly",
     "proofer temperature drift bluetooth sensor battery dashboard mismatch"),
    # --- 10 ---
    ("Switched the recipe vault from Evernote to an Obsidian cookbook on 2026-02-28 because the Dataview plugin finally let me filter Samin Nosrat's salt-fat-acid-heat axes against the pantry inventory.", "decision", "cross", False,
     [("Evernote", "service"), ("Obsidian", "tool"), ("2026-02-28", "date"), ("Dataview", "library"), ("Samin Nosrat", "person")],
     [("Obsidian", "Evernote", "REPLACES"), ("Obsidian", "Dataview", "USES")],
     "when did the recipe notes move into the local Obsidian vault and why",
     "recipe notes migration plugin query filter cookbook author axis"),
    # --- 11 ---
    ("The Thermomix TM6's cookidoo subscription auto-pushed the Karen Martini risotto recipe to the device on 2026-04-02 the moment Mei added it to the weekly plan in Mealime.", "fact", "cross", False,
     [("Thermomix TM6", "infrastructure"), ("cookidoo", "service"), ("Karen Martini", "person"), ("risotto", "food"), ("2026-04-02", "date"), ("Mei", "person"), ("Mealime", "service")],
     [("cookidoo", "Thermomix TM6", "DEPLOYED_ON"), ("Mealime", "cookidoo", "COMMUNICATES_WITH")],
     "how did the risotto recipe land on the Thermomix without a manual sync",
     "guided cooking recipe push meal plan integration cookbook author"),
    # --- 12 ---
    ("Frustration peaked when the Drop Scale's app dropped the bread-flour tare twice during the brioche bake and Reinhart's BBA formula required restart from zero.", "problem", "cross", False,
     [("Frustration", "emotion"), ("Drop Scale", "infrastructure"), ("brioche", "food"), ("Reinhart", "person"), ("BBA", "publication")],
     [],
     "what kitchen scale issue ruined the weekend brioche attempt",
     "connected scale tare loss baker percentage bread formula restart"),
    # --- 13 ---
    ("The Whisk API replaced the home-grown grocery scraper on 2026-01-19 because Whisk normalized the Hellofresh produce names against my Tesco delivery slot in one round trip.", "milestone", "cross", False,
     [("Whisk", "api"), ("2026-01-19", "date"), ("Hellofresh", "service"), ("Tesco", "organization")],
     [("Whisk", "Hellofresh", "COMMUNICATES_WITH"), ("Whisk", "Tesco", "COMMUNICATES_WITH")],
     "when did the grocery normalization move to the Whisk API",
     "ingredient normalization grocery api meal kit delivery slot scrape"),
    # --- 14 ---
    ("The Bartesian replaced the Drinkworks Pod on the bar cart after Drinkworks shut down its capsule supply chain and the JavaScript dashboard for cocktail counts went offline overnight.", "decision", "cross", False,
     [("Bartesian", "infrastructure"), ("Drinkworks Pod", "infrastructure"), ("Drinkworks", "organization"), ("JavaScript", "language")],
     [("Bartesian", "Drinkworks Pod", "REPLACES")],
     "which capsule cocktail machine replaced the dead one and why",
     "cocktail capsule machine swap supply chain shutdown dashboard offline"),
    # --- 15 ---
    ("Prefers the Fellow Aiden brewer's app over the Ratio Eight because Aiden's profile editor lets me run a James Hoffmann-style ultimate v60 bloom directly from the phone.", "preference", "cross", False,
     [("Fellow Aiden", "infrastructure"), ("Ratio Eight", "infrastructure"), ("James Hoffmann", "person"), ("v60", "infrastructure")],
     [("Fellow Aiden", "Ratio Eight", "PREFERS")],
     "which connected drip brewer wins for custom pour profiles",
     "drip brewer profile editor ultimate v60 bloom recipe coffee app"),
    # --- 16 ---
    ("The KitchenAid Smart Oven plus the Yonomi Routine Director kicks the preheat at 17:30 every Wednesday because the meal-plan webhook from Mealime fires when Mei opens the fridge.", "architecture", "cross", False,
     [("KitchenAid", "organization"), ("Yonomi", "service"), ("Mealime", "service"), ("Mei", "person")],
     [("Yonomi", "KitchenAid", "CONFIGURES"), ("Mealime", "Yonomi", "COMMUNICATES_WITH")],
     "how does the oven preheat itself before the Wednesday cook",
     "smart oven preheat automation routine webhook meal plan trigger"),
    # --- 17 ---
    ("Curiosity led me down the Serious Eats J. Kenji López-Alt rabbit hole one Sunday and the resulting wok-burner CSV ended up driving a Grafana dashboard against the Inkbird IBT-26S thermometer.", "fact", "cross", False,
     [("Curiosity", "emotion"), ("Serious Eats", "publication"), ("J. Kenji López-Alt", "person"), ("CSV", "concept"), ("Grafana", "tool"), ("Inkbird IBT-26S", "infrastructure")],
     [("Grafana", "Inkbird IBT-26S", "USES")],
     "what ended up wired into Grafana after a Kenji wok rabbit hole",
     "wok burner data logging dashboard cookbook author thermometer rig"),
    # --- 18 ---
    ("The Ooni Volt 12 indoor pizza oven replaced the Roccbox on the counter once the Volt's Wi-Fi temperature curve started feeding into the Home Assistant pizza-night blueprint.", "decision", "cross", False,
     [("Ooni Volt 12", "infrastructure"), ("Roccbox", "infrastructure"), ("Home Assistant", "platform")],
     [("Ooni Volt 12", "Roccbox", "REPLACES"), ("Ooni Volt 12", "Home Assistant", "COMMUNICATES_WITH")],
     "which pizza oven took over the counter and what tipped the choice",
     "indoor pizza oven swap wifi telemetry automation blueprint integration"),
    # --- 19 ---
    ("Joy hit when the 2026-04-05 dinner party's beef cheek braise hit 88C exactly when the Combustion app's predictive curve said it would, even with eight people leaning over the Dutch oven.", "milestone", "cross", False,
     [("Joy", "emotion"), ("2026-04-05", "date"), ("beef cheek", "food"), ("Combustion", "organization"), ("Dutch oven", "infrastructure")],
     [],
     "when did the dinner-party braise actually nail the timing",
     "dinner party braise predictive thermometer timing dutch oven success"),
    # --- 20 ---
    ("Pre-fermented the 2026-03-15 kombucha batch on a TP-Link Kasa smart plug because Kasa's local API let Home Assistant cut power the moment the floating EC sensor crossed the brewer's threshold.", "architecture", "cross", False,
     [("2026-03-15", "date"), ("kombucha", "food"), ("TP-Link Kasa", "infrastructure"), ("Kasa", "api"), ("Home Assistant", "platform"), ("EC", "concept")],
     [("Home Assistant", "TP-Link Kasa", "CONFIGURES"), ("Home Assistant", "Kasa", "USES")],
     "how did the kombucha brew autocut at the right acidity",
     "fermentation cutoff smart plug local api conductivity sensor threshold"),
    # --- 21 ---
    ("Prefers AnyList over Reminders for the grocery list because AnyList's recipe import parses Smitten Kitchen Deb Perelman pages into ingredients without choking on the parenthetical tomato-paste swap.", "preference", "cross", False,
     [("AnyList", "tool"), ("Reminders", "tool"), ("Smitten Kitchen", "publication"), ("Deb Perelman", "person"), ("tomato-paste", "food")],
     [("AnyList", "Reminders", "PREFERS")],
     "which grocery list app handles recipe parsing better",
     "grocery list app recipe parser ingredient extraction parenthetical"),
    # --- 22 ---
    ("The Traeger Timberline 850's WiFire app replaced the cheap dual-probe Inkbird because the Timberline pellet-feed schedule actually closes the loop on smoke density during the brisket overnight cook.", "decision", "cross", False,
     [("Traeger Timberline 850", "infrastructure"), ("WiFire", "service"), ("Inkbird", "infrastructure"), ("brisket", "food")],
     [("Traeger Timberline 850", "Inkbird", "REPLACES")],
     "which smoker app finally closed the loop on overnight brisket",
     "pellet smoker app smoke density loop overnight brisket schedule"),
    # --- 23 ---
    ("Migrated the Tandoor Recipes self-hosted instance from a Synology Docker container to a Proxmox LXC on 2026-02-09 because the SQLite database kept locking when Mei imported a NYT Cooking PDF.", "milestone", "cross", False,
     [("Tandoor Recipes", "tool"), ("Synology", "infrastructure"), ("Docker", "platform"), ("Proxmox", "platform"), ("LXC", "infrastructure"), ("2026-02-09", "date"), ("SQLite", "database"), ("Mei", "person"), ("NYT Cooking", "service"), ("PDF", "concept")],
     [("Tandoor Recipes", "LXC", "DEPLOYED_ON"), ("Tandoor Recipes", "SQLite", "USES")],
     "when did the recipe server move from the NAS to a Proxmox LXC",
     "self hosted recipe manager migration database lock pdf import"),
    # --- 24 ---
    ("The Hestan Cue induction burner replaced the Breville Control Freak on the test-kitchen counter because Hestan's recipe-step handoff to the Bluetooth pan eliminated the manual temperature dial dance.", "decision", "cross", False,
     [("Hestan Cue", "infrastructure"), ("Breville Control Freak", "infrastructure"), ("Bluetooth", "protocol")],
     [("Hestan Cue", "Breville Control Freak", "REPLACES"), ("Hestan Cue", "Bluetooth", "USES")],
     "which precision induction burner won the counter and why",
     "induction burner swap recipe step handoff smart pan temperature dial"),
    # --- 25 ---
    ("The Brewfather mobile app finally replaced the homebrew BeerSmith desktop license on 2026-04-01 because Brewfather syncs the gravity reading from the iSpindel hydrometer over MQTT in real time.", "milestone", "cross", False,
     [("Brewfather", "service"), ("BeerSmith", "tool"), ("2026-04-01", "date"), ("iSpindel", "infrastructure"), ("MQTT", "protocol")],
     [("Brewfather", "BeerSmith", "REPLACES"), ("Brewfather", "MQTT", "USES")],
     "when did the homebrew planning app swap and what triggered it",
     "homebrew planner mobile sync floating hydrometer mqtt real time"),
    # --- 26 ---
    ("Relief washed in when the 2026-03-30 Easter ham's GE Profile smart oven actually held the 60C low-temp probe target through a four-hour church service, surfaced live on the Home Assistant card.", "milestone", "cross", False,
     [("Relief", "emotion"), ("2026-03-30", "date"), ("ham", "food"), ("GE Profile", "infrastructure"), ("Home Assistant", "platform")],
     [("GE Profile", "Home Assistant", "COMMUNICATES_WITH")],
     "what tool kept the Easter ham safe while everyone was at church",
     "smart oven low temp hold probe target remote dashboard holiday"),
    # --- 27 ---
    ("The Plum Wine Preserver kept the Coravin off the counter for nightly tastings because Plum's RFID bottle recognition logged the Burgundy pours into Vivino without any phone scan.", "architecture", "cross", False,
     [("Plum Wine Preserver", "infrastructure"), ("Coravin", "infrastructure"), ("RFID", "protocol"), ("Burgundy", "food"), ("Vivino", "service")],
     [("Plum Wine Preserver", "Vivino", "COMMUNICATES_WITH"), ("Plum Wine Preserver", "RFID", "USES")],
     "how do nightly wine pours end up logged without phone friction",
     "wine preserver bottle recognition tasting log integration cellar"),
    # --- 28 ---
    ("Eight Sleep's pod-side hydration nudge fed into the Home Assistant kitchen scene that pre-warms the Bonavita BV1900 brewer because morning Excitement is real and waiting for water is not.", "architecture", "cross", False,
     [("Eight Sleep", "service"), ("Home Assistant", "platform"), ("Bonavita BV1900", "infrastructure"), ("Excitement", "emotion")],
     [("Eight Sleep", "Home Assistant", "COMMUNICATES_WITH"), ("Home Assistant", "Bonavita BV1900", "CONFIGURES")],
     "how does the morning brewer warm itself before anyone is up",
     "wake signal kitchen scene brewer pre warm hydration nudge automation"),
    # --- 29 ---
    ("Prefers the Misen Carbon Steel skillet over the Made In version because Misen's heat-up curve, logged through a FLIR ONE thermal probe on the iPhone, hits sear temp twelve seconds faster.", "preference", "cross", False,
     [("Misen", "organization"), ("Carbon Steel", "concept"), ("Made In", "organization"), ("FLIR ONE", "infrastructure"), ("iPhone", "infrastructure")],
     [("Misen", "Made In", "PREFERS")],
     "which carbon steel pan won after the thermal logging test",
     "carbon steel pan comparison thermal probe heat curve sear temp"),
    # --- 30 ---
    ("The Inkbird IBT-26S BLE smoker probe replaced the original FireBoard 2 because FireBoard's cloud account suspended the free tier and the BLE-only Inkbird talks straight to ESPHome on the patio.", "decision", "cross", False,
     [("Inkbird IBT-26S", "infrastructure"), ("BLE", "protocol"), ("FireBoard 2", "infrastructure"), ("ESPHome", "platform")],
     [("Inkbird IBT-26S", "FireBoard 2", "REPLACES"), ("Inkbird IBT-26S", "ESPHome", "COMMUNICATES_WITH")],
     "which smoker probe took over once the FireBoard cloud tier got cut",
     "smoker probe swap cloud tier change bluetooth local broker patio"),
    # --- 31 ---
    ("The 2026-04-09 family pasta night used the Marcato Atlas hand-cranked roller because Mei refuses to let me wire the Philips Smart Pasta Maker into Home Assistant after last month's flour explosion.", "fact", "cross", False,
     [("2026-04-09", "date"), ("Marcato Atlas", "infrastructure"), ("Mei", "person"), ("Philips Smart Pasta Maker", "infrastructure"), ("Home Assistant", "platform")],
     [],
     "what pasta tool actually got used after the flour explosion",
     "pasta roller manual choice automation veto kitchen mishap household"),
    # --- 32 ---
    ("Prefers Ooni Connect over the Gozney Roccbox companion because Ooni Connect publishes the deck-temperature MQTT topic that the Home Assistant pizza-night dashboard subscribes to.", "preference", "cross", False,
     [("Ooni Connect", "service"), ("Gozney Roccbox", "infrastructure"), ("MQTT", "protocol"), ("Home Assistant", "platform")],
     [("Ooni Connect", "Gozney Roccbox", "PREFERS"), ("Ooni Connect", "MQTT", "USES")],
     "which pizza oven companion app integrates better with the home dashboard",
     "pizza oven companion app mqtt topic dashboard subscription deck temp"),
    # --- 33 ---
    ("The Modernist Cuisine PDF index lives in a Calibre library on the home server because Nathan Myhrvold's six-volume set wouldn't fit on the iPad Air without aggressive WebP recompression.", "architecture", "cross", False,
     [("Modernist Cuisine", "publication"), ("PDF", "concept"), ("Calibre", "tool"), ("Nathan Myhrvold", "person"), ("iPad Air", "infrastructure"), ("WebP", "concept")],
     [("Calibre", "Modernist Cuisine", "USES")],
     "where does the Modernist Cuisine PDF set actually live and why",
     "cookbook reference library ebook server volume size compression iPad"),
    # --- 34. noise ---
    ("Sorry, give me a minute to think about this.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The Hello Fresh Subscription canceled itself on 2026-03-12 because the OFX export from the bank flagged the auto-renew as a duplicate against the Mealime SaaS line item the same week.", "problem", "cross", False,
     [("Hello Fresh", "service"), ("2026-03-12", "date"), ("OFX", "concept"), ("Mealime", "service")],
     [],
     "what caused the meal kit subscription to cancel itself in mid-March",
     "meal kit auto renew duplicate detection bank export saas overlap"),
    # --- 36 ---
    ("The Sansaire Delta replaced the Polyscience CREATIVE on the deep-bath sous-vide setup because Sansaire's app actually exposes a Webhook trigger when the bath crosses 60C for the chicken thigh batch.", "decision", "cross", False,
     [("Sansaire Delta", "infrastructure"), ("Polyscience CREATIVE", "infrastructure"), ("Webhook", "concept"), ("chicken thigh", "food")],
     [("Sansaire Delta", "Polyscience CREATIVE", "REPLACES")],
     "which deep-bath sous-vide rig won and why",
     "deep bath sous vide rig swap webhook trigger chicken batch cook"),
    # --- 37 ---
    ("The 2026-04-12 Italian-night menu pulled the Marcella Hazan tomato butter sauce recipe via the Paprika 3 web clipper because Tandoor Recipes still doesn't parse the Essentials of Italian Cooking layout.", "fact", "cross", False,
     [("2026-04-12", "date"), ("Marcella Hazan", "person"), ("tomato butter", "food"), ("Paprika 3", "tool"), ("Tandoor Recipes", "tool"), ("Essentials of Italian Cooking", "publication")],
     [("Paprika 3", "Tandoor Recipes", "PREFERS")],
     "which clipper actually pulled the Marcella Hazan recipe and why",
     "recipe clipper layout parser cookbook source italian classic sauce"),
    # --- 38 ---
    ("Prefers the OXO Brew nine-cup over the Technivorm Moccamaster for the office stand-up because OXO's MQTT-bridged smart-plug profile spins up reliably on the Aqara FP2 presence trigger.", "preference", "cross", False,
     [("OXO Brew", "infrastructure"), ("Technivorm Moccamaster", "infrastructure"), ("MQTT", "protocol"), ("Aqara FP2", "infrastructure")],
     [("OXO Brew", "Technivorm Moccamaster", "PREFERS"), ("OXO Brew", "MQTT", "USES")],
     "which office coffee maker won the presence-triggered automation",
     "office coffee brewer presence trigger smart plug profile automation"),
    # --- 39 ---
    ("Anxiety spiked on 2026-03-08 when the SmartThings hub lost the Samsung Family Hub fridge and the inventory scan needed to drive the Mealime cart was offline for the Saturday grocery run.", "problem", "cross", False,
     [("Anxiety", "emotion"), ("2026-03-08", "date"), ("SmartThings", "platform"), ("Samsung Family Hub", "infrastructure"), ("Mealime", "service")],
     [("SmartThings", "Samsung Family Hub", "CONFIGURES")],
     "what knocked the smart fridge inventory offline that Saturday morning",
     "smart fridge inventory hub disconnect grocery cart pipeline failure"),
    # --- 40 ---
    ("The Wirecutter pick for the Vitamin Mix migrated to a Vitamix Ascent A3500 in 2026-04-03 because the Ascent's wireless connectivity reads the smart container preset directly from the SELF-DETECT chip.", "milestone", "cross", False,
     [("Wirecutter", "publication"), ("Vitamix Ascent A3500", "infrastructure"), ("2026-04-03", "date"), ("SELF-DETECT", "concept")],
     [],
     "when did the household blender finally upgrade and why",
     "blender upgrade self detect container preset wireless reader review"),
    # --- 41 ---
    ("The 2026-02-22 Lunar New Year dumpling marathon used a Google Sheet linked to the Apple Numbers iCloud share because the cousins on iPad and the cousins on Pixel both had to edit fillings at once.", "architecture", "cross", False,
     [("2026-02-22", "date"), ("Google Sheet", "service"), ("Apple Numbers", "tool"), ("iCloud", "service"), ("iPad", "infrastructure"), ("Pixel", "infrastructure")],
     [("Apple Numbers", "iCloud", "USES")],
     "how did the dumpling marathon track fillings across mixed devices",
     "shared spreadsheet cross platform edit dumpling marathon planning"),
    # --- 42 ---
    ("Disappointment hit when the Plant Jammer recipe-generator app shut down on 2026-01-30 because nothing else suggests pantry-aware substitutions with the same vector-similarity ranking.", "problem", "cross", False,
     [("Disappointment", "emotion"), ("Plant Jammer", "service"), ("2026-01-30", "date")],
     [],
     "what creative recipe tool died at the end of January and why it stings",
     "recipe generator shutdown pantry substitution vector similarity rank"),
    # --- 43 ---
    ("The Combustion Inc. cloud account replaced the local CSV log shuttling because their REST API now backfills the brisket cook curve directly into a Postgres table on the homelab.", "decision", "cross", False,
     [("Combustion Inc.", "organization"), ("CSV", "concept"), ("REST", "protocol"), ("brisket", "food"), ("Postgres", "database")],
     [("Combustion Inc.", "Postgres", "COMMUNICATES_WITH"), ("Combustion Inc.", "REST", "USES")],
     "what replaced the manual CSV exports for the smoker cook logs",
     "thermometer cloud rest api backfill database integration cook log"),
    # --- 44 ---
    ("Prefers Plate Joy over Eat This Much for the macro-tracked dinner plan because Plate Joy's grocery export to the AmazonFresh API actually respects the Whole Foods substitution rules.", "preference", "cross", False,
     [("Plate Joy", "service"), ("Eat This Much", "service"), ("AmazonFresh", "api"), ("Whole Foods", "organization")],
     [("Plate Joy", "Eat This Much", "PREFERS"), ("Plate Joy", "AmazonFresh", "COMMUNICATES_WITH")],
     "which macro-aware meal planner won and why on grocery integration",
     "macro tracking meal plan grocery api substitution rule integration"),
    # --- 45 ---
    ("The Dinnertime Notion template replaced the Trello kanban for weeknight cooking because the Notion view actually renders Salt Fat Acid Heat callouts from Samin Nosrat next to the timer block.", "decision", "cross", False,
     [("Notion", "tool"), ("Trello", "tool"), ("Salt Fat Acid Heat", "publication"), ("Samin Nosrat", "person")],
     [("Notion", "Trello", "REPLACES"), ("Salt Fat Acid Heat", "Samin Nosrat", "AUTHORED_BY")],
     "where does the weeknight cooking dashboard live now and why",
     "weeknight cooking dashboard template callout cookbook reference timer"),
    # --- 45 fix below: actually 46 ---
    # --- 46 ---
    ("The 2026-04-11 induction-cooktop swap put a GE Profile PHP9036 in for the Bosch 800 because the GE exposes a Matter-over-Thread element-level temperature read for the wok burner zone.", "milestone", "cross", False,
     [("2026-04-11", "date"), ("GE Profile PHP9036", "infrastructure"), ("Bosch 800", "infrastructure"), ("Matter", "protocol"), ("Thread", "protocol")],
     [("GE Profile PHP9036", "Bosch 800", "REPLACES"), ("GE Profile PHP9036", "Matter", "USES")],
     "when did the induction cooktop change and what protocol won",
     "induction cooktop swap matter over thread element temperature read"),
    # --- 47 ---
    ("Curiosity won the day when the Snapchat-style Tasty AR app rendered the Yotam Ottolenghi sweet potato chaat over the actual sheet pan and the kids agreed to try it.", "fact", "cross", False,
     [("Curiosity", "emotion"), ("Tasty", "service"), ("Yotam Ottolenghi", "person"), ("sweet potato", "food")],
     [],
     "what AR cooking app actually convinced the kids to try the new dish",
     "augmented reality recipe overlay cookbook author kid friendly meal"),
    # --- 48 ---
    ("The Crouton iOS recipe library replaced Mela on the bedside iPad because Crouton's Shortcuts integration lets Siri start the bread autolyse timer without unlocking the screen.", "decision", "cross", False,
     [("Crouton", "tool"), ("Mela", "tool"), ("iPad", "infrastructure"), ("Shortcuts", "tool"), ("Siri", "service"), ("autolyse", "concept")],
     [("Crouton", "Mela", "REPLACES"), ("Crouton", "Shortcuts", "USES")],
     "which iPad recipe app won for hands-free baking and why",
     "iOS recipe app shortcuts integration voice timer hands free baking"),
    # --- 49 ---
    ("The 2026-03-19 Diaspora Co. Pragati turmeric arrival triggered a Home Assistant notification because the Sahil Bloom newsletter mentioned the harvest date and an iCal event fired the order webhook.", "fact", "cross", False,
     [("2026-03-19", "date"), ("Diaspora Co.", "organization"), ("Pragati", "food"), ("Home Assistant", "platform"), ("Sahil Bloom", "person"), ("iCal", "concept")],
     [("Home Assistant", "iCal", "USES")],
     "what tipped off the spice arrival notification on March 19",
     "spice subscription harvest date calendar trigger webhook notification"),
    # --- 50 ---
    ("Prefers Eric Kim's NYT Cooking gochujang-glazed potatoes recipe over the Maangchi version because the NYT Cooking app's notes section threads Mei's salt-tolerance edits across the iPad and Pixel together.", "preference", "cross", False,
     [("Eric Kim", "person"), ("NYT Cooking", "service"), ("gochujang", "food"), ("Maangchi", "person"), ("Mei", "person"), ("iPad", "infrastructure"), ("Pixel", "infrastructure")],
     [("NYT Cooking", "Maangchi", "PREFERS")],
     "which gochujang potatoes recipe won and what tool feature decided it",
     "korean recipe app comparison notes thread cross device household salt"),
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
