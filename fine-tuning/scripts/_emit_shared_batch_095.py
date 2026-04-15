"""One-off emitter for shared-base batch-095 — cross domain.

Slice: pets meets tech (smart feeders, pet cameras, GPS collars, aquarium
controllers, smart litter boxes, microchip doors, vet portals, training apps).
Writes 50 rows to data/v2/shared/batch_095.tmp.jsonl with ids
shared-04701..04750. The main session aggregates the tmp file into
shared.jsonl after validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_095.tmp.jsonl"
ID_OFFSET = 4700

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Swapped the PetSafe Smart Feed for a Petlibro Granary dual-hopper on 2026-02-11 because the Petlibro splits kibble across Miso and Yuzu without needing two separate units on the kitchen counter.", "decision", "cross", False,
     [("PetSafe Smart Feed", "service"), ("Petlibro Granary", "service"), ("2026-02-11", "date"), ("Miso", "person"), ("Yuzu", "person")],
     [("Petlibro Granary", "PetSafe Smart Feed", "REPLACES")],
     "when did the kitchen feeder change and what drove the swap",
     "smart feeder dual hopper multi cat kibble split counter space"),
    # --- 2 ---
    ("Prefers the SureFeed microchip feeder over the old magnet-collar bowl because the Bengal mix Indigo actually reads her own chip and the neighborhood cat can no longer raid the wet food.", "preference", "cross", False,
     [("SureFeed", "service"), ("Indigo", "person")],
     [("SureFeed", "Indigo", "KNOWS")],
     "which feeder actually stopped the neighbor cat from stealing wet food",
     "microchip feeder selective access collar magnet replacement wet food"),
    # --- 3 ---
    ("The Furbo 360 camera replaced the cheap Wyze Cam v3 in the living room on 2026-01-19 because the bark-alert ML on the Furbo catches the door-knock anxiety episodes Wyze's generic motion detection kept missing.", "decision", "cross", False,
     [("Furbo 360", "service"), ("Wyze Cam v3", "service"), ("2026-01-19", "date")],
     [("Furbo 360", "Wyze Cam v3", "REPLACES")],
     "which pet camera took over the living room and why",
     "bark detection machine learning pet camera swap separation anxiety"),
    # --- 4 ---
    ("Tractive LTE replaced the Whistle Go Explore on the shepherd-mix Arlo's collar after Whistle's 2026-03-02 service change dropped the live-tracking tier down to ten-minute refreshes.", "decision", "cross", False,
     [("Tractive LTE", "service"), ("Whistle Go Explore", "service"), ("Arlo", "person"), ("2026-03-02", "date")],
     [("Tractive LTE", "Whistle Go Explore", "REPLACES")],
     "why did the GPS collar change for Arlo in early March",
     "GPS pet tracker subscription change live tracking cadence dog collar"),
    # --- 5 ---
    ("The Jiobit tag on the senior dachshund Pepper travels in the backpack whenever we hike the Cascades because Jiobit's US-wide LTE beats the Tractive dead-zone map in the North Cascades backcountry.", "architecture", "cross", False,
     [("Jiobit", "service"), ("Pepper", "person"), ("Cascades", "place"), ("Tractive", "service"), ("North Cascades", "place")],
     [("Jiobit", "Tractive", "PREFERS")],
     "which pet tracker wins for backcountry hiking with the dachshund",
     "small pet GPS tracker LTE coverage backcountry dead zone hiking"),
    # --- 6. noise ---
    ("Let me reconsider that for a moment.", "fact", "noise", True, [], [], None, None),
    # --- 7 ---
    ("Hacked an Apple AirTag into a MagSafe-printed collar clip for the indoor cat Clover because SureFlap's microchip door logs already tell me when she's out, but AirTag gives the Find My handoff if a neighbor actually spots her.", "architecture", "cross", False,
     [("Apple AirTag", "infrastructure"), ("MagSafe", "protocol"), ("Clover", "person"), ("SureFlap", "service"), ("Find My", "service")],
     [("Apple AirTag", "Find My", "USES")],
     "how does the indoor cat backup tracking work alongside the microchip door",
     "airtag collar hack crowdsourced tracking microchip door exit log"),
    # --- 8 ---
    ("The Neptune Apex aquarium controller replaced the GHL Profilux on the 120-gallon reef on 2026-02-25 because Fusion's Trident calcium-alkalinity-magnesium probe pack finally ships drivers that match the Apex's ORP reading cadence.", "decision", "cross", False,
     [("Neptune Apex", "infrastructure"), ("GHL Profilux", "infrastructure"), ("2026-02-25", "date"), ("Fusion", "service"), ("Trident", "infrastructure")],
     [("Neptune Apex", "GHL Profilux", "REPLACES")],
     "which reef controller is running the 120-gallon now and why the swap",
     "reef controller migration calcium alkalinity magnesium probe integration"),
    # --- 9 ---
    ("The Litter-Robot 4 improves on the classic open pan setup because the Whisker app's weight log flagged Miso's 0.4-pound drop three days before the vet portal at MyVCA could slot a dehydration appointment.", "fact", "cross", False,
     [("Litter-Robot 4", "service"), ("Whisker", "service"), ("Miso", "person"), ("MyVCA", "service")],
     [("Litter-Robot 4", "Whisker", "USES"), ("Whisker", "MyVCA", "COMMUNICATES_WITH")],
     "how did the smart litter box end up catching the dehydration episode early",
     "self cleaning litter box weight trend dehydration vet portal alert"),
    # --- 10 ---
    ("SureFlap microchip cat door replaced the old magnetic-collar door on the laundry-room wall because the magnet kept letting the feral grey tom in and the chip-only lock actually recognizes Clover and Indigo.", "decision", "cross", False,
     [("SureFlap", "service"), ("Clover", "person"), ("Indigo", "person")],
     [("SureFlap", "Clover", "KNOWS"), ("SureFlap", "Indigo", "KNOWS")],
     "why did the cat door get upgraded off the magnetic collar system",
     "microchip cat door magnetic collar replacement feral intrusion lock"),
    # --- 11 ---
    ("PawPrint's vet-record aggregator pulls Arlo's rabies tag number from the MyVCA portal automatically, which improves on the old Google Drive folder of scanned PDFs that nobody kept current.", "decision", "cross", False,
     [("PawPrint", "service"), ("Arlo", "person"), ("MyVCA", "service"), ("Google Drive", "service"), ("PDF", "concept")],
     [("PawPrint", "Google Drive", "IMPROVES_ON"), ("PawPrint", "MyVCA", "COMMUNICATES_WITH")],
     "how do the vet records stay current now instead of in scanned PDFs",
     "vet record aggregator portal sync pdf folder replacement rabies tag"),
    # --- 12 ---
    ("Pawlicy Advisor's comparison table steered the Pepper insurance pick toward Lemonade Pet on 2026-03-14 because the hereditary-coverage filter caught the IVDD rider that Trupanion's plan silently excluded.", "decision", "cross", False,
     [("Pawlicy Advisor", "service"), ("Pepper", "person"), ("Lemonade Pet", "service"), ("2026-03-14", "date"), ("Trupanion", "service")],
     [("Pawlicy Advisor", "Trupanion", "CONTRADICTS")],
     "which pet insurance comparison site steered the dachshund coverage pick",
     "pet insurance comparison hereditary rider disc disease exclusion filter"),
    # --- 13 ---
    ("The Pet Notebook iOS app keeps the grooming notes for the Bernese Kenji because the app's coat-blowout reminder triggers off the Dogo training log's activity entries instead of a fixed cron.", "architecture", "cross", False,
     [("Pet Notebook", "service"), ("iOS", "infrastructure"), ("Kenji", "person"), ("Dogo", "service")],
     [("Pet Notebook", "Dogo", "COMMUNICATES_WITH"), ("Pet Notebook", "iOS", "DEPLOYED_ON")],
     "how do the grooming reminders for Kenji actually get scheduled",
     "grooming reminder coat blowout training log activity trigger app"),
    # --- 14 ---
    ("Frustration hit the kitchen when the Petcube Bites 2 treat-toss servo jammed on 2026-02-28 mid-afternoon and dumped half the treat hopper onto the floor before the Wi-Fi cut.", "problem", "cross", False,
     [("Frustration", "emotion"), ("Petcube Bites 2", "service"), ("2026-02-28", "date")],
     [],
     "what went wrong with the treat-toss camera that afternoon",
     "treat toss camera servo jam hopper spill connectivity drop"),
    # --- 15 ---
    ("Prefers Pupford's video-based puppy curriculum over Dogo for the collie pup Juno because Pupford's leash-walking progression maps onto the Tractive activity goals cleanly instead of Dogo's opaque streak system.", "preference", "cross", False,
     [("Pupford", "service"), ("Dogo", "service"), ("Juno", "person"), ("Tractive", "service")],
     [("Pupford", "Dogo", "PREFERS"), ("Pupford", "Tractive", "COMMUNICATES_WITH")],
     "which puppy-training app won for Juno and why",
     "puppy training app curriculum activity goal integration streak"),
    # --- 16 ---
    ("Relief washed over me when the Tractive alert pinged at 2026-04-02 dusk with Arlo already two blocks north, and the live-tracking refresh caught him before he hit the arterial road.", "milestone", "cross", False,
     [("Relief", "emotion"), ("Tractive", "service"), ("2026-04-02", "date"), ("Arlo", "person")],
     [],
     "when did the GPS collar actually save Arlo from the road",
     "lost dog alert live tracking refresh cadence arterial road escape"),
    # --- 17 ---
    ("The reef-tank logging lives in plain-text daily notes on Obsidian because the Apex Fusion CSV export pipes cleanly into a Dataview table and the old Reef2Reef spreadsheet was a nightmare to query.", "architecture", "cross", False,
     [("Obsidian", "tool"), ("Apex Fusion", "service"), ("CSV", "concept"), ("Dataview", "tool"), ("Reef2Reef", "service")],
     [("Obsidian", "Reef2Reef", "REPLACES"), ("Obsidian", "Apex Fusion", "USES")],
     "how does the reef tank logging actually get kept now",
     "reef tank log plain text obsidian csv export dataview query"),
    # --- 18 ---
    ("Cattime's breed tracker app replaced the Pet Notebook entries for the ragdoll Kumo because Cattime's growth-chart overlay against breed-standard weight flagged the hyperthyroid trend two months before the MyVCA blood panel confirmed it.", "milestone", "cross", False,
     [("Cattime", "service"), ("Pet Notebook", "service"), ("Kumo", "person"), ("MyVCA", "service")],
     [("Cattime", "Pet Notebook", "REPLACES")],
     "what app caught the hyperthyroid trend before the vet panel did",
     "breed tracker growth chart weight trend hyperthyroid early detection"),
    # --- 19 ---
    ("The SureFlap Connect hub sits on the 2.4 GHz IoT VLAN with the Petlibro feeder because both devices choke on 5 GHz roaming and the UniFi guest policy keeps them off the main network.", "architecture", "cross", False,
     [("SureFlap Connect", "service"), ("Petlibro", "service"), ("UniFi", "platform")],
     [("SureFlap Connect", "UniFi", "DEPLOYED_ON"), ("Petlibro", "UniFi", "DEPLOYED_ON")],
     "how are the cat door and feeder isolated on the home network",
     "iot vlan 2.4ghz segregation microchip hub pet hardware wifi policy"),
    # --- 20 ---
    ("Curiosity piqued when Petcube's Emergency Fund partnership actually reimbursed 200 dollars for Juno's foxtail-removal visit on 2026-03-19 after the in-app claim went through the PawPrint record sync.", "milestone", "cross", False,
     [("Curiosity", "emotion"), ("Petcube", "service"), ("Juno", "person"), ("2026-03-19", "date"), ("PawPrint", "service")],
     [("Petcube", "PawPrint", "USES")],
     "when did the Petcube emergency fund actually pay out for Juno",
     "pet camera emergency fund reimbursement vet visit record sync"),
    # --- 21 ---
    ("GroomIt replaced Rover for grooming-appointment booking on 2026-02-06 because the GroomIt groomer brings the van and Kenji no longer melts down on the drive to the shop.", "decision", "cross", False,
     [("GroomIt", "service"), ("Rover", "service"), ("2026-02-06", "date"), ("Kenji", "person")],
     [("GroomIt", "Rover", "REPLACES")],
     "which grooming-appointment app took over and why",
     "mobile grooming app booking van service anxiety drop travel stress"),
    # --- 22 ---
    ("The Whistle Go Explore on Pepper broke the charging pogo pins on 2026-01-29 and the replacement shipment was backordered six weeks, which is what finally pushed the Tractive migration.", "problem", "cross", False,
     [("Whistle Go Explore", "service"), ("Pepper", "person"), ("2026-01-29", "date"), ("Tractive", "service")],
     [("Whistle Go Explore", "Tractive", "CAUSES")],
     "what hardware failure kicked off the GPS collar migration",
     "charging pogo pin failure backorder GPS collar migration trigger"),
    # --- 23 ---
    ("The Petlibro fountain's flow sensor feeds into Home Assistant over a Zigbee2MQTT bridge because the native Petlibro app refuses to expose the water-level telemetry through any documented API.", "architecture", "cross", False,
     [("Petlibro", "service"), ("Home Assistant", "platform"), ("Zigbee2MQTT", "tool"), ("API", "concept")],
     [("Petlibro", "Home Assistant", "COMMUNICATES_WITH"), ("Home Assistant", "Zigbee2MQTT", "USES")],
     "how does the pet fountain water level actually surface on the dashboard",
     "pet fountain water level telemetry home assistant zigbee bridge"),
    # --- 24 ---
    ("Prefers the Petcube Cam over the Furbo for the senior cat Kumo's monitoring room because the Petcube's night-vision IR doesn't whine at the frequency that sends Kumo under the bed.", "preference", "cross", False,
     [("Petcube Cam", "service"), ("Furbo", "service"), ("Kumo", "person")],
     [("Petcube Cam", "Furbo", "PREFERS")],
     "which camera stays in the senior cat's room and why",
     "pet camera night vision IR whine frequency senior cat avoidance"),
    # --- 25 ---
    ("The 2026-03-08 rabies booster appointment for Arlo got scheduled through the MyVCA portal because the portal already had the PawPrint-imported titer record attached to the chart.", "milestone", "cross", False,
     [("2026-03-08", "date"), ("Arlo", "person"), ("MyVCA", "service"), ("PawPrint", "service")],
     [("MyVCA", "PawPrint", "USES")],
     "when and where did the rabies booster for Arlo actually get scheduled",
     "vet portal appointment rabies booster titer record import chart"),
    # --- 26 ---
    ("The aquarium monitoring shifted from the Seneye reef USB stick to an Apex-integrated ReefPi Raspberry Pi build because the Seneye's cloud-only dashboard kept dropping alerts during the ISP's 3am reboot window.", "decision", "cross", False,
     [("Seneye", "infrastructure"), ("Apex", "infrastructure"), ("ReefPi", "project"), ("Raspberry Pi", "infrastructure")],
     [("ReefPi", "Seneye", "REPLACES"), ("ReefPi", "Raspberry Pi", "DEPLOYED_ON")],
     "why did the aquarium monitoring move off Seneye and onto a Pi",
     "aquarium monitor migration cloud outage raspberry pi reef controller"),
    # --- 27 ---
    ("Panic set in when the Litter-Robot 4 wedged on 2026-02-22 mid-cycle with Indigo inside and the Whisker app's SOS sensor cut the motor before anything bad happened.", "milestone", "cross", False,
     [("Panic", "emotion"), ("Litter-Robot 4", "service"), ("2026-02-22", "date"), ("Indigo", "person"), ("Whisker", "service")],
     [("Whisker", "Litter-Robot 4", "CONFIGURES")],
     "when did the smart litter box actually catch a cat mid-cycle",
     "self cleaning litter jam weight sensor motor cutoff safety event"),
    # --- 28 ---
    ("The Tractive 2026 firmware push broke the geofence exit alerts for three days straight, so the backup Jiobit tag quietly took over the primary tracking duty on Arlo's harness.", "problem", "cross", False,
     [("Tractive", "service"), ("Jiobit", "service"), ("Arlo", "person")],
     [("Jiobit", "Tractive", "REPLACES")],
     "what pushed the backup GPS tag into the primary role that week",
     "firmware regression geofence alert outage backup tracker failover"),
    # --- 29 ---
    ("Pawlicy Advisor replaced the old Spruce Pets comparison blog for insurance research because Pawlicy models the breed-specific IVDD cost curve for Pepper that the blog couldn't quantify.", "decision", "cross", False,
     [("Pawlicy Advisor", "service"), ("Spruce Pets", "publication"), ("Pepper", "person")],
     [("Pawlicy Advisor", "Spruce Pets", "REPLACES")],
     "which insurance research tool actually modeled the IVDD cost curve",
     "pet insurance research breed specific cost projection blog replacement"),
    # --- 30 ---
    ("The Kasa smart plug on the aquarium heater is controlled by the Apex Fusion outlet schedule through IFTTT because Apex's native outlet module was backordered for the 2026-02-19 swap.", "architecture", "cross", False,
     [("Kasa", "service"), ("Apex Fusion", "service"), ("IFTTT", "service"), ("2026-02-19", "date")],
     [("Apex Fusion", "Kasa", "COMMUNICATES_WITH"), ("Apex Fusion", "IFTTT", "USES")],
     "how is the aquarium heater being scheduled during the outlet backorder",
     "smart plug aquarium heater schedule backorder integration bridge"),
    # --- 31 ---
    ("Dogo's clicker-training module stopped working on the Pixel 9 on 2026-03-05 because the Android 15 background-audio policy throttled the app's clicker sound below the reward window.", "problem", "cross", False,
     [("Dogo", "service"), ("Pixel 9", "infrastructure"), ("2026-03-05", "date"), ("Android 15", "infrastructure")],
     [("Dogo", "Android 15", "DEPLOYED_ON")],
     "what broke the Dogo clicker training on the new phone",
     "clicker training app audio background throttle policy reward timing"),
    # --- 32 ---
    ("The Petcube Play 2 laser toy feeds Clover's daily activity minutes into the Cattime weight-trend chart because Petcube's webhook posts a play-session JSON that Cattime's ingest accepts unmodified.", "architecture", "cross", False,
     [("Petcube Play 2", "service"), ("Clover", "person"), ("Cattime", "service"), ("JSON", "concept")],
     [("Petcube Play 2", "Cattime", "COMMUNICATES_WITH")],
     "how does Clover's laser-play time end up on the weight chart",
     "laser toy activity webhook json ingest weight trend chart cat"),
    # --- 33 ---
    ("Apex Fusion's 2026-03-11 outage knocked out dosing pump scheduling for eight hours and the ReefLink backup only caught the alert because a Pushover webhook fired off the local iCumulus script.", "problem", "cross", False,
     [("Apex Fusion", "service"), ("2026-03-11", "date"), ("ReefLink", "service"), ("Pushover", "service"), ("iCumulus", "tool")],
     [("ReefLink", "Pushover", "USES")],
     "what caught the eight-hour dosing outage that morning",
     "aquarium controller outage dosing pump pushover webhook alert fallback"),
    # --- 34. noise ---
    ("Hmm, that's an interesting point.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The Petlibro Polar ice-cooled feeder replaced the regular Petlibro Granary for the raw-food diet because the thermal fail-safe cuts the thaw timer if the basement freezer compressor trips on the Sense energy monitor.", "decision", "cross", False,
     [("Petlibro Polar", "service"), ("Petlibro Granary", "service"), ("Sense", "service")],
     [("Petlibro Polar", "Petlibro Granary", "REPLACES"), ("Petlibro Polar", "Sense", "COMMUNICATES_WITH")],
     "why did the raw-food feeder change out and what triggers the safety cut",
     "cooled feeder raw diet thermal safety freezer compressor energy monitor"),
    # --- 36 ---
    ("The 2026-04-05 Juno puppy-class graduation in the Pupford app unlocked the nosework module that the Dogo subscription never offered at any tier.", "milestone", "cross", False,
     [("2026-04-05", "date"), ("Juno", "person"), ("Pupford", "service"), ("Dogo", "service")],
     [("Pupford", "Dogo", "IMPROVES_ON")],
     "when did Juno graduate the puppy class and what opened up after",
     "puppy class graduation unlock nosework module tier comparison"),
    # --- 37 ---
    ("MyVCA portal swap to a Banfield Optimum Wellness plan on 2026-01-15 for Kenji because the VCA monthly dental cleaning credit wasn't matching the Banfield plan's unlimited exam policy for the Bernese breed's dental risk.", "decision", "cross", False,
     [("MyVCA", "service"), ("Banfield Optimum Wellness", "service"), ("2026-01-15", "date"), ("Kenji", "person")],
     [("Banfield Optimum Wellness", "MyVCA", "REPLACES")],
     "when did Kenji's vet plan change and what drove the swap",
     "vet wellness plan swap dental cleaning credit unlimited exam breed risk"),
    # --- 38 ---
    ("The Furbo bark-alert fires a webhook into Home Assistant which in turn dims the Hue lights in Arlo's crate room because the low-light state calms the reactivity episodes faster than the squirt-bottle routine ever did.", "architecture", "cross", False,
     [("Furbo", "service"), ("Home Assistant", "platform"), ("Hue", "service"), ("Arlo", "person")],
     [("Furbo", "Home Assistant", "COMMUNICATES_WITH"), ("Home Assistant", "Hue", "USES")],
     "how does the bark alert actually calm Arlo in the crate room now",
     "bark alert webhook smart light automation crate reactivity response"),
    # --- 39 ---
    ("Prefers the GHL Profilux over the Apex on the 40-gallon nano-reef because the Profilux's pH probe calibration holds three weeks longer and the nano doesn't need the Apex module library.", "preference", "cross", False,
     [("GHL Profilux", "infrastructure"), ("Apex", "infrastructure")],
     [("GHL Profilux", "Apex", "PREFERS")],
     "which reef controller wins on the smaller nano-reef build",
     "nano reef controller pH probe calibration drift module library"),
    # --- 40 ---
    ("The SureFlap 2026-03-22 firmware added dusk-dawn curfew rules which replaced the old Home Assistant automation that fired off sunrise-sunset from the Pirate Weather integration.", "milestone", "cross", False,
     [("SureFlap", "service"), ("2026-03-22", "date"), ("Home Assistant", "platform"), ("Pirate Weather", "service")],
     [("SureFlap", "Home Assistant", "REPLACES")],
     "when did the cat door pick up native dusk-dawn curfews",
     "microchip door firmware curfew dusk dawn rule sunrise sunset automation"),
    # --- 41 ---
    ("The PawPrint shared-family tier lets my sister Mariana review Kenji's appointment history before she dog-sits for the 2026-05-18 trip because MyVCA's own portal doesn't support guest access.", "architecture", "cross", False,
     [("PawPrint", "service"), ("Mariana", "person"), ("Kenji", "person"), ("2026-05-18", "date"), ("MyVCA", "service")],
     [("PawPrint", "MyVCA", "IMPROVES_ON"), ("Mariana", "Kenji", "KNOWS")],
     "how does the dog-sitter get read-only access to Kenji's vet chart",
     "shared family vet record access dog sitter guest portal limitation"),
    # --- 42 ---
    ("Curiosity about the Trident probe's accuracy led to a weekly ICP-Analysis mail-in test on 2026-02-14 because the Apex alkalinity reading was drifting 0.3 dKH from the Hanna Checker hand-test for two weeks.", "problem", "cross", False,
     [("Curiosity", "emotion"), ("Trident", "infrastructure"), ("ICP-Analysis", "service"), ("2026-02-14", "date"), ("Apex", "infrastructure"), ("Hanna Checker", "infrastructure")],
     [("ICP-Analysis", "Trident", "IMPROVES_ON")],
     "what pushed the weekly mail-in water test routine to start",
     "reef probe drift calibration cross check mail in icp analysis"),
    # --- 43 ---
    ("The Litter-Robot 4 weight-log CSV pipes into a Grafana dashboard on the home Docker host because the Whisker app's native trend view collapses the two-cat data without separating Clover and Indigo.", "architecture", "cross", False,
     [("Litter-Robot 4", "service"), ("CSV", "concept"), ("Grafana", "tool"), ("Docker", "platform"), ("Whisker", "service"), ("Clover", "person"), ("Indigo", "person")],
     [("Grafana", "Whisker", "IMPROVES_ON"), ("Grafana", "Docker", "DEPLOYED_ON")],
     "how do the per-cat litter box trends stay separated",
     "litter box weight log csv grafana dashboard multi cat separation"),
    # --- 44 ---
    ("Replaced the Amazon Alexa routine that spoke the Furbo bark count with a Telegram bot because Alexa's announcement volume couldn't be duckied during Zoom calls without killing the whole room's audio.", "decision", "cross", False,
     [("Amazon Alexa", "service"), ("Furbo", "service"), ("Telegram", "service"), ("Zoom", "service")],
     [("Telegram", "Amazon Alexa", "REPLACES")],
     "why did the bark-count notifier move from Alexa to Telegram",
     "voice announcement duck conflict work call notification channel swap"),
    # --- 45 ---
    ("The 2026-04-09 Tractive subscription renewed on the annual tier because the monthly cost for live tracking across Arlo and Juno would have been 60 percent more over the year.", "decision", "cross", False,
     [("2026-04-09", "date"), ("Tractive", "service"), ("Arlo", "person"), ("Juno", "person")],
     [],
     "why did the GPS collar subscription renew on the yearly tier",
     "gps subscription annual tier cost comparison multi pet savings"),
    # --- 46 ---
    ("The ReefPi build exposes MQTT topics that feed into the same Home Assistant dashboard as the Petlibro fountain, so a single Lovelace card shows tank temperature next to cat water-bowl flow.", "architecture", "cross", False,
     [("ReefPi", "project"), ("MQTT", "protocol"), ("Home Assistant", "platform"), ("Petlibro", "service"), ("Lovelace", "tool")],
     [("ReefPi", "MQTT", "USES"), ("Home Assistant", "Lovelace", "USES")],
     "how do the tank and pet-fountain readings end up on one screen",
     "mqtt reef pi home assistant lovelace dashboard pet fountain tank"),
    # --- 47 ---
    ("The Whisker SOS alert fired on 2026-04-01 at 2am when the Litter-Robot weight sensor detected Kumo sitting too long, and the MyVCA telehealth consult was booked before sunrise.", "milestone", "cross", False,
     [("Whisker", "service"), ("2026-04-01", "date"), ("Litter-Robot", "service"), ("Kumo", "person"), ("MyVCA", "service")],
     [("Whisker", "MyVCA", "COMMUNICATES_WITH")],
     "when did the litter-box SOS actually trigger a telehealth booking",
     "litter box SOS weight sensor overnight alert telehealth consult"),
    # --- 48 ---
    ("Apple AirTag on Juno's collar clip replaced the Tile Pro tag because the Find My network crowdsourced handoff in the neighborhood dog park already beat Tile's thinner Bluetooth mesh in three real trials.", "decision", "cross", False,
     [("Apple AirTag", "infrastructure"), ("Juno", "person"), ("Tile Pro", "infrastructure"), ("Find My", "service"), ("Bluetooth", "protocol")],
     [("Apple AirTag", "Tile Pro", "REPLACES"), ("Apple AirTag", "Find My", "USES")],
     "which collar tag won on the short-range backup tracking",
     "bluetooth tag airtag tile crowd network dog park tracking comparison"),
    # --- 49 ---
    ("The Reef2Reef thread on 2026-02-10 from user Aquanerd tipped the dosing-schedule ratio for the new Red Sea Coral Pro salt mix that the Apex Fusion template didn't yet support.", "reference", "cross", False,
     [("Reef2Reef", "service"), ("2026-02-10", "date"), ("Aquanerd", "person"), ("Red Sea Coral Pro", "service"), ("Apex Fusion", "service")],
     [("Aquanerd", "Apex Fusion", "IMPROVES_ON")],
     "which forum post had the dosing ratio the controller template missed",
     "reef forum dosing schedule salt mix ratio controller template gap"),
    # --- 50 ---
    ("Joy surged at the 2026-04-12 Pupford graduation livestream when Juno nailed the recall in front of the webcam because the whole training journal from the Dogo-era days had been retro-imported into Pupford's timeline the week prior.", "milestone", "cross", False,
     [("Joy", "emotion"), ("2026-04-12", "date"), ("Pupford", "service"), ("Juno", "person"), ("Dogo", "service")],
     [("Pupford", "Dogo", "REPLACES")],
     "when did Juno's recall training pay off on the graduation livestream",
     "training graduation livestream recall journal migration import"),
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
