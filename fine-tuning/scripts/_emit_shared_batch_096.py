"""One-off emitter for shared-base batch-096 — cross domain.

Slice: gardening meets tech (plant ID apps, soil sensors, smart watering,
Home Assistant grow-light integrations, hydroponics controllers, greenhouse
logging, garden planners, seed trackers, Obsidian/Notion journals, Bluetooth
pH/EC meters, grow-light spectrum data, named gardening YouTubers/podcasts).
Writes 50 rows to data/v2/shared/batch_096.tmp.jsonl with ids
shared-04751..04800. The main session aggregates the tmp file into
shared.jsonl after validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_096.tmp.jsonl"
ID_OFFSET = 4750

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Swapped PictureThis for PlantNet on the Pixel 9 because PlantNet's citizen-science reference set actually nailed the Quercus ilex cork oak sapling that PictureThis kept calling a holm maple.", "decision", "cross", False,
     [("PictureThis", "service"), ("PlantNet", "service"), ("Pixel 9", "infrastructure"), ("Quercus ilex", "concept")],
     [("PlantNet", "PictureThis", "REPLACES")],
     "which plant-id app took over for the backyard tree identification",
     "plant identification app citizen science oak sapling reference library"),
    # --- 2 ---
    ("The MiFlora Bluetooth soil sensor buried next to the Brandywine tomato feeds moisture and EC into Home Assistant through the passive BLE integration every five minutes.", "architecture", "cross", False,
     [("MiFlora", "infrastructure"), ("Brandywine", "concept"), ("Home Assistant", "platform"), ("BLE", "protocol")],
     [("MiFlora", "Home Assistant", "COMMUNICATES_WITH"), ("MiFlora", "BLE", "USES")],
     "how does the tomato bed's moisture reading reach the dashboard",
     "bluetooth soil probe passive integration dashboard sensor heirloom bed"),
    # --- 3 ---
    ("Rachio 3 replaced the Hunter Hydrawise controller on the front-yard drip zones on 2026-03-22 because Rachio's flow meter caught the Zone 4 mainline leak the Hydrawise schedule kept ignoring.", "decision", "cross", False,
     [("Rachio 3", "infrastructure"), ("Hunter Hydrawise", "infrastructure"), ("2026-03-22", "date")],
     [("Rachio 3", "Hunter Hydrawise", "REPLACES")],
     "when did the front-yard irrigation swap controllers and why",
     "smart irrigation controller swap flow meter leak detection drip zone"),
    # --- 4 ---
    ("Prefers the AC Infinity Controller 69 over the TrolMaster Hydro-X for the 2x4 grow tent because the Controller 69 ramps the inline fan PWM without needing the TrolMaster's add-on module.", "preference", "cross", False,
     [("AC Infinity Controller 69", "infrastructure"), ("TrolMaster", "organization"), ("Hydro-X", "infrastructure"), ("PWM", "protocol")],
     [("AC Infinity Controller 69", "Hydro-X", "PREFERS")],
     "which grow-tent controller wins for the small tent and what's the reason",
     "inline fan PWM ramp grow tent controller module dependency tent"),
    # --- 5 ---
    ("The Ecowitt GW2000 greenhouse gateway logs air temp, humidity, and par value into InfluxDB every minute so Grafana can overlay the Mars Hydro TS1000 spectrum curve against leaf-temp delta.", "architecture", "cross", False,
     [("Ecowitt", "organization"), ("GW2000", "infrastructure"), ("InfluxDB", "database"), ("Grafana", "service"), ("Mars Hydro", "organization"), ("TS1000", "infrastructure")],
     [("GW2000", "InfluxDB", "COMMUNICATES_WITH"), ("Grafana", "InfluxDB", "USES")],
     "how does the greenhouse climate pipeline get from sensors to dashboards",
     "greenhouse gateway timeseries ingestion grafana overlay spectrum leaf delta"),
    # --- 6. noise ---
    ("Sorry, what were you saying again?", "fact", "noise", True, [], [], None, None),
    # --- 7 ---
    ("Moved the seed inventory from a Google Sheet to Hortisketch on 2026-02-09 because Hortisketch's succession-planting timeline could actually chain the Provider bush bean sowings every 14 days.", "milestone", "cross", False,
     [("Google Sheet", "service"), ("Hortisketch", "tool"), ("2026-02-09", "date"), ("Provider", "concept")],
     [("Hortisketch", "Google Sheet", "REPLACES")],
     "when did the seed plan move off the spreadsheet and why",
     "seed inventory migration succession planting bean variety timeline"),
    # --- 8 ---
    ("The GrowVeg garden planner caught a brassica-family rotation violation in the 2026 plan that I would have run right into had I just eyeballed last year's Obsidian bed map.", "fact", "cross", False,
     [("GrowVeg", "tool"), ("Obsidian", "tool")],
     [("GrowVeg", "Obsidian", "IMPROVES_ON")],
     "what caught the crop-rotation mistake in the 2026 garden plan",
     "crop rotation violation brassica family planner bed map check"),
    # --- 9 ---
    ("The Seek by iNaturalist app replaced PictureThis for wild-foraging walks because Seek's offline taxonomy pack worked in the backcountry ravine where PictureThis demanded a data connection.", "decision", "cross", False,
     [("Seek", "service"), ("iNaturalist", "service"), ("PictureThis", "service")],
     [("Seek", "PictureThis", "REPLACES")],
     "which plant-id tool wins for offline foraging walks",
     "offline taxonomy pack foraging no signal plant identification backcountry"),
    # --- 10 ---
    ("The TrolMaster Hydro-X handles the flower-tent CO2 PPFD ramp because the Climate module integrates directly with the Titan Controls CO2 generator on the 2026-01-15 build.", "architecture", "cross", False,
     [("TrolMaster", "organization"), ("Hydro-X", "infrastructure"), ("CO2", "concept"), ("PPFD", "concept"), ("Titan Controls", "organization"), ("2026-01-15", "date")],
     [("Hydro-X", "Titan Controls", "COMMUNICATES_WITH")],
     "how does the flower tent manage CO2 dosing against light intensity",
     "climate controller CO2 generator integration flower tent module build"),
    # --- 11 ---
    ("An Apera PC60 Bluetooth pH/EC meter replaced the cheap three-in-one probe on 2026-03-01 because the three-in-one was drifting half a pH unit against the 7.00 Apera calibration solution.", "decision", "cross", False,
     [("Apera PC60", "infrastructure"), ("Bluetooth", "protocol"), ("2026-03-01", "date"), ("Apera", "organization")],
     [("Apera PC60", "Bluetooth", "USES")],
     "when did the nutrient-solution meter get upgraded and why",
     "pH EC meter upgrade calibration drift nutrient solution bluetooth probe"),
    # --- 12 ---
    ("The garden journal template in Obsidian replaced the Notion kanban on 2026-02-18 because the Obsidian Dataview queries could cross-link the Rutgers tomato bed to the 2025 harvest totals.", "decision", "cross", False,
     [("Obsidian", "tool"), ("Notion", "tool"), ("Dataview", "tool"), ("2026-02-18", "date"), ("Rutgers", "concept")],
     [("Obsidian", "Notion", "REPLACES"), ("Obsidian", "Dataview", "USES")],
     "when did the garden journal leave Notion for a local markdown vault",
     "garden journal migration markdown vault dataview cross link harvest totals"),
    # --- 13 ---
    ("Frustration set in when the Rachio 3 skipped the 2026-04-03 watering window because the Skip Weather forecast over-weighted a 40% rain chance that dropped nothing on the raised beds.", "problem", "cross", False,
     [("Frustration", "emotion"), ("Rachio 3", "infrastructure"), ("2026-04-03", "date"), ("Skip Weather", "concept")],
     [],
     "what went wrong with the smart irrigation on the first warm April day",
     "skip weather false positive rain forecast missed watering raised beds"),
    # --- 14 ---
    ("The Mars Hydro FC-E4800 replaced the old HLG 260XL over the veg tent because the FC-E4800's 2.8 umol/J efficacy actually pencils out on the kWh bill for the 4x4 footprint.", "decision", "cross", False,
     [("Mars Hydro", "organization"), ("FC-E4800", "infrastructure"), ("HLG 260XL", "infrastructure")],
     [("FC-E4800", "HLG 260XL", "REPLACES")],
     "which grow light took over the veg tent and why",
     "grow light upgrade efficacy umol per joule kwh pencil veg tent"),
    # --- 15 ---
    ("Prefers Home Assistant automations for grow-light schedules over the Controller 69's on-board timer because HA can dim the Mars Hydro TS1000 in response to the Ecowitt PAR reading.", "preference", "cross", False,
     [("Home Assistant", "platform"), ("Controller 69", "infrastructure"), ("Mars Hydro", "organization"), ("TS1000", "infrastructure"), ("Ecowitt", "organization"), ("PAR", "concept")],
     [("Home Assistant", "Controller 69", "PREFERS")],
     "which scheduler wins for grow-light timing and what it reacts to",
     "automation platform grow light schedule PAR reading dimming response"),
    # --- 16 ---
    ("Epic Gardening's 2026-02-20 podcast episode on the no-till market garden tipped me to the Neversink Farms crop plan template that Hortisketch can import as a CSV.", "reference", "cross", False,
     [("Epic Gardening", "publication"), ("2026-02-20", "date"), ("Neversink Farms", "organization"), ("Hortisketch", "tool"), ("CSV", "concept")],
     [("Hortisketch", "CSV", "USES")],
     "which podcast episode unlocked the market-garden crop plan import",
     "market garden crop plan csv import no till podcast episode template"),
    # --- 17 ---
    ("The hydroponics reservoir on the TrolMaster setup throws an alarm when the Bluelab Guardian EC reading breaches 2.4 mS/cm because the Charlie pepper stops uptaking past that point.", "fact", "cross", False,
     [("TrolMaster", "organization"), ("Bluelab Guardian", "infrastructure"), ("Charlie", "concept")],
     [("TrolMaster", "Bluelab Guardian", "COMMUNICATES_WITH")],
     "when does the nutrient alarm fire on the pepper reservoir",
     "hydroponic reservoir EC alarm threshold pepper variety uptake limit"),
    # --- 18 ---
    ("The MiFlora readings in Home Assistant replaced the finger-in-the-dirt check for the dwarf fig because the moisture trend over 48 hours caught the micro-drought the eye test kept missing.", "decision", "cross", False,
     [("MiFlora", "infrastructure"), ("Home Assistant", "platform")],
     [("MiFlora", "Home Assistant", "DEPLOYED_ON")],
     "why did the dwarf fig's watering switch from a touch test to a sensor",
     "moisture trend sensor micro drought fig tree touch test replacement"),
    # --- 19 ---
    ("Built a Grafana dashboard for the greenhouse that overlays the Ecowitt WH51 soil probe, the Sonoff SNZB-02 air temp, and the Mars Hydro TS1000 schedule on a single 24-hour axis.", "architecture", "cross", False,
     [("Grafana", "service"), ("Ecowitt", "organization"), ("WH51", "infrastructure"), ("Sonoff", "organization"), ("SNZB-02", "infrastructure"), ("Mars Hydro", "organization"), ("TS1000", "infrastructure")],
     [("Grafana", "WH51", "USES"), ("Grafana", "SNZB-02", "USES")],
     "how is the greenhouse climate visualized across sensors and lights",
     "greenhouse dashboard soil probe air temp grow light schedule overlay"),
    # --- 20 ---
    ("The GrowVeg frost-date import for 2026 pulled the wrong NOAA station until I manually set the Brattleboro coordinates because the default fell back to a coastal station 90 miles east.", "problem", "cross", False,
     [("GrowVeg", "tool"), ("NOAA", "organization"), ("Brattleboro", "place")],
     [("GrowVeg", "NOAA", "USES")],
     "what went wrong with the 2026 frost-date import in the garden planner",
     "frost date import weather station fallback wrong coordinates manual override"),
    # --- 21 ---
    ("Kevin Espiritu's 2026-03-08 YouTube tour of the Utah homestead mentioned the Birdies raised-bed modular kit I ended up buying for the backyard rebuild.", "reference", "cross", False,
     [("Kevin Espiritu", "person"), ("2026-03-08", "date"), ("Utah", "place"), ("Birdies", "organization")],
     [],
     "which YouTuber's homestead tour sold me on the modular raised-bed kit",
     "youtube homestead tour raised bed kit modular recommendation gardener"),
    # --- 22 ---
    ("Excitement hit when the ESPHome firmware on the Sonoff NSPanel finally let me swap grow-light profiles from the kitchen wall tablet without opening the Home Assistant app.", "milestone", "cross", False,
     [("Excitement", "emotion"), ("ESPHome", "platform"), ("Sonoff", "organization"), ("NSPanel", "infrastructure"), ("Home Assistant", "platform")],
     [("ESPHome", "NSPanel", "DEPLOYED_ON")],
     "when did the wall-tablet grow-light control finally come together",
     "esphome firmware wall tablet profile swap kitchen grow light control"),
    # --- 23 ---
    ("The Charles Dowding no-dig planner spreadsheet replaced my GrowVeg subscription for 2027 because the Dowding template respects the compost-mulch layer and GrowVeg assumes tilling.", "decision", "cross", False,
     [("Charles Dowding", "person"), ("GrowVeg", "tool")],
     [],
     "which garden planner took over from GrowVeg and why",
     "no dig planner spreadsheet compost mulch layer template tilling assumption"),
    # --- 24 ---
    ("The Ecowitt GW2000 replaced an older Acurite hub on 2025-12-30 because the Ecowitt JSON push endpoint lands in Home Assistant without the cloud relay the Acurite required.", "decision", "cross", False,
     [("Ecowitt", "organization"), ("GW2000", "infrastructure"), ("Acurite", "organization"), ("2025-12-30", "date"), ("JSON", "concept"), ("Home Assistant", "platform")],
     [("GW2000", "Acurite", "REPLACES"), ("GW2000", "Home Assistant", "COMMUNICATES_WITH")],
     "when did the weather gateway swap and what local endpoint unlocked it",
     "weather gateway migration local json push cloud relay hub replacement"),
    # --- 25 ---
    ("Joe Gardener's 2026-02-28 episode on biochar inoculation prompted the char-loading log I now keep in Notion with dated bucket batches and rye-based inoculant ratios.", "reference", "cross", False,
     [("Joe Gardener", "publication"), ("2026-02-28", "date"), ("Notion", "tool")],
     [],
     "which podcast started the biochar-batch log in Notion",
     "biochar inoculation log dated batch inoculant ratio podcast episode"),
    # --- 26 ---
    ("The Rachio 3 Hyperlocal Weather Intelligence replaced the stock NOAA forecast after I ran a month of side-by-side logs against a Davis Vantage Vue in the backyard.", "decision", "cross", False,
     [("Rachio 3", "infrastructure"), ("NOAA", "organization"), ("Davis Vantage Vue", "infrastructure")],
     [("Rachio 3", "NOAA", "IMPROVES_ON")],
     "which forecast source won for the irrigation controller and how it was verified",
     "hyperlocal forecast evaluation side by side weather station backyard log"),
    # --- 27 ---
    ("The Xiaomi MiFlora v2 sensors get a CR2032 battery swap every six months because the Home Assistant BLE proxy reports the battery percentage drop against the Theengs Gateway log.", "architecture", "cross", False,
     [("MiFlora", "infrastructure"), ("CR2032", "infrastructure"), ("Home Assistant", "platform"), ("BLE", "protocol"), ("Theengs Gateway", "tool")],
     [("Home Assistant", "Theengs Gateway", "USES"), ("Theengs Gateway", "BLE", "USES")],
     "how is the soil-sensor battery replacement actually scheduled",
     "soil sensor battery swap BLE proxy gateway percentage drop schedule"),
    # --- 28 ---
    ("The Hortisketch 2026 plan pulls companion-planting constraints from a Notion database that maps the Farmer's Almanac pairings to actual bed geometry.", "architecture", "cross", False,
     [("Hortisketch", "tool"), ("Notion", "tool"), ("Farmer's Almanac", "publication")],
     [("Hortisketch", "Notion", "USES")],
     "how do companion-planting rules feed into the garden layout",
     "companion planting database bed geometry pairings almanac integration"),
    # --- 29 ---
    ("Regret hit when the 2026-03-15 hailstorm destroyed the Mittoider Frenzy pepper starts because I hadn't wired the Ecowitt WH40 rain alert to trigger the Ratchet-arm cover on the coldframe.", "problem", "cross", False,
     [("Regret", "emotion"), ("2026-03-15", "date"), ("Mittoider Frenzy", "concept"), ("Ecowitt", "organization"), ("WH40", "infrastructure")],
     [],
     "what went wrong on the mid-March hail event for the pepper starts",
     "hail event pepper starts cover automation miss rain gauge alert"),
    # --- 30 ---
    ("The AC Infinity Controller 69 replaced an Inkbird ITC-308 on the seed-starting heat mat because the Controller 69 ramps soil temp against VPD instead of just a single setpoint.", "decision", "cross", False,
     [("AC Infinity Controller 69", "infrastructure"), ("Inkbird", "organization"), ("ITC-308", "infrastructure"), ("VPD", "concept")],
     [("AC Infinity Controller 69", "ITC-308", "REPLACES")],
     "what controller took over for the heat-mat seed starting",
     "heat mat controller upgrade VPD setpoint ramp seed starting thermostat"),
    # --- 31 ---
    ("Prefers the Haxnicks Seed Sprouter app's germination log over a spreadsheet because the app captures the Epsom Wonder lettuce seed packet barcode directly into the dated entry.", "preference", "cross", False,
     [("Haxnicks", "organization"), ("Epsom Wonder", "concept")],
     [],
     "which seed tracker wins for keeping germination notes tidy",
     "seed tracker germination log barcode capture packet lettuce variety"),
    # --- 32 ---
    ("Hydrawise's wind-skip threshold on the side-yard spray zones still beats Rachio's on gusty days because the Hunter controller polls Davis Vantage data every fifteen minutes instead of hourly.", "fact", "cross", False,
     [("Hydrawise", "infrastructure"), ("Rachio", "organization"), ("Hunter", "organization"), ("Davis Vantage", "infrastructure")],
     [("Hydrawise", "Rachio", "IMPROVES_ON")],
     "which controller wins on wind-skip responsiveness for the spray zones",
     "wind skip threshold polling cadence weather station spray zone irrigation"),
    # --- 33 ---
    ("The Mars Hydro TS1000 spectrum data showed a 660nm peak aligned with the flower-trigger window so the 2026-03-05 transition night was set to a 12-hour Home Assistant automation.", "fact", "cross", False,
     [("Mars Hydro", "organization"), ("TS1000", "infrastructure"), ("2026-03-05", "date"), ("Home Assistant", "platform")],
     [("TS1000", "Home Assistant", "CONFIGURES")],
     "how was the flower-trigger photoperiod decided for the grow tent",
     "grow light spectrum red peak photoperiod transition flower trigger"),
    # --- 34. noise ---
    ("Let me grab a glass of water real quick.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The Obsidian garden-journal template from the PARA-Garden community replaced my ad-hoc daily notes on 2026-01-10 because the template pre-populates weather, pest, and bed-yield front matter.", "milestone", "cross", False,
     [("Obsidian", "tool"), ("PARA-Garden", "project"), ("2026-01-10", "date")],
     [("Obsidian", "PARA-Garden", "USES")],
     "when did the daily garden notes move to a structured template",
     "garden journal template front matter daily notes structure community"),
    # --- 36 ---
    ("A grow-light spectrum comparison between the HLG 320XL and the Spider Farmer SF-4000 used the UPRtek MK350N handheld spectrometer to log micromole output per cubic foot.", "fact", "cross", False,
     [("HLG 320XL", "infrastructure"), ("Spider Farmer", "organization"), ("SF-4000", "infrastructure"), ("UPRtek", "organization"), ("MK350N", "infrastructure")],
     [("MK350N", "SF-4000", "APPLIES_TO"), ("MK350N", "HLG 320XL", "APPLIES_TO")],
     "which spectrometer backed the grow-light spectrum head-to-head",
     "spectrometer handheld grow light comparison micromole cubic foot test"),
    # --- 37 ---
    ("The Apera PC60 replaced a Hanna HI98107 pH pen on 2026-02-12 because the Hanna kept losing calibration in the TrolMaster reservoir whenever the Titan CO2 dose raised the carbonate buffer.", "decision", "cross", False,
     [("Apera PC60", "infrastructure"), ("Hanna", "organization"), ("HI98107", "infrastructure"), ("2026-02-12", "date"), ("TrolMaster", "organization"), ("Titan", "organization")],
     [("Apera PC60", "HI98107", "REPLACES")],
     "when did the pH pen swap happen and what was breaking the old one",
     "pH pen swap calibration loss carbonate buffer CO2 dose reservoir"),
    # --- 38 ---
    ("Triangle Gardener's 2026-02-03 YouTube interview with the Maryland extension agent mentioned the Cover Crop Chart spreadsheet from SARE that I loaded into the Hortisketch rotation notes.", "reference", "cross", False,
     [("Triangle Gardener", "publication"), ("2026-02-03", "date"), ("Maryland", "place"), ("SARE", "organization"), ("Hortisketch", "tool")],
     [("Hortisketch", "SARE", "USES")],
     "which interview led to the cover-crop chart getting imported into the planner",
     "cover crop chart extension interview rotation notes spreadsheet import"),
    # --- 39 ---
    ("Pride surged when the Home Assistant dashboard finally showed all twelve MiFlora sensors, the GW2000 weather, the Rachio zones, and the AC Infinity tents on a single Lovelace view.", "milestone", "cross", False,
     [("Pride", "emotion"), ("Home Assistant", "platform"), ("MiFlora", "infrastructure"), ("GW2000", "infrastructure"), ("Rachio", "organization"), ("AC Infinity", "organization"), ("Lovelace", "tool")],
     [("Lovelace", "Home Assistant", "IS_A")],
     "when did the whole-garden dashboard finally come together on one screen",
     "lovelace dashboard unified sensors weather irrigation tents single view"),
    # --- 40 ---
    ("The TrolMaster leaf-temp probe replaced the cheap Inkbird IBS-TH2 on 2026-03-20 because the IBS-TH2 readings drifted two degrees hot under the Mars Hydro FC-E4800's direct beam.", "decision", "cross", False,
     [("TrolMaster", "organization"), ("Inkbird", "organization"), ("IBS-TH2", "infrastructure"), ("2026-03-20", "date"), ("Mars Hydro", "organization"), ("FC-E4800", "infrastructure")],
     [("TrolMaster", "IBS-TH2", "REPLACES")],
     "when did the leaf-temp probe swap happen and what was wrong with the old one",
     "leaf temp probe swap drift direct beam grow light measurement"),
    # --- 41 ---
    ("Smart Garden's 2026-01-17 comparison article ranked the Rachio 3 above the Hunter Hydrawise for clay soil because of the cycle-and-soak algorithm Hunter still charges extra to enable.", "reference", "cross", False,
     [("Smart Garden", "publication"), ("2026-01-17", "date"), ("Rachio 3", "infrastructure"), ("Hunter Hydrawise", "infrastructure")],
     [("Rachio 3", "Hunter Hydrawise", "IMPROVES_ON")],
     "which irrigation-controller article backed the Rachio pick for clay soil",
     "cycle and soak algorithm clay soil irrigation comparison article ranking"),
    # --- 42 ---
    ("The greenhouse-climate CSV export from Grafana fed a Python notebook that matched the Mokum cucumber yield curve against the 2025 DLI daily integral totals.", "architecture", "cross", False,
     [("Grafana", "service"), ("CSV", "concept"), ("Python", "language"), ("Mokum", "concept"), ("DLI", "concept")],
     [("Python", "CSV", "USES")],
     "how did the cucumber yield get correlated with daily light integral",
     "yield curve DLI correlation csv export notebook analysis crop variety"),
    # --- 43 ---
    ("The Hortisketch 2026 succession plan overlaps with Neversink Farms's crop map only where the Salanova lettuce blocks line up because the bed widths still differ.", "fact", "cross", False,
     [("Hortisketch", "tool"), ("Neversink Farms", "organization"), ("Salanova", "concept")],
     [],
     "where does the market-garden template line up with the current plan",
     "succession plan template overlap lettuce block bed width mismatch"),
    # --- 44 ---
    ("Prefers Floriss over Planta as the plant-care reminder app because Floriss ingests the MiFlora sensor data for the ficus and skips notifications when the soil is already damp enough.", "preference", "cross", False,
     [("Floriss", "service"), ("Planta", "service"), ("MiFlora", "infrastructure")],
     [("Floriss", "Planta", "PREFERS"), ("Floriss", "MiFlora", "USES")],
     "which plant-care reminder app wins and why it edges out the alternative",
     "plant care reminder app sensor integration notification skip soil moisture"),
    # --- 45 ---
    ("The garden-bed QR codes printed from a Brother QL-820NWB label printer tie each bed to an Obsidian note through a custom URI scheme that opens the right markdown file.", "architecture", "cross", False,
     [("Brother QL-820NWB", "infrastructure"), ("Obsidian", "tool"), ("URI", "protocol")],
     [("Obsidian", "URI", "USES")],
     "how do the garden bed QR codes actually open the right note",
     "qr code label printer custom uri scheme bed to note mapping"),
    # --- 46 ---
    ("The TrolMaster Hydro-X's pH-dosing module replaced a peristaltic Blumat doser on the 2026-01-22 build because the Hydro-X feedback loop actually reads the Bluelab Guardian in-line.", "decision", "cross", False,
     [("TrolMaster", "organization"), ("Hydro-X", "infrastructure"), ("Blumat", "organization"), ("2026-01-22", "date"), ("Bluelab Guardian", "infrastructure")],
     [("Hydro-X", "Blumat", "REPLACES"), ("Hydro-X", "Bluelab Guardian", "USES")],
     "when did the pH-dosing hardware swap and what closed the feedback loop",
     "peristaltic doser replacement feedback loop inline meter build date"),
    # --- 47 ---
    ("Curiosity spiked when the Theengs Gateway firmware began decoding the Ruuvi tags I had lying around, so the cold-frame now reports temp through the same BLE proxy as the MiFlora sensors.", "milestone", "cross", False,
     [("Curiosity", "emotion"), ("Theengs Gateway", "tool"), ("Ruuvi", "organization"), ("BLE", "protocol"), ("MiFlora", "infrastructure")],
     [("Theengs Gateway", "Ruuvi", "SUPPORTS"), ("Theengs Gateway", "BLE", "USES")],
     "when did the cold-frame temp sensor finally land on the home dashboard",
     "ruuvi tag decoding ble proxy cold frame temperature home lab firmware"),
    # --- 48 ---
    ("The Farmbrite farm-management SaaS replaced a sprawling Airtable base on 2026-03-25 for the half-acre homestead because Farmbrite chains harvest yields to the livestock feed schedule.", "milestone", "cross", False,
     [("Farmbrite", "service"), ("Airtable", "service"), ("2026-03-25", "date")],
     [("Farmbrite", "Airtable", "REPLACES")],
     "when did the homestead records leave Airtable for a dedicated tool",
     "farm management migration airtable harvest livestock feed schedule chain"),
    # --- 49 ---
    ("The Spider Farmer SE-5000 spectrum chart shared on the MIGRO YouTube channel tipped me off to the 3500K bias that matched my tomato leaf-color test better than the 3000K alternative.", "reference", "cross", False,
     [("Spider Farmer", "organization"), ("SE-5000", "infrastructure"), ("MIGRO", "publication")],
     [("MIGRO", "SE-5000", "APPLIES_TO")],
     "which YouTube channel surfaced the spectrum bias that matched the tomato test",
     "spectrum chart grow light kelvin bias tomato leaf color youtube channel"),
    # --- 50 ---
    ("Joy hit on 2026-04-11 when the first Cherokee Purple ripened exactly on the Hortisketch projected date because the MiFlora moisture log showed a perfectly flat week of 35% soil.", "milestone", "cross", False,
     [("Joy", "emotion"), ("2026-04-11", "date"), ("Cherokee Purple", "concept"), ("Hortisketch", "tool"), ("MiFlora", "infrastructure")],
     [("Hortisketch", "MiFlora", "USES")],
     "when did the first Cherokee Purple actually ripen against the projected date",
     "heirloom tomato ripen projected date moisture log flat week validation"),
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
