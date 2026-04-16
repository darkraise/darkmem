"""One-off emitter for shared-base batch-191 — home automation and smart-home platforms (Home Assistant, ESPHome, Zigbee2MQTT, Node-RED, Frigate, presence detection, energy).

Writes 50 rows to data/v2/shared/batch_191.tmp.jsonl with ids shared-09501..09550.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_191.tmp.jsonl"
ID_OFFSET = 9500

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated from Domoticz to Home Assistant on a Raspberry Pi 5; the richer integration catalogue and the Lovelace dashboard editor made the old PHP UI unbearable to keep maintaining.", "decision", "technical", False,
     [("Domoticz", "tool"), ("Home Assistant", "platform"), ("Raspberry Pi 5", "infrastructure"), ("Lovelace", "framework")],
     [("Home Assistant", "Domoticz", "REPLACES"), ("Home Assistant", "Raspberry Pi 5", "DEPLOYED_ON")],
     "which home automation hub did the household swap to and what finally killed the previous PHP-based tool",
     "domoticz home assistant raspberry pi lovelace migrate php ui"),
    # --- 2 ---
    ("Zigbee2MQTT now fronts every Aqara and IKEA Tradfri device through a Sonoff ZBDongle-P coordinator; the vendor hubs got decommissioned because cross-brand groups never worked through them.", "architecture", "technical", False,
     [("Zigbee2MQTT", "tool"), ("Aqara", "organization"), ("IKEA Tradfri", "organization"), ("Sonoff ZBDongle-P", "infrastructure")],
     [("Zigbee2MQTT", "Aqara", "SUPPORTS"), ("Zigbee2MQTT", "IKEA Tradfri", "SUPPORTS"), ("Sonoff ZBDongle-P", "Zigbee2MQTT", "APPLIES_TO")],
     "which Zigbee stack took over from the vendor hubs and why did cross-brand grouping force the switch",
     "zigbee2mqtt aqara tradfri sonoff zbdongle coordinator vendor hub"),
    # --- 3 ---
    ("ESPHome replaced Tasmota on the Shelly 1 relays after a firmware bake-off; native Home Assistant API over noise-encrypted TCP avoided the MQTT broker dependency for the lighting loop.", "decision", "technical", False,
     [("ESPHome", "framework"), ("Tasmota", "framework"), ("Shelly 1", "infrastructure"), ("Home Assistant API", "api"), ("MQTT", "protocol")],
     [("ESPHome", "Tasmota", "REPLACES"), ("ESPHome", "Shelly 1", "APPLIES_TO")],
     "which firmware replaced Tasmota on the Shelly relays and what broker dependency did the swap eliminate",
     "esphome tasmota shelly bake off native api mqtt broker"),
    # --- 4 ---
    ("Frigate NVR runs object detection on a Coral TPU and publishes person events to Home Assistant via MQTT; the Reolink RLC-820A streams sub-stream for detect and main-stream for recordings.", "decision", "technical", False,
     [("Frigate NVR", "tool"), ("Coral TPU", "infrastructure"), ("Home Assistant", "platform"), ("MQTT", "protocol"), ("Reolink RLC-820A", "infrastructure")],
     [("Frigate NVR", "Coral TPU", "USES"), ("Frigate NVR", "Home Assistant", "COMMUNICATES_WITH"), ("Reolink RLC-820A", "Frigate NVR", "APPLIES_TO")],
     "how does the NVR share person events with the hub and which camera roles separate detect from record",
     "frigate coral tpu reolink mqtt home assistant substream detect"),
    # --- 5 ---
    ("Matter over Thread now handles the door sensors through a Nanoleaf border router; the earlier Zigbee sensors kept dropping off the mesh whenever the neighbour's microwave ran.", "milestone", "technical", False,
     [("Matter", "protocol"), ("Thread", "protocol"), ("Nanoleaf", "organization"), ("border router", "pattern"), ("Zigbee", "protocol")],
     [("Matter", "Zigbee", "REPLACES"), ("Nanoleaf", "Thread", "SUPPORTS")],
     "which protocol combination took over the door sensors and what radio interference forced the change",
     "matter thread nanoleaf border router zigbee microwave interference"),
    # --- 6 ---
    ("HACS is pinned at v2.0.1 for the supervised install; auto-updates were disabled after a custom integration bumped its minimum Home Assistant core past our stable version and bricked startup.", "problem", "technical", False,
     [("HACS", "tool"), ("v2.0.1", "config"), ("Home Assistant", "platform"), ("custom integration", "pattern")],
     [("HACS", "Home Assistant", "COMMUNICATES_WITH")],
     "why is the community store pinned on the supervised box and what broke when it auto-updated",
     "hacs version pin supervised auto update brick startup integration"),
    # --- 7 ---
    ("Mosquitto broker sits on the same LXC as Home Assistant with persistence on; retained topics are how ESPHome devices publish last-seen state that survives a broker restart.", "decision", "technical", False,
     [("Mosquitto", "service"), ("Home Assistant", "platform"), ("LXC", "technology"), ("ESPHome", "framework"), ("retained topics", "pattern")],
     [("Mosquitto", "Home Assistant", "COMMUNICATES_WITH"), ("ESPHome", "Mosquitto", "USES")],
     "how does the MQTT broker keep device last-seen state through restarts and where does it run",
     "mosquitto broker lxc retained topic esphome persistence restart"),
    # --- 8 ---
    ("Node-RED flows orchestrate the sunset routine: a sun position event triggers a delay, a state check on the Philips Hue bridge, and a scene activation call that dims living-room lights to 40%.", "fact", "technical", False,
     [("Node-RED", "tool"), ("sunset routine", "pattern"), ("Philips Hue", "organization"), ("scene activation", "pattern")],
     [("Node-RED", "Philips Hue", "COMMUNICATES_WITH")],
     "which flow engine handles the sunset dim sequence and what trio of nodes makes it work",
     "node red sunset flow hue bridge scene dim delay state check"),
    # --- 9 ---
    ("Z-Wave JS UI drives the older Aeotec sensors through a Zooz 800 LR stick; the legacy zwave2mqtt bridge was retired once the new add-on gained OTW firmware flashing for the stick.", "decision", "technical", False,
     [("Z-Wave JS UI", "tool"), ("Aeotec", "organization"), ("Zooz 800 LR", "infrastructure"), ("zwave2mqtt", "tool"), ("OTW", "protocol")],
     [("Z-Wave JS UI", "zwave2mqtt", "REPLACES"), ("Z-Wave JS UI", "Zooz 800 LR", "USES")],
     "which Z-Wave frontend replaced the older bridge and which firmware-flash feature sealed the choice",
     "zwave js ui zooz 800 aeotec zwave2mqtt otw firmware flash"),
    # --- 10. noise ---
    ("The hallway catbowl seems to telegraph weather: water sloshes out exactly when a cold front is about to roll in over the coast.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("InfluxDB 2.7 ingests the energy dashboard metrics from Home Assistant; the long-term SQLite recorder was trimmed to seven days because Grafana panels now read from Influx directly.", "architecture", "technical", False,
     [("InfluxDB", "database"), ("2.7", "config"), ("Home Assistant", "platform"), ("SQLite", "database"), ("Grafana", "tool")],
     [("InfluxDB", "Home Assistant", "COMMUNICATES_WITH"), ("Grafana", "InfluxDB", "USES")],
     "which time-series store replaced the long recorder window and where do the energy panels query from now",
     "influxdb home assistant sqlite recorder grafana energy dashboard"),
    # --- 12 ---
    ("Bermuda is the preferred presence detection stack; ESPresence base stations still run as fallback but the BLE trilateration from Bermuda settled the kitchen-versus-dining ambiguity that plagued room-aware lights.", "preference", "technical", False,
     [("Bermuda", "tool"), ("ESPresence", "tool"), ("BLE", "protocol"), ("trilateration", "algorithm")],
     [("Bermuda", "ESPresence", "PREFERS"), ("Bermuda", "BLE", "USES")],
     "which presence detection tool is preferred and what ambiguity did BLE trilateration actually fix",
     "bermuda espresence ble trilateration presence kitchen dining room"),
    # --- 13 ---
    ("WLED on a WS2812B strip handles the under-cabinet accent lighting; the ESP32 pushes state changes to Home Assistant through a native WLED integration rather than generic MQTT lights.", "fact", "technical", False,
     [("WLED", "framework"), ("WS2812B", "infrastructure"), ("ESP32", "infrastructure"), ("Home Assistant", "platform"), ("MQTT", "protocol")],
     [("WLED", "ESP32", "DEPLOYED_ON"), ("WLED", "Home Assistant", "COMMUNICATES_WITH")],
     "which LED firmware runs the under-cabinet strip and why was the native integration chosen over MQTT",
     "wled ws2812b esp32 under cabinet home assistant native integration"),
    # --- 14 ---
    ("Apple HomeKit exposure runs through the HomeKit Bridge add-on; only the climate and lock entities are published so the Home app doesn't drown in the hundred-plus Zigbee sensors.", "decision", "personal", False,
     [("Apple HomeKit", "platform"), ("HomeKit Bridge", "service"), ("Home app", "tool"), ("Zigbee", "protocol")],
     [("HomeKit Bridge", "Apple HomeKit", "COMMUNICATES_WITH")],
     "how is HomeKit exposure scoped so the Home app doesn't drown in sensors from the Zigbee mesh",
     "homekit bridge filter climate lock zigbee sensor home app expose"),
    # --- 15 ---
    ("Chose a Homey Pro Early 2023 over a SmartThings hub for the guest apartment; first-class Matter Controller support and local Z-Wave made remote troubleshooting realistic without VPN hops.", "decision", "technical", False,
     [("Homey Pro", "platform"), ("Early 2023", "config"), ("SmartThings", "platform"), ("Matter Controller", "service"), ("Z-Wave", "protocol")],
     [("Homey Pro", "SmartThings", "PREFERS"), ("Homey Pro", "Matter Controller", "SUPPORTS")],
     "which guest-apartment hub was picked over SmartThings and what two capabilities made the call easy",
     "homey pro smartthings matter controller zwave local guest vpn"),
    # --- 16 ---
    ("Tasmota 13.4 stays on the legacy Sonoff Basic relays in the garage; ESPHome flashes failed serial detection on those early chips, so the fleet split along firmware lines.", "fact", "technical", False,
     [("Tasmota", "framework"), ("13.4", "config"), ("Sonoff Basic", "infrastructure"), ("ESPHome", "framework")],
     [("Tasmota", "Sonoff Basic", "APPLIES_TO")],
     "which firmware still owns the garage Sonoff relays and what flashing issue kept the fleet split",
     "tasmota sonoff basic esphome flash serial detect fleet split"),
    # --- 17 ---
    ("The energy dashboard tracks grid consumption through a Shelly EM clamp on the main feed; individual circuit readings come from Shelly Plug S smart plugs reporting watt-hours to Home Assistant.", "architecture", "technical", False,
     [("energy dashboard", "pattern"), ("Shelly EM", "infrastructure"), ("Shelly Plug S", "infrastructure"), ("Home Assistant", "platform")],
     [("Shelly EM", "energy dashboard", "APPLIES_TO"), ("Shelly Plug S", "Home Assistant", "COMMUNICATES_WITH")],
     "which two classes of Shelly hardware feed the energy dashboard and what do they each measure",
     "energy dashboard shelly em plug s clamp watt hour circuit"),
    # --- 18 ---
    ("NFC tags glued inside kitchen cabinets trigger scripts via the iOS Home Assistant companion app; tapping the coffee-cupboard tag starts the kettle and plays the morning radio playlist.", "fact", "personal", False,
     [("NFC tags", "infrastructure"), ("iOS Home Assistant companion", "tool"), ("morning radio playlist", "pattern")],
     [],
     "which tap-to-trigger hardware drives the coffee-cupboard automation and which companion app reads it",
     "nfc tag kitchen cupboard ios companion coffee kettle morning radio"),
    # --- 19 ---
    ("Scrypted was added alongside Frigate to bridge Reolink cameras into Apple HomeKit Secure Video; Frigate keeps the AI pipeline but HomeKit users wanted the native timeline on the Home app.", "architecture", "technical", False,
     [("Scrypted", "tool"), ("Frigate", "tool"), ("Reolink", "organization"), ("Apple HomeKit Secure Video", "platform"), ("Home app", "tool")],
     [("Scrypted", "Apple HomeKit Secure Video", "COMMUNICATES_WITH"), ("Scrypted", "Reolink", "SUPPORTS")],
     "which tool bridges the cameras to HomeKit Secure Video and why is it running alongside Frigate rather than replacing it",
     "scrypted frigate reolink homekit secure video timeline home app"),
    # --- 20 ---
    ("Google Home and Amazon Alexa both see Home Assistant through the Nabu Casa cloud subscription; local-LAN exposure via emulated_hue was retired because voice routines stopped discovering scenes.", "decision", "technical", False,
     [("Google Home", "platform"), ("Amazon Alexa", "platform"), ("Home Assistant", "platform"), ("Nabu Casa", "service"), ("emulated_hue", "tool")],
     [("Nabu Casa", "emulated_hue", "REPLACES"), ("Home Assistant", "Google Home", "COMMUNICATES_WITH"), ("Home Assistant", "Amazon Alexa", "COMMUNICATES_WITH")],
     "which cloud bridge replaced the emulated Hue path for voice assistants and what scene-discovery bug drove the change",
     "nabu casa emulated hue google alexa voice scene discover"),
    # --- 21 ---
    ("Blueprints power every motion-light automation; the one-off YAML scripts were collapsed into two blueprints (hallway and closet) so tweaking fade time only edits input fields.", "architecture", "technical", False,
     [("Blueprints", "pattern"), ("motion-light automation", "pattern"), ("YAML", "language"), ("hallway", "pattern"), ("closet", "pattern")],
     [("Blueprints", "YAML", "REPLACES")],
     "which Home Assistant feature replaced the one-off YAML motion scripts and how many blueprints cover the house",
     "blueprint motion light yaml script hallway closet fade time"),
    # --- 22 ---
    ("Presence arrival triggers the unlock-and-warm routine: phone BLE crosses the Bermuda threshold, front door Aqara lock unlocks, and the ecobee bumps setpoint by two degrees.", "fact", "personal", False,
     [("Bermuda", "tool"), ("Aqara", "organization"), ("ecobee", "organization"), ("unlock-and-warm routine", "pattern")],
     [("Bermuda", "unlock-and-warm routine", "APPLIES_TO")],
     "what three-step routine fires when the phone BLE beacon crosses the arrival threshold",
     "arrival presence bermuda aqara lock ecobee setpoint warm routine"),
    # --- 23 ---
    ("Replaced all Philips Hue bulbs in the bedroom with IKEA Tradfri equivalents; the colour accuracy gap was negligible for warm-white scenes and the per-bulb cost dropped by two thirds.", "decision", "personal", False,
     [("Philips Hue", "organization"), ("IKEA Tradfri", "organization"), ("warm-white", "pattern")],
     [("IKEA Tradfri", "Philips Hue", "REPLACES")],
     "which bulb swap cut the bedroom lighting cost and what colour scenario made the quality gap acceptable",
     "hue tradfri bedroom bulb warm white colour accuracy cost"),
    # --- 24 ---
    ("openHAB 4.1 runs in parallel on a backup Pi as cold-standby; a weekly rsync of the Home Assistant config feeds a conversion script that keeps the failover rules mostly in sync.", "architecture", "technical", False,
     [("openHAB", "platform"), ("4.1", "config"), ("Pi", "infrastructure"), ("Home Assistant", "platform"), ("rsync", "tool")],
     [("openHAB", "Home Assistant", "COMMUNICATES_WITH")],
     "which secondary platform runs as cold-standby and how does the primary config bleed over to it weekly",
     "openhab cold standby raspberry pi rsync home assistant failover"),
    # --- 25 ---
    ("Thread network ships with two border routers (Nanoleaf and an Apple TV 4K) so a single outage doesn't sever the Matter fabric; the redundancy fixed Sunday-evening dropouts that used to land every week.", "milestone", "technical", False,
     [("Thread", "protocol"), ("Nanoleaf", "organization"), ("Apple TV 4K", "infrastructure"), ("Matter", "protocol")],
     [("Nanoleaf", "Thread", "SUPPORTS"), ("Apple TV 4K", "Thread", "SUPPORTS")],
     "how many border routers now serve the Thread fabric and what weekly outage pattern went away",
     "thread border router nanoleaf apple tv matter redundancy sunday"),
    # --- 26 ---
    ("The Aqara FP2 mmWave sensor replaced the PIR in the office; seated-at-desk detection finally works for the long coding sessions where the old motion sensor turned lights off every eight minutes.", "problem", "personal", False,
     [("Aqara FP2", "infrastructure"), ("mmWave", "protocol"), ("PIR", "infrastructure"), ("office", "place")],
     [("Aqara FP2", "PIR", "REPLACES")],
     "which sensor upgrade fixed the office lights cutting out during long desk sessions",
     "aqara fp2 mmwave pir office motion coding session desk"),
    # --- 27 ---
    ("Frigate's detector_fps was cut from 10 to 5 after CPU pressure climbed on the Intel N100 mini-PC; detection quality held because the Coral TPU did the heavy lifting regardless.", "problem", "technical", False,
     [("Frigate", "tool"), ("detector_fps", "config"), ("Intel N100", "infrastructure"), ("Coral TPU", "infrastructure")],
     [("Frigate", "Coral TPU", "USES")],
     "which Frigate knob was turned down after N100 CPU pressure and why did detection quality not suffer",
     "frigate detector fps intel n100 coral tpu cpu pressure cut"),
    # --- 28 ---
    ("Reference: the production Home Assistant LXC sits at 192.168.0.210, MQTT broker at 192.168.0.211, Frigate at 192.168.0.212, and InfluxDB at 192.168.0.213 on the trusted VLAN.", "reference", "technical", False,
     [("Home Assistant", "platform"), ("192.168.0.210", "infrastructure"), ("MQTT", "protocol"), ("192.168.0.211", "infrastructure"), ("Frigate", "tool"), ("192.168.0.212", "infrastructure"), ("InfluxDB", "database"), ("192.168.0.213", "infrastructure")],
     [("Home Assistant", "192.168.0.210", "DEPLOYED_ON"), ("Frigate", "192.168.0.212", "DEPLOYED_ON"), ("InfluxDB", "192.168.0.213", "DEPLOYED_ON")],
     "which four IP addresses on the trusted VLAN host the core home automation stack",
     "home assistant mqtt frigate influxdb ip address vlan lxc"),
    # --- 29 ---
    ("Reference: the ZHA-to-Zigbee2MQTT migration script lives at scripts/zha_migrate.py and reads the zigbee.db SQLite file to seed the devices.yaml that Zigbee2MQTT consumes on first start.", "reference", "technical", False,
     [("ZHA", "framework"), ("Zigbee2MQTT", "tool"), ("scripts/zha_migrate.py", "file"), ("zigbee.db", "file"), ("devices.yaml", "file")],
     [("Zigbee2MQTT", "devices.yaml", "USES")],
     "which helper script and input file drive the ZHA migration into Zigbee2MQTT",
     "zha zigbee2mqtt migrate script zigbee db devices yaml seed"),
    # --- 30 ---
    ("Sonoff ZBMINI relays are preferred over Shelly Plus 1 for in-wall installs because their depth fits the shallow UK back-boxes; Shelly stays the pick wherever neutral-wire depth allows.", "preference", "technical", False,
     [("Sonoff ZBMINI", "infrastructure"), ("Shelly Plus 1", "infrastructure"), ("UK back-box", "pattern"), ("neutral-wire", "pattern")],
     [("Sonoff ZBMINI", "Shelly Plus 1", "PREFERS")],
     "which in-wall relay is preferred for shallow UK boxes and which box type keeps Shelly in play",
     "sonoff zbmini shelly plus uk back box depth neutral wire"),
    # --- 31 ---
    ("Node-RED's dashboard node drives a kitchen tablet showing the laundry cycle state; the MQTT topic from an ESPHome vibration sensor on the washer feeds a state-machine function node that posts push alerts.", "architecture", "technical", False,
     [("Node-RED", "tool"), ("dashboard node", "pattern"), ("MQTT", "protocol"), ("ESPHome", "framework"), ("vibration sensor", "infrastructure")],
     [("Node-RED", "MQTT", "USES"), ("ESPHome", "MQTT", "USES")],
     "how does the kitchen tablet show laundry state and what sensor feeds the state-machine function",
     "node red dashboard kitchen tablet laundry vibration esphome alert"),
    # --- 32 ---
    ("Milestone: the house hit 100% local control this quarter; the last cloud dependency (Tuya) got yanked when all smart plugs were reflashed with ESPHome through the local OTA server.", "milestone", "technical", False,
     [("Tuya", "organization"), ("ESPHome", "framework"), ("OTA", "protocol")],
     [("ESPHome", "Tuya", "REPLACES")],
     "which cloud dependency finally got removed when the plugs were reflashed and how was the update delivered",
     "local control tuya esphome ota reflash smart plug milestone"),
    # --- 33 ---
    ("Automation blueprint for guest-mode exposes only the living-room Chromecast, hallway light, and kitchen Sonos; the Home Assistant Person entity gate filters entities based on whether a household phone is home.", "architecture", "personal", False,
     [("guest-mode", "pattern"), ("Chromecast", "infrastructure"), ("Sonos", "organization"), ("Home Assistant", "platform"), ("Person entity", "concept")],
     [("Person entity", "guest-mode", "APPLIES_TO")],
     "how does guest-mode scope entity exposure and which household signal gates the filter",
     "guest mode chromecast sonos person entity filter household phone"),
    # --- 34 ---
    ("Milestone: the first Matter-over-WiFi plug (a Meross MSS315) joined the fabric through the Home Assistant Matter Controller add-on; previously WiFi plugs had to ride the ESPHome or Tasmota path.", "milestone", "technical", False,
     [("Matter", "protocol"), ("Meross MSS315", "infrastructure"), ("Home Assistant", "platform"), ("Matter Controller", "service"), ("ESPHome", "framework"), ("Tasmota", "framework")],
     [("Meross MSS315", "Matter Controller", "COMMUNICATES_WITH"), ("Matter Controller", "Home Assistant", "DEPLOYED_ON")],
     "which WiFi plug became the first native Matter device and which add-on brought it in",
     "matter wifi meross mss315 controller addon plug esphome tasmota"),
    # --- 35 ---
    ("Scheduled backup runs nightly at 03:00; Home Assistant's native snapshot uploads to Backblaze B2 through rclone, and the last seven snapshots stay on the local SSD for fast rollback.", "reference", "technical", False,
     [("Home Assistant", "platform"), ("snapshot", "pattern"), ("Backblaze B2", "service"), ("rclone", "tool"), ("03:00", "date")],
     [("rclone", "Backblaze B2", "COMMUNICATES_WITH")],
     "when does the backup run, where does it upload, and how many local snapshots are kept for rollback",
     "backup schedule snapshot backblaze b2 rclone local ssd rollback"),
    # --- 36 ---
    ("Debounce on the front-door Aqara contact sensor is set to 2 seconds; shorter values triggered duplicate open-close pairs every time the rubber seal briefly bounced the magnet past the threshold.", "reference", "technical", False,
     [("Aqara", "organization"), ("front-door", "place"), ("Debounce", "pattern"), ("2 seconds", "date")],
     [],
     "which configuration on the front-door sensor was raised to 2 seconds and what duplicate-event problem did it fix",
     "aqara contact debounce door open close duplicate rubber seal"),
    # --- 37 ---
    ("Reference: the ESPHome OTA password, the Home Assistant long-lived token, and the MQTT broker credentials live in /config/secrets.yaml; the file is sourced into YAML with !secret references.", "reference", "technical", False,
     [("ESPHome", "framework"), ("Home Assistant", "platform"), ("MQTT", "protocol"), ("/config/secrets.yaml", "file"), ("!secret", "pattern")],
     [],
     "where are the OTA password, long-lived token, and MQTT credentials stored and how are they referenced in YAML",
     "secrets yaml esphome ota token mqtt credential reference config"),
    # --- 38 ---
    ("Chose a dedicated VLAN 30 for IoT devices; the Unifi UDM Pro firewall rules block outbound internet for the WLED controllers and Tasmota plugs while allowing MQTT traffic to the trusted VLAN.", "decision", "technical", False,
     [("VLAN 30", "config"), ("Unifi UDM Pro", "infrastructure"), ("WLED", "framework"), ("Tasmota", "framework"), ("MQTT", "protocol")],
     [("Unifi UDM Pro", "VLAN 30", "APPLIES_TO")],
     "which network segment isolates the IoT devices and what firewall exception keeps MQTT flowing",
     "vlan 30 unifi udm iot firewall wled tasmota mqtt trusted"),
    # --- 39 ---
    ("Presence detection dropped the Life360 integration entirely; the phone-tracker cost privacy credits without measurable accuracy gain over the combined Bermuda BLE plus WiFi DHCP presence signals.", "decision", "personal", False,
     [("Life360", "service"), ("Bermuda", "tool"), ("BLE", "protocol"), ("WiFi DHCP presence", "pattern")],
     [("Bermuda", "Life360", "REPLACES")],
     "which phone-tracker service was cut and which two local signals now cover presence detection",
     "life360 bermuda ble wifi dhcp presence privacy phone tracker"),
    # --- 40 ---
    ("Shelly 2PM Gen3 handles the motorised blinds; cover position is exposed through the Home Assistant integration so a single slider on the dashboard drives all four bedroom windows in parallel.", "fact", "personal", False,
     [("Shelly 2PM Gen3", "infrastructure"), ("motorised blinds", "infrastructure"), ("Home Assistant", "platform")],
     [("Shelly 2PM Gen3", "Home Assistant", "COMMUNICATES_WITH")],
     "which Shelly model drives the bedroom blinds and how is cover position exposed on the dashboard",
     "shelly 2pm blinds cover position home assistant slider bedroom"),
    # --- 41 ---
    ("Milestone: Frigate ingested its millionth frame this week; the Reolink Duo 2 at the driveway and the RLC-520A at the back door account for 70% of events, which informed the camera placement audit.", "milestone", "technical", False,
     [("Frigate", "tool"), ("Reolink Duo 2", "infrastructure"), ("RLC-520A", "infrastructure"), ("driveway", "place"), ("back door", "place")],
     [("Reolink Duo 2", "Frigate", "APPLIES_TO")],
     "which milestone did Frigate hit this week and which two cameras generate most of the events",
     "frigate million frame reolink duo 520 driveway back door event"),
    # --- 42 ---
    ("Energy peaks trigger a Node-RED flow that disables non-critical loads; the heat pump water heater pauses automatically when grid draw exceeds 8 kW during the evening solar-export window.", "architecture", "technical", False,
     [("Node-RED", "tool"), ("heat pump water heater", "infrastructure"), ("grid draw", "concept"), ("8 kW", "config")],
     [],
     "how does the house shed non-critical load at peak draw and which appliance pauses first in the flow",
     "node red energy peak heat pump water heater grid draw 8kw"),
    # --- 43. noise ---
    ("A fox kept a 3 AM circuit through the compost pile for three weeks and then vanished without leaving even a tail tuft behind.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Preferred text-to-speech is Piper running locally on the Intel N100; Google Cloud TTS is kept only as the fallback for languages the local Piper voice pack doesn't cover.", "preference", "technical", False,
     [("Piper", "tool"), ("Intel N100", "infrastructure"), ("Google Cloud TTS", "service")],
     [("Piper", "Google Cloud TTS", "PREFERS"), ("Piper", "Intel N100", "DEPLOYED_ON")],
     "which TTS engine runs locally and what role does the Google cloud service still fill in the stack",
     "piper intel n100 google cloud tts local fallback language voice"),
    # --- 45 ---
    ("Automation for laundry done uses a watt-threshold template sensor: when washer power drops below 2 W for 60 seconds after being above 100 W, Home Assistant fires a notification to every household phone.", "fact", "personal", False,
     [("watt-threshold template sensor", "pattern"), ("washer", "infrastructure"), ("Home Assistant", "platform"), ("2 W", "config"), ("60 seconds", "date"), ("100 W", "config")],
     [("Home Assistant", "watt-threshold template sensor", "USES")],
     "which power-drop rule marks laundry done and what two thresholds plus timer combine in the template",
     "laundry watt threshold template sensor washer 2w 60s 100w"),
    # --- 46 ---
    ("The house lost Zigbee coverage in the garage; adding an IKEA Tradfri repeater plug halfway along the corridor extended the mesh so the door sensor finally stayed attached through winter.", "preference", "technical", False,
     [("Zigbee", "protocol"), ("garage", "place"), ("IKEA Tradfri", "organization"), ("repeater plug", "infrastructure"), ("door sensor", "infrastructure")],
     [("IKEA Tradfri", "Zigbee", "SUPPORTS")],
     "which cheap add-on fixed the garage Zigbee coverage gap and what seasonal symptom went away",
     "zigbee garage coverage ikea tradfri repeater plug door sensor"),
    # --- 47 ---
    ("Reference: the Z-Wave JS UI websocket endpoint is at ws://192.168.0.214:3000 and the companion REST admin is on port 8091; Home Assistant's Z-Wave JS integration hits the websocket path only.", "reference", "technical", False,
     [("Z-Wave JS UI", "tool"), ("ws://192.168.0.214:3000", "infrastructure"), ("8091", "infrastructure"), ("Home Assistant", "platform")],
     [("Home Assistant", "Z-Wave JS UI", "COMMUNICATES_WITH")],
     "which websocket URL and admin port belong to Z-Wave JS UI and which one does Home Assistant actually use",
     "zwave js ui websocket 3000 admin 8091 home assistant integration"),
    # --- 48 ---
    ("Decided against a Homey Bridge in the cabin; Home Assistant Yellow with a Zigbee radio handled the seven sensors fine, and the subscription-free local operation beat the monthly Homey fee.", "decision", "personal", False,
     [("Homey Bridge", "infrastructure"), ("cabin", "place"), ("Home Assistant Yellow", "infrastructure"), ("Zigbee", "protocol")],
     [("Home Assistant Yellow", "Homey Bridge", "PREFERS")],
     "which hub was chosen for the cabin over Homey Bridge and what recurring cost was avoided",
     "home assistant yellow cabin homey bridge zigbee subscription"),
    # --- 49 ---
    ("Milestone: the Matter Controller add-on graduated from beta in the 2026.3 core release; the household commissioned twelve Matter-over-Thread door-window sensors the same weekend.", "milestone", "technical", False,
     [("Matter Controller", "service"), ("2026.3", "config"), ("Matter", "protocol"), ("Thread", "protocol"), ("door-window sensors", "infrastructure")],
     [("Matter", "Thread", "USES")],
     "which add-on hit GA in the 2026.3 release and how many new sensors were commissioned the same weekend",
     "matter controller beta graduate 2026 3 thread door window"),
    # --- 50 ---
    ("Milestone: hit 500 automations across the house after the kids' bedroom rollout; the usage report pruned 40 duplicates and collapsed redundant timers into the new scheduler helper introduced in Home Assistant 2026.1.", "milestone", "technical", False,
     [("automations", "pattern"), ("usage report", "tool"), ("scheduler helper", "service"), ("Home Assistant", "platform"), ("2026.1", "config")],
     [("scheduler helper", "Home Assistant", "DEPLOYED_ON")],
     "which automation count milestone was hit and what consolidation feature did the 2026.1 release introduce",
     "automation 500 milestone scheduler helper duplicate prune report"),
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
