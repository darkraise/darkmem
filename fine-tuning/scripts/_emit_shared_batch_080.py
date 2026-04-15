"""One-off emitter for shared-base batch-080 — cross domain.

Slice: home automation meets tech (lighting, security, climate, energy) for
non-kitchen rooms. Writes 50 rows to data/v2/shared/batch_080.tmp.jsonl with
ids shared-03951..04000. The main session aggregates the tmp file into
shared.jsonl after validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_080.tmp.jsonl"
ID_OFFSET = 3950

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the bedroom Hue bulbs off the Hue Bridge onto Zigbee2MQTT running on the Home Assistant box because the Hue cloud kept dropping the wake-up routine when the internet flapped.", "decision", "cross", False,
     [("Hue", "service"), ("Hue Bridge", "infrastructure"), ("Zigbee2MQTT", "service"), ("Home Assistant", "platform")],
     [("Zigbee2MQTT", "Hue Bridge", "REPLACES"), ("Zigbee2MQTT", "Home Assistant", "DEPLOYED_ON")],
     "why did the bedroom lighting move off the official Hue bridge",
     "zigbee local control bridge replacement wake routine cloud outage"),
    # --- 2 ---
    ("Ecobee SmartThermostat Premium replaced the Nest Learning unit in the upstairs zone on 2026-02-08 because Nest's HomeKit support stayed broken after the Matter rollout while Ecobee shipped native HomeKit.", "decision", "cross", False,
     [("Ecobee SmartThermostat Premium", "infrastructure"), ("Nest Learning", "infrastructure"), ("2026-02-08", "date"), ("HomeKit", "platform"), ("Matter", "protocol")],
     [("Ecobee SmartThermostat Premium", "Nest Learning", "IMPROVES_ON"), ("Ecobee SmartThermostat Premium", "HomeKit", "SUPPORTS")],
     "when did the upstairs thermostat get swapped and what triggered it",
     "thermostat swap homekit support matter rollout zoning upstairs"),
    # --- 3 ---
    ("Aqara FP2 mmWave sensors replaced the old PIR motion sensors in the living room because the FP2's zone targeting actually keeps the lights on while reading still on the couch.", "decision", "cross", False,
     [("Aqara FP2", "infrastructure"), ("PIR", "technology"), ("living room", "place")],
     [("Aqara FP2", "PIR", "REPLACES")],
     "why did the living room presence detection get upgraded",
     "mmwave presence sensor zone targeting motion timeout reading still"),
    # --- 4 ---
    ("Reolink RLC-823A 16x replaced the Ring Stick Up Cam at the side gate in 2026-01-19 because the local NVR recording on the Reolink avoids the Ring subscription and feeds directly into Frigate.", "decision", "cross", False,
     [("Reolink RLC-823A 16x", "infrastructure"), ("Ring Stick Up Cam", "infrastructure"), ("2026-01-19", "date"), ("Frigate", "service")],
     [("Reolink RLC-823A 16x", "Ring Stick Up Cam", "REPLACES"), ("Reolink RLC-823A 16x", "Frigate", "COMMUNICATES_WITH")],
     "when did the side gate camera get swapped off Ring and onto local recording",
     "camera swap subscription avoidance local NVR object detection feed"),
    # --- 5 ---
    ("Lutron Caseta dimmers cover every overhead in the house because the Pico remotes and the radio reliability still beat anything Zigbee or Z-Wave puts in the wall.", "preference", "cross", False,
     [("Lutron Caseta", "infrastructure"), ("Pico", "infrastructure"), ("Zigbee", "protocol"), ("Z-Wave", "protocol")],
     [("Lutron Caseta", "Zigbee", "PREFERS"), ("Lutron Caseta", "Z-Wave", "PREFERS")],
     "which in-wall dimmer ecosystem won the house and why",
     "in wall dimmer radio reliability pico remote ecosystem choice"),
    # --- 6. noise ---
    ("Hold on, let me pull that up.", "fact", "noise", True, [], [], None, None),
    # --- 7 ---
    ("The August Wi-Fi Smart Lock got pulled off the front door in favor of an Aqara U100 because the Aqara joined Apple Home over Matter without needing the August bridge that kept dying every six weeks.", "decision", "cross", False,
     [("August Wi-Fi Smart Lock", "infrastructure"), ("Aqara U100", "infrastructure"), ("Apple Home", "platform"), ("Matter", "protocol")],
     [("Aqara U100", "August Wi-Fi Smart Lock", "REPLACES"), ("Aqara U100", "Matter", "SUPPORTS")],
     "why did the front door lock get swapped after years of August",
     "smart lock swap matter native bridge failure reliability door"),
    # --- 8 ---
    ("ESPHome firmware on a Wemos D1 Mini drives the bathroom exhaust fan from the Aranet4 humidity reading because the Sonoff RF bridge kept missing the trigger above 70 percent.", "architecture", "cross", False,
     [("ESPHome", "service"), ("Wemos D1 Mini", "infrastructure"), ("Aranet4", "infrastructure"), ("Sonoff", "infrastructure")],
     [("ESPHome", "Wemos D1 Mini", "DEPLOYED_ON"), ("ESPHome", "Sonoff", "REPLACES")],
     "how does the bathroom fan trigger off humidity now",
     "esp32 humidity automation exhaust fan bathroom firmware trigger"),
    # --- 9 ---
    ("The bedroom IKEA Fyrtur blinds run on a Node-RED schedule that watches sunrise from the local home_assistant.sun entity instead of the IKEA app because the IKEA cloud schedule drifted ten minutes a season.", "architecture", "cross", False,
     [("IKEA Fyrtur", "infrastructure"), ("Node-RED", "tool"), ("home_assistant.sun", "config"), ("IKEA", "organization")],
     [("Node-RED", "home_assistant.sun", "USES"), ("Node-RED", "IKEA", "REPLACES")],
     "how do the bedroom blinds open at the right sunrise time now",
     "smart blind schedule sunrise drift node red local sun entity"),
    # --- 10 ---
    ("The Sense energy monitor on the main panel taught us that the basement dehumidifier was burning 180 kWh a month, which kicked off the Mysa floor-heat retrofit decision.", "fact", "cross", False,
     [("Sense", "infrastructure"), ("Mysa", "infrastructure")],
     [("Sense", "Mysa", "CAUSES")],
     "what convinced us to pull the trigger on the basement floor heat retrofit",
     "energy monitor whole home dehumidifier draw floor heat decision"),
    # --- 11 ---
    ("IotaWatt replaced the Sense on the solar subpanel because IotaWatt's per-circuit CTs stream straight to InfluxDB and the Sense ML guesses kept misattributing the heat-pump pulls.", "decision", "cross", False,
     [("IotaWatt", "infrastructure"), ("Sense", "infrastructure"), ("InfluxDB", "database")],
     [("IotaWatt", "Sense", "REPLACES"), ("IotaWatt", "InfluxDB", "COMMUNICATES_WITH")],
     "why did the solar subpanel monitoring switch off Sense",
     "circuit level monitoring CT clamp time series database accurate"),
    # --- 12 ---
    ("The Awair Element in the nursery feeds CO2 readings into Home Assistant which cracks the window-vent automation when the room crosses 1100 ppm during nap time.", "architecture", "cross", False,
     [("Awair Element", "infrastructure"), ("Home Assistant", "platform"), ("nursery", "place")],
     [("Awair Element", "Home Assistant", "COMMUNICATES_WITH")],
     "how does the nursery air quality drive the window vent",
     "co2 monitor ventilation automation nap room threshold trigger"),
    # --- 13 ---
    ("Frustration boiled over on 2026-03-22 when the Eufy HomeBase 3 lost the entire 30-day clip archive after a firmware push and the support ticket sat for nine days.", "problem", "cross", False,
     [("Frustration", "emotion"), ("2026-03-22", "date"), ("Eufy HomeBase 3", "infrastructure")],
     [],
     "what wiped the camera archive in late March and how did support handle it",
     "camera archive loss firmware update support delay clip retention"),
    # --- 14 ---
    ("Ubiquiti UniFi Protect with G5 Bullets replaced the entire Eufy fleet across the property after the HomeBase fiasco because Protect runs on the same UDM Pro that already handles the network.", "decision", "cross", False,
     [("Ubiquiti", "organization"), ("UniFi Protect", "service"), ("G5 Bullet", "infrastructure"), ("Eufy", "organization"), ("UDM Pro", "infrastructure")],
     [("UniFi Protect", "Eufy", "REPLACES"), ("UniFi Protect", "UDM Pro", "DEPLOYED_ON")],
     "what camera platform took over for the property after the Eufy incident",
     "camera platform consolidation NVR network gateway integration"),
    # --- 15 ---
    ("Prefers the Lutron Serena shades over the SwitchBot retrofit on the bedroom skylight because the Serena's quiet motor doesn't wake Mei during the 6 a.m. open.", "preference", "cross", False,
     [("Lutron Serena", "infrastructure"), ("SwitchBot", "infrastructure"), ("Mei", "person")],
     [("Lutron Serena", "SwitchBot", "PREFERS")],
     "which shade brand won the skylight and why",
     "shade quietness motor noise bedroom early morning wake partner"),
    # --- 16 ---
    ("The Mysa for Electric Baseboards replaced the dumb line-voltage thermostats in the guest suite on 2026-01-14 because the existing Z-Wave 240V thermostats wouldn't expose setpoint over the local API.", "decision", "cross", False,
     [("Mysa for Electric Baseboards", "infrastructure"), ("2026-01-14", "date"), ("Z-Wave", "protocol")],
     [("Mysa for Electric Baseboards", "Z-Wave", "REPLACES")],
     "when did the guest suite baseboards get a real smart controller",
     "line voltage thermostat baseboard heat local API setpoint control"),
    # --- 17 ---
    ("The Reolink Doorbell PoE feeds Frigate which feeds the announcement automation on the Sonos One in the office because the Ring chime kit refused to stay paired through router reboots.", "architecture", "cross", False,
     [("Reolink Doorbell PoE", "infrastructure"), ("Frigate", "service"), ("Sonos One", "infrastructure"), ("Ring", "service")],
     [("Frigate", "Reolink Doorbell PoE", "USES"), ("Frigate", "Sonos One", "COMMUNICATES_WITH"), ("Frigate", "Ring", "REPLACES")],
     "how does the doorbell announce visitors in the office now",
     "poe doorbell object detection text to speech announcement chime"),
    # --- 18 ---
    ("Joy hit the first time the Goodnight scene actually worked end-to-end: lights down, Aqara U100 thrown, Ecobee dropped to 18 C, and the Reolink notifications armed.", "milestone", "cross", False,
     [("Joy", "emotion"), ("Goodnight", "pattern"), ("Aqara U100", "infrastructure"), ("Ecobee", "infrastructure"), ("Reolink", "organization")],
     [],
     "when did the bedtime scene finally chain everything in one tap",
     "scene end to end bedtime chain lights lock thermostat camera arm"),
    # --- 19 ---
    ("The solar+battery dashboard runs on Grafana fed by the Enphase Envoy local API because the Enphase Enlighten cloud only refreshes every fifteen minutes and the live battery SoC needs to drive the EV charge automation.", "architecture", "cross", False,
     [("Grafana", "tool"), ("Enphase Envoy", "infrastructure"), ("Enphase Enlighten", "service"), ("EV", "concept")],
     [("Grafana", "Enphase Envoy", "USES"), ("Enphase Envoy", "Enphase Enlighten", "REPLACES")],
     "how does the solar dashboard get fast enough data for the EV charging logic",
     "solar battery dashboard local api refresh rate ev charge automation"),
    # --- 20 ---
    ("Curiosity peaked when the Aranet4 in the home office showed CO2 climbing above 1400 ppm by 3 p.m., so a Levoit Core 600S air purifier and a HRV boost automation got added that week.", "fact", "cross", False,
     [("Curiosity", "emotion"), ("Aranet4", "infrastructure"), ("Levoit Core 600S", "infrastructure"), ("HRV", "infrastructure")],
     [],
     "what air-quality reading triggered the office purifier and HRV changes",
     "co2 spike afternoon office purifier hrv boost automation health"),
    # --- 21 ---
    ("ESPHome on a Shelly Plus 1PM controls the garage door opener directly off the GPIO because the MyQ cloud cut off the unofficial integrations and the local Shelly survives MyQ outages.", "decision", "cross", False,
     [("ESPHome", "service"), ("Shelly Plus 1PM", "infrastructure"), ("MyQ", "service")],
     [("ESPHome", "Shelly Plus 1PM", "DEPLOYED_ON"), ("Shelly Plus 1PM", "MyQ", "REPLACES")],
     "how does the garage door stay automatable now that MyQ closed the door",
     "garage opener local control gpio cloud cutoff integration loss"),
    # --- 22 ---
    ("The Schlage Encode Plus on the back door stayed in place because the Apple Home Key support means tapping the iPhone is faster than pulling the Aqara fob, even with the noisier motor.", "decision", "cross", False,
     [("Schlage Encode Plus", "infrastructure"), ("Apple Home Key", "service"), ("iPhone", "infrastructure"), ("Aqara", "organization")],
     [("Schlage Encode Plus", "Apple Home Key", "SUPPORTS")],
     "why did the back door lock not get the same Aqara swap as the front",
     "home key tap to unlock smart lock convenience back door"),
    # --- 23 ---
    ("Z2M's network map showed the Sonoff Zigbee dongle was hopping through the basement bulb instead of the dedicated router, so a CC2652P router on a USB extension fixed the LQI on the laundry sensor.", "problem", "cross", False,
     [("Z2M", "service"), ("Sonoff", "infrastructure"), ("CC2652P", "infrastructure"), ("LQI", "concept")],
     [("Z2M", "Sonoff", "USES")],
     "what fixed the flaky laundry room zigbee sensor",
     "zigbee mesh routing weak link signal quality dedicated router fix"),
    # --- 24 ---
    ("The 2026-03-08 Goodnight automation rewrite moved from YAML scripts to a Node-RED flow because the conditional branches for guest-staying and travel-mode got unreadable in pure HASS YAML.", "milestone", "cross", False,
     [("2026-03-08", "date"), ("Goodnight", "pattern"), ("YAML", "language"), ("Node-RED", "tool"), ("HASS", "platform")],
     [("Node-RED", "YAML", "REPLACES")],
     "when did the bedtime automation graduate out of pure YAML",
     "automation rewrite conditional branches readability flow editor"),
    # --- 25 ---
    ("Prefers Aqara T2 motion sensors over the Hue Outdoor Motion in the side yard because the Aqara's lux reporting fires the porch lights more reliably at dusk than the Hue's photocell.", "preference", "cross", False,
     [("Aqara T2", "infrastructure"), ("Hue Outdoor Motion", "infrastructure")],
     [("Aqara T2", "Hue Outdoor Motion", "PREFERS")],
     "which outdoor motion sensor wins for the dusk porch trigger",
     "outdoor motion sensor lux reporting dusk porch reliability"),
    # --- 26 ---
    ("The Tesla Powerwall reserve drops from 80 percent to 30 percent overnight via a Home Assistant blueprint when the Octopus Agile rate goes negative, which the Powerwall app on its own can't do.", "architecture", "cross", False,
     [("Tesla Powerwall", "infrastructure"), ("Home Assistant", "platform"), ("Octopus Agile", "service")],
     [("Home Assistant", "Tesla Powerwall", "CONFIGURES"), ("Home Assistant", "Octopus Agile", "USES")],
     "how does the home battery exploit the negative pricing windows",
     "battery reserve dynamic dynamic tariff negative price grid arbitrage"),
    # --- 27 ---
    ("Confusion set in when the Matter-over-Thread Aqara U100 stopped responding to Apple Home commands until the Apple TV 4K Thread border router was rebooted and the credentials republished.", "problem", "cross", False,
     [("Confusion", "emotion"), ("Matter", "protocol"), ("Thread", "protocol"), ("Aqara U100", "infrastructure"), ("Apple TV 4K", "infrastructure")],
     [("Aqara U100", "Thread", "USES")],
     "what made the Matter lock stop responding and how did it come back",
     "thread border router credential refresh matter outage homekit lock"),
    # --- 28 ---
    ("The Ratgdo board replaced the original Chamberlain logic on the garage door because Ratgdo speaks ESPHome natively, exposes the obstruction sensor, and avoids the MyQ subscription entirely.", "decision", "cross", False,
     [("Ratgdo", "infrastructure"), ("Chamberlain", "organization"), ("ESPHome", "service"), ("MyQ", "service")],
     [("Ratgdo", "Chamberlain", "REPLACES"), ("Ratgdo", "ESPHome", "SUPPORTS"), ("Ratgdo", "MyQ", "REPLACES")],
     "what hardware took over the garage door logic from Chamberlain",
     "garage door retrofit board obstruction sensor subscription removal"),
    # --- 29 ---
    ("The Frigate Plus subscription paid for itself on the 2026-02-04 package theft because the trained model flagged the porch loiter ten seconds before the box left.", "milestone", "cross", False,
     [("Frigate Plus", "service"), ("2026-02-04", "date")],
     [],
     "when did the camera AI finally catch a real porch incident in time",
     "object detection trained model porch loiter package theft alert"),
    # --- 30 ---
    ("Prefers the SwitchBot Hub 2 over the Broadlink RM4 Pro for the bedroom IR fan because SwitchBot's cloud-to-local Matter bridge actually exposes the fan as a real fan entity instead of a generic switch.", "preference", "cross", False,
     [("SwitchBot Hub 2", "infrastructure"), ("Broadlink RM4 Pro", "infrastructure"), ("Matter", "protocol")],
     [("SwitchBot Hub 2", "Broadlink RM4 Pro", "PREFERS"), ("SwitchBot Hub 2", "Matter", "SUPPORTS")],
     "which IR bridge won for the bedroom fan and why",
     "ir blaster matter bridge generic switch fan entity homekit support"),
    # --- 31 ---
    ("The Reolink CX810 added color night vision to the back patio on 2026-02-26 because the Ubiquiti G4 Pro's IR was washing out everything past the lemon tree.", "milestone", "cross", False,
     [("Reolink CX810", "infrastructure"), ("2026-02-26", "date"), ("Ubiquiti G4 Pro", "infrastructure")],
     [("Reolink CX810", "Ubiquiti G4 Pro", "IMPROVES_ON")],
     "when did the back patio finally get usable color at night",
     "color night vision infrared washout patio camera upgrade"),
    # --- 32 ---
    ("The Hue Sync Box stayed on the living room TV because Plex's tone mapping plus the Sync Box's HDMI passthrough still beats anything WLED could do behind the panel.", "preference", "cross", False,
     [("Hue Sync Box", "infrastructure"), ("Plex", "service"), ("WLED", "service")],
     [("Hue Sync Box", "WLED", "PREFERS")],
     "which bias light setup won for the living room TV",
     "ambient lighting hdmi passthrough tone mapping bias light television"),
    # --- 33 ---
    ("Home Assistant Yellow on a Pi CM5 with the Skyconnect dongle replaced the old Pi 4 install because the SSD slot under the Yellow finally killed the SD card corruption pattern.", "decision", "cross", False,
     [("Home Assistant Yellow", "infrastructure"), ("Pi CM5", "infrastructure"), ("Skyconnect", "infrastructure"), ("Pi 4", "infrastructure")],
     [("Home Assistant Yellow", "Pi 4", "REPLACES")],
     "what hardware finally ended the SD card corruption on the home automation box",
     "compute module SSD storage upgrade SD card failure pattern fix"),
    # --- 34. noise ---
    ("Hmm, give me a moment.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The Aqara TVOC Air Quality Monitor in the garage triggers the exhaust fan and an Apple Home notification when toluene spikes during a paint session, which the cheap PM2.5 sensor never caught.", "architecture", "cross", False,
     [("Aqara TVOC Air Quality Monitor", "infrastructure"), ("Apple Home", "platform"), ("PM2.5", "concept")],
     [("Aqara TVOC Air Quality Monitor", "PM2.5", "IMPROVES_ON"), ("Aqara TVOC Air Quality Monitor", "Apple Home", "COMMUNICATES_WITH")],
     "how does the garage paint session trigger ventilation and alerts",
     "voc sensor garage paint exhaust fan health alert ventilation"),
    # --- 36 ---
    ("Z-Wave JS replaced the deprecated OpenZWave integration on the home server in 2026-01-09 because OpenZWave stopped getting device fingerprints for the new Zooz Titan valve actuator.", "decision", "cross", False,
     [("Z-Wave JS", "service"), ("OpenZWave", "service"), ("2026-01-09", "date"), ("Zooz Titan", "infrastructure")],
     [("Z-Wave JS", "OpenZWave", "REPLACES")],
     "when did the Z-Wave stack get migrated and what device forced it",
     "z-wave stack migration device fingerprint valve actuator water"),
    # --- 37 ---
    ("The Aqara P2 leak sensor under the laundry sink triggers a Zooz Titan shutoff valve plus a phone alert through the ntfy.sh push, which the Moen Flo subscription used to do for 100 dollars a year.", "architecture", "cross", False,
     [("Aqara P2", "infrastructure"), ("Zooz Titan", "infrastructure"), ("ntfy.sh", "service"), ("Moen Flo", "service")],
     [("Aqara P2", "Zooz Titan", "COMMUNICATES_WITH"), ("Aqara P2", "Moen Flo", "REPLACES")],
     "how does the laundry leak detection trigger the main shutoff now",
     "leak sensor automatic shutoff push notification subscription removal"),
    # --- 38 ---
    ("The away-mode scene also lowers the Bond Bridge ceiling fans to low because the upstairs guest bedroom kept being left on high after weekend visitors and the energy report flagged it.", "fact", "cross", False,
     [("Bond Bridge", "infrastructure")],
     [],
     "what does the away scene do for ceiling fans in the guest room",
     "away scene ceiling fan low speed energy waste guest room"),
    # --- 39 ---
    ("Prefers Wyze Cam OG indoor cams over Tapo C200 in the kids' rooms because Wyze's local RTSP firmware feeds Frigate without any cloud round-trip and the Tapo blocks RTSP unless you use the official app.", "preference", "cross", False,
     [("Wyze Cam OG", "infrastructure"), ("Tapo C200", "infrastructure"), ("RTSP", "protocol"), ("Frigate", "service")],
     [("Wyze Cam OG", "Tapo C200", "PREFERS"), ("Wyze Cam OG", "RTSP", "SUPPORTS")],
     "which indoor cam wins for the kids' rooms and why",
     "indoor camera local rtsp firmware kids room privacy cloud avoidance"),
    # --- 40 ---
    ("Anxiety lifted on 2026-03-15 once the door-state dashboard on the kitchen Lenovo display started showing the Aqara U100 as locked at 11 p.m. instead of leaving it as a silent guess.", "milestone", "cross", False,
     [("Anxiety", "emotion"), ("2026-03-15", "date"), ("Lenovo", "organization"), ("Aqara U100", "infrastructure")],
     [],
     "when did the bedtime door-status check stop being a worry",
     "door status dashboard wall display peace of mind nighttime check"),
    # --- 41 ---
    ("The Hue Festavia string lights got pulled from the porch because Govee Curtain Lights with their LAN API integrate with Home Assistant Scenes without needing the Hue Bridge or the Hue cloud.", "decision", "cross", False,
     [("Hue Festavia", "infrastructure"), ("Govee Curtain Lights", "infrastructure"), ("Home Assistant", "platform"), ("Hue Bridge", "infrastructure")],
     [("Govee Curtain Lights", "Hue Festavia", "REPLACES"), ("Govee Curtain Lights", "Home Assistant", "COMMUNICATES_WITH")],
     "what replaced the porch string lights and why",
     "outdoor string lights lan api local control bridge avoidance"),
    # --- 42 ---
    ("HACS keeps the Frigate, Adaptive Lighting, and Powercalc custom integrations updated because the official Home Assistant repos still don't carry the right Powercalc fork.", "architecture", "cross", False,
     [("HACS", "service"), ("Frigate", "service"), ("Adaptive Lighting", "library"), ("Powercalc", "library")],
     [("HACS", "Frigate", "USES"), ("HACS", "Adaptive Lighting", "USES"), ("HACS", "Powercalc", "USES")],
     "how do the custom integrations stay current outside the official catalog",
     "community integration store custom component fork update channel"),
    # --- 43 ---
    ("The Adaptive Lighting integration shifts the master bedroom Hue color temperature from 4000K at 7 a.m. to 1900K by 9 p.m., which finally got Mei to stop running the bedside lamp on a separate dimmer.", "fact", "cross", False,
     [("Adaptive Lighting", "library"), ("Hue", "service"), ("Mei", "person")],
     [("Adaptive Lighting", "Hue", "CONFIGURES")],
     "what tamed the bedside lamp dimmer war in the master bedroom",
     "circadian color temperature shift bedside lamp partner preference"),
    # --- 44 ---
    ("Frustration spiked on 2026-02-19 when the Nest Protect smoke alarms stopped reporting battery state to Google Home after the Nest-to-Google migration killed the local API.", "problem", "cross", False,
     [("Frustration", "emotion"), ("2026-02-19", "date"), ("Nest Protect", "infrastructure"), ("Google Home", "platform")],
     [],
     "what broke about the smoke alarms after the Google migration",
     "smoke alarm battery reporting cloud migration api shutdown loss"),
    # --- 45 ---
    ("First Alert Z-Wave smoke and CO sensors replaced the Nest Protects in 2026-03-02 because the Z-Wave alarms speak directly to Home Assistant and don't depend on a Google account.", "decision", "cross", False,
     [("First Alert", "organization"), ("Z-Wave", "protocol"), ("Nest Protect", "infrastructure"), ("2026-03-02", "date"), ("Home Assistant", "platform"), ("Google", "organization")],
     [("First Alert", "Nest Protect", "REPLACES"), ("First Alert", "Home Assistant", "COMMUNICATES_WITH")],
     "what smoke alarm replaced the Nest Protects and what was the trigger",
     "smoke alarm replacement local protocol cloud independence vendor lock"),
    # --- 46 ---
    ("The 2026-04-01 wake routine ramps the Lutron Serena bedroom blinds up over twelve minutes while Adaptive Lighting eases the Hue from 1900K to 4000K, which beats every alarm clock we've tried.", "milestone", "cross", False,
     [("2026-04-01", "date"), ("Lutron Serena", "infrastructure"), ("Adaptive Lighting", "library"), ("Hue", "service")],
     [("Adaptive Lighting", "Hue", "CONFIGURES"), ("Lutron Serena", "Adaptive Lighting", "RELATED_TO")],
     "when did the sunrise wake routine go fully hands-off",
     "wake routine gradual blind open color temperature ramp alarm replace"),
    # --- 47 ---
    ("The Reolink TrackMix on the driveway replaced the static G5 Bullet at the same spot because the auto-track feature catches license plates pulling in that the static lens crops out.", "decision", "cross", False,
     [("Reolink TrackMix", "infrastructure"), ("G5 Bullet", "infrastructure")],
     [("Reolink TrackMix", "G5 Bullet", "IMPROVES_ON")],
     "why did the driveway camera get swapped to a tracking lens",
     "auto track ptz license plate capture driveway lens upgrade"),
    # --- 48 ---
    ("Mosquitto running on the Home Assistant box brokers Z2M, ESPHome, and the Frigate detection events because moving to a single MQTT broker simplified the dashboard wiring across all four namespaces.", "architecture", "cross", False,
     [("Mosquitto", "service"), ("Home Assistant", "platform"), ("Z2M", "service"), ("ESPHome", "service"), ("Frigate", "service"), ("MQTT", "protocol")],
     [("Mosquitto", "MQTT", "IMPLEMENTS"), ("Z2M", "Mosquitto", "USES"), ("ESPHome", "Mosquitto", "USES"), ("Frigate", "Mosquitto", "USES")],
     "how do all the local automations talk to each other now",
     "mqtt broker consolidation message bus topic namespace integration"),
    # --- 49 ---
    ("The Home Assistant Energy dashboard has been the canonical reference for the solar+heat-pump payback model since 2026-01-25 because the Enphase and Mysa numbers actually agree there.", "reference", "cross", False,
     [("Home Assistant Energy", "service"), ("2026-01-25", "date"), ("Enphase", "organization"), ("Mysa", "infrastructure")],
     [("Home Assistant Energy", "Enphase", "USES"), ("Home Assistant Energy", "Mysa", "USES")],
     "where does the household get the trustworthy solar plus heat pump numbers",
     "energy dashboard payback solar heat pump reconciled source of truth"),
    # --- 50 ---
    ("Relief came on 2026-03-30 when the away-mode scene survived the full week trip to Porto, with the Aqara U100 logging seven correct lock cycles, the Reolink fleet armed the whole time, and the Ecobee parked at 12 C.", "milestone", "cross", False,
     [("Relief", "emotion"), ("2026-03-30", "date"), ("Porto", "place"), ("Aqara U100", "infrastructure"), ("Reolink", "organization"), ("Ecobee", "infrastructure")],
     [],
     "when did the away-mode scene prove itself across a real trip",
     "away mode trip vacation lock cycles camera arming setback heat"),
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
