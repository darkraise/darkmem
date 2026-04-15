"""One-off emitter for shared-base batch-125 — cross domain.

Slice: smart car and connected-vehicle meets tech (Tesla OTA, CarPlay/Android
Auto, OBD-II dongles, dashcam apps, EV routing, home-charger integrations,
phone-as-key, Carfax/HPI history checks, in-car subscription features). Writes
50 rows to data/v2/shared/batch_125.tmp.jsonl with ids shared-06201..06250. The
main session aggregates the tmp file into shared.jsonl after validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_125.tmp.jsonl"
ID_OFFSET = 6200

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The 2026-03-18 Tesla OTA bumped the Model Y to firmware 2026.8.5 and the new blind-spot camera overlay finally replaced the nagging BlindSpotMonitor third-party dashcam widget.", "milestone", "cross", False,
     [("2026-03-18", "date"), ("Tesla", "organization"), ("Model Y", "infrastructure"), ("BlindSpotMonitor", "service")],
     [("Tesla", "BlindSpotMonitor", "REPLACES")],
     "when did the over-the-air update land that killed the third-party blind-spot widget",
     "tesla ota firmware blind spot camera overlay model y update"),
    # --- 2 ---
    ("TeslaFi replaced Stats for Tesla on my phone because the charging-session granularity down to the individual phase actually mattered once the Wallbox Pulsar Plus went three-phase at home.", "decision", "cross", False,
     [("TeslaFi", "service"), ("Stats for Tesla", "service"), ("Wallbox Pulsar Plus", "infrastructure")],
     [("TeslaFi", "Stats for Tesla", "REPLACES")],
     "which tesla logger won after the home charger went three phase",
     "tesla logging app charging session phase granularity swap"),
    # --- 3 ---
    ("Prefers CarPlay over Android Auto on the 2024 Honda Civic because the wireless CarPlay adapter from Ottocast reconnects in under four seconds while the Motorola MA1 still renegotiates for twelve.", "preference", "cross", False,
     [("CarPlay", "service"), ("Android Auto", "service"), ("Honda Civic", "infrastructure"), ("Ottocast", "organization"), ("Motorola MA1", "infrastructure")],
     [("CarPlay", "Android Auto", "PREFERS")],
     "which phone projection wins in the civic and what hardware drives it",
     "wireless carplay adapter reconnect latency android auto dongle"),
    # --- 4 ---
    ("CarBridge on the jailbroken iPhone 14 Pro finally let YouTube run on the head unit, but the 2026-02-07 iOS 18.3 update killed the TrollStore sideload and the hack evaporated.", "problem", "cross", False,
     [("CarBridge", "service"), ("iPhone 14 Pro", "infrastructure"), ("YouTube", "service"), ("2026-02-07", "date"), ("iOS 18.3", "infrastructure"), ("TrollStore", "tool")],
     [("CarBridge", "TrollStore", "USES")],
     "what broke the youtube-on-head-unit jailbreak setup that week",
     "carbridge jailbreak sideload trollstore ios update head unit loss"),
    # --- 5 ---
    ("The OBDLink MX+ replaced the cheap Veepeak OBD-II dongle on the 2018 Subaru Outback because Torque Pro's live AFR logging kept dropping frames on the Veepeak's Bluetooth 2.1 radio.", "decision", "cross", False,
     [("OBDLink MX+", "infrastructure"), ("Veepeak", "infrastructure"), ("Subaru Outback", "infrastructure"), ("Torque Pro", "tool"), ("Bluetooth", "protocol")],
     [("OBDLink MX+", "Veepeak", "REPLACES"), ("Torque Pro", "OBDLink MX+", "USES")],
     "why did the obd dongle get upgraded on the outback",
     "obd2 dongle swap bluetooth bandwidth afr logging frame drop"),
    # --- 6. noise ---
    ("Let me pull that up for you.", "fact", "noise", True, [], [], None, None),
    # --- 7 ---
    ("FIXD's subscription alert for a pending P0420 code on the Subaru Outback caught the failing rear O2 sensor three weeks before the check-engine light actually stuck.", "fact", "cross", False,
     [("FIXD", "service"), ("P0420", "pattern"), ("Subaru Outback", "infrastructure")],
     [("FIXD", "Subaru Outback", "USES")],
     "what tipped off the failing oxygen sensor before the dash light came on",
     "fixd pending code alert oxygen sensor predictive maintenance outback"),
    # --- 8 ---
    ("BlackVue DR970X replaced the Nextbase 622GW in the Model 3 because cloud-over-LTE upload stayed alive through the garage's weak signal where the Nextbase's Wi-Fi-only sync just queued forever.", "decision", "cross", False,
     [("BlackVue DR970X", "infrastructure"), ("Nextbase 622GW", "infrastructure"), ("Model 3", "infrastructure"), ("LTE", "protocol")],
     [("BlackVue DR970X", "Nextbase 622GW", "REPLACES"), ("BlackVue DR970X", "LTE", "USES")],
     "which dashcam took over and why",
     "dashcam cloud upload lte versus wifi sync garage signal swap"),
    # --- 9 ---
    ("Tesla Sentry Mode caught the 2026-01-29 parking-lot hit-and-run in the Costco lot and the USB-stick clip fed straight into the insurance claim without even touching TeslaCam Viewer.", "milestone", "cross", False,
     [("Tesla Sentry Mode", "service"), ("2026-01-29", "date"), ("Costco", "organization"), ("TeslaCam Viewer", "tool")],
     [("Tesla Sentry Mode", "TeslaCam Viewer", "PREFERS")],
     "when did sentry mode actually earn its keep and did the review tool matter",
     "tesla sentry mode parking incident usb clip insurance claim evidence"),
    # --- 10 ---
    ("PlugShare replaced ChargeHub for the 2026-04-02 New England EV road trip because the community check-ins on broken Electrify America stalls at Sturbridge were four hours fresher.", "decision", "cross", False,
     [("PlugShare", "service"), ("ChargeHub", "service"), ("2026-04-02", "date"), ("Electrify America", "organization"), ("Sturbridge", "place")],
     [("PlugShare", "ChargeHub", "REPLACES")],
     "which charger map won for the northeast ev trip",
     "plugshare chargehub community check in stall status freshness ev"),
    # --- 11 ---
    ("A Better Routeplanner on the phone planned the 2026-05-24 Denver-to-Moab run with two CCS stops while the in-car Tesla planner wanted three because ABRP accepted the manual 65 mph cap.", "architecture", "cross", False,
     [("A Better Routeplanner", "service"), ("2026-05-24", "date"), ("Denver", "place"), ("Moab", "place"), ("CCS", "protocol"), ("Tesla", "organization")],
     [("A Better Routeplanner", "Tesla", "PREFERS")],
     "how did the utah ev route get to two charging stops instead of three",
     "abrp route planner speed cap input charging stop optimization"),
    # --- 12 ---
    ("The Smartcar API replaced a fragile Tesla Unofficial API scraper on the home dashboard because Smartcar's unified read for the Ford F-150 Lightning and the Model 3 finally ended the per-brand webhook mess.", "decision", "cross", False,
     [("Smartcar", "service"), ("Tesla Unofficial API", "service"), ("Ford F-150 Lightning", "infrastructure"), ("Model 3", "infrastructure")],
     [("Smartcar", "Tesla Unofficial API", "REPLACES")],
     "which car-api layer took over the multi-brand dashboard",
     "smartcar api unified oem read webhook consolidation ev fleet"),
    # --- 13 ---
    ("Emporia Vue's circuit-level submeter on the JuiceBox 40 breaker paired with the Wallbox app to catch the 2026-02-14 derate when the main panel hit 175 amps during simultaneous oven use.", "fact", "cross", False,
     [("Emporia Vue", "infrastructure"), ("JuiceBox 40", "infrastructure"), ("Wallbox", "service"), ("2026-02-14", "date")],
     [("Emporia Vue", "JuiceBox 40", "USES"), ("Emporia Vue", "Wallbox", "COMMUNICATES_WITH")],
     "what caught the evse derate during valentine's dinner prep",
     "emporia vue circuit submeter evse derate panel load coordination"),
    # --- 14 ---
    ("The phone-as-key setup on the BMW iX paired over UWB through the iPhone 15 Pro, which finally killed the NFC-tap fallback that only worked at the B-pillar.", "architecture", "cross", False,
     [("BMW iX", "infrastructure"), ("UWB", "protocol"), ("iPhone 15 Pro", "infrastructure"), ("NFC", "protocol")],
     [("UWB", "NFC", "REPLACES"), ("BMW iX", "UWB", "USES")],
     "how does the bmw phone key actually work now across the door",
     "digital car key uwb ultra wideband nfc tap fallback b pillar"),
    # --- 15 ---
    ("Prefers Tezlab over TeslaFi for the quick dashboard glance because Tezlab's Apple Watch complication shows the battery percentage without forcing the phone out of the pocket.", "preference", "cross", False,
     [("Tezlab", "service"), ("TeslaFi", "service"), ("Apple Watch", "infrastructure")],
     [("Tezlab", "TeslaFi", "PREFERS")],
     "which tesla app wins the wrist glance check",
     "tezlab teslafi apple watch complication battery percentage check"),
    # --- 16 ---
    ("Carfax flagged a 2021 airbag deployment on the VIN for the used 2022 Mazda CX-5 the dealer listed on 2026-03-09, and the deal got walked before the test drive even started.", "milestone", "cross", False,
     [("Carfax", "service"), ("Mazda CX-5", "infrastructure"), ("2026-03-09", "date")],
     [],
     "what killed the mazda purchase before the test drive",
     "carfax history airbag deployment vin check used car dealer walk"),
    # --- 17 ---
    ("HPI Check replaced the free Gov.uk MOT lookup for the 2026-02-22 used Golf GTI inspection in Manchester because HPI's outstanding-finance flag caught a live PCP balance the seller hid.", "decision", "cross", False,
     [("HPI Check", "service"), ("Gov.uk", "service"), ("2026-02-22", "date"), ("Golf GTI", "infrastructure"), ("Manchester", "place"), ("PCP", "concept")],
     [("HPI Check", "Gov.uk", "REPLACES")],
     "which uk history check tool caught the hidden finance balance",
     "hpi check outstanding finance pcp used car uk mot lookup"),
    # --- 18 ---
    ("Relief hit when ConnectedDrive finally ended the 80-dollar-a-year heated-seats subscription on 2026-03-31 and the feature just stayed on in the 2024 BMW 330i forever.", "milestone", "cross", False,
     [("Relief", "emotion"), ("ConnectedDrive", "service"), ("2026-03-31", "date"), ("BMW 330i", "infrastructure")],
     [],
     "when did the heated seats subscription finally go away on the 330i",
     "bmw connecteddrive heated seats subscription end in car feature"),
    # --- 19 ---
    ("The Mercedes me app replaced the standalone EQ Ready tracker for the EQE because the trip-review export into Strava-style GPX stopped choking on the wagon's 90 kWh pack data.", "decision", "cross", False,
     [("Mercedes me", "service"), ("EQ Ready", "service"), ("EQE", "infrastructure"), ("GPX", "concept")],
     [("Mercedes me", "EQ Ready", "REPLACES")],
     "why did the eqe trip tracking collapse back into the mercedes me app",
     "mercedes me eq ready trip review gpx export ev wagon battery"),
    # --- 20 ---
    ("CarPlay with the new 2026.4 Waze build finally replaced stock Tesla Navigation for the daily 2026-04-07 Oakland commute because the HOV-lane rules actually routed the I-880 exit right.", "decision", "cross", False,
     [("CarPlay", "service"), ("Waze", "service"), ("Tesla", "organization"), ("2026-04-07", "date"), ("Oakland", "place"), ("I-880", "infrastructure")],
     [("Waze", "Tesla", "REPLACES")],
     "which nav finally won the tesla commute once carplay landed",
     "carplay waze tesla native nav hov rule commute routing swap"),
    # --- 21 ---
    ("Torque Pro's PID library for the 2017 Ford Fusion decoded the AWD rear-differential temperature sensor that neither FIXD nor Carly could even surface on the same dongle.", "fact", "cross", False,
     [("Torque Pro", "tool"), ("Ford Fusion", "infrastructure"), ("FIXD", "service"), ("Carly", "service")],
     [("Torque Pro", "FIXD", "PREFERS")],
     "which obd tool actually exposed the rear diff temp on the fusion",
     "torque pro custom pid awd differential temperature ford fusion"),
    # --- 22 ---
    ("The 2026-05-01 Rivian OTA 2026.14 introduced Camp Power scheduling and the third-party RivianTracker app lost its only differentiating feature overnight.", "problem", "cross", False,
     [("2026-05-01", "date"), ("Rivian", "organization"), ("RivianTracker", "service")],
     [("Rivian", "RivianTracker", "REPLACES")],
     "what rivian ota killed the third party tracker's selling point",
     "rivian ota camp power schedule third party app obsolete"),
    # --- 23 ---
    ("Android Auto Coolwalk on the Pixel 9 Pro replaced the legacy Android Auto layout in the VW ID.4 because the split-screen media plus maps view stopped hiding the next-turn distance.", "decision", "cross", False,
     [("Android Auto Coolwalk", "service"), ("Pixel 9 Pro", "infrastructure"), ("Android Auto", "service"), ("VW ID.4", "infrastructure")],
     [("Android Auto Coolwalk", "Android Auto", "REPLACES")],
     "which android projection layout landed in the id4",
     "android auto coolwalk split screen maps media layout vw id4"),
    # --- 24 ---
    ("Autel MaxiSys MS906 replaced the OBDLink MX+ for the 2026-04-19 ABS-bleed job on the Porsche Cayman because bidirectional control of the PSM pump was outside the MX+'s generic scope.", "decision", "cross", False,
     [("Autel MaxiSys MS906", "infrastructure"), ("OBDLink MX+", "infrastructure"), ("2026-04-19", "date"), ("Porsche Cayman", "infrastructure"), ("PSM", "concept")],
     [("Autel MaxiSys MS906", "OBDLink MX+", "REPLACES")],
     "which scan tool took over the cayman abs bleed",
     "autel maxisys bidirectional abs bleed psm pump obd scan tool"),
    # --- 25 ---
    ("Prefers the Hyundai Bluelink app over the separate MyHyundai portal because the remote pre-condition on the Ioniq 5 actually fires while the car is plugged in to the JuiceBox 40 without draining the HV pack.", "preference", "cross", False,
     [("Hyundai Bluelink", "service"), ("MyHyundai", "service"), ("Ioniq 5", "infrastructure"), ("JuiceBox 40", "infrastructure")],
     [("Hyundai Bluelink", "MyHyundai", "PREFERS"), ("Hyundai Bluelink", "JuiceBox 40", "COMMUNICATES_WITH")],
     "which hyundai app wins for plugged-in precondition on the ioniq",
     "bluelink remote precondition ev hv pack plugged in juicebox evse"),
    # --- 26 ---
    ("Frustration built the day Toyota's remote-start subscription hit the 2026-02-11 paywall on the 2020 RAV4 and the original key-fob RemoteConnect feature silently stopped working.", "problem", "cross", False,
     [("Frustration", "emotion"), ("Toyota", "organization"), ("2026-02-11", "date"), ("RAV4", "infrastructure"), ("RemoteConnect", "service")],
     [],
     "what soured the rav4 remote start on that february date",
     "toyota remote start subscription paywall key fob remoteconnect"),
    # --- 27 ---
    ("The Wallbox Quasar 2 bidirectional charger paired with the Ford F-150 Lightning's Intelligent Backup Power during the 2026-01-17 ice storm, and the Home Integration System actually islanded the panel as promised.", "milestone", "cross", False,
     [("Wallbox Quasar 2", "infrastructure"), ("Ford F-150 Lightning", "infrastructure"), ("2026-01-17", "date"), ("Home Integration System", "infrastructure")],
     [("Wallbox Quasar 2", "Ford F-150 Lightning", "COMMUNICATES_WITH")],
     "when did the bidirectional charger and lightning actually keep the lights on",
     "wallbox quasar 2 v2h bidirectional lightning intelligent backup power"),
    # --- 28 ---
    ("Pulled the VAG-COM VCDS cable out of the drawer for the 2026-03-25 Golf R coding session because neither OBDeleven nor Carly would enable the launch-control staging rev on the MK8.", "decision", "cross", False,
     [("VCDS", "tool"), ("2026-03-25", "date"), ("Golf R", "infrastructure"), ("OBDeleven", "service"), ("Carly", "service")],
     [("VCDS", "OBDeleven", "PREFERS")],
     "which tool actually coded the golf r launch control staging",
     "vcds vag coding launch control mk8 golf r obd app limitation"),
    # --- 29 ---
    ("Apple's Shared Car Keys in iOS 18.4 let Mei drive the Model Y on 2026-03-14 without the second phone handoff, finally replacing the TeslaMate key-sharing hack I'd hosted on the Synology.", "decision", "cross", False,
     [("Shared Car Keys", "service"), ("iOS 18.4", "infrastructure"), ("Mei", "person"), ("Model Y", "infrastructure"), ("2026-03-14", "date"), ("TeslaMate", "tool"), ("Synology", "infrastructure")],
     [("Shared Car Keys", "TeslaMate", "REPLACES")],
     "how did mei finally get a clean tesla key without the selfhost hack",
     "apple shared car keys ios family share teslamate self host swap"),
    # --- 30 ---
    ("The BlackVue DR970X's Cloud Connectivity kept uploading motion clips to the BlackVue Cloud through the Verizon hotspot while parked at Mei's apartment, even as the Jellyfin backup stack choked on the same bandwidth.", "fact", "cross", False,
     [("BlackVue DR970X", "infrastructure"), ("BlackVue Cloud", "service"), ("Verizon", "organization"), ("Mei", "person"), ("Jellyfin", "service")],
     [("BlackVue DR970X", "BlackVue Cloud", "COMMUNICATES_WITH"), ("BlackVue DR970X", "Verizon", "USES")],
     "how did the dashcam stay online while the media stack couldn't",
     "blackvue cloud connectivity lte hotspot bandwidth contention parking"),
    # --- 31 ---
    ("Prefers Scan My Tesla over TeslaFi for the deep diagnostic dive on the 12V subsystem because the CAN-bus decode surfaces the BMS contactor count that TeslaFi's polled API can't even see.", "preference", "cross", False,
     [("Scan My Tesla", "service"), ("TeslaFi", "service"), ("CAN-bus", "protocol"), ("BMS", "concept")],
     [("Scan My Tesla", "TeslaFi", "PREFERS")],
     "which tesla tool gets at the bms contactor count",
     "scan my tesla can bus decode bms contactor deep diagnostic"),
    # --- 32 ---
    ("The ChargePoint Home Flex replaced the JuiceBox 40 on 2026-04-11 after Enphase Enlighten's solar-aware schedule refused to negotiate with JuiceNet's cloud-only API.", "decision", "cross", False,
     [("ChargePoint Home Flex", "infrastructure"), ("JuiceBox 40", "infrastructure"), ("2026-04-11", "date"), ("Enphase Enlighten", "service"), ("JuiceNet", "service")],
     [("ChargePoint Home Flex", "JuiceBox 40", "REPLACES")],
     "what triggered the home evse swap for solar coordination",
     "chargepoint home flex juicebox swap enphase enlighten solar schedule"),
    # --- 33 ---
    ("TezLab's Deep Sleep eco-score kept flagging the 2026-04-06 vampire drain on the Model 3 at 2% per day, and the Ranger traced it to a failed 12V LV battery the car hadn't warned about.", "milestone", "cross", False,
     [("TezLab", "service"), ("2026-04-06", "date"), ("Model 3", "infrastructure"), ("Ranger", "concept")],
     [],
     "what caught the vampire drain the tesla itself wasn't warning about",
     "tezlab deep sleep vampire drain 12v battery ranger service catch"),
    # --- 34. noise ---
    ("Hold on, I'll grab the details.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The 2026-05-12 Ford Power-Up 5.3 on the Mach-E re-enabled the BlueCruise hands-free lane-change feature that the 4.8 update had quietly dropped because of the cross-traffic sensor regression.", "milestone", "cross", False,
     [("2026-05-12", "date"), ("Ford", "organization"), ("Mach-E", "infrastructure"), ("BlueCruise", "service")],
     [("Ford", "BlueCruise", "USES")],
     "when did bluecruise hands free lane change come back to the mach e",
     "ford power up ota bluecruise hands free lane change regression"),
    # --- 36 ---
    ("Sideloaded the Polestar Android Automotive store on the 2024 Polestar 2 to get the Spotify Car Thing-style layout because the stock Google-built media tile buried the playlist picker two taps deep.", "decision", "cross", False,
     [("Polestar 2", "infrastructure"), ("Android Automotive", "platform"), ("Spotify Car Thing", "infrastructure"), ("Google", "organization")],
     [("Polestar 2", "Android Automotive", "USES"), ("Spotify Car Thing", "Google", "REPLACES")],
     "why did the polestar 2 media layout get replaced",
     "android automotive polestar sideload spotify playlist picker ui"),
    # --- 37 ---
    ("Prefers Drivvo over Fuelly for the household fuel-log because Drivvo's CSV export lands cleanly in the Grafana Postgres that already backs the home-energy dashboards.", "preference", "cross", False,
     [("Drivvo", "service"), ("Fuelly", "service"), ("Grafana", "service"), ("Postgres", "service")],
     [("Drivvo", "Fuelly", "PREFERS"), ("Drivvo", "Grafana", "COMMUNICATES_WITH")],
     "which fuel log app wins for the self-hosted dashboard pipeline",
     "drivvo fuelly csv export grafana postgres fuel log household"),
    # --- 38 ---
    ("The Carly adapter's coding session on the 2024 BMW 330i unlocked the US CIC video-in-motion after the 2026-04-03 iDrive 9 rollout re-locked it, and OBDeleven still can't touch BMW codes.", "fact", "cross", False,
     [("Carly", "service"), ("BMW 330i", "infrastructure"), ("CIC", "infrastructure"), ("2026-04-03", "date"), ("iDrive 9", "platform"), ("OBDeleven", "service")],
     [("Carly", "OBDeleven", "PREFERS")],
     "which coding tool re-unlocked the bmw video in motion",
     "carly bmw coding video in motion idrive 9 relock obdeleven gap"),
    # --- 39 ---
    ("The 2026-03-02 Tesla Premium Connectivity renewal bumped to 12 dollars a month and the Starlink Mini in the frunk replaced the in-car LTE for the streaming usage on long drives.", "decision", "cross", False,
     [("2026-03-02", "date"), ("Tesla Premium Connectivity", "service"), ("Starlink Mini", "infrastructure"), ("LTE", "protocol")],
     [("Starlink Mini", "Tesla Premium Connectivity", "REPLACES")],
     "what took over streaming in the tesla after the premium connectivity price hike",
     "starlink mini frunk tesla premium connectivity subscription swap"),
    # --- 40 ---
    ("Excitement ran high on 2026-01-05 when the Rivian R1T's Camp Mode Plus update let the phone-as-key stay unlocked during sleep, because the UWB handoff to Mei's Pixel 9 Pro finally worked.", "milestone", "cross", False,
     [("Excitement", "emotion"), ("2026-01-05", "date"), ("Rivian R1T", "infrastructure"), ("Mei", "person"), ("Pixel 9 Pro", "infrastructure"), ("UWB", "protocol")],
     [("Rivian R1T", "UWB", "USES")],
     "when did the rivian phone key finally stop waking the truck every hour",
     "rivian camp mode plus phone as key uwb sleep handoff pixel"),
    # --- 41 ---
    ("The Autotrader saved-search for a 2023 Model 3 Long Range under 32 thousand dollars pinged the Craigslist cross-poster script I wrote in Python on 2026-02-18 and the car was viewed that afternoon.", "fact", "cross", False,
     [("Autotrader", "service"), ("Model 3", "infrastructure"), ("Craigslist", "service"), ("Python", "language"), ("2026-02-18", "date")],
     [("Python", "Autotrader", "USES")],
     "how did the used tesla listing get caught fast enough to see same day",
     "autotrader saved search cross post scraper python used tesla ping"),
    # --- 42 ---
    ("Prefers the Porsche Connect app's Charging Planner over ABRP for the 911 Dakar because Porsche's Ionity integration pre-authorizes the handshake so the stall is actually live when I pull up.", "preference", "cross", False,
     [("Porsche Connect", "service"), ("ABRP", "service"), ("911 Dakar", "infrastructure"), ("Ionity", "organization")],
     [("Porsche Connect", "ABRP", "PREFERS"), ("Porsche Connect", "Ionity", "COMMUNICATES_WITH")],
     "which planner wins for the dakar because of the charging handshake",
     "porsche connect charging planner ionity preauth handshake abrp"),
    # --- 43 ---
    ("The Model Y's 2026-05-07 FSD v13.2 update replaced the lane-departure-assist beep with a haptic steering-wheel tick, and the third-party SteerHaptic mod on the Raspberry Pi became dead weight.", "decision", "cross", False,
     [("Model Y", "infrastructure"), ("2026-05-07", "date"), ("FSD", "service"), ("SteerHaptic", "service"), ("Raspberry Pi", "infrastructure")],
     [("FSD", "SteerHaptic", "REPLACES")],
     "what fsd update killed the diy haptic wheel mod",
     "fsd v13 haptic steering wheel tick steerhaptic mod raspberry pi"),
    # --- 44 ---
    ("HomeAssistant's tesla_custom integration pulling through the fleet telemetry endpoint replaced the polling teslamate_mqtt topic on 2026-04-24 once the 5-minute rate limit on the old TeslaMate API killed the live dashboard.", "architecture", "cross", False,
     [("HomeAssistant", "service"), ("tesla_custom", "tool"), ("TeslaMate", "tool"), ("2026-04-24", "date")],
     [("tesla_custom", "TeslaMate", "REPLACES")],
     "what took over the tesla live dashboard when the old api got rate limited",
     "home assistant tesla custom fleet telemetry teslamate mqtt swap"),
    # --- 45 ---
    ("The used 2020 Mini Cooper SE purchase on 2026-03-28 passed the AutoCheck history with flying colors but the FIXD dongle pulled three pending codes during the Enterprise test drive.", "problem", "cross", False,
     [("Mini Cooper SE", "infrastructure"), ("2026-03-28", "date"), ("AutoCheck", "service"), ("FIXD", "service"), ("Enterprise", "organization")],
     [("FIXD", "AutoCheck", "PREFERS")],
     "what caught mini se pending codes that the history report missed",
     "autocheck versus fixd pending codes used ev test drive rental"),
    # --- 46 ---
    ("Prefers the Volvo Cars app on Android Automotive over Google Maps for the XC40 Recharge because the live-range overlay actually talks to the HV pack instead of using the EPA-rated estimate.", "preference", "cross", False,
     [("Volvo Cars", "service"), ("Android Automotive", "platform"), ("Google Maps", "service"), ("XC40 Recharge", "infrastructure"), ("EPA", "organization")],
     [("Volvo Cars", "Google Maps", "PREFERS")],
     "which nav wins on the xc40 for live range truth",
     "volvo cars app android automotive live range epa estimate nav"),
    # --- 47 ---
    ("The Super Cruise subscription auto-renewed on 2026-01-20 for the Cadillac Lyriq at 25 dollars a month and the OnStar Guardian app replaced the third-party SafeBeacon SOS I'd been paying for.", "decision", "cross", False,
     [("Super Cruise", "service"), ("2026-01-20", "date"), ("Cadillac Lyriq", "infrastructure"), ("OnStar Guardian", "service"), ("SafeBeacon", "service")],
     [("OnStar Guardian", "SafeBeacon", "REPLACES")],
     "which sos service took over when the super cruise renewal hit",
     "gm super cruise renewal onstar guardian safebeacon sos swap"),
    # --- 48 ---
    ("Regret flooded in when the 2026-02-29 Subaru STARLINK subscription lapsed and the remote-start feature on the Outback turned into a paywalled in-app prompt with no grace period.", "problem", "cross", False,
     [("Regret", "emotion"), ("2026-02-29", "date"), ("Subaru STARLINK", "service"), ("Outback", "infrastructure")],
     [],
     "what made the outback remote start vanish overnight",
     "subaru starlink subscription lapse remote start paywall no grace"),
    # --- 49 ---
    ("The GasBuddy Pay replaced the Costco gas app for fueling the 2018 Subaru Outback on 2026-03-22 because the GasBuddy premium tier's 25-cent-per-gallon credit finally beat the Costco card rebate on non-member stations.", "decision", "cross", False,
     [("GasBuddy Pay", "service"), ("Costco", "organization"), ("Subaru Outback", "infrastructure"), ("2026-03-22", "date")],
     [("GasBuddy Pay", "Costco", "REPLACES")],
     "which fuel app won for the outback fill ups",
     "gasbuddy pay costco gas rebate premium tier fuel app swap"),
    # --- 50 ---
    ("Joy hit the morning the 2026-04-30 Ford Power-Up 5.4 on the F-150 Lightning finally added Apple Music lossless over Bluetooth LE Audio, because the Sonos Roam in the bed cluster-synced with the in-cab audio for the first time.", "milestone", "cross", False,
     [("Joy", "emotion"), ("2026-04-30", "date"), ("Ford Power-Up 5.4", "service"), ("F-150 Lightning", "infrastructure"), ("Apple Music", "service"), ("Bluetooth LE Audio", "protocol"), ("Sonos Roam", "infrastructure")],
     [("F-150 Lightning", "Bluetooth LE Audio", "USES"), ("Sonos Roam", "F-150 Lightning", "COMMUNICATES_WITH")],
     "when did the lightning finally bridge the speaker in the bed with the cab audio",
     "ford power up bluetooth le audio apple music lossless sonos cluster"),
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
